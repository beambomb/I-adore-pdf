import base64

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.main import create_app
from app.security import RateLimiter, credentials_match
from tests.pdf_helpers import make_pdf


def basic(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def build_client(monkeypatch, **env: str) -> TestClient:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    deps.get_settings.cache_clear()
    deps.get_job_store.cache_clear()
    return TestClient(create_app())


# --- credentials_match ---------------------------------------------------------------


def test_credentials_match_accepts_the_right_login():
    assert credentials_match(basic("me", "s3cret")["Authorization"], "me", "s3cret")


@pytest.mark.parametrize(
    "header",
    [None, "", "Bearer abc", "Basic !!!notbase64", "Basic " + base64.b64encode(b"nocolon").decode()],
)
def test_credentials_match_rejects_malformed_headers(header):
    assert not credentials_match(header, "me", "s3cret")


def test_credentials_match_rejects_wrong_user_or_password():
    assert not credentials_match(basic("me", "wrong")["Authorization"], "me", "s3cret")
    assert not credentials_match(basic("you", "s3cret")["Authorization"], "me", "s3cret")


def test_password_may_contain_colons():
    assert credentials_match(basic("me", "a:b:c")["Authorization"], "me", "a:b:c")


# --- authentication -------------------------------------------------------------------


def test_auth_is_off_by_default(client):
    assert client.get("/api/docs").status_code == 200


def test_auth_blocks_requests_without_credentials(monkeypatch):
    with build_client(monkeypatch, AUTH_USERNAME="me", AUTH_PASSWORD="s3cret") as client:
        response = client.post("/api/merge")
        assert response.status_code == 401
        assert response.headers["www-authenticate"].startswith("Basic")
        assert client.get("/api/download/" + "0" * 32).status_code == 401


def test_auth_rejects_wrong_password_and_accepts_right_one(monkeypatch):
    with build_client(monkeypatch, AUTH_USERNAME="me", AUTH_PASSWORD="s3cret") as client:
        assert client.get("/api/download/" + "0" * 32, headers=basic("me", "nope")).status_code == 401
        # Authenticated request reaches the app (job does not exist -> 404, not 401).
        assert client.get("/api/download/" + "0" * 32, headers=basic("me", "s3cret")).status_code == 404


def test_health_stays_public_for_container_health_checks(monkeypatch):
    with build_client(monkeypatch, AUTH_USERNAME="me", AUTH_PASSWORD="s3cret") as client:
        assert client.get("/api/health").status_code == 200


def test_half_configured_auth_refuses_to_start(monkeypatch):
    monkeypatch.setenv("AUTH_USERNAME", "me")
    deps.get_settings.cache_clear()
    with pytest.raises(ValueError, match="AUTH_USERNAME and AUTH_PASSWORD"):
        create_app()


# --- rate limiting --------------------------------------------------------------------


def test_rate_limiter_blocks_after_the_limit_and_recovers():
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.check("a", now=0) == 0
    assert limiter.check("a", now=1) == 0
    assert limiter.check("a", now=2) > 0  # third request in the window
    assert limiter.check("a", now=61) == 0  # first hit has expired


def test_rate_limiter_tracks_clients_separately():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.check("a", now=0) == 0
    assert limiter.check("b", now=0) == 0
    assert limiter.check("a", now=1) > 0


def test_rate_limiter_with_zero_limit_is_disabled():
    limiter = RateLimiter(limit=0)
    assert all(limiter.check("a", now=i) == 0 for i in range(100))


def test_post_requests_are_limited_with_retry_after(monkeypatch):
    with build_client(monkeypatch, RATE_LIMIT_PER_MINUTE="2") as client:
        for _ in range(2):
            assert client.post("/api/merge").status_code != 429
        blocked = client.post("/api/merge")
        assert blocked.status_code == 429
        assert int(blocked.headers["retry-after"]) >= 1


def test_get_requests_are_not_rate_limited(monkeypatch):
    with build_client(monkeypatch, RATE_LIMIT_PER_MINUTE="1") as client:
        assert all(client.get("/api/health").status_code == 200 for _ in range(5))


def test_proxy_header_is_only_trusted_when_enabled(monkeypatch):
    with build_client(monkeypatch, RATE_LIMIT_PER_MINUTE="1") as client:
        client.post("/api/merge", headers={"X-Forwarded-For": "1.1.1.1"})
        # Header ignored: both requests count against the same direct client.
        assert client.post("/api/merge", headers={"X-Forwarded-For": "2.2.2.2"}).status_code == 429

    with build_client(monkeypatch, RATE_LIMIT_PER_MINUTE="1", TRUST_PROXY_HEADERS="true") as client:
        client.post("/api/merge", headers={"X-Forwarded-For": "1.1.1.1"})
        assert client.post("/api/merge", headers={"X-Forwarded-For": "2.2.2.2"}).status_code != 429
        assert client.post("/api/merge", headers={"X-Forwarded-For": "1.1.1.1"}).status_code == 429


def test_invalid_rate_limit_value_is_rejected(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "-5")
    deps.get_settings.cache_clear()
    with pytest.raises(ValueError, match="RATE_LIMIT_PER_MINUTE"):
        create_app()


# --- headers and CORS -----------------------------------------------------------------


def test_security_headers_are_set(client):
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_api_docs_are_exempt_from_the_strict_csp(client):
    assert "content-security-policy" not in client.get("/api/docs").headers


def test_cors_is_closed_by_default(client):
    response = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_cors_allows_only_configured_origins(monkeypatch):
    with build_client(monkeypatch, CORS_ORIGINS="https://app.example") as client:
        allowed = client.get("/api/health", headers={"Origin": "https://app.example"})
        denied = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert allowed.headers["access-control-allow-origin"] == "https://app.example"
        assert "access-control-allow-origin" not in denied.headers


def test_cors_preflight_works_even_when_auth_is_enabled(monkeypatch):
    with build_client(
        monkeypatch, CORS_ORIGINS="https://app.example", AUTH_USERNAME="me", AUTH_PASSWORD="s3cret"
    ) as client:
        response = client.options(
            "/api/merge",
            headers={
                "Origin": "https://app.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert response.status_code == 200


def test_normal_requests_still_work_end_to_end_with_all_protections_on(monkeypatch):
    env = dict(AUTH_USERNAME="me", AUTH_PASSWORD="s3cret", RATE_LIMIT_PER_MINUTE="10")
    with build_client(monkeypatch, **env) as client:
        response = client.post(
            "/api/merge",
            headers=basic("me", "s3cret"),
            files=[
                ("files", ("a.pdf", make_pdf(1), "application/pdf")),
                ("files", ("b.pdf", make_pdf(1), "application/pdf")),
            ],
        )
        assert response.status_code == 200
