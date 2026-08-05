const CACHE_NAME = 'rench-estoque-v5';
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
