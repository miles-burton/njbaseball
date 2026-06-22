#!/usr/bin/env python3
"""
Pitch Index boys soccer data scraper.

Pulls real boys soccer standings, schedules, scoring, goalkeeping, and player
game logs from highschoolsports.nj.com for the current academic season.
"""

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


def current_soccer_season():
    now = datetime.now(ZoneInfo("America/New_York"))
    start_year = now.year if now.month >= 7 else now.year - 1
    return f"{start_year}-{start_year + 1}"


SEASON = os.environ.get("PITCH_SEASON", current_soccer_season())
SPORT = "boyssoccer"
BASE = "https://highschoolsports.nj.com"
OUTPUT_PATH = "js/pitch-data.js"
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


def table_rows(table):
    rows = []
    for row in re.findall(r"<tr.*?</tr>", table, flags=re.S | re.I):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        if cells:
            rows.append([clean_text(cell) for cell in cells])
    return rows


def parse_player_game_logs(html):
    logs = {}
    for table in re.findall(r"<table.*?</table>", html, flags=re.S | re.I):
        rows = table_rows(table)
        if len(rows) < 2:
            continue
        header = rows[0]
        if len(header) < 3 or header[0] != "Date" or header[1] != "Opponent" or header[2] != "Result":
            continue

        index = {name: idx for idx, name in enumerate(header)}
        parsed = []
        for row in rows[1:]:
            if not row or "total" in row[0].lower():
                continue
            row += [""] * (len(header) - len(row))
            item = {
                "date": row[index["Date"]],
                "opponent": row[index["Opponent"]],
                "result": row[index["Result"]],
            }
            for col in ("G", "A", "P", "Saves", "GP"):
                if col in index:
                    item[col] = parse_int(row[index[col]])
            parsed.append(item)

        if not parsed:
            continue
        if all(col in index for col in ("G", "A", "P")):
            logs["scoring"] = parsed
        elif "Saves" in index:
            logs["keepers"] = parsed
    return logs


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


def fetch_player_logs(player_url):
    if not player_url:
        return player_url, {}
    try:
        html = fetch(player_url, timeout=14)
        return player_url, parse_player_game_logs(html)
    except Exception:
        return player_url, {}


def load_existing_payload():
    try:
        text = open(OUTPUT_PATH, encoding="utf-8").read()
        payload_text = text.split("const PITCH_DATA = ", 1)[1].rsplit(";", 1)[0]
        return json.loads(payload_text)
    except (OSError, IndexError, json.JSONDecodeError):
        return {}


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

    def clamp(value, low, high):
        return max(low, min(high, value))

    def normalize(value, low, high):
        if high == low:
            return 0.5
        return clamp((value - low) / (high - low), 0, 1)

    def game_result_value(game):
        result = game.get("result")
        if result == "W":
            return 1
        if result == "T":
            return 0.5
        if result == "L":
            return 0
        return None

    def team_margin(game):
        team_score = game.get("teamScore")
        opponent_score = game.get("opponentScore")
        if team_score is None or opponent_score is None:
            return 0
        if game.get("result") == "W":
            return team_score - opponent_score
        if game.get("result") == "L":
            return opponent_score - team_score
        return 0

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
        quality_games = []
        quality_wins = 0
        top_25_wins = 0
        top_50_wins = 0
        elite_result_bonus = 0
        for opp in opponents:
            opp_o = max(opp.get("adjO", league_runs), 0.01)
            opp_d = max(opp.get("adjD", league_runs), 0.01)
            opp_expected = (opp_o ** exponent) / ((opp_o ** exponent) + (opp_d ** exponent))
            opp_wpcts.append(opp.get("winPct", 0.5))
            opp_exp.append(opp_expected)

        for game in team.get("schedule", []):
            opp = opponent_for(game)
            result_value = game_result_value(game)
            if not opp or result_value is None or opp["slug"] == team["slug"]:
                continue
            opp_o = max(opp.get("adjO", league_runs), 0.01)
            opp_d = max(opp.get("adjD", league_runs), 0.01)
            opp_expected = (opp_o ** exponent) / ((opp_o ** exponent) + (opp_d ** exponent))
            margin_score = clamp(team_margin(game) / 4, -1, 1)
            quality_games.append(((result_value - 0.5) * 2 * (0.65 + 0.70 * opp_expected)) + (0.12 * margin_score))
            opp_strength = opp_expected * 100
            if result_value == 1 and opp_strength >= 80:
                quality_wins += 1
                top_50_wins += 1
                elite_result_bonus += 0.75
            if result_value == 1 and opp_strength >= 85:
                top_25_wins += 1
                elite_result_bonus += 1.00
            if result_value == 1 and opp_strength >= 90:
                elite_result_bonus += 0.75
            if result_value == 0.5 and opp_strength >= 85:
                elite_result_bonus += 0.50
            if result_value == 0 and opp_strength >= 90 and abs(team_margin(game)) <= 1:
                elite_result_bonus += 0.25

        adj_o = max(team.get("adjO", 0), 0.01)
        adj_d = max(team.get("adjD", 0), 0.01)
        expected = (adj_o ** exponent) / ((adj_o ** exponent) + (adj_d ** exponent))
        gd_per_game = team.get("gd", 0) / max(team.get("games", 0), 1)
        efficiency_score = expected * 100
        result_score = team.get("winPct", 0) * 100
        sos_score = (sum(opp_exp) / len(opp_exp) if opp_exp else 0.5) * 100
        goal_profile_score = normalize(gd_per_game, -1.5, 4.0) * 100
        quality_score = clamp(50 + ((sum(quality_games) / len(quality_games)) / 2.2 * 100 if quality_games else 0), 0, 100)
        elite_result_bonus = min(elite_result_bonus, 10)

        # Pitch Score blends predictive efficiency with earned results. The
        # efficiency component keeps the model stable, while record, schedule,
        # quality wins, and goal profile prevent low-SOS blowout profiles from
        # outranking teams that proved it against elite opponents.
        raw_index = (
            0.42 * efficiency_score
            + 0.18 * result_score
            + 0.16 * sos_score
            + 0.16 * quality_score
            + 0.08 * goal_profile_score
            + elite_result_bonus
        )
        team["expectedWinPct"] = expected
        team["expectedRecord"] = f"{round(expected * team.get('games', 0), 1)}-{round((1 - expected) * team.get('games', 0), 1)}"
        team["luck"] = team.get("winPct", 0) - expected
        team["oppWinPct"] = sum(opp_wpcts) / len(opp_wpcts) if opp_wpcts else 0.5
        team["sos"] = round(sos_score, 1)
        team["qualityScore"] = round(quality_score, 1)
        team["qualityWins"] = quality_wins
        team["top25Wins"] = top_25_wins
        team["top50Wins"] = top_50_wins
        team["rawPower"] = raw_index
        team["adjO"] = round(team["adjO"], 2)
        team["adjD"] = round(team["adjD"], 2)
        team["expectedWinPct"] = round(team["expectedWinPct"], 3)
        team["luck"] = round(team["luck"], 3)

    max_raw = max((team.get("rawPower", 0) for team in teams), default=100) or 100
    for team in teams:
        team["powerScore"] = round(max(0, min(100, team.get("rawPower", 0) / max_raw * 100)), 1)

    teams.sort(key=lambda t: (t["powerScore"], t["winPct"], t["sos"], t["gd"]), reverse=True)
    for idx, team in enumerate(teams, start=1):
        team["rank"] = idx


def main():
    parser = argparse.ArgumentParser(description="Refresh Pitch Index data from NJ.com")
    parser.add_argument(
        "--skip-player-logs",
        action="store_true",
        help="Refresh teams, schedules, and leaderboards while preserving existing player logs",
    )
    args = parser.parse_args()
    existing_payload = load_existing_payload()

    print(f"Fetching {SEASON} boys soccer conference standings...")
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

    if len(all_teams) < 300:
        raise RuntimeError(f"Refusing to publish incomplete NJ.com data: only {len(all_teams)} teams found")

    print(f"Fetching team schedules/stats for {len(all_teams)} teams...")
    payloads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_team_payload, team) for team in all_teams]
        for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            team = future.result()
            payloads.append(team)
            if idx % 25 == 0 or idx == len(all_teams):
                print(f"  {idx}/{len(all_teams)}")

    successful_payloads = [team for team in payloads if not team.get("error")]
    failed_count = len(payloads) - len(successful_payloads)
    if len(successful_payloads) < int(len(all_teams) * 0.85):
        raise RuntimeError(
            f"Refusing to publish incomplete NJ.com data: only {len(successful_payloads)}/{len(all_teams)} team pages succeeded"
        )

    existing_by_slug = {
        team.get("slug"): team
        for team in existing_payload.get("teams", [])
        if existing_payload.get("season") == SEASON and team.get("slug")
    }
    unrecovered = [team["slug"] for team in payloads if team.get("error") and team["slug"] not in existing_by_slug]
    if unrecovered:
        raise RuntimeError(
            f"Refusing to publish incomplete NJ.com data: {len(unrecovered)} failed team pages have no prior data"
        )
    if failed_count:
        print(f"Preserving last known good data for {failed_count} temporarily unavailable team pages.")
        payloads = [{**existing_by_slug[team["slug"]]} if team.get("error") else team for team in payloads]

    payloads.sort(key=lambda team: team["slug"])
    compute_ratings(payloads)
    scorers = [player for team in payloads for player in team.get("scorers", [])]
    keepers = [player for team in payloads for player in team.get("keepers", [])]
    games = [game | {"team": team["name"], "teamSlug": team["slug"]} for team in payloads for game in team.get("schedule", [])]
    player_urls = sorted({player.get("playerUrl", "") for player in [*scorers, *keepers] if player.get("playerUrl")})
    existing_logs = existing_payload.get("playerLogs", {})
    player_logs = {url: existing_logs[url] for url in player_urls if url in existing_logs}
    if args.skip_player_logs:
        print(f"Preserving {len(player_logs)} existing player game logs (fast refresh).")
    else:
        print(f"Fetching player game logs for {len(player_urls)} players...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
            futures = [executor.submit(fetch_player_logs, url) for url in player_urls]
            for idx, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                url, logs = future.result()
                if logs:
                    player_logs[url] = logs
                if idx % 250 == 0 or idx == len(player_urls):
                    print(f"  {idx}/{len(player_urls)}")

    payload = {
        "season": SEASON,
        "sport": SPORT,
        "source": "highschoolsports.nj.com",
        "teams": payloads,
        "scorers": scorers,
        "keepers": keepers,
        "games": games,
        "playerLogs": player_logs,
    }

    comparable_existing = {key: value for key, value in existing_payload.items() if key != "updated"}
    if payload == comparable_existing:
        print("NJ.com data is unchanged; keeping the existing data file.")
        return

    payload["updated"] = datetime.now(timezone.utc).isoformat()

    temp_path = f"{OUTPUT_PATH}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write("// Auto-generated by pitch_scraper.py from highschoolsports.nj.com boys soccer data.\n")
        f.write("const PITCH_DATA = ")
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    os.replace(temp_path, OUTPUT_PATH)
    print(f"Wrote js/pitch-data.js with {len(payloads)} teams, {len(scorers)} scorers, {len(keepers)} keepers, {len(player_logs)} player logs.")


if __name__ == "__main__":
    main()
