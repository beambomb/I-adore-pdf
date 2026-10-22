import pytest
from fastapi.testclient import TestClient

from app import deps
from app.main import app


@pytest.fixture(autouse=True)
def isolated_jobs_dir(tmp_path, monkeypatch):
    """Every test gets its own jobs directory and fresh cached settings/store."""
    monkeypatch.setenv("JOBS_DIR", str(tmp_path / "jobs"))
    deps.get_settings.cache_clear()
    deps.get_job_store.cache_clear()
    yield
    deps.get_settings.cache_clear()
    deps.get_job_store.cache_clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
