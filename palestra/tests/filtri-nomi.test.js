// Nomi italiani nel catalogo e filtri che restano uguali quando torni.
const { chromium } = require('playwright');
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
const URL = process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html';

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT' });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('dialog', (d) => d.accept());
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.waitForTimeout(2500);

  console.log('\n== nomi in italiano ==');
  // un esercizio salvato tempo fa dal catalogo col nome inglese
  await p.evaluate(async () => {
    const db = await new Promise((r) => { const q = indexedDB.open('palestra'); q.onsuccess = () => r(q.result); });
    const t = db.transaction('exercises', 'readwrite');
    t.objectStore('exercises').put({ id: 'vecchio-face-pull', name: 'Face Pull', muscle: 'Spalle', equipment: 'Cavi', unit: 'kg',
      catalogId: 'face-pull', img: null, archived: false, createdAt: Date.now() });
    t.objectStore('exercises').put({ id: 'rinominato', name: 'Il mio rematore', muscle: 'Schiena', equipment: 'Cavi', unit: 'kg',
      catalogId: 'seated-cable-rows', img: null, archived: false, createdAt: Date.now() });
    await new Promise((r) => { t.oncomplete = r; });
  });
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(3000);
  const nomi = await p.evaluate(async () => {
    const db = await new Promise((r) => { const q = indexedDB.open('palestra'); q.onsuccess = () => r(q.result); });
    const all = await new Promise((r) => { const q = db.transaction('exercises').objectStore('exercises').getAll(); q.onsuccess = () => r(q.result); });
    return { fp: all.find((e) => e.id === 'vecchio-face-pull').name, ren: all.find((e) => e.id === 'rinominato').name };
  });
  check('un esercizio salvato col nome inglese passa all italiano', nomi.fp === 'Face pull', nomi.fp);
  check('un nome cambiato a mano non si tocca', nomi.ren === 'Il mio rematore', nomi.ren);

  await p.locator('[data-act="pick-exercise"]').click();
  await p.waitForTimeout(400);
  await p.locator('#pick-tabs button[data-tab="catalog"]').click();
  await p.waitForTimeout(1500);
  const primi = await p.evaluate(() => Array.from(document.querySelectorAll('#ex-pick li[data-cat] b')).slice(0, 3).map((b) => b.textContent));
  check('il catalogo e in italiano', primi.every((n) => !/Barbell|Dumbbell|Cable/.test(n)), primi.join(' | '));
  await p.locator('#ex-search').fill('bench press');
  await p.waitForTimeout(600);
  const en = await p.locator('#ex-pick li[data-cat] b').first().innerText().catch(() => '');
  check('cercando in inglese trova il nome italiano', /panca/i.test(en), en);
  await p.locator('#ex-search').fill('rematore');
  await p.waitForTimeout(600);
  const it = await p.locator('#ex-pick li[data-cat]').count();
  check('cercando in italiano trova gli esercizi', it > 5, it + ' rematori');

  console.log('\n== ricerca nel catalogo: resta uguale quando torni ==');
  await p.locator('#ex-search').fill('curl');
  await p.waitForTimeout(600);
  await p.locator('#f-muscle').selectOption('Bicipiti');
  await p.waitForTimeout(600);
  const tot = await p.locator('#ex-pick li[data-cat]').count();
  await p.evaluate(() => { document.querySelector('#ex-pick').scrollTop = 900; document.querySelector('#ex-pick').dispatchEvent(new Event('scroll')); });
  await p.waitForTimeout(400);
  const quale = await p.evaluate(() => {
    const l = document.querySelector('#ex-pick'); const top = l.getBoundingClientRect().top;
    const li = Array.from(l.querySelectorAll('li[data-cat]')).find((x) => x.getBoundingClientRect().top >= top);
    return li.dataset.cat;
  });
  await p.locator('#ex-pick li[data-cat="' + quale + '"] [data-act="cat-detail"]').click();
  await p.waitForTimeout(700);
  check('il dettaglio mostra anche il nome inglese', /In inglese:/.test(await p.locator('#modal-body').innerText()));
  check('dal dettaglio si torna alla lista', (await p.locator('[data-act="pick-back"]').count()) === 1);
  await p.locator('[data-act="pick-back"]').click();
  await p.waitForTimeout(900);
  check('al ritorno la ricerca e ancora "curl"', (await p.locator('#ex-search').inputValue()) === 'curl');
  check('al ritorno il filtro e ancora Bicipiti', (await p.locator('#f-muscle').inputValue()) === 'Bicipiti');
  check('al ritorno gli stessi risultati', (await p.locator('#ex-pick li[data-cat]').count()) === tot, tot + '');
  const sc = await p.evaluate(() => document.querySelector('#ex-pick').scrollTop);
  check('al ritorno sei nello stesso punto della lista', sc > 500, sc + ' px');

  await p.locator('#modal-close').click();
  await p.waitForTimeout(300);
  await p.locator('[data-act="pick-exercise"]').click();
  await p.waitForTimeout(1200);
  check('chiudendo e riaprendo resta tutto', (await p.locator('#ex-search').inputValue()) === 'curl' &&
    (await p.locator('#f-muscle').inputValue()) === 'Bicipiti' &&
    (await p.locator('#pick-tabs button.on').innerText()).includes('Catalogo'));
  await p.locator('#modal-close').click();

  console.log('\n== filtro del pannello: resta uguale ==');
  await p.locator('.chip', { hasText: 'Petto' }).first().click();
  await p.waitForTimeout(400);
  const n1 = await p.locator('.ex-row').count();
  await p.locator('.ex-row').first().click();
  await p.waitForTimeout(500);
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(800);
  await p.locator('[data-act="close-log"]').click();
  await p.waitForTimeout(400);
  check('dopo aver registrato il filtro e ancora Petto', (await p.locator('.chip.on').innerText()) === 'Petto');

  // aggiungo un esercizio di schiena dal catalogo mentre il filtro e' Petto
  await p.locator('[data-act="pick-exercise"]').click();
  await p.waitForTimeout(600);
  await p.locator('#ex-search').fill('rematore con bilanciere a busto flesso');
  await p.locator('#f-muscle').selectOption('');
  await p.waitForTimeout(700);
  await p.locator('#ex-pick li[data-cat]').first().click();
  await p.waitForTimeout(1200);
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(800);
  await p.locator('[data-act="close-log"]').click();
  await p.waitForTimeout(500);
  check('il filtro resta Petto anche dopo il catalogo', (await p.locator('.chip.on').innerText()) === 'Petto');
  const oggi = await p.evaluate(() => {
    const t = Array.from(document.querySelectorAll('.group-title')).find((x) => /fatti oggi/i.test(x.textContent));
    return t ? Array.from(t.nextElementSibling.querySelectorAll('.ex-name')).map((x) => x.textContent) : [];
  });
  check('"Fatti oggi" mostra anche l esercizio di schiena', oggi.some((n) => /rematore/i.test(n)), oggi.join(' | '));

  console.log('\n== la lista non torna in cima dopo ogni serie ==');
  await p.locator('.chip', { hasText: 'Tutti' }).first().click();
  await p.waitForTimeout(400);
  await p.evaluate(() => window.scrollTo(0, 1400));
  await p.waitForTimeout(300);
  const y0 = await p.evaluate(() => window.scrollY);
  const riga = p.locator('.ex-row').nth(8);
  await riga.click({ force: true });
  await p.waitForTimeout(500);
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(800);
  await p.locator('[data-act="close-log"]').click();
  await p.waitForTimeout(400);
  const y1 = await p.evaluate(() => window.scrollY);
  check('chiuso il pannello sei dove eri', Math.abs(y1 - y0) < 200 && y1 > 300, y0 + ' -> ' + y1 + ' px');

  await p.locator('#tabbar button[data-view="storico"]').click();
  await p.waitForTimeout(700);
  await p.locator('#tabbar button[data-view="oggi"]').click();
  await p.waitForTimeout(500);
  const y2 = await p.evaluate(() => window.scrollY);
  check('tornando da Storico ritrovi la lista dove l avevi lasciata', Math.abs(y2 - y1) < 200, y1 + ' -> ' + y2 + ' px');

  console.log('\n== anche chiudendo l app ==');
  await p.locator('.chip', { hasText: 'Gambe' }).first().click();
  await p.waitForTimeout(300);
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(2000);
  check('riaprendo l app il filtro e ancora Gambe', (await p.locator('.chip.on').innerText()) === 'Gambe');
  await p.locator('[data-act="pick-exercise"]').click();
  await p.waitForTimeout(1500);
  check('e anche la ricerca nel catalogo', (await p.locator('#ex-search').inputValue()) === 'rematore con bilanciere a busto flesso');

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 5).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
