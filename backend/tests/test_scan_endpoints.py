import base64
import io

from PIL import Image
from pypdf import PdfReader

from tests.test_scan import encode, make_photo


def photo_upload(name="photo.jpg"):
    return (name, encode(make_photo()), "image/jpeg")


def test_preview_returns_a_jpeg_data_url(client):
    response = client.post(
        "/api/scan/preview",
        files={"file": photo_upload()},
        data={"mode": "bw", "auto_crop": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["cropped"] is True
    assert body["image"].startswith("data:image/jpeg;base64,")
    jpeg = base64.b64decode(body["image"].split(",", 1)[1])
    assert Image.open(io.BytesIO(jpeg)).format == "JPEG"


def test_preview_respects_auto_crop_off(client):
    response = client.post(
        "/api/scan/preview",
        files={"file": photo_upload()},
        data={"mode": "color", "auto_crop": "false"},
    )
    assert response.status_code == 200
    assert response.json()["cropped"] is False


def test_scan_builds_a_multi_page_pdf_in_order(client):
    response = client.post(
        "/api/scan",
        files=[("files", photo_upload("a.jpg")), ("files", photo_upload("b.jpg")), ("files", photo_upload("c.jpg"))],
        data={"mode": "bw", "auto_crop": "true"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "scan.pdf"
    pdf = client.get(body["download_url"]).content
    assert len(PdfReader(io.BytesIO(pdf)).pages) == 3


def test_scan_rejects_invalid_mode(client):
    response = client.post(
        "/api/scan", files=[("files", photo_upload())], data={"mode": "sepia"}
    )
    assert response.status_code == 422


def test_scan_rejects_pdf_uploads(client):
    response = client.post(
        "/api/scan", files=[("files", ("a.pdf", b"%PDF-1.7 hi", "application/pdf"))]
    )
    assert response.status_code == 415


def test_scan_reports_corrupted_photo(client):
    response = client.post(
        "/api/scan",
        files=[("files", ("bad.jpg", b"\xff\xd8\xff garbage", "image/jpeg"))],
    )
    assert response.status_code == 422
    assert "bad.jpg" in response.json()["detail"]


def test_preview_reports_corrupted_photo(client):
    response = client.post(
        "/api/scan/preview",
        files={"file": ("bad.jpg", b"\xff\xd8\xff garbage", "image/jpeg")},
    )
    assert response.status_code == 422
