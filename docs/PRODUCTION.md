# NJ Sports Index Production Setup

## Hosting

The site is a static Vercel deployment backed by GitHub. Vercel should be connected to the `main` branch, so any push to `main` redeploys the public site.

`vercel.json` adds clean public routes:

- `/` -> sports home
- `/diamond` and `/baseball` -> Diamond Index
- `/pitch`, `/soccer`, and `/boys-soccer` -> boys Pitch Index
- `/girls-soccer` -> girls Pitch Index
- `/gridiron` and `/football` -> Gridiron Index
- `/court`, `/basketball`, and `/boys-basketball` -> Court Index

JavaScript and CSS are marked `must-revalidate` so daily data updates do not get stuck behind stale browser/CDN cache.

## Daily Data Updates

The site currently updates from NJ.com through GitHub Actions:

- `.github/workflows/update-stats.yml` refreshes baseball data with `scraper.py`.
- `.github/workflows/update-pitch.yml` refreshes boys and girls soccer data with `pitch_scraper.py`.
- `.github/workflows/update-football.yml` refreshes football data with `football_scraper.py`.
- `.github/workflows/update-basketball.yml` refreshes boys basketball data with `basketball_scraper.py`.

Each workflow commits changed files back to GitHub. Vercel then redeploys from that commit.

## Fall Season Readiness

Fall sports use the NJ.com school-year season. On or after July 1, the scrapers default to the new school year, such as `2026-2027`.

Manual overrides are available from GitHub Actions:

- `Update Pitch Index` accepts an optional `season` input and sends it to `PITCH_SEASON`.
- `Update Gridiron Index` accepts an optional `season` input and sends it to `FOOTBALL_SEASON`.
- `Update Stats` accepts an optional `season` input and sends it to `BASEBALL_SEASON`.
- `Update Court Index` accepts an optional `season` input and sends it to `BASKETBALL_SEASON`.

Run the readiness check locally:

```bash
python3 scripts/fall_readiness_check.py
```

Run it in GitHub:

1. Open GitHub Actions.
2. Select `Fall Readiness Check`.
3. Click `Run workflow`.

Before NJ.com publishes fall data, warnings that local data files are still on the previous season are normal. After NJ.com has standings and schedules for fall, those warnings should disappear after the first successful scrape.

## Instagram Drafts

`.github/workflows/instagram-drafts.yml` runs every morning and creates post-ready SVG drafts plus captions from the current site data.

Outputs are uploaded as a GitHub Actions artifact named `instagram-drafts-<run id>`.

Run it manually:

1. Open GitHub Actions.
2. Select `Generate Instagram Drafts`.
3. Click `Run workflow`.
4. Download the artifact from the completed run.

Local run:

```bash
python3 scripts/generate_instagram_drafts.py
```

The local output goes to `dist/instagram-drafts/<date>/`.

## Auto-Posting Roadmap

Automatic posting to Instagram requires a Meta Business or Creator account and Instagram Graph API credentials. The safe next step is:

1. Keep generating drafts automatically.
2. Review quality for a week.
3. Add Meta credentials as GitHub repository secrets.
4. Add a publishing workflow that posts approved daily graphics.

The site should not store API keys in source files.

## Future Sports

To add another sport cleanly:

1. Add a scraper that writes one static data file in `js/`.
2. Reuse the existing page shell and design tokens.
3. Add a GitHub Action schedule for that sport.
4. Add a Vercel clean route.
5. Add that sport to `scripts/generate_instagram_drafts.py`.
