#!/usr/bin/env python3
"""Build Court Index boys basketball data from NJ.com."""

import argparse
import concurrent.futures
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html import unescape
from zoneinfo import ZoneInfo

import certifi


def current_basketball_season():
    now = datetime.now(ZoneInfo("America/New_York"))
    start_year = now.year if now.month >= 7 else now.year - 1
    return f"{start_year}-{start_year + 1}"


SEASON = os.environ.get("BASKETBALL_SEASON") or current_basketball_season()
SPORT = os.environ.get("BASKETBALL_SPORT", "boysbasketball")
if SPORT not in {"boysbasketball", "girlsbasketball"}:
    raise ValueError(f"Unsupported Court Index sport: {SPORT}")
GENDER = "girls" if SPORT == "girlsbasketball" else "boys"
BASE = "https://highschoolsports.nj.com"
OUTPUT_PATH = os.environ.get("BASKETBALL_OUTPUT_PATH", "js/basketball-data.js")
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
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
    value = re.sub(r"<br\s*/?>", " ", str(value), flags=re.I)
    value = re.sub(r"<.*?>", " ", value, flags=re.S)
    value = unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def number(value):
    text = clean_text(value).replace(",", "").replace("—", "").replace("&mdash;", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return 0
    parsed = float(match.group())
    return int(parsed) if parsed.is_integer() else parsed


def parse_record(value):
    parts = [int(part) for part in re.findall(r"\d+", value or "")]
    while len(parts) < 3:
        parts.append(0)
    wins, losses, ties = parts[:3]
    games = wins + losses + ties
    pct = (wins + 0.5 * ties) / games if games else 0
    return wins, losses, ties, games, pct


def team_key(value):
    value = unescape(str(value or "")).lower().replace("&", " and ")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\b(high|school|boys|girls|basketball|prep|preparatory|academy|regional|the)\b", " ", value)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def parse_conference(conference):
    url = f"{BASE}/{SPORT}/standings/season/{SEASON}?conference={urllib.parse.quote(conference)}"
    page = fetch(url)
    table_match = re.search(r'<table[^>]*v-show="viewMode == \'Division\'"[^>]*>(.*?)</table>', page, re.S | re.I)
    table = table_match.group(1) if table_match else (re.findall(r"<table.*?</table>", page, re.S | re.I) or [""])[0]
    if not table:
        return []

    teams = []
    division = "Overall"
    for chunk in re.split(r"(<thead.*?</thead>)", table, flags=re.S | re.I):
        heading = re.search(r"<strong>(.*?)</strong>", chunk, re.S | re.I)
        if heading:
            division = clean_text(heading.group(1)) or "Overall"
            continue
        for row in re.findall(r"<tr.*?</tr>", chunk, re.S | re.I):
            href = re.search(rf'href="(/school/([^/]+)/{re.escape(SPORT)}/season/[^\"]+)"', row)
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
            if not href or len(cells) < 9:
                continue
            name = clean_text(cells[0])
            record = clean_text(cells[1])
            div_record = clean_text(cells[3])
            wins, losses, ties, games, pct = parse_record(record)
            div_wins, div_losses, div_ties, _, _ = parse_record(div_record)
            pf = int(number(cells[7]))
            pa = int(number(cells[8]))
            teams.append({
                "name": name,
                "slug": href.group(2),
                "conference": conference,
                "division": division,
                "record": record,
                "wins": wins,
                "losses": losses,
                "ties": ties,
                "games": games,
                "winPct": round(pct, 4),
                "divisionRecord": div_record,
                "divisionWins": div_wins,
                "divisionLosses": div_losses,
                "divisionTies": div_ties,
                "home": clean_text(cells[5]),
                "away": clean_text(cells[6]),
                "pf": pf,
                "pa": pa,
                "pointDiff": pf - pa,
                "pfPerGame": round(pf / games, 2) if games else 0,
                "paPerGame": round(pa / games, 2) if games else 0,
                "njUrl": f"{BASE}{href.group(1)}",
            })
    return teams


def parse_schedule(page):
    table_match = re.search(r"<table.*?</table>", page, re.S | re.I)
    if not table_match:
        return []
    games = []
    for row in re.findall(r"<tr.*?</tr>", table_match.group(0), re.S | re.I)[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        if len(cells) < 4:
            continue
        opponent_cell = cells[1]
        team_href = re.search(rf'href="(/school/([^/]+)/{re.escape(SPORT)}/season/[^\"]+)"', opponent_cell)
        game_href = re.search(r'href="(/game/\d+)[^\"]*"', row)
        opponent_text = clean_text(opponent_cell)
        opponent_alt = re.search(r'<img[^>]*alt="([^\"]+)"', opponent_cell, re.I)
        opponent_anchor = re.search(rf'<a[^>]*href="/school/[^\"]+/{re.escape(SPORT)}/[^\"]+"[^>]*>(.*?)</a>', opponent_cell, re.S | re.I)
        opponent = clean_text(opponent_alt.group(1) if opponent_alt else opponent_anchor.group(1) if opponent_anchor else opponent_cell)
        tournament_match = re.search(r"<small[^>]*>(.*?)</small>", opponent_cell, re.S | re.I)
        tournament = clean_text(tournament_match.group(1)) if tournament_match else ""
        site = "vs" if opponent_text.startswith("vs ") else "@" if opponent_text.startswith("@ ") else ""
        result_text = clean_text(cells[2])
        result_match = re.match(r"([WTL])\s+(\d+)\s*-\s*(\d+)", result_text)
        result = result_match.group(1) if result_match else ""
        first_score = int(result_match.group(2)) if result_match else None
        second_score = int(result_match.group(3)) if result_match else None
        team_score = second_score if result == "L" else first_score
        opponent_score = first_score if result == "L" else second_score
        games.append({
            "date": clean_text(cells[0]),
            "opponent": opponent.replace("vs ", "", 1).replace("@ ", "", 1).strip(),
            "opponentSlug": team_href.group(2) if team_href else "",
            "site": site,
            "result": result,
            "teamScore": team_score,
            "opponentScore": opponent_score,
            "scoreText": f"{team_score}-{opponent_score}" if team_score is not None and opponent_score is not None else "",
            "recordAfter": clean_text(cells[3]),
            "tournament": tournament,
            "gameUrl": f"{BASE}{game_href.group(1)}" if game_href else "",
            "njUrl": f"{BASE}{team_href.group(1)}" if team_href else "",
        })
    return games


def split_grade(name):
    grade = ""
    for value in ("Freshman", "Sophomore", "Junior", "Senior"):
        if re.search(rf"\b{value}\b", name):
            grade = value
            break
    base = re.split(r"\s+#\d+|\s+•|\s+(?:Freshman|Sophomore|Junior|Senior)\b", name, maxsplit=1)[0]
    return base.strip(), grade


def parse_logo(html):
    match = re.search(r"Logos/(\d+)\.png", html)
    if match:
        return f"https://nj.vsand-static.com/Logos/{match.group(1)}.png"
    match = re.search(r'https?://[^"\']+Logos/[^"\']+', html)
    return unescape(match.group(0)) if match else ""


def parse_players(stats_html, team):
    tables = re.findall(r"<table.*?</table>", stats_html, re.S | re.I)
    if not tables:
        return []
    rows = re.findall(r"<tr.*?</tr>", tables[0], re.S | re.I)
    if len(rows) < 2:
        return []
    headers = [clean_text(cell) for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", rows[0], re.S | re.I)]
    index = {header: i for i, header in enumerate(headers)}
    players = []
    for row in rows[1:]:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
        if len(cells) < 2:
            continue
        raw_name = clean_text(cells[0])
        name, grade = split_grade(raw_name)
        if not name or name.lower().startswith("total"):
            continue
        link = re.search(r'href="([^"]+)"', cells[0])
        player = {
            "name": name,
            "grade": grade,
            "team": team["name"],
            "teamSlug": team["slug"],
            "conference": team["conference"],
            "division": team["division"],
            "playerUrl": f"{BASE}{link.group(1)}" if link else "",
        }
        for col in ("2PT", "3PT", "FTM", "FTA", "PTS", "REB", "AST", "BLK", "STL", "GP"):
            player[col] = number(cells[index[col]]) if col in index and index[col] < len(cells) else 0
        players.append(player)
    return players


def add_player_metrics(players, team):
    team_pts = sum(player.get("PTS", 0) for player in players) or team.get("pf", 0)
    team_reb = sum(player.get("REB", 0) for player in players)
    team_ast = sum(player.get("AST", 0) for player in players)
    team["statPoints"] = team_pts
    team["statRebounds"] = team_reb
    team["statAssists"] = team_ast
    for player in players:
        gp = max(player.get("GP", 0), 1)
        pts = player.get("PTS", 0)
        reb = player.get("REB", 0)
        ast = player.get("AST", 0)
        stl = player.get("STL", 0)
        blk = player.get("BLK", 0)
        fta = player.get("FTA", 0)
        points_responsible = pts + 2 * ast
        player["PPG"] = round(pts / gp, 1)
        player["RPG"] = round(reb / gp, 1)
        player["APG"] = round(ast / gp, 1)
        player["SPG"] = round(stl / gp, 1)
        player["BPG"] = round(blk / gp, 1)
        player["StocksPG"] = round((stl + blk) / gp, 1)
        player["FTPct"] = round((player.get("FTM", 0) / fta) * 100, 1) if fta else 0
        player["TeamScoringShare"] = round((pts / team_pts) * 100, 1) if team_pts else 0
        player["TeamReboundingShare"] = round((reb / team_reb) * 100, 1) if team_reb else 0
        player["TeamAssistShare"] = round((ast / team_ast) * 100, 1) if team_ast else 0
        player["PointsResponsible"] = points_responsible
        player["PointsResponsiblePG"] = round(points_responsible / gp, 1)
        player["OffensiveInvolvement"] = round((points_responsible / team_pts) * 100, 1) if team_pts else 0
        player["TwoPointShare"] = round(((2 * player.get("2PT", 0)) / pts) * 100, 1) if pts else 0
        player["ThreePointShare"] = round(((3 * player.get("3PT", 0)) / pts) * 100, 1) if pts else 0
        player["FTShare"] = round((player.get("FTM", 0) / pts) * 100, 1) if pts else 0
        player["playerScore"] = round(
            min(100, max(0,
                player["PPG"] * 2.2
                + player["RPG"] * 1.6
                + player["APG"] * 2.0
                + player["StocksPG"] * 3.0
                + player["FTPct"] * 0.08
                + player["OffensiveInvolvement"] * 0.45
            )),
            1,
        )


def fetch_team(team):
    try:
        schedule_html = fetch(team["njUrl"], timeout=16)
        time.sleep(0.03)
        stats_html = fetch(f"{team['njUrl']}/stats", timeout=16)
    except Exception as exc:
        return {**team, "error": str(exc), "schedule": [], "players": [], "logo": ""}
    players = parse_players(stats_html, team)
    add_player_metrics(players, team)
    return {**team, "schedule": parse_schedule(schedule_html), "players": players, "logo": parse_logo(stats_html) or parse_logo(schedule_html)}


def compute_ratings(teams):
    by_slug = {team["slug"]: team for team in teams}
    by_name = {team_key(team["name"]): team for team in teams if team_key(team["name"])}
    league_ppg = sum(team.get("pf", 0) for team in teams) / max(sum(team.get("games", 0) for team in teams), 1)
    league_ppg = max(league_ppg, 45)

    def opponent_for(game):
        if game.get("opponentSlug") in by_slug:
            return by_slug[game["opponentSlug"]]
        key = team_key(game.get("opponent"))
        if key in by_name:
            return by_name[key]
        return None

    for team in teams:
        games = max(team.get("games", 0), 1)
        team["rawOffense"] = team.get("pf", 0) / games
        team["rawDefense"] = team.get("pa", 0) / games
        team["adjO"] = team["rawOffense"] or league_ppg
        team["adjD"] = team["rawDefense"] or league_ppg

    for _ in range(10):
        next_values = []
        for team in teams:
            opponents = [opponent_for(game) for game in team.get("schedule", [])]
            opponents = [opp for opp in opponents if opp and opp["slug"] != team["slug"]]
            avg_opp_def = sum(opp.get("adjD", league_ppg) for opp in opponents) / len(opponents) if opponents else league_ppg
            avg_opp_off = sum(opp.get("adjO", league_ppg) for opp in opponents) / len(opponents) if opponents else league_ppg
            next_values.append((team, team["rawOffense"] * (league_ppg / max(avg_opp_def, 35)) ** 0.45, team["rawDefense"] * (league_ppg / max(avg_opp_off, 35)) ** 0.45))
        for team, adj_o, adj_d in next_values:
            team["adjO"] = max(20, min(adj_o, 95))
            team["adjD"] = max(20, min(adj_d, 95))

    for team in teams:
        opponents = [opponent_for(game) for game in team.get("schedule", [])]
        opponents = [opp for opp in opponents if opp and opp["slug"] != team["slug"]]
        sos = sum(opp.get("winPct", 0.5) for opp in opponents) / len(opponents) if opponents else 0.5
        margin_pg = team.get("pointDiff", 0) / max(team.get("games", 0), 1)
        efficiency = 50 + (team.get("adjO", league_ppg) - team.get("adjD", league_ppg)) * 1.25
        raw = 0.45 * efficiency + 0.25 * team.get("winPct", 0) * 100 + 0.20 * sos * 100 + 0.10 * (50 + max(-25, min(25, margin_pg)) * 2)
        team["sos"] = round(sos * 100, 1)
        team["powerScore"] = round(max(0, min(100, raw)), 1)
        team["adjO"] = round(team["adjO"], 1)
        team["adjD"] = round(team["adjD"], 1)
    teams.sort(key=lambda team: (team["powerScore"], team["winPct"], team["sos"], team["pointDiff"]), reverse=True)
    for idx, team in enumerate(teams, 1):
        team["rank"] = idx


def load_existing():
    try:
        text = open(OUTPUT_PATH, encoding="utf-8").read()
        return json.loads(text.split("const BASKETBALL_DATA = ", 1)[1].rsplit(";", 1)[0])
    except (OSError, IndexError, json.JSONDecodeError):
        return {}


def main():
    parser = argparse.ArgumentParser(description="Refresh Court Index basketball data from NJ.com")
    parser.add_argument("--limit", type=int, default=0, help="Development-only team limit")
    args = parser.parse_args()
    existing = load_existing()

    print(f"Fetching {SEASON} {GENDER} basketball standings...")
    teams = []
    seen = set()
    conference_counts = {}
    for conference in CONFERENCES:
        try:
            conference_teams = parse_conference(conference)
            conference_counts[conference] = len(conference_teams)
            print(f"  {conference}: {len(conference_teams)} teams")
            for team in conference_teams:
                if team["slug"] not in seen:
                    seen.add(team["slug"])
                    teams.append(team)
        except Exception as exc:
            conference_counts[conference] = 0
            print(f"  {conference}: ERROR {exc}")
        time.sleep(0.05)
    if any(count == 0 for count in conference_counts.values()) and not args.limit:
        raise RuntimeError(f"Refusing incomplete conference data: {conference_counts}")
    if len(teams) < 300 and not args.limit:
        raise RuntimeError(f"Refusing incomplete statewide data: only {len(teams)} teams")
    if args.limit:
        teams = teams[:args.limit]

    print(f"Fetching schedules and stats for {len(teams)} teams...")
    payloads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_team, team) for team in teams]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            payloads.append(future.result())
            if index % 25 == 0 or index == len(teams):
                print(f"  {index}/{len(teams)}")

    failures = [team for team in payloads if team.get("error")]
    existing_by_slug = {team.get("slug"): team for team in existing.get("teams", [])}
    missing = [team["slug"] for team in failures if team["slug"] not in existing_by_slug]
    if missing and not args.limit:
        raise RuntimeError(f"Refusing incomplete data: {len(missing)} team pages failed without prior data")
    if failures:
        payloads = [existing_by_slug.get(team["slug"], team) if team.get("error") else team for team in payloads]

    payloads.sort(key=lambda team: team["slug"])
    compute_ratings(payloads)
    players = [player for team in payloads for player in team.get("players", [])]
    games = [{**game, "team": team["name"], "teamSlug": team["slug"]} for team in payloads for game in team.get("schedule", [])]
    for team in payloads:
        team.pop("players", None)

    payload = {
        "season": SEASON,
        "sport": SPORT,
        "gender": GENDER,
        "source": "highschoolsports.nj.com",
        "teams": payloads,
        "players": players,
        "games": games,
    }
    comparable = {key: value for key, value in existing.items() if key != "updated"}
    if payload == comparable and not args.limit:
        print("NJ.com data is unchanged; keeping the existing file.")
        return
    payload["updated"] = datetime.now(timezone.utc).isoformat()
    output = OUTPUT_PATH if not args.limit else "/tmp/basketball-data-test.js"
    temp = f"{output}.tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write("// Auto-generated by basketball_scraper.py from highschoolsports.nj.com basketball data.\n")
        handle.write("const BASKETBALL_DATA = ")
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write(";\n")
    os.replace(temp, output)
    print(f"Wrote {output}: {len(payloads)} teams, {len(players)} players, {len(games)} schedule rows.")


if __name__ == "__main__":
    main()

