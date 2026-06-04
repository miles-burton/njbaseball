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
    "West Orange":  "west-orange-west-orange",
    "Verona":       "verona-verona",
    "Caldwell":     "west-caldwell-caldwell",
    "Nutley":       "nutley-nutley",
    "SBP":          "west-orange-seton-hall-prep",
    "MKA":          "montclair-montclair-kimberley",
    # Add more teams here as you expand to all of NJ:
    # "Team Name": "town-school-name",
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

    lines = [
        "// AUTO-GENERATED by scraper.py\n",
        f"// Last updated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "// Do not edit by hand — run: python3 scraper.py\n\n",
    ]

    # Team identity (preserved from original)
    lines.append("""const TM = {
  'West Orange': { mascot:'Mountaineers', p:'#1c3a6e', s:'#4a7cc7', t:'#a8c4f0', bg:'#0c1e3a',
    svg:'<svg viewBox="0 0 24 24" fill="none"><polygon points="12,3 2,19 22,19" fill="#4a7cc7" opacity="0.9"/><polygon points="6,19 12,9 18,19" fill="#1c3a6e"/></svg>'},
  'Verona':      { mascot:'Hillbillies',  p:'#6b1a2a', s:'#b03050', t:'#f0b0c0', bg:'#2a0d14',
    svg:'<svg viewBox="0 0 24 24" fill="none"><ellipse cx="12" cy="10" rx="5" ry="5" fill="#b03050" opacity="0.9"/><rect x="5" y="17" width="14" height="3" rx="1.5" fill="#b03050" opacity="0.7"/></svg>'},
  'Caldwell':    { mascot:'Chiefs',       p:'#0d3060', s:'#2060c0', t:'#90c0f0', bg:'#071830',
    svg:'<svg viewBox="0 0 24 24" fill="none"><polygon points="12,2 3,9 3,21 21,21 21,9" fill="#2060c0" opacity="0.85"/><rect x="8" y="13" width="8" height="8" fill="#0d3060"/></svg>'},
  'Nutley':      { mascot:'Raiders',      p:'#5c1a1a', s:'#a03030', t:'#f0b0b0', bg:'#280a0a',
    svg:'<svg viewBox="0 0 24 24" fill="none"><path d="M12 2 L22 8 L22 16 L12 22 L2 16 L2 8 Z" fill="#a03030" opacity="0.8"/></svg>'},
  'SBP':         { mascot:'Gray Bees',    p:'#6b1520', s:'#9e2535', t:'#e09090', bg:'#28080e',
    svg:'<svg viewBox="0 0 24 24" fill="none"><ellipse cx="12" cy="13" rx="6" ry="7" fill="#9e2535" opacity="0.85"/><line x1="7" y1="10" x2="17" y2="10" stroke="#6b1520" stroke-width="1.5"/><line x1="7" y1="14" x2="17" y2="14" stroke="#6b1520" stroke-width="1.5"/><path d="M8 6 Q12 2 16 6" stroke="#9e2535" stroke-width="1.5" fill="none"/></svg>'},
  'MKA':         { mascot:'Cougars',      p:'#0e2d1a', s:'#1e7038', t:'#70d490', bg:'#061510',
    svg:'<svg viewBox="0 0 24 24" fill="none"><path d="M4 20 C4 11 8 5 12 4 C16 5 20 11 20 20" fill="#1e7038" opacity="0.85"/><circle cx="12" cy="9" r="3" fill="#0e2d1a"/><line x1="8" y1="7" x2="5" y2="4" stroke="#1e7038" stroke-width="1.3"/><line x1="16" y1="7" x2="19" y2="4" stroke="#1e7038" stroke-width="1.3"/></svg>'}
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
