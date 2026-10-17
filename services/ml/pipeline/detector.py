import os

COCO_INTEREST = {
    0: "person",
    24: "backpack",
    26: "handbag",
    28: "suitcase",
    39: "bottle",
    41: "cup",
    63: "laptop",
    64: "keyboard",
    66: "mouse",
    73: "cell phone",
    75: "clock",
    84: "book",
}
PERSON = 0
BAGS = {24, 26, 28}
PERSONAL = {39, 41, 73, 84, 66, 75}
EQUIPMENT = {63, 64}

WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights")


class Detection:
    __slots__ = ("x0", "y0", "x1", "y1", "score", "cls")

    def __init__(self, x0, y0, x1, y1, score, cls):
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.score = score
        self.cls = cls

    @property
    def cx(self):
        return (self.x0 + self.x1) / 2.0

    @property
    def cy(self):
        return (self.y0 + self.y1) / 2.0

    @property
    def area(self):
        return max(0.0, self.x1 - self.x0) * max(0.0, self.y1 - self.y0)


def _nms(dets, iou_thr=0.45):
    dets = sorted(dets, key=lambda d: -d.score)
    keep = []
    for d in dets:
        ok = True
        for k in keep:
            if k.cls != d.cls:
                continue
            ix = max(0.0, min(d.x1, k.x1) - max(d.x0, k.x0))
            iy = max(0.0, min(d.y1, k.y1) - max(d.y0, k.y0))
            inter = ix * iy
            u = d.area + k.area - inter
            if u > 0 and inter / u > iou_thr:
                ok = False
                break
        if ok:
            keep.append(d)
    return keep


class YoloV5Ort:
    def __init__(self, onnx_path, conf=0.35, person_min_area=60.0):
        import numpy as np
        import onnxruntime as ort

        self.np = np
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.iname = self.sess.get_inputs()[0].name
        self.size = int(self.sess.get_inputs()[0].shape[-1]) or 640
        self.dtype = np.float16 if "float16" in str(self.sess.get_inputs()[0].type) else np.float32
        self.conf = conf
        self.person_min_area = person_min_area

    def detect(self, bgr):
        import cv2

        np = self.np
        h, w = bgr.shape[:2]
        r = min(self.size / h, self.size / w)
        nw, nh = int(round(w * r)), int(round(h * r))
        canvas = np.full((self.size, self.size, 3), 114, dtype=np.uint8)
        canvas[:nh, :nw] = cv2.resize(bgr, (nw, nh), interpolation=cv2.INTER_LINEAR)
        blob = canvas[:, :, ::-1].astype(self.dtype).transpose(2, 0, 1)[None] / 255.0
        out = self.sess.run(None, {self.iname: blob})[0][0].astype(np.float32)
        conf = out[:, 4] * out[:, 5:].max(1)
        cls_ids = out[:, 5:].argmax(1)
        mask = conf > self.conf
        dets = []
        for i in np.nonzero(mask)[0]:
            cx, cy, bw, bh = out[i, :4]
            x0, y0 = (cx - bw / 2) / r, (cy - bh / 2) / r
            x1, y1 = (cx + bw / 2) / r, (cy + bh / 2) / r
            c = int(cls_ids[i])
            d = Detection(float(x0), float(y0), float(x1), float(y1), float(conf[i]), c)
            if c == PERSON and d.area < self.person_min_area:
                continue
            dets.append(d)
        return _nms(dets[:1000])


class ClassicBlobs:
    def __init__(self):
        from pipeline.motion import diff_mask, dilate, find_blobs

        self._diff, self._dil, self._cc = diff_mask, dilate, find_blobs
        self.prev = None

    def detect(self, gray_small, w, h):
        if self.prev is None:
            self.prev = gray_small
            return []
        m = self._dil(self._diff(self.prev, gray_small, w, h, thr=12), w, h)
        self.prev = gray_small
        out = []
        for b in self._cc(m, w, h, 8, 900):
            if b.area >= 30:
                out.append(Detection(b.x0, b.y0, b.x1, b.y1, 0.5, PERSON))
        return out


def pick_onnx(prefer="v5"):
    order = ["yolov5n_v7.0.onnx", "yolov5n.onnx", "yolov5s.onnx"]
    for name in order:
        p = os.path.join(WEIGHTS_DIR, name)
        if os.path.exists(p) and os.path.getsize(p) > 1_000_000:
            return p
    return None


def make_backend(backend="auto", onnx=None):
    if backend in ("auto", "dnn"):
        try:
            import onnxruntime
            import cv2
            import numpy

            p = onnx or pick_onnx()
            if p:
                return YoloV5Ort(p), "dnn:" + os.path.basename(p)
        except Exception:
            pass
    return ClassicBlobs(), "classic-blobs"
