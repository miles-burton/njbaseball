#!/usr/bin/env python3
"""
NJ Baseball Savant - Stats Scraper
Pulls hitting/pitching data from highschoolsports.nj.com and computes advanced metrics.

Usage:
  python3 scraper.py                        # scrape all teams in TEAMS dict
  python3 scraper.py west-orange-west-orange  # scrape one team by slug
"""

import urllib.request
import ssl
import certifi
import re
import json
import sys
import time

# ── LEAGUE CONSTANTS ───────────────────────────────────────────────────────────
SEASON       = "2025-2026"
WOBA_SCALE   = 1.12
WOBA_LEAGUE  = 0.353   # league-average wOBA (adjust each season)
R_PA_LEAGUE  = 0.177   # league runs/PA  (adjust each season)

# ── TEAMS TO SCRAPE ────────────────────────────────────────────────────────────
# Format: "Display Name" -> "url-slug"
TEAMS = {
    # ── Liberty Division ──────────────────────────────────────────────────
    "West Orange":       "west-orange-west-orange",
    "Verona":            "verona-verona",
    "Caldwell":          "west-caldwell-caldwell",
    "Nutley":            "nutley-nutley",
    "SBP":               "newark-st-benedicts",
    "MKA":               "montclair-montclair-kimberley",
    # ── American Division ─────────────────────────────────────────────────
    "SHP":               "west-orange-seton-hall-prep",
    "West Essex":        "north-caldwell-west-essex",
    "Columbia":          "maplewood-columbia",
    "Livingston":        "livingston-livingston",
    "Millburn":          "millburn-millburn",
    "Montclair":         "montclair-montclair",
    # ── Colonial Division ────────────────────────────────────────────────
    "Cedar Grove":       "cedar-grove-cedar-grove",
    "Glen Ridge":        "glen-ridge-glen-ridge",
    "Belleville":        "belleville-belleville",
    "Newark Academy":    "livingston-newark-academy",
    "Barringer":         "newark-barringer",
    "Bloomfield":        "bloomfield-bloomfield",
    # ── Freedom Division ─────────────────────────────────────────────────
    "Shabazz":           "newark-shabazz",
    "Orange":            "orange-orange",
    "North Star":        "newark-north-star-academy",
    "East Orange":       "east-orange-east-orange",
    "University":        "newark-university",
    "Weequahic":         "newark-weequahic",
    # ── Independence Division ─────────────────────────────────────────────
    "Newark Tech":       "newark-newark-tech",
    "Payne Tech":        "newark-payne-tech",
    "East Side":         "newark-newark-east-side",
    "Technology":        "newark-technology",
    "Newark Central":    "newark-newark-central",
    "Golda Och":         "west-orange-golda-och",
    # ── Statewide teams (auto-discovered) ────────────────────────────────
    "Matawan":  "aberdeen-matawan",
    "Holy Spirit":  "absecon-holy-spirit",
    "Delaware Valley":  "alexandria-delaware-valley",
    "Allentown":  "allentown-allentown",
    "North Hunterdon":  "annandale-north-hunterdon",
    "Asbury Park":  "asbury-park-asbury-park",
    "Atlantic City":  "atlantic-city-atlantic-city",
    "Audubon":  "audubon-audubon",
    "Barnegat":  "barnegat-barnegat",
    "Ridge":  "basking-ridge-ridge",
    "Bayonne":  "bayonne-bayonne",
    "Central Regional":  "bayville-central-regional",
    "St. Rose":  "belmar-st-rose",
    "Belvidere":  "belvidere-belvidere",
    "Gov. Livingston":  "berkeley-hts-gov-livingston",
    "Bernards":  "bernardsville-bernards",
    "Highland":  "blackwood-highland",
    "North Warren":  "blairstown-north-warren",
    "Boonton":  "boonton-boonton",
    "Bordentown":  "bordentown-bordentown",
    "Bound Brook":  "bound-brook-bound-brook",
    "Brick Memorial":  "brick-brick-memorial",
    "Brick Township":  "brick-brick-township",
    "Bridgeton":  "bridgeton-bridgeton",
    "Bridgewater-Raritan":  "bridgewater-bridgewater-raritan",
    "Somerset Tech":  "bridgewater-somerset-tech",
    "Buena":  "buena-buena",
    "Burlington City":  "burlington-burlington-city",
    "Doane Academy":  "burlington-doane-academy",
    "Burlington Township":  "burlington-twp-burlington-township",
    "Butler":  "butler-butler",
    "Cape May Tech":  "cape-may-ct-hse-cape-may-tech",
    "Middle Township":  "cape-may-ct-hse-middle-township",
    "Penns Grove":  "carneys-point-penns-grove",
    "Carteret":  "carteret-carteret",
    "Chatham":  "chatham-chatham",
    "Camden Catholic":  "cherry-hill-camden-catholic",
    "Cherry Hill East":  "cherry-hill-cherry-hill-east",
    "Cherry Hill West":  "cherry-hill-cherry-hill-west",
    "West Morris":  "chester-west-morris",
    "Cinnaminson":  "cinnaminson-cinnaminson",
    "Johnson":  "clark-johnson",
    "Clayton":  "clayton-clayton",
    "Collingswood":  "collingswood-collingswood",
    "Colonia":  "colonia-colonia",
    "Colts Neck":  "colts-neck-colts-neck",
    "Northern Burlington":  "columbus-northern-burlington",
    "Cranford":  "cranford-cranford",
    "Cresskill":  "cresskill-cresskill",
    "Delran":  "delran-delran",
    "Holy Cross Prep":  "delran-holy-cross-prep",
    "Morris Catholic":  "denville-morris-catholic",
    "Morris Tech":  "denville-morris-tech",
    "Deptford":  "deptford-deptford",
    "Dover":  "dover-dover",
    "Dunellen":  "dunellen-dunellen",
    "East Brunswick":  "east-brunswick-east-brunswick",
    "East Brunswick Magnet":  "east-brunswick-east-brunswick-tech",
    "Hanover Park":  "east-hanover-hanover-park",
    "Becton":  "east-rutherford-becton",
    "Edison":  "edison-edison",
    "J.P. Stevens":  "edison-jp-stevens",
    "St. Thomas Aquinas":  "edison-st-thomas-aquinas-formerly-bishop-ahr",
    "Cedar Creek":  "egg-harbor-city-cedar-creek",
    "Egg Harbor":  "egg-harbor-twp-egg-harbor",
    "Elizabeth":  "elizabeth-elizabeth",
    "Elmwood Park":  "elmwood-park-elmwood-park",
    "Emerson Boro":  "emerson-emerson-boro",
    "Dwight-Englewood":  "englewood-dwight-englewood",
    "Timber Creek":  "erial-timber-creek",
    "Lower Cape May":  "erma-lower-cape-may",
    "Ewing":  "ewing-ewing",
    "Howell":  "farmingdale-howell",
    "Mount Olive":  "flanders-mount-olive",
    "Hunterdon Central":  "flemington-hunterdon-central",
    "Florence":  "florence-florence",
    "Delsea":  "franklinville-delsea",
    "Freehold Borough":  "freehold-freehold-borough",
    "Freehold Township":  "freehold-freehold-township",
    "Absegami":  "galloway-absegami",
    "Garfield":  "garfield-garfield",
    "Gill St. Bernard&#x27;s":  "gladstone-gill-st-bernards",
    "Glassboro":  "glassboro-glassboro",
    "Voorhees":  "glen-gardner-voorhees",
    "Glen Rock":  "glen-rock-glen-rock",
    "Gloucester":  "gloucester-city-gloucester",
    "Gloucester Catholic":  "gloucester-city-gloucester-catholic",
    "Hackettstown":  "hackettstown-hackettstown",
    "Haddon Heights":  "haddon-heights-haddon-heights",
    "Haddonfield":  "haddonfield-haddonfield",
    "Paul VI":  "haddonfield-paul-vi",
    "Manchester Regional":  "haledon-manchester-regional",
    "Wallkill Valley":  "hamburg-wallkill-valley",
    "Hamilton West":  "hamilton-hamilton-west",
    "Nottingham":  "hamilton-nottingham",
    "Steinert":  "hamilton-steinert",
    "Hammonton":  "hammonton-hammonton",
    "St. Joseph (Hamm.)":  "hammonton-st-joseph-hamm",
    "Hasbrouck Heights":  "hasbrouck-hts-hasbrouck-heights",
    "Hawthorne":  "hawthorne-hawthorne",
    "Hawthorne Christian/Eastern Christian":  "hawthorne-hawthorne-christian",
    "Raritan":  "hazlet-raritan",
    "Highland Park":  "highland-park-highland-park",
    "Henry Hudson":  "highlands-henry-hudson",
    "Hightstown":  "hightstown-hightstown",
    "Hillsborough":  "hillsborough-hillsborough",
    "Hillside":  "hillside-hillside",
    "Hoboken":  "hoboken-hoboken",
    "Holmdel":  "holmdel-holmdel",
    "St. John Vianney":  "holmdel-st-john-vianney",
    "Hopatcong":  "hopatcong-hopatcong",
    "Iselin Kennedy":  "iselin-iselin-kennedy",
    "Jackson Township":  "jackson-jackson-township",
    "Dickinson":  "jersey-city-dickinson",
    "Ferris":  "jersey-city-ferris",
    "Hudson Catholic":  "jersey-city-hudson-catholic",
    "Lincoln":  "jersey-city-lincoln",
    "McNair":  "jersey-city-mcnair",
    "Snyder":  "jersey-city-snyder",
    "St. Peter&#x27;s Prep":  "jersey-city-st-peters-prep",
    "University Charter":  "jersey-city-university-charter",
    "Keansburg":  "keansburg-keansburg",
    "Kearny":  "kearny-kearny",
    "Brearley":  "kenilworth-brearley",
    "Keyport":  "keyport-keyport",
    "Kinnelon":  "kinnelon-kinnelon",
    "Lakewood":  "lakewood-lakewood",
    "South Hunterdon":  "lambertville-south-hunterdon",
    "Lacey":  "lanoka-harbor-lacey",
    "Lawrence":  "lawrenceville-lawrence",
    "Notre Dame":  "lawrenceville-notre-dame",
    "Leonia":  "leonia-leonia",
    "Christian Brothers":  "lincroft-christian-brothers",
    "Linden":  "linden-linden",
    "Mainland":  "linwood-mainland",
    "Red Bank Regional":  "little-silver-red-bank-regional",
    "Lodi":  "lodi-lodi",
    "Long Branch":  "long-branch-long-branch",
    "Lyndhurst":  "lyndhurst-lyndhurst",
    "Madison":  "madison-madison",
    "Southern":  "manahawkin-southern",
    "Manalapan":  "manalapan-manalapan",
    "Manasquan":  "manasquan-manasquan",
    "Manchester Township":  "manchester-manchester-township",
    "Manville":  "manville-manville",
    "Maple Shade":  "maple-shade-maple-shade",
    "Marlboro":  "marlboro-marlboro",
    "Cherokee":  "marlton-cherokee",
    "Pingry":  "martinsville-pingry",
    "Old Bridge":  "matawan-old-bridge",
    "Atlantic Tech":  "mays-landing-atlantic-tech",
    "Oakcrest":  "mays-landing-oakcrest",
    "Lenape":  "medford-lenape",
    "Medford Tech":  "medford-medford-tech",
    "Shawnee":  "medford-shawnee",
    "Mendham":  "mendham-mendham",
    "Metuchen":  "metuchen-metuchen",
    "St. Joseph (Met.)":  "metuchen-st-joseph-met",
    "Middlesex":  "middlesex-middlesex",
    "Middletown North":  "middletown-middletown-north",
    "Middletown South":  "middletown-middletown-south",
    "Midland Park":  "midland-park-midland-park",
    "Millville":  "millville-millville",
    "South Brunswick":  "monmouth-jct-south-brunswick",
    "Monroe":  "monroe-twp-monroe",
    "Montville":  "montville-montville",
    "Moorestown":  "moorestown-moorestown",
    "Moorestown Friends":  "moorestown-moorestown-friends",
    "Parsippany Hills":  "morris-plains-parsippany-hills",
    "Delbarton":  "morristown-delbarton",
    "Morristown":  "morristown-morristown",
    "Morristown-Beard":  "morristown-morristown-beard",
    "Rancocas Valley":  "mount-holly-rancocas-valley",
    "Mountain Lakes":  "mountain-lakes-mountain-lakes",
    "Clearview":  "mullica-hill-clearview",
    "Wildwood Catholic":  "n-wildwood-wildwood-catholic",
    "Neptune":  "neptune-neptune",
    "New Brunswick":  "new-brunswick-new-brunswick",
    "New Egypt":  "new-egypt-new-egypt",
    "New Milford":  "new-milford-new-milford",
    "New Providence":  "new-providence-new-providence",
    "Kittatinny":  "newton-kittatinny",
    "Newton":  "newton-newton",
    "North Plainfield":  "no-plainfield-north-plainfield",
    "North Arlington":  "north-arlington-north-arlington",
    "North Bergen":  "north-bergen-north-bergen",
    "North Brunswick":  "north-brunswick-north-brunswick",
    "Jefferson":  "oak-ridge-jefferson",
    "Ocean Township":  "oakhurst-ocean-township",
    "Ocean City":  "ocean-city-ocean-city",
    "Palmyra":  "palmyra-palmyra",
    "Park Ridge":  "park-ridge-park-ridge",
    "Sayreville":  "parlin-sayreville",
    "Parsippany":  "parsippany-parsippany",
    "Paterson Charter":  "paterson-paterson-charter",
    "Paulsboro":  "paulsboro-paulsboro",
    "Pemberton":  "pemberton-pemberton",
    "Hopewell Valley":  "pennington-hopewell-valley",
    "Bishop Eustace":  "pennsauken-bishop-eustace",
    "Pennsauken":  "pennsauken-pennsauken",
    "Pennsauken Tech":  "pennsauken-pennsauken-tech",
    "Pennsville":  "pennsville-pennsville",
    "Perth Amboy":  "perth-amboy-perth-amboy",
    "Perth Amboy Magnet":  "perth-amboy-perth-amboy-tech",
    "Phillipsburg":  "phillipsburg-phillipsburg",
    "Overbrook":  "pine-hill-overbrook",
    "Piscataway":  "piscataway-piscataway",
    "Piscataway Magnet":  "piscataway-piscataway-tech",
    "Timothy Christian/Roselle Catholic":  "piscataway-timothy-christian",
    "Pitman":  "pitman-pitman",
    "Schalick":  "pittsgrove-schalick",
    "Plainfield":  "plainfield-plainfield",
    "West Windsor-Plainsboro North":  "plainsboro-west-windsor-plainsboro-north",
    "Pleasantville":  "pleasantville-pleasantville",
    "Pompton Lakes":  "pompton-lakes-pompton-lakes",
    "Pequannock":  "pompton-plains-pequannock",
    "West Windsor-Plainsboro South":  "princeton-jct-west-windsor-plainsboro-south",
    "Princeton":  "princeton-princeton",
    "Princeton Day":  "princeton-princeton-day",
    "Point Pleasant Beach":  "pt-pleasant-bch-point-pleasant-beach",
    "Point Pleasant Boro":  "pt-pleasant-point-pleasant-boro",
    "Rahway":  "rahway-rahway",
    "Randolph":  "randolph-randolph",
    "Red Bank Catholic":  "red-bank-red-bank-catholic",
    "St. Augustine":  "richland-st-augustine",
    "Ridgefield/Palisades Park":  "ridgefield-ridgefield",
    "Riverside":  "riverside-riverside",
    "Robbinsville":  "robbinsville-robbinsville",
    "Morris Hills":  "rockaway-morris-hills",
    "Morris Knolls":  "rockaway-morris-knolls",
    "Roselle Park":  "roselle-park-roselle-park",
    "Rumson-Fair Haven":  "rumson-rumson-fair-haven",
    "Triton":  "runnemede-triton",
    "Rutherford":  "rutherford-rutherford",
    "St. Mary (Ruth.)":  "rutherford-st-mary-ruth",
    "Saddle Brook":  "saddle-brook-saddle-brook",
    "Salem":  "salem-salem",
    "Scotch Plains-Fanwood":  "scotch-plains-scotch-plains-fanwood",
    "Union Catholic":  "scotch-plains-union-catholic",
    "Cumberland":  "seabrook-cumberland",
    "Secaucus":  "secaucus-secaucus",
    "Gloucester Tech":  "sewell-gloucester-tech",
    "Washington Township":  "sewell-washington-township",
    "Montgomery":  "skillman-montgomery",
    "South Plainfield":  "so-plainfield-south-plainfield",
    "Sterling":  "somerdale-sterling",
    "Franklin":  "somerset-franklin",
    "Rutgers Prep":  "somerset-rutgers-prep",
    "Immaculata":  "somerville-immaculata",
    "Somerville":  "somerville-somerville",
    "South Amboy":  "south-amboy-south-amboy",
    "South River":  "south-river-south-river",
    "Pope John":  "sparta-pope-john",
    "Sparta":  "sparta-sparta",
    "Sussex Tech":  "sparta-sussex-tech",
    "Spotswood":  "spotswood-spotswood",
    "Dayton":  "springfield-dayton",
    "Lenape Valley":  "stanhope-lenape-valley",
    "Roxbury":  "succasunna-roxbury",
    "Oratory":  "summit-oratory",
    "Summit":  "summit-summit",
    "High Point":  "sussex-high-point",
    "Seneca":  "tabernacle-seneca",
    "Monmouth":  "tinton-falls-monmouth",
    "Ranney":  "tinton-falls-ranney",
    "Donovan Catholic":  "toms-river-donovan-catholic",
    "Toms River East":  "toms-river-toms-river-east",
    "Toms River North":  "toms-river-toms-river-north",
    "Toms River South":  "toms-river-toms-river-south",
    "Trenton":  "trenton-trenton",
    "Pinelands":  "tuckerton-pinelands",
    "Union City":  "union-city-union-city",
    "Union":  "union-union",
    "Vernon":  "vernon-vernon",
    "Vineland":  "vineland-vineland",
    "Eastern":  "voorhees-eastern",
    "Shore":  "w-long-branch-shore",
    "Waldwick":  "waldwick-waldwick",
    "Wall":  "wall-wall",
    "Wallington":  "wallington-wallington",
    "Watchung Hills":  "warren-watchung-hills",
    "Warren Hills":  "washington-warren-hills",
    "Weehawken":  "weehawken-weehawken",
    "Memorial":  "west-new-york-memorial",
    "Westampton Tech":  "westampton-westampton-tech",
    "Westfield":  "westfield-westfield",
    "Haddon Township":  "westmont-haddon-township",
    "West Deptford":  "westville-west-deptford",
    "Whippany Park":  "whippany-whippany-park",
    "Wildwood":  "wildwood-wildwood",
    "Williamstown":  "williamstown-williamstown",
    "Willingboro":  "willingboro-willingboro",
    "Wood-Ridge":  "wood-ridge-wood-ridge",
    "Woodbridge":  "woodbridge-woodbridge",
    "Gateway":  "woodbury-hts-gateway",
    "Woodstown":  "woodstown-woodstown",
    "Kingsway":  "woolwich-twp-kingsway",

}

# ── SCRAPER ────────────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return r.read().decode("utf-8")

def fetch_stats(slug):
    return fetch(f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}/stats")

def fetch_schedule(slug):
    return fetch(f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}")

def parse_schedule(html):
    """Parse schedule page → {coach, wins, losses, games: [{date, opponent, result, score, home}]}"""
    # Head coach
    coach_match = re.search(r'Head Coach:\s*([A-Z][a-zA-Z\'\-]+(?: [A-Z][a-zA-Z\'\-]+)+)', html)
    coach = coach_match.group(1).strip() if coach_match else ""

    games = []
    tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
    if not tables:
        return {"coach": coach, "wins": 0, "losses": 0, "games": []}

    rows = re.findall(r'<tr.*?</tr>', tables[0], re.DOTALL)
    wins = losses = 0

    for row in rows:
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
        cells = [re.sub(r'&amp;', '&', c) for c in cells]
        cells = [re.sub(r'&#x27;', "'", c) for c in cells]
        cells = [re.sub(r'&[a-z]+;', '', c) for c in cells]
        cells = [re.sub(r'<[^>]+>', ' ', c) for c in cells]
        cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
        cells = [c for c in cells if c and c != '\xa0']

        if len(cells) < 3 or cells[0] == 'Date':
            continue

        date     = cells[0] if len(cells) > 0 else ""
        opponent = cells[1] if len(cells) > 1 else ""
        result   = cells[2] if len(cells) > 2 else ""

        # Clean opponent (strip tournament info after comma)
        opp_clean = opponent.split(',')[0].strip()
        home = not opp_clean.startswith('@')
        opp_clean = opp_clean.lstrip('vs@ ').strip()

        # Parse result: "W 11-1" or "L 6-1"
        outcome = ""
        score   = ""
        rm = re.match(r'([WL])\s+(\d+-\d+)', result)
        if rm:
            outcome = rm.group(1)
            score   = rm.group(2)
            if outcome == 'W': wins += 1
            else: losses += 1

        if date and opp_clean:
            games.append({
                "date":     date,
                "opponent": opp_clean,
                "home":     home,
                "outcome":  outcome,
                "score":    score,
            })

    return {"coach": coach, "wins": wins, "losses": losses, "games": games}

def get_table_rows(html):
    """Return list of tables, each a list of rows, each a list of cell strings."""
    tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
    result = []
    for t in tables:
        rows = re.findall(r'<tr.*?</tr>', t, re.DOTALL)
        parsed_rows = []
        for row in rows:
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
            cells = [re.sub(r'<[^>]+>', ' ', c) for c in cells]
            cells = [re.sub(r'&bull;', '•', c) for c in cells]
            cells = [re.sub(r'&mdash;', '0', c) for c in cells]
            cells = [re.sub(r'&[a-z]+;', '', c) for c in cells]
            cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
            if any(c for c in cells):
                parsed_rows.append(cells)
        result.append(parsed_rows)
    return result

def parse_name_pos_year(cell):
    """Parse 'Jordan Jackson #8 • Senior • OF, P' -> (name, pos, year)"""
    cell = re.sub(r'#\d+', '', cell)
    cell = re.sub(r'&bull;', '•', cell)
    parts = [p.strip() for p in cell.split('•') if p.strip()]
    name = parts[0].strip() if len(parts) > 0 else cell.strip()
    year = parts[1].strip() if len(parts) > 1 else ''
    pos  = parts[2].strip() if len(parts) > 2 else ''
    return name, pos, year

def safe_float(v, default=0.0):
    try:
        v = str(v).replace(',', '').strip()
        return float(v) if v else default
    except:
        return default

# ── HITTING PARSER ─────────────────────────────────────────────────────────────
# Columns: name | AB R H RBI 1B 2B 3B HR BB HBP SB SF SH/B ROE LOB FC AVG SLG
def parse_hitting(rows, team_name):
    players = []
    # Find header row
    header_idx = None
    for i, row in enumerate(rows):
        if 'AB' in row and 'RBI' in row:
            header_idx = i
            break
    if header_idx is None:
        return players

    for row in rows[header_idx + 1:]:
        if len(row) < 10:
            continue
        name, pos, year = parse_name_pos_year(row[0])
        if not name or 'total' in name.lower():
            continue

        AB  = safe_float(row[1])
        R   = safe_float(row[2])
        H   = safe_float(row[3])
        RBI = safe_float(row[4])
        B1  = safe_float(row[5])
        B2  = safe_float(row[6])
        B3  = safe_float(row[7])
        HR  = safe_float(row[8])
        BB  = safe_float(row[9])
        HBP = safe_float(row[10]) if len(row) > 10 else 0
        SB  = safe_float(row[11]) if len(row) > 11 else 0
        SF  = safe_float(row[12]) if len(row) > 12 else 0
        SH  = safe_float(row[13]) if len(row) > 13 else 0

        PA = AB + BB + HBP + SF + SH
        if PA == 0:
            continue

        AVG      = H / AB if AB > 0 else 0
        SLG      = (B1 + 2*B2 + 3*B3 + 4*HR) / AB if AB > 0 else 0
        OBP      = (H + BB + HBP) / (AB + BB + HBP + SF) if (AB + BB + HBP + SF) > 0 else 0
        OPS      = OBP + SLG
        ISO      = SLG - AVG
        BB_pct   = (BB / PA) * 100
        BsR      = (SB * 0.2) + (B3 * 0.1)
        wOBA     = ((0.7*(BB+HBP)) + (0.9*B1) + (1.3*B2) + (1.6*B3) + (2*HR)) / PA
        wRAA     = ((wOBA - WOBA_LEAGUE) / WOBA_SCALE) * PA
        wRC      = wRAA + (PA * R_PA_LEAGUE)
        wRC_plus = round(((wOBA - WOBA_LEAGUE) / WOBA_SCALE + R_PA_LEAGUE) / R_PA_LEAGUE * 100)
        OFF      = wRAA + BsR

        players.append({
            "name": name, "pos": pos, "year": year, "team": team_name,
            "PA": int(PA), "AB": int(AB), "R": int(R), "H": int(H), "RBI": int(RBI),
            "B1": int(B1), "B2": int(B2), "B3": int(B3), "HR": int(HR),
            "BB": int(BB), "HBP": int(HBP), "SB": int(SB),
            "AVG":     round(AVG, 3),
            "SLG":     round(SLG, 3),
            "OBP":     round(OBP, 3),
            "OPS":     round(OPS, 3),
            "ISO":     round(ISO, 3),
            "BB_pct":  round(BB_pct, 1),
            "BsR":     round(BsR, 2),
            "wOBA":    round(wOBA, 3),
            "wRAA":    round(wRAA, 2),
            "wRC":     round(wRC, 1),
            "wRC_plus":wRC_plus,
            "OFF":     round(OFF, 2),
            "qualified": PA >= 50
        })
    return players

# ── PITCHING PARSER ────────────────────────────────────────────────────────────
# Columns: name | W L PIT IP H R ER BB K HB PO ERA
def parse_pitching(rows, team_name):
    pitchers = []
    header_idx = None
    for i, row in enumerate(rows):
        if 'ERA' in row and 'IP' in row:
            header_idx = i
            break
    if header_idx is None:
        return pitchers

    for row in rows[header_idx + 1:]:
        if len(row) < 8:
            continue
        name, pos, year = parse_name_pos_year(row[0])
        if not name or 'total' in name.lower():
            continue

        W      = safe_float(row[1])
        L      = safe_float(row[2])
        # row[3] = PIT pitch count
        IP_str = row[4]
        ip_parts = IP_str.split('.')
        try:
            IP = int(ip_parts[0]) + (int(ip_parts[1]) / 3 if len(ip_parts) > 1 and ip_parts[1] else 0)
        except:
            continue
        if IP == 0:
            continue

        H  = safe_float(row[5])
        R  = safe_float(row[6])
        ER = safe_float(row[7])
        BB = safe_float(row[8])  if len(row) > 8  else 0
        K  = safe_float(row[9])  if len(row) > 9  else 0
        HB = safe_float(row[10]) if len(row) > 10 else 0

        ERA       = (ER / IP) * 9
        WHIP      = (BB + H) / IP
        K7        = (K / IP) * 7
        BB7       = (BB / IP) * 7
        KBB       = K / BB if BB > 0 else 999
        FIP_const = 3.10
        FIP       = ((3*(BB+HB) - 2*K) / IP) + FIP_const
        ERA_minus = round((ERA / 4.31) * 100)
        FIP_minus = round((FIP / 4.31) * 100)
        RAA       = ((4.31 - ERA) / 9) * IP
        WAR       = round(RAA / 10, 1)

        pitchers.append({
            "name": name, "pos": pos, "year": year, "team": team_name,
            "W": int(W), "L": int(L),
            "IP":        round(IP, 2),
            "H":         int(H), "R": int(R), "ER": int(ER),
            "BB":        int(BB), "K": int(K), "HB": int(HB),
            "ERA":       round(ERA, 2),
            "ERA_minus": ERA_minus,
            "FIP":       round(FIP, 2),
            "FIP_minus": FIP_minus,
            "WHIP":      round(WHIP, 2),
            "K7":        round(K7, 2),
            "BB7":       round(BB7, 2),
            "KBB":       round(KBB, 2) if KBB != 999 else 999,
            "RAA":       round(RAA, 1),
            "WAR":       WAR,
            "PIP":       0,
            "qualPitch": IP >= 15
        })
    return pitchers

# ── MAIN ───────────────────────────────────────────────────────────────────────
def scrape_team(display_name, slug):
    print(f"  Scraping {display_name} ({slug})...", end=" ", flush=True)
    try:
        stats_html = fetch_stats(slug)
        tables     = get_table_rows(stats_html)
        hitters    = parse_hitting(tables[0],  display_name) if len(tables) > 0 else []
        pitchers   = parse_pitching(tables[1], display_name) if len(tables) > 1 else []

        sched_html = fetch_schedule(slug)
        schedule   = parse_schedule(sched_html)

        print(f"{len(hitters)} hitters, {len(pitchers)} pitchers, {schedule['wins']}-{schedule['losses']}")
        return hitters, pitchers, schedule
    except Exception as e:
        print(f"ERROR: {e}")
        return [], [], {"coach": "", "wins": 0, "losses": 0, "games": []}

def generate_js(all_hitters, all_pitchers, all_schedules={}):
    """Write scraped data directly into js/data.js so the site updates immediately."""
    import os
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "js", "data.js")

    now = __import__('datetime').datetime.now().strftime('%b %d, %Y')
    lines = [
        "// AUTO-GENERATED by scraper.py\n",
        f"// Last updated: {now}\n",
        "// Do not edit by hand — run: python3 scraper.py\n\n",
        f"const DATA_UPDATED = '{now}';\n\n",
    ]

    # Team identity (preserved from original)
    lines.append("""const TM = {
  // ── Liberty Division ───────────────────────────────────────────────────
  'West Orange':    { div:'Liberty',      mascot:'Mountaineers', p:'#1e3a6e', s:'#4a7cc7', t:'#a8c8f0', bg:'#0a1628', logo:'https://nj.vsand-static.com/Logos/4863.png' },
  'Verona':         { div:'Liberty',      mascot:'Hillbillies',  p:'#7a1010', s:'#a01818', t:'#d47070', bg:'#1e0505', logo:'https://nj.vsand-static.com/Logos/4742.png' },
  'Caldwell':       { div:'Liberty',      mascot:'Chiefs',       p:'#1a35a0', s:'#2a50c8', t:'#80a8e8', bg:'#060d28', logo:'https://nj.vsand-static.com/Logos/6250.png' },
  'Nutley':         { div:'Liberty',      mascot:'Raiders',      p:'#8b1a2a', s:'#b02535', t:'#d07080', bg:'#1a0508', logo:'https://nj.vsand-static.com/Logos/4185.png' },
  'SBP':            { div:'Liberty',      mascot:'Gray Bees',    p:'#6b1520', s:'#8b1a28', t:'#c08088', bg:'#150508', logo:'https://nj.vsand-static.com/Logos/5380.png' },
  'MKA':            { div:'Liberty',      mascot:'Cougars',      p:'#1a2a6b', s:'#7a6030', t:'#b09060', bg:'#07091e', logo:'https://nj.vsand-static.com/Logos/6252.png' },
  // ── American Division ──────────────────────────────────────────────────
  'SHP':            { div:'American',     mascot:'Pirates',      p:'#1a2a8b', s:'#2a50c8', t:'#8090e8', bg:'#06091e', logo:'logos/shp.png' },
  'West Essex':     { div:'American',     mascot:'Knights',      p:'#8b0a0a', s:'#b81818', t:'#e07070', bg:'#1e0505', logo:'https://nj.vsand-static.com/Logos/4855.png' },
  'Columbia':       { div:'American',     mascot:'Cougars',      p:'#0a4a1a', s:'#1a7a30', t:'#60c870', bg:'#051008', logo:'https://nj.vsand-static.com/Logos/2890.png' },
  'Livingston':     { div:'American',     mascot:'Lancers',      p:'#1a5a1a', s:'#2a8a2a', t:'#70c870', bg:'#071507', logo:'logos/livingston.png' },
  'Millburn':       { div:'American',     mascot:'Millers',      p:'#1a1a8b', s:'#3030b0', t:'#8888e0', bg:'#06061e', logo:'https://nj.vsand-static.com/Logos/3915.png' },
  'Montclair':      { div:'American',     mascot:'Mounties',     p:'#8b6914', s:'#c8960c', t:'#f0c040', bg:'#1e1500', logo:'https://nj.vsand-static.com/Logos/3939.png' },
  // ── Colonial Division ──────────────────────────────────────────────────
  'Cedar Grove':    { div:'Colonial',     mascot:'Panthers',     p:'#1a1500', s:'#c8960c', t:'#f0c040', bg:'#0e0b00', logo:'logos/cedar-grove.png' },
  'Glen Ridge':     { div:'Colonial',     mascot:'Ridgers',      p:'#8b1a1a', s:'#c02828', t:'#e08080', bg:'#1e0606', logo:'https://nj.vsand-static.com/Logos/3234.png' },
  'Belleville':     { div:'Colonial',     mascot:'Buccaneers',   p:'#1a2a6b', s:'#c8960c', t:'#f0c040', bg:'#06091a', logo:'logos/belleville.png' },
  'Newark Academy': { div:'Colonial',     mascot:'Minutemen',    p:'#6b1a1a', s:'#902828', t:'#d07070', bg:'#150606', logo:'https://nj.vsand-static.com/Logos/6253.png' },
  'Barringer':      { div:'Colonial',     mascot:'Blue Bears',   p:'#0a2a6b', s:'#1a4aa0', t:'#6090d8', bg:'#05101e', logo:'https://nj.vsand-static.com/Logos/2623.png' },
  'Bloomfield':     { div:'Colonial',     mascot:'Bengals',      p:'#a04010', s:'#d05818', t:'#f0a060', bg:'#200d05', logo:'https://nj.vsand-static.com/Logos/2683.png' },
  // ── Freedom Division ───────────────────────────────────────────────────
  'Shabazz':        { div:'Freedom',      mascot:'Bulldogs',     p:'#1a1a6b', s:'#2828a8', t:'#7878e0', bg:'#06061a', logo:'https://nj.vsand-static.com/Logos/3760.png' },
  'Orange':         { div:'Freedom',      mascot:'Tornadoes',    p:'#8b4a00', s:'#c86800', t:'#f0a030', bg:'#1e1000', logo:'https://nj.vsand-static.com/Logos/4222.png' },
  'North Star':     { div:'Freedom',      mascot:'Cougars',      p:'#1a4a1a', s:'#2a7a2a', t:'#70c870', bg:'#061206', logo:'https://nj.vsand-static.com/Logos/6414.png' },
  'East Orange':    { div:'Freedom',      mascot:'Jaguars',      p:'#1a6b1a', s:'#2a9a2a', t:'#70d070', bg:'#071507', logo:'https://nj.vsand-static.com/Logos/3018.png' },
  'University':     { div:'Freedom',      mascot:'Engineers',    p:'#4a1a6b', s:'#7028a8', t:'#b878e0', bg:'#10061a', logo:'https://nj.vsand-static.com/Logos/4713.png' },
  'Weequahic':      { div:'Freedom',      mascot:'Indians',      p:'#1a1a8b', s:'#2828b8', t:'#7878e0', bg:'#06061e', logo:'https://nj.vsand-static.com/Logos/4840.png' },
  // ── Independence Division ──────────────────────────────────────────────
  'Newark Tech':    { div:'Independence', mascot:'Engineers',    p:'#1a3a6e', s:'#2858a8', t:'#7098d8', bg:'#060f1e', logo:'https://nj.vsand-static.com/Logos/6318.png' },
  'Payne Tech':     { div:'Independence', mascot:'Panthers',     p:'#1a1a5a', s:'#2828a0', t:'#7878d8', bg:'#060614', logo:'https://nj.vsand-static.com/Logos/9906.png' },
  'East Side':      { div:'Independence', mascot:'Argonauts',    p:'#6b1a1a', s:'#a02828', t:'#d87070', bg:'#180606', logo:'https://nj.vsand-static.com/Logos/3019.png' },
  'Technology':     { div:'Independence', mascot:'Panthers',     p:'#1a1a1a', s:'#444444', t:'#cccccc', bg:'#0a0a0a', logo:'logos/technology.png' },
  'Newark Central': { div:'Independence', mascot:'Golden Bears', p:'#6b5000', s:'#a87800', t:'#e8c050', bg:'#181200', logo:'https://nj.vsand-static.com/Logos/2806.png' },
  'Golda Och':      { div:'Independence', mascot:'Royals',       p:'#4a006b', s:'#7800a8', t:'#c060e0', bg:'#100018', logo:'https://nj.vsand-static.com/Logos/6327.png' }

  // ── Statewide teams (auto-discovered) ─────────────────────────────────
  'Matawan': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3818.png' },
  'Holy Spirit': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4973.png' },
  'Delaware Valley': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2947.png' },
  'Allentown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2554.png' },
  'North Hunterdon': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4042.png' },
  'Asbury Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2587.png' },
  'Atlantic City': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2593.png' },
  'Audubon': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2601.png' },
  'Barnegat': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2622.png' },
  'Ridge': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4391.png' },
  'Bayonne': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2629.png' },
  'Central Regional': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2811.png' },
  'St. Rose': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5700.png' },
  'Belvidere': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2651.png' },
  'Gov. Livingston': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3251.png' },
  'Bernards': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2669.png' },
  'Highland': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3374.png' },
  'North Warren': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4045.png' },
  'Boonton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2690.png' },
  'Bordentown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2692.png' },
  'Bound Brook': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2694.png' },
  'Brick Memorial': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2712.png' },
  'Brick Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2711.png' },
  'Bridgeton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2713.png' },
  'Bridgewater-Raritan': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2714.png' },
  'Somerset Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4538.png' },
  'Buena': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2737.png' },
  'Burlington City': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2739.png' },
  'Doane Academy': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6330.png' },
  'Burlington Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2742.png' },
  'Butler': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2747.png' },
  'Cape May Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2767.png' },
  'Middle Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3894.png' },
  'Penns Grove': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4276.png' },
  'Carteret': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2776.png' },
  'Chatham': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2826.png' },
  'Camden Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5214.png' },
  'Cherry Hill East': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2833.png' },
  'Cherry Hill West': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2834.png' },
  'West Morris': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4860.png' },
  'Cinnaminson': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2847.png' },
  'Johnson': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2579.png' },
  'Clayton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2858.png' },
  'Collingswood': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2882.png' },
  'Colonia': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2884.png' },
  'Colts Neck': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2887.png' },
  'Northern Burlington': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4048.png' },
  'Cranford': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2916.png' },
  'Cresskill': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2920.png' },
  'Delran': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2948.png' },
  'Holy Cross Prep': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5161.png' },
  'Morris Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5829.png' },
  'Morris Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6316.png' },
  'Deptford': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2958.png' },
  'Dover': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2972.png' },
  'Dunellen': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2988.png' },
  'East Brunswick': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3009.png' },
  'East Brunswick Magnet': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3010.png' },
  'Hanover Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3309.png' },
  'Becton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3360.png' },
  'Edison': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3031.png' },
  'J.P. Stevens': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3479.png' },
  'St. Thomas Aquinas': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5596.png' },
  'Cedar Creek': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6947.png' },
  'Egg Harbor': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3042.png' },
  'Elizabeth': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3055.png' },
  'Elmwood Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3873.png' },
  'Emerson Boro': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3067.png' },
  'Dwight-Englewood': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6300.png' },
  'Timber Creek': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4679.png' },
  'Lower Cape May': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3731.png' },
  'Ewing': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3106.png' },
  'Howell': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3426.png' },
  'Mount Olive': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3961.png' },
  'Hunterdon Central': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3435.png' },
  'Florence': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3133.png' },
  'Delsea': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2951.png' },
  'Freehold Borough': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3188.png' },
  'Freehold Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3191.png' },
  'Absegami': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2498.png' },
  'Garfield': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3208.png' },
  'Gill St. Bernard&#x27;s': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6301.png' },
  'Glassboro': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3229.png' },
  'Voorhees': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4757.png' },
  'Glen Rock': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3235.png' },
  'Gloucester': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3243.png' },
  'Gloucester Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5232.png' },
  'Hackettstown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3288.png' },
  'Haddon Heights': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3290.png' },
  'Haddonfield': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3292.png' },
  'Paul VI': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5246.png' },
  'Manchester Regional': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3765.png' },
  'Wallkill Valley': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4768.png' },
  'Hamilton West': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3302.png' },
  'Nottingham': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3301.png' },
  'Steinert': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3300.png' },
  'Hammonton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3305.png' },
  'St. Joseph (Hamm.)': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4992.png' },
  'Hasbrouck Heights': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3328.png' },
  'Hawthorne': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3339.png' },
  'Hawthorne Christian/Eastern Christian': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6302.png' },
  'Raritan': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4364.png' },
  'Highland Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3375.png' },
  'Henry Hudson': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3359.png' },
  'Hightstown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3378.png' },
  'Hillsborough': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3387.png' },
  'Hillside': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3396.png' },
  'Hoboken': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3400.png' },
  'Holmdel': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3409.png' },
  'St. John Vianney': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5716.png' },
  'Hopatcong': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3413.png' },
  'Iselin Kennedy': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3471.png' },
  'Jackson Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/12815.png' },
  'Dickinson': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4906.png' },
  'Ferris': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3488.png' },
  'Hudson Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5468.png' },
  'Lincoln': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3683.png' },
  'McNair': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2982.png' },
  'Snyder': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3361.png' },
  'St. Peter&#x27;s Prep': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5489.png' },
  'University Charter': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6333.png' },
  'Keansburg': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3572.png' },
  'Kearny': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3573.png' },
  'Brearley': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2933.png' },
  'Keyport': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3579.png' },
  'Kinnelon': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3586.png' },
  'Lakewood': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3619.png' },
  'South Hunterdon': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4551.png' },
  'Lacey': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3598.png' },
  'Lawrence': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3637.png' },
  'Notre Dame': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5555.png' },
  'Leonia': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3650.png' },
  'Christian Brothers': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5767.png' },
  'Linden': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3697.png' },
  'Mainland': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3758.png' },
  'Red Bank Regional': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4375.png' },
  'Lodi': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3713.png' },
  'Long Branch': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3716.png' },
  'Lyndhurst': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3740.png' },
  'Madison': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3749.png' },
  'Southern': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4572.png' },
  'Manalapan': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3761.png' },
  'Manasquan': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3764.png' },
  'Manchester Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3766.png' },
  'Manville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3774.png' },
  'Maple Shade': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3778.png' },
  'Marlboro': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3793.png' },
  'Cherokee': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2831.png' },
  'Pingry': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6249.png' },
  'Old Bridge': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4212.png' },
  'Atlantic Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/7537.png' },
  'Oakcrest': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4193.png' },
  'Lenape': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3644.png' },
  'Medford Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6311.png' },
  'Shawnee': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4517.png' },
  'Mendham': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4861.png' },
  'Metuchen': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3885.png' },
  'St. Joseph (Met.)': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5623.png' },
  'Middlesex': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3897.png' },
  'Middletown North': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3898.png' },
  'Middletown South': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3899.png' },
  'Midland Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3903.png' },
  'Millville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3922.png' },
  'South Brunswick': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4547.png' },
  'Monroe': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3937.png' },
  'Montville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3943.png' },
  'Moorestown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3946.png' },
  'Moorestown Friends': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6315.png' },
  'Parsippany Hills': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4255.png' },
  'Delbarton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6255.png' },
  'Morristown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3956.png' },
  'Morristown-Beard': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6256.png' },
  'Rancocas Valley': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4357.png' },
  'Mountain Lakes': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3966.png' },
  'Clearview': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2861.png' },
  'Wildwood Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5284.png' },
  'Neptune': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4000.png' },
  'New Brunswick': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4004.png' },
  'New Egypt': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4006.png' },
  'New Milford': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4011.png' },
  'New Providence': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4013.png' },
  'Kittatinny': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3589.png' },
  'Newton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4021.png' },
  'North Plainfield': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4044.png' },
  'North Arlington': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4033.png' },
  'North Bergen': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4035.png' },
  'North Brunswick': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4037.png' },
  'Jefferson': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3510.png' },
  'Ocean Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4206.png' },
  'Ocean City': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4202.png' },
  'Palmyra': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4237.png' },
  'Park Ridge': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4244.png' },
  'Sayreville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6254.png' },
  'Parsippany': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4254.png' },
  'Paterson Charter': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/8392.png' },
  'Paulsboro': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4270.png' },
  'Pemberton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4274.png' },
  'Hopewell Valley': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6244.png' },
  'Bishop Eustace': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5256.png' },
  'Pennsauken': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4278.png' },
  'Pennsauken Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6323.png' },
  'Pennsville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4282.png' },
  'Perth Amboy': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4289.png' },
  'Perth Amboy Magnet': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4290.png' },
  'Phillipsburg': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4296.png' },
  'Overbrook': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4229.png' },
  'Piscataway': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4306.png' },
  'Piscataway Magnet': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4307.png' },
  'Timothy Christian/Roselle Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6331.png' },
  'Pitman': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4308.png' },
  'Schalick': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2581.png' },
  'Plainfield': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4311.png' },
  'West Windsor-Plainsboro North': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4866.png' },
  'Pleasantville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4314.png' },
  'Pompton Lakes': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4321.png' },
  'Pequannock': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4284.png' },
  'West Windsor-Plainsboro South': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4867.png' },
  'Princeton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4331.png' },
  'Princeton Day': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6247.png' },
  'Point Pleasant Beach': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4317.png' },
  'Point Pleasant Boro': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4318.png' },
  'Rahway': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4349.png' },
  'Randolph': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4360.png' },
  'Red Bank Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5795.png' },
  'St. Augustine': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4976.png' },
  'Ridgefield/Palisades Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4395.png' },
  'Riverside': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4409.png' },
  'Robbinsville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4414.png' },
  'Morris Hills': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3954.png' },
  'Morris Knolls': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3955.png' },
  'Roselle Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4457.png' },
  'Rumson-Fair Haven': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4464.png' },
  'Triton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4696.png' },
  'Rutherford': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4466.png' },
  'St. Mary (Ruth.)': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5120.png' },
  'Saddle Brook': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4469.png' },
  'Salem': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4472.png' },
  'Scotch Plains-Fanwood': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4500.png' },
  'Union Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6208.png' },
  'Cumberland': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/2927.png' },
  'Secaucus': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4505.png' },
  'Gloucester Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3245.png' },
  'Washington Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4829.png' },
  'Montgomery': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3940.png' },
  'South Plainfield': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4556.png' },
  'Sterling': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4594.png' },
  'Franklin': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3177.png' },
  'Rutgers Prep': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6325.png' },
  'Immaculata': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6134.png' },
  'Somerville': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4543.png' },
  'South Amboy': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4546.png' },
  'South River': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4559.png' },
  'Pope John': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6157.png' },
  'Sparta': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4577.png' },
  'Sussex Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4617.png' },
  'Spotswood': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4581.png' },
  'Dayton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3547.png' },
  'Lenape Valley': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3646.png' },
  'Roxbury': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4462.png' },
  'Oratory': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6216.png' },
  'Summit': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4611.png' },
  'High Point': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3371.png' },
  'Seneca': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4508.png' },
  'Monmouth': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3935.png' },
  'Ranney': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6324.png' },
  'Donovan Catholic': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/5976.png' },
  'Toms River East': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4685.png' },
  'Toms River North': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4686.png' },
  'Toms River South': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4687.png' },
  'Trenton': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4694.png' },
  'Pinelands': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4303.png' },
  'Union City': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6402.png' },
  'Union': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4710.png' },
  'Vernon': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4741.png' },
  'Vineland': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4752.png' },
  'Eastern': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3023.png' },
  'Shore': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4522.png' },
  'Waldwick': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4762.png' },
  'Wall': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4764.png' },
  'Wallington': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4767.png' },
  'Watchung Hills': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4832.png' },
  'Warren Hills': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4793.png' },
  'Weehawken': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4839.png' },
  'Memorial': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3864.png' },
  'Westampton Tech': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/6337.png' },
  'Westfield': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4870.png' },
  'Haddon Township': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3291.png' },
  'West Deptford': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4849.png' },
  'Whippany Park': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4876.png' },
  'Wildwood': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4892.png' },
  'Williamstown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4910.png' },
  'Willingboro': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4912.png' },
  'Wood-Ridge': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4951.png' },
  'Woodbridge': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4933.png' },
  'Gateway': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3209.png' },
  'Woodstown': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/4965.png' },
  'Kingsway': { div:'', mascot:'', p:'#1a2a4a', s:'#2a4a7a', t:'#8aaccc', bg:'#060d18', logo:'https://nj.vsand-static.com/Logos/3583.png' },
};\n\n""")

    # Stat configs
    lines.append("""const HSC = {
  AVG:     { label:'AVG',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  SLG:     { label:'SLG',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  OBP:     { label:'OBP',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  OPS:     { label:'OPS',  fmt: v => v.toFixed(3) },
  BsR:     { label:'BsR',  fmt: v => v.toFixed(1) },
  ISO:     { label:'ISO',  fmt: v => v.toFixed(3).replace(/^0/,'') },
  BB_pct:  { label:'BB%',  fmt: v => v.toFixed(1)+'%' },
  wOBA:    { label:'wOBA', fmt: v => v.toFixed(3).replace(/^0/,'') },
  wRAA:    { label:'wRAA', fmt: v => v.toFixed(1) },
  wRC:     { label:'wRC',  fmt: v => v.toFixed(0) },
  wRC_plus:{ label:'wRC+', fmt: v => v.toFixed(0) },
  OFF:     { label:'OFF',  fmt: v => v.toFixed(1) }
};
const HIT_TABLE_COLS = ['wRC_plus','wOBA','OPS','AVG','SLG','OBP','ISO','BsR','OFF'];
const HIT_PCT_GROUPS = [
  { title:'Advanced Rate', stats:['wRC_plus','wRC','wOBA','wRAA'] },
  { title:'Traditional',   stats:['OPS','OBP','SLG','AVG'] },
  { title:'Other',         stats:['ISO','BB_pct','BsR','OFF'] }
];\n\n""")

    lines.append("""const PSC = {
  IP:       { label:'IP',   fmt: v => v.toFixed(1),  lowerBetter:false },
  H:        { label:'H',    fmt: v => v.toFixed(0),  lowerBetter:true  },
  R:        { label:'R',    fmt: v => v.toFixed(0),  lowerBetter:true  },
  ER:       { label:'ER',   fmt: v => v.toFixed(0),  lowerBetter:true  },
  BB:       { label:'BB',   fmt: v => v.toFixed(0),  lowerBetter:true  },
  K:        { label:'K',    fmt: v => v.toFixed(0),  lowerBetter:false },
  HB:       { label:'HB',   fmt: v => v.toFixed(0),  lowerBetter:true  },
  ERA:      { label:'ERA',  fmt: v => v.toFixed(2),  lowerBetter:true  },
  ERA_minus:{ label:'ERA-', fmt: v => v.toFixed(0),  lowerBetter:true  },
  FIP:      { label:'FIP',  fmt: v => v.toFixed(2),  lowerBetter:true  },
  FIP_minus:{ label:'FIP-', fmt: v => v.toFixed(0),  lowerBetter:true  },
  RAA:      { label:'RAA',  fmt: v => v.toFixed(1),  lowerBetter:false },
  K7:       { label:'K/7',  fmt: v => v.toFixed(2),  lowerBetter:false },
  BB7:      { label:'BB/7', fmt: v => v.toFixed(2),  lowerBetter:true  },
  PIP:      { label:'P/IP', fmt: v => v.toFixed(1),  lowerBetter:false },
  KBB:      { label:'K/BB', fmt: v => v.toFixed(2),  lowerBetter:false },
  WHIP:     { label:'WHIP', fmt: v => v.toFixed(2),  lowerBetter:true  },
  WAR:      { label:'WAR',  fmt: v => v.toFixed(1),  lowerBetter:false }
};
const PIT_TABLE_COLS = ['ERA','FIP','WHIP','K7','BB7','KBB','ERA_minus','FIP_minus','WAR','IP'];
const PIT_PCT_GROUPS = [
  { title:'Run Prevention',  stats:['ERA','ERA_minus','FIP','FIP_minus'] },
  { title:'Command & Stuff', stats:['WHIP','K7','BB7','KBB'] },
  { title:'Value',           stats:['WAR','RAA','IP','K'] }
];\n\n""")

    # Hitters array
    lines.append("const AP = [\n")
    for p in all_hitters:
        lines.append(f"  {json.dumps(p)},\n")
    lines.append("];\n\n")

    # Pitchers array
    lines.append("const PP = [\n")
    for p in all_pitchers:
        lines.append(f"  {json.dumps(p)},\n")
    lines.append("];\n\n")

    # Schedules object
    lines.append("const SCHEDULES = {\n")
    for team, sched in all_schedules.items():
        lines.append(f"  {json.dumps(team)}: {json.dumps(sched)},\n")
    lines.append("};\n")

    with open(out_path, "w") as f:
        f.writelines(lines)

    print(f"\n✅  Written to {out_path}")
    return out_path

def print_summary(all_hitters, all_pitchers):
    print(f"\n{'─'*50}")
    print(f"  Total hitters:  {len(all_hitters)}")
    print(f"  Total pitchers: {len(all_pitchers)}")
    teams = sorted(set(p['team'] for p in all_hitters))
    print(f"  Teams scraped:  {', '.join(teams)}")

    # Top 5 hitters by wRC+
    print(f"\n  Top 5 by wRC+ (qualified):")
    qualified = [p for p in all_hitters if p['qualified']]
    for p in sorted(qualified, key=lambda x: x['wRC_plus'], reverse=True)[:5]:
        print(f"    {p['name']:25} {p['team']:15} wRC+: {p['wRC_plus']}")

    # Top 5 pitchers by ERA
    print(f"\n  Top 5 ERA (qualified):")
    qpit = [p for p in all_pitchers if p['qualPitch']]
    for p in sorted(qpit, key=lambda x: x['ERA'])[:5]:
        print(f"    {p['name']:25} {p['team']:15} ERA: {p['ERA']:.2f}")
    print(f"{'─'*50}\n")

if __name__ == "__main__":
    # Allow scraping a single team via CLI arg
    if len(sys.argv) > 1:
        slug = sys.argv[1]
        name = slug.replace('-', ' ').title()
        teams_to_scrape = {name: slug}
    else:
        teams_to_scrape = TEAMS

    print(f"\n🔍 Scraping {len(teams_to_scrape)} team(s) from highschoolsports.nj.com...\n")

    all_hitters   = []
    all_pitchers  = []
    all_schedules = {}

    for display_name, slug in teams_to_scrape.items():
        hitters, pitchers, schedule = scrape_team(display_name, slug)
        all_hitters.extend(hitters)
        all_pitchers.extend(pitchers)
        all_schedules[display_name] = schedule
        time.sleep(0.5)  # be polite to the server

    print_summary(all_hitters, all_pitchers)
    generate_js(all_hitters, all_pitchers, all_schedules)
