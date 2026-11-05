/* Parcel story panel — reads the public-area CHILD SQLite database, not a hand-coded page chronology. */
(function () {
  'use strict';
  if (document.getElementById('cedwyn-parcel-panel')) return;

  var ROOT = '/_cedwyn/';
  function node(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = String(txt);
    return e;
  }
  function link(path, label) {
    if (!path || path.charAt(0) !== '/' || path.indexOf('//') === 0) return null;
    var a = node('a', '', label || path);
    a.href = path;
    return a;
  }
  function loadCatalogue() {
    if (window.Cedwyn && window.Cedwyn.sectionDb) return Promise.resolve(window.Cedwyn);
    return new Promise(function (resolve, reject) {
      var existing = document.querySelector('script[data-cedwyn-parcel-catalogue]');
      if (existing) { existing.addEventListener('load', function () { resolve(window.Cedwyn); }, { once: true }); existing.addEventListener('error', reject, { once: true }); return; }
      var s = document.createElement('script');
      s.src = ROOT + 'cat.js?v=1';
      s.setAttribute('data-cedwyn-parcel-catalogue', '1');
      s.onload = function () { if (window.Cedwyn && window.Cedwyn.sectionDb) resolve(window.Cedwyn); else reject(new Error('Catalogue API unavailable')); };
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  function currentTheme() {
    var scripts = document.querySelectorAll('script[src*="/_cedwyn/runtime.js"]');
    for (var i = 0; i < scripts.length; i++) {
      var t = scripts[i].getAttribute('data-theme');
      if (t) return t;
    }
    return location.pathname.split('/').filter(Boolean)[0] || '';
  }
  function resolveArea(doc) {
    var theme = currentTheme();
    var parts = location.pathname.split('/').filter(Boolean);
    var areas = doc.areas || [];
    // Match the rendered theme before the outer /wales/ or /patagonia/ section prefix.
    var byTheme = areas.find(function (a) {
      var aliases = a.aliases || [];
      return a.id === theme ||
        (a.path || '') === ('/' + theme + '/') ||
        aliases.indexOf('/' + theme + '/') >= 0;
    });
    if (byTheme) return byTheme;
    return areas.find(function (a) {
      var aliases = a.aliases || [];
      return (parts.length && a.id === parts[0]) ||
        (parts.length && aliases.indexOf('/' + parts[0] + '/') >= 0);
    }) || null;
  }
  function addStyles() {
    if (document.getElementById('cedwyn-parcel-css')) return;
    var style = node('style');
    style.id = 'cedwyn-parcel-css';
    style.textContent =
      '#cedwyn-parcel-panel{clear:both;display:block;box-sizing:border-box;width:100%;margin:1.25rem auto 0;padding:1rem clamp(.75rem,2.5vw,1.5rem);border-top:3px solid #ad4545;background:color-mix(in srgb,currentColor 3%,transparent);color:inherit;font:inherit;line-height:1.45}' +
      '#cedwyn-parcel-panel *{box-sizing:border-box}#cedwyn-parcel-panel .cpp-wrap{max-width:1200px;margin:0 auto}' +
      '#cedwyn-parcel-panel .cpp-head{display:flex;flex-wrap:wrap;gap:.45rem;align-items:center;margin:0 0 .65rem}' +
      '#cedwyn-parcel-panel .cpp-kicker{font-size:.75rem;letter-spacing:.06em;font-weight:800;text-transform:uppercase;opacity:.75}' +
      '#cedwyn-parcel-panel h2{font-size:1.25rem;line-height:1.25;margin:.1rem 0 .3rem}' +
      '#cedwyn-parcel-panel .cpp-grid{display:grid;grid-template-columns:minmax(170px,260px) minmax(0,1fr);gap:1rem;align-items:start}' +
      '#cedwyn-parcel-panel figure{margin:0;border:2px solid #ad4545;border-radius:7px;padding:.3rem;position:relative;min-width:0}' +
      '#cedwyn-parcel-panel figure img{display:block;width:100%;height:auto;max-height:300px;object-fit:cover;object-position:top}' +
      '#cedwyn-parcel-panel .cpp-tag{display:inline-block;font-size:.75rem;font-weight:800;border:1px solid #ad4545;border-radius:4px;padding:.18rem .4rem;margin:0 0 .35rem}' +
      '#cedwyn-parcel-panel figcaption,#cedwyn-parcel-panel .cpp-note{font-size:.84rem;opacity:.82;margin:.4rem 0 0}' +
      '#cedwyn-parcel-panel .cpp-links{display:flex;flex-wrap:wrap;gap:.75rem;margin:.6rem 0}' +
      '#cedwyn-parcel-panel details{margin:.75rem 0 0;border-top:1px solid color-mix(in srgb,currentColor 18%,transparent);padding-top:.55rem}' +
      '#cedwyn-parcel-panel summary{font-weight:750;cursor:pointer;padding:.25rem 0;min-height:32px}' +
      '#cedwyn-parcel-panel .cpp-table-wrap{overflow-x:auto;max-width:100%}#cedwyn-parcel-panel table{border-collapse:collapse;width:100%;min-width:620px;font-size:.86rem;margin:.4rem 0}' +
      '#cedwyn-parcel-panel th,#cedwyn-parcel-panel td{padding:.45rem .5rem;border:1px solid color-mix(in srgb,currentColor 18%,transparent);vertical-align:top;text-align:left}' +
      '#cedwyn-parcel-panel th{font-weight:750}#cedwyn-parcel-panel .cpp-status{font-size:.8rem;opacity:.8}' +
      '#cedwyn-parcel-panel .cpp-models{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:.5rem;margin:.5rem 0}' +
      '#cedwyn-parcel-panel .cpp-model{border:1px solid color-mix(in srgb,currentColor 22%,transparent);border-radius:5px;padding:.55rem}' +
      '#cedwyn-parcel-panel .cpp-model strong{display:block;margin-bottom:.2rem}' +
      '@media(max-width:560px){#cedwyn-parcel-panel .cpp-grid{grid-template-columns:1fr}#cedwyn-parcel-panel figure{max-width:290px}#cedwyn-parcel-panel{padding:.8rem .7rem}}';
    (document.head || document.documentElement).appendChild(style);
  }
  function makeTable(events, modelEvents, parcel) {
    var details = node('details', 'cpp-chronology');
    var summary = node('summary', '', 'Expand chronology · events for this webapp parcel');
    details.appendChild(summary);
    var wrap = node('div', 'cpp-table-wrap');
    var table = node('table');
    var thead = node('thead');
    var hr = node('tr');
    ['Date','Parcel / scope','Event','Status','Source'].forEach(function (x) { hr.appendChild(node('th','',x)); });
    thead.appendChild(hr); table.appendChild(thead);
    var body = node('tbody');
    (events || []).forEach(function (e) {
      body.appendChild(eventRow(e.date_text, e.scope || ('Webapp slot P' + String(parcel.slot).padStart(2,'0')), e.title, e.details, e.status, e.source_ev, e.source_path));
    });
    // Only show shared-model events in this slot's chronology after a verified model link exists.
    (modelEvents || []).filter(function (e) { return parcel && parcel.model_parcel_id && e.model_id === parcel.model_parcel_id; }).forEach(function (e) {
      body.appendChild(eventRow(e.date_text, e.model_id, e.title, e.details, e.status, (function(){try{return JSON.parse(e.source_evs_json||'[]').join(', ')}catch(_){return ''}})(), e.source_path));
    });
    table.appendChild(body); wrap.appendChild(table); details.appendChild(wrap);
    return details;
  }
  function makeSharedModelEventTable(modelEvents) {
    var details = node('details', 'cpp-chronology');
    details.appendChild(node('summary', '', 'Expand cross-parcel working chronology (A1 / A2 / B / C)'));
    details.appendChild(node('p','cpp-note','These entries are shared research context, not this webapp’s own chain of title unless and until a verified parcel link is assigned.'));
    var wrap = node('div', 'cpp-table-wrap');
    var table = node('table');
    var thead = node('thead');
    var hr = node('tr');
    ['Date','Model parcel','Event','Status','Source'].forEach(function (x) { hr.appendChild(node('th','',x)); });
    thead.appendChild(hr); table.appendChild(thead);
    var body = node('tbody');
    (modelEvents || []).forEach(function (e) {
      var source = '';
      try { source = JSON.parse(e.source_evs_json || '[]').join(', '); } catch (_) {}
      body.appendChild(eventRow(e.date_text,e.model_id,e.title,e.details,e.status,source,e.source_path));
    });
    table.appendChild(body); wrap.appendChild(table); details.appendChild(wrap);
    return details;
  }
  function eventRow(date, scope, title, detailsText, status, source, path) {
    var tr = node('tr');
    tr.appendChild(node('td','',date || 'Date not specified'));
    tr.appendChild(node('td','',scope || '—'));
    var td = node('td');
    td.appendChild(node('strong','',title || 'Untitled event'));
    if (detailsText) td.appendChild(node('p','',detailsText));
    tr.appendChild(td);
    tr.appendChild(node('td','cpp-status',status || 'Status not specified'));
    var sourceCell = node('td');
    if (source) sourceCell.appendChild(node('span','',source));
    if (path) {
      if (source) sourceCell.appendChild(node('span','',' · '));
      var a = link(path,'Open record / search route');
      if (a) sourceCell.appendChild(a);
    }
    tr.appendChild(sourceCell);
    return tr;
  }
  function render(area, parcel, events, models, modelEvents) {
    addStyles();
    var box = node('section');
    box.id = 'cedwyn-parcel-panel';
    box.setAttribute('aria-labelledby','cedwyn-parcel-title');
    var inner = node('div','cpp-wrap');
    var head = node('div','cpp-head');
    head.appendChild(node('span','cpp-kicker','Parcel story · parent catalogue + child database'));
    inner.appendChild(head);
    inner.appendChild(node('h2','', 'Parcel focus for this webapp: ' + (parcel.title || parcel.parcel_id)));
    var status = node('p','cpp-note','Working allocation P' + String(parcel.slot).padStart(2,'0') + '. A webapp slot is not a historical tithe number. Exact map outline and plot match remain pending.');
    inner.appendChild(status);

    var grid = node('div','cpp-grid');
    var fig = node('figure');
    fig.appendChild(node('span','cpp-tag','P' + String(parcel.slot).padStart(2,'0') + ' · outline pending'));
    var img = node('img');
    img.src = parcel.map_asset || '/parcels/poster.jpg';
    img.alt = 'Photograph of a page from the c.1841 tithe schedule. This is a source image, not a geographic map or verified parcel outline.';
    img.loading = 'lazy';
    fig.appendChild(img);
    fig.appendChild(node('figcaption','', 'Reference image only: historic plot and boundary have not yet been matched for this slot.'));
    grid.appendChild(fig);

    var copy = node('div');
    copy.appendChild(node('p','',parcel.summary || 'Parcel-specific history is awaiting mapping.'));
    copy.appendChild(node('p','cpp-note','Working parcel model: A = A1 (north woods) + A2 (house, buildings and garden). B = eastern/right-hand fields currently treated as the intended subject of the 1955 Order 14. C = separate green south of the house; possible Williams interest remains open.'));
    var links = node('div','cpp-links');
    var l1 = link('/parcels/','Open tithe source and 10-minute parcel explainer');
    var l2 = link('/research/missing-records/mr-0008/','1955 order, writ and execution return search');
    if (l1) links.appendChild(l1);
    if (l2) links.appendChild(l2);
    copy.appendChild(links);
    grid.appendChild(copy);
    inner.appendChild(grid);

    inner.appendChild(makeTable(events,modelEvents,parcel));
    var more = node('details','');
    more.appendChild(node('summary','','Expand the current A1 / A2 / B / C parcel model'));
    var cards = node('div','cpp-models');
    (models || []).forEach(function(m){
      var c = node('div','cpp-model');
      c.appendChild(node('strong','',m.label || m.model_id));
      c.appendChild(node('span','cpp-status',m.status || 'status pending'));
      c.appendChild(node('p','',m.description || ''));
      c.appendChild(node('p','cpp-note',m.limits || ''));
      cards.appendChild(c);
    });
    more.appendChild(cards); more.appendChild(makeSharedModelEventTable(modelEvents)); inner.appendChild(more);
    inner.appendChild(node('p','cpp-note','This panel is rendered from the current webapp’s child SQLite database. The parent catalogue stores the full 36-slot register and parcel-model records. The map overlay remains deliberately unclaimed until the original schedule, map and later deed plans can be matched.'));
    box.appendChild(inner);

    var foot = document.getElementById('ghf-agent-footer');
    if (foot && foot.parentNode) foot.parentNode.insertBefore(box,foot);
    else {
      var otherFooter = document.querySelector('body > footer, body footer');
      if (otherFooter && otherFooter.parentNode) otherFooter.parentNode.insertBefore(box,otherFooter);
      else document.body.appendChild(box);
    }
  }
  function start() {
    if (!document.body) return;
    fetch('/areas.json',{cache:'no-cache'}).then(function(r){if(!r.ok)throw new Error('area registry '+r.status);return r.json();}).then(function(doc){
      var area = resolveArea(doc);
      if (!area || area.built === false) return;
      return loadCatalogue().then(function(C){
        return C.sectionDb(area.id).then(function(db){
          return Promise.all([
            db.query('SELECT * FROM estate_parcels WHERE area_id=? LIMIT 1',[area.id]),
            db.query('SELECT * FROM parcel_events ORDER BY seq',[ ]),
            db.query('SELECT * FROM estate_parcel_model ORDER BY CASE model_id WHEN "A" THEN 0 WHEN "A1" THEN 1 WHEN "A2" THEN 2 WHEN "B" THEN 3 WHEN "C" THEN 4 ELSE 5 END',[]),
            db.query('SELECT * FROM estate_parcel_model_events ORDER BY model_id, seq',[])
          ]).then(function(rs){
            var parcel = (rs[0]||[])[0];
            if (!parcel) return;
            // Area child DBs only contain events for their own assigned story slot, so no client-side filtering is needed.
            render(area,parcel,rs[1]||[],rs[2]||[],rs[3]||[]);
          });
        });
      });
    }).catch(function(err){
      if (!document.getElementById('cedwyn-parcel-panel')) {
        var box=node('section',''); box.id='cedwyn-parcel-panel';
        box.appendChild(node('p','','Parcel-story panel could not read this page’s child database: '+(err && err.message ? err.message : 'database unavailable')+'.'));
        var foot=document.getElementById('ghf-agent-footer');
        if(foot&&foot.parentNode)foot.parentNode.insertBefore(box,foot);
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();