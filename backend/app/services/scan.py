import io
from dataclasses import dataclass
from typing import Literal

import cv2
import img2pdf
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.images import MAX_PIXELS
from app.services.pdf_errors import PdfProcessingError

Mode = Literal["bw", "grayscale", "color"]

# Long side of the image used to find the page edges. Smaller is faster and less noisy.
_DETECT_SIDE = 800
# Never produce pages larger than roughly A4 at 300 dpi (keeps memory and PDF size sane).
_MAX_OUTPUT_SIDE = 3508
# A detected page must cover at least this share of the photo to be trusted.
_MIN_PAGE_AREA_RATIO = 0.2
# ...and at most this share, otherwise it is just the photo frame itself.
_MAX_PAGE_AREA_RATIO = 0.98
# A4 length in PDF points, used to size each scanned page.
_PAGE_LONG_SIDE_PT = 842.0


@dataclass(frozen=True)
class ScanResult:
    image: np.ndarray  # BGR (color), or single channel (grayscale / bw)
    cropped: bool  # True when the page edges were found and the photo was straightened


def decode_image(data: bytes, name: str) -> np.ndarray:
    """Decode an uploaded photo to a BGR array, applying its EXIF rotation."""
    try:
        Image.MAX_IMAGE_PIXELS = MAX_PIXELS
        with Image.open(io.BytesIO(data)) as source:
            upright = ImageOps.exif_transpose(source).convert("RGB")
            rgb = np.asarray(upright)
    except Image.DecompressionBombError as exc:
        raise PdfProcessingError(f"'{name}' has too many pixels to process safely.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PdfProcessingError(f"'{name}' is corrupted or not a valid image.") from exc
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def order_points(points: np.ndarray) -> np.ndarray:
    """Order four points as top-left, top-right, bottom-right, bottom-left."""
    pts = points.astype("float32")
    sums = pts.sum(axis=1)
    diffs = np.diff(pts, axis=1).ravel()
    ordered = np.zeros((4, 2), dtype="float32")
    ordered[0] = pts[np.argmin(sums)]  # top-left has the smallest x + y
    ordered[2] = pts[np.argmax(sums)]  # bottom-right has the largest x + y
    ordered[1] = pts[np.argmin(diffs)]  # top-right has the smallest y - x
    ordered[3] = pts[np.argmax(diffs)]  # bottom-left has the largest y - x
    return ordered


def _quad_from_contours(contours, min_area: float, max_area: float) -> np.ndarray | None:
    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:6]:
        area = cv2.contourArea(contour)
        if area < min_area:
            break
        # A "page" that is the whole frame means nothing was really detected
        # (e.g. a uniform photo makes Otsu select every pixel).
        if area > max_area:
            continue
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return approx.reshape(4, 2)
    return None


def find_document_corners(image: np.ndarray) -> np.ndarray | None:
    """Find the four corners of the page in a photo, or None if no page is found."""
    height, width = image.shape[:2]
    scale = _DETECT_SIDE / max(height, width)
    small = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else image
    factor = 1.0 / scale if scale < 1 else 1.0
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY) if small.ndim == 3 else small
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    frame_area = gray.shape[0] * gray.shape[1]
    min_area = _MIN_PAGE_AREA_RATIO * frame_area
    max_area = _MAX_PAGE_AREA_RATIO * frame_area
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))

    # Attempt 1: strong edges (works for pages on contrasting backgrounds).
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    quad = _quad_from_contours(contours, min_area, max_area)

    # Attempt 2: bright page vs darker surroundings via Otsu thresholding.
    if quad is None:
        _, mask = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        quad = _quad_from_contours(contours, min_area, max_area)

    if quad is None:
        return None
    return order_points(quad.astype("float32") * factor)


def four_point_transform(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    """Straighten the quadrilateral `corners` (tl, tr, br, bl) into a flat rectangle."""
    tl, tr, br, bl = corners
    out_width = int(round(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))))
    out_height = int(round(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))))
    destination = np.array(
        [[0, 0], [out_width - 1, 0], [out_width - 1, out_height - 1], [0, out_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(corners, destination)
    return cv2.warpPerspective(
        image, matrix, (out_width, out_height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def _limit_size(image: np.ndarray, max_side: int) -> np.ndarray:
    longest = max(image.shape[:2])
    if longest <= max_side:
        return image
    ratio = max_side / longest
    return cv2.resize(image, None, fx=ratio, fy=ratio, interpolation=cv2.INTER_AREA)


def apply_mode(image: np.ndarray, mode: Mode) -> np.ndarray:
    """Convert to color, grayscale or clean black and white (adaptive threshold)."""
    if mode == "color":
        return image
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    if mode == "grayscale":
        return gray
    # Adaptive threshold compares each pixel to its neighbourhood, so uneven
    # lighting and soft shadows do not turn into black blotches.
    block = int(min(gray.shape[:2]) / 16) | 1
    block = max(15, min(block, 101))
    smooth = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(
        smooth, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, 12
    )


def scan_image(data: bytes, name: str, mode: Mode, auto_crop: bool) -> ScanResult:
    """Turn a photo of a document into a flat, cleaned-up page image."""
    photo = decode_image(data, name)
    cropped = False
    page = photo
    if auto_crop:
        corners = find_document_corners(photo)
        if corners is not None:
            warped = four_point_transform(photo, corners)
            # Reject degenerate results and fall back to the whole photo.
            if min(warped.shape[:2]) >= 100:
                page = warped
                cropped = True
    page = _limit_size(page, _MAX_OUTPUT_SIDE)
    return ScanResult(apply_mode(page, mode), cropped)


def encode_page(image: np.ndarray, mode: Mode) -> tuple[bytes, str]:
    """Encode a scanned page. Returns (bytes, format) with format 'png' or 'jpeg'."""
    if mode == "bw":
        # 1-bit PNG: tiny files and lossless sharp text.
        buffer = io.BytesIO()
        Image.fromarray(image).convert("1", dither=Image.Dither.NONE).save(buffer, format="PNG")
        return buffer.getvalue(), "png"
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise PdfProcessingError("Could not encode the scanned page.")
    return encoded.tobytes(), "jpeg"


def preview_page(data: bytes, name: str, mode: Mode, auto_crop: bool, max_side: int = 1000) -> tuple[bytes, bool]:
    """Small JPEG preview of the scan result for the UI. Returns (jpeg_bytes, cropped)."""
    result = scan_image(data, name, mode, auto_crop)
    small = _limit_size(result.image, max_side)
    ok, encoded = cv2.imencode(".jpg", small, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if not ok:
        raise PdfProcessingError("Could not create a preview.")
    return encoded.tobytes(), result.cropped


def _page_layout(imgwidthpx: int, imgheightpx: int, ndpi) -> tuple[float, float, float, float]:
    """Size each page so its long side is A4 length; the image fills the page."""
    scale = _PAGE_LONG_SIDE_PT / max(imgwidthpx, imgheightpx)
    width, height = imgwidthpx * scale, imgheightpx * scale
    return width, height, width, height


def scan_to_pdf(photos: list[tuple[str, bytes]], mode: Mode, auto_crop: bool) -> bytes:
    """Scan every photo and combine the pages into one PDF, keeping the given order."""
    if not photos:
        raise PdfProcessingError("Select at least one photo.")
    pages = []
    for name, data in photos:
        result = scan_image(data, name, mode, auto_crop)
        encoded, _ = encode_page(result.image, mode)
        pages.append(encoded)
    try:
        pdf = img2pdf.convert(pages, layout_fun=_page_layout)
    except (img2pdf.ImageOpenError, ValueError, OSError) as exc:
        raise PdfProcessingError("Could not build the PDF from these photos.") from exc
    if pdf is None:
        raise PdfProcessingError("Could not build the PDF from these photos.")
    return pdf
