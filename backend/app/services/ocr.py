import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app.services.pdf_errors import PdfProcessingError, open_pdf

# Tesseract language packs installed in the Docker image.
SUPPORTED_LANGUAGES = ("eng", "ind")

OCR_TIMEOUT_SECONDS = 900

# OCRmyPDF exit code when a page already has text and neither skip nor force was requested.
_EXIT_PRIOR_OCR_FOUND = 6
# OCRmyPDF exit code when a required program or language pack is missing.
_EXIT_MISSING_DEPENDENCY = 3


class OcrUnavailable(RuntimeError):
    """Tesseract is not installed on this machine."""


def parse_languages(value: str | list[str]) -> list[str]:
    """Validate a language selection such as 'eng,ind' and return it without duplicates."""
    parts = value.split(",") if isinstance(value, str) else value
    languages: list[str] = []
    for part in parts:
        code = part.strip().lower()
        if not code:
            continue
        if code not in SUPPORTED_LANGUAGES:
            raise PdfProcessingError(
                f"Unsupported language '{code}'. Choose from: {', '.join(SUPPORTED_LANGUAGES)}."
            )
        if code not in languages:
            languages.append(code)
    if not languages:
        raise PdfProcessingError("Choose at least one language for OCR.")
    return languages


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


def ocr_pdf(data: bytes, name: str, languages: list[str], skip_text: bool = True) -> bytes:
    """Add a searchable text layer to a scanned PDF using OCRmyPDF.

    With `skip_text` pages that already contain text are left alone; otherwise every
    page is re-recognized (which rasterizes the page).
    """
    languages = parse_languages(languages)
    # Rejects encrypted and corrupted files with a readable message.
    open_pdf(data, name)
    if not tesseract_available():
        raise OcrUnavailable("Tesseract is not installed.")

    with tempfile.TemporaryDirectory(prefix="ocr-") as tmp:
        source = Path(tmp) / "input.pdf"
        target = Path(tmp) / "output.pdf"
        source.write_bytes(data)
        # Arguments are passed as a list (no shell) so file names can never be interpreted.
        command = [
            sys.executable,
            "-m",
            "ocrmypdf",
            "--quiet",
            "-l",
            "+".join(languages),
            "--skip-text" if skip_text else "--force-ocr",
            "--output-type",
            "pdf",
            "--jobs",
            "2",
            str(source),
            str(target),
        ]
        try:
            completed = subprocess.run(
                command, capture_output=True, timeout=OCR_TIMEOUT_SECONDS, check=False
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfProcessingError(
                f"OCR on '{name}' took too long. Try a PDF with fewer pages."
            ) from exc

        if completed.returncode == _EXIT_PRIOR_OCR_FOUND:
            raise PdfProcessingError(f"'{name}' already contains text. Enable 'skip pages with text'.")
        if completed.returncode == _EXIT_MISSING_DEPENDENCY:
            raise OcrUnavailable("A required OCR component or language pack is missing.")
        if completed.returncode != 0 or not target.is_file():
            raise PdfProcessingError(f"Could not run OCR on '{name}'. The file may be damaged.")
        return target.read_bytes()
