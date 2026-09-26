import * as E from './engine.js';
import { parseScore, parseWatchPaste } from './quick.js';

const US = E.US, THEM = E.THEM;
const $ = (sel) => document.querySelector(sel);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// ---- Dati ------------------------------------------------------------------

const KEY = 'padel.v1', LIVE = 'padel.live.v1', SETUP = 'padel.setup.v1';
const load = (k, fallback) => { try { return JSON.parse(localStorage.getItem(k)) ?? fallback; } catch { return fallback; } };
const save = (k, v) => localStorage.setItem(k, JSON.stringify(v));

let db = load(KEY, { players: [], matches: [] });
const persist = () => save(KEY, db);
const names = () => Object.fromEntries(db.players.map((p) => [p.id, p.name]));
const playerName = (id) => (id ? names()[id] ?? 'Giocatore eliminato' : '');

function playerIdFor(name) {
  const n = name.trim();
  if (!n) return undefined;
  const found = db.players.find((p) => p.name.localeCompare(n, 'it', { sensitivity: 'base' }) === 0);
  if (found) return found.id;
  const p = { id: E.newId(), name: n, createdAt: new Date().toISOString() };
  db.players.push(p);
  return p.id;
}

// Chiede al browser di non cancellare i dati (Safari lo rispetta per le app sulla Home).
navigator.storage?.persist?.();

// ---- Formattazione ---------------------------------------------------------

const fmtDate = (d) => new Date(d).toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
const fmtClock = (sec) => {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = sec % 60;
  const pad = (x) => String(x).padStart(2, '0');
  return h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
};
const fmtLong = (sec) => {
  const min = Math.round((sec || 0) / 60), h = Math.floor(min / 60), m = min % 60;
  return h ? (m ? `${h} h ${m} min` : `${h} h`) : `${m} min`;
};
const badge = (sets) => {
  const r = E.winnerBySets(sets);
  return `<span class="badge ${r === US ? 'win' : r === THEM ? 'loss' : ''}">${r === US ? 'V' : r === THEM ? 'S' : '–'}</span>`;
};

// ---- Router ----------------------------------------------------------------

const routes = { partite: renderList, gioca: renderPlay, statistiche: renderStats, impostazioni: renderSettings, partita: renderEdit, veloce: renderQuick };

function route() {
  stopTicker();
  const [name, arg] = location.hash.replace(/^#\/?/, '').split('/');
  const view = routes[name] ? name : 'partite';
  document.querySelectorAll('nav a').forEach((a) => a.classList.toggle('active', a.dataset.view === (view === 'partita' || view === 'veloce' ? 'partite' : view)));
  document.body.classList.toggle('playing', view === 'gioca' && !!load(LIVE, null));
  routes[view](arg);
  window.scrollTo(0, 0);
}
window.addEventListener('hashchange', route);

// ---- Storico ---------------------------------------------------------------

function renderList() {
  const matches = [...db.matches].sort((a, b) => new Date(b.date) - new Date(a.date));
  $('#main').innerHTML = `
    <header class="bar"><h1>Partite</h1><a class="btn small" href="#/veloce">⚡ Veloce</a><a class="btn small ghost" href="#/partita/nuova">+ Nuova</a></header>
    ${matches.length === 0 ? `<p class="empty">Nessuna partita. Tocca <b>Gioca</b> per il segnapunti oppure <b>+ Nuova</b> per inserirla a mano.</p>` : ''}
    ${matches.map(matchCard).join('')}`;
}

function matchCard(m) {
  const r = E.winnerBySets(m.sets);
  const val = (s, t) => (s.isSuperTiebreak ? (t === US ? s.tiebreakUs : s.tiebreakThem) ?? 0 : (t === US ? s.us : s.them));
  const row = (t, who) => `
    <div class="mrow ${r === t ? 'winner' : ''}"><span class="cup">${r === t ? '🏆' : ''}</span>
      <span class="who">${esc(who)}</span>
      ${m.sets.map((s) => `<b class="${E.setWinner(s) === t ? 'w' : ''}">${val(s, t)}</b>`).join('')}</div>`;
  const opps = [m.opponent1ID, m.opponent2ID].filter(Boolean).map(playerName);
  const d = new Date(m.date);
  return `<a class="mcard" href="#/partita/${m.id}">
    <div class="mhead"><span class="tag">PARTITA</span><span class="grow"></span>
      <span>📅 ${d.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit', year: 'numeric' })}</span>
      ${m.duration ? `<span>⏱ ${Math.round(m.duration / 60)}′</span>` : ''}</div>
    ${row(US, m.partnerID ? `Noi · ${playerName(m.partnerID)}` : 'Noi')}
    ${row(THEM, opps.length ? opps.join(' e ') : 'Avversari')}
    ${m.club ? `<div class="muted small">${esc(m.club)}${m.court ? ' · ' + esc(m.court) : ''}</div>` : ''}
  </a>`;
}

// ---- Modifica / inserimento ------------------------------------------------

function renderEdit(id) {
  const isNew = id === 'nuova' || !id;
  const m = isNew
    ? { id: E.newId(), date: new Date().toISOString(), club: '', court: '', rules: E.defaultRules(), sets: [{ us: 0, them: 0 }], duration: 5400, notes: '', source: 'manual' }
    : structuredClone(db.matches.find((x) => x.id === id));
  if (!m) { location.hash = '#/partite'; return; }
  const local = new Date(new Date(m.date).getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const opt = (map, sel) => Object.entries(map).map(([k, v]) => `<option value="${k}" ${k === sel ? 'selected' : ''}>${esc(v)}</option>`).join('');

  const draw = () => {
    $('#main').innerHTML = `
      <header class="bar"><a class="btn small ghost" href="#/partite">Annulla</a><h1>${isNew ? 'Nuova partita' : 'Partita'}</h1><button class="btn small" id="save">Salva</button></header>
      <form class="form" id="f" autocomplete="off">
        <fieldset><legend>Partita</legend>
          <label>Data <input type="datetime-local" name="date" value="${local}"></label>
          <label>Circolo <input name="club" value="${esc(m.club)}"></label>
          <label>Campo <input name="court" value="${esc(m.court)}"></label>
          <label class="row">Campo coperto <input type="checkbox" name="indoor" ${m.rules.indoor ? 'checked' : ''}></label>
        </fieldset>
        <fieldset><legend>Giocatori</legend>
          <label>Compagno <input name="partner" list="players" value="${esc(playerName(m.partnerID))}"></label>
          <label>Avversario 1 <input name="opp1" list="players" value="${esc(playerName(m.opponent1ID))}"></label>
          <label>Avversario 2 <input name="opp2" list="players" value="${esc(playerName(m.opponent2ID))}"></label>
          <datalist id="players">${db.players.map((p) => `<option value="${esc(p.name)}">`).join('')}</datalist>
          <p class="muted small">Scrivi un nome nuovo per aggiungerlo alla rubrica.</p>
        </fieldset>
        <fieldset><legend>Regole</legend>
          <label>Sul 40-40 <select name="deuce">${opt(E.DEUCE_LABELS, m.rules.deuceRule)}</select></label>
          <label>Formato <select name="format">${opt(E.FORMAT_LABELS, m.rules.format)}</select></label>
          <label>Primo servizio <select name="server">${opt({ us: 'Noi', them: 'Loro' }, m.rules.firstServer)}</select></label>
        </fieldset>
        <fieldset><legend>Set</legend>
          ${m.sets.map((s, i) => `
            <div class="setrow" data-i="${i}">
              <b>${s.isSuperTiebreak ? 'Super TB' : 'Set ' + (i + 1)}</b>
              ${s.isSuperTiebreak
                ? `<input type="number" inputmode="numeric" min="0" max="40" data-k="tiebreakUs" value="${s.tiebreakUs ?? 0}"> – <input type="number" inputmode="numeric" min="0" max="40" data-k="tiebreakThem" value="${s.tiebreakThem ?? 0}">`
                : `<input type="number" inputmode="numeric" min="0" max="7" data-k="us" value="${s.us}"> – <input type="number" inputmode="numeric" min="0" max="7" data-k="them" value="${s.them}">
                   ${(s.us === 7 && s.them === 6) || (s.us === 6 && s.them === 7) ? `<span class="muted small">TB</span> <input type="number" inputmode="numeric" min="0" max="40" data-k="tiebreakUs" value="${s.tiebreakUs ?? ''}"> – <input type="number" inputmode="numeric" min="0" max="40" data-k="tiebreakThem" value="${s.tiebreakThem ?? ''}">` : ''}`}
              <button type="button" class="link danger" data-del="${i}">✕</button>
            </div>`).join('')}
          ${m.sets.length < 3 ? `<button type="button" class="btn small ghost" id="addset">+ Set</button>` : ''}
          ${m.sets.length === 2 && m.rules.format === 'twoSetsSuperTiebreak' ? `<button type="button" class="btn small ghost" id="addstb">+ Super tie-break</button>` : ''}
          <p class="muted small" id="result"></p>
        </fieldset>
        <fieldset><legend>Durata e note</legend>
          <label>Durata (minuti) <input type="number" inputmode="numeric" min="0" max="360" name="minutes" value="${Math.round((m.duration || 0) / 60)}"></label>
          <label>Note <textarea name="notes" rows="3">${esc(m.notes)}</textarea></label>
        </fieldset>
        ${m.activeCalories ? `<p class="muted">Calorie ${Math.round(m.activeCalories)} kcal${m.averageHeartRate ? ` · FC media ${Math.round(m.averageHeartRate)}` : ''}${m.maxHeartRate ? ` · max ${Math.round(m.maxHeartRate)}` : ''}</p>` : ''}
        ${isNew ? '' : `<button type="button" class="btn danger wide" id="delete">Elimina partita</button>`}
      </form>`;
    showResult();

    const f = $('#f');
    f.addEventListener('input', (e) => {
      const row = e.target.closest('.setrow');
      if (row) {
        const s = m.sets[+row.dataset.i];
        const v = e.target.value === '' ? undefined : Math.max(0, parseInt(e.target.value, 10) || 0);
        s[e.target.dataset.k] = v;
        if (s.isSuperTiebreak) { s.us = (s.tiebreakUs ?? 0) > (s.tiebreakThem ?? 0) ? 1 : 0; s.them = (s.tiebreakThem ?? 0) > (s.tiebreakUs ?? 0) ? 1 : 0; }
        s.us ??= 0; s.them ??= 0;
        showResult();
      }
    });
    f.addEventListener('change', (e) => {
      readForm();
      // Ridisegna quando cambia la presenza del tie-break o il formato.
      if (e.target.closest('.setrow') || e.target.name === 'format') draw();
    });
    f.querySelectorAll('[data-del]').forEach((b) => b.onclick = () => { readForm(); m.sets.splice(+b.dataset.del, 1); draw(); });
    $('#addset')?.addEventListener('click', () => { readForm(); m.sets.push({ us: 0, them: 0 }); draw(); });
    $('#addstb')?.addEventListener('click', () => { readForm(); m.sets.push({ us: 0, them: 0, tiebreakUs: 0, tiebreakThem: 0, isSuperTiebreak: true }); draw(); });
    $('#delete')?.addEventListener('click', () => {
      if (!confirm('Eliminare questa partita?')) return;
      db.matches = db.matches.filter((x) => x.id !== m.id); persist(); location.hash = '#/partite';
    });
    $('#save').onclick = () => {
      readForm(true);
      for (const s of m.sets) {
        const tb = (s.us === 7 && s.them === 6) || (s.us === 6 && s.them === 7);
        if (!s.isSuperTiebreak && !tb) { delete s.tiebreakUs; delete s.tiebreakThem; }
      }
      const i = db.matches.findIndex((x) => x.id === m.id);
      if (i >= 0) db.matches[i] = m; else db.matches.push(m);
      persist();
      location.hash = '#/partite';
    };
  };

  const readForm = (withPlayers = false) => {
    const f = $('#f'); if (!f) return;
    const d = new FormData(f);
    if (d.get('date')) m.date = new Date(d.get('date')).toISOString();
    m.club = d.get('club').trim(); m.court = d.get('court').trim();
    m.rules = { deuceRule: d.get('deuce'), format: d.get('format'), firstServer: d.get('server'), indoor: !!d.get('indoor') };
    m.duration = (parseInt(d.get('minutes'), 10) || 0) * 60;
    m.notes = d.get('notes');
    if (withPlayers) {
      m.partnerID = playerIdFor(d.get('partner'));
      m.opponent1ID = playerIdFor(d.get('opp1'));
      m.opponent2ID = playerIdFor(d.get('opp2'));
    }
  };

  const showResult = () => {
    const r = E.winnerBySets(m.sets), w = E.setsWon(m.sets), l = E.setsLost(m.sets);
    $('#result').textContent = r === US ? `Risultato: vittoria ${w}-${l}` : r === THEM ? `Risultato: sconfitta ${w}-${l}` : 'Risultato: nessun vincitore (set pari)';
  };

  draw();
}

// ---- Aggiungi veloce --------------------------------------------------------
// Per chi segna i punti con un'altra app sul Watch: punteggio in una riga,
// durata e battito incollati dal Comando rapido di fine allenamento.

/** Giocatori piu' frequenti in un ruolo, dal piu' ricorrente. */
function frequent(keys, limit = 4) {
  const count = new Map();
  for (const m of db.matches) for (const k of keys) if (m[k]) count.set(m[k], (count.get(m[k]) || 0) + 1);
  return [...count.entries()].sort((a, b) => b[1] - a[1]).map(([id]) => playerName(id)).filter((n) => n && n !== 'Giocatore eliminato').slice(0, limit);
}

function renderQuick() {
  const last = [...db.matches].sort((a, b) => new Date(b.date) - new Date(a.date))[0];
  const clubs = [...new Set(db.matches.map((m) => m.club).filter(Boolean))];
  const d = { date: new Date(), minutes: '', calories: '', avg: '', max: '' };
  const local = (t) => new Date(t - new Date(t).getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  const chips = (field, names) => names.length
    ? `<div class="chips">${names.map((n) => `<button type="button" class="chip-btn" data-fill="${field}" data-name="${esc(n)}">${esc(n)}</button>`).join('')}</div>` : '';

  $('#main').innerHTML = `
    <header class="bar"><a class="btn small ghost" href="#/partite">Annulla</a><h1>Aggiungi veloce</h1><button class="btn small" id="qsave">Salva</button></header>
    <form class="form" id="qf" autocomplete="off">
      <fieldset><legend>Punteggio</legend>
        <input name="score" id="score" class="score-input" placeholder="6-4 3-6 7-5" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="done">
        <p class="small muted">Set separati da spazi. Tie-break: <b>7-6(5)</b>. Super tie-break: <b>[10-8]</b>. Il primo numero è sempre il vostro.</p>
        <div id="preview" class="preview"></div>
      </fieldset>
      <fieldset><legend>Dal Watch</legend>
        <button type="button" class="btn wide watch-btn" id="paste">⌚ Incolla dal Watch</button>
        <p class="small muted" id="pastemsg">Dopo la partita lancia il Comando rapido di fine allenamento, poi tocca qui.</p>
        <div id="manualpaste" hidden>
          <textarea id="pastebox" rows="4" placeholder="Incolla qui il testo copiato dal Comando rapido"></textarea>
          <button type="button" class="btn small" id="pasteread">Leggi</button>
        </div>
        <label>Data e ora <input type="datetime-local" name="date" value="${local(d.date.getTime())}"></label>
        <div class="grid2">
          <label>Durata (min) <input type="number" inputmode="numeric" min="0" max="360" name="minutes"></label>
          <label>Calorie <input type="number" inputmode="numeric" min="0" max="3000" name="calories"></label>
          <label>FC media <input type="number" inputmode="numeric" min="0" max="250" name="avg"></label>
          <label>FC max <input type="number" inputmode="numeric" min="0" max="250" name="max"></label>
        </div>
      </fieldset>
      <fieldset><legend>Giocatori</legend>
        <label>Compagno <input name="partner" list="players"></label>${chips('partner', frequent(['partnerID']))}
        <label>Avversario 1 <input name="opp1" list="players"></label>
        <label>Avversario 2 <input name="opp2" list="players"></label>${chips('opp', frequent(['opponent1ID', 'opponent2ID'], 6))}
        <datalist id="players">${db.players.map((p) => `<option value="${esc(p.name)}">`).join('')}</datalist>
        <label>Circolo <input name="club" list="clubs" value="${esc(last?.club ?? '')}"></label>
        <datalist id="clubs">${clubs.map((c) => `<option value="${esc(c)}">`).join('')}</datalist>
      </fieldset>
    </form>`;

  const f = $('#qf');
  let parsed = null;
  const showPreview = () => {
    const text = f.score.value;
    parsed = text.trim() ? parseScore(text) : null;
    const box = $('#preview');
    if (!parsed) { box.innerHTML = ''; return; }
    if (parsed.error) { box.innerHTML = `<p class="err">${esc(parsed.error)}</p>`; return; }
    const w = E.setsWon(parsed.sets), l = E.setsLost(parsed.sets);
    box.innerHTML = `
      <div class="pv-sets">${badge(parsed.sets)}${parsed.sets.map((st) => `<span class="${E.setWinner(st) === US ? 'win' : 'loss'}">${esc(E.setDisplay(st))}</span>`).join('')}</div>
      <p>${parsed.winner === US ? `Vittoria ${w}-${l}` : parsed.winner === THEM ? `Sconfitta ${w}-${l}` : 'Partita non conclusa'}${parsed.format === 'twoSetsSuperTiebreak' ? ' · con super tie-break' : ''}</p>
      ${parsed.warning ? `<p class="warn">${esc(parsed.warning)}</p>` : ''}`;
  };
  f.score.addEventListener('input', showPreview);
  f.score.focus();

  f.querySelectorAll('[data-fill]').forEach((b) => b.onclick = () => {
    if (b.dataset.fill === 'partner') { f.partner.value = b.dataset.name; return; }
    // Avversari: riempie il primo campo libero (o sostituisce il secondo).
    const name = b.dataset.name;
    if (f.opp1.value === name || f.opp2.value === name) return;
    if (!f.opp1.value) f.opp1.value = name; else f.opp2.value = name;
  });

  const applyWatch = (text) => {
    const r = parseWatchPaste(text);
    const msg = $('#pastemsg');
    if (r.error) { msg.innerHTML = `<span class="err">${esc(r.error)}</span>`; return false; }
    if (r.start) {
      f.date.value = local(r.start);
      f.minutes.value = Math.round(r.duration / 60);
      f.avg.value = r.avg;
      f.max.value = r.max;
    }
    if (r.calories != null) f.calories.value = r.calories;
    msg.innerHTML = r.start
      ? `<span class="ok">✓ ${fmtLong(r.duration)} dalle ${new Date(r.start).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })} · FC media ${r.avg}, max ${r.max}${r.calories != null ? ` · ${r.calories} kcal` : ''}</span>`
      : `<span class="ok">✓ ${r.calories} kcal</span>`;
    $('#manualpaste').hidden = true;
    return true;
  };
  $('#paste').onclick = async () => {
    try {
      // Su iPhone Safari chiede conferma con il pulsante "Incolla".
      const text = await navigator.clipboard.readText();
      if (applyWatch(text)) return;
    } catch { /* appunti non concessi: si incolla a mano */ }
    $('#manualpaste').hidden = false;
    $('#pastebox').focus();
  };
  $('#pasteread').onclick = () => applyWatch($('#pastebox').value);

  $('#qsave').onclick = () => {
    showPreview();
    if (!parsed || parsed.error) {
      if (!parsed) $('#preview').innerHTML = '<p class="err">Scrivi il punteggio, per esempio 6-4 3-6 7-5.</p>';
      f.score.focus();
      return;
    }
    const num = (v) => (v === '' || v == null ? undefined : Math.max(0, Number(v)));
    const setup = load(SETUP, E.defaultRules());
    const match = {
      id: E.newId(),
      date: new Date(f.date.value || Date.now()).toISOString(),
      club: f.club.value.trim(), court: '',
      partnerID: playerIdFor(f.partner.value),
      opponent1ID: playerIdFor(f.opp1.value),
      opponent2ID: playerIdFor(f.opp2.value),
      rules: { deuceRule: setup.deuceRule, format: parsed.format, firstServer: US, indoor: !!setup.indoor },
      sets: parsed.sets,
      duration: (num(f.minutes.value) ?? 0) * 60,
      activeCalories: num(f.calories.value),
      averageHeartRate: num(f.avg.value),
      maxHeartRate: num(f.max.value),
      notes: '', source: 'manual',
    };
    for (const k of Object.keys(match)) if (match[k] === undefined) delete match[k];
    db.matches.push(match);
    persist();
    location.hash = '#/partite';
  };
}

// ---- Segnapunti ------------------------------------------------------------

let ticker = null, wakeLock = null;
const stopTicker = () => { clearInterval(ticker); ticker = null; wakeLock?.release?.(); wakeLock = null; };

async function keepAwake() {
  try { wakeLock = await navigator.wakeLock?.request('screen'); } catch { /* non supportato */ }
}
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && ticker) keepAwake();
});

function renderPlay() {
  const live = load(LIVE, null);
  if (!live) return renderSetup();
  document.body.classList.add('playing');
  const match = live.match;
  const s = match.state;

  if (s.winner) {
    $('#main').innerHTML = `
      <section class="won">
        <h1 class="${s.winner === US ? 'us' : 'them'}">${s.winner === US ? 'Vittoria!' : 'Sconfitta'}</h1>
        <p class="bigsets">${esc(s.completedSets.map(E.setCompact).join('  '))}</p>
        <button class="btn wide" id="finish">Salva partita</button>
        <button class="btn ghost wide" id="undo">↶ Indietro</button>
      </section>`;
    $('#finish').onclick = () => finishLive(live);
    $('#undo').onclick = () => { E.undoLastPoint(match); save(LIVE, live); renderPlay(); };
    return;
  }

  const panel = (t) => `
    <button class="team ${t === US ? 'us' : 'them'} ${s.server === t ? 'serving' : ''}" data-team="${t}">
      <span class="tname">${t === US ? 'NOI' : 'LORO'} ${s.server === t ? '<span class="ball" aria-label="al servizio">●</span>' : ''}</span>
      <span class="pts">${E.pointLabel(match, t)}</span>
      <span class="gms">${E.games(s, t)} <small>game</small></span>
      <span class="dots">${[0, 1].map((i) => `<i class="${i < E.sets(s, t) ? 'on' : ''}"></i>`).join('')}</span>
    </button>`;
  const status = E.statusLabel(match);
  $('#main').innerHTML = `
    <section class="board">
      <div class="top">
        <span>${esc(s.completedSets.map(E.setCompact).join(' ') || 'Set 1')}</span>
        ${status ? `<span class="chip">${esc(status)}</span>` : ''}
        <span id="clock">${fmtClock((Date.now() - live.start) / 1000)}</span>
      </div>
      ${panel(US)}
      ${panel(THEM)}
      <div class="controls">
        <button class="btn ghost" id="undo" ${E.canUndo(match) ? '' : 'disabled'}>↶ Indietro</button>
        <button class="btn ghost" id="server">Servizio: ${E.teamLabel(s.server)}</button>
        <button class="btn danger" id="end">Termina</button>
      </div>
    </section>`;
  document.querySelectorAll('.team').forEach((b) => b.onclick = () => {
    const outcome = E.point(match, b.dataset.team);
    navigator.vibrate?.(outcome === 'point' ? 20 : [40, 40, 40]);
    save(LIVE, live); renderPlay();
  });
  $('#undo').onclick = () => { E.undoLastPoint(match); save(LIVE, live); renderPlay(); };
  $('#server').onclick = () => { E.setServer(match, E.opp(s.server)); save(LIVE, live); renderPlay(); };
  $('#end').onclick = () => { if (confirm('Terminare la partita e salvarla?')) finishLive(live); };
  if (!ticker) {
    ticker = setInterval(() => { const c = $('#clock'); if (c) c.textContent = fmtClock((Date.now() - live.start) / 1000); }, 1000);
    keepAwake();
  }
}

function renderSetup() {
  document.body.classList.remove('playing');
  const r = load(SETUP, E.defaultRules());
  const radio = (name, value, label) => `<label class="seg"><input type="radio" name="${name}" value="${value}" ${String(r[name]) === String(value) ? 'checked' : ''}><span>${label}</span></label>`;
  $('#main').innerHTML = `
    <header class="bar"><h1>Nuova partita</h1></header>
    <form class="form" id="setup">
      <fieldset><legend>Sul 40-40</legend><div class="segs">${radio('deuceRule', 'goldenPoint', "Punto d'oro")}${radio('deuceRule', 'advantages', 'Vantaggi')}</div></fieldset>
      <fieldset><legend>Formato</legend><div class="segs">${radio('format', 'bestOfThree', '3 set')}${radio('format', 'twoSetsSuperTiebreak', '2 set + STB')}</div></fieldset>
      <fieldset><legend>Serve per primo</legend><div class="segs">${radio('firstServer', US, 'Noi')}${radio('firstServer', THEM, 'Loro')}</div></fieldset>
      <fieldset><legend>Campo coperto</legend><div class="segs">${radio('indoor', 'false', 'No')}${radio('indoor', 'true', 'Sì')}</div></fieldset>
      <button class="btn wide big" type="submit">▶ Inizia partita</button>
    </form>`;
  $('#setup').onsubmit = (e) => {
    e.preventDefault();
    const d = new FormData(e.target);
    const rules = { deuceRule: d.get('deuceRule'), format: d.get('format'), firstServer: d.get('firstServer'), indoor: d.get('indoor') === 'true' };
    save(SETUP, rules);
    save(LIVE, { id: E.newId(), start: Date.now(), match: E.newMatch(rules) });
    renderPlay();
  };
}

function finishLive(live) {
  const s = live.match.state;
  const partial = !s.winner && s.gamesUs + s.gamesThem > 0 ? ` Partita terminata con il set in corso sul ${s.gamesUs}-${s.gamesThem}.` : '';
  db.matches.push({
    id: live.id, date: new Date(live.start).toISOString(), club: '', court: '',
    rules: live.match.rules, sets: s.completedSets, duration: Math.round((Date.now() - live.start) / 1000),
    notes: partial.trim(), source: 'manual',
  });
  persist();
  localStorage.removeItem(LIVE);
  stopTicker();
  document.body.classList.remove('playing');
  location.hash = `#/partita/${live.id}`;
}

// ---- Statistiche -----------------------------------------------------------

let period = 'allTime';

function renderStats() {
  const st = E.statistics(db.matches, names(), period);
  const tile = (t, v, cls = '') => `<div class="tile"><span>${t}</span><b class="${cls}">${v}</b></div>`;
  const streak = st.streak ? `${st.streak.count} ${st.streak.type === 'wins' ? (st.streak.count === 1 ? 'vittoria' : 'vittorie') : (st.streak.count === 1 ? 'sconfitta' : 'sconfitte')}` : '—';
  const maxMonth = Math.max(1, ...st.months.map((m) => m.won + m.lost));
  const monthName = (key) => new Date(key + '-01T12:00').toLocaleDateString('it-IT', { month: 'short' });
  const trend = st.trend.length > 1
    ? st.trend.map((p, i) => `${(i / (st.trend.length - 1)) * 300},${100 - p.pct}`).join(' ')
    : null;

  $('#main').innerHTML = `
    <header class="bar"><h1>Statistiche</h1></header>
    <div class="segs period">${[['allTime', 'Sempre'], ['last12Months', '12 mesi'], ['last3Months', '3 mesi']].map(([k, l]) =>
      `<label class="seg"><input type="radio" name="p" value="${k}" ${k === period ? 'checked' : ''}><span>${l}</span></label>`).join('')}</div>
    ${st.played === 0 ? '<p class="empty">Nessuna partita con un vincitore nel periodo.</p>' : `
    <div class="overview">
      <div class="top2"><span class="n">${st.played}</span><b>${st.played === 1 ? 'PARTITA' : 'PARTITE'}</b>
        <span class="wl">${st.won} VINTE<br>${st.lost} PERSE</span></div>
      <div class="bar2"><i style="flex:${st.won};background:var(--win)"></i><i style="flex:${st.lost};background:var(--loss)"></i></div>
    </div>
    <div class="tiles">
      ${tile('% vittorie', Math.round(st.winPct) + '%', st.winPct >= 50 ? 'win' : 'loss')}
      ${tile('Set vinti – persi', `${st.setsWon} – ${st.setsLost}`)}
      ${tile('Ore in campo', (st.duration / 3600).toLocaleString('it-IT', { maximumFractionDigits: 1 }))}
      ${tile('Calorie totali', Math.round(st.calories) + ' kcal')}
      ${tile('Serie attuale', streak, st.streak?.type === 'wins' ? 'win' : 'loss')}
    </div>
    <section class="card"><h2>Vinte e perse per mese</h2>
      <div class="bars">${st.months.map((m) => `
        <div class="barcol" title="${m.won} vinte, ${m.lost} perse">
          <div class="stack" style="height:${((m.won + m.lost) / maxMonth) * 100}%">
            <i class="loss" style="flex:${m.lost}"></i><i class="win" style="flex:${m.won}"></i>
          </div><span>${monthName(m.key)}</span></div>`).join('')}</div>
      <p class="legend"><i class="win"></i> Vinte <i class="loss"></i> Perse</p>
    </section>
    ${trend ? `<section class="card"><h2>% vittorie nel tempo</h2>
      <svg viewBox="0 0 300 100" preserveAspectRatio="none" class="trend">
        <line x1="0" y1="50" x2="300" y2="50" class="half"/><polyline points="${trend}"/></svg>
      <p class="muted small">Da ${fmtDate(st.trend[0].date)} a ${fmtDate(st.trend.at(-1).date)} · linea tratteggiata = 50%</p></section>` : ''}
    <section class="card"><h2>Classifica compagni</h2>
      ${st.partners.length ? st.partners.map((p) => `
        <div class="rank ${st.bestPartner?.id === p.id ? 'best' : ''}">
          <span>${st.bestPartner?.id === p.id ? '★ ' : ''}${esc(p.name)}</span>
          <span class="muted">${p.won}V ${p.lost}S</span><b>${Math.round(p.pct)}%</b></div>`).join('')
        + '<p class="muted small">Il miglior compagno serve almeno 3 partite insieme.</p>'
      : '<p class="muted">Indica il compagno nelle partite per vedere la classifica.</p>'}
    </section>
    <section class="card"><h2>Bilancio contro gli avversari</h2>
      ${st.opponents.length ? st.opponents.map((o) => `
        <div class="rank"><span>${esc(o.name)}</span><b class="${o.won > o.lost ? 'win' : o.won < o.lost ? 'loss' : ''}">${o.won} – ${o.lost}</b></div>`).join('')
      : '<p class="muted">Indica gli avversari nelle partite per vedere il bilancio.</p>'}
    </section>`}`;
  document.querySelectorAll('input[name=p]').forEach((i) => i.onchange = () => { period = i.value; renderStats(); });
}

// ---- Impostazioni ----------------------------------------------------------

function renderSettings() {
  const players = [...db.players].sort((a, b) => a.name.localeCompare(b.name, 'it'));
  $('#main').innerHTML = `
    <header class="bar"><h1>Impostazioni</h1></header>
    <section class="card"><h2>Backup</h2>
      <p class="muted">${db.matches.length} partite, ${db.players.length} giocatori. Stesso formato JSON dell'app per iPhone: puoi spostare i dati dall'una all'altra.</p>
      <button class="btn wide" id="export">Esporta backup</button>
      <label class="btn ghost wide">Importa backup<input type="file" accept="application/json,.json" id="import" hidden></label>
      <p class="muted small">I dati stanno solo su questo telefono. Fai un backup ogni tanto e salvalo in File.</p>
    </section>
    <section class="card"><h2>Giocatori</h2>
      <form id="addp" class="inline"><input name="n" placeholder="Nuovo giocatore"><button class="btn small">Aggiungi</button></form>
      ${players.length ? players.map((p) => `
        <div class="rank"><span>${esc(p.name)}</span>
          <span><button class="link" data-ren="${p.id}">Rinomina</button> <button class="link danger" data-delp="${p.id}">Elimina</button></span></div>`).join('')
      : '<p class="muted">La rubrica si riempie anche scrivendo i nomi nelle partite.</p>'}
    </section>
    <p class="muted small center">Padel · versione web</p>`;

  $('#export').onclick = exportBackup;
  $('#import').onchange = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    try {
      const merged = E.mergeBackup(JSON.parse(await file.text()), db.players, db.matches);
      db = { players: merged.players, matches: merged.matches }; persist();
      alert(merged.added.matches + merged.added.players === 0 ? 'Nessun dato nuovo: era tutto già presente.'
        : `Importate ${merged.added.matches} partite e ${merged.added.players} giocatori.`);
    } catch (err) { alert('Importazione non riuscita: ' + err.message); }
    renderSettings();
  };
  $('#addp').onsubmit = (e) => { e.preventDefault(); if (playerIdFor(e.target.n.value)) { persist(); renderSettings(); } };
  document.querySelectorAll('[data-ren]').forEach((b) => b.onclick = () => {
    const p = db.players.find((x) => x.id === b.dataset.ren);
    const n = prompt('Nuovo nome', p.name)?.trim();
    if (n) { p.name = n; persist(); renderSettings(); }
  });
  document.querySelectorAll('[data-delp]').forEach((b) => b.onclick = () => {
    const id = b.dataset.delp;
    if (!confirm('Eliminare il giocatore? Verrà tolto dalle partite, che restano.')) return;
    db.players = db.players.filter((x) => x.id !== id);
    for (const m of db.matches) for (const k of ['partnerID', 'opponent1ID', 'opponent2ID']) if (m[k] === id) delete m[k];
    persist(); renderSettings();
  });
}

async function exportBackup() {
  const json = JSON.stringify(E.buildBackup(db.players, db.matches), null, 2);
  const name = `padel-backup-${new Date().toISOString().slice(0, 10)}.json`;
  const file = new File([json], name, { type: 'application/json' });
  // Su iPhone apre il foglio di condivisione (Salva in File, AirDrop...).
  if (navigator.canShare?.({ files: [file] })) {
    try { await navigator.share({ files: [file], title: 'Backup Padel' }); return; } catch (e) { if (e.name === 'AbortError') return; }
  }
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(file), download: name });
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ---- Avvio -----------------------------------------------------------------

if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js');
if (!location.hash && load(LIVE, null)) location.hash = '#/gioca';
route();
