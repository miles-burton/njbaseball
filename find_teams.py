#!/usr/bin/env python3
"""
Diamond Index — NJ Baseball Team Finder
Crawls highschoolsports.nj.com to discover every baseball team in NJ
that has stats entered for the current season.

Usage:
  python3 find_teams.py              # discover all teams, print results
  python3 find_teams.py --add        # also add new teams to scraper.py automatically
"""

import urllib.request
import ssl
import certifi
import re
import time
import sys
import json

SEASON  = "2025-2026"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
CTX     = ssl.create_default_context(cafile=certifi.where())

# Known conferences on nj.com — used to group discovered teams
CONFERENCES = [
    "Big North",
    "Cape-Atlantic",
    "Colonial Valley",
    "Greater Middlesex",
    "Hunterdon-Warren-Sussex",
    "Jersey Shore",
    "Middlesex County",
    "Northeast",
    "North Jersey Interscholastic",
    "Passaic County",
    "Shore",
    "Skyland",
    "Super Essex",
    "Union County",
    "Burlington County",
    "Camden County",
]

def fetch(url, timeout=12):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8")

def has_stats(slug):
    """Return (has_data, logo_id, num_hitters) for a given school slug."""
    url = f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}/stats"
    try:
        html = fetch(url, timeout=8)
        tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
        if not tables:
            return False, None, 0
        rows = len(re.findall(r'<tr', tables[0])) - 1
        if rows < 3:  # skip teams with almost no data
            return False, None, rows
        logo = re.search(r'Logos/(\d+)\.png', html)
        logo_id = logo.group(1) if logo else None
        # Get school display name
        title = re.search(r'<title>([^<]+)</title>', html)
        name  = title.group(1).replace(' Baseball 2025-2026 Stats - NJ.com','').strip() if title else slug
        return True, logo_id, rows
    except:
        return False, None, 0

def get_school_name(slug):
    """Get the display name for a school from its stats page title."""
    url = f"https://highschoolsports.nj.com/school/{slug}/baseball/season/{SEASON}/stats"
    try:
        html = fetch(url, timeout=8)
        title = re.search(r'<title>([^<]+)</title>', html)
        if title:
            return title.group(1).replace(' Baseball 2025-2026 Stats - NJ.com','').strip()
    except:
        pass
    return slug.replace('-', ' ').title()

def crawl_conference(conf_slug):
    """Get all team slugs from a conference standings page."""
    url = f"https://highschoolsports.nj.com/baseball/standings/season/{SEASON}?conference={conf_slug}"
    try:
        html = fetch(url)
        slugs = re.findall(r'/school/([a-z0-9\-]+)/baseball', html)
        return list(dict.fromkeys(slugs))  # dedupe, preserve order
    except Exception as e:
        return []

def crawl_all_schools():
    """Crawl the main schools directory for any school with baseball."""
    url = f"https://highschoolsports.nj.com/baseball/schools"
    try:
        html = fetch(url)
        slugs = re.findall(r'/school/([a-z0-9\-]+)', html)
        return list(dict.fromkeys(slugs))
    except:
        return []

def crawl_nj_teams():
    """Main crawler — finds all NJ baseball teams with stats this season."""
    print("🔍 Crawling highschoolsports.nj.com for NJ baseball teams...\n")

    all_slugs = set()

    # Method 1: Crawl each conference standings page
    conf_map = {
        'BCSL':         'Burlington County',
        'Big':          'Big North',
        'Cape-Atlantic':'Cape-Atlantic',
        'Colonial':     'Colonial',
        'CVC':          'Colonial Valley',
        'GMC':          'Greater Middlesex',
        'HCIAL':        'HCIAL',
        'NJAC':         'NJAC',
        'NJIC':         'NJIC',
        'Olympic':      'Olympic',
        'SEC':          'Super Essex',
        'Shore':        'Shore',
        'Skyland':      'Skyland',
        'Tri-County':   'Tri-County',
        'UCC':          'Union County',
    }

    print("  Scraping conference standings pages...")
    for code, name in conf_map.items():
        slugs = crawl_conference(code)
        new = [s for s in slugs if s not in all_slugs]
        all_slugs.update(slugs)
        if slugs:
            print(f"    {name}: {len(slugs)} teams ({len(new)} new)")
        time.sleep(0.3)

    # Method 2: Also try the baseball schools listing
    print("\n  Crawling baseball schools directory...")
    extra = crawl_all_schools()
    new_extra = [s for s in extra if s not in all_slugs]
    all_slugs.update(extra)
    print(f"    Found {len(extra)} slugs, {len(new_extra)} new")

    print(f"\n  Total unique slugs found: {len(all_slugs)}")
    print("\n  Checking which have stats this season...\n")

    # Now check each slug for actual stats data
    results = []
    no_data = []
    errors  = []

    slugs_list = sorted(all_slugs)
    for i, slug in enumerate(slugs_list):
        ok, logo_id, rows = has_stats(slug)
        if ok:
            name = get_school_name(slug)
            results.append({
                'slug':    slug,
                'name':    name,
                'logo_id': logo_id,
                'rows':    rows,
            })
            print(f"  ✅ [{i+1}/{len(slugs_list)}] {name:35} ({rows} hitters)")
        else:
            no_data.append(slug)
            if i % 20 == 0:
                print(f"  ... [{i+1}/{len(slugs_list)}] checked, {len(results)} with data so far")
        time.sleep(0.25)

    return results, no_data

def load_existing_teams():
    """Read currently configured teams from scraper.py."""
    with open('scraper.py', 'r') as f:
        content = f.read()
    existing = re.findall(r'"([^"]+)":\s*"([a-z0-9\-]+)"', content)
    # Filter to just the TEAMS dict section
    teams_section = re.search(r'TEAMS\s*=\s*\{(.*?)\}', content, re.DOTALL)
    if teams_section:
        pairs = re.findall(r'"([^"]+)":\s*"([a-z0-9\-]+)"', teams_section.group(1))
        return {slug: name for name, slug in pairs}
    return {}

def add_teams_to_scraper(new_teams):
    """Append newly discovered teams to the TEAMS dict in scraper.py."""
    with open('scraper.py', 'r') as f:
        content = f.read()

    additions = "\n    # ── Auto-discovered ──────────────────────────────────────────────────\n"
    for t in new_teams:
        additions += f'    "{t["name"]}":  "{t["slug"]}",\n'

    # Insert before the closing brace of TEAMS
    content = content.replace(
        '    # ── Independence Division ─────────────────────────────────────────',
        additions + '    # ── Independence Division ─────────────────────────────────────────',
        1
    )

    # For teams not already in a division block, append at end of TEAMS
    if additions not in content:
        content = re.sub(
            r'(    "Golda Och"[^\n]+\n)',
            r'\1' + additions,
            content
        )

    with open('scraper.py', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    add_mode = '--add' in sys.argv

    results, no_data = crawl_nj_teams()

    # Load existing teams
    existing = load_existing_teams()
    new_teams = [t for t in results if t['slug'] not in existing]

    print(f"\n{'='*60}")
    print(f"  Total teams with stats:    {len(results)}")
    print(f"  Already in scraper.py:     {len(results) - len(new_teams)}")
    print(f"  NEW teams found:           {len(new_teams)}")
    print(f"  Teams without stats:       {len(no_data)}")
    print(f"{'='*60}\n")

    if new_teams:
        print("NEW TEAMS TO ADD:")
        for t in new_teams:
            logo_url = f"https://nj.vsand-static.com/Logos/{t['logo_id']}.png" if t['logo_id'] else "none"
            print(f"  \"{t['name']}\": \"{t['slug']}\"  (logo: {t['logo_id']}, {t['rows']} hitters)")

        # Save results to JSON for review
        with open('discovered_teams.json', 'w') as f:
            json.dump({'new': new_teams, 'all': results}, f, indent=2)
        print(f"\n  Results saved to discovered_teams.json")

        if add_mode:
            add_teams_to_scraper(new_teams)
            print(f"\n  ✅ Added {len(new_teams)} teams to scraper.py")
            print("  Run ./sync.sh to scrape all teams and update the site.")
        else:
            print(f"\n  Run with --add to automatically add these to scraper.py:")
            print(f"  python3 find_teams.py --add")
    else:
        print("  No new teams found — scraper.py is already up to date!")
