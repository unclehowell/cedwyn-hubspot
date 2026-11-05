/* Cedwyn runtime - loaded first in every theme page. Keeps each theme working under /<theme>/ on one URL:
   prefixes root-absolute paths made by page scripts, maps old subdomain URLs to /<theme>/..., and sends every
   outbound link to the archive interface (/wayback/go/). No tracking, no outbound requests. - Sion's Tab agent */
(function () {
  var me = document.currentScript, T = (me && me.getAttribute('data-theme')) || location.pathname.split('/')[1] || '';
  var SECTION_SPA = __SECTION_SPA__, P = '/' + T, HOSTS = __HOSTMAP__, APEX = __APEX__, MEDIA = __MEDIA__, THEMES = __THEMES__, COLLIDE = __COLLIDE__, VHOST = __VHOST__;
  // 25 Oct 2026 (Sion): two sections over one database. /wales/<theme>/... and /argentina/<theme>/... serve the same theme files
  // (Pages rewrites in _redirects, tools/sections.py); LP is the theme path without the section prefix. section.js adds the
  // section ribbon and keeps theme links inside the section; the section gives the default language (Wales cy, Argentina es).
  var DE0 = document.documentElement, SECM = /^\/(wales|argentina)(\/[^\/]+)/.exec(location.pathname), SEC = '', SS = '', LP = location.pathname;
  if (T && SECM && SECM[2] === P) { SEC = SECM[1]; LP = location.pathname.slice(SEC.length + 1); }
  try { if (SEC) sessionStorage.setItem('cedwyn-sec', SEC); else SS = sessionStorage.getItem('cedwyn-sec') || ''; } catch (e) {}
  if (SEC) DE0.setAttribute('data-cedwyn-sec-url', SEC);
  if (SEC || /^(wales|argentina)$/.test(SS)) {
    DE0.setAttribute('data-cedwyn-sec', SEC || SS);
    if (!DE0.getAttribute('data-ghf-lang-default')) DE0.setAttribute('data-ghf-lang-default', (SEC || SS) === 'wales' ? 'cy' : 'es');
    if (SEC && SECTION_SPA.indexOf(T) >= 0) try { history.replaceState(history.state, '', LP + location.search + location.hash); } catch (e) {}   // a client-side router reads the plain theme path
    var SJ = document.createElement('script'); SJ.src = '/_cedwyn/section.js?v=1.2.0'; SJ.async = true; (document.head || DE0).appendChild(SJ);
  }
  window.__cedwynSec = SEC; window.__cedwynLP = LP;
  // the shared header (basecamp.js) reads the theme's former address from <html data-ghf-host / data-ghf-path>
  (function () { var v = VHOST[T]; if (!v) return; var de = document.documentElement, rest = LP.slice(P.length).replace(/^\/+/, '');
    if (!de.getAttribute('data-ghf-host')) de.setAttribute('data-ghf-host', v[0]);
    if (!de.getAttribute('data-ghf-path')) de.setAttribute('data-ghf-path', v[1] + rest); })();
  // Stage 3: every theme reads its data and evidence from the one catalogue database. The service worker (/cedwyn-sw.js)
  // answers those requests from the database chunks. On a first visit, before the worker controls this page, loading
  // stops, the worker starts, and the page loads again under it (once per tab). Where no service worker can run, the
  // fetch/XHR and media fallbacks below read the same database from the page itself.
  var SWC = navigator.serviceWorker, SWOK = !!SWC && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1');
  function ss(k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } }
  if (SWOK) {
    if (!SWC.controller && !ss('cedwyn-sw')) {
      ss('cedwyn-sw', '1');
      try { window.stop(); } catch (e) {}
      var went = false, go = function () { if (!went) { went = true; location.reload(); } };
      SWC.addEventListener('controllerchange', go);
      SWC.register('/cedwyn-sw.js', { scope: '/', updateViaCache: 'none' }).then(function (reg) {
        if (reg.active && !SWC.controller) reg.active.postMessage('claim');
      }).catch(go);
      setTimeout(go, 6000);
    } else SWC.register('/cedwyn-sw.js', { scope: '/', updateViaCache: 'none' }).catch(function () {});
  }
  var DBX = /\.(json|csv|xml|geojson|png|jpe?g|gif|webp|svg|avif|ico|bmp|tiff?|pdf|docx?|mp3|m4a|ogg|wav)$/i, DBP = null;
  function noSW() { return !(SWC && SWC.controller); }
  function dbfs() {
    if (!DBP) DBP = new Promise(function (ok, no) { if (window.CedwynDB) return ok(window.CedwynDB); var s = document.createElement('script'); s.src = '/_cedwyn/dbfs.js?v=4';
      s.onload = function () { ok(window.CedwynDB); }; s.onerror = no; (document.head || document.documentElement).appendChild(s); });
    return DBP;
  }
  function dbPath(u) { try { var x = new URL(u, location.href); return x.origin === location.origin && DBX.test(x.pathname) && !/^\/(db|_cedwyn)\//.test(x.pathname) ? x.pathname : null; } catch (e) { return null; } }
  function fromDB(path) { return dbfs().then(function (D) { var p2 = path.replace(/^\/(wales|argentina)(\/[^\/]+\/)/, '$2'); return D.get(path).then(function (r) { return r || p2 === path ? r : D.get(p2); }); }); }
  var RES = ['/_cedwyn/', '/_blob/', '/db/', '/graphql', '/catalogue', '/wayback/go/', '/values/', '/argentina/', '/explore/', '/guestbook/', '/_ext/', '/areas.json', '/parcels/'];   // P-051 (30 Oct 2026): + vendored /_ext/ files and the central /areas.json, which live at the site root (theme-prefixed copies 404) - Sion's Tab agent   // 26 Oct 2026: + the Agent guest book
  function starts(u, a) { for (var i = 0; i < a.length; i++) if (u.indexOf(a[i]) === 0) return true; return false; }
  function mapHost(host, path) {
    host = host.toLowerCase();
    if (host === 'bucklerfamily.estate' || host === 'www.bucklerfamily.estate') {
      for (var i = 0; i < APEX.length; i++) { var pre = APEX[i][0]; if (path.indexOf(pre) === 0 || path + '/' === pre) return '/' + APEX[i][1] + '/' + path.slice(pre.length).replace(/^\/+/, ''); }
    }
    if (host === location.hostname) return path;
    if (HOSTS[host]) return '/' + HOSTS[host] + (path.charAt(0) === '/' ? path : '/' + path);
    return null;
  }
  function fix(u) {
    if (typeof u !== 'string' || !u) return u;
    if (u.charAt(0) === '/' && u.charAt(1) !== '/') {
      if (!T || u === P || u.indexOf(P + '/') === 0 || starts(u, RES)) return u;
      if (/^\/[a-z0-9-]+\/_db\//.test(u)) return u;   // P-101 (30 Oct 2026): an area's child database (/<area>/_db/) lives at the site root - Sion's Tab agent
      var x = u.split(/[\/?#]/)[1];   // already a cedwyn theme path (/<theme>/...): leave it, unless this theme has its own folder of that name
      if (x && THEMES.indexOf(x) >= 0 && (COLLIDE[T] || []).indexOf(x) < 0) return u;
      return P + u;
    }
    var m = u.match(/^(?:https?:)?\/\/([^\/?#:]+)(?::\d+)?([^?#]*)(.*)$/i);
    if (m) { var t = mapHost(m[1], m[2] || '/'); if (t !== null) return t + m[3]; }
    return u;
  }
  function isOut(u) {
    var m = String(u).match(/^(?:https?:)?\/\/([^\/?#:]+)/i);
    return !!(m && m[1].toLowerCase() !== location.hostname && mapHost(m[1], '/') === null) && !pass(String(u));
  }
  function archive(u) { return '/wayback/go/?u=' + encodeURIComponent(u); }
  window.__cedwyn = { theme: T, fix: fix, archive: archive };
  // 25 Oct 2026: a link to the archive interface whose address is really a theme (a former *.bucklerfamily.estate site, the
  // Legal Wiki on wordpress.com) opens that theme: /wayback/go/ is only for outside addresses with no theme
  function untrap(h) { var m = /^(?:https?:\/\/[^\/]+)?\/wayback\/go\/\?u=([^&#]+)/.exec(h || ''), u, t; if (!m) return null;
    try { u = decodeURIComponent(m[1]); } catch (e) { return null; } if (pass(u)) return u; t = fix(u); return t !== u && t.charAt(0) === '/' ? t : null; }
  window.__cedwyn.untrap = untrap;
  // 25 Oct 2026 (sales fix): the shop's own checkout and sign-up hosts are the one exception to "no outbound links":
  // a buy button opens Stripe/Gumroad checkout instead of the archive page (26 Oct 2026: the mailing list is now Cedwyn's own, below).
  function pass(u) { var m = /^https:\/\/([^\/?#:]+)/i.exec(u || ''), h; if (!m) return false; h = m[1].toLowerCase();
    return h === 'buy.stripe.com' || h === 'checkout.stripe.com' || h === 'gumroad.com' || /\.gumroad\.com$/.test(h)
      // 26 Oct 2026: the Agent guest book's version links (commits of this site's own repository) open GitHub directly; the owner allowed them out
      || (h === 'github.com' && /^\/unclehowell\/cedwyn\/commits?\/[^\s]+$/i.test(u.replace(/^https:\/\/[^\/]+/i, '').split(/[?#]/)[0])); }   // 27 Oct 2026: also a page's commit history (commits/<branch>/<path>), the version table's "See all"
  window.__cedwyn.pass = pass;
  document.addEventListener('submit', function (e) { var f = e.target, a = f && f.getAttribute ? f.getAttribute('action') : '', m, u;
    m = /^(?:https?:\/\/[^\/]+)?\/wayback\/go\/\?u=([^&#]+)/.exec(a || ''); if (!m) return;
    try { u = decodeURIComponent(m[1]).replace(/&amp;/g, '&'); } catch (x) { return; } if (pass(u)) f.setAttribute('action', u); }, true);
  // 26 Oct 2026: Cedwyn's own mailing list replaces Mailchimp. A sign-up form that still points at Mailchimp (list-manage.com, directly
  // or through /wayback/go/), and the film page's form, post to /api/list/subscribe instead: the visitor gets a confirm email from
  // cedwyn@bucklerfamily.estate and joins when they tap its link. The page's own checks (email, consent tick) run first.
  var LW = { en: ['Nearly there: check your email and tap the link to confirm.', 'That did not go through. Please try again later.', 'Please enter a valid email address.'],
    cy: ['Bron yno: edrychwch ar eich e-bost a thapio’r ddolen i gadarnhau.', 'Ni aeth hynny drwodd. Rhowch gynnig arall arni yn nes ymlaen.', 'Rhowch gyfeiriad e-bost dilys.'],
    es: ['Casi listo: revise su correo y pulse el enlace para confirmar.', 'No se pudo enviar. Inténtelo más tarde.', 'Escriba una dirección de correo válida.'] };
  function llang() { var l = window.__cedwynLang || ''; if (!l) { try { l = localStorage.getItem('ghf_lang') || ''; } catch (x) {} }
    l = (l || DE0.getAttribute('data-ghf-lang-default') || DE0.getAttribute('lang') || 'en').slice(0, 2).toLowerCase(); return LW[l] ? l : 'en'; }
  function mcForm(f) { var a = f.getAttribute('action') || ''; try { a = decodeURIComponent(a); } catch (x) {} return /list-manage\.com/i.test(a) || f.id === 'cm-sub' || f.hasAttribute('data-cedwyn-mc'); }   // data-cedwyn-mc: a Mailchimp form the build pointed at /api/list/subscribe (26 Oct 2026)
  function listSend(f) {
    var em = f.querySelector('input[name=EMAIL],input[name=email],input[type=email]'), v = em ? String(em.value || '').trim() : '', l = llang(), W = LW[l];
    var hp = f.querySelector('input[name^="b_"],input[name=website]'), nm = f.querySelector('input[name=FNAME],input[name=name]'), src = f.querySelector('input[name=UTMSRC]');
    var done = f.parentNode && f.parentNode.querySelector('.ghf-done'), msg = f.querySelector('[role=status]') || f.querySelector('.ghf-err');
    function say(t, ok) {
      if (ok && done) { var p = done.querySelector('p'); if (p) p.textContent = t; done.hidden = false; f.hidden = true; return; }
      if (!msg) { msg = document.createElement('p'); msg.setAttribute('role', 'status'); f.appendChild(msg); }
      msg.textContent = t; msg.hidden = false; if (ok) [].forEach.call(f.querySelectorAll('input,button'), function (x) { x.disabled = true; });
    }
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v)) { say(W[2]); return; }
    var topic = f.id === 'cm-sub' ? 'film' : /sample-chapter/.test(src ? src.value : '') ? 'sample-chapter' : 'news';
    var b = f.querySelector('[type=submit]'); if (b) b.disabled = true;
    (of || fetch).call(window, '/api/list/subscribe', { method: 'POST', credentials: 'omit', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ email: v, lang: l, topic: topic, source: location.pathname, name: nm ? nm.value : '', website: hp ? hp.value : '' }) })
      .then(function (r) { return r.json().catch(function () { return {}; }); })
      .then(function (j) { if (b) b.disabled = false; if (j && j.ok) say(W[0], true); else say((j && j.message) || W[1]); }, function () { if (b) b.disabled = false; say(W[1]); });
  }
  document.addEventListener('submit', function (e) { var f = e.target; if (!f || !f.getAttribute || f.id !== 'cm-sub' || !mcForm(f)) return;
    e.preventDefault(); e.stopImmediatePropagation(); listSend(f); }, true);   // the film page's form: ours from the start
  document.addEventListener('submit', function (e) { var f = e.target; if (!f || !f.getAttribute || f.id === 'cm-sub' || !mcForm(f)) return;
    if (e.defaultPrevented) return;   // the page's own check stopped it (no email, no tick)
    e.preventDefault(); setTimeout(function () { listSend(f); }, 0); }, false);
  document.addEventListener('click', function (e) { var a = e.target && e.target.closest ? e.target.closest('a[href]') : null, t;
    if (a && (t = untrap(a.getAttribute('href')))) a.setAttribute('href', t); }, true);
  var of = window.fetch;
  if (of) window.fetch = function (i, o) {
    try { if (typeof i === 'string') i = fix(i); else if (i && i.url && i.url.indexOf(location.origin + '/') === 0) { var f = fix(i.url.slice(location.origin.length)); if (f !== i.url.slice(location.origin.length)) i = new Request(f, i); } } catch (e) {}
    var self_ = this, dp = noSW() && (!o || !o.method || /^get$/i.test(o.method)) && dbPath(typeof i === 'string' ? i : (i && i.url) || '');
    if (dp) return fromDB(dp).then(function (r) { return r ? new Response(r.bytes, { status: 200, headers: { 'Content-Type': r.mime, 'X-Cedwyn-Source': 'db-page' } }) : of.call(self_, i, o); }, function () { return of.call(self_, i, o); });
    return of.call(this, i, o);
  };
  var xo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u) { var a = [].slice.call(arguments); a[1] = fix(u);
    this.__cdb = noSW() && /^get$/i.test(m) && a[2] !== false && dbPath(a[1]) ? [m, dbPath(a[1])] : null; return xo.apply(this, a); };
  var xs = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function () {   // no service worker: the same database, read from this page
    var x = this, d = x.__cdb, args = arguments; if (!d) return xs.apply(x, args);
    x.__cdb = null;
    fromDB(d[1]).then(function (r) { if (r) { xo.call(x, d[0], URL.createObjectURL(new Blob([r.bytes], { type: r.mime })), true); } xs.apply(x, args); }, function () { xs.apply(x, args); });
  };
  // media that failed to load before the worker took over (or with no worker at all): load it again from the database
  document.addEventListener('error', function (e) {
    var el = e.target, tag = el && el.tagName; if (!/^(IMG|SOURCE|VIDEO|AUDIO|EMBED|INPUT)$/.test(tag || '') || el.__cdbTried) return;
    var src = el.currentSrc || el.getAttribute('src'), dp = src && dbPath(src); if (!dp) return; el.__cdbTried = 1;
    if (!noSW()) { var u = new URL(src, location.href); u.searchParams.set('cdb', '1'); el.setAttribute('src', u.pathname + u.search); return; }
    fromDB(dp).then(function (r) { if (r) el.setAttribute('src', URL.createObjectURL(new Blob([r.bytes], { type: r.mime }))); }, function () {});
  }, true);
  var sa = Element.prototype.setAttribute, ATTRS = { src: 1, href: 1, action: 1, poster: 1, 'data-src': 1 };
  Element.prototype.setAttribute = function (n, v) {
    if (ATTRS[String(n).toLowerCase()] && typeof v === 'string') { v = fix(v); if (/^iframe$/i.test(this.tagName) && /UC2sN1VEs1WeLfBH8VmbvLWw|sionbuckler5713/i.test(v)) v = 'about:blank'; }
    return sa.call(this, n, v);
  };
  [['HTMLImageElement', 'src'], ['HTMLScriptElement', 'src'], ['HTMLLinkElement', 'href'], ['HTMLSourceElement', 'src'], ['HTMLIFrameElement', 'src'],
   ['HTMLMediaElement', 'src'], ['HTMLAnchorElement', 'href'], ['HTMLFormElement', 'action'], ['HTMLVideoElement', 'poster']].forEach(function (c) {
    var K = window[c[0]]; if (!K) return; var d = Object.getOwnPropertyDescriptor(K.prototype, c[1]); if (!d || !d.set) return;
    Object.defineProperty(K.prototype, c[1], { configurable: true, enumerable: d.enumerable, get: d.get, set: function (v) { d.set.call(this, fix(String(v))); } });
  });
  ['pushState', 'replaceState'].forEach(function (k) { var h = history[k]; history[k] = function (s, t, u) { return h.call(this, s, t, u == null ? u : fix(String(u))); }; });
  var wo = window.open; window.open = function (u) { var a = [].slice.call(arguments); if (a[0]) { a[0] = fix(String(a[0])); if (isOut(a[0])) { location.href = archive(new URL(a[0], location.href).href); return null; } } return wo.apply(window, a); };
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href],area[href]') : null; if (!a) return;
    var h = a.getAttribute('href'); if (!h) return;
    if (isOut(h)) { e.preventDefault(); e.stopPropagation(); location.href = archive(new URL(h, location.href).href); return; }
    if (/^(?:https?:)?\/\//i.test(h)) { var f = fix(h); if (f !== h) a.setAttribute('href', f); }  // static paths are already resolved at build time
  }, true);
  document.addEventListener('submit', function (e) {
    var f = e.target, act = f && f.getAttribute && f.getAttribute('action');
    if (act && isOut(act)) { e.preventDefault(); location.href = archive(new URL(act, location.href).href); }
  }, true);
  function sweep(root) {
    if (!root || !root.querySelectorAll) return;
    var els = [].slice.call(root.querySelectorAll('[src^="/"],[href^="/"],[poster^="/"]')); if (root.getAttribute) els.unshift(root);
    for (var i = 0; i < els.length; i++) ['src', 'href', 'poster'].forEach(function (n) { var v = els[i].getAttribute(n); if (v && v.charAt(0) === '/') { var f = fix(v); if (f !== v) sa.call(els[i], n, f); } });
  }
  // only nodes that page scripts add after parsing are swept: the parsed page was resolved at build time
  function watch() { try { new MutationObserver(function (ms) { ms.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType === 1) { sweep(n); } }); }); }).observe(document.documentElement, { childList: true, subtree: true }); } catch (e) {} }
  // small Cedwyn pill: back to the theme picker, search the shared catalogue
  function pill() {
    if (document.getElementById('cedwyn-pill') || !document.body) return;
    var d = document.createElement('div'); d.id = 'cedwyn-pill';
    d.innerHTML = '<a href="/" title="All Cedwyn themes" aria-label="All Cedwyn themes">C</a><a href="/catalogue/?theme=' + encodeURIComponent(T) + '" title="Search the catalogue" aria-label="Search the catalogue">&#9906;</a>';
    var s = document.createElement('style');
    s.textContent = '#cedwyn-pill{position:fixed;left:8px;bottom:8px;z-index:2147483000;display:flex;gap:4px;opacity:.72;font:600 13px/1 -apple-system,Segoe UI,Roboto,sans-serif}#cedwyn-pill:hover{opacity:1}#cedwyn-pill a{display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:15px;background:#14141c;color:#fca;text-decoration:none;border:1px solid #fca;box-shadow:0 1px 4px rgba(0,0,0,.3)}@media print{#cedwyn-pill{display:none}}';
    document.head.appendChild(s); document.body.appendChild(d);
  }
  function parcelPanelScript() {
    if (document.querySelector('script[data-cedwyn-parcel-panel]')) return;
    var s = document.createElement('script'); s.src = '/_cedwyn/parcel-panel.js?v=1'; s.defer = true;
    s.setAttribute('data-cedwyn-parcel-panel', '1'); document.head.appendChild(s);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { watch(); pill(); parcelPanelScript(); }); else { watch(); pill(); parcelPanelScript(); }
  // Unsubstantiated text (Sion, 03:07 GMT 26 Oct 2026): .unsub = smaller italic, one en/cy/es legend per page (tools/unsub.py) - Sion's Tab agent
  (function () {
    var LG = { en: "Small italic text = not yet backed by a record in this archive.", cy: "Testun italig bach = heb ei ategu eto gan gofnod yn yr archif hon.", es: "Texto pequeño en cursiva = aún sin respaldo de un documento en este archivo." };
    function css() { if (document.getElementById("cedwyn-unsub-css")) return; var s = document.createElement("style"); s.id = "cedwyn-unsub-css";
      s.textContent = ".unsub{font-size:.86em;font-style:italic}.unsub .unsub{font-size:1em}#cedwyn-unsub-legend{font-size:12px;line-height:1.35;font-style:italic;opacity:.85;margin:6px 0 8px}#cedwyn-unsub-legend .unsub-eg{font-size:.86em}";
      (document.head || document.documentElement).appendChild(s); }
    function lg() { var l = ""; try { if (window.CedwynSection) l = window.CedwynSection.lang(); } catch (e) {} if (!l) { try { l = localStorage.getItem("ghf_lang") || ""; } catch (e) {} }
      l = (l || document.documentElement.getAttribute("lang") || "en").slice(0, 2); return LG[l] ? l : "en"; }
    function go() { css(); if (!document.body) return; var u = document.querySelector(".unsub"), g = document.getElementById("cedwyn-unsub-legend"); if (!u) return;
      if (!g) { g = document.createElement("p"); g.id = "cedwyn-unsub-legend"; g.setAttribute("data-no-translate", ""); var m = document.querySelector("main") || u.parentNode;
        if (m === document.querySelector("main")) m.insertBefore(g, m.firstChild); else m.parentNode.insertBefore(g, m); }
      var l = lg(); g.setAttribute("lang", l); g.textContent = LG[l]; }
    css(); if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
    window.addEventListener("load", go); document.addEventListener("ghf-lang-change", function () { setTimeout(go, 150); }); window.CedwynUnsub = go;
  })();
  // Headline-first pages (Sion, 12:01 GMT 26 Oct 2026, m:2c8d96e9): tools/headlines.py folds each section's detail into a native
  // <details class="cw-more">; this relabels "Read more" in the chosen language and opens a fold that a link points into - Sion's Tab agent
  (function () {
    var LB = { en: "Learn more", cy: "Dysgu mwy", es: "Saber m\u00e1s" };   // Sion 22:12 GMT 26 Oct 2026 (m:611a2587): "learn more"
    function lg() { var l = ""; try { if (window.CedwynSection) l = window.CedwynSection.lang(); } catch (e) {} if (!l) { try { l = localStorage.getItem("ghf_lang") || ""; } catch (e) {} }
      l = (l || document.documentElement.getAttribute("data-ghf-lang-default") || document.documentElement.getAttribute("lang") || "en").slice(0, 2); return LB[l] ? l : "en"; }
    function label() { var q = document.querySelectorAll("details.cw-more > summary .cw-more-l"), t = LB[lg()], i; for (i = 0; i < q.length; i++) if (q[i].textContent !== t) q[i].textContent = t; }
    function reveal() { var h = location.hash ? decodeURIComponent(location.hash.slice(1)) : "", el, d; if (!h) return; try { el = document.getElementById(h); } catch (e) { el = null; }
      d = el && el.closest ? el.closest("details.cw-more") : null; while (d) { d.open = true; d = d.parentElement && d.parentElement.closest ? d.parentElement.closest("details.cw-more") : null; }
      if (el && el.scrollIntoView) setTimeout(function () { el.scrollIntoView(); }, 30); }
    function go() { label(); reveal(); }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
    window.addEventListener("hashchange", reveal); document.addEventListener("ghf-lang-change", function () { setTimeout(label, 150); }); window.CedwynMore = go;
  })();
})();
/* Dark guard 1.0.0 (30 Oct 2026): in night mode a page drawn dark by its own CSS can still carry blocks whose CSS
   hard-codes a white or pale background (cards, tables, notes, callouts, panels), which show as white boxes, often with
   light text on them. This recolours any such block to a dark tint of its own colour and lifts any text that would fall
   under 4.5:1 contrast. Day mode is untouched and everything is restored on a switch back. Inverted pages (html.ghf-inv),
   media, the shared header (.ghf-ui), [data-ghf-keep] and preserved archive copies are left alone.
   Opt out per page with <html data-ghf-dark-guard="off">. - Sion's Tab agent */
(function () {
  if (window.__cedwynDarkGuard) return; window.__cedwynDarkGuard = '1.0.0'; 
  var de = document.documentElement, done = [], on = false, q = [], busy = false;
  window.__cedwynDarkGuardCount = function () { return done.length; };
  if (/^\/(?:[\w-]+\/)?wayback\/(?:websites|mail|go|html|snapshots?)\//.test(location.pathname)) return;
  var SKIP = /^(IMG|VIDEO|CANVAS|IFRAME|EMBED|OBJECT|SVG|PICTURE|SOURCE|SCRIPT|STYLE|NOSCRIPT|BR|HR|PATH|G|USE|TEMPLATE|AUDIO|TRACK|MATH)$/;
  function rgb(c) { var m = /rgba?\(([^)]+)\)/.exec(c || ''); if (!m) return null; var v = m[1].split(/[\s,\/]+/).filter(Boolean).map(parseFloat); if (v.length > 3 && v[3] < 0.35) return null; return v; }
  function lum(v) { function f(x) { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); } return 0.2126 * f(v[0]) + 0.7152 * f(v[1]) + 0.0722 * f(v[2]); }
  function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function night() { return de.getAttribute('data-ghf-mode') === 'night' && !de.classList.contains('ghf-inv') && de.getAttribute('data-ghf-dark-guard') !== 'off'; }
  function dark(v) { var mn = Math.min(v[0], v[1], v[2]); return [0, 1, 2].map(function (i) { return Math.round(30 + (v[i] - mn) * 0.55); }); }
  function css(v) { return 'rgb(' + v.join(',') + ')'; }
  function set(el, p, val) { if (!el.__cdg) { el.__cdg = {}; done.push(el); } if (!(p in el.__cdg)) el.__cdg[p] = [el.style.getPropertyValue(p), el.style.getPropertyPriority(p)]; el.style.setProperty(p, val, 'important'); }
  function kept(el) { return el.closest && el.closest('.ghf-ui,[data-ghf-keep],svg,#ghf-agent-footer[hidden]'); }
  function ground(el) { for (var e = el; e && e.nodeType === 1; e = e.parentElement) { var v = rgb((e.__cdg && e.style.getPropertyValue('background-color')) || getComputedStyle(e).backgroundColor); if (v) return v; } return [0, 0, 0]; }
  function fixBg(el) {
    if (SKIP.test(el.tagName.toUpperCase()) || kept(el)) return;
    var cs = getComputedStyle(el); if (cs.display === 'none') return;
    var bi = cs.backgroundImage || 'none';
    if (bi !== 'none' && /gradient/.test(bi) && !/url\(/.test(bi)) {
      var st = (bi.match(/rgba?\([^)]+\)/g) || []).map(rgb).filter(Boolean);
      if (st.length && st.every(function (v) { return lum(v) > 0.72; })) {
        set(el, 'background-image', bi.replace(/rgba?\(([^)]+)\)/g, function (m0, a) { var v = a.split(/[\s,\/]+/).filter(Boolean).map(parseFloat); if (lum(v) <= 0.72) return m0; var d = dark(v); return 'rgba(' + d.join(',') + ',' + (v.length > 3 ? v[3] : 1) + ')'; }));
        var b0 = rgb(cs.backgroundColor); if (b0 && lum(b0) > 0.72) set(el, 'background-color', css(dark(b0))); return;
      }
    }
    var v = rgb(cs.backgroundColor);
    if (v && /^(A|BUTTON|INPUT|SELECT|OPTION|LABEL)$/.test(el.tagName.toUpperCase()) || el.getAttribute('role') === 'button') { var r = el.getBoundingClientRect(); if (r.width * r.height < 40000) return; }
    if (v && lum(v) > 0.72 && !/url\(/.test(bi)) set(el, 'background-color', css(dark(v)));
  }
  function hasText(el) { for (var n = el.firstChild; n; n = n.nextSibling) if (n.nodeType === 3 && /\S/.test(n.nodeValue)) return true; return /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(el.tagName); }
  function fixText(el) {
    if (SKIP.test(el.tagName.toUpperCase()) || !hasText(el) || kept(el)) return;
    var c = rgb(getComputedStyle(el).color); if (!c) return; var g = ground(el);
    if (ratio(c, g) >= 4.5) return;
    var light = lum(g) < 0.18, k, t;
    for (k = 0.3; k <= 1.001; k += 0.1) { t = c.map(function (x) { return Math.round(light ? x + (255 - x) * k : x * (1 - k)); }); if (ratio(t, g) >= 4.5) break; }
    set(el, 'color', css(t));
  }
  function walk(root) { var all = root.querySelectorAll ? root.querySelectorAll('*') : []; var i; if (root.nodeType === 1 && root !== de) { fixBg(root); } for (i = 0; i < all.length; i++) fixBg(all[i]); if (root.nodeType === 1 && root !== de) fixText(root); for (i = 0; i < all.length; i++) fixText(all[i]); }
  function restore() { for (var i = 0; i < done.length; i++) { var el = done[i], s = el.__cdg; for (var p in s) { if (s[p][0]) el.style.setProperty(p, s[p][0], s[p][1]); else el.style.removeProperty(p); } el.__cdg = null; } done = []; }
  function run() { busy = false; var n = night(); if (!n) { if (on) restore(); on = false; q = []; return; } if (!on) { on = true; q = []; if (document.body) walk(document.body); return; } var w = q; q = []; for (var i = 0; i < w.length; i++) if (w[i].isConnected) walk(w[i]); }
  function soon(t) { if (!busy) { busy = true; setTimeout(run, t || 60); } }
  try { new MutationObserver(function () { if (on && !night()) { restore(); on = false; } else soon(30); }).observe(de, { attributes: true, attributeFilter: ['data-ghf-mode', 'class', 'data-ghf-dark-guard', 'style'] }); } catch (e) {}
  function start() { soon(0); try { new MutationObserver(function (ms) { if (!on) return; for (var i = 0; i < ms.length; i++) { var m = ms[i]; if (m.type === 'childList') { for (var j = 0; j < m.addedNodes.length; j++) if (m.addedNodes[j].nodeType === 1) q.push(m.addedNodes[j]); } else if (m.target.nodeType === 1 && !m.target.__cdg) q.push(m.target); } if (q.length) soon(250); }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class'] }); } catch (e) {} }
  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
  window.addEventListener('load', function () { if (on) { q.push(document.body); soon(100); } });
})();
