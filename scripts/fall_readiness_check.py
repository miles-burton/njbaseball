#!/usr/bin/env python3
"""Check whether NJ Sports Index is ready for the next fall season."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]


def academic_season() -> str:
    now = datetime.now(ZoneInfo("America/New_York"))
    start_year = now.year if now.month >= 7 else now.year - 1
    return f"{start_year}-{start_year + 1}"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def extract_const(path: str, const_name: str):
    text = read(path)
    match = re.search(rf"const\s+{re.escape(const_name)}\s*=", text)
    if not match:
        raise ValueError(f"{path}: missing const {const_name}")
    start = match.end()
    while start < len(text) and text[start].isspace():
        start += 1
    opener = text[start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                literal = re.sub(r",(\s*[\]}])", r"\1", text[start:idx + 1])
                return json.loads(literal)
    raise ValueError(f"{path}: const {const_name} never closed")


def check(condition: bool, ok: str, bad: str, warnings: list[str], errors: list[str], warn: bool = False) -> None:
    if condition:
        print(f"PASS {ok}")
    elif warn:
        warnings.append(bad)
        print(f"WARN {bad}")
    else:
        errors.append(bad)
        print(f"FAIL {bad}")


def main() -> int:
    expected = academic_season()
    warnings: list[str] = []
    errors: list[str] = []

    print(f"Fall readiness check at {datetime.now(timezone.utc).isoformat()}")
    print(f"Expected current school-year season: {expected}")
    print()

    vercel = json.loads(read("vercel.json"))
    routes = {(item["source"], item["destination"]) for item in vercel.get("rewrites", [])}
    required_routes = {
        ("/diamond", "/diamond-index.html"),
        ("/pitch", "/pitch-index.html"),
        ("/girls-soccer", "/girls-pitch-index.html"),
        ("/gridiron", "/gridiron-index.html"),
        ("/football", "/gridiron-index.html"),
    }
    check(required_routes.issubset(routes), "Vercel clean sport routes exist", "Vercel clean sport routes are incomplete", warnings, errors)

    workflows = {
        "baseball": read(".github/workflows/update-stats.yml"),
        "pitch": read(".github/workflows/update-pitch.yml"),
        "football": read(".github/workflows/update-football.yml"),
    }
    check("BASEBALL_SEASON" in read("scraper.py"), "Baseball scraper supports season override", "Baseball scraper does not support BASEBALL_SEASON", warnings, errors)
    check("PITCH_SEASON" in read("pitch_scraper.py"), "Pitch scraper supports season override", "Pitch scraper does not support PITCH_SEASON", warnings, errors)
    check("FOOTBALL_SEASON" in read("football_scraper.py"), "Football scraper supports season override", "Football scraper does not support FOOTBALL_SEASON", warnings, errors)
    check("season:" in workflows["baseball"], "Baseball workflow has manual season input", "Baseball workflow lacks manual season input", warnings, errors)
    check("season:" in workflows["pitch"], "Pitch workflow has manual season input", "Pitch workflow lacks manual season input", warnings, errors)
    check("season:" in workflows["football"], "Football workflow has manual season input", "Football workflow lacks manual season input", warnings, errors)

    pitch = extract_const("js/pitch-data.js", "PITCH_DATA")
    girls = extract_const("js/girls-pitch-data.js", "PITCH_DATA")
    football = extract_const("js/football-data.js", "FOOTBALL_DATA")
    fall_payloads = [
        ("boys soccer", pitch),
        ("girls soccer", girls),
        ("football", football),
    ]
    for label, payload in fall_payloads:
        teams = payload.get("teams", [])
        games = payload.get("games", [])
        updated = payload.get("updated", "unknown")
        season = payload.get("season", "")
        check(len(teams) >= 300, f"{label} has statewide team coverage ({len(teams)} teams)", f"{label} has low team coverage ({len(teams)} teams)", warnings, errors)
        check(len(games) > 0, f"{label} has schedule/game data ({len(games)} rows)", f"{label} has no schedule/game data", warnings, errors)
        check(season == expected, f"{label} data is already on {expected}", f"{label} data file is still on {season}; scheduled fall runs should flip it to {expected} once NJ.com publishes data", warnings, errors, warn=True)
        print(f"INFO {label} last updated: {updated}")

    print()
    print(f"Summary: {len(errors)} error(s), {len(warnings)} warning(s)")
    if warnings:
        print("Warnings are expected before NJ.com publishes fall-season data, but should disappear after the first successful fall scrape.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

