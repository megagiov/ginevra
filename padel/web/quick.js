// "Aggiungi veloce": legge il punteggio scritto in una riga e i dati del
// battito copiati dal Comando rapido di fine allenamento. Funzioni pure,
// testate con `node --test`.

import { setsWon, setsLost, winnerBySets } from './engine.js';

// ---- Punteggio ---------------------------------------------------------------

const DASH = '[-–—/:]';
const SET_RE = new RegExp(
  String.raw`\[\s*(\d{1,2})\s*${DASH}\s*(\d{1,2})\s*\]` +                       // [10-8]
  String.raw`|(\d{1,2})\s*${DASH}\s*(\d{1,2})` +                                 // 6-4
  String.raw`(?:\s*\(\s*(\d{1,2})(?:\s*${DASH}\s*(\d{1,2}))?\s*\))?`,            // (5) o (7-5)
  'g');

/**
 * "6-4 3-6 7-5", "6/4, 6-7(5), [10-8]", "7-6 (7-3) 6-2".
 * Restituisce { sets, format, winner, warning } oppure { error }.
 */
export function parseScore(text) {
  const src = String(text ?? '').trim();
  if (!src) return { error: 'Scrivi il punteggio, per esempio 6-4 3-6 7-5.' };

  const sets = [];
  let m;
  SET_RE.lastIndex = 0;
  while ((m = SET_RE.exec(src))) {
    const raw = m[0].trim();
    let set;
    if (m[1] != null) {
      set = superTiebreak(+m[1], +m[2], raw);
    } else {
      const a = +m[3], b = +m[4];
      set = Math.max(a, b) >= 8 ? superTiebreak(a, b, raw) : regularSet(a, b, m[5], m[6], raw);
    }
    if (set.error) return set;
    sets.push(set);
  }

  const leftover = src.replace(SET_RE, ' ').replace(/[\s,;.]+|\bset\b/gi, '');
  if (leftover) return { error: `Non capisco "${leftover}". Scrivi i set come 6-4 3-6 7-5.` };
  if (!sets.length) return { error: 'Non trovo nessun set. Scrivi per esempio 6-4 3-6 7-5.' };
  if (sets.length > 3) return { error: 'Al massimo 3 set.' };

  // Ordine dei set: dopo 2 set vinti la partita e' finita; il super
  // tie-break si gioca solo sull'1-1, come terzo set.
  for (let i = 0; i < sets.length; i++) {
    const before = sets.slice(0, i);
    if (setsWon(before) === 2 || setsLost(before) === 2) {
      return { error: `La partita era già finita prima del set ${i + 1}.` };
    }
    if (sets[i].isSuperTiebreak && !(i === 2 && setsWon(before) === 1 && setsLost(before) === 1)) {
      return { error: 'Il super tie-break si scrive per terzo, dopo un set a testa.' };
    }
  }

  const winner = winnerBySets(sets);
  const complete = setsWon(sets) === 2 || setsLost(sets) === 2;
  return {
    sets,
    format: sets.some((s) => s.isSuperTiebreak) ? 'twoSetsSuperTiebreak' : 'bestOfThree',
    winner: complete ? winner : null,
    warning: complete ? null : 'Nessuno ha vinto 2 set: la partita non conterà nelle statistiche.',
  };
}

function regularSet(a, b, tb1, tb2, raw) {
  const hi = Math.max(a, b), lo = Math.min(a, b);
  const ok = (hi === 6 && lo <= 4) || (hi === 7 && (lo === 5 || lo === 6));
  if (!ok) return { error: `"${raw}" non è un set valido (6-0…6-4, 7-5 o 7-6).` };
  const set = { us: a, them: b, isSuperTiebreak: false };
  if (tb1 == null) return set;
  if (lo !== 6) return { error: `"${raw}": i punti del tie-break vanno solo su un 7-6.` };
  const weWon = a > b;
  let win, lose;
  if (tb2 != null) {
    // (7-5): punti di chi ha vinto il set per primi, come si scrive di solito.
    win = Math.max(+tb1, +tb2); lose = Math.min(+tb1, +tb2);
  } else {
    // (5): solo i punti di chi l'ha perso.
    lose = +tb1; win = Math.max(7, lose + 2);
  }
  if (win < 7 || win - lose < 2) return { error: `"${raw}": un tie-break si vince a 7 con 2 punti di scarto.` };
  set.tiebreakUs = weWon ? win : lose;
  set.tiebreakThem = weWon ? lose : win;
  return set;
}

function superTiebreak(a, b, raw) {
  const hi = Math.max(a, b), lo = Math.min(a, b);
  if (hi < 10 || hi - lo < 2 || (hi > 10 && hi - lo !== 2)) {
    return { error: `"${raw}" non è un super tie-break valido (a 10, con 2 punti di scarto).` };
  }
  return { us: a > b ? 1 : 0, them: a > b ? 0 : 1, tiebreakUs: a, tiebreakThem: b, isSuperTiebreak: true };
}

// ---- Dati dal Watch (appunti) -------------------------------------------------

const MESI = { gen: 0, feb: 1, mar: 2, apr: 3, mag: 4, giu: 5, lug: 6, ago: 7, set: 8, ott: 9, nov: 10, dic: 11 };

/** Stesse date che legge Palestra: italiano di Comandi rapidi, gg/mm/aaaa, ISO, epoch. */
export function parseDate(v) {
  if (v == null) return NaN;
  if (typeof v === 'number') return v < 1e11 ? v * 1000 : v;
  const s = String(v).trim();
  if (/^\d+$/.test(s)) { const n = Number(s); return n < 1e11 ? n * 1000 : n; }
  const it = s.match(/^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})[,\s]+(\d{1,2}):(\d{2})(?::(\d{2}))?/);
  if (it) return new Date(+it[3], +it[2] - 1, +it[1], +it[4], +it[5], +(it[6] || 0)).getTime();
  const itl = s.toLowerCase().match(/^(\d{1,2})\s+([a-zà-ú]+)\.?\s+(\d{4})(?:\s*,|\s+alle(?:\s+ore)?)?\s+(\d{1,2})[:.](\d{2})(?:[:.](\d{2}))?/);
  if (itl && MESI[itl[2].slice(0, 3)] != null) {
    return new Date(+itl[3], MESI[itl[2].slice(0, 3)], +itl[1], +itl[4], +itl[5], +(itl[6] || 0)).getTime();
  }
  const t = Date.parse(s);
  return isNaN(t) ? NaN : t;
}

const KCAL_RE = /(?:kcal|calorie|energia(?:\s+attiva)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*kcal/i;
// Oltre 3 minuti senza campioni non e' piu' la stessa sessione di gioco.
const GAP_MS = 3 * 60 * 1000;
const MIN_BLOCK_MS = 10 * 60 * 1000;

/**
 * Legge quello che il Comando rapido di fine allenamento copia negli appunti:
 * una riga per campione di battito ("25 set 2026 alle ore 18:03, 132") e,
 * facoltativa, una riga con le calorie ("kcal: 540").
 * Restituisce { start, end, duration (s), avg, max, samples, calories } o { error }.
 */
export function parseWatchPaste(text) {
  const lines = String(text ?? '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  let calories = null;
  const samples = [];
  for (const line of lines) {
    const k = line.match(KCAL_RE);
    if (k) { calories = Math.round(parseFloat((k[1] ?? k[2]).replace(',', '.'))); continue; }
    const m = line.match(/^(.*?)[\s,;|\t]+(\d{2,3}(?:[.,]\d+)?)\s*(?:bpm|battiti\/min|count\/min|conteggio\/min)?\s*$/i);
    if (!m) continue;
    const t = parseDate(m[1].replace(/[\s,;|]+$/, ''));
    const v = parseFloat(m[2].replace(',', '.'));
    if (!isNaN(t) && v >= 25 && v <= 250) samples.push({ t, bpm: Math.round(v) });
  }
  if (samples.length < 2) {
    if (calories != null) return { calories };
    return { error: 'Negli appunti non trovo i dati del battito. Lancia prima il Comando rapido di fine allenamento.' };
  }
  samples.sort((a, b) => a.t - b.t);

  // Le "ultime 3 ore" possono comprendere anche il riscaldamento o il viaggio:
  // durante un allenamento il Watch misura ogni pochi secondi, fuori ogni
  // qualche minuto. Tengo l'ultimo tratto fitto, se e' abbastanza lungo.
  let from = samples.length - 1;
  while (from > 0 && samples[from].t - samples[from - 1].t <= GAP_MS) from--;
  const block = samples[samples.length - 1].t - samples[from].t >= MIN_BLOCK_MS ? samples.slice(from) : samples;

  const bpms = block.map((s) => s.bpm);
  return {
    start: block[0].t,
    end: block[block.length - 1].t,
    duration: Math.round((block[block.length - 1].t - block[0].t) / 1000),
    avg: Math.round(bpms.reduce((a, b) => a + b, 0) / bpms.length),
    max: Math.max(...bpms),
    samples: block.length,
    calories,
  };
}

