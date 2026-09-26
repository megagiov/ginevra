// node --test padel/web/
import test from 'node:test';
import assert from 'node:assert/strict';
import { parseScore, parseWatchPaste, parseDate } from './quick.js';

const ok = (text) => {
  const r = parseScore(text);
  assert.equal(r.error, undefined, `${text}: ${r.error}`);
  return r;
};
const bad = (text, pattern) => {
  const r = parseScore(text);
  assert.ok(r.error, `${text} doveva essere rifiutato`);
  if (pattern) assert.match(r.error, pattern);
};

test('punteggi semplici, separatori diversi', () => {
  for (const t of ['6-4 6-3', '6/4, 6/3', '6:4 ; 6:3', '6–4 6–3', ' 6 - 4   6 - 3 ', 'set 6-4 set 6-3']) {
    const r = ok(t);
    assert.deepEqual(r.sets.map((s) => [s.us, s.them]), [[6, 4], [6, 3]], t);
    assert.equal(r.winner, 'us');
    assert.equal(r.format, 'bestOfThree');
  }
});

test('tre set e sconfitta', () => {
  const r = ok('6-4 3-6 5-7');
  assert.equal(r.winner, 'them');
  assert.equal(r.sets.length, 3);
});

test('tie-break: (5) = punti di chi perde, (7-5) espliciti', () => {
  let r = ok('7-6(5) 6-4');
  assert.deepEqual([r.sets[0].tiebreakUs, r.sets[0].tiebreakThem], [7, 5]);
  r = ok('6-7(10) 6-4 6-2');
  assert.deepEqual([r.sets[0].tiebreakUs, r.sets[0].tiebreakThem], [10, 12]);
  r = ok('7-6 (7-3) 6-2');
  assert.deepEqual([r.sets[0].tiebreakUs, r.sets[0].tiebreakThem], [7, 3]);
  r = ok('6-7 (3-7) 7-5 6-4');
  assert.deepEqual([r.sets[0].tiebreakUs, r.sets[0].tiebreakThem], [3, 7]);
  r = ok('7-6 6-4');
  assert.equal(r.sets[0].tiebreakUs, undefined, 'senza dettaglio resta vuoto');
});

test('super tie-break, con o senza parentesi quadre', () => {
  for (const t of ['6-4 3-6 [10-8]', '6-4 3-6 10-8', '6/4 3/6 [12-10]']) {
    const r = ok(t);
    assert.equal(r.format, 'twoSetsSuperTiebreak', t);
    assert.equal(r.sets[2].isSuperTiebreak, true);
    assert.equal(r.winner, 'us');
  }
  const r = ok('4-6 6-3 [7-10]');
  assert.equal(r.winner, 'them');
  assert.deepEqual([r.sets[2].tiebreakUs, r.sets[2].tiebreakThem], [7, 10]);
});

test('partita non finita: accettata con avviso', () => {
  const r = ok('6-4 3-6');
  assert.equal(r.winner, null);
  assert.match(r.warning, /statistiche/);
  assert.equal(ok('6-2').warning !== null, true);
});

test('errori chiari', () => {
  bad('', /Scrivi il punteggio/);
  bad('ciao', /Non capisco/);
  bad('6-5 6-4', /non è un set valido/);
  bad('8-6 6-4', /super tie-break/);
  bad('6-4 6-4 6-4', /già finita/);
  bad('[10-8] 6-4 6-3', /per terzo/);
  bad('6-4 6-3 [10-8]', /già finita/);
  bad('6-4(5) 6-3', /solo su un 7-6/);
  bad('7-6(7-6) 6-3', /2 punti di scarto/);
  bad('6-4 3-6 [11-8]', /super tie-break valido/);
  bad('6-4 3-6 [10-9]', /super tie-break valido/);
  bad('6-4 e 6-3', /Non capisco "e"/);
});

// ---- Dati dal Watch --------------------------------------------------------

// Genera righe come le scrive Comandi rapidi, in italiano.
const MESI = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
const riga = (d, bpm) => `${d.getDate()} ${MESI[d.getMonth()]} ${d.getFullYear()} alle ore ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}, ${bpm}`;

test('date nei formati di Comandi rapidi', () => {
  const ref = new Date(2026, 8, 25, 18, 3, 12).getTime();
  assert.equal(parseDate('25 set 2026 alle ore 18:03:12'), ref);
  assert.equal(parseDate('25 settembre 2026, 18:03:12'), ref);
  assert.equal(parseDate('25/09/2026 18:03:12'), ref);
  assert.equal(parseDate(String(ref / 1000)), ref);
});

test('battito: tiene solo il blocco fitto della partita', () => {
  const lines = [];
  const start = new Date(2026, 8, 25, 17, 0, 0);
  // Prima della partita: un campione ogni 8 minuti.
  for (let i = 0; i < 6; i++) lines.push(riga(new Date(start.getTime() + i * 8 * 60000), 80));
  // Partita: dalle 18:00 alle 19:30, un campione ogni 5 secondi, bpm 120..160.
  const g0 = new Date(2026, 8, 25, 18, 0, 0).getTime();
  for (let s = 0; s <= 90 * 60; s += 5) lines.push(riga(new Date(g0 + s * 1000), 120 + (s % 41)));
  lines.push('kcal: 612');
  const r = parseWatchPaste(lines.join('\n'));
  assert.equal(r.error, undefined);
  assert.equal(r.start, g0);
  assert.equal(r.duration, 90 * 60);
  assert.equal(r.max, 160);
  assert.ok(r.avg > 125 && r.avg < 160, `media ${r.avg}`);
  assert.equal(r.calories, 612);
});

test('battito: blocco corto, usa tutti i campioni', () => {
  const g0 = new Date(2026, 8, 25, 18, 0, 0).getTime();
  const lines = [0, 5, 10].map((m) => riga(new Date(g0 + m * 60000), 100 + m));
  const r = parseWatchPaste(lines.join('\n'));
  assert.equal(r.duration, 10 * 60);
  assert.equal(r.avg, 105);
});

test('appunti senza dati utili', () => {
  assert.match(parseWatchPaste('ciao').error, /Comando rapido/);
  assert.match(parseWatchPaste('').error, /Comando rapido/);
  assert.deepEqual(parseWatchPaste('Calorie: 480'), { calories: 480 });
  const r = parseWatchPaste('540 kcal\n25/09/2026 18:00:00, 110 bpm\n25/09/2026 18:40:00, 150 bpm');
  assert.equal(r.calories, 540, 'la riga delle calorie non diventa un battito');
  assert.equal(r.max, 150);
});
