from app.services import ocr as ocr_service
from tests.test_scan import encode, make_photo


def photo():
    return ("photo.jpg", encode(make_photo()), "image/jpeg")


def test_scan_without_ocr_never_calls_ocr(client, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("OCR must not run unless requested")

    monkeypatch.setattr("app.routers.scan.ocr_pdf", boom)
    response = client.post("/api/scan", files=[("files", photo())], data={"mode": "bw"})
    assert response.status_code == 200


def test_scan_with_ocr_runs_ocr_on_the_generated_pdf(client, monkeypatch):
    seen = {}

    def fake_ocr(pdf, name, languages, skip_text):
        seen.update(pdf=pdf, name=name, languages=languages, skip_text=skip_text)
        return pdf + b"\n% ocr-marker"

    monkeypatch.setattr("app.routers.scan.ocr_pdf", fake_ocr)
    response = client.post(
        "/api/scan",
        files=[("files", photo())],
        data={"mode": "bw", "ocr": "true", "languages": "eng,ind"},
    )
    assert response.status_code == 200
    assert seen["languages"] == ["eng", "ind"]
    assert seen["pdf"].startswith(b"%PDF-")
    assert client.get(response.json()["download_url"]).content.endswith(b"% ocr-marker")


def test_scan_with_ocr_rejects_unknown_language(client):
    response = client.post(
        "/api/scan",
        files=[("files", photo())],
        data={"ocr": "true", "languages": "klingon"},
    )
    assert response.status_code == 422


def test_scan_with_ocr_reports_missing_tesseract(client, monkeypatch):
    monkeypatch.setattr(ocr_service, "tesseract_available", lambda: False)
    response = client.post(
        "/api/scan", files=[("files", photo())], data={"ocr": "true"}
    )
    assert response.status_code == 503
