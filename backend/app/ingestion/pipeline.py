"""The whole ingestion pipeline in one function: bytes in, validated + processed image out.

Milestone 2 plugs the model in AFTER this function (it takes `normalized` as its input), so nothing here
needs to change when the CNN is added.
"""
from dataclasses import dataclass

from app.ingestion import preprocess
from app.ingestion.validate import ALLOWED_FORMATS, load_image


@dataclass
class ProcessedImage:
    original: bytes            # the file exactly as uploaded
    original_ext: str          # ".jpg" or ".png"
    content_type: str
    normalized: bytes          # JPEG
    corrected: bytes           # JPEG
    foreground: bytes | None   # PNG with transparent background, or None if it could not be cut reliably
    width: int                 # size of the normalized image
    height: int
    quality: dict


def process_upload(raw: bytes) -> ProcessedImage:
    img, fmt = load_image(raw)                    # raises IngestError for bad files
    content_type, ext = ALLOWED_FORMATS[fmt]

    norm = preprocess.normalize(img)
    quality = preprocess.quality_report(img, norm)
    cut = preprocess.remove_background(norm)

    return ProcessedImage(
        original=raw, original_ext=ext, content_type=content_type,
        normalized=preprocess.to_jpeg(norm),
        corrected=preprocess.to_jpeg(preprocess.color_correct(norm)),
        foreground=preprocess.to_png(cut) if cut is not None else None,
        width=norm.size[0], height=norm.size[1], quality=quality,
    )
