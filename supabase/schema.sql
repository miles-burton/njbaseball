-- NJ Sports Index Supabase foundation.
-- Run this in the Supabase SQL editor for your project.

create extension if not exists pgcrypto;

create table if not exists public.problem_reports (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  status text not null default 'new' check (status in ('new', 'triaged', 'fixed', 'ignored')),
  site text not null default 'NJ Sports Index',
  sport text not null default '',
  season text not null default '',
  page_url text not null default '',
  report_type text not null default '',
  details text not null default '',
  contact text not null default '',
  theme text not null default '',
  user_agent text not null default '',
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists problem_reports_status_created_idx
  on public.problem_reports (status, created_at desc);

create index if not exists problem_reports_sport_season_idx
  on public.problem_reports (sport, season);

alter table public.problem_reports enable row level security;

drop policy if exists "Public can create problem reports" on public.problem_reports;
create policy "Public can create problem reports"
  on public.problem_reports
  for insert
  to anon, authenticated
  with check (true);

create table if not exists public.data_corrections (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  status text not null default 'new' check (status in ('new', 'reviewing', 'approved', 'rejected', 'applied')),
  sport text not null,
  season text not null,
  entity_type text not null check (entity_type in ('team', 'player', 'game', 'stat', 'ranking', 'other')),
  entity_name text not null default '',
  source_url text not null default '',
  submitted_value text not null default '',
  corrected_value text not null default '',
  notes text not null default '',
  contact text not null default '',
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists data_corrections_status_created_idx
  on public.data_corrections (status, created_at desc);

create index if not exists data_corrections_sport_season_idx
  on public.data_corrections (sport, season);

alter table public.data_corrections enable row level security;

drop policy if exists "Public can create data corrections" on public.data_corrections;
create policy "Public can create data corrections"
  on public.data_corrections
  for insert
  to anon, authenticated
  with check (true);

create table if not exists public.scrape_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  sport text not null,
  season text not null,
  source text not null default 'highschoolsports.nj.com',
  status text not null check (status in ('started', 'success', 'failed')),
  teams_found integer not null default 0,
  players_found integer not null default 0,
  games_found integer not null default 0,
  commit_sha text not null default '',
  error text not null default '',
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists scrape_runs_sport_created_idx
  on public.scrape_runs (sport, created_at desc);

alter table public.scrape_runs enable row level security;

create table if not exists public.sport_snapshots (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  sport text not null,
  gender text not null default '',
  season text not null,
  payload jsonb not null,
  published boolean not null default false,
  source_commit text not null default ''
);

create unique index if not exists sport_snapshots_unique_published_idx
  on public.sport_snapshots (sport, gender, season)
  where published = true;

alter table public.sport_snapshots enable row level security;

drop policy if exists "Public can read published sport snapshots" on public.sport_snapshots;
create policy "Public can read published sport snapshots"
  on public.sport_snapshots
  for select
  to anon, authenticated
  using (published = true);

