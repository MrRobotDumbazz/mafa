import json
import os
import unicodedata

WEIGHTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "weights")

PROMPTS = ["door", "safe", "vault", "banknote", "stack of banknotes", "key", "identity card", "wallet", "handbag", "bottle", "cup", "cell phone"]

PROMPT_MAP = {
    "door": "DOOR",
    "safe": "SAFE",
    "vault": "SAFE",
    "banknote": "MONEY",
    "stack of banknotes": "MONEY",
    "key": "KEY",
    "identity card": "ID_DOC",
    "wallet": "WALLET",
    "handbag": "BAG",
    "bottle": "ITEM",
    "cup": "ITEM",
    "cell phone": "ITEM",
}


def _bytes_to_unicode():
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(2 ** 8):
        if b not in bs:
            bs.append(b)
            cs.append(2 ** 8 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))


class ClipBpe:
    def __init__(self, vocab_path, merges_path):
        with open(vocab_path, encoding="utf-8") as f:
            self.vocab = json.load(f)
        self.inv = {v: k for k, v in self.vocab.items()}
        self.bpe_ranks = {}
        with open(merges_path, encoding="utf-8") as f:
            for i, line in enumerate(f.read().split("\n")[1 : 49152 - 256 - 2 + 1]):
                parts = tuple(line.split())
                if len(parts) == 2:
                    self.bpe_ranks[parts] = i
        self.byte_enc = _bytes_to_unicode()
        self.pat_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789' ")

    def _bpe(self, token):
        word = tuple(token)
        pairs = set()
        for i in range(len(word) - 1):
            pairs.add((word[i], word[i + 1]))
        if not pairs:
            return token
        while True:
            bigram = min(pairs, key=lambda p: self.bpe_ranks.get(p, float("inf")))
            if bigram not in self.bpe_ranks:
                break
            first, second = bigram
            new_word = []
            i = 0
            while i < len(word):
                j = word.index(first, i) if first in word[i:] else len(word)
                if j < len(word):
                    new_word.extend(word[i:j])
                    i = j
                else:
                    new_word.extend(word[i:])
                    i = len(word)
                if i >= len(word) or word[i] != first:
                    continue
                if i < len(word) - 1 and word[i + 1] == second:
                    new_word.append(first + second)
                    i += 2
                else:
                    new_word.append(first)
                    i += 1
            word = tuple(new_word)
            if len(word) == 1:
                break
            pairs = set()
            for i in range(len(word) - 1):
                pairs.add((word[i], word[i + 1]))
        return " ".join(word)

    def encode(self, text, max_len=16):
        text = unicodedata.normalize("NFC", text.lower())
        tokens = []
        cur = ""
        for ch in text:
            if ch in self.pat_chars:
                cur += ch
            else:
                if cur:
                    tokens.append(cur)
                cur = ""
                if ch.strip():
                    tokens.append(ch)
        if cur:
            tokens.append(cur)
        ids = [self.vocab.get("<|startoftext|>", 49406)]
        for tok in tokens:
            btok = "".join(self.byte_enc[b] for b in tok.encode("utf-8"))
            for piece in self._bpe(btok).split():
                if piece in self.vocab:
                    ids.append(self.vocab[piece])
        ids = ids[: max_len - 1]
        ids.append(self.vocab.get("<|endoftext|>", 49407))
        attn = [1] * len(ids)
        pad = max_len - len(ids)
        ids += [self.vocab.get("<|endoftext|>", 49407)] * pad
        attn += [0] * pad
        return ids, attn


class Owlv2Ort:
    def __init__(self, onnx_path, vocab_path, merges_path, conf=0.25):
        import numpy as np
        import onnxruntime as ort

        self.np = np
        self.sess = ort.InferenceSession(onnx_path, providers=["CPUExecutionProvider"])
        self.inputs = {i.name: i.shape for i in self.sess.get_inputs()}
        self.conf = conf
        self.tok = ClipBpe(vocab_path, merges_path)
        import cv2

        self.cv2 = cv2

    def detect(self, bgr, prompts=PROMPTS):
        np = self.np
        cv2 = self.cv2
        ph = pw = 768
        for out_meta in self.sess.get_outputs():
            if "image_embeds" in out_meta.name and len(out_meta.shape) == 4:
                gh, gw = out_meta.shape[1], out_meta.shape[2]
                if isinstance(gh, int) and gh > 0 and isinstance(gw, int) and gw > 0:
                    ph, pw = gh * 16, gw * 16
        for name, shape in self.inputs.items():
            if "pixel" in name and len(shape) == 4:
                if isinstance(shape[2], int) and shape[2] > 0:
                    ph = shape[2]
                if isinstance(shape[3], int) and shape[3] > 0:
                    pw = shape[3]
        h, w = bgr.shape[:2]
        r = min(ph / h, pw / w)
        nw, nh = int(round(w * r)), int(round(h * r))
        canvas = np.full((ph, pw, 3), 127, np.uint8)
        canvas[:nh, :nw] = cv2.resize(bgr, (nw, nh))
        rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)
        pixel = rgb.astype(np.float32) / 255.0
        pixel = (pixel - np.array([0.48145466, 0.4578275, 0.40821073])) / np.array([0.26862954, 0.26130258, 0.27577711])
        pixel = pixel.transpose(2, 0, 1)[None]
        ids_batch = []
        attn_batch = []
        for pr in prompts:
            ids, attn = self.tok.encode(pr)
            ids_batch.append(ids)
            attn_batch.append(attn)
        feed = {}
        for name in self.inputs:
            if "pixel" in name:
                feed[name] = pixel.astype(np.float32)
            elif "input_ids" in name:
                feed[name] = np.array([ids_batch], dtype=np.int64).reshape(len(prompts), -1)
            elif "attention_mask" in name:
                feed[name] = np.array([attn_batch], dtype=np.int64).reshape(len(prompts), -1)
        outs = self.sess.run(None, feed)
        logits = None
        boxes = None
        for out, meta in zip(outs, self.sess.get_outputs()):
            if "logits" in meta.name:
                logits = out
            elif "box" in meta.name:
                boxes = out
        if logits is None or boxes is None:
            return []
        lg = 1.0 / (1.0 + np.exp(-logits[0]))
        bx = boxes[0]
        out_dets = []
        for j, pr in enumerate(prompts):
            if j >= lg.shape[1]:
                break
            q = int(lg[:, j].argmax())
            score = float(lg[q, j])
            if score < self.conf:
                continue
            cx, cy, bw, bh = bx[q]
            x0, y0 = (cx - bw / 2) * pw / r, (cy - bh / 2) * ph / r
            x1, y1 = (cx + bw / 2) * pw / r, (cy + bh / 2) * ph / r
            out_dets.append(
                {
                    "class": PROMPT_MAP.get(pr, pr),
                    "score": score,
                    "box": (max(0.0, x0), max(0.0, y0), min(w, x1), min(h, y1)),
                    "raw": pr,
                }
            )
        out_dets.sort(key=lambda d: -d["score"])
        return out_dets


def make_owlv2(conf=0.25):
    onnx = os.path.join(WEIGHTS_DIR, "owlv2-base-int8.onnx")
    vocab = os.path.join(WEIGHTS_DIR, "owlv2-vocab.json")
    merges = os.path.join(WEIGHTS_DIR, "owlv2-merges.txt")
    if all(os.path.exists(p) and os.path.getsize(p) > 1000 for p in (onnx, vocab, merges)):
        try:
            return Owlv2Ort(onnx, vocab, merges, conf=conf)
        except Exception:
            return None
    return None
