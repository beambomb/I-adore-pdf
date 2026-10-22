import asyncio
from pathlib import PurePath
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import Settings
from app.deps import get_job_store, get_settings
from app.routers.download import JobResult, job_result
from app.services.jobs import JobStore
from app.services.pdf_errors import PdfProcessingError
from app.services.split import extract_ranges, page_count, split_all_pages
from app.utils.validation import PDF, read_upload

router = APIRouter(prefix="/api/split", tags=["split"])


class SplitInfo(BaseModel):
    filename: str
    pages: int


@router.post("/info", response_model=SplitInfo)
async def info(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
) -> SplitInfo:
    upload = await read_upload(file, frozenset({PDF}), settings.max_file_bytes)
    try:
        pages = await asyncio.to_thread(page_count, upload.data, upload.filename)
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SplitInfo(filename=upload.filename, pages=pages)


@router.post("", response_model=JobResult)
async def split(
    file: UploadFile = File(...),
    mode: Literal["ranges", "all"] = Form(...),
    ranges: str = Form(""),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> JobResult:
    upload = await read_upload(file, frozenset({PDF}), settings.max_file_bytes)
    stem = PurePath(upload.filename).stem or "document"
    try:
        if mode == "ranges":
            data = await asyncio.to_thread(extract_ranges, upload.data, upload.filename, ranges)
            job = store.create(f"{stem}-split.pdf", data, "application/pdf")
        else:
            data = await asyncio.to_thread(split_all_pages, upload.data, upload.filename)
            job = store.create(f"{stem}-pages.zip", data, "application/zip")
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return job_result(job)
