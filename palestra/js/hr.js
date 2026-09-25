/* Battito cardiaco.
 *
 * Tre strade, perche' nessuna copre tutti i casi:
 *
 * 1) SALUTE DI APPLE (Apple Watch) — via Comandi rapidi.
 *    Nessun browser puo' leggere HealthKit: non esiste un'API web per farlo.
 *    Il giro che funziona e': un Comando rapido legge i campioni di frequenza
 *    cardiaca da Salute, li salva in un file JSON, e tu lo importi qui. I
 *    battuti vengono agganciati da soli agli allenamenti giusti confrontando
 *    gli orari. Istruzioni nel README.
 *
 * 2) FASCIA BLUETOOTH IN DIRETTA — via Web Bluetooth (servizio standard
 *    0x180D). Funziona su Chrome/Edge (Android, Mac, Windows), NON su Safari
 *    iOS. Serve una fascia cardio o un Apple Watch con un'app che lo faccia
 *    trasmettere come cardiofrequenzimetro BLE.
 *
 * 3) A MANO — media e massimo letti dall'orologio e scritti a mano.
 */
const HR = (function () {
  const HR_SERVICE = 0x180D;
  const HR_CHAR = 0x2A37;
  const MIN_GAP_MS = 3000;   // non registro piu' di un campione ogni 3 secondi

  let device = null;
  let charac = null;
  let live = [];             // [{t, bpm}] della sessione in corso
  let current = null;
  let listeners = [];

  function supported() {
    return !!(navigator.bluetooth && navigator.bluetooth.requestDevice);
  }

  function onChange(fn) { listeners.push(fn); }
  function emit() { listeners.forEach((fn) => { try { fn(current, device && device.gatt.connected); } catch (e) { /* */ } }); }

  function parseValue(dv) {
    const flags = dv.getUint8(0);
    return (flags & 0x01) ? dv.getUint16(1, true) : dv.getUint8(1);
  }

  function handle(ev) {
    const bpm = parseValue(ev.target.value);
    if (!bpm || bpm < 25 || bpm > 250) return;
    current = bpm;
    const now = Date.now();
    if (!live.length || now - live[live.length - 1].t >= MIN_GAP_MS) live.push({ t: now, bpm });
    emit();
  }

  function connect() {
    if (!supported()) {
      return Promise.reject(new Error('Questo browser non espone il Bluetooth (su iPhone Safari non lo fa). Usa l import da Salute.'));
    }
    return navigator.bluetooth.requestDevice({
      filters: [{ services: [HR_SERVICE] }],
      optionalServices: [HR_SERVICE]
    }).then((d) => {
      device = d;
      device.addEventListener('gattserverdisconnected', () => { current = null; emit(); });
      return d.gatt.connect();
    }).then((server) => server.getPrimaryService(HR_SERVICE))
      .then((svc) => svc.getCharacteristic(HR_CHAR))
      .then((c) => {
        charac = c;
        c.addEventListener('characteristicvaluechanged', handle);
        return c.startNotifications();
      }).then(() => { emit(); return device.name || 'Sensore'; });
  }

  function disconnect() {
    try {
      if (charac) charac.removeEventListener('characteristicvaluechanged', handle);
      if (device && device.gatt.connected) device.gatt.disconnect();
    } catch (e) { /* */ }
    device = null; charac = null; current = null;
    emit();
  }

  function connected() { return !!(device && device.gatt && device.gatt.connected); }
  function bpm() { return current; }

  function takeLive() { const out = live.slice(); live = []; return out; }
  function liveSamples() { return live.slice(); }
  function resetLive() { live = []; }

  /* ---------- statistiche ---------- */

  function stats(samples) {
    const vals = samples.map((s) => s.bpm).filter((v) => v > 0);
    if (!vals.length) return null;
    const sum = vals.reduce((a, b) => a + b, 0);
    return {
      avg: Math.round(sum / vals.length),
      max: Math.max.apply(null, vals),
      min: Math.min.apply(null, vals),
      n: vals.length
    };
  }

  // Zone classiche in percentuale della frequenza massima stimata (220 - eta').
  function zone(bpmValue, age) {
    if (!age || !bpmValue) return null;
    const hrMax = 220 - age;
    const pct = bpmValue / hrMax;
    if (pct < 0.6) return { n: 1, label: 'Riscaldamento', pct };
    if (pct < 0.7) return { n: 2, label: 'Brucia grassi', pct };
    if (pct < 0.8) return { n: 3, label: 'Aerobica', pct };
    if (pct < 0.9) return { n: 4, label: 'Soglia', pct };
    return { n: 5, label: 'Massimale', pct };
  }

  /* ---------- import da Salute ---------- */

  function parseDate(v) {
    if (v == null) return NaN;
    if (typeof v === 'number') return v < 1e11 ? v * 1000 : v;
    const s = String(v).trim();
    if (/^\d+$/.test(s)) { const n = Number(s); return n < 1e11 ? n * 1000 : n; }
    // gg/mm/aaaa hh:mm(:ss) — formato italiano
    const it = s.match(/^(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})[,\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?/);
    if (it) {
      return new Date(+it[3], +it[2] - 1, +it[1], +it[4], +it[5], +(it[6] || 0)).getTime();
    }
    // "25 set 2026 alle ore 18:03", "25 settembre 2026, 18:03:12": e' quello
    // che scrive Comandi rapidi se non gli si chiede un formato preciso.
    const mesi = { gen: 0, feb: 1, mar: 2, apr: 3, mag: 4, giu: 5, lug: 6, ago: 7, set: 8, ott: 9, nov: 10, dic: 11 };
    const itl = s.toLowerCase().match(/^(\d{1,2})\s+([a-z\u00e0-\u00fa]+)\.?\s+(\d{4})(?:\s*,|\s+alle(?:\s+ore)?)?\s+(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?/);
    if (itl && mesi[itl[2].slice(0, 3)] != null) {
      return new Date(+itl[3], mesi[itl[2].slice(0, 3)], +itl[1], +itl[4], +itl[5], +(itl[6] || 0)).getTime();
    }
    const t = Date.parse(s);
    return isNaN(t) ? NaN : t;
  }

  function pick(obj, keys) {
    for (let i = 0; i < keys.length; i++) {
      const k = Object.keys(obj).find((o) => o.toLowerCase().replace(/[\s_-]/g, '') === keys[i]);
      if (k != null && obj[k] !== '' && obj[k] != null) return obj[k];
    }
    return null;
  }

  const DATE_KEYS = ['date', 'startdate', 'start', 'time', 'timestamp', 'datetime', 'data', 'ora', 'inizio', 't'];
  const VAL_KEYS = ['value', 'bpm', 'heartrate', 'hr', 'battito', 'frequenza', 'valore', 'count'];

  function fromRows(rows) {
    const out = [];
    rows.forEach((r) => {
      if (Array.isArray(r) && r.length >= 2) {
        const t = parseDate(r[0]);
        const v = parseFloat(String(r[1]).replace(',', '.'));
        if (!isNaN(t) && v > 0) out.push({ t, bpm: Math.round(v) });
        return;
      }
      if (r && typeof r === 'object') {
        const t = parseDate(pick(r, DATE_KEYS));
        const raw = pick(r, VAL_KEYS);
        const v = parseFloat(String(raw == null ? '' : raw).replace(',', '.'));
        if (!isNaN(t) && v > 0) out.push({ t, bpm: Math.round(v) });
      }
    });
    return out.sort((a, b) => a.t - b.t);
  }

  // Una riga per campione: il valore e' l'ultimo numero della riga, la data
  // e' tutto quello che c'e' prima. Regge anche date con dentro la virgola.
  function parseLines(lines) {
    const out = [];
    lines.forEach((l) => {
      const m = l.trim().match(/^(.*?)[\s,;|\t]+(\d{2,3}(?:[.,]\d+)?)\s*(?:bpm|battiti\/min|count\/min|conteggio\/min)?\s*$/i);
      if (!m) return;
      const t = parseDate(m[1].replace(/[\s,;|]+$/, ''));
      const v = parseFloat(m[2].replace(',', '.'));
      if (!isNaN(t) && v >= 25 && v <= 250) out.push({ t, bpm: Math.round(v) });
    });
    return out.sort((a, b) => a.t - b.t);
  }

  function parseCsv(text) {
    const lines = text.split(/\r?\n/).filter((l) => l.trim());
    if (!lines.length) return [];
    // Prima prova riga per riga: e' il formato del Comando rapido.
    const righe = parseLines(lines);
    if (righe.length >= Math.max(1, Math.floor(lines.length * 0.6))) return righe;
    const sep = (lines[0].match(/;/g) || []).length > (lines[0].match(/,/g) || []).length ? ';' : ',';
    const head = lines[0].split(sep).map((h) => h.trim().replace(/^"|"$/g, ''));
    const headerLooksLikeData = !isNaN(parseDate(head[0])) && head.length >= 2 && !isNaN(parseFloat(head[1]));
    const rows = [];
    const start = headerLooksLikeData ? 0 : 1;
    for (let i = start; i < lines.length; i++) {
      const cells = lines[i].split(sep).map((c) => c.trim().replace(/^"|"$/g, ''));
      if (headerLooksLikeData) { rows.push(cells); continue; }
      const obj = {};
      head.forEach((h, j) => { obj[h] = cells[j]; });
      rows.push(obj);
    }
    return fromRows(rows);
  }

  // Accetta quello che produce Comandi rapidi: JSON, CSV, o righe "data, valore".
  function parseFile(text) {
    const trimmed = text.trim();
    if (!trimmed) return [];
    if (trimmed[0] === '[' || trimmed[0] === '{') {
      let json;
      try { json = JSON.parse(trimmed); }
      catch (e) { throw new Error('JSON non valido: ' + e.message); }
      let rows = json;
      if (!Array.isArray(rows)) {
        rows = json.samples || json.data || json.items || json.heartRate || json.values || null;
        if (!rows) throw new Error('Nel JSON non trovo la lista dei campioni (mi aspetto un array).');
      }
      return fromRows(rows);
    }
    return parseCsv(trimmed);
  }

  // Riduce i campioni: uno ogni 15 secondi basta e avanza per il grafico.
  function downsample(samples, everyMs) {
    const step = everyMs || 15000;
    const out = [];
    samples.forEach((s) => {
      if (!out.length || s.t - out[out.length - 1].t >= step) out.push(s);
    });
    return out;
  }

  // Aggancia i campioni agli allenamenti confrontando gli orari.
  function attachToSessions(samples, sessions) {
    const result = [];
    sessions.forEach((s) => {
      const from = s.startedAt;
      const to = s.endedAt || Date.now();
      const mine = samples.filter((x) => x.t >= from - 60000 && x.t <= to + 60000);
      if (mine.length < 2) return;
      const st = stats(mine);
      s.hr = {
        src: 'health',
        avg: st.avg, max: st.max, min: st.min, n: st.n,
        samples: downsample(mine).map((x) => [x.t, x.bpm])
      };
      result.push(s);
    });
    return result;
  }

  return {
    supported, connect, disconnect, connected, bpm, onChange,
    takeLive, liveSamples, resetLive,
    stats, zone, parseFile, parseDate, attachToSessions, downsample
  };
})();
