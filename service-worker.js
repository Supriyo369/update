const cacheName = 'app-cache-v1';
const filesToCache = [
  'https://shipwithsupriyo.netlify.app/assets/css/theme.css',
  'C:\\Users\\Supriyo\\Desktop\\SWS\\courier\\192x192.png',
  'C:\\Users\\Supriyo\\Desktop\\SWS\\courier\\512x512.png',
];

// Install the service worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(cacheName).then(cache => {
      return cache.addAll(filesToCache);
    })
  );
});

// Activate the service worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== cacheName) {
            return caches.delete(cache);
          }
        })
      );
    })
  );
});

// Fetch the cached content
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
