#!/usr/bin/env python3
"""Broad production health checks for the static NJ Sports Index site."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML_PAGES = ["index.html", "diamond-index.html", "pitch-index.html", "girls-pitch-index.html", "gridiron-index.html"]
DATA_FILES = ["js/data.js", "js/player_logs.js", "js/pitch-data.js", "js/girls-pitch-data.js", "js/football-data.js"]
SCRIPT_FILES = ["js/app.js", "js/pitch.js", "js/football.js", "js/supabase-client.js", "js/supabase-config.js", "js/sports-registry.js"]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def main() -> int:
    errors: list[str] = []

    def record(condition: bool, ok: str, bad: str) -> None:
        if condition:
            print(f"PASS {ok}")
        else:
            errors.append(bad)
            print(f"FAIL {bad}")

    for path in [*HTML_PAGES, *DATA_FILES, *SCRIPT_FILES, "vercel.json", "supabase/schema.sql"]:
        record((ROOT / path).exists(), f"{path} exists", f"missing required file {path}")

    for page in HTML_PAGES:
        text = read(page)
        record('<meta name="description"' in text, f"{page} has SEO description", f"{page} is missing a meta description")
        record(not re.search(r'class="[^"]*\bcoming-soon\b', text), f"{page} has no stale coming-soon card", f"{page} still marks an active sport as coming soon")
        record(
            "This opens a pre-filled GitHub issue" not in text and "This opens a prefilled GitHub Issue" not in text,
            f"{page} report copy is current",
            f"{page} has stale report form copy",
        )
        if page != "index.html":
            record("js/supabase-config.js" in text, f"{page} loads Supabase config", f"{page} is missing Supabase config script")
            record("js/sports-registry.js" in text, f"{page} loads sports registry", f"{page} is missing sports registry script")

    hub = read("index.html")
    record(
        all(stale not in hub for stale in ["1,458", "9,472", "2025 season"]),
        "hub avoids brittle hardcoded network counts",
        "hub contains brittle hardcoded counts or stale season copy",
    )

    config = read("js/supabase-config.js")
    record(
        "jyxclxebnutnxpzrvcgt.supabase.co" in config and "anonKey: ''" not in config,
        "Supabase browser config is present",
        "Supabase browser config is incomplete",
    )

    vercel = json.loads(read("vercel.json"))
    route_sources = {item.get("source") for item in vercel.get("rewrites", [])}
    for route in ["/diamond", "/pitch", "/girls-soccer", "/gridiron", "/football"]:
        record(route in route_sources, f"Vercel route {route} exists", f"Vercel route missing: {route}")
    record(
        any(header.get("source") == "/js/(.*)" for header in vercel.get("headers", [])),
        "Vercel JS cache revalidation is configured",
        "Vercel headers do not cover JS cache revalidation",
    )

    schema = read("supabase/schema.sql")
    for table in ["problem_reports", "data_corrections", "scrape_runs", "sport_snapshots"]:
        record(
            f"create table if not exists public.{table}" in schema,
            f"Supabase table {table} is defined",
            f"Supabase schema missing {table}",
        )

    for path in SCRIPT_FILES:
        record("debugger" not in read(path), f"{path} has no debugger statement", f"{path} contains debugger statement")

    print()
    if errors:
        print(f"Site health failed with {len(errors)} issue(s).")
        return 1
    print("Site health check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

