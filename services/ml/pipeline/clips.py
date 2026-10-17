import detector as D


def person_windows(feat, zones):
    others = [tr for tr in feat["confirmed"] if tr.cls == D.PERSON and tr is not zones.cashier and (tr.last_t - tr.first_t) >= 1.0]
    ivs = sorted((tr.first_t, tr.last_t) for tr in others)
    merged = []
    for a, b in ivs:
        if merged and a - merged[-1][1] <= 2.0:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return merged


def solo_windows(feat, zones, clients):
    span = feat["person_boxes_by_t"]
    if not span:
        return []
    solo = []
    s = None
    for t, boxes in span:
        others = [tid for tid, _ in boxes if zones.cashier is None or tid != zones.cashier.tid]
        alone = len(boxes) >= 1 and not others
        if alone and s is None:
            s = t
        elif not alone and s is not None:
            if t - s >= 4.0 and not _covered(s, t, clients):
                solo.append((s, t))
            s = None
    if s is not None and span and span[-1][0] - s >= 4.0 and not _covered(s, span[-1][0], clients):
        solo.append((s, span[-1][0]))
    return solo


def _covered(a, b, windows):
    for wa, wb in windows:
        if min(b, wb) - max(a, wa) >= 3.0:
            return True
    return False


def bag_windows(feat):
    bags = [tr for tr in feat["confirmed"] if tr.cls in D.BAGS and (tr.last_t - tr.first_t) >= 2.0]
    return [(tr.first_t, tr.last_t, tr.tid) for tr in bags]


def item_segments(feat, zones, min_dur=5.0):
    if zones.staff_rect is None:
        return []
    x0, y0, x1, y1 = zones.staff_rect
    segs = []
    for tr in feat["confirmed"]:
        if tr.cls == D.PERSON or tr.cls in D.BAGS:
            continue
        inside_frac = 0
        total = 0
        for t, cx, cy in tr.pts:
            total += 1
            if x0 <= cx <= x1 and y0 <= cy <= y1:
                inside_frac += 1
        if total and inside_frac / total >= 0.5 and (tr.last_t - tr.first_t) >= min_dur:
            segs.append((tr.first_t, tr.last_t, tr.cls))
    return segs


def interactions(feat, max_dist=60.0, min_dur=2.0):
    pts = {}
    for tr in feat["confirmed"]:
        if tr.cls != D.PERSON:
            continue
        for t, cx, cy in tr.pts:
            pts.setdefault(round(t, 1), []).append((tr.tid, cx, cy))
    ts = sorted(pts)
    segs = []
    s = None
    last_hi = None
    for t in ts:
        lst = pts[t]
        close = False
        for i in range(len(lst)):
            for j in range(i + 1, len(lst)):
                d = ((lst[i][1] - lst[j][1]) ** 2 + (lst[i][2] - lst[j][2]) ** 2) ** 0.5
                if d <= max_dist:
                    close = True
                    break
            if close:
                break
        if close:
            if s is None:
                s = t
            last_hi = t
        elif s is not None and t - last_hi > 1.5:
            if last_hi - s >= min_dur:
                segs.append((s, last_hi))
            s = None
    if s is not None and last_hi is not None and last_hi - s >= min_dur:
        segs.append((s, last_hi))
    return segs


def classify(feat, zones):
    clients = person_windows(feat, zones)
    solos = solo_windows(feat, zones, clients)
    bags = bag_windows(feat)
    items = item_segments(feat, zones)
    inter = interactions(feat)
    clips = []
    for a, b in clients:
        clips.append({"category": "service", "t0": a, "t1": b})
    for a, b in solos:
        clips.append({"category": "solo_count", "t0": a, "t1": b})
    for a, b, tid in bags:
        clips.append({"category": "bag_incass", "t0": a, "t1": b})
    for a, b, cls in items:
        clips.append({"category": "item_in_staff", "t0": a, "t1": b, "coco_cls": cls})
    clips.sort(key=lambda c: c["t0"])
    return clips, {"clients": clients, "solos": solos, "bags": bags, "items": items, "inter": inter}


def op_prims(clips):
    out = []
    for c in clips:
        if c["category"] == "service":
            out.append(("receive", c["t0"], c["t1"]))
        elif c["category"] == "solo_count":
            out.append(("count", c["t0"], c["t1"]))
        elif c["category"] == "bag_incass":
            out.append(("incass", c["t0"], c["t1"]))
    return out
