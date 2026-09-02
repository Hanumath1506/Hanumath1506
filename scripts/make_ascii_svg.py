#!/usr/bin/env python3
"""
make_ascii_svg.py — convert a prepped portrait photo into a monochrome ASCII-art
SVG. Each row wipes in left-to-right via a clip-path <animate>, rows are
staggered top-to-bottom, and the whole animation plays exactly once (no loop).

Usage:
    python scripts/make_ascii_svg.py data/photo_prepped.png -o assets/ascii-portrait.svg

Requires: pillow
    pip install pillow
"""
import argparse
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

# Density ramp: index 0 = lightest (background), last = darkest (subject detail).
RAMP = " .'`^,:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def image_to_ascii_grid(img: Image.Image, cols: int, rows: int) -> list[str]:
    gray = img.convert("L").resize((cols, rows), Image.LANCZOS)
    pixels = list(gray.getdata())
    ramp_len = len(RAMP) - 1
    lines = []
    for r in range(rows):
        row_pixels = pixels[r * cols : (r + 1) * cols]
        # invert: bright (background/white) -> ramp[0] (space), dark -> dense glyph
        chars = "".join(RAMP[ramp_len - int(p / 255 * ramp_len)] for p in row_pixels)
        lines.append(chars)
    return lines


def build_svg(
    grid: list[str],
    cell_w: float,
    cell_h: float,
    font_size: float,
    fg: str,
    bg: str,
    row_stagger: float,
    row_duration: float,
) -> str:
    cols = len(grid[0]) if grid else 0
    rows = len(grid)
    width = cols * cell_w
    height = rows * cell_h

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Animated ASCII portrait" '
        f'font-family="SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" '
        f'font-size="{font_size:.1f}" fill="{fg}">'
    )
    parts.append(f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" fill="{bg}"/>')

    for i, row in enumerate(grid):
        y = (i + 1) * cell_h - (cell_h - font_size) / 2 - font_size * 0.2
        clip_id = f"rowclip{i}"
        begin = i * row_stagger
        safe_row = escape(row)
        parts.append(f'<clipPath id="{clip_id}">')
        parts.append(f'<rect x="0" y="{i * cell_h:.2f}" width="0" height="{cell_h:.2f}">')
        parts.append(
            f'<animate attributeName="width" from="0" to="{width:.1f}" '
            f'begin="{begin:.3f}s" dur="{row_duration:.3f}s" fill="freeze" '
            f'calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
        )
        parts.append('</rect>')
        parts.append('</clipPath>')
        parts.append(f'<g clip-path="url(#{clip_id})">')
        parts.append(
            f'<text x="0" y="{y:.2f}" '
            f'textLength="{width:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'xml:space="preserve">{safe_row}</text>'
        )
        parts.append('</g>')

    parts.append('</svg>')
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="prepped portrait PNG (white background)")
    parser.add_argument("-o", "--output", type=Path, default=Path("assets/ascii-portrait.svg"))
    parser.add_argument("--cols", type=int, default=100)
    parser.add_argument("--rows", type=int, default=53)
    parser.add_argument("--cell-w", type=float, default=7.2, help="pixel width per character cell")
    parser.add_argument("--cell-h", type=float, default=13.5, help="pixel height per character cell")
    parser.add_argument("--font-size", type=float, default=13.0)
    parser.add_argument("--fg", type=str, default="#39d353", help="foreground (glyph) color")
    parser.add_argument("--bg", type=str, default="#0d1117", help="background color")
    parser.add_argument("--row-stagger", type=float, default=0.045, help="seconds between row starts")
    parser.add_argument("--row-duration", type=float, default=0.55, help="seconds for one row's wipe")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"error: input not found: {args.input}")

    img = Image.open(args.input)
    grid = image_to_ascii_grid(img, args.cols, args.rows)
    svg = build_svg(
        grid,
        cell_w=args.cell_w,
        cell_h=args.cell_h,
        font_size=args.font_size,
        fg=args.fg,
        bg=args.bg,
        row_stagger=args.row_stagger,
        row_duration=args.row_duration,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(f"done -> {args.output} ({args.cols}x{args.rows} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
