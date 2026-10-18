from functools import lru_cache
import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        keys = os.getenv("FORTE_API_KEYS", os.getenv("FORTE_API_KEY", ""))
        self.api_keys: set[str] = {k.strip() for k in keys.split(",") if k.strip()}
        base = Path(__file__).resolve().parent.parent
        self.storage_dir = Path(os.getenv("FORTE_STORAGE_DIR", str(base / ".storage")))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_upload_bytes = int(os.getenv("FORTE_MAX_UPLOAD_MB", "200")) * 1024 * 1024
        self.job_timeout_sec = float(os.getenv("FORTE_JOB_TIMEOUT_SEC", "300"))
        self.pipeline_cmd = os.getenv("FORTE_PIPELINE_CMD") or f"python3 {base.parent / 'ml' / 'run.py'}"
        static_dir_env = os.getenv("FORTE_STATIC_DIR", "")
        self.static_dir = Path(static_dir_env) if static_dir_env else None
        self.web_keyless = os.getenv("FORTE_WEB_KEYLESS", "1") == "1"
        self.violation_catalog = Path(
            os.getenv("FORTE_VIOLATION_CATALOG", str(base.parent.parent / "contracts" / "violation_catalog.yaml"))
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
