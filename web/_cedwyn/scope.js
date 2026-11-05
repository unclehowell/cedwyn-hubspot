/*! scope.js — Cedwyn's three scopes: Wales, Argentina (Patagonia) and Online · v1.0.0 (1 Nov 2026)
 * One shared helper for every webapp, the way ghf_lang serves the language. Spec: docs/SCOPES.md.
 * WHICH SCOPE: the address decides, as it always has: /wales/... = wales, /argentina/... = argentina, anything else = online.
 *   ?scope=wales|argentina|online on any page switches to the same page in that scope. The visitor's last explicit choice
 *   is kept like the language: localStorage + cookie "ghf_loc" (stored words wales | patagonia | cyberspace, unchanged so
 *   older pages keep reading it). ghf-boot.js sets <html data-cedwyn-scope> before the first paint.
 * WHAT SHOWS: any element may carry data-scope="wales|argentina|online|all" (several words allowed, space-separated).
 *   Untagged = all. An element whose words do not include the current scope (or "all") is hidden, and a short neutral
 *   line takes its place, linking to the same page in the scope it belongs to (or to data-scope-href, an internal path).
 * WITHOUT EDITING A WEBAPP: /_cedwyn/scope-map.json tags whole areas ("home") and blocks (CSS selector, optional text
 *   match) per area, so a mirrored or generated page is tagged from one file.
 * API: window.CedwynScope = { get(), stored(), set(s), href(s, path), label(s, lang), apply() }. */
(function () {
  if (window.CedwynScope) return;
  var d = document, de = d.documentElement, V = "1.0.0";
  var SC = ["wales", "argentina", "online"];
  var ALIAS = { wales: "wales", cymru: "wales", argentina: "argentina", patagonia: "argentina", online: "online", cyberspace: "online", "ar-lein": "online" };
  var STORE = { wales: "wales", argentina: "patagonia", online: "cyberspace" };   // ghf_loc words (basecamp.js reads these)
  var T = {
    en: { wales: "Wales", argentina: "Argentina", online: "Online",
          to_wales: ["Visiting in person?", "See Wales"], to_argentina: ["The planned replica:", "see Argentina"], to_online: ["Games, library and records:", "see Online"],
          area_wales: "This area is about visiting in Wales.", area_argentina: "This area is about the planned replica in Patagonia.", area_online: "This area is part of the online estate.", go: ["See Wales", "See Argentina", "See Online"] },
    cy: { wales: "Cymru", argentina: "Yr Ariannin", online: "Ar-lein",
          to_wales: ["Ymweld yn bersonol?", "Gweler Cymru"], to_argentina: ["Y replica arfaethedig:", "gweler yr Ariannin"], to_online: ["Gemau, llyfrgell a chofnodion:", "gweler Ar-lein"],
          area_wales: "Mae’r adran hon am ymweld yng Nghymru.", area_argentina: "Mae’r adran hon am y replica arfaethedig ym Mhatagonia.", area_online: "Mae’r adran hon yn rhan o’r ystâd ar-lein.", go: ["Gweler Cymru", "Gweler yr Ariannin", "Gweler Ar-lein"] },
    es: { wales: "Gales", argentina: "Argentina", online: "En línea",
          to_wales: ["¿Visita en persona?", "Vea Gales"], to_argentina: ["La réplica planificada:", "vea Argentina"], to_online: ["Juegos, biblioteca y registros:", "vea En línea"],
          area_wales: "Esta sección trata de la visita en Gales.", area_argentina: "Esta sección trata de la réplica planificada en la Patagonia.", area_online: "Esta sección forma parte de la finca en línea.", go: ["Vea Gales", "Vea Argentina", "Vea En línea"] }
  };
  function norm(v) { v = String(v || "").toLowerCase(); return ALIAS[v] || null; }
  function cookie(n) { var m = new RegExp("(?:^|;\\s*)" + n + "=([a-z-]+)").exec(d.cookie || ""); return m ? m[1] : null; }
  function lang() {
    var l = window.__cedwynLang || cookie("ghf_lang"); if (!l) { try { l = localStorage.getItem("ghf_lang"); } catch (e) {} }
    if (!/^(en|cy|es)$/.test(l || "")) l = de.getAttribute("data-ghf-lang-default") || (de.getAttribute("lang") || "en").slice(0, 2);
    return T[l] ? l : "en";
  }
  function split(p) {   // -> [scope from the address, the same path with no section prefix]
    p = p || location.pathname || "/";
    var m = /^\/(wales|argentina)(\/.*)?$/.exec(p);
    if (m) return [m[1], m[2] || "/"];
    return [null, p];
  }
  function fromAddress() {
    var s = norm(de.getAttribute("data-cedwyn-sec")); if (s === "wales" || s === "argentina") return s;
    return split()[0] || "online";
  }
  function get() { return norm(de.getAttribute("data-cedwyn-scope")) || fromAddress(); }
  function stored() { var v = null; try { v = localStorage.getItem("ghf_loc"); } catch (e) {} return norm(v || cookie("ghf_loc")); }
  function set(s) {
    s = norm(s); if (!s) return;
    try { localStorage.setItem("ghf_loc", STORE[s]); } catch (e) {}
    try { d.cookie = "ghf_loc=" + STORE[s] + "; path=/; max-age=31536000; SameSite=Lax" + (location.protocol === "https:" ? "; Secure" : "") + (/(^|\.)bucklerfamily\.estate$/.test(location.hostname) ? "; domain=.bucklerfamily.estate" : ""); } catch (e) {}
  }
  function href(s, path) {
    s = norm(s) || "online";
    var base = split(path || ((window.__cedwynLP || location.pathname) + "")); var p = base[1];
    if (/^\/(wales|argentina)\//.test(p)) p = split(p)[1];
    return (s === "online" ? "" : "/" + s) + p;
  }
  function label(s, l) { return (T[l || lang()] || T.en)[norm(s) || "online"]; }
  function words(el) { var w = (el.getAttribute("data-scope") || "").toLowerCase().split(/[\s,|]+/), o = [], i, x; for (i = 0; i < w.length; i++) { x = w[i] === "all" ? "all" : norm(w[i]); if (x && o.indexOf(x) < 0) o.push(x); } return o; }
  function shows(el, s) { var w = words(el); return !w.length || w.indexOf("all") >= 0 || w.indexOf(s) >= 0; }
  function css() {
    if (d.getElementById("cedwyn-scope-css")) return;
    var st = d.createElement("style"); st.id = "cedwyn-scope-css";
    st.textContent = SC.map(function (s) { return "html[data-cedwyn-scope=" + s + "] [data-scope]:not([data-scope~=" + s + "]):not([data-scope~=all]):not(.cs-stub)"; }).join(",") + "{display:none!important}" +
      ".cs-stub{display:block;margin:10px 0;padding:8px 12px;border-left:3px solid var(--ghf-accent,#c9a227);background:rgba(127,127,127,.12);color:inherit;font:500 14px/1.45 Barlow,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;max-width:100%;box-sizing:border-box;overflow-wrap:anywhere;text-align:left}" +
      ".cs-stub a{color:inherit;font-weight:700;text-decoration:underline;text-underline-offset:2px}li.cs-stub{display:list-item}tr.cs-stub{display:table-row;background:none;border:0}tr.cs-stub>td{padding:8px 12px;border-left:3px solid var(--ghf-accent,#c9a227);background:rgba(127,127,127,.12);font:500 14px/1.45 Barlow,system-ui,sans-serif}" +
      ".cs-area{margin:12px auto;max-width:860px;padding:14px 16px;font-size:16px}.cs-area b{display:block;margin-bottom:4px}";
    (d.head || de).appendChild(st);
  }
  function stubFor(el, target) {
    var l = lang(), t = T[l] || T.en, pair = t["to_" + target], tag = el.tagName, box, cell;
    var a = d.createElement("a"); a.href = el.getAttribute("data-scope-href") || href(target); a.textContent = pair[1];
    a.setAttribute("data-scope-go", target); a.addEventListener("click", function () { set(target); });
    if (tag === "TR") { box = d.createElement("tr"); cell = d.createElement("td"); cell.colSpan = 99; box.appendChild(cell); }
    else { box = d.createElement(tag === "LI" ? "li" : "p"); cell = box; }
    box.className = "cs-stub ghf-ui"; box.setAttribute("data-no-translate", ""); box.setAttribute("data-scope-stub", target);
    cell.appendChild(d.createTextNode(pair[0] + " ")); cell.appendChild(a);
    return box;
  }
  function target(el) { var w = words(el); return w.indexOf("wales") >= 0 ? "wales" : w.indexOf("argentina") >= 0 ? "argentina" : "online"; }
  function prevStub(el) { var p = el.previousElementSibling; while (p && !p.classList.contains("cs-stub") && !shows(p, get())) p = p.previousElementSibling; return p && p.classList.contains("cs-stub") ? p : null; }
  var MAP = null, mapTried = false;
  function areaOf(p) {   // the webapp this page belongs to, by its first path segment (after any section prefix)
    var a = MAP && MAP.areas, seg = (split(p)[1].split("/")[1] || ""), best = null, k, bp;
    if (!a) return null;
    for (k in a) { bp = (a[k].path || "/" + k + "/"); if (bp === "/" + seg + "/" || (a[k].aliases || []).indexOf("/" + seg + "/") >= 0) best = a[k]; }
    return best;
  }
  function tagFromMap() {
    if (!MAP) return;
    var p = window.__cedwynLP || location.pathname, ar = areaOf(p), rules = [], i, j, q, k, bare = split(p)[1];
    if (ar && ar.blocks) rules = rules.concat(ar.blocks);
    if (MAP.pages) for (k in MAP.pages) if (bare.indexOf(k) === 0) rules = rules.concat(MAP.pages[k].blocks || []);
    for (i = 0; i < rules.length; i++) {
      try { q = d.querySelectorAll(rules[i].sel); } catch (e) { continue; }
      for (j = 0; j < q.length; j++) {
        if (q[j].hasAttribute("data-scope") || q[j].closest(".cs-stub")) continue;
        if (rules[i].text && (q[j].textContent || "").indexOf(rules[i].text) < 0) continue;
        q[j].setAttribute("data-scope", rules[i].scope);
        if (rules[i].href && !q[j].hasAttribute("data-scope-href")) q[j].setAttribute("data-scope-href", rules[i].href);
      }
    }
    var home = null;
    if (MAP.pages) for (k in MAP.pages) if (bare.indexOf(k) === 0 && MAP.pages[k].home) home = MAP.pages[k];
    if (!home && ar && ar.home && ar.home !== "all") home = ar;
    areaCard(home);
  }
  function areaCard(ar) {   // a whole webapp that belongs to another scope: its content steps aside for one line pointing there
    var s = get(), h = ar && norm(ar.home), el, i, kids;
    if (!h || h === s || !d.body || d.querySelector(".cs-area")) return;
    var l = lang(), t = T[l] || T.en, box = d.createElement("div"), b = d.createElement("b"), p = d.createElement("p");
    box.className = "cs-stub cs-area ghf-ui"; box.setAttribute("data-no-translate", ""); box.setAttribute("data-scope-stub", h); box.setAttribute("role", "note");
    b.textContent = t["area_" + h]; box.appendChild(b);
    var a = d.createElement("a"); a.href = ar.href || href(h); a.textContent = t.go[SC.indexOf(h)]; a.setAttribute("data-scope-go", h); a.addEventListener("click", function () { set(h); });
    p.appendChild(a); p.style.margin = "0"; box.appendChild(p);
    kids = d.body.children;
    for (i = 0; i < kids.length; i++) {
      el = kids[i];
      if (/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE|LINK)$/.test(el.tagName) || /^ghf-/.test(el.id || "") || /(^|\s)(ghf-|cedwyn-rib|cs-stub)/.test(el.getAttribute("class") || "")) continue;
      el.setAttribute("data-scope", h);
    }
    d.body.insertBefore(box, d.body.firstChild);
  }
  function apply() {
    var s = get(); de.setAttribute("data-cedwyn-scope", s); css();
    tagFromMap();
    var q = d.querySelectorAll("[data-scope]:not(.cs-stub)"), i, el, tg, ps;
    for (i = 0; i < q.length; i++) {
      el = q[i];
      if (el.closest(".cs-area") || el.parentNode && el.parentNode.closest && el.parentNode.closest("[data-scope]:not(.cs-stub)") && !shows(el.parentNode.closest("[data-scope]:not(.cs-stub)"), s)) continue;
      if (el.__csStub) { if (shows(el, s)) { el.__csStub.remove(); el.__csStub = null; } continue; }
      if (shows(el, s) || el.hasAttribute("data-scope-nostub") || el.closest(".cs-area")) continue;
      tg = target(el); ps = prevStub(el);
      if (ps && ps.getAttribute("data-scope-stub") === tg) { el.__csStub = ps; continue; }
      if (d.body && d.querySelector(".cs-area") && el.parentNode === d.body) continue;   // the area card already speaks for it
      el.__csStub = stubFor(el, tg); el.parentNode.insertBefore(el.__csStub, el);
    }
  }
  function relabel() {   // the language changed: the stubs follow it
    var q = d.querySelectorAll(".cs-stub"), i; for (i = 0; i < q.length; i++) q[i].parentNode && q[i].parentNode.removeChild(q[i]);
    var e = d.querySelectorAll("[data-scope]"); for (i = 0; i < e.length; i++) e[i].__csStub = null;
    apply();
  }
  // ?scope= switches to the same page in the chosen scope (and remembers it)
  try { var qs = /[?&]scope=([a-zA-Z-]+)/.exec(location.search), want = qs && norm(qs[1]); if (want) { set(want); if (want !== fromAddress()) { location.replace(href(want) + location.search.replace(/([?&])scope=[^&]*&?/, "$1").replace(/[?&]$/, "") + location.hash); return; } } } catch (e) {}
  de.setAttribute("data-cedwyn-scope", fromAddress()); css();
  window.CedwynScope = { v: V, get: get, stored: stored, set: set, href: href, label: label, apply: apply, scopes: SC.slice() };
  var t0 = null; function soon() { if (t0) return; t0 = setTimeout(function () { t0 = null; apply(); }, 150); }
  function start() {
    apply();
    if (!mapTried) { mapTried = true; try { fetch("/_cedwyn/scope-map.json?v=" + V, { credentials: "same-origin" }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) { if (j && j.areas) { MAP = j; apply(); } }).catch(function () {}); } catch (e) {} }
    try { new MutationObserver(function (ms) { for (var i = 0; i < ms.length; i++) { var m = ms[i]; if (m.type === "attributes" && m.attributeName === "lang") { relabel(); return; } if (m.addedNodes && m.addedNodes.length) { for (var j = 0; j < m.addedNodes.length; j++) { var n = m.addedNodes[j]; if (n.nodeType === 1 && !(n.classList && n.classList.contains("cs-stub")) && (n.hasAttribute("data-scope") || n.querySelector && n.querySelector("[data-scope]"))) { soon(); return; } } } } }).observe(de, { attributes: true, attributeFilter: ["lang"], childList: true, subtree: true }); } catch (e) {}
  }
  if (d.readyState === "loading") d.addEventListener("DOMContentLoaded", start); else start();
})();
