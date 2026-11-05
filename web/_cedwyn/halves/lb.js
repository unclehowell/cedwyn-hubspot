/*! lb.js v1.0.0 (27 Oct 2026) - the shared image lightbox of the /wales/ and /argentina/ pages (tools/halves.py adds it).
 * Every element marked data-lb on the page is a thumbnail: a tap or click (or Enter / Space) opens it full width in a
 * full-screen dialog, captioned with the image's own title. Swipe left / right, the arrow keys or the on-screen arrows
 * move through ALL the page's images and loop round (last -> first, first -> last). Swipe down, Escape, the X or a tap
 * on the dark backdrop closes it. Neighbours are preloaded. Focus stays inside the dialog and returns to the thumbnail.
 * No libraries, no outside requests. - Sion's Tab agent */
(function () {
  "use strict";
  if (window.__cedwynLb) return; window.__cedwynLb = 1;
  var L = { en: ["Close", "Previous image", "Next image", "Image viewer"],
            cy: ["Cau", "Llun blaenorol", "Llun nesaf", "Gwyliwr lluniau"],
            es: ["Cerrar", "Imagen anterior", "Imagen siguiente", "Visor de imágenes"] };
  function lang() { var l = (document.documentElement.getAttribute("lang") || window.__cedwynLang || "en").slice(0, 2); return L[l] ? l : "en"; }
  function items() { return [].slice.call(document.querySelectorAll("[data-lb]")); }
  function imgOf(el) { return el.tagName === "IMG" ? el : el.querySelector("img"); }
  function full(el) { var i = imgOf(el); return el.getAttribute("data-lb") || (i && (i.getAttribute("data-lb-full") || i.currentSrc || i.src)) || ""; }
  function cap(el) {
    var c = el.getAttribute("data-lb-cap"); if (c) return c;
    var f = el.closest("figure"), fc = f && f.querySelector("figcaption"); if (fc && fc.textContent.trim()) return fc.textContent.trim();
    var s = el.closest(".hv-stop"), h = s && s.querySelector("h3"); if (h && h.textContent.trim()) return h.textContent.trim();
    var i = imgOf(el); return (i && i.getAttribute("alt")) || "";
  }
  function altOf(el) { var i = imgOf(el); return (i && i.getAttribute("alt")) || cap(el); }

  var box, pic, cnt, capEl, bPrev, bNext, bClose, list = [], cur = 0, opener = null, preload = [];
  function btn(cls, txt) { var b = document.createElement("button"); b.type = "button"; b.className = "cwlb-b " + cls; b.textContent = txt; return b; }
  function build() {
    box = document.createElement("div"); box.className = "cwlb"; box.hidden = true;
    box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true");
    var st = document.createElement("div"); st.className = "cwlb-st";
    pic = document.createElement("img"); pic.className = "cwlb-i"; pic.decoding = "async"; pic.draggable = false;
    st.appendChild(pic);
    var bar = document.createElement("div"); bar.className = "cwlb-bar";
    capEl = document.createElement("p"); capEl.className = "cwlb-c"; capEl.id = "cwlb-c";
    cnt = document.createElement("span"); cnt.className = "cwlb-n"; cnt.setAttribute("aria-live", "polite");
    bar.appendChild(capEl); bar.appendChild(cnt);
    bPrev = btn("cwlb-p", "\u2039"); bNext = btn("cwlb-x", "\u203A"); bClose = btn("cwlb-q", "\u00D7");
    box.appendChild(st); box.appendChild(bar); box.appendChild(bPrev); box.appendChild(bNext); box.appendChild(bClose);
    box.setAttribute("aria-describedby", "cwlb-c");
    document.body.appendChild(box);
    bPrev.addEventListener("click", function () { go(cur - 1); });
    bNext.addEventListener("click", function () { go(cur + 1); });
    bClose.addEventListener("click", close);
    st.addEventListener("click", function (e) { if (e.target === st || (e.target === pic && !onPicture(e))) close(); });   // the dark backdrop around the picture
    box.addEventListener("keydown", key);
    touch(st);
  }
  function onPicture(e) {   // object-fit: contain leaves dark bands inside the image box; a tap there is a backdrop tap
    var r = pic.getBoundingClientRect(), nw = pic.naturalWidth, nh = pic.naturalHeight; if (!nw || !nh) return false;
    var s = Math.min(r.width / nw, r.height / nh), w = nw * s, h = nh * s, x = r.left + (r.width - w) / 2, y = r.top + (r.height - h) / 2;
    return e.clientX >= x && e.clientX <= x + w && e.clientY >= y && e.clientY <= y + h;
  }
  function label() { var t = L[lang()]; bClose.setAttribute("aria-label", t[0]); bPrev.setAttribute("aria-label", t[1]); bNext.setAttribute("aria-label", t[2]); box.setAttribute("aria-label", t[3]); }
  function show(i) {
    var n = list.length; if (!n) return;
    cur = ((i % n) + n) % n; var el = list[cur];
    pic.style.transform = ""; pic.style.opacity = "";
    pic.src = full(el); pic.alt = altOf(el);
    capEl.textContent = cap(el); cnt.textContent = (cur + 1) + " / " + n;
    var multi = n > 1; bPrev.hidden = !multi; bNext.hidden = !multi;
    preload = [cur + 1, cur - 1].map(function (j) { var im = new Image(); im.decoding = "async"; im.src = full(list[((j % n) + n) % n]); return im; });
  }
  function go(i) { show(i); }
  function open(el) {
    list = items(); var i = list.indexOf(el); if (i < 0) return;
    if (!box) build(); label(); opener = el;
    box.hidden = false; document.documentElement.classList.add("cwlb-on");
    show(i); bClose.focus({ preventScroll: true });
  }
  function close() {
    if (!box || box.hidden) return;
    box.hidden = true; document.documentElement.classList.remove("cwlb-on"); pic.removeAttribute("src");
    if (opener && opener.focus) try { opener.focus({ preventScroll: true }); } catch (e) {}
    opener = null;
  }
  function key(e) {
    if (e.key === "Escape" || e.key === "Esc") { e.preventDefault(); close(); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(cur + 1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(cur - 1); }
    else if (e.key === "Tab") {   // focus trap: cycle through the dialog's visible buttons
      var f = [bPrev, bNext, bClose].filter(function (b) { return !b.hidden; }), k = f.indexOf(document.activeElement);
      e.preventDefault(); f[(k + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus();
    }
  }
  function touch(st) {
    var x0 = 0, y0 = 0, dx = 0, dy = 0, on = false;
    st.addEventListener("touchstart", function (e) { if (e.touches.length !== 1) { on = false; return; } on = true; x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; dx = dy = 0; pic.style.transition = "none"; }, { passive: true });
    st.addEventListener("touchmove", function (e) {
      if (!on) return; dx = e.touches[0].clientX - x0; dy = e.touches[0].clientY - y0;
      if (Math.abs(dx) > Math.abs(dy)) pic.style.transform = "translateX(" + dx + "px)";
      else if (dy > 0) { pic.style.transform = "translateY(" + dy + "px)"; pic.style.opacity = String(Math.max(.3, 1 - dy / 400)); }
      e.preventDefault();
    }, { passive: false });
    st.addEventListener("touchend", function () {
      if (!on) return; on = false; pic.style.transition = "";
      var ax = Math.abs(dx), ay = Math.abs(dy);
      if (ax > 45 && ax > ay) go(cur + (dx < 0 ? 1 : -1));        // swipe left = next, swipe right = previous
      else if (dy > 90 && ay > ax) close();                        // swipe down = close
      else { pic.style.transform = ""; pic.style.opacity = ""; }
    });
  }
  function wire(el) {
    if (el.__lb) return; el.__lb = 1;
    if (!/^(A|BUTTON)$/.test(el.tagName)) { el.setAttribute("tabindex", "0"); el.setAttribute("role", "button"); }
    if (!el.getAttribute("aria-label") && el.tagName !== "IMG") el.setAttribute("aria-label", altOf(el));
    el.setAttribute("aria-haspopup", "dialog");
  }
  function init() { items().forEach(wire); }
  // capture phase: the tap opens the viewer and goes no further (the thumbnail's plain link is the no-script fallback)
  document.addEventListener("click", function (e) {
    var el = e.target && e.target.closest ? e.target.closest("[data-lb]") : null;
    if (!el || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault(); e.stopPropagation(); open(el);
  }, true);
  document.addEventListener("keydown", function (e) {
    var el = e.target; if (!el || !el.hasAttribute || !el.hasAttribute("data-lb") || el.tagName === "A" || el.tagName === "BUTTON") return;
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(el); }
  });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init); else init();
  window.cedwynLightbox = { open: function (i) { var l = items(); if (l[i]) open(l[i]); }, close: close, next: function () { go(cur + 1); }, prev: function () { go(cur - 1); } };
})();
