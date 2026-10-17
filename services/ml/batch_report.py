import argparse
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "pipeline"))
sys.path.insert(0, os.path.join(BASE, "model"))

from emit import analyze
import catalog


def collect(paths):
    rows = []
    for p in paths:
        vid = os.path.splitext(os.path.basename(p))[0]
        t0 = time.time()
        try:
            res = analyze(p, vid, evidence_dir=None, include_unverified=True, want_frames=False)
            rows.append(
                {
                    "video_id": vid,
                    "path": p,
                    "verdict": res["summary"]["verdict"],
                    "backend": res["pipeline_version"],
                    "clips": res["summary"]["clips"],
                    "events": [
                        {
                            "label": e["type"],
                            "title_ru": catalog.describe(e["type"]),
                            "timecode_sec": e["timecode_sec"],
                            "confidence": e["confidence"],
                            "normative": e.get("normative"),
                        }
                        for e in res["events"]
                    ],
                    "sec": round(time.time() - t0, 1),
                }
            )
        except Exception as ex:
            rows.append({"video_id": vid, "path": p, "verdict": "error", "error": str(ex)})
    return rows


def to_markdown(rows):
    viol = [r for r in rows if r.get("verdict") == "violation"]
    clean = [r for r in rows if r.get("verdict") == "no_violation"]
    lines = [
        "# Отчёт по загруженным видео",
        "",
        f"Дата: {time.strftime('%Y-%m-%d %H:%M')} | Видео: {len(rows)} | Нарушения: {len(viol)} | Без нарушений: {len(clean)} | Ошибки: {len(rows) - len(viol) - len(clean)}",
        "",
    ]
    for r in rows:
        verdict = {"violation": "НАРУШЕНИЕ", "no_violation": "без нарушения"}.get(r.get("verdict"), r.get("verdict", "?"))
        lines.append(f"## {r['video_id']} — {verdict}")
        lines.append("")
        if r.get("verdict") == "error":
            lines.append(f"Ошибка обработки: {r.get('error')}")
            lines.append("")
            continue
        lines.append(f"Бэкенд: `{r.get('backend')}` | Клипы: " + (", ".join(f"{c['category']}[{c['t0']}–{c['t1']}s]" for c in r["clips"]) or "—"))
        lines.append("")
        if r["events"]:
            lines.append("| label (код) | что это | таймкод, с | уверенность | норматив |")
            lines.append("|---|---|---|---|---|")
            for e in r["events"]:
                norm = e.get("normative") or {}
                nref = f"{norm.get('document', '')}, {norm.get('clause', '')}".strip(", ") or "не верифицировано"
                lines.append(f"| `{e['label']}` | {e['title_ru']} | {e['timecode_sec']} | {e['confidence']} | {nref} |")
        else:
            lines.append("Нарушений не обнаружено.")
        lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help=".mov файлы и/или директории")
    ap.add_argument("--out-dir", default=os.path.join(BASE, "research"))
    args = ap.parse_args()
    paths = []
    for x in args.inputs:
        if os.path.isdir(x):
            paths.extend(sorted(os.path.join(x, f) for f in os.listdir(x) if f.lower().endswith(".mov")))
        else:
            paths.append(x)
    rows = collect(paths)
    os.makedirs(args.out_dir, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    md = os.path.join(args.out_dir, f"uploads_report_{stamp}.md")
    js = os.path.join(args.out_dir, f"uploads_report_{stamp}.json")
    with open(md, "w", encoding="utf-8") as f:
        f.write(to_markdown(rows) + "\n")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"processed: {len(rows)} -> {md}")


if __name__ == "__main__":
    main()
