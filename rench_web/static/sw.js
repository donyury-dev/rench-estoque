const CACHE_NAME = 'rench-estoque-v2';
const URLS_TO_CACHE = [
  '/suprimentos/mobile',
  '/static/manifest.json?v=2',
  '/static/logo_rench.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(URLS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if(event.request.method !== 'GET') return;

  const req = event.request;

  if(req.url.includes('/api/') || req.url.includes('/suprimentos/mobile')){
    event.respondWith(
      fetch(req).then(networkResp => {
        const clone = networkResp.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(req, clone));
        return networkResp;
      }).catch(() => caches.match(req))
    );
    return;
  }

  event.respondWith(
    caches.match(req).then(response => {
      return response || fetch(req).catch(() => {
        if(req.mode === 'navigate'){
          return caches.match('/suprimentos/mobile');
        }
      });
    })
  );
});
