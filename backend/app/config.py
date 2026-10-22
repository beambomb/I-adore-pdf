import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc
    if value < minimum:
        raise ValueError(f"Environment variable {name} must be at least {minimum}, got {value}")
    return value


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(name: str) -> list[str]:
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    max_file_bytes: int
    max_total_bytes: int
    job_ttl_seconds: int
    cleanup_interval_seconds: int
    jobs_dir: Path
    # Optional HTTP Basic authentication. Enabled only when both values are set.
    auth_username: str | None = None
    auth_password: str | None = None
    # Maximum POST requests per client per minute. 0 turns rate limiting off.
    rate_limit_per_minute: int = 120
    # Trust the X-Forwarded-For header (only enable behind a reverse proxy you control).
    trust_proxy_headers: bool = False
    # Origins allowed to call the API from a browser on another site. Empty = same-origin only.
    cors_origins: list[str] = field(default_factory=list)
    # Folder with the built frontend. When set, the backend serves it.
    static_dir: Path | None = None

    @property
    def auth_enabled(self) -> bool:
        return bool(self.auth_username and self.auth_password)


def load_settings() -> Settings:
    default_jobs_dir = Path(tempfile.gettempdir()) / "i-adore-pdf-jobs"
    username = os.environ.get("AUTH_USERNAME") or None
    password = os.environ.get("AUTH_PASSWORD") or None
    if bool(username) != bool(password):
        # A half-configured login would silently leave the app open, so refuse to start.
        raise ValueError("AUTH_USERNAME and AUTH_PASSWORD must be set together.")
    static = os.environ.get("STATIC_DIR")
    return Settings(
        max_file_bytes=_int_env("MAX_FILE_MB", 50) * 1024 * 1024,
        max_total_bytes=_int_env("MAX_TOTAL_MB", 200) * 1024 * 1024,
        job_ttl_seconds=_int_env("JOB_TTL_SECONDS", 30 * 60),
        cleanup_interval_seconds=_int_env("CLEANUP_INTERVAL_SECONDS", 60),
        jobs_dir=Path(os.environ.get("JOBS_DIR") or default_jobs_dir),
        auth_username=username,
        auth_password=password,
        rate_limit_per_minute=_int_env("RATE_LIMIT_PER_MINUTE", 120, minimum=0),
        trust_proxy_headers=_bool_env("TRUST_PROXY_HEADERS"),
        cors_origins=_list_env("CORS_ORIGINS"),
        static_dir=Path(static) if static else None,
    )
