import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "pipeline"))

import labels

VID_DIR = os.path.normpath(os.path.join(BASE, "..", "..", "datasets", "open", "videos"))
LABELS_XLSX = os.path.join(BASE, "open_labels.xlsx")


def probe(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
        capture_output=True, text=True,
    )
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    fps = v.get("avg_frame_rate", "0/1")
    try:
        num, den = fps.split("/")
        fps = float(num) / float(den) if float(den) else 0.0
    except ValueError:
        fps = 0.0
    return {
        "w": v.get("width"),
        "h": v.get("height"),
        "fps": round(fps, 2),
        "dur": round(float(d.get("format", {}).get("duration", 0)), 1),
        "mb": round(os.path.getsize(path) / 1e6, 1),
        "codec": v.get("codec_name"),
    }


def main():
    gt = labels.load_labels(LABELS_XLSX)
    files = sorted(
        f for f in os.listdir(VID_DIR) if f.lower().endswith(".mov")
    )
    rows = []
    for fn in files:
        stem = labels.norm_name(os.path.splitext(fn)[0])
        info = probe(os.path.join(VID_DIR, fn))
        g = gt.get(stem, {})
        rows.append({"name": stem, "file": fn, **info, "verdict": g.get("verdict", "?"), "t": g.get("t"), "hyp": g.get("hyp", "")})
    os.makedirs(os.path.join(BASE, "research"), exist_ok=True)
    with open(os.path.join(BASE, "research", "eda_videos.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    durs = [r["dur"] for r in rows if r["dur"]]
    dims = {}
    for r in rows:
        dims[f"{r['w']}x{r['h']}@{r['fps']}"] = dims.get(f"{r['w']}x{r['h']}@{r['fps']}", 0) + 1
    viol = [r for r in rows if r["verdict"] == "violation"]
    clean = [r for r in rows if r["verdict"] == "clean"]
    lines = [
        "# EDA: датасет открытых видео",
        "",
        f"Всего файлов: {len(rows)} (метки сопоставлены: {len([r for r in rows if r['verdict'] != '?'])}).",
        f"Нарушений: {len(viol)} | Без нарушения: {len(clean)}.",
        f"Длительность: мин {min(durs):.0f} с / макс {max(durs):.0f} с / медиана {sorted(durs)[len(durs)//2]:.0f} с.",
        f"Размеры/fps: {dims}.",
        "",
        "| видео | dur,с | WxH@fps | МБ | вердикт | t_gt | гипотеза |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(rows, key=lambda x: x["name"]):
        lines.append(f"| {r['name']} | {r['dur']} | {r['w']}x{r['h']}@{r['fps']} | {r['mb']} | {r['verdict']} | {r['t'] if r['t'] else '—'} | {r['hyp'] or '—'} |")
    with open(os.path.join(BASE, "research", "eda_videos.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"EDA: {len(rows)} videos -> research/eda_videos.md")


if __name__ == "__main__":
    main()
