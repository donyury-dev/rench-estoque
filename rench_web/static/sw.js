const CACHE_NAME = 'rench-mobile-v7';
const URLS_TO_CACHE = [
  '/mobile',
  '/mobile?v=3',
  '/suprimentos/mobile',
  '/static/manifest.json?v=3',
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
      Promise.all(keys.map(key => {
        if (key !== CACHE_NAME) {
          return caches.delete(key);
        }
      }))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  
  // Sempre busca paginas dinamicas na rede primeiro
  if (event.request.mode === 'navigate' || 
      event.request.url.includes('/mobile') || 
      event.request.url.includes('/suprimentos/mobile')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Atualiza o cache com a resposta da rede
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }
  
  // Para arquivos estaticos, cache first
  event.respondWith(
    caches.match(event.request).then(cached => {
      return cached || fetch(event.request).then(response => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        return response;
      });
    })
  );
});

self.addEventListener('push', event => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch(e) {
    data = { title: 'RENCH Equipamentos', body: event.data ? event.data.text() : 'Nova notificacao' };
  }
  const title = data.title || 'RENCH Equipamentos';
  const options = {
    body: data.body || 'Nova notificacao',
    icon: data.icon || '/static/logo_rench.png',
    badge: data.badge || '/static/logo_rench.png',
    tag: data.tag || 'rench-default',
    requireInteraction: false,
    data: data.data || {}
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  const urlToOpen = event.notification.data && event.notification.data.url ? event.notification.data.url : '/';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
      for(const client of windowClients){
        if(client.url === urlToOpen && 'focus' in client){
          return client.focus();
        }
      }
      if(clients.openWindow){
        return clients.openWindow(urlToOpen);
      }
    })
  );
});
