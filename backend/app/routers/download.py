from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.deps import get_job_store
from app.services.jobs import Job, JobStore

router = APIRouter(prefix="/api", tags=["download"])


class JobResult(BaseModel):
    job_id: str
    filename: str
    size: int
    media_type: str
    download_url: str


def job_result(job: Job) -> JobResult:
    return JobResult(
        job_id=job.job_id,
        filename=job.filename,
        size=job.size,
        media_type=job.media_type,
        download_url=f"/api/download/{job.job_id}",
    )


@router.get("/download/{job_id}")
def download(job_id: str, store: JobStore = Depends(get_job_store)) -> FileResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="File not found or expired.")
    return FileResponse(job.path, media_type=job.media_type, filename=job.filename)
