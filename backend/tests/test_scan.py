import io

import cv2
import numpy as np
import pytest
from PIL import Image

from app.services.pdf_errors import PdfProcessingError
from app.services.scan import (
    apply_mode,
    decode_image,
    find_document_corners,
    four_point_transform,
    order_points,
    scan_image,
    scan_to_pdf,
)
from tests.image_helpers import make_image

# Where the "paper" sits in the synthetic photo (tl, tr, br, bl).
PAPER = np.array([[150, 100], [850, 150], [800, 700], [100, 620]], dtype=np.int32)


def make_photo(shadow: bool = False, with_paper: bool = True) -> np.ndarray:
    """A 1000x800 photo: a skewed bright page with dark text lines on a dark table."""
    photo = np.full((800, 1000, 3), 60, dtype=np.uint8)
    if not with_paper:
        return photo
    page = np.full((800, 1000, 3), 60, dtype=np.uint8)
    cv2.fillPoly(page, [PAPER], (238, 238, 238))
    if shadow:
        # Smooth left-to-right falloff, like uneven room lighting.
        gradient = np.linspace(0.7, 1.0, 1000, dtype=np.float32)[None, :, None]
        shaded = (page.astype(np.float32) * gradient).clip(0, 255).astype(np.uint8)
        mask = np.zeros((800, 1000), dtype=np.uint8)
        cv2.fillPoly(mask, [PAPER], 255)
        page = np.where(mask[..., None] == 255, shaded, page)
    # Text-like dark bars inside the page.
    for y in range(220, 600, 45):
        cv2.line(page, (230, y), (700, y + 10), (20, 20, 20), 6)
    return page


def encode(image: np.ndarray, ext: str = ".jpg") -> bytes:
    ok, buffer = cv2.imencode(ext, image)
    assert ok
    return buffer.tobytes()


def test_order_points_handles_any_input_order():
    shuffled = PAPER[[2, 0, 3, 1]].astype("float32")
    assert order_points(shuffled).tolist() == PAPER.astype("float32").tolist()


def test_finds_skewed_page_corners():
    corners = find_document_corners(make_photo())
    assert corners is not None
    distances = np.linalg.norm(corners - PAPER.astype("float32"), axis=1)
    assert distances.max() < 20


def test_no_page_means_no_corners():
    assert find_document_corners(make_photo(with_paper=False)) is None


def test_four_point_transform_gives_a_rectangle_of_page_size():
    flat = four_point_transform(make_photo(), PAPER.astype("float32"))
    height, width = flat.shape[:2]
    # Top edge ~ sqrt(700^2 + 50^2), left edge ~ sqrt(50^2 + 520^2)
    assert 690 <= width <= 720
    assert 510 <= height <= 580
    # The corners of the flattened page are paper, not table.
    assert flat[5, 5].mean() > 200 and flat[-5, -5].mean() > 200


def test_scan_with_auto_crop_flattens_the_page():
    result = scan_image(encode(make_photo()), "photo.jpg", "color", auto_crop=True)
    assert result.cropped is True
    assert result.image.ndim == 3
    assert result.image.shape[1] < 1000  # table was cut away


def test_bw_output_is_pure_black_and_white_with_text_preserved():
    result = scan_image(encode(make_photo()), "photo.jpg", "bw", auto_crop=True)
    assert result.image.ndim == 2
    assert set(np.unique(result.image)).issubset({0, 255})
    white_share = (result.image == 255).mean()
    assert white_share > 0.85  # mostly clean white paper
    assert (result.image == 0).any()  # text survived


def test_bw_handles_uneven_lighting():
    result = scan_image(encode(make_photo(shadow=True)), "photo.jpg", "bw", auto_crop=True)
    assert (result.image == 255).mean() > 0.85  # shadow did not become black blotches


def test_grayscale_and_color_modes_have_expected_shapes():
    data = encode(make_photo())
    assert scan_image(data, "p.jpg", "grayscale", True).image.ndim == 2
    assert scan_image(data, "p.jpg", "color", True).image.shape[2] == 3


def test_falls_back_to_whole_photo_when_no_page_is_found():
    result = scan_image(encode(make_photo(with_paper=False)), "table.jpg", "color", auto_crop=True)
    assert result.cropped is False
    assert result.image.shape[:2] == (800, 1000)


def test_auto_crop_off_keeps_the_whole_photo():
    result = scan_image(encode(make_photo()), "photo.jpg", "color", auto_crop=False)
    assert result.cropped is False
    assert result.image.shape[:2] == (800, 1000)


def test_exif_orientation_is_applied_before_scanning():
    rotated = make_image("JPEG", (200, 100), orientation=6)
    photo = decode_image(rotated, "phone.jpg")
    assert photo.shape[:2] == (200, 100)  # portrait after rotation


def test_corrupted_photo_is_rejected_with_its_name():
    with pytest.raises(PdfProcessingError, match="broken.jpg"):
        scan_image(b"\xff\xd8\xffnot an image", "broken.jpg", "bw", True)


def test_apply_mode_bw_uses_only_two_values():
    noise = np.random.default_rng(1).integers(0, 255, (200, 300, 3), dtype=np.uint8)
    assert set(np.unique(apply_mode(noise, "bw"))).issubset({0, 255})


def test_scan_to_pdf_makes_one_a4_length_page_per_photo():
    from pypdf import PdfReader

    photos = [("a.jpg", encode(make_photo())), ("b.jpg", encode(make_photo(shadow=True)))]
    pdf = scan_to_pdf(photos, "bw", auto_crop=True)
    pages = PdfReader(io.BytesIO(pdf)).pages
    assert len(pages) == 2
    for page in pages:
        assert round(max(float(page.mediabox.width), float(page.mediabox.height))) == 842


def test_scan_to_pdf_requires_a_photo():
    with pytest.raises(PdfProcessingError):
        scan_to_pdf([], "bw", True)


def test_pillow_can_open_the_bw_page_as_one_bit():
    from app.services.scan import encode_page

    result = scan_image(encode(make_photo()), "p.jpg", "bw", True)
    data, fmt = encode_page(result.image, "bw")
    assert fmt == "png"
    assert Image.open(io.BytesIO(data)).mode == "1"
