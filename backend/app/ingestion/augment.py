"""Feature-preserving augmentation for TRAINING (not used by the API).

"Feature-preserving" here means: no hue or saturation shifts and no strong colour changes, because soil
colour is the main clue for the soil class. Only geometry and mild lighting / sharpness changes are used.
"""
import random

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def augment_image(img: Image.Image, rng: random.Random) -> Image.Image:
    img = img.convert("RGB")

    if rng.random() < 0.5:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if rng.random() < 0.5:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    img = img.rotate(rng.choice([0, 90, 180, 270]) + rng.uniform(-10, 10), resample=Image.BICUBIC, expand=False)

    # random crop that keeps 75-100% of the area, then back to the original size
    w, h = img.size
    scale = rng.uniform(0.75, 1.0) ** 0.5
    cw, ch = int(w * scale), int(h * scale)
    x, y = rng.randint(0, w - cw), rng.randint(0, h - ch)
    img = img.crop((x, y, x + cw, y + ch)).resize((w, h), Image.BICUBIC)

    # mild lighting changes (phones, shade, midday sun)
    img = ImageEnhance.Brightness(img).enhance(rng.uniform(0.8, 1.2))
    img = ImageEnhance.Contrast(img).enhance(rng.uniform(0.85, 1.15))

    if rng.random() < 0.3:                                    # slight blur, like a shaky hand
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 1.0)))
    if rng.random() < 0.3:                                    # sensor noise
        arr = np.asarray(img).astype(np.float32)
        arr += np.random.default_rng(rng.randint(0, 2**31)).normal(0, 4, arr.shape)
        img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return img
