/* D&D Companion Service Worker - vollständig unabhängig von der Lern-App */

const CACHE_NAME = 'dnd-companion-v1';
const ASSET_CACHE = 'dnd-assets-v1';

const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './css/variables.css',
  './css/base.css',
  './css/dashboard.css',
  './css/modals.css',
  './css/responsive.css',
  './js/utils.js',
  './js/storage.js',
  './js/character.js',
  './js/transaction.js',
  './js/resources.js',
  './js/modal.js',
  './js/ui.js',
  './js/views.js',
  './js/nav.js',
  './js/app.js',
  './icons/icon.svg'
];

// Cleanup: Entferne alle alten Service Worker Registrierungen mit falschen Scopes
if (typeof self.clients !== 'undefined') {
  self.addEventListener('install', function() {
    self.skipWaiting();
  });
}

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS_TO_CACHE).then(() => {
        self.skipWaiting();
      });
    })
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name !== CACHE_NAME && name !== ASSET_CACHE)
          .map(name => caches.delete(name))
      ).then(() => {
        self.clients.claim();
      });
    })
  );
});

self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  event.respondWith(
    fetch(event.request)
      .then(response => {
        const clone = response.clone();
        caches.open(ASSET_CACHE).then(cache => {
          cache.put(event.request, clone);
        });
        return response;
      })
      .catch(() => {
        return caches.match(event.request);
      })
  );
});
