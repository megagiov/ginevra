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
    lastUsed: {},          // exerciseId -> quando l'hai toccato l'ultima volta
    muscleFilter: '',
    logExId: null,         // esercizio aperto nel pannello di registrazione
    resumable: null,       // sessione chiusa da poco che si puo' riprendere
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

  // Solo per mostrare: in italiano i decimali vanno con la virgola.
  // Non usarla mai per riempire un campo numerico, che vuole il punto.
  function num(n) {
    const v = Number(n) || 0;
    return Math.abs(v % 1) > 0.001 ? v.toFixed(1).replace('.', ',') : String(Math.round(v));
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

  function giorniFa(ts) {
    const g = Math.floor((Date.now() - ts) / 86400000);
    if (g <= 0) return 'oggi';
    if (g === 1) return 'ieri';
    return g + ' giorni fa';
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
    let endAt = 0, iv = null, total = 0, audioCtx = null, ctxMode = null;
    let scheduled = [];          // oscillatori gia' programmati per il bip
    let beepArmed = false;       // il bip e' affidato all'orologio audio

    // Modalita' del suono: 'mix' suona sopra la musica senza fermarla ma
    // rispetta l'interruttore silenzioso; 'silent' suona anche col silenzioso
    // ma su iPhone puo' mettere in pausa la musica; 'off' niente.
    function mode() {
      const s = state.settings || {};
      if (s.soundMode) return s.soundMode;
      return s.sound === false ? 'off' : 'mix';
    }

    // Safari decide la categoria audio quando nasce il contesto: va impostata
    // prima. Senza, l'audio web finisce in 'ambient' e il silenzioso lo zittisce.
    function applySession() {
      try {
        if (navigator.audioSession) {
          navigator.audioSession.type = mode() === 'silent' ? 'playback' : 'transient';
        }
      } catch (e) { /* API non disponibile: pazienza */ }
    }

    function ctx() {
      if (mode() === 'off') return null;
      try {
        if (audioCtx && ctxMode !== mode()) {
          // Cambiata la modalita': il contesto va ricreato perche' conti.
          audioCtx.close().catch(() => {});
          audioCtx = null;
        }
        if (!audioCtx) {
          applySession();
          audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          ctxMode = mode();
        }
        if (audioCtx.state !== 'running') audioCtx.resume().catch(() => {});
        return audioCtx;
      } catch (e) { return null; }
    }

    // Tre bip programmati sull'orologio audio, non su un setInterval: cosi'
    // suonano puntuali anche se il browser rallenta i timer della pagina.
    function scheduleBeep(delaySec) {
      cancelBeep();
      const c = ctx();
      if (!c) return false;
      applySession();
      const t0 = c.currentTime + Math.max(0.05, delaySec);
      [0, 0.22, 0.44].forEach((off) => {
        const o = c.createOscillator();
        const g = c.createGain();
        o.type = 'sine';
        o.frequency.value = 880;
        g.gain.setValueAtTime(0.0001, t0 + off);
        g.gain.exponentialRampToValueAtTime(0.5, t0 + off + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, t0 + off + 0.16);
        o.connect(g); g.connect(c.destination);
        o.start(t0 + off);
        o.stop(t0 + off + 0.18);
        scheduled.push(o);
      });
      beepArmed = true;
      return true;
    }

    function cancelBeep() {
      scheduled.forEach((o) => { try { o.stop(); } catch (e) { /* gia' fermo */ } });
      scheduled = [];
      beepArmed = false;
    }

    function canVibrate() { return typeof navigator.vibrate === 'function'; }

    function buzz() {
      if (state.settings && state.settings.vibrate && canVibrate()) navigator.vibrate([200, 90, 200]);
    }

    // Su iPhone la vibrazione non esiste per le web app: al suo posto lo
    // schermo lampeggia, cosi' il segnale arriva comunque se lo stai guardando.
    function flash() {
      const f = $('#rest-flash');
      if (!f) return;
      f.hidden = false;
      f.classList.remove('go');
      void f.offsetWidth;          // riavvia l'animazione
      f.classList.add('go');
      setTimeout(() => { f.hidden = true; f.classList.remove('go'); }, 1600);
    }

    // Ogni tocco rianima l'audio: iOS lo sospende quando vuole.
    function unlock() { ctx(); }

    function paint() {
      const left = (endAt - Date.now()) / 1000;
      $('#rest-time').textContent = mmss(left);
      $('#rest-fill').style.width = (total > 0 ? Math.max(0, Math.min(1, left / total)) * 100 : 0).toFixed(1) + '%';
      // La barra fissa finisce sotto al pannello: qui il conto alla rovescia
      // si vede anche mentre registri la serie dopo.
      const sheet = $('#sheet-rest');
      if (sheet) {
        sheet.hidden = false;
        sheet.textContent = 'Recupero ' + mmss(left);
      }
      if (left <= 0) finish(false);
    }

    // late = ci si accorge della fine solo tornando all'app: niente bip in
    // ritardo, che suonerebbe a caso minuti dopo, solo il segnale visivo.
    function finish(late) {
      clearInterval(iv); iv = null;
      $('#rest-time').textContent = '00:00';
      $('#rest-fill').style.width = '0%';
      $('#rest-bar').classList.add('done');
      if (late) cancelBeep();
      else if (!beepArmed && mode() !== 'off') scheduleBeep(0);   // riserva
      beepArmed = false;
      scheduled = [];
      flash();
      buzz();
      setTimeout(stop, 2500);
    }

    function start(seconds) {
      total = seconds;
      endAt = Date.now() + seconds * 1000;
      $('#rest-bar').hidden = false;
      $('#rest-bar').classList.remove('done');
      document.body.classList.add('rest-on');
      scheduleBeep(seconds);
      paint();
      clearInterval(iv);
      iv = setInterval(paint, 250);
    }

    function stop() {
      clearInterval(iv); iv = null;
      cancelBeep();
      const sheet = $('#sheet-rest');
      if (sheet) sheet.hidden = true;
      $('#rest-bar').hidden = true;
      $('#rest-bar').classList.remove('done');
      document.body.classList.remove('rest-on');
    }

    function adjust(sec) {
      if ($('#rest-bar').hidden) return;
      endAt += sec * 1000;
      if (sec > 0) total += sec;
      if (endAt < Date.now()) endAt = Date.now();
      scheduleBeep((endAt - Date.now()) / 1000);
      paint();
    }

    // Tornando sull'app dopo aver bloccato lo schermo: se il recupero e'
    // finito nel frattempo lo chiudo senza bip tardivi.
    function resync() {
      if (!iv) return;
      if (Date.now() >= endAt) finish(true);
      else { scheduleBeep((endAt - Date.now()) / 1000); paint(); }
    }

    // Per il pulsante di prova nelle impostazioni.
    function test() {
      const ok = scheduleBeep(0.05);
      beepArmed = false;
      scheduled = [];
      flash();
      buzz();
      return { suono: ok, contesto: audioCtx ? audioCtx.state : 'assente',
        sessione: navigator.audioSession ? navigator.audioSession.type : 'non supportata',
        vibrazione: canVibrate() };
    }

    return { start, stop, adjust, unlock, resync, test, canVibrate, reset: () => { ctxMode = null; } };
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
    if (document.visibilityState !== 'visible') return;
    if (state.session && !wakeLock) keepAwake(true);
    Rest.resync();
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

  // L'ultimo momento in cui l'allenamento ha dato segni di vita: l'ultima
  // serie, l'avvio, oppure il momento in cui l'hai ripreso a mano.
  function lastActivity(session, sets) {
    let t = session.startedAt;
    if (sets && sets.length) t = Math.max(t, sets[sets.length - 1].ts);
    if (session.resumedAt) t = Math.max(t, session.resumedAt);
    return t;
  }

  function loadSession() {
    return DB.activeSession().then((s) => {
      if (!s) return finishLoad(null, []);
      return DB.setsOfSession(s.id).then((sets) => {
        const limit = (state.settings.autoCloseMinutes || 15) * 60000;
        const idle = Date.now() - lastActivity(s, sets);
        if (idle > limit) {
          // La chiudo all'ora dell'ultima serie, non adesso: cosi' la durata
          // nello storico resta quella vera.
          s.endedAt = lastActivity(s, sets);
          s.autoClosed = true;
          return DB.put('sessions', s).then(() => finishLoad(null, []));
        }
        return finishLoad(s, sets);
      });
    });
  }

  function finishLoad(session, sets) {
    state.session = session;
    state.sets = sets;
    keepAwake(!!session);
    return loadHistory().then(() => (session ? null : loadResumable()));
  }

  // Un allenamento chiuso da meno di due ore si puo' riprendere con un tocco:
  // serve quando la chiusura automatica scatta durante un recupero lungo.
  function loadResumable() {
    state.resumable = null;
    return DB.listSessions().then((rows) => {
      const last = rows.filter((r) => r.endedAt)[0];
      if (last && Date.now() - last.endedAt < 2 * 3600000) state.resumable = last;
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

  // Ultima volta, record precedente e ultimo utilizzo, per ogni esercizio.
  // Una sola lettura di tutte le serie: in locale e' piu' veloce di una query
  // per esercizio, e serve comunque l'elenco completo per ordinare la lista.
  function loadHistory() {
    return DB.getAll('sets').then((all) => {
      all.sort((a, b) => a.ts - b.ts);
      const byEx = {};
      all.forEach((x) => { (byEx[x.exerciseId] = byEx[x.exerciseId] || []).push(x); });

      state.lastPerf = {};
      state.bestPrior = {};
      state.lastUsed = {};
      const curId = state.session ? state.session.id : null;

      Object.keys(byEx).forEach((exId) => {
        const rows = byEx[exId];
        state.lastUsed[exId] = rows[rows.length - 1].ts;
        const past = rows.filter((r) => r.sessionId !== curId && !r.warmup);
        if (!past.length) return;
        const lastSid = past[past.length - 1].sessionId;
        const lastSets = past.filter((r) => r.sessionId === lastSid);
        state.lastPerf[exId] = { ts: lastSets[lastSets.length - 1].ts, sets: lastSets };
        state.bestPrior[exId] = past.reduce((b, x) => Math.max(b, e1rm(x.weight, x.reps)), 0);
      });
    });
  }

  /* ================= vista: Oggi (pannello principale) ================= */

  function viewOggi() {
    let h = '';
    if (state.session) h += sessionBar();
    else if (state.resumable) h += resumeBar();
    else h += '<p class="lead">Tocca l\u2019esercizio che stai per fare. L\u2019allenamento parte da solo.</p>';

    h += muscleChips();

    const groups = buildGroups();
    const totale = groups.reduce((t, g) => t + g.items.length, 0);
    if (!totale) {
      h += '<p class="empty">Nessun esercizio con questo filtro.</p>';
    } else {
      groups.forEach((g) => {
        if (!g.items.length) return;
        h += '<h2 class="group-title">' + esc(g.title) +
          ' <span class="group-count">' + g.items.length + '</span></h2>';
        h += '<ul class="ex-list">' + g.items.map((ex) => exRow(ex, g.kind)).join('') + '</ul>';
      });
    }

    h += '<button class="btn wide big-search" data-act="pick-exercise" type="button">' +
      icon('search') + ' Cerca un altro esercizio</button>';
    return h;
  }

  function sessionBar() {
    const s = state.session;
    return '<section class="session-bar"><div class="sb-main" data-act="session-details" role="button" tabindex="0">' +
      '<b>' + esc(s.name) + '</b>' +
      '<span class="muted small" id="session-stats">' + sessionStatsLine() + '</span></div>' +
      hrChip() +
      '<button class="btn danger" data-act="end-session" type="button">Termina</button></section>';
  }

  function resumeBar() {
    const r = state.resumable;
    const quando = fmtTime(r.endedAt);
    return '<section class="session-bar resume"><div class="sb-main">' +
      '<b>Allenamento chiuso alle ' + quando + '</b>' +
      '<span class="muted small">' + (r.autoClosed ? 'chiuso da solo per inattivit\u00e0' : 'chiuso da te') +
      ' · lo riprendi da dove eri</span></div>' +
      '<button class="btn primary" data-act="resume-session" data-id="' + r.id + '" type="button">Riprendi</button>' +
      '</section>';
  }

  function sessionStatsLine() {
    const s = state.session;
    if (!s) return '';
    return fmtDur(Date.now() - s.startedAt) + ' · ' +
      state.sets.filter((x) => !x.warmup).length + ' serie · ' + num(volume(state.sets)) + ' kg';
  }

  function hrChip() {
    if (HR.connected()) {
      return '<button class="hr-chip live" data-act="hr-options" type="button" id="hr-live">' +
        '<span class="beating">' + icon('heart', 'sm') + '</span><b class="bpm">' + (HR.bpm() || '--') + '</b></button>';
    }
    const s = state.session;
    if (s && s.hr) {
      return '<button class="hr-chip" data-act="hr-options" type="button">' +
        icon('heart', 'sm') + '<b>' + s.hr.avg + '</b></button>';
    }
    return '<button class="hr-chip empty" data-act="hr-options" type="button" aria-label="Battito cardiaco">' +
      icon('heart', 'sm') + '</button>';
  }

  // Chip per gruppo muscolare: solo quelli in cui hai davvero degli esercizi.
  function muscleChips() {
    const counts = {};
    state.exercises.forEach((e) => { counts[e.muscle] = (counts[e.muscle] || 0) + 1; });
    const keys = Object.keys(counts).sort((a, b) => a.localeCompare(b, 'it'));
    if (keys.length < 2) return '';
    let h = '<div class="chips">';
    h += '<button class="chip' + (state.muscleFilter ? '' : ' on') + '" data-act="filter-muscle" data-muscle="" type="button">Tutti</button>';
    keys.forEach((k) => {
      h += '<button class="chip' + (state.muscleFilter === k ? ' on' : '') +
        '" data-act="filter-muscle" data-muscle="' + esc(k) + '" type="button">' + esc(k) + '</button>';
    });
    return h + '</div>';
  }

  // Tre gruppi: quelli di oggi, quelli della scheda aperta, il resto per ultimo uso.
  function buildGroups() {
    const f = state.muscleFilter;
    const pass = (ex) => !f || ex.muscle === f;

    const oggiIds = [];
    state.sets.forEach((x) => { if (oggiIds.indexOf(x.exerciseId) === -1) oggiIds.push(x.exerciseId); });

    const planIds = [];
    if (state.session && state.session.plan) {
      state.session.plan.forEach((pl) => {
        if (oggiIds.indexOf(pl.exerciseId) === -1 && planIds.indexOf(pl.exerciseId) === -1) planIds.push(pl.exerciseId);
      });
    }

    const usati = state.exercises
      .filter((e) => oggiIds.indexOf(e.id) === -1 && planIds.indexOf(e.id) === -1 && state.lastUsed[e.id])
      .sort((a, b) => state.lastUsed[b.id] - state.lastUsed[a.id]);

    const mai = state.exercises
      .filter((e) => oggiIds.indexOf(e.id) === -1 && planIds.indexOf(e.id) === -1 && !state.lastUsed[e.id])
      .sort((a, b) => a.name.localeCompare(b.name, 'it'));

    const byId = (id) => state.exMap[id];
    return [
      { kind: 'oggi', title: 'Fatti oggi', items: oggiIds.map(byId).filter((e) => e && pass(e)) },
      {
        kind: 'plan',
        title: state.session && state.session.routineId ? 'Ancora da fare' : 'In programma',
        items: planIds.map(byId).filter((e) => e && pass(e))
      },
      { kind: 'recenti', title: 'Usati di recente', items: usati.filter(pass) },
      {
        kind: 'mai',
        title: Object.keys(state.lastUsed).length ? 'Mai usati' : 'I tuoi esercizi',
        items: mai.filter(pass)
      }
    ];
  }

  function exRow(ex, kind) {
    const thumb = thumbFor(ex);
    const last = state.lastPerf[ex.id];
    const oggi = state.sets.filter((x) => x.exerciseId === ex.id);
    const best = state.bestPrior[ex.id] || 0;

    let riga;
    if (kind === 'oggi' && oggi.length) riga = describeSets(oggi);
    else if (last) riga = describeSets(last.sets);
    else riga = 'mai registrato';

    let meta = '';
    if (kind === 'oggi' && oggi.length) meta = 'adesso';
    else if (last) meta = fmtDateShort(last.ts);
    if (best > 0) meta += (meta ? ' · ' : '') + 'record ' + num(best) + ' kg';

    return '<li class="ex-row" data-act="open-log" data-id="' + ex.id + '">' +
      (thumb
        ? '<img class="ex-thumb" src="' + esc(thumb) + '" alt="" loading="lazy" decoding="async">'
        : '<span class="ex-thumb ph">' + icon('dumbbell') + '</span>') +
      '<span class="ex-row-main">' +
        '<span class="ex-name">' + esc(ex.name) + '</span>' +
        '<span class="ex-last">' + esc(riga) + '</span>' +
        (meta ? '<span class="ex-meta">' + esc(meta) + '</span>' : '') +
      '</span>' +
      (oggi.length ? '<span class="ex-badge">' + oggi.filter((x) => !x.warmup).length + '</span>' : '') +
      '<span class="ex-go">' + icon('go') + '</span>' +
      '</li>';
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
        '<button class="btn primary" data-act="start-routine" data-id="' + r.id + '" type="button">' +
          (state.session ? 'Aggiungi all\u2019allenamento in corso' : 'Allenati con questa') + '</button>' +
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
          if (sets.length) {
            h += '<button class="btn wide share-btn" data-act="session-share" data-id="' + s.id + '" type="button">' +
              icon('share', 'sm') + ' Condividi su WhatsApp</button>';
          }
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
    const modo = s.soundMode || (s.sound === false ? 'off' : 'mix');
    let h = '<section class="card"><h3>' + icon('timer') + ' Recupero</h3>' +
      '<label class="field">Secondi di recupero predefiniti' +
      '<input type="number" min="10" max="600" step="5" value="' + s.restSeconds + '" data-act="set-rest"></label>' +
      '<label class="chk big"><input type="checkbox" data-act="set-autorest"' + (s.autoRest ? ' checked' : '') + '> Parte da solo quando registro una serie</label>' +
      '<label class="field">Suono a fine recupero<select data-act="set-soundmode">' +
      '<option value="mix"' + (modo === 'mix' ? ' selected' : '') + '>Normale: suona sopra la musica, tace col silenzioso</option>' +
      '<option value="silent"' + (modo === 'silent' ? ' selected' : '') + '>Anche col silenzioso: pu\u00f2 mettere in pausa la musica</option>' +
      '<option value="off"' + (modo === 'off' ? ' selected' : '') + '>Spento</option>' +
      '</select></label>';
    if (Rest.canVibrate()) {
      h += '<label class="chk big"><input type="checkbox" data-act="set-vibrate"' + (s.vibrate ? ' checked' : '') + '> Vibrazione a fine recupero</label>';
    } else {
      h += '<p class="note-ios"><b>Vibrazione: non disponibile su questo telefono.</b> Su iPhone Apple non la permette alle app web, in nessuna versione. ' +
        'Al suo posto, a fine recupero lo schermo lampeggia di verde.</p>';
    }
    h += '<p class="note-ios">Il segnale arriva solo se l\u2019app \u00e8 aperta e lo schermo acceso: col telefono bloccato in tasca il browser si ferma. ' +
      'Durante l\u2019allenamento l\u2019app chiede di tenere lo schermo acceso.</p>' +
      '<button class="btn" data-act="test-sound" type="button">' + icon('timer', 'sm') + ' Prova suono e segnale</button>' +
      '<div id="test-out"></div></section>';

    h += '<section class="card"><h3>' + icon('dumbbell') + ' Registrazione</h3>' +
      '<label class="field">Di quanto salgono i pulsanti + e \u2212' +
      '<select data-act="set-step">' +
      [1, 1.25, 2.5, 5].map((v) => '<option value="' + v + '"' + (Number(s.weightStep) === v ? ' selected' : '') +
        '>' + num(v) + ' kg</option>').join('') + '</select></label>' +
      '<label class="field">Chiudi l\u2019allenamento dopo tanti minuti senza registrare niente' +
      '<select data-act="set-autoclose">' +
      [15, 30, 60, 120, 240].map((v) => '<option value="' + v + '"' + (Number(s.autoCloseMinutes) === v ? ' selected' : '') +
        '>' + v + ' minuti' + (v === 15 ? ' (corto: un recupero lungo pu\u00f2 bastare a chiuderlo)' : '') + '</option>').join('') +
      '</select></label>' +
      '<p class="muted small">Se si chiude mentre ti stai ancora allenando, il tasto Riprendi in cima al pannello lo riapre dov\u2019era.</p>' +
      '</section>';

    h += '<section class="card"><h3>' + icon('pulse') + ' Battito cardiaco</h3>' +
      '<p class="muted">Importa qui il file che genera il Comando rapido di iPhone: i battiti si agganciano da soli agli allenamenti giusti confrontando gli orari.</p>' +
      '<label class="field">La tua eta (serve per le zone)<input type="number" min="12" max="99" value="' +
      (s.age || '') + '" placeholder="es. 38" data-act="set-age"></label>' +
      '<div class="row gap wrap"><button class="btn primary" data-act="hr-import" type="button">' + icon('upload', 'sm') + ' Importa da Salute</button>' +
      '<button class="btn" data-act="hr-help" type="button">Come si fa</button></div>' +
      '<input type="file" id="hr-file" accept=".json,.csv,.txt,application/json,text/csv,text/plain" hidden></section>';

    const ultimo = s.lastBackupAt
      ? 'Ultimo backup: ' + fmtDate(s.lastBackupAt) + ' (' + giorniFa(s.lastBackupAt) + ')'
      : 'Nessun backup fatto finora.';
    h += '<section class="card"><h3>' + icon('download') + ' Backup</h3>' +
      '<p class="muted">I dati stanno solo su questo telefono. Il file di backup \u00e8 la tua unica copia.</p>' +
      '<p class="note-ios"><b>Su iPhone:</b> premi Esporta, si apre il menu Condividi. Scorri le azioni e scegli ' +
      '<b>\u201cSalva su File\u201d</b>, poi <b>iCloud Drive</b>. Non scegliere le app nella fila in alto (AnyDesk, WhatsApp\u2026): ' +
      'quelle aprono il file, non lo salvano.</p>' +
      '<p class="muted small">' + esc(ultimo) + '</p>' +
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
    if (state.view === 'oggi') view.innerHTML = viewOggi();
    else if (state.view === 'schede') view.innerHTML = viewSchede();
    else if (state.view === 'storico') { view.innerHTML = viewStorico(); renderStoricoInto(); }
    else if (state.view === 'progressi') { view.innerHTML = viewProgressi(); renderProgressInto(); }
    // Il backup si rifa' a ogni apertura di Altro: una copia preparata prima
    // resterebbe ferma e lascerebbe fuori le serie registrate nel frattempo.
    else if (state.view === 'impostazioni') { view.innerHTML = viewImpostazioni(); preparaBackup(); }
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

  // Apre una sessione al volo quando registri la prima serie senza averne una.
  function ensureSession() {
    if (state.session) return Promise.resolve(state.session);
    return DB.startSession({ name: 'Allenamento' }).then((s) => {
      state.session = s;
      state.sets = [];
      keepAwake(true);
      return s;
    });
  }
  const go = (view) => { state.view = view; render(); };

  /* ================= pannello di registrazione ================= */

  function stepFor(ex, field) {
    if (field === 'reps') return (ex && ex.unit === 'time') ? 5 : 1;
    if (ex && ex.unit === 'bw') return 1;
    return Number(state.settings.weightStep) || 2.5;
  }

  function openLog(exerciseId) {
    const ex = state.exMap[exerciseId];
    if (!ex) return;
    state.logExId = exerciseId;
    const today = state.sets.filter((x) => x.exerciseId === exerciseId);
    const last = state.lastPerf[exerciseId];
    const prev = today.length
      ? today[today.length - 1]
      : (last && last.sets.length ? last.sets[last.sets.length - 1] : null);
    state.logDraft = {
      weight: prev ? prev.weight : 0,
      reps: prev ? prev.reps : (ex.unit === 'time' ? 30 : 8),
      rpe: null,
      warmup: false
    };
    openModal(ex.name, logBody());
    watchInfo();
  }

  function renderLog() {
    const box = $('#modal-body');
    if (box && state.logExId) { box.innerHTML = logBody(); watchInfo(); }
  }

  function watchInfo() {
    const d = $('#modal-body .ex-info');
    if (d) d.addEventListener('toggle', () => { state.logInfoOpen = d.open; });
  }

  function logBody() {
    const ex = state.exMap[state.logExId];
    const u = unitLabels(ex);
    const d = state.logDraft;
    const last = state.lastPerf[ex.id];
    const today = state.sets.filter((x) => x.exerciseId === ex.id);
    const best = state.bestPrior[ex.id] || 0;

    let h = '<div id="sheet-rest" hidden></div>';

    h += schedaInfo(ex, today);
    h += infoEsercizio(ex);

    h += '<p class="log-last">' + (last
      ? 'Ultima volta (' + fmtDateShort(last.ts) + '): <b>' + esc(describeSets(last.sets)) + '</b>'
      : 'Prima volta che lo registri.') +
      (best > 0 ? '<br>Record: <b>' + num(best) + ' kg</b> di massimale stimato' : '') + '</p>';

    h += stepper('weight', u.w.toUpperCase(), d.weight, ex);
    h += stepper('reps', u.r.toUpperCase(), d.reps, ex);

    h += '<div class="rpe-row"><div class="rpe-head"><span class="stepper-label">SFORZO (RPE)</span>' +
      '<label class="chk"><input type="checkbox" data-act="log-warmup"' + (d.warmup ? ' checked' : '') +
      '> riscaldamento</label></div><div class="chips">' +
      ['', '6', '7', '8', '9', '10'].map((v) =>
        '<button class="chip' + ((d.rpe == null ? '' : String(d.rpe)) === v ? ' on' : '') +
        '" data-act="set-rpe" data-v="' + v + '" type="button">' + (v === '' ? 'niente' : v) + '</button>'
      ).join('') + '</div></div>';


    h += '<button class="btn primary huge" data-act="log-save" type="button">' +
      (d.warmup ? 'Registra riscaldamento' : 'Registra serie') + '</button>';

    if (today.length) {
      h += '<h3 class="log-h3">Oggi</h3><ol class="sets">';
      let n = 0;
      today.forEach((x) => {
        if (!x.warmup) n++;
        const isPr = !x.warmup && best > 0 && e1rm(x.weight, x.reps) > best;
        h += '<li data-act="edit-set" data-id="' + x.id + '" class="' + (x.warmup ? 'warm' : '') + '">' +
          '<span class="n">' + (x.warmup ? 'r' : n) + '</span>' +
          '<span class="load"><b>' + num(x.weight) + '</b> ' + u.w + ' × <b>' + x.reps + '</b> ' + u.repWord + '</span>' +
          (isPr ? '<span class="tag pr">record</span>' : '') +
          (x.rpe ? '<span class="tag">RPE ' + num(x.rpe) + '</span>' : '') + '</li>';
      });
      h += '</ol><p class="muted small">' + today.filter((x) => !x.warmup).length + ' serie di lavoro · ' +
        num(volume(today)) + ' kg di volume</p>';
    }

    h += '<button class="btn wide" data-act="close-log" type="button">Fatto</button>';
    return h;
  }

  // Cosa dice la scheda su questo esercizio. Vale sia se l'hai aperto dalla
  // scheda sia se l'hai scelto dalla lista: basta che stia in una scheda.
  function schedaInfo(ex, today) {
    const fatte = today.filter((x) => !x.warmup).length;
    const piano = state.session && state.session.plan
      ? state.session.plan.filter((p) => p.exerciseId === ex.id && p.sets)[0]
      : null;
    if (piano) {
      const r = state.routines.filter((x) => x.id === (piano.routineId || state.session.routineId))[0];
      const obiettivo = Number(piano.sets) || 0;
      const pct = obiettivo ? Math.min(100, Math.round((fatte / obiettivo) * 100)) : 0;
      return '<div class="scheda-box"><div class="row between"><span class="sb-label">' +
        esc(r ? r.name : 'Scheda') + '</span><b>' + esc(piano.sets) + ' \u00d7 ' + esc(piano.reps) + '</b></div>' +
        '<div class="sb-track"><div class="sb-fill" style="width:' + pct + '%"></div></div>' +
        '<span class="sb-count">' + fatte + ' di ' + esc(piano.sets) + ' serie' +
        (obiettivo && fatte >= obiettivo ? ' \u00b7 fatto' : '') + '</span></div>';
    }
    const inSchede = state.routines
      .map((r) => ({ r, it: (r.items || []).filter((i) => i.exerciseId === ex.id)[0] }))
      .filter((x) => x.it);
    if (!inSchede.length) return '';
    return '<div class="scheda-box muted-box"><span class="sb-label">Nelle tue schede</span>' +
      inSchede.map((x) => '<div class="row between"><span>' + esc(x.r.name) + '</span><b>' +
        esc(x.it.sets) + ' \u00d7 ' + esc(x.it.reps) + '</b></div>').join('') + '</div>';
  }

  // Le foto restano sempre in vista: di molti esercizi e' la foto a dirti
  // cosa sono. Le istruzioni invece stanno chiuse, altrimenti il testo spinge
  // i pulsanti + e \u2212 fuori dallo schermo.
  function infoEsercizio(ex) {
    const it = ex.catalogId && Catalog.loaded() ? Catalog.get(ex.catalogId) : null;
    const foto = it && it.img.length ? it.img : (ex.img ? [ex.img] : []);
    let h = '';
    if (foto.length) {
      h += '<div class="ex-gallery log-photos">' + foto.slice(0, 2).map((f, i) =>
        '<img src="' + esc(Catalog.imageUrl(f)) + '" alt="' + esc(ex.name) + (foto.length > 1 ? (i ? ', fine movimento' : ', inizio movimento') : '') +
        '" loading="lazy" decoding="async">').join('') + '</div>';
    }
    if (it && (it.ins.length || it.m.length)) {
      h += '<details class="ex-info"' + (state.logInfoOpen ? ' open' : '') + '>' +
        '<summary><span>Istruzioni</span><span class="muted small">' + esc(it.m.join(', ')) + '</span></summary>' +
        (it.s.length ? '<p class="muted small">Muscoli secondari: ' + esc(it.s.join(', ')) + '</p>' : '') +
        (it.ins.length ? '<ol class="steps">' + it.ins.map((i) => '<li>' + esc(i) + '</li>').join('') + '</ol>' +
          '<p class="muted small">In inglese, come nel dataset originale.</p>' : '') +
        '</details>';
    }
    return h;
  }

  function stepper(field, label, value, ex) {
    const step = stepFor(ex, field);
    const unita = field === 'reps'
      ? (ex.unit === 'time' ? 'sec' : 'reps')
      : (ex.unit === 'bw' ? 'kg' : 'kg');
    return '<div class="stepper-block"><span class="stepper-label">' + esc(label) + '</span>' +
      '<div class="stepper">' +
      '<button class="step-btn" data-act="step" data-f="' + field + '" data-d="-1" type="button" aria-label="Meno ' + step + '">−</button>' +
      '<div class="step-val" data-act="edit-num" data-f="' + field + '" role="button" tabindex="0">' +
        '<span class="num" id="val-' + field + '">' + num(value) + '</span>' +
        '<span class="su">' + unita + '</span>' +
        '<input class="num-input" id="in-' + field + '" type="number" inputmode="decimal" step="' + step + '" min="0" hidden>' +
      '</div>' +
      '<button class="step-btn" data-act="step" data-f="' + field + '" data-d="1" type="button" aria-label="Piu ' + step + '">+</button>' +
      '</div></div>';
  }

  function stepValue(field, dir) {
    const ex = state.exMap[state.logExId];
    const step = stepFor(ex, field);
    const d = state.logDraft;
    d[field] = Math.max(0, Math.round((Number(d[field]) + dir * step) * 100) / 100);
    const el = $('#val-' + field);
    if (el) el.textContent = num(d[field]);
    if (state.settings.vibrate && navigator.vibrate) navigator.vibrate(12);
  }

  // Tocchi il numero e scrivi il valore esatto con la tastiera.
  function editNum(field) {
    const input = $('#in-' + field);
    if (!input) return;
    const box = input.parentElement;
    input.value = state.logDraft[field];
    input.hidden = false;
    box.classList.add('editing');
    input.focus();
    input.select();
    const commit = () => {
      const v = parseFloat(String(input.value).replace(',', '.'));
      if (!isNaN(v) && v >= 0) state.logDraft[field] = v;
      input.hidden = true;
      box.classList.remove('editing');
      const el = $('#val-' + field);
      if (el) el.textContent = num(state.logDraft[field]);
    };
    input.addEventListener('blur', commit, { once: true });
    input.addEventListener('keydown', (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); input.blur(); } });
  }

  function saveLogSet() {
    const d = state.logDraft;
    const exId = state.logExId;
    if (!d || !exId) return;
    if (!d.reps || d.reps <= 0) { toast('Metti almeno le ripetizioni', true); return; }
    ensureSession()
      .then(() => DB.addSet({
        sessionId: state.session.id,
        exerciseId: exId,
        weight: d.weight,
        reps: d.reps,
        rpe: d.rpe,
        warmup: d.warmup,
        note: ''
      }))
      .then(() => {
        Rest.unlock();
        if (state.settings.autoRest && !d.warmup) Rest.start(state.settings.restSeconds);
        return DB.setsOfSession(state.session.id);
      })
      .then((sets) => {
        state.sets = sets;
        state.lastUsed[exId] = Date.now();
        state.resumable = null;
        d.warmup = false;          // la prossima e' una serie di lavoro
        // Peso e ripetizioni restano (di solito si ripetono), lo sforzo no: e'
        // un giudizio su quella serie e non va copiato su quella dopo.
        d.rpe = null;
        renderLog();
        render();                  // aggiorna la lista dietro al pannello
      });
  }

  function sessionDetailsModal() {
    const s = state.session;
    if (!s) return;
    openModal('Allenamento',
      '<form id="sess-form">' +
      '<label class="field">Nome<input name="name" maxlength="60" value="' + esc(s.name) + '"></label>' +
      '<label class="field">Nota<textarea name="note" rows="3" placeholder="Com\u2019\u00e8 andata, cosa cambiare la prossima volta">' +
      esc(s.note || '') + '</textarea></label>' +
      '<button class="btn primary wide" type="submit">Salva</button></form>');
    $('#sess-form').addEventListener('submit', (ev) => {
      ev.preventDefault();
      s.name = ev.target.name.value.trim() || 'Allenamento';
      s.note = ev.target.note.value;
      DB.put('sessions', s).then(() => { closeModal(); toast('Salvato'); return refresh(); });
    });
  }

  function hrOptionsModal() {
    let h = '<p class="muted">Tre modi, scegli quello che ti viene comodo.</p><div class="stack">';
    if (HR.connected()) {
      h += '<button class="btn wide" data-act="hr-disconnect" type="button">Scollega il sensore</button>';
    } else if (HR.supported()) {
      h += '<button class="btn primary wide" data-act="hr-connect" type="button">' +
        icon('bluetooth', 'sm') + ' Collega una fascia Bluetooth</button>';
    }
    h += '<button class="btn wide" data-act="hr-manual" type="button">Scrivi media e massimo a mano</button>';
    h += '<button class="btn wide" data-act="hr-help" type="button">Come si porta dentro da Salute</button>';
    return openModal('Battito cardiaco', h + '</div>');
  }

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
      '</p><p class="muted small">Questo esercizio non \u00e8 collegato al catalogo, quindi non ha foto.</p>');
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
      '<form id="hr-manual-form"><p class="muted">Leggi i valori sull\u2019orologio a fine allenamento e scrivili qui.</p>' +
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

  /* ================= condivisione su WhatsApp ================= */

  // Una serie scritta come la scrive chi allena: 80×8, @8 per l'RPE.
  function serieTesto(x, ex) {
    let t;
    if (ex && ex.unit === 'time') t = (x.weight > 0 ? num(x.weight) + ' kg ' : '') + x.reps + ' s';
    else if (!x.weight) t = x.reps + ' rip';
    else t = num(x.weight) + '×' + x.reps;
    if (x.rpe) t += ' @' + num(x.rpe);
    return t;
  }

  // Il messaggio per il personal. Grassetto con gli asterischi, che
  // WhatsApp rende da solo; niente fronzoli.
  function testoAllenamento(s, sets, bestPrima) {
    const lavoro = sets.filter((x) => !x.warmup);
    const ordine = [];
    sets.forEach((x) => { if (ordine.indexOf(x.exerciseId) === -1) ordine.push(x.exerciseId); });

    let titolo = s.name || 'Allenamento';
    if (/^Allenamento( libero)?$/.test(titolo)) {
      const gruppi = [];
      ordine.forEach((id) => {
        const m = state.exMap[id] && state.exMap[id].muscle;
        if (m && gruppi.indexOf(m) === -1) gruppi.push(m);
      });
      if (gruppi.length) titolo = 'Allenamento: ' + gruppi.join(', ');
    }
    const quando = new Date(s.startedAt).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' });
    const vol = Math.round(volume(sets));

    const r = [];
    r.push('*' + titolo + '*');
    r.push(quando.charAt(0).toUpperCase() + quando.slice(1) + ' · ' + fmtDur((s.endedAt || Date.now()) - s.startedAt));
    r.push(lavoro.length + ' serie · ' + vol.toLocaleString('it-IT') + ' kg sollevati');
    r.push('');

    ordine.forEach((id) => {
      const ex = state.exMap[id];
      const mie = sets.filter((x) => x.exerciseId === id);
      const risc = mie.filter((x) => x.warmup);
      const lav = mie.filter((x) => !x.warmup);
      r.push('*' + (ex ? ex.name : 'Esercizio') + '*');
      if (risc.length) r.push('risc. ' + risc.map((x) => serieTesto(x, ex)).join(' · '));
      if (lav.length) {
        const top = lav.reduce((b, x) => Math.max(b, e1rm(x.weight, x.reps)), 0);
        const prima = bestPrima[id] || 0;
        r.push(lav.map((x) => serieTesto(x, ex)).join(' · ') + (prima > 0 && top > prima ? '  — nuovo record' : ''));
      }
      mie.filter((x) => x.note).forEach((x) => r.push('_' + x.note + '_'));
      r.push('');
    });

    if (s.hr && s.hr.avg) r.push('Battito: media ' + s.hr.avg + (s.hr.max ? ', massimo ' + s.hr.max : ''));
    if (s.note) r.push('Nota: ' + s.note);
    return r.join('\n').trim();
  }

  // Senza numero, WhatsApp si apre col testo gia' scritto e chiede a chi
  // mandarlo: il contatto lo scegli tu.
  function linkWa(testo) {
    return 'https://wa.me/?text=' + encodeURIComponent(testo);
  }

  let testoDaCondividere = '';

  function condividiModal(sessionId) {
    Promise.all([DB.get('sessions', sessionId), DB.setsOfSession(sessionId), DB.getAll('sets')])
      .then(([s, sets, tutte]) => {
        if (!s || !sets.length) { toast('Allenamento vuoto: niente da condividere', true); return; }
        // record battuti: confronto con quello che avevi fatto PRIMA di quel giorno
        const bestPrima = {};
        tutte.forEach((x) => {
          if (x.warmup || x.ts >= s.startedAt) return;
          bestPrima[x.exerciseId] = Math.max(bestPrima[x.exerciseId] || 0, e1rm(x.weight, x.reps));
        });
        testoDaCondividere = testoAllenamento(s, sets, bestPrima);
        openModal('Condividi l\u2019allenamento',
          '<p class="muted small">Questo \u00e8 il testo che parte. Il grassetto lo mette WhatsApp.</p>' +
          '<pre class="share-preview">' + esc(testoDaCondividere) + '</pre>' +
          '<a class="btn primary wide wa-btn" href="' + esc(linkWa(testoDaCondividere)) + '" target="_blank" rel="noopener">' +
            'Invia su WhatsApp</a>' +
          '<p class="muted small center">Si apre WhatsApp col messaggio gi\u00e0 scritto: scegli tu la chat.</p>' +
          '<div class="row gap wrap">' +
          (navigator.share ? '<button class="btn" data-act="share-other" type="button">' + icon('share', 'sm') + ' Altre app</button>' : '') +
          '<button class="btn" data-act="share-copy" type="button">Copia il testo</button></div>');
      });
  }

  function copiaTesto(t) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(t).then(() => toast('Testo copiato: incollalo nella chat'));
    }
    const ta = document.createElement('textarea');
    ta.value = t;
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); toast('Testo copiato: incollalo nella chat'); }
    catch (e) { toast('Non riesco a copiare: tieni premuto sul testo', true); }
    document.body.removeChild(ta);
    return Promise.resolve();
  }

  /* ================= azioni varie ================= */

  // Se un allenamento e' gia' aperto la scheda si aggiunge a quello: prima ne
  // apriva un secondo e lasciava il primo aperto per sempre.
  function startRoutine(routineId) {
    const r = state.routines.filter((x) => x.id === routineId)[0];
    if (!r) return;
    const piano = (r.items || []).map((i) => ({ exerciseId: i.exerciseId, sets: i.sets, reps: i.reps, routineId: r.id }));
    const s = state.session;
    if (s) {
      s.plan = s.plan || [];
      piano.forEach((pl) => { if (!s.plan.some((x) => x.exerciseId === pl.exerciseId)) s.plan.push(pl); });
      s.routineId = s.routineId || r.id;
      if (!s.name || s.name === 'Allenamento' || s.name === 'Allenamento libero') s.name = r.name;
      return DB.put('sessions', s).then(() => {
        state.view = 'oggi';
        toast('Scheda aggiunta all\u2019allenamento in corso');
        return refresh();
      });
    }
    DB.startSession({ name: r.name, routineId: r.id, plan: piano })
      .then(() => { state.view = 'oggi'; HR.resetLive(); toast('Buon allenamento'); return refresh(); });
  }

  // Mette l'esercizio in programma. Se non c'e' una sessione aperta non la
  // apre: nasce da sola quando registri la prima serie.
  function addExerciseToSession(exerciseId) {
    const s = state.session;
    if (!s) { state.lastUsed[exerciseId] = state.lastUsed[exerciseId] || 0; return loadCore().then(render); }
    s.plan = s.plan || [];
    if (!s.plan.some((p) => p.exerciseId === exerciseId)) s.plan.push({ exerciseId, sets: '', reps: '' });
    return DB.put('sessions', s).then(() => loadCore()).then(render);
  }

  function addExerciseToRoutine(routineId, exerciseId) {
    const r = state.routines.filter((x) => x.id === routineId)[0];
    if (!r) return Promise.resolve();
    r.items = r.items || [];
    r.items.push({ exerciseId, sets: 3, reps: '8-12', note: '' });
    return DB.put('routines', r).then(() => loadCore()).then(render);
  }

  // Il file di backup si prepara in anticipo, appena apri Altro: iPhone
  // concede il menu Condividi solo nell'istante del tocco, e leggere il
  // database dopo il tocco rischia di far scadere il permesso.
  let backupPronto = null;
  function preparaBackup() {
    backupPronto = null;
    return DB.exportAll().then((data) => {
      const nome = 'palestra-backup-' + new Date().toISOString().slice(0, 10) + '.json';
      const json = JSON.stringify(data, null, 2);
      backupPronto = { nome, json, file: new File([json], nome, { type: 'application/json' }) };
      return backupPronto;
    });
  }

  function segnaBackup() {
    return DB.saveSettings({ lastBackupAt: Date.now() }).then((st) => {
      state.settings = st;
      if (state.view === 'impostazioni') render();
    });
  }

  function scaricaFile(nome, json) {
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = nome;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  }

  function doExport() {
    const b = backupPronto;
    if (!b) {
      toast('Preparo il backup, ripremi tra un attimo');
      preparaBackup();
      return;
    }
    const puoCondividere = navigator.canShare && navigator.share && navigator.canShare({ files: [b.file] });
    if (puoCondividere) {
      navigator.share({ files: [b.file], title: 'Backup Palestra' })
        .then(() => { toast('Backup condiviso'); return segnaBackup(); })
        .catch((e) => {
          if (e && e.name === 'AbortError') return;     // hai chiuso tu il menu
          scaricaFile(b.nome, b.json);
          toast('Backup scaricato');
          return segnaBackup();
        })
        .then(() => preparaBackup());
      return;
    }
    scaricaFile(b.nome, b.json);
    toast('Backup scaricato');
    segnaBackup().then(() => preparaBackup());
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
    // I form rimasti (modifica serie, nuovo esercizio, battito) si gestiscono
    // da soli: qui non serve piu' intercettare la registrazione delle serie.
    void ev;
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
      case 'open-log':
        Rest.unlock();
        openLog(id);
        break;
      case 'close-log':
        state.logExId = null;
        closeModal();
        break;
      case 'step':
        stepValue(t.dataset.f, Number(t.dataset.d));
        break;
      case 'edit-num':
        if (!ev.target.closest('.num-input')) editNum(t.dataset.f);
        break;
      case 'set-rpe':
        state.logDraft.rpe = t.dataset.v === '' ? null : Number(t.dataset.v);
        $$('[data-act="set-rpe"]').forEach((b) => b.classList.toggle('on', b === t));
        break;
      case 'log-save':
        saveLogSet();
        break;
      case 'filter-muscle':
        state.muscleFilter = t.dataset.muscle || '';
        render();
        break;
      case 'resume-session':
        DB.reopenSession(id).then(() => { toast('Allenamento ripreso'); return refresh(); });
        break;
      case 'hr-options':
        hrOptionsModal();
        break;
      case 'session-share':
        condividiModal(id);
        break;
      case 'share-other':
        navigator.share({ text: testoDaCondividere }).catch(() => {});
        break;
      case 'share-copy':
        copiaTesto(testoDaCondividere);
        break;
      case 'test-sound': {
        const r = Rest.test();
        const out = $('#test-out');
        if (out) {
          out.className = 'test-out';
          out.textContent =
            'Suono: ' + (r.suono ? 'inviato' : 'spento nelle impostazioni') + '\n' +
            'Audio: ' + r.contesto + '\n' +
            'Categoria audio: ' + r.sessione + '\n' +
            'Vibrazione: ' + (r.vibrazione ? 'disponibile' : 'non disponibile su questo telefono') + '\n\n' +
            (r.suono
              ? 'Non hai sentito niente? Controlla l\u2019interruttore silenzioso sul lato del telefono e il volume. ' +
                'Se lo tieni sempre in silenzioso, scegli \u201cAnche col silenzioso\u201d qui sopra.'
              : '');
        }
        break;
      }
      case 'session-details':
        sessionDetailsModal();
        break;
      case 'start-free':
        DB.startSession({ name: 'Allenamento libero' }).then(() => { state.view = 'oggi'; HR.resetLive(); return refresh(); });
        break;
      case 'start-routine':
        startRoutine(id);
        break;
      case 'end-session': {
        if (!confirm('Chiudere l\u2019allenamento?')) break;
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
        pickExerciseModal((exId) => {
          state.muscleFilter = '';
          return addExerciseToSession(exId).then(() => openLog(exId));
        });
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
        if (state.sets.some((s) => s.exerciseId === id)) { toast('Ha gi\u00e0 delle serie: cancellale prima', true); break; }
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
        if (!confirm('Sicuro? Esporta un backup prima, se non l\u2019hai fatto.')) break;
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
    else if (act === 'set-step') patch.weightStep = Number(t.value) || 2.5;
    else if (act === 'set-soundmode') patch.soundMode = t.value;
    else if (act === 'set-autoclose') patch.autoCloseMinutes = Number(t.value) || 15;
    else if (act === 'log-warmup') {
      state.logDraft.warmup = t.checked;
      renderLog();
      return;
    }
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
    // Foto non raggiungibile (offline, CDN bloccato): metto l'icona al posto
    // dell'immagine rotta. L'evento error non risale, serve la fase di cattura.
    document.addEventListener('error', (ev) => {
      const t = ev.target;
      if (!t || t.tagName !== 'IMG') return;
      if (!t.classList.contains('ex-thumb') && !t.closest('#ex-pick')) return;
      const span = document.createElement('span');
      // Nel catalogo la miniatura ha una misura sua, nella lista un'altra.
      span.className = t.closest('#ex-pick') ? 'ph' : 'ex-thumb ph';
      span.innerHTML = '<svg class="ico" aria-hidden="true"><use href="#i-dumbbell"/></svg>';
      t.replaceWith(span);
    }, true);

    // iOS sospende l'audio quando vuole: ogni tocco lo rianima, cosi' il bip
    // di fine recupero trova il contesto pronto.
    document.addEventListener('pointerdown', () => Rest.unlock(), { passive: true });

    // Chiedo al browser di non cancellare i dati per fare spazio.
    try {
      if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(() => {});
    } catch (e) { /* non supportato */ }

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
      if (document.hidden) return;
      const line = $('#session-stats');
      if (line && state.session) line.textContent = sessionStatsLine();
      // Se resti fermo troppo a lungo l'allenamento si chiude da solo.
      if (state.session) {
        const limit = (state.settings.autoCloseMinutes || 15) * 60000;
        if (Date.now() - lastActivity(state.session, state.sets) > limit) refresh();
      }
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
        $('#view').innerHTML = '<p class="empty">Il database locale non \u00e8 disponibile: ' + esc(e.message) +
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
