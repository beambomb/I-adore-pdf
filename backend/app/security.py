import base64
import binascii
import secrets
import time
from collections import defaultdict, deque

from starlette.requests import Request

# Paths that must stay reachable without credentials (container health checks).
PUBLIC_PATHS = frozenset({"/api/health"})


def credentials_match(header: str | None, username: str, password: str) -> bool:
    """Check an HTTP Basic Authorization header in constant time."""
    if not header or not header.lower().startswith("basic "):
        return False
    try:
        decoded = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return False
    given_user, sep, given_password = decoded.partition(":")
    if not sep:
        return False
    # Compare both fields without short-circuiting so timing does not reveal which was wrong.
    user_ok = secrets.compare_digest(given_user.encode(), username.encode())
    password_ok = secrets.compare_digest(given_password.encode(), password.encode())
    return user_ok and password_ok


def client_key(request: Request, trust_proxy_headers: bool) -> str:
    """Identify the caller for rate limiting."""
    if trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "unknown"


class RateLimiter:
    """Sliding-window limiter kept in memory (one instance per process)."""

    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float | None = None) -> float:
        """Record a request. Returns 0 if allowed, otherwise seconds until a retry may succeed."""
        if self.limit <= 0:
            return 0.0
        current = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and current - hits[0] >= self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return max(self.window - (current - hits[0]), 1.0)
        hits.append(current)
        # Drop idle keys occasionally so the table cannot grow without bound.
        if len(self._hits) > 10_000:
            for stale in [k for k, v in self._hits.items() if not v]:
                del self._hits[stale]
        return 0.0
