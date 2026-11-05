/* Level 1 artifacts / Level 2 observations browser.
   Source: the catalogue database; theme slice first, central fallback second.
   All displayed record text is inserted as text, never as executable markup. */
(function () {
  'use strict';
  var root = document.querySelector('[data-cedwyn-evidence-browser]');
  if (!root) return;
  var pageSize = 50, offset = 0, mode = 'artifacts', db = null, dbSource = '', coverageText = '', busy = false, exhausted = false;
  root.innerHTML = [
    '<section class="cw-eb" aria-labelledby="cw-eb-title">',
    '<style>',
    '.cw-eb{margin:1.4rem 0 2rem;color:var(--wiki-text,#202122);font:inherit}',
    '.cw-eb *{box-sizing:border-box}',
    '.cw-eb .cw-eb-intro{color:var(--wiki-muted,#54595d);max-width:78ch}',
    '.cw-eb .cw-eb-tabs{display:flex;flex-wrap:wrap;gap:.5rem;margin:1rem 0 .75rem}',
    '.cw-eb button,.cw-eb input{font:inherit;color:inherit;border:1px solid var(--wiki-border,#a2a9b1);background:var(--wiki-paper,#fff);border-radius:3px;padding:.5rem .65rem}',
    '.cw-eb button{cursor:pointer}.cw-eb button[aria-pressed="true"]{font-weight:700;border-bottom:3px solid var(--wiki-link,#0645ad)}',
    '.cw-eb .cw-eb-search{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin:.5rem 0 1rem}',
    '.cw-eb .cw-eb-search input{flex:1;min-width:14rem}.cw-eb .cw-eb-status{font-size:.86rem;color:var(--wiki-muted,#54595d);margin:.5rem 0}',
    '.cw-eb .cw-eb-card{border:1px solid var(--wiki-soft-border,#c8ccd1);padding:1rem;margin:.8rem 0;background:var(--wiki-paper,#fff);min-width:0}',
    '.cw-eb .cw-eb-card h3{font-family:Georgia,"Times New Roman",serif;font-size:1.18rem;line-height:1.35;margin:0 0 .25rem;overflow-wrap:anywhere}',
    '.cw-eb .cw-eb-meta{font-size:.82rem;color:var(--wiki-muted,#54595d);margin:.2rem 0 .7rem;overflow-wrap:anywhere}',
    '.cw-eb .cw-eb-field{margin:.7rem 0}.cw-eb .cw-eb-field strong{display:block;margin-bottom:.12rem}',
    '.cw-eb .cw-eb-field p{margin:.1rem 0;white-space:pre-wrap;overflow-wrap:anywhere}',
    '.cw-eb .cw-eb-note{border-left:3px solid var(--wiki-border,#a2a9b1);padding:.25rem .7rem;margin:.6rem 0}',
    '.cw-eb .cw-eb-links{display:flex;flex-wrap:wrap;gap:.7rem;margin:.5rem 0}',
    '.cw-eb .cw-eb-links a,.cw-eb a{color:var(--wiki-link,#0645ad);text-decoration:underline}',
    '.cw-eb .cw-eb-chip{font-size:.75rem;padding:.08rem .3rem;border:1px solid var(--wiki-border,#a2a9b1);border-radius:2px}',
    '.cw-eb .cw-eb-ref{padding:.45rem 0;border-top:1px solid var(--wiki-soft-border,#c8ccd1)}',
    '.cw-eb .cw-eb-existing{border:1px solid var(--wiki-soft-border,#c8ccd1);padding:.55rem .7rem;margin:.8rem 0;background:var(--wiki-bg,#f8f9fa)}',
    '.cw-eb .cw-eb-existing summary{cursor:pointer;font-weight:600}',
    '.cw-eb .cw-eb-existing pre{font:13px/1.5 ui-monospace,SFMono-Regular,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:24rem;overflow:auto;margin:.6rem 0 0}',
    '.cw-eb ul{padding-left:1.4rem}.cw-eb li{margin:.2rem 0}',
    '.cw-eb .cw-eb-empty{padding:.8rem;border:1px dashed var(--wiki-border,#a2a9b1)}',
    '</style>',
    '<h2 id="cw-eb-title">Evidence catalogue: artifacts and observations</h2>',
    '<p class="cw-eb-intro">Level 1 contains the source artifacts. Level 2 contains observations derived from one or more artifacts. Description, transcription and interpretation are separate fields; an unassessed field is marked as such rather than guessed.</p>',
    '<p class="cw-eb-coverage" data-coverage>Loading catalogue coverage…</p>',
    '<div class="cw-eb-tabs" role="group" aria-label="Evidence hierarchy">',
    '<button type="button" data-mode="artifacts" aria-pressed="true">Level 1 · Artifacts</button>',
    '<button type="button" data-mode="observations" aria-pressed="false">Level 2 · Observations</button>',
    '</div>',
    '<form class="cw-eb-search" role="search"><label for="cw-eb-query">Search this level</label><input id="cw-eb-query" type="search" placeholder="EV ID, title, wording or subject"><button type="submit">Search</button><button type="button" data-reset>Reset</button></form>',
    '<p class="cw-eb-status" role="status" aria-live="polite" data-status>Connecting to the catalogue…</p>',
    '<div data-results></div>',
    '<div class="cw-eb-links"><button type="button" data-more hidden>Load more</button><a href="/wiki/observations/">Open all observation pages</a></div>',
    '</section>'
  ].join('');
  var hasCsscpsg = false;
  var status = root.querySelector('[data-status]');
  var results = root.querySelector('[data-results]');
  var queryInput = root.querySelector('#cw-eb-query');
  var moreButton = root.querySelector('[data-more]');

  function el(tag, cls, value) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (value !== undefined && value !== null) node.textContent = String(value);
    return node;
  }
  function field(parent, label, value, state) {
    var wrap = el('div', 'cw-eb-field');
    wrap.appendChild(el('strong', '', label));
    if (state) wrap.appendChild(el('span', 'cw-eb-chip', state.replace(/_/g, ' ')));
    var p = el('p', '', value || 'Not yet entered or assessed.');
    wrap.appendChild(p); parent.appendChild(wrap);
  }
  function link(parent, href, label) {
    if (!href) return;
    var a = el('a', '', label);
    a.href = href;
    parent.appendChild(a);
  }
  function addText(parent, tag, text, cls) {
    parent.appendChild(el(tag, cls || '', text || ''));
  }
  function safePath(path) {
    if (!path || typeof path !== 'string') return '';
    return path.charAt(0) === '/' ? path : '/' + path;
  }
  function artifactCard(r) {
    var card = el('article', 'cw-eb-card');
    var title = r.title || r.ev || 'Untitled catalogue record';
    card.appendChild(el('h3', '', (r.ev ? r.ev + ' — ' : '') + title));
    card.appendChild(el('p', 'cw-eb-meta',
      'Grade: ' + (r.evidence_grade == null ? 'not assessed' : r.evidence_grade) +
      ' · Source verification: ' + (r.source_verification_status || 'not_assessed') +
      (r.independent_origin_id ? ' · Origin: ' + r.independent_origin_id : '')));
    var links = el('div', 'cw-eb-links');
    link(links, safePath(r.path), 'Open catalogue entry');
    card.appendChild(links);
    field(card, 'Neutral description', r.description, r.description_status);
    field(card, 'Transcription / source wording', r.transcript, r.transcript_status);
    field(card, 'Interpretation (separate from the artifact)', r.interpretation, r.interpretation_status);
    if (r.grade_note) {
      var note = el('div', 'cw-eb-note');
      note.appendChild(el('strong', '', 'Provenance / assessment note'));
      note.appendChild(el('p', '', r.grade_note));
      card.appendChild(note);
    }
    if (r.limitations) field(card, 'Limits and unresolved checks', r.limitations, '');
    if (r.csscpsg_json) {
      var cs = null;
      try { cs = JSON.parse(r.csscpsg_json); } catch (_) {}
      if (cs && (cs.scores || cs.result)) {
        var csBox = el('div', 'cw-eb-note cw-eb-csscpsg');
        csBox.appendChild(el('strong', '', 'CSSCPSG structural reading (S1-S6)'));
        var ruleNames = { S1: 'Scope', S2: 'Party', S3: 'Agency', S4: 'Term shift', S5: 'Text gap', S6: 'Inconsistency' };
        if (cs.scores) {
          var csList = el('ul', '');
          Object.keys(ruleNames).forEach(function (k) {
            if (!(k in cs.scores)) return;
            var li = el('li', '');
            var why = (cs.why && cs.why[k]) ? ' - ' + cs.why[k] : '';
            li.textContent = k + ' ' + ruleNames[k] + ': ' + cs.scores[k] + why;
            csList.appendChild(li);
          });
          csBox.appendChild(csList);
        }
        if (cs.result) {
          csBox.appendChild(el('p', '', cs.result.compliant
            ? 'Read against rules S1-S6: no breach recorded for this record.'
            : 'Recorded as not compliant' + (cs.result.reason ? ': ' + cs.result.reason : '')));
        }
        if (cs.timing && cs.timing.length) {
          if (cs.timing_note) csBox.appendChild(el('p', 'cw-eb-meta', 'Timing note: ' + cs.timing_note));
          var tList = el('ul', '');
          cs.timing.forEach(function (t) {
            var li = el('li', '');
            li.textContent = 'Timing - ' + t.event + ': ' + t.score + (t.why ? ' - ' + t.why : '');
            tList.appendChild(li);
          });
          csBox.appendChild(tList);
        }
        if (cs.S != null || cs.T != null || cs.D != null) {
          csBox.appendChild(el('p', 'cw-eb-meta',
            'S = ' + (cs.S != null ? cs.S : '?') + ' · T = ' + (cs.T != null ? cs.T : '?') +
            ' · D = S x (1 + T) = ' + (cs.D != null ? cs.D : '?')));
        }
        if (cs.port || cs.derived) {
          csBox.appendChild(el('p', 'cw-eb-meta',
            'Port: ' + (cs.port || 'not stated') +
            (cs.derived ? ' · derived fields (' + cs.derived.fields.join(', ') + ') added by ' + cs.derived.by + ': ' + cs.derived.basis : '')));
        }
        if (cs.unassessed_rules && cs.unassessed_rules.length) {
          csBox.appendChild(el('p', 'cw-eb-meta', 'Rules not yet assessed: ' + cs.unassessed_rules.join(', ')));
        }
        if (cs.score_completeness) {
          csBox.appendChild(el('p', 'cw-eb-meta', 'Score completeness: ' + cs.score_completeness));
        }
        csBox.appendChild(el('p', 'cw-eb-meta', cs.caveat || 'A mark is an observation about the record, not a finding of wrongdoing.'));
        if (cs.source) csBox.appendChild(el('p', 'cw-eb-meta', 'Source: ' + cs.source));
        card.appendChild(csBox);
      }
    }
    if (r.catalogue_page_text) {
      var existing = el('details', 'cw-eb-existing');
      existing.appendChild(el('summary', '', 'Existing catalogue page text · not a source transcription'));
      existing.appendChild(el('pre', '', r.catalogue_page_text));
      if (r.catalogue_text_truncated) existing.appendChild(el('p', 'cw-eb-meta', 'The indexed page text is truncated; open the catalogue entry for the full page.'));
      card.appendChild(existing);
    }
    return card;
  }
  async function observationCard(r) {
    var card = el('article', 'cw-eb-card');
    card.appendChild(el('h3', '', r.id + ' — ' + r.title));
    card.appendChild(el('p', 'cw-eb-meta', (r.observation_type || 'observation').replace(/_/g, ' ') + ' · ' + (r.status || 'status not set')));
    card.appendChild(el('p', '', r.summary || 'No summary entered.'));
    field(card, 'Analysis', r.analysis, '');
    field(card, 'Limits / what this does not establish', r.limits, '');
    var tests = [];
    try { tests = JSON.parse(r.test_questions_json || '[]'); } catch (_) {}
    if (tests.length) {
      card.appendChild(el('strong', '', 'Tests and questions'));
      var ul = el('ul');
      tests.forEach(function (t) { ul.appendChild(el('li', '', t)); });
      card.appendChild(ul);
    }
    var refs = await db.query(
      'SELECT r.ev,r.path,r.role,r.note,ec.title FROM observation_refs r LEFT JOIN evidence_catalogue ec ON ec.ev=r.ev WHERE r.observation_id=? ORDER BY r.seq',
      [r.id]
    );
    if (refs.length) {
      card.appendChild(el('strong', '', 'Underlying artifact references'));
      refs.forEach(function (ref) {
        var item = el('div', 'cw-eb-ref');
        var label = (ref.ev ? ref.ev + ' — ' : '') + (ref.title || ref.role || ref.path || 'Referenced record');
        link(item, safePath(ref.path), label);
        if (ref.role) addText(item, 'span', ' · ' + ref.role);
        if (ref.note) addText(item, 'p', ref.note);
        card.appendChild(item);
      });
    } else {
      card.appendChild(el('p', 'cw-eb-meta', 'No artifact references are linked yet.'));
    }
    var links = el('div', 'cw-eb-links');
    link(links, safePath(r.page_path), 'Open observation page');
    link(links, safePath(r.related_page), 'Related existing analysis');
    card.appendChild(links);
    return card;
  }
  /* 30 Oct 2026 cold-load fix: the human catalogue view must fetch the catalogue
     client itself - pages do not include cat.js in their markup and agent-tools
     loads it only for agent invocations, so a first load() before any client
     existed used to fail with 'Catalogue client did not load'. Awaits the script
     load event (no timers, no blind retry); a genuine failure keeps the designed
     degradation message. */
  var clientPromise = null;
  function clientReady() {
    if (window.Cedwyn && typeof window.Cedwyn.db === 'function') return Promise.resolve(window.Cedwyn);
    if (clientPromise) return clientPromise;
    clientPromise = new Promise(function (resolve, reject) {
      var s = document.createElement('script');
      s.src = '/_cedwyn/cat.js';
      s.async = true;
      s.onload = function () { resolve(window.Cedwyn); };
      s.onerror = function () { reject(new Error('Could not load /_cedwyn/cat.js')); };
      (document.head || document.documentElement).appendChild(s);
    }).then(function (c) {
      if (c && typeof c.db === 'function') return c;
      clientPromise = null;
      throw new Error('Catalogue client did not load.');
    }, function (err) {
      clientPromise = null;
      throw err;
    });
    return clientPromise;
  }
  async function openDb() {
    if (db) return db;
    if (!window.Cedwyn || typeof window.Cedwyn.db !== 'function') await clientReady();
    if (typeof window.Cedwyn.sectionDb === 'function') {
      try { db = await window.Cedwyn.sectionDb('wiki'); dbSource = 'Wiki section database'; return db; } catch (e) { /* central fallback below */ }
    }
    db = await window.Cedwyn.db();
    dbSource = 'central catalogue database (section slice unavailable)';
    return db;
  }
  async function load(reset) {
    if (busy) return;
    busy = true;
    if (reset) { offset = 0; exhausted = false; results.replaceChildren(); }
    status.textContent = 'Reading ' + (mode === 'artifacts' ? 'Level 1 artifacts' : 'Level 2 observations') + ' from the catalogue database…';
    moreButton.hidden = true;
    try {
      await openDb();
      try {
        var cols = await db.query("SELECT name FROM pragma_table_info('artifact_assessments')", []);
        hasCsscpsg = cols.some(function (c) { return c.name === 'csscpsg_json'; });
      } catch (e) { hasCsscpsg = false; }
      if (!coverageText) {
        var cov = await db.query(
          "SELECT COUNT(*) AS total, " +
          "SUM(CASE WHEN trim(COALESCE(aa.description,''))<>'' THEN 1 ELSE 0 END) AS described, " +
          "SUM(CASE WHEN trim(COALESCE(aa.transcript,''))<>'' THEN 1 ELSE 0 END) AS transcribed, " +
          "SUM(CASE WHEN trim(COALESCE(aa.interpretation,''))<>'' THEN 1 ELSE 0 END) AS interpreted " +
          "FROM evidence_catalogue ec LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev"
        );
        var cv = cov[0] || {};
        coverageText = 'Catalogue coverage · ' + (cv.total || 0) + ' records · description populated: ' + (cv.described || 0) +
          ' · source transcription entered: ' + (cv.transcribed || 0) + ' · interpretation populated: ' + (cv.interpreted || 0) +
          '. Existing catalogue-page text is separate from a source transcription.';
        var coverageNode = root.querySelector('[data-coverage]');
        if (coverageNode) coverageNode.textContent = coverageText;
      }
      var q = String(queryInput.value || '').trim().toLowerCase();
      var rows;
      if (mode === 'artifacts') {
        var base = "SELECT ec.ev, ec.title, ec.path, ec.evidence_grade, ec.independent_origin_id, ec.grade_note, " +
          "aa.description, aa.description_status, aa.transcript, aa.transcript_status, aa.interpretation, " +
          "aa.interpretation_status, aa.source_verification_status, aa.limitations, " +
          (hasCsscpsg ? "aa.csscpsg_json, " : "'' AS csscpsg_json, ") +
          "et.body AS catalogue_page_text, et.truncated AS catalogue_text_truncated " +
          "FROM evidence_catalogue ec LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev " +
          "LEFT JOIN evidence_text et ON et.aid=ec.artifact_id ";
        var where = q ? "WHERE lower(ec.ev) LIKE ? OR lower(ec.title) LIKE ? OR lower(ec.path) LIKE ? OR lower(ec.aliases_json) LIKE ? OR lower(COALESCE(aa.description,'')) LIKE ? OR lower(COALESCE(aa.interpretation,'')) LIKE ? OR lower(COALESCE(et.body,'')) LIKE ? " : "";
        var params = q ? Array(7).fill('%' + q + '%') : [];
        rows = await db.query(base + where + 'ORDER BY ec.ev LIMIT ? OFFSET ?', params.concat([pageSize, offset]));
        rows.forEach(function (r) { results.appendChild(artifactCard(r)); });
      } else {
        var obwhere = q ? "WHERE lower(o.id) LIKE ? OR lower(o.title) LIKE ? OR lower(o.summary) LIKE ? OR lower(o.analysis) LIKE ? OR lower(o.limits) LIKE ? " : "";
        var obparams = q ? Array(5).fill('%' + q + '%') : [];
        rows = await db.query("SELECT o.* FROM observations o " + obwhere + " ORDER BY o.seq,o.id LIMIT ? OFFSET ?", obparams.concat([pageSize, offset]));
        for (var i = 0; i < rows.length; i++) results.appendChild(await observationCard(rows[i]));
      }
      offset += rows.length;
      exhausted = rows.length < pageSize;
      moreButton.hidden = exhausted;
      if (offset === rows.length && rows.length === 0) {
        results.appendChild(el('p', 'cw-eb-empty', 'No records match this search.'));
      }
      status.textContent = (mode === 'artifacts' ? 'Level 1 · Artifacts' : 'Level 2 · Observations') +
        ' · ' + offset + ' shown' + (exhausted ? '' : ' · more available') +
        (db === null ? '' : ' · source: ' + dbSource);
    } catch (err) {
      status.textContent = 'Could not read the catalogue: ' + String(err && err.message || err);
      results.appendChild(el('p', 'cw-eb-empty', 'The source register remains below. This database view can be retried after the catalogue data is available.'));
    } finally {
      busy = false;
    }
  }
  root.querySelectorAll('[data-mode]').forEach(function (button) {
    button.addEventListener('click', function () {
      mode = button.getAttribute('data-mode');
      root.querySelectorAll('[data-mode]').forEach(function (b) { b.setAttribute('aria-pressed', String(b === button)); });
      load(true);
    });
  });
  root.querySelector('form').addEventListener('submit', function (e) { e.preventDefault(); load(true); });
  root.querySelector('[data-reset]').addEventListener('click', function () { queryInput.value = ''; load(true); });
  moreButton.addEventListener('click', function () { load(false); });
  load(true);
})();
