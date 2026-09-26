const { chromium } = require('playwright');
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT' });
  await ctx.addInitScript(() => {
    window.__copiato = null; window.__condiviso = null;
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: async (t) => { window.__copiato = t; } }, configurable: true });
    navigator.share = async (d) => { window.__condiviso = d; };
  });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('dialog', (d) => d.accept());
  await p.goto((process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html'), { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);

  // la volta scorsa: panca a 75x8, cosi' oggi 80x8 e' un record
  await p.evaluate(async () => {
    const db = await new Promise((r) => { const q = indexedDB.open('palestra'); q.onsuccess = () => r(q.result); });
    const ex = await new Promise((r) => { const q = db.transaction('exercises').objectStore('exercises').getAll(); q.onsuccess = () => r(q.result); });
    const panca = ex.find((e) => e.name === 'Panca piana bilanciere');
    const t = db.transaction(['sessions', 'sets'], 'readwrite');
    const base = Date.now() - 4 * 86400000;
    t.objectStore('sessions').put({ id: 'vecchia', date: '', name: 'Allenamento', routineId: null, plan: [], startedAt: base, endedAt: base + 3000000, note: '' });
    [[75, 8], [75, 7]].forEach(([w, r], i) => t.objectStore('sets').put({ id: 'v' + i, sessionId: 'vecchia', exerciseId: panca.id, weight: w, reps: r, rpe: null, warmup: false, note: '', ts: base + i * 1000 }));
    await new Promise((r) => { t.oncomplete = r; });
  });
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);

  // oggi: riscaldamento + 2 serie di lavoro, una con RPE
  await p.locator('.ex-row', { hasText: 'PANCA PIANA' }).first().click();
  await p.waitForTimeout(600);
  const setVal = async (f, v) => {
    await p.locator('.step-val[data-f="' + f + '"]').click();
    await p.locator('#in-' + f).fill(String(v));
    await p.locator('#in-' + f).press('Enter');
    await p.waitForTimeout(150);
  };
  await setVal('weight', 40); await setVal('reps', 12);
  await p.locator('[data-act="log-warmup"]').check(); await p.waitForTimeout(300);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await setVal('weight', 80); await setVal('reps', 8);
  await p.locator('[data-act="set-rpe"][data-v="8"]').click();
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await setVal('reps', 7);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="close-log"]').click(); await p.waitForTimeout(400);
  // un secondo esercizio a corpo libero
  await p.locator('.ex-row', { hasText: 'TRAZIONI' }).first().click(); await p.waitForTimeout(500);
  await setVal('weight', 0); await setVal('reps', 10);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="close-log"]').click(); await p.waitForTimeout(400);
  // battito e nota
  await p.locator('[data-act="hr-options"]').click(); await p.waitForTimeout(300);
  await p.locator('[data-act="hr-manual"]').click(); await p.waitForTimeout(300);
  await p.locator('#hr-manual-form input[name="avg"]').fill('128');
  await p.locator('#hr-manual-form input[name="max"]').fill('165');
  await p.locator('#hr-manual-form button[type="submit"]').click(); await p.waitForTimeout(700);
  await p.locator('.session-bar .sb-main').click(); await p.waitForTimeout(300);
  await p.locator('#sess-form textarea[name="note"]').fill('Spalla destra ok, ultima serie lenta');
  await p.locator('#sess-form button[type="submit"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="end-session"]').click(); await p.waitForTimeout(900);

  console.log('\n== dallo storico ==');
  await p.locator('#tabbar button[data-view="storico"]').click();
  await p.waitForTimeout(1000);
  const btn = p.locator('[data-act="session-share"]').first();
  check('ogni allenamento ha "Condividi su WhatsApp"', (await btn.innerText()).includes('WhatsApp'));
  await btn.click();
  await p.waitForTimeout(900);
  const testo = await p.locator('.share-preview').innerText();
  console.log('\n----- testo che parte -----\n' + testo + '\n---------------------------\n');
  check('niente campo per il numero', (await p.locator('input[type="tel"]').count()) === 0);
  check('titolo coi gruppi muscolari lavorati', /^\*Allenamento: Petto, Schiena\*/.test(testo), testo.split('\n')[0]);
  check('data e durata', /\n[A-ZÀ-Ú][a-zà-ú]+ \d+ \w+ · /.test(testo), testo.split('\n')[1]);
  check('totali di serie e kg', /3 serie · 1\.200 kg sollevati/.test(testo), testo.split('\n')[2]);
  check('il riscaldamento e separato', testo.includes('risc. 40×12'));
  check('RPE scritto come @8', testo.includes('80×8 @8'));
  check('il record battuto e segnalato', /80×8 @8 · 80×7\s+— nuovo record/.test(testo));
  check('lo sforzo non viene copiato sulla serie dopo', !testo.includes('80×7 @8'));
  check('corpo libero scritto in ripetizioni', testo.includes('10 rip'));
  check('c e il battito', testo.includes('Battito: media 128, massimo 165'));
  check('c e la nota', testo.includes('Nota: Spalla destra ok, ultima serie lenta'));

  const href = await p.locator('.wa-btn').getAttribute('href');
  check('il link apre WhatsApp senza contatto fissato', href.startsWith('https://wa.me/?text='), href.slice(0, 30));
  check('il link porta esattamente quel testo', decodeURIComponent(href.split('?text=')[1]) === testo);

  await p.locator('[data-act="share-copy"]').click(); await p.waitForTimeout(400);
  check('"Copia il testo" copia quel testo', (await p.evaluate(() => window.__copiato)) === testo);
  await p.locator('[data-act="share-other"]').click(); await p.waitForTimeout(400);
  const c = await p.evaluate(() => window.__condiviso);
  check('"Altre app" apre il menu Condividi con quel testo', c && c.text === testo);
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/S1-condividi.png' });

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 5).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
