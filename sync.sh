#!/bin/bash
# NJ Baseball Savant — one command to scrape stats and update the live site
# Usage: ./sync.sh

set -e
cd "$(dirname "$0")"

echo "🔍 Scraping latest stats from nj.com..."
python3 scraper.py

echo ""
echo "🚀 Pushing to GitHub..."
git add -A
git commit -m "Update stats $(date '+%Y-%m-%d')"
git push

echo ""
echo "✅ Done! Site will update at https://miles-burton.github.io/njbaseball in ~30 seconds."
