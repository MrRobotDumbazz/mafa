import argparse
import hashlib
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "pipeline"))
sys.path.insert(0, os.path.join(BASE, "model"))

import labels
from emit import analyze

VID_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "datasets", "open", "videos"))
LABELS_XLSX = os.path.join(BASE, "open_labels.xlsx")
RESEARCH = os.path.join(BASE, "research")
TIMECODE_TOL_SEC = 10.0


def norm(s):
    return labels.norm_name(s)


def video_files():
    out = {}
    for fn in os.listdir(VID_DIR):
        if fn.lower().endswith(".mov"):
            out[norm(os.path.splitext(fn)[0])] = os.path.join(VID_DIR, fn)
    return out


def stratified_split(gt, seed=42, holdout_frac=0.3):
    def key(name):
        return hashlib.sha256(f"{seed}:{name}".encode()).hexdigest()

    tune, hold = [], []
    for verdict in ("violation", "clean"):
        names = sorted(n for n, g in gt.items() if g["verdict"] == verdict and n in video_files.cache)
        names.sort(key=key)
        k = max(1, round(len(names) * holdout_frac)) if len(names) > 3 else 0
        hold.extend(names[:k])
        tune.extend(names[k:])
    return sorted(tune), sorted(hold)


def run_set(names, paths, backend="auto"):
    preds = {}
    for name in names:
        path = paths[name]
        t0 = time.time()
        try:
            res = analyze(path, name, evidence_dir=None, include_unverified=True, want_frames=False, backend=backend)
            events = [{"type": e["type"], "t": e["timecode_sec"]} for e in res["events"]]
            preds[name] = {"verdict": "violation" if events else "clean", "events": events, "sec": round(time.time() - t0, 1)}
        except Exception as e:
            preds[name] = {"verdict": "error", "events": [], "error": str(e), "sec": round(time.time() - t0, 1)}
    return preds


def metrics(gt, preds, names):
    tp = fp = fn_ = tn = 0
    for n in names:
        g = gt[n]["verdict"] == "violation"
        p = preds[n]["verdict"] == "violation"
        if g and p:
            tp += 1
        elif g and not p:
            fn_ += 1
        elif not g and p:
            fp += 1
        else:
            tn += 1
    rec = tp / (tp + fn_) if tp + fn_ else 0.0
    prec = tp / (tp + fp) if tp + fp else 0.0
    f1 = 2 * rec * prec / (rec + prec) if rec + prec else 0.0
    fpr = fp / (fp + tn) if fp + tn else 0.0
    return {"tp": tp, "fp": fp, "fn": fn_, "tn": tn, "recall": rec, "precision": prec, "f1": f1, "fpr": fpr}


def timecode_hits(gt, preds, names):
    total = hit = 0
    for n in names:
        g = gt[n]
        if g["verdict"] != "violation" or not g["t"]:
            continue
        total += 1
        if any(abs(e["t"] - g["t"]) <= TIMECODE_TOL_SEC for e in preds[n]["events"]):
            hit += 1
    return hit, total


def per_type(gt, preds, names):
    rows = []
    for n in names:
        g = gt[n]
        if g["verdict"] != "violation":
            continue
        expected = labels.GT_TYPE_MAP.get(g["hyp"], "ANOM_UNKNOWN" if g["hyp"] else None)
        got = {e["type"] for e in preds[n]["events"]}
        rows.append((n, g["hyp"], expected, g["t"], sorted(got)))
    return rows


def write_report(gt, tune, hold, preds_tune, preds_hold, path):
    m_t = metrics(gt, preds_tune, tune)
    m_h = metrics(gt, preds_hold, hold)
    h_t = timecode_hits(gt, preds_tune, tune)
    h_h = timecode_hits(gt, preds_hold, hold)
    lines = [
        "# Holdout-отчёт v0.1 (perception ffmpeg+stdlib, без весов)",
        "",
        f"Дата: {time.strftime('%Y-%m-%d %H:%M')} | Split: seed 42, стратифицированный 70/30 по вердикту.",
        f"Tune: {len(tune)} видео | Holdout: {len(hold)} видео. Тюнинг порогов — только на tune.",
        "",
        "## Вердикт по видео (recall-приоритет, FAQ 16)",
        "",
        "| набор | TP | FP | FN | TN | recall | precision | F1 | FPR |",
        "|---|---|---|---|---|---|---|---|---|",
        f"| tune | {m_t['tp']} | {m_t['fp']} | {m_t['fn']} | {m_t['tn']} | {m_t['recall']:.2f} | {m_t['precision']:.2f} | {m_t['f1']:.2f} | {m_t['fpr']:.2f} |",
        f"| holdout | {m_h['tp']} | {m_h['fp']} | {m_h['fn']} | {m_h['tn']} | {m_h['recall']:.2f} | {m_h['precision']:.2f} | {m_h['f1']:.2f} | {m_h['fpr']:.2f} |",
        "",
        "## Попадание в таймкод (±10 с) среди нарушений с известным t",
        "",
        f"- tune: {h_t[0]}/{h_t[1]}",
        f"- holdout: {h_h[0]}/{h_h[1]}",
        "",
        "## Детали по holdout (тип разметки → предсказанные типы)",
        "",
        "| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |",
        "|---|---|---|---|---|",
    ]
    for n, hyp, exp, t, got in per_type(gt, preds_hold, hold):
        lines.append(f"| {n} | {hyp or '—'} | {exp or '—'} | {t if t else '—'} | {', '.join(got) or '—'} |")
    lines += [
        "",
        "## Детали по tune",
        "",
        "| видео | гипотеза разметки | ожидаемый label | t_gt | предсказано |",
        "|---|---|---|---|---|",
    ]
    for n, hyp, exp, t, got in per_type(gt, preds_tune, tune):
        lines.append(f"| {n} | {hyp or '—'} | {exp or '—'} | {t if t else '—'} | {', '.join(got) or '—'} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["tune", "holdout", "all"], default="all")
    ap.add_argument("--split-only", action="store_true")
    ap.add_argument("--backend", choices=["auto", "dnn", "classic"], default="auto")
    args = ap.parse_args()
    video_files.cache = {}
    paths = video_files()
    video_files.cache = paths
    gt = labels.load_labels(LABELS_XLSX)
    matched = {n: g for n, g in gt.items() if n in paths}
    tune, hold = stratified_split(matched)
    print(f"videos: {len(paths)} | labels matched: {len(matched)} | tune: {len(tune)} | holdout: {len(hold)}")
    if args.split_only:
        print("tune:", tune)
        print("holdout:", hold)
        return
    names = {"tune": tune, "holdout": hold, "all": tune + hold}[args.set]
    preds = run_set(names, paths, backend=args.backend)
    all_preds = {}
    for pred_name, pred_set in (("tune", tune), ("holdout", hold)):
        if pred_name == args.set or args.set == "all":
            all_preds.update({n: preds[n] for n in pred_set if n in preds})
    other = run_set([], {})
    out_json = os.path.join(RESEARCH, "holdout_predictions.json")
    existing = {}
    if os.path.exists(out_json):
        with open(out_json, encoding="utf-8") as f:
            existing = json.load(f)
    existing.update(all_preds if all_preds else preds)
    os.makedirs(RESEARCH, exist_ok=True)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=1)
    if args.set == "all":
        write_report(matched, tune, hold, {n: preds[n] for n in tune}, {n: preds[n] for n in hold}, os.path.join(RESEARCH, "holdout_report.md"))
        m_h = metrics(matched, preds, hold)
        print("holdout:", m_h)
    else:
        m = metrics(matched, preds, names)
        print(args.set, m)


if __name__ == "__main__":
    main()
