#!/usr/bin/env python3
"""build_db.py - the one catalogue database behind every Cedwyn theme.
Walks dist/ (all themes + the /_blob/ store) and writes one SQLite file:
  themes, artifacts (one row per unique file, by sha256), locations (where each artifact appears in which theme),
  blobs (the evidence bytes themselves as BLOBs: images, PDFs, small media), fts (FTS5 full-text index of every page
  and data file), nodes + edges (graph: page->embeds/links->artifact, artifact->mentions->year, artifact->cites->host),
  captures (original URL -> archived copy, from the Wayback Vault index).
Then VACUUMs (page_size 4096), maps every blob's byte position (tools/dbmap.py -> db/blobmap.json, checked by sha256) and splits the file into 256 KB chunk files under dist/db/ (far under the 25 MB limit).
The browser fetches only the chunk files a query touches (sql.js-httpvfs, chunked mode; one file per request, because
Cloudflare Pages answers Range requests with the whole file) - no server, no D1. - Sion's Tab agent"""
import json, os, re, sys, sqlite3, hashlib, pathlib, posixpath, html as H, mimetypes, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'themes.json'))
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
OUT = DIST / 'db'; OUT.mkdir(parents=True, exist_ok=True)
DBF = pathlib.Path('cedwyn.sqlite3'); DBF.unlink(missing_ok=True)
CHUNK = int(os.environ.get('DB_CHUNK', 256 * 1024))   # Pages serves whole files (no Range), so each chunk file = one request; 256 KB since stage 3 (theme pages read single files from the DB)
BLOB_MAX = int(os.environ.get('BLOB_MAX', 2_500_000)); BLOB_TOTAL = int(os.environ.get('BLOB_TOTAL', 700_000_000))
TIDS = [t['id'] for t in CFG['themes']]; D = len(DIST.parts)
KIND = {'.html':'page','.htm':'page','.json':'data','.geojson':'data','.csv':'data','.xml':'data','.txt':'text','.md':'text','.css':'style','.js':'script','.mjs':'script',
        '.jpg':'image','.jpeg':'image','.png':'image','.gif':'image','.webp':'image','.svg':'image','.avif':'image','.ico':'image','.bmp':'image','.tif':'image','.tiff':'image',
        '.pdf':'document','.doc':'document','.docx':'document','.mp3':'audio','.m4a':'audio','.ogg':'audio','.wav':'audio','.mp4':'video','.webm':'video','.mov':'video',
        '.woff':'font','.woff2':'font','.ttf':'font','.otf':'font','.eot':'font'}
BLOB_KINDS = {'image', 'document', 'audio', 'data'}   # 'data': every theme's own JSON/CSV/XML feeds live in the catalogue too (stage 2)
YEAR = re.compile(r'\b(1[0-9]{3}|20[0-2][0-9])\b')
con = sqlite3.connect(DBF); con.execute('PRAGMA page_size=4096'); con.execute('PRAGMA journal_mode=OFF'); con.execute('PRAGMA synchronous=OFF')
con.executescript('''
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE themes(id TEXT PRIMARY KEY, title TEXT, cy TEXT, es TEXT, live TEXT, source TEXT, n_files INTEGER, n_pages INTEGER);
CREATE TABLE artifacts(id INTEGER PRIMARY KEY, sha TEXT UNIQUE, kind TEXT, mime TEXT, bytes INTEGER, title TEXT, year_min INTEGER, year_max INTEGER, has_blob INTEGER DEFAULT 0, ext_url TEXT);
CREATE TABLE locations(aid INTEGER, theme TEXT, path TEXT PRIMARY KEY, url TEXT) WITHOUT ROWID;
CREATE INDEX loc_aid ON locations(aid);
CREATE INDEX loc_theme ON locations(theme, aid);
CREATE TABLE nodes(id TEXT PRIMARY KEY, kind TEXT, label TEXT) WITHOUT ROWID;
CREATE TABLE edges(src TEXT, rel TEXT, dst TEXT, PRIMARY KEY(src, rel, dst)) WITHOUT ROWID;
CREATE INDEX edges_dst ON edges(dst, rel);
CREATE TABLE captures(key TEXT PRIMARY KEY, url TEXT, title TEXT, latest TEXT, captured TEXT) WITHOUT ROWID;
CREATE VIRTUAL TABLE fts USING fts5(title, body, aid UNINDEXED, theme UNINDEXED, path UNINDEXED, tokenize='porter unicode61');
CREATE TABLE blobs(sha TEXT PRIMARY KEY, data BLOB);
CREATE TABLE evidence_text(
  aid INTEGER PRIMARY KEY, path TEXT NOT NULL, title TEXT, body TEXT NOT NULL,
  body_chars INTEGER NOT NULL, truncated INTEGER NOT NULL DEFAULT 0
);
''')
def text_of_html(s):
    t = re.search(r'<title[^>]*>(.*?)</title>', s, re.S | re.I)
    title = H.unescape(re.sub(r'\s+', ' ', t.group(1))).strip()[:300] if t else ''
    b = re.sub(r'(?is)<(script|style|noscript|svg|template)\b.*?</\1>', ' ', s)
    b = re.sub(r'(?s)<!--.*?-->', ' ', b); b = re.sub(r'<[^>]+>', ' ', b)
    return title, re.sub(r'\s+', ' ', H.unescape(b)).strip()
def strings_of_json(s):
    try: o = json.loads(s)
    except Exception: return ''
    out = []
    def walk(x):
        if len(out) > 4000: return
        if isinstance(x, str):
            if len(x) > 2 and not x.startswith(('http', '/', 'data:')): out.append(x)
        elif isinstance(x, dict): [walk(v) for v in x.values()]
        elif isinstance(x, list): [walk(v) for v in x]
    walk(o); return ' '.join(out)
def node(nid, kind, label): con.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?)', (nid, kind, label))
def edge(s, r, d): con.execute('INSERT OR IGNORE INTO edges VALUES(?,?,?)', (s, r, d))
for t in CFG['themes']:
    node('theme:' + t['id'], 'theme', t['title'])
for g in CFG.get('groups', []):
    node('group:' + g['id'], 'group', g['title'])
for t in CFG['themes']:
    if t.get('group'): edge('theme:' + t['id'], 'in_group', 'group:' + t['group'])
sha_id = {}; blob_total = 0; blob_skipped = 0; path_aid = {}; pending = []
files = sorted(p for p in DIST.rglob('*') if p.is_file() and len(p.parts) > D + 1 and (p.parts[D] in TIDS or p.parts[D] == '_blob') and not (p.parent.name == '_db' and p.name.startswith('section.sqlite')))
for p in files:
    rel = '/' + '/'.join(p.parts[D:]); theme = p.parts[D]; ext = p.suffix.lower(); kind = KIND.get(ext, 'other')
    data = p.read_bytes(); sha = hashlib.sha256(data).hexdigest()
    aid = sha_id.get(sha)
    if aid is None:
        title = ''; body = ''
        if kind == 'page':
            title, body = text_of_html(data.decode('utf-8', 'ignore'))
        elif ext == '.json' and len(data) < 15_000_000:
            body = strings_of_json(data.decode('utf-8', 'ignore'))
        elif kind == 'text' and len(data) < 5_000_000:
            body = data.decode('utf-8', 'ignore')
        if not title: title = urllib.parse.unquote(p.name)
        ys = sorted({int(y) for y in YEAR.findall(body[:200000]) if 1066 <= int(y) <= 2026}) if body else []
        mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
        cur = con.execute('INSERT INTO artifacts(sha,kind,mime,bytes,title,year_min,year_max) VALUES(?,?,?,?,?,?,?)',
                          (sha, kind, mime, len(data), title, ys[0] if ys else None, ys[-1] if ys else None))
        aid = cur.lastrowid; sha_id[sha] = aid
        if body or kind == 'page':
            con.execute('INSERT INTO fts(title, body, aid, theme, path) VALUES(?,?,?,?,?)', (title, body[:6000], aid, theme, rel))
        for y in ys[:24]:
            node(f'year:{y}', 'year', str(y)); edge(f'a:{aid}', 'mentions', f'year:{y}')
        if kind in BLOB_KINDS:
            if len(data) <= BLOB_MAX and blob_total + len(data) <= BLOB_TOTAL:
                pending.append((0 if kind == 'data' else 1, theme, rel, sha, p)); blob_total += len(data)   # written below, clustered
                con.execute('UPDATE artifacts SET has_blob=1 WHERE id=?', (aid,))
            else: blob_skipped += 1
    con.execute('INSERT OR IGNORE INTO locations VALUES(?,?,?,?)', (aid, theme, rel, rel)); path_aid[rel] = aid
    # Preserve the complete plain-text evidence entry in the central DB; generic FTS text is short.
    if kind == 'page' and re.search(r'/(?:research|wiki)/evidence/ev-[0-9]{4}-[^/]+/index\.html$', rel, re.I):
        evidence_title, evidence_body = text_of_html(data.decode('utf-8', 'ignore'))
        evidence_body = evidence_body or ''
        con.execute('INSERT OR REPLACE INTO evidence_text VALUES(?,?,?,?,?,?)',
                    (aid, rel, evidence_title, evidence_body[:40000], len(evidence_body), int(len(evidence_body) > 40000)))
    if theme != '_blob': edge(f'a:{aid}', 'in_theme', 'theme:' + theme)
# blob rows are written clustered: every theme's JSON/CSV/XML first, then media, each grouped by theme and path, so the
# few chunk files one theme page needs sit next to each other in the database file (stage 3: themes read from the DB)
for _, _, _, sha, p in sorted(pending, key=lambda x: x[:3]):
    con.execute('INSERT OR IGNORE INTO blobs VALUES(?,?)', (sha, p.read_bytes()))
del pending
# files the content-addressed store took out of a theme: record where they appeared, served from /_blob/
_bm = json.load(open(DIST / '_blob_map.json')) if (DIST / '_blob_map.json').exists() else {}
for orig, bl in _bm.items():
    if orig in path_aid or bl not in path_aid: continue
    th = orig.split('/')[1]; aid = path_aid[bl]
    con.execute('INSERT OR IGNORE INTO locations VALUES(?,?,?,?)', (aid, th, orig, bl)); path_aid[orig] = aid
    edge(f'a:{aid}', 'in_theme', 'theme:' + th)
# graph edges from pages: embeds / links / cites
ATT = re.compile(r'''\s(href|src|poster|data-src)\s*=\s*["']([^"']+)["']''', re.I)
blobmap = json.load(open(DIST / '_blob_map.json')) if (DIST / '_blob_map.json').exists() else {}
n_ext = 0
for p in files:
    if p.suffix.lower() not in ('.html', '.htm') or p.parts[D] == '_blob': continue
    rel = '/' + '/'.join(p.parts[D:]); src = path_aid.get(rel)
    s = p.read_text('utf-8', 'ignore')
    for attr, u in ATT.findall(s):
        if u.startswith('/wayback/go/?u='):
            ou = urllib.parse.unquote(u[15:]); host = (urllib.parse.urlsplit(ou).hostname or '').lower()
            if host: node('host:' + host, 'host', host); edge(f'a:{src}', 'cites', 'host:' + host); n_ext += 1
            continue
        if u.startswith(('http', '//', 'data:', '#', 'mailto:', 'javascript:')): continue
        path = u.split('#')[0].split('?')[0]
        if not path: continue
        absp = path if path.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(rel), path))
        absp = urllib.parse.unquote(absp)
        if absp.endswith('/'): absp += 'index.html'
        dst = path_aid.get(absp) or path_aid.get(absp + '/index.html') or path_aid.get(absp + '.html')
        if dst and dst != src: edge(f'a:{src}', 'embeds' if attr.lower() != 'href' else 'links', f'a:{dst}')
# captures from the Wayback Vault index
wi = DIST / 'wayback' / 'websites' / 'index.json'
if wi.exists():
    try:
        for it in json.load(open(wi)).get('items', []):
            con.execute('INSERT OR IGNORE INTO captures VALUES(?,?,?,?,?)', (it.get('key'), it.get('url'), it.get('title'), '/wayback' + (it.get('latest') or ''), it.get('captured')))
    except Exception as e: print('captures: ', e)
# Layers (25 Oct 2026): a layer is a reading over the same evidence, stored as rows that point at artifacts already in this
# database (never copies). First layer: "1000 Cuts" (web/thousand-cuts/cuts.json) - the dated cuts to the Williams family's
# standing in law, each with its evidence pages (artifact ids via locations) and its dependencies (graph edges cut->depends_on->cut). - Sion's Tab agent
con.executescript('''
CREATE TABLE IF NOT EXISTS layers(id TEXT PRIMARY KEY, title TEXT, subtitle TEXT, version TEXT, built TEXT, doc TEXT);
CREATE TABLE IF NOT EXISTS layer_items(layer TEXT, id TEXT, kind TEXT, seq INTEGER, tier INTEGER, date TEXT, event TEXT, blow TEXT, label TEXT, context INTEGER, PRIMARY KEY(layer, id)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS layer_refs(layer TEXT, item TEXT, ev TEXT, path TEXT, aid INTEGER);
CREATE TABLE IF NOT EXISTS layer_deps(layer TEXT, item TEXT, depends_on TEXT, PRIMARY KEY(layer, item, depends_on)) WITHOUT ROWID;
''')
n_layer_items = n_layer_refs = n_layer_deps = 0
for lf in sorted(DIST.glob('*/layer.json')):
    try: L = json.load(open(lf))
    except Exception as e: print('layer', lf, e); continue
    lid = L['slug']; slim = {k: v for k, v in L.items() if k not in ('peak', 'cuts')}
    con.execute('INSERT OR REPLACE INTO layers VALUES(?,?,?,?,?,?)', (lid, L.get('title'), L.get('subtitle'), L.get('version'), L.get('built'), json.dumps(slim, ensure_ascii=False)))
    node('layer:' + lid, 'layer', L.get('title') or lid)
    items = [dict(x, kind='peak', layer_n=0) for x in L.get('peak', [])] + [dict(x, kind='cut', layer_n=x.get('layer', 0)) for x in L.get('cuts', [])]
    for seq, x in enumerate(items):
        con.execute('INSERT OR REPLACE INTO layer_items VALUES(?,?,?,?,?,?,?,?,?,?)', (lid, x['id'], x['kind'], seq, int(x['layer_n']), x.get('date'), x.get('event'),
                    x.get('changed') or x.get('blow') or x.get('note'), x.get('label'), 1 if x.get('context') else 0)); n_layer_items += 1
        nid = f'{lid}:{x["id"]}'; node(nid, 'layer_item', (x.get('date', '') + ' ' + x.get('event', ''))[:120]); edge(nid, 'in_layer', 'layer:' + lid)
        for r in x.get('refs', []):
            p = '/' + (L.get('ref_theme') or 'research') + r['path']; p2 = p + 'index.html' if p.endswith('/') else p
            aid = path_aid.get(p2) or path_aid.get(p)
            con.execute('INSERT INTO layer_refs VALUES(?,?,?,?,?)', (lid, x['id'], r.get('ev'), p, aid)); n_layer_refs += 1
            if aid: edge(nid, 'cites', f'a:{aid}')
        for d in x.get('depends_on', []):
            con.execute('INSERT OR IGNORE INTO layer_deps VALUES(?,?,?)', (lid, x['id'], d)); n_layer_deps += 1
            edge(nid, 'depends_on', f'{lid}:{d}')
# Section databases (27 Oct 2026): a section branch may ship its own SQLite database at <section>/_db/section.sqlite, table
# records(kind TEXT, id TEXT, seq INTEGER, data TEXT) with one JSON object per row ("src" = the artifact path a record derives from,
# "image" = the artifact path it shows). Every section database is merged here into section_records, with graph edges
# record -> derived_from / shows -> artifact, so a section's words and data are read from this one catalogue and export with it.
con.execute('CREATE TABLE IF NOT EXISTS section_records(theme TEXT, kind TEXT, id TEXT, seq INTEGER, data TEXT, PRIMARY KEY(theme, kind, id)) WITHOUT ROWID')
n_section_records = 0
for _sf in sorted(DIST.glob('*/_db/section.sqlite')):
    _th = _sf.parts[D]
    if _th not in TIDS: continue
    try:
        _sc = sqlite3.connect(f'file:{_sf}?mode=ro', uri=True)
        _rows = _sc.execute('SELECT kind, id, seq, data FROM records ORDER BY seq').fetchall(); _sc.close()
    except Exception as e: print('section db', _sf, e); continue
    for _kind, _rid, _seq, _data in _rows:
        con.execute('INSERT OR REPLACE INTO section_records VALUES(?,?,?,?,?)', (_th, _kind, _rid, _seq, _data)); n_section_records += 1
        _nid = f'{_th}:{_rid}'; node(_nid, 'record', f'{_th} {_kind} {_rid}'[:120]); edge(_nid, 'in_theme', 'theme:' + _th)
        try: _x = json.loads(_data)
        except Exception: _x = {}
        for _key, _rel in (('src', 'derived_from'), ('image', 'shows')):
            _p = _x.get(_key) if isinstance(_x, dict) else None
            if isinstance(_p, str) and path_aid.get(_p): edge(_nid, _rel, f'a:{path_aid[_p]}')
print('section records:', n_section_records)
# Evidence catalogue: stable EV key, aliases, grade/provenance metadata and full evidence-page text.
con.execute('CREATE TABLE IF NOT EXISTS evidence_grades(ev TEXT PRIMARY KEY, grade INTEGER, origin TEXT, path TEXT, note TEXT) WITHOUT ROWID')
con.execute('''CREATE TABLE IF NOT EXISTS evidence_catalogue(
 ev TEXT PRIMARY KEY, artifact_id INTEGER, path TEXT NOT NULL, evidence_grade INTEGER,
 independent_origin_id TEXT, aliases_json TEXT NOT NULL DEFAULT '[]', grade_note TEXT, title TEXT
) WITHOUT ROWID''')
_eg = ROOT / 'data' / 'evidence-grades.json'
if _eg.exists():
    _evidence_doc = json.load(open(_eg, encoding='utf-8'))
    con.execute('CREATE TABLE IF NOT EXISTS evidence_catalogue_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID')
    for _key in ('version', 'date', 'status', 'rule_verified', 'independent_origin_id'):
        if _key in _evidence_doc:
            _value = _evidence_doc[_key]
            _value = _value if isinstance(_value, str) else json.dumps(_value, ensure_ascii=False)
            con.execute('INSERT OR REPLACE INTO evidence_catalogue_meta VALUES(?,?)', (_key, _value))
    con.execute('CREATE TABLE IF NOT EXISTS evidence_grade_scale(grade INTEGER PRIMARY KEY, meaning TEXT NOT NULL) WITHOUT ROWID')
    for _grade, _meaning in _evidence_doc.get('scale', {}).items():
        con.execute('INSERT OR REPLACE INTO evidence_grade_scale VALUES(?,?)', (int(_grade), str(_meaning)))
    for _x in _evidence_doc.get('evidence', []):
        _ev = (_x.get('ev') or '').strip()
        _rawpath = (_x.get('path') or '').strip()
        _p = _rawpath if _rawpath.startswith('/') else ('/' + _rawpath if _rawpath else '')
        _p_lookup = _p.rstrip('/') + '/index.html' if _p else ''
        _aid = (path_aid.get(_p_lookup) or path_aid.get(_p) or path_aid.get(_p.rstrip('/') + '/')) if _p else None
        _title_row = con.execute('SELECT title FROM artifacts WHERE id=?', (_aid,)).fetchone() if _aid else None
        _title = (_title_row[0] if _title_row else '') or ''
        con.execute('INSERT OR REPLACE INTO evidence_grades VALUES(?,?,?,?,?)',
                    (_ev, _x.get('evidence_grade'), _x.get('independent_origin_id'), _rawpath, _x.get('grade_note')))
        if _ev:
            con.execute('''INSERT OR REPLACE INTO evidence_catalogue
                (ev, artifact_id, path, evidence_grade, independent_origin_id, aliases_json, grade_note, title)
                VALUES(?,?,?,?,?,?,?,?)''',
                (_ev, _aid, _rawpath, _x.get('evidence_grade'), _x.get('independent_origin_id'),
                 json.dumps(_x.get('aliases', []), ensure_ascii=False), _x.get('grade_note'), _title))

# Complete the EV index from actual built evidence pages as well as data/evidence-grades.json.
# Discovering a page does not invent a grade or establish an independent source origin.
_ev_pages = {}
for _rel in path_aid:
    _m = re.match(r'^/(?:research|wiki)/evidence/(ev-[0-9]{4}-[^/]+)/index[.]html$', _rel, re.I)
    if not _m:
        continue
    _number = re.match(r'^ev-([0-9]{4})-', _m.group(1), re.I)
    if not _number:
        continue
    _ev = 'EV-' + _number.group(1)
    _prio = 0 if _rel.startswith('/research/') else 1
    if _ev not in _ev_pages or _prio < _ev_pages[_ev][0]:
        _ev_pages[_ev] = (_prio, _rel)
for _ev, (_, _epath) in sorted(_ev_pages.items()):
    if con.execute('SELECT 1 FROM evidence_catalogue WHERE ev=?', (_ev,)).fetchone():
        continue
    _aid = path_aid.get(_epath)
    _title_row = con.execute('SELECT title FROM artifacts WHERE id=?', (_aid,)).fetchone() if _aid else None
    _page_path = _epath.rsplit('/index.html', 1)[0] + '/'
    con.execute('''INSERT OR IGNORE INTO evidence_catalogue
        (ev, artifact_id, path, evidence_grade, independent_origin_id, aliases_json, grade_note, title)
        VALUES(?,?,?,NULL,NULL,'[]','Not yet assessed in data/evidence-grades.json',?)''',
        (_ev, _aid, _page_path, (_title_row[0] if _title_row else _epath)))

# Level 1: neutral description, transcript and interpretation are separate assessment fields.
con.execute('''CREATE TABLE IF NOT EXISTS artifact_assessments(
 ev TEXT PRIMARY KEY, artifact_id INTEGER, description TEXT NOT NULL DEFAULT '',
 description_status TEXT NOT NULL DEFAULT 'not_assessed',
 transcript TEXT NOT NULL DEFAULT '', transcript_status TEXT NOT NULL DEFAULT 'not_assessed',
 interpretation TEXT NOT NULL DEFAULT '', interpretation_status TEXT NOT NULL DEFAULT 'not_assessed',
 source_verification_status TEXT NOT NULL DEFAULT 'not_assessed',
 limitations TEXT NOT NULL DEFAULT '', csscpsg_json TEXT NOT NULL DEFAULT '', updated_at TEXT
) WITHOUT ROWID''')
con.execute('''INSERT OR IGNORE INTO artifact_assessments
 (ev, artifact_id, description_status, transcript_status, interpretation_status, source_verification_status)
 SELECT ev, artifact_id, 'not_assessed', 'not_assessed', 'not_assessed', 'not_assessed'
 FROM evidence_catalogue''')
_assessment_path = ROOT / 'data' / 'artifact-assessments.json'
if _assessment_path.exists():
    _assessment_doc = json.load(open(_assessment_path, encoding='utf-8'))
    _defaults = _assessment_doc.get('defaults', {})
    _assessment_fields = ('description', 'description_status', 'transcript', 'transcript_status',
                          'interpretation', 'interpretation_status', 'source_verification_status', 'limitations')
    for _item in _assessment_doc.get('items', []):
        _ev = str(_item.get('ev', '')).strip().upper()
        if not _ev:
            continue
        _catalogue_row = con.execute('SELECT artifact_id FROM evidence_catalogue WHERE ev=?', (_ev,)).fetchone()
        _aid = _catalogue_row[0] if _catalogue_row else None
        _values = [_item.get(_field, _defaults.get(_field, '')) for _field in _assessment_fields]
        _csscpsg = _item.get('csscpsg')
        _csscpsg_json = json.dumps(_csscpsg, ensure_ascii=False) if _csscpsg else ''
        con.execute('''INSERT OR REPLACE INTO artifact_assessments
          (ev, artifact_id, description, description_status, transcript, transcript_status,
           interpretation, interpretation_status, source_verification_status, limitations, csscpsg_json, updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
          (_ev, _aid, *_values, _csscpsg_json, _assessment_doc.get('date', '2026-10-29')))

# Level 2: derived observations cite the Level 1 records without replacing them.
con.execute('''CREATE TABLE IF NOT EXISTS observations(
 id TEXT PRIMARY KEY, slug TEXT UNIQUE NOT NULL, seq INTEGER NOT NULL,
 title TEXT NOT NULL, theme TEXT NOT NULL, observation_type TEXT NOT NULL,
 status TEXT NOT NULL, summary TEXT NOT NULL, analysis TEXT NOT NULL,
 limits TEXT NOT NULL, test_questions_json TEXT NOT NULL, related_page TEXT,
 page_path TEXT NOT NULL, updated_at TEXT
) WITHOUT ROWID''')
con.execute('''CREATE TABLE IF NOT EXISTS observation_refs(
 observation_id TEXT NOT NULL, seq INTEGER NOT NULL, ev TEXT, path TEXT NOT NULL,
 role TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', artifact_id INTEGER,
 PRIMARY KEY(observation_id, seq)
) WITHOUT ROWID''')
_observation_path = ROOT / 'data' / 'observations.json'
if _observation_path.exists():
    _observation_doc = json.load(open(_observation_path, encoding='utf-8'))
    for _obs in _observation_doc.get('items', []):
        _oid = str(_obs.get('id', '')).strip()
        _slug = str(_obs.get('slug', '')).strip()
        if not _oid or not _slug:
            continue
        _page_path = '/wiki/observations/' + _slug + '/'
        con.execute('''INSERT OR REPLACE INTO observations
          (id, slug, seq, title, theme, observation_type, status, summary, analysis, limits,
           test_questions_json, related_page, page_path, updated_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
          (_oid, _slug, int(_obs.get('seq', 0)), _obs.get('title', ''), _obs.get('theme', 'wiki'),
           _obs.get('observation_type', 'pattern'), _obs.get('status', 'working_observation'),
           _obs.get('summary', ''), _obs.get('analysis', ''), _obs.get('limits', ''),
           json.dumps(_obs.get('test_questions', []), ensure_ascii=False), _obs.get('related_page'),
           _page_path, _observation_doc.get('date', '2026-10-29')))
        con.execute('DELETE FROM observation_refs WHERE observation_id=?', (_oid,))
        _node_id = 'observation:' + _oid
        node(_node_id, 'observation', _obs.get('title', _oid))
        edge(_node_id, 'in_theme', 'theme:' + str(_obs.get('theme', 'wiki')))
        for _seq, _ref in enumerate(_obs.get('refs', []), 1):
            _ref_ev = str(_ref.get('ev') or '').strip().upper() or None
            _ref_path = str(_ref.get('path') or '').strip()
            _ref_aid = None
            if _ref_ev:
                _er = con.execute('SELECT artifact_id, path FROM evidence_catalogue WHERE ev=?', (_ref_ev,)).fetchone()
                if _er:
                    _ref_aid = _er[0]
                    if not _ref_path:
                        _ref_path = _er[1] or ''
            if _ref_path:
                _rp = _ref_path.rstrip('/')
                for _candidate in (_rp + '/index.html', _rp, _rp + '.html'):
                    if path_aid.get(_candidate):
                        _ref_aid = _ref_aid or path_aid[_candidate]
                        break
            if not _ref_path and _ref_ev:
                _er = con.execute('SELECT path FROM evidence_catalogue WHERE ev=?', (_ref_ev,)).fetchone()
                _ref_path = (_er[0] if _er else '') or ''
            con.execute('INSERT OR REPLACE INTO observation_refs VALUES(?,?,?,?,?,?,?)',
                (_oid, _seq, _ref_ev, _ref_path, _ref.get('role', ''), _ref.get('note', ''), _ref_aid))
            if _ref_aid:
                edge(_node_id, 'cites', f'a:{_ref_aid}')
                edge(f'a:{_ref_aid}', 'cited_by_observation', _node_id)

for t in CFG['themes']:
    nf = con.execute('SELECT count(*) FROM locations WHERE theme=?', (t['id'],)).fetchone()[0]
    npg = con.execute("SELECT count(*) FROM locations l JOIN artifacts a ON a.id=l.aid WHERE l.theme=? AND a.kind='page'", (t['id'],)).fetchone()[0]
    con.execute('INSERT INTO themes VALUES(?,?,?,?,?,?,?,?)', (t['id'], t['title'], t.get('cy'), t.get('es'), t['live'],
                 ('branch ' + t['branch']) if t.get('branch') else ('crawl of ' + t.get('crawl', '')), nf, npg))

# Title Theory: normalized, testable hypothesis data in the master catalogue, with graph edges to Level 1 artifacts.
con.executescript("""
CREATE TABLE IF NOT EXISTS title_theories(
 model_id TEXT PRIMARY KEY, slug TEXT NOT NULL, title TEXT NOT NULL, version TEXT NOT NULL,
 status TEXT NOT NULL, summary TEXT NOT NULL, model_json TEXT NOT NULL, page_path TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS title_theory_hypotheses(
 model_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL, rank INTEGER NOT NULL, title TEXT NOT NULL,
 classification TEXT NOT NULL, status TEXT NOT NULL, explanation TEXT NOT NULL,
 data_json TEXT NOT NULL, PRIMARY KEY(model_id, hypothesis_id)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS title_theory_events(
 model_id TEXT NOT NULL, event_id TEXT NOT NULL, period TEXT NOT NULL, stage TEXT NOT NULL,
 proposition TEXT NOT NULL, if_true TEXT NOT NULL, alternative TEXT NOT NULL,
 data_json TEXT NOT NULL, PRIMARY KEY(model_id, event_id)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS title_theory_edges(
 model_id TEXT NOT NULL, from_id TEXT NOT NULL, to_id TEXT NOT NULL,
 relation TEXT NOT NULL, status TEXT NOT NULL, note TEXT NOT NULL,
 PRIMARY KEY(model_id, from_id, to_id, relation)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS title_theory_tests(
 model_id TEXT NOT NULL, test_id TEXT NOT NULL, title TEXT NOT NULL, purpose TEXT NOT NULL,
 data_json TEXT NOT NULL, PRIMARY KEY(model_id, test_id)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS title_theory_refs(
 model_id TEXT NOT NULL, seq INTEGER NOT NULL, ev TEXT, path TEXT NOT NULL,
 role TEXT NOT NULL, note TEXT NOT NULL, artifact_id INTEGER,
 PRIMARY KEY(model_id, seq)
) WITHOUT ROWID;
""")
_title_theory_path = ROOT / "data" / "title-theory.json"
_n_tt_hyp = _n_tt_events = _n_tt_edges = _n_tt_tests = _n_tt_refs = 0
if _title_theory_path.exists():
    _tt = json.loads(_title_theory_path.read_text(encoding="utf-8"))
    _ttid = str(_tt.get("model_id", "TT-UNKNOWN"))
    _ttnode = "title_theory:" + _ttid
    con.execute("INSERT OR REPLACE INTO title_theories VALUES(?,?,?,?,?,?,?,?,?)", (
        _ttid, "title-theory", _tt.get("title", ""), _tt.get("version", ""),
        _tt.get("status", ""), _tt.get("summary", ""),
        json.dumps(_tt, ensure_ascii=False), "/wiki/title-theory/",
        _tt.get("updated_at", "")))
    node(_ttnode, "title_theory", _tt.get("title", _ttid))
    edge(_ttnode, "in_theme", "theme:wiki")
    for _h in _tt.get("hypotheses", []):
        _hid = str(_h.get("id", ""))
        if not _hid: continue
        con.execute("INSERT OR REPLACE INTO title_theory_hypotheses VALUES(?,?,?,?,?,?,?,?)", (
            _ttid, _hid, int(_h.get("rank", 999)), _h.get("title", ""),
            _h.get("class", ""), _h.get("status", ""), _h.get("explanation", ""),
            json.dumps(_h, ensure_ascii=False)))
        _hn = "title_hypothesis:" + _ttid + ":" + _hid
        node(_hn, "title_hypothesis", _h.get("title", _hid))
        edge(_ttnode, "has_hypothesis", _hn)
        _n_tt_hyp += 1
    for _e in _tt.get("working_mechanism", []):
        _eid = str(_e.get("id", ""))
        if not _eid: continue
        con.execute("INSERT OR REPLACE INTO title_theory_events VALUES(?,?,?,?,?,?,?,?)", (
            _ttid, _eid, _e.get("period", ""), _e.get("stage", ""),
            _e.get("proposition", ""), _e.get("if_true", ""),
            _e.get("against_or_alternative", ""), json.dumps(_e, ensure_ascii=False)))
        _en = "title_theory_event:" + _ttid + ":" + _eid
        node(_en, "title_theory_event", _e.get("stage", _eid))
        edge(_ttnode, "has_event", _en)
        for _ev in _e.get("source_evs", []):
            _er = con.execute("SELECT artifact_id FROM evidence_catalogue WHERE ev=?", (str(_ev).upper(),)).fetchone()
            if _er and _er[0]:
                edge(_en, "cites", "a:" + str(_er[0]))
                edge("a:" + str(_er[0]), "cited_by_title_theory", _en)
        _n_tt_events += 1
    for _gn in _tt.get("causal_graph", {}).get("nodes", []):
        _gnid = str(_gn.get("id", ""))
        if not _gnid: continue
        _nid = "title_theory_node:" + _ttid + ":" + _gnid
        node(_nid, "title_theory_node", _gn.get("label", _gnid))
        edge(_ttnode, "has_graph_node", _nid)
    for _g in _tt.get("causal_graph", {}).get("edges", []):
        con.execute("INSERT OR REPLACE INTO title_theory_edges VALUES(?,?,?,?,?,?)", (
            _ttid, _g.get("from", ""), _g.get("to", ""), _g.get("relation", ""),
            _g.get("status", ""), _g.get("note", "")))
        _n_tt_edges += 1
    for _s in _tt.get("simulations", []):
        _sid = str(_s.get("id", ""))
        if not _sid: continue
        con.execute("INSERT OR REPLACE INTO title_theory_tests VALUES(?,?,?,?,?)", (
            _ttid, _sid, _s.get("title", ""), _s.get("purpose", ""),
            json.dumps(_s, ensure_ascii=False)))
        _n_tt_tests += 1
    for _seq, _r in enumerate(_tt.get("evidence_refs", []), 1):
        _ev = str(_r.get("ev", "")).upper() or None
        _path = str(_r.get("path", ""))
        _aid = None
        if _ev:
            _row = con.execute("SELECT artifact_id FROM evidence_catalogue WHERE ev=?", (_ev,)).fetchone()
            if _row: _aid = _row[0]
        if not _aid and _path:
            _p = _path.rstrip("/")
            for _candidate in (_p + "/index.html", _p, _p + ".html"):
                if path_aid.get(_candidate):
                    _aid = path_aid[_candidate]; break
        con.execute("INSERT OR REPLACE INTO title_theory_refs VALUES(?,?,?,?,?,?,?)", (
            _ttid, _seq, _ev, _path, _r.get("role", ""), _r.get("note", ""), _aid))
        if _aid:
            edge(_ttnode, "cites", "a:" + str(_aid))
            edge("a:" + str(_aid), "cited_by_title_theory", _ttnode)
        _n_tt_refs += 1
    for _edge in _tt.get("causal_graph", {}).get("edges", []):
        _from = "title_theory_node:" + _ttid + ":" + str(_edge.get("from", ""))
        _to = "title_theory_node:" + _ttid + ":" + str(_edge.get("to", ""))
        if _edge.get("from") and _edge.get("to"):
            edge(_from, str(_edge.get("relation", "related_to")), _to)

# Parcel-story register: parent DB is canonical; section_dbs.py projects one story into each public-area child DB.
con.executescript("""
CREATE TABLE IF NOT EXISTS estate_parcels (
 parcel_id TEXT PRIMARY KEY, area_id TEXT NOT NULL UNIQUE, slot INTEGER NOT NULL UNIQUE,
 title TEXT NOT NULL, historic_plot_number TEXT, model_parcel_id TEXT,
 mapping_status TEXT NOT NULL, map_asset TEXT NOT NULL, map_status TEXT NOT NULL,
 summary TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS parcel_events (
 parcel_id TEXT NOT NULL, seq INTEGER NOT NULL, date_text TEXT NOT NULL, title TEXT NOT NULL,
 details TEXT NOT NULL, event_type TEXT NOT NULL, scope TEXT NOT NULL, status TEXT NOT NULL,
 source_ev TEXT, source_path TEXT, PRIMARY KEY(parcel_id, seq)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS estate_parcel_model (
 model_id TEXT PRIMARY KEY, parent_id TEXT, label TEXT NOT NULL, status TEXT NOT NULL,
 description TEXT NOT NULL, limits TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS estate_parcel_model_events (
 model_id TEXT NOT NULL, seq INTEGER NOT NULL, date_text TEXT NOT NULL, title TEXT NOT NULL,
 details TEXT NOT NULL, event_type TEXT NOT NULL, status TEXT NOT NULL,
 source_evs_json TEXT NOT NULL, source_path TEXT, PRIMARY KEY(model_id, seq)
) WITHOUT ROWID;
""")
_parcel_file = ROOT / "data" / "parcel-stories.json"
if _parcel_file.exists():
    _parcel_doc = json.loads(_parcel_file.read_text(encoding="utf-8"))
    for _tbl in ("parcel_events", "estate_parcels", "estate_parcel_model_events", "estate_parcel_model"):
        con.execute("DELETE FROM " + _tbl)
    for _p in _parcel_doc.get("parcels", []):
        con.execute("INSERT INTO estate_parcels VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
            _p["parcel_id"], _p["area_id"], int(_p["slot"]), _p["title"],
            _p.get("historic_plot_number"), _p.get("model_parcel_id"), _p["mapping_status"],
            _p.get("map_asset", "/parcels/poster.jpg"), _p.get("map_status", "pending"),
            _p.get("summary", ""), _p.get("updated_at", _parcel_doc.get("updated_at", ""))))
        for _e in _p.get("events", []):
            con.execute("INSERT INTO parcel_events VALUES(?,?,?,?,?,?,?,?,?,?)", (
                _p["parcel_id"], int(_e.get("seq", 0)), _e.get("date_text", ""),
                _e.get("title", ""), _e.get("details", ""), _e.get("event_type", ""),
                _e.get("scope", ""), _e.get("status", ""), _e.get("source_ev"), _e.get("source_path")))
    for _m in _parcel_doc.get("parcel_model", []):
        con.execute("INSERT INTO estate_parcel_model VALUES(?,?,?,?,?,?)", (
            _m["model_id"], _m.get("parent_id"), _m.get("label", ""), _m.get("status", ""),
            _m.get("description", ""), _m.get("limits", "")))
    for _e in _parcel_doc.get("model_events", []):
        con.execute("INSERT INTO estate_parcel_model_events VALUES(?,?,?,?,?,?,?,?,?)", (
            _e["model_id"], int(_e.get("seq", 0)), _e.get("date_text", ""),
            _e.get("title", ""), _e.get("details", ""), _e.get("event_type", ""),
            _e.get("status", ""), json.dumps(_e.get("source_evs", []), ensure_ascii=False),
            _e.get("source_path")))

cnt = lambda q: con.execute(q).fetchone()[0]
stats = dict(artifacts=cnt('SELECT count(*) FROM artifacts'), locations=cnt('SELECT count(*) FROM locations'), blobs=cnt('SELECT count(*) FROM blobs'),
             blob_bytes=blob_total, blob_skipped_over_cap=blob_skipped, edges=cnt('SELECT count(*) FROM edges'), nodes=cnt('SELECT count(*) FROM nodes'),
             fts_rows=cnt('SELECT count(*) FROM fts'), captures=cnt('SELECT count(*) FROM captures'), cites=n_ext, themes=len(TIDS),
             layer_items=n_layer_items, layer_refs=n_layer_refs, layer_deps=n_layer_deps,
             evidence_records=cnt('SELECT count(*) FROM evidence_catalogue'), evidence_texts=cnt('SELECT count(*) FROM evidence_text'),
             artifact_assessments=cnt('SELECT count(*) FROM artifact_assessments'), observations=cnt('SELECT count(*) FROM observations'), observation_refs=cnt('SELECT count(*) FROM observation_refs'),
             parcel_stories=cnt('SELECT count(*) FROM estate_parcels'), parcel_events=cnt('SELECT count(*) FROM parcel_events'),
             parcel_models=cnt('SELECT count(*) FROM estate_parcel_model'), parcel_model_events=cnt('SELECT count(*) FROM estate_parcel_model_events'),
              title_theories=cnt('SELECT count(*) FROM title_theories'), title_theory_hypotheses=cnt('SELECT count(*) FROM title_theory_hypotheses'),
              title_theory_events=cnt('SELECT count(*) FROM title_theory_events'), title_theory_edges=cnt('SELECT count(*) FROM title_theory_edges'),
              title_theory_tests=cnt('SELECT count(*) FROM title_theory_tests'), title_theory_refs=cnt('SELECT count(*) FROM title_theory_refs'))
for k, v in stats.items(): con.execute('INSERT INTO meta VALUES(?,?)', (k, str(v)))
con.commit()
# Emit small section-local SQLite slices from the same central catalogue. The main catalogue remains authoritative.
import section_dbs
section_db_stats = section_dbs.run(con, DIST, CFG, CHUNK)
con.execute("INSERT INTO fts(fts) VALUES('optimize')"); con.commit()
con.execute('VACUUM'); con.close()
size = DBF.stat().st_size
import dbmap   # stage 3: where every blob's bytes sit in the file, so the service worker reads them straight from the chunks
bm = dbmap.build(DBF, CHUNK, '/db/cedwyn.sqlite3.', 3)
json.dump(bm, open(OUT / 'blobmap.json', 'w'), separators=(',', ':'))
stats.update(blobmap_paths=len(bm['paths']), blobmap_blobs=len(bm['blobs']), db_version=bm['v'])
for old in OUT.glob('cedwyn.sqlite3.*'): old.unlink()
n = 0
with open(DBF, 'rb') as f:
    while True:
        b = f.read(CHUNK)
        if not b: break
        (OUT / ('cedwyn.sqlite3.%03d' % n)).write_bytes(b); n += 1
config = {'serverMode': 'chunked', 'requestChunkSize': CHUNK, 'databaseLengthBytes': size, 'serverChunkSize': CHUNK,
          'urlPrefix': '/db/cedwyn.sqlite3.', 'suffixLength': 3}
json.dump(config, open(OUT / 'config.json', 'w'))
stats.update(db_bytes=size, chunks=n, chunk_max_bytes=CHUNK)
json.dump(stats, open(OUT / 'stats.json', 'w'), indent=1)
# Whole-database export, portable and independent of any front end: /db/export/manifest.json,
# CSV + JSON + metadata SQLite + one slice per section + fetch-full.sh; never fails the build - docs library build
import db_export
db_export.run(DBF, OUT, stats)
DBF.unlink()
print(json.dumps(stats))
