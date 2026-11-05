/* cw-graph.js v1.2.4 (30 Oct 2026 21:20Z: on a page carrying the parcel-story panel, the panel leaves the page flow and opens
   in this modal under a 'Parcel story' tab (last tab); on /research/ an 'Instruments & registrations' tab plotting /_cedwyn/graph/parcels.json opens first; 1.2.3 (30 Oct 2026: long axis names wrap to two lines at 390 px; 1.2.2: a graph may fix its own colours, data.c.colors — Dartboard green/amber/red) - graph promo banner, full-screen scatter modal and 100vh "Read more" clip for every Cedwyn page.
   Asked for 01:27 GMT 30 Oct 2026: the closable header strip becomes a graph promotion; tapping it slides a full-screen
   scatter graph of the data the page/section shows down over the page (it slides back up on close, Esc or swipe up);
   text pages load clipped to the screen height with a "Read more" bar, further text arriving in chunks from the build's
   per-page JSON (/<page>/_more/N.json) on demand. Data: /_cedwyn/graph/<area>.json (built by tools/graph_data.py) or,
   when a section has none, the page's own items and dated text. No outside services, no libraries. - Cedwyn editors */
(function () {
  'use strict';
  if (window.__cwGraph) return;
  var d = document, de = d.documentElement, VER = '1.2.4';
  window.__cwGraph = { v: VER };
  var RM = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  var T = {
    en: { promo: 'See this section as a graph', cta: 'Graph', close: 'Close', closeg: 'Close the graph', more: 'Read more', page: 'This page', sec: 'Whole section', open: 'Open', none: 'Nothing on this page has dates or values to plot yet.', pts: 'points', tap: 'Tap a dot to see what it is.', rank: 'dates spaced evenly in date order', loading: 'Loading…', inst: 'Instruments & registrations', story: 'Parcel story' },
    cy: { promo: 'Gweld yr adran hon fel graff', cta: 'Graff', close: 'Cau', closeg: 'Cau’r graff', more: 'Darllen mwy', page: 'Y dudalen hon', sec: 'Yr adran gyfan', open: 'Agor', none: 'Does dim dyddiadau na gwerthoedd i’w plotio ar y dudalen hon eto.', pts: 'pwynt', tap: 'Tapiwch ddot i weld beth ydyw.', rank: 'dyddiadau wedi’u gosod yn gyfartal yn ôl trefn', loading: 'Wrthi’n llwytho…', inst: 'Offerynnau a chofrestriadau', story: 'Stori’r llain' },
    es: { promo: 'Ver esta sección como gráfico', cta: 'Gráfico', close: 'Cerrar', closeg: 'Cerrar el gráfico', more: 'Leer más', page: 'Esta página', sec: 'Toda la sección', open: 'Abrir', none: 'Esta página aún no tiene fechas ni valores para graficar.', pts: 'puntos', tap: 'Toca un punto para ver qué es.', rank: 'fechas espaciadas por orden', loading: 'Cargando…', inst: 'Instrumentos y registros', story: 'Historia de la parcela' }
  };
  function lg() { var l = (de.getAttribute('lang') || 'en').slice(0, 2).toLowerCase(); return T[l] ? l : 'en'; }
  function t(k) { return T[lg()][k]; }
  function mk(tag, cls, txt) { var e = d.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function night() {
    var m = de.getAttribute('data-ghf-mode');
    if (m === 'night' || de.getAttribute('data-ghf-native') === 'dark') return true;
    if (m === 'day') return false;
    return !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
  }
  var segs = location.pathname.split('/').filter(Boolean), half = '';
  if (segs[0] === 'wales' || segs[0] === 'argentina') half = segs.shift();
  var AREA = (segs[0] || (half || 'home')).toLowerCase().replace(/[^a-z0-9-]/g, '');
  var CSS =
    '.cw-gb{display:flex;align-items:stretch;width:100%;height:34px;min-width:0}' +
    '.cw-gb-open{all:unset;box-sizing:border-box;flex:1 1 auto;min-width:0;display:flex;align-items:center;gap:9px;height:34px;padding:0 4px 0 2px;color:inherit;cursor:pointer;font:13px/1 system-ui,-apple-system,Segoe UI,sans-serif;letter-spacing:.02em;-webkit-tap-highlight-color:transparent}' +
    '.cw-gb-open svg{flex:0 0 auto;display:block}.cw-gb-t{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}' +
    '.cw-gb-c{flex:0 0 auto;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--ghf-s,#f2c94c);white-space:nowrap}' +
    '.cw-gb-x{all:unset;box-sizing:border-box;flex:0 0 auto;width:44px;height:34px;margin-right:-10px;display:flex;align-items:center;justify-content:center;color:inherit;opacity:.75;cursor:pointer;font:20px/1 system-ui,sans-serif}' +
    '.cw-gb-open:focus-visible,.cw-gb-x:focus-visible{outline:2px solid var(--ghf-s,#f2c94c);outline-offset:-2px}' +
    '.cw-gm{position:fixed;inset:0;z-index:2147483000;display:flex;flex-direction:column;background:var(--gm-bg);color:var(--gm-fg);transform:translateY(-102%);transition:transform .25s ease-out;visibility:hidden;font:15px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;--gm-bg:#fbfaf6;--gm-fg:#1b1b1b;--gm-mu:#5d5d5d;--gm-ln:rgba(0,0,0,.14);--gm-card:#fff}' +
    '.cw-gm.cw-night{--gm-bg:#101215;--gm-fg:#eceef1;--gm-mu:#a9b0b9;--gm-ln:rgba(255,255,255,.16);--gm-card:#1b1f24}' +
    '.cw-gm.cw-on{transform:translateY(0);visibility:visible}.cw-gm.cw-rm{transition:none}' +
    '.cw-gm-h{display:flex;align-items:center;gap:10px;padding:max(10px,env(safe-area-inset-top)) 12px 8px 16px;border-bottom:1px solid var(--gm-ln)}' +
    '.cw-gm-h h2{flex:1 1 auto;margin:0;font:600 17px/1.25 system-ui,sans-serif;min-width:0}.cw-gm-h small{display:block;font-weight:400;font-size:12px;color:var(--gm-mu);margin-top:2px}' +
    '.cw-gm-x{all:unset;box-sizing:border-box;width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;font:22px/1 system-ui;color:var(--gm-fg)}' +
    '.cw-gm-x:focus-visible,.cw-gm-tab:focus-visible{outline:2px solid currentColor}' +
    '.cw-gm-tabs{display:flex;gap:6px;padding:8px 16px 0}.cw-gm-tab{all:unset;cursor:pointer;padding:6px 12px;border-radius:999px;border:1px solid var(--gm-ln);font-size:13px}.cw-gm-tab[aria-pressed=true]{background:var(--gm-fg);color:var(--gm-bg)}' +
    '.cw-gm-sp{flex:1 1 auto}.cw-gm-b{flex:0 1 auto;min-height:0;overflow:auto;padding:6px 8px 0;-webkit-overflow-scrolling:touch}' +
    '#cedwyn-parcel-panel:not(.cw-gm-pp){display:none!important}.cw-gm-b #cedwyn-parcel-panel.cw-gm-pp{display:block!important;margin:0 4px 8px;max-width:none}' +
    '.cw-gm-b svg{display:block;width:100%;height:auto;touch-action:manipulation}.cw-gm-b text{fill:var(--gm-mu);font:11px system-ui,sans-serif}' +
    '.cw-gm-b .ax{stroke:var(--gm-ln)}.cw-gm-b .pt{cursor:pointer;stroke:var(--gm-bg);stroke-width:1}.cw-gm-b .pt.sel{stroke:var(--gm-fg);stroke-width:2.5}' +
    '.cw-gm-lg{display:flex;flex-wrap:wrap;gap:6px 12px;padding:6px 16px;font-size:12px;color:var(--gm-mu)}.cw-gm-lg i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}' +
    '.cw-gm-i{margin:0 12px 8px;padding:10px 12px;border-radius:10px;background:var(--gm-card);border:1px solid var(--gm-ln);min-height:44px;font-size:14px}' +
    '.cw-gm-i b{display:block}.cw-gm-i span{color:var(--gm-mu);font-size:12px}.cw-gm-i a{color:inherit;font-weight:600}' +
    '.cw-gm-f{padding:8px 16px max(10px,env(safe-area-inset-bottom));border-top:1px solid var(--gm-ln);font-size:13px}.cw-gm-f a{color:inherit}' +
    'html.cw-gm-lock,html.cw-gm-lock body{overflow:hidden!important}html.cw-vh-lock{overflow-y:hidden!important}' +
    '.cw-vh-clip{overflow:hidden!important}.cw-vh-hide{display:none!important}' +
    '.cw-vh-bar{position:sticky;bottom:0;z-index:50;display:flex;justify-content:center;padding:8px 12px calc(8px + env(safe-area-inset-bottom));background:var(--cw-vh-bg,#fff)}' +
    '.cw-vh-bar:before{content:"";position:absolute;left:0;right:0;top:-56px;height:56px;pointer-events:none;background:linear-gradient(to bottom,rgba(0,0,0,0),var(--cw-vh-bg,#fff))}' +
    '.cw-vh-btn{all:unset;box-sizing:border-box;cursor:pointer;min-height:44px;padding:0 26px;border-radius:999px;display:flex;align-items:center;font:600 15px/1 system-ui,sans-serif;background:var(--cw-vh-fg,#111);color:var(--cw-vh-bg,#fff)}' +
    '.cw-vh-btn:focus-visible{outline:3px solid var(--ghf-s,#f2c94c);outline-offset:2px}' +
    '.cwl-hid{display:none!important}.cwl-on .cwl-pv,.cwl-on .cwl-rm,.cwl-back[hidden]{display:none}.cwl-on .cwl-x{display:none!important}' +
            '.cwl-card{display:block;position:relative;cursor:pointer;padding:14px 4px 12px;margin:0;border:0;border-bottom:1px solid rgba(127,127,127,.22);border-radius:0;background:none;-webkit-tap-highlight-color:transparent;transition:background .15s}' +
    '.cwl-card:hover{background:rgba(127,127,127,.07)}.cwl-card:focus-visible{outline:3px solid var(--ghf-s,#f2c94c);outline-offset:2px}' +
    '.cwl-card>.cwl-h{margin:0 0 6px!important;font-size:1.12em;line-height:1.3}.cwl-card>.cwl-body,.cwl-card>.cwl-s{display:none!important}' +
    '.cwl-card>.cwl-pv{display:-webkit-box!important;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;margin:0 0 6px;opacity:.86;line-height:1.5}' +
    '.cwl-card>.cwl-rm{display:inline-block!important;font-weight:600;font-size:.92em;text-decoration:underline;text-underline-offset:3px}.cwl-card>.cwl-rm:after{content:" \u203a"}' +
    '.cwl-cur>.cwl-h{scroll-margin-top:70px}.cwl-cur>.cwl-h:focus{outline:none}.cwl-sum{display:none!important}.cwl-dup{display:none!important}.cwl-mh{font-weight:700;font-size:1.05em;margin:0 0 6px}' +
    '.cwl-back{position:sticky;top:8px;z-index:60;display:inline-flex;align-items:center;gap:6px;min-height:44px;min-width:44px;max-width:calc(100vw - 24px);padding:0 16px 0 12px;margin:4px 0 10px;border-radius:999px;border:1px solid rgba(127,127,127,.35);background:var(--cw-lv-bg,rgba(255,255,255,.94));color:inherit;font:600 15px/1.1 system-ui,sans-serif;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.12);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}' +
    '.cwl-back:focus-visible{outline:3px solid var(--ghf-s,#f2c94c);outline-offset:2px}.cwl-ba{font-size:22px;line-height:1;margin-top:-2px}.cwl-bt{font-weight:400;opacity:.75;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:46vw}.cwl-bt:not(:empty):before{content:"\u00b7 "}' +
    'html[data-ghf-mode=night] .cwl-back,html.dark .cwl-back{--cw-lv-bg:rgba(24,26,30,.92)}@media (prefers-color-scheme:dark){html:not([data-ghf-mode=day]) .cwl-back{--cw-lv-bg:rgba(24,26,30,.92)}}' +
    'html.cwl-anim,html.cwl-anim body{overflow-x:hidden!important}.cwl-on{will-change:auto}html.cwl-anim .cwl-on{will-change:transform,opacity}' +
    '.cwl-on .cwl-gt{display:none}.cwl-card>.cwl-gt{display:block;font-weight:700;font-size:1.08em;line-height:1.3;margin:0 0 6px}.cwl-gk{display:inline-block;margin-left:6px;font-weight:500;font-size:.72em;opacity:.7;text-transform:uppercase;letter-spacing:.04em}.cwl-card.cwl-generic>.cwl-h{display:none!important}.cwl-on:not(.cwl-sub) .cwl-gh{}' +
    '@media print{.cwl-back,.cwl-pv,.cwl-rm,.cwl-more{display:none!important}}' +
    '@media print{.cw-vh-clip{max-height:none!important;overflow:visible!important}.cw-vh-hide{display:revert!important}.cw-vh-bar,.cw-gb{display:none!important}}';
  var st = mk('style'); st.id = 'cw-graph-css'; st.textContent = CSS; (d.head || de).appendChild(st);

  /* ---------------- banner ---------------- */
  var KEY = 'cw-gb-closed', bar = null, ebook = null;
  function closed() { try { return sessionStorage.getItem(KEY) === '1'; } catch (e) { return false; } }
  function thumb() {
    var p = [[3, 15], [7, 11], [10, 13], [13, 7], [16, 9], [19, 4], [22, 6], [8, 16], [17, 12]], s = '';
    for (var i = 0; i < p.length; i++) s += '<circle cx="' + p[i][0] + '" cy="' + p[i][1] + '" r="1.7"/>';
    return '<svg viewBox="0 0 26 20" width="30" height="22" aria-hidden="true"><path d="M1.5 1v17.5H25" fill="none" stroke="currentColor" stroke-opacity=".6" stroke-width="1"/><g fill="var(--ghf-s,#f2c94c)">' + s + '</g></svg>';
  }
  function takeover(up) {
    if (!up || up.querySelector('.cw-gb')) return;
    var a = up.querySelector('a.ghf-v2-upa'), col = getComputedStyle(a || up).color; if (a) { var tt = a.querySelector('.ghf-v2-upt'); ebook = { href: a.href, text: clean(tt ? tt.textContent : a.textContent) }; }
    if (closed()) { up.style.setProperty('display', 'none', 'important'); return; }
    var w = mk('div', 'cw-gb'), o = mk('button', 'cw-gb-open'), x = mk('button', 'cw-gb-x', '\u00d7'); w.style.color = col;
    o.type = 'button'; x.type = 'button'; o.setAttribute('aria-haspopup', 'dialog');
    o.innerHTML = thumb(); o.appendChild(mk('span', 'cw-gb-t', t('promo'))); o.appendChild(mk('span', 'cw-gb-c', t('cta') + ' \u203a'));
    x.setAttribute('aria-label', t('close'));
    o.onclick = function () { openModal(o); };
    x.onclick = function () { try { sessionStorage.setItem(KEY, '1'); } catch (e) {} up.style.setProperty('display', 'none', 'important'); try { window.dispatchEvent(new Event('resize')); } catch (e) {} };
    w.appendChild(o); w.appendChild(x); up.textContent = ''; up.appendChild(w); up.setAttribute('aria-label', t('promo'));
  }
  function watchBanner() {
    var n = 0, iv = setInterval(function () {
      var up = d.querySelector('.ghf-v2-up');
      if (up) { clearInterval(iv); bar = up; takeover(up); new MutationObserver(function () { if (!up.querySelector('.cw-gb')) takeover(up); }).observe(up, { childList: true }); }
      else if (++n > 100) clearInterval(iv);
    }, 100);
  }

  /* ---------------- data ---------------- */
  var MON = { jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11, ion: 0, chw: 1, maw: 2, ebr: 3, mai: 4, meh: 5, gor: 6, aws: 7, med: 8, hyd: 9, tach: 10, rhag: 11 };
  var RE_DATE = /(?:\b(1[0-9]\d\d|20[0-4]\d)-(\d\d)-(\d\d)\b)|(?:\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(1[0-9]\d\d|20[0-4]\d)\b)|(?:\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2},\s+)?(1[0-9]\d\d|20[0-4]\d)\b)|(?:(?:^|[^\w\-\/#.£$€])(1[0-9]\d\d|20[0-4]\d)(?![\w\-\/]|\.\d))/gi;
  function dates(s, max) {
    var out = [], m; RE_DATE.lastIndex = 0;
    while ((m = RE_DATE.exec(s)) && out.length < (max || 6)) {
      var y, mo = 0, dd = 1, prec = 'y';
      if (m[1]) { y = +m[1]; mo = +m[2] - 1; dd = +m[3]; prec = 'd'; }
      else if (m[4]) { y = +m[6]; mo = MON[m[5].toLowerCase()]; dd = +m[4]; prec = 'd'; }
      else if (m[7]) { y = +m[9]; mo = MON[m[7].toLowerCase()]; prec = 'm'; }
      else { y = +m[10]; }
      if (y < 1000 || y > 2040 || mo < 0 || mo > 11) continue;
      out.push({ t: Date.UTC(y, mo, dd), y: y, prec: prec, at: m.index });
    }
    return out;
  }
  function iso(ms, prec) { var x = new Date(ms); var s = String(x.getUTCFullYear()); if (prec === 'y') return s; s += '-' + ('0' + (x.getUTCMonth() + 1)).slice(-2); if (prec === 'm') return s; return s + '-' + ('0' + x.getUTCDate()).slice(-2); }
  var SKIPQ = '.ghf-ui,header,nav,footer,script,style,noscript,#cedwyn-guestbook,#ghf-agent-footer,[data-for-agents],.cw-gm,.cw-vh-bar,.cwl-pv,.cwl-rm,.cwl-back,.cwl-more,.cwl-gt,.cwl-gh,[aria-hidden=true],template';
  function content() {
    var c = d.querySelector('main,[role=main]') || d.querySelector('article') || d.querySelector('#content,.content,#main');
    if (c && (c.textContent || '').length > 300) return c;
    var best = null, bl = 0, k = d.body ? d.body.children : [];
    for (var i = 0; i < k.length; i++) {
      var e = k[i]; if (e.matches(SKIPQ) || /^(SCRIPT|STYLE|LINK)$/.test(e.tagName)) continue;
      var l = (e.textContent || '').length; if (l > bl) { bl = l; best = e; }
    }
    return best || d.body;
  }
  function clean(s) { return (s || '').replace(/\s+/g, ' ').trim(); }
  function idFor(e, n) { if (!e.id) e.id = 'cw-g-' + n; return '#' + e.id; }
  function heading(e, root) {   /* nearest heading before e (in document order) inside root */
    var w = d.createTreeWalker(root, NodeFilter.SHOW_ELEMENT, null), last = '', n;
    while ((n = w.nextNode())) { if (n === e || n.contains(e)) { if (n === e) break; continue; } if (/^H[1-4]$/.test(n.tagName) && !n.closest(SKIPQ)) last = clean(n.textContent).slice(0, 48); if (n.compareDocumentPosition(e) & 2) break; }
    return last;
  }
  var STRENGTH = [[/family testimony|testimony/i, 'Family testimony'], [/not yet confirmed|not checked|to be confirmed/i, 'Not yet confirmed'], [/working (?:theory|hypothesis)|hypothes[ie]s/i, 'Working hypothesis'], [/\brecord\b|catalogue|register|deed|minute/i, 'Record']];
  function strength(s) { for (var i = 0; i < STRENGTH.length; i++) if (STRENGTH[i][0].test(s)) return STRENGTH[i][1]; return 'Text'; }
  function domData() {
    var root = content(); if (!root) return null;
    /* 1) repeated items that each carry a date: list rows, table rows, cards */
    var sig = {}, q = root.querySelectorAll('li,tr,article,section,details,.card,[class*=card],[class*=item],[class*=entry],[class*=row]'), i;
    for (i = 0; i < q.length && i < 4000; i++) {
      var e = q[i]; if (e.closest(SKIPQ)) continue;
      var tx = clean(e.textContent); if (tx.length < 8 || tx.length > 1600) continue;
      var ds = dates(tx, 1); if (!ds.length) continue;
      var k = e.tagName + '.' + (typeof e.className === 'string' ? e.className.split(/\s+/)[0] : '');
      (sig[k] = sig[k] || []).push([e, ds[0], tx]);
    }
    var bestK = null, bn = 0; for (var k2 in sig) if (sig[k2].length > bn) { bn = sig[k2].length; bestK = k2; }
    var pts = [], n = 0;
    if (bn >= 6) {
      sig[bestK].forEach(function (r) {
        var e = r[0], a = e.querySelector('a[href]:not([href^="javascript"])'), h = e.querySelector('h1,h2,h3,h4,h5,strong,b,a');
        var lab = clean(h ? h.textContent : r[2]).slice(0, 110) || r[2].slice(0, 110);
        var tag = e.querySelector('[class*=tag],[class*=badge],[class*=chip],[class*=status],[class*=label],[class*=kind],[class*=type]');
        var ct = tag ? clean(tag.textContent).slice(0, 28) : '';
        pts.push({ x: r[1].t, xp: r[1].prec, y: heading(e, root) || ct || 'Items', c: ct || strength(r[2]), l: lab, h: a ? a.getAttribute('href') : idFor(e, ++n) });
      });
      return pack(pts, 'Date', 'Section', 'Kind');
    }
    /* 2) prose: every date the text mentions, by section, coloured by how the passage presents it */
    var blocks = root.querySelectorAll('p,li,td,dd,blockquote,h2,h3,h4,figcaption'), seen = {};
    for (i = 0; i < blocks.length && pts.length < 600; i++) {
      var b = blocks[i]; if (b.closest(SKIPQ) || (b.tagName === 'LI' && b.querySelector('p,li'))) continue;
      var s = clean(b.textContent); if (s.length < 6) continue;
      var ds2 = dates(s, 8), hd = null;
      for (var j = 0; j < ds2.length; j++) {
        var kk = ds2[j].y + '|' + i; if (seen[kk]) continue; seen[kk] = 1;
        if (hd === null) hd = heading(b, root) || 'Text';
        var a0 = Math.max(0, s.lastIndexOf('.', ds2[j].at) + 1), z = s.indexOf('. ', ds2[j].at); if (z < 0) z = s.length;
        var sent = s.slice(a0, z + 1).trim(); if (sent.length > 140) sent = sent.slice(0, 137) + '…';
        pts.push({ x: ds2[j].t, xp: ds2[j].prec, y: hd, c: strength(s), l: sent, h: idFor(b, ++n) });
      }
    }
    if (pts.length >= 3) return pack(pts, 'Date mentioned', 'Section', 'Presented as');
    /* 3) no dates: sections by position and length */
    var hs = root.querySelectorAll('h2,h3'), sec = [];
    for (i = 0; i < hs.length; i++) {
      var hh = hs[i]; if (hh.closest(SKIPQ)) continue;
      var words = 0, sib = hh.nextElementSibling; while (sib && !/^H[1-3]$/.test(sib.tagName)) { words += clean(sib.textContent).split(' ').length; sib = sib.nextElementSibling; }
      sec.push({ x: sec.length + 1, y: words, c: hh.tagName === 'H2' ? 'Section' : 'Subsection', l: clean(hh.textContent).slice(0, 110), h: idFor(hh, ++n) });
    }
    if (sec.length >= 2) return { x: { label: 'Order on the page', type: 'num' }, y: { label: 'Words', type: 'num' }, c: { label: 'Level', cats: ['Section', 'Subsection'] }, p: sec.map(function (s) { return [s.x, s.y, s.c === 'Section' ? 0 : 1, s.l, s.h]; }) };
    return null;
  }
  function top(arr, k, max) { var c = {}; arr.forEach(function (p) { c[p[k]] = (c[p[k]] || 0) + 1; }); var ks = Object.keys(c).sort(function (a, b) { return c[b] - c[a]; }); if (ks.length > max) { ks = ks.slice(0, max - 1); ks.push('Other'); } return ks; }
  function pack(pts, xl, yl, cl) {
    var ys = top(pts, 'y', 12), cs = top(pts, 'c', 8);
    return { x: { label: xl, type: 'date' }, y: { label: yl, type: 'cat', cats: ys }, c: { label: cl, cats: cs }, p: pts.map(function (p) { var yi = ys.indexOf(p.y), ci = cs.indexOf(p.c); return [iso(p.x, p.xp), yi < 0 ? ys.length - 1 : yi, ci < 0 ? cs.length - 1 : ci, p.l, p.h]; }) };
  }

  /* ---------------- scatter renderer (inline SVG) ---------------- */
  var PAL = ['#2f7ed8', '#e4572e', '#29a36a', '#c9a227', '#8e5ad8', '#d6457b', '#17a2b8', '#7a8a99'];
  var NPAL = ['#6aa8ff', '#ff7a59', '#4cd18f', '#f2c94c', '#b48cff', '#ff6fa3', '#4dd0e1', '#a3b1bf'];
  function xv(v) { if (typeof v === 'number') return v; var p = String(v).split('-'); return Date.UTC(+p[0], (+p[1] || 1) - 1, +p[2] || 1); }
  function hsh(s) { var h = 0; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0; return ((h >>> 0) % 1000) / 1000; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var MS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function fmt(ms, step) { var x = new Date(ms); if (step < 3e9) return x.getUTCDate() + ' ' + MS[x.getUTCMonth()]; if (step < 3.2e10) return MS[x.getUTCMonth()] + ' ' + String(x.getUTCFullYear()).slice(2); return String(x.getUTCFullYear()); }
  /* 1.2.3 (30 Oct 2026): long category names on the left axis wrap onto two lines that fit the label column (11 px type,
     about 6 px a character) instead of running off the left edge at 390 px; the full name rides in a <title>. - Sion's Tab agent */
  function wrap(s, n) {
    if (s.length <= n) return [s];
    var w = s.split(' '), a = '', k = 0;
    while (k < w.length && (a ? a.length + 1 : 0) + w[k].length <= n) { a += (a ? ' ' : '') + w[k]; k++; }
    if (!a) { a = s.slice(0, n - 1) + '-'; w = [s.slice(n - 1)]; k = 0; }
    var b = w.slice(k).join(' ');
    return [a, b.length > n ? b.slice(0, n - 1) + '…' : b];
  }
  function render(host, data, info, legend, sub) {
    var W = Math.max(320, Math.min(host.clientWidth || 360, 1100)), cat = data.y.type === 'cat', cats = cat ? data.y.cats : null;
    var padL = cat ? Math.min(132, Math.round(W * 0.32)) : 44, padR = 12, padT = 10, padB = 36;
    var band = cat ? Math.max(30, Math.min(54, 520 / cats.length)) : 0;
    var H = cat ? padT + padB + band * cats.length : Math.max(260, Math.min(520, Math.round(W * 0.75)));
    var P = data.p, n = P.length, xs = P.map(function (p) { return xv(p[0]); });
    var sorted = xs.slice().sort(function (a, b) { return a - b; }), mn = sorted[0], mx = sorted[n - 1];
    var dateX = data.x.type === 'date', rank = false;
    if (dateX && n > 8) { var q10 = sorted[Math.floor(n * 0.1)], q90 = sorted[Math.floor(n * 0.9)]; if (mx > mn && (q90 - q10) < (mx - mn) * 0.12) rank = true; }
    var order = {}; if (rank) sorted.forEach(function (v, i) { if (order[v] == null) order[v] = i; });
    var pw = W - padL - padR, ph = H - padT - padB;
    function X(v) { if (rank) return padL + (n > 1 ? order[v] / (n - 1) : 0.5) * pw; return padL + (mx > mn ? (v - mn) / (mx - mn) : 0.5) * pw; }
    var ys = P.map(function (p) { return +p[1]; }), ymn = Math.min.apply(null, ys), ymx = Math.max.apply(null, ys);
    function Y(p, i) { if (cat) return padT + band * (+p[1]) + band * (0.18 + 0.64 * hsh(String(p[3]) + i)); return padT + ph - (ymx > ymn ? (+p[1] - ymn) / (ymx - ymn) : 0.5) * ph; }
    var pal = (data.c && data.c.colors) || (night() ? NPAL : PAL), s = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(data.y.label + ' by ' + data.x.label) + '">';
    if (cat) cats.forEach(function (c, i) { var y = padT + band * i, L = wrap(String(c), Math.max(8, Math.floor((padL - 10) / 6.1))); s += '<line class="ax" x1="' + padL + '" x2="' + (W - padR) + '" y1="' + y + '" y2="' + y + '"/><text x="' + (padL - 6) + '" y="' + (y + band / 2 + (L.length > 1 ? -2 : 4)) + '" text-anchor="end"><title>' + esc(c) + '</title>' + L.map(function (l, k) { return '<tspan x="' + (padL - 6) + '"' + (k ? ' dy="12"' : '') + '>' + esc(l) + '</tspan>'; }).join('') + '</text>'; });
    else for (var g = 0; g <= 4; g++) { var yv = ymn + (ymx - ymn) * g / 4, yy = padT + ph - ph * g / 4; s += '<line class="ax" x1="' + padL + '" x2="' + (W - padR) + '" y1="' + yy + '" y2="' + yy + '"/><text x="' + (padL - 6) + '" y="' + (yy + 4) + '" text-anchor="end">' + (Math.round(yv * 10) / 10) + '</text>'; }
    s += '<line class="ax" x1="' + padL + '" x2="' + (W - padR) + '" y1="' + (H - padB) + '" y2="' + (H - padB) + '"/>';
    var ticks = Math.max(2, Math.min(6, Math.floor(pw / 70)));
    for (var k = 0; k <= ticks; k++) {
      var tv, tx; if (rank) { tv = sorted[Math.round((n - 1) * k / ticks)]; tx = X(tv); } else { tv = mn + (mx - mn) * k / ticks; tx = padL + pw * k / ticks; }
      var lab = dateX ? fmt(tv, rank ? Math.abs(tv - (k > 0 ? sorted[Math.round((n - 1) * (k - 1) / ticks)] : tv)) || (mx - mn) : (mx - mn) / ticks) : String(Math.round(tv * 10) / 10);
      s += '<text x="' + tx + '" y="' + (H - padB + 15) + '" text-anchor="' + (k === 0 ? 'start' : k === ticks ? 'end' : 'middle') + '">' + esc(lab) + '</text>';
    }
    s += '<text x="' + (padL + pw / 2) + '" y="' + (H - 4) + '" text-anchor="middle">' + esc(data.x.label + (rank ? ' (' + t('rank') + ')' : '')) + '</text>';
    for (var i = 0; i < n; i++) s += '<circle class="pt" data-i="' + i + '" cx="' + X(xs[i]).toFixed(1) + '" cy="' + Y(P[i], i).toFixed(1) + '" r="' + (n > 400 ? 4 : 5.5) + '" fill="' + pal[(+P[i][2] || 0) % pal.length] + '" fill-opacity=".85"><title>' + esc(P[i][3]) + '</title></circle>';
    host.innerHTML = s + '</svg>';
    legend.innerHTML = ''; (data.c && data.c.cats || []).forEach(function (c, i) { var sp = mk('span'); sp.innerHTML = '<i style="background:' + pal[i % pal.length] + '"></i>'; sp.appendChild(d.createTextNode(c)); legend.appendChild(sp); });
    sub.textContent = data.y.label + ' \u00d7 ' + data.x.label + ' \u00b7 ' + n + ' ' + t('pts');
    var svg = host.firstChild, sel = null;
    svg.addEventListener('click', function (e) {
      var c = e.target.closest && e.target.closest('.pt');
      if (!c) { var r = svg.getBoundingClientRect(), sx = W / r.width, ex = (e.clientX - r.left) * sx, ey = (e.clientY - r.top) * sx, bd = 1e9; [].forEach.call(svg.querySelectorAll('.pt'), function (p) { var dx = p.cx.baseVal.value - ex, dy = p.cy.baseVal.value - ey, dd = dx * dx + dy * dy; if (dd < bd) { bd = dd; c = p; } }); if (bd > 900) c = null; }
      if (!c) return;
      if (sel) sel.classList.remove('sel'); sel = c; c.classList.add('sel');
      var p = P[+c.getAttribute('data-i')]; info.textContent = '';
      info.appendChild(mk('b', null, p[3]));
      info.appendChild(mk('span', null, (dateX ? p[0] : data.x.label + ' ' + p[0]) + ' \u00b7 ' + (cat ? cats[+p[1]] : data.y.label + ' ' + p[1]) + (data.c && data.c.cats ? ' \u00b7 ' + data.c.cats[+p[2]] : '')));
      if (p[4]) { info.appendChild(d.createTextNode(' ')); var a = mk('a', null, t('open') + ' \u203a'); a.href = p[4]; a.onclick = function () { if (p[4].charAt(0) === '#') { closeModal(); expandTo(p[4]); } }; info.appendChild(a); }
    });
  }

  /* ---------------- modal ---------------- */
  var M = null, opener = null, sets = {}, cur = null;
  var PP = null; function panel() { var e = d.getElementById('cedwyn-parcel-panel'); if (e) PP = e; return PP; }   /* 1.2.4 */
  function build() {
    M = mk('div', 'cw-gm' + (RM ? ' cw-rm' : '')); M.setAttribute('role', 'dialog'); M.setAttribute('aria-modal', 'true'); M.setAttribute('aria-labelledby', 'cw-gm-t'); M.setAttribute('data-no-translate', '');
    M.innerHTML = '<div class="cw-gm-h"><h2 id="cw-gm-t"></h2><button type="button" class="cw-gm-x">\u2191</button></div><div class="cw-gm-tabs" hidden></div><div class="cw-gm-lg"></div><div class="cw-gm-b"></div><div class="cw-gm-i" aria-live="polite"></div><div class="cw-gm-sp"></div><div class="cw-gm-f"></div>';
    var x = M.querySelector('.cw-gm-x'); x.setAttribute('aria-label', t('closeg')); x.onclick = closeModal;
    var y0 = null; M.addEventListener('touchstart', function (e) { y0 = e.touches[0].clientY; }, { passive: true });
    M.addEventListener('touchend', function (e) { if (y0 != null && e.changedTouches[0].clientY - y0 < -70 && !e.target.closest('.cw-gm-b svg')) closeModal(); y0 = null; }, { passive: true });
    d.addEventListener('keydown', function (e) { if (M.classList.contains('cw-on') && e.key === 'Escape') closeModal(); });
    d.body.appendChild(M);
  }
  function title() { var h = d.querySelector('.ghf-v2-name b, .ghf-v2-chain [aria-current]'); var tt = clean((h && h.textContent) || (d.querySelector('h1') || {}).textContent || d.title).split(/[|·–—]/)[0].trim(); return tt.slice(0, 60); }
  function show(which) {
    cur = which; var data = sets[which], body = M.querySelector('.cw-gm-b'), info = M.querySelector('.cw-gm-i');
    [].forEach.call(M.querySelectorAll('.cw-gm-tab'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-k') === which)); });
    var hh = M.querySelector('#cw-gm-t'), ht = which === 'story' ? t('story') : ((data && data.title) || (sets.sec && sets.sec.title) || null);
    if (ht && hh.firstChild && hh.firstChild.nodeType === 3) hh.firstChild.nodeValue = ht;
    info.hidden = false;
    if (which === 'story') {   /* 1.2.4: the parcel-story panel, moved (not copied) into the modal; the other tabs replace the body */
      var pn = panel(); body.textContent = ''; M.querySelector('.cw-gm-lg').innerHTML = ''; info.textContent = ''; info.hidden = true;
      var sm = hh.querySelector('small'); if (sm) sm.textContent = '';
      if (pn) { pn.classList.add('cw-gm-pp'); body.appendChild(pn); }
      return;
    }
    info.textContent = t('tap');
    if (!data || !data.p || data.p.length < 1) { body.innerHTML = '<p style="padding:16px">' + esc(t('none')) + '</p>'; M.querySelector('.cw-gm-lg').innerHTML = ''; return; }
    render(body, data, info, M.querySelector('.cw-gm-lg'), M.querySelector('#cw-gm-t small') || (function () { var s = mk('small'); M.querySelector('#cw-gm-t').appendChild(s); return s; })());
  }
  function openModal(from) {
    opener = from || null; if (!M) build();
    M.classList.toggle('cw-night', night());
    var h = M.querySelector('#cw-gm-t'); h.textContent = (data0 && data0.title) || title(); h.appendChild(mk('small', null, t('loading')));
    var f = M.querySelector('.cw-gm-f'); f.textContent = ''; if (ebook && ebook.href) { var a = mk('a', null, (ebook.text || 'E-books') + ' \u203a'); a.href = ebook.href; f.appendChild(a); } else f.hidden = true;
    de.classList.add('cw-gm-lock'); M.style.visibility = 'visible';
    requestAnimationFrame(function () { requestAnimationFrame(function () { M.classList.add('cw-on'); M.querySelector('.cw-gm-x').focus({ preventScroll: true }); }); });
    loadSets(function () {
      var tabs = M.querySelector('.cw-gm-tabs'); tabs.textContent = '';
      var ks = ['inst', 'sec', 'page'].filter(function (k) { return sets[k] && sets[k].p && sets[k].p.length >= 3; });
      if (panel()) ks.push('story');
      if (ks.length > 1) { tabs.hidden = false; ks.forEach(function (k) { var b = mk('button', 'cw-gm-tab', t(k)); b.type = 'button'; b.setAttribute('data-k', k); b.onclick = function () { show(k); }; tabs.appendChild(b); }); } else tabs.hidden = true;
      if (sets.sec && sets.sec.title) { h.firstChild.nodeValue = sets.sec.title; }
      show(ks[0] || 'page');
    });
  }
  var data0 = null, loaded = false;
  function loadSets(cb) {
    if (loaded) return cb(); loaded = true;
    try { sets.page = domData(); } catch (e) { sets.page = null; }
    var done = false, to = setTimeout(function () { if (!done) { done = true; cb(); } }, 4000);
    function gj(a) { return fetch('/_cedwyn/graph/' + a + '.json?v=' + VER, { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }
    var jobs = [gj(AREA).then(function (j) { if (j && j.p) sets.sec = j; })];
    if (AREA === 'research' && panel()) jobs.push(gj('parcels').then(function (j) { if (j && j.p) sets.inst = j; }));   /* 1.2.4: on /research/ only, the parcel panel's own data (other webapps keep plotting only their own database; owner rule 30 Oct 2026) */
    Promise.all(jobs).catch(function () {}).then(function () { if (!done) { done = true; clearTimeout(to); cb(); } });
  }
  function closeModal() {
    if (!M || !M.classList.contains('cw-on')) return;
    M.classList.remove('cw-on'); de.classList.remove('cw-gm-lock');
    setTimeout(function () { if (!M.classList.contains('cw-on')) M.style.visibility = 'hidden'; }, RM ? 0 : 260);
    if (opener && opener.focus) opener.focus({ preventScroll: true });
  }
  window.__cwGraph.open = function () { openModal(null); }; window.__cwGraph.close = closeModal; window.__cwGraph.dom = domData;

  /* ---------------- 100vh clip + Read more ---------------- */
  var NOCLIP = /^\/(?:(?:wales|argentina)\/)?(?:dartboard|documentary|movie|story|academy|wayback|legal|terms|privacy|cookies|chess|arcade|maps|chat|app|infographic|familytree|terrain|thousand-cuts|shop|ebooks|subscribe|nft-art|db|parcels|cyberspace|estate|directory|patagonia)(?:\/|$)/;
  var C = null, Hc = 0, hidden = [], vbar = null, more = null, moreN = 0, moreI = 0, busyMore = false;
  function bgOf(e) { while (e && e.nodeType === 1) { var c = getComputedStyle(e).backgroundColor, m = c && c.match(/rgba?\(([^)]+)\)/); if (m) { var p = m[1].split(','); if (p.length < 4 || parseFloat(p[3]) > 0.5) return 'rgb(' + p.slice(0, 3).join(',') + ')'; } e = e.parentElement; } return night() ? '#111' : '#fff'; }
  function unclampV2(root) { [].forEach.call(root.querySelectorAll('.cw-ctl'), function (e) { e.remove(); }); [].forEach.call(root.querySelectorAll('.cw-c,.cw-h,.cw-o'), function (e) { e.classList.remove('cw-c', 'cw-h', 'cw-o'); }); }
  function afterEls(c) { var out = [], e = c; while (e && e !== d.body) { var s = e.nextElementSibling; while (s) { if (!s.matches('.ghf-v2,.ghf-v2-btn,script,style,link,.cw-gm,.cw-vh-bar') && /^(static|relative)$/.test(getComputedStyle(s).position) && s.getClientRects().length) out.push(s); s = s.nextElementSibling; } e = e.parentElement; } return out; }
  function setH(h) { Hc = Math.max(160, Math.round(h)); C.style.setProperty('max-height', Hc + 'px', 'important'); }
  function fits() { return C.scrollHeight <= Hc + 4 && !(more && moreI < moreN); }
  function unclip() {
    if (!C) return; C.classList.remove('cw-vh-clip'); C.style.removeProperty('max-height');
    hidden.forEach(function (e) { e.classList.remove('cw-vh-hide'); e.style.removeProperty('display'); }); hidden = [];
    if (vbar) vbar.remove(); vbar = null; de.classList.remove('cw-vh', 'cw-vh-lock'); C = null;
  }
  function loadMore(cb) {
    if (!more || moreI >= moreN) return cb && cb(false); if (busyMore) return cb && setTimeout(function () { cb(false); }, 150); busyMore = true;
    var url = more.getAttribute('data-cw-more') + (++moreI) + '.json';
    fetch(url, { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
      if (j && j.html) { var tmp = d.createElement('div'); tmp.innerHTML = j.html; while (tmp.firstChild) more.parentNode.insertBefore(tmp.firstChild, more); }
      else moreI = moreN;
    }).catch(function () { moreI = moreN; }).then(function () { busyMore = false; if (moreI >= moreN) { var nsc = more.parentNode && more.parentNode.querySelector('.cw-more-noscript'); if (nsc) nsc.remove(); } cb && cb(true); });
  }
  function step() {
    if (!C) return;
    opened = true; de.classList.remove('cw-vh-lock'); var next = Hc + Math.round(innerHeight * 0.85);
    function go() {
      setH(next); if (C.scrollHeight <= Hc + 4 && !(more && moreI < moreN)) unclip();
      else if (vbar) vbar.querySelector('button').setAttribute('aria-expanded', 'true');
    }
    if (more && moreI < moreN && C.scrollHeight < next + innerHeight) loadMore(go); else go();
  }
  function expandTo(hash) {
    if (!C || !hash || hash.length < 2) return;
    var id; try { id = decodeURIComponent(hash.slice(1)); } catch (e) { id = hash.slice(1); }
    var tg = d.getElementById(id) || d.querySelector('[name="' + id.replace(/"/g, '') + '"]');
    if (!tg) { if (more && moreI < moreN) loadMore(function () { expandTo(hash); }); return; }
    if (!C.contains(tg)) return;
    var need = tg.getBoundingClientRect().top - C.getBoundingClientRect().top + innerHeight * 0.6;
    if (need > Hc) { opened = true; de.classList.remove('cw-vh-lock'); setH(need); if (C.scrollHeight <= Hc + 4 && !(more && moreI < moreN)) unclip(); }
    setTimeout(function () { try { tg.scrollIntoView({ block: 'start' }); } catch (e) {} }, 30);
  }
  function clip() {
    if (NOCLIP.test(location.pathname) || de.hasAttribute('data-cw-noclip') || location.search.indexOf('full=1') >= 0) return;
    var c = content(); if (!c || c === d.body || c.closest('.ghf-ui')) return;
    while (c.parentElement && c.parentElement !== d.body && !c.parentElement.matches('.ghf-ui') && c.getBoundingClientRect().top + scrollY > innerHeight * 0.45) c = c.parentElement;
    if (c.querySelector('canvas,video,iframe,[data-cw-noclip],form input[type=email]') && (c.textContent || '').length < 4000) return;
    if ((c.textContent || '').replace(/\s+/g, ' ').length < 900) return;
    more = c.querySelector('[data-cw-more]'); moreN = more ? +more.getAttribute('data-cw-more-n') || 0 : 0;
    if (de.scrollHeight <= innerHeight + 2 && !moreN) return;
    C = c; unclampV2(C); C.classList.add('cw-vh-clip'); de.classList.add('cw-vh');
    hidden = afterEls(C); hidden.forEach(function (e) { e.classList.add('cw-vh-hide'); e.style.setProperty('display', 'none', 'important'); });
    vbar = mk('div', 'cw-vh-bar'); var b = mk('button', 'cw-vh-btn', t('more')); b.type = 'button'; b.setAttribute('aria-expanded', 'false'); b.onclick = step; vbar.appendChild(b);
    C.parentNode.insertBefore(vbar, C.nextSibling);
    var bg = bgOf(C); vbar.style.setProperty('--cw-vh-bg', bg); var fg = getComputedStyle(C).color; vbar.style.setProperty('--cw-vh-fg', fg);
    var top = C.getBoundingClientRect().top + scrollY;
    setH(innerHeight - top - vbar.offsetHeight);
    for (var k = 0; k < 3 && de.scrollHeight > innerHeight + 1; k++) setH(Hc - (de.scrollHeight - innerHeight));
    if (fits()) { unclip(); return; }
    [].forEach.call(C.querySelectorAll('input[type=search],input[type=text],select'), function (inp) { inp.addEventListener('focus', function full() { inp.removeEventListener('focus', full); (function all() { if (more && moreI < moreN) loadMore(all); else unclip(); })(); }); });
    if (location.hash) expandTo(location.hash);
    addEventListener('hashchange', function () { expandTo(location.hash); });
    d.addEventListener('click', function (e) { var a = e.target.closest && e.target.closest('a[href^="#"]'); if (a && C) expandTo(a.getAttribute('href')); }, true);
    [600, 1500, 3000, 6000].forEach(function (ms) { setTimeout(refit, ms); });
    try { var mo = new MutationObserver(function () { clearTimeout(rf); rf = setTimeout(refit, 120); }); mo.observe(d.body, { childList: true }); setTimeout(function () { mo.disconnect(); }, 9000); } catch (e) {}
  }
  var rf = 0, opened = false;
  function refit() {   /* late scripts add blocks below the text (panels, guestbook): keep them folded and the first view at 100vh */
    if (!C || opened) return; unclampV2(C);
    afterEls(C).forEach(function (e) { if (hidden.indexOf(e) < 0) { e.classList.add('cw-vh-hide'); e.style.setProperty('display', 'none', 'important'); hidden.push(e); } });
    for (var k = 0; k < 3 && de.scrollHeight > innerHeight + 1 && scrollY < 5; k++) setH(Hc - (de.scrollHeight - innerHeight));
    if (de.scrollHeight > innerHeight + 1 && scrollY < 5) de.classList.add('cw-vh-lock');   /* only a stray off-screen panel is left below: no scroll until Read more */
  }

  function autoMore() {   /* 1.0.2: no clip; chunked long pages load their remaining blocks as the reader scrolls near the end */
    more = d.querySelector('[data-cw-more]'); moreN = more ? +more.getAttribute('data-cw-more-n') || 0 : 0; if (!moreN) return;
    function pull() { if (moreI < moreN) loadMore(function () { if (moreI < moreN && more.getBoundingClientRect().top < innerHeight * 1.6) pull(); }); }
    try { var io = new IntersectionObserver(function (en) { if (en[0].isIntersecting) pull(); }, { rootMargin: '0px 0px 500px 0px' }); io.observe(more); } catch (e) { pull(); }
    function all(cb) { if (moreI < moreN) loadMore(function () { all(cb); }); else cb && cb(); }
    function hashGo() { var h = location.hash; if (!h || h.length < 2) return; var id; try { id = decodeURIComponent(h.slice(1)); } catch (e) { id = h.slice(1); } if (!d.getElementById(id)) all(function () { var tg = d.getElementById(id); if (tg) tg.scrollIntoView({ block: 'start' }); }); }
    hashGo(); addEventListener('hashchange', hashGo);
    d.addEventListener('focusin', function f(e) { if (e.target.matches && e.target.matches('input[type=search],input[type=text],select')) { d.removeEventListener('focusin', f); all(); } });
    addEventListener('beforeprint', function () { all(); });
    window.__cwGraph.loadAll = all;
  }

  /* ---------------- card levels 1.1.0 (02:30 GMT 30 Oct 2026): text pages become cards (header + 4 lines + Read more);
     Read more walks into a deeper level (the level left zooms past the screen edges, the new one zooms in), Back walks out. ---- */
  var LV = null, RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  function LV_TITLE() { var h1 = d.querySelector('main h1,article h1,h1'); return h1 ? clean(h1.textContent).split(/ [—–:|] /)[0].slice(0, 60) : ''; }
  function lvTxt(k) { var L = { en: ['Back', 'Read more', 'More in this section', 'Top of the page', 'The full list'], cy: ['Yn ôl', 'Darllen mwy', 'Rhagor yn yr adran hon', 'Brig y dudalen', 'Y rhestr lawn'], es: ['Volver', 'Leer más', 'Más en esta sección', 'Inicio de la página', 'La lista completa'] }; return (L[lg()] || L.en)[k]; }
  function isH(n) { return n && n.nodeType === 1 && /^H[2-4]$/.test(n.tagName) && !n.closest(SKIPQ) && !n.classList.contains('vh'); }
  function slug(s) { return clean(s).toLowerCase().replace(/[^a-z0-9\u00c0-\u024f]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 's'; }
  function flowParent(root) {
    var cnt = new Map(), best = null, bn = 0;
    [].forEach.call(root.querySelectorAll('h2,h3,h4'), function (h) { if (!isH(h)) return; var p = h.parentElement; if (p.tagName === 'SUMMARY' || p.tagName === 'A') return; cnt.set(p, (cnt.get(p) || 0) + 1); });
    cnt.forEach(function (n, p) { if (n > bn) { bn = n; best = p; } });
    return bn >= 3 ? { p: best, n: bn } : null;
  }
  function blockParent(root) {   /* pages built from <details>/<section> blocks, one heading each */
    var best = null, bn = 0;
    [root].concat([].slice.call(root.querySelectorAll('*'))).forEach(function (p) {
      if (p.children.length < 3 || p.closest(SKIPQ)) return; var n = 0;
      [].forEach.call(p.children, function (k) { if (/^(DETAILS|SECTION|ARTICLE)$/.test(k.tagName) && k.querySelector('h2,h3,h4,summary')) n++; });
      if (n > bn) { bn = n; best = p; }
    });
    return bn >= 3 ? { p: best, n: bn } : null;
  }
  var BLK = 'p,li,td,th,div,h1,h2,h3,h4,h5,h6,dt,dd,tr,section,article,blockquote,ul,ol,table,figcaption,summary,details,pre';
  function spaced(root) {   /* text with a space wherever one block ends and the next begins */
    var w = d.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), n, out = '', last = null, len = 0;
    while ((n = w.nextNode()) && len < 1600) { var p = n.parentElement; if (!p || p.closest('script,style,.cwl-pv,.cwl-rm,[aria-hidden=true],.vh')) continue; var b = p.closest(BLK); out += (b !== last ? ' ' : '') + n.nodeValue; last = b; len = out.length; }
    return clean(out);
  }
  function mkSec(h, lvl, parent) {
    var s = { h: h, lvl: lvl, kids: [], body: [], parent: parent, el: null, key: '' };
    parent.kids.push(s); return s;
  }
  function materialize(s, used, dp) {
    dp = dp || 1;
    var el = mk('section', 'cwl-s'); s.el = el; el._cwl = s;
    var base = (s.h.id || slug(s.h.textContent)), k = base, i = 2; while (used[k]) k = base + '-' + (i++); used[k] = 1; s.key = k; el.setAttribute('data-cwl', k);
    s.h.parentNode.insertBefore(el, s.h); el.appendChild(s.h); s.h.classList.add('cwl-h');
    var pv = mk('p', 'cwl-pv'); pv.setAttribute('aria-hidden', 'true'); el.appendChild(pv);
    var body = mk('div', 'cwl-body'); el.appendChild(body); s.body.forEach(function (n) { body.appendChild(n); });
    var rm = mk('span', 'cwl-rm', lvTxt(1)); rm.setAttribute('aria-hidden', 'true');
    s.kids.forEach(function (c) { materialize(c, used, dp + 1); el.appendChild(c.el); });
    if (!s.kids.length && dp < 4) subSecs(s, body, used, dp);
    el.appendChild(rm);
    var txt = spaced(body); if (txt.length < 60 && s.kids.length) txt = clean(s.kids.map(function (c) { return c.h.textContent + '. ' + spaced(c.el.querySelector('.cwl-body')); }).join(' '));
    var ht = clean(s.h.textContent); if (ht && txt.toLowerCase().indexOf(ht.toLowerCase()) === 0) txt = txt.slice(ht.length).replace(/^[\s:·.—-]+/, '');
    if (GEN[ht.toLowerCase()] > 2 && txt.length > 20) { var m = txt.match(/^(.{20,90}?)(?:[.;!?](?:\s|$)|$)/); var gt = mk('div', 'cwl-gt', (m ? m[1] : txt.slice(0, 80)) + ' '); gt.appendChild(mk('span', 'cwl-gk', ht)); gt.setAttribute('aria-hidden', 'true'); el.insertBefore(gt, pv); el.classList.add('cwl-generic'); txt = txt.slice(m ? m[0].length : 80).trim() || txt; }
    pv.textContent = txt.slice(0, 420);
  }
  var GEN = {};
  function countGen(P) { GEN = {}; [].forEach.call(P.querySelectorAll('h2,h3,h4'), function (h) { var k = clean(h.textContent).toLowerCase(); GEN[k] = (GEN[k] || 0) + 1; }); }
  function buildFlow(P) {
    countGen(P);
    var root = { kids: [], body: [], lvl: 1, el: P, key: '' }, stack = [root], top = 9;
    [].forEach.call(P.children, function (n) { if (isH(n)) top = Math.min(top, +n.tagName[1]); });
    [].slice.call(P.childNodes).forEach(function (n) {
      var L = isH(n) ? +n.tagName[1] : 0;
      if (L && L >= top) { while (stack.length > 1 && stack[stack.length - 1].lvl >= L) stack.pop(); stack.push(mkSec(n, L, stack[stack.length - 1])); }
      else if (stack.length > 1) stack[stack.length - 1].body.push(n);
    });
    if (root.kids.length < 2) return null;
    /* a long register or list before the first heading becomes its own first card, so the cards are not buried under it */
    var intro = [].slice.call(P.childNodes).filter(function (n) { return root.kids[0].h.compareDocumentPosition(n) & 2; }), acc = 0, cut = -1;
    for (var i = 0; i < intro.length; i++) { var n = intro[i], L = clean(n.textContent).length; if (n.nodeType === 1 && (L > 1500 || /^(TABLE|OL|UL|DL)$/.test(n.tagName) && L > 600) && acc > 0 || acc > 900) { cut = i; break; } acc += L; }
    if (cut >= 0 && clean(intro.slice(cut).map(function (n) { return n.textContent; }).join(' ')).length > 2500) {
      var gh = mk('h2', 'cwl-gh', LV_TITLE() || lvTxt(4)); P.insertBefore(gh, intro[cut]);
      var gs = { h: gh, lvl: top, kids: [], body: intro.slice(cut), parent: root, el: null, key: '' }; root.kids.unshift(gs);
    }
    var used = {}; root.kids.forEach(function (s) { materialize(s, used); });
    return root;
  }
  function looseSecs(nodes, root, top, first) {   /* loose nodes between blocks: a heading starts a card; a long run with no heading becomes one card */
    var segs = [[]]; nodes.forEach(function (n) { if (isH(n)) segs.push([n]); else segs[segs.length - 1].push(n); });
    var out = [];
    segs.forEach(function (sg, k) {
      if (!sg.length) return;
      if (k > 0) { out.push({ h: sg[0], lvl: top, kids: [], body: sg.slice(1), parent: root, el: null, key: '' }); return; }
      var acc = 0, cut = -1;
      for (var i = 0; i < sg.length; i++) { var n = sg[i], L = clean(n.textContent).length; if (n.nodeType === 1 && ((L > 1500 || /^(TABLE|OL|UL|DL)$/.test(n.tagName) && L > 600) && (acc > 0 || !first) || acc > 900)) { cut = i; break; } acc += L; }
      if (cut < 0 || clean(sg.slice(cut).map(function (n) { return n.textContent; }).join(' ')).length < 2500) return;
      var gh = mk('h2', 'cwl-gh', first ? (LV_TITLE() || lvTxt(4)) : lvTxt(4)); sg[cut].parentNode.insertBefore(gh, sg[cut]);
      out.push({ h: gh, lvl: top, kids: [], body: sg.slice(cut), parent: root, el: null, key: '' });
    });
    return out;
  }
  function buildBlocks(P) {
    countGen(P);
    var root = { kids: [], body: [], lvl: 1, el: P, key: '' }, used = {}, loose = [], seen = false, plan = [];
    function flush() { looseSecs(loose, root, 2, !seen).forEach(function (s) { plan.push(s); }); loose = []; }
    [].slice.call(P.childNodes).forEach(function (b) {
      var blk = b.nodeType === 1 && /^(DETAILS|SECTION|ARTICLE)$/.test(b.tagName) && (b.querySelector('h2,h3,h4') || b.querySelector('summary'));
      if (!blk) { loose.push(b); return; }
      flush(); seen = true;
      var h = b.querySelector('h2,h3,h4') || b.querySelector('summary'), sm = b.tagName === 'DETAILS' ? b.querySelector(':scope > summary') : null;
      var hh = mk('h2', '', clean(h.textContent)); if (h.id) { hh.id = h.id; h.removeAttribute('id'); }
      b.parentNode.insertBefore(hh, b);
      if (sm) { b.open = true; sm.classList.add('cwl-sum'); } else if (h.tagName !== 'SUMMARY') h.classList.add('cwl-dup');
      plan.push({ h: hh, lvl: 2, kids: [], body: [b], parent: root, el: null, key: '' });
    });
    flush();
    if (plan.length < 3) return null;
    plan.forEach(function (s) { root.kids.push(s); materialize(s, used); });
    return root;
  }
  function headIn(k) {   /* the heading a block-like child carries near its top, if any */
    if (!k.querySelector || /^(TABLE|THEAD|TBODY|TR|PRE|FIGURE|IMG|SCRIPT|STYLE)$/.test(k.tagName) || k.closest(SKIPQ)) return null;
    var h = k.querySelector('h2,h3,h4,h5'); if (!h || !isH5(h)) return null;
    var depth = 0; for (var e = h; e && e !== k; e = e.parentElement) depth++; return depth <= 3 && clean(k.textContent).length > clean(h.textContent).length + 30 ? h : null;
  }
  function isH5(n) { return n && n.nodeType === 1 && /^H[2-5]$/.test(n.tagName) && !n.closest(SKIPQ) && !n.classList.contains('vh') && !n.classList.contains('cwl-h'); }
  function subSecs(s, body, used, dp) {   /* sub-headings or heading-led blocks inside a section become its child cards */
    var best = null, bn = 0, mode = '';
    [body].concat([].slice.call(body.querySelectorAll('div,section,article,ul,ol,details'))).forEach(function (E) {
      if (E.closest('table') || E.closest('.cwl-s') !== s.el) return;
      var nh = 0, nb = 0;
      [].forEach.call(E.children, function (k) { if (isH5(k)) nh++; else if (headIn(k)) nb++; });
      if (nh >= 2 && nh > bn) { bn = nh; best = E; mode = 'flow'; }
      else if (nb >= 2 && nb > bn) { bn = nb; best = E; mode = 'blocks'; }
    });
    if (!best) return;
    var made = [];
    if (mode === 'flow') {
      var top = 9; [].forEach.call(best.children, function (k) { if (isH5(k)) top = Math.min(top, +k.tagName[1]); });
      var cur = null;
      [].slice.call(best.childNodes).forEach(function (n) {
        if (isH5(n) && +n.tagName[1] <= top) { cur = { h: n, lvl: top, kids: [], body: [], parent: s, el: null, key: '' }; made.push(cur); }
        else if (cur) cur.body.push(n);
      });
    } else {
      [].slice.call(best.children).forEach(function (k) {
        var h = headIn(k); if (!h) return;
        var hh = mk('h' + Math.min(6, (+h.tagName[1]) || 3), '', clean(h.textContent)); if (h.id) { hh.id = h.id; h.removeAttribute('id'); }
        k.parentNode.insertBefore(hh, k); h.classList.add('cwl-dup');
        made.push({ h: hh, lvl: 3, kids: [], body: [k], parent: s, el: null, key: '' });
      });
    }
    if (made.length < 2) return;
    made.forEach(function (c) { s.kids.push(c); materialize(c, used, dp + 1); });
  }
  function secOf(el) { var s = el && el.closest && el.closest('.cwl-s'); return s && s._cwl; }
  function depthOf(s) { var n = 0; while (s && s.h) { n++; s = s.parent; } return n; }
  function findKey(k) { var f = null; (function walk(a) { a.forEach(function (s) { if (s.key === k) f = s; else walk(s.kids); }); })(LV.root.kids); return f; }
  function topOff() { var y = 0; [].forEach.call(d.querySelectorAll('body *'), function (e) { if (e.offsetParent === null && getComputedStyle(e).position !== 'fixed') return; var cs = getComputedStyle(e); if ((cs.position === 'fixed' || cs.position === 'sticky') && e.getBoundingClientRect().top <= 1 && e.offsetHeight < innerHeight / 3 && e.offsetWidth > innerWidth / 2 && !e.closest('.cwl-on,.cw-gm')) y = Math.max(y, e.getBoundingClientRect().bottom); }); return Math.round(y); }
  function paint(s, pg) {   /* s = null for the top level */
    var P = LV.P; LV.cur = s; LV.pg = pg || 0;
    [].forEach.call(P.querySelectorAll('.cwl-path,.cwl-cur,.cwl-card,.cwl-x'), function (e) { e.classList.remove('cwl-path', 'cwl-cur', 'cwl-card', 'cwl-x'); e.removeAttribute('tabindex'); e.removeAttribute('role'); e.removeAttribute('aria-label'); });
    [].forEach.call(P.querySelectorAll('.cwl-more'), function (e) { e.remove(); });
    [].forEach.call(P.querySelectorAll('.cwl-hid'), function (e) { e.classList.remove('cwl-hid'); });
    if (s) { for (var n = s.el; n && n !== P && n.parentNode; n = n.parentNode) [].forEach.call(n.parentNode.children, function (sib) { if (sib !== n && !sib.classList.contains('cwl-back')) sib.classList.add('cwl-hid'); }); }
    var dep = depthOf(s); P.classList.toggle('cwl-sub', dep > 0); P.setAttribute('data-cwl-depth', dep);
    var list;
    if (s) { s.el.classList.add('cwl-cur'); for (var a = s.parent; a && a.h; a = a.parent) a.el.classList.add('cwl-path'); list = s.kids; }
    else list = LV.root.kids;
    var from = s ? LV.pg * 4 : 0, to = s ? from + 4 : list.length;
    list.forEach(function (c, i) {
      if (i < from || i >= to) { c.el.classList.add('cwl-x'); return; }
      c.el.classList.add('cwl-card'); c.el.tabIndex = 0; c.el.setAttribute('role', 'button'); c.el.setAttribute('aria-label', lvTxt(1) + ': ' + clean(c.h.textContent));
    });
    if (s && list.length > to) {
      var mc = mk('div', 'cwl-s cwl-card cwl-more'); mc.tabIndex = 0; mc.setAttribute('role', 'button');
      mc.appendChild(mk('div', 'cwl-h cwl-mh', lvTxt(2) + ' (' + (list.length - to) + ')'));
      mc.appendChild(mk('p', 'cwl-pv', list.slice(to, to + 6).map(function (c) { return clean(c.h.textContent); }).join(' · ')));
      mc.appendChild(mk('span', 'cwl-rm', lvTxt(1))); mc._more = true; var last = list[to - 1].el; last.parentNode.insertBefore(mc, last.nextSibling);
    }
    var bk = LV.back; bk.hidden = dep === 0;
    if (dep) { var up = s.parent && s.parent.h ? clean(s.parent.h.textContent) : (LV.pg ? clean(s.h.textContent) : LV.title || lvTxt(3)); if (LV.pg) up = clean(s.h.textContent); bk.querySelector('.cwl-bt').textContent = up.slice(0, 40); bk.style.top = (topOff() + 8) + 'px'; }
  }
  function hashFor(s, pg) { return s ? '#cwl-' + s.key + (pg ? '~' + (pg + 1) : '') : ''; }
  function parseHash(h) { var m = /^#cwl-(.+?)(?:~(\d+))?$/.exec(decodeURIComponent(h || '')); if (!m) return null; var s = findKey(m[1]); return s ? { s: s, pg: m[2] ? +m[2] - 1 : 0 } : null; }
  function anim(el, frames, ms, ease) { try { return el.animate(frames, { duration: ms, easing: ease || 'ease', fill: 'none' }).finished; } catch (e) { return Promise.resolve(); } }
  function scrollTopOf() { return Math.max(0, LV.P.getBoundingClientRect().top + scrollY - topOff() - 8); }
  function go(s, pg, dir, originEl) {   /* dir: 1 enter, -1 exit, 0 jump */
    if (LV.busy) { LV.pending = [s, pg, dir, originEl]; return; } var P = LV.P, prevKey = hashFor(LV.cur, LV.pg);
    var heavy = P.offsetHeight > innerHeight * 14;   /* a huge register: a quick fade instead of a zoom */
    if (dir > 0) LV.scrolls[prevKey] = scrollY;
    function swap() {
      paint(s, pg);
      var y = dir < 0 && LV.scrolls[hashFor(s, pg)] != null ? LV.scrolls[hashFor(s, pg)] : (s ? scrollTopOf() : (dir < 0 ? 0 : scrollY));
      scrollTo(0, y);
    }
    if (!dir || RM || heavy) {
      if ((RM || heavy) && dir) { LV.busy = true; anim(P, [{ opacity: 1 }, { opacity: 0 }], 120).then(function () { swap(); return anim(P, [{ opacity: 0 }, { opacity: 1 }], 160); }).then(done); } else { swap(); done(); }
      return;
    }
    LV.busy = true; de.classList.add('cwl-anim');
    var pr = P.getBoundingClientRect(), o = originEl && originEl.getBoundingClientRect ? originEl.getBoundingClientRect() : null;
    var ox = o ? (o.left + o.width / 2 - pr.left) : pr.width / 2, oy = o ? (o.top + o.height / 2 - pr.top) : Math.min(pr.height, innerHeight) / 2;
    P.style.transformOrigin = ox + 'px ' + oy + 'px';
    var OUT = dir > 0 ? 'perspective(800px) translateZ(260px)' : 'perspective(800px) translateZ(-110px)';
    var IN = dir > 0 ? 'perspective(800px) translateZ(-110px)' : 'perspective(800px) translateZ(260px)';
    anim(P, [{ transform: 'none', opacity: 1, filter: 'blur(0)' }, { transform: OUT, opacity: 0, filter: 'blur(' + (dir > 0 ? 2 : 0) + 'px)' }], dir > 0 ? 260 : 220, 'cubic-bezier(.45,0,.9,.5)').then(function () {
      P.style.opacity = '0'; swap();
      var pr2 = P.getBoundingClientRect(), tgt = dir < 0 && LV.lastLeft ? LV.lastLeft.getBoundingClientRect() : null;
      P.style.transformOrigin = tgt ? (tgt.left + tgt.width / 2 - pr2.left) + 'px ' + (tgt.top + tgt.height / 2 - pr2.top) + 'px' : (pr2.width / 2) + 'px ' + Math.max(0, scrollY - (pr2.top + scrollY) + innerHeight / 3) + 'px';
      P.style.opacity = '';
      return anim(P, [{ transform: IN, opacity: 0 }, { transform: 'none', opacity: 1 }], dir > 0 ? 340 : 320, 'cubic-bezier(.15,.6,.3,1)');
    }).then(done, done);
    function done() {
      LV.busy = false; de.classList.remove('cwl-anim'); P.style.transformOrigin = ''; P.style.opacity = '';
      if (LV.pending) { var q = LV.pending; LV.pending = null; setTimeout(function () { go(q[0], q[1], q[2], q[3]); }, 0); }
      if (dir > 0 && s) { s.h.tabIndex = -1; s.h.focus({ preventScroll: true }); }
      else if (dir < 0 && LV.lastLeft && LV.lastLeft.isConnected && LV.lastLeft.classList.contains('cwl-card')) LV.lastLeft.focus({ preventScroll: true });
    }
  }
  function enterCard(card) {
    if (card._more) { var s = LV.cur, pg = LV.pg + 1; history.pushState({ cwl: 1 }, '', hashFor(s, pg)); LV.lastLeft = card; go(s, pg, 1, card); return; }
    var c = card._cwl; LV.lastLeft = card; history.pushState({ cwl: 1 }, '', hashFor(c, 0)); go(c, 0, 1, card);
  }
  function upOne() {
    var s = LV.cur; if (!s) return;
    if (history.state && history.state.cwl) { history.back(); return; }
    var t = LV.pg ? { s: s, pg: LV.pg - 1 } : { s: s.parent && s.parent.h ? s.parent : null, pg: 0 };
    LV.lastLeft = LV.pg ? null : s.el; history.replaceState(null, '', t.s ? hashFor(t.s, t.pg) : location.pathname + location.search); go(t.s, t.pg, -1);
  }
  function onPop() {
    var t = parseHash(location.hash);
    if (!t) { var tg = location.hash.length > 1 && d.getElementById(decodeURIComponent(location.hash.slice(1))); if (tg && LV.P.contains(tg)) { openFor(tg); return; } }
    var ns = t ? t.s : null, npg = t ? t.pg : 0, cd = depthOf(LV.cur) * 10 + LV.pg, nd = depthOf(ns) * 10 + npg;
    if (ns === LV.cur && npg === LV.pg) return;
    if (nd < cd) LV.lastLeft = LV.cur && !LV.pg ? LV.cur.el : null;
    go(ns, npg, nd < cd ? -1 : 1, nd < cd ? null : null);
  }
  function openFor(tg) {   /* a #link to text inside a card: open the level that holds it, then show it */
    var s = secOf(tg); if (s && s.h === tg && s.parent) s = s.parent.h ? s.parent : null;
    if (s && tg === s.el) s = s.parent && s.parent.h ? s.parent : null;
    var sec = secOf(tg); var lvl = sec; if (sec && (tg === sec.h)) lvl = sec;
    var pg = 0; if (lvl && lvl.parent && lvl.parent.h) { /* none */ }
    paint(lvl || null, 0); setTimeout(function () { try { tg.scrollIntoView({ block: 'start' }); scrollBy(0, -topOff() - 52); } catch (e) {} }, 30);
  }
  function levels() {
    if (NOCLIP.test(location.pathname) || location.pathname === '/' || /^\/(?:wales|argentina)\/?$/.test(location.pathname) || de.hasAttribute('data-cw-nolevels') || location.search.indexOf('full=1') >= 0) return;
    var c = content(); if (!c || c.closest('.ghf-ui')) return;
    if (c.querySelector('canvas,video,iframe[src*="player"],[data-cw-nolevels]') && clean(c.textContent).length < 4000) return;
    var fp = flowParent(c), bp = blockParent(c), P = null, root = null;
    function ok(x) { return x && !x.p.querySelector('input,select,textarea'); }
    if (ok(bp) && (!ok(fp) || bp.n > fp.n || bp.p.contains(fp.p) && bp.n >= 3)) { P = bp.p; root = buildBlocks(P); }
    if (!root && ok(fp)) { P = fp.p; root = buildFlow(P); }
    if (!root || clean(P.textContent).length < 1200) return;
    var h1 = d.querySelector('main h1,article h1,h1'); LV = { P: P, root: root, cur: null, pg: 0, scrolls: {}, busy: false, title: h1 ? clean(h1.textContent).split(/ [—–:|] /)[0] : '' };
    P.classList.add('cwl-on');
    var bk = mk('button', 'cwl-back'); bk.type = 'button'; bk.innerHTML = '<span class="cwl-ba" aria-hidden="true">‹</span><span>' + lvTxt(0) + '</span><span class="cwl-bt"></span>'; bk.hidden = true;
    bk.onclick = upOne; P.insertBefore(bk, P.firstChild); LV.back = bk;
    P.addEventListener('click', function (e) {
      var card = e.target.closest('.cwl-card'); if (!card || !P.contains(card)) return;
      var a = e.target.closest('a[href]'); if (a && !card.querySelector('.cwl-pv').contains(a) && card !== a) { if (!card.classList.contains('cwl-card')) return; }
      e.preventDefault(); e.stopPropagation(); enterCard(card);
    });
    P.addEventListener('keydown', function (e) { var card = e.target.closest && e.target.closest('.cwl-card'); if (card && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); enterCard(card); } });
    d.addEventListener('keydown', function (e) { if (e.key === 'Escape' && LV.cur && !de.classList.contains('cw-gm-lock')) upOne(); });
    addEventListener('popstate', onPop);
    d.addEventListener('click', function (e) { var a = e.target.closest && e.target.closest('a[href^="#"]'); if (!a || a.closest('.cwl-card')) return; var id = decodeURIComponent(a.getAttribute('href').slice(1)), tg = id && d.getElementById(id); if (tg && P.contains(tg) && tg.getClientRects().length === 0) { e.preventDefault(); history.pushState({ cwl: 1 }, '', '#' + id); openFor(tg); } }, true);
    addEventListener('beforeprint', function () { P.classList.remove('cwl-on'); }); addEventListener('afterprint', function () { P.classList.add('cwl-on'); });
    var t0 = parseHash(location.hash);
    if (t0) paint(t0.s, t0.pg);
    else { paint(null, 0); var id = location.hash.length > 1 && decodeURIComponent(location.hash.slice(1)), tg = id && d.getElementById(id); if (tg && P.contains(tg)) openFor(tg); }
    window.__cwGraph.levels = LV;
  }
  function start() {
    watchBanner(); try { autoMore(); } catch (e) {}
    function lv() { try { levels(); } catch (e) { if (window.console) console.warn('cw levels', e); } }
    if (moreN && window.__cwGraph.loadAll) window.__cwGraph.loadAll(lv); else lv();
  }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', start); else start();
})();
