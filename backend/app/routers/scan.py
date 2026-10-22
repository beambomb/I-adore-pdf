import asyncio
import base64
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import Settings
from app.deps import get_job_store, get_settings
from app.routers.download import JobResult, job_result
from app.services.jobs import JobStore
from app.services.pdf_errors import PdfProcessingError
from app.services.scan import preview_page, scan_to_pdf
from app.utils.validation import IMAGE_TYPES, read_upload, read_uploads

router = APIRouter(prefix="/api/scan", tags=["scan"])

ScanMode = Literal["bw", "grayscale", "color"]


class ScanPreview(BaseModel):
    image: str  # data URL (JPEG)
    cropped: bool


@router.post("/preview", response_model=ScanPreview)
async def preview(
    file: UploadFile = File(...),
    mode: ScanMode = Form("bw"),
    auto_crop: bool = Form(True),
    settings: Settings = Depends(get_settings),
) -> ScanPreview:
    upload = await read_upload(file, IMAGE_TYPES, settings.max_file_bytes)
    try:
        jpeg, cropped = await asyncio.to_thread(
            preview_page, upload.data, upload.filename, mode, auto_crop
        )
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    encoded = base64.b64encode(jpeg).decode("ascii")
    return ScanPreview(image=f"data:image/jpeg;base64,{encoded}", cropped=cropped)


@router.post("", response_model=JobResult)
async def scan(
    files: list[UploadFile] = File(...),
    mode: ScanMode = Form("bw"),
    auto_crop: bool = Form(True),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> JobResult:
    uploads = await read_uploads(
        files, IMAGE_TYPES, settings.max_file_bytes, settings.max_total_bytes
    )
    try:
        pdf = await asyncio.to_thread(
            scan_to_pdf, [(item.filename, item.data) for item in uploads], mode, auto_crop
        )
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job_result(store.create("scan.pdf", pdf, "application/pdf"))
