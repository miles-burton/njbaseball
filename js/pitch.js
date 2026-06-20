const $ = (id) => document.getElementById(id);
const TEAMS = PITCH_DATA.teams || [];
const SCORERS = PITCH_DATA.scorers || [];
const KEEPERS = PITCH_DATA.keepers || [];
const TEAM_BY_SLUG = Object.fromEntries(TEAMS.map((team) => [team.slug, team]));
const CONFERENCES = [...new Set(TEAMS.map((team) => team.conference))].sort();
const state = {
  view: 'home',
  teamSlug: '',
  playerKey: '',
  rankingSort: { key: 'powerScore', asc: false },
  leaderType: 'scoring',
  leaderSort: { key: 'P', asc: false },
  filters: { query: '', conference: 'All' },
};

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));
}

function pct(value) {
  return Number.isFinite(value) ? value.toFixed(3).replace(/^0/, '') : '.000';
}

function logoSrc(team) {
  if (!team) return '';
  const shared = typeof TEAM_LOGOS !== 'undefined' ? TEAM_LOGOS[team.name] : '';
  return shared || team.logo || '';
}

function logo(team) {
  const primary = logoSrc(team);
  const fallback = team?.logo && team.logo !== primary ? team.logo : '';
  return primary
    ? `<img class="team-logo" src="${esc(primary)}" alt="" ${fallback ? `onerror="this.onerror=null;this.src='${esc(fallback)}'"` : ''}>`
    : `<span class="team-logo"></span>`;
}

function setView(view, detail = '') {
  state.view = view;
  document.querySelectorAll('.view').forEach((el) => el.classList.remove('active'));
  $(`view-${view}`)?.classList.add('active');
  document.querySelectorAll('.pitch-nav button').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.view === view);
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

function playerKey(player) {
  return `${player.name}__${player.teamSlug}`;
}

function playerButton(player) {
  return `<button class="linkish" data-player-key="${encodeURIComponent(playerKey(player))}">${esc(player.name)}</button>`;
}

function renderHome() {
  const topTeams = TEAMS.slice(0, 8);
  const topScorers = sortRows(SCORERS, 'P').slice(0, 8);
  const recentGames = [...(PITCH_DATA.games || [])]
    .filter((game) => game.result && game.teamScore !== null)
    .slice(-80)
    .sort((a, b) => (Math.abs((b.teamScore ?? 0) - (b.opponentScore ?? 0)) - Math.abs((a.teamScore ?? 0) - (a.opponentScore ?? 0))))
    .slice(0, 8);
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
                <div class="home-section-title">Power Rankings</div>
                <div class="home-section-sub">Top boys soccer teams by Pitch Score</div>
              </div>
              <button class="home-section-link" data-view-target="rankings">Full Rankings →</button>
            </div>
            ${miniRanking(topTeams)}
          </div>

          <div class="home-section">
            <div class="home-section-header">
              <div>
                <div class="home-section-title">Scoring Leaders</div>
                <div class="home-section-sub">Sorted by points</div>
              </div>
              <button class="home-section-link" data-view-target="leaders">All Leaders →</button>
            </div>
          ${leaderTable(topScorers, 'scoring', false)}
        </div>
        </div>

        <div class="home-side-column">
          <div class="home-section">
            <div class="home-section-header">
              <div>
                <div class="home-section-title">Index Snapshot</div>
                <div class="home-section-sub">Current boys soccer dataset</div>
              </div>
            </div>
            <div class="grid-3">
              <div class="stat-card"><b>${TEAMS.length}</b><span>Teams</span></div>
              <div class="stat-card"><b>${SCORERS.length.toLocaleString()}</b><span>Scorers</span></div>
              <div class="stat-card"><b>${KEEPERS.length.toLocaleString()}</b><span>Keepers</span></div>
            </div>
          </div>

          <div class="home-section">
            <div class="home-section-header">
              <div>
                <div class="home-section-title">Notable Results</div>
                <div class="home-section-sub">From NJ.com schedules</div>
              </div>
            </div>
            ${gameList(recentGames)}
          </div>
        </div>
      </div>
    </div>`;
}

function miniRanking(rows) {
  return `<div class="table-wrap"><table><tbody>${rows.map((team) => `
    <tr>
      <td class="rank">#${team.rank}</td>
      <td><div class="team-cell">${logo(team)}<div>${teamButton(team)}<div class="muted">${esc(team.conference)} · ${esc(team.record)}</div></div></div></td>
      <td class="num">${team.powerScore.toFixed(1)}</td>
    </tr>`).join('')}</tbody></table></div>`;
}

function gameList(rows, ownerTeam = null) {
  if (!rows.length) return `<div class="card pad muted">No completed games found in the current data.</div>`;
  return `<div class="table-wrap"><table><tbody>${rows.map((game) => {
    const team = TEAM_BY_SLUG[game.teamSlug] || ownerTeam;
    const opp = TEAM_BY_SLUG[game.opponentSlug];
    return `<tr>
      <td>${esc(game.date)}</td>
      <td>${teamButton(team || { name: game.team, slug: game.teamSlug })}<div class="muted">${game.site || 'vs'} ${opp ? teamButton(opp) : esc(game.opponent)}</div></td>
      <td class="num ${game.result === 'W' ? 'score-good' : game.result === 'L' ? 'score-bad' : ''}">${esc(game.result)} ${game.teamScore}-${game.opponentScore}</td>
    </tr>`;
  }).join('')}</tbody></table></div>`;
}

function renderRankings() {
  const rows = sortRows(filteredTeams(), state.rankingSort.key, state.rankingSort.asc);
  $('view-rankings').innerHTML = `
    <div class="page-banner">
      <div class="page-banner-inner">
        <div>
          <div class="page-title">Power <span>Rankings</span></div>
          <div class="page-meta">New Jersey High School Boys Soccer <span class="page-meta-dot"></span> ${esc(PITCH_DATA.season)} Season <span class="page-meta-dot"></span> Pitch Score</div>
        </div>
      </div>
    </div>
    <div class="leaderboard-wrap">
      ${toolbar('rankings')}
      <div class="card table-wrap">${rankingTable(rows, true)}</div>
    </div>`;
}

function toolbar(kind) {
  return `<div class="toolbar">
    <input data-filter-query type="search" placeholder="Search teams..." value="${esc(state.filters.query)}">
    <select data-filter-conference>${conferenceOptions(state.filters.conference)}</select>
  </div>`;
}

function rankingTable(rows, sortable) {
  const head = (label, key, cls = '') => `<th class="${sortable ? 'sortable ' : ''}${cls}" ${sortable ? `data-rank-sort="${key}"` : ''}>${label}</th>`;
  return `<table>
    <thead><tr>${head('#','rank')}${head('Team','name')}${head('Conf','conference')}${head('Rec','record')}${head('Pct','winPct','num')}${head('GF','gf','num')}${head('GA','ga','num')}${head('GD','gd','num')}${head('SOS','sos','num')}${head('Pitch','powerScore','num')}</tr></thead>
    <tbody>${rows.map((team) => `<tr>
      <td class="rank">#${team.rank}</td>
      <td><div class="team-cell">${logo(team)}<div>${teamButton(team)}<div class="muted">${esc(team.division)}</div></div></div></td>
      <td>${esc(team.conference)}</td><td>${esc(team.record)}</td>
      <td class="num">${pct(team.winPct)}</td><td class="num">${team.gf}</td><td class="num">${team.ga}</td><td class="num">${team.gd}</td>
      <td class="num">${team.sos.toFixed(1)}</td><td class="num"><strong>${team.powerScore.toFixed(1)}</strong></td>
    </tr>`).join('')}</tbody></table>`;
}

function renderLeaders() {
  const isScoring = state.leaderType === 'scoring';
  let rows = isScoring ? SCORERS : KEEPERS;
  const q = state.filters.query.toLowerCase();
  rows = rows.filter((player) => {
    const matchesQ = !q || player.name.toLowerCase().includes(q) || player.team.toLowerCase().includes(q);
    const matchesConf = state.filters.conference === 'All' || player.conference === state.filters.conference;
    return matchesQ && matchesConf;
  });
  rows = sortRows(rows, state.leaderSort.key, state.leaderSort.asc).slice(0, 500);
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
      <div class="toolbar">
        <button class="btn ${isScoring ? 'primary' : ''}" data-leader-type="scoring">Scoring</button>
        <button class="btn ${!isScoring ? 'primary' : ''}" data-leader-type="keepers">Goalkeepers</button>
        <input data-filter-query type="search" placeholder="Search players or teams..." value="${esc(state.filters.query)}">
        <select data-filter-conference>${conferenceOptions(state.filters.conference)}</select>
      </div>
      <div class="card">${leaderTable(rows, state.leaderType, true)}</div>
    </div>`;
}

function leaderTable(rows, type, sortable) {
  const cols = type === 'keepers'
    ? [['Saves','Saves'], ['GP','GP']]
    : [['G','G'], ['A','A'], ['P','P']];
  const sort = (key) => sortable ? `data-leader-sort="${key}" class="sortable num"` : 'class="num"';
  return `<div class="table-wrap"><table>
    <thead><tr><th>Player</th><th>Team</th><th>Class</th>${cols.map(([label,key]) => `<th ${sort(key)}>${label}</th>`).join('')}</tr></thead>
    <tbody>${rows.map((player) => {
      const team = TEAM_BY_SLUG[player.teamSlug];
      return `<tr>
        <td>${playerButton(player)}</td>
        <td>${team ? teamButton(team) : esc(player.team)}<div class="muted">${esc(player.conference)}</div></td>
        <td>${esc(player.grade || '')}</td>
        ${cols.map(([, key]) => `<td class="num"><strong>${player[key] ?? 0}</strong></td>`).join('')}
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
    <div class="team-grid">${rows.map((team) => `<button class="team-tile" data-team-slug="${esc(team.slug)}">
      ${logo(team)}<span><strong>${esc(team.name)}</strong><small>${esc(team.conference)} · ${esc(team.record)} · Pitch ${team.powerScore.toFixed(1)}</small></span>
    </button>`).join('')}</div>
  </div>`;
}

function renderTeam() {
  const team = TEAM_BY_SLUG[state.teamSlug];
  if (!team) return;
  const scorers = sortRows(team.scorers || [], 'P').slice(0, 15);
  const keepers = sortRows(team.keepers || [], 'Saves').slice(0, 8);
  $('view-team').innerHTML = `<div class="leaderboard-wrap">
    <button class="btn" data-view-target="teams" style="margin-bottom:14px">Back to Teams</button>
    <div class="card pad">
      <div class="team-hero">${logo(team)}<div>
        <div class="eyebrow">${esc(team.conference)} · ${esc(team.division)}</div>
        <h2>${esc(team.name)}</h2>
        <div class="team-hero-meta">
          <span class="pill">Record ${esc(team.record)}</span><span class="pill">Division ${esc(team.divisionRecord)}</span><span class="pill">Rank #${team.rank}</span><span class="pill">Pitch ${team.powerScore.toFixed(1)}</span><span class="pill">SOS ${team.sos.toFixed(1)}</span>
        </div>
      </div></div>
      <div class="grid-3">
        <div class="stat-card"><b>${team.gf}</b><span>Goals For</span></div>
        <div class="stat-card"><b>${team.ga}</b><span>Goals Allowed</span></div>
        <div class="stat-card"><b>${team.gd}</b><span>Goal Diff</span></div>
      </div>
    </div>
    <div class="subgrid">
      <div class="card"><div class="card-title">Schedule & Results <span>${team.schedule?.length || 0} games</span></div>${gameList(team.schedule || [], team)}</div>
      <div>
        <div class="card"><div class="card-title">Scoring Leaders</div>${leaderTable(scorers, 'scoring', false)}</div>
        <div style="height:20px"></div>
        <div class="card"><div class="card-title">Goalkeepers</div>${leaderTable(keepers, 'keepers', false)}</div>
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
    <div class="card pad">
      <div class="team-hero">${logo(team)}<div>
        <div class="eyebrow">${esc(player.grade || 'Player')} · ${esc(player.conference)}</div>
        <h2>${esc(player.name)}</h2>
        <div class="team-hero-meta">${team ? `<span class="pill">${teamButton(team)}</span>` : ''}<span class="pill">${esc(player.division)}</span></div>
      </div></div>
      <div class="grid-3">
        <div class="stat-card"><b>${scoring?.G ?? 0}</b><span>Goals</span></div>
        <div class="stat-card"><b>${scoring?.A ?? 0}</b><span>Assists</span></div>
        <div class="stat-card"><b>${scoring?.P ?? 0}</b><span>Points</span></div>
        <div class="stat-card"><b>${keeping?.Saves ?? 0}</b><span>Saves</span></div>
        <div class="stat-card"><b>${keeping?.GP ?? 0}</b><span>Keeper GP</span></div>
        <div class="stat-card"><b>${team?.rank ? `#${team.rank}` : '-'}</b><span>Team Rank</span></div>
      </div>
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
  if (state.view === 'standings') renderStandings();
  if (state.view === 'teams') renderTeams();
  if (state.view === 'team') renderTeam();
  if (state.view === 'player') renderPlayer();
}

document.querySelectorAll('.pitch-nav button').forEach((btn) => {
  btn.addEventListener('click', () => setView(btn.dataset.view));
});

document.addEventListener('click', (event) => {
  const navTarget = event.target.closest('.pitch-nav [data-view]');
  if (navTarget) {
    setView(navTarget.dataset.view);
    return;
  }

  const viewTarget = event.target.closest('[data-view-target]');
  if (viewTarget) {
    setView(viewTarget.dataset.viewTarget);
    return;
  }

  const teamTarget = event.target.closest('[data-team-slug]');
  if (teamTarget) {
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
    state.rankingSort = { key, asc: state.rankingSort.key === key ? !state.rankingSort.asc : false };
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
    render();
  }
});

document.addEventListener('input', (event) => {
  if (event.target.matches('[data-filter-query]')) {
    state.filters.query = event.target.value;
    render();
  }
});

document.addEventListener('change', (event) => {
  if (event.target.matches('[data-filter-conference]')) {
    state.filters.conference = event.target.value;
    render();
  }
});

$('globalSearch').addEventListener('input', renderGlobalSearch);
document.addEventListener('click', (event) => {
  if (!event.target.closest('.pitch-global-search')) $('searchResults').classList.remove('open');
});

initTheme();
renderHome();
