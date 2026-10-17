class Blob:
    __slots__ = ("x0", "y0", "x1", "y1", "area", "cx", "cy")

    def __init__(self, x0, y0, x1, y1, area):
        self.x0, self.y0, self.x1, self.y1, self.area = x0, y0, x1, y1, area
        self.cx = (x0 + x1) / 2.0
        self.cy = (y0 + y1) / 2.0


def dilate(mask, w, h):
    out = bytearray(w * h)
    for y in range(h):
        base = y * w
        up = (y - 1) * w if y > 0 else base
        dn = (y + 1) * w if y < h - 1 else base
        for x in range(w):
            if (
                mask[base + x] or mask[up + x] or mask[dn + x]
                or (x > 0 and (mask[base + x - 1] or mask[up + x - 1] or mask[dn + x - 1]))
                or (x < w - 1 and (mask[base + x + 1] or mask[up + x + 1] or mask[dn + x + 1]))
            ):
                out[base + x] = 1
    return out


def diff_mask(prev, cur, w, h, thr=14):
    mask = bytearray(w * h)
    for i in range(w * h):
        d = cur[i] - prev[i]
        if d >= thr or d <= -thr:
            mask[i] = 1
    return mask


def find_blobs(mask, w, h, min_area=6, max_area=2500):
    blobs = []
    stack = []
    idx = 0
    n = w * h
    while idx < n:
        if mask[idx]:
            x0 = y0 = 10 ** 9
            x1 = y1 = -1
            area = 0
            stack.append(idx)
            mask[idx] = 0
            while stack:
                p = stack.pop()
                py, px = divmod(p, w)
                if px < x0: x0 = px
                if px > x1: x1 = px
                if py < y0: y0 = py
                if py > y1: y1 = py
                area += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        qy, qx = py + dy, px + dx
                        if 0 <= qy < h and 0 <= qx < w:
                            q = qy * w + qx
                            if mask[q]:
                                mask[q] = 0
                                stack.append(q)
            if min_area <= area <= max_area:
                blobs.append(Blob(x0, y0, x1, y1, area))
        idx += 1
    return blobs


class Track:
    __slots__ = ("tid", "cx", "cy", "miss", "first_t", "last_t", "pts", "live")

    def __init__(self, tid, blob, t):
        self.tid = tid
        self.cx, self.cy = blob.cx, blob.cy
        self.miss = 0
        self.first_t = t
        self.last_t = t
        self.pts = [(t, blob.cx, blob.cy)]
        self.live = True


class Tracker:
    def __init__(self, dist=22, max_miss=8):
        self.dist = dist
        self.max_miss = max_miss
        self.tracks = []
        self._next = 1

    def update(self, blobs, t):
        for tr in self.tracks:
            tr.live = False
        free = list(range(len(blobs)))
        assigned = set()
        for tr in self.tracks:
            best, bd = None, 1e9
            for j in free:
                if j in assigned:
                    continue
                d = ((tr.cx - blobs[j].cx) ** 2 + (tr.cy - blobs[j].cy) ** 2) ** 0.5
                if d < bd:
                    best, bd = j, d
            if best is not None and bd <= self.dist:
                assigned.add(best)
                tr.cx, tr.cy = blobs[best].cx, blobs[best].cy
                tr.miss = 0
                tr.last_t = t
                tr.pts.append((t, tr.cx, tr.cy))
                tr.live = True
        for j, b in enumerate(blobs):
            if j not in assigned:
                self.tracks.append(Track(self._next, b, t))
                self._next += 1
        for tr in self.tracks:
            if not tr.live:
                tr.miss += 1
        alive = []
        for tr in self.tracks:
            if tr.miss <= self.max_miss:
                alive.append(tr)
        self.tracks = alive

    def active(self):
        return [tr for tr in self.tracks if tr.live or tr.miss == 0]
