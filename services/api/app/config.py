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


@lru_cache
def get_settings() -> Settings:
    return Settings()
