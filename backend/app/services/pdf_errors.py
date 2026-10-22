import io

from pypdf import PdfReader
from pypdf.errors import PyPdfError


class PdfProcessingError(ValueError):
    """A user-facing problem with an uploaded PDF (corrupted, encrypted, ...)."""


def open_pdf(data: bytes, name: str) -> PdfReader:
    """Open a PDF for reading, turning pypdf failures into readable errors."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PdfProcessingError(f"'{name}' is password-protected. Unlock it first.")
        if len(reader.pages) == 0:
            raise PdfProcessingError(f"'{name}' has no pages.")
    except PdfProcessingError:
        raise
    except (PyPdfError, ValueError, KeyError, IndexError, OSError) as exc:
        raise PdfProcessingError(f"'{name}' is corrupted or not a valid PDF.") from exc
    return reader
