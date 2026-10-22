import io
import subprocess

import img2pdf
import pytest
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader

from app.services import ocr as ocr_service
from app.services.ocr import OcrUnavailable, ocr_pdf, parse_languages, tesseract_available
from app.services.pdf_errors import PdfProcessingError
from tests.pdf_helpers import make_pdf

needs_tesseract = pytest.mark.skipif(not tesseract_available(), reason="Tesseract is not installed")


def text_scan_pdf(text: str = "HELLO WORLD") -> bytes:
    """A PDF containing only a picture of `text` (like a scan), with no text layer."""
    image = Image.new("RGB", (1600, 500), "white")
    draw = ImageDraw.Draw(image)
    draw.text((120, 150), text, fill="black", font=ImageFont.load_default(size=130))
    png = io.BytesIO()
    image.save(png, format="PNG")
    return img2pdf.convert(
        png.getvalue(), layout_fun=img2pdf.get_fixed_dpi_layout_fun((200, 200))
    )


def extracted_text(pdf: bytes) -> str:
    return " ".join((page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages)


# --- languages ---------------------------------------------------------------


def test_parse_languages_accepts_known_codes_and_removes_duplicates():
    assert parse_languages("eng") == ["eng"]
    assert parse_languages("eng, ind") == ["eng", "ind"]
    assert parse_languages("IND,eng,ind") == ["ind", "eng"]
    assert parse_languages(["eng", "eng"]) == ["eng"]


@pytest.mark.parametrize("value", ["", " , ", "fra", "eng,xx", "eng+ind", "../etc"])
def test_parse_languages_rejects_empty_or_unknown(value):
    with pytest.raises(PdfProcessingError):
        parse_languages(value)


# --- error handling without needing Tesseract ----------------------------------


def test_encrypted_pdf_is_rejected():
    with pytest.raises(PdfProcessingError, match="password-protected"):
        ocr_pdf(make_pdf(1, encrypt_with="secret"), "locked.pdf", ["eng"])


def test_missing_tesseract_is_reported(monkeypatch):
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: False)
    with pytest.raises(OcrUnavailable):
        ocr_pdf(make_pdf(1), "a.pdf", ["eng"])


def fake_run_factory(seen, returncode=0):
    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, returncode=returncode, stdout=b"", stderr=b"")

    return fake_run


def test_command_is_a_list_without_shell_and_uses_selected_options(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_service.subprocess, "run", fake_run_factory(seen, returncode=2))
    with pytest.raises(PdfProcessingError):
        ocr_pdf(make_pdf(1), "a.pdf", ["eng", "ind"], skip_text=True)

    command = seen["command"]
    assert isinstance(command, list)
    assert command[command.index("-l") + 1] == "eng+ind"
    assert "--skip-text" in command
    assert "--force-ocr" not in command
    assert not seen["kwargs"].get("shell")
    assert seen["kwargs"]["timeout"] > 0


def test_force_mode_uses_force_ocr(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_service.subprocess, "run", fake_run_factory(seen, returncode=2))
    with pytest.raises(PdfProcessingError):
        ocr_pdf(make_pdf(1), "a.pdf", ["eng"], skip_text=False)
    assert "--force-ocr" in seen["command"]
    assert "--skip-text" not in seen["command"]


def test_timeout_becomes_a_readable_error(monkeypatch):
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: True)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="ocrmypdf", timeout=1)

    monkeypatch.setattr(ocr_service.subprocess, "run", fake_run)
    with pytest.raises(PdfProcessingError, match="too long"):
        ocr_pdf(make_pdf(1), "a.pdf", ["eng"])


def test_prior_ocr_exit_code_is_explained(monkeypatch):
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_service.subprocess, "run", fake_run_factory({}, returncode=6))
    with pytest.raises(PdfProcessingError, match="already contains text"):
        ocr_pdf(make_pdf(1), "a.pdf", ["eng"], skip_text=False)


def test_missing_dependency_exit_code_means_unavailable(monkeypatch):
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_service.subprocess, "run", fake_run_factory({}, returncode=3))
    with pytest.raises(OcrUnavailable):
        ocr_pdf(make_pdf(1), "a.pdf", ["eng"])


# --- endpoint ---------------------------------------------------------------------


def test_endpoint_rejects_unknown_language(client):
    response = client.post(
        "/api/ocr",
        files={"file": ("a.pdf", make_pdf(1), "application/pdf")},
        data={"languages": "fra"},
    )
    assert response.status_code == 422
    assert "Unsupported language" in response.json()["detail"]


def test_endpoint_rejects_non_pdf(client):
    response = client.post("/api/ocr", files={"file": ("a.pdf", b"MZ nope", "application/pdf")})
    assert response.status_code == 415


def test_endpoint_reports_missing_tesseract_as_503(client, monkeypatch):
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: False)
    response = client.post(
        "/api/ocr", files={"file": ("a.pdf", make_pdf(1), "application/pdf")}
    )
    assert response.status_code == 503
    assert "Tesseract" in response.json()["detail"]


# --- real OCR (needs Tesseract; runs inside Docker) --------------------------------


@needs_tesseract
def test_ocr_makes_scanned_text_searchable():
    scanned = text_scan_pdf()
    assert "WORLD" not in extracted_text(scanned).upper()  # starts as a pure picture
    result = ocr_pdf(scanned, "scan.pdf", ["eng"])
    text = extracted_text(result).upper()
    assert "WORLD" in text


@needs_tesseract
def test_endpoint_returns_searchable_pdf(client):
    response = client.post(
        "/api/ocr",
        files={"file": ("receipt.pdf", text_scan_pdf(), "application/pdf")},
        data={"languages": "eng,ind", "skip_text": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "receipt-ocr.pdf"
    assert "WORLD" in extracted_text(client.get(body["download_url"]).content).upper()


@needs_tesseract
def test_pages_with_text_are_skipped_instead_of_failing():
    # A blank page has no text, but skip mode must not error on already-processed files either.
    first = ocr_pdf(text_scan_pdf(), "scan.pdf", ["eng"])
    again = ocr_pdf(first, "scan-ocr.pdf", ["eng"], skip_text=True)
    assert "WORLD" in extracted_text(again).upper()
