#!/usr/bin/env python3
"""
render_heatmap_svg.py — render data/contributions.json as a 53x7 GitHub-style
contribution heatmap SVG: rounded boxes in the GitHub green palette, a
diagonal slide-down reveal (SMIL), a legend, and a stats footer.

Usage:
    python scripts/render_heatmap_svg.py data/contributions.json -o assets/heatmap.svg
"""
import argparse
import calendar
import json
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

LEVEL_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

PALETTE = {
    "bg": "#0d1117",
    "text": "#c9d1d9",
    "muted": "#8b949e",
    "border": "#30363d",
}


def sunday_index(d: date) -> int:
    # Monday=0..Sunday=6 (date.weekday()) -> Sunday=0..Saturday=6
    return (d.weekday() + 1) % 7


def build_week_grid(days: list[dict]) -> list[list[dict | None]]:
    by_date = {d["date"]: d for d in days}
    first_date = date.fromisoformat(days[0]["date"])
    last_date = date.fromisoformat(days[-1]["date"])

    start = first_date - timedelta(days=sunday_index(first_date))
    end = last_date + timedelta(days=6 - sunday_index(last_date))

    total_days = (end - start).days + 1
    weeks: list[list[dict | None]] = []
    cursor = start
    week: list[dict | None] = []
    for _ in range(total_days):
        iso = cursor.isoformat()
        cell = by_date.get(iso)  # None for calendar padding outside the fetched window
        week.append(cell)
        if len(week) == 7:
            weeks.append(week)
            week = []
        cursor += timedelta(days=1)
    if week:
        while len(week) < 7:
            week.append(None)
        weeks.append(week)
    return weeks


def month_labels(weeks: list[list[dict | None]]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    last_month = None
    for wi, week in enumerate(weeks):
        first_real = next((c for c in week if c and c.get("date")), None)
        if not first_real:
            continue
        d = date.fromisoformat(first_real["date"])
        if d.month != last_month:
            labels.append((wi, calendar.month_abbr[d.month]))
            last_month = d.month
    return labels


def build_svg(
    payload: dict,
    cell: float,
    gap: float,
    stagger: float,
    duration: float,
) -> str:
    days = payload["days"]
    weeks = build_week_grid(days)
    n_weeks = len(weeks)

    top_pad = 26.0
    left_pad = 4.0
    grid_w = n_weeks * (cell + gap) - gap
    grid_h = 7 * (cell + gap) - gap
    legend_h = 26.0
    footer_h = 30.0
    width = max(grid_w + left_pad * 2, 620.0)
    height = top_pad + grid_h + legend_h + footer_h + 14.0

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" '
        f'width="{width:.0f}" height="{height:.0f}" role="img" aria-label="Contribution heatmap" '
        f'font-family="SFMono-Regular,Menlo,Consolas,\'DejaVu Sans Mono\',monospace" font-size="11">'
    )
    parts.append(f'<rect x="0" y="0" width="{width:.1f}" height="{height:.1f}" rx="10" fill="{PALETTE["bg"]}"/>')

    # month labels
    for wi, label in month_labels(weeks):
        x = left_pad + wi * (cell + gap)
        parts.append(f'<text x="{x:.1f}" y="{top_pad - 10:.1f}" fill="{PALETTE["muted"]}">{escape(label)}</text>')

    # diagonal-reveal grid
    for wi, week in enumerate(weeks):
        for di, day in enumerate(week):
            x = left_pad + wi * (cell + gap)
            y = top_pad + di * (cell + gap)
            level = 0
            count = 0
            date_str = ""
            if day is not None and day.get("date"):
                level = day.get("level") or 0
                count = day.get("count") or 0
                date_str = day["date"]
            color = LEVEL_COLORS[min(level, 4)]
            begin = (wi + di) * stagger
            title = f"{count} contributions on {date_str}" if date_str else ""
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.5" ry="2.5" '
                f'fill="{color}" opacity="0" transform="translate(0,-8)">'
            )
            if title:
                parts.append(f'<title>{escape(title)}</title>')
            parts.append(
                f'<animate attributeName="opacity" from="0" to="1" begin="{begin:.3f}s" '
                f'dur="{duration:.3f}s" fill="freeze" calcMode="spline" keySplines="0.3 0.1 0.3 1"/>'
            )
            parts.append(
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="0,-8" to="0,0" begin="{begin:.3f}s" dur="{duration:.3f}s" '
                f'fill="freeze" calcMode="spline" keySplines="0.3 0.1 0.3 1"/>'
            )
            parts.append('</rect>')

    # legend: Less [] [] [] [] [] More
    legend_y = top_pad + grid_h + 20.0
    parts.append(f'<text x="{left_pad:.1f}" y="{legend_y:.1f}" fill="{PALETTE["muted"]}">Less</text>')
    lx = left_pad + 34.0
    for i, color in enumerate(LEVEL_COLORS):
        parts.append(
            f'<rect x="{lx + i * (cell + gap):.1f}" y="{legend_y - cell + 2:.1f}" '
            f'width="{cell:.1f}" height="{cell:.1f}" rx="2.5" fill="{color}"/>'
        )
    parts.append(
        f'<text x="{lx + len(LEVEL_COLORS) * (cell + gap) + 6:.1f}" y="{legend_y:.1f}" '
        f'fill="{PALETTE["muted"]}">More</text>'
    )

    # stats footer
    total = payload.get("total_contributions", 0)
    cur = payload.get("current_streak", {}).get("length", 0)
    longest = payload.get("longest_streak", {}).get("length", 0)
    footer_y = legend_y + 24.0
    footer_text = (
        f"{total} contributions in the last year  ·  "
        f"current streak: {cur}d  ·  longest streak: {longest}d"
    )
    parts.append(f'<text x="{left_pad:.1f}" y="{footer_y:.1f}" fill="{PALETTE["text"]}">{escape(footer_text)}</text>')

    parts.append('</svg>')
    return "".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", default=Path("data/contributions.json"))
    parser.add_argument("-o", "--output", type=Path, default=Path("assets/heatmap.svg"))
    parser.add_argument("--cell", type=float, default=11.0)
    parser.add_argument("--gap", type=float, default=3.0)
    parser.add_argument("--stagger", type=float, default=0.012, help="seconds between diagonal steps")
    parser.add_argument("--duration", type=float, default=0.4, help="seconds for one cell's reveal")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"error: input not found: {args.input} (run fetch_contributions.py first)")

    payload = json.loads(args.input.read_text(encoding="utf-8"))
    svg = build_svg(payload, cell=args.cell, gap=args.gap, stagger=args.stagger, duration=args.duration)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(f"done -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
