/*! section.js — Cedwyn's two sections, Wales and Argentina (Sion, 25 Oct 2026) · v1.0.0 · Sion's Tab agent
 * One database, two framings. On a theme page opened under /wales/<theme>/ or /argentina/<theme>/ (runtime.js sets
 * <html data-cedwyn-sec>), this adds the section ribbon (accent colours, the section's coming-soon focus and cross-sell,
 * a switch to the same theme in the other nation) and keeps the visitor inside the section when they follow a theme link.
 * It also renders [data-i18n] text in en/cy/es (landing and hub pages), runs the notify-me forms, and names the footer
 * headings in the chosen language. The language and the day/night choice are the shared ones (ghf_lang, ghf-theme);
 * a section only supplies the default language (Wales: cy, Argentina: es) until the visitor picks one. */
(function () {
  if (window.CedwynSection) return;
  var de = document.documentElement;
  var T = window.CEDWYN_T || /*SECTION_T*/{};
  var THEMES = /*SECTION_THEMES*/[];
  var SEC = de.getAttribute("data-cedwyn-sec") || "", SECURL = de.getAttribute("data-cedwyn-sec-url") || "";
  var ACC = { wales: ["#00843D", "#C8102E"], argentina: ["#4E8CC8", "#F6B40E"] };
  function cookie(n) { var m = new RegExp("(?:^|;\\s*)" + n + "=([a-z]+)").exec(document.cookie || ""); return m ? m[1] : null; }
  function lang() {
    var l = window.__cedwynLang || cookie("ghf_lang"); if (!l) { try { l = localStorage.getItem("ghf_lang"); } catch (e) {} }
    if (!/^(en|cy|es)$/.test(l || "")) l = de.getAttribute("data-ghf-lang-default");
    return /^(en|cy|es)$/.test(l || "") ? l : "en";
  }
  function tr(k, l) { var v = T[k]; if (!v) return null; return v[l || lang()] || v.en; }
  function setLang(k) {
    window.__cedwynLang = k;
    if (window.GHFLang && window.GHFLang.set) { window.GHFLang.set(k); return; }
    try { localStorage.setItem("ghf_lang", k); } catch (e) {}
    try { document.cookie = "ghf_lang=" + k + "; path=/; max-age=31536000; SameSite=Lax" + (location.protocol === "https:" ? "; Secure" : ""); } catch (e) {}
    paint();
  }
  function paint() {
    var l = lang(), q = document.querySelectorAll("[data-i18n]"), i, el, v, n = de.getAttribute("data-cedwyn-n") || "37";
    for (i = 0; i < q.length; i++) { el = q[i]; v = tr(el.getAttribute("data-i18n"), l); if (v != null) { v = v.replace("{n}", n); if (v.indexOf("\u27E6") < 0) el.textContent = v; else el.innerHTML = v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\u27E6/g, '<span class="unsub">').replace(/\u27E7/g, "</span>"); } }
    q = document.querySelectorAll("[data-i18n-ph]"); for (i = 0; i < q.length; i++) { v = tr(q[i].getAttribute("data-i18n-ph"), l); if (v) q[i].setAttribute("placeholder", v); }
    q = document.querySelectorAll("[data-i18n-al]"); for (i = 0; i < q.length; i++) { v = tr(q[i].getAttribute("data-i18n-al"), l); if (v) q[i].setAttribute("aria-label", v); }
    q = document.querySelectorAll("[data-cedwyn-lang]"); for (i = 0; i < q.length; i++) q[i].setAttribute("aria-pressed", q[i].getAttribute("data-cedwyn-lang") === l ? "true" : "false");
    if (document.body && document.body.hasAttribute("data-cedwyn-page")) de.setAttribute("lang", l === "en" ? "en-GB" : l);
    var f = document.getElementById("ghf-agent-footer");
    if (f && T.f_log) { var h = f.querySelector("h2"); if (h) h.textContent = tr("f_log", l); var st = f.querySelector(".gaf-log p strong"); if (st) st.textContent = tr("f_cur", l); }
  }
  function css() {
    if (document.getElementById("cedwyn-sec-css")) return;
    var s = document.createElement("style"); s.id = "cedwyn-sec-css";
    s.textContent = ".cedwyn-rib{position:relative;z-index:5;display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:0;padding:8px 40px 8px 12px;" +
      "font:500 13px/1.35 Barlow,system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;letter-spacing:.02em;color:#fff;background:#111;border-top:3px solid var(--cs-a);border-bottom:3px solid var(--cs-b);text-align:left}" +
      ".cedwyn-rib *{box-sizing:border-box}.cedwyn-rib a{color:#fff;text-decoration:none;border:1px solid rgba(255,255,255,.45);border-radius:999px;padding:4px 10px;white-space:nowrap;min-height:30px;display:inline-flex;align-items:center}" +
      ".cedwyn-rib a:hover,.cedwyn-rib a:focus-visible{border-color:var(--cs-b);outline:none}.cedwyn-rib .cr-t{flex:1 1 100%;font-weight:600;text-decoration:none;border:0;padding:0;min-height:0;white-space:normal}" +
      ".cedwyn-rib .cr-x{position:absolute;top:6px;right:6px;width:30px;height:30px;border:0;background:none;color:#fff;font:400 20px/1 system-ui;cursor:pointer;opacity:.8}" +
      ".cedwyn-rib .cr-dot{display:inline-block;width:10px;height:10px;border-radius:50%;background:var(--cs-a);box-shadow:0 0 0 2px var(--cs-b);margin-right:8px;vertical-align:1px}" +
      "@media (min-width:783px){.cedwyn-rib .cr-t{flex:0 1 auto;margin-right:8px}}" +
      "html[data-ghf-mode=day] .cedwyn-rib{background:#fff;color:#111}html[data-ghf-mode=day] .cedwyn-rib a,html[data-ghf-mode=day] .cedwyn-rib .cr-x{color:#111;border-color:rgba(0,0,0,.35)}";
    (document.head || de).appendChild(s);
  }
  function lp() { return window.__cedwynLP || location.pathname; }
  function ribbon(tries) {
    if (!SEC || !document.body || document.querySelector(".cedwyn-rib") || document.body.hasAttribute("data-cedwyn-page")) return;
    var hd = document.querySelector(".ghf-v2");   // the shared 3-row header: the ribbon sits directly under it
    if (!hd && (tries || 0) < 20) { setTimeout(function () { ribbon((tries || 0) + 1); }, 150); return; }
    try { if (sessionStorage.getItem("cedwyn-rib-hide") === SEC) return; } catch (e) {}
    css();
    var r = document.createElement("div"), a = ACC[SEC], other = SEC === "wales" ? "argentina" : "wales";
    r.className = "cedwyn-rib ghf-ui"; r.setAttribute("data-no-translate", ""); r.setAttribute("role", "region");
    r.style.setProperty("--cs-a", a[0]); r.style.setProperty("--cs-b", a[1]);
    function link(href, key, cls) { var x = document.createElement("a"); x.setAttribute("href", href); x.setAttribute("data-i18n", key); if (cls) x.className = cls; r.appendChild(x); return x; }
    var t = link("/" + SEC + "/", SEC === "wales" ? "rib_w" : "rib_a", "cr-t"); t.insertBefore(document.createElement("span"), t.firstChild);
    if (SEC === "wales") { link("/wales/#shop", "rib_v"); link("/ebooks/", "rib_e"); }
    else { link("/argentina/#museum", "rib_mu"); link("/argentina/#retelling", "rib_re"); }
    var sw = document.createElement("a"), th = lp(); sw.setAttribute("href", "/" + other + (/^\/[^\/]+\//.test(th) ? th : "/") + location.search);
    sw.setAttribute("data-i18n", other === "wales" ? "w_name" : "a_name"); sw.className = "cr-sw"; r.appendChild(sw);
    var x = document.createElement("button"); x.type = "button"; x.className = "cr-x"; x.textContent = "\u00D7"; x.setAttribute("data-i18n-al", "rib_close");
    x.onclick = function () { try { sessionStorage.setItem("cedwyn-rib-hide", SEC); } catch (e) {} r.parentNode.removeChild(r); };
    r.appendChild(x); r.setAttribute("data-i18n-al", SEC === "wales" ? "w_name" : "a_name");
    if (hd && hd.parentNode) hd.parentNode.insertBefore(r, hd.nextSibling); else document.body.insertBefore(r, document.body.firstChild);
    paint();
    var dot = r.querySelector(".cr-t span"); if (dot) { dot.className = "cr-dot"; dot.setAttribute("aria-hidden", "true"); }
  }
  // keep the visitor inside the section: a theme link (/<theme>/...) followed from a sectioned page gains the section prefix
  function sectioned(h) { var m = /^\/(wales|argentina)\/([^\/?#]+)/.exec(h); return !!(m && THEMES.indexOf(m[2]) >= 0); }
  if (SECURL) document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[href]") : null; if (!a || a.target === "_blank" && false) return;
    var h = a.getAttribute("href"); if (!h || h.charAt(0) !== "/" || h.charAt(1) === "/") return;
    if (sectioned(h)) return;
    var x = h.split(/[\/?#]/)[1]; if (x && THEMES.indexOf(x) >= 0) a.setAttribute("href", "/" + SECURL + h);
  }, true);
  // notify-me forms: Cedwyn's own mailing list (26 Oct 2026, replaces Mailchimp). Sent only when the visitor submits; they get a
  // confirm email from cedwyn@bucklerfamily.estate and are added when they tap its link.
  function forms() {
    var q = document.querySelectorAll("form[data-cedwyn-notify]");
    [].forEach.call(q, function (f) {
      if (f.__cn) return; f.__cn = 1;
      f.addEventListener("submit", function (ev) {
        ev.preventDefault();
        var err = f.querySelector(".cn-err"), em = (f.EMAIL.value || "").trim(), nt = f.getAttribute("data-cedwyn-notify") || ""; err.hidden = true;
        if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em)) { err.textContent = tr("err_email"); err.hidden = false; return; }
        if (!f.querySelector(".cn-ok").checked) { err.textContent = tr("err_tick"); err.hidden = false; return; }
        var b = f.querySelector("[type=submit]"), done = false, hp = f.querySelector("input[name=website]");
        function fin(ok, m) { if (done) return; done = true; if (b) b.disabled = false;
          if (ok) { f.hidden = true; var d = f.parentNode.querySelector(".cn-done"); if (d) d.hidden = false; } else { err.textContent = m || tr("err_send"); err.hidden = false; } }
        if (b) b.disabled = true; setTimeout(function () { fin(false); }, 15000);
        fetch("/api/list/subscribe", { method: "POST", credentials: "omit", headers: { "content-type": "application/json" },
          body: JSON.stringify({ email: em, lang: lang(), topic: "notify-" + nt, source: location.pathname, website: hp ? hp.value : "" }) })
          .then(function (r) { return r.json().catch(function () { return {}; }); })
          .then(function (j) { fin(!!(j && j.ok), j && j.message); }, function () { fin(false); });
      });
    });
  }

  function wireLang() {
    var q = document.querySelectorAll("[data-cedwyn-lang]");
    [].forEach.call(q, function (b) { if (b.__cl) return; b.__cl = 1; b.addEventListener("click", function () { setLang(b.getAttribute("data-cedwyn-lang")); }); });
  }
  function go() { ribbon(0); wireLang(); forms(); paint(); }
  document.addEventListener("ghf-lang-change", function (e) { if (e && e.detail && e.detail.lang) window.__cedwynLang = e.detail.lang; paint(); });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", go); else go();
  window.addEventListener("load", paint);
  window.CedwynSection = { section: SEC, lang: lang, setLang: setLang, paint: paint, version: "1.0.0" };

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
})();
