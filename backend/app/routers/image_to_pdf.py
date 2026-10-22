import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import Settings
from app.deps import get_job_store, get_settings
from app.routers.download import JobResult, job_result
from app.services.image_to_pdf import images_to_pdf
from app.services.jobs import JobStore
from app.services.pdf_errors import PdfProcessingError
from app.utils.validation import IMAGE_TYPES, read_uploads

router = APIRouter(prefix="/api", tags=["image-to-pdf"])


@router.post("/image-to-pdf", response_model=JobResult)
async def image_to_pdf(
    files: list[UploadFile] = File(...),
    page_size: Literal["fit", "a4"] = Form("fit"),
    orientation: Literal["auto", "portrait", "landscape"] = Form("auto"),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> JobResult:
    uploads = await read_uploads(
        files, IMAGE_TYPES, settings.max_file_bytes, settings.max_total_bytes
    )
    try:
        pdf = await asyncio.to_thread(
            images_to_pdf,
            [(item.filename, item.data) for item in uploads],
            page_size,
            orientation,
        )
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job_result(store.create("images.pdf", pdf, "application/pdf"))
