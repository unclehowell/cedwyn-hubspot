/*! glossary-modal.js v1.0.2 - Cedwyn site-wide glossary pop-up (27 Oct 2026). One source: /_cedwyn/glossary.json
 (built from data/glossary.json by tools/wikilinks.py). Native <dialog>: Esc closes, focus returns to the opener, the page
 behind is inert. Dotted glossary words, links to /glossary/ and the "Glossary" button open it at the term. /glossary/ stays a
 plain crawlable page that opens the pop-up on load. Day/night aware (also under the night-mode inversion). - Sion's Tab agent */
(function () {
  if (window.CWGlossary) return;
  var D = document, SRC = "/_cedwyn/glossary.json?v=1", data = null, dlg = null, list = null, q = null, pending = null, opener = null;
  var css = ".cw-gl{border:0;padding:0;width:min(560px,calc(100vw - 20px));max-height:min(86vh,760px);border-radius:16px;background:#fff;color:#141414;" +
    "box-shadow:0 18px 50px rgba(0,0,0,.45);font:400 16px/1.45 system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;text-align:left}" +
    ".cw-gl::backdrop{background:rgba(0,0,0,.6)}.cw-gl-in{display:flex;flex-direction:column;max-height:min(86vh,760px)}" +
    ".cw-gl-hd{display:flex;align-items:center;gap:8px;padding:14px 14px 8px 18px}.cw-gl-hd h2{flex:1;margin:0;font-size:1.25em;line-height:1.2;color:inherit}" +
    ".cw-gl-x{width:44px;height:44px;border:0;border-radius:22px;background:transparent;color:inherit;font-size:28px;line-height:1;cursor:pointer}" +
    ".cw-gl-q{margin:0 18px 8px;padding:10px 12px;font:inherit;font-size:16px;border:1px solid #9a9a9a;border-radius:10px;background:transparent;color:inherit}" +
    ".cw-gl-ls{overflow:auto;padding:0 18px 16px;margin:0;-webkit-overflow-scrolling:touch}.cw-gl-it{padding:10px 0;border-top:1px solid rgba(127,127,127,.28)}" +
    ".cw-gl-it h3{margin:0 0 4px;font-size:1.02em;color:inherit}.cw-gl-it p{margin:0}.cw-gl-it .cw-gl-lm{margin-top:6px;font-size:.9em}" +
    ".cw-gl-it a{color:#8a5300;font-weight:600}.cw-gl-it.cw-gl-on{background:rgba(214,145,0,.16);border-radius:8px;padding:10px 8px}" +
    ".cw-gl-none{padding:12px 0;opacity:.75}.cw-gl-x:focus-visible,.cw-gl-q:focus-visible,.cw-gl-open:focus-visible{outline:2px solid currentColor;outline-offset:2px}" +
    ".cw-gl-open{font:inherit;color:inherit;background:transparent;border:1px solid currentColor;border-radius:999px;padding:4px 12px;margin:0 6px;cursor:pointer;min-height:32px}" +
    "html[data-ghf-mode=night] .cw-gl{background:#16161c;color:#f1f1f5}" + /* the dialog sits in the top layer, outside the night-mode inversion */
    "html[data-ghf-mode=night] .cw-gl-it a{color:#ffcf70}" +
    "@media (prefers-color-scheme:dark){html:not([data-ghf-mode]) .cw-gl{background:#16161c;color:#f1f1f5}html:not([data-ghf-mode]) .cw-gl-it a{color:#ffcf70}}";
  function el(t, c, txt) { var e = D.createElement(t); if (c) e.className = c; if (txt != null) e.textContent = txt; return e; }
  function links(lm) {
    var out = [], i, x; if (!lm) return out; if (!Array.isArray(lm)) lm = [lm];
    for (i = 0; i < lm.length; i++) { x = lm[i]; var u = typeof x === "string" ? x : (x.url || x.href || x.path), l = typeof x === "string" ? x : (x.title || x.label || x.text || u);
      if (u && /^\//.test(u)) out.push([u, l]); }
    return out;
  }
  function build() {
    if (dlg) return;
    var st = el("style"); st.id = "cw-gl-css"; st.textContent = css; (D.head || D.documentElement).appendChild(st);
    dlg = el("dialog", "cw-gl"); dlg.id = "cw-glossary"; dlg.setAttribute("aria-labelledby", "cw-gl-h");
    var inn = el("div", "cw-gl-in"), hd = el("div", "cw-gl-hd"), h = el("h2", null, "Glossary"); h.id = "cw-gl-h";
    var x = el("button", "cw-gl-x", "\u00d7"); x.type = "button"; x.setAttribute("aria-label", "Close"); x.onclick = function () { dlg.close(); };
    hd.appendChild(h); hd.appendChild(x);
    q = el("input", "cw-gl-q"); q.type = "search"; q.placeholder = "Search the glossary"; q.setAttribute("aria-label", "Search the glossary"); q.autocomplete = "off";
    q.oninput = filter;
    list = el("div", "cw-gl-ls"); list.setAttribute("role", "list");
    inn.appendChild(hd); inn.appendChild(q); inn.appendChild(list); dlg.appendChild(inn); D.body.appendChild(dlg);
    dlg.addEventListener("click", function (e) { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener("close", function () { if (opener && opener.focus) try { opener.focus(); } catch (e) {} });
    dlg.addEventListener("keydown", function (e) { if (e.key === "Escape") { e.preventDefault(); dlg.close(); } }); // Esc closes even from the search box
  }
  function render() {
    list.textContent = "";
    var ts = (data && data.terms) || [];
    ts.slice().sort(function (a, b) { return a.term.localeCompare(b.term); }).forEach(function (t) {
      var it = el("div", "cw-gl-it"); it.id = "cw-gl-" + t.slug; it.setAttribute("role", "listitem"); it.setAttribute("data-k", (t.term + " " + t.definition).toLowerCase());
      it.appendChild(el("h3", null, t.term)); it.appendChild(el("p", null, t.definition));
      var lk = links(t.learn_more);
      if (lk.length) { var p = el("p", "cw-gl-lm"); p.appendChild(D.createTextNode("Learn more: "));
        lk.slice(0, 4).forEach(function (l, i) { if (i) p.appendChild(D.createTextNode(" \u00b7 ")); var a = el("a", null, l[1]); a.href = l[0]; p.appendChild(a); }); it.appendChild(p); }
      list.appendChild(it);
    });
    var no = el("p", "cw-gl-none", "No term matches."); no.hidden = true; no.id = "cw-gl-none"; list.appendChild(no);
  }
  function filter() {
    var v = (q.value || "").trim().toLowerCase(), n = 0, its = list.querySelectorAll(".cw-gl-it");
    for (var i = 0; i < its.length; i++) { var on = !v || its[i].getAttribute("data-k").indexOf(v) >= 0; its[i].hidden = !on; if (on) n++; }
    var no = D.getElementById("cw-gl-none"); if (no) no.hidden = n > 0;
  }
  function load(cb) {
    if (data) return cb();
    fetch(SRC, { credentials: "same-origin" }).then(function (r) { return r.json(); }).then(function (j) { data = j; render(); cb(); })
      .catch(function () { location.href = "/glossary/" + (pending ? "#" + pending : ""); });
  }
  function open(slug, from) {
    build(); opener = from || D.activeElement; pending = slug || null;
    load(function () {
      q.value = ""; filter();
      var on = list.querySelectorAll(".cw-gl-on"); for (var i = 0; i < on.length; i++) on[i].classList.remove("cw-gl-on");
      if (!dlg.open) { try { dlg.showModal(); } catch (e) { dlg.setAttribute("open", ""); } }
      var it = slug && D.getElementById("cw-gl-" + slug);
      if (it) { it.classList.add("cw-gl-on"); it.scrollIntoView({ block: "center" }); dlg.querySelector(".cw-gl-x").focus(); } else { list.scrollTop = 0; q.focus(); }
    });
  }
  function slugOf(href) { var m = /\/glossary\/?(?:index\.html)?(?:[?][^#]*)?(?:#([\w-]+))?$/.exec(href || ""); return m ? (m[1] || "") : null; }
  D.addEventListener("click", function (e) {
    if (e.defaultPrevented || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    var b = e.target.closest && e.target.closest(".cw-gl-open"); if (b) { e.preventDefault(); open(b.getAttribute("data-term") || "", b); return; }
    var a = e.target.closest && e.target.closest("a[href]"); if (!a || (dlg && dlg.contains(a))) return;
    var h = a.getAttribute("href"); if (!/^(https:\/\/cedwyn\.bucklerfamily\.estate)?\/glossary\//.test(h)) return;
    var s = slugOf(h.replace(/^https:\/\/cedwyn\.bucklerfamily\.estate/, "")); if (s === null) return;
    e.preventDefault(); open(s, a);
  });
  function addButtons() {
    var spots = D.querySelectorAll(".cw-legend,#ghf-agent-footer,footer"), done = 0;
    for (var i = 0; i < spots.length && done < 2; i++) {
      if (spots[i].querySelector(".cw-gl-open")) { done++; continue; }
      var b = el("button", "cw-gl-open", "Glossary"); b.type = "button"; b.setAttribute("aria-haspopup", "dialog");
      spots[i].appendChild(b); done++;
    }
  }
  function boot() {
    addButtons();
    if (/^\/glossary\/?(index\.html)?$/.test(location.pathname)) open((location.hash || "").slice(1));
  }
  window.CWGlossary = { open: open };
  if (D.readyState === "loading") D.addEventListener("DOMContentLoaded", boot); else boot();
})();
