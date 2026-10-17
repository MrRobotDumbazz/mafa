import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "model"))

from frames import FrameReader
from motion import Tracker, diff_mask, dilate, find_blobs
from states import Brightness, StaticObjects
from zones import Zones

FPS = 5.0
SW, SH = 108, 192
TW, TH = 54, 96
MIN_AREA = 8
MAX_AREA = 900
DIST = 25


def _half(frame, w, h):
    out = bytearray((w // 2) * (h // 2))
    i = 0
    for y in range(0, h, 2):
        base = y * w
        for x in range(0, w, 2):
            out[i] = frame[base + x]
            i += 1
    return bytes(out)


def extract_features(path):
    reader = FrameReader(path, fps=FPS, width=SW, height=SH)
    tracker = Tracker(dist=DIST, max_miss=8)
    bright = Brightness()
    stobjs = StaticObjects(SW, SH, cols=18, rows=30)
    dt = 1.0 / FPS
    prev = None
    for t, (w, h, frame) in reader:
        bright.add(t, frame)
        small = _half(frame, w, h)
        if prev is None:
            prev = small
            stobjs.update(t, dt, frame, [])
            continue
        mask = dilate(diff_mask(prev, small, TW, TH, thr=12), TW, TH)
        prev = small
        blobs = find_blobs(mask, TW, TH, MIN_AREA, MAX_AREA)
        tracker.update(blobs, t)
        boxes = []
        for b in blobs:
            boxes.append((b.x0 * 2, b.y0 * 2, b.x1 * 2, b.y1 * 2))
        stobjs.update(t, dt, frame, boxes)
    return {
        "tracks": tracker.tracks,
        "bright": bright,
        "stobjs": stobjs,
        "w": TW,
        "h": TH,
    }


def build_zones(feat):
    return Zones(feat["tracks"])


def staff_norm_rect(feat, zones):
    if zones.staff_rect is None:
        return None
    x0, y0, x1, y1 = zones.staff_rect
    return (x0 / feat["w"], y0 / feat["h"], x1 / feat["w"], y1 / feat["h"])
