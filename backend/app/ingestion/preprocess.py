"""Step 2: normalise the image, check its quality, and make the OpenCV variants.

Three files are produced from every upload:

  normalized  resized JPEG with the original colours. THIS is what the models should use (Milestone 2),
              because they were trained on unmodified colours and soil colour is a key clue
              (red vs yellow vs black soil).
  corrected   gray-world white balance + local contrast. Looks better under odd lighting.
              For display and later experiments only; test it before feeding it to the CNN.
  foreground  the soil with the background (hand, sky, shoes) cut out, as a transparent PNG.

All thresholds are plain constants below so they are easy to tune.
"""
import io

import cv2
import numpy as np
from PIL import Image

from app.config import settings

# ---- quality thresholds (tune with real phone photos) ----
BLUR_MIN = 40.0         # variance of the Laplacian on a 512px grayscale copy; lower = blurrier
DARK_MEAN_MAX = 50      # mean gray level (0-255) below this = too dark
BRIGHT_MEAN_MIN = 215   # mean gray level above this = too bright
LOW_RES_SIDE = 224      # shorter side below this = low resolution (the CNN looks at 224px)


def normalize(img: Image.Image) -> Image.Image:
    """Limit the longest side. Colours are not changed."""
    out = img.copy()
    out.thumbnail((settings.normalized_max_side, settings.normalized_max_side), Image.LANCZOS)
    return out


def to_jpeg(img: Image.Image, quality: int = 90) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _gray_small(img: Image.Image, side: int = 512) -> np.ndarray:
    small = img.copy()
    small.thumbnail((side, side))
    return cv2.cvtColor(np.asarray(small), cv2.COLOR_RGB2GRAY)


def quality_report(original: Image.Image, normalized: Image.Image) -> dict:
    """Scores plus a list of warning keys. Warnings never block an upload; the app shows them as advice."""
    gray = _gray_small(normalized)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())

    warnings = []
    if blur < BLUR_MIN:
        warnings.append("image.blurry")
    if brightness < DARK_MEAN_MAX:
        warnings.append("image.too_dark")
    elif brightness > BRIGHT_MEAN_MIN:
        warnings.append("image.too_bright")
    if min(original.size) < LOW_RES_SIDE:
        warnings.append("image.low_resolution")

    return {"blur_score": round(blur, 1), "brightness": round(brightness, 1),
            "original_width": original.size[0], "original_height": original.size[1],
            "warnings": warnings}


def color_correct(img: Image.Image) -> Image.Image:
    """Gray-world white balance (gains limited so colours stay believable), then CLAHE on lightness."""
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    means = arr.reshape(-1, 3).mean(axis=0)
    gains = np.clip(means.mean() / np.maximum(means, 1e-6), 0.8, 1.25)
    balanced = np.clip(arr * gains, 0, 255).astype(np.uint8)

    lab = cv2.cvtColor(balanced, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[..., 0] = clahe.apply(lab[..., 0])
    return Image.fromarray(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB))


def remove_background(img: Image.Image) -> Image.Image | None:
    """Cut the soil out with GrabCut, starting from the centre of the photo.

    Returns an RGBA image, or None when the result looks unreliable (almost nothing or everything was
    selected). That is common for close-up soil shots that fill the frame, where there is no background.
    """
    rgb = np.asarray(img.convert("RGB"))
    h, w = rgb.shape[:2]
    scale = 400 / max(h, w)
    small = cv2.resize(rgb, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA)
    sh, sw = small.shape[:2]

    mask = np.zeros((sh, sw), np.uint8)
    rect = (int(sw * 0.08), int(sh * 0.08), int(sw * 0.84), int(sh * 0.84))
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(cv2.cvtColor(small, cv2.COLOR_RGB2BGR), mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return None

    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    share = float((fg > 0).mean())
    if share < 0.15 or share > 0.97:
        return None

    alpha = cv2.resize(fg, (w, h), interpolation=cv2.INTER_LINEAR)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 2)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
