#!/usr/bin/env python3
"""
make_info_card.py — render a neofetch-style terminal panel (role, stack,
highlights) as a self-contained animated SVG. Lines fade + slide in on a
stagger via SMIL <animate>/<animateTransform>, no CSS <style> or <script>.

Usage:
    python scripts/make_info_card.py -o assets/info-card.svg
    python scripts/make_info_card.py --data data/info_card.json -o assets/info-card.svg
"""
import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

DEFAULT_DATA = {
    "user": "hanumath",
    "host": "github",
    "fields": [
        {"label": "Role", "value": "Software Engineer"},
        {"label": "Stack", "value": "Python, TypeScript, Go, SQL"},
        {"label": "Tools", "value": "Docker, AWS, Postgres, Git"},
        {"label": "Focus", "value": "Backend systems & developer tooling"},
        {"label": "Highlights", "value": "Open source contributor"},
        {"label": "Highlights", "value": "Shipped production ML pipelines"},
        {"label": "Highlights", "value": "Enjoys clean, readable code"},
    ],
}

PALETTE = {
    "bg": "#0d1117",
    "border": "#30363d",
    "prompt": "#39d353",
    "label": "#58a6ff",
    "value": "#c9d1d9",
    "muted": "#8b949e",
    "accent": "#f0883e",
}


def load_data(path: Path | None) -> dict:
    if path is None:
        return DEFAULT_DATA
    return json.loads(path.read_text(encoding="utf-8"))


def build_svg(
    data: dict,
    width: float,
    line_height: float,
    font_size: float,
    pad: float,
    stagger: float,
    duration: float,
) -> str:
    fields = data.get("fields", [])
    user = data.get("user", "user")
    host = data.get("host", "host")

    header_lines = 2  # "user@host" + separator rule
    total_lines = header_lines + len(fields) + 1  # +1 bottom padding line
    height = pad * 2 + total_lines * line_height

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Profile info card" '
        f'font-family="SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" '
        f'font-size="{font_size:.1f}">'
    )

    # frame
    parts.append(
        f'<rect x="0.5" y="0.5" width="{width - 1:.1f}" height="{height - 1:.1f}" '
        f'rx="10" ry="10" fill="{PALETTE["bg"]}" stroke="{PALETTE["border"]}"/>'
    )
    # title bar dots
    dot_y = pad * 0.55
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{pad + i * 16}" cy="{dot_y:.1f}" r="4.5" fill="{color}"/>')

    def line_y(idx: int) -> float:
        return pad + line_height * 1.6 + idx * line_height

    def fade_slide_group(idx: int, inner: str) -> str:
        gid = f"line{idx}"
        begin = idx * stagger
        return (
            f'<g id="{gid}" opacity="0" transform="translate(-14,0)">'
            f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.3f}s" '
            f'dur="{duration:.3f}s" fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1"/>'
            f'<animateTransform attributeName="transform" type="translate" '
            f'from="-14,0" to="0,0" begin="{begin:.3f}s" dur="{duration:.3f}s" '
            f'fill="freeze" calcMode="spline" keySplines="0.25 0.1 0.25 1" additive="replace"/>'
            f'{inner}'
            f'</g>'
        )

    row = 0
    # user@host header
    header_text = (
        f'<text x="{pad:.1f}" y="{line_y(row):.1f}" fill="{PALETTE["prompt"]}">'
        f'{escape(user)}<tspan fill="{PALETTE["muted"]}">@</tspan>'
        f'<tspan fill="{PALETTE["prompt"]}">{escape(host)}</tspan></text>'
    )
    parts.append(fade_slide_group(row, header_text))
    row += 1

    sep_width = width - pad * 2
    sep_text = (
        f'<line x1="{pad:.1f}" y1="{line_y(row) - font_size * 0.35:.1f}" '
        f'x2="{pad + sep_width:.1f}" y2="{line_y(row) - font_size * 0.35:.1f}" '
        f'stroke="{PALETTE["border"]}" stroke-width="1"/>'
    )
    parts.append(fade_slide_group(row, sep_text))
    row += 1

    label_x = pad
    value_x = pad + 12 * (font_size * 0.62)  # align values to a fixed column

    for field in fields:
        label = escape(field.get("label", ""))
        value = escape(field.get("value", ""))
        field_text = (
            f'<text x="{label_x:.1f}" y="{line_y(row):.1f}" fill="{PALETTE["label"]}">'
            f'{label}<tspan fill="{PALETTE["muted"]}">:</tspan></text>'
            f'<text x="{value_x:.1f}" y="{line_y(row):.1f}" fill="{PALETTE["value"]}">{value}</text>'
        )
        parts.append(fade_slide_group(row, field_text))
        row += 1

    # trailing color swatches, like neofetch's palette strip
    swatch_y = line_y(row) - font_size * 0.75
    swatch_colors = [PALETTE["prompt"], PALETTE["label"], PALETTE["accent"], PALETTE["value"], PALETTE["muted"], "#f85149", "#a371f7", "#39d353"]
    swatch_size = min(18.0, sep_width / len(swatch_colors) - 2)
    swatches_inner = "".join(
        f'<rect x="{label_x + i * (swatch_size + 3):.1f}" y="{swatch_y:.1f}" '
        f'width="{swatch_size:.1f}" height="{swatch_size * 0.6:.1f}" rx="2" fill="{c}"/>'
        for i, c in enumerate(swatch_colors)
    )
    parts.append(fade_slide_group(row, swatches_inner))

    parts.append('</svg>')
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=None, help="optional JSON file overriding DEFAULT_DATA")
    parser.add_argument("-o", "--output", type=Path, default=Path("assets/info-card.svg"))
    parser.add_argument("--width", type=float, default=560.0)
    parser.add_argument("--line-height", type=float, default=26.0)
    parser.add_argument("--font-size", type=float, default=15.0)
    parser.add_argument("--pad", type=float, default=22.0)
    parser.add_argument("--stagger", type=float, default=0.12, help="seconds between line starts")
    parser.add_argument("--duration", type=float, default=0.5, help="seconds for one line's fade/slide")
    args = parser.parse_args()

    data_path = args.data
    if data_path is None and Path("data/info_card.json").exists():
        data_path = Path("data/info_card.json")
    data = load_data(data_path)
    svg = build_svg(
        data,
        width=args.width,
        line_height=args.line_height,
        font_size=args.font_size,
        pad=args.pad,
        stagger=args.stagger,
        duration=args.duration,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(f"done -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
