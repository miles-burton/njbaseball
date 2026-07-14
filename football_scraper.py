#!/usr/bin/env python3
"""Build Gridiron Index football data from NJ.com."""

import argparse
import concurrent.futures
import json
import math
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


def current_football_season():
    now = datetime.now(ZoneInfo("America/New_York"))
    start_year = now.year if now.month >= 7 else now.year - 1
    return f"{start_year}-{start_year + 1}"


SEASON = os.environ.get("FOOTBALL_SEASON") or current_football_season()
BASE = "https://highschoolsports.nj.com"
OUTPUT_PATH = os.environ.get("FOOTBALL_OUTPUT_PATH", "js/football-data.js")
CONFERENCES = ["Big Central", "Independent", "NJIC", "SFC", "Shore", "WJFL"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
CTX = ssl.create_default_context(cafile=certifi.where())

# Football has a bigger schedule-context problem than baseball or soccer:
# national opponents, private-school schedules, and roster strength are not
# fully captured by NJ.com box scores. These priors are intentionally small,
# but they keep the model aligned with common NJ top-20 poll context.
FOOTBALL_POLL_PRIORS = {
    "ramsey-don-bosco-prep": 100,
    "montvale-st-joseph-mont": 98,
    "oradell-bergen-catholic": 96,
    "atco-winslow": 92,
    "wayne-depaul": 89,
    "jersey-city-st-peters-prep": 88,
    "old-tappan-old-tappan": 86,
    "franklin-lakes-ramapo": 84,
    "west-orange-seton-hall-prep": 82,
    "richland-st-augustine": 82,
    "red-bank-red-bank-catholic": 82,
    "toms-river-toms-river-north": 81,
    "millville-millville": 80,
    "linwood-mainland": 79,
    "washington-township-washington-township": 79,
    "somerville-somerville": 78,
    "egg-harbor-city-cedar-creek": 77,
    "willingboro-willingboro": 76,
    "camden-camden": 76,
    "clifton-passaic-tech": 75,
    "englishtown-manalapan": 75,
    "union-city-union-city": 75,
}

EXTERNAL_OPPONENT_PRIORS = {
    "img academy": 100,
    "east st. louis": 94,
    "st. john": 88,
    "hun school": 88,
    "west boca": 86,
    "cardinal hayes": 84,
    "melissa": 82,
    "st. anthony": 82,
    "monarch": 80,
    "st. thomas more": 78,
    "springside": 75,
    "mt. zion": 65,
}

TABLE_SCHEMAS = [
    ("passing", ["Cmp", "PassAtt", "PassYds", "PassTD", "INT", "PassLng"]),
    ("rushing", ["RushAtt", "RushYds", "RushTD", "RushLng"]),
    ("receiving", ["Rec", "RecYds", "RecTD", "RecLng"]),
    ("defense", ["Sacks", "TFL", "Solo", "Ast", "Tackles", "FF", "FR", "FumTD", "DefINT", "IntTD", "Safety", "KB"]),
    ("returns", ["KORAtt", "KORYds", "KORLng", "KORTD", "PRAtt", "PRYds", "PRLng", "PRTD"]),
    ("kicking", ["FGM", "FGA", "FGLng", "XPM", "XPA", "TwoPT"]),
    ("punting", ["Punts", "PuntYds", "PuntLng", "Inside20"]),
]


def fetch(url, timeout=18):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout, context=CTX) as response:
        return response.read().decode("utf-8", "ignore")


def clean_text(value):
    value = re.sub(r"<br\s*/?>", " ", str(value), flags=re.I)
    value = re.sub(r"<.*?>", " ", value, flags=re.S)
    value = unescape(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def number(value):
    text = clean_text(value).replace(",", "").replace("—", "").strip()
    if not text or text == "-":
        return 0
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
    return wins, losses, ties, games, (wins + 0.5 * ties) / games if games else 0


def team_key(value):
    value = unescape(str(value or "")).lower().replace("&", " and ")
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"\b(high|school|football|prep|preparatory|academy|regional|the)\b", " ", value)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value)).strip()


def parse_conference(conference):
    url = f"{BASE}/football/standings/season/{SEASON}?conference={urllib.parse.quote(conference)}"
    page = fetch(url)
    table_match = re.search(r'<table[^>]*v-show="viewMode == \'Division\'"[^>]*>(.*?)</table>', page, re.S | re.I)
    if not table_match:
        tables = re.findall(r"<table.*?</table>", page, re.S | re.I)
        table = tables[0] if tables else ""
    else:
        table = table_match.group(1)
    if not table:
        return []

    teams = []
    division = "Overall"
    for chunk in re.split(r"(<thead.*?</thead>)", table, flags=re.S | re.I):
        heading = re.search(r"<strong>(.*?)</strong>", chunk, re.S | re.I)
        if heading:
            division = clean_text(heading.group(1)) or "Independent"
            continue
        for row in re.findall(r"<tr.*?</tr>", chunk, re.S | re.I):
            href = re.search(r'href="(/school/([^/]+)/football/season/[^\"]+)"', row)
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
            if not href or len(cells) < 9:
                continue
            name = clean_text(cells[0])
            record = clean_text(cells[1])
            div_record = clean_text(cells[3])
            wins, losses, ties, games, win_pct = parse_record(record)
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
                "winPct": round(win_pct, 4),
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
        team_href = re.search(r'href="(/school/([^/]+)/football/season/[^\"]+)"', opponent_cell)
        game_href = re.search(r'href="(/game/\d+)[^\"]*"', row)
        opponent_text = clean_text(opponent_cell)
        opponent_alt = re.search(r'<img[^>]*alt="([^\"]+)"', opponent_cell, re.I)
        opponent_anchor = re.search(r'<a[^>]*href="/school/[^\"]+"[^>]*>(.*?)</a>', opponent_cell, re.S | re.I)
        opponent = clean_text(opponent_alt.group(1) if opponent_alt else opponent_anchor.group(1) if opponent_anchor else opponent_cell)
        tournament_match = re.search(r"<small[^>]*>(.*?)</small>", opponent_cell, re.S | re.I)
        tournament = clean_text(tournament_match.group(1)) if tournament_match else ""
        site_match = re.search(r'<span[^>]*class="[^"]*mr-2[^"]*"[^>]*>(vs|@)</span>', opponent_cell, re.S | re.I)
        site = clean_text(site_match.group(1)) if site_match else "vs" if opponent_text.startswith("vs ") else "@" if opponent_text.startswith("@ ") else ""
        result_text = clean_text(cells[2])
        result_match = re.match(r"([WTL])\s+(\d+)\s*-\s*(\d+)", result_text)
        opponent = opponent.replace("vs ", "", 1).replace("@ ", "", 1).strip()
        result = result_match.group(1) if result_match else ""
        first_score = int(result_match.group(2)) if result_match else None
        second_score = int(result_match.group(3)) if result_match else None
        team_score = second_score if result == "L" else first_score
        opponent_score = first_score if result == "L" else second_score
        games.append({
            "date": clean_text(cells[0]),
            "opponent": opponent,
            "opponentSlug": team_href.group(2) if team_href else "",
            "site": site,
            "result": result,
            "teamScore": team_score,
            "opponentScore": opponent_score,
            "scoreText": f"{first_score}-{second_score}" if result_match else "",
            "recordAfter": clean_text(cells[3]),
            "tournament": tournament,
            "gameUrl": f"{BASE}{game_href.group(1)}" if game_href else "",
            "njUrl": f"{BASE}{team_href.group(1)}" if team_href else "",
        })
    return games


def link_schedule_opponents(teams):
    by_name = {team_key(team["name"]): team["slug"] for team in teams}
    for team in teams:
        for game in team.get("schedule", []):
            if game.get("opponentSlug"):
                continue
            key = team_key(game.get("opponent"))
            if key in by_name:
                game["opponentSlug"] = by_name[key]
                continue
            for candidate, slug in by_name.items():
                if key and (candidate.startswith(key) or key.startswith(candidate)):
                    game["opponentSlug"] = slug
                    break


def player_identity(cell, team):
    raw = clean_text(cell)
    link = re.search(r'href="([^\"]+)"[^>]*>(.*?)</a>', cell, re.S | re.I)
    name = clean_text(link.group(2)) if link else re.split(r"\s+#\d+|\s+•|\s+(?:Freshman|Sophomore|Junior|Senior)$", raw, maxsplit=1)[0].strip()
    grade_match = re.search(r"\b(Freshman|Sophomore|Junior|Senior)\b", raw)
    position_match = re.search(r"(?:Freshman|Sophomore|Junior|Senior)\s+•\s+(.+)$", raw)
    if not position_match:
        pieces = [piece.strip() for piece in raw.split("•")]
        position_match_value = pieces[-1] if len(pieces) >= 3 else ""
    else:
        position_match_value = position_match.group(1)
    url = f"{BASE}{link.group(1)}" if link else ""
    key = f"{team['slug']}::{name.lower()}"
    return key, {
        "name": name,
        "grade": grade_match.group(1) if grade_match else "",
        "position": position_match_value,
        "team": team["name"],
        "teamSlug": team["slug"],
        "conference": team["conference"],
        "division": team["division"],
        "playerUrl": url,
    }


def parse_players(stats_page, team):
    players = {}
    tables = re.findall(r"<table.*?</table>", stats_page, re.S | re.I)
    for table_index, (group, columns) in enumerate(TABLE_SCHEMAS):
        if table_index >= len(tables):
            continue
        rows = re.findall(r"<tr.*?</tr>", tables[table_index], re.S | re.I)[1:]
        for row in rows:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)
            if len(cells) < len(columns) + 1:
                continue
            key, identity = player_identity(cells[0], team)
            if not identity["name"] or identity["name"].lower().startswith("total"):
                continue
            player = players.setdefault(key, {**identity, "groups": []})
            repeated_group = group in player["groups"]
            if not player.get("grade") and identity.get("grade"):
                player["grade"] = identity["grade"]
            if not player.get("position") and identity.get("position"):
                player["position"] = identity["position"]
            if identity.get("playerUrl") and (not player.get("playerUrl") or len(identity["playerUrl"]) < len(player["playerUrl"])):
                player["playerUrl"] = identity["playerUrl"]
            if not repeated_group:
                player["groups"].append(group)
            for index, column in enumerate(columns, start=1):
                parsed = number(cells[index])
                player[column] = player.get(column, 0) + parsed if repeated_group else parsed
    return list(players.values())


def parse_logo(page):
    match = re.search(r"https://nj\.vsand-static\.com/Logos/(\d+)\.png", page)
    return f"https://nj.vsand-static.com/Logos/{match.group(1)}.png?404=missinglogo&maxheight=220" if match else ""


def fetch_team(team):
    try:
        schedule_page = fetch(team["njUrl"], timeout=18)
        time.sleep(0.02)
        stats_page = fetch(f"{team['njUrl']}/stats", timeout=18)
        return {
            **team,
            "schedule": parse_schedule(schedule_page),
            "players": parse_players(stats_page, team),
            "logo": parse_logo(stats_page) or parse_logo(schedule_page),
        }
    except Exception as exc:
        return {**team, "error": str(exc), "schedule": [], "players": [], "logo": ""}


def opponent_lookup(teams):
    by_slug = {team["slug"]: team for team in teams}
    by_name = {team_key(team["name"]): team for team in teams}

    def find(game):
        if game.get("opponentSlug") in by_slug:
            return by_slug[game["opponentSlug"]]
        key = team_key(game.get("opponent"))
        if key in by_name:
            return by_name[key]
        for candidate, team in by_name.items():
            if key and (candidate.startswith(key) or key.startswith(candidate)):
                return team
        return None

    return find


def external_opponent_rating(name):
    text = clean_text(name).lower()
    for key, rating in EXTERNAL_OPPONENT_PRIORS.items():
        if key in text:
            return rating
    # If NJ.com gives a state in parentheses, treat it as a real outside-NJ
    # opponent instead of dropping the game from SOS entirely.
    if re.search(r"\([a-z]{2,}\)", text):
        return 72
    return None


def playoff_result_bonus(game, margin):
    tournament = clean_text(game.get("tournament", "")).lower()
    if not tournament:
        return 0
    if "quarterfinal" in tournament:
        bonus = 1.5
    elif "semifinal" in tournament:
        bonus = 3
    elif "final round" in tournament or ("championship" in tournament and "final" in tournament):
        bonus = 5
    else:
        bonus = 1
    return bonus if margin > 0 else -bonus if margin < 0 else 0


def compute_team_ratings(teams):
    find_opponent = opponent_lookup(teams)
    total_games = sum(team["games"] for team in teams) or 1
    league_points = sum(team["pf"] for team in teams) / total_games
    for team in teams:
        team["rawOffense"] = team["pfPerGame"]
        team["rawDefense"] = team["paPerGame"]
        team["adjO"] = team["pfPerGame"] or league_points
        team["adjD"] = team["paPerGame"] or league_points

    for _ in range(18):
        next_values = []
        for team in teams:
            opponents = [find_opponent(game) for game in team["schedule"]]
            opponents = [opponent for opponent in opponents if opponent and opponent["slug"] != team["slug"]]
            average_defense = sum(opponent["adjD"] for opponent in opponents) / len(opponents) if opponents else league_points
            average_offense = sum(opponent["adjO"] for opponent in opponents) / len(opponents) if opponents else league_points
            # Reward scoring against strong defenses (low opponent adjD) and
            # holding strong offenses (high opponent adjO) down. Both terms must
            # point the same way: opponent strength raises your adjusted rating.
            adjusted_offense = team["rawOffense"] * (max(league_points, 1) / max(average_defense, 1)) ** 0.55
            adjusted_defense = team["rawDefense"] * (league_points / max(average_offense, 1)) ** 0.55
            next_values.append((team, max(0, min(adjusted_offense, 60)), max(1, min(adjusted_defense, 60))))
        for team, offense, defense in next_values:
            team["adjO"], team["adjD"] = offense, defense

    for team in teams:
        adj_net = team["adjO"] - team["adjD"]
        expected = 1 / (1 + math.exp(-adj_net / 8.5))
        team["adjO"] = round(team["adjO"], 2)
        team["adjD"] = round(team["adjD"], 2)
        team["adjNet"] = round(adj_net, 2)
        team["expectedWinPct"] = round(expected, 3)
        team["luck"] = round(team["winPct"] - expected, 3)
        poll_anchor = FOOTBALL_POLL_PRIORS.get(team["slug"], 50)
        efficiency_seed = 50 + adj_net * 1.15
        team["_rating"] = 0.82 * efficiency_seed + 0.18 * poll_anchor
        team["_pollAnchor"] = poll_anchor if team["slug"] in FOOTBALL_POLL_PRIORS else 50

    for _ in range(25):
        next_ratings = {}
        for team in teams:
            game_performances = []
            opponent_ratings = []
            resume_points = 0
            for game in team["schedule"]:
                if game.get("result") not in {"W", "L", "T"}:
                    continue
                opponent = find_opponent(game)
                if opponent and opponent["slug"] != team["slug"]:
                    opponent_rating = opponent["_rating"]
                else:
                    opponent_rating = external_opponent_rating(game.get("opponent", ""))
                if opponent_rating is None:
                    continue
                margin = (game.get("teamScore") or 0) - (game.get("opponentScore") or 0)
                capped_margin = math.copysign(min(abs(margin), 35) ** 0.72, margin) if margin else 0
                result_bonus = 3 if margin > 0 else -3 if margin < 0 else 0
                playoff_bonus = playoff_result_bonus(game, margin)
                game_performances.append(opponent_rating + capped_margin * 1.55 + result_bonus + playoff_bonus)
                opponent_ratings.append(opponent_rating)
                if margin > 0 and opponent_rating > 76:
                    resume_points += (opponent_rating - 76) / 8 + max(0, playoff_bonus) * 0.8
                elif margin < 0 and opponent_rating < 60:
                    resume_points -= (60 - opponent_rating) / 10
            efficiency_rating = 50 + team["adjNet"] * 1.0
            resume_rating = sum(game_performances) / len(game_performances) if game_performances else team["_rating"]
            true_sos = sum(opponent_ratings) / len(opponent_ratings) if opponent_ratings else 50
            resume_bonus = resume_points / max(team["games"], 1) * 5
            poll_anchor = team["_pollAnchor"]
            prior_weight = 0.18 if team["slug"] in FOOTBALL_POLL_PRIORS else 0.03
            next_ratings[team["slug"]] = (
                0.42 * efficiency_rating
                + 0.35 * resume_rating
                + 0.14 * true_sos
                + 0.09 * (50 + resume_bonus * 6)
                + prior_weight * poll_anchor
            ) / (0.42 + 0.35 + 0.14 + 0.09 + prior_weight)
            team["basePower"] = round(efficiency_rating, 2)
            team["resumeScore"] = round(resume_rating, 2)
            team["trueSos"] = round(true_sos, 2)
            team["resumeBonus"] = round(resume_bonus, 3)
            team["pollAnchor"] = poll_anchor
        for team in teams:
            team["_rating"] = 0.65 * team["_rating"] + 0.35 * next_ratings[team["slug"]]

    for team in teams:
        title_bonus = 0
        for game in team["schedule"]:
            if game.get("result") != "W":
                continue
            tournament = clean_text(game.get("tournament", "")).lower()
            if "quarterfinal" in tournament or "semifinal" in tournament or "final round" not in tournament:
                continue
            opponent = find_opponent(game)
            opponent_rating = opponent.get("_rating", 50) if opponent else external_opponent_rating(game.get("opponent", "")) or 50
            if "non-public, group a" in tournament:
                title_bonus += 3.5
            elif "group" in tournament and opponent_rating >= 76:
                title_bonus += 1.5
        team["titleBonus"] = round(min(title_bonus, 4), 2)
        team["rawPower"] = round(team["_rating"] + team["titleBonus"], 8)
        team["sos"] = round(team.get("trueSos", 50), 1)
        team["qualityScore"] = round(team.get("resumeScore", 50), 1)
        team["qualityWins"] = sum(
            1
            for game in team["schedule"]
            if game.get("result") == "W"
            and (
                (find_opponent(game) and find_opponent(game).get("_rating", 0) >= 70)
                or (external_opponent_rating(game.get("opponent", "")) or 0) >= 70
            )
        )

    raw_values = sorted(team["rawPower"] for team in teams)
    low = raw_values[0]
    high = raw_values[-1]
    for team in teams:
        normalized = (team["rawPower"] - low) / max(high - low, 1)
        team["powerScore"] = round(max(0, min(100, normalized * 100)), 1)
    teams.sort(key=lambda team: (team["rawPower"], team["winPct"], team["sos"], team["pointDiff"]), reverse=True)
    for rank, team in enumerate(teams, start=1):
        team["rank"] = rank
        team.pop("_rating", None)
        team.pop("_pollAnchor", None)


def percentile(values, value):
    values = sorted(values)
    if not values:
        return 50
    below = sum(item < value for item in values)
    equal = sum(item == value for item in values)
    return round(100 * (below + 0.5 * equal) / len(values), 1)


def assign_player_metrics(teams):
    team_by_slug = {team["slug"]: team for team in teams}
    players = [player for team in teams for player in team.get("players", [])]
    for player in players:
        pass_att = player.get("PassAtt", 0)
        rush_att = player.get("RushAtt", 0)
        rec = player.get("Rec", 0)
        tackles = player.get("Tackles", 0)
        player["CmpPct"] = round(100 * player.get("Cmp", 0) / pass_att, 1) if pass_att else 0
        player["PassYPA"] = round(player.get("PassYds", 0) / pass_att, 2) if pass_att else 0
        player["AdjYPA"] = round((player.get("PassYds", 0) + 20 * player.get("PassTD", 0) - 45 * player.get("INT", 0)) / pass_att, 2) if pass_att else 0
        player["PassTDPct"] = round(100 * player.get("PassTD", 0) / pass_att, 1) if pass_att else 0
        player["INTPct"] = round(100 * player.get("INT", 0) / pass_att, 1) if pass_att else 0
        player["RushYPA"] = round(player.get("RushYds", 0) / rush_att, 2) if rush_att else 0
        player["RushTDRate"] = round(100 * player.get("RushTD", 0) / rush_att, 1) if rush_att else 0
        player["RecYPR"] = round(player.get("RecYds", 0) / rec, 2) if rec else 0
        player["RecTDRate"] = round(100 * player.get("RecTD", 0) / rec, 1) if rec else 0
        player["TotalYds"] = player.get("PassYds", 0) + player.get("RushYds", 0) + player.get("RecYds", 0)
        player["TotalTD"] = player.get("PassTD", 0) + player.get("RushTD", 0) + player.get("RecTD", 0) + player.get("KORTD", 0) + player.get("PRTD", 0) + player.get("FumTD", 0) + player.get("IntTD", 0)
        player["DefImpact"] = round(tackles + 3 * player.get("TFL", 0) + 4 * player.get("Sacks", 0) + 4 * player.get("FF", 0) + 4 * player.get("FR", 0) + 6 * player.get("DefINT", 0) + 8 * player.get("FumTD", 0) + 8 * player.get("IntTD", 0) + 6 * player.get("Safety", 0) + 3 * player.get("KB", 0), 1)
        player["ReturnAvg"] = round((player.get("KORYds", 0) + player.get("PRYds", 0)) / max(player.get("KORAtt", 0) + player.get("PRAtt", 0), 1), 2)
        player["FGPct"] = round(100 * player.get("FGM", 0) / player.get("FGA", 0), 1) if player.get("FGA", 0) else 0
        player["XPPct"] = round(100 * player.get("XPM", 0) / player.get("XPA", 0), 1) if player.get("XPA", 0) else 0
        player["KickPoints"] = 3 * player.get("FGM", 0) + player.get("XPM", 0) + 2 * player.get("TwoPT", 0)
        player["PuntAvg"] = round(player.get("PuntYds", 0) / player.get("Punts", 0), 2) if player.get("Punts", 0) else 0

        if pass_att >= 20:
            role = "QB"
        elif rush_att >= 10 and rush_att >= rec * 1.5:
            role = "Rusher"
        elif rec >= 5:
            role = "Receiver"
        elif player.get("DefImpact", 0) >= 8:
            role = "Defender"
        elif player.get("FGA", 0) + player.get("XPA", 0) >= 3:
            role = "Kicker"
        elif player.get("Punts", 0) >= 3:
            role = "Punter"
        elif player.get("KORAtt", 0) + player.get("PRAtt", 0) >= 3:
            role = "Returner"
        else:
            role = "Utility"
        player["role"] = role

    role_metrics = {
        "QB": [("AdjYPA", 0.34), ("CmpPct", 0.18), ("PassTD", 0.18), ("PassYds", 0.18), ("INTPct", -0.12)],
        "Rusher": [("RushYds", 0.34), ("RushYPA", 0.28), ("RushTD", 0.28), ("RushLng", 0.10)],
        "Receiver": [("RecYds", 0.34), ("RecYPR", 0.24), ("RecTD", 0.28), ("Rec", 0.14)],
        "Defender": [("DefImpact", 0.46), ("Tackles", 0.18), ("TFL", 0.14), ("Sacks", 0.10), ("DefINT", 0.12)],
        "Kicker": [("KickPoints", 0.42), ("FGPct", 0.25), ("XPPct", 0.18), ("FGLng", 0.15)],
        "Punter": [("PuntAvg", 0.52), ("Inside20", 0.28), ("PuntLng", 0.20)],
        "Returner": [("ReturnAvg", 0.48), ("KORYds", 0.18), ("PRYds", 0.14), ("KORTD", 0.10), ("PRTD", 0.10)],
        "Utility": [("TotalYds", 0.50), ("TotalTD", 0.30), ("DefImpact", 0.20)],
    }
    for player in players:
        peers = [peer for peer in players if peer["role"] == player["role"]]
        metric_percentiles = {}
        weighted = 0
        total_weight = 0
        for metric, weight in role_metrics[player["role"]]:
            values = [peer.get(metric, 0) for peer in peers]
            pct = percentile(values, player.get(metric, 0))
            if weight < 0:
                pct = 100 - pct
            metric_percentiles[metric] = pct
            weighted += pct * abs(weight)
            total_weight += abs(weight)
        base_score = weighted / total_weight if total_weight else 50
        team = team_by_slug.get(player["teamSlug"], {})
        sos_adjustment = (team.get("sos", 50) - 50) * 0.10
        player["metricPercentiles"] = metric_percentiles
        player["playerScore"] = round(max(0, min(100, base_score + sos_adjustment)), 1)
    return players


def load_existing():
    try:
        text = open(OUTPUT_PATH, encoding="utf-8").read()
        return json.loads(text.split("const FOOTBALL_DATA = ", 1)[1].rsplit(";", 1)[0])
    except (OSError, IndexError, json.JSONDecodeError):
        return {}


def main():
    parser = argparse.ArgumentParser(description="Refresh Gridiron Index data from NJ.com")
    parser.add_argument("--limit", type=int, default=0, help="Development-only team limit")
    args = parser.parse_args()
    existing = load_existing()

    print(f"Fetching {SEASON} football standings...")
    teams = []
    seen = set()
    conference_counts = {}
    for conference in CONFERENCES:
        conference_teams = parse_conference(conference)
        conference_counts[conference] = len(conference_teams)
        print(f"  {conference}: {len(conference_teams)} teams")
        for team in conference_teams:
            if team["slug"] not in seen:
                seen.add(team["slug"])
                teams.append(team)
        time.sleep(0.05)
    if any(count == 0 for count in conference_counts.values()):
        raise RuntimeError(f"Refusing incomplete conference data: {conference_counts}")
    if len(teams) < 300:
        raise RuntimeError(f"Refusing incomplete statewide data: only {len(teams)} teams")
    if args.limit:
        teams = teams[:args.limit]

    print(f"Fetching schedules and seven stat groups for {len(teams)} teams...")
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
        print(f"Preserving {len(failures)} temporarily unavailable teams where possible.")
        payloads = [existing_by_slug.get(team["slug"], team) if team.get("error") else team for team in payloads]

    payloads.sort(key=lambda team: team["slug"])
    link_schedule_opponents(payloads)
    compute_team_ratings(payloads)
    players = assign_player_metrics(payloads)
    games = [{**game, "team": team["name"], "teamSlug": team["slug"]} for team in payloads for game in team["schedule"]]
    for team in payloads:
        team.pop("players", None)
    payload = {
        "season": SEASON,
        "sport": "football",
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
    output = OUTPUT_PATH if not args.limit else "/tmp/football-data-test.js"
    temp = f"{output}.tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write("// Auto-generated by football_scraper.py from highschoolsports.nj.com football data.\n")
        handle.write("const FOOTBALL_DATA = ")
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write(";\n")
    os.replace(temp, output)
    print(f"Wrote {output}: {len(payloads)} teams, {len(players)} players, {len(games)} schedule rows.")


if __name__ == "__main__":
    main()
