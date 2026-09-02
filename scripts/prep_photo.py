#!/usr/bin/env python3
"""
prep_photo.py — remove the background from a source photo, boost local contrast
with CLAHE, and composite the result on a flat white background.

Usage:
    python scripts/prep_photo.py <input_photo> [-o output.png] [--size WxH]

Requires: rembg, pillow, numpy, opencv-python-headless
    pip install rembg pillow numpy opencv-python-headless onnxruntime
"""
import argparse
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def remove_background(image_bytes: bytes) -> Image.Image:
    from rembg import remove

    out_bytes = remove(image_bytes)
    return Image.open(io.BytesIO(out_bytes)).convert("RGBA")


def apply_clahe(rgba: Image.Image) -> Image.Image:
    import cv2

    rgb = np.array(rgba.convert("RGB"))
    alpha = np.array(rgba.getchannel("A"))

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)

    lab = cv2.merge((l, a, b))
    rgb_boosted = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    boosted = Image.fromarray(rgb_boosted).convert("RGBA")
    boosted.putalpha(Image.fromarray(alpha))
    return boosted


def composite_on_white(rgba: Image.Image) -> Image.Image:
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    white_bg.alpha_composite(rgba)
    return white_bg.convert("RGB")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="source photo path")
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("data/photo_prepped.png"),
        help="output PNG path (default: data/photo_prepped.png)",
    )
    parser.add_argument(
        "--size", type=str, default=None,
        help="optional resize as WxH, e.g. 600x800",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"[1/3] removing background from {args.input} ...")
    source_bytes = args.input.read_bytes()
    cutout = remove_background(source_bytes)

    print("[2/3] applying CLAHE contrast boost ...")
    boosted = apply_clahe(cutout)

    print("[3/3] compositing on white background ...")
    final = composite_on_white(boosted)

    if args.size:
        w, h = (int(v) for v in args.size.lower().split("x"))
        final = final.resize((w, h), Image.LANCZOS)

    final.save(args.output)
    print(f"done -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
