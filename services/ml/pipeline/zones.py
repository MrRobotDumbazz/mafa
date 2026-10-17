def percentile(vals, q):
    if not vals:
        return 0.0
    vals = sorted(vals)
    k = min(len(vals) - 1, max(0, int(round(q * (len(vals) - 1)))))
    return float(vals[k])


class Zones:
    def __init__(self, tracks):
        self.tracks = tracks
        self.cashier = None
        self.staff_rect = None
        self.client_windows = []
        self._build()

    def _spread(self, tr):
        xs = [p[1] for p in tr.pts]
        ys = [p[2] for p in tr.pts]
        mx = (percentile(xs, 0.95) - percentile(xs, 0.05)) / 2
        my = (percentile(ys, 0.95) - percentile(ys, 0.05)) / 2
        return max(mx, my)

    def _build(self):
        cands = sorted(self.tracks, key=lambda tr: (-(tr.last_t - tr.first_t), self._spread(tr)))
        self.cashier = cands[0] if cands else None
        if self.cashier is not None:
            xs = [p[1] for p in self.cashier.pts]
            ys = [p[2] for p in self.cashier.pts]
            x0 = max(0.0, percentile(xs, 0.15) - 4)
            x1 = percentile(xs, 0.85) + 4
            y0 = max(0.0, percentile(ys, 0.15) - 4)
            y1 = percentile(ys, 0.85) + 4
            self.staff_rect = (x0, y0, x1, y1)
            cx0 = max(0.0, percentile(xs, 0.25))
            cx1 = percentile(xs, 0.75)
            cy0 = max(0.0, percentile(ys, 0.25))
            cy1 = percentile(ys, 0.75)
            self.core_rect = (cx0, cy0, cx1, cy1)
        else:
            self.core_rect = None
        others = [tr for tr in self.tracks if tr is not self.cashier and (tr.last_t - tr.first_t) >= 1.0]
        ivs = sorted((tr.first_t, tr.last_t) for tr in others)
        for a, b in ivs:
            if self.client_windows and a - self.client_windows[-1][1] <= 2.0:
                self.client_windows[-1][1] = max(self.client_windows[-1][1], b)
            else:
                self.client_windows.append([a, b])

    def cashier_out_segments(self, min_dur=2.0):
        if self.cashier is None or self.staff_rect is None:
            return []
        x0, y0, x1, y1 = self.staff_rect
        segs = []
        s = None
        for t, cx, cy in self.cashier.pts:
            out = not (x0 <= cx <= x1 and y0 <= cy <= y1)
            if out and s is None:
                s = t
            elif not out and s is not None:
                if t - s >= min_dur:
                    segs.append((s, t))
                s = None
        if s is not None and self.cashier.pts and self.cashier.pts[-1][0] - s >= min_dur:
            segs.append((s, self.cashier.pts[-1][0]))
        return segs

    def stable_third_segments(self, min_dur=4.0, min_dist=8.0):
        if self.cashier is None:
            return []
        cpts = self.cashier.pts
        segs = []
        for tr in self.tracks:
            if tr is self.cashier or tr.first_t < 3.0 or (tr.last_t - tr.first_t) < min_dur:
                continue
            if tr.last_t < cpts[0][0] or tr.first_t > cpts[-1][0]:
                continue
            near = far = 0
            for t, cx, cy in tr.pts:
                dmin = min((cx - px) ** 2 + (cy - py) ** 2 for pt, px, py in cpts if abs(pt - t) <= 0.6)
                if dmin ** 0.5 >= min_dist:
                    far += 1
                else:
                    near += 1
            if far >= near:
                segs.append((tr.first_t, tr.last_t))
        segs.sort()
        merged = []
        for s, e in segs:
            if merged and s - merged[-1][1] <= 1.0:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return [tuple(m) for m in merged]

    def third_person_segments(self, min_dur=3.0, staff_stay=1.5):
        if self.cashier is None:
            return []
        others = [tr for tr in self.tracks if tr is not self.cashier]
        if not others:
            return []
        first_client = min(tr.first_t for tr in others)
        latecomers = [tr for tr in others if tr.first_t > first_client + 1.0 and (tr.last_t - tr.first_t) >= min_dur]
        segs = []
        cx0, cy0, cx1, cy1 = self.cashier.cx, self.cashier.cy, 0, 0
        xs = [p[1] for p in self.cashier.pts]
        ys = [p[2] for p in self.cashier.pts]
        sx0, sx1 = min(xs) - 10, max(xs) + 10
        sy0, sy1 = min(ys) - 10, max(ys) + 10
        for tr in latecomers:
            stay = 0.0
            for t, x, y in tr.pts:
                if sx0 <= x <= sx1 and sy0 <= y <= sy1:
                    stay += 1.0
            if stay >= staff_stay:
                segs.append((tr.first_t, tr.last_t))
        segs.sort()
        merged = []
        for s, e in segs:
            if merged and s - merged[-1][1] <= 1.0:
                merged[-1][1] = max(merged[-1][1], e)
            else:
                merged.append([s, e])
        return [tuple(m) for m in merged]

    def concurrent_third_segments(self, min_count=3, min_dur=2.0, tol=0.5):
        times = sorted({round(p[0], 1) for tr in self.tracks for p in tr.pts})
        if not times:
            return []
        by_track = [{round(p[0], 1) for p in tr.pts} for tr in self.tracks]
        segs = []
        s = None
        last_hi = None
        for t in times:
            cnt = sum(1 for pts in by_track if any(abs(t - pt) <= tol for pt in pts))
            if cnt >= min_count:
                if s is None:
                    s = t
                last_hi = t
            elif s is not None and t - last_hi > 1.0:
                if last_hi - s >= min_dur:
                    segs.append((s, last_hi))
                s = None
        if s is not None and last_hi is not None and last_hi - s >= min_dur:
            segs.append((s, last_hi))
        return segs

    def third_in_staff_segments(self, min_dur=4.0):
        if self.core_rect is None or self.cashier is None:
            return []
        x0, y0, x1, y1 = self.core_rect
        c_span = (self.cashier.first_t, self.cashier.last_t)
        segs = []
        for tr in self.tracks:
            if tr is self.cashier:
                continue
            s = None
            for t, cx, cy in tr.pts:
                inside = x0 <= cx <= x1 and y0 <= cy <= y1
                if inside and s is None:
                    s = t
                elif not inside and s is not None:
                    if t - s >= min_dur and not (t < c_span[0] or s > c_span[1]):
                        segs.append((tr.tid, s, t))
                    s = None
            if s is not None and tr.pts and tr.pts[-1][0] - s >= min_dur and not (tr.pts[-1][0] < c_span[0] or s > c_span[1]):
                segs.append((tr.tid, s, tr.pts[-1][0]))
        return segs
