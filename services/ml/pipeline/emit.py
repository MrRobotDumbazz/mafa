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


def _rect_overlap(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / ua if ua > 0 else 0.0


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
    leaves = zones.cashier_out_segments(min_dur=4.0, wide=True)
    staff = zones.staff_rect
    norm = None
    if staff is not None:
        norm = (staff[0] / w, staff[1] / h, staff[2] / w, staff[3] / h)
    door = zones.entry_zone(w, h)
    last_client_leave = max((p.t for p in prims if p.kind == "ZONE_LEAVE" and p.who.startswith("client")), default=None)
    det = feat["stobjs"].segments_detailed(norm_rect=None, gap=6.0, min_dur=2.0)
    if feat.get("scene_states", False):
        for d in det:
            r = d["rect"]
            in_staff = norm and not (r[2] < norm[0] or r[0] > norm[2] or r[3] < norm[1] or r[1] > norm[3])
            overlap_door = door and not (r[2] < door[0] or r[0] > door[2] or r[3] < door[1] or r[1] > door[3])
            near_edge = r[0] <= 0.14 or r[1] <= 0.14 or r[2] >= 0.86 or r[3] >= 0.86
            if not d["persistent_to_end"]:
                continue
            if overlap_door and d["cells"] >= 2 and (last_client_leave is None or d["t0"] >= last_client_leave - 2.0):
                prims.append(Prim("STATE_DOOR_OPEN", d["t0"], dur=d["t1"] - d["t0"], conf=0.6, frames=(d["t0"], d["t1"])))
            elif in_staff and near_edge and 3 <= d["cells"] <= 40:
                prims.append(Prim("STATE_SAFE_OPEN", d["t0"], dur=d["t1"] - d["t0"], conf=0.55, frames=(d["t0"], d["t1"])))
    st = feat["stobjs"]
    staff_cells = set()
    if norm:
        ex = (max(0.0, norm[0] - 0.05), max(0.0, norm[1] - 0.05), min(1.0, norm[2] + 0.05), min(1.0, norm[3] + 0.05))
        for ci in range(st.cols * st.rows):
            cx0, cy0, cx1, cy1 = st.cell_rect(ci)
            if ex[0] <= (cx0 + cx1) / 2 <= ex[2] and ex[1] <= (cy0 + cy1) / 2 <= ex[3]:
                staff_cells.add(ci)
    merge_times = []
    for t, ci, nb in st.merges:
        if ci in staff_cells and nb in staff_cells:
            merge_times.append(t)
    merged_times = []
    for t in sorted(merge_times):
        if merged_times and t - merged_times[-1] <= 4.0:
            continue
        merged_times.append(t)
    for t in merged_times:
        prims.append(Prim("PILE_MERGE", t, dur=1.0, conf=0.6, frames=(t,)))
    for d in det:
        staff_hits = sum(1 for ci in d.get("cell_ids", ()) if ci in staff_cells)
        if norm and 1 <= staff_hits <= 25:
            prims.append(Prim("STATE_MONEY_TABLE", d["t0"], dur=d["t1"] - d["t0"], frames=(d["t0"], (d["t0"] + d["t1"]) / 2)))
            people_end = max((tr.last_t for tr in zones.tracks), default=None)
            if people_end is not None and d["t0"] <= people_end <= d["t1"] - 1.0:
                leaves.append((people_end, d["t1"]))
    for s, e in sorted(set(leaves)):
        prims.append(Prim("LEAVE_STATION", s, dur=e - s, who="cashier", frames=(s, e)))
    for s, e, cls in aux["items"]:
        prims.append(Prim("STATE_ITEM_TABLE", s, dur=e - s, conf=0.6, frames=(s, (s + e) / 2)))
    for s, e, tid in aux["bags"]:
        prims.append(Prim("BAG_TO_CASHIER", s, dur=e - s, who=f"bag-{tid}", frames=(s, e)))
    owl_tl = feat.get("owl") or []
    if owl_tl:
        door_boxes = [d["box"] for d in owl_tl if d["class"] == "DOOR"]
        door_box = None
        if len(door_boxes) >= 2:
            xs0 = sorted(b[0] for b in door_boxes)
            ys0 = sorted(b[1] for b in door_boxes)
            xs1 = sorted(b[2] for b in door_boxes)
            ys1 = sorted(b[3] for b in door_boxes)
            n = len(door_boxes)
            door_box = (xs0[n // 2] / w, ys0[n // 2] / h, xs1[n // 2] / w, ys1[n // 2] / h)
        keys = [d for d in owl_tl if d["class"] == "KEY"]
        if keys:
            s = min(d["t"] for d in keys)
            e = max(d["t"] for d in keys)
            prims.append(Prim("STATE_KEY_TABLE", s, dur=max(2.0, e - s), conf=0.6, frames=(s, e)))
        for d in owl_tl:
            if d["class"] == "ID_DOC":
                prims.append(Prim("DOC_SHOW", d["t"], conf=d["score"], who="client", frames=(d["t"],)))
            if d["class"] == "MONEY" and norm:
                bx = (d["box"][0] / w, d["box"][1] / h, d["box"][2] / w, d["box"][3] / h)
                if _rect_overlap(bx, norm) >= 0.2:
                    prims.append(Prim("STATE_MONEY_TABLE", d["t"], dur=5.0, conf=d["score"], frames=(d["t"],)))
        if door_box is not None:
            for d in det:
                if not d["persistent_to_end"]:
                    continue
                r = d["rect"]
                if _rect_overlap(r, door_box) >= 0.25 and d["cells"] >= 1:
                    prims.append(Prim("STATE_DOOR_OPEN", d["t0"], dur=d["t1"] - d["t0"], conf=0.65, frames=(d["t0"], d["t1"])))
                elif norm and 3 <= d["cells"] <= 60 and _rect_overlap(r, norm) >= 0.1 and (r[0] <= 0.2 or r[1] <= 0.2 or r[2] >= 0.8 or r[3] >= 0.8):
                    prims.append(Prim("STATE_SAFE_OPEN", d["t0"], dur=d["t1"] - d["t0"], conf=0.55, frames=(d["t0"], d["t1"])))
    wrists = feat.get("wrists") or []
    if wrists and zones.cashier is not None:
        cy_tid = zones.cashier.tid
        series = [(t, x, y) for t, tid, x, y in wrists if tid == cy_tid]
        series.sort()
        swings = 0
        s0 = None
        last_dir = 0
        for i in range(1, len(series)):
            dy = series[i][2] - series[i - 1][2]
            if abs(dy) < 2.5:
                continue
            d = 1 if dy > 0 else -1
            if last_dir and d != last_dir:
                swings += 1
            last_dir = d
            if swings == 4 and s0 is None:
                s0 = series[max(0, i - 8)][0]
            if swings >= 14:
                prims.append(Prim("COUNT_MONEY", s0 if s0 is not None else series[0][0], dur=series[i][0] - (s0 or series[0][0]), who="cashier", conf=0.6, frames=(series[i][0],)))
                break
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
    cfg = EngineConfig(
        enable_steps=False,
        observe_doc=bool(feat.get("owl")),
        observe_count=bool(feat.get("wrists")) and feat.get("kind") == "v1",
    )
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
