import os
import time

from app.services.jobs import JobStore


def test_create_and_get_job(tmp_path):
    store = JobStore(tmp_path, ttl_seconds=60)
    job = store.create("../report?.pdf", b"data", "application/pdf")
    assert job.filename == "report_.pdf"
    found = store.get(job.job_id)
    assert found is not None
    assert found.path.read_bytes() == b"data"
    assert found.size == 4


def test_get_rejects_malformed_ids(tmp_path):
    store = JobStore(tmp_path, ttl_seconds=60)
    assert store.get("../../etc/passwd") is None
    assert store.get("nothex") is None
    assert store.get("a" * 32) is None


def test_expired_jobs_are_hidden_and_cleaned(tmp_path):
    store = JobStore(tmp_path, ttl_seconds=10)
    old = store.create("old.pdf", b"x", "application/pdf")
    fresh = store.create("new.pdf", b"y", "application/pdf")
    past = time.time() - 100
    os.utime(tmp_path / old.job_id, (past, past))

    assert store.get(old.job_id) is None
    assert store.cleanup_expired() == 1
    assert not (tmp_path / old.job_id).exists()
    assert store.get(fresh.job_id) is not None
