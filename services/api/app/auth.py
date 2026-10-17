from .config import get_settings
from .errors import ApiError


def require_api_key(provided: str | None) -> None:
    settings = get_settings()
    if not settings.api_keys:
        raise ApiError(503, "API key not configured")
    if provided is None or provided not in settings.api_keys:
        raise ApiError(401, "Invalid or missing X-API-Key")
