const FOOTBALL_TEAMS = FOOTBALL_DATA.teams || [];
const FOOTBALL_PLAYERS = FOOTBALL_DATA.players || [];
const FOOTBALL_GAMES = FOOTBALL_DATA.games || [];
const FOOTBALL_TEAM_BY_SLUG = Object.fromEntries(FOOTBALL_TEAMS.map((team) => [team.slug, team]));
const FOOTBALL_CONFERENCES = [...new Set(FOOTBALL_TEAMS.map((team) => team.conference))].sort();

const footballState = {
  view: 'home',
  previousView: 'home',
  teamSlug: '',
  playerKey: '',
  leaderSide: 'offense',
  leaderSort: { key: 'playerScore', asc: false },
  leaderPage: 1,
  rankingSort: { key: 'powerScore', asc: false },
  conference: 'All',
  search: '',
  role: 'All',
  teamPanel: 'offense',
  predictor: { teamA: FOOTBALL_TEAMS[0]?.slug || '', teamB: FOOTBALL_TEAMS[1]?.slug || '', venue: 'neutral' },
};

const footballMetricLabels = {
  Cmp: 'Completions', PassAtt: 'Pass Attempts', INT: 'Interceptions', PassLng: 'Longest Pass',
  AdjYPA: 'Adjusted Yards / Attempt', CmpPct: 'Completion %', PassTD: 'Passing TD', PassYds: 'Passing Yards', INTPct: 'Interception %',
  RushAtt: 'Carries', RushYds: 'Rushing Yards', RushYPA: 'Yards / Carry', RushTD: 'Rushing TD', RushLng: 'Longest Rush',
  RecYds: 'Receiving Yards', RecYPR: 'Yards / Reception', RecTD: 'Receiving TD', Rec: 'Receptions', RecLng: 'Longest Reception',
  DefImpact: 'Defensive Impact', Tackles: 'Total Tackles', TFL: 'Tackles for Loss', Sacks: 'Sacks', Solo: 'Solo Tackles', Ast: 'Assisted Tackles', DefINT: 'Interceptions', FF: 'Forced Fumbles', FR: 'Fumble Recoveries', FumTD: 'Fumble TD', IntTD: 'Interception TD', Safety: 'Safeties', KB: 'Blocked Kicks',
  FGM: 'Field Goals Made', FGA: 'Field Goal Attempts', XPM: 'Extra Points Made', XPA: 'Extra Point Attempts', TwoPT: 'Two-Point Conversions', KickPoints: 'Kicking Points', FGPct: 'Field Goal %', XPPct: 'Extra Point %', FGLng: 'Longest Field Goal',
  Punts: 'Punts', PuntYds: 'Punt Yards', PuntAvg: 'Punt Average', Inside20: 'Inside 20', PuntLng: 'Longest Punt',
  KORAtt: 'Kick Returns', KORYds: 'Kick Return Yards', KORLng: 'Longest Kick Return', PRAtt: 'Punt Returns', PRYds: 'Punt Return Yards', PRLng: 'Longest Punt Return', ReturnAvg: 'Return Average', KORTD: 'Kick Return TD', PRTD: 'Punt Return TD',
  TotalYds: 'Total Yards', TotalTD: 'Total TD',
};

function footballEl(id) { return document.getElementById(id); }
function footballEsc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}
function footballNum(value, digits = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '-';
}
function footballPlayerKey(player) { return `${player.name}__${player.teamSlug}`; }
function footballPlayer(player) { return FOOTBALL_PLAYERS.find((item) => footballPlayerKey(item) === player); }
function footballLogo(team, size = 28) {
  if (!team?.logo) return `<span class="football-logo-fallback" style="width:${size}px;height:${size}px">${footballEsc(team?.name?.[0] || 'F')}</span>`;
  return `<img class="football-team-logo" src="${footballEsc(team.logo)}" alt="" width="${size}" height="${size}" loading="lazy">`;
}
function footballTeamButton(team, className = 'linkish') {
  return `<button class="${className}" data-team-slug="${footballEsc(team.slug)}" type="button">${footballEsc(team.name)}</button>`;
}
function footballPlayerButton(player) {
  return `<button class="linkish" data-player-key="${encodeURIComponent(footballPlayerKey(player))}" type="button">${footballEsc(player.name)}</button>`;
}
function footballUpdated() {
  const date = new Date(FOOTBALL_DATA.updated || '');
  return Number.isNaN(date.getTime()) ? 'Update unavailable' : `Updated ${date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
}
function footballDateValue(value) {
  const match = String(value || '').match(/(\d{1,2})\/(\d{1,2})/);
  if (!match) return 0;
  const startYear = Number(String(FOOTBALL_DATA.season || '').slice(0, 4)) || new Date().getFullYear();
  const month = Number(match[1]);
  return new Date(month >= 7 ? startYear : startYear + 1, month - 1, Number(match[2])).getTime();
}
function footballCloseDropdowns() {
  document.querySelectorAll('.nav-dropdown-menu').forEach((menu) => menu.classList.remove('open'));
}

function footballGroupBy(items, keyFor) {
  return items.reduce((groups, item) => {
    const key = keyFor(item);
    (groups[key] ||= []).push(item);
    return groups;
  }, {});
}

function initFootballTheme() {
  const saved = localStorage.getItem('sports-index-theme');
  const theme = saved || 'dark';
  document.documentElement.dataset.theme = theme;
  const label = footballEl('themeToggleLabel');
  if (label) label.textContent = theme === 'light' ? 'Light' : 'Dark';
}
function toggleTheme() {
  const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = next;
  localStorage.setItem('sports-index-theme', next);
  const label = footballEl('themeToggleLabel');
  if (label) label.textContent = next === 'light' ? 'Light' : 'Dark';
}
function openReportProblem() { footballEl('reportModal')?.classList.add('open'); footballEl('reportModal')?.setAttribute('aria-hidden', 'false'); }
function closeReportProblem() { footballEl('reportModal')?.classList.remove('open'); footballEl('reportModal')?.setAttribute('aria-hidden', 'true'); }
function submitProblemReport(event) {
  event.preventDefault();
  const type = footballEl('reportType')?.value || 'Other';
  const details = footballEl('reportDetails')?.value || '';
  const contact = footballEl('reportContact')?.value || '';
  const title = encodeURIComponent(`[Gridiron Index] ${type}`);
  const body = encodeURIComponent(`Page: ${location.href}\nSeason: ${FOOTBALL_DATA.season}\n\n${details}\n\nContact: ${contact || 'Not provided'}`);
  window.open(`https://github.com/miles-burton/njbaseball/issues/new?title=${title}&body=${body}`, '_blank', 'noopener');
}

function footballSetView(view) {
  footballState.previousView = footballState.view;
  footballState.view = view;
  document.querySelectorAll('.view').forEach((element) => element.classList.remove('active'));
  footballEl(`view-${view}`)?.classList.add('active');
  document.querySelectorAll('.pitch-nav .nav-tab').forEach((tab) => tab.classList.remove('active'));
  const navMap = { rankings: 'tab-team-rankings', scores: 'tab-scores', predictor: 'tab-predictor', standings: 'tab-standings', glossary: 'tab-glossary' };
  if (navMap[view]) footballEl(navMap[view])?.classList.add('active');
  footballRender();
  window.scrollTo({ top: 0, behavior: 'auto' });
}

function footballPageHeader(kicker, title, description) {
  return `<div class="page-banner"><div class="page-banner-inner"><div><div class="page-kicker">${footballEsc(kicker)}</div><h1 class="page-title">${footballEsc(title)}</h1><div class="page-meta">${footballEsc(description)}</div></div><div class="page-updated">${footballEsc(footballUpdated())}</div></div></div>`;
}

function footballUniqueGames() {
  const seen = new Set();
  return FOOTBALL_GAMES.filter((game) => {
    if (game.teamScore == null || game.opponentScore == null) return false;
    const pair = [game.teamSlug, game.opponentSlug || game.opponent].sort().join('::');
    const key = game.gameUrl || `${game.date}::${pair}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function footballRenderHome() {
  const top = FOOTBALL_TEAMS.slice(0, 10);
  const completed = footballUniqueGames();
  const latestDate = Math.max(...completed.map((game) => footballDateValue(game.date)), 0);
  const scores = completed.filter((game) => footballDateValue(game.date) === latestDate).sort((a, b) => {
    const importanceA = (FOOTBALL_TEAM_BY_SLUG[a.teamSlug]?.powerScore || 0) + (FOOTBALL_TEAM_BY_SLUG[a.opponentSlug]?.powerScore || 0);
    const importanceB = (FOOTBALL_TEAM_BY_SLUG[b.teamSlug]?.powerScore || 0) + (FOOTBALL_TEAM_BY_SLUG[b.opponentSlug]?.powerScore || 0);
    return importanceB - importanceA;
  }).slice(0, 5);
  const offense = FOOTBALL_PLAYERS.filter((player) => ['QB', 'Rusher', 'Receiver'].includes(player.role)).sort((a, b) => b.playerScore - a.playerScore).slice(0, 5);
  const defense = FOOTBALL_PLAYERS.filter((player) => player.role === 'Defender').sort((a, b) => b.playerScore - a.playerScore).slice(0, 5);
  footballEl('view-home').innerHTML = `
    <section class="home-hero pitch-hero football-home-hero">
      <div class="home-hero-inner">
        <div class="home-hero-text">
          <div class="home-hero-eyebrow">New Jersey Football &middot; ${footballEsc(FOOTBALL_DATA.season)} Season</div>
          <h1 class="home-hero-title">GRIDIRON<br>INDEX</h1>
          <div class="home-hero-tagline">Measure Every Down.</div>
          <p class="home-hero-sub">Statewide team ratings and role-based player analytics built from real NJ.com schedules, results, and seven football stat groups.</p>
          <div class="home-hero-actions">
            <button class="home-btn-primary" data-view-target="rankings">Power Rankings</button>
            <button class="home-btn-secondary" data-view-target="leaders">Player Leaders</button>
          </div>
        </div>
        <aside class="pitch-hero-index" aria-label="Top three Gridiron Index teams">
          <div class="pitch-hero-index-header"><div><span>Live Index</span><strong>State Top 3</strong></div><button data-view-target="rankings">View all</button></div>
          <div class="pitch-hero-index-list">${top.slice(0, 3).map((team) => `<button class="pitch-hero-index-row" data-team-slug="${footballEsc(team.slug)}"><span class="pitch-hero-index-rank">${team.rank}</span><span class="pitch-hero-index-logo">${footballLogo(team, 30)}</span><span class="pitch-hero-index-team"><strong>${footballEsc(team.name)}</strong><small>${footballEsc(team.record)} &middot; ${footballEsc(team.conference)}</small></span><span class="pitch-hero-index-score">${team.powerScore.toFixed(1)}</span></button>`).join('')}</div>
          <div class="pitch-hero-index-updated">${footballEsc(footballUpdated())}</div>
        </aside>
      </div>
    </section>
    <main class="shell football-home-shell">
      <div class="pitch-grid-3 football-action-grid">
        <button class="home-action-card" data-view-target="rankings"><span>Gridiron Score</span><strong>Opponent-adjusted team ratings with schedule quality and capped margins.</strong></button>
        <button class="home-action-card" data-view-target="leaders"><span>Player Analytics</span><strong>Role-specific scores and percentiles across seven statistical groups.</strong></button>
        <button class="home-action-card" data-view-target="predictor"><span>Matchup Predictor</span><strong>Expected score and win probability from adjusted offense and defense.</strong></button>
      </div>
      <div class="football-dashboard-grid">
        <section class="card"><div class="card-title">Recent Scores <button class="linkish" data-view-target="scores">All Scores</button></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Game</th><th class="num">Score</th><th class="num">GI</th></tr></thead><tbody>${scores.map((game, index) => footballScoreRow(game, index + 1)).join('')}</tbody></table></div></section>
        <section class="card"><div class="card-title">Power Rankings <button class="linkish" data-view-target="rankings">Top 10</button></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Team</th><th class="num">Score</th><th class="num">AdjO</th><th class="num">AdjD</th></tr></thead><tbody>${top.slice(0, 6).map((team) => `<tr><td class="rank-cell">${team.rank}</td><td><div class="football-table-team">${footballLogo(team, 24)}${footballTeamButton(team)}</div></td><td class="num score-good">${team.powerScore.toFixed(1)}</td><td class="num">${team.adjO.toFixed(1)}</td><td class="num">${team.adjD.toFixed(1)}</td></tr>`).join('')}</tbody></table></div></section>
        ${footballHomeLeaders('Offensive Leaders', offense)}
        ${footballHomeLeaders('Defensive Leaders', defense)}
      </div>
    </main>`;
}

function footballHomeLeaders(title, players) {
  return `<section class="card"><div class="card-title">${title}<button class="linkish" data-view-target="leaders">View all</button></div><div class="football-mini-leaders">${players.map((player, index) => {
    const team = FOOTBALL_TEAM_BY_SLUG[player.teamSlug];
    return `<button class="football-mini-player" data-player-key="${encodeURIComponent(footballPlayerKey(player))}"><span class="rank-cell">${index + 1}</span>${footballLogo(team, 28)}<span><strong>${footballEsc(player.name)}</strong><small>${footballEsc(player.team)} &middot; ${footballEsc(player.role)}</small></span><b>${player.playerScore.toFixed(1)}</b></button>`;
  }).join('')}</div></section>`;
}

function footballScoreRow(game, rank = '') {
  const team = FOOTBALL_TEAM_BY_SLUG[game.teamSlug];
  const opponent = FOOTBALL_TEAM_BY_SLUG[game.opponentSlug];
  const teamWon = game.result === 'W';
  const winner = teamWon ? team : opponent;
  const loser = teamWon ? opponent : team;
  const winnerName = winner?.name || (teamWon ? game.team : game.opponent);
  const loserName = loser?.name || (teamWon ? game.opponent : game.team);
  const winnerScore = Math.max(game.teamScore, game.opponentScore);
  const loserScore = Math.min(game.teamScore, game.opponentScore);
  return `<tr class="football-score-row"><td class="rank-cell">${rank}</td><td>${game.tournament ? '<span class="home-score-badge">TOURNEY</span>' : ''}<div class="football-score-matchup"><strong>${winner ? footballTeamButton(winner) : footballEsc(winnerName)}</strong><span>def.</span>${loser ? footballTeamButton(loser) : footballEsc(loserName)}</div></td><td class="num">${winnerScore}-${loserScore}</td><td class="num score-good">${winner?.powerScore?.toFixed(1) || '-'}</td></tr>`;
}

function footballFilteredPlayers() {
  const sideRoles = footballState.leaderSide === 'defense' ? ['Defender'] : ['QB', 'Rusher', 'Receiver', 'Kicker', 'Punter', 'Returner', 'Utility'];
  const query = footballState.search.toLowerCase();
  return FOOTBALL_PLAYERS.filter((player) => sideRoles.includes(player.role))
    .filter((player) => footballState.conference === 'All' || player.conference === footballState.conference)
    .filter((player) => footballState.role === 'All' || player.role === footballState.role)
    .filter((player) => !query || player.name.toLowerCase().includes(query) || player.team.toLowerCase().includes(query));
}

function footballRenderLeaders() {
  const roles = footballState.leaderSide === 'defense' ? ['All', 'Defender'] : ['All', 'QB', 'Rusher', 'Receiver', 'Kicker', 'Punter', 'Returner', 'Utility'];
  const rows = footballFilteredPlayers();
  const { key, asc } = footballState.leaderSort;
  rows.sort((a, b) => ((Number(a[key]) || 0) - (Number(b[key]) || 0)) * (asc ? 1 : -1));
  const pageSize = 100;
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  footballState.leaderPage = Math.min(footballState.leaderPage, pages);
  const visible = rows.slice((footballState.leaderPage - 1) * pageSize, footballState.leaderPage * pageSize);
  const stats = footballState.leaderSide === 'defense'
    ? [['playerScore', 'PS'], ['DefImpact', 'Impact'], ['Tackles', 'Tackles'], ['TFL', 'TFL'], ['Sacks', 'Sacks'], ['DefINT', 'INT'], ['FF', 'FF']]
    : [['playerScore', 'PS'], ['TotalYds', 'Total Yds'], ['TotalTD', 'Total TD'], ['PassYds', 'Pass Yds'], ['RushYds', 'Rush Yds'], ['RecYds', 'Rec Yds']];
  footballEl('view-leaders').innerHTML = `${footballPageHeader('Player Analytics', `${footballState.leaderSide === 'defense' ? 'Defensive' : 'Offensive'} Leaders`, `${rows.length.toLocaleString()} qualified player profiles`)}
    <main class="leaderboard-wrap pitch-leaders-wrap football-leaders-wrap">
      <div class="controls-row">
        <div class="football-side-switch"><button class="${footballState.leaderSide === 'offense' ? 'active' : ''}" data-leader-side="offense">Offense</button><button class="${footballState.leaderSide === 'defense' ? 'active' : ''}" data-leader-side="defense">Defense</button></div>
        <div class="search-wrap"><input class="search-input" data-football-search type="search" value="${footballEsc(footballState.search)}" placeholder="Search player..."></div>
        <select class="ctrl-select" data-football-conference><option>All</option>${FOOTBALL_CONFERENCES.map((conference) => `<option ${footballState.conference === conference ? 'selected' : ''}>${footballEsc(conference)}</option>`).join('')}</select>
        <select class="ctrl-select" data-football-role>${roles.map((role) => `<option ${footballState.role === role ? 'selected' : ''}>${footballEsc(role)}</option>`).join('')}</select>
      </div>
      <div class="lb-count">Showing <strong>${rows.length.toLocaleString()}</strong> players</div>
      <div class="lb-table-wrap"><table><thead><tr><th>#</th><th>Player</th><th>Team</th><th>Role</th>${stats.map(([stat, label]) => `<th class="num sortable" data-player-sort="${stat}">${label}${key === stat ? (asc ? ' &#9650;' : ' &#9660;') : ''}</th>`).join('')}</tr></thead><tbody>${visible.map((player, index) => {
        const team = FOOTBALL_TEAM_BY_SLUG[player.teamSlug];
        return `<tr><td class="rank-cell">${(footballState.leaderPage - 1) * pageSize + index + 1}</td><td class="player-cell">${footballPlayerButton(player)}<div class="player-sub">${footballEsc(player.grade)}${player.position ? ` &middot; ${footballEsc(player.position)}` : ''}</div></td><td><button class="team-chip" data-team-slug="${footballEsc(player.teamSlug)}">${footballLogo(team, 18)}${footballEsc(player.team)}</button></td><td>${footballEsc(player.role)}</td>${stats.map(([stat]) => `<td class="num ${stat === 'playerScore' ? 'score-good' : ''}">${footballNum(player[stat], stat === 'playerScore' ? 1 : 0)}</td>`).join('')}</tr>`;
      }).join('')}</tbody></table></div>
      <div class="football-pagination"><button data-player-page="prev" ${footballState.leaderPage <= 1 ? 'disabled' : ''}>Previous</button><span>Page ${footballState.leaderPage} of ${pages}</span><button data-player-page="next" ${footballState.leaderPage >= pages ? 'disabled' : ''}>Next</button></div>
    </main>`;
}

function footballRenderRankings() {
  const query = footballState.search.toLowerCase();
  const teams = FOOTBALL_TEAMS.filter((team) => footballState.conference === 'All' || team.conference === footballState.conference)
    .filter((team) => !query || team.name.toLowerCase().includes(query));
  const { key, asc } = footballState.rankingSort;
  teams.sort((a, b) => ((Number(a[key]) || 0) - (Number(b[key]) || 0)) * (asc ? 1 : -1));
  const columns = [['powerScore', 'Gridiron'], ['adjO', 'AdjO'], ['adjD', 'AdjD'], ['adjNet', 'Net'], ['sos', 'SOS'], ['qualityScore', 'Quality'], ['luck', 'Luck'], ['pfPerGame', 'PF/G'], ['paPerGame', 'PA/G']];
  footballEl('view-rankings').innerHTML = `${footballPageHeader('Team Analytics', 'Power Rankings', 'Opponent-adjusted football ratings on a 0-100 scale')}
    <main class="shell football-rankings"><div class="controls-row"><div class="search-wrap"><input class="search-input" data-football-search type="search" value="${footballEsc(footballState.search)}" placeholder="Search teams..."></div><select class="ctrl-select" data-football-conference><option>All</option>${FOOTBALL_CONFERENCES.map((conference) => `<option ${footballState.conference === conference ? 'selected' : ''}>${footballEsc(conference)}</option>`).join('')}</select></div>
    <div class="lb-table-wrap"><table><thead><tr><th>#</th><th>Team</th><th>Conf</th><th>Record</th>${columns.map(([stat, label]) => `<th class="num sortable" data-ranking-sort="${stat}">${label}${key === stat ? (asc ? ' &#9650;' : ' &#9660;') : ''}</th>`).join('')}</tr></thead><tbody>${teams.map((team) => `<tr><td class="rank-cell">${team.rank}</td><td><div class="football-table-team">${footballLogo(team, 28)}${footballTeamButton(team)}</div></td><td>${footballEsc(team.conference)}</td><td>${footballEsc(team.record)}</td>${columns.map(([stat]) => `<td class="num ${stat === 'powerScore' ? 'score-good' : ''}">${footballNum(team[stat], 1)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></main>`;
}

function footballRenderScores() {
  const games = footballUniqueGames().sort((a, b) => footballDateValue(b.date) - footballDateValue(a.date) || ((FOOTBALL_TEAM_BY_SLUG[b.teamSlug]?.powerScore || 0) - (FOOTBALL_TEAM_BY_SLUG[a.teamSlug]?.powerScore || 0)));
  footballEl('view-scores').innerHTML = `${footballPageHeader('Scoreboard', 'Recent Scores', 'Completed games from the NJ.com statewide schedule')}
    <main class="shell football-scores"><div class="card"><div class="table-wrap"><table><thead><tr><th>#</th><th>Date</th><th>Game</th><th class="num">Score</th><th class="num">Gridiron</th></tr></thead><tbody>${games.slice(0, 300).map((game, index) => footballScoreRow(game, index + 1).replace('<td class="rank-cell">', `<td class="rank-cell">`).replace('</td><td>', `</td><td>${footballEsc(game.date)}</td><td>`)).join('')}</tbody></table></div></div></main>`;
}

function footballRenderTeams() {
  const query = footballState.search.toLowerCase();
  const teams = FOOTBALL_TEAMS.filter((team) => footballState.conference === 'All' || team.conference === footballState.conference).filter((team) => !query || team.name.toLowerCase().includes(query));
  footballEl('view-teams').innerHTML = `${footballPageHeader('Directory', 'All Teams', `${teams.length} football programs`)}<main class="teams-wrap"><div class="controls-row"><div class="search-wrap"><input class="search-input" data-football-search value="${footballEsc(footballState.search)}" placeholder="Search teams..."></div><select class="ctrl-select" data-football-conference><option>All</option>${FOOTBALL_CONFERENCES.map((conference) => `<option ${footballState.conference === conference ? 'selected' : ''}>${footballEsc(conference)}</option>`).join('')}</select></div><div class="teams-grid">${teams.map((team) => `<button class="team-card" data-team-slug="${footballEsc(team.slug)}"><div class="team-card-top">${footballLogo(team, 44)}<div><strong>${footballEsc(team.name)}</strong><small>${footballEsc(team.conference)} &middot; ${footballEsc(team.division)}</small></div></div><div class="team-card-stats"><div><b>#${team.rank}</b><span>State</span></div><div><b>${team.powerScore.toFixed(1)}</b><span>GI</span></div><div><b>${footballEsc(team.record)}</b><span>Record</span></div></div></button>`).join('')}</div></main>`;
}

function footballRenderStandings() {
  const conferences = footballState.conference === 'All' ? FOOTBALL_CONFERENCES : [footballState.conference];
  footballEl('view-standings').innerHTML = `${footballPageHeader('League Tables', 'Standings', 'Conference and division records from NJ.com')}<main class="standings-wrap"><div class="controls-row"><select class="ctrl-select" data-football-conference><option>All</option>${FOOTBALL_CONFERENCES.map((conference) => `<option ${footballState.conference === conference ? 'selected' : ''}>${footballEsc(conference)}</option>`).join('')}</select></div>${conferences.map((conference) => {
    const divisions = footballGroupBy(FOOTBALL_TEAMS.filter((team) => team.conference === conference), (team) => team.division || 'Overall');
    return `<section class="card standings-group"><div class="standings-heading">${footballEsc(conference)}</div>${Object.entries(divisions).map(([division, teams]) => `<div class="standings-division-block"><h3>${footballEsc(division)}</h3><div class="standings-table-wrap"><table><thead><tr><th>#</th><th>Team</th><th>Record</th><th>Division</th><th class="num">PF</th><th class="num">PA</th><th class="num">GI</th></tr></thead><tbody>${teams.sort((a, b) => b.divisionWins - a.divisionWins || b.winPct - a.winPct).map((team, index) => `<tr><td>${index + 1}</td><td><div class="football-table-team">${footballLogo(team, 22)}${footballTeamButton(team)}</div></td><td>${footballEsc(team.record)}</td><td>${footballEsc(team.divisionRecord)}</td><td class="num">${team.pf}</td><td class="num">${team.pa}</td><td class="num score-good">${team.powerScore.toFixed(1)}</td></tr>`).join('')}</tbody></table></div></div>`).join('')}</section>`;
  }).join('')}</main>`;
}

function footballPredict(teamA, teamB, venue) {
  if (!teamA || !teamB || teamA.slug === teamB.slug) return null;
  const homeA = venue === 'a-home' ? 1.5 : venue === 'b-home' ? -1.5 : 0;
  const scoreA = Math.max(3, (teamA.adjO + teamB.adjD) / 2 + homeA);
  const scoreB = Math.max(3, (teamB.adjO + teamA.adjD) / 2 - homeA);
  const winA = 1 / (1 + Math.exp(-(scoreA - scoreB) / 8.5));
  return { scoreA, scoreB, winA };
}
function footballTeamInput(slot, team) {
  return `<input class="predictor-team-search" data-predict-team-search="${slot}" list="footballTeamList" type="search" value="${footballEsc(team?.name || '')}" placeholder="Search teams...">`;
}
function footballRenderPredictor() {
  const teamA = FOOTBALL_TEAM_BY_SLUG[footballState.predictor.teamA] || FOOTBALL_TEAMS[0];
  const teamB = FOOTBALL_TEAM_BY_SLUG[footballState.predictor.teamB] || FOOTBALL_TEAMS[1];
  const prediction = footballPredict(teamA, teamB, footballState.predictor.venue);
  footballEl('view-predictor').innerHTML = `${footballPageHeader('Game Model', 'Matchup Predictor', 'Neutral-field projections from adjusted scoring and defensive efficiency')}<main class="predictor-wrap"><div class="predictor-panel"><div class="predictor-controls"><label class="predictor-field"><span>Team A</span>${footballTeamInput('A', teamA)}</label><label class="predictor-field"><span>Venue</span><select data-predict-venue><option value="neutral">Neutral</option><option value="a-home" ${footballState.predictor.venue === 'a-home' ? 'selected' : ''}>Team A Home</option><option value="b-home" ${footballState.predictor.venue === 'b-home' ? 'selected' : ''}>Team B Home</option></select></label><label class="predictor-field"><span>Team B</span>${footballTeamInput('B', teamB)}</label></div><datalist id="footballTeamList">${FOOTBALL_TEAMS.map((team) => `<option value="${footballEsc(team.name)}"></option>`).join('')}</datalist>${prediction ? `<div class="prediction-card"><div class="prediction-head"><div class="prediction-team">${footballLogo(teamA, 54)}<div><strong>${footballEsc(teamA.name)}</strong><span>#${teamA.rank} &middot; GI ${teamA.powerScore.toFixed(1)}</span></div></div><div class="prediction-vs"><small>Projected Score</small><b>${prediction.scoreA.toFixed(1)} - ${prediction.scoreB.toFixed(1)}</b></div><div class="prediction-team prediction-team-right">${footballLogo(teamB, 54)}<div><strong>${footballEsc(teamB.name)}</strong><span>#${teamB.rank} &middot; GI ${teamB.powerScore.toFixed(1)}</span></div></div></div><div class="football-win-bar"><div style="width:${(prediction.winA * 100).toFixed(1)}%"></div></div><div class="football-win-labels"><strong>${(prediction.winA * 100).toFixed(1)}% ${footballEsc(teamA.name)}</strong><strong>${((1 - prediction.winA) * 100).toFixed(1)}% ${footballEsc(teamB.name)}</strong></div></div>` : '<div class="predictor-empty">Choose two different teams.</div>'}</div></main>`;
}

function footballRenderGlossary() {
  const cards = [
    ['Gridiron Score', '0-100 team rating blending opponent-adjusted efficiency, results, schedule strength, and quality performance. Blowout margins are logarithmically dampened.'],
    ['AdjO', 'Points scored per game adjusted for the defensive quality of every opponent. Higher is better.'],
    ['AdjD', 'Points allowed per game adjusted for opponent offensive quality. Lower is better.'],
    ['SOS', 'Average opponent winning percentage, displayed on a 0-100 scale.'],
    ['Player Score', '0-100 composite calculated against players in the same primary role. Team schedule strength provides a small adjustment.'],
    ['Adj Y/A', '(Passing yards + 20 x passing TD - 45 x interceptions) / attempts.'],
    ['Def Impact', 'Tackles plus weighted impact plays: TFL, sacks, takeaways, defensive touchdowns, safeties, and blocked kicks.'],
    ['Luck', 'Actual winning percentage minus the expected percentage generated by adjusted point efficiency.'],
  ];
  footballEl('view-glossary').innerHTML = `${footballPageHeader('Methodology', 'Glossary', 'Definitions for Gridiron Index ratings and advanced football metrics')}<main class="glossary-wrap"><div class="glossary-grid">${cards.map(([stat, text]) => `<div class="glossary-card ${['Gridiron Score', 'Player Score'].includes(stat) ? 'gc-highlight' : ''}"><div class="gc-stat">${footballEsc(stat)}</div><div class="gc-def">${footballEsc(text)}</div></div>`).join('')}</div></main>`;
}

function footballRosterTable(players, side) {
  const offense = side === 'offense';
  const columns = offense ? [['playerScore', 'PS'], ['PassYds', 'Pass Yds'], ['PassTD', 'Pass TD'], ['RushYds', 'Rush Yds'], ['RushTD', 'Rush TD'], ['RecYds', 'Rec Yds'], ['RecTD', 'Rec TD']] : [['playerScore', 'PS'], ['DefImpact', 'Impact'], ['Tackles', 'Tackles'], ['TFL', 'TFL'], ['Sacks', 'Sacks'], ['DefINT', 'INT'], ['FF', 'FF']];
  const offensiveRoles = ['QB', 'Rusher', 'Receiver', 'Kicker', 'Punter', 'Returner', 'Utility'];
  const filtered = players.filter((player) => offense ? offensiveRoles.includes(player.role) : player.groups.includes('defense')).sort((a, b) => b.playerScore - a.playerScore);
  return `<div class="table-wrap"><table><thead><tr><th>Player</th><th>Role</th>${columns.map(([, label]) => `<th class="num">${label}</th>`).join('')}</tr></thead><tbody>${filtered.map((player) => `<tr><td class="player-cell">${footballPlayerButton(player)}<div class="player-sub">${footballEsc(player.grade)}${player.position ? ` &middot; ${footballEsc(player.position)}` : ''}</div></td><td>${footballEsc(player.role)}</td>${columns.map(([stat]) => `<td class="num ${stat === 'playerScore' ? 'score-good' : ''}">${footballNum(player[stat], stat === 'playerScore' ? 1 : 0)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
}

function footballSchedule(team) {
  return `<div class="table-wrap"><table class="football-schedule"><thead><tr><th>Date</th><th>Opponent</th><th>W/L</th><th class="num">Score</th></tr></thead><tbody>${team.schedule.map((game) => {
    const opponent = FOOTBALL_TEAM_BY_SLUG[game.opponentSlug];
    return `<tr><td>${footballEsc(game.date)}</td><td><div class="pitch-schedule-opponent">${opponent ? footballLogo(opponent, 22) : ''}${opponent ? footballTeamButton(opponent, 'schedule-team-link') : `<strong>${footballEsc(game.opponent)}</strong>`}${game.tournament ? `<span class="tournament-badge schedule-tournament-badge">${footballEsc(game.tournament)}</span>` : ''}</div></td><td class="result-${footballEsc(game.result.toLowerCase())}">${footballEsc(game.result || '-')}</td><td class="num">${footballEsc(game.scoreText || (game.teamScore == null ? '-' : `${game.teamScore}-${game.opponentScore}`))}</td></tr>`;
  }).join('')}</tbody></table></div>`;
}

function footballRenderTeam() {
  const team = FOOTBALL_TEAM_BY_SLUG[footballState.teamSlug];
  if (!team) return footballSetView('teams');
  const players = FOOTBALL_PLAYERS.filter((player) => player.teamSlug === team.slug);
  footballEl('view-team').innerHTML = `<main class="team-wrap football-team-page"><div class="team-hero"><div class="team-shield-lg">${footballLogo(team, 70)}</div><div class="team-info"><div class="team-name-lg">${footballEsc(team.name)}</div><div class="team-details"><span class="team-meta-pill team-meta-pill-accent"><span>Record</span>${footballEsc(team.record)}</span><span class="team-meta-pill"><span>Conference</span>${footballEsc(team.conference)}</span><span class="team-meta-pill"><span>Division</span>${footballEsc(team.division)}</span><span class="team-meta-pill team-meta-pill-accent"><span>Div Record</span>${footballEsc(team.divisionRecord)}</span></div></div></div><div class="team-stat-cards"><div class="team-stat-card team-score-card"><div class="team-stat-card-label">GI Score</div><div class="team-stat-card-val">${team.powerScore.toFixed(1)}</div></div><div class="team-stat-card"><div class="team-stat-card-label">State Rank</div><div class="team-stat-card-val">#${team.rank}</div></div><div class="team-stat-card"><div class="team-stat-card-label">AdjO</div><div class="team-stat-card-val">${team.adjO.toFixed(1)}</div></div><div class="team-stat-card"><div class="team-stat-card-label">AdjD</div><div class="team-stat-card-val">${team.adjD.toFixed(1)}</div></div><div class="team-stat-card"><div class="team-stat-card-label">SOS</div><div class="team-stat-card-val">${team.sos.toFixed(1)}</div></div><div class="team-stat-card"><div class="team-stat-card-label">PF/G</div><div class="team-stat-card-val">${team.pfPerGame.toFixed(1)}</div></div><div class="team-stat-card"><div class="team-stat-card-label">PA/G</div><div class="team-stat-card-val">${team.paPerGame.toFixed(1)}</div></div><div class="team-stat-card"><div class="team-stat-card-label">Quality Wins</div><div class="team-stat-card-val">${team.qualityWins}</div></div></div><div class="team-section-tabs"><button class="team-section-tab ${footballState.teamPanel === 'offense' ? 'active' : ''}" data-team-panel-target="offense">Offense</button><button class="team-section-tab ${footballState.teamPanel === 'defense' ? 'active' : ''}" data-team-panel-target="defense">Defense</button><button class="team-section-tab ${footballState.teamPanel === 'schedule' ? 'active' : ''}" data-team-panel-target="schedule">Schedule</button></div><section class="card football-team-panel">${footballState.teamPanel === 'schedule' ? footballSchedule(team) : footballRosterTable(players, footballState.teamPanel)}</section></main>`;
}

function footballPlayerSummary(player) {
  const metrics = player.role === 'QB' ? [['PassYds', 'Pass Yds'], ['PassTD', 'Pass TD'], ['CmpPct', 'Cmp%'], ['AdjYPA', 'Adj Y/A']]
    : player.role === 'Rusher' ? [['RushYds', 'Rush Yds'], ['RushTD', 'Rush TD'], ['RushYPA', 'Y/A'], ['TotalYds', 'Total Yds']]
    : player.role === 'Receiver' ? [['Rec', 'REC'], ['RecYds', 'Rec Yds'], ['RecTD', 'Rec TD'], ['RecYPR', 'Y/REC']]
    : player.role === 'Defender' ? [['Tackles', 'Tackles'], ['TFL', 'TFL'], ['Sacks', 'Sacks'], ['DefINT', 'INT']]
    : player.role === 'Kicker' ? [['FGM', 'FGM'], ['FGPct', 'FG%'], ['XPM', 'XPM'], ['KickPoints', 'Points']]
    : player.role === 'Punter' ? [['Punts', 'Punts'], ['PuntAvg', 'Average'], ['PuntLng', 'Long'], ['Inside20', 'Inside 20']]
    : [['TotalYds', 'Total Yds'], ['TotalTD', 'Total TD'], ['DefImpact', 'Def Impact'], ['ReturnAvg', 'Return Avg']];
  return metrics;
}
function footballPctColor(value) {
  if (value >= 90) return '#dc5b4b';
  if (value >= 75) return '#c77b4b';
  if (value >= 58) return '#96724f';
  if (value >= 42) return '#5C677D';
  if (value >= 25) return '#3a6ea8';
  return '#2a5080';
}
function footballRenderPlayer() {
  const player = footballPlayer(decodeURIComponent(footballState.playerKey));
  if (!player) return footballSetView('leaders');
  const team = FOOTBALL_TEAM_BY_SLUG[player.teamSlug];
  const summary = footballPlayerSummary(player);
  const percentileRows = Object.entries(player.metricPercentiles || {}).map(([metric, pct]) => `<div class="pct-row"><span class="pct-label">${footballEsc(footballMetricLabels[metric] || metric)}</span><div class="pct-bar-outer"><div class="pct-bar-track"><div class="pct-bar-fill" style="width:${pct}%;background:${footballPctColor(pct)}"></div><div class="pct-bubble" style="left:${pct}%;background:${footballPctColor(pct)}">${Math.round(pct)}</div></div></div><span class="pct-raw">${footballNum(player[metric], ['CmpPct', 'INTPct', 'FGPct', 'XPPct'].includes(metric) ? 1 : 1)}</span></div>`).join('');
  const countingKeys = ['Cmp', 'PassAtt', 'PassYds', 'PassTD', 'INT', 'PassLng', 'RushAtt', 'RushYds', 'RushTD', 'RushLng', 'Rec', 'RecYds', 'RecTD', 'RecLng', 'Sacks', 'TFL', 'Solo', 'Ast', 'Tackles', 'FF', 'FR', 'FumTD', 'DefINT', 'IntTD', 'Safety', 'KB', 'KORAtt', 'KORYds', 'KORLng', 'KORTD', 'PRAtt', 'PRYds', 'PRLng', 'PRTD', 'FGM', 'FGA', 'FGLng', 'XPM', 'XPA', 'TwoPT', 'Punts', 'PuntYds', 'PuntLng', 'Inside20'];
  const allStats = countingKeys.filter((key) => Number(player[key]) !== 0).map((key) => [key, player[key]]);
  footballEl('view-player').innerHTML = `<main class="player-wrap pitch-player-page football-player-page"><div class="football-player-hero">${footballLogo(team, 64)}<div><button class="player-team-link" data-team-slug="${footballEsc(team.slug)}">${footballEsc(team.name)}</button><h1>${footballEsc(player.name)}</h1><div class="player-meta">${footballEsc(player.grade)}${player.position ? ` &middot; ${footballEsc(player.position)}` : ''} &middot; ${footballEsc(player.role)}</div></div></div><div class="team-stat-cards football-player-summary"><div class="team-stat-card team-score-card"><div class="team-stat-card-label">Player Score</div><div class="team-stat-card-val">${player.playerScore.toFixed(1)}</div></div>${summary.map(([stat, label]) => `<div class="team-stat-card"><div class="team-stat-card-label">${footballEsc(label)}</div><div class="team-stat-card-val">${footballNum(player[stat], ['CmpPct', 'AdjYPA', 'RushYPA', 'RecYPR', 'PuntAvg', 'ReturnAvg', 'FGPct'].includes(stat) ? 1 : 0)}</div></div>`).join('')}</div><section class="football-player-layout"><div class="card pad"><div class="pct-section-title">${footballEsc(player.role)} Percentile Rankings</div><p class="football-percentile-note">Compared only with qualified ${footballEsc(player.role.toLowerCase())} players statewide. Player Score is shown above and is not itself a percentile.</p><div class="football-percentiles">${percentileRows}</div></div><div class="card pad"><div class="pct-section-title">Season Counting Stats</div><div class="counting-grid">${allStats.map(([stat, value]) => `<div class="counting-card"><div class="counting-value">${footballNum(value, Number.isInteger(value) ? 0 : 1)}</div><div class="counting-label">${footballEsc(footballMetricLabels[stat] || stat)}</div></div>`).join('')}</div></div></section></main>`;
}

function footballRenderGlobalSearch() {
  const query = footballEl('globalSearch').value.trim().toLowerCase();
  const box = footballEl('searchResults');
  if (!query) { box.classList.remove('open'); box.innerHTML = ''; return; }
  const teams = FOOTBALL_TEAMS.filter((team) => team.name.toLowerCase().includes(query)).slice(0, 5);
  const players = FOOTBALL_PLAYERS.filter((player) => player.name.toLowerCase().includes(query) || player.team.toLowerCase().includes(query)).slice(0, 8);
  box.innerHTML = [...teams.map((team) => `<button class="search-hit" data-team-slug="${footballEsc(team.slug)}">${footballEsc(team.name)}<small>Team &middot; ${footballEsc(team.record)}</small></button>`), ...players.map((player) => `<button class="search-hit" data-player-key="${encodeURIComponent(footballPlayerKey(player))}">${footballEsc(player.name)}<small>${footballEsc(player.role)} &middot; ${footballEsc(player.team)}</small></button>`)].join('') || '<div class="search-hit">No matches</div>';
  box.classList.add('open');
}

function footballBuildTeamNav() {
  const container = footballEl('teamsNavList');
  container.innerHTML = FOOTBALL_CONFERENCES.map((conference) => `<div class="nav-dropdown-label">${footballEsc(conference)}</div>${FOOTBALL_TEAMS.filter((team) => team.conference === conference).sort((a, b) => a.name.localeCompare(b.name)).map((team) => `<button class="nav-dropdown-item" data-team-slug="${footballEsc(team.slug)}">${footballEsc(team.name)}</button>`).join('')}`).join('<div class="nav-dropdown-divider"></div>');
}

function footballRender() {
  if (footballState.view === 'home') footballRenderHome();
  if (footballState.view === 'leaders') footballRenderLeaders();
  if (footballState.view === 'rankings') footballRenderRankings();
  if (footballState.view === 'scores') footballRenderScores();
  if (footballState.view === 'predictor') footballRenderPredictor();
  if (footballState.view === 'standings') footballRenderStandings();
  if (footballState.view === 'teams') footballRenderTeams();
  if (footballState.view === 'glossary') footballRenderGlossary();
  if (footballState.view === 'team') footballRenderTeam();
  if (footballState.view === 'player') footballRenderPlayer();
}

document.addEventListener('click', (event) => {
  const trigger = event.target.closest('.nav-dropdown-trigger');
  if (trigger) {
    const dropdown = trigger.closest('.nav-dropdown')?.querySelector('.nav-dropdown-menu');
    const open = dropdown?.classList.contains('open');
    footballCloseDropdowns();
    if (dropdown && !open) dropdown.classList.add('open');
    event.stopPropagation();
    return;
  }
  if (!event.target.closest('.nav-dropdown-menu')) footballCloseDropdowns();
  const nav = event.target.closest('.pitch-nav [data-view]');
  if (nav) {
    if (nav.dataset.leaderType) footballState.leaderSide = nav.dataset.leaderType === 'keepers' ? 'defense' : 'offense';
    footballCloseDropdowns();
    footballSetView(nav.dataset.view); return;
  }
  const target = event.target.closest('[data-view-target]');
  if (target) { footballSetView(target.dataset.viewTarget); return; }
  const team = event.target.closest('[data-team-slug]');
  if (team) { footballState.teamSlug = team.dataset.teamSlug; footballSetView('team'); return; }
  const player = event.target.closest('[data-player-key]');
  if (player) { footballState.playerKey = player.dataset.playerKey; footballSetView('player'); return; }
  const panel = event.target.closest('[data-team-panel-target]');
  if (panel) { footballState.teamPanel = panel.dataset.teamPanelTarget; footballRenderTeam(); return; }
  const side = event.target.closest('[data-leader-side]');
  if (side) { footballState.leaderSide = side.dataset.leaderSide; footballState.role = 'All'; footballState.leaderPage = 1; footballRenderLeaders(); return; }
  const playerSort = event.target.closest('[data-player-sort]');
  if (playerSort) { const key = playerSort.dataset.playerSort; footballState.leaderSort = { key, asc: footballState.leaderSort.key === key ? !footballState.leaderSort.asc : false }; footballRenderLeaders(); return; }
  const rankingSort = event.target.closest('[data-ranking-sort]');
  if (rankingSort) { const key = rankingSort.dataset.rankingSort; footballState.rankingSort = { key, asc: footballState.rankingSort.key === key ? !footballState.rankingSort.asc : false }; footballRenderRankings(); return; }
  const page = event.target.closest('[data-player-page]');
  if (page) { footballState.leaderPage += page.dataset.playerPage === 'next' ? 1 : -1; footballRenderLeaders(); }
});

document.addEventListener('input', (event) => {
  if (event.target.matches('[data-football-search]')) {
    footballState.search = event.target.value;
    footballState.leaderPage = 1;
    footballRender();
    const replacement = document.querySelector('[data-football-search]');
    replacement?.focus();
    replacement?.setSelectionRange(footballState.search.length, footballState.search.length);
  }
  if (event.target.matches('[data-predict-team-search]')) {
    const selected = FOOTBALL_TEAMS.find((team) => team.name.toLowerCase() === event.target.value.trim().toLowerCase());
    if (selected) {
      footballState.predictor[event.target.dataset.predictTeamSearch === 'A' ? 'teamA' : 'teamB'] = selected.slug;
      footballRenderPredictor();
    }
  }
  if (event.target.id === 'globalSearch') footballRenderGlobalSearch();
});
document.addEventListener('change', (event) => {
  if (event.target.matches('[data-football-conference]')) { footballState.conference = event.target.value; footballState.leaderPage = 1; footballRender(); }
  if (event.target.matches('[data-football-role]')) { footballState.role = event.target.value; footballState.leaderPage = 1; footballRenderLeaders(); }
  if (event.target.matches('[data-predict-venue]')) { footballState.predictor.venue = event.target.value; footballRenderPredictor(); }
  if (event.target.matches('[data-predict-team-search]')) {
    const selected = FOOTBALL_TEAMS.find((team) => team.name.toLowerCase() === event.target.value.trim().toLowerCase());
    if (!selected) return;
    footballState.predictor[event.target.dataset.predictTeamSearch === 'A' ? 'teamA' : 'teamB'] = selected.slug;
    footballRenderPredictor();
  }
});
document.addEventListener('keydown', (event) => { if (event.key === 'Escape') { footballCloseDropdowns(); closeReportProblem(); } });
document.addEventListener('click', (event) => { if (!event.target.closest('.pitch-global-search')) footballEl('searchResults')?.classList.remove('open'); });

initFootballTheme();
footballBuildTeamNav();
footballRenderHome();
