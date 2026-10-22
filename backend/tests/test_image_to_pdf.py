import io

import pytest
from pypdf import PdfReader

from app.services.image_to_pdf import images_to_pdf
from app.services.images import normalize_image
from app.services.pdf_errors import PdfProcessingError
from tests.image_helpers import make_image


def page_sizes(pdf: bytes) -> list[tuple[int, int]]:
    reader = PdfReader(io.BytesIO(pdf))
    return [(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in reader.pages]


def test_one_page_per_image_in_order():
    first = make_image("PNG", (200, 100))
    second = make_image("JPEG", (100, 300))
    pdf = images_to_pdf([("a.png", first), ("b.jpg", second)])
    sizes = page_sizes(pdf)
    assert len(sizes) == 2
    assert sizes[0][0] > sizes[0][1]  # landscape first
    assert sizes[1][0] < sizes[1][1]  # portrait second


def test_exif_rotation_is_applied():
    # Stored 200x100 but tagged "rotate 90 degrees": it should display as portrait.
    rotated = make_image("JPEG", (200, 100), orientation=6)
    pdf = images_to_pdf([("phone.jpg", rotated)])
    (width, height), = page_sizes(pdf)
    assert width < height


def test_jpeg_without_rotation_is_passed_through_untouched():
    original = make_image("JPEG", (120, 80))
    assert normalize_image(original, "x.jpg") == original


def test_png_with_alpha_is_flattened_and_converts():
    transparent = make_image("PNG", (50, 50), mode="RGBA", color=(0, 0, 0, 0))
    pdf = images_to_pdf([("t.png", transparent)])
    assert len(page_sizes(pdf)) == 1


def test_webp_is_converted():
    webp = make_image("WEBP", (60, 40))
    pdf = images_to_pdf([("w.webp", webp)])
    assert len(page_sizes(pdf)) == 1


def test_a4_portrait_and_landscape_pages():
    image = make_image("PNG", (300, 100))
    assert page_sizes(images_to_pdf([("a.png", image)], "a4", "portrait")) == [(595, 842)]
    assert page_sizes(images_to_pdf([("a.png", image)], "a4", "landscape")) == [(842, 595)]


def test_a4_auto_follows_image_orientation():
    wide = make_image("PNG", (300, 100))
    tall = make_image("PNG", (100, 300))
    sizes = page_sizes(images_to_pdf([("w.png", wide), ("t.png", tall)], "a4", "auto"))
    assert sizes == [(842, 595), (595, 842)]


def test_corrupted_image_is_rejected_with_name():
    with pytest.raises(PdfProcessingError, match="broken.png"):
        images_to_pdf([("broken.png", b"\x89PNG\r\n\x1a\nnot really png")])


def test_requires_at_least_one_image():
    with pytest.raises(PdfProcessingError):
        images_to_pdf([])


def test_endpoint_converts_multiple_images(client):
    response = client.post(
        "/api/image-to-pdf",
        files=[
            ("files", ("a.png", make_image("PNG"), "image/png")),
            ("files", ("b.jpg", make_image("JPEG", orientation=6), "image/jpeg")),
        ],
        data={"page_size": "a4", "orientation": "portrait"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "images.pdf"
    pdf = client.get(body["download_url"]).content
    assert page_sizes(pdf) == [(595, 842), (595, 842)]


def test_endpoint_rejects_pdf_upload(client):
    response = client.post(
        "/api/image-to-pdf",
        files=[("files", ("a.pdf", b"%PDF-1.7 hi", "application/pdf"))],
    )
    assert response.status_code == 415


def test_endpoint_rejects_invalid_page_size(client):
    response = client.post(
        "/api/image-to-pdf",
        files=[("files", ("a.png", make_image("PNG"), "image/png"))],
        data={"page_size": "letter"},
    )
    assert response.status_code == 422


def test_endpoint_reports_corrupted_image(client):
    response = client.post(
        "/api/image-to-pdf",
        files=[("files", ("bad.png", b"\x89PNG\r\n\x1a\ngarbage", "image/png"))],
    )
    assert response.status_code == 422
    assert "bad.png" in response.json()["detail"]
