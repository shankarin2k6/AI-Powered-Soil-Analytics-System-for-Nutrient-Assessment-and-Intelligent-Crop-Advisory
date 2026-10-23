"""Unit tests for the image steps and the augmentation (no web server involved)."""
import random

import numpy as np
from PIL import Image

from app.ingestion import preprocess
from app.ingestion.augment import augment_image


def noisy(color, size=(300, 200), sigma=20):
    rng = np.random.default_rng(3)
    arr = np.clip(np.array(color, np.float32) + rng.normal(0, sigma, (size[1], size[0], 3)), 0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def test_color_correct_reduces_a_strong_colour_cast_but_not_completely():
    img = noisy((200, 120, 60))                       # warm / orange cast
    before = np.asarray(img).reshape(-1, 3).mean(0)
    after = np.asarray(preprocess.color_correct(img)).reshape(-1, 3).mean(0)
    assert (after.max() - after.min()) < (before.max() - before.min())
    assert after[0] > after[2]                         # red soil is still reddish: gains are capped


def test_normalize_keeps_aspect_ratio_and_never_enlarges():
    big = Image.new("RGB", (4000, 1000))
    assert preprocess.normalize(big).size == (1600, 400)
    small = Image.new("RGB", (300, 200))
    assert preprocess.normalize(small).size == (300, 200)


def test_remove_background_returns_none_for_a_full_frame_close_up():
    assert preprocess.remove_background(noisy((120, 80, 50), (400, 300))) is None


def test_augment_keeps_size_and_colour_family():
    img = noisy((170, 90, 60), (256, 256))
    mean_before = np.asarray(img).reshape(-1, 3).mean(0)
    for seed in range(20):
        out = augment_image(img, random.Random(seed))
        assert out.size == img.size and out.mode == "RGB"
        m = np.asarray(out).reshape(-1, 3).mean(0)
        assert m[0] > m[2]                             # still red-brown, hue was not shifted
        assert np.abs(m - mean_before).max() < 60      # only mild brightness change


def test_augment_is_repeatable_for_same_seed():
    img = noisy((170, 90, 60), (128, 128))
    a, b = augment_image(img, random.Random(7)), augment_image(img, random.Random(7))
    assert np.array_equal(np.asarray(a), np.asarray(b))
