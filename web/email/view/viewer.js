/* The Post Office · thread and message viewer (Cedwyn, static). Opens /email/thread/<id-slug>/ and /email/reference/<id>/
   from the case-mail catalogue copied into this compartment (/email/view/index.json, from datro@wayback wayback/api/index.json)
   and the redacted message texts already in the Wayback Vault (/wayback/mail/<id>.txt). Same origin only, no outbound requests.
   With no id it lists every thread, newest first. - Sion's Tab agent, 25 Oct 2026 */
(function () {
  var box = document.getElementById('ev'), lp = window.__cedwynLP || location.pathname, d = document;
  var m = /\/email\/(thread|reference)\/([^\/?#]+)/.exec(lp), kind = m && m[1], key = m ? decodeURIComponent(m[2]).toLowerCase() : '';
  function el(t, c, x) { var e = d.createElement(t); if (c) e.className = c; if (x != null) e.textContent = x; return e; }
  function day(s) { return s ? String(s).replace('T', ' ').replace(/:\d\d(\.\d+)?Z$/, ' UTC') : 'undated'; }
  function who(r) { var n = (r.institutions || []).map(function (i) { return i.name; }).join(', ') || 'correspondent';
    return (r.direction === 'sent' ? 'Sent to ' : r.direction === 'received' ? 'Received from ' : '') + n; }
  function norm(v) { return String(v || '').toLowerCase().replace(/^(?:re\s*[:_\-]?\s*)+/i, '').replace(/\.(txt|eml|html?)$/i, '').replace(/[^a-z0-9]+/g, ' ').trim(); }
  function link(th) { var r = th[0], s = ('gt ' + String(r.threadId).replace(/^gt-/, '') + ' ' + norm(r.subject)).trim().replace(/\s+/g, '-').slice(0, 140); return '/email/thread/' + s + '/'; }
  function back() { var p = el('p', 'ev-back'), a = el('a', null, '‹ All mail in the Post Office'); a.href = '/email/view/'; p.appendChild(a); return p; }
  function render(list, focus) {
    list.sort(function (a, b) { return String(a.date || '').localeCompare(String(b.date || '')); });
    box.textContent = ''; box.appendChild(back());
    var h = el('h1', null, list[0].subject || 'Thread'); box.appendChild(h); d.title = (list[0].subject || 'Thread') + ' · The Post Office · Cedwyn';
    box.appendChild(el('p', 'ev-mut', list.length + (list.length === 1 ? ' message' : ' messages') + (list[0].refs && list[0].refs.length ? ' · ' + list[0].refs.join(', ') : '')));
    list.forEach(function (r) {
      var s = el('section', 'ev-msg'); s.id = r.gmailMessageId || r.id; if (focus && (focus === r.gmailMessageId || focus === r.id)) s.className += ' ev-on';
      s.appendChild(el('h2', null, who(r))); s.appendChild(el('p', 'ev-mut', day(r.date) + (r.subject && r.subject !== list[0].subject ? ' · ' + r.subject : '')));
      var pre = el('pre', 'ev-body', 'Loading the message…'); s.appendChild(pre);
      var src = r.textUrl ? '/wayback' + r.textUrl : null;
      if (src) { var p = el('p', 'ev-mut'), a = el('a', null, 'Archived text file'); a.href = src; p.appendChild(a); s.appendChild(p);
        fetch(src).then(function (x) { if (!x.ok) throw 0; return x.text(); }).then(function (t) { pre.textContent = t; }).catch(function () { pre.textContent = 'The archived text of this message is not in the vault yet.'; }); }
      else pre.textContent = 'The archived text of this message is not in the vault yet.';
      box.appendChild(s);
    });
    var f = focus && d.getElementById(focus); if (f) setTimeout(function () { f.scrollIntoView({ block: 'start' }); }, 300);
  }
  function hay(th) { return norm(th.map(function (r) { return [r.subject, r.from, (r.refs || []).join(' '), (r.institutions || []).map(function (i) { return i.name; }).join(' '), r.date, r.direction].join(' '); }).join(' ')); }
  function index(threads) {
    box.textContent = ''; box.appendChild(el('h1', null, 'The Post Office · all mail'));
    var cnt = el('p', 'ev-mut', threads.length + ' threads, newest first. Contact details are redacted in every message.'); box.appendChild(cnt);
    /* search (26 Oct 2026): the old email site's search, here over the same records catalogue — subject, sender, institution, reference, date */
    var f = el('form', 'ev-find'); f.setAttribute('role', 'search'); f.onsubmit = function (e) { e.preventDefault(); };
    var q = el('input'); q.type = 'search'; q.name = 'q'; q.placeholder = 'Search the mail: institution, subject, reference, date'; q.setAttribute('aria-label', 'Search the mail');
    f.appendChild(q); box.appendChild(f);
    var ul = el('ul', 'ev-list'), rows = [];
    threads.forEach(function (th) { var r = th[th.length - 1], li = el('li'), a = el('a', null, th[0].subject || '(no subject)'); a.href = link(th);
      li.appendChild(a); li.appendChild(el('span', 'ev-mut', ' · ' + day(r.date).slice(0, 10) + ' · ' + who(r).replace(/^(Sent to|Received from) /, '') + ' · ' + th.length)); ul.appendChild(li); rows.push([li, hay(th)]); });
    box.appendChild(ul);
    function run() { var w = norm(q.value).split(' ').filter(Boolean), n = 0;
      rows.forEach(function (x) { var on = w.every(function (t) { return x[1].indexOf(t) >= 0; }); x[0].style.display = on ? '' : 'none'; if (on) n++; });
      cnt.textContent = w.length ? n + ' of ' + threads.length + ' threads match.' : threads.length + ' threads, newest first. Contact details are redacted in every message.';
      try { history.replaceState(null, '', location.pathname + (w.length ? '?q=' + encodeURIComponent(q.value) : '')); } catch (e) {} }
    q.oninput = run; var m0 = /[?&]q=([^&]*)/.exec(location.search); if (m0) { q.value = decodeURIComponent(m0[1].replace(/\+/g, ' ')); run(); }
  }
  function missing(extra) {
    box.textContent = ''; box.appendChild(back());
    box.appendChild(el('h1', null, 'Mail reference ' + key));
    var note = el('p', 'ev-mut', 'This message is not in the mail catalogue yet.'); box.appendChild(note);
    fetch('/wayback/email/mail-index.json').then(function (x) { return x.json(); }).then(function (mi) {
      var w = key.replace(/^gt-[0-9a-f]{16}-?/, '').split('-').filter(function (x) { return x.length > 1; }), hit = (mi.records || []).filter(function (r) {
        var s = norm(r.subject + ' ' + r.name); return w.length && w.every(function (x) { return s.indexOf(x) >= 0; }); }).slice(0, 25);
      if (!hit.length) return; note.textContent = 'The archived texts for this reference are in the Wayback Vault:';
      var ul = el('ul', 'ev-list'); hit.forEach(function (r) { var li = el('li'), a = el('a', null, r.subject || r.name); a.href = '/wayback/' + r.sourcePath.split('/').map(encodeURIComponent).join('/');
        li.appendChild(a); li.appendChild(el('span', 'ev-mut', ' · ' + (r.date || 'undated'))); ul.appendChild(li); }); box.appendChild(ul);
    }).catch(function () {});
  }
  fetch('/email/view/index.json').then(function (x) { return x.json(); }).then(function (D) {
    var rs = D.records || [], by = {}, order = [];
    rs.forEach(function (r) { var t = r.threadId || r.id; if (!by[t]) { by[t] = []; order.push(t); } by[t].push(r); });
    if (!kind) { var th = order.map(function (t) { return by[t].sort(function (a, b) { return String(a.date || '').localeCompare(String(b.date || '')); }); });
      th.sort(function (a, b) { return String(b[b.length - 1].date || '').localeCompare(String(a[a.length - 1].date || '')); }); return index(th); }
    var hx = /^(?:gt-|gm-)?([0-9a-f]{16})/.exec(key), id = hx && hx[1];
    if (id) {
      if (by['gt-' + id]) return render(by['gt-' + id].slice(), kind === 'reference' ? id : null);
      var r = rs.filter(function (x) { return x.gmailMessageId === id; })[0]; if (r) return render(by[r.threadId].slice(), id);
    }
    var s = rs.filter(function (x) { return x.threadSlug === key || norm(x.subject).replace(/\s+/g, '-') === key; })[0];
    if (s) return render(by[s.threadId].slice(), null);
    missing();
  }).catch(function () { missing(); });
})();
