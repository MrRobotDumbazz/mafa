def _iou(a, b):
    ix = max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0))
    iy = max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0))
    inter = ix * iy
    u = a.area + b.area - inter
    return inter / u if u > 0 else 0.0


class VTrack:
    __slots__ = ("tid", "cls", "box", "t0", "t1", "missing", "hits", "vx", "vy", "pts")

    def __init__(self, tid, det, t):
        self.tid = tid
        self.cls = det.cls
        self.box = (det.x0, det.y0, det.x1, det.y1)
        self.t0 = t
        self.t1 = t
        self.missing = 0
        self.hits = 1
        self.vx = 0.0
        self.vy = 0.0
        self.pts = [(t, det.cx, det.cy)]

    @property
    def cx(self):
        return (self.box[0] + self.box[2]) / 2.0

    @property
    def cy(self):
        return (self.box[1] + self.box[3]) / 2.0

    @property
    def first_t(self):
        return self.t0

    @property
    def last_t(self):
        return self.t1

    def update(self, det, t):
        nx, ny = det.cx, det.cy
        self.vx = nx - self.cx
        self.vy = ny - self.cy
        self.box = (det.x0, det.y0, det.x1, det.y1)
        self.t1 = t
        self.missing = 0
        self.hits += 1
        self.pts.append((t, nx, ny))


class ByteLite:
    def __init__(self, iou_thr=0.25, dist_thr=55.0, max_missing=6, min_hits=2):
        self.iou_thr = iou_thr
        self.dist_thr = dist_thr
        self.max_missing = max_missing
        self.min_hits = min_hits
        self.tracks = []
        self._next = 1

    def _pred_box(self, tr):
        x0, y0, x1, y1 = tr.box
        return (x0 + tr.vx, y0 + tr.vy, x1 + tr.vx, y1 + tr.vy)

    def update(self, dets, t):
        from detector import Detection

        preds = []
        for tr in self.tracks:
            px0, py0, px1, py1 = self._pred_box(tr)
            preds.append((tr, Detection(px0, py0, px1, py1, 1.0, tr.cls)))
        used_tr = set()
        used_d = set()
        for ti, (tr, pb) in enumerate(preds):
            best, bi, bs = None, None, 0.0
            for di, d in enumerate(dets):
                if di in used_d or d.cls != tr.cls:
                    continue
                s = _iou(pb, d)
                if s > bs:
                    best, bi, bs = d, di, s
            if best is not None and bs >= self.iou_thr:
                tr.update(best, t)
                used_tr.add(ti)
                used_d.add(bi)
        for ti, (tr, pb) in enumerate(preds):
            if ti in used_tr:
                continue
            best, bi, bd = None, None, 1e9
            for di, d in enumerate(dets):
                if di in used_d or d.cls != tr.cls:
                    continue
                dd = ((pb.cx - d.cx) ** 2 + (pb.cy - d.cy) ** 2) ** 0.5
                if dd < bd:
                    best, bi, bd = d, di, dd
            if best is not None and bd <= self.dist_thr:
                tr.update(best, t)
                used_tr.add(ti)
                used_d.add(bi)
        for ti, tr in enumerate(self.tracks):
            if ti not in used_tr:
                tr.missing += 1
        for di, d in enumerate(dets):
            if di not in used_d:
                self.tracks.append(VTrack(self._next, d, t))
                self._next += 1
        alive = []
        for tr in self.tracks:
            if tr.missing <= self.max_missing:
                alive.append(tr)
        self.tracks = alive

    def confirmed(self):
        return [tr for tr in self.tracks if tr.hits >= self.min_hits]
