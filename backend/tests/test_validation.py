import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

from app.utils.validation import (
    IMAGE_TYPES,
    PDF,
    read_upload,
    read_uploads,
    sanitize_filename,
    sniff_type,
)

PDF_HEAD = b"%PDF-1.7\n%fake body"


def make_upload(data: bytes, name: str = "doc.pdf") -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=name)


def run(coro):
    return asyncio.run(coro)


def test_sniff_type_detects_known_formats():
    assert sniff_type(b"%PDF-1.4") == "pdf"
    assert sniff_type(b"\xff\xd8\xff\xe0") == "jpeg"
    assert sniff_type(b"\x89PNG\r\n\x1a\n") == "png"
    assert sniff_type(b"RIFF\x00\x00\x00\x00WEBP") == "webp"
    assert sniff_type(b"MZ\x90\x00") is None


def test_sanitize_filename_removes_paths_and_unsafe_chars():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("C:\\Users\\me\\my file?.pdf") == "my file_.pdf"
    assert sanitize_filename(".hidden") == "hidden"
    assert sanitize_filename("") == "file"
    assert sanitize_filename(None, fallback="x") == "x"


def test_read_upload_accepts_real_pdf():
    result = run(read_upload(make_upload(PDF_HEAD), frozenset({PDF}), 1024))
    assert result.kind == PDF
    assert result.filename == "doc.pdf"


def test_read_upload_rejects_fake_pdf_by_content():
    with pytest.raises(HTTPException) as exc:
        run(read_upload(make_upload(b"not really a pdf", "evil.pdf"), frozenset({PDF}), 1024))
    assert exc.value.status_code == 415


def test_read_upload_rejects_wrong_type_for_tool():
    with pytest.raises(HTTPException) as exc:
        run(read_upload(make_upload(PDF_HEAD), IMAGE_TYPES, 1024))
    assert exc.value.status_code == 415


def test_read_upload_rejects_oversized_file():
    with pytest.raises(HTTPException) as exc:
        run(read_upload(make_upload(PDF_HEAD + b"x" * 2048), frozenset({PDF}), 1024))
    assert exc.value.status_code == 413


def test_read_upload_rejects_empty_file():
    with pytest.raises(HTTPException) as exc:
        run(read_upload(make_upload(b""), frozenset({PDF}), 1024))
    assert exc.value.status_code == 400


def test_read_uploads_enforces_total_limit():
    uploads = [make_upload(PDF_HEAD + b"x" * 600, f"{i}.pdf") for i in range(3)]
    with pytest.raises(HTTPException) as exc:
        run(read_uploads(uploads, frozenset({PDF}), 1024, 1500))
    assert exc.value.status_code == 413


def test_read_uploads_requires_at_least_one_file():
    with pytest.raises(HTTPException) as exc:
        run(read_uploads([], frozenset({PDF}), 1024, 2048))
    assert exc.value.status_code == 400
