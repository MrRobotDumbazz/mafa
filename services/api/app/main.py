import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .auth import require_api_key
from .config import get_settings
from .errors import ApiError
from .jobs import JobStore
from .mlpipe.external import ExternalPipeline
from .mlpipe.mock import MockPipeline
from .multipart import parse_multipart

settings = get_settings()


def _build_pipeline():
    if settings.pipeline_cmd:
        return ExternalPipeline(settings.pipeline_cmd)
    return MockPipeline()


store = JobStore(_build_pipeline(), timeout_sec=settings.job_timeout_sec)


class Handler(BaseHTTPRequestHandler):
    server_version = "forte-vision/0.1"
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

    def do_GET(self) -> None:
        try:
            if self.path == "/health":
                self._send_json(200, {"status": "ok"})
                return
            if self.path.startswith("/api/v1/jobs/"):
                require_api_key(self.headers.get("X-API-Key"))
                job_id = self.path[len("/api/v1/jobs/"):].split("?")[0]
                if not job_id:
                    raise ApiError(404, "Unknown job_id")
                job = store.get(job_id)
                if job is None:
                    raise ApiError(404, "Unknown job_id")
                self._send_json(200, store.result(job))
                return
            raise ApiError(404, "not found")
        except ApiError as e:
            self._send_json(e.status, {"detail": e.detail})

    def do_POST(self) -> None:
        try:
            if self.path != "/api/v1/analyze":
                raise ApiError(404, "not found")
            require_api_key(self.headers.get("X-API-Key"))
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
            job = store.create(dest)
            self._send_json(200, {"job_id": job.job_id, "status": "processing"})
        except ApiError as e:
            self._send_json(e.status, {"detail": e.detail})


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"forte-vision API listening on {host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    run(port=int(os.getenv("FORTE_PORT", "8000")))
