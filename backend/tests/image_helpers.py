import io

from PIL import Image


def make_image(
    fmt: str = "PNG",
    size: tuple[int, int] = (200, 100),
    mode: str = "RGB",
    orientation: int | None = None,
    color=(200, 30, 30),
) -> bytes:
    """Build a small test image, optionally tagged with an EXIF orientation."""
    image = Image.new(mode, size, color if mode in ("RGB", "RGBA") else 128)
    output = io.BytesIO()
    kwargs: dict = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = orientation
        kwargs["exif"] = exif.tobytes()
    image.save(output, format=fmt, **kwargs)
    return output.getvalue()
