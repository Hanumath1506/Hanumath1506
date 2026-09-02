#!/usr/bin/env python3
"""
fetch_contributions.py — scrape the public contributions-graph fragment at
https://github.com/users/<username>/contributions (no auth/token needed) and
write a normalized JSON file with per-day counts + streak stats.

Usage:
    python scripts/fetch_contributions.py -u Hanumath1506 -o data/contributions.json

Requires: requests, beautifulsoup4
    pip install requests beautifulsoup4
"""
import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

COUNT_RE = re.compile(r"^(No|\d+)\s+contributions?", re.IGNORECASE)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; profile-art-bot/1.0; "
        "+https://github.com/Hanumath1506)"
    ),
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_count(text: str) -> int:
    m = COUNT_RE.match(text.strip())
    if not m:
        return 0
    token = m.group(1)
    return 0 if token.lower() == "no" else int(token)


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    tooltip_by_id: dict[str, str] = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if target:
            tooltip_by_id[target] = tip.get_text(strip=True)

    cells = soup.find_all(attrs={"data-date": True})
    days: list[dict] = []
    for cell in cells:
        cell_date = cell.get("data-date")
        if not cell_date:
            continue

        level_attr = cell.get("data-level")
        level = int(level_attr) if level_attr is not None else None

        count = None
        cell_id = cell.get("id")
        tooltip_text = None
        if cell_id and cell_id in tooltip_by_id:
            tooltip_text = tooltip_by_id[cell_id]
        elif cell.get("aria-label"):
            tooltip_text = cell.get("aria-label")

        if tooltip_text:
            count = parse_count(tooltip_text)

        if count is None:
            # fall back to level as a proxy (0 == 0 contributions is safe;
            # >0 levels without a tooltip just preserve relative intensity)
            count = 0 if (level or 0) == 0 else None

        if level is None:
            level = 0 if count == 0 else 1

        days.append({"date": cell_date, "count": count, "level": level})

    days.sort(key=lambda d: d["date"])
    return days


def compute_streaks(days: list[dict]) -> dict:
    if not days:
        return {
            "current_streak": {"length": 0, "start": None, "end": None},
            "longest_streak": {"length": 0, "start": None, "end": None},
            "total_contributions": 0,
            "best_day": None,
        }

    total = sum(d["count"] or 0 for d in days)
    best_day = max(days, key=lambda d: d["count"] or 0)

    # longest streak anywhere in the window
    longest_len = 0
    longest_start = longest_end = None
    run_len = 0
    run_start = None
    for d in days:
        if (d["count"] or 0) > 0:
            if run_len == 0:
                run_start = d["date"]
            run_len += 1
            if run_len > longest_len:
                longest_len = run_len
                longest_start = run_start
                longest_end = d["date"]
        else:
            run_len = 0
            run_start = None

    # current streak, trailing from the end of the window; if the very last
    # day is "today" with zero contributions yet, don't let it zero out an
    # otherwise active streak (the day isn't over).
    today_iso = date.today().isoformat()
    end_idx = len(days) - 1
    if days[end_idx]["date"] == today_iso and (days[end_idx]["count"] or 0) == 0:
        end_idx -= 1

    current_len = 0
    i = end_idx
    while i >= 0 and (days[i]["count"] or 0) > 0:
        current_len += 1
        i -= 1
    current_start = days[i + 1]["date"] if current_len > 0 else None
    current_end = days[end_idx]["date"] if current_len > 0 else None

    return {
        "current_streak": {"length": current_len, "start": current_start, "end": current_end},
        "longest_streak": {"length": longest_len, "start": longest_start, "end": longest_end},
        "total_contributions": total,
        "best_day": {"date": best_day["date"], "count": best_day["count"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-u", "--username", default="Hanumath1506")
    parser.add_argument("-o", "--output", type=Path, default=Path("data/contributions.json"))
    args = parser.parse_args()

    try:
        html = fetch_html(args.username)
    except requests.RequestException as exc:
        print(f"error: failed to fetch contributions page: {exc}", file=sys.stderr)
        return 1

    days = parse_days(html)
    if not days:
        print("error: no contribution cells parsed — GitHub markup may have changed", file=sys.stderr)
        return 1

    stats = compute_streaks(days)
    payload = {
        "username": args.username,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **stats,
        "days": days,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"done -> {args.output} "
        f"({len(days)} days, total={stats['total_contributions']}, "
        f"current_streak={stats['current_streak']['length']}, "
        f"longest_streak={stats['longest_streak']['length']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
