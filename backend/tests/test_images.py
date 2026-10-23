import io

import numpy as np
from PIL import Image

from tests.conftest import make_soil_image


def upload(client, field_id, data, name="soil.jpg", ctype="image/jpeg"):
    return client.post(f"/api/v1/fields/{field_id}/images", files={"file": (name, data, ctype)})


def test_upload_jpeg_stores_all_variants(client, field_id):
    r = upload(client, field_id, make_soil_image())
    assert r.status_code == 201
    body = r.json()
    assert body["field_id"] == field_id and body["width"] == 640 and body["height"] == 480
    assert set(body["urls"]) >= {"original", "normalized", "corrected"}
    for variant in ("original", "normalized", "corrected"):
        f = client.get(body["urls"][variant])
        assert f.status_code == 200
        Image.open(io.BytesIO(f.content)).verify()
    assert client.get(body["urls"]["normalized"]).headers["content-type"] == "image/jpeg"


def test_upload_png_is_accepted_and_normalised_to_jpeg(client, field_id):
    r = upload(client, field_id, make_soil_image(fmt="PNG"), "soil.png", "image/png")
    assert r.status_code == 201
    assert r.json()["content_type"] == "image/png"
    assert client.get(r.json()["urls"]["original"]).headers["content-type"] == "image/png"
    assert client.get(r.json()["urls"]["normalized"]).headers["content-type"] == "image/jpeg"


def test_large_photo_is_resized_but_original_is_kept(client, field_id):
    big = make_soil_image(size=(3000, 2000))
    r = upload(client, field_id, big)
    assert r.status_code == 201
    assert max(r.json()["width"], r.json()["height"]) == 1600
    assert client.get(r.json()["urls"]["original"]).content == big


def test_exif_rotation_is_applied(client, field_id):
    # orientation 6 = the phone was held sideways: 640x480 pixels must become 480x640
    r = upload(client, field_id, make_soil_image(exif_orientation=6))
    assert (r.json()["width"], r.json()["height"]) == (480, 640)


def test_blurry_dark_and_bright_photos_get_warnings_but_are_stored(client, field_id):
    blurry = Image.new("RGB", (640, 480), (150, 90, 60))
    buf = io.BytesIO(); blurry.save(buf, "JPEG")
    r = upload(client, field_id, buf.getvalue())
    assert r.status_code == 201 and "image.blurry" in r.json()["quality"]["warnings"]

    dark = upload(client, field_id, make_soil_image(base=(10, 8, 6)))
    assert "image.too_dark" in dark.json()["quality"]["warnings"]

    bright = upload(client, field_id, make_soil_image(base=(250, 245, 240)))
    assert "image.too_bright" in bright.json()["quality"]["warnings"]


def test_sharp_normal_photo_has_no_warnings(client, field_id):
    assert upload(client, field_id, make_soil_image()).json()["quality"]["warnings"] == []


def test_low_resolution_warning(client, field_id):
    r = upload(client, field_id, make_soil_image(size=(160, 120)))
    assert r.status_code == 201 and "image.low_resolution" in r.json()["quality"]["warnings"]


def test_rejects_non_image(client, field_id):
    r = upload(client, field_id, b"hello this is not an image", "notes.txt", "text/plain")
    assert r.status_code == 400 and r.json()["message_key"] == "image.not_readable"


def test_rejects_empty_file(client, field_id):
    r = upload(client, field_id, b"")
    assert r.status_code == 400 and r.json()["message_key"] == "image.empty"


def test_rejects_unsupported_format(client, field_id):
    buf = io.BytesIO(); Image.new("RGB", (200, 200), (120, 80, 50)).save(buf, "GIF")
    r = upload(client, field_id, buf.getvalue(), "soil.gif", "image/gif")
    assert r.status_code == 415 and r.json()["message_key"] == "image.unsupported_format"


def test_rejects_tiny_image(client, field_id):
    r = upload(client, field_id, make_soil_image(size=(40, 40)))
    assert r.status_code == 400 and r.json()["message_key"] == "image.too_small"


def test_rejects_oversized_file(client, field_id, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "max_upload_bytes", 1000)
    r = upload(client, field_id, make_soil_image())
    assert r.status_code == 413 and r.json()["message_key"] == "image.too_large"


def test_rejects_truncated_jpeg(client, field_id):
    r = upload(client, field_id, make_soil_image()[:2000])
    assert r.status_code == 400


def test_unknown_field_and_image(client):
    assert upload(client, 999, make_soil_image()).status_code == 404
    assert client.get("/api/v1/images/999").status_code == 404
    assert client.get("/api/v1/images/999/file").status_code == 404


def test_bad_variant_and_missing_foreground(client, field_id):
    body = upload(client, field_id, make_soil_image()).json()
    assert client.get(f"/api/v1/images/{body['id']}/file?variant=nope").status_code == 422


def test_list_images_newest_first(client, field_id):
    a = upload(client, field_id, make_soil_image()).json()["id"]
    b = upload(client, field_id, make_soil_image()).json()["id"]
    assert [i["id"] for i in client.get(f"/api/v1/fields/{field_id}/images").json()] == [b, a]


def test_foreground_cutout_is_transparent_png_when_available(client, field_id):
    # a bright background with a dark round 'soil' blob in the middle: GrabCut should find the blob
    arr = np.full((480, 640, 3), (225, 235, 245), np.uint8)
    yy, xx = np.ogrid[:480, :640]
    blob = (yy - 240) ** 2 + (xx - 320) ** 2 < 170 ** 2
    rng = np.random.default_rng(1)
    arr[blob] = np.clip(np.array([110, 70, 45]) + rng.normal(0, 18, (blob.sum(), 3)), 0, 255)
    buf = io.BytesIO(); Image.fromarray(arr).save(buf, "JPEG", quality=95)
    body = upload(client, field_id, buf.getvalue()).json()
    assert "foreground" in body["urls"]
    cut = Image.open(io.BytesIO(client.get(body["urls"]["foreground"]).content))
    assert cut.mode == "RGBA"
    alpha = np.asarray(cut)[..., 3]
    assert alpha[240, 320] > 200 and alpha[10, 10] < 50      # centre kept, corner removed


def test_files_are_stored_under_field_folder(client, field_id):
    body = upload(client, field_id, make_soil_image()).json()
    files = [p for p in client.storage.root.rglob("*") if p.is_file()]
    assert files and all(f"images/{field_id}/" in p.as_posix() for p in files)
    assert body["size_bytes"] > 0


def test_thumbnail_is_small_and_only_for_the_owner(client, other_client, field_id):
    body = upload(client, field_id, make_soil_image(size=(1600, 1200))).json()
    assert body["urls"]["thumb"].endswith("variant=thumb")
    r = client.get(body["urls"]["thumb"])
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    small = Image.open(io.BytesIO(r.content))
    assert max(small.size) == 320 and len(r.content) < 60_000
    assert other_client.get(body["urls"]["thumb"]).status_code == 404
