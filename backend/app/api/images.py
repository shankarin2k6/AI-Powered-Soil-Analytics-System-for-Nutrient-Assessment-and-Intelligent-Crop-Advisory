import io
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import owned_field, owned_image
from app.db import get_db
from app.ingestion.pipeline import process_upload
from app.ingestion.validate import read_upload
from app.models_db import FarmField, SoilImage
from app.schemas import ImageOut
from app.services.storage import Storage, get_storage

router = APIRouter(tags=["images"])

VARIANTS = {            # url name -> (column on SoilImage, media type)
    "original": ("original_key", None),
    "normalized": ("normalized_key", "image/jpeg"),
    "corrected": ("corrected_key", "image/jpeg"),
    "foreground": ("foreground_key", "image/png"),
}


THUMB_SIDE = 320       # longest side of the small preview used in lists (made on request, not stored)


def image_out(img: SoilImage) -> ImageOut:
    urls = {name: f"/api/v1/images/{img.id}/file?variant={name}"
            for name, (column, _) in VARIANTS.items() if getattr(img, column)}
    urls["thumb"] = f"/api/v1/images/{img.id}/file?variant=thumb"
    return ImageOut(id=img.id, field_id=img.field_id, width=img.width, height=img.height,
                    size_bytes=img.size_bytes, content_type=img.content_type,
                    quality=img.quality, urls=urls, created_at=img.created_at)


@router.post("/fields/{field_id}/images", response_model=ImageOut, status_code=201)
def upload_image(file: UploadFile = File(...), field: FarmField = Depends(owned_field),
                 db: Session = Depends(get_db), storage: Storage = Depends(get_storage)):
    """Validate, normalise and store a soil photo. Problems with the file raise IngestError (see main.py)."""
    field_id = field.id
    processed = process_upload(read_upload(file.file))

    base = f"images/{field_id}/{uuid.uuid4().hex}"
    keys = {"original_key": f"{base}/original{processed.original_ext}",
            "normalized_key": f"{base}/normalized.jpg"}
    storage.save(keys["original_key"], processed.original)
    storage.save(keys["normalized_key"], processed.normalized)
    keys["corrected_key"] = f"{base}/corrected.jpg"
    storage.save(keys["corrected_key"], processed.corrected)
    keys["foreground_key"] = None
    if processed.foreground is not None:
        keys["foreground_key"] = f"{base}/foreground.png"
        storage.save(keys["foreground_key"], processed.foreground)

    img = SoilImage(field_id=field_id, width=processed.width, height=processed.height,
                    size_bytes=len(processed.original), content_type=processed.content_type,
                    quality=processed.quality, **keys)
    db.add(img)
    db.commit()
    return image_out(img)


@router.get("/fields/{field_id}/images", response_model=list[ImageOut])
def list_images(field: FarmField = Depends(owned_field), db: Session = Depends(get_db)):
    rows = db.scalars(select(SoilImage).where(SoilImage.field_id == field.id)
                      .order_by(SoilImage.created_at.desc(), SoilImage.id.desc())).all()
    return [image_out(r) for r in rows]


@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(img: SoilImage = Depends(owned_image)):
    return image_out(img)


@router.get("/images/{image_id}/file")
def get_image_file(variant: str = Query("normalized"), img: SoilImage = Depends(owned_image),
                   storage: Storage = Depends(get_storage)):
    if variant == "thumb":                       # small preview so lists do not download 1600 px photos
        with Image.open(io.BytesIO(storage.read(img.normalized_key))) as src:
            small = src.convert("RGB")
            small.thumbnail((THUMB_SIDE, THUMB_SIDE))
        buf = io.BytesIO()
        small.save(buf, "JPEG", quality=80)
        return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})
    if variant not in VARIANTS:
        raise HTTPException(422, f"variant must be one of {sorted(VARIANTS) + ['thumb']}")
    column, media_type = VARIANTS[variant]
    key = getattr(img, column)
    if not key:
        raise HTTPException(404, f"This image has no '{variant}' version")
    media_type = media_type or img.content_type
    return Response(storage.read(key), media_type=media_type,
                    headers={"Cache-Control": "private, max-age=86400"})
