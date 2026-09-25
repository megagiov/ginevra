const { chromium } = require('playwright');
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, locale: 'it-IT' });
  await ctx.addInitScript(() => {
    window.__appunti = '';
    window.__negaAppunti = false;
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: {
      readText: async () => { if (window.__negaAppunti) throw new Error('negato'); return window.__appunti; },
      writeText: async () => {}
    } });
  });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('console', (m) => { if (m.type() === 'error') console.log('     [console] ' + m.text()); });
  p.on('dialog', (d) => d.accept());
  await p.goto((process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html'), { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);

  // un allenamento vero, poi lo chiudo
  await p.locator('.ex-row').first().click(); await p.waitForTimeout(500);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(700);
  await p.locator('[data-act="close-log"]').click(); await p.waitForTimeout(400);
  await p.locator('[data-act="end-session"]').click(); await p.waitForTimeout(900);

  console.log('\n== appena chiuso l allenamento ==');
  const btn = p.locator('.paste-watch');
  check('compare "Incolla il battito dal Watch"', (await btn.count()) === 1);

  // quello che l'automazione di Comandi rapidi mette negli appunti: date italiane, una riga per battito
  await p.evaluate(() => {
    const mesi = ['gennaio','febbraio','marzo','aprile','maggio','giugno','luglio','agosto','settembre','ottobre','novembre','dicembre'];
    const riga = (t, v) => { const d = new Date(t); const z = (n) => String(n).padStart(2, '0');
      return d.getDate() + ' ' + mesi[d.getMonth()] + ' ' + d.getFullYear() + ', ' + z(d.getHours()) + ':' + z(d.getMinutes()) + ':' + z(d.getSeconds()) + ', ' + v; };
    const ora = Date.now();
    window.__appunti = [[-40, 96], [-30, 118], [-20, 142], [-10, 151], [-3, 137]].map(([s, v]) => riga(ora + s * 1000, v)).join('\n');
  });
  await btn.click();
  await p.waitForTimeout(1200);
  const t = await p.locator('#toast').innerText();
  check('il battito si aggancia all allenamento', /aggiunto a 1 allenamento/.test(t), t);
  check('il pulsante sparisce una volta incollato', (await p.locator('.paste-watch').count()) === 0);

  console.log('\n== nello storico ==');
  await p.locator('#tabbar button[data-view="storico"]').click();
  await p.waitForTimeout(1000);
  const st = (await p.locator('#view').innerText()).replace(/\s+/g, ' ');
  check('media corretta (96+118+142+151+137)/5 = 129', st.includes('129'), (st.match(/\d+ bpm medi/) || [''])[0]);
  check('massimo corretto 151', st.includes('151'));
  check('c e il grafico del battito', (await p.locator('.chart.hr').count()) === 1);
  console.log('     pulsanti condividi: ' + await p.locator('[data-act="session-share"]').count() +
    ' · modale aperta prima del clic: ' + !(await p.locator('#modal-root').isHidden()));
  await p.locator('[data-act="session-share"]').first().click();
  await p.waitForTimeout(1500);
  console.log('     dopo il clic — titolo modale: "' + (await p.locator('#modal-title').innerText().catch(() => '?')) +
    '" · nascosta: ' + (await p.locator('#modal-root').isHidden()) + ' · errori: ' + JSON.stringify(errs));
  check('il battito finisce anche nel messaggio per il personal', (await p.locator('.share-preview').innerText()).includes('Battito: media 129, massimo 151'));
  await p.locator('#modal-close').click();

  console.log('\n== se il browser non da gli appunti ==');
  await p.evaluate(() => { window.__negaAppunti = true; });
  await p.locator('#tabbar button[data-view="impostazioni"]').click();
  await p.waitForTimeout(800);
  await p.locator('.card [data-act="hr-paste"]').click();
  await p.waitForTimeout(600);
  check('si apre il riquadro per incollare a mano', (await p.locator('#hr-paste').count()) === 1);
  await p.locator('#hr-paste').fill('1 gennaio 2020, 10:00:00, 120\n1 gennaio 2020, 10:00:05, 125');
  await p.locator('[data-act="hr-paste-go"]').click();
  await p.waitForTimeout(800);
  check('battiti fuori da ogni allenamento: lo dice chiaro', /nessuno cade dentro/.test(await p.locator('#toast').innerText()), await p.locator('#toast').innerText());
  await p.locator('#hr-paste').fill('niente di utile qui');
  await p.locator('[data-act="hr-paste-go"]').click();
  await p.waitForTimeout(600);
  check('testo sbagliato: spiega cosa fare', /Comando rapido/.test(await p.locator('#toast').innerText()), await p.locator('#toast').innerText());

  console.log('\n== guida ==');
  await p.locator('#modal-close').click();
  await p.locator('.card [data-act="hr-help"]').click();
  await p.waitForTimeout(500);
  const g = await p.locator('#modal-body').innerText();
  check('spiega l automazione di fine allenamento', /Allenamento Apple Watch/.test(g) && /Termina/.test(g));
  check('spiega la via in diretta con il suo costo', /Bluefy/.test(g) && /memoria/.test(g));
  await p.screenshot({ path: require('os').tmpdir() + '/palestra-shots/W1-guida.png' });

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 5).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
