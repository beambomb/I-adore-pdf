import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import Settings
from app.deps import get_job_store, get_settings
from app.routers.download import JobResult, job_result
from app.services.jobs import JobStore
from app.services.merge import merge_pdfs
from app.services.pdf_errors import PdfProcessingError
from app.utils.validation import PDF, read_uploads

router = APIRouter(prefix="/api", tags=["merge"])


@router.post("/merge", response_model=JobResult)
async def merge(
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> JobResult:
    uploads = await read_uploads(
        files, frozenset({PDF}), settings.max_file_bytes, settings.max_total_bytes
    )
    try:
        merged = await asyncio.to_thread(
            merge_pdfs, [(item.filename, item.data) for item in uploads]
        )
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job_result(store.create("merged.pdf", merged, "application/pdf"))
