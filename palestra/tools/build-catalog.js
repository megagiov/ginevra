#!/usr/bin/env node
/* Costruisce data/catalog.json partendo da free-exercise-db (Unlicense,
 * dominio pubblico): 870+ esercizi con foto.
 *
 *   node tools/build-catalog.js
 *
 * Le foto NON vengono scaricate: restano sul CDN e il service worker le
 * mette in cache man mano che le guardi. Il catalogo pesa ~1 MB, le foto
 * tutte insieme sarebbero decine di MB.
 *
 * Il dataset e' in inglese. I nomi italiani stanno in tools/nomi-it.json,
 * tradotti uno per uno con i termini che si usano davvero in palestra (lat
 * machine resta lat machine, "Barbell" diventa "con bilanciere"). Il nome
 * inglese resta nel campo `en`: serve alla ricerca e a riconoscere gli
 * esercizi gia' salvati col nome vecchio.
 *
 * Le istruzioni complete restano in inglese (`ins`). Al loro posto l'app
 * mostra un riassunto breve in italiano (`r`), scritto a mano esercizio per
 * esercizio in tools/riassunti-it.json: posizione, movimento, dettaglio
 * che conta.
 */
const fs = require('fs');
const path = require('path');

const SRC = 'https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/dist/exercises.json';
const CDN = 'https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/';
const OUT = path.join(__dirname, '..', 'data', 'catalog.json');
const CACHE = path.join(__dirname, '.cache-exercises.json');
const NOMI_IT = require('./nomi-it.json');
const RIASSUNTI = require('./riassunti-it.json');

const MUSCLES = {
  abdominals: 'Addominali', abductors: 'Abduttori', adductors: 'Adduttori',
  biceps: 'Bicipiti', calves: 'Polpacci', chest: 'Petto', forearms: 'Avambracci',
  glutes: 'Glutei', hamstrings: 'Femorali', lats: 'Dorsali', 'lower back': 'Lombari',
  'middle back': 'Dorso', neck: 'Collo', quadriceps: 'Quadricipiti',
  shoulders: 'Spalle', traps: 'Trapezio', triceps: 'Tricipiti'
};

const EQUIPMENT = {
  'body only': 'Corpo libero', machine: 'Macchina', other: 'Altro',
  'foam roll': 'Foam roller', kettlebells: 'Kettlebell', dumbbell: 'Manubri',
  cable: 'Cavi', barbell: 'Bilanciere', bands: 'Elastici',
  'medicine ball': 'Palla medica', 'exercise ball': 'Fitball', 'e-z curl bar': 'Bilanciere EZ'
};

const CATEGORY = {
  strength: 'Forza', stretching: 'Stretching', plyometrics: 'Pliometria',
  strongman: 'Strongman', powerlifting: 'Powerlifting', cardio: 'Cardio',
  'olympic weightlifting': 'Sollevamento olimpico'
};

const LEVEL = { beginner: 'Principiante', intermediate: 'Intermedio', expert: 'Avanzato' };
const FORCE = { pull: 'Tirata', push: 'Spinta', static: 'Statico' };

// Termini inglesi -> parole italiane usate in palestra. Servono alla ricerca,
// non come traduzione del nome.
const TERMS = {
  bench: 'panca', press: 'press spinte', barbell: 'bilanciere', dumbbell: 'manubri',
  cable: 'cavi', machine: 'macchina', smith: 'multipower', squat: 'squat',
  deadlift: 'stacco', romanian: 'rumeno', sumo: 'sumo', curl: 'curl',
  hammer: 'martello', row: 'rematore', rowing: 'rematore', pulldown: 'lat machine',
  pullup: 'trazioni', 'pull-up': 'trazioni', chinup: 'trazioni', 'chin-up': 'trazioni',
  pushup: 'piegamenti flessioni', 'push-up': 'piegamenti flessioni', dip: 'dip parallele',
  dips: 'dip parallele', lunge: 'affondo', lunges: 'affondi', raise: 'alzate',
  raises: 'alzate', lateral: 'laterali', front: 'frontali', rear: 'posteriori',
  extension: 'estensioni', extensions: 'estensioni', leg: 'gambe', legs: 'gambe',
  calf: 'polpacci', calves: 'polpacci', crunch: 'crunch addominali',
  'sit-up': 'addominali', situp: 'addominali', plank: 'plank', fly: 'croci',
  flye: 'croci', flyes: 'croci', shrug: 'scrollate', shrugs: 'scrollate',
  shoulder: 'spalle', chest: 'petto', back: 'schiena', biceps: 'bicipiti',
  bicep: 'bicipiti', triceps: 'tricipiti', tricep: 'tricipiti', glute: 'glutei',
  hip: 'anca', thrust: 'spinta', clean: 'girata', snatch: 'strappo', jerk: 'slancio',
  incline: 'inclinata', decline: 'declinata', seated: 'seduto', standing: 'in piedi',
  lying: 'sdraiato', close: 'stretta', wide: 'larga', grip: 'presa',
  kettlebell: 'kettlebell', band: 'elastico', ball: 'palla', stretch: 'allungamento',
  twist: 'torsione', jump: 'salto', jumping: 'salti', sprint: 'scatto', run: 'corsa',
  running: 'corsa', bike: 'bici', rope: 'corda', upright: 'verticale',
  overhead: 'sopra la testa', military: 'military', preacher: 'panca scott',
  concentration: 'concentrazione', reverse: 'inverso', alternating: 'alternato',
  single: 'singolo', 'one-arm': 'un braccio', neutral: 'neutra', abs: 'addominali',
  core: 'core', hamstring: 'femorali', quad: 'quadricipiti', lat: 'dorsali',
  pull: 'tirata', push: 'spinta', good: 'good', morning: 'morning', face: 'face'
};

function keywords(ex) {
  const words = new Set();
  String(ex.name).toLowerCase().split(/[^a-z0-9-]+/).forEach((w) => {
    if (!w) return;
    if (TERMS[w]) TERMS[w].split(' ').forEach((t) => words.add(t));
  });
  (ex.primaryMuscles || []).forEach((m) => { if (MUSCLES[m]) words.add(MUSCLES[m].toLowerCase()); });
  if (EQUIPMENT[ex.equipment]) words.add(EQUIPMENT[ex.equipment].toLowerCase());
  return Array.from(words).join(' ');
}

function slug(name) {
  return String(name).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function load() {
  if (fs.existsSync(CACHE)) return Promise.resolve(JSON.parse(fs.readFileSync(CACHE, 'utf8')));
  console.log('Scarico il dataset da', SRC);
  return fetch(SRC).then((r) => {
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }).then((json) => {
    fs.writeFileSync(CACHE, JSON.stringify(json));
    return json;
  });
}

load().then((rows) => {
  const mancanti = rows.filter((ex) => !NOMI_IT[ex.name]).map((ex) => ex.name);
  if (mancanti.length) {
    console.warn('Senza traduzione (restano in inglese): ' + mancanti.length);
    mancanti.slice(0, 20).forEach((n) => console.warn('  - ' + n));
  }
  const items = rows.map((ex) => ({
    id: slug(ex.name),
    n: NOMI_IT[ex.name] || ex.name,
    en: ex.name,
    m: (ex.primaryMuscles || []).map((x) => MUSCLES[x] || x),
    s: (ex.secondaryMuscles || []).map((x) => MUSCLES[x] || x),
    eq: EQUIPMENT[ex.equipment] || 'Altro',
    cat: CATEGORY[ex.category] || ex.category,
    lvl: LEVEL[ex.level] || ex.level,
    f: FORCE[ex.force] || '',
    img: ex.images || [],
    ins: ex.instructions || [],
    r: RIASSUNTI[ex.name] || '',
    k: keywords(ex)
  })).sort((a, b) => a.n.localeCompare(b.n, 'it'));

  const seen = {};
  items.forEach((it) => {
    if (seen[it.id]) it.id = it.id + '-' + (++seen[it.id]);
    else seen[it.id] = 1;
  });

  const out = {
    v: 1,
    source: 'free-exercise-db (yuhonas) — Unlicense / dominio pubblico',
    cdn: CDN,
    count: items.length,
    items
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(out));
  const kb = Math.round(fs.statSync(OUT).size / 1024);
  console.log('Scritto ' + OUT + ': ' + items.length + ' esercizi, ' + kb + ' KB');
  console.log('Con foto: ' + items.filter((i) => i.img.length).length);
}).catch((e) => {
  console.error('Errore:', e.message);
  process.exit(1);
});
