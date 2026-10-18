const { chromium } = require('playwright');
const fs = require('fs');
const SHOT = require('os').tmpdir() + '/palestra-shots';
fs.mkdirSync(SHOT, { recursive: true });
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT' });
  const page = await ctx.newPage();
  const errs = [];
  page.on('pageerror', (e) => errs.push(e.message));
  page.on('dialog', (d) => d.accept());

  console.log('\n== 1. pannello principale ==');
  await page.goto((process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html'), { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const righe = await page.locator('.ex-row').count();
  check('gli esercizi sono tutti a vista in lista', righe === 30, righe + ' righe');
  check('nessun allenamento aperto all inizio', (await page.locator('.session-bar').count()) === 0);
  check('i filtri per gruppo muscolare ci sono', (await page.locator('.chip').count()) >= 6);
  const nomeSize = await page.evaluate(() => {
    const el = document.querySelector('.ex-name');
    return { px: parseFloat(getComputedStyle(el).fontSize), testo: el.textContent };
  });
  check('i nomi sono grandi', nomeSize.px >= 22, nomeSize.px + 'px — "' + nomeSize.testo + '"');
  await page.screenshot({ path: SHOT + '/P1-pannello.png' });

  console.log('\n== 2. filtro per gruppo ==');
  await page.locator('.chip', { hasText: 'Petto' }).first().click();
  await page.waitForTimeout(400);
  const filtrate = await page.locator('.ex-row').count();
  check('il filtro riduce la lista', filtrate > 0 && filtrate < righe, filtrate + ' esercizi di petto');
  await page.locator('.chip', { hasText: 'Tutti' }).first().click();
  await page.waitForTimeout(300);

  console.log('\n== 3. tocco un esercizio: si apre la registrazione ==');
  const primo = page.locator('.ex-row').first();
  const nomePrimo = await primo.locator('.ex-name').innerText();
  await primo.click();
  await page.waitForTimeout(600);
  check('il pannello di registrazione si apre', !(await page.locator('#modal-root').isHidden()));
  check('mostra l esercizio giusto', (await page.locator('#modal-title').innerText()).toUpperCase().includes(nomePrimo.slice(0, 8)));
  check('ci sono due stepper (peso e ripetizioni)', (await page.locator('.stepper').count()) === 2);
  check('i pulsanti sono grandi', (await page.evaluate(() => {
    const b = document.querySelector('.step-btn').getBoundingClientRect();
    return Math.min(b.width, b.height);
  })) >= 60);

  console.log('\n== 4. pulsanti + e − ==');
  const leggi = () => page.locator('#val-weight').innerText();
  const p0 = await leggi();
  await page.locator('[data-act="step"][data-f="weight"][data-d="1"]').click();
  await page.waitForTimeout(200);
  const p1 = await leggi();
  check('il + aumenta di 2,5 kg', Number(p1.replace(',', '.')) - Number(p0.replace(',', '.')) === 2.5, p0 + ' -> ' + p1);
  await page.locator('[data-act="step"][data-f="weight"][data-d="-1"]').click();
  await page.waitForTimeout(200);
  check('il − riporta indietro', (await leggi()) === p0, await leggi());
  // porto il peso a 80 scrivendolo a mano
  await page.locator('.step-val[data-f="weight"]').click();
  await page.waitForTimeout(300);
  await page.locator('#in-weight').fill('80');
  await page.locator('#in-weight').press('Enter');
  await page.waitForTimeout(300);
  check('si puo scrivere il valore esatto', (await leggi()) === '80', await leggi());
  await page.locator('[data-act="set-rpe"][data-v="8"]').click();
  await page.waitForTimeout(200);
  await page.screenshot({ path: SHOT + '/P2-registrazione.png' });

  console.log('\n== 5. registro: l allenamento deve nascere da solo ==');
  await page.locator('[data-act="log-save"]').click();
  await page.waitForTimeout(900);
  check('la serie compare nel pannello', (await page.locator('#modal-body .sets li').count()) === 1);
  check('il recupero parte e si vede nel pannello', !(await page.locator('#sheet-rest').isHidden()));
  const restTxt = await page.locator('#sheet-rest').innerText();
  check('il conto alla rovescia gira', /Recupero 0[12]:\d\d/.test(restTxt), restTxt);
  await page.locator('[data-act="log-save"]').click();
  await page.waitForTimeout(800);
  check('seconda serie registrata col carico mantenuto', (await page.locator('#modal-body .sets li').count()) === 2);
  await page.locator('[data-act="close-log"]').click();
  await page.waitForTimeout(600);
  check('l allenamento e partito da solo', (await page.locator('.session-bar').count()) === 1);
  const barra = (await page.locator('.session-bar').innerText()).replace(/\s+/g, ' ');
  check('la barra conta le serie', barra.includes('2 serie'), barra.slice(0, 60));
  const g0 = (await page.locator('.group-title').first().innerText()).toLowerCase();
  check('l esercizio e finito nel gruppo "Fatti oggi"', g0.includes('fatti oggi'), g0);
  check('la riga mostra il contatore delle serie', (await page.locator('.ex-badge').first().innerText()) === '2');
  await page.screenshot({ path: SHOT + '/P3-dopo-registrazione.png' });

  console.log('\n== 6. riapro: deve ricordare il carico ==');
  await page.locator('.ex-row').first().click();
  await page.waitForTimeout(600);
  check('riparte dal carico dell ultima serie', (await page.locator('#val-weight').innerText()) === '80', await page.locator('#val-weight').innerText());
  await page.locator('[data-act="close-log"]').click();
  await page.waitForTimeout(400);

  console.log('\n== 7. chiusura automatica dopo 15 minuti ==');
  // sposto indietro di 20 minuti l orario della serie, poi ricarico
  await page.evaluate(async () => {
    const db = await new Promise((res) => { const r = indexedDB.open('palestra'); r.onsuccess = () => res(r.result); });
    const t = db.transaction(['sets', 'sessions'], 'readwrite');
    const vecchio = Date.now() - 20 * 60000;
    const os = t.objectStore('sets');
    const all = await new Promise((res) => { const r = os.getAll(); r.onsuccess = () => res(r.result); });
    all.forEach((s) => { s.ts = vecchio; os.put(s); });
    const oss = t.objectStore('sessions');
    const ses = await new Promise((res) => { const r = oss.getAll(); r.onsuccess = () => res(r.result); });
    ses.forEach((s) => { s.startedAt = vecchio - 60000; delete s.resumedAt; oss.put(s); });
    await new Promise((res) => { t.oncomplete = res; });
  });
  await page.reload({ waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  check('l allenamento si e chiuso da solo', (await page.locator('.session-bar.resume').count()) === 1);
  const resumeTxt = (await page.locator('.session-bar.resume').innerText()).replace(/\s+/g, ' ');
  check('dice che si e chiuso per inattivita', resumeTxt.includes('inattivit'), resumeTxt.slice(0, 70));
  await page.screenshot({ path: SHOT + '/P4-riprendi.png' });

  console.log('\n== 8. riprendo l allenamento ==');
  await page.locator('[data-act="resume-session"]').click();
  await page.waitForTimeout(900);
  check('l allenamento e di nuovo aperto', (await page.locator('.session-bar:not(.resume)').count()) === 1);
  check('le serie di prima sono ancora dentro', (await page.locator('.ex-badge').first().innerText()) === '2');

  console.log('\n== 9. storico e durata ==');
  await page.locator('#tabbar button[data-view="storico"]').click();
  await page.waitForTimeout(900);
  const st = (await page.locator('#view').innerText()).replace(/\s+/g, ' ');
  check('lo storico ha una sola sessione, non due', (st.match(/serie ·/g) || []).length === 1, st.slice(0, 110));

  console.log('\n== 10. impostazioni nuove ==');
  await page.locator('#tabbar button[data-view="impostazioni"]').click();
  await page.waitForTimeout(700);
  check('si puo cambiare il passo dei pulsanti', (await page.locator('[data-act="set-step"]').count()) === 1);
  check('si puo cambiare la chiusura automatica', (await page.locator('[data-act="set-autoclose"]').count()) === 1);
  const sel = await page.locator('[data-act="set-autoclose"]').inputValue();
  check('la chiusura automatica e a 15 minuti', sel === '15', sel);

  console.log('\n== 11. schermo stretto ==');
  await page.setViewportSize({ width: 320, height: 568 });
  await page.locator('#tabbar button[data-view="oggi"]').click();
  await page.waitForTimeout(600);
  check('nessuno scroll orizzontale a 320px', (await page.evaluate(() => document.documentElement.scrollWidth)) <= 320);
  await page.screenshot({ path: SHOT + '/P5-stretto.png' });

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 6).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
