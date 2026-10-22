from typing import Literal

import img2pdf

from app.services.images import normalize_image
from app.services.pdf_errors import PdfProcessingError

PageSize = Literal["fit", "a4"]
Orientation = Literal["auto", "portrait", "landscape"]

_A4_PORTRAIT = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
_A4_LANDSCAPE = (_A4_PORTRAIT[1], _A4_PORTRAIT[0])


def _layout(page_size: PageSize, orientation: Orientation):
    """Build the img2pdf layout function for the chosen page options."""
    if page_size == "fit":
        # Each page takes the size of its image.
        return None
    if orientation == "portrait":
        return img2pdf.get_layout_fun(_A4_PORTRAIT, fit=img2pdf.FitMode.into)
    if orientation == "landscape":
        return img2pdf.get_layout_fun(_A4_LANDSCAPE, fit=img2pdf.FitMode.into)
    # auto: turn the A4 page to match each image's orientation
    return img2pdf.get_layout_fun(_A4_PORTRAIT, fit=img2pdf.FitMode.into, auto_orient=True)


def images_to_pdf(
    images: list[tuple[str, bytes]],
    page_size: PageSize = "fit",
    orientation: Orientation = "auto",
) -> bytes:
    """Convert images (in the given order) to a PDF with one image per page."""
    if not images:
        raise PdfProcessingError("Select at least one image.")
    prepared = [normalize_image(data, name) for name, data in images]
    layout = _layout(page_size, orientation)
    # Passing layout_fun=None would override img2pdf's default, so only pass it when set.
    options = {} if layout is None else {"layout_fun": layout}
    try:
        pdf = img2pdf.convert(prepared, **options)
    except (img2pdf.ImageOpenError, img2pdf.PdfTooLargeError, ValueError, OSError) as exc:
        raise PdfProcessingError("Could not convert these images to PDF.") from exc
    if pdf is None:
        raise PdfProcessingError("Could not convert these images to PDF.")
    return pdf
