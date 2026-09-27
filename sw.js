// Offline support for the installed app.
// Page and index.json: network first, so the daily refresh always shows; the cached copy is used offline.
// details.json?v=<refresh time>: cache first, since each refresh gets a new URL; older copies are dropped.
// Brand photos are not touched here; the browser's own cache handles them.
const CACHE = 'saree-v2';
const SHELL = ['./', 'index.html', 'manifest.webmanifest', 'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const networkFirst = async req => {
  const c = await caches.open(CACHE);
  try {
    const res = await fetch(req);
    if (res.ok) c.put(req, res.clone());
    return res;
  } catch (err) {
    return (await c.match(req, { ignoreSearch: true })) || (req.mode === 'navigate' && await c.match('index.html')) || Promise.reject(err);
  }
};
const cacheFirstVersioned = async req => {
  const c = await caches.open(CACHE);
  const hit = await c.match(req);
  if (hit) return hit;
  try {
    const res = await fetch(req);
    if (res.ok) {
      const base = new URL(req.url).pathname;
      for (const k of await c.keys()) if (new URL(k.url).pathname === base) await c.delete(k);
      await c.put(req, res.clone());
    }
    return res;
  } catch (err) {
    return (await c.match(req, { ignoreSearch: true })) || Promise.reject(err);
  }
};

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname.endsWith('/data/details.json')) e.respondWith(cacheFirstVersioned(req));
  else e.respondWith(networkFirst(req));
});
