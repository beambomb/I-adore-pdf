import re
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile

PDF = "pdf"
JPEG = "jpeg"
PNG = "png"
WEBP = "webp"

IMAGE_TYPES = frozenset({JPEG, PNG, WEBP})

_CHUNK = 1024 * 1024
_UNSAFE = re.compile(r"[^A-Za-z0-9._ -]")


def sniff_type(head: bytes) -> str | None:
    """Detect the real file type from magic bytes (the extension is never trusted)."""
    if head.startswith(b"%PDF-"):
        return PDF
    if head.startswith(b"\xff\xd8\xff"):
        return JPEG
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return PNG
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return WEBP
    return None


def sanitize_filename(name: str | None, fallback: str = "file") -> str:
    """Strip directories and unsafe characters from a client-supplied filename."""
    base = (name or "").replace("\\", "/").split("/")[-1].strip()
    base = _UNSAFE.sub("_", base).lstrip(".")
    return base[:120] or fallback


@dataclass(frozen=True)
class UploadedFile:
    filename: str
    kind: str
    data: bytes


async def read_upload(upload: UploadFile, allowed: frozenset[str], max_bytes: int) -> UploadedFile:
    """Read an upload fully into memory while enforcing size and real-type limits."""
    filename = sanitize_filename(upload.filename)
    chunks: list[bytes] = []
    total = 0
    while chunk := await upload.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"'{filename}' is larger than the {max_bytes // (1024 * 1024)} MB limit.",
            )
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise HTTPException(status_code=400, detail=f"'{filename}' is empty.")
    kind = sniff_type(data[:16])
    if kind is None or kind not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"'{filename}' is not a supported file type.",
        )
    return UploadedFile(filename=filename, kind=kind, data=data)


async def read_uploads(
    uploads: list[UploadFile],
    allowed: frozenset[str],
    max_file_bytes: int,
    max_total_bytes: int,
) -> list[UploadedFile]:
    """Read several uploads, enforcing the per-file and combined size limits."""
    if not uploads:
        raise HTTPException(status_code=400, detail="No files were uploaded.")
    files: list[UploadedFile] = []
    total = 0
    for upload in uploads:
        item = await read_upload(upload, allowed, max_file_bytes)
        total += len(item.data)
        if total > max_total_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Combined upload exceeds the {max_total_bytes // (1024 * 1024)} MB limit.",
            )
        files.append(item)
    return files
