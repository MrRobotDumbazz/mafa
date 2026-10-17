import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))

from primitives import Prim
from engine import Engine, EngineConfig
import catalog
import clips as C
import detector as D

PIPELINE_VERSION = "ml-v0.2-perception-yolox"


def _grab_jpeg(video_path, t, out_dir, video_id):
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{video_id}_{t:.1f}.jpg".replace(" ", "_"))
    if not os.path.exists(out):
        subprocess.run(
            ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{max(0.0, t):.2f}",
             "-i", video_path, "-frames:v", "1", "-q:v", "4", out],
            check=False,
        )
    return out if os.path.exists(out) else None


def features_to_prims_v1(feat, zones):
    prims = []
    w, h = feat["w"], feat["h"]
    for tr in zones.tracks:
        if tr is zones.cashier:
            continue
        who = f"client-{tr.tid}"
        prims.append(Prim("ZONE_ENTER", tr.first_t, who=who, args={"zone": "client"}))
        prims.append(Prim("ZONE_LEAVE", tr.last_t, who=who, args={"zone": "client"}))
    clip_list, aux = C.classify(feat, zones)
    for op, a, b in C.op_prims(clip_list):
        prims.append(Prim("OP_CLS", a, args={"op": op, "t0": a, "t1": b + 2.0}))
    for s, e in zones.third_person_segments(min_dur=3.0, staff_stay=1.5):
        prims.append(Prim("THIRD_IN_STAFF", s, dur=e - s, who="third", frames=(s, e)))
    leaves = zones.cashier_out_segments(min_dur=2.0)
    staff = zones.staff_rect
    norm = None
    if staff is not None:
        norm = (staff[0] / w, staff[1] / h, staff[2] / w, staff[3] / h)
    for s, e in feat["stobjs"].segments(norm_rect=norm, gap=5.0, min_dur=1.5):
        prims.append(Prim("STATE_MONEY_TABLE", s, dur=e - s, frames=(s, (s + e) / 2)))
        people_end = max((tr.last_t for tr in zones.tracks), default=None)
        if people_end is not None and s <= people_end <= e - 1.0:
            leaves.append((people_end, e))
    for s, e in sorted(set(leaves)):
        prims.append(Prim("LEAVE_STATION", s, dur=e - s, who="cashier", frames=(s, e)))
    for s, e, cls in aux["items"]:
        prims.append(Prim("STATE_ITEM_TABLE", s, dur=e - s, conf=0.6, frames=(s, (s + e) / 2)))
    for s, e, tid in aux["bags"]:
        prims.append(Prim("BAG_TO_CASHIER", s, dur=e - s, who=f"bag-{tid}", frames=(s, e)))
    return prims, clip_list


def analyze(video_path, video_id, evidence_dir=None, include_unverified=False, want_frames=True, keep_prims=False, backend="auto", onnx=None):
    if backend in ("auto", "dnn"):
        try:
            import cv2
            import numpy

            ok = True
        except Exception:
            ok = False
        if ok:
            import vision
            feat = vision.extract_features(video_path, backend=backend, onnx=onnx)
        else:
            import featurize as A
            feat = A.extract_features(video_path)
    else:
        import featurize as A
        feat = A.extract_features(video_path)
    clip_list = []
    if feat.get("kind") == "v1":
        from zones import Zones

        persons = [tr for tr in feat["confirmed"] if tr.cls == D.PERSON]
        zones = Zones(persons)
        prims, clip_list = features_to_prims_v1(feat, zones)
        pipeline_version = PIPELINE_VERSION + "/" + feat["backend"]
    else:
        import featurize as A
        zones = A.build_zones(feat)
        prims = features_to_prims(feat, zones)
        pipeline_version = "ml-v0.1-perception-classic"
    cfg = EngineConfig(enable_steps=False)
    violations = Engine(cfg).run(prims)
    events = []
    for v in violations:
        if not include_unverified and v.label in catalog.UNVERIFIED:
            continue
        ev = {
            "type": v.label,
            "timecode_sec": round(float(v.t_start), 1),
            "timecode_end_sec": round(float(v.t_end), 1),
            "description": catalog.describe(v.label, v.note),
            "confidence": round(float(v.conf), 2),
            "evidence": [],
        }
        norm = catalog.normative(v.label)
        if norm:
            ev["normative"] = norm
        ts = list(v.frames[:3]) or [v.t_start]
        for t in ts:
            item = {"timestamp_sec": round(float(t), 1)}
            if want_frames and evidence_dir:
                p = _grab_jpeg(video_path, t, evidence_dir, video_id)
                if p:
                    item["frame"] = p
            ev["evidence"].append(item)
        if not ev["evidence"]:
            ev["evidence"].append({"timestamp_sec": round(float(v.t_start), 1)})
        events.append(ev)
    events.sort(key=lambda e: e["timecode_sec"])
    summary = {
        "verdict": "violation" if events else "no_violation",
        "backend": pipeline_version,
        "clips": [{"category": c["category"], "t0": round(c["t0"], 1), "t1": round(c["t1"], 1)} for c in clip_list],
        "violations": [
            {
                "label": e["type"],
                "title_ru": catalog.describe(e["type"]),
                "timecode_sec": e["timecode_sec"],
                "normative": e.get("normative"),
            }
            for e in events
        ],
    }
    result = {"video_id": video_id, "pipeline_version": pipeline_version, "events": events, "summary": summary}
    if keep_prims:
        result["_prims"] = [(p.kind, p.t, p.dur, p.who) for p in prims]
    return result


def features_to_prims(feat, zones):
    prims = []
    w, h = feat["w"], feat["h"]
    staff = zones.staff_rect
    for tr in zones.tracks:
        if tr is zones.cashier:
            continue
        who = f"client-{tr.tid}"
        prims.append(Prim("ZONE_ENTER", tr.first_t, who=who, args={"zone": "client"}))
        prims.append(Prim("ZONE_LEAVE", tr.last_t, who=who, args={"zone": "client"}))
    for a, b in zones.client_windows:
        prims.append(Prim("OP_CLS", a, args={"op": "receive", "t0": a, "t1": b + 2.0}))
    for s, e in zones.cashier_out_segments(min_dur=2.0):
        prims.append(Prim("LEAVE_STATION", s, dur=e - s, who="cashier", frames=(s, e)))
    for s, e in zones.stable_third_segments(min_dur=4.0, min_dist=8.0):
        prims.append(Prim("THIRD_IN_STAFF", s, dur=e - s, who="third", frames=(s, e)))
    norm = None
    if staff is not None:
        norm = (staff[0] / w, staff[1] / h, staff[2] / w, staff[3] / h)
    people_end = max((tr.last_t for tr in zones.tracks), default=None)
    for s, e in feat["stobjs"].segments(norm_rect=norm, gap=5.0, min_dur=1.5):
        prims.append(Prim("STATE_MONEY_TABLE", s, dur=e - s, frames=(s, (s + e) / 2)))
        if people_end is not None and s <= people_end <= e - 1.0:
            prims.append(
                Prim(
                    "LEAVE_STATION",
                    people_end,
                    dur=e - people_end,
                    who="cashier",
                    frames=(people_end, (people_end + e) / 2),
                )
            )
    return prims
