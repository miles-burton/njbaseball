const $ = (id) => document.getElementById(id);
const TEAMS = PITCH_DATA.teams || [];
const SCORERS = PITCH_DATA.scorers || [];
const KEEPERS = PITCH_DATA.keepers || [];
const TEAM_BY_SLUG = Object.fromEntries(TEAMS.map((team) => [team.slug, team]));
const CONFERENCES = [...new Set(TEAMS.map((team) => team.conference))].sort();
const REPORT_ISSUE_URL = 'https://github.com/miles-burton/njbaseball/issues/new';
const state = {
  view: 'home',
  teamSlug: '',
  playerKey: '',
  rankingSort: { key: 'powerScore', asc: false },
  leaderType: 'scoring',
  leaderSort: { key: 'P', asc: false },
  filters: { query: '', conference: 'All' },
  leaderFilters: { query: '', conference: 'All', team: 'All', grade: 'All', min: 0 },
  predictor: {
    teamA: TEAMS[0]?.slug || '',
    teamB: TEAMS[1]?.slug || '',
    venue: 'neutral',
  },
};
const RANK_LOWER_BETTER = new Set(['adjD', 'gaPerGame', 'ga', 'luck']);

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function pct(value) {
  return Number.isFinite(value) ? value.toFixed(3).replace(/^0/, '') : '.000';
}

function signed(value, digits = 3) {
  if (!Number.isFinite(value)) return '—';
  return `${value > 0 ? '+' : ''}${value.toFixed(digits).replace(/^([-+])0/, '$1')}`;
}

function logoSrc(team) {
  if (!team) return '';
  const shared = typeof TEAM_LOGOS !== 'undefined' ? TEAM_LOGOS[team.name] : '';
  return shared || team.logo || '';
}

function logo(team, cls = 'team-logo') {
  const primary = logoSrc(team);
  const fallback = team?.logo && team.logo !== primary ? team.logo : '';
  return primary
    ? `<img class="${cls}" loading="lazy" decoding="async" src="${esc(primary)}" alt="" ${fallback ? `onerror="this.onerror=null;this.src='${esc(fallback)}'"` : ''}>`
    : `<span class="${cls}"></span>`;
}

function logoImg(team, size = 22) {
  const src = logoSrc(team);
  return src ? `<img loading="lazy" decoding="async" src="${esc(src)}" width="${size}" height="${size}" style="object-fit:contain;border-radius:3px;flex-shrink:0" alt="">` : '';
}

function setView(view, detail = '') {
  state.view = view;
  document.querySelectorAll('.view').forEach((el) => el.classList.remove('active'));
  $(`view-${view}`)?.classList.add('active');
  document.querySelectorAll('.pitch-nav [data-view]').forEach((btn) => {
    const active = btn.dataset.view === view ||
      (view === 'leaders' && btn.id === 'tab-leaders') ||
      ((view === 'teams' || view === 'team') && btn.id === 'tab-teams-dd');
    btn.classList.toggle('active', active);
  });
  if (view === 'team') state.teamSlug = detail;
  if (view === 'player') state.playerKey = decodeURIComponent(detail);
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function applyTheme(theme) {
  const safeTheme = theme === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = safeTheme;
  localStorage.setItem('diamondIndexTheme', safeTheme);
  const label = $('themeToggleLabel');
  if (label) label.textContent = safeTheme === 'light' ? 'Light' : 'Dark';
}

function toggleTheme() {
  applyTheme(document.documentElement.dataset.theme === 'light' ? 'dark' : 'light');
}

function initTheme() {
  const saved = localStorage.getItem('diamondIndexTheme');
  const preferred = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  applyTheme(saved || preferred);
}

function openReportProblem() {
  closeDropdowns();
  const modal = $('reportModal');
  if (!modal) return;
  modal.classList.add('open');
  modal.setAttribute('aria-hidden', 'false');
  setTimeout(() => $('reportDetails')?.focus(), 0);
}

function closeReportProblem() {
  const modal = $('reportModal');
  if (!modal) return;
  modal.classList.remove('open');
  modal.setAttribute('aria-hidden', 'true');
}

function submitProblemReport(event) {
  event.preventDefault();
  const type = $('reportType')?.value || 'Site problem';
  const details = $('reportDetails')?.value.trim() || '';
  const contact = $('reportContact')?.value.trim() || '';
  const title = `[Pitch Index Report] ${type}`;
  const body = [
    '## Problem type',
    type,
    '',
    '## Details',
    details,
    '',
    '## Page context',
    `URL: ${window.location.href}`,
    `Season: ${PITCH_DATA.season || ''}`,
    `Theme: ${document.documentElement.dataset.theme || 'dark'}`,
    `Browser: ${navigator.userAgent}`,
    '',
    '## Contact',
    contact || 'No contact provided',
  ].join('\n');
  window.open(`${REPORT_ISSUE_URL}?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`, '_blank', 'noopener');
  closeReportProblem();
}

function sortRows(rows, key, asc = false) {
  return [...rows].sort((a, b) => {
    const av = a[key] ?? '';
    const bv = b[key] ?? '';
    const value = typeof av === 'number' && typeof bv === 'number'
      ? av - bv
      : String(av).localeCompare(String(bv));
    return asc ? value : -value;
  });
}

function filteredTeams() {
  const q = state.filters.query.toLowerCase();
  return TEAMS.filter((team) => {
    const matchesQ = !q || team.name.toLowerCase().includes(q);
    const matchesConf = state.filters.conference === 'All' || team.conference === state.filters.conference;
    return matchesQ && matchesConf;
  });
}

function conferenceOptions(selected) {
  return `<option>All</option>${CONFERENCES.map((conf) => (
    `<option ${conf === selected ? 'selected' : ''}>${esc(conf)}</option>`
  )).join('')}`;
}

function teamButton(team) {
  return `<button class="linkish" data-team-slug="${esc(team.slug)}">${esc(team.name)}</button>`;
}

function linkedTeam(team, fallback = '') {
  return team
    ? `<button class="schedule-team-link" data-team-slug="${esc(team.slug)}">${esc(team.name)}</button>`
    : esc(fallback);
}

function teamChip(team) {
  if (!team) return '<span class="team-chip">Unknown</span>';
  return `<span class="team-chip">${logoImg(team, 14)}${esc(team.name)}</span>`;
}

function leaderPlayerCell(player) {
  const sub = [player.grade, player.division].filter(Boolean).join(' · ');
  return `<td class="player-cell">
    <div class="player-name">${esc(player.name)}</div>
    ${sub ? `<div class="player-sub">${esc(sub)}</div>` : ''}
  </td>`;
}

function playerKey(player) {
  return `${player.name}__${player.teamSlug}`;
}

function playerButton(player) {
  return `<button class="linkish" data-player-key="${encodeURIComponent(playerKey(player))}">${esc(player.name)}</button>`;
}

function closeDropdowns() {
  document.querySelectorAll('.nav-dropdown-menu').forEach((menu) => menu.classList.remove('open'));
}

function buildTeamsNav() {
  const el = $('teamsNavList');
  if (!el) return;
  el.innerHTML = CONFERENCES.map((conf) => {
    const teams = TEAMS.filter((team) => team.conference === conf).sort((a, b) => a.name.localeCompare(b.name));
    return `<div class="nav-dropdown-label">${esc(conf)}</div>` +
      teams.map((team) => `<button class="nav-dropdown-item" data-team-slug="${esc(team.slug)}" data-close-dropdowns="1" type="button">${esc(team.name)}</button>`).join('');
  }).join('<div class="nav-dropdown-divider"></div>');
}

function seasonStartYear() {
  const first = String(PITCH_DATA.season || '').match(/\d{4}/);
  return first ? Number(first[0]) : new Date().getFullYear();
}

function parsePitchDate(dateStr) {
  const m = String(dateStr || '').match(/(\d{1,2})\/(\d{1,2})/);
  if (!m) return null;
  const month = Number(m[1]);
  const day = Number(m[2]);
  const start = seasonStartYear();
  const year = month >= 8 ? start : start + 1;
  return new Date(year, month - 1, day);
}

function pitchDateKey(date) {
  if (!date) return '';
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function displayPitchDate(date) {
  return date ? date.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }) : '';
}

function cleanPitchOpponentLabel(opponent) {
  return String(opponent || '')
    .replace(/\s+2025\s+Boys Soccer.*$/i, '')
    .replace(/\s+NJSIAA.*$/i, '')
    .replace(/\s+Tournament.*$/i, '')
    .trim();
}

function resolveOpponentTeam(game) {
  if (game.opponentSlug && TEAM_BY_SLUG[game.opponentSlug]) return TEAM_BY_SLUG[game.opponentSlug];
  const label = cleanPitchOpponentLabel(game.opponent).toLowerCase();
  if (!label) return null;
  return TEAMS
    .filter((team) => team.slug !== game.teamSlug)
    .find((team) => label === team.name.toLowerCase() || label.includes(team.name.toLowerCase()));
}

function gameImportance(game) {
  const team = TEAM_BY_SLUG[game.teamSlug];
  const opp = TEAM_BY_SLUG[game.opponentSlug];
  const teamPower = team?.powerScore || 50;
  const oppPower = opp?.powerScore || 50;
  const avgPower = (teamPower + oppPower) / 2;
  const margin = Number.isFinite(game.margin) ? game.margin : Math.abs((game.teamScore ?? 0) - (game.opponentScore ?? 0));
  const closeBonus = Math.max(0, 4 - margin) * 2;
  const rankedBonus = (team?.rank <= 25 ? 6 : 0) + (opp?.rank <= 25 ? 6 : 0);
  const upsetBonus = (
    (game.result === 'W' && oppPower - teamPower > 10) ||
    (game.result === 'L' && teamPower - oppPower > 10)
  ) ? 8 : 0;
  const tournamentBonus = /tournament|county|njsiaa|sectional|final|semifinal|quarterfinal|playoff/i.test(`${game.opponent || ''} ${game.event || ''}`) ? 5 : 0;
  return avgPower + closeBonus + rankedBonus + upsetBonus + tournamentBonus;
}

function isTournamentGame(game) {
  return /tournament|county|njsiaa|sectional|final|semifinal|quarterfinal|playoff/i.test(`${game.opponent || ''} ${game.event || ''}`);
}

function allPitchGames() {
  const source = PITCH_DATA.games && PITCH_DATA.games.length
    ? PITCH_DATA.games
    : TEAMS.flatMap((team) => (team.schedule || []).map((game) => ({ ...game, team: team.name, teamSlug: team.slug })));
  const seen = new Set();
  return source.map((game) => {
    const date = parsePitchDate(game.date);
    const team = TEAM_BY_SLUG[game.teamSlug];
    const opp = resolveOpponentTeam(game);
    const margin = Math.abs((game.teamScore ?? 0) - (game.opponentScore ?? 0));
    const normalized = {
      ...game,
      dateObj: date,
      dateKey: pitchDateKey(date),
      teamName: team?.name || game.team || '',
      opponentSlug: opp?.slug || game.opponentSlug || '',
      opponentName: opp?.name || cleanPitchOpponentLabel(game.opponent) || game.opponent || '',
      margin,
      tournament: isTournamentGame(game),
    };
    normalized.importance = gameImportance(normalized);
    return normalized;
  }).filter((game) => {
    const names = [game.teamSlug || game.teamName, game.opponentSlug || game.opponentName].sort();
    const scores = [game.teamScore, game.opponentScore].filter((v) => v !== null && v !== undefined).sort((a, b) => Number(a) - Number(b));
    const key = [
      game.date,
      names[0],
      names[1],
      scores[0] ?? '',
      scores[1] ?? '',
    ].join('|');
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function completedPitchGames() {
  return allPitchGames()
    .filter((game) => game.result && game.teamScore !== null && game.opponentScore !== null)
    .sort((a, b) => (b.dateObj || 0) - (a.dateObj || 0) || b.importance - a.importance || a.margin - b.margin);
}

function upcomingPitchGames() {
  return allPitchGames()
    .filter((game) => !game.result || game.teamScore === null || game.opponentScore === null)
    .sort((a, b) => (a.dateObj || 0) - (b.dateObj || 0) || b.importance - a.importance);
}

function latestCompletedPitchGames() {
  const games = completedPitchGames();
  const latestKey = games[0]?.dateKey;
  return latestKey ? games.filter((game) => game.dateKey === latestKey).sort((a, b) => b.importance - a.importance || a.margin - b.margin) : [];
}

function teamOptions(selectedSlug) {
  return TEAMS.map((team) => `<option value="${esc(team.slug)}" ${team.slug === selectedSlug ? 'selected' : ''}>${esc(team.name)} · ${esc(team.record)} · #${team.rank}</option>`).join('');
}

function filterTeamOptions(selected = 'All') {
  return `<option value="All">All Teams</option>${TEAMS
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .map((team) => `<option value="${esc(team.slug)}" ${team.slug === selected ? 'selected' : ''}>${esc(team.name)}</option>`)
    .join('')}`;
}

function gradeOptions(selected = 'All') {
  const grades = [...new Set([...SCORERS, ...KEEPERS].map((player) => player.grade).filter(Boolean))].sort();
  return `<option value="All">All Grades</option>${grades.map((grade) => `<option value="${esc(grade)}" ${grade === selected ? 'selected' : ''}>${esc(grade)}</option>`).join('')}`;
}

function renderHome() {
  const topTeams = TEAMS.slice(0, 10);
  const topScorers = sortRows(SCORERS, 'P').slice(0, 3);
  const topKeepers = sortRows(KEEPERS, 'Saves').slice(0, 3);
  const recentGames = latestCompletedPitchGames().slice(0, 8);
  const upcomingGames = upcomingPitchGames().slice(0, 8);
  const recentDate = recentGames[0]?.dateObj;
  $('view-home').innerHTML = `
    <div class="home-hero pitch-hero">
      <div class="home-hero-inner">
        <div class="home-hero-text">
          <div class="home-hero-eyebrow">New Jersey Boys Soccer · ${esc(PITCH_DATA.season)} Season</div>
          <h1 class="home-hero-title">PITCH<br>INDEX</h1>
          <div class="home-hero-tagline">Measure the Match.</div>
          <p class="home-hero-sub">The boys soccer branch of NJ Sports Index, built from real NJ.com standings, schedules, scoring leaders, goalkeeper data, and team rankings.</p>
          <div class="home-hero-actions">
            <button class="home-btn-primary" data-view-target="rankings">Power Rankings</button>
            <button class="home-btn-secondary" data-view-target="leaders">Player Leaders</button>
          </div>
        </div>
      </div>
    </div>

    <div class="home-wrap">
      <div class="home-action-grid">
        <button class="home-action-card" data-view-target="rankings">
          <span>Pitch Score</span>
          <strong>Team rankings adjusted by record, goal profile, and schedule quality.</strong>
        </button>
        <button class="home-action-card" data-view-target="leaders">
          <span>Player Leaders</span>
          <strong>Scoring and goalkeeper leaderboards from the 2025 NJ.com season.</strong>
        </button>
        <button class="home-action-card" data-view-target="standings">
          <span>Standings</span>
          <strong>Conference and division tables for every boys soccer team indexed.</strong>
        </button>
      </div>

      <div class="home-dashboard">
        <div class="home-main-column">
          <div class="home-section">
            <div class="home-section-header">
              <div>
                <div class="home-section-title">Recent Scores</div>
                <div class="home-section-sub">${recentDate ? `${displayPitchDate(recentDate)} · ranked by game importance` : 'Latest completed games'}</div>
              </div>
              <button class="home-section-link" data-view-target="scores">Scores Page →</button>
            </div>
            ${gameList(recentGames)}
          </div>

          <div class="home-section">
            <div class="home-section-header">
              <div>
                <div class="home-section-title">Power Rankings</div>
                <div class="home-section-sub">Top 10 boys soccer teams by Pitch Score</div>
              </div>
              <button class="home-section-link" data-view-target="rankings">Full Rankings →</button>
            </div>
            ${miniRanking(topTeams)}
        </div>
        </div>

        <div class="home-side-column">
          <div class="home-section">
            <div class="home-section-header">
              <div>
                <div class="home-section-title">Upcoming Games</div>
                <div class="home-section-sub">Scheduled or unscored matchups</div>
              </div>
              <button class="home-section-link" data-view-target="scores">All Games →</button>
            </div>
            ${gameList(upcomingGames)}
          </div>

          <div class="home-section">
            <div class="home-section-header">
              <div class="home-section-title">Top Performers</div>
              <button class="home-section-link" data-view-target="leaders">All Leaders →</button>
            </div>
            <div class="home-performers-grid">${performerCards(topScorers, topKeepers)}</div>
          </div>
        </div>
      </div>
    </div>`;
}

function miniRanking(rows) {
  return `<table class="home-rankings-table">
    <thead><tr>
      <th style="width:28px">#</th>
      <th>Team</th>
      <th class="num">Score</th>
      <th class="num">AdjO</th>
      <th class="num">AdjD</th>
    </tr></thead>
    <tbody>${rows.slice(0, 10).map((team, i) => `
      <tr data-team-slug="${esc(team.slug)}">
        <td style="font-family:var(--font-mono);font-weight:700;color:${i < 3 ? 'var(--accent)' : 'var(--muted)'}">${i + 1}</td>
        <td><div class="team-cell">${logoImg(team, 20)}<div>${teamButton(team)}<div class="muted">${esc(team.conference)} · ${esc(team.record)}</div></div></div></td>
        <td class="num" style="font-weight:700;color:var(--accent)">${team.powerScore.toFixed(1)}</td>
        <td class="num" style="color:var(--muted2)">${team.adjO.toFixed(2)}</td>
        <td class="num" style="color:var(--muted2)">${team.adjD.toFixed(2)}</td>
      </tr>`).join('')}</tbody>
  </table>`;
}

function gameList(rows, ownerTeam = null, limit = null, includeDate = false) {
  if (!rows.length) return `<div class="empty">No games found in the current data.</div>`;
  const selected = limit ? rows.slice(0, limit) : rows;
  return `<table class="home-rankings-table">
    <thead><tr>
      <th style="width:32px">#</th>
      ${includeDate ? '<th>Date</th>' : ''}
      <th>Game</th>
      <th class="num">Score</th>
      <th class="num">PI</th>
    </tr></thead>
    <tbody>${selected.map((game, i) => {
    const team = TEAM_BY_SLUG[game.teamSlug] || ownerTeam;
    const opp = TEAM_BY_SLUG[game.opponentSlug];
    const hasScore = game.teamScore !== null && game.opponentScore !== null && game.teamScore !== undefined && game.opponentScore !== undefined;
    const winner = hasScore && game.result === 'L' ? opp : team;
    const loser = hasScore && game.result === 'L' ? team : opp;
    const winnerLabel = winner?.name || (game.result === 'L' ? game.opponentName : game.teamName);
    const loserLabel = loser?.name || (game.result === 'L' ? game.teamName : game.opponentName);
    const winnerScore = hasScore ? Math.max(Number(game.teamScore), Number(game.opponentScore)) : null;
    const loserScore = hasScore ? Math.min(Number(game.teamScore), Number(game.opponentScore)) : null;
    const power = winner?.powerScore ?? team?.powerScore;
    return `<tr>
      <td style="font-family:var(--font-mono);color:${i < 3 ? 'var(--accent)' : 'var(--muted)'};font-size:16px">${i + 1}</td>
      ${includeDate ? `<td style="color:var(--muted2);font-size:12px;white-space:nowrap">${esc(game.date || '')}</td>` : ''}
      <td>
        <div class="home-score-game">
          ${game.tournament ? '<span class="home-score-badge">TOURNEY</span>' : ''}
          <span class="home-score-team home-score-primary">${winner ? logoImg(winner, 18) : ''}<span>${winner ? linkedTeam(winner) : esc(winnerLabel || '')}</span></span>
          <span class="home-score-vs">${hasScore ? 'def.' : 'vs.'}</span>
          <span class="home-score-team home-score-primary">${loser ? logoImg(loser, 18) : ''}<span>${loser ? linkedTeam(loser) : esc(loserLabel || '')}</span></span>
        </div>
      </td>
      <td class="num" style="font-family:var(--font-mono);font-size:16px;color:var(--text)">${hasScore ? `${winnerScore}-${loserScore}` : '—'}</td>
      <td class="num" style="color:var(--muted2)">${Number.isFinite(power) ? power.toFixed(1) : '—'}</td>
    </tr>`;
  }).join('')}</tbody></table>`;
}

function performerCards(scorers, keepers) {
  const rankColors = ['gold', 'silver', 'bronze'];
  const card = (player, stat, label, idx) => {
    const team = TEAM_BY_SLUG[player.teamSlug];
    return `<div class="performer-card" data-player-key="${encodeURIComponent(playerKey(player))}">
      <div class="performer-rank ${rankColors[idx]}">${idx + 1}</div>
      <div style="flex-shrink:0">${team ? logoImg(team, 28) : ''}</div>
      <div class="performer-info">
        <div class="performer-name">${esc(player.name)}</div>
        <div class="performer-team">${esc(player.team)} · ${esc(player.grade || '')}</div>
      </div>
      <div class="performer-stat">
        <div class="performer-stat-val">${player[stat] ?? 0}</div>
        <div class="performer-stat-label">${label}</div>
      </div>
    </div>`;
  };
  return `<div class="performer-group-label">Offense — Points</div>` +
    scorers.map((player, i) => card(player, 'P', 'PTS', i)).join('') +
    `<div class="performer-group-label performer-group-label-spaced">Keepers — Saves</div>` +
    keepers.map((player, i) => card(player, 'Saves', 'SV', i)).join('');
}

function renderRankings() {
  const rows = sortRows(filteredTeams(), state.rankingSort.key, state.rankingSort.asc);
  $('view-rankings').innerHTML = `
    <div class="page-banner">
      <div class="page-banner-inner">
        <div>
          <div class="page-title">Power <span>Rankings</span></div>
          <div class="page-meta">
            Pitch Index Team Score
            <span class="page-meta-dot"></span>
            0-100 scale
            <span class="page-meta-dot"></span>
            Adjusted offensive and defensive efficiency
          </div>
        </div>
      </div>
    </div>
    <div class="leaderboard-wrap">
      <div class="controls-row">
        <div class="search-wrap">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="6.5" cy="6.5" r="5"/><path d="M10.5 10.5L14 14"/>
          </svg>
          <input class="search-input" data-filter-query type="text" placeholder="Search teams..." value="${esc(state.filters.query)}">
        </div>
        <select class="ctrl-select" data-filter-conference>${conferenceOptions(state.filters.conference)}</select>
      </div>
      <div class="lb-table-wrap">${rankingTable(rows, true)}</div>
    </div>`;
}

function toolbar(kind) {
  return `<div class="toolbar">
    <input data-filter-query type="search" placeholder="Search teams..." value="${esc(state.filters.query)}">
    <select data-filter-conference>${conferenceOptions(state.filters.conference)}</select>
  </div>`;
}

function rankingTable(rows, sortable) {
  const sortArrow = state.rankingSort.asc ? ' ▴' : ' ▾';
  const head = (label, key, cls = '') => {
    const active = sortable && state.rankingSort.key === key;
    return `<th class="${cls}${sortable ? ' sortable' : ''}${active ? ' rankings-sort-active' : ''}" ${sortable ? `data-rank-sort="${key}"` : ''}>${label}${active ? sortArrow : ''}</th>`;
  };
  return `<table>
    <thead><tr>
      <th style="width:28px">#</th>
      <th>Team</th>
      <th>Conf</th>
      <th class="num">Record</th>
      ${head('Pitch', 'powerScore', 'num')}
      ${head('AdjO', 'adjO', 'num')}
      ${head('AdjD', 'adjD', 'num')}
      ${head('SOS', 'sos', 'num')}
      ${head('Luck', 'luck', 'num')}
      ${head('PCT', 'winPct', 'num')}
      ${head('GF/G', 'gfPerGame', 'num')}
      ${head('GA/G', 'gaPerGame', 'num')}
      ${head('GD', 'gd', 'num')}
    </tr></thead>
    <tbody>${rows.map((team) => `<tr class="rankings-row" data-team-slug="${esc(team.slug)}">
      <td style="font-family:var(--font-sans);font-weight:700;color:${team.rank <= 3 ? 'var(--accent)' : 'var(--muted)'}">${team.rank}</td>
      <td><div class="team-cell">${logo(team)}<div>${teamButton(team)}<div class="muted">${esc(team.division)}</div></div></div></td>
      <td style="font-size:11px;color:var(--muted2);max-width:170px">${esc(team.conference)}</td>
      <td class="num"><span class="standings-record ${team.winPct > 0.5 ? 'over-500' : team.winPct < 0.5 ? 'under-500' : 'even-500'}">${esc(team.record)}</span></td>
      <td class="num" style="${state.rankingSort.key === 'powerScore' ? 'font-weight:700;color:var(--accent)' : ''}">${team.powerScore.toFixed(1)}</td>
      <td class="num" style="${state.rankingSort.key === 'adjO' ? 'font-weight:700;color:var(--accent)' : ''}">${team.adjO.toFixed(2)}</td>
      <td class="num" style="${state.rankingSort.key === 'adjD' ? 'font-weight:700;color:var(--accent)' : ''}">${team.adjD.toFixed(2)}</td>
      <td class="num" style="${state.rankingSort.key === 'sos' ? 'font-weight:700;color:var(--accent)' : ''}">${team.sos.toFixed(1)}</td>
      <td class="num" style="${state.rankingSort.key === 'luck' ? 'font-weight:700;color:var(--accent)' : ''}">${signed(team.luck)}</td>
      <td class="num" style="${state.rankingSort.key === 'winPct' ? 'font-weight:700;color:var(--accent)' : ''}">${pct(team.winPct)}</td>
      <td class="num" style="${state.rankingSort.key === 'gfPerGame' ? 'font-weight:700;color:var(--accent)' : ''}">${team.gfPerGame.toFixed(2)}</td>
      <td class="num" style="${state.rankingSort.key === 'gaPerGame' ? 'font-weight:700;color:var(--accent)' : ''}">${team.gaPerGame.toFixed(2)}</td>
      <td class="num" style="${state.rankingSort.key === 'gd' ? 'font-weight:700;color:var(--accent)' : ''}">${team.gd}</td>
    </tr>`).join('')}</tbody></table>`;
}

function renderLeaders() {
  const isScoring = state.leaderType === 'scoring';
  let rows = isScoring ? SCORERS : KEEPERS;
  const filters = state.leaderFilters;
  const q = filters.query.toLowerCase();
  rows = rows.filter((player) => {
    const matchesQ = !q || player.name.toLowerCase().includes(q) || player.team.toLowerCase().includes(q);
    const matchesConf = filters.conference === 'All' || player.conference === filters.conference;
    const matchesTeam = filters.team === 'All' || player.teamSlug === filters.team;
    const matchesGrade = filters.grade === 'All' || player.grade === filters.grade;
    const stat = isScoring ? 'P' : 'Saves';
    const matchesMin = Number(player[stat] || 0) >= Number(filters.min || 0);
    return matchesQ && matchesConf && matchesTeam && matchesGrade && matchesMin;
  });
  rows = sortRows(rows, state.leaderSort.key, state.leaderSort.asc).slice(0, 500);
  const statOptions = isScoring
    ? [['P','Points'], ['G','Goals'], ['A','Assists']]
    : [['Saves','Saves'], ['GP','Keeper GP']];
  $('view-leaders').innerHTML = `
    <div class="page-banner">
      <div class="page-banner-inner">
        <div>
          <div class="page-title">Player <span>Leaders</span></div>
          <div class="page-meta">New Jersey High School Boys Soccer <span class="page-meta-dot"></span> ${esc(PITCH_DATA.season)} Season <span class="page-meta-dot"></span> Scoring and Goalkeeping</div>
        </div>
      </div>
    </div>
    <div class="leaderboard-wrap">
      <div class="lb-mode-tabs">
        <button class="lb-tab ${isScoring ? 'lb-tab-active' : ''}" data-leader-type="scoring" type="button">Scoring</button>
        <button class="lb-tab ${!isScoring ? 'lb-tab-active' : ''}" data-leader-type="keepers" type="button">Goalkeepers</button>
      </div>
      <div class="controls-row">
        <div class="search-wrap">
          <svg class="search-icon" width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="6.5" cy="6.5" r="5"/><path d="M10.5 10.5L14 14"/>
          </svg>
          <input class="search-input" data-leader-query type="search" placeholder="Search player..." value="${esc(filters.query)}">
        </div>
        <select class="ctrl-select" data-leader-conference>${conferenceOptions(filters.conference)}</select>
        <select class="ctrl-select" data-leader-team>${filterTeamOptions(filters.team)}</select>
        <select class="ctrl-select" data-leader-grade>${gradeOptions(filters.grade)}</select>
        <select class="ctrl-select" data-leader-stat>
          ${statOptions.map(([key, label]) => `<option value="${key}" ${state.leaderSort.key === key ? 'selected' : ''}>${label}</option>`).join('')}
        </select>
        <div class="pa-filter-wrap">
          <span>Min ${isScoring ? 'P' : 'SV'}:</span>
          <input class="pa-filter-input" data-leader-min type="number" min="0" value="${Number(filters.min || 0)}">
        </div>
      </div>
      <div class="results-info">Showing <span>${rows.length}</span> ${isScoring ? 'scoring leader' : 'goalkeeper'}${rows.length === 1 ? '' : 's'}</div>
      ${leaderTable(rows, state.leaderType, true)}
    </div>`;
}

function leaderTable(rows, type, sortable) {
  const cols = type === 'keepers'
    ? [['Saves','Saves'], ['GP','GP']]
    : [['G','G'], ['A','A'], ['P','P']];
  const sortArrow = state.leaderSort.asc ? ' ▴' : ' ▾';
  const sort = (key) => {
    const active = sortable && state.leaderSort.key === key;
    return `class="num${sortable ? ' sortable' : ''}${active ? ' rankings-sort-active' : ''}" ${sortable ? `data-leader-sort="${key}"` : ''}`;
  };
  return `<div class="lb-table-wrap"><table>
    <thead><tr>
      <th style="width:36px">#</th>
      <th>Player</th>
      <th>Team</th>
      <th>Class</th>
      ${cols.map(([label,key]) => `<th ${sort(key)}>${label}${state.leaderSort.key === key ? sortArrow : ''}</th>`).join('')}
    </tr></thead>
    <tbody>${rows.map((player, i) => {
      const team = TEAM_BY_SLUG[player.teamSlug];
      return `<tr data-player-key="${encodeURIComponent(playerKey(player))}">
        <td class="rank-cell${i < 3 ? ' top3' : ''}">${i + 1}</td>
        ${leaderPlayerCell(player)}
        <td>${teamChip(team)}<div class="muted">${esc(player.conference)}</div></td>
        <td>${esc(player.grade || '')}</td>
        ${cols.map(([, key]) => {
          const active = state.leaderSort.key === key;
          return `<td class="num" style="${active ? 'font-weight:700;color:var(--accent)' : 'color:var(--muted2)'}">${player[key] ?? 0}</td>`;
        }).join('')}
      </tr>`;
    }).join('')}</tbody></table></div>`;
}

function renderStandings() {
  const rows = filteredTeams();
  const byConf = Object.groupBy ? Object.groupBy(rows, (team) => team.conference) : rows.reduce((acc, team) => ((acc[team.conference] ||= []).push(team), acc), {});
  $('view-standings').innerHTML = `
  <div class="page-banner">
    <div class="page-banner-inner">
      <div>
        <div class="page-title">Conference <span>Standings</span></div>
        <div class="page-meta">New Jersey High School Boys Soccer <span class="page-meta-dot"></span> ${esc(PITCH_DATA.season)} Season</div>
      </div>
    </div>
  </div>
  <div class="leaderboard-wrap">
    ${toolbar('standings')}
    ${Object.keys(byConf).sort().map((conf) => {
      const divs = byConf[conf].reduce((acc, team) => ((acc[team.division] ||= []).push(team), acc), {});
      return `<div class="card standings-group"><div class="standings-heading">${esc(conf)}</div>${Object.keys(divs).sort().map((division) => `
        <div class="division-label">${esc(division)}</div>${rankingTable(sortRows(divs[division], 'divisionWins'), false)}
      `).join('')}</div>`;
    }).join('')}
  </div>`;
}

function renderTeams() {
  const rows = sortRows(filteredTeams(), 'name', true);
  $('view-teams').innerHTML = `
  <div class="page-banner">
    <div class="page-banner-inner">
      <div>
        <div class="page-title">Team <span>Directory</span></div>
        <div class="page-meta">New Jersey High School Boys Soccer <span class="page-meta-dot"></span> ${TEAMS.length} teams</div>
      </div>
    </div>
  </div>
  <div class="leaderboard-wrap">
    ${toolbar('teams')}
    <div class="teams-grid">${rows.map((team) => `<div class="team-card" data-team-slug="${esc(team.slug)}">
      <div class="team-card-header">
        <div class="team-card-icon">${logoImg(team, 30)}</div>
        <div>
          <div class="team-card-name">${esc(team.name)}</div>
          <div class="team-card-mascot">${esc(team.conference)} · ${esc(team.division)}</div>
        </div>
      </div>
      <div class="team-card-stats">
        <div class="team-card-stat"><div class="team-card-stat-val">${esc(team.record)}</div><div class="team-card-stat-label">Record</div></div>
        <div class="team-card-stat"><div class="team-card-stat-val">#${team.rank}</div><div class="team-card-stat-label">Rank</div></div>
        <div class="team-card-stat"><div class="team-card-stat-val">${team.powerScore.toFixed(1)}</div><div class="team-card-stat-label">Pitch</div></div>
      </div>
    </div>`).join('')}</div>
  </div>`;
}

function renderScores() {
  const recent = completedPitchGames();
  const upcoming = upcomingPitchGames();
  $('view-scores').innerHTML = `
  <div class="page-banner">
    <div class="page-banner-inner">
      <div>
        <div class="page-title">Scores <span>& Results</span></div>
        <div class="page-meta">New Jersey High School Boys Soccer <span class="page-meta-dot"></span> ${esc(PITCH_DATA.season)} Season <span class="page-meta-dot"></span> Ranked by game importance</div>
      </div>
    </div>
  </div>
  <div class="scores-wrap">
    <div class="scores-grid">
      <div class="home-section">
        <div class="home-section-header">
          <div>
            <div class="home-section-title">Recent Scores</div>
            <div class="home-section-sub" id="scoresRecentMeta">${recent.length.toLocaleString()} completed games · newest first, then importance</div>
          </div>
        </div>
        <div id="scoresRecent">${gameList(recent, null, 120, true)}</div>
      </div>
      <div class="home-section">
        <div class="home-section-header">
          <div>
            <div class="home-section-title">Upcoming Games</div>
            <div class="home-section-sub" id="scoresUpcomingMeta">${upcoming.length.toLocaleString()} scheduled or unscored games</div>
          </div>
        </div>
        <div id="scoresUpcoming">${gameList(upcoming, null, 120, true)}</div>
      </div>
    </div>
  </div>`;
}

function predictPitchMatchup(teamA, teamB, venue = 'neutral') {
  if (!teamA || !teamB || teamA.slug === teamB.slug) return null;
  const leagueGF = TEAMS.length ? TEAMS.reduce((sum, team) => sum + team.gfPerGame, 0) / TEAMS.length : 2;
  const homeGoal = 0.18;
  const aHome = venue === 'a-home' ? homeGoal : 0;
  const bHome = venue === 'b-home' ? homeGoal : 0;
  const expA = Math.max(0.05, (teamA.adjO * teamB.adjD / Math.max(0.1, leagueGF)) + aHome);
  const expB = Math.max(0.05, (teamB.adjO * teamA.adjD / Math.max(0.1, leagueGF)) + bHome);
  const diff = expA - expB;
  const winProbA = 1 / (1 + Math.exp(-diff * 1.25));
  return { teamA, teamB, expA, expB, winProbA, winner: winProbA >= 0.5 ? teamA : teamB };
}

function renderPredictor() {
  const teamA = TEAM_BY_SLUG[state.predictor.teamA] || TEAMS[0];
  const teamB = TEAM_BY_SLUG[state.predictor.teamB] || TEAMS[1];
  const prediction = predictPitchMatchup(teamA, teamB, state.predictor.venue);
  $('view-predictor').innerHTML = `
  <div class="page-banner">
    <div class="page-banner-inner">
      <div>
        <div class="page-title">Matchup <span>Predictor</span></div>
        <div class="page-meta">Uses Pitch Index adjusted offense, defense, and team rating context</div>
      </div>
    </div>
  </div>
  <div class="predictor-wrap">
    <div class="predictor-panel">
      <div class="predictor-controls">
        <label class="predictor-field">
          <span>Team A</span>
          <select class="ctrl-select" data-predict-team="A">${teamOptions(teamA?.slug)}</select>
        </label>
        <label class="predictor-field">
          <span>Venue</span>
          <select class="ctrl-select" data-predict-venue>
            <option value="neutral" ${state.predictor.venue === 'neutral' ? 'selected' : ''}>Neutral</option>
            <option value="a-home" ${state.predictor.venue === 'a-home' ? 'selected' : ''}>Team A Home</option>
            <option value="b-home" ${state.predictor.venue === 'b-home' ? 'selected' : ''}>Team B Home</option>
          </select>
        </label>
        <label class="predictor-field">
          <span>Team B</span>
          <select class="ctrl-select" data-predict-team="B">${teamOptions(teamB?.slug)}</select>
        </label>
      </div>
      ${prediction ? `
        <div class="prediction-card">
          <div class="prediction-head">
            <div class="prediction-team">
              ${logo(teamA, 'prediction-logo')}
              <div>
                <div class="prediction-team-name">${esc(teamA.name)}</div>
                <div class="prediction-team-meta">#${teamA.rank} · Pitch ${teamA.powerScore.toFixed(1)} · ${esc(teamA.record)}</div>
              </div>
            </div>
            <div class="prediction-vs">
              <span>vs</span>
            </div>
            <div class="prediction-team prediction-team-right">
              ${logo(teamB, 'prediction-logo')}
              <div>
                <div class="prediction-team-name">${esc(teamB.name)}</div>
                <div class="prediction-team-meta">#${teamB.rank} · Pitch ${teamB.powerScore.toFixed(1)} · ${esc(teamB.record)}</div>
              </div>
            </div>
          </div>
          <div class="prediction-main">
            <div class="prediction-pick-label">Projected Winner</div>
            <div class="prediction-pick">${esc(prediction.winner.name)}</div>
            <div class="prediction-score">${prediction.expA.toFixed(2)} - ${prediction.expB.toFixed(2)} projected goals</div>
            <div class="prediction-confidence">Win probability: ${(Math.max(prediction.winProbA, 1 - prediction.winProbA) * 100).toFixed(1)}%</div>
          </div>
          <div class="prediction-prob">
            <div class="prediction-prob-row"><span>${esc(teamA.name)}</span><strong>${(prediction.winProbA * 100).toFixed(1)}%</strong></div>
            <div class="prediction-bar"><div class="prediction-bar-a" style="width:${(prediction.winProbA * 100).toFixed(1)}%"></div></div>
            <div class="prediction-prob-row"><span>${esc(teamB.name)}</span><strong>${((1 - prediction.winProbA) * 100).toFixed(1)}%</strong></div>
            <div class="prediction-bar"><div class="prediction-bar-b" style="width:${((1 - prediction.winProbA) * 100).toFixed(1)}%"></div></div>
          </div>
          <div class="prediction-metrics">
            <div class="prediction-metric"><div class="prediction-metric-label">Team A AdjO</div><div class="prediction-metric-values">${teamA.adjO.toFixed(2)}</div></div>
            <div class="prediction-metric"><div class="prediction-metric-label">Team B AdjO</div><div class="prediction-metric-values">${teamB.adjO.toFixed(2)}</div></div>
            <div class="prediction-metric"><div class="prediction-metric-label">Team A AdjD</div><div class="prediction-metric-values">${teamA.adjD.toFixed(2)}</div></div>
            <div class="prediction-metric"><div class="prediction-metric-label">Team B AdjD</div><div class="prediction-metric-values">${teamB.adjD.toFixed(2)}</div></div>
          </div>
        </div>
      ` : `<div class="predictor-empty">Choose two different teams to generate a prediction.</div>`}
    </div>
  </div>`;
}

function renderGlossary() {
  $('view-glossary').innerHTML = `
  <div class="page-banner">
    <div class="page-banner-inner">
      <div>
        <div class="page-title">Pitch <span>Glossary</span></div>
        <div class="page-meta">Definitions and formulas for Pitch Index metrics</div>
      </div>
    </div>
  </div>
  <div class="glossary-wrap">
    <div class="glossary-section">
      <div class="glossary-section-title">Team Ratings</div>
      <div class="glossary-grid">
        <div class="glossary-card gc-highlight"><div class="gc-stat">PITCH</div><div class="gc-name">Pitch Score</div><div class="gc-def">0-100 team rating based on adjusted goal efficiency, record, goal differential, and schedule context.</div></div>
        <div class="glossary-card"><div class="gc-stat">AdjO</div><div class="gc-name">Adjusted Offense</div><div class="gc-def">Goals scored per game adjusted for opponent defensive strength and normalized to the state environment.</div></div>
        <div class="glossary-card"><div class="gc-stat">AdjD</div><div class="gc-name">Adjusted Defense</div><div class="gc-def">Goals allowed per game adjusted for opponent attacking strength. Lower is better.</div></div>
        <div class="glossary-card"><div class="gc-stat">SOS</div><div class="gc-name">Strength of Schedule</div><div class="gc-def">Opponent quality on a 0-100 scale using opponents' adjusted team strength.</div></div>
        <div class="glossary-card"><div class="gc-stat">Luck</div><div class="gc-name">Luck</div><div class="gc-def">Difference between actual winning percentage and expected winning percentage from adjusted goal profile.</div></div>
      </div>
    </div>
    <div class="glossary-section">
      <div class="glossary-section-title">Player Leaderboards</div>
      <div class="glossary-grid">
        <div class="glossary-card"><div class="gc-stat">G</div><div class="gc-name">Goals</div><div class="gc-def">Total goals from NJ.com scoring leaders.</div></div>
        <div class="glossary-card"><div class="gc-stat">A</div><div class="gc-name">Assists</div><div class="gc-def">Total assists from NJ.com scoring leaders.</div></div>
        <div class="glossary-card"><div class="gc-stat">P</div><div class="gc-name">Points</div><div class="gc-def">Goals plus assists.</div></div>
        <div class="glossary-card"><div class="gc-stat">Saves</div><div class="gc-name">Goalkeeper Saves</div><div class="gc-def">Total saves from NJ.com goalkeeper leaders.</div></div>
      </div>
    </div>
  </div>`;
}

function renderTeam() {
  const team = TEAM_BY_SLUG[state.teamSlug];
  if (!team) return;
  const scorers = sortRows(team.scorers || [], 'P').slice(0, 15);
  const keepers = sortRows(team.keepers || [], 'Saves').slice(0, 8);
  $('view-team').innerHTML = `<div class="leaderboard-wrap">
    <button class="btn" data-view-target="teams" style="margin-bottom:14px">Back to Teams</button>
    <div class="team-hero">
      <div class="team-shield-lg">
        ${logo(team, 'team-logo-large')}
      </div>
      <div class="team-info">
        <div class="team-name-lg">${esc(team.name)}</div>
        <div class="team-mascot-lg">${esc(team.conference)}</div>
        <div class="team-details">
          <span class="team-meta-pill team-meta-pill-accent"><span>Record</span>${esc(team.record)}</span>
          <span class="team-meta-pill"><span>Division</span>${esc(team.division)}</span>
          <span class="team-meta-pill team-meta-pill-accent"><span>Div Record</span>${esc(team.divisionRecord)}</span>
          <span class="team-meta-pill"><span>Rank</span>#${team.rank}</span>
        </div>
      </div>
    </div>
    <div class="team-stat-cards">
      <div class="team-stat-card team-score-card"><div class="team-stat-card-label">Pitch Score</div><div class="team-stat-card-val">${team.powerScore.toFixed(1)}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">State Rank</div><div class="team-stat-card-val">#${team.rank}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">GF</div><div class="team-stat-card-val">${team.gf}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">GA</div><div class="team-stat-card-val">${team.ga}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">AdjO</div><div class="team-stat-card-val">${team.adjO.toFixed(2)}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">AdjD</div><div class="team-stat-card-val">${team.adjD.toFixed(2)}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">SOS</div><div class="team-stat-card-val">${team.sos.toFixed(1)}</div></div>
      <div class="team-stat-card"><div class="team-stat-card-label">Luck</div><div class="team-stat-card-val">${signed(team.luck)}</div></div>
    </div>
    <div class="subgrid">
      <div class="home-section"><div class="home-section-header"><div><div class="home-section-title">Schedule & Results</div><div class="home-section-sub">${team.schedule?.length || 0} games</div></div></div>${gameList(team.schedule || [], team)}</div>
      <div>
        <div class="home-section"><div class="home-section-header"><div><div class="home-section-title">Scoring Leaders</div></div></div>${leaderTable(scorers, 'scoring', false)}</div>
        <div style="height:20px"></div>
        <div class="home-section"><div class="home-section-header"><div><div class="home-section-title">Goalkeepers</div></div></div>${leaderTable(keepers, 'keepers', false)}</div>
      </div>
    </div>
  </div>`;
}

function renderPlayer() {
  const all = [...SCORERS, ...KEEPERS];
  const player = all.find((item) => playerKey(item) === state.playerKey);
  if (!player) return;
  const team = TEAM_BY_SLUG[player.teamSlug];
  const scoring = SCORERS.find((item) => playerKey(item) === state.playerKey);
  const keeping = KEEPERS.find((item) => playerKey(item) === state.playerKey);
  $('view-player').innerHTML = `<div class="leaderboard-wrap">
    <button class="btn" data-view-target="leaders" style="margin-bottom:14px">Back to Leaders</button>
    <div class="player-hero">
      <div class="player-shield">
        ${team ? logo(team, 'player-team-logo') : ''}
      </div>
      <div class="player-info">
        <div class="player-full-name">${esc(player.name)}</div>
        <div class="player-details">
          ${team ? `<span class="p-tag">${teamButton(team)}</span>` : ''}
          ${player.grade ? `<span class="p-tag">${esc(player.grade)}</span>` : ''}
          <span class="p-tag">${esc(player.conference)}</span>
          <span class="p-tag">${esc(player.division)}</span>
        </div>
      </div>
    </div>
    <div class="counting-grid">
      <div class="counting-card"><div class="counting-label">Goals</div><div class="counting-value">${scoring?.G ?? 0}</div></div>
      <div class="counting-card"><div class="counting-label">Assists</div><div class="counting-value">${scoring?.A ?? 0}</div></div>
      <div class="counting-card"><div class="counting-label">Points</div><div class="counting-value">${scoring?.P ?? 0}</div></div>
      <div class="counting-card"><div class="counting-label">Saves</div><div class="counting-value">${keeping?.Saves ?? 0}</div></div>
      <div class="counting-card"><div class="counting-label">Keeper GP</div><div class="counting-value">${keeping?.GP ?? 0}</div></div>
      <div class="counting-card"><div class="counting-label">Team Rank</div><div class="counting-value">${team?.rank ? `#${team.rank}` : '-'}</div></div>
    </div>
  </div>`;
}

function renderGlobalSearch() {
  const box = $('searchResults');
  const q = $('globalSearch').value.trim().toLowerCase();
  if (!q) {
    box.classList.remove('open');
    box.innerHTML = '';
    return;
  }
  const teamHits = TEAMS.filter((team) => team.name.toLowerCase().includes(q)).slice(0, 5);
  const playerHits = [...SCORERS, ...KEEPERS]
    .filter((player) => player.name.toLowerCase().includes(q) || player.team.toLowerCase().includes(q))
    .slice(0, 8);
  box.innerHTML = [
    ...teamHits.map((team) => `<button class="search-hit" data-team-slug="${esc(team.slug)}" data-clear-search="1">${esc(team.name)}<small>Team · ${esc(team.conference)} · ${esc(team.record)}</small></button>`),
    ...playerHits.map((player) => `<button class="search-hit" data-player-key="${encodeURIComponent(playerKey(player))}" data-clear-search="1">${esc(player.name)}<small>Player · ${esc(player.team)} · ${esc(player.grade || '')}</small></button>`),
  ].join('') || `<div class="search-hit muted">No matches</div>`;
  box.classList.add('open');
}

function render() {
  if (state.view === 'home') renderHome();
  if (state.view === 'rankings') renderRankings();
  if (state.view === 'leaders') renderLeaders();
  if (state.view === 'scores') renderScores();
  if (state.view === 'predictor') renderPredictor();
  if (state.view === 'standings') renderStandings();
  if (state.view === 'teams') renderTeams();
  if (state.view === 'glossary') renderGlossary();
  if (state.view === 'team') renderTeam();
  if (state.view === 'player') renderPlayer();
}

document.addEventListener('click', (event) => {
  const trigger = event.target.closest('.nav-dropdown-trigger');
  const menu = event.target.closest('.nav-dropdown-menu');
  if (trigger) {
    const dropdown = trigger.closest('.nav-dropdown')?.querySelector('.nav-dropdown-menu');
    const isOpen = dropdown?.classList.contains('open');
    closeDropdowns();
    if (dropdown && !isOpen) dropdown.classList.add('open');
    event.stopPropagation();
    return;
  }
  if (!menu) closeDropdowns();

  const navTarget = event.target.closest('.pitch-nav [data-view]');
  if (navTarget) {
    if (navTarget.dataset.leaderType) {
      state.leaderType = navTarget.dataset.leaderType;
      state.leaderSort = state.leaderType === 'keepers' ? { key: 'Saves', asc: false } : { key: 'P', asc: false };
    }
    closeDropdowns();
    setView(navTarget.dataset.view);
    return;
  }

  const viewTarget = event.target.closest('[data-view-target]');
  if (viewTarget) {
    closeDropdowns();
    setView(viewTarget.dataset.viewTarget);
    return;
  }

  const teamTarget = event.target.closest('[data-team-slug]');
  if (teamTarget) {
    if (teamTarget.dataset.closeDropdowns) closeDropdowns();
    setView('team', teamTarget.dataset.teamSlug);
    if (teamTarget.dataset.clearSearch) {
      $('globalSearch').value = '';
      renderGlobalSearch();
    }
    return;
  }

  const playerTarget = event.target.closest('[data-player-key]');
  if (playerTarget) {
    setView('player', playerTarget.dataset.playerKey);
    if (playerTarget.dataset.clearSearch) {
      $('globalSearch').value = '';
      renderGlobalSearch();
    }
    return;
  }

  const rankSort = event.target.closest('[data-rank-sort]');
  if (rankSort) {
    const key = rankSort.dataset.rankSort;
    state.rankingSort = { key, asc: state.rankingSort.key === key ? !state.rankingSort.asc : RANK_LOWER_BETTER.has(key) };
    render();
    return;
  }

  const leaderSort = event.target.closest('[data-leader-sort]');
  if (leaderSort) {
    const key = leaderSort.dataset.leaderSort;
    state.leaderSort = { key, asc: state.leaderSort.key === key ? !state.leaderSort.asc : false };
    render();
    return;
  }

  const leaderType = event.target.closest('[data-leader-type]');
  if (leaderType) {
    state.leaderType = leaderType.dataset.leaderType;
    state.leaderSort = state.leaderType === 'keepers' ? { key: 'Saves', asc: false } : { key: 'P', asc: false };
    if (state.view !== 'leaders') setView('leaders');
    else render();
  }
});

document.addEventListener('input', (event) => {
  if (event.target.matches('[data-filter-query]')) {
    state.filters.query = event.target.value;
    render();
  }
  if (event.target.matches('[data-leader-query]')) {
    state.leaderFilters.query = event.target.value;
    renderLeaders();
  }
  if (event.target.matches('[data-leader-min]')) {
    state.leaderFilters.min = Number(event.target.value || 0);
    renderLeaders();
  }
});

document.addEventListener('change', (event) => {
  if (event.target.matches('[data-filter-conference]')) {
    state.filters.conference = event.target.value;
    render();
  }
  if (event.target.matches('[data-leader-conference]')) {
    state.leaderFilters.conference = event.target.value;
    renderLeaders();
  }
  if (event.target.matches('[data-leader-team]')) {
    state.leaderFilters.team = event.target.value;
    renderLeaders();
  }
  if (event.target.matches('[data-leader-grade]')) {
    state.leaderFilters.grade = event.target.value;
    renderLeaders();
  }
  if (event.target.matches('[data-leader-stat]')) {
    state.leaderSort = { key: event.target.value, asc: false };
    renderLeaders();
  }
  if (event.target.matches('[data-predict-team]')) {
    if (event.target.dataset.predictTeam === 'A') state.predictor.teamA = event.target.value;
    if (event.target.dataset.predictTeam === 'B') state.predictor.teamB = event.target.value;
    renderPredictor();
  }
  if (event.target.matches('[data-predict-venue]')) {
    state.predictor.venue = event.target.value;
    renderPredictor();
  }
});

$('globalSearch').addEventListener('input', renderGlobalSearch);
document.addEventListener('click', (event) => {
  if (!event.target.closest('.pitch-global-search')) $('searchResults').classList.remove('open');
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeDropdowns();
    closeReportProblem();
  }
});

initTheme();
buildTeamsNav();
renderHome();
