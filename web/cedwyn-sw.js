/* Cedwyn service worker - every theme reads its data and evidence from the one catalogue database.
   Requests for a theme's JSON/CSV/XML, images, PDFs and audio are answered from the database chunks (via dbfs.js); pages,
   scripts and styles, and any file the database does not hold, go to the network as before. Responses served from the
   database carry the header X-Cedwyn-Source: db. - Sion's Tab agent */
importScripts('/_cedwyn/dbfs.js?v=3');
// sw build 2026-10-25h: checkout pass-through for Stripe/Gumroad/Mailchimp (runtime v=8); Wales and Argentina sections (header v2.1.9) (new bytes, so phones update the worker)
var EXT = /\.(json|csv|xml|geojson|png|jpe?g|gif|webp|svg|avif|ico|bmp|tiff?|pdf|docx?|mp3|m4a|ogg|wav)$/i;
self.addEventListener('install', function (e) { self.skipWaiting(); e.waitUntil(CedwynDB.map().catch(function () {})); });
self.addEventListener('activate', function (e) {
  e.waitUntil(CedwynDB.map().catch(function () {}).then(function () {
    var keep = 'cedwyn-db-' + CedwynDB.version();
    return caches.keys().then(function (ks) { return Promise.all(ks.filter(function (k) { return k.indexOf('cedwyn-db-') === 0 && k !== keep; }).map(function (k) { return caches.delete(k); })); });
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('message', function (e) { if (e.data === 'claim') self.clients.claim(); });
function respond(o, req) {
  var b = o.bytes, h = { 'Content-Type': o.mime, 'X-Cedwyn-Source': 'db', 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-cache' };
  if (/^(text\/|application\/(json|xml))/.test(o.mime)) h['Content-Type'] = o.mime + '; charset=utf-8';
  var rg = req.headers.get('Range'), m = rg && /bytes=(\d*)-(\d*)/.exec(rg);
  if (m && (m[1] || m[2])) {
    var s = m[1] ? +m[1] : Math.max(0, b.length - +m[2]), e = m[1] && m[2] ? Math.min(+m[2], b.length - 1) : b.length - 1;
    if (s >= b.length) return new Response(null, { status: 416, headers: { 'Content-Range': 'bytes */' + b.length } });
    h['Content-Range'] = 'bytes ' + s + '-' + e + '/' + b.length; h['Content-Length'] = String(e - s + 1);
    return new Response(b.slice(s, e + 1), { status: 206, headers: h });
  }
  h['Content-Length'] = String(b.length);
  return new Response(b, { status: 200, headers: h });
}
self.addEventListener('fetch', function (e) {
  var r = e.request; if (r.method !== 'GET') return;
  var u = new URL(r.url); if (u.origin !== self.location.origin) return;
  var p = u.pathname; if (p.indexOf('/db/') === 0 || p.indexOf('/_cedwyn/') === 0) return;
  // 25 Oct 2026: /wales/<theme>/... and /argentina/<theme>/... are the same theme files: try the plain theme path too
  var p2 = p.replace(/^\/(wales|argentina)(\/[^\/]+\/)/, '$2');
  if (CedwynDB.ready()) { if (CedwynDB.find(p) < 0) { if (p2 !== p && CedwynDB.find(p2) >= 0) p = p2; else return; } }
  else if (!EXT.test(p)) return;
  e.respondWith(CedwynDB.get(p).then(function (o) { return o ? respond(o, r) : (p2 !== p ? CedwynDB.get(p2).then(function (o2) { return o2 ? respond(o2, r) : fetch(r); }) : fetch(r)); }).catch(function () { return fetch(r); }));
});
