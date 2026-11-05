// Evidence preview endpoint for the research pages' pop-up (query: path, or url on this same site).
// Answers JSON {found, title, excerpt, url}, read from the published page itself through the static assets; no other data.
var SKIP = /^(small print|page id|page type|ev id|evidence status|version|about this page|read the docs)\b/i;
function dec(s) {
  return s.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#0?39;|&rsquo;|&#8217;|&lsquo;|&#8216;/g, "'")
    .replace(/&ldquo;|&#8220;|&rdquo;|&#8221;/g, '"').replace(/&mdash;|&#8212;/g, "\u2014").replace(/&ndash;|&#8211;/g, "\u2013")
    .replace(/&hellip;|&#8230;/g, "\u2026").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, function (m, n) { return String.fromCharCode(+n); });
}
function txt(s) { return dec(String(s || "").replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>/gi, " ").replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim(); }
function cut(s, n) { return s.length > n ? s.slice(0, n).replace(/\s+\S*$/, "") + "\u2026" : s; }
function meta(h, re) { var m = h.match(re); return m ? txt(m[1]) : ""; }
function pick(html) {
  var title = meta(html, /<h1[^>]*>([\s\S]*?)<\/h1>/i) || meta(html, /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']*)["']/i) || meta(html, /<title[^>]*>([\s\S]*?)<\/title>/i);
  var desc = meta(html, /<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)["']/i);
  var start = html.search(/class=["'][^"']*\bcontent\b/i); if (start < 0) start = html.search(/<main\b/i); if (start < 0) start = html.search(/<h1\b/i);
  var body = start < 0 ? html : html.slice(start), ex = "", re = /<p\b[^>]*>([\s\S]*?)<\/p>/gi, m, k = 0;
  while ((m = re.exec(body)) && k++ < 40) { var t = txt(m[1]); if (t.length >= 60 && !SKIP.test(t) && t.indexOf("Editing Protocol") < 0) { ex = t; break; } }
  if (!ex && desc.length >= 40 && !SKIP.test(desc)) ex = desc;
  return { title: cut(title, 160), excerpt: cut(ex, 360) };
}
function out(o, st) {
  return new Response(JSON.stringify(o), { status: st || 200, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=300", "X-Content-Type-Options": "nosniff" } });
}
export async function onRequestGet(ctx) {
  var req = ctx.request, here = new URL(req.url), q = here.searchParams, p = q.get("path") || "";
  if (!p && q.get("url")) { try { var u = new URL(q.get("url"), here.origin); if (u.origin === here.origin) p = u.pathname; } catch (e) {} }
  if (!p || p.charAt(0) !== "/" || p.charAt(1) === "/" || p.length > 600 || /^\/api\//.test(p)) return out({ found: false });
  try {
    var target = new URL(p, here.origin), res = null;
    for (var i = 0; i < 4; i++) {
      res = await ctx.env.ASSETS.fetch(new Request(target.toString(), { headers: { Accept: "text/html" } }));
      var loc = res.headers.get("Location");
      if (res.status >= 300 && res.status < 400 && loc) { var nx = new URL(loc, target); if (nx.origin !== here.origin) return out({ found: false }); target = nx; continue; }
      break;
    }
    if (!res || res.status !== 200 || (res.headers.get("Content-Type") || "").indexOf("text/html") < 0) return out({ found: false });
    var html = await res.text(), r = pick(html.slice(0, 400000));
    if (!r.title) return out({ found: false });
    return out({ found: true, title: r.title, excerpt: r.excerpt, url: target.pathname + target.search });
  } catch (e) { return out({ found: false }); }
}
export async function onRequest() { return new Response(null, { status: 405, headers: { Allow: "GET" } }); }
