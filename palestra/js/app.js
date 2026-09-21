/* Palestra — registro allenamenti offline.
 * Stato in IndexedDB (js/db.js), catalogo foto in js/catalog.js,
 * battito cardiaco in js/hr.js. Niente framework: una vista e' una funzione
 * che torna HTML, piu' delega degli eventi su [data-act]. */
const App = (function () {
  const state = {
    view: 'oggi',
    settings: null,
    exercises: [],
    exMap: {},
    routines: [],
    session: null,
    sets: [],
    lastPerf: {},
    bestPrior: {},
    progressEx: null,
    lastTrainedEx: null,
    progressMetric: 'top',
    pickTab: 'mine'
  };

  /* ================= utilita' ================= */

  const $ = (sel, root) => (root || document).querySelector(sel);
  const $$ = (sel, root) => Array.prototype.slice.call((root || document).querySelectorAll(sel));

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function icon(name, cls) {
    return '<svg class="ico' + (cls ? ' ' + cls : '') + '" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
  }

  function num(n) {
    const v = Number(n) || 0;
    return Math.abs(v % 1) > 0.001 ? v.toFixed(1) : String(Math.round(v));
  }

  const fmtDate = (ts) => new Date(ts).toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
  const fmtDateShort = (ts) => new Date(ts).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' });
  const fmtTime = (ts) => new Date(ts).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });

  function fmtDur(ms) {
    if (!ms || ms < 0) return '—';
    const m = Math.round(ms / 60000);
    if (m < 60) return m + ' min';
    return Math.floor(m / 60) + 'h ' + String(m % 60).padStart(2, '0') + 'm';
  }

  function mmss(sec) {
    const s = Math.max(0, Math.round(sec));
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }

  // Epley: stima del massimale da carico e ripetizioni.
  function e1rm(weight, reps) {
    if (!weight || !reps) return 0;
    return reps === 1 ? weight : weight * (1 + reps / 30);
  }

  function volume(sets) {
    return sets.reduce((t, s) => t + (s.warmup ? 0 : (s.weight || 0) * (s.reps || 0)), 0);
  }

  let toastTimer = null;
  function toast(msg, isError) {
    const t = $('#toast');
    t.textContent = msg;
    t.classList.toggle('error', !!isError);
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 2800);
  }

  const describeSets = (sets) => sets.map((s) => num(s.weight) + '×' + s.reps + (s.warmup ? ' (r)' : '')).join(' · ');

  function unitLabels(ex) {
    const u = (ex && ex.unit) || 'kg';
    if (u === 'time') return { w: 'kg', r: 'sec', repWord: 'sec' };
    if (u === 'bw') return { w: 'zavorra', r: 'reps', repWord: 'reps' };
    return { w: 'kg', r: 'reps', repWord: 'reps' };
  }

  function thumbFor(ex) {
    if (ex && ex.img) return Catalog.imageUrl(ex.img);
    if (ex && ex.catalogId && Catalog.loaded()) {
      const it = Catalog.get(ex.catalogId);
      if (it && it.img.length) return Catalog.imageUrl(it.img[0]);
    }
    return '';
  }

  /* ================= timer di recupero ================= */

  const Rest = (function () {
    let endAt = 0, iv = null, total = 0, audioCtx = null;

    function beep() {
      if (!state.settings || !state.settings.sound) return;
      try {
        audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
        [0, 0.22, 0.44].forEach((offset) => {
          const o = audioCtx.createOscillator();
          const g = audioCtx.createGain();
          o.type = 'sine';
          o.frequency.value = 880;
          g.gain.setValueAtTime(0.0001, audioCtx.currentTime + offset);
          g.gain.exponentialRampToValueAtTime(0.35, audioCtx.currentTime + offset + 0.02);
          g.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + offset + 0.16);
          o.connect(g); g.connect(audioCtx.destination);
          o.start(audioCtx.currentTime + offset);
          o.stop(audioCtx.currentTime + offset + 0.18);
        });
      } catch (e) { /* audio non disponibile */ }
    }

    function buzz() {
      if (state.settings && state.settings.vibrate && navigator.vibrate) navigator.vibrate([200, 90, 200]);
    }

    // iOS sblocca l'audio solo dentro un gesto dell'utente.
    function unlock() {
      try {
        audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
        if (audioCtx.state === 'suspended') audioCtx.resume();
      } catch (e) { /* ignora */ }
    }

    function paint() {
      const left = (endAt - Date.now()) / 1000;
      $('#rest-time').textContent = mmss(left);
      $('#rest-fill').style.width = (total > 0 ? Math.max(0, Math.min(1, left / total)) * 100 : 0).toFixed(1) + '%';
      if (left <= 0) finish();
    }

    function finish() {
      clearInterval(iv); iv = null;
      $('#rest-time').textContent = '00:00';
      $('#rest-fill').style.width = '0%';
      $('#rest-bar').classList.add('done');
      beep(); buzz();
      setTimeout(stop, 2500);
    }

    function start(seconds) {
      total = seconds;
      endAt = Date.now() + seconds * 1000;
      $('#rest-bar').hidden = false;
      $('#rest-bar').classList.remove('done');
      document.body.classList.add('rest-on');
      paint();
      clearInterval(iv);
      iv = setInterval(paint, 250);
    }

    function stop() {
      clearInterval(iv); iv = null;
      $('#rest-bar').hidden = true;
      $('#rest-bar').classList.remove('done');
      document.body.classList.remove('rest-on');
    }

    function adjust(sec) {
      if ($('#rest-bar').hidden) return;
      endAt += sec * 1000;
      if (sec > 0) total += sec;
      if (endAt < Date.now()) endAt = Date.now();
      paint();
    }

    return { start, stop, adjust, unlock };
  })();

  /* ================= schermo acceso ================= */

  let wakeLock = null;
  function keepAwake(on) {
    try {
      if (on && 'wakeLock' in navigator) {
        navigator.wakeLock.request('screen').then((w) => { wakeLock = w; }).catch(() => {});
      } else if (wakeLock) {
        wakeLock.release().catch(() => {});
        wakeLock = null;
      }
    } catch (e) { /* non supportato */ }
  }
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && state.session && !wakeLock) keepAwake(true);
  });

  /* ================= modale ================= */

  function openModal(title, bodyHtml) {
    $('#modal-title').textContent = title;
    $('#modal-body').innerHTML = bodyHtml;
    $('#modal-root').hidden = false;
  }

  function closeModal() {
    $('#modal-root').hidden = true;
    $('#modal-body').innerHTML = '';
  }

  /* ================= dati ================= */

  function loadCore() {
    return Promise.all([DB.getSettings(), DB.listExercises(), DB.listRoutines()])
      .then(([settings, exercises, routines]) => {
        state.settings = settings;
        state.exercises = exercises;
        state.exMap = {};
        exercises.forEach((e) => { state.exMap[e.id] = e; });
        state.routines = routines;
      });
  }

  function loadSession() {
    return DB.activeSession().then((s) => {
      state.session = s;
      keepAwake(!!s);
      if (!s) { state.sets = []; state.lastPerf = {}; state.bestPrior = {}; return null; }
      return DB.setsOfSession(s.id).then((sets) => {
        state.sets = sets;
        return loadHistoryFor(sessionExerciseIds(), s.id);
      });
    });
  }

  function sessionExerciseIds() {
    const ids = [];
    (state.session && state.session.plan ? state.session.plan : []).forEach((p) => {
      if (ids.indexOf(p.exerciseId) === -1) ids.push(p.exerciseId);
    });
    state.sets.forEach((s) => { if (ids.indexOf(s.exerciseId) === -1) ids.push(s.exerciseId); });
    return ids;
  }

  // Ultima volta + record precedente, per esercizio.
  function loadHistoryFor(ids, excludeSessionId) {
    state.lastPerf = {};
    state.bestPrior = {};
    return Promise.all(ids.map((id) => DB.setsOfExercise(id).then((rows) => {
      const past = rows.filter((r) => r.sessionId !== excludeSessionId && !r.warmup);
      if (!past.length) return;
      const lastSessionId = past[past.length - 1].sessionId;
      const lastSets = past.filter((r) => r.sessionId === lastSessionId);
      state.lastPerf[id] = { ts: lastSets[lastSets.length - 1].ts, sets: lastSets };
      state.bestPrior[id] = past.reduce((b, s) => Math.max(b, e1rm(s.weight, s.reps)), 0);
    })));
  }

  /* ================= vista: Oggi ================= */

  function viewOggi() {
    if (!state.session) return viewOggiIdle();

    const s = state.session;
    const ids = sessionExerciseIds();
    const planMap = {};
    (s.plan || []).forEach((p) => { planMap[p.exerciseId] = p; });

    let html = '<section class="card session-head"><div class="row between">' +
      '<div><h2>' + esc(s.name) + '</h2><p class="muted" id="session-stats">' + sessionStatsLine() + '</p></div>' +
      '<button class="btn danger" data-act="end-session" type="button">Termina</button></div></section>';

    html += hrCard();

    if (!ids.length) html += '<p class="empty">Allenamento vuoto: aggiungi il primo esercizio.</p>';

    ids.forEach((id) => {
      const ex = state.exMap[id];
      if (ex) html += exerciseCard(ex, state.sets.filter((x) => x.exerciseId === id), planMap[id]);
    });

    html += '<button class="btn wide" data-act="pick-exercise" type="button">' + icon('plus') + ' Aggiungi esercizio</button>';
    html += '<details class="card"><summary>Nota della sessione</summary>' +
      '<textarea id="session-note" rows="3" placeholder="Come e andata, cosa cambiare la prossima volta">' +
      esc(s.note || '') + '</textarea>' +
      '<button class="btn" data-act="save-session-note" type="button">Salva nota</button></details>';
    return html;
  }

  function sessionStatsLine() {
    const s = state.session;
    if (!s) return '';
    return 'Dalle ' + fmtTime(s.startedAt) + ' · ' + fmtDur(Date.now() - s.startedAt) +
      ' · ' + state.sets.filter((x) => !x.warmup).length + ' serie · ' + num(volume(state.sets)) + ' kg';
  }

  function viewOggiIdle() {
    let html = '<section class="card"><h2>Nessun allenamento in corso</h2>' +
      '<p class="muted">Parti da una scheda oppure registra al volo quello che fai.</p>';
    if (state.routines.length) {
      html += '<div class="stack">';
      state.routines.forEach((r) => {
        html += '<button class="btn primary wide" data-act="start-routine" data-id="' + r.id + '" type="button">' +
          esc(r.name) + ' <span class="muted-inline">· ' + (r.items || []).length + ' esercizi</span></button>';
      });
      html += '</div>';
    }
    html += '<button class="btn wide" data-act="start-free" type="button">Allenamento libero</button></section>';
    html += '<div id="idle-recent"></div>';
    return html;
  }

  function hrCard() {
    const s = state.session;
    const connected = HR.connected();
    const saved = s && s.hr;
    let h = '<section class="card hr-card"><div class="row between"><h3>' + icon('pulse') + ' Battito cardiaco</h3>' +
      '<button class="icon-btn" data-act="hr-help" type="button" aria-label="Come funziona">' + icon('info') + '</button></div>';

    if (connected) {
      const bpm = HR.bpm();
      const z = HR.zone(bpm, state.settings.age);
      h += '<div class="hr-now" id="hr-live"><span class="beating">' + icon('heart') + '</span>' +
        '<span class="bpm">' + (bpm || '--') + '</span><span class="unit">bpm' +
        (z ? '<br><span class="zone-badge">Z' + z.n + ' ' + z.label + '</span>' : '') + '</span></div>';
      h += '<button class="btn wide" data-act="hr-disconnect" type="button">Scollega sensore</button>';
    } else if (saved) {
      h += '<div class="stats"><div><b>' + saved.avg + '</b><span>media</span></div>' +
        '<div><b>' + saved.max + '</b><span>massimo</span></div>' +
        '<div><b>' + (saved.min || '—') + '</b><span>minimo</span></div></div>';
      h += '<button class="btn wide" data-act="hr-manual" type="button">Correggi a mano</button>';
    } else {
      h += '<p class="muted">Apple Watch: registra l allenamento su Salute e importalo dopo (Altro → Battito). ' +
        'Fascia cardio Bluetooth: puoi vederlo qui in diretta.</p>';
      h += '<div class="row gap wrap">';
      if (HR.supported()) {
        h += '<button class="btn" data-act="hr-connect" type="button">' + icon('bluetooth', 'sm') + ' Collega sensore</button>';
      }
      h += '<button class="btn" data-act="hr-manual" type="button">Inserisci a mano</button></div>';
    }
    return h + '</section>';
  }

  function exerciseCard(ex, done, plan) {
    const u = unitLabels(ex);
    const last = state.lastPerf[ex.id];
    const best = state.bestPrior[ex.id] || 0;
    const prev = done.length ? done[done.length - 1] : (last && last.sets.length ? last.sets[last.sets.length - 1] : null);
    const thumb = thumbFor(ex);

    let h = '<section class="card ex-card" data-ex="' + ex.id + '"><div class="ex-head">';
    if (thumb) {
      h += '<img class="ex-thumb" src="' + esc(thumb) + '" alt="" loading="lazy" decoding="async" ' +
        'data-act="ex-detail" data-id="' + ex.id + '">';
    }
    h += '<div style="flex:1;min-width:0"><h3>' + esc(ex.name) + '</h3><p class="muted small">' +
      esc([ex.muscle, ex.equipment].filter(Boolean).join(' · ')) +
      (plan && plan.sets ? ' · obiettivo ' + esc(plan.sets) + '×' + esc(plan.reps) : '') + '</p></div>';
    h += '<button class="icon-btn" data-act="remove-ex" data-id="' + ex.id + '" aria-label="Togli esercizio" type="button">' +
      icon('close') + '</button></div>';

    h += last
      ? '<p class="hint">Ultima volta (' + fmtDateShort(last.ts) + '): ' + esc(describeSets(last.sets)) + '</p>'
      : '<p class="hint">Prima volta che lo registri.</p>';

    if (done.length) {
      h += '<ol class="sets">';
      let n = 0;
      done.forEach((d) => {
        if (!d.warmup) n++;
        const isPr = !d.warmup && best > 0 && e1rm(d.weight, d.reps) > best;
        h += '<li data-act="edit-set" data-id="' + d.id + '" class="' + (d.warmup ? 'warm' : '') + '">' +
          '<span class="n">' + (d.warmup ? 'r' : n) + '</span>' +
          '<span class="load"><b>' + num(d.weight) + '</b> ' + u.w + ' × <b>' + d.reps + '</b> ' + u.repWord + '</span>' +
          (isPr ? '<span class="tag pr">record</span>' : '') +
          (d.rpe ? '<span class="tag">RPE ' + num(d.rpe) + '</span>' : '') +
          (d.note ? '<span class="tag" title="' + esc(d.note) + '">nota</span>' : '') +
          '</li>';
      });
      h += '</ol><p class="muted small">' + done.filter((d) => !d.warmup).length + ' serie di lavoro · ' +
        num(volume(done)) + ' kg di volume</p>';
    }

    h += '<form class="set-form" data-act="add-set" data-ex="' + ex.id + '">' +
      '<label>' + u.w + '<input name="weight" type="number" inputmode="decimal" step="0.5" min="0" value="' +
        (prev ? num(prev.weight) : '') + '"></label>' +
      '<label>' + u.r + '<input name="reps" type="number" inputmode="numeric" step="1" min="0" value="' +
        (prev ? prev.reps : '') + '"></label>' +
      '<label>RPE<input name="rpe" type="number" inputmode="decimal" step="0.5" min="5" max="10" placeholder="—"></label>' +
      '<button class="btn primary" type="submit">Salva serie</button>' +
      '<label class="chk"><input type="checkbox" name="warmup"> riscaldamento</label>' +
      '<input class="note-input" name="note" type="text" placeholder="nota (opzionale)" maxlength="140">' +
      '</form></section>';
    return h;
  }

  function renderRecentInto() {
    const box = $('#idle-recent');
    if (!box) return;
    DB.listSessions().then((rows) => {
      const done = rows.filter((r) => r.endedAt).slice(0, 3);
      if (!done.length) { box.innerHTML = ''; return; }
      Promise.all(done.map((s) => DB.setsOfSession(s.id).then((sets) => ({ s, sets })))).then((items) => {
        let h = '<section class="card"><h3>Ultimi allenamenti</h3><ul class="list">';
        items.forEach(({ s, sets }) => {
          h += '<li><div><b>' + esc(s.name) + '</b><div class="muted small">' + fmtDate(s.startedAt) + '</div></div>' +
            '<div class="muted small">' + sets.filter((x) => !x.warmup).length + ' serie · ' + num(volume(sets)) +
            ' kg · ' + fmtDur(s.endedAt - s.startedAt) + (s.hr ? ' · ' + s.hr.avg + ' bpm' : '') + '</div></li>';
        });
        box.innerHTML = h + '</ul></section>';
      });
    });
  }

  /* ================= vista: Schede ================= */

  function viewSchede() {
    let h = '<button class="btn primary wide" data-act="routine-new" type="button">' + icon('plus') + ' Nuova scheda</button>';
    if (!state.routines.length) return h + '<p class="empty">Nessuna scheda. Creane una con gli esercizi che ripeti sempre.</p>';

    state.routines.forEach((r) => {
      h += '<section class="card"><div class="row between"><h3>' + esc(r.name) + '</h3><div class="row gap">' +
        '<button class="icon-btn" data-act="routine-rename" data-id="' + r.id + '" aria-label="Rinomina" type="button">' + icon('pencil') + '</button>' +
        '<button class="icon-btn danger" data-act="routine-del" data-id="' + r.id + '" aria-label="Elimina" type="button">' + icon('trash') + '</button>' +
        '</div></div>';
      if (!(r.items || []).length) {
        h += '<p class="muted">Ancora nessun esercizio.</p>';
      } else {
        h += '<ol class="list ordered">';
        r.items.forEach((it, i) => {
          const ex = state.exMap[it.exerciseId];
          h += '<li><div style="flex:1;min-width:0"><b>' + esc(ex ? ex.name : 'Esercizio rimosso') + '</b>' +
            '<div class="muted small">' + esc(it.sets) + ' × ' + esc(it.reps) + '</div></div><div class="row gap">' +
            '<button class="icon-btn" data-act="item-up" data-id="' + r.id + '" data-i="' + i + '" aria-label="Su" type="button"' + (i === 0 ? ' disabled' : '') + '>' + icon('up') + '</button>' +
            '<button class="icon-btn" data-act="item-down" data-id="' + r.id + '" data-i="' + i + '" aria-label="Giu" type="button"' + (i === r.items.length - 1 ? ' disabled' : '') + '>' + icon('down') + '</button>' +
            '<button class="icon-btn" data-act="item-edit" data-id="' + r.id + '" data-i="' + i + '" aria-label="Serie e ripetizioni" type="button">' + icon('pencil') + '</button>' +
            '<button class="icon-btn danger" data-act="item-del" data-id="' + r.id + '" data-i="' + i + '" aria-label="Togli" type="button">' + icon('close') + '</button>' +
            '</div></li>';
        });
        h += '</ol>';
      }
      h += '<div class="row gap wrap"><button class="btn" data-act="routine-add-ex" data-id="' + r.id + '" type="button">' +
        icon('plus', 'sm') + ' Esercizio</button>' +
        '<button class="btn primary" data-act="start-routine" data-id="' + r.id + '" type="button">Allenati con questa</button>' +
        '</div></section>';
    });
    return h;
  }

  /* ================= vista: Storico ================= */

  function viewStorico() { return '<div id="storico-box"><p class="muted">Carico…</p></div>'; }

  function renderStoricoInto() {
    const box = $('#storico-box');
    if (!box) return;
    DB.listSessions().then((rows) => {
      if (!rows.length) { box.innerHTML = '<p class="empty">Nessun allenamento registrato.</p>'; return; }
      Promise.all(rows.map((s) => DB.setsOfSession(s.id).then((sets) => ({ s, sets })))).then((items) => {
        const totVol = items.reduce((t, i) => t + volume(i.sets), 0);
        let h = '<section class="card"><h3>Totali</h3><div class="stats">' +
          '<div><b>' + items.length + '</b><span>allenamenti</span></div>' +
          '<div><b>' + items.reduce((t, i) => t + i.sets.filter((x) => !x.warmup).length, 0) + '</b><span>serie</span></div>' +
          '<div><b>' + num(Math.round(totVol / 100) / 10) + 't</b><span>volume</span></div></div></section>';

        items.forEach(({ s, sets }) => {
          const byEx = {};
          sets.forEach((x) => { (byEx[x.exerciseId] = byEx[x.exerciseId] || []).push(x); });
          h += '<section class="card"><div class="row between"><div><h3>' + esc(s.name) +
            (s.endedAt ? '' : ' <span class="tag">in corso</span>') + '</h3><p class="muted small">' +
            fmtDate(s.startedAt) + ' · ' + fmtDur((s.endedAt || Date.now()) - s.startedAt) + ' · ' +
            sets.filter((x) => !x.warmup).length + ' serie · ' + num(volume(sets)) + ' kg</p></div>' +
            '<button class="icon-btn danger" data-act="session-del" data-id="' + s.id + '" aria-label="Elimina" type="button">' +
            icon('trash') + '</button></div>';

          if (s.hr) {
            h += '<div class="stats"><div><b>' + s.hr.avg + '</b><span>bpm medi</span></div>' +
              '<div><b>' + s.hr.max + '</b><span>bpm max</span></div>' +
              '<div><b>' + (s.hr.min || '—') + '</b><span>bpm min</span></div></div>';
            if (s.hr.samples && s.hr.samples.length > 2) {
              h += Chart.line(s.hr.samples.map((p) => ({ x: p[0], y: p[1] })), { format: (v) => v + ' bpm', cls: 'hr' });
            }
          }

          h += '<ul class="list compact">';
          Object.keys(byEx).forEach((exId) => {
            const ex = state.exMap[exId];
            h += '<li><div><b>' + esc(ex ? ex.name : '—') + '</b><div class="muted small">' +
              esc(describeSets(byEx[exId])) + '</div></div></li>';
          });
          h += '</ul>';
          if (s.note) h += '<p class="hint">' + esc(s.note) + '</p>';
          h += '</section>';
        });
        box.innerHTML = h;
      });
    });
  }

  /* ================= vista: Progressi ================= */

  function viewProgressi() {
    if (!state.exercises.length) return '<p class="empty">Nessun esercizio in archivio.</p>';
    const fallback = (state.lastTrainedEx && state.exMap[state.lastTrainedEx])
      ? state.lastTrainedEx
      : state.exercises[0].id;
    const sel = state.progressEx && state.exMap[state.progressEx] ? state.progressEx : fallback;
    state.progressEx = sel;
    let h = '<section class="card"><label class="field">Esercizio<select data-act="progress-ex">';
    state.exercises.forEach((e) => {
      h += '<option value="' + e.id + '"' + (e.id === sel ? ' selected' : '') + '>' + esc(e.name) + '</option>';
    });
    h += '</select></label><div class="seg">' +
      [['top', 'Peso max'], ['e1rm', 'Massimale'], ['volume', 'Volume']].map(([k, lbl]) =>
        '<button class="' + (state.progressMetric === k ? 'on' : '') + '" data-act="progress-metric" data-metric="' + k + '" type="button">' + lbl + '</button>'
      ).join('') + '</div></section><div id="progress-box"><p class="muted">Carico…</p></div>';
    return h;
  }

  function renderProgressInto() {
    const box = $('#progress-box');
    if (!box || !state.progressEx) return;
    const ex = state.exMap[state.progressEx];
    DB.setsOfExercise(state.progressEx).then((rows) => {
      const work = rows.filter((r) => !r.warmup && r.reps > 0);
      if (!work.length) {
        box.innerHTML = '<p class="empty">Nessuna serie registrata per ' + esc(ex ? ex.name : '') + '.</p>';
        return;
      }
      const bySession = {};
      work.forEach((r) => { (bySession[r.sessionId] = bySession[r.sessionId] || []).push(r); });

      const points = Object.keys(bySession).map((sid) => {
        const sets = bySession[sid];
        let y;
        if (state.progressMetric === 'volume') y = volume(sets);
        else if (state.progressMetric === 'e1rm') y = Math.max.apply(null, sets.map((s) => e1rm(s.weight, s.reps)));
        else y = Math.max.apply(null, sets.map((s) => s.weight));
        return { x: sets[sets.length - 1].ts, y: Math.round(y * 10) / 10 };
      }).sort((a, b) => a.x - b.x);

      const prWeight = work.reduce((b, s) => (s.weight > (b ? b.weight : -1) ? s : b), null);
      const pr1rm = work.reduce((b, s) => (e1rm(s.weight, s.reps) > (b ? e1rm(b.weight, b.reps) : -1) ? s : b), null);
      const bestVol = Object.keys(bySession).reduce((best, sid) => {
        const v = volume(bySession[sid]);
        return v > best.v ? { v, ts: bySession[sid][0].ts } : best;
      }, { v: 0, ts: 0 });

      let h = '<section class="card"><h3>Record personali</h3><div class="stats">' +
        '<div><b>' + num(prWeight.weight) + '</b><span>kg max (×' + prWeight.reps + ')</span></div>' +
        '<div><b>' + num(e1rm(pr1rm.weight, pr1rm.reps)) + '</b><span>1RM stimato</span></div>' +
        '<div><b>' + num(bestVol.v) + '</b><span>miglior volume</span></div></div>' +
        '<p class="muted small">Record di peso il ' + fmtDate(prWeight.ts) + ' · massimale stimato da ' +
        num(pr1rm.weight) + '×' + pr1rm.reps + ' con la formula di Epley</p></section>';

      h += '<section class="card"><h3>' +
        (state.progressMetric === 'volume' ? 'Volume per sessione' :
          state.progressMetric === 'e1rm' ? 'Massimale stimato' : 'Peso massimo per sessione') + '</h3>' +
        Chart.line(points, { format: (v) => num(v) + ' kg' }) + '</section>';

      const recent = Object.keys(bySession).map((sid) => bySession[sid])
        .sort((a, b) => b[0].ts - a[0].ts).slice(0, 10);
      h += '<section class="card"><h3>Ultime sessioni</h3><ul class="list compact">';
      recent.forEach((sets) => {
        h += '<li><div><b>' + fmtDate(sets[0].ts) + '</b><div class="muted small">' + esc(describeSets(sets)) +
          '</div></div><div class="muted small">' + num(volume(sets)) + ' kg</div></li>';
      });
      box.innerHTML = h + '</ul></section>';
    });
  }

  /* ================= vista: Altro ================= */

  function viewImpostazioni() {
    const s = state.settings;
    let h = '<section class="card"><h3>' + icon('timer') + ' Recupero</h3>' +
      '<label class="field">Secondi di recupero predefiniti' +
      '<input type="number" min="10" max="600" step="5" value="' + s.restSeconds + '" data-act="set-rest"></label>' +
      '<label class="chk big"><input type="checkbox" data-act="set-autorest"' + (s.autoRest ? ' checked' : '') + '> Parte da solo quando salvo una serie</label>' +
      '<label class="chk big"><input type="checkbox" data-act="set-sound"' + (s.sound ? ' checked' : '') + '> Suono a fine recupero</label>' +
      '<label class="chk big"><input type="checkbox" data-act="set-vibrate"' + (s.vibrate ? ' checked' : '') + '> Vibrazione a fine recupero</label></section>';

    h += '<section class="card"><h3>' + icon('pulse') + ' Battito cardiaco</h3>' +
      '<p class="muted">Importa qui il file che genera il Comando rapido di iPhone: i battiti si agganciano da soli agli allenamenti giusti confrontando gli orari.</p>' +
      '<label class="field">La tua eta (serve per le zone)<input type="number" min="12" max="99" value="' +
      (s.age || '') + '" placeholder="es. 38" data-act="set-age"></label>' +
      '<div class="row gap wrap"><button class="btn primary" data-act="hr-import" type="button">' + icon('upload', 'sm') + ' Importa da Salute</button>' +
      '<button class="btn" data-act="hr-help" type="button">Come si fa</button></div>' +
      '<input type="file" id="hr-file" accept=".json,.csv,.txt,application/json,text/csv,text/plain" hidden></section>';

    h += '<section class="card"><h3>' + icon('download') + ' Backup</h3>' +
      '<p class="muted">I dati stanno solo su questo telefono. Esporta ogni tanto: quel file e la tua unica copia.</p>' +
      '<div class="row gap wrap"><button class="btn primary" data-act="export" type="button">Esporta backup</button>' +
      '<button class="btn" data-act="import" type="button">Importa backup</button></div>' +
      '<input type="file" id="import-file" accept="application/json,.json" hidden></section>';

    h += '<section class="card"><h3>Esercizi (' + state.exercises.length + ')</h3>' +
      '<div class="row gap wrap"><button class="btn" data-act="exercise-new" type="button">' + icon('plus', 'sm') + ' Nuovo</button>' +
      '<button class="btn" data-act="browse-catalog" type="button">' + icon('search', 'sm') + ' Catalogo con foto</button></div>' +
      '<ul class="list compact">';
    state.exercises.forEach((e) => {
      h += '<li><div style="flex:1;min-width:0"><b>' + esc(e.name) + '</b><div class="muted small">' +
        esc([e.muscle, e.equipment].filter(Boolean).join(' · ')) + '</div></div>' +
        '<button class="icon-btn" data-act="exercise-archive" data-id="' + e.id + '" aria-label="Archivia" type="button">' +
        icon('close') + '</button></li>';
    });
    h += '</ul></section>';

    h += '<section class="card"><h3>Zona pericolosa</h3>' +
      '<button class="btn danger wide" data-act="wipe" type="button">Cancella tutti i dati</button></section>';

    h += '<p class="muted small center">Palestra · funziona offline · foto esercizi da free-exercise-db (dominio pubblico)</p>';
    return h;
  }

  /* ================= render ================= */

  const TITLES = { oggi: 'Oggi', schede: 'Schede', storico: 'Storico', progressi: 'Progressi', impostazioni: 'Altro' };

  function render() {
    $('#view-title').textContent = TITLES[state.view] || '';
    $$('#tabbar button').forEach((b) => b.classList.toggle('active', b.dataset.view === state.view));
    const view = $('#view');
    if (state.view === 'oggi') { view.innerHTML = viewOggi(); if (!state.session) renderRecentInto(); }
    else if (state.view === 'schede') view.innerHTML = viewSchede();
    else if (state.view === 'storico') { view.innerHTML = viewStorico(); renderStoricoInto(); }
    else if (state.view === 'progressi') { view.innerHTML = viewProgressi(); renderProgressInto(); }
    else if (state.view === 'impostazioni') view.innerHTML = viewImpostazioni();
    window.scrollTo(0, 0);
  }

  // Qual e' l'ultimo esercizio che hai toccato: serve per aprire Progressi
  // su qualcosa di sensato invece che sul primo in ordine alfabetico.
  function loadLastTrained() {
    return DB.listSessions().then((rows) => {
      if (!rows.length) return null;
      return DB.setsOfSession(rows[0].id).then((sets) => {
        state.lastTrainedEx = sets.length ? sets[sets.length - 1].exerciseId : null;
      });
    });
  }

  const refresh = () => loadCore().then(loadSession).then(loadLastTrained).then(render);
  const go = (view) => { state.view = view; render(); };

  /* ================= catalogo ed esercizi ================= */

  function catalogListHtml(items) {
    if (!items.length) return '<p class="empty">Nessun esercizio trovato.</p>';
    let h = '<ul class="list pick" id="ex-pick">';
    items.slice(0, 80).forEach((it) => {
      const img = it.img && it.img.length ? Catalog.imageUrl(it.img[0]) : '';
      h += '<li data-cat="' + esc(it.id) + '"><div>' +
        (img ? '<img src="' + esc(img) + '" alt="" loading="lazy" decoding="async">' : '<span class="ph">' + icon('dumbbell') + '</span>') +
        '<div style="min-width:0"><b>' + esc(it.n) + '</b><div class="muted small">' +
        esc(it.m.join(', ') + ' · ' + it.eq) + '</div></div></div>' +
        '<button class="icon-btn" data-act="cat-detail" data-id="' + esc(it.id) + '" aria-label="Dettagli" type="button">' +
        icon('info') + '</button></li>';
    });
    if (items.length > 80) h += '<li class="muted small">…e altri ' + (items.length - 80) + '. Affina la ricerca.</li>';
    return h + '</ul>';
  }

  function mineListHtml(query) {
    const q = (query || '').toLowerCase();
    const items = state.exercises.filter((e) => !q || e.name.toLowerCase().indexOf(q) !== -1);
    if (!items.length) return '<p class="empty">Nessun esercizio fra i tuoi. Cerca nel catalogo.</p>';
    let h = '<ul class="list pick" id="ex-pick">';
    items.forEach((e) => {
      const img = thumbFor(e);
      h += '<li data-pick="' + e.id + '"><div>' +
        (img ? '<img src="' + esc(img) + '" alt="" loading="lazy" decoding="async">' : '<span class="ph">' + icon('dumbbell') + '</span>') +
        '<div style="min-width:0"><b>' + esc(e.name) + '</b><div class="muted small">' +
        esc([e.muscle, e.equipment].filter(Boolean).join(' · ')) + '</div></div></div></li>';
    });
    return h + '</ul>';
  }

  let pickHandler = null;

  function pickExerciseModal(onPick, title) {
    pickHandler = onPick;
    const body =
      '<div class="seg" id="pick-tabs">' +
      '<button class="' + (state.pickTab === 'mine' ? 'on' : '') + '" data-tab="mine" type="button">I miei</button>' +
      '<button class="' + (state.pickTab === 'catalog' ? 'on' : '') + '" data-tab="catalog" type="button">Catalogo con foto</button>' +
      '</div>' +
      '<label class="field" style="margin-top:12px">Cerca<input class="search" id="ex-search" type="search" ' +
      'placeholder="panca, stacco, curl…" autocomplete="off"></label>' +
      '<div id="pick-filters"></div>' +
      '<div id="pick-list"></div>' +
      '<button class="btn wide" data-act="exercise-new" type="button">' + icon('plus', 'sm') + ' Crea esercizio a mano</button>';
    openModal(title || 'Aggiungi esercizio', body);
    renderPickList();
    $('#ex-search').addEventListener('input', debounce(renderPickList, 180));
  }

  function debounce(fn, ms) {
    let t = null;
    return function () { clearTimeout(t); t = setTimeout(fn, ms); };
  }

  function renderPickList() {
    const listBox = $('#pick-list');
    const filterBox = $('#pick-filters');
    if (!listBox) return;
    const q = $('#ex-search') ? $('#ex-search').value : '';

    if (state.pickTab === 'mine') {
      filterBox.innerHTML = '';
      listBox.innerHTML = mineListHtml(q);
      return;
    }

    if (!Catalog.loaded()) {
      listBox.innerHTML = '<p class="muted">Carico il catalogo (876 esercizi)…</p>';
      Catalog.load().then(() => renderPickList()).catch((e) => {
        listBox.innerHTML = '<p class="empty">Catalogo non disponibile offline la prima volta: ' + esc(e.message) +
          '<br>Collegati a internet una volta sola, poi resta salvato.</p>';
      });
      return;
    }

    const fm = $('#f-muscle') ? $('#f-muscle').value : '';
    const fe = $('#f-eq') ? $('#f-eq').value : '';
    if (!$('#f-muscle')) {
      filterBox.innerHTML = '<div class="filters">' +
        '<select id="f-muscle" data-act="pick-filter"><option value="">Tutti i muscoli</option>' +
        Catalog.muscles().map((m) => '<option>' + esc(m) + '</option>').join('') + '</select>' +
        '<select id="f-eq" data-act="pick-filter"><option value="">Tutti gli attrezzi</option>' +
        Catalog.equipment().map((m) => '<option>' + esc(m) + '</option>').join('') + '</select></div>';
    }
    listBox.innerHTML = catalogListHtml(Catalog.search(q, { muscle: fm, equipment: fe }));
  }

  function catalogDetailModal(catalogId, backToPick) {
    const it = Catalog.get(catalogId);
    if (!it) return;
    let h = '';
    if (it.img.length) {
      h += '<div class="ex-gallery">' + it.img.map((i) =>
        '<img src="' + esc(Catalog.imageUrl(i)) + '" alt="Esecuzione di ' + esc(it.n) + '" loading="lazy" decoding="async">').join('') + '</div>';
    }
    h += '<p class="muted">' + esc(it.m.join(', ')) + (it.s.length ? ' · secondari: ' + esc(it.s.join(', ')) : '') +
      '<br>' + esc(it.eq) + ' · ' + esc(it.cat) + ' · ' + esc(it.lvl) + (it.f ? ' · ' + esc(it.f) : '') + '</p>';
    if (it.ins.length) {
      h += '<h3>Esecuzione</h3><ol class="steps">' + it.ins.map((i) => '<li>' + esc(i) + '</li>').join('') + '</ol>' +
        '<p class="muted small">Istruzioni in inglese: vengono dal dataset originale, non sono state tradotte a macchina per non storpiarle.</p>';
    }
    h += '<button class="btn primary wide" data-act="cat-add" data-id="' + esc(it.id) + '" type="button">' +
      (backToPick ? 'Aggiungi all allenamento' : 'Aggiungi ai miei esercizi') + '</button>';
    openModal(it.n, h);
  }

  // Crea (o ritrova) l'esercizio locale corrispondente a una scheda del catalogo.
  function ensureExerciseFromCatalog(catalogId) {
    const existing = state.exercises.filter((e) => e.catalogId === catalogId)[0];
    if (existing) return Promise.resolve(existing);
    const it = Catalog.get(catalogId);
    if (!it) return Promise.reject(new Error('Esercizio non trovato nel catalogo'));
    return DB.createExercise({
      name: it.n,
      muscle: it.m[0] || 'Altro',
      equipment: it.eq,
      unit: Catalog.unitFor(it),
      catalogId: it.id,
      img: it.img && it.img.length ? it.img[0] : null
    }).then((ex) => loadCore().then(() => ex));
  }

  function exerciseDetailModal(exerciseId) {
    const ex = state.exMap[exerciseId];
    if (!ex) return;
    if (ex.catalogId && Catalog.loaded()) { catalogDetailModal(ex.catalogId, false); return; }
    openModal(ex.name, '<p class="muted">' + esc([ex.muscle, ex.equipment].filter(Boolean).join(' · ')) +
      '</p><p class="muted small">Questo esercizio non e collegato al catalogo, quindi non ha foto.</p>');
  }

  function newExerciseModal(afterCreate) {
    const muscles = ['Petto', 'Schiena', 'Gambe', 'Spalle', 'Braccia', 'Core', 'Altro'];
    openModal('Nuovo esercizio',
      '<form id="new-ex-form">' +
      '<label class="field">Nome<input name="name" required maxlength="60" placeholder="Es. Panca stretta"></label>' +
      '<label class="field">Gruppo muscolare<select name="muscle">' + muscles.map((m) => '<option>' + m + '</option>').join('') + '</select></label>' +
      '<label class="field">Attrezzo<input name="equipment" maxlength="40" placeholder="Bilanciere, manubri, cavi…"></label>' +
      '<label class="field">Come lo misuri<select name="unit">' +
      '<option value="kg">Carico in kg × ripetizioni</option>' +
      '<option value="bw">Corpo libero (kg = zavorra)</option>' +
      '<option value="time">A tempo (secondi)</option></select></label>' +
      '<button class="btn primary wide" type="submit">Crea</button></form>');
    $('#new-ex-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.target;
      DB.createExercise({ name: f.name.value, muscle: f.muscle.value, equipment: f.equipment.value, unit: f.unit.value })
        .then((ex) => {
          closeModal();
          toast('Esercizio creato');
          return loadCore().then(() => { if (afterCreate) afterCreate(ex.id); else render(); });
        }).catch((e) => toast(e.message, true));
    });
  }

  function editSetModal(setId) {
    const s = state.sets.filter((x) => x.id === setId)[0];
    if (!s) return;
    const ex = state.exMap[s.exerciseId];
    const u = unitLabels(ex);
    openModal('Modifica serie',
      '<form id="edit-set-form"><p class="muted">' + esc(ex ? ex.name : '') + '</p><div class="row gap">' +
      '<label class="field">' + u.w + '<input name="weight" type="number" step="0.5" min="0" value="' + s.weight + '"></label>' +
      '<label class="field">' + u.r + '<input name="reps" type="number" step="1" min="0" value="' + s.reps + '"></label>' +
      '<label class="field">RPE<input name="rpe" type="number" step="0.5" min="5" max="10" value="' + (s.rpe == null ? '' : s.rpe) + '"></label>' +
      '</div><label class="chk big"><input type="checkbox" name="warmup"' + (s.warmup ? ' checked' : '') + '> Serie di riscaldamento</label>' +
      '<label class="field">Nota<input name="note" maxlength="140" value="' + esc(s.note || '') + '"></label>' +
      '<div class="row gap"><button class="btn primary" type="submit">Salva</button>' +
      '<button class="btn danger" type="button" data-act="del-set" data-id="' + s.id + '">Elimina serie</button></div></form>');
    $('#edit-set-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.target;
      s.weight = Number(f.weight.value) || 0;
      s.reps = Number(f.reps.value) || 0;
      s.rpe = f.rpe.value === '' ? null : Number(f.rpe.value);
      s.warmup = f.warmup.checked;
      s.note = f.note.value;
      DB.updateSet(s).then(() => { closeModal(); toast('Serie aggiornata'); return refresh(); });
    });
  }

  /* ================= battito: interfaccia ================= */

  function hrHelpModal() {
    openModal('Battito cardiaco: come collegarlo',
      '<h3>Apple Watch (via Salute)</h3>' +
      '<p class="muted">Nessun browser puo leggere HealthKit: non esiste un API web per farlo, ne su Safari ne altrove. ' +
      'Il giro che funziona davvero e questo, e si fa una volta sola.</p>' +
      '<ol class="steps">' +
      '<li>Allenati con l app <b>Allenamento</b> dell Apple Watch, come fai di solito.</li>' +
      '<li>Su iPhone apri <b>Comandi rapidi</b> e creane uno nuovo.</li>' +
      '<li>Azione <b>Trova campioni di salute</b> (Find Health Samples): tipo <b>Frequenza cardiaca</b>, ' +
      'filtro sulla data di inizio (es. ultime 24 ore), ordinati per data.</li>' +
      '<li>Azione <b>Ripeti con ciascuno</b> e dentro <b>Ottieni dettagli del campione</b>: prendi <b>Valore</b> e <b>Data di inizio</b>. ' +
      'Formatta la data come <code>yyyy-MM-dd HH:mm:ss</code>.</li>' +
      '<li>Componi un testo con una riga per campione: <code>data,valore</code>. Poi <b>Salva file</b>.</li>' +
      '<li>Torna qui: <b>Altro → Importa da Salute</b> e scegli quel file.</li>' +
      '</ol>' +
      '<p class="muted small">I nomi delle azioni cambiano leggermente fra le versioni di iOS. ' +
      'L import accetta JSON o CSV, con date ISO oppure in formato italiano: se il tuo file ha una colonna data e una valore, funziona.</p>' +
      '<h3>Fascia cardio Bluetooth</h3>' +
      '<p class="muted">Si collega in diretta e vedi i bpm mentre ti alleni. Serve un browser con Bluetooth (Chrome su Android, Mac, Windows): ' +
      'Safari su iPhone non lo espone. Vale anche per l Apple Watch se usi un app che lo fa trasmettere come cardiofrequenzimetro.</p>' +
      '<p class="muted small">Stato qui: Bluetooth ' + (HR.supported() ? 'disponibile' : 'non disponibile in questo browser') + '.</p>');
  }

  function hrManualModal() {
    const cur = (state.session && state.session.hr) || {};
    openModal('Battito a mano',
      '<form id="hr-manual-form"><p class="muted">Leggi i valori sull orologio a fine allenamento e scrivili qui.</p>' +
      '<div class="row gap">' +
      '<label class="field">Medio<input name="avg" type="number" min="30" max="230" value="' + (cur.avg || '') + '"></label>' +
      '<label class="field">Massimo<input name="max" type="number" min="30" max="230" value="' + (cur.max || '') + '"></label>' +
      '</div><button class="btn primary wide" type="submit">Salva</button></form>');
    $('#hr-manual-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      const f = ev.target;
      const avg = Number(f.avg.value) || 0;
      const max = Number(f.max.value) || 0;
      if (!avg && !max) { toast('Metti almeno un valore', true); return; }
      state.session.hr = { src: 'manual', avg: avg || max, max: max || avg, min: null, n: 0, samples: [] };
      DB.put('sessions', state.session).then(() => { closeModal(); toast('Battito salvato'); return refresh(); });
    });
  }

  function hrConnect() {
    toast('Cerco il sensore…');
    HR.connect().then((name) => { toast('Collegato: ' + name); render(); })
      .catch((e) => toast(e.message || 'Collegamento annullato', true));
  }

  // Aggiorna solo il numero, senza ridisegnare tutta la vista.
  HR.onChange((bpm) => {
    const box = $('#hr-live');
    if (!box) return;
    const el = box.querySelector('.bpm');
    if (el) el.textContent = bpm || '--';
    const z = HR.zone(bpm, state.settings && state.settings.age);
    const badge = box.querySelector('.zone-badge');
    if (badge && z) badge.textContent = 'Z' + z.n + ' ' + z.label;
  });

  function saveLiveHrToSession(session) {
    const samples = HR.takeLive();
    if (!samples.length) return Promise.resolve(session);
    const st = HR.stats(samples);
    if (!st) return Promise.resolve(session);
    session.hr = {
      src: 'ble', avg: st.avg, max: st.max, min: st.min, n: st.n,
      samples: HR.downsample(samples).map((x) => [x.t, x.bpm])
    };
    return DB.put('sessions', session).then(() => session);
  }

  function doHrImport(file) {
    const reader = new FileReader();
    reader.onload = () => {
      let samples;
      try { samples = HR.parseFile(String(reader.result)); }
      catch (e) { toast(e.message, true); return; }
      if (!samples.length) { toast('Nel file non ho trovato campioni leggibili', true); return; }
      DB.listSessions().then((sessions) => {
        const touched = HR.attachToSessions(samples, sessions);
        if (!touched.length) {
          toast(samples.length + ' campioni letti, ma nessuno cade dentro un allenamento registrato', true);
          return;
        }
        return DB.putMany('sessions', touched).then(() => {
          toast('Battito aggiunto a ' + touched.length + ' allenamenti');
          return refresh();
        });
      });
    };
    reader.readAsText(file);
  }

  /* ================= azioni varie ================= */

  function startRoutine(routineId) {
    const r = state.routines.filter((x) => x.id === routineId)[0];
    if (!r) return;
    DB.startSession({
      name: r.name,
      routineId: r.id,
      plan: (r.items || []).map((i) => ({ exerciseId: i.exerciseId, sets: i.sets, reps: i.reps }))
    }).then(() => { state.view = 'oggi'; HR.resetLive(); toast('Buon allenamento'); return refresh(); });
  }

  function addExerciseToSession(exerciseId) {
    const s = state.session;
    if (!s) return Promise.resolve();
    s.plan = s.plan || [];
    if (!s.plan.some((p) => p.exerciseId === exerciseId)) s.plan.push({ exerciseId, sets: '', reps: '' });
    return DB.put('sessions', s).then(refresh);
  }

  function addExerciseToRoutine(routineId, exerciseId) {
    const r = state.routines.filter((x) => x.id === routineId)[0];
    if (!r) return Promise.resolve();
    r.items = r.items || [];
    r.items.push({ exerciseId, sets: 3, reps: '8-12', note: '' });
    return DB.put('routines', r).then(() => loadCore()).then(render);
  }

  function doExport() {
    DB.exportAll().then((data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'palestra-backup-' + new Date().toISOString().slice(0, 10) + '.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast('Backup esportato');
    }).catch((e) => toast(e.message, true));
  }

  function doImport(file) {
    const reader = new FileReader();
    reader.onload = () => {
      let data;
      try { data = JSON.parse(reader.result); }
      catch (e) { toast('File JSON non valido', true); return; }
      const mode = confirm('OK = sostituisci tutti i dati con il backup.\nAnnulla = unisci il backup a quello che c e gia.')
        ? 'replace' : 'merge';
      DB.importAll(data, mode)
        .then((n) => { toast('Importati ' + n.sessions + ' allenamenti e ' + n.sets + ' serie'); return refresh(); })
        .catch((e) => toast(e.message, true));
    };
    reader.readAsText(file);
  }

  /* ================= eventi ================= */

  function onSubmit(ev) {
    const form = ev.target.closest('form[data-act="add-set"]');
    if (!form) return;
    ev.preventDefault();
    const reps = form.reps.value;
    if (reps === '' || Number(reps) <= 0) { toast('Metti almeno le ripetizioni', true); form.reps.focus(); return; }
    DB.addSet({
      sessionId: state.session.id,
      exerciseId: form.dataset.ex,
      weight: form.weight.value,
      reps: reps,
      rpe: form.rpe.value,
      warmup: form.warmup.checked,
      note: form.note.value
    }).then(() => {
      Rest.unlock();
      if (state.settings.autoRest && !form.warmup.checked) Rest.start(state.settings.restSeconds);
      return DB.setsOfSession(state.session.id).then((sets) => { state.sets = sets; render(); });
    });
  }

  function onClick(ev) {
    const tab = ev.target.closest('#pick-tabs button[data-tab]');
    if (tab) {
      state.pickTab = tab.dataset.tab;
      $$('#pick-tabs button').forEach((b) => b.classList.toggle('on', b === tab));
      $('#pick-filters').innerHTML = '';
      renderPickList();
      return;
    }
    const pickLi = ev.target.closest('#ex-pick li[data-pick]');
    if (pickLi && pickHandler) { const fn = pickHandler; closeModal(); fn(pickLi.dataset.pick); return; }
    const catLi = ev.target.closest('#ex-pick li[data-cat]');
    if (catLi && !ev.target.closest('[data-act="cat-detail"]')) {
      const fn = pickHandler;
      ensureExerciseFromCatalog(catLi.dataset.cat).then((ex) => { closeModal(); if (fn) fn(ex.id); else render(); })
        .catch((e) => toast(e.message, true));
      return;
    }

    const t = ev.target.closest('[data-act]');
    if (!t) return;
    const act = t.dataset.act;
    const id = t.dataset.id;

    switch (act) {
      case 'start-free':
        DB.startSession({ name: 'Allenamento libero' }).then(() => { state.view = 'oggi'; HR.resetLive(); return refresh(); });
        break;
      case 'start-routine':
        startRoutine(id);
        break;
      case 'end-session': {
        if (!confirm('Chiudere l allenamento?')) break;
        const sess = state.session;
        saveLiveHrToSession(sess)
          .then(() => DB.endSession(sess.id))
          .then(() => { Rest.stop(); HR.resetLive(); toast('Allenamento salvato'); return refresh(); });
        break;
      }
      case 'save-session-note':
        state.session.note = $('#session-note').value;
        DB.put('sessions', state.session).then(() => toast('Nota salvata'));
        break;
      case 'pick-exercise':
        pickExerciseModal((exId) => addExerciseToSession(exId));
        break;
      case 'browse-catalog':
        state.pickTab = 'catalog';
        pickExerciseModal(null, 'Catalogo esercizi');
        break;
      case 'cat-detail':
        catalogDetailModal(id, !!pickHandler);
        break;
      case 'cat-add': {
        const fn = pickHandler;
        ensureExerciseFromCatalog(id).then((ex) => {
          closeModal();
          if (fn) return fn(ex.id);
          toast('Aggiunto ai tuoi esercizi');
          return render();
        }).catch((e) => toast(e.message, true));
        break;
      }
      case 'ex-detail':
        exerciseDetailModal(id);
        break;
      case 'remove-ex':
        if (state.sets.some((s) => s.exerciseId === id)) { toast('Ha gia delle serie: cancellale prima', true); break; }
        state.session.plan = (state.session.plan || []).filter((p) => p.exerciseId !== id);
        DB.put('sessions', state.session).then(refresh);
        break;
      case 'edit-set':
        editSetModal(id);
        break;
      case 'del-set':
        DB.deleteSet(id).then(() => { closeModal(); toast('Serie eliminata'); return refresh(); });
        break;
      case 'routine-new': {
        const name = prompt('Nome della scheda', 'Nuova scheda');
        if (!name) break;
        DB.createRoutine(name).then(() => loadCore()).then(render);
        break;
      }
      case 'routine-rename': {
        const r = state.routines.filter((x) => x.id === id)[0];
        const name = prompt('Nome della scheda', r.name);
        if (!name) break;
        r.name = name;
        DB.put('routines', r).then(() => loadCore()).then(render);
        break;
      }
      case 'routine-del':
        if (!confirm('Eliminare la scheda? Gli allenamenti registrati restano.')) break;
        DB.del('routines', id).then(() => loadCore()).then(render);
        break;
      case 'routine-add-ex':
        pickExerciseModal((exId) => addExerciseToRoutine(id, exId), 'Aggiungi alla scheda');
        break;
      case 'item-edit': {
        const r = state.routines.filter((x) => x.id === id)[0];
        const i = Number(t.dataset.i);
        const sets = prompt('Quante serie?', r.items[i].sets);
        if (sets === null) break;
        const reps = prompt('Quante ripetizioni? (es. 8-10)', r.items[i].reps);
        if (reps === null) break;
        r.items[i].sets = sets;
        r.items[i].reps = reps;
        DB.put('routines', r).then(() => loadCore()).then(render);
        break;
      }
      case 'item-up':
      case 'item-down':
      case 'item-del': {
        const r = state.routines.filter((x) => x.id === id)[0];
        const i = Number(t.dataset.i);
        if (act === 'item-del') r.items.splice(i, 1);
        else {
          const j = act === 'item-up' ? i - 1 : i + 1;
          if (j < 0 || j >= r.items.length) break;
          const tmp = r.items[i]; r.items[i] = r.items[j]; r.items[j] = tmp;
        }
        DB.put('routines', r).then(() => loadCore()).then(render);
        break;
      }
      case 'session-del':
        if (!confirm('Eliminare questo allenamento e tutte le sue serie?')) break;
        DB.deleteSession(id).then(() => { toast('Allenamento eliminato'); return refresh(); });
        break;
      case 'progress-metric':
        state.progressMetric = t.dataset.metric;
        render();
        break;
      case 'exercise-new':
        newExerciseModal();
        break;
      case 'exercise-archive': {
        const ex = state.exMap[id];
        if (!confirm('Archiviare "' + ex.name + '"? Sparisce dalle liste, lo storico resta.')) break;
        ex.archived = true;
        DB.put('exercises', ex).then(() => loadCore()).then(render);
        break;
      }
      case 'hr-connect': hrConnect(); break;
      case 'hr-disconnect': HR.disconnect(); render(); break;
      case 'hr-manual': hrManualModal(); break;
      case 'hr-help': hrHelpModal(); break;
      case 'hr-import': $('#hr-file').click(); break;
      case 'export': doExport(); break;
      case 'import': $('#import-file').click(); break;
      case 'wipe':
        if (!confirm('Cancellare TUTTO (esercizi, schede, allenamenti)? Non si torna indietro.')) break;
        if (!confirm('Sicuro? Esporta un backup prima, se non l hai fatto.')) break;
        DB.clearAll().then(() => SEED.ensure()).then(() => { toast('Dati cancellati'); return refresh(); });
        break;
      default: break;
    }
  }

  function onChange(ev) {
    const t = ev.target;
    if (t.id === 'import-file' && t.files && t.files[0]) { doImport(t.files[0]); t.value = ''; return; }
    if (t.id === 'hr-file' && t.files && t.files[0]) { doHrImport(t.files[0]); t.value = ''; return; }
    const act = t.dataset ? t.dataset.act : null;
    if (!act) return;
    if (act === 'pick-filter') { renderPickList(); return; }
    if (act === 'progress-ex') { state.progressEx = t.value; renderProgressInto(); return; }
    const patch = {};
    if (act === 'set-rest') patch.restSeconds = Math.max(10, Math.min(600, Number(t.value) || 120));
    else if (act === 'set-sound') patch.sound = t.checked;
    else if (act === 'set-vibrate') patch.vibrate = t.checked;
    else if (act === 'set-autorest') patch.autoRest = t.checked;
    else if (act === 'set-age') patch.age = Number(t.value) || null;
    else return;
    DB.saveSettings(patch).then((s) => { state.settings = s; toast('Salvato'); });
  }

  /* ================= avvio ================= */

  // Aggancia le foto del catalogo agli esercizi creati dal seed.
  function backfillImages() {
    const todo = state.exercises.filter((e) => e.catalogId && !e.img);
    if (!todo.length) return Promise.resolve(false);
    const updated = [];
    todo.forEach((e) => {
      const it = Catalog.get(e.catalogId);
      if (it && it.img && it.img.length) { e.img = it.img[0]; updated.push(e); }
    });
    if (!updated.length) return Promise.resolve(false);
    return DB.putMany('exercises', updated).then(() => true);
  }

  function init() {
    document.addEventListener('click', onClick);
    document.addEventListener('submit', onSubmit);
    document.addEventListener('change', onChange);

    $('#tabbar').addEventListener('click', (ev) => {
      const b = ev.target.closest('button[data-view]');
      if (b) { Rest.unlock(); go(b.dataset.view); }
    });

    $('#modal-close').addEventListener('click', () => { pickHandler = null; closeModal(); });
    $('#modal-backdrop').addEventListener('click', () => { pickHandler = null; closeModal(); });
    document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') { pickHandler = null; closeModal(); } });

    $('#rest-skip').addEventListener('click', () => Rest.stop());
    $$('#rest-bar .rest-adj').forEach((b) => b.addEventListener('click', () => Rest.adjust(Number(b.dataset.adj))));

    // Durata e totali si aggiornano da soli mentre ti alleni.
    setInterval(() => {
      const line = $('#session-stats');
      if (line && state.session && !document.hidden) line.textContent = sessionStatsLine();
    }, 30000);

    return DB.open()
      .then(() => SEED.ensure())
      .then(() => refresh())
      .then(() => {
        // Il catalogo si carica in sottofondo: serve per foto e ricerca.
        Catalog.load()
          .then(() => backfillImages())
          .then((changed) => { if (changed) return loadCore().then(render); })
          .catch(() => { /* offline la prima volta: pazienza, riprova dopo */ });
      })
      .catch((e) => {
        $('#view').innerHTML = '<p class="empty">Il database locale non e disponibile: ' + esc(e.message) +
          '<br><br>Succede in navigazione privata o se il browser blocca i dati dei siti.</p>';
      });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  return { state, refresh, go };
})();

/* Service worker: installabile e utilizzabile senza rete. */
if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => { /* niente offline, pazienza */ });
  });
}
