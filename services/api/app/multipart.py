import re

from .errors import ApiError


def parse_multipart(body: bytes, content_type: str) -> tuple[str, bytes]:
    m = re.search(r'boundary="?([^";]+)"?', content_type)
    if m is None:
        raise ApiError(400, "expected multipart/form-data")
    delim = b"--" + m.group(1).encode()
    for raw in body.split(delim):
        if raw.startswith(b"\r\n"):
            raw = raw[2:]
        if raw.endswith(b"\r\n"):
            raw = raw[:-2]
        if not raw or raw == b"--":
            continue
        if b"\r\n\r\n" not in raw:
            continue
        head, content = raw.split(b"\r\n\r\n", 1)
        disp = b"".join(l for l in head.split(b"\r\n") if b"Content-Disposition" in l)
        fm = re.search(rb'filename="([^"]*)"', disp)
        if fm is None:
            continue
        return fm.group(1).decode("utf-8", "replace"), content
    raise ApiError(400, "file part not found")
