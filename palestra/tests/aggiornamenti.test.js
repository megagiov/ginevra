// Gli aggiornamenti devono arrivare davvero sul telefono.
//
// Il caso che ha fatto nascere questa prova: il service worker serviva
// l'app dalla memoria del telefono e non si accorgeva mai delle versioni
// nuove. Qui si installa l'app, si registra un allenamento, si "pubblica"
// una versione nuova come si fa davvero (file cambiato + tools/versione.js)
// e si controlla che il telefono la riceva da solo, senza perdere dati.
const { chromium } = require('playwright');
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
const PORT = 8791;
const SRC = path.join(__dirname, '..');
const DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'palestra-agg-'));

(async () => {
  execSync('cp -r "' + SRC + '/." "' + DIR + '"');
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1'], { cwd: DIR, stdio: 'ignore' });
  await new Promise((r) => setTimeout(r, 1200));
  const URL = 'http://127.0.0.1:' + PORT + '/index.html';

  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'it-IT' });
  const p = await ctx.newPage();
  p.on('dialog', (d) => d.accept());
  const leggi = async (expr) => { try { return await p.evaluate(expr); } catch (e) { return null; } };

  console.log('\n== installazione ==');
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.evaluate(() => navigator.serviceWorker.ready);
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  const v1 = await leggi(() => window.APP_VERSION);
  check('app installata e controllata dal service worker', await leggi(() => !!navigator.serviceWorker.controller), 'versione ' + v1);
  await p.locator('.ex-row').first().click(); await p.waitForTimeout(400);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="close-log"]').click(); await p.waitForTimeout(400);
  check('allenamento registrato', (await p.locator('.session-bar').count()) === 1);

  console.log('\n== pubblico una versione nuova ==');
  fs.appendFileSync(path.join(DIR, 'js/app.js'), '\nwindow.__SEGNO_VERSIONE_NUOVA = true;\n');
  execSync('node tools/versione.js', { cwd: DIR });
  const v2 = fs.readFileSync(path.join(DIR, 'js/version.js'), 'utf8').match(/'([^']+)'/)[1];
  check('la versione e cambiata', v2 !== v1, v1 + ' -> ' + v2);

  console.log('\n== riapro l app, una volta sola ==');
  await p.reload({ waitUntil: 'networkidle' });
  let arrivata = false;
  for (let i = 0; i < 25 && !arrivata; i++) {
    await p.waitForTimeout(1000);
    arrivata = (await leggi(() => window.APP_VERSION)) === v2 && (await leggi(() => window.__SEGNO_VERSIONE_NUOVA)) === true;
  }
  check('la versione nuova arriva da sola', arrivata, 'ora ' + (await leggi(() => window.APP_VERSION)));
  await p.waitForTimeout(800);
  const t = await p.locator('#toast').innerText().catch(() => '');
  check('avvisa che l app si e aggiornata', /aggiornata/i.test(t), t);
  check('l allenamento in corso c e ancora', (await p.locator('.session-bar').count()) === 1);
  const cache = await leggi(async () => (await caches.keys()).sort());
  check('la versione vecchia e stata cancellata dalla memoria', cache && cache.filter((k) => k.startsWith('palestra-shell-')).length === 1, JSON.stringify(cache));

  console.log('\n== niente ricariche a meta serie ==');
  fs.appendFileSync(path.join(DIR, 'js/app.js'), '\nwindow.__SEGNO_TERZA = true;\n');
  execSync('node tools/versione.js', { cwd: DIR });
  await p.locator('.ex-row').first().click();                      // pannello aperto
  await p.waitForTimeout(300);
  await p.evaluate(() => navigator.serviceWorker.getRegistration().then((r) => r.update()));
  await p.waitForTimeout(4000);
  check('col pannello aperto non ricarica', (await leggi(() => !document.getElementById('modal-root').hidden)) === true &&
    (await leggi(() => window.__SEGNO_TERZA)) !== true);
  await p.locator('[data-act="close-log"]').click();
  let terza = false;
  for (let i = 0; i < 15 && !terza; i++) { await p.waitForTimeout(1000); terza = (await leggi(() => window.__SEGNO_TERZA)) === true; }
  check('chiuso il pannello, si aggiorna', terza);

  console.log('\n== senza rete, dopo l aggiornamento ==');
  await ctx.setOffline(true);
  await p.reload({ waitUntil: 'domcontentloaded' }).catch(() => {});
  await p.waitForTimeout(2000);
  check('l app si apre anche offline', (await leggi(() => document.title)) === 'Palestra' && (await leggi(() => window.__SEGNO_TERZA)) === true);
  check('i dati sono li anche offline', (await p.locator('.session-bar').count()) === 1);

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  await browser.close();
  server.kill();
  fs.rmSync(DIR, { recursive: true, force: true });
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
