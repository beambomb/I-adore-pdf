from app.deps import get_job_store


def test_download_returns_file_with_name_and_type(client):
    job = get_job_store().create("merged.pdf", b"%PDF-1.7 hello", "application/pdf")
    response = client.get(f"/api/download/{job.job_id}")
    assert response.status_code == 200
    assert response.content == b"%PDF-1.7 hello"
    assert response.headers["content-type"] == "application/pdf"
    assert "merged.pdf" in response.headers["content-disposition"]


def test_download_unknown_job_is_404(client):
    response = client.get("/api/download/" + "0" * 32)
    assert response.status_code == 404


def test_download_malformed_id_is_404(client):
    response = client.get("/api/download/not-a-job")
    assert response.status_code == 404
