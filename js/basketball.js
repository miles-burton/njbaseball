const $ = (id) => document.getElementById(id);
const BASKETBALL_TEAMS = BASKETBALL_DATA.teams || [];
const BASKETBALL_PLAYERS = BASKETBALL_DATA.players || [];
const BASKETBALL_GAMES = BASKETBALL_DATA.games || [];
const TEAM_BY_SLUG = Object.fromEntries(BASKETBALL_TEAMS.map((team) => [team.slug, team]));
const CONFERENCES = [...new Set(BASKETBALL_TEAMS.map((team) => team.conference))].sort();
const REPORT_ISSUE_URL = 'https://github.com/miles-burton/njbaseball/issues/new';
const state = {
  view: 'home',
  previousView: 'home',
  teamSlug: '',
  playerKey: '',
  gameKey: '',
  rankingSort: { key: 'powerScore', asc: false },
  leaderSort: { key: 'PPG', asc: false },
  filters: { query: '', conference: 'All' },
  leaderFilters: { query: '', conference: 'All', team: 'All', grade: 'All', min: 0 },
  predictor: { teamA: BASKETBALL_TEAMS[0]?.slug || '', teamB: BASKETBALL_TEAMS[1]?.slug || '', venue: 'neutral' },
};

const LEADER_COLS = [
  ['PPG', 'PPG'], ['RPG', 'RPG'], ['APG', 'APG'], ['SPG', 'SPG'], ['BPG', 'BPG'],
  ['StocksPG', 'Stocks/G'], ['FTPct', 'FT%'], ['TeamScoringShare', 'Scoring Share'],
  ['TeamReboundingShare', 'Reb Share'], ['TeamAssistShare', 'Ast Share'],
  ['PointsResponsible', 'Pts Resp'], ['OffensiveInvolvement', 'Off Inv'], ['playerScore', 'PS'],
];

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}

function fmt(value, digits = 1) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : '—';
}

function logoSrc(team) {
  const shared = typeof TEAM_LOGOS !== 'undefined' ? TEAM_LOGOS[team?.name] : '';
  return shared || team?.logo || '';
}

function logo(team, size = 22) {
  const src = logoSrc(team);
  return src ? `<img loading="lazy" decoding="async" src="${esc(src)}" width="${size}" height="${size}" style="object-fit:contain;border-radius:3px;flex-shrink:0" alt="">` : '';
}

function setView(view, detail = '') {
  state.previousView = state.view;
  state.view = view;
  document.querySelectorAll('.view').forEach((el) => el.classList.remove('active'));
  $(`view-${view}`)?.classList.add('active');
  document.querySelectorAll('.pitch-nav [data-view]').forEach((btn) => {
    const active = btn.dataset.view === view || (view === 'team' && btn.id === 'tab-teams-dd');
    btn.classList.toggle('active', active);
  });
  if (view === 'team') state.teamSlug = detail;
  if (view === 'player') state.playerKey = decodeURIComponent(detail);
  if (view === 'game') state.gameKey = decodeURIComponent(detail);
  $('backBtn')?.classList.toggle('show', ['team', 'player', 'game'].includes(view));
  render();
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function basketballGoBack() {
  const previous = state.previousView && state.previousView !== state.view ? state.previousView : 'home';
  setView(['team', 'player', 'game'].includes(previous) ? 'home' : previous);
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

function openReportProblem() {
  closeDropdowns();
  $('reportModal')?.classList.add('open');
  $('reportModal')?.setAttribute('aria-hidden', 'false');
  setTimeout(() => $('reportDetails')?.focus(), 0);
}

function closeReportProblem() {
  $('reportModal')?.classList.remove('open');
  $('reportModal')?.setAttribute('aria-hidden', 'true');
}

async function submitProblemReport(event) {
  event.preventDefault();
  const type = $('reportType')?.value || 'Site problem';
  const details = $('reportDetails')?.value.trim() || '';
  const contact = $('reportContact')?.value.trim() || '';
  const report = { site: 'Court Index', sport: BASKETBALL_DATA.sport || 'boysbasketball', season: BASKETBALL_DATA.season || '', pageUrl: location.href, type, details, contact };
  try {
    const stored = await window.NJSupabaseReports?.submit(report);
    if (stored?.ok) {
      alert('Report sent. Thanks for flagging it.');
      closeReportProblem();
      return;
    }
  } catch (err) {
    console.warn('Supabase report failed; falling back to GitHub issue.', err);
  }
  const body = encodeURIComponent(`Page: ${location.href}\nSeason: ${BASKETBALL_DATA.season || ''}\n\n${details}\n\nContact: ${contact || 'Not provided'}`);
  window.open(`${REPORT_ISSUE_URL}?title=${encodeURIComponent(`[Court Index] ${type}`)}&body=${body}`, '_blank', 'noopener');
  closeReportProblem();
}

function sortRows(rows, key, asc = false) {
  return [...rows].sort((a, b) => {
    const av = a[key] ?? '';
    const bv = b[key] ?? '';
    const value = typeof av === 'number' && typeof bv === 'number' ? av - bv : String(av).localeCompare(String(bv));
    return asc ? value : -value;
  });
}

function teamButton(team) {
  if (!team) return '<span class="muted">Unknown</span>';
  return `<button class="linkish" data-team-slug="${esc(team.slug)}">${logo(team, 18)}${esc(team.name)}</button>`;
}

function playerKey(player) {
  return `${player.name}__${player.teamSlug}`;
}

function playerButton(player) {
  return `<button class="linkish" data-player-key="${encodeURIComponent(playerKey(player))}">${esc(player.name)}</button>`;
}

function gameKey(game) {
  return `${game.teamSlug}__${game.opponentSlug || game.opponent}__${game.date}__${game.scoreText || 'upcoming'}`;
}

function completedGames() {
  return BASKETBALL_GAMES.filter((game) => game.result && game.teamScore !== null && game.teamScore !== undefined)
    .sort((a, b) => (b.gameUrl || '').localeCompare(a.gameUrl || ''));
}

function upcomingGames() {
  return BASKETBALL_GAMES.filter((game) => !game.result).slice(0, 100);
}

function renderHome() {
  const topTeams = BASKETBALL_TEAMS.slice(0, 10);
  const leaders = sortRows(BASKETBALL_PLAYERS.filter((p) => p.GP >= 5), 'PPG').slice(0, 5);
  const recentGames = completedGames().slice(0, 5);
  $('view-home').innerHTML = `
    <div class="home-hero" style="position:relative;overflow:hidden">
      <div class="home-hero-inner">
        <div class="home-hero-text">
          <div class="home-hero-eyebrow">New Jersey Boys Basketball · ${esc(BASKETBALL_DATA.season)} Season</div>
          <h1 class="home-hero-title">COURT<br>INDEX</h1>
          <div class="home-hero-tagline">Measure the Court.</div>
          <p class="home-hero-sub">Statewide boys basketball analytics built from NJ.com standings, schedules, player stats, team rankings, and advanced offensive involvement metrics.</p>
          <div class="home-hero-actions">
            <button class="home-btn-primary" data-view-target="rankings">Power Rankings</button>
            <button class="home-btn-secondary" data-view-target="leaders">Player Leaders</button>
          </div>
        </div>
      </div>
    </div>
    <div class="home-wrap">
      <div class="home-content-grid">
        <section class="home-panel"><div class="home-panel-head"><h2>Top Teams</h2><button class="home-section-link" data-view-target="rankings">Full Rankings →</button></div>${miniTeamTable(topTeams)}</section>
        <section class="home-panel"><div class="home-panel-head"><h2>Scoring Leaders</h2><button class="home-section-link" data-view-target="leaders">All Leaders →</button></div>${miniLeaderTable(leaders)}</section>
        <section class="home-panel"><div class="home-panel-head"><h2>Recent Scores</h2><button class="home-section-link" data-view-target="scores">All Scores →</button></div>${gamesTable(recentGames, true)}</section>
      </div>
    </div>`;
}

function miniTeamTable(teams) {
  return `<div class="table-wrap"><table><tbody>${teams.map((team, index) => `<tr data-team-slug="${esc(team.slug)}"><td class="rank">${index + 1}</td><td>${teamButton(team)}</td><td class="num">${fmt(team.powerScore)}</td></tr>`).join('')}</tbody></table></div>`;
}

function miniLeaderTable(players) {
  return `<div class="table-wrap"><table><tbody>${players.map((player, index) => `<tr data-player-key="${encodeURIComponent(playerKey(player))}"><td class="rank">${index + 1}</td><td>${playerButton(player)}<div class="muted">${esc(player.grade || '')}</div></td><td>${teamButton(TEAM_BY_SLUG[player.teamSlug])}</td><td class="num">${fmt(player.PPG)}</td></tr>`).join('')}</tbody></table></div>`;
}

function renderRankings() {
  const teams = sortRows(BASKETBALL_TEAMS, state.rankingSort.key, state.rankingSort.asc);
  $('view-rankings').innerHTML = `<main class="shell">${pageHeader('Court Index Rankings', 'Opponent-adjusted team ratings with record, schedule strength, scoring margin, adjusted offense, and adjusted defense.')}
    <section class="card"><div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="num">Score</th><th class="num">Adj O</th><th class="num">Adj D</th><th class="num">SOS</th><th class="num">Record</th></tr></thead>
    <tbody>${teams.map((team) => `<tr data-team-slug="${esc(team.slug)}"><td class="rank">${team.rank}</td><td>${teamButton(team)}</td><td class="num">${fmt(team.powerScore)}</td><td class="num">${fmt(team.adjO)}</td><td class="num">${fmt(team.adjD)}</td><td class="num">${fmt(team.sos)}</td><td class="num">${esc(team.record)}</td></tr>`).join('')}</tbody></table></div></section></main>`;
}

function renderLeaders() {
  const f = state.leaderFilters;
  const query = f.query.toLowerCase();
  let players = BASKETBALL_PLAYERS.filter((player) => {
    return (!query || player.name.toLowerCase().includes(query))
      && (f.conference === 'All' || player.conference === f.conference)
      && (f.team === 'All' || player.teamSlug === f.team)
      && (f.grade === 'All' || player.grade === f.grade)
      && Number(player.GP || 0) >= Number(f.min || 0);
  });
  players = sortRows(players, state.leaderSort.key, state.leaderSort.asc);
  $('view-leaders').innerHTML = `<main class="shell pitch-leaders-wrap">${pageHeader('Basketball Leaders', `Showing ${players.length} players · Updated ${esc(BASKETBALL_DATA.updated || 'pending')}`)}
    <div class="controls-row">
      <div class="search-wrap"><input class="search-input" data-leader-query placeholder="Search player..." value="${esc(f.query)}"></div>
      <select class="ctrl-select" data-leader-conference><option>All</option>${CONFERENCES.map((c) => `<option ${c === f.conference ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select>
      <select class="ctrl-select" data-leader-team><option value="All">All Teams</option>${BASKETBALL_TEAMS.map((t) => `<option value="${esc(t.slug)}" ${t.slug === f.team ? 'selected' : ''}>${esc(t.name)}</option>`).join('')}</select>
      <select class="ctrl-select" data-leader-grade><option>All</option>${['Freshman','Sophomore','Junior','Senior'].map((g) => `<option ${g === f.grade ? 'selected' : ''}>${g}</option>`).join('')}</select>
      <select class="ctrl-select" data-leader-stat>${LEADER_COLS.map(([key,label]) => `<option value="${key}" ${key === state.leaderSort.key ? 'selected' : ''}>${label}</option>`).join('')}</select>
      <input class="pa-filter-input" data-leader-min type="number" min="0" value="${esc(f.min)}" placeholder="Min GP">
    </div>
    <section class="card"><div class="table-wrap"><table><thead><tr><th>#</th><th>Player</th><th>Team</th><th class="num">GP</th>${LEADER_COLS.map(([key,label]) => `<th class="num sortable" data-sort="${key}">${label}</th>`).join('')}</tr></thead>
    <tbody>${players.slice(0, 250).map((player, index) => `<tr data-player-key="${encodeURIComponent(playerKey(player))}"><td class="rank">${index + 1}</td><td>${playerButton(player)}<div class="muted">${esc(player.grade || '')}</div></td><td>${teamButton(TEAM_BY_SLUG[player.teamSlug])}</td><td class="num">${player.GP || 0}</td>${LEADER_COLS.map(([key]) => `<td class="num">${fmt(player[key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div></section></main>`;
}

function renderScores() {
  const games = completedGames().slice(0, 250);
  $('view-scores').innerHTML = `<main class="shell">${pageHeader('Scores', 'Completed games from NJ.com, sorted by latest available game rows.')}<section class="card">${gamesTable(games, true)}</section></main>`;
}

function renderPredictor() {
  const a = TEAM_BY_SLUG[state.predictor.teamA];
  const b = TEAM_BY_SLUG[state.predictor.teamB];
  const pred = a && b && a.slug !== b.slug ? predict(a, b) : null;
  $('view-predictor').innerHTML = `<main class="shell">${pageHeader('Matchup Predictor', 'Projected score and win probability from Court Index team ratings.')}
    <section class="card pad"><div class="grid-2"><select class="ctrl-select" data-predictor-a>${teamOptions(state.predictor.teamA)}</select><select class="ctrl-select" data-predictor-b>${teamOptions(state.predictor.teamB)}</select></div>
    ${pred ? `<div class="prediction-card" style="margin-top:18px"><div class="prediction-pick-label">Projected Winner</div><div class="prediction-pick">${esc(pred.winner.name)}</div><div class="prediction-score">${pred.scoreA.toFixed(1)} - ${pred.scoreB.toFixed(1)} projected points</div><div class="prediction-confidence">${esc(a.name)} ${(pred.winA * 100).toFixed(1)}% · ${esc(b.name)} ${((1 - pred.winA) * 100).toFixed(1)}%</div></div>` : '<div class="predictor-empty">Choose two different teams.</div>'}</section></main>`;
}

function predict(a, b) {
  const spread = (a.powerScore - b.powerScore) * 0.28;
  const total = Math.max(80, Math.min(170, (a.adjO + b.adjO + a.adjD + b.adjD) / 2));
  const scoreA = total / 2 + spread;
  const scoreB = total / 2 - spread;
  const winA = 1 / (1 + Math.exp(-spread / 6.5));
  return { scoreA, scoreB, winA, winner: winA >= 0.5 ? a : b };
}

function renderStandings() {
  const groups = {};
  BASKETBALL_TEAMS.forEach((team) => {
    const key = `${team.conference} · ${team.division || 'Overall'}`;
    (groups[key] ||= []).push(team);
  });
  $('view-standings').innerHTML = `<main class="shell">${pageHeader('Standings', 'Conference and division records with scoring margin and Court Index score.')}
    ${Object.entries(groups).sort().map(([name, rows]) => `<section class="card standings-group"><div class="standings-heading">${esc(name)}</div><div class="table-wrap"><table><thead><tr><th>Team</th><th class="num">Record</th><th class="num">Div</th><th class="num">PF/G</th><th class="num">PA/G</th><th class="num">Score</th></tr></thead><tbody>${sortRows(rows, 'winPct').map((team) => `<tr data-team-slug="${esc(team.slug)}"><td>${teamButton(team)}</td><td class="num">${esc(team.record)}</td><td class="num">${esc(team.divisionRecord)}</td><td class="num">${fmt(team.pfPerGame)}</td><td class="num">${fmt(team.paPerGame)}</td><td class="num">${fmt(team.powerScore)}</td></tr>`).join('')}</tbody></table></div></section>`).join('')}</main>`;
}

function renderTeams() {
  const q = state.filters.query.toLowerCase();
  const rows = BASKETBALL_TEAMS.filter((team) => (!q || team.name.toLowerCase().includes(q)) && (state.filters.conference === 'All' || team.conference === state.filters.conference));
  $('view-teams').innerHTML = `<main class="shell">${pageHeader('Teams', `${rows.length} teams`)}<div class="controls-row"><input class="search-input" data-team-query placeholder="Search team..." value="${esc(state.filters.query)}"><select class="ctrl-select" data-team-conference><option>All</option>${CONFERENCES.map((c) => `<option ${c === state.filters.conference ? 'selected' : ''}>${esc(c)}</option>`).join('')}</select></div>${miniTeamTable(rows)}</main>`;
}

function renderTeam() {
  const team = TEAM_BY_SLUG[state.teamSlug] || BASKETBALL_TEAMS[0];
  if (!team) return;
  const roster = sortRows(BASKETBALL_PLAYERS.filter((p) => p.teamSlug === team.slug), 'PPG');
  const games = BASKETBALL_GAMES.filter((g) => g.teamSlug === team.slug);
  $('view-team').innerHTML = `<main class="shell pitch-team-page">${pageHeader(`${logo(team, 44)} ${esc(team.name)}`, `${esc(team.record)} · ${esc(team.conference)} · #${team.rank || '—'}`)}
    <div class="grid-3"><div class="stat-card"><span>CI Score</span><strong>${fmt(team.powerScore)}</strong></div><div class="stat-card"><span>Adj O</span><strong>${fmt(team.adjO)}</strong></div><div class="stat-card"><span>Adj D</span><strong>${fmt(team.adjD)}</strong></div></div>
    <section class="card" style="margin-top:18px"><div class="card-title">Roster <span>Basketball leaders</span></div>${leadersRoster(roster)}</section>
    <section class="card" style="margin-top:18px"><div class="card-title">Schedule <span>${games.length} games</span></div>${gamesTable(games, false)}</section></main>`;
}

function leadersRoster(players) {
  return `<div class="table-wrap"><table><thead><tr><th>Player</th><th class="num">GP</th><th class="num">PPG</th><th class="num">RPG</th><th class="num">APG</th><th class="num">Stocks/G</th><th class="num">PS</th></tr></thead><tbody>${players.map((p) => `<tr data-player-key="${encodeURIComponent(playerKey(p))}"><td>${playerButton(p)}<div class="muted">${esc(p.grade || '')}</div></td><td class="num">${p.GP}</td><td class="num">${fmt(p.PPG)}</td><td class="num">${fmt(p.RPG)}</td><td class="num">${fmt(p.APG)}</td><td class="num">${fmt(p.StocksPG)}</td><td class="num">${fmt(p.playerScore)}</td></tr>`).join('')}</tbody></table></div>`;
}

function renderPlayer() {
  const player = BASKETBALL_PLAYERS.find((p) => playerKey(p) === state.playerKey) || BASKETBALL_PLAYERS[0];
  if (!player) return;
  const team = TEAM_BY_SLUG[player.teamSlug];
  $('view-player').innerHTML = `<main class="shell pitch-player-page">${pageHeader(`${esc(player.name)}`, `${teamButton(team)} · ${esc(player.grade || '')}`)}
    <div class="grid-3"><div class="stat-card"><span>PS</span><strong>${fmt(player.playerScore)}</strong></div><div class="stat-card"><span>PPG</span><strong>${fmt(player.PPG)}</strong></div><div class="stat-card"><span>Off Inv</span><strong>${fmt(player.OffensiveInvolvement)}%</strong></div></div>
    <section class="card" style="margin-top:18px"><div class="card-title">Advanced Profile <span>Shares and breakdown</span></div>
    <div class="counting-grid">${LEADER_COLS.map(([key,label]) => `<div class="count-stat"><span>${label}</span><strong>${fmt(player[key])}${key.includes('Share') || key === 'FTPct' || key === 'OffensiveInvolvement' || key.includes('PointShare') || key === 'FTShare' ? '%' : ''}</strong></div>`).join('')}<div class="count-stat"><span>2PT Share</span><strong>${fmt(player.TwoPointShare)}%</strong></div><div class="count-stat"><span>3PT Share</span><strong>${fmt(player.ThreePointShare)}%</strong></div><div class="count-stat"><span>FT Share</span><strong>${fmt(player.FTShare)}%</strong></div></div></section></main>`;
}

function renderGame() {
  const game = BASKETBALL_GAMES.find((row) => gameKey(row) === state.gameKey) || BASKETBALL_GAMES[0];
  if (!game) return;
  const team = TEAM_BY_SLUG[game.teamSlug];
  const opponent = TEAM_BY_SLUG[game.opponentSlug];
  const projection = team && opponent ? predict(team, opponent) : null;
  $('view-game').innerHTML = `<main class="shell">${pageHeader('Game Detail', `${esc(game.date)} · ${esc(game.tournament || 'Regular Season')}`)}
    <section class="card pad game-detail-card">
      <div class="game-detail-row">
        <div>${teamButton(team)}<span class="game-score">${game.teamScore ?? '—'}</span></div>
        <div>${opponent ? teamButton(opponent) : esc(game.opponent)}<span class="game-score">${game.opponentScore ?? '—'}</span></div>
      </div>
      ${game.tournament ? `<div class="tourney-badge">${esc(game.tournament)}</div>` : ''}
      ${projection ? `<div class="prediction-card"><div class="prediction-pick-label">Rating Preview</div><div class="prediction-confidence">${esc(team.name)} ${(projection.winA * 100).toFixed(1)}% · ${esc(opponent.name)} ${((1 - projection.winA) * 100).toFixed(1)}%</div></div>` : ''}
    </section></main>`;
}

function renderGlossary() {
  $('view-glossary').innerHTML = `<main class="shell">${pageHeader('Glossary', 'Court Index basketball metrics')}
    <section class="card pad"><p><strong>Stocks/Game</strong>: steals plus blocks per game.</p><p><strong>Team Scoring/Rebounding/Assist Share</strong>: player total divided by team total in that category.</p><p><strong>Points Responsible</strong>: points plus two times assists.</p><p><strong>Offensive Involvement</strong>: points responsible divided by team points.</p><p><strong>Scoring Breakdown</strong>: percentage of points from 2s, 3s, and free throws.</p><p><strong>Court Index Score</strong>: opponent-adjusted team rating using adjusted offense, adjusted defense, record, schedule strength, and scoring margin.</p></section></main>`;
}

function pageHeader(title, meta) {
  return `<div class="page-header"><h1>${title}</h1><p class="pitch-page-lede">${meta}</p></div>`;
}

function gamesTable(games, includeTeam) {
  return `<div class="table-wrap"><table><thead><tr>${includeTeam ? '<th>Team</th>' : ''}<th>Date</th><th>Opponent</th><th class="num">Result</th><th class="num">Score</th></tr></thead><tbody>${games.map((game) => {
    const team = TEAM_BY_SLUG[game.teamSlug];
    const opp = TEAM_BY_SLUG[game.opponentSlug];
    return `<tr data-game-key="${encodeURIComponent(gameKey(game))}">${includeTeam ? `<td>${teamButton(team)}</td>` : ''}<td>${esc(game.date)}</td><td>${opp ? teamButton(opp) : esc(game.opponent)}${game.tournament ? ` <span class="tourney-badge">${esc(game.tournament)}</span>` : ''}</td><td class="num ${game.result === 'W' ? 'score-good' : game.result === 'L' ? 'score-bad' : ''}">${esc(game.result || '—')}</td><td class="num">${esc(game.scoreText || '—')}</td></tr>`;
  }).join('')}</tbody></table></div>`;
}

function teamOptions(selected) {
  return BASKETBALL_TEAMS.map((team) => `<option value="${esc(team.slug)}" ${team.slug === selected ? 'selected' : ''}>${esc(team.name)}</option>`).join('');
}

function render() {
  if (state.view === 'home') renderHome();
  if (state.view === 'rankings') renderRankings();
  if (state.view === 'leaders') renderLeaders();
  if (state.view === 'scores') renderScores();
  if (state.view === 'predictor') renderPredictor();
  if (state.view === 'standings') renderStandings();
  if (state.view === 'teams') renderTeams();
  if (state.view === 'team') renderTeam();
  if (state.view === 'player') renderPlayer();
  if (state.view === 'game') renderGame();
  if (state.view === 'glossary') renderGlossary();
}

function closeDropdowns() {
  document.querySelectorAll('.nav-dropdown-menu').forEach((menu) => menu.classList.remove('open'));
}

function bindEvents() {
  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('.nav-dropdown-trigger');
    if (trigger) {
      const menu = trigger.parentElement?.querySelector('.nav-dropdown-menu');
      const open = menu?.classList.contains('open');
      closeDropdowns();
      if (!open) menu?.classList.add('open');
      return;
    }
    const viewTarget = event.target.closest('[data-view-target],[data-view]');
    if (viewTarget?.dataset.viewTarget || viewTarget?.dataset.view) {
      setView(viewTarget.dataset.viewTarget || viewTarget.dataset.view);
      closeDropdowns();
      return;
    }
    const teamEl = event.target.closest('[data-team-slug]');
    if (teamEl?.dataset.teamSlug) {
      setView('team', teamEl.dataset.teamSlug);
      return;
    }
    const playerEl = event.target.closest('[data-player-key]');
    if (playerEl?.dataset.playerKey) {
      setView('player', decodeURIComponent(playerEl.dataset.playerKey));
      return;
    }
    const gameEl = event.target.closest('[data-game-key]');
    if (gameEl?.dataset.gameKey) {
      setView('game', decodeURIComponent(gameEl.dataset.gameKey));
      return;
    }
    closeDropdowns();
  });
  document.addEventListener('input', (event) => {
    if (event.target.matches('[data-leader-query]')) { state.leaderFilters.query = event.target.value; renderLeaders(); }
    if (event.target.matches('[data-leader-min]')) { state.leaderFilters.min = event.target.value; renderLeaders(); }
    if (event.target.matches('[data-team-query]')) { state.filters.query = event.target.value; renderTeams(); }
    if (event.target.id === 'globalSearch') renderGlobalSearch(event.target.value);
  });
  document.addEventListener('change', (event) => {
    if (event.target.matches('[data-leader-conference]')) { state.leaderFilters.conference = event.target.value; renderLeaders(); }
    if (event.target.matches('[data-leader-team]')) { state.leaderFilters.team = event.target.value; renderLeaders(); }
    if (event.target.matches('[data-leader-grade]')) { state.leaderFilters.grade = event.target.value; renderLeaders(); }
    if (event.target.matches('[data-leader-stat]')) { state.leaderSort.key = event.target.value; renderLeaders(); }
    if (event.target.matches('[data-team-conference]')) { state.filters.conference = event.target.value; renderTeams(); }
    if (event.target.matches('[data-predictor-a]')) { state.predictor.teamA = event.target.value; renderPredictor(); }
    if (event.target.matches('[data-predictor-b]')) { state.predictor.teamB = event.target.value; renderPredictor(); }
  });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') { closeDropdowns(); closeReportProblem(); } });
}

function renderGlobalSearch(query) {
  const box = $('searchResults');
  if (!box) return;
  const q = query.trim().toLowerCase();
  if (!q) {
    box.innerHTML = '';
    box.classList.remove('open');
    return;
  }
  const teams = BASKETBALL_TEAMS.filter((team) => team.name.toLowerCase().includes(q)).slice(0, 5);
  const players = BASKETBALL_PLAYERS.filter((player) => player.name.toLowerCase().includes(q)).slice(0, 7);
  const rows = [
    ...players.map((player) => `<button type="button" data-player-key="${encodeURIComponent(playerKey(player))}"><span>${esc(player.name)}</span><small>${esc(player.team)}</small></button>`),
    ...teams.map((team) => `<button type="button" data-team-slug="${esc(team.slug)}"><span>${logo(team, 16)}${esc(team.name)}</span><small>${esc(team.conference)}</small></button>`),
  ];
  box.innerHTML = rows.length ? rows.join('') : '<div class="search-empty">No results</div>';
  box.classList.add('open');
}

function init() {
  const saved = localStorage.getItem('diamondIndexTheme');
  const preferred = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  applyTheme(saved || preferred);
  const seasonEnd = (BASKETBALL_DATA.season || '2025-2026').split('-')[1] || (BASKETBALL_DATA.season || '2025-2026').slice(0, 4);
  $('basketballSeasonSelect').innerHTML = `<option>${esc(seasonEnd)}</option>`;
  $('teamsNavList').innerHTML = BASKETBALL_TEAMS.slice(0, 80).map((team) => `<button class="nav-dropdown-item" data-team-slug="${esc(team.slug)}">${esc(team.name)}</button>`).join('');
  bindEvents();
  render();
}

init();
