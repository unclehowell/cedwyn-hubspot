/* Cedwyn dbfs - reads a file's bytes straight out of the one catalogue database (/db/cedwyn.sqlite3.NNN chunks).
   /db/blobmap.json (written by tools/dbmap.py at build time) says, for every theme path, which row of the `blobs` table holds
   it and where that row's bytes sit in the database file. Each read asks for only the bytes it needs (HTTP Range); where the
   host answers with the whole chunk file instead, the chunk is kept in this browser's cache for later reads. Every result
   is checked against the row's sha256 before it is used. Works in a service worker and in a page. - Sion's Tab agent */
(function (G) {
  var M = null, MP = null, MEM = new Map(), FLY = new Map(), MEMMAX = 24, CN = null;
  function map() {
    if (!MP) MP = fetch('/db/blobmap.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error('blobmap ' + r.status); return r.json(); })
      .then(function (m) { M = m; CN = 'cedwyn-db-' + m.v; return m; }).catch(function (e) { MP = null; throw e; });
    return MP;
  }
  function key(p) { try { p = decodeURIComponent(p); } catch (e) {} return p; }
  function find(path) { var i = M && M.paths[key(path)]; return i == null ? -1 : i; }
  function pad(n) { var s = String(n); while (s.length < M.suffixLength) s = '0' + s; return s; }
  function remember(n, buf) { MEM.set(n, buf); if (MEM.size > MEMMAX) MEM.delete(MEM.keys().next().value); }
  function cacheOpen() { try { return G.caches ? G.caches.open(CN) : Promise.resolve(null); } catch (e) { return Promise.resolve(null); } }
  // bytes [a, b) of chunk n. Asks for just those bytes (Range); a host that answers with the whole chunk file instead is
  // remembered (RANGE=false) and from then on each chunk is fetched once, whole, and kept in the cache.
  var RANGE = null;
  function whole(n, url, c, stats) {
    if (FLY.has(n)) return FLY.get(n);
    var p = fetch(url).then(function (r) { if (!r.ok) throw new Error('chunk ' + n + ' ' + r.status); stats.whole++; return r.arrayBuffer(); })
      .then(function (buf) { remember(n, buf); if (c) try { c.put(url, new Response(buf.slice(0), { headers: { 'Content-Type': 'application/octet-stream' } })).catch(function () {}); } catch (e) {} return buf; });
    FLY.set(n, p); p.then(function () { FLY.delete(n); }, function () { FLY.delete(n); });
    return p;
  }
  function part(n, a, b, stats) {
    var buf = MEM.get(n); if (buf) { stats.mem++; return Promise.resolve(new Uint8Array(buf, a, b - a)); }
    var url = M.prefix + pad(n) + '?v=' + M.v;
    if (FLY.has(n)) return FLY.get(n).then(function (buf) { return new Uint8Array(buf, a, b - a); });
    return cacheOpen().then(function (c) {
      return (c ? c.match(url) : Promise.resolve(null)).then(function (hit) {
        if (hit) return hit.arrayBuffer().then(function (buf) { stats.cache++; remember(n, buf); return new Uint8Array(buf, a, b - a); });
        if (RANGE === false) return whole(n, url, c, stats).then(function (buf) { return new Uint8Array(buf, a, b - a); });
        return fetch(url, { headers: { Range: 'bytes=' + a + '-' + (b - 1) } }).then(function (r) {
          if (r.status === 206) { RANGE = true; stats.range++; return r.arrayBuffer().then(function (x) { return new Uint8Array(x); }); }
          if (!r.ok) throw new Error('chunk ' + n + ' ' + r.status);
          RANGE = false; stats.whole++;
          return r.arrayBuffer().then(function (buf) { remember(n, buf); if (c) try { c.put(url, new Response(buf.slice(0), { headers: { 'Content-Type': 'application/octet-stream' } })).catch(function () {}); } catch (e) {} return new Uint8Array(buf, a, b - a); });
        });
      });
    });
  }
  function hex(buf) { var a = new Uint8Array(buf), s = ''; for (var i = 0; i < 8; i++) s += (a[i] < 16 ? '0' : '') + a[i].toString(16); return s; }
  function read(i) {
    var e = M.blobs[i], n = e[0], C = M.chunk, segs = [[e[1], e[2]]], flat = e[3], rem = n - e[2], U = M.u, PS = M.ps;
    for (var k = 0; k < flat.length; k += 2) for (var pg = flat[k]; pg < flat[k] + flat[k + 1]; pg++) { var t = Math.min(U - 4, rem); segs.push([(pg - 1) * PS + 4, t]); rem -= t; }
    // group the segments by chunk; one request per chunk, covering just the span needed in it
    var want = new Map();
    segs.forEach(function (s) { var o = s[0], l = s[1]; while (l > 0) { var c = Math.floor(o / C), a = o - c * C, b = Math.min(C, a + l), w = want.get(c);
      if (!w) want.set(c, [a, b]); else { w[0] = Math.min(w[0], a); w[1] = Math.max(w[1], b); } l -= b - a; o += b - a; } });
    var stats = { mem: 0, cache: 0, range: 0, whole: 0 }, got = new Map();
    return Promise.all(Array.from(want.keys()).map(function (c) { var w = want.get(c); return part(c, w[0], w[1], stats).then(function (u) { got.set(c, { a: w[0], u: u }); }); }))
      .then(function () {
        var out = new Uint8Array(n), at = 0;
        segs.forEach(function (s) { var o = s[0], l = s[1]; while (l > 0) { var c = Math.floor(o / C), g = got.get(c), a = o - c * C, take = Math.min(l, C - a);
          out.set(g.u.subarray(a - g.a, a - g.a + take), at); at += take; l -= take; o += take; } });
        var sub = G.crypto && G.crypto.subtle;
        if (!sub) return out;
        return sub.digest('SHA-256', out).then(function (d) { if (hex(d) !== e[5]) { MEM.clear(); throw new Error('sha mismatch ' + e[5]); } return out; });
      }).then(function (bytes) { return { bytes: bytes, mime: e[4], sha: e[5], stats: stats }; });
  }
  // the bytes for a site path, or null when the database does not hold that path
  function get(path) { return map().then(function () { var i = find(path); return i < 0 ? null : read(i); }); }
  G.CedwynDB = { map: map, find: function (p) { return M ? find(p) : null; }, get: get, ready: function () { return !!M; }, version: function () { return M && M.v; } };
})(typeof self !== 'undefined' ? self : window);
