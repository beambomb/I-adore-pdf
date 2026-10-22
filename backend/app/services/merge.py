import io

from pypdf import PdfWriter
from pypdf.errors import PyPdfError

from app.services.pdf_errors import PdfProcessingError, open_pdf


def merge_pdfs(documents: list[tuple[str, bytes]]) -> bytes:
    """Merge PDFs in the given order. `documents` is a list of (filename, bytes)."""
    if len(documents) < 2:
        raise PdfProcessingError("Select at least two PDF files to merge.")
    writer = PdfWriter()
    try:
        for name, data in documents:
            reader = open_pdf(data, name)
            for page in reader.pages:
                writer.add_page(page)
        output = io.BytesIO()
        writer.write(output)
    except PdfProcessingError:
        raise
    except (PyPdfError, ValueError, KeyError, IndexError, OSError) as exc:
        raise PdfProcessingError("Could not merge these files. One of them may be damaged.") from exc
    return output.getvalue()
