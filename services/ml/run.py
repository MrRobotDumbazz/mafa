import argparse
import json
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "pipeline"))
sys.path.insert(0, os.path.join(BASE, "model"))

from emit import analyze


def validate_mov(path):
    if not os.path.isfile(path):
        return f"file not found: {path}", None
    if not path.lower().endswith(".mov"):
        return "only .mov files are supported", None
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height",
         "-show_entries", "format=duration", "-of", "json", path],
        capture_output=True, text=True,
    )
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return "not a readable media file"
    if not d.get("streams"):
        return "no video stream found"
    dur = float(d.get("format", {}).get("duration", 0) or 0)
    if dur <= 0:
        return "zero duration"
    if dur > 600:
        return f"duration {dur:.0f}s exceeds 600s limit", None
    return None, dur


def _try_venv_reexec():
    if sys.platform != "linux":
        return
    try:
        import cv2
        import numpy

        return
    except Exception:
        pass
    vpy = os.path.join(BASE, ".venv", "bin", "python")
    if os.path.isfile(vpy) and os.path.abspath(sys.executable) != os.path.abspath(vpy):
        try:
            import subprocess as sp

            r = sp.run([vpy, "-c", "import cv2, numpy"], capture_output=True)
            if r.returncode == 0:
                os.execv(vpy, [vpy] + sys.argv)
        except Exception:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", help="path to .mov")
    ap.add_argument("--video-id", default=None)
    ap.add_argument("--backend", choices=["auto", "dnn", "classic"], default="auto")
    ap.add_argument("--include-unverified", action="store_true")
    ap.add_argument("--no-frames", action="store_true")
    ap.add_argument("--evidence-dir", default=os.path.join(BASE, "run_evidence"))
    args = ap.parse_args()
    _try_venv_reexec()
    err, dur = validate_mov(args.video)
    if err:
        json.dump({"error": err}, sys.stdout, ensure_ascii=False)
        sys.exit(2)
    video_id = args.video_id or os.path.splitext(os.path.basename(args.video))[0]
    result = analyze(
        args.video,
        video_id,
        evidence_dir=None if args.no_frames else args.evidence_dir,
        include_unverified=args.include_unverified,
        want_frames=not args.no_frames,
        backend=args.backend,
        dur=dur or 0.0,
    )
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
