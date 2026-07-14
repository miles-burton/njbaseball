# NJ Sports Index Sport Format

Every sport should feel like the same product with a different data model and accent color.

## Required Shell

Every sport page must include:

- Sticky `site-header`
- Brand logo in the top left
- `Leaders` dropdown
- `Teams` dropdown
- Direct nav tabs: `Rankings`, `Scores`, `Predictor`, `Standings`, `Glossary`, `Sports`, `Report`
- Season selector
- Light/dark toggle
- Global search
- Back button
- Report modal wired through Supabase with GitHub fallback

## Required Views

Each sport needs these canonical experiences:

- `home`
- `leaders`
- `rankings`
- `scores`
- `predictor`
- `standings`
- `teams`
- `glossary`
- `team`
- `player`
- `game` when the sport has game pages or box scores

Diamond Index currently maps older names into the same contract:

- `leaderboard` and `pitching` satisfy `leaders`
- `team-rankings` satisfies `rankings`

Future sports should use the canonical names directly.

## Shared Visual Rules

- Use `css/style.css` for the base design system.
- A sport-specific CSS file may only define accent color and sport-specific table/card details.
- Do not redesign the header, nav, report form, team page shell, player page shell, rankings shell, or score cards per sport.
- Use the same card radius, table density, typography, spacing, and dark/light mode tokens.
- Sport identity comes from accent color, labels, formulas, and data, not layout drift.

## Required Data Experiences

Every sport should eventually support:

- Team rankings
- Player leaders
- Team pages
- Player pages
- Scores and schedules
- Standings
- Matchup predictor
- Glossary
- Problem reports

## Enforcement

Run:

```bash
python3 scripts/check_sport_format.py
```

This verifies current sport pages against the shared shell contract. Add new sports to `js/sports-registry.js` and `scripts/check_sport_format.py` when they launch.

