/* clamp.js v3 - the three-line paragraph clamp (v1/v2, 26-27 Oct 2026) is replaced by the screen-height "Read more" of
   cw-graph.js (asked for 01:27 GMT 30 Oct 2026: pages load with no vertical scroll, text clipped at 100vh, more only on
   "Read more", further text loaded in chunks). This file now only loads cw-graph.js for pages that still reference it.
   - Cedwyn editors */
(function () {
  if (window.__cwClamp) return; window.__cwClamp = 3;
  if (window.__cwGraph || document.querySelector('script[src*="/_cedwyn/cw-graph.js"]')) return;
  var s = document.createElement('script'); s.src = '/_cedwyn/cw-graph.js?v=1.2.1'; s.defer = true;
  (document.head || document.documentElement).appendChild(s);
})();
