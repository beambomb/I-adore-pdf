import json
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.utils.validation import sanitize_filename

_JOB_ID = re.compile(r"^[0-9a-f]{32}$")
_META = "meta.json"


@dataclass(frozen=True)
class Job:
    job_id: str
    filename: str
    media_type: str
    path: Path
    size: int


class JobStore:
    """Stores processed outputs on disk, one UUID-named directory per job."""

    def __init__(self, root: Path, ttl_seconds: int) -> None:
        self.root = root
        self.ttl_seconds = ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def create(self, filename: str, data: bytes, media_type: str) -> Job:
        job_id = uuid.uuid4().hex
        job_dir = self.root / job_id
        job_dir.mkdir()
        safe_name = sanitize_filename(filename, fallback="result")
        (job_dir / "output.bin").write_bytes(data)
        (job_dir / _META).write_text(
            json.dumps({"filename": safe_name, "media_type": media_type}), encoding="utf-8"
        )
        return Job(job_id, safe_name, media_type, job_dir / "output.bin", len(data))

    def get(self, job_id: str) -> Job | None:
        # Strict id format check prevents path traversal via the URL.
        if not _JOB_ID.match(job_id):
            return None
        job_dir = self.root / job_id
        meta_path = job_dir / _META
        output = job_dir / "output.bin"
        if not meta_path.is_file() or not output.is_file():
            return None
        if self._expired(job_dir):
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return Job(job_id, meta["filename"], meta["media_type"], output, output.stat().st_size)

    def cleanup_expired(self) -> int:
        removed = 0
        for job_dir in self.root.iterdir():
            if job_dir.is_dir() and self._expired(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
                removed += 1
        return removed

    def _expired(self, job_dir: Path) -> bool:
        try:
            age = time.time() - job_dir.stat().st_mtime
        except FileNotFoundError:
            return True
        return age > self.ttl_seconds
