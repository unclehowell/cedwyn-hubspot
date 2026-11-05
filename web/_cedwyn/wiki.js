/* wiki.js - Cedwyn word links (Sion, 22:12 GMT 26 Oct 2026, m:611a2587). - Sion's Tab agent
   a.cw-g  glossary word: hover / focus / first tap shows the one-line meaning; the link opens /glossary/#term.
   a.cw-n  name with spelling variants: hover shows this spelling's one-liner; click or tap opens a pop-up of every name the
           records use (keyboard and touch; Esc, the X or a tap outside closes it). Without JS it opens the Nomenclature page.
   [data-cw-less]  "Show less" inside a Learn more fold: closes that fold and returns to its button. */
(function () {
  'use strict';
  if (window.__cwWiki) return; window.__cwWiki = 1;
  var d = document, tip = null, cur = null, ptr = 'mouse', hideT = 0, data = null, bg = null, lastFocus = null;
  function el(t, c, txt) { var e = d.createElement(t); if (c) e.className = c; if (txt != null) e.textContent = txt; return e; }
  function place(a) {
    var r = a.getBoundingClientRect(), vw = d.documentElement.clientWidth, sx = window.pageXOffset, sy = window.pageYOffset;
    tip.style.left = '0px'; tip.style.top = '0px'; tip.style.display = 'block';
    var w = tip.offsetWidth, h = tip.offsetHeight, left = Math.max(8, Math.min(r.left, vw - w - 8)), top = r.bottom + 6;
    if (top + h > window.innerHeight - 4 && r.top - h - 6 > 4) top = r.top - h - 6;
    tip.style.left = (left + sx) + 'px'; tip.style.top = (top + sy) + 'px';
  }
  function show(a, withLink) {
    var t = a.getAttribute('data-tip'); if (!t) return;
    if (!tip) { tip = el('div', 'cw-tip'); tip.id = 'cw-tip'; tip.setAttribute('role', 'tooltip'); d.body.appendChild(tip);
      tip.addEventListener('mouseenter', function () { clearTimeout(hideT); });
      tip.addEventListener('mouseleave', function () { hide(); }); }
    clearTimeout(hideT); tip.textContent = '';
    tip.appendChild(el('span', '', t));
    if (withLink) { tip.appendChild(d.createElement('br')); var l = el('a', '', a.classList.contains('cw-n') ? 'Every name ›' : 'Read more ›'); l.href = a.href; tip.appendChild(l); }
    if (cur && cur !== a) cur.removeAttribute('aria-describedby');
    cur = a; a.setAttribute('aria-describedby', 'cw-tip'); place(a);
  }
  function hide(now) {
    clearTimeout(hideT);
    hideT = setTimeout(function () { if (tip) tip.style.display = 'none'; if (cur) cur.removeAttribute('aria-describedby'); cur = null; }, now ? 0 : 160);
  }
  function tipTarget(e) { var t = e.target; return t && t.closest ? t.closest('[data-tip]') : null; }
  d.addEventListener('pointerdown', function (e) { ptr = e.pointerType || 'mouse'; }, true);
  d.addEventListener('touchstart', function () { ptr = 'touch'; }, { passive: true, capture: true });
  d.addEventListener('mouseover', function (e) { if (ptr === 'touch') return; var a = tipTarget(e); if (a) show(a, false); });
  d.addEventListener('mouseout', function (e) { if (ptr === 'touch') return; var a = tipTarget(e); if (a && (!e.relatedTarget || !a.contains(e.relatedTarget))) hide(); });
  d.addEventListener('focusin', function (e) { var a = tipTarget(e); if (a && ptr !== 'touch') show(a, false); });
  d.addEventListener('focusout', function (e) { if (ptr !== 'touch' && tipTarget(e)) hide(); });
  d.addEventListener('scroll', function () { if (tip && tip.style.display === 'block' && ptr === 'touch') hide(true); }, { passive: true });

  function load(cb) {
    if (data) return cb(data);
    var x = new XMLHttpRequest(); x.open('GET', '/_cedwyn/nomenclature.json?v=1');
    x.onload = function () { try { data = JSON.parse(x.responseText).groups; } catch (err) { data = null; } cb(data); };
    x.onerror = function () { cb(null); }; x.send();
  }
  function close() {
    if (!bg) return; bg.remove(); bg = null; d.documentElement.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function open(a) {
    var id = a.getAttribute('data-n'); lastFocus = a; hide(true);
    load(function (groups) {
      var g = groups && groups[id]; if (!g) { location.href = a.href; return; }
      close(); bg = el('div', 'cw-modal-bg'); var m = el('div', 'cw-modal');
      m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true'); m.setAttribute('aria-labelledby', 'cw-mt');
      var x = el('button', 'cw-x', '\u00d7'); x.type = 'button'; x.setAttribute('aria-label', 'Close'); x.onclick = close;
      var h = el('h2', '', g.name); h.id = 'cw-mt';
      m.appendChild(x); m.appendChild(h); m.appendChild(el('p', 'cw-ms', g.summary));
      var ul = el('ul');
      (g.variants || []).forEach(function (v) {
        var li = el('li'), n;
        if (v.url) { n = el('a', '', v.variant); n.href = v.url; n.setAttribute('data-tip', v.variant + ' \u2014 ' + v.one_liner); }
        else n = el('strong', '', v.variant);
        li.appendChild(n);
        var meta = [v.first_record, v.source_id].filter(Boolean).join(' \u00b7 ');
        if (meta) li.appendChild(el('span', 'cw-md', meta));
        li.appendChild(el('span', 'cw-ol', v.one_liner));
        ul.appendChild(li);
      });
      m.appendChild(ul);
      var f = el('p', 'cw-mf'), fl = el('a', '', 'All names and their records \u203a'); fl.href = g.url; f.appendChild(fl); m.appendChild(f);
      var gl = el('a', '', 'Glossary \u203a'); gl.href = '/glossary/#name-' + id; f.appendChild(d.createTextNode(' \u00b7 ')); f.appendChild(gl);
      bg.appendChild(m); d.body.appendChild(bg); d.documentElement.style.overflow = 'hidden';
      bg.addEventListener('click', function (e) { if (e.target === bg) close(); });
      x.focus();
    });
  }
  d.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { if (bg) { e.preventDefault(); close(); } else hide(true); return; }
    if (e.key === 'Tab' && bg) {
      var fs = bg.querySelectorAll('a[href],button'); if (!fs.length) return;
      var first = fs[0], last = fs[fs.length - 1];
      if (e.shiftKey && d.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && d.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });
  d.addEventListener('click', function (e) {
    var t = e.target; if (!t || !t.closest) return;
    var less = t.closest('[data-cw-less]');
    if (less) { var det = less.closest('details'); if (det) { det.open = false; var s = det.querySelector('summary');
      if (s) { s.focus({ preventScroll: true }); var r = s.getBoundingClientRect(); if (r.top < 0 || r.top > window.innerHeight) s.scrollIntoView({ block: 'center' }); } } return; }
    var n = t.closest('a.cw-n');
    if (n && !e.metaKey && !e.ctrlKey && !e.shiftKey && !(bg && bg.contains(n))) { e.preventDefault(); open(n); return; }
    var g = t.closest('a.cw-g');
    if (g && ptr === 'touch' && cur !== g) { e.preventDefault(); show(g, true); return; }
    if (tip && tip.style.display === 'block' && !(tip.contains(t)) && !t.closest('[data-tip]')) hide(true);
  });
  function ready() { var b = d.querySelectorAll('[data-cw-less][hidden]'); for (var i = 0; i < b.length; i++) b[i].hidden = false; }
  if (d.readyState === 'loading') d.addEventListener('DOMContentLoaded', ready); else ready();
})();
