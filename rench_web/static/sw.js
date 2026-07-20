const CACHE_NAME = 'rench-suprimentos-v1';
const URLS_TO_CACHE = [
  '/suprimentos/mobile',
  '/static/manifest.json',
  '/static/logo_rench.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(URLS_TO_CACHE))
  );
});

self.addEventListener('fetch', event => {
  if(event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request).catch(() => {
        if(event.request.mode === 'navigate'){
          return caches.match('/suprimentos/mobile');
        }
      });
    })
  );
});
