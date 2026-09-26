// Motore di punteggio del padel: porting 1:1 di PadelKit/MatchEngine.swift.
// Funzioni pure, nessuna dipendenza dal DOM: testato con `node --test`.

export const US = 'us';
export const THEM = 'them';
export const opp = (t) => (t === US ? THEM : US);
export const teamLabel = (t) => (t === US ? 'Noi' : 'Loro');

export const GAMES_PER_SET = 6;
export const TIEBREAK_TARGET = 7;
export const SUPER_TIEBREAK_TARGET = 10;
export const SETS_TO_WIN = 2;

export const DEUCE_LABELS = { goldenPoint: "Punto d'oro", advantages: 'Vantaggi' };
export const FORMAT_LABELS = { bestOfThree: 'Al meglio dei 3 set', twoSetsSuperTiebreak: '2 set + super tie-break' };

export function defaultRules() {
  return { deuceRule: 'goldenPoint', format: 'bestOfThree', firstServer: US, indoor: false };
}

export function initialState(server) {
  return {
    completedSets: [], gamesUs: 0, gamesThem: 0, pointsUs: 0, pointsThem: 0,
    mode: 'regular', server, tiebreakFirstServer: null, winner: null,
  };
}

export function newMatch(rules) {
  return { rules: { ...rules }, events: [], state: initialState(rules.firstServer) };
}

// ---- Set -------------------------------------------------------------------

export function setWinner(s) {
  if (s.us > s.them) return US;
  if (s.them > s.us) return THEM;
  return null;
}

export function setDisplay(s) {
  if (s.isSuperTiebreak && s.tiebreakUs != null) return `[${s.tiebreakUs}-${s.tiebreakThem}]`;
  if (s.tiebreakUs != null && s.tiebreakThem != null) return `${s.us}-${s.them} (${s.tiebreakUs}-${s.tiebreakThem})`;
  return `${s.us}-${s.them}`;
}

export function setCompact(s) {
  if (s.isSuperTiebreak && s.tiebreakUs != null) return `[${s.tiebreakUs}-${s.tiebreakThem}]`;
  return `${s.us}-${s.them}`;
}

export const setsWon = (sets) => sets.filter((s) => setWinner(s) === US).length;
export const setsLost = (sets) => sets.filter((s) => setWinner(s) === THEM).length;
export function winnerBySets(sets) {
  const w = setsWon(sets), l = setsLost(sets);
  return w > l ? US : l > w ? THEM : null;
}

// ---- Azioni ----------------------------------------------------------------

const isPoint = (e) => e.type === 'point';

/** Restituisce 'ignored' | 'point' | 'game' | 'set' | 'match'. */
export function point(match, team) {
  if (match.state.winner) return 'ignored';
  const ev = { type: 'point', team };
  match.events.push(ev);
  return apply(ev, match.state, match.rules);
}

export function setServer(match, team) {
  if (match.state.server === team || match.state.winner) return;
  const ev = { type: 'setServer', team };
  match.events.push(ev);
  apply(ev, match.state, match.rules);
}

export const canUndo = (match) => match.events.some(isPoint);

/** Annulla l'ultimo punto (e le correzioni di servizio successive). */
export function undoLastPoint(match) {
  let idx = -1;
  for (let i = match.events.length - 1; i >= 0; i--) if (isPoint(match.events[i])) { idx = i; break; }
  if (idx < 0) return;
  match.events.splice(idx);
  match.state = replay(match.events, match.rules);
}

export function replay(events, rules) {
  const state = initialState(rules.firstServer);
  for (const e of events) apply(e, state, rules);
  return state;
}

// ---- Visualizzazione -------------------------------------------------------

const pts = (s, t) => (t === US ? s.pointsUs : s.pointsThem);
export const games = (s, t) => (t === US ? s.gamesUs : s.gamesThem);
export const sets = (s, t) => (t === US ? setsWon(s.completedSets) : setsLost(s.completedSets));

export function pointLabel(match, team) {
  const s = match.state;
  const mine = pts(s, team), theirs = pts(s, opp(team));
  if (s.mode !== 'regular') return String(mine);
  if (mine >= 3 && theirs >= 3) return mine > theirs ? 'AD' : '40';
  return ['0', '15', '30', '40'][Math.min(mine, 3)];
}

export function statusLabel(match) {
  const s = match.state;
  if (s.winner) return s.winner === US ? 'Vittoria' : 'Sconfitta';
  if (s.mode === 'tiebreak') return 'Tie-break';
  if (s.mode === 'superTiebreak') return 'Super tie-break';
  if (s.pointsUs >= 3 && s.pointsThem >= 3) {
    if (match.rules.deuceRule === 'goldenPoint') return "Punto d'oro";
    if (s.pointsUs === s.pointsThem) return 'Parità';
    return `Vantaggio ${s.pointsUs > s.pointsThem ? 'Noi' : 'Loro'}`;
  }
  return null;
}

// ---- Regole ----------------------------------------------------------------

function apply(ev, s, rules) {
  if (ev.type === 'setServer') {
    s.server = ev.team;
    if (s.mode !== 'regular' && s.pointsUs + s.pointsThem === 0) s.tiebreakFirstServer = ev.team;
    return 'point';
  }
  if (s.winner) return 'ignored';
  if (ev.team === US) s.pointsUs++; else s.pointsThem++;
  return s.mode === 'regular' ? regularPoint(s, rules) : tiebreakPoint(s, rules);
}

function regularPoint(s, rules) {
  const us = s.pointsUs, them = s.pointsThem;
  const leader = us > them ? US : THEM;
  const high = Math.max(us, them), low = Math.min(us, them);
  const golden = rules.deuceRule === 'goldenPoint';
  if (!(high >= 4 && (high - low >= 2 || golden))) return 'point';

  if (leader === US) s.gamesUs++; else s.gamesThem++;
  s.pointsUs = 0; s.pointsThem = 0;
  s.server = opp(s.server);

  const gu = s.gamesUs, gt = s.gamesThem;
  if (Math.max(gu, gt) >= GAMES_PER_SET && Math.abs(gu - gt) >= 2) {
    return closeSet({ us: gu, them: gt, isSuperTiebreak: false }, s, rules);
  }
  if (gu === GAMES_PER_SET && gt === GAMES_PER_SET) {
    s.mode = 'tiebreak';
    s.tiebreakFirstServer = s.server;
  }
  return 'game';
}

function tiebreakPoint(s, rules) {
  const us = s.pointsUs, them = s.pointsThem;
  const target = s.mode === 'superTiebreak' ? SUPER_TIEBREAK_TARGET : TIEBREAK_TARGET;
  if (Math.max(us, them) >= target && Math.abs(us - them) >= 2) {
    const first = s.tiebreakFirstServer ?? s.server;
    const weWon = us > them;
    const set = s.mode === 'superTiebreak'
      ? { us: weWon ? 1 : 0, them: weWon ? 0 : 1, tiebreakUs: us, tiebreakThem: them, isSuperTiebreak: true }
      : { us: s.gamesUs + (weWon ? 1 : 0), them: s.gamesThem + (weWon ? 0 : 1), tiebreakUs: us, tiebreakThem: them, isSuperTiebreak: false };
    // Il primo game dopo il tie-break lo serve chi ha risposto per primo.
    s.server = opp(first);
    return closeSet(set, s, rules);
  }
  // Primo punto al primo battitore, poi si cambia ogni 2.
  if ((us + them) % 2 === 1) s.server = opp(s.server);
  return 'point';
}

function closeSet(set, s, rules) {
  s.completedSets.push(set);
  s.gamesUs = 0; s.gamesThem = 0; s.pointsUs = 0; s.pointsThem = 0;
  s.mode = 'regular';
  s.tiebreakFirstServer = null;
  if (setsWon(s.completedSets) === SETS_TO_WIN) { s.winner = US; return 'match'; }
  if (setsLost(s.completedSets) === SETS_TO_WIN) { s.winner = THEM; return 'match'; }
  if (rules.format === 'twoSetsSuperTiebreak' && s.completedSets.length === 2) {
    s.mode = 'superTiebreak';
    s.tiebreakFirstServer = s.server;
  }
  return 'set';
}

// ---- Statistiche (stesse regole di PadelKit/Statistics.swift) --------------

export function periodStart(period, now = new Date()) {
  const d = new Date(now);
  if (period === 'last12Months') { d.setMonth(d.getMonth() - 12); return d; }
  if (period === 'last3Months') { d.setMonth(d.getMonth() - 3); return d; }
  return null;
}

export function statistics(allMatches, names, period, now = new Date()) {
  const start = periodStart(period, now);
  const matches = allMatches
    .filter((m) => winnerBySets(m.sets) && (!start || new Date(m.date) >= start))
    .sort((a, b) => new Date(a.date) - new Date(b.date));
  const r = { played: 0, won: 0, lost: 0, setsWon: 0, setsLost: 0, duration: 0, calories: 0,
    streak: null, months: [], trend: [], partners: [], opponents: [] };
  const months = new Map(), partners = new Map(), opponents = new Map();
  const name = (id) => names[id] ?? 'Giocatore eliminato';
  const bump = (map, id, win) => {
    const x = map.get(id) ?? { id, name: name(id), won: 0, lost: 0 };
    if (win) x.won++; else x.lost++;
    map.set(id, x);
  };
  for (const m of matches) {
    const win = winnerBySets(m.sets) === US;
    r.played++; if (win) r.won++; else r.lost++;
    r.setsWon += setsWon(m.sets); r.setsLost += setsLost(m.sets);
    r.duration += m.duration || 0; r.calories += m.activeCalories || 0;
    const d = new Date(m.date);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    const b = months.get(key) ?? { key, won: 0, lost: 0 };
    if (win) b.won++; else b.lost++;
    months.set(key, b);
    r.trend.push({ date: m.date, pct: (r.won / r.played) * 100 });
    if (m.partnerID) bump(partners, m.partnerID, win);
    for (const o of new Set([m.opponent1ID, m.opponent2ID].filter(Boolean))) bump(opponents, o, win);
  }
  const pct = (x) => (x.won + x.lost ? (x.won / (x.won + x.lost)) * 100 : 0);
  r.months = [...months.values()].sort((a, b) => a.key.localeCompare(b.key));
  r.partners = [...partners.values()].map((x) => ({ ...x, pct: pct(x) }))
    .sort((a, b) => b.pct - a.pct || (b.won + b.lost) - (a.won + a.lost) || a.name.localeCompare(b.name));
  r.opponents = [...opponents.values()].map((x) => ({ ...x, pct: pct(x) }))
    .sort((a, b) => (b.won + b.lost) - (a.won + a.lost) || a.name.localeCompare(b.name));
  r.bestPartner = r.partners.filter((p) => p.won + p.lost >= 3)
    .sort((a, b) => b.pct - a.pct || (b.won + b.lost) - (a.won + a.lost))[0] ?? null;
  r.winPct = r.played ? (r.won / r.played) * 100 : 0;
  if (matches.length) {
    const last = winnerBySets(matches[matches.length - 1].sets);
    let n = 0;
    for (let i = matches.length - 1; i >= 0 && winnerBySets(matches[i].sets) === last; i--) n++;
    r.streak = { type: last === US ? 'wins' : 'losses', count: n };
  }
  return r;
}

// ---- Backup: stesso formato JSON dell'app nativa (BackupFile) ---------------

/** ISO8601 senza millisecondi: e' quello che si aspetta il JSONDecoder di Swift. */
export const isoDate = (d) => new Date(d).toISOString().replace(/\.\d{3}Z$/, 'Z');

export function buildBackup(players, matches, now = new Date()) {
  const clean = (o) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== null && v !== undefined));
  return {
    version: 1,
    exportedAt: isoDate(now),
    players: players.map((p) => ({ id: p.id, name: p.name, createdAt: isoDate(p.createdAt) })),
    matches: matches.map((m) => clean({
      id: m.id, date: isoDate(m.date), club: m.club ?? '', court: m.court ?? '',
      partnerID: m.partnerID, opponent1ID: m.opponent1ID, opponent2ID: m.opponent2ID,
      rules: m.rules, sets: m.sets.map((s) => clean({ ...s, isSuperTiebreak: !!s.isSuperTiebreak })),
      duration: m.duration ?? 0, activeCalories: m.activeCalories,
      averageHeartRate: m.averageHeartRate, maxHeartRate: m.maxHeartRate,
      notes: m.notes ?? '', source: m.source ?? 'manual',
    })),
  };
}

/** Unisce un backup: aggiunge solo gli UUID nuovi. */
export function mergeBackup(file, players, matches) {
  if (!file || typeof file.version !== 'number' || !Array.isArray(file.players) || !Array.isArray(file.matches)) {
    throw new Error('File non valido: non è un backup di Padel.');
  }
  if (file.version > 1) throw new Error(`Backup creato da una versione più recente (formato ${file.version}).`);
  const pIds = new Set(players.map((p) => p.id.toUpperCase()));
  const mIds = new Set(matches.map((m) => m.id.toUpperCase()));
  const newPlayers = file.players.filter((p) => !pIds.has(p.id.toUpperCase()))
    .map((p) => ({ ...p, id: p.id.toUpperCase() }));
  const up = (x) => (x ? x.toUpperCase() : undefined);
  const newMatches = file.matches.filter((m) => !mIds.has(m.id.toUpperCase()))
    .map((m) => ({ ...m, id: m.id.toUpperCase(), partnerID: up(m.partnerID), opponent1ID: up(m.opponent1ID), opponent2ID: up(m.opponent2ID) }));
  return { players: [...players, ...newPlayers], matches: [...matches, ...newMatches], added: { players: newPlayers.length, matches: newMatches.length } };
}

export const newId = () => crypto.randomUUID().toUpperCase();
