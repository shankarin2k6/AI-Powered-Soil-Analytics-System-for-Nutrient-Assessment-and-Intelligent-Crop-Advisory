"""Step 1 of the pipeline: check the upload and turn it into an upright RGB image."""
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import settings

ALLOWED_FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png")}


class IngestError(Exception):
    """A problem with the uploaded image. `key` is an i18n message key the frontend can translate."""

    def __init__(self, status_code: int, key: str, message: str):
        super().__init__(message)
        self.status_code, self.key, self.message = status_code, key, message


def read_upload(file_obj) -> bytes:
    raw = file_obj.read(settings.max_upload_bytes + 1)
    if not raw:
        raise IngestError(400, "image.empty", "The uploaded file is empty.")
    if len(raw) > settings.max_upload_bytes:
        raise IngestError(413, "image.too_large", f"Image is larger than {settings.max_upload_bytes // (1024 * 1024)} MB.")
    return raw


def load_image(raw: bytes) -> tuple[Image.Image, str]:
    """Return (upright RGB image, format name). Raises IngestError for anything unusable."""
    try:
        probe = Image.open(io.BytesIO(raw))
        probe.verify()                       # detects truncated / corrupt files
        img = Image.open(io.BytesIO(raw))    # verify() invalidates the object, so open again
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise IngestError(400, "image.not_readable", "The uploaded file is not a readable image.")

    fmt = img.format or ""
    if fmt not in ALLOWED_FORMATS:
        raise IngestError(415, "image.unsupported_format", "Only JPEG and PNG images are supported.")
    if img.size[0] * img.size[1] > settings.max_pixels:
        raise IngestError(413, "image.too_many_pixels", "Image has too many pixels.")

    try:
        img = ImageOps.exif_transpose(img).convert("RGB")   # phones store rotation in EXIF
    except (OSError, ValueError):
        raise IngestError(400, "image.not_readable", "The uploaded file is not a readable image.")
    if min(img.size) < settings.min_side_px:
        raise IngestError(400, "image.too_small", f"Image is too small (minimum {settings.min_side_px}px on the short side).")
    return img, fmt
