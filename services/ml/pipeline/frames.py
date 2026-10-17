import subprocess


class FrameReader:
    def __init__(self, path, fps=5.0, width=96, height=54):
        self.path = path
        self.fps = fps
        self.w = width
        self.h = height

    def __iter__(self):
        vf = f"fps={self.fps},scale={self.w}:{self.h},format=gray"
        cmd = [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-i", self.path,
            "-vf", vf, "-f", "image2pipe", "-vcodec", "pgm", "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        dt = 1.0 / self.fps
        t = 0.0
        try:
            for frame in self._frames(proc.stdout):
                yield t, frame
                t += dt
        finally:
            proc.stdout.close()
            proc.wait()

class RawReader:
    def __init__(self, path, fps=5.0, width=270, height=480):
        self.path = path
        self.fps = fps
        self.w = width
        self.h = height

    def __iter__(self):
        import numpy as np

        vf = f"fps={self.fps},scale={self.w}:{self.h}"
        cmd = [
            "ffmpeg", "-nostdin", "-loglevel", "error", "-i", self.path,
            "-vf", vf, "-pix_fmt", "bgr24", "-f", "rawvideo", "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        n = self.w * self.h * 3
        dt = 1.0 / self.fps
        t = 0.0
        try:
            while True:
                buf = proc.stdout.read(n)
                if not buf or len(buf) < n:
                    return
                yield t, np.frombuffer(buf, dtype=np.uint8).reshape(self.h, self.w, 3)
                t += dt
        finally:
            proc.stdout.close()
            proc.wait()

    def _frames(self, f):
        n = self.w * self.h
        while True:
            magic = f.readline()
            if not magic:
                return
            if magic.strip() != b"P5":
                return
            try:
                w, h = map(int, f.readline().split())
                f.readline()
            except ValueError:
                return
            data = f.read(w * h)
            if len(data) < w * h:
                return
            yield w, h, data
