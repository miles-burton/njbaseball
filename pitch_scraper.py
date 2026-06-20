#!/usr/bin/env python3
"""
Pitch Index boys soccer data scraper.

Pulls real 2025-2026 boys soccer standings, schedules, scoring, and goalkeeping
data from highschoolsports.nj.com and writes js/pitch-data.js for the static app.
"""

import concurrent.futures
import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape

import certifi


SEASON = "2025-2026"
SPORT = "boyssoccer"
BASE = "https://highschoolsports.nj.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}
CTX = ssl.create_default_context(cafile=certifi.where())
CONFERENCES = [
    "BCSL",
    "Big North",
    "Cape-Atlantic",
    "Colonial",
    "CVC",
    "GMC",
    "HCIAL",
    "NJAC",
    "NJIC",
    "Olympic",
    "SEC",
    "Shore",
    "Skyland",
    "Tri-County",
    "UCC",
]


def fetch(url, timeout=18):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as res:
        return res.read().decode("utf-8", "ignore")


def clean_text(value):
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.I)
    value = re.sub(r"<.*?>", " ", value, flags=re.S)
    value = unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def parse_int(value):
    value = clean_text(str(value)).replace("—", "").replace("-", "")
    match = re.search(r"-?\d+", value)
    return int(match.group()) if match else 0


def parse_record(record):
    parts = [int(p) for p in re.findall(r"\d+", record or "")]
    while len(parts) < 3:
        parts.append(0)
    wins, losses, ties = parts[:3]
    games = wins + losses + ties
    pct = (wins + 0.5 * ties) / games if games else 0
    return {"wins": wins, "losses": losses, "ties": ties, "games": games, "pct": pct}


def parse_conference(conf):
    url = f"{BASE}/{SPORT}/standings/season/{SEASON}?conference={urllib.parse.quote(conf)}"
    html = fetch(url)
    table_match = re.search(
        r'<table[^>]*v-show="viewMode == \'Division\'"[^>]*>(.*?)</table>',
        html,
        flags=re.S | re.I,
    )
    if not table_match:
        table_match = re.search(r"<table.*?</table>", html, flags=re.S | re.I)
    if not table_match:
        return []

    teams = []
    current_division = "Overall"
    table = table_match.group(1)
    for chunk in re.split(r"(<thead.*?</thead>)", table, flags=re.S | re.I):
        division_match = re.search(r"<strong>(.*?)</strong>", chunk, flags=re.S | re.I)
        if division_match:
            current_division = clean_text(division_match.group(1))
            continue

        for row in re.findall(r"<tr.*?</tr>", chunk, flags=re.S | re.I):
            href_match = re.search(r'href="(/school/([^/]+)/boyssoccer/season/[^"]+)"', row)
            if not href_match:
                continue
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S | re.I)
            if len(cells) < 9:
                continue
            name = clean_text(cells[0])
            slug = href_match.group(2)
            record = clean_text(cells[1])
            division_record = clean_text(cells[3])
            home = clean_text(cells[5])
            away = clean_text(cells[6])
            gf = parse_int(cells[7])
            ga = parse_int(cells[8])
            rec = parse_record(record)
            div_rec = parse_record(division_record)
            teams.append(
                {
                    "name": name,
                    "slug": slug,
                    "conference": conf,
                    "division": current_division,
                    "record": record,
                    "wins": rec["wins"],
                    "losses": rec["losses"],
                    "ties": rec["ties"],
                    "games": rec["games"],
                    "winPct": rec["pct"],
                    "divisionRecord": division_record,
                    "divisionWins": div_rec["wins"],
                    "divisionLosses": div_rec["losses"],
                    "divisionTies": div_rec["ties"],
                    "home": home,
                    "away": away,
                    "gf": gf,
                    "ga": ga,
                    "gd": gf - ga,
                    "gfPerGame": round(gf / rec["games"], 2) if rec["games"] else 0,
                    "gaPerGame": round(ga / rec["games"], 2) if rec["games"] else 0,
                    "njUrl": f"{BASE}{href_match.group(1)}",
                }
            )
    return teams


def parse_schedule(html, team_slug):
    table_match = re.search(r"<table.*?</table>", html, flags=re.S | re.I)
    if not table_match:
        return []
    rows = []
    for row in re.findall(r"<tr.*?</tr>", table_match.group(0), flags=re.S | re.I)[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S | re.I)
        if len(cells) < 4:
            continue
        date = clean_text(cells[0])
        opponent_cell = cells[1]
        href = re.search(r'href="(/school/([^/]+)/boyssoccer/season/[^"]+)"', opponent_cell)
        opponent = clean_text(opponent_cell)
        result_text = clean_text(cells[2])
        record_after = clean_text(cells[3])
        result_match = re.match(r"([WTL])\s+(\d+)\s*-\s*(\d+)", result_text)
        result = result_match.group(1) if result_match else ""
        team_score = int(result_match.group(2)) if result_match else None
        opp_score = int(result_match.group(3)) if result_match else None
        rows.append(
            {
                "date": date,
                "opponent": opponent.replace("vs ", "").replace("@ ", "").strip(),
                "opponentSlug": href.group(2) if href else "",
                "site": "vs" if opponent.startswith("vs ") else "@" if opponent.startswith("@ ") else "",
                "result": result,
                "teamScore": team_score,
                "opponentScore": opp_score,
                "recordAfter": record_after,
                "njUrl": f"{BASE}{href.group(1)}" if href else "",
            }
        )
    return rows


def split_grade(name):
    grade = ""
    for value in ("Freshman", "Sophomore", "Junior", "Senior"):
        if re.search(rf"\b{value}\b", name):
            grade = value
            break
    base = re.split(r"\s+#\d+|\s+•|\s+(?:Freshman|Sophomore|Junior|Senior)\b", name, maxsplit=1)[0]
    return base.strip(), grade


def parse_stat_table(table, columns, team):
    players = []
    rows = re.findall(r"<tr.*?</tr>", table, flags=re.S | re.I)[1:]
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        if len(cells) < len(columns) + 1:
            continue
        player_cell = cells[0]
        link = re.search(r'href="([^"]+)"', player_cell)
        raw_name = clean_text(player_cell)
        name, grade = split_grade(raw_name)
        if not name or name.lower().startswith("total"):
            continue
        item = {
            "name": name,
            "grade": grade,
            "team": team["name"],
            "teamSlug": team["slug"],
            "conference": team["conference"],
            "division": team["division"],
            "playerUrl": f"{BASE}{link.group(1)}" if link else "",
        }
        for idx, col in enumerate(columns, start=1):
            item[col] = parse_int(cells[idx])
        players.append(item)
    return players


def parse_stats(html, team):
    tables = re.findall(r"<table.*?</table>", html, flags=re.S | re.I)
    scorers = parse_stat_table(tables[0], ["G", "A", "P"], team) if len(tables) > 0 else []
    keepers = parse_stat_table(tables[1], ["Saves", "GP"], team) if len(tables) > 1 else []
    return scorers, keepers


def parse_logo(html):
    match = re.search(r'Logos/(\d+)\.png', html)
    if match:
        return f"https://image.maxpreps.io/school-mascot/{match.group(1)}.png"
    match = re.search(r'https?://[^"\']+Logos/[^"\']+', html)
    return unescape(match.group(0)) if match else ""


def fetch_team_payload(team):
    schedule_html = ""
    stats_html = ""
    try:
        schedule_html = fetch(team["njUrl"], timeout=16)
        time.sleep(0.03)
        stats_html = fetch(f"{team['njUrl']}/stats", timeout=16)
    except Exception as exc:
        return {**team, "error": str(exc), "schedule": [], "scorers": [], "keepers": [], "logo": ""}

    schedule = parse_schedule(schedule_html, team["slug"])
    scorers, keepers = parse_stats(stats_html, team)
    logo = parse_logo(stats_html) or parse_logo(schedule_html)
    return {**team, "schedule": schedule, "scorers": scorers, "keepers": keepers, "logo": logo}


def compute_ratings(teams):
    by_slug = {team["slug"]: team for team in teams}
    for team in teams:
        games = max(team.get("games", 0), 1)
        gd_per_game = team.get("gd", 0) / games
        attack = min(max(team.get("gfPerGame", 0) / 4.0, 0), 1)
        defense = min(max((3.0 - team.get("gaPerGame", 0)) / 3.0, 0), 1)
        margin = 0.5 + max(min(gd_per_game, 4), -4) / 8
        team["rawPower"] = 100 * (
            0.36 * team.get("winPct", 0)
            + 0.24 * margin
            + 0.18 * attack
            + 0.14 * defense
            + 0.08 * 0.5
        )

    for team in teams:
        opp_pcts = []
        opp_scores = []
        for game in team.get("schedule", []):
            opponent = by_slug.get(game.get("opponentSlug"))
            if opponent and opponent["slug"] != team["slug"]:
                opp_pcts.append(opponent.get("winPct", 0))
                opp_scores.append(opponent.get("rawPower", 0))
        team["oppWinPct"] = sum(opp_pcts) / len(opp_pcts) if opp_pcts else 0.5
        team["oppPower"] = sum(opp_scores) / len(opp_scores) if opp_scores else 50

    for team in teams:
        games = max(team.get("games", 0), 1)
        gd_per_game = team.get("gd", 0) / games
        attack = min(max(team.get("gfPerGame", 0) / 4.0, 0), 1)
        defense = min(max((3.0 - team.get("gaPerGame", 0)) / 3.0, 0), 1)
        margin = 0.5 + max(min(gd_per_game, 4), -4) / 8
        base = 100 * (
            0.36 * team.get("winPct", 0)
            + 0.24 * margin
            + 0.18 * attack
            + 0.14 * defense
            + 0.08 * team.get("oppWinPct", 0.5)
        )
        team["rawPower"] = base

    for team in teams:
        opp_power = team.get("oppPower", 50)
        team["sos"] = round(100 * (0.65 * team.get("oppWinPct", 0.5) + 0.35 * (opp_power / 100)), 1)
        adjusted = team["rawPower"] + (team["sos"] - 50) * 0.22
        team["powerScore"] = round(max(0, min(100, adjusted)), 1)

    teams.sort(key=lambda t: (t["powerScore"], t["winPct"], t["gd"]), reverse=True)
    for idx, team in enumerate(teams, start=1):
        team["rank"] = idx


def main():
    print("Fetching boys soccer conference standings...")
    all_teams = []
    seen = set()
    for conf in CONFERENCES:
        try:
            teams = parse_conference(conf)
            print(f"  {conf}: {len(teams)} teams")
            for team in teams:
                if team["slug"] in seen:
                    continue
                seen.add(team["slug"])
                all_teams.append(team)
        except Exception as exc:
            print(f"  {conf}: ERROR {exc}")
        time.sleep(0.08)

    print(f"Fetching team schedules/stats for {len(all_teams)} teams...")
    payloads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_team_payload, team) for team in all_teams]
        for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            team = future.result()
            payloads.append(team)
            if idx % 25 == 0 or idx == len(all_teams):
                print(f"  {idx}/{len(all_teams)}")

    compute_ratings(payloads)
    scorers = [player for team in payloads for player in team.get("scorers", [])]
    keepers = [player for team in payloads for player in team.get("keepers", [])]
    games = [game | {"team": team["name"], "teamSlug": team["slug"]} for team in payloads for game in team.get("schedule", [])]
    payload = {
        "season": SEASON,
        "sport": SPORT,
        "source": "highschoolsports.nj.com",
        "updated": datetime.now(timezone.utc).isoformat(),
        "teams": payloads,
        "scorers": scorers,
        "keepers": keepers,
        "games": games,
    }

    with open("js/pitch-data.js", "w", encoding="utf-8") as f:
        f.write("// Auto-generated by pitch_scraper.py from highschoolsports.nj.com boys soccer data.\n")
        f.write("const PITCH_DATA = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"Wrote js/pitch-data.js with {len(payloads)} teams, {len(scorers)} scorers, {len(keepers)} keepers.")


if __name__ == "__main__":
    main()
