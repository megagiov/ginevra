// Le foto devono esserci a ogni apertura, non solo alla prima.
//
// Il difetto che ha fatto nascere questa prova: alla prima apertura le foto
// c'erano, dalla seconda in poi sparivano tutte, perche' l'indirizzo veniva
// costruito dal catalogo, caricato dopo il primo disegno della lista. Le
// altre prove partono sempre da un telefono "nuovo" e non potevano vederlo.
//
// Il CDN delle foto qui viene simulato: cosi' la prova non dipende dalla rete.
const { chromium } = require('playwright');
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
const URL = process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html';
// un JPEG 1x1 valido
const JPEG = Buffer.from('/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACP/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q==', 'base64');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  // service worker bloccato: il difetto e' nell'ordine di caricamento, non nella cache
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, serviceWorkers: 'block' });
  const richieste = [];
  await ctx.route('https://cdn.jsdelivr.net/**', (r) => { richieste.push(r.request().url()); r.fulfill({ status: 200, contentType: 'image/jpeg', body: JPEG }); });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));

  // Le foto si caricano quando ci arrivi scorrendo (loading="lazy"): prima di
  // contarle scorro tutta la lista, come fa chi la usa.
  const scorriTutto = async () => {
    const h = await p.evaluate(() => document.documentElement.scrollHeight);
    for (let y = 0; y <= h; y += 600) { await p.evaluate((yy) => window.scrollTo(0, yy), y); await p.waitForTimeout(120); }
    await p.waitForTimeout(800);
  };
  const foto = () => p.evaluate(() => {
    const righe = Array.from(document.querySelectorAll('.ex-row'));
    const img = righe.map((r) => r.querySelector('img.ex-thumb')).filter(Boolean);
    return { righe: righe.length, conFoto: img.filter((i) => i.naturalWidth > 0).length,
      relative: img.filter((i) => !/^https:\/\//.test(i.getAttribute('src'))).length };
  });

  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.waitForTimeout(3500);
  await scorriTutto();
  const a = await foto();
  check('prima apertura: tutte le righe hanno la foto', a.conFoto === a.righe && a.righe > 0, a.conFoto + ' su ' + a.righe);

  for (let i = 2; i <= 3; i++) {
    await p.reload({ waitUntil: 'networkidle' });
    await p.waitForTimeout(3500);
    await scorriTutto();
    const b = await foto();
    check('apertura ' + i + ': tutte le righe hanno ancora la foto', b.conFoto === b.righe, b.conFoto + ' su ' + b.righe);
    check('apertura ' + i + ': nessun indirizzo monco', b.relative === 0, b.relative + ' relativi');
  }

  // anche nel pannello di registrazione, aperto subito, prima del catalogo
  await p.reload({ waitUntil: 'domcontentloaded' });
  await p.waitForSelector('.ex-row');
  await p.locator('.ex-row').first().click();
  await p.waitForTimeout(1500);
  const panel = await p.evaluate(() => Array.from(document.querySelectorAll('.log-photos img')).map((i) => i.naturalWidth > 0));
  check('le foto nel pannello di registrazione ci sono', panel.length > 0 && panel.every(Boolean), JSON.stringify(panel));
  check('le foto chiedono il CDN vero', richieste.length > 0 && richieste.every((u) => u.startsWith('https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/')));

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 5).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
