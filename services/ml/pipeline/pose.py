import os

WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights")

COCO17 = [
    "nose", "l_eye", "r_eye", "l_ear", "r_ear", "l_shoulder", "r_shoulder",
    "l_elbow", "r_elbow", "l_wrist", "r_wrist", "l_hip", "r_hip",
    "l_knee", "r_knee", "l_ankle", "r_ankle",
]


class RtmposeOrt:
    def __init__(self, onnx_path):
        import numpy as np
        import onnxruntime as ort

        self.np = np
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.iname = self.sess.get_inputs()[0].name
        shape = self.sess.get_inputs()[0].shape
        self.ih = int(shape[2]) if isinstance(shape[2], int) and shape[2] > 0 else 256
        self.iw = int(shape[3]) if isinstance(shape[3], int) and shape[3] > 0 else 192
        import cv2

        self.cv2 = cv2

    def keypoints(self, bgr, box):
        np = self.np
        cv2 = self.cv2
        x0, y0, x1, y1 = [int(round(v)) for v in box]
        x0 = max(0, x0)
        y0 = max(0, y0)
        crop = bgr[y0 : y1, x0 : x1]
        if crop.size == 0:
            return None
        ch, cw = crop.shape[:2]
        canvas = cv2.resize(crop, (self.iw, self.ih))
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        m = np.array([0.485, 0.456, 0.406], np.float32)
        s = np.array([0.229, 0.224, 0.225], np.float32)
        blob = ((rgb - m) / s).transpose(2, 0, 1)[None]
        outs = self.sess.run(None, {self.iname: blob.astype(np.float32)})
        pts = {}
        if len(outs) == 2 and outs[0].ndim == 3 and outs[0].shape[1] == 17:
            sx = outs[0][0]
            sy = outs[1][0]
            wx, wy = sx.shape[1], sy.shape[1]
            for j in range(17):
                fx = int(sx[j].argmax())
                fy = int(sy[j].argmax())
                pts[COCO17[j]] = (x0 + fx / (wx - 1) * cw, y0 + fy / (wy - 1) * ch)
        return pts


def make_pose():
    p = os.path.join(WEIGHTS_DIR, "rtmpose-s.onnx")
    if os.path.exists(p) and os.path.getsize(p) > 1_000_000:
        try:
            return RtmposeOrt(p)
        except Exception:
            return None
    p2 = os.path.join(WEIGHTS_DIR, "movenet-lightning-fp16.onnx")
    if os.path.exists(p2) and os.path.getsize(p2) > 1_000_000:
        try:
            return RtmposeOrt(p2)
        except Exception:
            return None
    return None
