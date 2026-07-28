/* Bird Population Decline AI — service worker (offline shell) */
const CACHE = "bpd-v1";
const ASSETS = [
  "/", "/dashboard", "/methodology", "/explore", "/about", "/faq",
  "/assets/css/style.css", "/assets/js/site.js", "/assets/js/dashboard.js",
  "/assets/icon.svg", "/manifest.webmanifest",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(ASSETS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // Never cache the API or cross-origin requests (Mapbox tiles, CDNs, geocoding).
  if (url.pathname.startsWith("/api/")) return;
  if (url.origin !== location.origin) return;
  // Cache-first for the static shell, fall back to network, then to home when offline.
  e.respondWith(
    caches.match(e.request).then((cached) =>
      cached || fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match("/"))
    )
  );
});
