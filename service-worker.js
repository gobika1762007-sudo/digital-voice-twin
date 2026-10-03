// Digital Voice Twin — Service Worker
const CACHE_NAME = "dvt-v2";
const STATIC_ASSETS = [
  "/",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

// Install — cache static assets
self.addEventListener("install", function(e) {
  e.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS).catch(function(err) {
        console.log("Cache install error:", err);
      });
    })
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener("activate", function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE_NAME; })
            .map(function(k) { return caches.delete(k); })
      );
    })
  );
  self.clients.claim();
});

// Fetch — network first, cache fallback
self.addEventListener("fetch", function(e) {
  // Skip non-GET and API calls
  if (e.request.method !== "GET") return;
  if (e.request.url.includes("/chat") || e.request.url.includes("/audio")) return;

  e.respondWith(
    fetch(e.request)
      .then(function(response) {
        // Cache successful responses
        if (response && response.status === 200) {
          var clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(e.request, clone);
          });
        }
        return response;
      })
      .catch(function() {
        // Network failed — try cache
        return caches.match(e.request).then(function(cached) {
          if (cached) return cached;
          // Offline fallback
          return new Response(
            '<html><body style="background:#0d0d1a;color:#0fa;font-family:sans-serif;text-align:center;padding:50px">' +
            '<h2>📡 Offline</h2><p>Internet connection illaye. Try again!</p></body></html>',
            { headers: { "Content-Type": "text/html" } }
          );
        });
      })
  );
});
