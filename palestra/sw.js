/* Service worker: l'app parte anche senza rete.
 * - guscio dell'app: precaricato all'installazione
 * - catalogo esercizi: aggiornato quando c'e' rete, servito dalla cache quando non c'e'
 * - foto degli esercizi: salvate man mano che le guardi */
const VERSION = 'v1';
const SHELL = 'palestra-shell-' + VERSION;
const DATA = 'palestra-data-' + VERSION;
const IMAGES = 'palestra-img';           // niente versione: le foto non cambiano mai
const IMG_HOST = 'cdn.jsdelivr.net';

const SHELL_FILES = [
  './',
  'index.html',
  'app.css',
  'fonts.css',
  'manifest.webmanifest',
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
      // addAll fallisce tutto se un file manca: meglio uno per uno.
      .then((c) => Promise.all(SHELL_FILES.map((f) => c.add(f).catch(() => null))))
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

  // Navigazione: sempre il guscio, cosi' l'app apre anche offline.
  if (req.mode === 'navigate') {
    ev.respondWith(
      fetch(req).catch(() => caches.match('index.html', { cacheName: SHELL })
        .then((hit) => hit || caches.match('./')))
    );
    return;
  }

  ev.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res && res.ok && (url.pathname.indexOf('/js/') !== -1 || url.pathname.indexOf('/fonts/') !== -1)) {
        const copy = res.clone();
        caches.open(SHELL).then((c) => c.put(req, copy));
      }
      return res;
    }))
  );
});
