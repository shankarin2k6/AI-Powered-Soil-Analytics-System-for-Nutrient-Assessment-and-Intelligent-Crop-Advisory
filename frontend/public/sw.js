/* Service worker: lets the app install on a phone and open without a connection.
 *
 *  - App files (/_next/static, icons): saved on first use, served from the phone afterwards.
 *  - Pages: network first, the saved copy when there is no signal (offline.html if never opened before).
 *  - Saved results (the API's read-only GET calls): network first, saved copy when there is no signal.
 *  - Never saved: photo/test uploads, the voice audio, login and logout.
 * The saved results belong to one farmer, so the app deletes the DATA cache on logout (see src/lib/pwa.ts).
 * Change VERSION when this file changes so old caches are thrown away.
 */
const VERSION = "v3";
const SHELL = `soil-shell-${VERSION}`;
const STATIC = `soil-static-${VERSION}`;
const DATA = "soil-data-v1";            // the name is also used in src/lib/pwa.ts
const MAX_DATA_ENTRIES = 150;
const PAGES = ["/", "/login", "/signup", "/capture", "/soil-test", "/analysis", "/history", "/report", "/offline.html"];

// read-only API calls worth keeping for offline use
const SAVEABLE_API = /^\/api\/v1\/(auth\/me|fields|analyses|images|analysis\/status|fertilizer-plan)/;

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    await Promise.allSettled(PAGES.map((p) => cache.add(p)));   // one failing page must not stop the install
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keep = [SHELL, STATIC, DATA];
    for (const name of await caches.keys()) if (!keep.includes(name)) await caches.delete(name);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                       // uploads and logins go straight to the network
  const url = new URL(req.url);

  if (url.pathname.startsWith("/api/v1/")) {
    const one = url.pathname.match(/^\/api\/v1\/analyses\/(\d+)$/);
    if (one) event.respondWith(analysisWithFallback(req, Number(one[1])));
    else if (SAVEABLE_API.test(url.pathname)) event.respondWith(networkFirst(req, DATA, 5000));
    return;
  }
  if (url.origin !== location.origin) return;

  if (url.pathname.startsWith("/_next/static/") || url.pathname.startsWith("/icons/")) {
    event.respondWith(cacheFirst(req, STATIC));
  } else if (req.mode === "navigate") {
    event.respondWith(navigate(req, url));
  } else {
    event.respondWith(networkFirst(req, SHELL, 4000));
  }
});

async function cacheFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  const hit = await cache.match(req);
  if (hit) return hit;
  const res = await fetch(req);
  if (res.ok) cache.put(req, res.clone());
  return res;
}

/** Network first. If a saved copy exists and the network is slower than `ms`, use the saved copy (weak signal). */
async function networkFirst(req, cacheName, ms) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(req);
  const network = fetch(req).then((res) => {
    if (res.ok || res.type === "opaque") {
      cache.put(req, res.clone()).then(() => trim(cacheName)).catch(() => {});
    }
    return res;
  });
  if (!cached) return network;                              // nothing saved: the real result or the real error
  return Promise.race([
    network.catch(() => cached),
    new Promise((resolve) => setTimeout(() => resolve(cached), ms)),
  ]);
}

/** One saved result: if it was never opened by itself, rebuild it from a saved list (home, history) that holds it. */
async function analysisWithFallback(req, id) {
  try {
    return await networkFirst(req, DATA, 5000);
  } catch (err) {
    const found = await findAnalysis(id);
    if (found) return new Response(JSON.stringify(found), { headers: { "Content-Type": "application/json" } });
    throw err;
  }
}

async function findAnalysis(id) {
  const cache = await caches.open(DATA);
  for (const key of await cache.keys()) {
    const m = new URL(key.url).pathname.match(/^\/api\/v1\/fields\/(\d+)\/(analyses|history)$/);
    if (!m) continue;
    try {
      const rows = await (await cache.match(key)).json();
      for (const row of rows) {
        if (m[2] === "analyses" && row.id === id) return row;                       // already the same shape
        if (m[2] === "history" && row.type === "analysis" && row.id === id) {         // history rows nest the result
          return { id, field_id: Number(m[1]), image_id: row.data.image_id, soil_test_id: row.data.soil_test_id,
                   model_version: row.data.model_version, created_at: row.created_at, result: row.data.result };
        }
      }
    } catch { /* a damaged entry: try the next one */ }
  }
  return null;
}

async function navigate(req, url) {
  const cache = await caches.open(SHELL);
  const key = url.origin + url.pathname;                    // /analysis?id=3 and /analysis?id=4 share one page file
  try {
    const res = await fetch(req);
    if (res.ok && !res.redirected) cache.put(key, res.clone());
    return res;
  } catch {
    return (await cache.match(key)) || (await cache.match("/offline.html")) || Response.error();
  }
}

async function trim(cacheName) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();
  if (cacheName === DATA && keys.length > MAX_DATA_ENTRIES) {
    for (const k of keys.slice(0, keys.length - MAX_DATA_ENTRIES)) await cache.delete(k);
  }
}
