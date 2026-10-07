// Allenarsi direttamente dalla scheda: si entra, si tocca l'esercizio e si
// registra. Prima la scheda serviva solo a modificarla e "Allenati" stava in
// fondo, fuori dallo schermo.
const { chromium } = require('playwright');
const proxy = process.env.HTTPS_PROXY;
const URL = process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html';
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
const shots = require('os').tmpdir() + '/palestra-shots/';

// Legge o cambia le sessioni direttamente nel database del telefono.
const sessioni = (p) => p.evaluate(async () => {
  const db = await new Promise((r) => { const q = indexedDB.open('palestra'); q.onsuccess = () => r(q.result); });
  return new Promise((r) => { const q = db.transaction('sessions').objectStore('sessions').getAll(); q.onsuccess = () => r(q.result); });
});
const invecchia = (p, minuti) => p.evaluate(async (min) => {
  const db = await new Promise((r) => { const q = indexedDB.open('palestra'); q.onsuccess = () => r(q.result); });
  const indietro = min * 60000;
  const tutti = (store) => new Promise((r) => { const q = db.transaction(store).objectStore(store).getAll(); q.onsuccess = () => r(q.result); });
  const [ss, sets] = [await tutti('sessions'), await tutti('sets')];
  await new Promise((r) => {
    const t = db.transaction(['sessions', 'sets'], 'readwrite');
    ss.filter((s) => !s.endedAt).forEach((s) => {
      s.startedAt -= indietro;
      if (s.resumedAt) s.resumedAt -= indietro;
      t.objectStore('sessions').put(s);
      sets.filter((x) => x.sessionId === s.id).forEach((x) => { x.ts -= indietro; t.objectStore('sets').put(x); });
    });
    t.oncomplete = r;
  });
}, minuti);

async function nuovaPagina(browser) {
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT', ignoreHTTPSErrors: true });
  const p = await ctx.newPage();
  p.errs = [];
  p.on('pageerror', (e) => p.errs.push(e.message));
  p.on('dialog', (d) => d.accept());
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  return p;
}
const fermaRecupero = (p) => p.evaluate(() => { const b = document.querySelector('#rest-skip'); if (b && b.offsetParent) b.click(); });

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined,
    proxy: proxy ? { server: proxy, bypass: '127.0.0.1,localhost' } : undefined, args: ['--ignore-certificate-errors'] });
  const p = await nuovaPagina(browser);

  console.log('\n== elenco schede ==');
  await p.locator('#tabbar button[data-view="schede"]').click();
  await p.waitForTimeout(600);
  check('le 3 schede si vedono come elenco', (await p.locator('[data-act="routine-open"]').count()) === 3);
  check('nell elenco niente frecce e X', (await p.locator('[data-act="item-up"], [data-act="item-del"]').count()) === 0);

  console.log('\n== dentro la scheda ==');
  await p.locator('[data-act="routine-open"]', { hasText: 'Push' }).click();
  await p.waitForTimeout(500);
  const allenati = await p.evaluate(() => {
    const b = document.querySelector('[data-act="start-routine"]');
    const tab = document.querySelector('#tabbar').getBoundingClientRect().top;
    return b ? { testo: b.textContent.trim(), basso: Math.round(b.getBoundingClientRect().bottom), tab: Math.round(tab) } : null;
  });
  check('il pulsante Allenati e in vista senza scorrere', allenati && allenati.basso <= allenati.tab, JSON.stringify(allenati));
  check('i 5 esercizi si toccano', (await p.locator('[data-act="routine-log"]').count()) === 5);
  check('frecce e X stanno dietro a Modifica', (await p.locator('[data-act="item-up"], [data-act="item-del"]').count()) === 0);
  check('niente scroll orizzontale', (await p.evaluate(() => document.documentElement.scrollWidth)) <= 390);
  await p.screenshot({ path: shots + 'S1-dentro-scheda.png' });

  console.log('\n== tocco un esercizio e registro subito ==');
  await p.locator('[data-act="routine-log"]', { hasText: 'Alzate laterali' }).click();
  await p.waitForTimeout(900);
  check('si apre il pannello di quell esercizio', /alzate laterali/i.test(await p.locator('#modal-title').innerText()));
  const box = (await p.locator('.scheda-box').innerText().catch(() => '')).replace(/\s+/g, ' ');
  check('il pannello mostra l obiettivo della scheda', /3\s*×\s*12-15/.test(box), box);
  let ss = await sessioni(p);
  const aperta = ss.filter((s) => !s.endedAt)[0];
  check('l allenamento e partito con la scheda', ss.length === 1 && aperta && /push/i.test(aperta.name) && aperta.plan.length === 5,
    aperta ? aperta.name + ' · ' + aperta.plan.length + ' in programma' : 'nessuna sessione');
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(700);
  await p.locator('[data-act="close-log"]').click();
  await fermaRecupero(p);
  await p.waitForTimeout(400);
  const badge = await p.locator('[data-act="routine-log"]', { hasText: 'Alzate laterali' }).locator('.ex-badge').innerText().catch(() => '');
  check('la riga segna 1 serie su 3', badge.trim() === '1/3', badge);
  check('si resta dentro la scheda', (await p.locator('.scheda-title').count()) === 1);
  const cont = await p.locator('[data-act="start-routine"]').innerText();
  check('il pulsante diventa Continua', /continua/i.test(cont), cont);

  console.log('\n== Continua apre il primo ancora da fare ==');
  await p.locator('[data-act="start-routine"]').click();
  await p.waitForTimeout(900);
  check('apre la panca piana', /panca piana/i.test(await p.locator('#modal-title').innerText()));
  for (let i = 0; i < 4; i++) { await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(500); }
  await p.locator('[data-act="close-log"]').click();
  await fermaRecupero(p);
  await p.waitForTimeout(400);
  check('la panca finita si spunta', (await p.locator('.ex-row.done', { hasText: 'Panca piana' }).count()) === 1);
  const meta = await p.locator('[data-act="routine-log"]', { hasText: 'Panca piana' }).locator('.ex-meta').innerText();
  check('sotto si leggono le serie di oggi', /^oggi /i.test(meta.trim()) && (meta.match(/×/g) || []).length === 4, meta);
  ss = await sessioni(p);
  check('sempre un solo allenamento', ss.length === 1, ss.length + '');
  await p.locator('[data-act="start-routine"]').click();
  await p.waitForTimeout(900);
  check('poi passa alla panca inclinata', /panca inclinata/i.test(await p.locator('#modal-title').innerText()));
  await p.locator('[data-act="close-log"]').click();
  await p.waitForTimeout(300);
  await p.screenshot({ path: shots + 'S2-scheda-in-corso.png' });

  console.log('\n== Modifica ==');
  await p.locator('[data-act="routine-edit"]').click();
  await p.waitForTimeout(400);
  check('con Modifica compaiono frecce, matita e X', (await p.locator('[data-act="item-up"]').count()) === 5);
  check('e Rinomina, Elimina, + Esercizio', (await p.locator('[data-act="routine-rename"], [data-act="routine-del"], [data-act="routine-add-ex"]').count()) === 3);
  check('niente scroll orizzontale in modifica', (await p.evaluate(() => document.documentElement.scrollWidth)) <= 390);
  await p.locator('[data-act="routine-edit"]').click();
  await p.waitForTimeout(400);
  check('Fine modifiche torna alla scheda per allenarsi', (await p.locator('[data-act="item-up"]').count()) === 0 &&
    (await p.locator('[data-act="routine-log"]').count()) === 5);

  console.log('\n== tornare all elenco e rientrare ==');
  await p.locator('#tabbar button[data-view="schede"]').click();
  await p.waitForTimeout(400);
  check('toccare Schede da dentro riporta all elenco', (await p.locator('[data-act="routine-open"]').count()) === 3);
  const riga = await p.locator('[data-act="routine-open"]', { hasText: 'Push' }).innerText();
  check('l elenco dice quale scheda e in corso', /in corso/i.test(riga), riga.replace(/\s+/g, ' '));
  await p.locator('[data-act="routine-open"]', { hasText: 'Push' }).click();
  await p.waitForTimeout(300);
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  await p.locator('#tabbar button[data-view="schede"]').click();
  await p.waitForTimeout(500);
  const titolo = await p.locator('.scheda-title').innerText().catch(() => '');
  check('se il telefono ricarica l app, la scheda resta aperta', /push/i.test(titolo), titolo);
  check('nessun errore JavaScript', !p.errs.length, p.errs.slice(0, 3).join(' | '));

  console.log('\n== prima della prima serie non si chiude dopo 15 minuti ==');
  const q = await nuovaPagina(browser);
  await q.locator('#tabbar button[data-view="schede"]').click();
  await q.waitForTimeout(500);
  await q.locator('[data-act="routine-open"]', { hasText: 'Gambe' }).click();
  await q.waitForTimeout(400);
  await q.locator('[data-act="start-routine"]').click();
  await q.waitForTimeout(900);
  await q.locator('[data-act="close-log"]').click();
  await invecchia(q, 40);
  await q.reload({ waitUntil: 'networkidle' });
  await q.waitForTimeout(1500);
  ss = await sessioni(q);
  check('avviata 40 minuti fa e nessuna serie: resta aperta', ss.filter((s) => !s.endedAt).length === 1);
  check('e la scheda e ancora in Oggi', (await q.locator('.group-title', { hasText: 'Ancora da fare' }).count()) === 1);
  await invecchia(q, 100);
  await q.reload({ waitUntil: 'networkidle' });
  await q.waitForTimeout(1500);
  ss = await sessioni(q);
  check('dopo piu di 2 ore senza serie si chiude', ss.filter((s) => !s.endedAt).length === 0);

  console.log('\n== dopo la prima serie valgono i 15 minuti ==');
  const w = await nuovaPagina(browser);
  await w.locator('#tabbar button[data-view="schede"]').click();
  await w.waitForTimeout(500);
  await w.locator('[data-act="routine-open"]', { hasText: 'Gambe' }).click();
  await w.waitForTimeout(400);
  await w.locator('[data-act="start-routine"]').click();
  await w.waitForTimeout(900);
  await w.locator('[data-act="log-save"]').click();
  await w.waitForTimeout(600);
  await w.locator('[data-act="close-log"]').click();
  await invecchia(w, 20);
  await w.reload({ waitUntil: 'networkidle' });
  await w.waitForTimeout(1500);
  ss = await sessioni(w);
  check('ultima serie 20 minuti fa: si chiude da sola', ss.filter((s) => !s.endedAt).length === 0);
  check('e si puo riprendere', (await w.locator('[data-act="resume-session"]').count()) === 1);

  const errs = [].concat(q.errs, w.errs);
  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 5).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
