import pytest

from app.services.merge import merge_pdfs
from app.services.pdf_errors import PdfProcessingError
from tests.pdf_helpers import make_pdf, page_widths


def test_merge_keeps_order_and_page_count():
    merged = merge_pdfs([("a.pdf", make_pdf(2)), ("b.pdf", make_pdf(3))])
    # make_pdf encodes page index in width: a -> 100,101 ; b -> 100,101,102
    assert page_widths(merged) == [100, 101, 100, 101, 102]


def test_merge_requires_two_files():
    with pytest.raises(PdfProcessingError):
        merge_pdfs([("a.pdf", make_pdf(1))])


def test_merge_rejects_corrupted_pdf():
    broken = b"%PDF-1.7\nthis is not a real pdf body"
    with pytest.raises(PdfProcessingError, match="b.pdf"):
        merge_pdfs([("a.pdf", make_pdf(1)), ("b.pdf", broken)])


def test_merge_rejects_encrypted_pdf():
    with pytest.raises(PdfProcessingError, match="password-protected"):
        merge_pdfs([("a.pdf", make_pdf(1)), ("locked.pdf", make_pdf(1, encrypt_with="secret"))])


def test_merge_endpoint_returns_downloadable_job(client):
    response = client.post(
        "/api/merge",
        files=[
            ("files", ("a.pdf", make_pdf(1), "application/pdf")),
            ("files", ("b.pdf", make_pdf(2), "application/pdf")),
        ],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "merged.pdf"
    download = client.get(body["download_url"])
    assert download.status_code == 200
    assert page_widths(download.content) == [100, 100, 101]


def test_merge_endpoint_rejects_non_pdf_content(client):
    response = client.post(
        "/api/merge",
        files=[
            ("files", ("a.pdf", make_pdf(1), "application/pdf")),
            ("files", ("fake.pdf", b"MZ not a pdf", "application/pdf")),
        ],
    )
    assert response.status_code == 415


def test_merge_endpoint_reports_corrupted_pdf(client):
    response = client.post(
        "/api/merge",
        files=[
            ("files", ("a.pdf", make_pdf(1), "application/pdf")),
            ("files", ("bad.pdf", b"%PDF-1.7\ngarbage", "application/pdf")),
        ],
    )
    assert response.status_code == 422
    assert "bad.pdf" in response.json()["detail"]
