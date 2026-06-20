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


def team_key(value):
    value = unescape(str(value or "")).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\b(high|school|boys|soccer|prep|preparatory|academy|regional|the)\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


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
    by_name = {}
    for team in teams:
        key = team_key(team["name"])
        if key:
            by_name[key] = team

    def opponent_for(game):
        slug = game.get("opponentSlug")
        if slug and slug in by_slug:
            return by_slug[slug]
        opp_key = team_key(game.get("opponent"))
        if opp_key in by_name:
            return by_name[opp_key]
        for key, team in by_name.items():
            if opp_key and (opp_key == key or opp_key.startswith(f"{key} ") or key.startswith(f"{opp_key} ")):
                return team
        return None

    total_games = sum(team.get("games", 0) for team in teams) or 1
    league_gf_pg = sum(team.get("gf", 0) for team in teams) / total_games
    league_ga_pg = sum(team.get("ga", 0) for team in teams) / total_games
    league_runs = max((league_gf_pg + league_ga_pg) / 2, 0.35)

    for team in teams:
        games = max(team.get("games", 0), 1)
        team["rawOffense"] = team.get("gf", 0) / games
        team["rawDefense"] = team.get("ga", 0) / games
        team["adjO"] = team["rawOffense"] or league_runs
        team["adjD"] = team["rawDefense"] or league_runs

    # Soccer version of Diamond's adjusted efficiency loop:
    # scoring is boosted for facing strong defenses, and goals allowed are
    # discounted for facing strong offenses.
    for _ in range(14):
        next_values = []
        for team in teams:
            opponents = [
                opponent_for(game)
                for game in team.get("schedule", [])
            ]
            opponents = [opp for opp in opponents if opp and opp["slug"] != team["slug"]]
            avg_opp_def = sum(opp.get("adjD", league_runs) for opp in opponents) / len(opponents) if opponents else league_runs
            avg_opp_off = sum(opp.get("adjO", league_runs) for opp in opponents) / len(opponents) if opponents else league_runs
            off_factor = (league_runs / max(avg_opp_def, 0.35)) ** 0.45
            def_factor = (league_runs / max(avg_opp_off, 0.35)) ** 0.45
            adj_o = team["rawOffense"] * off_factor
            adj_d = team["rawDefense"] * def_factor
            next_values.append((team, max(0, min(adj_o, 5.75)), max(0.05, min(adj_d, 5.75))))
        for team, adj_o, adj_d in next_values:
            team["adjO"] = adj_o
            team["adjD"] = adj_d

    exponent = 1.35
    for team in teams:
        opponents = [
            opponent_for(game)
            for game in team.get("schedule", [])
        ]
        opponents = [opp for opp in opponents if opp and opp["slug"] != team["slug"]]
        opp_wpcts = []
        opp_exp = []
        for opp in opponents:
            opp_o = max(opp.get("adjO", league_runs), 0.01)
            opp_d = max(opp.get("adjD", league_runs), 0.01)
            opp_expected = (opp_o ** exponent) / ((opp_o ** exponent) + (opp_d ** exponent))
            opp_wpcts.append(opp.get("winPct", 0.5))
            opp_exp.append(opp_expected)

        adj_o = max(team.get("adjO", 0), 0.01)
        adj_d = max(team.get("adjD", 0), 0.01)
        expected = (adj_o ** exponent) / ((adj_o ** exponent) + (adj_d ** exponent))
        team["expectedWinPct"] = expected
        team["expectedRecord"] = f"{round(expected * team.get('games', 0), 1)}-{round((1 - expected) * team.get('games', 0), 1)}"
        team["luck"] = team.get("winPct", 0) - expected
        team["oppWinPct"] = sum(opp_wpcts) / len(opp_wpcts) if opp_wpcts else 0.5
        team["sos"] = round((sum(opp_exp) / len(opp_exp) if opp_exp else 0.5) * 100, 1)
        team["powerScore"] = round(max(0, min(100, expected * 100)), 1)
        team["adjO"] = round(team["adjO"], 2)
        team["adjD"] = round(team["adjD"], 2)
        team["expectedWinPct"] = round(team["expectedWinPct"], 3)
        team["luck"] = round(team["luck"], 3)

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
