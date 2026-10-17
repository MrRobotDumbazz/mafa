from pathlib import Path

from ..extract import extract_frame_jpeg_b64, probe_duration_sec
from .base import Evidence, MLEvent, MLResult


class MockPipeline:
    version = "mock-0.1"

    def analyze(self, video_path: Path) -> MLResult:
        duration = probe_duration_sec(video_path)
        points = [duration * 0.3] if duration <= 20 else [duration * 0.3, duration * 0.6]
        events: list[MLEvent] = []
        for i, t in enumerate(points, start=1):
            frame_path = video_path.parent / f"{video_path.stem}_ev{i}.jpg"
            image = extract_frame_jpeg_b64(video_path, t, frame_path)
            events.append(
                MLEvent(
                    type="mock_event",
                    timecode_sec=round(t, 2),
                    confidence=0.5,
                    description="Мок-событие: пайплайн зоны ml ещё не подключён; таймкод и кадр-доказательство реальные.",
                    evidence=[Evidence(timestamp_sec=round(t, 2), frame=image)],
                )
            )
        return MLResult(video_id=video_path.name, pipeline_version=self.version, events=events)
