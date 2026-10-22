import io
import re
import zipfile

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError

from app.services.pdf_errors import PdfProcessingError, open_pdf

_PART = re.compile(r"^(\d+)(?:(-)(\d*))?$")


def parse_ranges(spec: str, total_pages: int) -> list[int]:
    """Turn '1-3,5,8-' into zero-based page indices (in the order written).

    Supported parts: 'N', 'A-B' and open-ended 'A-' (through the last page).
    Pages are 1-based in the spec. Duplicates are removed, keeping first occurrence.
    """
    if total_pages < 1:
        raise PdfProcessingError("The PDF has no pages.")
    cleaned = spec.replace(" ", "")
    if not cleaned:
        raise PdfProcessingError("Enter the pages to extract, for example 1-3,5.")

    indices: list[int] = []
    seen: set[int] = set()
    for part in cleaned.split(","):
        match = _PART.match(part)
        if not match:
            raise PdfProcessingError(f"'{part}' is not a valid page range. Use formats like 3 or 2-5.")
        start = int(match.group(1))
        if match.group(2) is None:
            end = start
        elif match.group(3) == "":
            end = total_pages
        else:
            end = int(match.group(3))

        if start < 1 or end < 1:
            raise PdfProcessingError("Page numbers start at 1.")
        if start > end:
            raise PdfProcessingError(f"'{part}' goes backwards. Write it as {end}-{start}.")
        if end > total_pages:
            raise PdfProcessingError(
                f"'{part}' is outside the document, which has {total_pages} page(s)."
            )
        for page in range(start - 1, end):
            if page not in seen:
                seen.add(page)
                indices.append(page)
    return indices


def page_count(data: bytes, name: str) -> int:
    return len(open_pdf(data, name).pages)


def _write(reader: PdfReader, indices: list[int]) -> bytes:
    writer = PdfWriter()
    for index in indices:
        writer.add_page(reader.pages[index])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def extract_ranges(data: bytes, name: str, spec: str) -> bytes:
    """Return one PDF containing only the pages selected by `spec`."""
    reader = open_pdf(data, name)
    indices = parse_ranges(spec, len(reader.pages))
    try:
        return _write(reader, indices)
    except (PyPdfError, ValueError, KeyError, IndexError, OSError) as exc:
        raise PdfProcessingError(f"Could not split '{name}'. It may be damaged.") from exc


def split_all_pages(data: bytes, name: str) -> bytes:
    """Return a ZIP containing every page as its own PDF (page-001.pdf, page-002.pdf, ...)."""
    reader = open_pdf(data, name)
    total = len(reader.pages)
    width = max(3, len(str(total)))
    archive = io.BytesIO()
    try:
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as zf:
            for index in range(total):
                zf.writestr(f"page-{index + 1:0{width}d}.pdf", _write(reader, [index]))
    except (PyPdfError, ValueError, KeyError, IndexError, OSError) as exc:
        raise PdfProcessingError(f"Could not split '{name}'. It may be damaged.") from exc
    return archive.getvalue()
