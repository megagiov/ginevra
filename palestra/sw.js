/* Service worker: l'app parte anche senza rete.
 *
 * - guscio dell'app: scaricato tutto insieme quando arriva una versione
 *   nuova, e servito sempre dalla stessa versione, cosi' pagina, script e
 *   stili non si mescolano mai fra versioni diverse
 * - catalogo esercizi: aggiornato quando c'e' rete, dalla memoria quando no
 * - foto degli esercizi: salvate man mano che le guardi
 *
 * VERSION e DATA_VERSION li scrive tools/versione.js: sono l'impronta dei
 * file. Se non cambiano, il telefono non scarica mai la versione nuova. */
const VERSION = '9a92471cb1';
const DATA_VERSION = '04b3317b27';
const SHELL = 'palestra-shell-' + VERSION;
const DATA = 'palestra-data-' + DATA_VERSION;
const IMAGES = 'palestra-img';           // niente versione: le foto non cambiano mai
const IMG_HOST = 'cdn.jsdelivr.net';

const SHELL_FILES = [
  './',
  'index.html',
  'app.css',
  'fonts.css',
  'manifest.webmanifest',
  'js/version.js',
  'js/db.js',
  'js/seed.js',
  'js/chart.js',
  'js/catalog.js',
  'js/hr.js',
  'js/app.js',
  'fonts/barlow-400.woff2',
  'fonts/barlow-500.woff2',
  'fonts/barlow-600.woff2',
  'fonts/barlow-700.woff2',
  'fonts/barlow-condensed-600.woff2',
  'fonts/barlow-condensed-700.woff2',
  'icons/icon-192.png',
  'icons/icon-512.png',
  'icons/icon-maskable-512.png'
];

self.addEventListener('install', (ev) => {
  ev.waitUntil(
    caches.open(SHELL)
      // cache: 'reload' salta la cache del browser: altrimenti un file
      // appena scaricato dalla versione vecchia finirebbe in quella nuova.
      .then((c) => Promise.all(SHELL_FILES.map((f) =>
        c.add(new Request(f, { cache: 'reload' })).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (ev) => {
  ev.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.map((k) => {
        if (k === SHELL || k === DATA || k === IMAGES) return null;
        return caches.delete(k);
      })))
      .then(() => self.clients.claim())
  );
});

function staleWhileRevalidate(req, cacheName) {
  return caches.open(cacheName).then((cache) => cache.match(req).then((hit) => {
    const net = fetch(req).then((res) => {
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    }).catch(() => hit);
    return hit || net;
  }));
}

function cacheFirst(req, cacheName) {
  return caches.open(cacheName).then((cache) => cache.match(req).then((hit) => {
    if (hit) return hit;
    return fetch(req).then((res) => {
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    });
  }));
}

self.addEventListener('fetch', (ev) => {
  const req = ev.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // Foto degli esercizi dal CDN.
  if (url.hostname === IMG_HOST) {
    ev.respondWith(cacheFirst(req, IMAGES).catch(() => new Response('', { status: 504 })));
    return;
  }

  if (url.origin !== location.origin) return;

  // Catalogo: se c'e' rete lo aggiorna, altrimenti serve quello salvato.
  if (url.pathname.endsWith('/data/catalog.json')) {
    ev.respondWith(staleWhileRevalidate(req, DATA));
    return;
  }

  // Pagina e guscio: sempre dalla versione installata, tutta insieme.
  // L'aggiornamento arriva col service worker nuovo, non file per file.
  if (req.mode === 'navigate') {
    ev.respondWith(
      caches.open(SHELL)
        .then((c) => c.match('index.html'))
        .then((hit) => hit || fetch(req))
        .catch(() => fetch(req))
    );
    return;
  }

  ev.respondWith(
    caches.open(SHELL)
      .then((c) => c.match(req, { ignoreSearch: true }))
      .then((hit) => hit || fetch(req))
  );
});
