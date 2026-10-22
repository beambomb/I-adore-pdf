import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.deps import get_job_store, get_settings
from app.routers import download, image_to_pdf, merge, split


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


app = FastAPI(
    title="I-adore-pdf",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.include_router(download.router)
app.include_router(merge.router)
app.include_router(split.router)
app.include_router(image_to_pdf.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
