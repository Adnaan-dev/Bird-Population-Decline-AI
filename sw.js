/* Bird Population Decline AI — service worker (offline shell) */
const CACHE = "bpd-v3";
const ASSETS = [
  "/", "/dashboard", "/methodology", "/explore", "/about", "/faq",
  "/assets/css/style.css", "/assets/js/site.js", "/assets/js/dashboard.js",
  "/assets/icon.svg", "/manifest.webmanifest",
  "/assets/img/eagle1.png", "/assets/img/eagle2.png", "/assets/img/eagle3.png",
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

  // Network-first for page navigations (HTML) so users always get the latest
  // markup; fall back to the cached shell only when offline.
  if (e.request.mode === "navigate") {
    e.respondWith(
      fetch(e.request).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy)).catch(() => {});
        return res;
      }).catch(() => caches.match(e.request).then((c) => c || caches.match("/")))
    );
    return;
  }

  // Cache-first for the static shell (css/js/img), fall back to network.
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
