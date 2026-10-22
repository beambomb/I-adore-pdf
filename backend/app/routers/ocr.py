import asyncio
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.config import Settings
from app.deps import get_job_store, get_settings
from app.routers.download import JobResult, job_result
from app.services.jobs import JobStore
from app.services.ocr import OcrUnavailable, ocr_pdf, parse_languages
from app.services.pdf_errors import PdfProcessingError
from app.utils.validation import PDF, read_upload

router = APIRouter(prefix="/api", tags=["ocr"])

OCR_UNAVAILABLE_MESSAGE = "OCR is unavailable: Tesseract is not installed."


@router.post("/ocr", response_model=JobResult)
async def ocr(
    file: UploadFile = File(...),
    languages: str = Form("eng"),
    skip_text: bool = Form(True),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_job_store),
) -> JobResult:
    upload = await read_upload(file, frozenset({PDF}), settings.max_file_bytes)
    try:
        selected = parse_languages(languages)
        data = await asyncio.to_thread(ocr_pdf, upload.data, upload.filename, selected, skip_text)
    except OcrUnavailable as exc:
        raise HTTPException(status_code=503, detail=OCR_UNAVAILABLE_MESSAGE) from exc
    except PdfProcessingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    stem = PurePath(upload.filename).stem or "document"
    return job_result(store.create(f"{stem}-ocr.pdf", data, "application/pdf"))
