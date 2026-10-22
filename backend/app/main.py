import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.deps import get_job_store, get_settings
from app.routers import compress, download, image_to_pdf, merge, ocr, scan, split
from app.security import PUBLIC_PATHS, RateLimiter, client_key, credentials_match
from app.static import mount_frontend

# Swagger UI loads scripts from a CDN, so the strict policy below would break it.
_DOCS_PREFIXES = ("/api/docs", "/api/openapi")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
_CONTENT_SECURITY_POLICY = (
    "default-src 'self'; img-src 'self' data: blob:; object-src 'none'; "
    "base-uri 'self'; frame-ancestors 'none'"
)


async def _cleanup_loop(interval: int) -> None:
    store = get_job_store()
    while True:
        await asyncio.sleep(interval)
        await asyncio.to_thread(store.cleanup_expired)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(_cleanup_loop(get_settings().cleanup_interval_seconds))
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    limiter = RateLimiter(settings.rate_limit_per_minute)

    app = FastAPI(
        title="I-adore-pdf",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def guard(request: Request, call_next):
        current = get_settings()
        path = request.url.path

        if current.auth_enabled and path not in PUBLIC_PATHS:
            allowed = credentials_match(
                request.headers.get("authorization"),
                current.auth_username or "",
                current.auth_password or "",
            )
            # Let CORS preflight requests through; browsers never send credentials with them.
            if not allowed and request.method != "OPTIONS":
                return JSONResponse(
                    {"detail": "Authentication required."},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="I-adore-pdf", charset="UTF-8"'},
                )

        if request.method == "POST":
            retry_after = limiter.check(client_key(request, current.trust_proxy_headers))
            if retry_after:
                return JSONResponse(
                    {"detail": "Too many requests. Please wait a moment and try again."},
                    status_code=429,
                    headers={"Retry-After": str(int(retry_after))},
                )

        response = await call_next(request)
        for name, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if not path.startswith(_DOCS_PREFIXES):
            response.headers.setdefault("Content-Security-Policy", _CONTENT_SECURITY_POLICY)
        return response

    # Added last so it is the outermost layer and answers preflight requests first.
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(download.router)
    app.include_router(merge.router)
    app.include_router(split.router)
    app.include_router(image_to_pdf.router)
    app.include_router(compress.router)
    app.include_router(scan.router)
    app.include_router(ocr.router)

    # Registered last: the catch-all frontend route must not shadow any API route.
    if settings.static_dir is not None:
        mount_frontend(app, settings.static_dir)

    return app


app = create_app()
