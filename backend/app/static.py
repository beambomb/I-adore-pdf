from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def mount_frontend(app: FastAPI, directory: Path) -> bool:
    """Serve the built React app. Returns False when there is no build to serve.

    Real files (JS, CSS, icons) are returned as-is. Any other non-API path returns
    index.html so client-side routes such as /merge work on refresh.
    """
    root = directory.resolve()
    index = root / "index.html"
    if not index.is_file():
        return False

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found.")
        candidate = (root / path).resolve()
        # Only serve files that really live inside the build folder (blocks ../ tricks).
        if path and candidate.is_file() and candidate.is_relative_to(root):
            return FileResponse(candidate)
        return FileResponse(index)

    return True
