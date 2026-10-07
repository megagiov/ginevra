// Testo grande: in palestra il telefono sta sulla panca o in mano col
// fiatone, e le scritte piccole non si leggono. Qui si controlla la misura
// predefinita, che la scelta in Altro valga dappertutto e resti dopo una
// riapertura, e che col testo grande il pannello di registrazione sia ancora
// usabile senza scorrere e senza scroll orizzontale.
const { chromium } = require('playwright');
const fs = require('fs');
const SHOT = require('os').tmpdir() + '/palestra-shots';
fs.mkdirSync(SHOT, { recursive: true });
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
  const radice = () => p.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize));
  const minimo = () => p.evaluate(() => {
    let min = 99, dove = '';
    document.querySelectorAll('#view *, #tabbar *').forEach((el) => {
      if (!el.offsetParent || !Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim())) return;
      const px = parseFloat(getComputedStyle(el).fontSize);
      if (px < min) { min = px; dove = el.className || el.tagName; }
    });
    return { min, dove };
  });

  // Pannello di registrazione: pulsante nello schermo, sforzo (RPE) non coperto.
  const pannello = async (nome) => {
    await p.locator('#tabbar button[data-view="oggi"]').click();
    await p.waitForTimeout(500);
    await p.locator('.ex-row').first().click();
    await p.waitForTimeout(900);
    const m = await p.evaluate(() => {
      const b = document.querySelector('[data-act="log-save"]').getBoundingClientRect();
      const chips = Array.from(document.querySelectorAll('.rpe-row .chip')).map((c) => c.getBoundingClientRect());
      const card = document.getElementById('modal-card');
      return {
        basso: Math.round(b.bottom), alto: Math.round(b.top), schermo: window.innerHeight,
        rpe: Math.round(Math.max.apply(null, chips.map((c) => c.bottom))),
        largo: card.scrollWidth <= card.clientWidth
      };
    });
    check(nome + ': "Registra serie" sta nello schermo', m.basso <= m.schermo, m.basso + ' su ' + m.schermo + ' px');
    check(nome + ': il pulsante non copre lo sforzo (RPE)', m.rpe <= m.alto, 'RPE fino a ' + m.rpe + ', pulsante da ' + m.alto);
    check(nome + ': niente scroll orizzontale nel pannello', m.largo);
    await p.screenshot({ path: SHOT + '/T-' + nome + '-registrazione.png' });
    await p.locator('[data-act="close-log"]').click();
    await p.waitForTimeout(400);
  };

  console.log('\n== misura predefinita ==');
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  const r1 = await radice();
  check('il testo parte grande', r1 >= 20, r1 + ' px di base (prima erano 16)');
  const m1 = await minimo();
  check('nessuna scritta piccola nel pannello', m1.min >= 16, m1.min + ' px (' + m1.dove + ')');
  await p.screenshot({ path: SHOT + '/T-grande-oggi.png' });
  await pannello('grande');

  console.log('\n== scelgo "Molto grande" ==');
  await p.locator('#tabbar button[data-view="impostazioni"]').click();
  await p.waitForTimeout(600);
  check('in Altro c e la misura del testo, su Grande', (await p.locator('[data-act="set-textsize"]').inputValue()) === 'grande');
  await p.locator('[data-act="set-textsize"]').selectOption('molto');
  await p.waitForTimeout(500);
  const r2 = await radice();
  check('il testo cresce subito', r2 >= 24, r2 + ' px');
  for (const v of ['oggi', 'schede', 'storico', 'progressi', 'impostazioni']) {
    await p.locator('#tabbar button[data-view="' + v + '"]').click();
    await p.waitForTimeout(500);
    const w = await p.evaluate(() => document.documentElement.scrollWidth);
    check('niente scroll orizzontale in ' + v, w <= 390, w + ' px');
  }
  await pannello('molto');

  console.log('\n== riapro l app ==');
  await p.reload({ waitUntil: 'domcontentloaded' });
  const subito = await p.evaluate(() => document.documentElement.dataset.testo);
  check('la misura e gia giusta prima che l app parta', subito === 'molto', subito);
  await p.waitForTimeout(1200);
  check('e resta dopo la riapertura', (await radice()) >= 24);

  console.log('\n== torno a "Normale" ==');
  await p.locator('#tabbar button[data-view="impostazioni"]').click();
  await p.waitForTimeout(500);
  await p.locator('[data-act="set-textsize"]').selectOption('normale');
  await p.waitForTimeout(400);
  check('si torna alla misura di prima', (await radice()) === 16);

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 6).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
