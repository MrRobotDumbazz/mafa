import base64
import json
import shlex
import subprocess
from pathlib import Path

from .base import Evidence, MLEvent, MLNormative, MLResult


class ExternalPipeline:
    def __init__(self, command: str) -> None:
        self._command = shlex.split(command)

    def analyze(self, video_path: Path) -> MLResult:
        out = subprocess.run(
            [*self._command, str(video_path)],
            capture_output=True, text=True, timeout=280,
        )
        if out.returncode != 0:
            raise ValueError(f"pipeline failed: {out.stderr.strip()[:200]}")
        return self._parse(json.loads(out.stdout), video_path)

    @staticmethod
    def _frame_payload(ev: dict) -> str | None:
        frame = ev.get("frame")
        if not frame:
            return None
        p = Path(frame)
        if p.is_file():
            return base64.b64encode(p.read_bytes()).decode("ascii")
        return frame

    def _parse(self, data: dict, video_path: Path) -> MLResult:
        if "events" not in data:
            raise ValueError("pipeline output missing 'events'")
        events = []
        for e in data.get("events", []):
            norm = e.get("normative")
            events.append(
                MLEvent(
                    type=e["type"],
                    timecode_sec=e["timecode_sec"],
                    description=e["description"],
                    evidence=[
                        Evidence(timestamp_sec=ev["timestamp_sec"], frame=self._frame_payload(ev))
                        for ev in e.get("evidence", [])
                    ],
                    timecode_end_sec=e.get("timecode_end_sec"),
                    confidence=e.get("confidence"),
                    normative=MLNormative(**norm) if norm else None,
                )
            )
        return MLResult(
            video_id=data.get("video_id", video_path.name),
            pipeline_version=data.get("pipeline_version", "external"),
            events=events,
        )
