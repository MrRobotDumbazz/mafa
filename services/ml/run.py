"""run.py — стык зоны ml с backend (интерфейс: services/api/README.md).

argv[1] = путь к .mov; stdout = JSON по contracts/ml_events.schema.json:
  {video_id, pipeline_version, events: [{type, timecode_sec, timecode_end_sec?,
   confidence, description, evidence: [{timestamp_sec, frame(base64|path)}]}]}
events: [] легитимно -> вердикт no_violation.

Слой восприятия (детекция/трекинг/поза -> примитивы) ещё не подключён (блокер: пакеты/весa).
Пока примитивы берутся из сайдкара `<видео>.prims.json` (список dict-полей Prim,
см. model/primitives.py) — это точка входа для будущего perception-слоя W3.
Без сайдкара примитивов нет -> движок ничего не детектирует -> no_violation.
"""
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "model"))

from engine import Engine
from primitives import load_prims

VERSION = "w3-engine-0.1+run-0.1"
CATALOG = BASE.parent.parent / "contracts" / "violation_catalog.yaml"

A1 = "ПП НБРК от 29.11.2019 № 231 «Правила осуществления кассовых операций и операций по инкассации…» (действует)"


def load_sidecar_prims(video: Path):
    sidecar = video.with_name(video.name + ".prims.json")
    if sidecar.is_file():
        return load_prims(json.loads(sidecar.read_text(encoding="utf-8")))
    return []


def load_catalog():
    titles = {}
    if not CATALOG.is_file():
        return titles
    current = None
    in_source = False
    for raw in CATALOG.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "types:":
            current = None
            continue
        if stripped.startswith("- id:"):
            current = {"id": stripped[5:].strip().strip('"'), "hint": ""}
            titles[current["id"]] = current
            in_source = False
            continue
        if current is None:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped == "source:":
            in_source = True
            continue
        if in_source and indent >= 6:
            continue
        in_source = False
        if stripped.startswith("title:"):
            current["title"] = stripped[6:].strip().strip('"')
        elif stripped.startswith("visible_hint:"):
            current["hint"] = stripped[13:].strip().strip('"')
    return titles


def describe(v, catalog):
    entry = catalog.get(v.label)
    if entry and entry.get("title"):
        text = entry["title"]
        if entry.get("hint"):
            text += f". На видео: {entry['hint']}"
        return text
    text = v.note or v.rule
    return f"{v.label}: {text}"


def extract_evidence(video: Path, timestamps, tmp: str):
    events = []
    for i, t in enumerate(list(timestamps)[:3]):
        jpg = Path(tmp) / f"ev_{i}_{t:.1f}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, float(t)):.3f}", "-i", str(video),
             "-frames:v", "1", "-q:v", "2", "-y", str(jpg)],
            capture_output=True, timeout=120,
        )
        item = {"timestamp_sec": round(float(t), 2)}
        if jpg.exists():
            item["frame"] = base64.b64encode(jpg.read_bytes()).decode("ascii")
        events.append(item)
    return events


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: run.py <video.mov>"}))
        sys.exit(2)
    video = Path(sys.argv[1])
    prims = load_sidecar_prims(video)
    violations = Engine().run(prims)
    catalog = load_catalog()
    with tempfile.TemporaryDirectory(prefix="forte_ml_") as tmp:
        events = []
        for v in violations:
            ts = list(v.frames[:3]) or [v.t_start]
            event = {
                "type": v.label,
                "timecode_sec": round(float(v.t_start), 2),
                "confidence": round(float(v.conf), 3),
                "description": describe(v, catalog),
                "evidence": extract_evidence(video, ts, tmp),
            }
            if float(v.t_end) > float(v.t_start):
                event["timecode_end_sec"] = round(float(v.t_end), 2)
            events.append(event)
    print(json.dumps({
        "video_id": video.name,
        "pipeline_version": VERSION,
        "events": events,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
