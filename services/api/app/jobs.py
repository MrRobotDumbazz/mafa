import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from .mlpipe.base import MLResult
from .mlpipe.mock import MockPipeline


@dataclass
class Job:
    job_id: str
    video_path: Path
    status: str = "processing"
    verdict: str | None = None
    violations: list[dict] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)


def _violation_dict(e):
    v = {
        "type": e.type,
        "timecode_sec": e.timecode_sec,
        "description": e.description,
        "evidence_frames": [
            {"timestamp_sec": ev.timestamp_sec, "image_base64": ev.frame or ""}
            for ev in e.evidence
        ],
    }
    if e.normative is not None:
        v["normative"] = {
            "document": e.normative.document,
            "clause": e.normative.clause,
            "url": e.normative.url,
        }
    return v


class JobStore:
    def __init__(self, pipeline: MockPipeline, timeout_sec: float = 300.0, workers: int = 2) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=workers)
        self._pipeline = pipeline
        self._timeout_sec = timeout_sec

    def create(self, video_path: Path) -> Job:
        job = Job(job_id=uuid.uuid4().hex[:8], video_path=video_path)
        with self._lock:
            self._jobs[job.job_id] = job
        self._executor.submit(self._run, job.job_id)
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is not None and job.status == "processing":
            if time.monotonic() - job.created_at > self._timeout_sec:
                self._fail(job, f"processing exceeded {int(self._timeout_sec)}s limit")
        return job

    def result(self, job: Job) -> dict:
        payload = {
            "job_id": job.job_id,
            "status": job.status,
            "verdict": job.verdict,
            "violations": job.violations,
        }
        if job.error:
            payload["error"] = job.error
        return payload

    def _fail(self, job: Job, message: str) -> None:
        with self._lock:
            if job.status != "processing":
                return
            job.status = "failed"
            job.error = message[:300]

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
        try:
            result: MLResult = self._pipeline.analyze(job.video_path)
            violations = [_violation_dict(e) for e in result.events]
            with self._lock:
                job.status = "done"
                job.verdict = "violation" if violations else "no_violation"
                job.violations = violations
        except Exception as exc:
            self._fail(job, str(exc)[:300])
