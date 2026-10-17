import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))

import detector as D
from frames import RawReader
from tracker import ByteLite


class StaticFast:
    def __init__(self, w, h, cols=18, rows=30, alpha=0.03, fg_thr=17.0, cell_ratio=0.12, pers_on=1.3):
        import numpy as np

        self.np = np
        self.w, self.h = w, h
        self.cols, self.rows = cols, rows
        self.alpha = alpha
        self.fg_thr = fg_thr
        self.cell_ratio = cell_ratio
        self.pers_on = pers_on
        self.bg = None
        self.pers = np.zeros(cols * rows, dtype=np.float32)
        self.timeline = []
        self.warm = 0.0
        self.cell_mask = np.zeros((rows, cols, h, w), dtype=bool)
        ys = np.arange(h) * rows // h
        xs = np.arange(w) * cols // w
        self.cell_of = ys[:, None] * cols + xs[None, :]

    def update(self, t, dt, gray, boxes):
        np = self.np
        if self.bg is None:
            self.bg = gray.astype(np.float32)
            return
        pm = np.zeros_like(gray, dtype=bool)
        for x0, y0, x1, y1 in boxes:
            pm[max(0, int(y0) - 2):int(y1) + 3, max(0, int(x0) - 2):int(x1) + 3] = True
        upd = ~pm
        self.bg[upd] += (gray[upd] - self.bg[upd]) * self.alpha
        fg = (np.abs(gray - self.bg) > self.fg_thr) & (~pm)
        free = ~pm
        act = []
        for ci in range(self.cols * self.rows):
            cell = self.cell_of == ci
            tot = int((cell & free).sum())
            if tot == 0:
                self.pers[ci] *= 0.88
                continue
            ratio = float((fg & cell).sum()) / tot
            if ratio > self.cell_ratio:
                self.pers[ci] += dt
            else:
                self.pers[ci] *= 0.88
            if self.pers[ci] > self.pers_on:
                act.append(ci)
        self.warm += dt
        if self.warm > 5.0 and act:
            self.timeline.append((t, act))

    def cell_rect(self, ci):
        cx, cy = ci % self.cols, ci // self.cols
        return (cx / self.cols, cy / self.rows, (cx + 1) / self.cols, (cy + 1) / self.rows)

    def segments(self, norm_rect=None, gap=5.0, min_dur=2.0):
        def inside(ci):
            if not norm_rect:
                return True
            r = self.cell_rect(ci)
            return max(r[0], norm_rect[0]) <= min(r[2], norm_rect[2]) and max(r[1], norm_rect[1]) <= min(r[3], norm_rect[3])

        by_cell = {}
        for t, act in self.timeline:
            for ci in act:
                if inside(ci):
                    by_cell.setdefault(ci, []).append(t)
        segs = []
        for ci, ts in by_cell.items():
            ts.sort()
            s = prev = ts[0]
            for t in ts[1:]:
                if t - prev > gap:
                    if prev - s >= min_dur:
                        segs.append((s, prev))
                    s = t
                prev = t
            if prev - s >= min_dur:
                segs.append((s, prev))
        if not segs:
            return []
        segs.sort()
        merged = [list(segs[0])]
        for s, e in segs[1:]:
            if s - merged[-1][1] <= gap:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return [tuple(m) for m in merged]


def extract_features(path, backend="auto", onnx=None, fps=3.0, w=270, h=480):
    import cv2

    det, backend_name = D.make_backend(backend, onnx)
    reader = RawReader(path, fps=fps, width=w, height=h)
    tracker = ByteLite()
    registry = {}
    st = StaticFast(w, h)
    bright = []
    dt = 1.0 / fps
    person_boxes_by_t = []
    for t, frame in reader:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bright.append(float(gray.mean()))
        dets = det.detect(frame) if backend_name.startswith("dnn") else det.detect(gray.tobytes(), w, h)
        tracker.update(dets, t)
        for tr in tracker.tracks:
            if tr.hits >= 2:
                registry[tr.tid] = tr
        persons = [tr for tr in tracker.confirmed() if tr.cls == D.PERSON and tr.missing == 0]
        boxes = [tr.box for tr in persons]
        st.update(t, dt, gray, boxes)
        person_boxes_by_t.append((t, [(tr.tid, tr.box) for tr in persons]))
    return {
        "kind": "v1",
        "backend": backend_name,
        "tracks": list(registry.values()),
        "confirmed": list(registry.values()),
        "stobjs": st,
        "bright": bright,
        "w": w,
        "h": h,
        "fps": fps,
        "person_boxes_by_t": person_boxes_by_t,
    }
