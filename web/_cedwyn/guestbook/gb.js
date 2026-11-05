/*! gb.js - the page version table (Agent guest book) in the shared footer of every Cedwyn page (v1.1.1, 29 Oct 2026).
 * v1.1.1: the page versions and the agent footer (#ghf-agent-footer: change log, agent rules, THE TRIGGER EVENT) sit in ONE
 * native <details> "Page versions & agent info", closed on load. Nothing is hidden with display:none or removed: the agent text
 * stays in the HTML and the DOM, so crawlers and LLM fetchers read it; a tap opens it. An older footer without the <details>
 * is wrapped in place (its nodes are moved, never dropped). Pages with no agent footer keep the guest book alone, collapsed.
 * v1.1.0: shows THIS page's 3 most recent versions, open, from /api/v (the commits to the file the page is built from;
 * semver 1.change.fix per page), and "See all" opens that file's full commit history on GitHub. If /api/v cannot answer,
 * it falls back to the site-wide /guestbook/guestbook.json rows and the repo history.  Also carries the
 * first-party analytics beacon (bottom of this file; no cookies). Labels in en / cy / es. v1.0.1: moves #cedwyn-guestbook into the shared
 * legal footer (or the app footer line on full-screen app pages). - Sion's Tab agent */
(function () {
  "use strict";
  if (window.__cedwynGB) return; window.__cedwynGB = 1;
  var DATA = location.origin + "/guestbook/guestbook.json", PAGE = location.origin + "/api/v?p=" + encodeURIComponent(location.pathname), data = null, loading = false;   // absolute: the theme runtime prefixes root paths
  var HIST = "https://github.com/unclehowell/cedwyn/commits/main";
  var L = {
    en: { title: "Page versions", meta: "Page versions & agent info", v: "Version", d: "Date", n: "Change", w: "Who", all: "See all", log: "Whole-site log",
          rule: "versions 1.change.fix, from this page\u2019s commit history",
          intro: "Every change to this site, newest first. Each version opens the change on GitHub." },
    cy: { title: "Fersiynau\u2019r dudalen", meta: "Fersiynau\u2019r dudalen a gwybodaeth i asiantau", v: "Fersiwn", d: "Dyddiad", n: "Newid", w: "Pwy", all: "Gweld y cyfan", log: "Cofnod y wefan gyfan",
          rule: "fersiynau 1.newid.trwsiad, o hanes newidiadau\u2019r dudalen hon",
          intro: "Pob newid i\u2019r wefan hon, y diweddaraf yn gyntaf. Mae pob fersiwn yn agor y newid ar GitHub." },
    es: { title: "Versiones de la p\u00e1gina", meta: "Versiones de la p\u00e1gina e informaci\u00f3n para agentes", v: "Versi\u00f3n", d: "Fecha", n: "Cambio", w: "Qui\u00e9n", all: "Ver todo", log: "Registro de todo el sitio",
          rule: "versiones 1.cambio.correcci\u00f3n, del historial de cambios de esta p\u00e1gina",
          intro: "Todos los cambios de este sitio, del m\u00e1s reciente al m\u00e1s antiguo. Cada versi\u00f3n abre el cambio en GitHub." }
  };
  function lang() {
    var l = (document.documentElement.getAttribute("lang") || "").slice(0, 2).toLowerCase();
    if (!L[l]) { try { l = (localStorage.getItem("ghf_lang") || "en").slice(0, 2); } catch (e) { l = "en"; } }
    return L[l] ? l : "en";
  }
  function label() {
    var D = L[lang()], els = document.querySelectorAll("[data-gb-l]");
    for (var i = 0; i < els.length; i++) { var k = els[i].getAttribute("data-gb-l"); if (D[k]) els[i].textContent = D[k]; }
  }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function link(repo, sha) { return ["https:", "", "github.com", repo, "commit", sha].join("/"); }   // opens GitHub directly (allowed out, 26 Oct 2026)
  function sec() { return document.getElementById("cedwyn-guestbook"); }
  // v1.0.1: a full-screen app page (body does not scroll, e.g. the chessboard) has no shared legal footer: the guest book joins
  // the app's own footer line (or, with none, sits small at the bottom-left) and opens as a panel above it
  function appPage() { try { return /hidden|clip/.test(getComputedStyle(document.body).overflowY + " " + getComputedStyle(document.documentElement).overflowY); } catch (e) { return false; } }
  function appLine() {
    var fs = document.querySelectorAll("footer"), best = null;
    for (var i = 0; i < fs.length && !best; i++) {
      var r = fs[i].getBoundingClientRect(); if (!r.height || r.bottom > innerHeight + 2 || r.top < 0) continue;
      var w = document.createTreeWalker(fs[i], NodeFilter.SHOW_TEXT), t;
      while ((t = w.nextNode())) if (t.nodeValue.indexOf("\u00a9") >= 0 && !(t.parentNode.closest && t.parentNode.closest("#cedwyn-guestbook"))) { best = t.parentNode; break; }
    }
    return best ? (best.parentNode && best.parentNode.nodeType === 1 && best.parentNode.tagName !== "FOOTER" ? best.parentNode : best) : null;
  }
  // v1.1.1: ONE collapsed disclosure at the foot of the page for the page versions + the agent footer (closed on load)
  var MCSS = "#ghf-agent-footer>details.gaf-d{display:block}#ghf-agent-footer>details.gaf-d>summary{display:list-item!important;cursor:pointer;font-size:12px!important;line-height:1.5!important;padding:8px 0!important;min-height:32px;list-style-position:inside}#ghf-agent-footer>details.gaf-d>summary>span{font-size:12px!important;line-height:1.5!important}" +
    "#ghf-agent-footer>details.gaf-d[open]>summary{margin-bottom:4px!important}#ghf-agent-footer #cedwyn-guestbook{display:block!important;margin:0 0 8px!important;padding:0!important;max-width:none!important}" +
    "#ghf-agent-footer #cedwyn-guestbook,#ghf-agent-footer #cedwyn-guestbook *{font-size:11px!important;line-height:1.4!important}#ghf-agent-footer #cedwyn-guestbook summary{display:list-item!important;cursor:pointer}" +
    "#ghf-agent-footer #cedwyn-guestbook table{display:table!important;width:100%!important}#ghf-agent-footer #cedwyn-guestbook thead{display:table-header-group!important}" +
    "#ghf-agent-footer #cedwyn-guestbook tbody{display:table-row-group!important}#ghf-agent-footer #cedwyn-guestbook tr{display:table-row!important}" +
    "#ghf-agent-footer #cedwyn-guestbook th::before,#ghf-agent-footer #cedwyn-guestbook td::before{content:none!important}";
  function box() {
    var f = document.getElementById("ghf-agent-footer"); if (!f) return null;
    if (!document.getElementById("cedwyn-gb-meta-css")) { var st = document.createElement("style"); st.id = "cedwyn-gb-meta-css"; st.textContent = MCSS; (document.head || document.documentElement).appendChild(st); }
    var d = f.querySelector(":scope>details.gaf-d");
    if (!d) {   // an older footer (no <details>): wrap its content in place, moving every node (nothing removed or hidden)
      d = document.createElement("details"); d.className = "gaf-d";
      d.innerHTML = '<summary><span data-gb-l="meta">Page versions &amp; agent info</span> <span class="gb-mv"></span></summary>';
      var kids = [].slice.call(f.childNodes);
      for (var i = 0; i < kids.length; i++) if (!(kids[i].nodeType === 1 && kids[i].tagName === "STYLE")) d.appendChild(kids[i]);
      f.appendChild(d); label();
    }
    if (!d.hasAttribute("data-gb-wired")) { d.setAttribute("data-gb-wired", "1"); d.addEventListener("toggle", function () { if (d.open) { load(); fill(); } }); }
    return d;
  }
  function meta() { var m = box(); return m && (document.querySelector("[data-ghf-legal-foot]") || !document.body || !appPage()) ? m : null; }   // a full-screen app page keeps its docked guest book
  function target() { return meta() || document.querySelector("[data-ghf-legal-foot]"); }
  function place() {
    var all = document.querySelectorAll("#cedwyn-guestbook");
    for (var i = 1; i < all.length; i++) all[i].parentNode.removeChild(all[i]);
    var s = sec(); if (!s) return;
    var m = meta();
    if (m) {   // first thing inside the disclosure, right under its summary; its own table shows when the disclosure opens
      s.classList.remove("gb-dock", "gb-fixed"); var sm = m.querySelector(":scope>summary");
      if (s.parentNode !== m || s.previousElementSibling !== sm) m.insertBefore(s, sm ? sm.nextSibling : m.firstChild);
      var gd = s.querySelector("details"); if (gd && !gd.hasAttribute("data-gb-opened")) { gd.setAttribute("data-gb-opened", "1"); gd.open = true; }
      return;
    }
    var f = document.querySelector("[data-ghf-legal-foot]");
    if (f) { s.classList.remove("gb-dock", "gb-fixed"); if (s.parentNode !== f) f.appendChild(s); return; }
    if (!document.body || !appPage()) return;
    var l = appLine();
    if (l) { s.classList.add("gb-dock"); s.classList.remove("gb-fixed"); if (s.parentNode !== l) l.appendChild(s); }
    else { s.classList.add("gb-dock", "gb-fixed"); if (s.parentNode !== document.body) document.body.appendChild(s); }
    var p = s.querySelector("details > p"), w = s.querySelector(".gbw"); if (p && w) w.appendChild(p);
    if (!document.getElementById("cedwyn-gb-dock-css")) { var st = document.createElement("style"); st.id = "cedwyn-gb-dock-css";
      st.textContent = "#cedwyn-guestbook.gb-dock{display:inline!important;margin:0 0 0 6px!important;padding:0!important;max-width:none}" +
        "#cedwyn-guestbook.gb-dock details,#cedwyn-guestbook.gb-dock summary{display:inline!important}#cedwyn-guestbook.gb-dock .gb-r{display:none}" +
        "#cedwyn-guestbook.gb-fixed{position:fixed!important;left:8px;bottom:8px;z-index:2147482000;display:block!important;padding:2px 8px!important;border-radius:10px;background:Canvas!important;color:CanvasText!important;opacity:.9}" +
        "#cedwyn-guestbook.gb-dock details[open]>.gbw{position:fixed!important;left:8px;right:8px;bottom:44px;max-height:60vh;overflow:auto;z-index:2147483000;margin:0!important;padding:8px!important;" +
        "background:Canvas!important;color:CanvasText!important;border:1px solid rgba(128,128,128,.5);border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.35);text-align:left!important}";
      (document.head || document.documentElement).appendChild(st); }
  }
  // the page's own scripts may re-render <body> (e.g. a React app that hydrates the whole page): put the guest book back, as the agent footer does
  var TPL = null;
  function keep() {
    if (sec() || !TPL || !document.body) return;
    var n = TPL.cloneNode(true); document.body.appendChild(n); wire(n); absolutize(); place(); label(); openUp(); if (data) fill();
  }
  function wire(s) { var d = s && s.querySelector("details"); if (d) d.addEventListener("toggle", function () { if (d.open) { load(); fill(); } }); }
  function fill() {
    var s = sec(); if (!s || !data) return;
    var v = s.querySelector(".gb-v"); if (v) v.textContent = data.version ? "v" + data.version : "";
    var mv = document.querySelectorAll("#ghf-agent-footer .gb-mv"); for (var k = 0; k < mv.length; k++) mv[k].textContent = data.version ? "\u00b7 v" + data.version : "";
    if (data.history_url) HIST = data.history_url;
    absolutize();
    var tb = s.querySelector(".gb-rows"); if (!tb || tb.getAttribute("data-filled")) return;
    var rows = (data.rows || []).filter(function (r) { return r.kind !== "build"; }).slice(0, 3), h = "";
    rows.forEach(function (r) {
      h += '<tr><td>' + (r.sha ? '<a href="' + esc(link(data.repo || "unclehowell/cedwyn", r.sha)) + '" target="_blank" rel="noopener" title="' + esc(r.sha.slice(0, 7)) + '">' + esc(r.v) + "</a>" : esc(r.v)) + "</td><td>" +
        esc(r.date) + "</td><td>" + esc(r.note) + "</td><td>" + esc(r.who) + "</td></tr>";
    });
    tb.innerHTML = h; tb.setAttribute("data-filled", "1");
  }
  function load() {
    if (data || loading) return; loading = true;
    fetch(PAGE).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) { if (!d || !(d.rows || []).length) throw 0; data = d; fill(); })
      .catch(function () {   // fallback: the site-wide log (main), "See all" still opens GitHub
        fetch(DATA, { cache: "no-cache" }).then(function (r) { return r.json(); }).then(function (d) { data = d; fill(); }).catch(function () { loading = false; });
      });
  }
  function untrapAll() {   // the full guest book page's static links pass through /wayback/go/ (the build's outbound guard): open GitHub directly
    var as = document.querySelectorAll('#guestbook a[href^="/wayback/go/?u="]');
    for (var i = 0; i < as.length; i++) { var u; try { u = decodeURIComponent(as[i].getAttribute("href").slice(15)); } catch (e) { continue; }
      if (/^https:\/\/github\.com\/unclehowell\/cedwyn\/commit\/[0-9a-f]{7,40}$/i.test(u)) { as[i].setAttribute("href", u); as[i].setAttribute("target", "_blank"); as[i].setAttribute("rel", "noopener"); } }
  }
  function absolutize() {
    var a = document.querySelectorAll('#cedwyn-guestbook a[data-gb-l="all"]');
    for (var i = 0; i < a.length; i++) { if (a[i].getAttribute("href") !== HIST) a[i].setAttribute("href", HIST); a[i].setAttribute("target", "_blank"); a[i].setAttribute("rel", "noopener");
      if (!a[i].parentNode.querySelector('a[data-gb-l="log"]')) { var l = document.createElement("a"); l.setAttribute("data-gb-l", "log"); l.textContent = L[lang()].log; a[i].parentNode.appendChild(document.createTextNode(" \u00b7 ")); a[i].parentNode.appendChild(l); } }
    var g = document.querySelectorAll('#cedwyn-guestbook a[data-gb-l="log"]'), u = location.origin + "/guestbook/"; for (var j = 0; j < g.length; j++) if (g[j].getAttribute("href") !== u) g[j].setAttribute("href", u);
  }
  // v1.1.1: closed on load (owner, 28 Oct 2026). Inside the agent-info disclosure the guest book's own table is pre-opened (place()),
  // so one tap shows the 3 newest versions and the agent text; on a page with no agent footer the guest book stays collapsed.
  function openUp() { }
  // a theme runtime may prefix root links or guard outbound ones: the site log always opens at the root, "See all" opens GitHub
  document.addEventListener("click", function (e) { var a = e.target && e.target.closest && e.target.closest('#cedwyn-guestbook a[data-gb-l="all"],#cedwyn-guestbook a[data-gb-l="log"]'); if (!a) return; absolutize(); if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return; e.preventDefault(); e.stopImmediatePropagation();
    if (a.getAttribute("data-gb-l") === "log") location.href = location.origin + "/guestbook/"; else window.open(HIST, "_blank", "noopener"); }, true);
  function init() {
    if (!TPL && sec()) TPL = sec().cloneNode(true);
    absolutize(); place(); label(); untrapAll(); wire(sec()); openUp();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  addEventListener("load", function () { keep(); absolutize(); place(); label(); openUp(); setTimeout(load, 300); });
  [300, 600, 1300, 2600, 6100, 12100].forEach(function (t) { setTimeout(function () { keep(); place(); absolutize(); }, t); });
  if (window.MutationObserver) {
    var mo = new MutationObserver(function () { if (!sec()) { keep(); return; } var f = target(); if (f && sec().parentNode !== f) place(); });
    mo.observe(document.documentElement, { childList: true, subtree: true }); setTimeout(function () { mo.disconnect(); }, 20000);
  }
  document.addEventListener("ghf-lang-change", label); window.addEventListener("ghf-lang-change", label);
  new MutationObserver(label).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
})();
/* Cedwyn's first-party analytics beacon (27 Oct 2026): one POST to /api/a per page view and per checkout / academy click;
 * no cookies, no storage; the server keeps path, referrer host, country, browser class and a daily-salted hash, never the IP. */
(function(){if(window.__cedwynA)return;window.__cedwynA=1;var O=location.origin+"/api/a";function s(e,t){try{var d=JSON.stringify({p:location.pathname,r:document.referrer,e:e,t:t||null,l:(document.documentElement.getAttribute("lang")||"").slice(0,2),w:window.innerWidth,d:navigator.webdriver?1:0});if(navigator.sendBeacon&&navigator.sendBeacon(O,new Blob([d],{type:"text/plain"})))return;fetch(O,{method:"POST",body:d,keepalive:true}).catch(function(){});}catch(x){}}window.cedwynTrack=s;function pv(){s("pv");}if(document.readyState==="complete")pv();else addEventListener("load",pv);document.addEventListener("click",function(ev){var a=ev.target&&ev.target.closest&&ev.target.closest("a[href]");if(!a)return;var h=a.href,u=h,m=h.match(/[?&]u=([^&]+)/);if(m){try{u=decodeURIComponent(m[1]);}catch(x){}}if(/^https:\/\/(buy|checkout)\.stripe\.com\/|gumroad\.com\//.test(u))s("checkout",u.slice(0,200));else{try{var q=new URL(h,location.href);if(q.origin===location.origin&&/^\/learn\/?$/.test(q.pathname))s("academy",location.pathname);}catch(x){}}},true);})();
