/* Service worker minimo.
 *
 * Non mette in cache le pagine: mostrare posti liberi vecchi di un giorno
 * sarebbe peggio che non mostrare niente. In cache va solo il guscio
 * statico, piu' una pagina di cortesia quando la rete manca.
 */
const CACHE = 'studio-v1';
const STATICI = ['/stile.css', '/manifest.json', '/icona-180.png', '/icona-512.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(STATICI)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((nomi) => Promise.all(nomi.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const richiesta = e.request;
  if (richiesta.method !== 'GET') return;

  const url = new URL(richiesta.url);
  if (url.origin !== self.location.origin) return;

  // Statici: prima la cache, e' roba che non cambia.
  if (STATICI.includes(url.pathname)) {
    e.respondWith(caches.match(richiesta).then((r) => r || fetch(richiesta)));
    return;
  }

  // Tutto il resto: sempre dalla rete. Senza rete, un messaggio onesto.
  e.respondWith(
    fetch(richiesta).catch(() =>
      new Response(
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
        '<style>body{font:16px system-ui;padding:2rem;text-align:center;color:#0F172A}</style>' +
        '<h1>Sei senza connessione</h1>' +
        '<p>Per prenotare serve la rete. Riprova fra poco.</p>',
        { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
      )
    )
  );
});
