#!/usr/bin/env python3
"""eval41.py — прогон датасета через ML-стык + метрики против open_labels.xlsx.

Зона backend (W1). Этап 4: «прогон всех 41 видео; тюнинг порогов; holdout-метрики».
Для каждого видео вызывает пайплайн (по умолчанию ../ml/run.py — тот же стык, что и
сервис), сравнивает вердикт с разметкой, считает recall/precision (FAQ 16:
пропуск недопустим — recall приоритетен) и попадание таймкода в допуск.

Использование:
  python3 services/api/eval41.py                       # весь датасет
  python3 services/api/eval41.py --out report.json     # + JSON-отчёт
  python3 services/api/eval41.py --pipeline-cmd "..."  # другой пайплайн/пороги
"""
import argparse
import json
import re
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BASE = Path(__file__).resolve().parent
NS = "{http://schemas.openformats.org/spreadsheetml/2006/main}"
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def parse_labels(xlsx: Path) -> list[dict]:
    with zipfile.ZipFile(xlsx) as z:
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows: list[dict] = []
    for row in root.iter(f"{XLSX_NS}row"):
        cells: dict[str, str] = {}
        for c in row.iter(f"{XLSX_NS}c"):
            col = re.match(r"[A-Z]+", c.get("r", "A")).group(0)
            is_t = c.find(f"{XLSX_NS}is/{XLSX_NS}t")
            v_t = c.find(f"{XLSX_NS}v")
            text = is_t.text if is_t is not None else (v_t.text if v_t is not None else "")
            cells[col] = (text or "").strip()
        name = cells.get("A", "")
        if not name or name == "наименование файла":
            continue
        m = re.search(r"\d+", cells.get("B", "") or "")
        ts = float(m.group(0)) if m else None
        raw = cells.get("C", "") or ""
        label = "violation" if ("нарушение" in raw and "без" not in raw) else "no_violation"
        rows.append({"video": name, "label": label, "label_timecode": ts, "label_raw": raw})
    return rows


def find_video(videos_dir: Path, stem: str) -> Path | None:
    for candidate in (stem + ".mov", stem + ".MOV"):
        p = videos_dir / candidate
        if p.is_file():
            return p
    for p in videos_dir.glob("*.mov"):
        if p.stem.lower() == stem.lower():
            return p
    return None


def run_pipeline(cmd: list[str], video: Path) -> tuple[dict | None, str | None]:
    try:
        r = subprocess.run([*cmd, str(video)], capture_output=True, text=True, timeout=280)
    except subprocess.TimeoutExpired:
        return None, "pipeline timeout"
    if r.returncode != 0:
        return None, (r.stderr.strip() or "pipeline failed")[:200]
    try:
        return json.loads(r.stdout), None
    except Exception as exc:
        return None, f"bad json: {exc}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--videos-dir", default=str(BASE.parent.parent / "datasets" / "open" / "videos"))
    ap.add_argument("--labels", default=str(BASE.parent.parent / "datasets" / "open" / "open_labels.xlsx"))
    ap.add_argument("--pipeline-cmd", default=f"python3 {BASE.parent / 'ml' / 'run.py'}")
    ap.add_argument("--tolerance-sec", type=float, default=10.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    videos_dir = Path(args.videos_dir)
    cmd = args.pipeline_cmd.split()
    results: list[dict] = []
    for row in parse_labels(Path(args.labels)):
        video = find_video(videos_dir, row["video"])
        rec = dict(row)
        if video is None:
            rec.update({"video_found": False, "pred": None, "events": [], "error": "video file not found"})
            results.append(rec)
            print(f"{row['video']:>6}  FILE NOT FOUND", flush=True)
            continue
        out, err = run_pipeline(cmd, video)
        if out is None:
            rec.update({"video_found": True, "pred": None, "events": [], "error": err})
            results.append(rec)
            print(f"{row['video']:>6}  ERROR: {err}", flush=True)
            continue
        events = out.get("events", [])
        pred = "violation" if events else "no_violation"
        hit = None
        if row["label_timecode"] is not None and events:
            dt = min(abs(float(e.get("timecode_sec", 0)) - row["label_timecode"]) for e in events)
            hit = dt <= args.tolerance_sec
        rec.update({
            "video_found": True,
            "pred": pred,
            "events": [{"type": e.get("type"), "timecode_sec": e.get("timecode_sec")} for e in events],
            "timecode_hit": hit,
            "pipeline_version": out.get("pipeline_version"),
        })
        results.append(rec)
        extra = f"  tc_hit={hit}" if hit is not None else ""
        print(f"{row['video']:>6}  label={row['label']:<13} pred={pred:<13} events={len(events)}{extra}", flush=True)

    tp = fn = fp = tn = 0
    for r in results:
        if not r["pred"]:
            continue
        if r["label"] == "violation" and r["pred"] == "violation":
            tp += 1
        elif r["label"] == "violation":
            fn += 1
        elif r["pred"] == "violation":
            fp += 1
        else:
            tn += 1
    total = tp + fn + fp + tn
    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    hits = [r for r in results if r.get("timecode_hit")]
    summary = {
        "pipeline": args.pipeline_cmd,
        "tolerance_sec": args.tolerance_sec,
        "total": total,
        "errors": sum(1 for r in results if r.get("error")),
        "not_found": sum(1 for r in results if not r.get("video_found")),
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "timecode_hits": len(hits),
    }
    print("\n=== SUMMARY ===")
    for k, v in summary.items():
        print(f"{k}: {v}")
    if args.out:
        Path(args.out).write_text(
            json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"report: {args.out}")


if __name__ == "__main__":
    main()
