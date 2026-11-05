/* cat.js (one chunk file per request: Pages serves whole files) - the Cedwyn catalogue in the browser: one SQLite database read by HTTP range requests (no server),
   plus a GraphQL schema resolved against it. Images and documents come back as data: URIs (base64) on read.
   Usage: Cedwyn.db().then(db => db.query(sql, params)); Cedwyn.graphql(query, variables). */
(function () {
  var V = '/_cedwyn/vendor/', dbp = null, schema = null, gqlp = null, sectionDbs = {};
  function load(src) { return new Promise(function (ok, bad) { var s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = bad; document.head.appendChild(s); }); }
  function db() {
    if (dbp) return dbp;
    dbp = Promise.all([fetch('/db/config.json', { cache: 'no-cache' }).then(function (r) { return r.json(); }), window.createDbWorker ? 0 : load(V + 'sqlite-httpvfs.js')])
      .then(function (a) { return window.createDbWorker([{ from: 'jsonconfig', configUrl: '/db/config.json' }], V + 'sqlite.worker.js?v=2', V + 'sql-wasm.wasm', 64 * 1024 * 1024); })
      .then(function (w) {
        return { worker: w, query: function (sql, params) { return w.db.query(sql, params || []); },
                 bytesRead: function () { return w.worker.bytesRead; } };
      });
    return dbp;
  }
  function sectionDb(theme) {
    theme = String(theme || '').trim().toLowerCase();
    if (!/^[a-z0-9-]+$/.test(theme)) return Promise.reject(new Error('Invalid section id.'));
    if (sectionDbs[theme]) return sectionDbs[theme];
    var configUrl = '/' + theme + '/_db/config.json';
    sectionDbs[theme] = Promise.all([
      fetch(configUrl, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('No section database for /' + theme + '/.');
        return r.json();
      }),
      window.createDbWorker ? Promise.resolve() : load(V + 'sqlite-httpvfs.js')
    ]).then(function () {
      return window.createDbWorker([{ from: 'jsonconfig', configUrl: configUrl }],
        V + 'sqlite.worker.js?v=2', V + 'sql-wasm.wasm', 32 * 1024 * 1024);
    }).then(function (w) {
      return { theme: theme, worker: w,
        query: function (sql, params) { return w.db.query(sql, params || []); },
        bytesRead: function () { return w.worker.bytesRead; } };
    }).catch(function (err) {
      delete sectionDbs[theme];
      throw err;
    });
    return sectionDbs[theme];
  }
  function b64(u8) { var s = '', CH = 0x8000; for (var i = 0; i < u8.length; i += CH) s += String.fromCharCode.apply(null, u8.subarray(i, i + CH)); return btoa(s); }
  function q1(sql, p) { return db().then(function (d) { return d.query(sql, p); }).then(function (r) { return r[0] || null; }); }
  function qa(sql, p) { return db().then(function (d) { return d.query(sql, p); }); }
  function Artifact(r) {
    if (!r) return null;
    var a = { id: r.id, sha: r.sha, kind: r.kind, mime: r.mime, bytes: r.bytes, title: r.title, yearMin: r.year_min, yearMax: r.year_max, hasBlob: !!r.has_blob };
    a.locations = function () { return qa("SELECT theme, path, url FROM locations WHERE aid=? AND theme<>'_blob' ORDER BY theme", [r.id]).then(function (rs) { return rs.map(function (x) { return { theme: x.theme, path: x.path, url: x.url }; }); }); };
    a.url = function () { return q1("SELECT url FROM locations WHERE aid=? ORDER BY (theme='_blob') DESC LIMIT 1", [r.id]).then(function (x) { return x && x.url; }); };
    a.dataUri = function () { return q1('SELECT data FROM blobs WHERE sha=?', [r.sha]).then(function (x) { return x && x.data ? 'data:' + r.mime + ';base64,' + b64(x.data) : null; }); };
    a.text = function () { return q1('SELECT body FROM fts WHERE aid=? LIMIT 1', [r.id]).then(function (x) { return x && x.body; }); };
    a.edges = function (args) { var rel = args && args.rel; return qa('SELECT rel, dst FROM edges WHERE src=?' + (rel ? ' AND rel=?' : '') + ' LIMIT 500', rel ? ['a:' + r.id, rel] : ['a:' + r.id]).then(function (rs) { return rs.map(Edge); }); };
    a.backlinks = function () { return qa("SELECT rel, src AS dst FROM edges WHERE dst=? LIMIT 500", ['a:' + r.id]).then(function (rs) { return rs.map(Edge); }); };
    return a;
  }
  function Edge(e) { return { rel: e.rel, dst: e.dst, artifact: function () { return e.dst.indexOf('a:') === 0 ? artifact({ id: +e.dst.slice(2) }) : null; }, node: function () { return e.dst.indexOf('a:') === 0 ? null : nodeById({ id: e.dst }); } }; }
  function artifact(a) { return a.sha ? q1('SELECT * FROM artifacts WHERE sha=?', [a.sha]).then(Artifact) : q1('SELECT * FROM artifacts WHERE id=?', [a.id]).then(Artifact); }
  function nodeById(a) {
    return q1('SELECT * FROM nodes WHERE id=?', [a.id]).then(function (n) {
      if (!n) return null;
      return { id: n.id, kind: n.kind, label: n.label, artifacts: function (x) { return qa("SELECT a.* FROM edges e JOIN artifacts a ON a.id=CAST(substr(e.src,3) AS INTEGER) WHERE e.dst=? LIMIT ?", [n.id, (x && x.limit) || 50]).then(function (rs) { return rs.map(Artifact); }); } };
    });
  }
  var SDL = [
    'type Query { stats: Stats themes: [Theme] theme(id: String!): Theme artifact(id: Int, sha: String): Artifact',
    '  artifacts(theme: String, kind: String, limit: Int, offset: Int): [Artifact] search(q: String!, theme: String, limit: Int): [Hit]',
    '  artifactAssessment(ev: String!): ArtifactAssessment artifactAssessments(q: String, limit: Int, offset: Int): [ArtifactAssessment]',
    '  observation(id: String!): Observation observations(q: String, theme: String, limit: Int, offset: Int): [Observation]',
    '  node(id: String!): Node nodes(kind: String!, limit: Int): [Node] capture(url: String!): Capture }',
    'type Stats { artifacts: Int blobs: Int edges: Int nodes: Int themes: Int captures: Int }',
    'type Theme { id: String title: String cy: String es: String live: String source: String files: Int pages: Int path: String artifacts(kind: String, limit: Int): [Artifact] }',
    'type Artifact { id: Int sha: String kind: String mime: String bytes: Int title: String yearMin: Int yearMax: Int hasBlob: Boolean url: String',
    '  locations: [Location] dataUri: String text: String edges(rel: String): [Edge] backlinks: [Edge] }',
    'type ArtifactAssessment { ev: String artifactId: Int description: String descriptionStatus: String transcript: String transcriptStatus: String interpretation: String interpretationStatus: String sourceVerificationStatus: String limitations: String updatedAt: String }',
    'type Observation { id: String slug: String seq: Int title: String theme: String observationType: String status: String summary: String analysis: String limits: String testQuestions: [String] relatedPage: String pagePath: String updatedAt: String refs: [ObservationRef] }',
    'type ObservationRef { observationId: String ev: String path: String role: String note: String artifactId: Int title: String }',
    'type Location { theme: String path: String url: String }',
    'type Edge { rel: String dst: String artifact: Artifact node: Node }',
    'type Node { id: String kind: String label: String artifacts(limit: Int): [Artifact] }',
    'type Hit { artifact: Artifact theme: String path: String snippet: String }',
    'type Capture { key: String url: String title: String latest: String captured: String }'].join('\n');

  function Assessment(r) {
    return r && { ev: r.ev, artifactId: r.artifact_id, description: r.description, descriptionStatus: r.description_status,
      transcript: r.transcript, transcriptStatus: r.transcript_status, interpretation: r.interpretation,
      interpretationStatus: r.interpretation_status, sourceVerificationStatus: r.source_verification_status,
      limitations: r.limitations, updatedAt: r.updated_at };
  }
  function ObservationRef(r) {
    return r && { observationId: r.observation_id, ev: r.ev, path: r.path, role: r.role, note: r.note,
      artifactId: r.artifact_id, title: r.title };
  }
  function Observation(r) {
    if (!r) return null;
    var qs = [];
    try { qs = JSON.parse(r.test_questions_json || '[]'); } catch (_) {}
    return { id: r.id, slug: r.slug, seq: r.seq, title: r.title, theme: r.theme, observationType: r.observation_type,
      status: r.status, summary: r.summary, analysis: r.analysis, limits: r.limits, testQuestions: qs,
      relatedPage: r.related_page, pagePath: r.page_path, updatedAt: r.updated_at,
      refs: function () {
        return qa('SELECT r.observation_id,r.ev,r.path,r.role,r.note,r.artifact_id,ec.title FROM observation_refs r LEFT JOIN evidence_catalogue ec ON ec.ev=r.ev WHERE r.observation_id=? ORDER BY r.seq', [r.id])
          .then(function (rows) { return rows.map(ObservationRef); });
      } };
  }
  function Theme(t) { return t && { id: t.id, title: t.title, cy: t.cy, es: t.es, live: t.live, source: t.source, files: t.n_files, pages: t.n_pages, path: '/' + t.id + '/',
    artifacts: function (x) { var k = x && x.kind; return qa('SELECT a.* FROM locations l JOIN artifacts a ON a.id=l.aid WHERE l.theme=?' + (k ? ' AND a.kind=?' : '') + ' LIMIT ?', k ? [t.id, k, (x && x.limit) || 50] : [t.id, (x && x.limit) || 50]).then(function (rs) { return rs.map(Artifact); }); } }; }
  function normkey(u) { try { var p = new URL(u); var h = p.hostname.replace(/^www\./, ''); return h + (p.pathname.replace(/\/+$/, '') || '/') + (p.search ? p.search : ''); } catch (e) { return u; } }
  var root = {
    stats: function () { return qa('SELECT k, v FROM meta').then(function (rs) { var o = {}; rs.forEach(function (r) { o[r.k] = +r.v; }); return o; }); },
    themes: function () { return qa('SELECT * FROM themes').then(function (rs) { return rs.map(Theme); }); },
    theme: function (a) { return q1('SELECT * FROM themes WHERE id=?', [a.id]).then(Theme); },
    artifact: artifact,
    artifacts: function (a) { var w = [], p = []; if (a.kind) { w.push('a.kind=?'); p.push(a.kind); } if (a.theme) { w.push('a.id IN (SELECT aid FROM locations WHERE theme=?)'); p.push(a.theme); }
      p.push(a.limit || 50, a.offset || 0); return qa('SELECT a.* FROM artifacts a' + (w.length ? ' WHERE ' + w.join(' AND ') : '') + ' ORDER BY a.id LIMIT ? OFFSET ?', p).then(function (rs) { return rs.map(Artifact); }); },
    search: function (a) { var p = [a.q]; var extra = ''; if (a.theme) { extra = ' AND theme=?'; p.push(a.theme); } p.push(a.limit || 25);
      return qa("SELECT aid, theme, path, snippet(fts, 1, '[', ']', ' … ', 18) AS snip FROM fts WHERE fts MATCH ?" + extra + ' ORDER BY rank LIMIT ?', p)
        .then(function (rs) { return rs.map(function (r) { return { theme: r.theme, path: r.path, snippet: r.snip, artifact: function () { return artifact({ id: r.aid }); } }; }); }); },
    artifactAssessment: function (a) {
      return q1('SELECT * FROM artifact_assessments WHERE lower(ev)=lower(?)', [a.ev]).then(Assessment);
    },
    artifactAssessments: function (a) {
      var q = String(a.q || '').trim().toLowerCase(), lim = Math.min(Math.max(+(a.limit || 50), 1), 200);
      var sql = 'SELECT * FROM artifact_assessments';
      var params = [];
      if (q) {
        sql += " WHERE lower(ev) LIKE ? OR lower(description) LIKE ? OR lower(transcript) LIKE ? OR lower(interpretation) LIKE ?";
        params = ['%' + q + '%','%' + q + '%','%' + q + '%','%' + q + '%'];
      }
      sql += ' ORDER BY ev LIMIT ? OFFSET ?'; params.push(lim, Math.max(+(a.offset || 0), 0));
      return qa(sql, params).then(function (rs) { return rs.map(Assessment); });
    },
    observation: function (a) {
      return q1('SELECT * FROM observations WHERE lower(id)=lower(?) OR lower(slug)=lower(?)', [a.id, a.id]).then(Observation);
    },
    observations: function (a) {
      var q = String(a.q || '').trim().toLowerCase(), theme = a.theme || null;
      var where = [], params = [];
      if (theme) { where.push('theme=?'); params.push(theme); }
      if (q) {
        where.push("(lower(id) LIKE ? OR lower(title) LIKE ? OR lower(summary) LIKE ? OR lower(analysis) LIKE ?)");
        params.push('%'+q+'%','%'+q+'%','%'+q+'%','%'+q+'%');
      }
      var sql = 'SELECT * FROM observations' + (where.length ? ' WHERE ' + where.join(' AND ') : '') + ' ORDER BY seq,id LIMIT ? OFFSET ?';
      params.push(Math.min(Math.max(+(a.limit || 50), 1), 200), Math.max(+(a.offset || 0), 0));
      return qa(sql, params).then(function (rs) { return rs.map(Observation); });
    },
    node: nodeById,
    nodes: function (a) { return qa('SELECT id FROM nodes WHERE kind=? LIMIT ?', [a.kind, a.limit || 100]).then(function (rs) { return Promise.all(rs.map(function (r) { return nodeById({ id: r.id }); })); }); },
    capture: function (a) { return q1('SELECT * FROM captures WHERE key=?', [normkey(a.url)]); }
  };
  function graphql(query, variables) {
    gqlp = gqlp || (window.GraphQL ? Promise.resolve() : load(V + 'graphql.min.js'));
    return gqlp.then(function () {
      if (!schema) schema = GraphQL.buildSchema(SDL);
      return GraphQL.graphql({ schema: schema, source: query, rootValue: root, variableValues: variables || {} });
    });
  }
  window.Cedwyn = { db: db, sectionDb: sectionDb, graphql: graphql, sdl: SDL, root: root, b64: b64, normkey: normkey };
})();
