# Supabase Setup

Supabase is optional for the current site. The main public stats still run through:

```text
NJ.com -> GitHub Actions -> static JS data files -> Vercel
```

Use Supabase first for reports, corrections, scrape logs, and future admin tools.

## 1. Create Tables

Open Supabase, go to SQL Editor, and run:

```sql
-- paste the contents of supabase/schema.sql
```

This creates:

- `problem_reports`: user-submitted site/data issues.
- `data_corrections`: future correction queue.
- `scrape_runs`: future scraper observability.
- `sport_snapshots`: future database-backed published data.

RLS is enabled. Public visitors can insert reports/corrections, but they cannot read the report table.

## 2. Connect the Site

In Supabase:

1. Go to Project Settings.
2. Open API.
3. Copy the Project URL.
4. Copy the anon public key.
5. Paste both into `js/supabase-config.js`.

The anon key is allowed to be public as long as RLS policies stay locked down.

## 3. Current Behavior

When Supabase config is filled in, the Report form inserts into `problem_reports`.

If Supabase is not configured or the insert fails, the site falls back to opening a prefilled GitHub issue.

## 4. Recommended Fall Plan

For fall, keep Supabase in this order:

1. Problem reports and correction requests.
2. Scrape run logs.
3. Admin/correction dashboard.
4. Historical season database.
5. Full API-backed data if static JS files become too large.

Do not move the main rankings/leaders data into Supabase until the static pipeline becomes too slow or too hard to manage.

