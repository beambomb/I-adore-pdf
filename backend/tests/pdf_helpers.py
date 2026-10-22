import io

from pypdf import PdfReader, PdfWriter


def make_pdf(pages: int = 1, encrypt_with: str | None = None) -> bytes:
    """Build a small PDF with `pages` blank pages; page i has width 100 + i so order is checkable."""
    writer = PdfWriter()
    for i in range(pages):
        writer.add_blank_page(width=100 + i, height=200)
    if encrypt_with:
        writer.encrypt(encrypt_with)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def page_widths(data: bytes) -> list[int]:
    return [int(page.mediabox.width) for page in PdfReader(io.BytesIO(data)).pages]
