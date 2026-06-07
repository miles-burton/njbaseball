#!/usr/bin/env python3
"""
Build compact historical season data files for Diamond Index.

This uses the same parsers as scraper.py, but skips player game logs so older
seasons can be backfilled quickly. Output files are loaded on demand by app.js.

Examples:
  python3 build_season_data.py 2024-2025
  python3 build_season_data.py 2024-2025 2023-2024
"""

import datetime
import json
import os
import sys
import time

import scraper


def display_year(season):
    return season.split("-")[-1]


def scrape_team_compact(display_name, slug):
    print(f"  {display_name}...", end=" ", flush=True)
    try:
        stats_html = scraper.fetch_stats(slug)
        tables = scraper.get_table_rows(stats_html)
        hitters = scraper.parse_hitting(tables[0], display_name) if len(tables) > 0 else []
        pitchers = scraper.parse_pitching(tables[1], display_name) if len(tables) > 1 else []
        schedule = scraper.parse_schedule(scraper.fetch_schedule(slug))
        print(f"{len(hitters)} hitters, {len(pitchers)} pitchers, {schedule['wins']}-{schedule['losses']}")
        return hitters, pitchers, schedule
    except Exception as exc:
        print(f"ERROR: {exc}")
        return [], [], {"coach": "", "wins": 0, "losses": 0, "games": []}


def write_season_file(season, hitters, pitchers, schedules):
    year = display_year(season)
    out_dir = os.path.join("js", "seasons", year)
    os.makedirs(out_dir, exist_ok=True)
    updated = datetime.datetime.now().strftime("%b %d, %Y")
    payload = {
        "year": year,
        "season": season,
        "updated": updated,
        "AP": hitters,
        "PP": pitchers,
        "SCHEDULES": schedules,
    }
    out_path = os.path.join(out_dir, "data.js")
    with open(out_path, "w") as f:
        f.write("// AUTO-GENERATED historical season data\n")
        f.write(f"// Season: {season}\n\n")
        f.write("window.DI_SEASON_DATA = window.DI_SEASON_DATA || {};\n")
        f.write(f"window.DI_SEASON_DATA[{json.dumps(year)}] = ")
        json.dump(payload, f, separators=(",", ":"))
        f.write(";\n")
    print(f"✅ wrote {out_path}")


def update_manifest(seasons):
    existing = [{"year": "2026", "season": "2025-2026", "label": "2026", "current": True}]
    manifest_path = os.path.join("js", "seasons", "manifest.js")
    if os.path.exists(manifest_path):
        text = open(manifest_path).read()
        # Keep this intentionally simple; generated manifest is small and stable.
        import re
        m = re.search(r"window\.DI_SEASONS\s*=\s*(\[.*?\]);", text, re.S)
        if m:
            try:
                existing = json.loads(m.group(1))
            except json.JSONDecodeError:
                existing = [{"year": "2026", "season": "2025-2026", "label": "2026", "current": True}]

    by_year = {item["year"]: item for item in existing}
    for season in seasons:
        year = display_year(season)
        by_year[year] = {
            "year": year,
            "season": season,
            "label": year,
            "file": f"js/seasons/{year}/data.js",
        }
    ordered = sorted(by_year.values(), key=lambda x: int(x["year"]), reverse=True)
    with open(manifest_path, "w") as f:
        f.write("// AUTO-GENERATED season manifest. Add generated season files here as they are backfilled.\n")
        f.write("window.DI_SEASONS = ")
        json.dump(ordered, f, indent=2)
        f.write(";\nwindow.DI_SEASON_DATA = window.DI_SEASON_DATA || {};\n")
    print(f"✅ updated {manifest_path}")


def build(season):
    scraper.SEASON = season
    print(f"\nScraping compact season data for {season}\n")
    hitters = []
    pitchers = []
    schedules = {}
    for display_name, slug in scraper.TEAMS.items():
        h, p, sched = scrape_team_compact(display_name, slug)
        hitters.extend(h)
        pitchers.extend(p)
        schedules[display_name] = sched
        time.sleep(0.08)
    write_season_file(season, hitters, pitchers, schedules)
    return {"season": season, "hitters": len(hitters), "pitchers": len(pitchers), "teams": len(schedules)}


if __name__ == "__main__":
    seasons = sys.argv[1:] or ["2024-2025"]
    summaries = [build(season) for season in seasons]
    update_manifest(seasons)
    print("\nSummary")
    for row in summaries:
        print(f"  {row['season']}: {row['teams']} teams, {row['hitters']} hitters, {row['pitchers']} pitchers")
