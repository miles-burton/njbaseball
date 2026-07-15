#!/usr/bin/env python3
"""Validate that every sport index follows the shared NJ Sports Index shell."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SPORT_PAGES = {
    "diamond-index.html": {
        "sport": "baseball",
        "brand": "Diamond Index",
        "view_aliases": {
            "leaders": ["leaderboard", "pitching"],
            "rankings": ["team-rankings"],
        },
    },
    "pitch-index.html": {
        "sport": "boyssoccer",
        "brand": "Pitch Index",
        "view_aliases": {},
    },
    "girls-pitch-index.html": {
        "sport": "girlssoccer",
        "brand": "Pitch Index",
        "view_aliases": {},
    },
    "gridiron-index.html": {
        "sport": "football",
        "brand": "Gridiron Index",
        "view_aliases": {},
    },
    "court-index.html": {
        "sport": "boysbasketball",
        "brand": "Court Index",
        "view_aliases": {},
    },
}

REQUIRED_NAV = ["Leaders", "Teams", "Rankings", "Scores", "Predictor", "Standings", "Glossary", "Sports", "Report"]
REQUIRED_IDS = ["navTabs", "themeToggle", "backBtn", "reportModal", "teamsNavList"]
REQUIRED_VIEWS = ["home", "leaders", "rankings", "scores", "predictor", "standings", "teams", "glossary", "team", "player"]
REQUIRED_SCRIPTS = ["js/supabase-config.js", "js/supabase-client.js"]


def page_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def has_view(text: str, canonical: str, aliases: dict[str, list[str]]) -> bool:
    candidates = [canonical, *aliases.get(canonical, [])]
    return any(f'id="view-{candidate}"' in text or f"id='view-{candidate}'" in text for candidate in candidates)


def main() -> int:
    errors: list[str] = []
    registry = page_text("js/sports-registry.js")

    for page, config in SPORT_PAGES.items():
        text = page_text(page)
        print(f"Checking {page}...")

        if config["brand"].upper().replace(" ", "</span><span>") not in text.upper() and config["brand"].upper() not in text.upper():
            errors.append(f"{page}: missing visible brand {config['brand']}")

        if f"data-sport=\"{config['sport']}\"" not in text:
            errors.append(f"{page}: missing html data-sport=\"{config['sport']}\"")

        for nav in REQUIRED_NAV:
            if nav not in text:
                errors.append(f"{page}: missing nav item {nav}")

        for node_id in REQUIRED_IDS:
            if f'id="{node_id}"' not in text:
                errors.append(f"{page}: missing #{node_id}")

        for view in REQUIRED_VIEWS:
            if not has_view(text, view, config["view_aliases"]):
                errors.append(f"{page}: missing canonical view {view}")

        for script in REQUIRED_SCRIPTS:
            if script not in text:
                errors.append(f"{page}: missing script {script}")

        if "global-search" not in text or "global-search-input" not in text:
            errors.append(f"{page}: missing shared global search structure")

        if "site-header" not in text or "site-logo" not in text or "nav-tabs" not in text:
            errors.append(f"{page}: missing shared header classes")

    for page, config in SPORT_PAGES.items():
        if page not in registry or config["sport"] not in registry:
            errors.append(f"js/sports-registry.js: missing {page}/{config['sport']}")

    docs = page_text("docs/SPORT_FORMAT.md")
    for view in REQUIRED_VIEWS:
        if view not in docs:
            errors.append(f"docs/SPORT_FORMAT.md: missing view contract for {view}")

    if errors:
        print("\nSport format check failed:")
        for error in errors:
            print(f"FAIL {error}")
        return 1

    print("PASS all sport pages follow the shared shell contract")
    return 0


if __name__ == "__main__":
    sys.exit(main())
