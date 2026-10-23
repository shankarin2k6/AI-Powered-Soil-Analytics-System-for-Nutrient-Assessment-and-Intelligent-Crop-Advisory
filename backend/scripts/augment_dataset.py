"""Make augmented copies of a training image folder (class sub-folders are kept).

Run from the backend folder:
    python -m scripts.augment_dataset --src ../ml/data/train --dst ../ml/data/train_aug --copies 3

Only augment the TRAINING split. Never augment validation or test images.
"""
import argparse
import random
from pathlib import Path

from PIL import Image

from app.ingestion.augment import augment_image

EXTS = {".jpg", ".jpeg", ".png"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--dst", required=True, type=Path)
    ap.add_argument("--copies", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    count = 0
    for path in sorted(args.src.rglob("*")):
        if path.suffix.lower() not in EXTS:
            continue
        out_dir = args.dst / path.relative_to(args.src).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        with Image.open(path) as im:
            for i in range(args.copies):
                augment_image(im, rng).save(out_dir / f"{path.stem}_aug{i}.jpg", quality=92)
                count += 1
    print(f"wrote {count} augmented images to {args.dst}")


if __name__ == "__main__":
    main()
