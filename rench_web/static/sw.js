const CACHE_NAME = 'rench-estoque-v3';
const URLS_TO_CACHE = [
  '/suprimentos/mobile?v=3',
  '/static/manifest.json?v=3',
  '/static/logo_rench.png'
];

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(key => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if(event.request.method !== 'GET') return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request)));
});
