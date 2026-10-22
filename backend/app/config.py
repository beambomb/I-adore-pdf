import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"Environment variable {name} must be positive, got {value}")
    return value


@dataclass(frozen=True)
class Settings:
    max_file_bytes: int
    max_total_bytes: int
    job_ttl_seconds: int
    cleanup_interval_seconds: int
    jobs_dir: Path


def load_settings() -> Settings:
    default_jobs_dir = Path(tempfile.gettempdir()) / "i-adore-pdf-jobs"
    return Settings(
        max_file_bytes=_int_env("MAX_FILE_MB", 50) * 1024 * 1024,
        max_total_bytes=_int_env("MAX_TOTAL_MB", 200) * 1024 * 1024,
        job_ttl_seconds=_int_env("JOB_TTL_SECONDS", 30 * 60),
        cleanup_interval_seconds=_int_env("CLEANUP_INTERVAL_SECONDS", 60),
        jobs_dir=Path(os.environ.get("JOBS_DIR") or default_jobs_dir),
    )
