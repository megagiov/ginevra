// Lo schermo non deve spegnersi mentre ti alleni.
//
// Il difetto che ha fatto nascere questa prova: l'app chiedeva lo schermo
// acceso una volta sola. Quando il telefono si bloccava o passavi a un'altra
// app, il sistema toglieva il blocco, e al ritorno l'app credeva di averlo
// ancora: da li' in poi lo schermo si spegneva. In piu' lo chiedeva solo
// ad allenamento iniziato, non mentre guardavi gli esercizi.
//
// Il Wake Lock qui e' finto, cosi' si puo' simulare il blocco del telefono e
// contare le richieste.
const { chromium } = require('playwright');
let bad = 0;
const check = (n, c, x) => { if (!c) bad++; console.log((c ? '  ok  ' : ' FAIL ') + n + (x ? ' — ' + x : '')); };
const URL = process.env.PALESTRA_URL || 'http://127.0.0.1:8777/index.html';

const finto = () => {
  window.__wl = { richieste: 0, attivi: 0, ultimo: null };
  const wakeLock = {
    request() {
      window.__wl.richieste++;
      const l = new EventTarget();
      l.released = false;
      l.type = 'screen';
      l.release = () => {
        if (!l.released) { l.released = true; window.__wl.attivi--; l.dispatchEvent(new Event('release')); }
        return Promise.resolve();
      };
      window.__wl.attivi++;
      window.__wl.ultimo = l;
      return Promise.resolve(l);
    }
  };
  Object.defineProperty(navigator, 'wakeLock', { value: wakeLock, configurable: true });
};

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, locale: 'it-IT' });
  await ctx.addInitScript(finto);
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', (e) => errs.push(e.message));
  p.on('dialog', (d) => d.accept());
  const wl = () => p.evaluate(() => ({ richieste: window.__wl.richieste, attivi: window.__wl.attivi }));
  const altro = async () => { await p.locator('#tabbar button[data-view="impostazioni"]').click(); await p.waitForTimeout(500); };

  console.log('\n== app aperta, nessun allenamento ==');
  await p.goto(URL, { waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  let w = await wl();
  check('lo schermo resta acceso gia mentre guardi gli esercizi', w.attivi === 1, JSON.stringify(w));

  console.log('\n== il telefono si blocca e poi torni nell app ==');
  await p.evaluate(() => window.__wl.ultimo.release());           // il sistema toglie il blocco
  await p.waitForTimeout(200);
  await p.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
  await p.waitForTimeout(400);
  w = await wl();
  check('al ritorno lo richiede di nuovo', w.attivi === 1 && w.richieste === 2, JSON.stringify(w));
  await p.evaluate(() => window.__wl.ultimo.release());
  await p.waitForTimeout(200);
  await p.locator('.ex-row').first().click();                     // basta anche un tocco
  await p.waitForTimeout(400);
  w = await wl();
  check('anche solo toccando lo schermo torna acceso', w.attivi === 1, JSON.stringify(w));
  await p.locator('[data-act="close-log"]').click();
  await p.waitForTimeout(300);

  console.log('\n== impostazioni ==');
  await altro();
  check('in Altro c e la scelta, su "Sempre"', (await p.locator('[data-act="set-awake"]').inputValue()) === 'sempre');
  const st = await p.locator('#awake-stato').innerText();
  check('dice se lo schermo e acceso adesso', /acceso/.test(st), st);

  await p.locator('[data-act="set-awake"]').selectOption('allenamento');
  await p.waitForTimeout(500);
  w = await wl();
  check('"Solo durante l allenamento": senza allenamento si spegne', w.attivi === 0, JSON.stringify(w));
  await p.locator('#tabbar button[data-view="oggi"]').click();
  await p.waitForTimeout(400);
  await p.locator('.ex-row').first().click(); await p.waitForTimeout(400);
  await p.locator('[data-act="log-save"]').click(); await p.waitForTimeout(800);
  await p.locator('[data-act="close-log"]').click(); await p.waitForTimeout(400);
  w = await wl();
  check('con la prima serie l allenamento parte e lo schermo resta acceso', w.attivi === 1, JSON.stringify(w));

  await altro();
  await p.locator('[data-act="set-awake"]').selectOption('mai');
  await p.waitForTimeout(500);
  w = await wl();
  check('"Mai": lo lascia spegnere', w.attivi === 0, JSON.stringify(w));
  check('e lo dice', (await p.locator('#awake-stato').innerText()) === 'spento');

  console.log('\n== riapro l app ==');
  await p.reload({ waitUntil: 'networkidle' });
  await p.waitForTimeout(1500);
  w = await wl();
  check('la scelta "Mai" resta', w.attivi === 0, JSON.stringify(w));
  await altro();
  await p.locator('[data-act="set-awake"]').selectOption('sempre');
  await p.waitForTimeout(500);
  check('e si torna a "Sempre"', (await wl()).attivi === 1);

  console.log('\n== iPhone ==');
  const ios = await browser.newContext({
    viewport: { width: 390, height: 844 }, locale: 'it-IT', hasTouch: true, isMobile: true,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Mobile/15E148 Safari/604.1'
  });
  await ios.addInitScript(finto);
  const q = await ios.newPage();
  q.on('pageerror', (e) => errs.push(e.message));
  await q.goto(URL, { waitUntil: 'networkidle' });
  await q.waitForTimeout(1500);
  const v = await q.evaluate(() => {
    const el = document.querySelector('video.sveglia');
    return el && { muto: el.muted, inline: el.hasAttribute('playsinline'), loop: el.loop, src: el.src.slice(0, 22), alto: el.getBoundingClientRect().height };
  });
  check('su iPhone c e anche il video che tiene sveglio lo schermo', !!v, JSON.stringify(v));
  check('muto, dentro la pagina, in loop', v && v.muto && v.inline && v.loop && v.src === 'data:video/mp4;base64,');
  check('non si vede', v && v.alto <= 1);
  check('e c e anche il Wake Lock', (await q.evaluate(() => window.__wl.attivi)) === 1);
  await ios.close();

  console.log('\n===== ' + (bad ? bad + ' FALLITI' : 'tutti passati') + ' =====');
  console.log(errs.length ? 'errori JS: ' + errs.slice(0, 6).join(' | ') : 'nessun errore JavaScript');
  await browser.close();
  process.exit(bad || errs.length ? 1 : 0);
})().catch((e) => { console.error('CRASH:', e.message); process.exit(2); });
