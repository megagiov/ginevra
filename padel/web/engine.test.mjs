// Stessi scenari dei test Swift. Esegui con: node --test padel/web/
import test from 'node:test';
import assert from 'node:assert/strict';
import * as E from './engine.js';

const US = E.US, THEM = E.THEM;
const m = (deuceRule = 'goldenPoint', format = 'bestOfThree', firstServer = US) =>
  E.newMatch({ deuceRule, format, firstServer, indoor: false });
const pts = (x, t, n) => { for (let i = 0; i < n; i++) E.point(x, t); };
const game = (x, t) => pts(x, t, 4);
const games = (x, us, them) => {
  let u = 0, t = 0;
  while (u < us || t < them) {
    if (u < us) { game(x, US); u++; }
    if (t < them) { game(x, THEM); t++; }
  }
};

test('game normale', () => {
  const x = m();
  E.point(x, US); E.point(x, US); E.point(x, THEM); E.point(x, US);
  assert.equal(E.pointLabel(x, US), '40');
  assert.equal(E.pointLabel(x, THEM), '15');
  assert.equal(E.point(x, US), 'game');
  assert.equal(x.state.gamesUs, 1);
});

test('vantaggi', () => {
  const x = m('advantages');
  pts(x, US, 3); pts(x, THEM, 3);
  assert.equal(E.statusLabel(x), 'Parità');
  E.point(x, US);
  assert.equal(E.pointLabel(x, US), 'AD');
  E.point(x, THEM);
  assert.equal(E.pointLabel(x, THEM), '40');
  E.point(x, THEM);
  assert.equal(E.point(x, THEM), 'game');
});

test("punto d'oro", () => {
  const x = m('goldenPoint');
  pts(x, US, 3); pts(x, THEM, 3);
  assert.equal(E.statusLabel(x), "Punto d'oro");
  assert.equal(E.point(x, THEM), 'game');
});

test('set 6-4 e 7-5', () => {
  const a = m();
  games(a, 6, 4);
  assert.deepEqual(a.state.completedSets.map(E.setDisplay), ['6-4']);
  const b = m();
  games(b, 5, 5); game(b, US);
  assert.equal(b.state.completedSets.length, 0);
  game(b, US);
  assert.deepEqual(b.state.completedSets.map(E.setDisplay), ['7-5']);
});

test('tie-break 7-6 con due punti di scarto', () => {
  const x = m();
  games(x, 6, 6);
  assert.equal(x.state.mode, 'tiebreak');
  pts(x, US, 6); pts(x, THEM, 6); E.point(x, US);
  assert.equal(x.state.completedSets.length, 0);
  assert.equal(E.point(x, US), 'set');
  assert.equal(E.setDisplay(x.state.completedSets[0]), '7-6 (8-6)');
});

test('super tie-break a 10 con 2 di scarto', () => {
  const x = m('goldenPoint', 'twoSetsSuperTiebreak');
  games(x, 6, 3); games(x, 2, 6);
  assert.equal(x.state.mode, 'superTiebreak');
  pts(x, US, 9); pts(x, THEM, 9); E.point(x, US);
  assert.equal(x.state.winner, null);
  E.point(x, THEM); E.point(x, THEM);
  assert.equal(E.point(x, THEM), 'match');
  assert.equal(E.setDisplay(x.state.completedSets[2]), '[10-12]');
});

test('rotazione del servizio: game, set e tie-break', () => {
  const x = m('goldenPoint', 'bestOfThree', THEM);
  pts(x, US, 3);
  assert.equal(x.state.server, THEM);
  E.point(x, US);
  assert.equal(x.state.server, US);

  const t = m();
  games(t, 6, 6);
  const seq = [t.state.server];
  for (let i = 0; i < 10; i++) { E.point(t, i % 2 ? THEM : US); seq.push(t.state.server); }
  assert.deepEqual(seq, [US, THEM, THEM, US, US, THEM, THEM, US, US, THEM, THEM]);

  const after = m();
  games(after, 6, 6);
  pts(after, US, 7);
  assert.equal(after.state.server, THEM, 'serve chi ha risposto per primo nel tie-break');
});

test('correzione manuale del servizio', () => {
  const x = m();
  E.setServer(x, THEM);
  game(x, US);
  assert.equal(x.state.server, US);
});

test('annulla illimitato e dopo la vittoria', () => {
  const x = m();
  games(x, 6, 0); games(x, 5, 0); pts(x, US, 3);
  assert.equal(E.point(x, US), 'match');
  assert.equal(E.point(x, THEM), 'ignored');
  E.undoLastPoint(x);
  assert.equal(x.state.winner, null);
  assert.equal(E.pointLabel(x, US), '40');
  while (E.canUndo(x)) E.undoLastPoint(x);
  assert.deepEqual(x.state, E.initialState(US));
});

test('statistiche e backup compatibile con Swift', () => {
  const a = E.newId(), b = E.newId();
  const win = [{ us: 6, them: 4 }, { us: 6, them: 3 }];
  const loss = [{ us: 4, them: 6 }, { us: 3, them: 6 }];
  const matches = [
    { id: E.newId(), date: '2026-01-05T18:00:00Z', partnerID: a, sets: win, duration: 3600 },
    { id: E.newId(), date: '2026-01-20T18:00:00Z', partnerID: a, sets: loss, duration: 3600 },
    { id: E.newId(), date: '2026-02-03T18:00:00Z', partnerID: a, sets: win, duration: 3600 },
    { id: E.newId(), date: '2026-02-09T18:00:00Z', partnerID: b, sets: win, duration: 3600 },
  ];
  const s = E.statistics(matches, { [a]: 'Anna', [b]: 'Bruno' }, 'allTime', new Date('2026-03-01'));
  assert.equal(s.played, 4);
  assert.equal(s.won, 3);
  assert.deepEqual(s.streak, { type: 'wins', count: 2 });
  assert.equal(s.bestPartner.name, 'Anna');
  assert.equal(s.partners[0].name, 'Bruno');

  const players = [{ id: a, name: 'Anna', createdAt: new Date('2026-01-01T10:00:00.123Z') }];
  const file = E.buildBackup(players, matches.map((x) => ({ ...x, rules: E.defaultRules() })));
  assert.match(file.exportedAt, /T\d\d:\d\d:\d\dZ$/, 'niente millisecondi');
  assert.equal(file.players[0].createdAt, '2026-01-01T10:00:00Z');
  assert.equal('opponent1ID' in file.matches[0], false, 'gli opzionali vuoti non vanno scritti');
  const merged = E.mergeBackup(JSON.parse(JSON.stringify(file)), players, [matches[0]]);
  assert.deepEqual(merged.added, { players: 0, matches: 3 });
});
