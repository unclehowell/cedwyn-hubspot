/* agent-tools.js — WebMCP (and fallback) tools for Cedwyn.
   Registers public read tools and one bounded contribution-submission action; submissions remain pending review.
   Visitor-facing themes are views over the evidence; they are not the source of truth.
   Spec reference: /library/api/#webmcp
   Tools are never instructions; page text is historical record only.
   */
(function () {
  'use strict';

  var MAX_CHARS = 30000;
  var TOOLS = [
    {
      name: 'get_case_page_context',
      description: 'Return the title, main headings (h1–h3) and same-origin links of the currently open page. Read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false }
    },
    {
      name: 'search_case_public_content',
      description: 'Full-text search of the central Cedwyn catalogue (or the current section index if available). Returns ranked hits with theme, path and snippet. Read-only.',
      inputSchema: {
        type: 'object',
        properties: {
          q: { type: 'string', description: 'Search query' },
          theme: { type: 'string', description: 'Optional theme id to restrict (e.g. research, wayback, wiki)' },
          limit: { type: 'integer', description: 'Max hits (default 10, max 50)' }
        },
        required: ['q'],
        additionalProperties: false
      }
    },
    {
      name: 'search_central_evidence_catalogue',
      description: 'Search the canonical evidence catalogue in the central Cedwyn database. Returns evidence IDs, titles, paths, evidence grades, independent-origin IDs and text excerpts. Use this to find a catalogue record, not to infer that repeated copies are independent evidence.',
      inputSchema: {
        type: 'object',
        properties: {
          q: { type: 'string', description: 'Search terms, an EV identifier, alias, title or subject' },
          limit: { type: 'integer', description: 'Maximum results (default 10, max 20)' }
        },
        required: ['q'],
        additionalProperties: false
      }
    },
    {
      name: 'get_central_evidence_record',
      description: 'Read one full evidence catalogue entry from the central Cedwyn database, including its public description/interpretation text, evidence grade and meaning, independent origin, aliases, locations and related chronology/layer references. Accepts an EV identifier, known alias or catalogue path.',
      inputSchema: {
        type: 'object',
        properties: {
          key: { type: 'string', description: 'EV identifier such as EV-0628, an alias such as GHF-E090, or an evidence page path' }
        },
        required: ['key'],
        additionalProperties: false
      }
    },
    {
      name: 'search_central_observations',
      description: 'Search Level 2 observation records in the central Cedwyn catalogue. Observations describe patterns derived from cited artifacts and include limits, test questions and source references; they are not original evidence.',
      inputSchema: {
        type: 'object',
        properties: {
          q: { type: 'string', description: 'Optional words, observation ID or subject' },
          limit: { type: 'integer', description: 'Maximum results (default 10, max 50)' }
        },
        additionalProperties: false
      }
    },
    {
      name: 'get_central_observation',
      description: 'Read one Level 2 observation by its OBS ID or slug, including analysis, limits, test questions and linked Level 1 artifact references.',
      inputSchema: {
        type: 'object',
        properties: { key: { type: 'string', description: 'Observation ID such as OBS-0002 or its slug' } },
        required: ['key'],
        additionalProperties: false
      }
    },
    {
      name: 'list_case_public_resources',
      description: 'List machine-readable resources for the current section or the whole site (agents.json, llms.txt, agent-index.json, /db/stats.json, GraphQL, etc.). Read-only.',
      inputSchema: {
        type: 'object',
        properties: {
          section: { type: 'string', description: 'Optional section path prefix (e.g. /research/, /wayback/)' }
        },
        additionalProperties: false
      }
    },
    {
      name: 'read_case_public_resource',
      description: 'Fetch one public same-origin resource as plain text (HTML stripped or raw JSON/text). Truncated at 30 000 characters. Read-only.',
      inputSchema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'Absolute path on this origin, e.g. /agents.json or /research/ai-agent-index/' }
        },
        required: ['path'],
        additionalProperties: false
      }
    },
    {
      name: 'get_cedwyn_agent_task_index',
      description: 'Read the public machine-readable snapshot of Cedwyn/Great House Farm-related HubSpot task metadata. HubSpot remains authoritative; this index contains no task bodies.',
      inputSchema: {
        type: 'object',
        properties: {
          offset: { type: 'integer', description: 'Zero-based offset from the public task snapshot (default 0).' },
          limit: { type: 'integer', description: 'Rows per page (default 50, maximum 50).' }
        },
        additionalProperties: false
      },
      readOnly: true
    },
    {
      name: 'get_cedwyn_agent_bridge_manifest',
      description: 'Read the opaque Cedwyn agent bridge manifest, including permission tiers, available resources, submission policy and X/Grok handoff rules. Public, read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      readOnly: true
    },
    {
      name: 'get_cedwyn_agent_queue_summary',
      description: 'Read counts of pending, published and rejected external-agent submissions. Pending submission text is not exposed by this endpoint. Public, read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      readOnly: true
    },
    {
      name: 'get_cedwyn_flow_watch_health',
      description: 'Read the live sanitised Cedwyn anti-stagnation status: latest GitHub source/build queue, production build stamp, Agent Library publication, shared e-book/documentary version registry, current blockers and explicit connector coverage gaps. Read this before and after work.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      readOnly: true
    },
    {
      name: 'get_cedwyn_flow_watch_events',
      description: 'Read recent sanitised Cedwyn operational issues, resolution timestamps and GitHub build-job transitions. Read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      readOnly: true
    },
    {
      name: 'get_cedwyn_flow_watch_contract',
      description: 'Read the machine-readable anti-stagnation contract, monitoring cadence, observable systems and connector gaps. Read-only.',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      readOnly: true
    },
    {
      name: 'read_cedwyn_x_activity',
      description: 'Read the reviewed X/Grok discussion references submitted by authorised X-capable agents. This is not a live X crawl; pending submissions are hidden.',
      inputSchema: {
        type: 'object',
        properties: { limit: { type: 'integer', description: 'Maximum items (default 20, max 20).' } },
        additionalProperties: false
      },
      readOnly: true
    },
    {
      name: 'submit_agent_contribution',
      description: 'Submit a source-linked research lead, question, analysis, X post or X reply reference to Cedwyn’s private pending-review queue. This does not create a HubSpot task, post on X, or publish content. Submit source URLs and separate fact from interpretation.',
      inputSchema: {
        type: 'object',
        properties: {
          platform: { type: 'string', enum: ['x', 'github', 'webmcp', 'other'] },
          activity_type: { type: 'string', enum: ['x_post', 'x_reply', 'research_lead', 'analysis', 'question', 'task_help'] },
          agent_label: { type: 'string', maxLength: 100 },
          source_url: { type: 'string', maxLength: 500 },
          post_id: { type: 'string', maxLength: 100 },
          reply_to: { type: 'string', maxLength: 100 },
          conversation_id: { type: 'string', maxLength: 100 },
          related_task_id: { type: 'string', maxLength: 20 },
          artifact_ids: { type: 'array', items: { type: 'string', maxLength: 100 }, maxItems: 40 },
          body: { type: 'string', minLength: 12, maxLength: 4000 }
        },
        required: ['platform', 'activity_type', 'body'],
        additionalProperties: false
      },
      readOnly: false
    }
  ];

  function sameOrigin(path) {
    if (!path || typeof path !== 'string') return false;
    path = path.trim();
    if (path.startsWith('//') || /^https?:/i.test(path)) {
      try {
        var u = new URL(path, location.href);
        return u.origin === location.origin;
      } catch (e) { return false; }
    }
    return path.startsWith('/');
  }

  // Load the catalogue client only when an agent invokes a catalogue-backed tool.
  // Ordinary evidence pages do not necessarily include cat.js in their human-facing markup.
  var catalogueClientPromise = null;
  function loadCatalogueClient() {
    if (window.Cedwyn && typeof window.Cedwyn.db === 'function' &&
        typeof window.Cedwyn.graphql === 'function') {
      return Promise.resolve(window.Cedwyn);
    }
    if (catalogueClientPromise) return catalogueClientPromise;
    catalogueClientPromise = new Promise(function (resolve, reject) {
      var script = document.createElement('script');
      script.src = '/_cedwyn/cat.js';
      script.async = true;
      script.onload = function () {
        if (window.Cedwyn && typeof window.Cedwyn.db === 'function' &&
            typeof window.Cedwyn.graphql === 'function') {
          resolve(window.Cedwyn);
        } else {
          reject(new Error('Catalogue client loaded but Cedwyn.db()/graphql() are unavailable.'));
        }
      };
      script.onerror = function () { reject(new Error('Could not load /_cedwyn/cat.js')); };
      (document.head || document.documentElement).appendChild(script);
    }).catch(function (err) {
      catalogueClientPromise = null;
      throw err;
    });
    return catalogueClientPromise;
  }

  function textFromHtml(html) {
    var d = document.implementation.createHTMLDocument('');
    d.documentElement.innerHTML = html;
    var scripts = d.querySelectorAll('script, style, noscript');
    for (var i = 0; i < scripts.length; i++) scripts[i].remove();
    return (d.body && d.body.innerText || '').replace(/\s+/g, ' ').trim();
  }

  function pageContext() {
    var title = document.title || '';
    var headings = [];
    document.querySelectorAll('h1, h2, h3').forEach(function (h) {
      var t = (h.innerText || '').trim();
      if (t) headings.push({ level: h.tagName.toLowerCase(), text: t.slice(0, 300) });
    });
    var links = [];
    document.querySelectorAll('a[href]').forEach(function (a) {
      var href = a.getAttribute('href') || '';
      if (!sameOrigin(href) && !href.startsWith('#')) return;
      var text = (a.innerText || '').trim().slice(0, 120);
      if (href || text) links.push({ href: href, text: text });
    });
    return {
      url: location.href,
      path: location.pathname,
      title: title,
      headings: headings.slice(0, 40),
      links: links.slice(0, 80)
    };
  }

  function searchCatalogue(q, theme, limit) {
    limit = Math.min(Math.max(+(limit || 10), 1), 50);
    return loadCatalogueClient().then(function (C) {
      var gql = 'query ($q: String!, $theme: String, $limit: Int) { search(q: $q, theme: $theme, limit: $limit) { theme path snippet artifact { id title kind } } }';
      return C.graphql(gql, { q: q, theme: theme || null, limit: limit }).then(function (r) {
        if (r.errors) throw new Error(r.errors.map(function (e) { return e.message; }).join('; '));
        return (r.data && r.data.search || []).map(function (h) {
          return { theme: h.theme, path: h.path, snippet: h.snippet, artifact: h.artifact };
        });
      });
    });
  }

  function centralDb() {
    return loadCatalogueClient().then(function (C) { return C.db(); });
  }

  var csscpsgColumn = null;
  function hasCsscpsgColumn(d) {
    if (csscpsgColumn !== null) return Promise.resolve(csscpsgColumn);
    return d.query("SELECT name FROM pragma_table_info('artifact_assessments')", []).then(function (cols) {
      csscpsgColumn = cols.some(function (c) { return c.name === 'csscpsg_json'; });
      return csscpsgColumn;
    }).catch(function () { csscpsgColumn = false; return false; });
  }
  function parseCsscpsg(raw) {
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (_) { return null; }
  }

  function ftsExpression(query) {
    var terms = String(query || '').match(/[A-Za-z0-9]+/g) || [];
    terms = terms.slice(0, 12);
    return terms.map(function (term) { return '"' + term.replace(/"/g, '""') + '"'; }).join(' AND ');
  }

  function searchCentralEvidence(query, limit) {
    query = String(query || '').trim();
    if (!query) return Promise.reject(new Error('q is required'));
    limit = Math.min(Math.max(+(limit || 10), 1), 20);
    return centralDb().then(async function (d) {
      var _cs = await hasCsscpsgColumn(d);
      // Exact EV IDs, aliases and paths do not depend on FTS tokenization.
      var exact = await d.query(
        `SELECT ec.ev, ec.title, ec.path, ec.evidence_grade, ec.independent_origin_id,
                ec.aliases_json, ec.grade_note, et.body AS excerpt, et.body_chars, et.truncated,
                aa.description, aa.description_status, aa.transcript, aa.transcript_status,
                aa.interpretation, aa.interpretation_status, aa.source_verification_status, aa.limitations${_cs ? ', aa.csscpsg_json' : ''}
           FROM evidence_catalogue ec
           LEFT JOIN evidence_text et ON et.aid=ec.artifact_id
           LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev
          WHERE lower(ec.ev)=lower(?) OR lower(ec.path)=lower(?)
             OR lower(ec.aliases_json) LIKE lower(?)
          ORDER BY ec.ev LIMIT ?`,
        [query, query, '%' + query + '%', limit]
      );
      if (exact.length) {
        return {
          source: 'central Cedwyn evidence catalogue database',
          matchType: 'exact ID, path or alias',
          results: exact.map(function (r) {
            var aliases = [];
            try { aliases = JSON.parse(r.aliases_json || '[]'); } catch (_) {}
            return {
              ev: r.ev, title: r.title, path: r.path, evidenceGrade: r.evidence_grade,
              independentOriginId: r.independent_origin_id, aliases: aliases,
              gradeNote: r.grade_note, excerpt: (r.excerpt || '').slice(0, 2000),
              entryTextChars: r.body_chars || 0, entryTextTruncated: !!r.truncated,
              assessment: { description: r.description || '', descriptionStatus: r.description_status || 'not_assessed',
                transcript: r.transcript || '', transcriptStatus: r.transcript_status || 'not_assessed',
                interpretation: r.interpretation || '', interpretationStatus: r.interpretation_status || 'not_assessed',
                sourceVerificationStatus: r.source_verification_status || 'not_assessed', limitations: r.limitations || '', csscpsg: parseCsscpsg(r.csscpsg_json) }
            };
          })
        };
      }
      var expression = ftsExpression(query);
      if (!expression) return { source: 'central Cedwyn evidence catalogue database', matchType: 'text', results: [] };
      var rows = await d.query(
        `SELECT DISTINCT ec.ev, ec.title, ec.path, ec.evidence_grade, ec.independent_origin_id,
                ec.aliases_json, ec.grade_note,
                snippet(fts, 1, '[', ']', ' … ', 18) AS match_snippet,
                substr(et.body, 1, 1800) AS excerpt, et.body_chars, et.truncated,
                aa.description, aa.description_status, aa.transcript, aa.transcript_status,
                aa.interpretation, aa.interpretation_status, aa.source_verification_status, aa.limitations${_cs ? ', aa.csscpsg_json' : ''}
           FROM fts
           JOIN evidence_catalogue ec ON ec.artifact_id=CAST(fts.aid AS INTEGER)
           LEFT JOIN evidence_text et ON et.aid=ec.artifact_id
           LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev
          WHERE fts MATCH ?
          ORDER BY rank LIMIT ?`,
        [expression, limit]
      );
      return {
        source: 'central Cedwyn evidence catalogue database',
        matchType: 'full-text',
        results: rows.map(function (r) {
          var aliases = [];
          try { aliases = JSON.parse(r.aliases_json || '[]'); } catch (_) {}
          return {
            ev: r.ev, title: r.title, path: r.path, evidenceGrade: r.evidence_grade,
            independentOriginId: r.independent_origin_id, aliases: aliases,
            gradeNote: r.grade_note, matchSnippet: r.match_snippet,
            excerpt: r.excerpt || '', entryTextChars: r.body_chars || 0,
            entryTextTruncated: !!r.truncated,
            assessment: { description: r.description || '', descriptionStatus: r.description_status || 'not_assessed',
              transcript: r.transcript || '', transcriptStatus: r.transcript_status || 'not_assessed',
              interpretation: r.interpretation || '', interpretationStatus: r.interpretation_status || 'not_assessed',
              sourceVerificationStatus: r.source_verification_status || 'not_assessed', limitations: r.limitations || '', csscpsg: parseCsscpsg(r.csscpsg_json) }
          };
        })
      };
    });
  }

  function getCentralEvidenceRecord(key) {
    key = String(key || '').trim();
    if (!key) return Promise.reject(new Error('key is required'));
    var pathCandidate = key.charAt(0) === '/' ? key.replace(/index\.html$/i, '').replace(/\/?$/, '/') : '';
    return centralDb().then(async function (d) {
      var _cs = await hasCsscpsgColumn(d);
      var rows = await d.query(
        `SELECT ec.ev, ec.artifact_id, ec.path, ec.evidence_grade, ec.independent_origin_id,
                ec.aliases_json, ec.grade_note, ec.title,
                et.body AS record_text, et.body_chars, et.truncated,
                a.sha, a.kind, a.mime, a.bytes, a.year_min, a.year_max,
                aa.description, aa.description_status, aa.transcript, aa.transcript_status,
                aa.interpretation, aa.interpretation_status, aa.source_verification_status, aa.limitations${_cs ? ', aa.csscpsg_json' : ''}
           FROM evidence_catalogue ec
           LEFT JOIN evidence_text et ON et.aid=ec.artifact_id
           LEFT JOIN artifacts a ON a.id=ec.artifact_id
           LEFT JOIN artifact_assessments aa ON aa.ev=ec.ev
          WHERE lower(ec.ev)=lower(?) OR lower(ec.path)=lower(?)
             OR (?<>'' AND lower(ec.path)=lower(?))
             OR lower(ec.aliases_json) LIKE lower(?)
          ORDER BY ec.ev LIMIT 3`,
        [key, key, pathCandidate, pathCandidate, '%' + key + '%']
      );
      if (!rows.length) {
        return {
          found: false, key: key,
          source: 'central Cedwyn evidence catalogue database',
          message: 'No exact evidence ID, alias or catalogue path was found. Search the catalogue first.'
        };
      }
      var r = rows[0], aid = r.artifact_id == null ? null : r.artifact_id;
      var aliases = [];
      try { aliases = JSON.parse(r.aliases_json || '[]'); } catch (_) {}
      var refs = [], locations = [], relations = [], gradeMeaning = null, cataloguePolicy = {};
      var parallel = await Promise.all([
        d.query('SELECT key, value FROM evidence_catalogue_meta'),
        r.evidence_grade == null ? Promise.resolve([]) :
          d.query('SELECT meaning FROM evidence_grade_scale WHERE grade=?', [r.evidence_grade]),
        aid == null ? Promise.resolve([]) : d.query(
          `SELECT lr.layer AS layerId, l.title AS layerTitle, lr.item AS itemId,
                  li.kind AS itemKind, li.date AS date, li.event AS event,
                  li.blow AS interpretationNote, li.label AS label,
                  lr.ev AS referencedEvidence, lr.path AS referencedPath
             FROM layer_refs lr
             LEFT JOIN layers l ON l.id=lr.layer
             LEFT JOIN layer_items li ON li.layer=lr.layer AND li.id=lr.item
            WHERE lower(lr.ev)=lower(?) OR lr.aid=?
            ORDER BY l.title, li.seq LIMIT 40`,
          [r.ev, aid]
        ),
        aid == null ? Promise.resolve([]) : d.query(
          `SELECT theme, path, url FROM locations
            WHERE aid=? AND theme<>'_blob' ORDER BY theme, path LIMIT 40`,
          [aid]
        ),
        aid == null ? Promise.resolve([]) : d.query(
          `SELECT e.rel, e.dst, a.title, a.kind, a.id AS artifactId
             FROM edges e
             LEFT JOIN artifacts a ON e.dst=('a:' || a.id)
            WHERE e.src=? ORDER BY e.rel, e.dst LIMIT 50`,
          ['a:' + aid]
        )
      ]);
      parallel[0].forEach(function (p) {
        try { cataloguePolicy[p.key] = JSON.parse(p.value); }
        catch (_) { cataloguePolicy[p.key] = p.value; }
      });
      gradeMeaning = parallel[1].length ? parallel[1][0].meaning : null;
      refs = parallel[2]; locations = parallel[3]; relations = parallel[4];
      return {
        found: true,
        source: 'central Cedwyn evidence catalogue database',
        cataloguePolicy: cataloguePolicy,
        record: {
          ev: r.ev, title: r.title, path: r.path, aliases: aliases,
          evidenceGrade: r.evidence_grade, evidenceGradeMeaning: gradeMeaning,
          independentOriginId: r.independent_origin_id, gradeNote: r.grade_note,
          sha256: r.sha, kind: r.kind, mime: r.mime, bytes: r.bytes,
          yearMin: r.year_min, yearMax: r.year_max,
          assessment: { description: r.description || '', descriptionStatus: r.description_status || 'not_assessed',
            transcript: r.transcript || '', transcriptStatus: r.transcript_status || 'not_assessed',
            interpretation: r.interpretation || '', interpretationStatus: r.interpretation_status || 'not_assessed',
            sourceVerificationStatus: r.source_verification_status || 'not_assessed', limitations: r.limitations || '', csscpsg: parseCsscpsg(r.csscpsg_json) },
          sourcePageText: r.record_text || '',
          entryTextChars: r.body_chars || 0, entryTextTruncated: !!r.truncated,
          locations: locations, chronologyAndLayerReferences: refs, graphRelations: relations
        },
        interpretationNote: 'The entry text is the catalogue page’s published description and interpretation; distinguish it from the underlying primary record and from any inference it discusses. Identical copies share an independent-origin ID and are not independent corroboration.'
      };
    });
  }

  function observationSummary(r) {
    var tests = [];
    try { tests = JSON.parse(r.test_questions_json || '[]'); } catch (_) {}
    return { id: r.id, slug: r.slug, title: r.title, seq: r.seq, theme: r.theme,
      observationType: r.observation_type, status: r.status, summary: r.summary,
      analysis: r.analysis, limits: r.limits, testQuestions: tests,
      relatedPage: r.related_page, pagePath: r.page_path, updatedAt: r.updated_at };
  }

  async function observationReferences(d, id) {
    return d.query(
      `SELECT r.ev, r.path, r.role, r.note, r.artifact_id AS artifactId,
              ec.title, ec.independent_origin_id AS independentOriginId,
              ec.evidence_grade AS evidenceGrade, ec.grade_note AS gradeNote
         FROM observation_refs r LEFT JOIN evidence_catalogue ec ON ec.ev=r.ev
        WHERE r.observation_id=? ORDER BY r.seq`,
      [id]
    );
  }

  async function searchCentralObservations(query, limit) {
    query = String(query || '').trim().toLowerCase();
    limit = Math.min(Math.max(+(limit || 10), 1), 50);
    return centralDb().then(async function (d) {
      var sql = 'SELECT o.*, (SELECT count(*) FROM observation_refs r WHERE r.observation_id=o.id) AS reference_count FROM observations o';
      var params = [];
      if (query) {
        sql += ` WHERE lower(o.id) LIKE ? OR lower(o.slug) LIKE ? OR lower(o.title) LIKE ?
                   OR lower(o.summary) LIKE ? OR lower(o.analysis) LIKE ? OR lower(o.limits) LIKE ?
                   OR EXISTS (SELECT 1 FROM observation_refs r WHERE r.observation_id=o.id AND
                     (lower(COALESCE(r.ev,'')) LIKE ? OR lower(r.path) LIKE ? OR lower(r.note) LIKE ?))`;
        params = Array(9).fill('%' + query + '%');
      }
      sql += ' ORDER BY o.seq,o.id LIMIT ?';
      params.push(limit);
      var rows = await d.query(sql, params);
      return {
        source: 'central Cedwyn observations database',
        level: 2,
        results: await Promise.all(rows.map(async function (r) {
          var item = observationSummary(r);
          item.referenceCount = r.reference_count;
          item.references = await observationReferences(d, r.id);
          return item;
        }))
      };
    });
  }

  async function getCentralObservation(key) {
    key = String(key || '').trim();
    if (!key) return Promise.reject(new Error('key is required'));
    return centralDb().then(async function (d) {
      var rows = await d.query(
        'SELECT * FROM observations WHERE lower(id)=lower(?) OR lower(slug)=lower(?) LIMIT 2',
        [key, key]
      );
      if (!rows.length) return {
        found: false, key: key, source: 'central Cedwyn observations database',
        message: 'No observation ID or slug was found. Search the observation catalogue first.'
      };
      var item = observationSummary(rows[0]);
      item.references = await observationReferences(d, item.id);
      item.level = 2;
      item.source = 'central Cedwyn observations database';
      item.editorialRule = 'This is a derived observation, not an original artifact. Check each cited source and distinguish independent records from repeated recitals or copies.';
      return { found: true, observation: item };
    });
  }

  function listResources(section) {
    var base = [
      { path: '/agents.json', kind: 'json', note: 'Agent entry point and rules' },
      { path: '/llms.txt', kind: 'text', note: 'Site map for language models' },
      { path: '/academy/', kind: 'html', note: 'Cedwyn Academy (soul, memory, skills, work board)' },
      { path: '/academy/FLYWHEELS/snowball.html', kind: 'html', note: 'Cedwyn Snowball master programme and agent operating rules' },
      { path: '/academy/FLYWHEELS/snowball.md', kind: 'text', note: 'Full machine-readable Snowball protocol and specialist work packages' },
      { path: '/academy/FLYWHEELS/flywheels.json', kind: 'json', note: 'Machine-readable specialist flywheel register, including the Snowball parent loop' },
      { path: '/projects/procurement/', kind: 'html', note: 'Public planned procurement register and approval status' },
      { path: '/projects/data/procurement.json', kind: 'json', note: 'Machine-readable procurement register' },
      { path: '/x78s8jej33i8f8rrj4is88/manifest.json', kind: 'json', note: 'Opaque Cedwyn agent bridge manifest and permission tiers' },
      { path: '/x78s8jej33i8f8rrj4is88/tasks.json', kind: 'json', note: 'Sanitised public machine-readable mirror of Snowball HubSpot task metadata' },
      { path: '/x78s8jej33i8f8rrj4is88/x.json', kind: 'json', note: 'Reviewed X activity and public discussion references for BuckerCarlson' },
      { path: '/x78s8jej33i8f8rrj4is88/contributions.json', kind: 'json', note: 'Reviewed public external-agent contributions' },
      { path: '/x78s8jej33i8f8rrj4is88/queue-summary.json', kind: 'json', note: 'Counts of pending and published agent submissions; no pending text exposed' },
      { path: '/x78s8jej33i8f8rrj4is88/flow-health.json', kind: 'json', note: 'Live sanitised anti-stagnation health: source/build queue, production revision, Library and product-version status' },
      { path: '/x78s8jej33i8f8rrj4is88/flow-events.json', kind: 'json', note: 'Recent operational issues and GitHub build-job transitions' },
      { path: '/x78s8jej33i8f8rrj4is88/flow-contract.json', kind: 'json', note: 'Machine-readable mandatory flow-watch protocol' },
      { path: '/x78s8jej33i8f8rrj4is88/webmcp.json', kind: 'json', note: 'Agent bridge machine resource registry' },
      { path: '/academy/work.json', kind: 'json', note: 'Open agent jobs' },
      { path: '/db/stats.json', kind: 'json', note: 'Catalogue database counts and version' },
      { path: '/db/config.json', kind: 'json', note: 'SQLite chunk layout for sql.js-httpvfs' },
      { path: '/db/blobmap.json', kind: 'json', note: 'Path → blob byte locations in the DB' },
      { path: '/db/export/manifest.json', kind: 'json', note: 'Export manifest for the central SQLite catalogue' },
      { path: '/wiki/observations/', kind: 'html', note: 'Level 2 observation index linked to Level 1 artifacts' },
      { path: '/wiki/_db/config.json', kind: 'json', note: 'Compact wiki section SQLite slice' },
      { path: '/graphql/', kind: 'html', note: 'In-browser GraphQL against the catalogue' },
      { path: '/library/api/', kind: 'html', note: 'API and WebMCP documentation' },
      { path: '/_cedwyn/glossary.json', kind: 'json', note: 'Glossary' },
      { path: '/_cedwyn/nomenclature.json', kind: 'json', note: 'Name variants' }
    ];
    if (section) {
      var p = section.replace(/\/+$/, '') + '/';
      base.push(
        { path: p + 'agent-index.json', kind: 'json', note: 'Section machine index (if published)' },
        { path: p + 'llms.txt', kind: 'text', note: 'Section llms.txt (if published)' }
      );
    } else {
      // current section guess
      var parts = location.pathname.split('/').filter(Boolean);
      if (parts.length) {
        var sec = '/' + parts[0] + '/';
        base.push(
          { path: sec + 'agent-index.json', kind: 'json', note: 'Current section machine index (if published)' },
          { path: sec + 'llms.txt', kind: 'text', note: 'Current section llms.txt (if published)' }
        );
      }
    }
    return Promise.resolve(base);
  }

  function readResource(path) {
    if (!sameOrigin(path)) return Promise.reject(new Error('Only same-origin paths are allowed'));
    var url = path.startsWith('http') ? path : (location.origin + (path.startsWith('/') ? path : '/' + path));
    return fetch(url, { credentials: 'same-origin', cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' for ' + path);
      var ct = (r.headers.get('content-type') || '').toLowerCase();
      return r.text().then(function (body) {
        var text = body;
        if (ct.indexOf('html') >= 0) text = textFromHtml(body);
        if (text.length > MAX_CHARS) text = text.slice(0, MAX_CHARS) + '\n…[truncated at ' + MAX_CHARS + ' chars]';
        return { path: path, contentType: ct, chars: text.length, text: text };
      });
    });
  }

  function postAgentContribution(args) {
    args = args || {};
    var allowedPlatforms = ['x', 'github', 'webmcp', 'other'];
    var allowedTypes = ['x_post', 'x_reply', 'research_lead', 'analysis', 'question', 'task_help'];
    var payload = {
      platform: String(args.platform || '').toLowerCase(),
      activity_type: String(args.activity_type || '').toLowerCase(),
      agent_label: String(args.agent_label || 'external-agent').slice(0, 100),
      claimed_access: 'unverified',
      source_url: String(args.source_url || '').slice(0, 500),
      post_id: String(args.post_id || '').slice(0, 100),
      reply_to: String(args.reply_to || '').slice(0, 100),
      conversation_id: String(args.conversation_id || '').slice(0, 100),
      related_task_id: String(args.related_task_id || '').slice(0, 20),
      artifact_ids: Array.isArray(args.artifact_ids) ? args.artifact_ids.slice(0, 40).map(function (x) { return String(x).slice(0, 100); }) : [],
      body: String(args.body || '').trim().slice(0, 4000)
    };
    if (allowedPlatforms.indexOf(payload.platform) < 0) return Promise.reject(new Error('Unsupported platform.'));
    if (allowedTypes.indexOf(payload.activity_type) < 0) return Promise.reject(new Error('Unsupported activity type.'));
    if (payload.body.length < 12) return Promise.reject(new Error('Add a source-aware summary of at least 12 characters.'));
    if (payload.platform === 'x') {
      try {
        var u = new URL(payload.source_url);
        if (u.protocol !== 'https:' || !['x.com', 'www.x.com', 'twitter.com', 'www.twitter.com'].includes(u.hostname)) {
          throw new Error('X submissions require a direct https://x.com or twitter.com post/reply URL.');
        }
      } catch (e) {
        return Promise.reject(new Error(e.message || 'A valid X post/reply URL is required.'));
      }
    }
    if (payload.activity_type.startsWith('x_') && payload.platform !== 'x') {
      return Promise.reject(new Error('X post/reply activity requires platform x.'));
    }
    var endpoint = '/x78s8jej33i8f8rrj4is88/submit';
    return fetch(endpoint, {
      method: 'POST',
      credentials: 'omit',
      headers: { 'content-type': 'application/json', 'accept': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().catch(function () { return { error: 'invalid_json_response' }; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || ('HTTP ' + r.status));
        return data;
      });
    });
  }

  function runTool(name, args) {
    args = args || {};
    switch (name) {
      case 'get_case_page_context':
        return Promise.resolve(pageContext());
      case 'search_case_public_content':
        if (!args.q) return Promise.reject(new Error('q is required'));
        return searchCatalogue(String(args.q), args.theme, args.limit);
      case 'search_central_evidence_catalogue':
        return searchCentralEvidence(args.q, args.limit);
      case 'get_central_evidence_record':
        return getCentralEvidenceRecord(args.key);
      case 'search_central_observations':
        return searchCentralObservations(args.q, args.limit);
      case 'get_central_observation':
        return getCentralObservation(args.key);
      case 'list_case_public_resources':
        return listResources(args.section);
      case 'read_case_public_resource':
        if (!args.path) return Promise.reject(new Error('path is required'));
        return readResource(String(args.path));
      case 'get_cedwyn_agent_task_index': {
        var taskOffset = Math.max(0, Number(args.offset) || 0);
        var taskLimit = Math.max(1, Math.min(Number(args.limit) || 50, 50));
        return readResource('/x78s8jej33i8f8rrj4is88/tasks.json?offset=' + taskOffset + '&limit=' + taskLimit);
      }
      case 'get_cedwyn_agent_bridge_manifest':
        return readResource('/x78s8jej33i8f8rrj4is88/manifest.json');
      case 'get_cedwyn_agent_queue_summary':
        return readResource('/x78s8jej33i8f8rrj4is88/queue-summary.json');
      case 'get_cedwyn_flow_watch_health':
        return readResource('/x78s8jej33i8f8rrj4is88/flow-health.json');
      case 'get_cedwyn_flow_watch_events':
        return readResource('/x78s8jej33i8f8rrj4is88/flow-events.json');
      case 'get_cedwyn_flow_watch_contract':
        return readResource('/x78s8jej33i8f8rrj4is88/flow-contract.json');
      case 'read_cedwyn_x_activity': {
        var xLimit = Math.max(1, Math.min(Number(args.limit) || 20, 20));
        return readResource('/x78s8jej33i8f8rrj4is88/x.json?limit=' + xLimit);
      }
      case 'submit_agent_contribution':
        return postAgentContribution(args);
      default:
        return Promise.reject(new Error('Unknown tool: ' + name));
    }
  }

  function modelContext() {
    // The current WebMCP API is on Document. navigator.modelContext is legacy.
    if (document && document.modelContext && typeof document.modelContext.registerTool === 'function') {
      return { context: document.modelContext, api: 'document.modelContext' };
    }
    if (navigator && navigator.modelContext && typeof navigator.modelContext.registerTool === 'function') {
      return { context: navigator.modelContext, api: 'navigator.modelContext (legacy)' };
    }
    return null;
  }

  async function registerWebMCP() {
    var found = modelContext();
    if (!found) {
      window.__cedwynWebMCP = {
        available: false,
        registered: false,
        api: null,
        tools: TOOLS.map(function (t) { return t.name; }),
        run: runTool,
        message: 'WebMCP is not exposed by this browser. The JavaScript fallback remains available.'
      };
      return false;
    }

    var mc = found.context;
    var registered = [];
    var failures = [];
    for (var i = 0; i < TOOLS.length; i++) {
      var tool = TOOLS[i];
      try {
        await mc.registerTool({
          name: tool.name,
          description: tool.description,
          inputSchema: tool.inputSchema,
          annotations: { readOnlyHint: tool.readOnly !== false, destructiveHint: false },
          execute: async function (input, options) {
            try {
              // Keep the public-resource reader same-origin and honour cancellation.
              if (options && options.signal && options.signal.aborted) {
                return { error: 'Tool execution was cancelled.' };
              }
              var result = await runTool(this.name, input || {});
              return result;
            } catch (err) {
              return { error: String(err && err.message || err) };
            }
          }.bind({ name: tool.name })
        });
        registered.push(tool.name);
      } catch (e) {
        failures.push({ name: tool.name, error: String(e && e.message || e) });
        console.warn('[cedwyn agent-tools] registration failed:', tool.name, e);
      }
    }

    // Verify via the API where supported; do not equate API presence with success.
    var verified = false;
    if (typeof mc.getTools === 'function') {
      try {
        var liveTools = await mc.getTools();
        var liveNames = liveTools.map(function (t) { return t.name; });
        registered = registered.filter(function (name) { return liveNames.indexOf(name) !== -1; });
        verified = TOOLS.every(function (t) { return liveNames.indexOf(t.name) !== -1; });
      } catch (e) {
        failures.push({ name: 'getTools', error: String(e && e.message || e) });
      }
    }

    window.__cedwynWebMCP = {
      available: true,
      registered: registered.length > 0,
      verified: verified,
      api: found.api,
      tools: registered,
      expectedTools: TOOLS.map(function (t) { return t.name; }),
      failures: failures,
      run: runTool,
      message: verified ? ('All ' + TOOLS.length + ' WebMCP tools registered and verified.') :
        (registered.length === TOOLS.length ? 'Registration calls completed; tool discovery could not be fully verified.' :
          'WebMCP registration incomplete. See failures for details.')
    };
    return registered.length === TOOLS.length;
  }

  // Expose a small status node agents / humans can inspect
  function statusNode() {
    var id = 'webmcp-status';
    var el = document.getElementById(id);
    if (!el) {
      el = document.createElement('div');
      el.id = id;
      el.setAttribute('hidden', '');
      el.setAttribute('data-for-agents', '');
      el.setAttribute('aria-hidden', 'true');
      (document.body || document.documentElement).appendChild(el);
    }
    var state = window.__cedwynWebMCP || {};
    el.textContent = state.message || 'WebMCP registration is in progress.';
    el.setAttribute('data-webmcp-api', state.api || 'unavailable');
    el.setAttribute('data-webmcp-registered', (state.tools || []).join(','));
    el.setAttribute('data-webmcp-verified', String(!!state.verified));
  }

  async function boot() {
    await registerWebMCP();
    statusNode();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
