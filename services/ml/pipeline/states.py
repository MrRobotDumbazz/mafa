from array import array


class Brightness:
    def __init__(self):
        self.samples = []

    def add(self, t, frame):
        n = len(frame)
        s = 0
        c = 0
        for i in range(0, n, 4):
            s += frame[i]
            c += 1
        self.samples.append((t, s / max(1, c)))

    def segments(self, on=26.0, off=34.0, min_dur=5.0):
        segs = []
        start = None
        for t, b in self.samples:
            if start is None and b < on:
                start = t
            elif start is not None and b > off:
                if t - start >= min_dur:
                    segs.append((start, t))
                start = None
        if start is not None and self.samples and self.samples[-1][0] - start >= min_dur:
            segs.append((start, self.samples[-1][0]))
        return segs


class StaticObjects:
    def __init__(self, w, h, cols=9, rows=15):
        self.w, self.h = w, h
        self.cols, self.rows = cols, rows
        self.cw = w / cols
        self.ch = h / rows
        self.n = w * h
        self.bg = array("f", bytes(4 * self.n))
        first = True
        self._first = first
        self.pers = array("f", bytes(4 * cols * rows))
        self.timeline = []
        self.warm = 0

    def _person_mask(self, boxes):
        m = bytearray(self.n)
        for x0, y0, x1, y1 in boxes:
            for y in range(max(0, int(y0) - 2), min(self.h, int(y1) + 3)):
                base = y * self.w
                for x in range(max(0, int(x0) - 2), min(self.w, int(x1) + 3)):
                    m[base + x] = 1
        return m

    def update(self, t, dt, frame, person_boxes):
        if self._first:
            for i in range(self.n):
                self.bg[i] = frame[i]
            self._first = False
            return
        pm = self._person_mask(person_boxes)
        alpha = 0.03
        bg = self.bg
        for i in range(self.n):
            if not pm[i]:
                bg[i] += (frame[i] - bg[i]) * alpha
        cells = []
        for cy in range(self.rows):
            for cx in range(self.cols):
                x0 = int(cx * self.cw)
                x1 = int(min(self.w, (cx + 1) * self.cw))
                y0 = int(cy * self.ch)
                y1 = int(min(self.h, (cy + 1) * self.ch))
                tot = hit = 0
                for y in range(y0, y1):
                    base = y * self.w
                    for x in range(x0, x1):
                        tot += 1
                        d = frame[base + x] - bg[base + x]
                        if (d > 16 or d < -16) and not pm[base + x]:
                            hit += 1
                ci = cy * self.cols + cx
                if tot and hit / tot > 0.10:
                    self.pers[ci] += dt
                else:
                    self.pers[ci] *= 0.85
        self.warm += dt
        if self.warm > 5.0:
            act = [ci for ci in range(self.cols * self.rows) if self.pers[ci] > 2.5]
            if act:
                self.timeline.append((t, act))

    def cell_rect(self, ci):
        cx, cy = ci % self.cols, ci // self.cols
        return (cx * self.cw / self.w, cy * self.ch / self.h, (cx + 1) * self.cw / self.w, (cy + 1) * self.ch / self.h)

    def segments(self, norm_rect=None, gap=5.0, min_dur=2.0):
        if norm_rect:
            x0, y0, x1, y1 = norm_rect
            def inside(ci):
                r = self.cell_rect(ci)
                mx = max(r[0], x0) <= min(r[2], x1)
                my = max(r[1], y0) <= min(r[3], y1)
                return mx and my
        else:
            def inside(ci):
                return True
        events = []
        for t, act in self.timeline:
            for ci in act:
                if inside(ci):
                    events.append((t, ci))
        by_cell = {}
        for t, ci in events:
            by_cell.setdefault(ci, []).append(t)
        segs = []
        for ci, ts in by_cell.items():
            ts.sort()
            s = ts[0]
            prev = ts[0]
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
