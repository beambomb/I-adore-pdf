import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.services.pdf_errors import PdfProcessingError

# Refuse absurdly large images (decompression bombs) instead of exhausting memory.
MAX_PIXELS = 100_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

_JPEG_QUALITY = 95
_EXIF_ORIENTATION = 0x0112


def _flatten_to_rgb(image: Image.Image) -> Image.Image:
    """Remove transparency by compositing onto white (PDFs from img2pdf cannot hold alpha)."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _encode(image: Image.Image, fmt: str) -> bytes:
    output = io.BytesIO()
    if fmt == "JPEG":
        image.save(output, format="JPEG", quality=_JPEG_QUALITY, subsampling=0)
    else:
        image.save(output, format="PNG")
    return output.getvalue()


def normalize_image(data: bytes, name: str) -> bytes:
    """Return image bytes that img2pdf can embed, with EXIF rotation applied.

    JPEG and plain PNG files without rotation are passed through untouched so
    the PDF keeps the original quality.
    """
    try:
        with Image.open(io.BytesIO(data)) as source:
            source.load()
            fmt = source.format
            orientation = source.getexif().get(_EXIF_ORIENTATION, 1)
            has_alpha = source.mode in ("RGBA", "LA") or (
                source.mode == "P" and "transparency" in source.info
            )

            if fmt == "JPEG" and orientation == 1 and source.mode in ("RGB", "L"):
                return data
            if fmt == "PNG" and not has_alpha and source.mode in ("RGB", "L", "P"):
                if orientation == 1:
                    return data

            upright = ImageOps.exif_transpose(source)
            if fmt == "PNG" and not has_alpha:
                return _encode(upright.convert("RGB"), "PNG")
            return _encode(_flatten_to_rgb(upright), "JPEG")
    except Image.DecompressionBombError as exc:
        raise PdfProcessingError(f"'{name}' has too many pixels to process safely.") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise PdfProcessingError(f"'{name}' is corrupted or not a valid image.") from exc
