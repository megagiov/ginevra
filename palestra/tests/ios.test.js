const { chromium } = require('playwright');
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };

// Simula quello che fa Safari su iPhone: niente vibrazione, menu Condividi
// con file, categoria audio. E registra i bip programmati.
const FINTO_IPHONE = () => {
  try { delete Navigator.prototype.vibrate; } catch (e) {}
  Object.defineProperty(navigator, 'vibrate', { value: undefined, configurable: true });
  window.__sessione = { type: 'auto' };
  Object.defineProperty(navigator, 'audioSession', { value: window.__sessione, configurable: true });
  window.__condivisi = [];
  navigator.canShare = (d) => !!(d && d.files && d.files.length);
  navigator.share = async (d) => {
    const f = d.files[0];
    window.__condivisi.push({ nome: f.name, tipo: f.type, testo: await f.text() });
  };
};
const SPIA_AUDIO = () => {
  window.__bip = [];
  const Orig = window.AudioContext;
  window.AudioContext = function () {
    const c = new Orig();
    window.__categoriaAllaNascita = navigator.audioSession ? navigator.audioSession.type : 'n/d';
    const co = c.createOscillator.bind(c);
    c.createOscillator = () => {
      const o = co();
      const st = o.start.bind(o);
      o.start = (t) => { window.__bip.push(+(t - c.currentTime).toFixed(2)); return st(t); };
      return o;
    };
    return c;
  };
};

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined,
    args: ['--autoplay-policy=no-user-gesture-required'] });

  // ------------------------------------------------------------ iPhone
  console.log('\n######## come su iPhone ########');
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT', acceptDownloads: true });
  await ctx.addInitScript(FINTO_IPHONE);
  await ctx.addInitScript(SPIA_AUDIO);
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('dialog', (d) => d.accept());
  await p.goto((process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html'), { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);

  console.log('\n== impostazioni ==');
  await p.locator('#tabbar button[data-view="impostazioni"]').click();
  await p.waitForTimeout(900);
  check('niente interruttore vibrazione finto', (await p.locator('[data-act="set-vibrate"]').count()) === 0);
  const nota = await p.locator('.note-ios').first().innerText();
  check('spiega che su iPhone la vibrazione non c e', /non disponibile/i.test(nota), nota.slice(0, 70));
  check('c e la scelta della modalita del suono', (await p.locator('[data-act="set-soundmode"]').count()) === 1);
  check('il predefinito e "normale"', (await p.locator('[data-act="set-soundmode"]').inputValue()) === 'mix');
  const bk = await p.locator('.card', { hasText: 'Backup' }).innerText();
  check('il backup spiega "Salva su File"', bk.includes('Salva su File'), '');
  check('il backup avvisa di non scegliere AnyDesk', bk.includes('AnyDesk'), '');

  console.log('\n== pulsante di prova ==');
  await p.locator('[data-act="test-sound"]').click();
  await p.waitForTimeout(700);
  const out = await p.locator('#test-out').innerText();
  console.log('     ' + out.split('\n').slice(0, 4).join(' | '));
  check('la prova produce il bip', (await p.evaluate(() => window.__bip.length)) >= 3);
  check('categoria audio "transient" gia prima di creare l audio', (await p.evaluate(() => window.__categoriaAllaNascita)) === 'transient',
    await p.evaluate(() => window.__categoriaAllaNascita));
  check('il lampeggio parte', (await p.locator('#rest-flash.go').count()) === 1);

  console.log('\n== modalita "anche col silenzioso" ==');
  await p.locator('[data-act="set-soundmode"]').selectOption('silent');
  await p.waitForTimeout(600);
  await p.locator('[data-act="test-sound"]').click();
  await p.waitForTimeout(500);
  check('passa a "playback"', (await p.evaluate(() => window.__sessione.type)) === 'playback', await p.evaluate(() => window.__sessione.type));
  await p.locator('[data-act="set-soundmode"]').selectOption('mix');
  await p.waitForTimeout(500);

  console.log('\n== bip programmato sull orologio audio ==');
  await p.locator('input[data-act="set-rest"]').fill('10');
  await p.locator('input[data-act="set-rest"]').blur();
  await p.waitForTimeout(500);
  await p.locator('#tabbar button[data-view="oggi"]').click();
  await p.waitForTimeout(700);
  await p.evaluate(() => { window.__bip = []; });
  await p.locator('.ex-row').first().click();
  await p.waitForTimeout(500);
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(600);
  const prog = await p.evaluate(() => window.__bip.slice());
  check('il bip e programmato a fine recupero, non adesso', prog.length === 3 && prog[0] > 8 && prog[0] <= 10.1, JSON.stringify(prog));
  await p.evaluate(() => { window.__bip = []; });
  await p.locator('[data-act="close-log"]').click();
  await p.locator('#rest-bar [data-adj="15"]').click();
  await p.waitForTimeout(400);
  const rip = await p.evaluate(() => window.__bip.slice());
  check('con +15 il bip si sposta', rip.length === 3 && rip[0] > 20, JSON.stringify(rip));
  await p.locator('#rest-bar [data-adj="-15"]').click();
  await p.waitForTimeout(300);
  console.log('     aspetto la fine del recupero…');
  await p.waitForTimeout(11000);
  check('a fine recupero lo schermo lampeggia', (await p.locator('#rest-flash.go').count()) === 1 || (await p.locator('#rest-bar.done').count()) === 1);
  await p.waitForTimeout(3000);
  check('la barra del recupero poi sparisce', await p.locator('#rest-bar').isHidden());
  await p.evaluate(() => { window.__bip = []; });
  await p.locator('.ex-row').first().click();
  await p.waitForTimeout(400);
  await p.locator('[data-act="log-save"]').click();
  await p.waitForTimeout(400);
  await p.locator('[data-act="close-log"]').click();
  await p.locator('#rest-skip').click();
  await p.waitForTimeout(300);
  check('Stop cancella il bip programmato', await p.locator('#rest-bar').isHidden());

  console.log('\n== backup col menu Condividi ==');
  await p.locator('#tabbar button[data-view="impostazioni"]').click();
  await p.waitForTimeout(1200);
  await p.locator('[data-act="export"]').click();
  await p.waitForTimeout(1200);
  const cond = await p.evaluate(() => window.__condivisi.slice());
  check('apre il menu Condividi con il file', cond.length === 1, cond.length + '');
  if (cond.length) {
    check('il file ha il nome giusto', /^palestra-backup-\d{4}-\d\d-\d\d\.json$/.test(cond[0].nome), cond[0].nome);
    let ok = false, n = 0;
    try { const j = JSON.parse(cond[0].testo); ok = j.format === 'palestra-backup'; n = j.sets.length; } catch (e) {}
    check('il file e un backup valido con le serie dentro', ok && n >= 2, n + ' serie');
  }
  const ult = await p.locator('.card', { hasText: 'Backup' }).innerText();
  check('ricorda la data dell ultimo backup', /Ultimo backup:.*oggi/.test(ult), (ult.match(/Ultimo backup[^\n]*/) || [''])[0]);

  console.log('\n== reimport dello stesso file ==');
  const [chooser] = await Promise.all([p.waitForEvent('filechooser'), p.locator('[data-act="import"]').click()]);
  await chooser.setFiles({ name: cond[0].nome, mimeType: 'application/json', buffer: Buffer.from(cond[0].testo) });
  await p.waitForTimeout(1500);
  check('il backup si reimporta', (await p.locator('#toast').innerText()).includes('Importati'), await p.locator('#toast').innerText());
  check('nessun errore JavaScript (iPhone)', errs.length === 0, errs.slice(0, 3).join(' | '));
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/IOS-impostazioni.png', fullPage: true });

  // ------------------------------------------------------------ Android
  console.log('\n######## come su Android ########');
  const ctx2 = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'it-IT', acceptDownloads: true });
  const q = await ctx2.newPage();
  const errs2 = [];
  q.on('pageerror', (e) => errs2.push(e.message));
  await q.goto((process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html'), { waitUntil: 'networkidle' });
  await q.waitForTimeout(1200);
  await q.locator('#tabbar button[data-view="impostazioni"]').click();
  await q.waitForTimeout(1200);
  check('qui la vibrazione c e ed e attivabile', (await q.locator('[data-act="set-vibrate"]').count()) === 1);
  const dl = q.waitForEvent('download', { timeout: 6000 }).catch(() => null);
  await q.locator('[data-act="export"]').click();
  const d = await dl;
  check('senza menu Condividi il backup si scarica', !!d, d ? d.suggestedFilename() : 'niente');
  check('nessun errore JavaScript (Android)', errs2.length === 0, errs2.slice(0, 3).join(' | '));

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  await browser.close();
  process.exit(bad ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
