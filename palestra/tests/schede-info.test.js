const { chromium } = require('playwright');
const proxy = process.env.HTTPS_PROXY;
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined,
    proxy: proxy ? { server: proxy, bypass: '127.0.0.1,localhost' } : undefined, args: ['--ignore-certificate-errors'] });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT', ignoreHTTPSErrors: true });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('dialog', (d) => d.accept());
  await p.goto((process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html'), { waitUntil: 'networkidle' });
  await p.waitForTimeout(3000);

  console.log('\n== foto grandi ==');
  const mis = await p.evaluate(() => { const i = document.querySelector('.ex-row .ex-thumb'); const r = i.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; });
  check('la foto nella lista e grande', mis[0] >= 110 && mis[1] >= 110, mis.join('x') + ' px');
  const nome = await p.evaluate(() => parseFloat(getComputedStyle(document.querySelector('.ex-name')).fontSize));
  check('il nome resta grande', nome >= 22, nome + ' px');
  check('niente scroll orizzontale', (await p.evaluate(() => document.documentElement.scrollWidth)) <= 390);
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/F1-lista-foto-grandi.png' });

  console.log('\n== esercizio scelto dalla lista, fuori da una scheda aperta ==');
  // la Panca piana sta nella scheda Push: anche aprendola dalla lista deve dirlo
  await p.locator('.chip', { hasText: 'Petto' }).first().click();
  await p.waitForTimeout(400);
  await p.locator('.ex-row', { hasText: 'PANCA PIANA' }).first().click();
  await p.waitForTimeout(1500);
  const box = await p.locator('.scheda-box').innerText().catch(() => '');
  check('mostra in quale scheda sta e con che obiettivo', /Push/.test(box) && /4\s*×\s*6-8/.test(box), box.replace(/\s+/g, ' '));
  check('le due foto (inizio e fine movimento) sono in vista', (await p.locator('.log-photos img').count()) === 2);
  const fh = await p.evaluate(() => Math.round(document.querySelector('.log-photos img').getBoundingClientRect().height));
  check('le foto sono ben visibili', fh >= 90, fh + ' px di altezza');
  check('le istruzioni ci sono', (await p.locator('.ex-info .steps li').count()) > 0);
  check('le istruzioni partono chiuse', (await p.locator('.ex-info[open]').count()) === 0);
  const rias = await p.evaluate(() => {
    const r = document.querySelector('.ex-info > summary .ex-r');
    if (!r) return null;
    const lh = parseFloat(getComputedStyle(r).lineHeight);
    return { testo: r.textContent, righe: Math.round(r.getBoundingClientRect().height / lh) };
  });
  check('il riassunto in italiano e\u2019 in vista', !!rias && /panca/i.test(rias.testo) && /petto/.test(rias.testo), rias && rias.testo);
  check('da chiuso occupa al massimo due righe', !!rias && rias.righe <= 2, rias && rias.righe + ' righe');
  check('le istruzioni inglesi sono a parte, chiuse', (await p.locator('.ex-info .ex-en:not([open])').count()) === 1);
  const bt = await p.evaluate(() => {
    const b = document.querySelector('[data-act="log-save"]').getBoundingClientRect();
    return { basso: Math.round(b.bottom), schermo: window.innerHeight };
  });
  check('"Registra serie" sta nello schermo senza scorrere', bt.basso <= bt.schermo, bt.basso + ' su ' + bt.schermo + ' px');
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/F2-registrazione-foto.png' });
  // registro una serie: parte l'allenamento libero
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(900);
  check('le foto restano dopo aver registrato', (await p.locator('.log-photos img').count()) === 2);
  await p.locator('.ex-info > summary').click();
  await p.waitForTimeout(300);
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(900);
  check('se apri le istruzioni restano aperte anche dopo la serie', (await p.locator('.ex-info[open]').count()) === 1);
  await p.locator('.ex-info > summary').click();
  await p.locator('[data-act="close-log"]').click();
  await p.waitForTimeout(500);
  await p.locator('.chip', { hasText: 'Tutti' }).first().click();
  await p.waitForTimeout(400);
  check('allenamento partito da solo', (await p.locator('.session-bar:not(.resume)').count()) === 1);

  console.log('\n== apro una scheda ad allenamento gia iniziato ==');
  await p.locator('#tabbar button[data-view="schede"]').click();
  await p.waitForTimeout(700);
  const et = await p.locator('[data-act="start-routine"]').first().innerText();
  check('il pulsante dice che si aggiunge all allenamento in corso', /in corso/i.test(et), et);
  await p.locator('[data-act="start-routine"]').first().click();
  await p.waitForTimeout(1200);
  const n = await p.evaluate(async () => {
    const db = await new Promise((r) => { const q = indexedDB.open('palestra'); q.onsuccess = () => r(q.result); });
    const all = await new Promise((r) => { const q = db.transaction('sessions').objectStore('sessions').getAll(); q.onsuccess = () => r(q.result); });
    return { totali: all.length, aperte: all.filter((x) => !x.endedAt).length };
  });
  check('niente secondo allenamento: resta uno solo', n.totali === 1 && n.aperte === 1, JSON.stringify(n));
  check('la sessione prende il nome della scheda', (await p.locator('.session-bar').innerText()).includes('Push'));
  const g = await p.evaluate(() => Array.from(document.querySelectorAll('.group-title')).map((e) => e.textContent.trim().toLowerCase()));
  check('la panca gia fatta resta in "Fatti oggi", il resto della scheda in "Ancora da fare"', g[0].startsWith('fatti oggi') && g[1].startsWith('ancora da fare'), JSON.stringify(g.slice(0, 3)));

  console.log('\n== esercizio aperto dalla scheda: obiettivo e avanzamento ==');
  await p.locator('.ex-row', { hasText: 'PANCA PIANA' }).first().click();
  await p.waitForTimeout(900);
  const box2 = (await p.locator('.scheda-box').innerText()).replace(/\s+/g, ' ');
  check('mostra l obiettivo della scheda', /4\s*×\s*6-8/.test(box2), box2);
  check('mostra quante serie hai fatto su quante', /2 di 4 serie/.test(box2), box2);
  const w = await p.evaluate(() => document.querySelector('.sb-fill').style.width);
  check('la barra di avanzamento e a meta', w === '50%', w);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(900);
  const box3 = (await p.locator('.scheda-box').innerText()).replace(/\s+/g, ' ');
  check('a 4 su 4 segna "fatto"', /4 di 4 serie · fatto/.test(box3), box3);
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/F3-obiettivo-scheda.png' });
  await p.locator('[data-act="close-log"]').click();

  console.log('\n== catalogo: foto piu grandi ==');
  await p.locator('[data-act="pick-exercise"]').click();
  await p.waitForTimeout(500);
  await p.locator('#pick-tabs button[data-tab="catalog"]').click();
  await p.waitForTimeout(2500);
  const cm = await p.evaluate(() => { const i = document.querySelector('#ex-pick img'); return i ? Math.round(i.getBoundingClientRect().width) : 0; });
  check('le foto nel catalogo sono piu grandi', cm >= 86, cm + ' px');
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/F4-catalogo-foto.png' });

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 5).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
