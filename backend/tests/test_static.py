import pytest
from fastapi.testclient import TestClient

from app import deps
from app.main import create_app


@pytest.fixture
def site(tmp_path, monkeypatch):
    """A fake frontend build, with a 'secret' file next to it that must never be served."""
    build = tmp_path / "dist"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text("<html>app shell</html>", encoding="utf-8")
    (build / "assets" / "app.js").write_text("console.log('hi')", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("top secret", encoding="utf-8")

    monkeypatch.setenv("STATIC_DIR", str(build))
    deps.get_settings.cache_clear()
    deps.get_job_store.cache_clear()
    with TestClient(create_app()) as client:
        yield client


def test_root_serves_the_app_shell(site):
    response = site.get("/")
    assert response.status_code == 200
    assert "app shell" in response.text


def test_client_side_routes_fall_back_to_index(site):
    for path in ("/merge", "/split", "/some/deep/route"):
        response = site.get(path)
        assert response.status_code == 200
        assert "app shell" in response.text


def test_real_assets_are_served_as_files(site):
    response = site.get("/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


def test_unknown_api_paths_return_404_not_the_app_shell(site):
    response = site.get("/api/nope")
    assert response.status_code == 404
    assert "app shell" not in response.text


def test_api_routes_still_win_over_the_catch_all(site):
    assert site.get("/api/health").json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    ["/../secret.txt", "/..%2Fsecret.txt", "/assets/../../secret.txt", "/%2e%2e/secret.txt"],
)
def test_path_traversal_never_leaks_files_outside_the_build(site, path):
    response = site.get(path)
    assert "top secret" not in response.text


def test_no_static_dir_means_no_frontend_routes(client):
    # Default test app has no STATIC_DIR (frontend runs on Vite in development).
    assert client.get("/merge").status_code == 404


def test_missing_build_folder_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "does-not-exist"))
    deps.get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/merge").status_code == 404
        assert client.get("/api/health").status_code == 200
