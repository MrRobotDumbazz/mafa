import base64
import subprocess
from pathlib import Path


def probe_duration_sec(video_path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "csv=p=0",
            str(video_path),
        ],
        capture_output=True, text=True, timeout=60,
    )
    if out.returncode != 0:
        raise ValueError(f"ffprobe failed: {out.stderr.strip()[:200]}")
    return float(out.stdout.strip())


def extract_frame_jpeg_b64(video_path: Path, timestamp_sec: float, out_path: Path) -> str:
    out = subprocess.run(
        [
            "ffmpeg", "-v", "error",
            "-ss", f"{max(0.0, timestamp_sec):.3f}",
            "-i", str(video_path),
            "-frames:v", "1", "-q:v", "2", "-y",
            str(out_path),
        ],
        capture_output=True, timeout=120,
    )
    if out.returncode != 0 or not out_path.exists():
        raise ValueError(f"frame extraction failed at {timestamp_sec}")
    return base64.b64encode(out_path.read_bytes()).decode("ascii")
