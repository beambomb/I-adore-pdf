from functools import lru_cache

from app.config import Settings, load_settings
from app.services.jobs import JobStore


@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def get_job_store() -> JobStore:
    settings = get_settings()
    return JobStore(settings.jobs_dir, settings.job_ttl_seconds)
