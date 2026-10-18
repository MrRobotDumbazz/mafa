import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .auth import require_api_key
from .config import get_settings
from .errors import ApiError
from .extract import probe_duration_sec
from .jobs import JobStore
from .mlpipe.external import ExternalPipeline
from .multipart import parse_multipart

settings = get_settings()
store = JobStore(
    ExternalPipeline(settings.pipeline_cmd),
    timeout_sec=settings.job_timeout_sec,
    catalog_path=settings.violation_catalog,
)

STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
    ".json": "application/json",
    ".map": "application/json",
    ".txt": "text/plain; charset=utf-8",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "forte-vision/0.2"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def _send_json(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "X-API-Key, Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    @staticmethod
    def _normalize(path: str) -> tuple[str, bool]:
        if path.startswith("/web/api/"):
            return "/api/" + path[len("/web/api/"):], True
        return path, False

    def _maybe_key(self, web: bool) -> None:
        if web and settings.web_keyless:
            return
        require_api_key(self.headers.get("X-API-Key"))

    def do_GET(self) -> None:
        try:
            path, web = self._normalize(self.path)
            if path == "/health":
                self._send_json(200, {"status": "ok"})
                return
            if path.startswith("/api/v1/jobs/"):
                self._maybe_key(web)
                job_id = path[len("/api/v1/jobs/"):].split("?")[0]
                if not job_id:
                    raise ApiError(404, "Unknown job_id")
                job = store.get(job_id)
                if job is None:
                    raise ApiError(404, "Unknown job_id")
                self._send_json(200, store.result(job))
                return
            if settings.static_dir is not None and self._serve_static(path):
                return
            raise ApiError(404, "not found")
        except ApiError as e:
            self._send_json(e.status, {"detail": e.detail})

    def do_POST(self) -> None:
        try:
            path, web = self._normalize(self.path)
            if path != "/api/v1/analyze":
                raise ApiError(404, "not found")
            self._maybe_key(web)
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                raise ApiError(400, "empty body")
            if length > settings.max_upload_bytes:
                raise ApiError(413, "File too large")
            body = self.rfile.read(length)
            filename, content = parse_multipart(body, self.headers.get("Content-Type", ""))
            if not filename.lower().endswith(".mov"):
                raise ApiError(400, "Only .mov files are accepted")
            dest = settings.storage_dir / f"{uuid.uuid4().hex}_{Path(filename).name}"
            dest.write_bytes(content)
            try:
                probe_duration_sec(dest)
            except Exception:
                dest.unlink(missing_ok=True)
                raise ApiError(400, "File is not a readable video")
            job = store.create(dest)
            self._send_json(200, {"job_id": job.job_id, "status": "processing"})
        except ApiError as e:
            self._send_json(e.status, {"detail": e.detail})

    def _serve_static(self, path: str) -> bool:
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        base = settings.static_dir.resolve()
        target = (base / rel).resolve()
        if not str(target).startswith(str(base)):
            return False
        if not target.is_file():
            target = base / "index.html"
            if not target.is_file():
                return False
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", STATIC_TYPES.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store" if target.suffix == ".html" else "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)
        return True


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"forte-vision API listening on {host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    run(port=int(os.getenv("FORTE_PORT", "8000")))
