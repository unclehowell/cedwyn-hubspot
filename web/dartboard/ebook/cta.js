/*! ebook cta \u2014 "Get the e-book" card for the Great House Farm (T\u0177 Mawr) sites. Dependency-free.
 * Links to the shop page (never straight to checkout). Follows <html lang> (en / cy / es) set by ghf-lang.
 * Source: bucklerfamily.estate/ebook/cta.js \u00b7 v3 (20 Oct 2026: \u201cMore books\u201d line; v3 prices for the \u00a30.00 v0.01 / \u00a39.99 v0.02 edition ladder; v3.1 price first, \u00a30.00 not free) */
(function () {
  "use strict";
  if (window.__ghfEbookCta) return; window.__ghfEbookCta = 1;
  var h = location.hostname.replace(/^www\./, "");
  if (h === "bucklerfamily.estate" && /^\/(ebook\/?|$)/.test(location.pathname)) return;
  var SHOP = "https://bucklerfamily.estate/ebook/", BOOKS = "https://ebooks.bucklerfamily.estate/";
  var T = {
    en: { k: "The e-book", t: "Great House Farm \u2014 The Evidence Archive", d: "The evidence, history and heritage of Great House Farm (T\u0177 Mawr) in one searchable 2,064-page PDF, each record with its source.", b: "Get the e-book (\u00a34.99 \u2013 v0.0.2 \u00b7 \u00a30.00 \u2013 v0.0.1)", m: "More from the estate", mb: "More books", mbt: "Fraud, Concealment and Government Involvement \u00b7 The Disclosure Dartboard \u00b7 the Projects dossier \u00b7 all four for \u00a319.96 \u00b7 every book from \u00a30.00 \u2013 v0.0.1" },
    cy: { k: "Yr e-lyfr", t: "Great House Farm \u2014 Archif y Dystiolaeth", d: "Tystiolaeth, hanes a threftadaeth Great House Farm (T\u0177 Mawr) mewn un PDF chwiliadwy 2,064 tudalen, pob cofnod gyda\u2019i ffynhonnell.", b: "Prynwch yr e-lyfr (\u00a34.99 \u2013 v0.0.2 \u00b7 \u00a30.00 \u2013 v0.0.1)", m: "Mwy o\u2019r yst\u00e2d", mb: "Rhagor o lyfrau", mbt: "Fraud, Concealment and Government Involvement \u00b7 The Disclosure Dartboard \u00b7 dosbarth y Prosiectau \u00b7 y pedwar am \u00a319.96 \u00b7 pob llyfr o \u00a30.00 \u2013 v0.0.1" },
    es: { k: "El libro electr\u00f3nico", t: "Great House Farm \u2014 El Archivo de Pruebas", d: "Las pruebas, la historia y el patrimonio de Great House Farm (T\u0177 Mawr) en un PDF de 2064 p\u00e1ginas con b\u00fasqueda, cada registro con su fuente.", b: "Consigue el libro electr\u00f3nico (4,99 \u00a3 \u2013 v0.0.2 \u00b7 0,00 \u00a3 \u2013 v0.0.1)", m: "M\u00e1s de la finca", mb: "M\u00e1s libros", mbt: "Fraud, Concealment and Government Involvement \u00b7 The Disclosure Dartboard \u00b7 el dosier de Proyectos \u00b7 los cuatro por 19,96 \u00a3 \u00b7 cada libro desde 0,00 \u00a3 \u2013 v0.0.1" }
  };
  var SITES = [
    ["bucklerfamily.estate", "https://bucklerfamily.estate/", { en: "Campus", cy: "Campws", es: "Campus" }],
    ["bpvsbuckler.bucklerfamily.estate", "https://bpvsbuckler.bucklerfamily.estate/", { en: "Timeline", cy: "Llinell amser", es: "Cronolog\u00eda" }],
    ["wayback.bucklerfamily.estate", "https://wayback.bucklerfamily.estate/", { en: "Wayback archive", cy: "Archif Wayback", es: "Archivo Wayback" }],
    ["projects.bucklerfamily.estate", "https://projects.bucklerfamily.estate/", { en: "Projects", cy: "Prosiectau", es: "Proyectos" }],
    ["greathousefarmwiki.wordpress.com", "https://greathousefarmwiki.wordpress.com/", { en: "Legal Wiki", cy: "Wici Cyfreithiol", es: "Wiki jur\u00eddica" }]
  ];
  function lang() { var l = (document.documentElement.getAttribute("lang") || "en").slice(0, 2).toLowerCase(); return T[l] ? l : "en"; }
  var box;
  function render() {
    var L = lang(), t = T[L];
    var more = SITES.filter(function (s) { return s[0] !== h; }).slice(0, 4).map(function (s) {
      return '<a href="' + s[1] + '" style="color:inherit;opacity:.85;white-space:nowrap">' + s[2][L] + "</a>";
    }).join("");
    box.innerHTML =
      '<div style="font-size:12px;letter-spacing:.14em;text-transform:uppercase;opacity:.75;margin:0 0 4px">' + t.k + "</div>" +
      '<div style="font-weight:800;font-size:18px;line-height:1.25;margin:0 0 6px">' + t.t + "</div>" +
      '<p style="margin:0 0 12px;font-size:15px;line-height:1.45;opacity:.9">' + t.d + "</p>" +
      '<a href="' + SHOP + '" style="display:inline-block;background:#ffd700;color:#1a1a0d;font-weight:800;font-size:16px;padding:11px 16px;border-radius:8px;text-decoration:none">' + t.b + " \u2192</a>" +
      (h === "ebooks.bucklerfamily.estate" ? "" : '<div style="margin-top:12px;font-size:14px;line-height:1.45"><a href="' + BOOKS + '" style="color:#ffd700;font-weight:700;text-decoration:none">' + t.mb + " \u2192</a> " + '<span style="opacity:.85">' + t.mbt + "</span></div>") +
      '<div style="margin-top:12px;font-size:13px;line-height:1.5;display:flex;flex-wrap:wrap;gap:4px 12px"><span style="opacity:.7">' + t.m + ":</span>" + more + "</div>";
  }
  function mount() {
    if (document.getElementById("ghf-ebook-cta")) return;
    box = document.createElement("aside");
    box.id = "ghf-ebook-cta"; box.setAttribute("data-no-translate", ""); box.setAttribute("translate", "no");
    box.setAttribute("aria-label", "Great House Farm e-book");
    box.style.cssText = "box-sizing:border-box;max-width:760px;margin:28px auto;padding:16px 18px;border:1px solid rgba(255,215,0,.45);border-left:5px solid #ffd700;border-radius:10px;background:#12160e;color:#ece9df;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,Arial,sans-serif;text-align:left;clear:both;position:relative;z-index:1";
    render();
    var anchor = document.querySelector("[data-ghf-ebook-cta]") || document.querySelector("body > footer, footer:last-of-type");
    if (anchor && anchor.hasAttribute && anchor.hasAttribute("data-ghf-ebook-cta")) anchor.appendChild(box);
    else if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(box, anchor);
    else { var w = document.createElement("div"); w.style.cssText = "padding:0 14px"; w.appendChild(box); document.body.appendChild(w); }
    new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["lang"] });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
