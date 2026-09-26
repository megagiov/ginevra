// Tiene l'app disponibile anche senza rete (in campo spesso non c'e').
// Cambia VERSION a ogni pubblicazione per aggiornare la cache.
const VERSION = 'padel-v5';
const FILES = ['./', './index.html', './style.css', './app.js', './engine.js', './quick.js', './manifest.json',
  './icons/icon-192.png', './icons/icon-512.png', './icons/apple-touch-icon.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    // Solo le cache di Padel: sullo stesso dominio possono esserci altre app.
    .then((keys) => Promise.all(keys.filter((k) => k.startsWith('padel-') && k !== VERSION).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Rete prima (per avere sempre l'ultima versione), cache se offline.
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(VERSION).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }).then((r) => r || caches.match('./index.html')))
  );
});
