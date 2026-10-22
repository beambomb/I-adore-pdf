import asyncio
from pathlib import PurePath
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import Settings
from app.deps import get_job_store, get_settings
from app.routers.download import JobResult, job_result
from app.services.compress import GhostscriptUnavailable, compress_pdf
from app.services.jobs import JobStore
from app.services.pdf_errors import PdfProcessingError
from app.utils.validation import PDF, read_upload

router = APIRouter(prefix="/api", tags=["compress"])


class CompressJobResult(JobResult):
    original_size: int
    compressed_size: int
    saved_percent: float
    # True when the file was already as small as Ghostscript could make it.
    already_optimal: bool


@router.post("/compress", response_model=CompressJobResult)
async def compress(
    file: UploadFile = File(...),
    level: Literal["low", "medium", "high"] = Form("medium"),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> CompressJobResult:
    upload = await read_upload(file, frozenset({PDF}), settings.max_file_bytes)
    try:
        outcome = await asyncio.to_thread(compress_pdf, upload.data, upload.filename, level)
    except GhostscriptUnavailable as exc:
        raise HTTPException(
            status_code=503, detail="Compression is unavailable: Ghostscript is not installed."
        ) from exc
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    stem = PurePath(upload.filename).stem or "document"
    job = store.create(f"{stem}-compressed.pdf", outcome.data, "application/pdf")
    return CompressJobResult(
        **job_result(job).model_dump(),
        original_size=outcome.original_size,
        compressed_size=outcome.compressed_size,
        saved_percent=outcome.saved_percent,
        already_optimal=not outcome.reduced,
    )
