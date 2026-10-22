import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.services.pdf_errors import PdfProcessingError, open_pdf

Level = Literal["low", "medium", "high"]

# "low" keeps the most quality (smallest saving); "high" shrinks the most.
PRESETS: dict[str, str] = {
    "low": "/printer",
    "medium": "/ebook",
    "high": "/screen",
}

GS_TIMEOUT_SECONDS = 180


class GhostscriptUnavailable(RuntimeError):
    """Ghostscript is not installed on this machine."""


@dataclass(frozen=True)
class CompressionResult:
    data: bytes
    original_size: int
    compressed_size: int
    # False when Ghostscript could not make the file smaller and the original was kept.
    reduced: bool

    @property
    def saved_percent(self) -> float:
        if self.original_size == 0:
            return 0.0
        return round((1 - self.compressed_size / self.original_size) * 100, 1)


def find_ghostscript() -> str | None:
    for name in ("gs", "gswin64c", "gswin32c"):
        path = shutil.which(name)
        if path:
            return path
    return None


def compress_pdf(data: bytes, name: str, level: Level) -> CompressionResult:
    """Shrink a PDF with Ghostscript. Returns the original if it cannot be made smaller."""
    if level not in PRESETS:
        raise PdfProcessingError("Choose a compression level: low, medium or high.")
    # Validates the file and rejects encrypted or corrupted PDFs with a readable message.
    open_pdf(data, name)

    gs = find_ghostscript()
    if gs is None:
        raise GhostscriptUnavailable("Ghostscript is not installed.")

    with tempfile.TemporaryDirectory(prefix="compress-") as tmp:
        source = Path(tmp) / "input.pdf"
        target = Path(tmp) / "output.pdf"
        source.write_bytes(data)
        # Arguments are passed as a list (no shell) so file names can never be interpreted.
        command = [
            gs,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={PRESETS[level]}",
            "-dNOPAUSE",
            "-dBATCH",
            "-dQUIET",
            "-dSAFER",
            f"-sOutputFile={target}",
            str(source),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                timeout=GS_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfProcessingError(
                f"Compressing '{name}' took too long. Try a smaller file."
            ) from exc
        if completed.returncode != 0 or not target.is_file():
            raise PdfProcessingError(f"Could not compress '{name}'. The file may be damaged.")
        output = target.read_bytes()

    if len(output) >= len(data):
        return CompressionResult(data, len(data), len(data), reduced=False)
    return CompressionResult(output, len(data), len(output), reduced=True)
