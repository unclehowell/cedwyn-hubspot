/*! Cedwyn version gate · /_cedwyn/version-gate.js · v1.0.0 (2026-11-01) · Cedwyn editors · standard docs/VERSION-STANDARD.md 1.0.0
 * A click-to-load facade in the media slot (never a full-page overlay, never a separate chooser page): where a gated item would
 * load (the e-book PDF reader, a documentary clip), a random image from the NFT collection shows with "Select a version" and a
 * down arrow, and a drop-down of the item's versions from /_cedwyn/version-gate.json, the free one preselected (one tap opens it).
 * Prices are computed, never typed: the latest version costs the item's current price, each earlier one £4.99 less per step back
 * (never below £0), v0.0.1 always free. An (i) beside the drop-down opens a table of every version (version, date, what changed,
 * pages or length, price). Choosing the free version loads the item in place; the latest paid version goes to the existing
 * checkout (the page's own Buy button). While a free item is open a one-line, dismissible bar names the latest version with its
 * whole price and size, linking inside the site. The choice is kept for the browser session (sessionStorage "cvg:<item>").
 * An item with no paid version gets no gate. Pages with no matching item are untouched; without JS every item keeps its plain link.
 * Argentina scope: no prices, no bar. Counts: /_cedwyn/ev/vgate-shown|passed|paid/<item>/<page>, <html data-cvg-shown/-passed>.
 * Loaded (deferred) by /_cedwyn/ghf/ghf-boot.js.
 * CHANGELOG
 * 1.0.0 (2026-11-01): first version: e-books (shelf reader + /ebooks/read/), the (i) version table, the one-step price ladder;
 *   documentary clips wired but inert until the player names a clip's door. */
(function () {
  "use strict";
  if (window.CedwynVersionGate) return;
  var d = document, de = d.documentElement, VER = "1.0.0", MF = "/_cedwyn/version-gate.json?v=" + VER, M = null, pending = null;
  var T = {
    sel: {en: "Select a version", cy: "Dewiswch fersiwn", es: "Seleccione una versión"},
    free: {en: "free", cy: "am ddim", es: "gratis"},
    freeword: {en: "Free", cy: "Am ddim", es: "Gratis"},
    pages: {en: "pages", cy: "tudalen", es: "páginas"},
    min: {en: "min", cy: "mun", es: "min"},
    openp: {en: "Open the free version", cy: "Agor y fersiwn am ddim", es: "Abrir la versión gratuita"},
    openc: {en: "Play the free version", cy: "Chwarae’r fersiwn am ddim", es: "Ver la versión gratuita"},
    buy: {en: "Buy", cy: "Prynu", es: "Comprar"},
    see: {en: "See", cy: "Gweld", es: "Ver"},
    bar: {en: "Newest", cy: "Diweddaraf", es: "Más reciente"},
    added: {en: "What’s added", cy: "Beth sy’n newydd", es: "Qué añade"},
    hide: {en: "Hide", cy: "Cuddio", es: "Ocultar"},
    info: {en: "What changed in each version", cy: "Beth newidiodd ym mhob fersiwn", es: "Qué cambió en cada versión"},
    ver: {en: "Version", cy: "Fersiwn", es: "Versión"},
    date: {en: "Date", cy: "Dyddiad", es: "Fecha"},
    what: {en: "What changed", cy: "Beth newidiodd", es: "Qué cambió"},
    size_pages: {en: "Pages", cy: "Tudalennau", es: "Páginas"},
    size_length: {en: "Length", cy: "Hyd", es: "Duración"},
    price: {en: "Price", cy: "Pris", es: "Precio"},
    close: {en: "Close", cy: "Cau", es: "Cerrar"}
  };
  function L() { var l = "en"; try { l = (window.GHFLang && GHFLang.get()) || de.getAttribute("lang") || "en"; } catch (e) {} l = String(l).slice(0, 2); return T.sel[l] ? l : "en"; }
  function t(k) { var l = L(); return (T[k] && (T[k][l] || T[k].en)) || k; }
  function nf(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ","); }
  function el(tag, cls, txt) { var x = d.createElement(tag); if (cls) x.className = cls; if (txt != null) x.textContent = txt; return x; }
  function argentina() { var s = de.getAttribute("data-cedwyn-scope"); return s === "argentina" || /^\/(argentina|patagonia)(\/|$)/.test(location.pathname); }
  function ss(k, v) { try { if (v === undefined) return sessionStorage.getItem("cvg:" + k); sessionStorage.setItem("cvg:" + k, v); } catch (e) {} return null; }
  function count(name, key) {
    var a = "data-cvg-" + name; de.setAttribute(a, String((+de.getAttribute(a) || 0) + 1));
    try { new Image().src = "/_cedwyn/ev/vgate-" + name + "/" + encodeURIComponent(String(key).replace(/[^a-z0-9.:-]+/gi, "-")) + "/" + encodeURIComponent((location.pathname.replace(/^\/|\/$/g, "") || "home").replace(/\//g, "_")); } catch (e) {}
  }
  function css() {
    if (d.querySelector("link[data-cvg]")) return;
    var l = d.createElement("link"); l.rel = "stylesheet"; l.href = "/_cedwyn/version-gate.css?v=" + VER; l.setAttribute("data-cvg", ""); (d.head || de).appendChild(l);
  }
  function load() {
    if (M) return Promise.resolve(M);
    return fetch(MF, {credentials: "same-origin"}).then(function (r) { if (!r.ok) throw r.status; return r.json(); }).then(function (j) { M = j; return j; });
  }
  /* ---------- the standard: versions oldest first; prices by the one-step ladder ---------- */
  function gbp(s) { var n = parseFloat(String(s == null ? "" : s).replace(/[^0-9.]/g, "")); return isFinite(n) ? n : 0; }
  function prices(item) {   // latest = the item's current price; each step back £4.99 less, floored at 0; v0.0.1 free
    var vs = item.versions, top = gbp(item.price), step = (M && M.price_step_gbp) || 4.99, n = vs.length;
    return vs.map(function (o, i) { return o.v === "0.0.1" ? 0 : Math.max(0, Math.round((top - step * (n - 1 - i)) * 100) / 100); });
  }
  function money(n) { return n > 0 ? "£" + n.toFixed(2) : t("freeword"); }
  function size(item, o) { if (item.unit === "length" && o.seconds) return Math.round(o.seconds / 60) + " " + t("min"); return o.pages ? nf(o.pages) + " " + t("pages") : ""; }
  /* "v0.0.1 — free (20 pages)" · "v0.0.2 — £4.99 (221 pages)" */
  function label(item, i) {
    var o = item.versions[i], p = item.p[i], sz = size(item, o);
    return "v" + o.v + " — " + (p > 0 ? (argentina() ? "" : "£" + p.toFixed(2)) : t("free")) + (sz ? " (" + sz + ")" : "");
  }
  function dt(s) { try { return new Date(s + "T12:00:00Z").toLocaleDateString(L() === "cy" ? "cy-GB" : L() === "es" ? "es-ES" : "en-GB", {day: "numeric", month: "short", year: "numeric"}); } catch (e) { return s || ""; } }
  function ready(item) {   // computes prices; returns null when there is nothing to gate (no paid version)
    if (!item || !item.versions || !item.versions.length) return null;
    item.p = prices(item); item.last = item.versions.length - 1;
    item.freeI = item.p.indexOf(0); if (item.freeI < 0 || !(item.p[item.last] > 0)) return null;
    return item;
  }
  /* ---------- the (i) version table: a dialog inside the facade ---------- */
  function table(item, host, opener) {
    var old = host.querySelector(".cvg-log"); if (old) { old.remove(); return; }
    var p = el("div", "cvg-log"); p.setAttribute("role", "dialog"); p.setAttribute("aria-modal", "true"); p.setAttribute("aria-label", t("info")); p.tabIndex = -1;
    var hd = el("div", "cvg-logh"); hd.appendChild(el("strong", "", t("info")));
    var x = el("button", "cvg-logx", "×"); x.type = "button"; x.setAttribute("aria-label", t("close")); x.title = t("close"); hd.appendChild(x); p.appendChild(hd);
    var heads = [t("ver"), t("date"), t("what"), t(item.unit === "length" ? "size_length" : "size_pages"), t("price")];
    var tb = el("table", "cvg-tab"), th = el("tr"); heads.forEach(function (h) { var c = el("th", "", h); c.scope = "col"; th.appendChild(c); });
    var thead = el("thead"); thead.appendChild(th); tb.appendChild(thead); var body = el("tbody");
    for (var i = item.versions.length - 1; i >= 0; i--) {
      var o = item.versions[i], tr = el("tr"), cells = ["v" + o.v, dt(o.date), o.change || "", size(item, o).replace(/ \S+$/, ""), argentina() ? "" : money(item.p[i])];
      cells.forEach(function (c, j) { var td = el("td", "cvg-c" + j, c); td.setAttribute("data-l", heads[j]); tr.appendChild(td); });
      body.appendChild(tr);
    }
    tb.appendChild(body); p.appendChild(tb); host.appendChild(p);
    function shut() { p.remove(); try { opener.focus(); } catch (e) {} }
    x.addEventListener("click", shut);
    p.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); shut(); }
      else if (ev.key === "Tab") { ev.preventDefault(); x.focus(); }   // one control inside: focus stays on Close
    });
    try { x.focus(); } catch (e) {}
  }
  /* ---------- the facade, built inside the slot the item would load into ---------- */
  function facade(item) {
    css(); count("shown", item.key);
    var f = el("div", "cvg"); f.setAttribute("data-no-translate", ""); f.setAttribute("data-ghf-keep", "");
    var fig = el("figure", "cvg-fig"), imgs = (M && M.images) || [];
    if (imgs.length) { var im = el("img", "cvg-img"); im.alt = ""; im.decoding = "async"; im.src = imgs[Math.floor(Math.random() * imgs.length)]; fig.appendChild(im); }
    var cap = el("figcaption", "cvg-cap"), h = el("span", "cvg-h", t("sel")); cap.appendChild(h); var ar = el("span", "cvg-arr", "↓"); ar.setAttribute("aria-hidden", "true"); cap.appendChild(ar);
    fig.appendChild(cap); f.appendChild(fig);
    var id = "cvg-s-" + Math.random().toString(36).slice(2, 8), lab = el("label", "cvg-lab", t("sel")); lab.htmlFor = id; f.appendChild(lab);
    var s = el("select", "cvg-s"); s.id = id; s.setAttribute("autocomplete", "off");
    var opts = [];
    item.versions.forEach(function (o, i) { if (item.p[i] > 0 && argentina()) return; var op = el("option", "", label(item, i)); op.value = String(i); if (i === item.freeI) op.selected = true; s.appendChild(op); opts.push([op, i]); });
    var row = el("div", "cvg-row"); row.appendChild(s);
    var ib = el("button", "cvg-i", "i"); ib.type = "button"; ib.setAttribute("aria-label", t("info")); ib.title = t("info"); ib.setAttribute("aria-haspopup", "dialog");
    ib.addEventListener("click", function () { table(item, f, ib); }); row.appendChild(ib); f.appendChild(row);
    var b = el("button", "cvg-go"); b.type = "button"; f.appendChild(b);
    function paint() { var i = +s.value; b.textContent = item.p[i] > 0 ? t("buy") + " v" + item.versions[i].v + " · £" + item.p[i].toFixed(2) : t(item.cut ? "openc" : "openp"); }
    paint();
    function go(i) { if (item.p[i] > 0) { count("paid", item.key); item.buy(i); } else { ss(item.key, "free"); count("passed", item.key); item.open(); bar(item); } }
    s.addEventListener("change", function () { paint(); if (!(item.p[+s.value] > 0)) go(+s.value); });
    b.addEventListener("click", function () { go(+s.value); });
    d.addEventListener("ghf-lang-change", function () { h.textContent = t("sel"); lab.textContent = t("sel"); ib.setAttribute("aria-label", t("info")); ib.title = t("info"); opts.forEach(function (a) { a[0].textContent = label(item, a[1]); }); paint(); });
    return f;
  }
  /* ---------- the bar: one line, dismissible, while the free item is open ---------- */
  var BAR = null, watch = null;
  function hideBar() { if (BAR) BAR.hidden = true; de.classList.remove("cvg-barred"); clearInterval(watch); }
  function bar(item) {
    if (argentina() || ss(item.key + ":bar") === "x") return;
    css();
    if (!BAR) { BAR = el("div", "cvg-bar"); BAR.setAttribute("role", "status"); BAR.setAttribute("data-no-translate", ""); BAR.setAttribute("data-ghf-keep", ""); (d.body || de).appendChild(BAR); }
    BAR.innerHTML = "";
    var o = item.versions[item.last], sz = size(item, o);
    BAR.appendChild(el("span", "cvg-bt", t("bar") + " v" + o.v + ": £" + item.p[item.last].toFixed(2) + (sz ? ", " + sz : "")));
    var a = el("a", "cvg-bl", t("added")); a.href = item.path; BAR.appendChild(a);
    var x = el("button", "cvg-bx", "×"); x.type = "button"; x.setAttribute("aria-label", t("hide")); x.title = t("hide");
    x.addEventListener("click", function () { ss(item.key + ":bar", "x"); hideBar(); }); BAR.appendChild(x);
    BAR.hidden = false; de.classList.add("cvg-barred");
    clearInterval(watch); if (item.isOpen) watch = setInterval(function () { if (!item.isOpen()) hideBar(); }, 700);
  }
  /* ---------- e-books: the PDF reader's own slot (.edp-mbody in the reader dialog, [data-edp-viewer] on /ebooks/read/) ---------- */
  function bookKey(gb) { return String(gb || "").split("@")[0]; }
  function ebook(k, title) {
    var e = M && M.ebooks && M.ebooks[k]; if (!e) return null;
    var cid = e.card; if (!cid) { var ca = d.querySelector('a[data-gb^="' + k + '@"]'), li = ca && ca.closest("li[id]"); cid = li ? li.id : ""; }
    var path = (M.purchase_path || "/ebooks/") + (cid ? "#" + cid : "");
    return ready({key: "ebook:" + k, title: title || "", versions: e.versions, price: e.price, unit: e.unit || "pages", path: path,
      buy: function (i) {   // the latest version: the card's own Buy (existing checkout); any other paid version: the shelf
        var card = cid && d.getElementById(cid), go = card && card.querySelector(".sv-go"), sel = card && card.querySelector(".sv-sel");
        if (i === this.last && go && sel) { sel.value = "v" + this.versions[i].v; try { sel.dispatchEvent(new Event("change", {bubbles: true})); } catch (x) {} go.click(); }
        else location.href = path;
      }});
  }
  function swapIn(slot, item, plain) {   // the slot keeps loading off-screen; the facade takes its place until a version is chosen
    var ph = plain ? el("div", "cvg-page") : slot.cloneNode(false); ph.classList.add("cvg-slot"); ph.appendChild(facade(item));
    slot.parentNode.replaceChild(ph, slot);
    item.open = function () { if (ph.parentNode) ph.parentNode.replaceChild(slot, ph); };
    return ph;
  }
  d.addEventListener("click", function (ev) {   // capture: note which book link is being opened
    pending = null;
    if (!M || !window.__edp || ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    var a = ev.target.closest && ev.target.closest("a[data-edp-pdf]"); if (!a) return;
    var gb = a.getAttribute("data-gb") || ((/[?&]book=([^&#]+)/.exec(a.getAttribute("data-edp-pdf")) || [])[1] || "");
    var item = ebook(bookKey(decodeURIComponent(gb)), a.getAttribute("data-title"));
    if (!item) return;
    item.isOpen = function () { var m = d.querySelector(".edp-mod"); return !!(m && !m.hidden); };
    if (ss(item.key) === "free") { setTimeout(function () { bar(item); }, 0); return; }
    pending = item;
  }, true);
  window.addEventListener("click", function () {   // bubble, after the reader has opened: gate its slot
    var item = pending; pending = null; if (!item) return;
    var m = d.querySelector(".edp-mod"); if (!m || m.hidden) return;
    var box = m.querySelector(".edp-mbody"); if (box) swapIn(box, item);
  });
  function readerPage() {
    var vb = d.querySelector("[data-edp-viewer]"); if (!vb) return;
    var item = ebook(bookKey(new URLSearchParams(location.search).get("book") || ""), ""); if (!item) return;
    if (ss(item.key) === "free") { bar(item); return; }
    swapIn(vb, item, true);
  }
  /* ---------- documentary clips (movie/<id>/<id>.<lang>.v<semver>.webm) with an unowned paid cut ---------- */
  function onPath(ps) { var p = location.pathname; return (ps || []).some(function (x) { return p.indexOf(x) === 0; }); }
  function clip(v) {
    var m = M && M.movie, C = window.CedwynDoc; if (!m || !onPath(m.paths) || !C || !C.entries || !C.chips) return null;
    var src = v.currentSrc || v.src || ""; if (!src) { var so = v.querySelector("source"); src = so ? so.src : ""; }
    var x = new RegExp(m.file).exec(src); if (!x) return null;
    var n = null, k;
    try { for (k in C.entries) { var e = C.entries[k], cid = String((e && e.clip) || "").split("/").pop().split(".")[0]; if (e && (e.id === x[1] || cid === x[1])) { n = +k; break; } } } catch (er) {}
    if (n == null) return null;
    var ch = (C.chips(n) || [])[0]; if (!ch || !ch.paid || ch.coming || (C.owns && C.owns(n, ch.v))) return null;
    var pv = String(ch.v).replace(/^v/, ""); if (pv === x[3]) return null;
    return ready({key: "clip:" + x[1] + ":" + x[3], versions: [{v: x[3]}, {v: pv}], price: m.price, unit: "length", cut: true, path: m.purchase_path || "/documentary/",
      buy: function () { try { C.buyLatest(n); } catch (e) { location.href = m.purchase_path || "/documentary/"; } },
      isOpen: function () { return d.contains(v) && !v.paused; }});
  }
  d.addEventListener("play", function (ev) {
    var v = ev.target; if (!M || !v || v.tagName !== "VIDEO" || v.__cvgOk) return;
    var item = clip(v); if (!item) return;
    if (ss(item.key) === "free") { v.__cvgOk = 1; bar(item); return; }
    try { v.pause(); } catch (e) {}
    var f = facade(item); f.classList.add("cvg-inslot"); v.parentNode.insertBefore(f, v); v.style.display = "none";
    item.open = function () { v.__cvgOk = 1; if (f.parentNode) f.parentNode.removeChild(f); v.style.display = ""; var p = v.play(); if (p && p.catch) p.catch(function () {}); };
  }, true);
  function start() { load().then(readerPage).catch(function () { M = null; }); }
  window.CedwynVersionGate = {version: VER, prices: function (versions, price) { return prices({versions: versions, price: price}); }};
  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", start); else start();
})();
