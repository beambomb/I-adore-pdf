import io
import zipfile

from tests.pdf_helpers import make_pdf, page_widths


def post_split(client, data, **form):
    return client.post(
        "/api/split",
        files={"file": ("report.pdf", data, "application/pdf")},
        data=form,
    )


def test_info_returns_page_count(client):
    response = client.post(
        "/api/split/info", files={"file": ("report.pdf", make_pdf(7), "application/pdf")}
    )
    assert response.status_code == 200
    assert response.json() == {"filename": "report.pdf", "pages": 7}


def test_info_rejects_corrupted_pdf(client):
    response = client.post(
        "/api/split/info", files={"file": ("bad.pdf", b"%PDF-1.7\njunk", "application/pdf")}
    )
    assert response.status_code == 422


def test_ranges_mode_returns_selected_pages_in_order(client):
    response = post_split(client, make_pdf(10), mode="ranges", ranges="1-3,5")
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "report-split.pdf"
    download = client.get(body["download_url"])
    # Page i has width 100 + i: pages 1,2,3,5 -> 100,101,102,104
    assert page_widths(download.content) == [100, 101, 102, 104]


def test_ranges_mode_open_ended(client):
    response = post_split(client, make_pdf(5), mode="ranges", ranges="4-")
    download = client.get(response.json()["download_url"])
    assert page_widths(download.content) == [103, 104]


def test_ranges_outside_document_is_422(client):
    response = post_split(client, make_pdf(3), mode="ranges", ranges="2-9")
    assert response.status_code == 422
    assert "3 page" in response.json()["detail"]


def test_ranges_mode_requires_ranges(client):
    response = post_split(client, make_pdf(3), mode="ranges", ranges="")
    assert response.status_code == 422


def test_all_mode_returns_zip_with_one_pdf_per_page(client):
    response = post_split(client, make_pdf(10), mode="all")
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "report-pages.zip"
    assert body["media_type"] == "application/zip"

    archive = zipfile.ZipFile(io.BytesIO(client.get(body["download_url"]).content))
    names = archive.namelist()
    assert len(names) == 10
    assert names[0] == "page-001.pdf"
    assert names[-1] == "page-010.pdf"
    assert page_widths(archive.read("page-004.pdf")) == [103]


def test_invalid_mode_is_rejected(client):
    response = post_split(client, make_pdf(2), mode="halves")
    assert response.status_code == 422


def test_split_rejects_encrypted_pdf(client):
    response = post_split(client, make_pdf(3, encrypt_with="secret"), mode="all")
    assert response.status_code == 422
    assert "password-protected" in response.json()["detail"]


def test_split_rejects_non_pdf_upload(client):
    response = post_split(client, b"MZ not a pdf", mode="all")
    assert response.status_code == 415
