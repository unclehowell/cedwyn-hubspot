/*! ghf-lang.js — English / Cymraeg / Español switcher for the Great House Farm (Tŷ Mawr) sites.
 * Dependency-free. Translates interface text only (nav, headings, buttons, labels) from a static
 * per-site dictionary; long evidence and legal text stays in its original English, which is the
 * authoritative record. Choice is remembered (?lang=, localStorage, and a .bucklerfamily.estate cookie)
 * and sets <html lang>.  Source: bucklerfamily.estate/ghf-lang/  ·  v1.0.5 (27 Oct 2026: no translation notice; the menu opens downward)
 */
(function () {
  "use strict";
  if (window.GHFLang) return;
  var LANGS = ["en", "cy", "es"];
  var NAMES = { en: "English", cy: "Cymraeg", es: "Español" };
  var SHORT = { en: "EN", cy: "CY", es: "ES" };
  var UI = {
    label: { en: "Language", cy: "Iaith", es: "Idioma" },
    close: { cy: "Cau", es: "Cerrar", en: "Close" }
  };
  var me = document.currentScript || (function () {
    var s = document.getElementsByTagName("script");
    for (var i = s.length - 1; i >= 0; i--) if (/ghf-lang(\.min)?\.js/.test(s[i].src)) return s[i];
    return null;
  })();
  var base = me && me.src ? me.src.replace(/[^\/]*$/, "") : "/_cedwyn/ghf/";
  function siteKey() {
    if (me && me.getAttribute("data-site")) return me.getAttribute("data-site");
    var h = (document.documentElement.getAttribute("data-ghf-host") || location.hostname).replace(/^www\./, "");
    if (h === "bucklerfamily.estate" || /pages\.dev$/.test(h) && /bucklerfamilyfarm/.test(h)) return "estate";
    return h.split(".")[0];
  }
  var SITE = siteKey();
  var dict = {}, conf = {}, cur = "en", origLang = document.documentElement.getAttribute("lang") || "en";
  var orig = new WeakMap(), done = new WeakMap(), origAttr = new WeakMap(), origTitle = null;
  var SKIP = "script,style,noscript,textarea,code,pre,blockquote,[data-no-translate],[translate=no],.ghf-lang,.ghf-lang-note,[contenteditable=true]";
  var ATTRS = ["placeholder", "title", "aria-label"];

  function norm(s) { return s.replace(/\s+/g, " ").trim(); }
  var EDGE = /^([^\p{L}\p{N}]*)([\s\S]*?)([^\p{L}\p{N}.)?!]*)$/u;
  function look(text) {
    var n = norm(text);
    if (!n) return null;
    return seg(n) || pat(n) || comp(n);
  }
  var MON = {
    cy: ["Ionawr","Chwefror","Mawrth","Ebrill","Mai","Mehefin","Gorffennaf","Awst","Medi","Hydref","Tachwedd","Rhagfyr"],
    es: ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]
  };
  var MRE = /\b(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.? (\d{4})\b/g;
  var MK = "janfebmaraprmayjunjulaugsepoctnovdec";
  function dates(s) {
    return s.replace(MRE, function (_, d, m, y) {
      var i = MK.indexOf(m.slice(0, 3).toLowerCase()) / 3;
      return cur === "es" ? d + " de " + MON.es[i] + " de " + y : d + " " + MON.cy[i] + " " + y;
    });
  }
  function seg(s) {                      // one segment: dictionary, edge-stripped, or a date
    var hit = dict[s];
    if (hit && hit[cur]) return hit[cur];
    var m = EDGE.exec(s);
    if (m && m[2] && (m[1] || m[3])) { hit = dict[m[2]]; if (hit && hit[cur]) return m[1] + hit[cur] + m[3]; }
    if (/^\d{1,2} [A-Z][a-z]{2,8}\.? \d{4}$/.test(s)) { var d = dates(s); if (d !== s) return d; }
    return null;
  }
  function pat(n) {
    var P = conf.patterns || [];
    for (var i = 0; i < P.length; i++) {
      var re = P[i]._re || (P[i]._re = new RegExp(P[i].re, "u"));
      var m = re.exec(n);
      if (!m || !P[i][cur]) continue;
      return P[i][cur].replace(/\$(\d)/g, function (_, k) {
        var g = m[+k] || "", t = seg(g) || dates(g);
        return t;
      });
    }
    return null;
  }
  function comp(n) {                     // "Name: subtitle", "A · B", "A — B": translate the parts we know
    if (n.length > 140) return null;
    var parts = n.split(/(: | · | — | – | \| |\s›\s)/);
    if (parts.length < 3) return null;
    var any = false, out = "";
    for (var i = 0; i < parts.length; i++) {
      if (i % 2) { out += parts[i]; continue; }
      var t = parts[i] ? (seg(parts[i]) || pat(parts[i])) : null;
      if (t != null) any = true;
      out += t != null ? t : parts[i];
    }
    return any ? out : null;
  }
  function wrap(src, val) {
    var lead = (src.match(/^\s*/) || [""])[0], trail = (src.match(/\s*$/) || [""])[0];
    return lead + val + trail;
  }
  function skipEl(el) { return !el || (el.closest && el.closest(SKIP)); }

  function doText(node) {
    var p = node.parentElement;
    if (skipEl(p)) return;
    if (p.namespaceURI === "http://www.w3.org/2000/svg") {     // multi-line SVG signs stay whole (no half-translated labels)
      var te = p.closest("text"); if (te && te.querySelectorAll("tspan").length > 1) return;
    }
    var v = node.nodeValue;
    if (done.get(node) === v) return;            // our own write
    orig.set(node, v);                             // new English from the page
    if (cur === "en") return;
    var t = look(v);
    if (t != null) { var w = wrap(v, t); node.nodeValue = w; done.set(node, w); }
  }
  function doEl(el) {
    if (skipEl(el)) return;
    for (var i = 0; i < ATTRS.length; i++) {
      var a = ATTRS[i];
      if (!el.hasAttribute(a)) continue;
      var store = origAttr.get(el) || {};
      var v = el.getAttribute(a);
      if (store["_" + a] !== v) store[a] = v;       // not our own write
      origAttr.set(el, store);
      var src = store[a];
      var t = cur === "en" ? src : look(src);
      if (t != null && t !== v) { el.setAttribute(a, t); store["_" + a] = t; }
    }
  }
  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { doText(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1) { if (skipEl(root)) return; doEl(root); }
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT, {
      acceptNode: function (n) {
        if (n.nodeType === 1) return n.matches(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n, els = root.nodeType === 1 ? root.querySelectorAll("[placeholder],[title],[aria-label]") : document.querySelectorAll("[placeholder],[title],[aria-label]");
    while ((n = tw.nextNode())) doText(n);
    for (var i = 0; i < els.length; i++) doEl(els[i]);
  }
  function restore() {
    var tw = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null), n;
    while ((n = tw.nextNode())) {
      if (done.has(n) && done.get(n) === n.nodeValue && orig.has(n)) { n.nodeValue = orig.get(n); done.delete(n); }
    }
    var els = document.querySelectorAll("[placeholder],[title],[aria-label]");
    for (var i = 0; i < els.length; i++) {
      var s = origAttr.get(els[i]); if (!s) continue;
      for (var j = 0; j < ATTRS.length; j++) {
        var a = ATTRS[j];
        if (s[a] != null && s["_" + a] === els[i].getAttribute(a)) { els[i].setAttribute(a, s[a]); delete s["_" + a]; }
      }
    }
  }
  function doTitle() {
    if (origTitle === null) origTitle = document.title;
    if (cur === "en") { document.title = origTitle; return; }
    var parts = origTitle.split(/(\s[·|—–-]\s)/), out = "";
    for (var i = 0; i < parts.length; i++) { var t = i % 2 ? null : look(parts[i]); out += t != null ? t : parts[i]; }
    document.title = out;
  }

  var mo = null, queue = [], rafId = 0;
  function flush() {
    rafId = 0;
    var q = queue; queue = [];
    for (var i = 0; i < q.length; i++) walk(q[i]);
  }
  function observe() {
    if (mo || !window.MutationObserver) return;
    mo = new MutationObserver(function (list) {
      for (var i = 0; i < list.length; i++) {
        var m = list[i];
        if (m.type === "characterData") queue.push(m.target);
        else for (var j = 0; j < m.addedNodes.length; j++) queue.push(m.addedNodes[j]);
      }
      if (!rafId) rafId = (window.requestAnimationFrame || setTimeout)(flush);
    });
    mo.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  // ---------- persistence ----------
  function readCookie() { var m = document.cookie.match(/(?:^|;\s*)ghf_lang=(en|cy|es)/); return m ? m[1] : null; }
  function save(l) {
    try { localStorage.setItem("ghf_lang", l); } catch (e) {}
    var dom = /(^|\.)bucklerfamily\.estate$/.test(location.hostname) ? "; domain=.bucklerfamily.estate" : "";
    document.cookie = "ghf_lang=" + l + "; path=/; max-age=31536000; SameSite=Lax" + dom + (location.protocol === "https:" ? "; Secure" : "");
  }
  function initial() {
    var q = null;
    try { q = new URLSearchParams(location.search).get("lang"); } catch (e) {}
    if (q && LANGS.indexOf(q.toLowerCase()) >= 0) { q = q.toLowerCase(); save(q); return q; }
    var c = readCookie(); if (c) return c;
    try { var s = localStorage.getItem("ghf_lang"); if (LANGS.indexOf(s) >= 0) return s; } catch (e) {}
    // Cedwyn sections (25 Oct 2026): with no saved choice, the section's language (Wales cy, Argentina es) - Sion's Tab agent
    var dl = document.documentElement.getAttribute("data-ghf-lang-default"); if (LANGS.indexOf(dl) >= 0) return dl;
    return "en";
  }

  // ---------- UI ----------
  var CSS = ".ghf-lang{position:relative;display:inline-flex;align-items:center;font:500 13px/1.2 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;z-index:2147482000;flex:0 0 auto;letter-spacing:0;text-transform:none}" +
    ".ghf-lang.ghf-fixed{position:fixed}" +
    ".ghf-lang-btn{display:inline-flex;align-items:center;gap:5px;min-height:32px;padding:5px 10px;border-radius:999px;border:1px solid var(--ghf-lang-bd,rgba(255,255,255,.35));background:var(--ghf-lang-bg,rgba(12,14,18,.82));color:var(--ghf-lang-fg,#fff);font:inherit;cursor:pointer;-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);white-space:nowrap;box-shadow:0 1px 6px rgba(0,0,0,.18)}" +
    ".ghf-lang-btn:hover{filter:brightness(1.12)}.ghf-lang-btn:focus-visible,.ghf-lang-opt:focus-visible{outline:2px solid #f5c542;outline-offset:2px}" +
    ".ghf-lang-btn svg{width:15px;height:15px;flex:0 0 auto}.ghf-lang-caret{font-size:10px;opacity:.8}" +
    ".ghf-lang-menu{position:absolute;top:calc(100% + 6px);right:0;min-width:150px;margin:0;padding:5px;list-style:none;z-index:2147483000;border-radius:12px;background:var(--ghf-lang-menu,#111418);color:#fff;border:1px solid rgba(255,255,255,.18);box-shadow:0 10px 30px rgba(0,0,0,.35);display:none}" +
    ".ghf-lang.ghf-left .ghf-lang-menu{right:auto;left:0}.ghf-v2-loc.ghf-lang-row-open{overflow:visible!important}" +   /* 27 Oct: the menu always opens downward, in front of the header */
    ".ghf-lang.ghf-open .ghf-lang-menu{display:block}" +
    ".ghf-lang-opt{display:flex;justify-content:space-between;align-items:center;gap:12px;width:100%;padding:9px 10px;border:0;border-radius:8px;background:transparent;color:inherit;font:inherit;font-size:14px;text-align:left;cursor:pointer}" +
    ".ghf-lang-opt:hover,.ghf-lang-opt[aria-selected=true]{background:rgba(255,255,255,.1)}.ghf-lang-opt small{opacity:.6;font-size:11px}" +
    ".ghf-lang-opt[aria-selected=true]::after{content:'\\2713';color:#f5c542}" +
    "@media print{.ghf-lang{display:none!important}}";
  var GLOBE = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9.2"/><path d="M2.8 12h18.4M12 2.8c2.6 2.6 3.9 5.6 3.9 9.2s-1.3 6.6-3.9 9.2c-2.6-2.6-3.9-5.6-3.9-9.2S9.4 5.4 12 2.8z"/></svg>';
  var root, btn, menu;
  function build() {
    var st = document.createElement("style"); st.id = "ghf-lang-css"; st.textContent = CSS + (conf.css || "");
    document.head.appendChild(st);
    root = document.createElement("div");
    root.className = "ghf-lang"; root.setAttribute("data-no-translate", ""); root.setAttribute("translate", "no");
    root.innerHTML = '<button type="button" class="ghf-lang-btn" aria-haspopup="listbox" aria-expanded="false">' + GLOBE +
      '<span class="ghf-lang-cur"></span><span class="ghf-lang-caret" aria-hidden="true">&#9662;</span></button><ul class="ghf-lang-menu" role="listbox" tabindex="-1"></ul>';
    btn = root.firstChild; menu = root.lastChild;
    LANGS.forEach(function (l) {
      var li = document.createElement("li"); li.setAttribute("role", "presentation");
      var b = document.createElement("button"); b.type = "button"; b.className = "ghf-lang-opt"; b.setAttribute("role", "option");
      b.setAttribute("data-lang", l); b.setAttribute("lang", l);
      b.innerHTML = "<span>" + NAMES[l] + "</span><small>" + SHORT[l] + "</small>";
      b.addEventListener("click", function () { set(l); close(); btn.focus(); });
      li.appendChild(b); menu.appendChild(li);
    });
    btn.addEventListener("click", function (e) { e.stopPropagation(); root.classList.contains("ghf-open") ? close() : open(true); });
    root.addEventListener("keydown", function (e) {
      var opts = [].slice.call(menu.querySelectorAll(".ghf-lang-opt")), i = opts.indexOf(document.activeElement);
      if (e.key === "Escape") { close(); btn.focus(); }
      else if (e.key === "ArrowDown") { e.preventDefault(); if (!root.classList.contains("ghf-open")) open(true); else opts[(i + 1) % opts.length].focus(); }
      else if (e.key === "ArrowUp") { e.preventDefault(); if (i >= 0) opts[(i + opts.length - 1) % opts.length].focus(); }
    });
    document.addEventListener("click", function (e) { if (!root.contains(e.target)) close(); });
    place();
  }
  function place() {
    var pos = (me && me.getAttribute("data-position")) || conf.position || "auto";
    var sel = (me && me.getAttribute("data-mount")) || conf.mount;
    var host = null;
    if (conf.fixedBelow && window.innerWidth < conf.fixedBelow) pos = "fixed";
    if (pos !== "fixed" && sel) { var c = sel.split("|"); for (var i = 0; i < c.length && !host; i++) host = document.querySelector(c[i]); }
    if (host) {
      if (conf.mountMode === "prepend") host.insertBefore(root, host.firstChild);
      else if (conf.mountMode === "after") host.parentNode.insertBefore(root, host.nextSibling);
      else if (conf.mountMode === "before") host.parentNode.insertBefore(root, host);
      else host.appendChild(root);
      if (conf.inlineStyle) root.setAttribute("style", conf.inlineStyle);
    } else {
      var f = conf.fixed || { top: "10px", right: "10px" };
      root.classList.add("ghf-fixed");
      for (var k in f) root.style[k] = f[k];
      if (f.left) root.classList.add("ghf-left");
      document.body.appendChild(root);
    }
    if (conf.menuLeft) root.classList.add("ghf-left");
  }
  function open(focus) {
    root.classList.add("ghf-open"); btn.setAttribute("aria-expanded", "true");
    var row = root.closest && root.closest(".ghf-v2-loc"); if (row) row.classList.add("ghf-lang-row-open");
    if (root.classList.contains("ghf-fixed")) { var over = menu.getBoundingClientRect().bottom - ((window.innerHeight || 600) - 8); if (over > 0) root.style.transform = "translateY(" + (-Math.ceil(over)) + "px)"; }
    var r = root.getBoundingClientRect();
    if (r.left < 170 && !root.classList.contains("ghf-left") && r.right < 170) root.classList.add("ghf-left");
    if (focus) { var s = menu.querySelector("[aria-selected=true]"); if (s) s.focus(); }
  }
  function close() {
    if (!root) return; root.classList.remove("ghf-open"); btn.setAttribute("aria-expanded", "false"); root.style.transform = "";
    var row = root.closest && root.closest(".ghf-v2-loc"); if (row) row.classList.remove("ghf-lang-row-open");
  }
  function paint() {
    if (!root) return;
    root.querySelector(".ghf-lang-cur").textContent = SHORT[cur];
    btn.setAttribute("aria-label", UI.label[cur] + ": " + NAMES[cur] + " (Language / Iaith / Idioma)");
    btn.title = UI.label[cur];
    [].forEach.call(menu.querySelectorAll(".ghf-lang-opt"), function (b) { b.setAttribute("aria-selected", b.getAttribute("data-lang") === cur ? "true" : "false"); });
  }
  function note() { // 27 Oct 2026: the translation notice is gone for good; clear any copy an older script left on the page
    var old = document.querySelectorAll(".ghf-lang-note"); for (var i = 0; i < old.length; i++) old[i].parentNode.removeChild(old[i]);
  }
  function set(l, quiet) {
    if (LANGS.indexOf(l) < 0) l = "en";
    var prev = cur; cur = l;
    if (!quiet) save(l);
    document.documentElement.setAttribute("lang", l === "en" ? origLang : l);
    if (prev !== "en") restore();
    if (l !== "en") { walk(document.body); observe(); }
    doTitle(); paint(); note();
    try { document.dispatchEvent(new CustomEvent("ghf-lang-change", { detail: { lang: l } })); } catch (e) {}
  }

  function start(data) {
    conf = data || {};
    dict = conf.strings || {};
    if (!document.body) return;
    build();
    var l = initial();
    if (l !== "en") set(l, true); else { paint(); walk(document.body); }
    observe();
  }
  function load() {
    var url = (me && me.getAttribute("data-dict")) || (base + "sites/" + SITE + ".json");
    var fallback = base + "sites/estate.json";
    var done1 = false;
    function go(d) { if (done1) return; done1 = true; start(d); }
    function get(u, last) {
      try {
        var x = new XMLHttpRequest();
        x.open("GET", u, true);
        x.onload = function () {
          var d = null; try { d = JSON.parse(x.responseText); } catch (e) {}
          if ((x.status >= 400 || !d) && !last && u !== fallback) return get(fallback, true);
          go(x.status < 400 ? d : null);
        };
        x.onerror = function () { if (!last && u !== fallback) get(fallback, true); else go(null); };
        x.timeout = 8000; x.ontimeout = function () { go(null); };
        x.send();
      } catch (e) { go(null); }
    }
    get(url, false);
  }
  window.GHFLang = {
    set: function (l) { set(l); }, get: function () { return cur; },
    open: function () { open(false); }, close: close, site: SITE, version: "1.0.5"
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", load); else load();
  // Base camp: every GHF site gets a "Back to base camp" link (basecamp.js, same folder; 20 Oct 2026, Sion's Tab agent).
  try {
    if (!window.GHFBasecamp && !document.querySelector('script[src*="basecamp.js"]')) {
      var bc = document.createElement("script");
      bc.src = base + "basecamp.js?v=2.1.19"; bc.async = true;
      (document.head || document.documentElement).appendChild(bc);
    }
  } catch (e) {}
})();
