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
    "West Orange":     "west-orange-west-orange",
    "Verona":          "verona-verona",
    "Caldwell":        "west-caldwell-caldwell",
    "Nutley":          "nutley-nutley",
    "SHP":             "west-orange-seton-hall-prep",
    "SBP":             "newark-st-benedicts",
    "MKA":             "montclair-montclair-kimberley",
    # ── American Division ─────────────────────────────────────────────────
    "Montclair":       "montclair-montclair",
    "Columbia":        "maplewood-columbia",
    "Bloomfield":      "bloomfield-bloomfield",
    "Cedar Grove":     "cedar-grove-cedar-grove",
    "Glen Ridge":      "glen-ridge-glen-ridge",
    "Livingston":      "livingston-livingston",
    "Millburn":        "millburn-millburn",
    # ── National Division ─────────────────────────────────────────────────
    "Newark Academy":  "livingston-newark-academy",
    "Belleville":      "belleville-belleville",
    "Barringer":       "newark-barringer",
    "East Orange":     "east-orange-east-orange",
    "West Essex":      "north-caldwell-west-essex",
    "Technology":      "newark-technology",
    "Orange":          "orange-orange",
    "Weequahic":       "newark-weequahic",
}

# ── SCRAPER ────────────────────────────────────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def fetch(slug):
    url = f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}/stats"
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return r.read().decode("utf-8")

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
        html   = fetch(slug)
        tables = get_table_rows(html)
        hitters  = parse_hitting(tables[0],  display_name) if len(tables) > 0 else []
        pitchers = parse_pitching(tables[1], display_name) if len(tables) > 1 else []
        print(f"{len(hitters)} hitters, {len(pitchers)} pitchers")
        return hitters, pitchers
    except Exception as e:
        print(f"ERROR: {e}")
        return [], []

def generate_js(all_hitters, all_pitchers):
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
  'West Orange':    { mascot:'Mountaineers', p:'#1e3a6e', s:'#4a7cc7', t:'#a8c8f0', bg:'#0a1628', logo:'https://nj.vsand-static.com/Logos/4863.png' },
  'Verona':         { mascot:'Hillbillies',  p:'#7a1010', s:'#a01818', t:'#d47070', bg:'#1e0505', logo:'https://nj.vsand-static.com/Logos/4742.png' },
  'Caldwell':       { mascot:'Chiefs',       p:'#1a35a0', s:'#2a50c8', t:'#80a8e8', bg:'#060d28', logo:'https://nj.vsand-static.com/Logos/6250.png' },
  'Nutley':         { mascot:'Raiders',      p:'#8b1a2a', s:'#b02535', t:'#d07080', bg:'#1a0508', logo:'https://nj.vsand-static.com/Logos/4185.png' },
  'SHP':            { mascot:'Pirates',      p:'#8b0000', s:'#b00000', t:'#e07070', bg:'#1e0000', logo:'https://nj.vsand-static.com/Logos/5412.png' },
  'SBP':            { mascot:'Gray Bees',    p:'#6b1520', s:'#8b1a28', t:'#c08088', bg:'#150508', logo:'https://nj.vsand-static.com/Logos/5380.png' },
  'MKA':            { mascot:'Cougars',      p:'#1a2a6b', s:'#7a6030', t:'#b09060', bg:'#07091e', logo:'https://nj.vsand-static.com/Logos/6252.png' },
  // ── American Division ──────────────────────────────────────────────────
  'Montclair':      { mascot:'Mounties',     p:'#8b6914', s:'#c8960c', t:'#f0c040', bg:'#1e1500', logo:'https://nj.vsand-static.com/Logos/3939.png' },
  'Columbia':       { mascot:'Cougars',      p:'#0a4a1a', s:'#1a7a30', t:'#60c870', bg:'#051008', logo:'https://nj.vsand-static.com/Logos/2890.png' },
  'Bloomfield':     { mascot:'Bengals',      p:'#a04010', s:'#d05818', t:'#f0a060', bg:'#200d05', logo:'https://nj.vsand-static.com/Logos/2683.png' },
  'Cedar Grove':    { mascot:'Panthers',     p:'#1a1a8b', s:'#2a2ac8', t:'#8080e8', bg:'#06061e', logo:'https://nj.vsand-static.com/Logos/2785.png' },
  'Glen Ridge':     { mascot:'Ridgers',      p:'#8b1a1a', s:'#c02828', t:'#e08080', bg:'#1e0606', logo:'https://nj.vsand-static.com/Logos/3234.png' },
  'Livingston':     { mascot:'Lancers',      p:'#1a5a1a', s:'#2a8a2a', t:'#70c870', bg:'#071507', logo:'https://nj.vsand-static.com/Logos/3711.png' },
  'Millburn':       { mascot:'Millers',      p:'#1a1a8b', s:'#3030b0', t:'#8888e0', bg:'#06061e', logo:'https://nj.vsand-static.com/Logos/3915.png' },
  // ── National Division ──────────────────────────────────────────────────
  'Newark Academy': { mascot:'Minutemen',    p:'#6b1a1a', s:'#902828', t:'#d07070', bg:'#150606', logo:'https://nj.vsand-static.com/Logos/6253.png' },
  'Belleville':     { mascot:'Buccaneers',   p:'#8b4500', s:'#c06010', t:'#e8a060', bg:'#1e0e00', logo:'https://nj.vsand-static.com/Logos/2646.png' },
  'Barringer':      { mascot:'Blue Bears',   p:'#0a2a6b', s:'#1a4aa0', t:'#6090d8', bg:'#05101e', logo:'https://nj.vsand-static.com/Logos/2623.png' },
  'East Orange':    { mascot:'Jaguars',      p:'#1a6b1a', s:'#2a9a2a', t:'#70d070', bg:'#071507', logo:'https://nj.vsand-static.com/Logos/3018.png' },
  'West Essex':     { mascot:'Knights',      p:'#8b0a0a', s:'#b81818', t:'#e07070', bg:'#1e0505', logo:'https://nj.vsand-static.com/Logos/4855.png' },
  'Technology':     { mascot:'Panthers',     p:'#1a1a5a', s:'#2828a0', t:'#7878d8', bg:'#060614', logo:'https://nj.vsand-static.com/Logos/4632.png' },
  'Orange':         { mascot:'Tornadoes',    p:'#8b4a00', s:'#c86800', t:'#f0a030', bg:'#1e1000', logo:'https://nj.vsand-static.com/Logos/4222.png' },
  'Weequahic':      { mascot:'Indians',      p:'#1a1a8b', s:'#2828b8', t:'#7878e0', bg:'#06061e', logo:'https://nj.vsand-static.com/Logos/4840.png' }
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
    lines.append("];\n")

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

    all_hitters  = []
    all_pitchers = []

    for display_name, slug in teams_to_scrape.items():
        hitters, pitchers = scrape_team(display_name, slug)
        all_hitters.extend(hitters)
        all_pitchers.extend(pitchers)
        time.sleep(0.5)  # be polite to the server

    print_summary(all_hitters, all_pitchers)
    generate_js(all_hitters, all_pitchers)
