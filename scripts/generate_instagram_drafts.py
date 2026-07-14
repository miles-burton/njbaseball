#!/usr/bin/env python3
"""Generate daily NJ Sports Index social post drafts from local site data."""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GOLD = "#C89B3C"
NAVY = "#0B1F3A"
GRAPHITE = "#10151d"
OFF_WHITE = "#F8F9FA"
RED = "#FF6F5E"
GREEN = "#2EA36B"


@dataclass
class Draft:
    filename: str
    title: str
    subtitle: str
    rows: list[dict[str, Any]]
    accent: str
    caption: str


def extract_const(path: Path, const_name: str) -> Any:
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"const\s+{re.escape(const_name)}\s*=", text)
    if not match:
        raise ValueError(f"Could not find const {const_name} in {path}")
    start = match.end()
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] not in "[{":
        raise ValueError(f"Const {const_name} does not start with a JSON object/array")

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
    raise ValueError(f"Const {const_name} was not closed")


def safe_extract(path: Path, const_name: str, fallback: Any) -> Any:
    try:
        return extract_const(path, const_name)
    except Exception as exc:
        print(f"warning: {path.name}:{const_name} skipped: {exc}")
        return fallback


def fmt_num(value: Any, places: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value or "-")
    if abs(number - round(number)) < 0.001:
        return str(int(round(number)))
    return f"{number:.{places}f}"


def team_logo_map(teams: dict[str, Any]) -> dict[str, str]:
    return {
        name: str(info.get("logo", ""))
        for name, info in teams.items()
        if isinstance(info, dict) and info.get("logo")
    }


def baseball_team_rows() -> list[dict[str, Any]]:
    data_path = ROOT / "js" / "data.js"
    hitters = safe_extract(data_path, "AP", [])
    teams = safe_extract(data_path, "TM", {})
    schedules = safe_extract(data_path, "SCHEDULES", {})
    logos = team_logo_map(teams)
    by_team: dict[str, dict[str, Any]] = {}
    for player in hitters:
        team = player.get("team")
        if not team:
            continue
        row = by_team.setdefault(team, {"team": team, "wrc": 0.0, "pa": 0, "hr": 0, "rbi": 0})
        pa = float(player.get("PA") or 0)
        row["wrc"] += float(player.get("wRC") or 0)
        row["pa"] += pa
        row["hr"] += int(player.get("HR") or 0)
        row["rbi"] += int(player.get("RBI") or 0)
    for team, row in by_team.items():
        sched = schedules.get(team, {}) if isinstance(schedules, dict) else {}
        wins = int(sched.get("wins") or 0)
        losses = int(sched.get("losses") or 0)
        games = max(1, wins + losses)
        row["record"] = f"{wins}-{losses}" if wins or losses else "-"
        row["score"] = row["wrc"] + (wins / games) * 35 + row["hr"] * 1.5
        row["logo"] = logos.get(team, "")
    return sorted(by_team.values(), key=lambda r: r["score"], reverse=True)[:10]


def soccer_team_rows(path: Path) -> list[dict[str, Any]]:
    data = safe_extract(path, "PITCH_DATA", {})
    teams = data.get("teams", {}) if isinstance(data, dict) else {}
    if isinstance(teams, list):
        teams = {str(team.get("name", f"Team {idx + 1}")): team for idx, team in enumerate(teams) if isinstance(team, dict)}
    rows = []
    for name, team in teams.items():
        if not isinstance(team, dict):
            continue
        rows.append({
            "team": name,
            "record": team.get("record", "-"),
            "score": team.get("powerScore", 0),
            "logo": team.get("logo", ""),
            "meta": f"GF {team.get('gf', 0)} | GA {team.get('ga', 0)}",
        })
    return sorted(rows, key=lambda r: float(r.get("score") or 0), reverse=True)[:10]


def football_team_rows() -> list[dict[str, Any]]:
    data = safe_extract(ROOT / "js" / "football-data.js", "FOOTBALL_DATA", {})
    teams = data.get("teams", {}) if isinstance(data, dict) else {}
    if isinstance(teams, list):
        teams = {str(team.get("name", f"Team {idx + 1}")): team for idx, team in enumerate(teams) if isinstance(team, dict)}
    rows = []
    for name, team in teams.items():
        if not isinstance(team, dict):
            continue
        rows.append({
            "team": name,
            "record": team.get("record", "-"),
            "score": team.get("powerScore", 0),
            "logo": team.get("logo", ""),
            "meta": f"PF {team.get('pf', 0)} | PA {team.get('pa', 0)}",
        })
    return sorted(rows, key=lambda r: float(r.get("score") or 0), reverse=True)[:10]


def svg_card(draft: Draft) -> str:
    rows = draft.rows[:10]
    row_svg = []
    y = 265
    for idx, row in enumerate(rows, 1):
        top_three = idx <= 3
        fill = "#17202b" if top_three else "#111821"
        stroke = draft.accent if top_three else "#263241"
        score = fmt_num(row.get("score"), 1)
        team = html.escape(str(row.get("team", "-")))
        record = html.escape(str(row.get("record", "-")))
        meta = html.escape(str(row.get("meta", "")))
        row_svg.append(f"""
  <rect x="78" y="{y}" width="924" height="72" rx="14" fill="{fill}" stroke="{stroke}" stroke-opacity="{0.55 if top_three else 0.25}"/>
  <text x="112" y="{y + 46}" fill="{draft.accent}" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="800">{idx}</text>
  <circle cx="176" cy="{y + 36}" r="22" fill="#0A1220" stroke="#2A3444"/>
  <text x="176" y="{y + 45}" fill="{draft.accent}" font-family="Inter, Arial, sans-serif" font-size="20" font-weight="900" text-anchor="middle">{team[:1]}</text>
  <text x="222" y="{y + 32}" fill="{OFF_WHITE}" font-family="Inter, Arial, sans-serif" font-size="25" font-weight="800">{team}</text>
  <text x="222" y="{y + 56}" fill="#9AA5B4" font-family="Inter, Arial, sans-serif" font-size="15" font-weight="700">{record} {meta}</text>
  <text x="952" y="{y + 46}" fill="{draft.accent}" font-family="Inter, Arial, sans-serif" font-size="28" font-weight="900" text-anchor="end">{score}</text>
""")
        y += 82
    generated = datetime.now().strftime("%b %-d, %Y") if "%" else datetime.now().isoformat()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <rect width="1080" height="1350" fill="{GRAPHITE}"/>
  <rect x="0" y="0" width="1080" height="190" fill="{NAVY}"/>
  <path d="M78 92 L104 66 L130 92 L104 118 Z M104 66 L104 118 M78 92 L130 92" fill="none" stroke="{draft.accent}" stroke-width="8" stroke-linecap="round"/>
  <path d="M74 126 L162 38 L230 106 L300 36" fill="none" stroke="{draft.accent}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="342" y="83" fill="{draft.accent}" font-family="Inter, Arial, sans-serif" font-size="25" font-weight="900" letter-spacing="3">NJ SPORTS INDEX</text>
  <text x="342" y="126" fill="{OFF_WHITE}" font-family="Inter, Arial, sans-serif" font-size="58" font-weight="900">{html.escape(draft.title)}</text>
  <text x="80" y="226" fill="#9AA5B4" font-family="Inter, Arial, sans-serif" font-size="22" font-weight="700">{html.escape(draft.subtitle)}</text>
  <text x="1000" y="226" fill="#9AA5B4" font-family="Inter, Arial, sans-serif" font-size="18" font-weight="700" text-anchor="end">{html.escape(generated)}</text>
  {''.join(row_svg)}
  <text x="80" y="1248" fill="{OFF_WHITE}" font-family="Inter, Arial, sans-serif" font-size="30" font-weight="900">@njdiamondindex</text>
  <text x="80" y="1286" fill="#9AA5B4" font-family="Inter, Arial, sans-serif" font-size="20" font-weight="700">Measure the Game.</text>
</svg>
"""


def build_drafts() -> list[Draft]:
    return [
        Draft(
            filename="diamond-index-top-10.svg",
            title="DIAMOND TOP 10",
            subtitle="Baseball power snapshot from the latest site data",
            rows=baseball_team_rows(),
            accent=GOLD,
            caption="Diamond Index Top 10 from today’s data refresh. Full rankings and team pages are live on the site. #NJBaseball #DiamondIndex",
        ),
        Draft(
            filename="pitch-index-boys-top-10.svg",
            title="PITCH BOYS TOP 10",
            subtitle="Boys soccer power snapshot from the latest site data",
            rows=soccer_team_rows(ROOT / "js" / "pitch-data.js"),
            accent=GREEN,
            caption="Pitch Index Boys Soccer Top 10 from today’s data refresh. Full rankings, scores, and team pages are live on the site. #NJSoccer #PitchIndex",
        ),
        Draft(
            filename="pitch-index-girls-top-10.svg",
            title="PITCH GIRLS TOP 10",
            subtitle="Girls soccer power snapshot from the latest site data",
            rows=soccer_team_rows(ROOT / "js" / "girls-pitch-data.js"),
            accent=GREEN,
            caption="Pitch Index Girls Soccer Top 10 from today’s data refresh. Full rankings, scores, and team pages are live on the site. #NJSoccer #PitchIndex",
        ),
        Draft(
            filename="gridiron-index-top-10.svg",
            title="GRIDIRON TOP 10",
            subtitle="Football power snapshot from the latest site data",
            rows=football_team_rows(),
            accent=RED,
            caption="Gridiron Index Top 10 from today’s data refresh. Full rankings, scores, and team pages are live on the site. #NJFootball #GridironIndex",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "dist" / "instagram-drafts"))
    args = parser.parse_args()

    day_dir = Path(args.output) / datetime.now().strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    captions = ["# Daily Instagram Drafts\n"]
    for draft in build_drafts():
        if not draft.rows:
            print(f"warning: no rows for {draft.filename}; skipping")
            continue
        target = day_dir / draft.filename
        target.write_text(svg_card(draft), encoding="utf-8")
        manifest.append({
            "file": draft.filename,
            "title": draft.title,
            "caption": draft.caption,
            "rows": draft.rows,
        })
        captions.append(f"## {draft.title}\n\nGraphic: `{draft.filename}`\n\n{draft.caption}\n")

    (day_dir / "captions.md").write_text("\n".join(captions), encoding="utf-8")
    (day_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Generated {len(manifest)} draft graphics in {day_dir}")


if __name__ == "__main__":
    main()
