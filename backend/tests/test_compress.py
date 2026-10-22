import io
import os
import subprocess

import img2pdf
import pytest
from PIL import Image
from pypdf import PdfReader

from app.services import compress as compress_service
from app.services.compress import PRESETS, GhostscriptUnavailable, compress_pdf, find_ghostscript
from app.services.pdf_errors import PdfProcessingError
from tests.pdf_helpers import make_pdf

needs_gs = pytest.mark.skipif(find_ghostscript() is None, reason="Ghostscript is not installed")


def heavy_pdf() -> bytes:
    """A PDF dominated by one large noisy image, so compression has something to remove."""
    side = 1400
    image = Image.frombytes("RGB", (side, side), os.urandom(side * side * 3))
    jpeg = io.BytesIO()
    image.save(jpeg, format="JPEG", quality=95)
    # Ghostscript only downsamples images above ~1.5x the target resolution, so embed the
    # image at 300 dpi like a real scan (the default 96 dpi would be left untouched).
    return img2pdf.convert(
        jpeg.getvalue(), layout_fun=img2pdf.get_fixed_dpi_layout_fun((300, 300))
    )


def test_presets_map_levels_to_ghostscript_settings():
    assert PRESETS == {"low": "/printer", "medium": "/ebook", "high": "/screen"}


def test_invalid_level_is_rejected():
    with pytest.raises(PdfProcessingError):
        compress_pdf(make_pdf(1), "a.pdf", "extreme")  # type: ignore[arg-type]


def test_encrypted_pdf_is_rejected_before_running_ghostscript():
    with pytest.raises(PdfProcessingError, match="password-protected"):
        compress_pdf(make_pdf(1, encrypt_with="secret"), "locked.pdf", "high")


def test_missing_ghostscript_is_reported(monkeypatch):
    monkeypatch.setattr(compress_service, "find_ghostscript", lambda: None)
    with pytest.raises(GhostscriptUnavailable):
        compress_pdf(make_pdf(1), "a.pdf", "high")


def test_timeout_becomes_a_readable_error(monkeypatch):
    monkeypatch.setattr(compress_service, "find_ghostscript", lambda: "gs")

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="gs", timeout=1)

    monkeypatch.setattr(compress_service.subprocess, "run", fake_run)
    with pytest.raises(PdfProcessingError, match="too long"):
        compress_pdf(make_pdf(1), "a.pdf", "high")


def test_ghostscript_failure_becomes_a_readable_error(monkeypatch):
    monkeypatch.setattr(compress_service, "find_ghostscript", lambda: "gs")
    monkeypatch.setattr(
        compress_service.subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode=1, stdout=b"", stderr=b"boom"),
    )
    with pytest.raises(PdfProcessingError, match="Could not compress"):
        compress_pdf(make_pdf(1), "a.pdf", "high")


def test_command_is_a_list_without_shell(monkeypatch):
    seen = {}
    monkeypatch.setattr(compress_service, "find_ghostscript", lambda: "gs")

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, returncode=1, stdout=b"", stderr=b"")

    monkeypatch.setattr(compress_service.subprocess, "run", fake_run)
    with pytest.raises(PdfProcessingError):
        compress_pdf(make_pdf(1), "a.pdf", "medium")
    assert isinstance(seen["command"], list)
    assert "-dPDFSETTINGS=/ebook" in seen["command"]
    assert "-dSAFER" in seen["command"]
    assert not seen["kwargs"].get("shell")
    assert seen["kwargs"]["timeout"] > 0


@needs_gs
def test_high_preset_reduces_a_heavy_pdf():
    original = heavy_pdf()
    outcome = compress_pdf(original, "heavy.pdf", "high")
    assert outcome.reduced is True
    assert outcome.compressed_size < outcome.original_size
    assert outcome.saved_percent > 0
    assert len(PdfReader(io.BytesIO(outcome.data)).pages) == 1


@needs_gs
def test_levels_are_ordered_by_strength():
    original = heavy_pdf()
    low = compress_pdf(original, "heavy.pdf", "low")
    high = compress_pdf(original, "heavy.pdf", "high")
    assert high.compressed_size <= low.compressed_size


@needs_gs
def test_tiny_pdf_keeps_original_when_not_smaller():
    original = make_pdf(1)
    outcome = compress_pdf(original, "tiny.pdf", "low")
    assert outcome.reduced is False
    assert outcome.data == original
    assert outcome.saved_percent == 0.0


@needs_gs
def test_endpoint_returns_sizes_and_download(client):
    original = heavy_pdf()
    response = client.post(
        "/api/compress",
        files={"file": ("scan.pdf", original, "application/pdf")},
        data={"level": "high"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "scan-compressed.pdf"
    assert body["original_size"] == len(original)
    assert body["compressed_size"] < body["original_size"]
    assert body["already_optimal"] is False
    download = client.get(body["download_url"])
    assert len(download.content) == body["compressed_size"]


def test_endpoint_rejects_invalid_level(client):
    response = client.post(
        "/api/compress",
        files={"file": ("a.pdf", make_pdf(1), "application/pdf")},
        data={"level": "extreme"},
    )
    assert response.status_code == 422


def test_endpoint_rejects_non_pdf(client):
    response = client.post(
        "/api/compress", files={"file": ("a.pdf", b"MZ not pdf", "application/pdf")}
    )
    assert response.status_code == 415


def test_endpoint_reports_missing_ghostscript_as_503(client, monkeypatch):
    monkeypatch.setattr(compress_service, "find_ghostscript", lambda: None)
    response = client.post(
        "/api/compress", files={"file": ("a.pdf", make_pdf(1), "application/pdf")}
    )
    assert response.status_code == 503
    assert "Ghostscript" in response.json()["detail"]
