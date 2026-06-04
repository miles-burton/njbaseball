# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

NJBaseball — a static single-page baseball analytics site for the Super Essex Conference (Essex County, NJ). It scrapes raw stats from highschoolsports.nj.com, computes advanced sabermetric metrics, and renders them as an interactive leaderboard site hosted on GitHub Pages.

There is no build step, no framework, no package.json. Everything runs in the browser directly.

## Updating the Live Site

```bash
./sync.sh          # scrape all teams → rebuild data.js → git push
python3 scraper.py # scrape only (no push)
python3 scraper.py west-orange-west-orange  # scrape one team by slug
```

The site auto-deploys at https://miles-burton.github.io/njbaseball within ~30s of every push.

## File Structure

| File | Purpose |
|------|---------|
| `scraper.py` | Scrapes nj.com, computes all advanced stats, writes `js/data.js` |
| `js/data.js` | **Auto-generated** — never edit by hand. Contains `AP[]`, `PP[]`, `TM{}`, `HSC{}`, `PSC{}`, `HIT_TABLE_COLS`, `PIT_TABLE_COLS`, `HIT_PCT_GROUPS`, `PIT_PCT_GROUPS` |
| `js/app.js` | All rendering logic. Reads from globals defined in `data.js` |
| `css/style.css` | All styles. Uses CSS variables (`--bg`, `--accent`, etc.) |
| `index.html` | Markup only — no inline scripts or styles |
| `sync.sh` | One-command scrape + push |

## Architecture

`data.js` is loaded first and defines globals consumed by `app.js`. There is no module system — everything is plain global JS.

**Data flow:**
```
nj.com HTML → scraper.py → js/data.js (AP[], PP[]) → app.js renders tables
```

**View system:** Five named views (`leaderboard`, `pitching`, `player`, `teams`, `team`) toggled by `showView(v)`. Only one is `display:block` at a time. `prevView` tracks navigation history for the back button.

**Percentile coloring:** `calcPct(vals, v, lowerBetter)` ranks a value against the qualified pool. `pc(percentile)` maps the result to a color. Red = elite, grey = average, blue = poor. Applied to every stat cell in both leaderboards.

## Adding Teams

In `scraper.py`, add to both `TEAMS` dict and the `TM` block inside `generate_js()`:

```python
# TEAMS dict
"School Name": "town-school-name",   # must match highschoolsports.nj.com/school/[slug]

# TM block — find logo ID from the og:image tag on their nj.com stats page
'School Name': { mascot:'...', p:'#primary', s:'#secondary', t:'#text', bg:'#dark-bg',
    logo:'https://nj.vsand-static.com/Logos/XXXX.png' },
```

Also add the team to both `<select>` dropdowns in `index.html`.

## Stat Formulas (computed in scraper.py)

**Hitting** (inputs: AB, H, 1B, 2B, 3B, HR, BB, HBP, SB, SF, SH):
- `PA = AB + BB + HBP + SF + SH`
- `wOBA = (0.7*(BB+HBP) + 0.9*1B + 1.3*2B + 1.6*3B + 2*HR) / PA`
- `wRAA = ((wOBA - 0.353) / 1.12) * PA`
- `wRC = wRAA + (PA * 0.177)`
- `wRC+ = ((wOBA - 0.353) / 1.12 + 0.177) / 0.177 * 100`
- `BsR = (SB * 0.2) + (3B * 0.1)`
- `OFF = wRAA + BsR`

**Pitching** (inputs: IP, H, ER, BB, K, HB):
- `ERA = (ER / IP) * 9`
- `FIP = ((3*(BB+HB) - 2*K) / IP) + 3.10`
- `ERA- = (ERA / 4.31) * 100`
- `FIP- = (FIP / 4.31) * 100`
- `RAA = ((4.31 - ERA) / 9) * IP`
- `WAR = RAA / 10`

League constants (adjust each season at top of `scraper.py`): `WOBA_LEAGUE=0.353`, `R_PA_LEAGUE=0.177`, FIP constant `3.10`, ERA baseline `4.31`.

## Current Teams

**Liberty:** West Orange, Verona, Caldwell, Nutley, SHP, SBP, MKA  
**American:** Montclair, Columbia, Bloomfield, Cedar Grove, Glen Ridge, Livingston, Millburn  
**National:** Newark Academy, Belleville, Barringer, East Orange, West Essex, Technology, Orange, Weequahic

## Known Quirks

- `js/data.js` is committed to git (it's the "database"). `sync.sh` runs `git add -A` so it always gets included.
- nj.com's `&bull;` separates player name/year/position in the HTML. The scraper converts it to `•` before parsing — if player names show up mangled, check `get_table_rows()`.
- SHP logo (ID 5412) occasionally times out on download — the CDN URL still works fine in the browser.
- `data.scraped.js` in `js/` is a leftover artifact and unused — `data.js` is the live file.
- Qualified thresholds: 50 PA for hitters, 15 IP for pitchers. These control percentile pool membership and the `qualified`/`qualPitch` flags.
