#!/usr/bin/env python3
"""graph_data.py 1.2.0 - per-section scatter data for the header graph promo (cw-graph.js).
Asked for 01:27 GMT 30 Oct 2026: each webapp area's header banner opens a full-screen scatter graph of the data that area
shows. Runs at the end of site.py (wrapped in try: never stops a build). Writes dist/_cedwyn/graph/<area>.json in one compact
shape: {v, area, title, x:{label,type}, y:{label,type,cats}, c:{label,cats}, p:[[x, y, colour, label, href], ...]}.
Sources are files the build already ships: /qa/questions.json, /email/view/index.json, data/evidence-grades.json + the
evidence pages, and for every other area its own built pages (title + first date, by sub-folder). Areas with no dated
material get no file and cw-graph.js plots the page itself. - Cedwyn editors"""
import json, re, sys, html, pathlib
from collections import Counter
from urllib.parse import quote_plus

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAXP = 1000
DATE = re.compile(r'\b(1[0-9]\d\d|20[0-4]\d)-(\d\d)-(\d\d)\b|\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(1[0-9]\d\d|20[0-4]\d)\b|(?<![\w\-/#.])(1[0-9]\d\d|20[0-4]\d)(?![\w\-/])')
MON = {m: i + 1 for i, m in enumerate('January February March April May June July August September October November December'.split())}
BANNED = re.compile(r'\b(says|claims|according to|hearsay|unverified|alleged|fraud|stolen)\b', re.I)

def first_date(s):
    m = DATE.search(s or '')
    if not m: return None
    if m.group(1): return '%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
    if m.group(4): return '%s-%02d-%02d' % (m.group(6), MON[m.group(5)], int(m.group(4)))
    return m.group(7)

def label(s, n=110):
    s = re.sub(r'\s+', ' ', html.unescape(s or '')).strip()
    s = BANNED.sub('…', s)
    return s if len(s) <= n else s[:n - 1] + '…'

def top_cats(vals, mx):
    c = Counter(vals); ks = [k for k, _ in c.most_common()]
    if len(ks) > mx: ks = ks[:mx - 1] + ['Other']
    return ks

def pack(area, title, xl, yl, cl, rows, ymax=12, cmax=8):
    """rows: dicts with x (YYYY[-MM-DD]), y, c, l, h"""
    rows = [r for r in rows if r.get('x')]
    rows.sort(key=lambda r: str(r['x']))
    if len(rows) > MAXP: rows = rows[::-(-len(rows) // MAXP)]
    ys = top_cats([r['y'] for r in rows], ymax); cs = top_cats([r['c'] for r in rows], cmax)
    def ix(lst, v): return lst.index(v) if v in lst else len(lst) - 1
    return {'v': 1, 'area': area, 'title': title, 'x': {'label': xl, 'type': 'date'}, 'y': {'label': yl, 'type': 'cat', 'cats': ys},
            'c': {'label': cl, 'cats': cs}, 'p': [[str(r['x']), ix(ys, r['y']), ix(cs, r['c']), label(r['l'], 90), r.get('h') or ''] for r in rows]}

def qa(dist):
    f = dist / 'qa' / 'questions.json'
    if not f.exists(): return None
    j = json.loads(f.read_text('utf-8')); rows = []
    status = lambda s: 'Answered' if s in ('answered', 'partly answered', 'reply received') else 'Not held' if s == 'not held' else 'Refused or redirected' if s in ('refused', 'redirected') else 'No answer yet'
    for q in j.get('questions', []):
        for a in (q.get('asked_by') or [])[:6]:
            rows.append({'x': q.get('asked') or a.get('date'), 'y': a.get('tag') or a.get('name') or 'Other', 'c': status(q.get('status', '')), 'l': q.get('question', ''), 'h': (a.get('email') or '').split('?')[0] or '/qa/'})
    return pack('qa', 'Questions asked', 'Date asked', 'Institution asked', 'Answer', rows, ymax=14, cmax=4)

def email(dist):
    f = dist / 'email' / 'view' / 'index.json'
    if not f.exists(): return None
    j = json.loads(f.read_text('utf-8')); rows = []
    for r in j.get('records', []):
        inst = (r.get('institutions') or [{}])[0].get('name') or 'Other'
        d = (r.get('date') or '')[:10]; gid = r.get('gmailMessageId') or ''
        h = '/email/reference/%s/' % gid if gid else ''
        rows.append({'x': d, 'y': inst, 'c': 'Sent' if r.get('direction') == 'sent' else 'Received', 'l': r.get('subject', ''), 'h': h})
    return pack('email', 'Correspondence', 'Date', 'Institution', 'Direction', rows, ymax=14, cmax=2)

GRADE = {1: '1 Record read in full', 2: '2 Record partly read or recited', 3: '3 Later official record', 4: '4 Press', 5: '5 Testimony', 6: '6 Research inference'}
def evidence(dist, area):
    f = ROOT / 'data' / 'evidence-grades.json'
    if not f.exists(): return None
    rows = []
    for e in json.loads(f.read_text('utf-8')).get('evidence', []):
        p = e.get('path') or ''; d = first_date(p.replace('-', ' '))
        if not d:
            pg = dist / p.strip('/') / 'index.html'
            if pg.exists():
                t = pg.read_text('utf-8', 'ignore'); m = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S)
                d = first_date(re.sub('<[^>]+>', ' ', m.group(1)) if m else '') or first_date(re.sub('<[^>]+>', ' ', t[:20000]))
        raw_grade = e.get('evidence_grade')
        if raw_grade is None:
            continue
        g = int(raw_grade)
        slug = p.rstrip('/').split('/')[-1]; nm = re.sub(r'^ev-\d+-', '', slug).replace('-', ' ')
        rows.append({'x': d, 'y': GRADE.get(g, str(g)), 'c': GRADE.get(g, str(g)), 'l': '%s %s' % (e.get('ev', ''), nm), 'h': p})
    out = pack(area, 'Evidence catalogue', 'Date of the record', 'Evidence grade', 'Grade', rows, ymax=6, cmax=6)
    order = [GRADE[k] for k in sorted(GRADE) if GRADE[k] in out['y']['cats']]
    remap = {out['y']['cats'].index(c): i for i, c in enumerate(order)}
    out['y']['cats'] = order; out['c']['cats'] = order
    for p in out['p']: p[1] = remap.get(p[1], p[1]); p[2] = p[1]
    return out

def pages(dist, area, title):
    """Any other area: its own pages by date (first date in the page head/title/h1) and sub-folder."""
    base = dist / area
    if not base.is_dir(): return None
    rows = []
    for i, f in enumerate(sorted(base.rglob('index.html'))):
        if i > 3000: break
        try: t = f.read_text('utf-8', 'ignore')[:60000]
        except Exception: continue
        m = re.search(r'<h1[^>]*>(.*?)</h1>', t, re.S) or re.search(r'<title>(.*?)</title>', t, re.S)
        ttl = re.sub('<[^>]+>', ' ', m.group(1)) if m else f.parent.name
        md = re.search(r'(?:article:modified_time|dateModified|datePublished|article:published_time)["\']?\s*(?:content=|:)\s*["\']([0-9]{4}-[0-9]{2}-[0-9]{2})', t)
        d = (md.group(1) if md else None) or first_date(ttl) or first_date(re.sub('<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', t, flags=re.S))[:6000])
        rel = f.parent.relative_to(base).parts
        rows.append({'x': d, 'y': (rel[0].replace('-', ' ') if rel else 'Home')[:30], 'c': 'Index' if len(rel) <= 1 else 'Page', 'l': ttl, 'h': '/' + area + '/' + ('/'.join(rel) + '/' if rel else '')})
    if sum(1 for r in rows if r['x']) < 5: return None
    return pack(area, title, 'Date', 'Part of the section', 'Page', rows, ymax=12, cmax=2)

# 30 Oct 2026 (owner 14:18 GMT): every header graph plots ONLY its own webapp's database. Dartboard's database is its own
# reply ledger (data/snl-mail.json + data/roadmap.json of the Dartboard app), never the central catalogue or its pages.
# 2025/26 replies: green = positive (records disclosed), amber = less than positive (holding, partial, redirected, fee or
# clarification), red = less still (refused, not held, declined, or no reply by the statutory date). - Sion's Tab agent
RAG_CATS = ['Positive', 'Less than positive', 'Refused, not held or no reply']
RAG_COLS = ['#29a36a', '#e0a100', '#d64545']
RAG_GREEN = {'substantive disclosure', 'subject-access response'}
RAG_RED = {'not held', 'not held (review upheld)', 'refusal', 'declined', 'not found'}
DART_ORIGINS = ('https://dartboard.righteous.workers.dev', 'https://dartboard.bucklerfamily.estate')
def _app_json(dist, app, rel):
    f = dist / app / rel
    if f.exists(): return json.loads(f.read_text('utf-8')), '/%s/%s' % (app, rel)
    import urllib.request
    for o in DART_ORIGINS:
        try:
            with urllib.request.urlopen(urllib.request.Request(o + '/' + rel, headers={'User-Agent': 'cedwyn-build'}), timeout=60) as r:
                return json.loads(r.read().decode('utf-8')), '/%s/%s' % (app, rel)
        except Exception: continue
    return None, None
def rag_class(c):
    c = (c or '').strip().lower()
    return 0 if c in RAG_GREEN else 2 if c in RAG_RED else 1
def dartboard(dist):
    mail, src = _app_json(dist, 'dartboard', 'data/snl-mail.json')
    if not mail: return None
    road, _ = _app_json(dist, 'dartboard', 'data/roadmap.json')
    names = {l.get('id'): l.get('name') for l in (road or {}).get('lanes', [])}
    rows = []
    for lane, msgs in (mail.get('lanes') or {}).items():
        inst = names.get(lane) or lane.replace('-', ' ').title()
        for m in msgs:
            d = (m.get('d') or '')[:10]
            if m.get('out') or d[:4] not in ('2025', '2026'): continue
            k = rag_class(m.get('c')); gid = (m.get('id') or '').replace('gm-', '')
            rows.append({'x': d, 'y': inst, 'k': k, 'l': '%s · %s' % ((m.get('c') or 'reply').capitalize(), inst), 'h': '/email/reference/%s/' % gid if gid else ''})
    for l in (road or {}).get('lanes', []):
        for s in l.get('steps', []):
            d = (s.get('date') or '')[:10]
            if s.get('status') == 'missed' and d[:4] in ('2025', '2026'):
                rows.append({'x': d, 'y': l.get('name') or l.get('id'), 'k': 2, 'l': 'No reply by the statutory date · %s' % (l.get('name') or ''), 'h': ''})
    if not rows: return None
    rows.sort(key=lambda r: r['x'])
    ys = top_cats([r['y'] for r in rows], 14)
    def ix(v): return ys.index(v) if v in ys else len(ys) - 1
    return {'v': 1, 'area': 'dartboard', 'title': 'Disclosure Dartboard — replies 2025/26', 'source': src,
            'x': {'label': 'Date', 'type': 'date'}, 'y': {'label': 'Institution', 'type': 'cat', 'cats': ys},
            'c': {'label': 'Reply', 'cats': RAG_CATS, 'colors': RAG_COLS},
            'p': [[r['x'], ix(r['y']), r['k'], label(r['l'], 90), r['h']] for r in rows[:MAXP]]}

# 30 Oct 2026 (ADR-002 WP10): an app that publishes its own database (<app>/_db/view.json, a plain file) is plotted from that
# file and nothing else - never the central catalogue, never its page list. Kissed Frogs: one point per screened record (date of
# the record, the screening outcome). E-book shelf: one point per release of each book (first edition, current edition,
# supplement) from the shop's own view (written by ebook_editions.py from data/ebooks.json). - Sion's Tab agent
VIEW_APPS = ('kissed-frogs', 'ebooks', 'parcels')
def _view(dist, app):
    f = dist / app / '_db' / 'view.json'
    if not f.exists(): return None
    try: return json.loads(f.read_text('utf-8'))
    except Exception: return None
def kissed_frogs(dist):
    v = _view(dist, 'kissed-frogs')
    if not v: return None
    rows = []
    for fr in v.get('frogs') or []:
        dt = fr.get('date') or {}; shown = '%s %s' % (dt.get('display') or '', fr.get('title') or '')
        x = str(dt.get('sort') or '')[:10]
        if not x or x[:4] not in shown: x = first_date(str(dt.get('display') or '')) or first_date(fr.get('title') or '')   # plot only a date the record shows
        if not x or str(x)[:4] in ('1547', '1552'): continue
        x = str(x)[:10]
        sc = fr.get('scope') or {}
        rows.append({'x': x, 'y': sc.get('label') or fr.get('status') or 'Other', 'c': 'Screened record',
                     'l': '%s %s' % (fr.get('id') or '', fr.get('title') or ''), 'h': '/kissed-frogs/%s/' % fr['slug'] if fr.get('slug') else '/kissed-frogs/'})
    for rt in v.get('retained') or []:
        x = first_date(rt.get('title') or '')
        if x: rows.append({'x': x, 'y': (rt.get('scope') or {}).get('label') or 'In scope', 'c': 'Retained in scope', 'l': '%s %s' % (rt.get('id') or '', rt.get('title') or ''), 'h': '/kissed-frogs/'})
    if not rows: return None
    j = pack('kissed-frogs', 'Kissed Frogs: records screened', 'Date of the record', 'Screening outcome', 'Register', rows, ymax=12, cmax=2)
    j['source'] = '/kissed-frogs/_db/view.json'
    return j
def ebooks(dist):
    v = _view(dist, 'ebooks')
    if not v: return None
    rows = []
    for r in v.get('releases') or []:
        if r.get('date'): rows.append({'x': r['date'][:10], 'y': r.get('book') or 'Other', 'c': r.get('kind') or 'Edition', 'l': r.get('label') or '', 'h': r.get('page') or '/ebooks/'})
    if not rows: return None
    j = pack('ebooks', 'E-book shelf: releases', 'Release date', 'Book', 'Release', rows, ymax=14, cmax=4)
    j['source'] = '/ebooks/_db/view.json'
    return j

def parcels(dist):
    # Parcels page (asked 19:16 GMT 30 Oct 2026): its header graph plots the page's own database, /parcels/_db/view.json -
    # the instruments relied on by the corporations and the registrations of the parcels in their names, one row per parcel. - Sion's Tab agent
    v = _view(dist, 'parcels')
    if not v: return None
    keys = list((v.get('parcels') or {}).keys()); cats = [v['parcels'][k] for k in keys]; kinds = v.get('kinds') or ['Item']
    p = []
    for it in sorted(v.get('items') or [], key=lambda r: str(r.get('x') or '')):
        if not it.get('x') or it.get('parcel') not in keys: continue
        p.append([str(it['x']), keys.index(it['parcel']), int(it.get('kind') or 0) % len(kinds), label(it.get('short') or it.get('inst') or '', 90), ('#' + it['id']) if it.get('id') else '/parcels/'])
    if not p: return None
    return {'v': 1, 'area': 'parcels', 'title': v.get('title') or 'The parcels', 'x': {'label': 'Date', 'type': 'date'},
            'y': {'label': 'Parcel', 'type': 'cat', 'cats': cats}, 'c': {'label': 'Kind', 'cats': kinds, 'colors': v.get('colors') or ['#f2c94c', '#ff7a59', '#6aa8ff']},
            'p': p, 'source': '/parcels/_db/view.json'}

# Build check (owner 14:18 GMT 30 Oct): a graph may only name its own webapp's data as its source.
SHARED_OK = {'research': 'data/evidence-grades.json', 'docs': 'data/evidence-grades.json'}   # evidence apps: the evidence register is their own db until WP2
def own_source(area, j, dist=None):
    s = j.get('source') or ''
    if dist is not None and (pathlib.Path(dist) / area / '_db' / 'view.json').exists():   # an app with its own db must be plotted from it (WP10)
        return s == '/%s/_db/view.json' % area
    return s.startswith('/%s/' % area) or s == '/%s pages' % area or SHARED_OK.get(area) == s

def run(dist):
    dist = pathlib.Path(dist); out = dist / '_cedwyn' / 'graph'; out.mkdir(parents=True, exist_ok=True)
    areas = []
    try: areas = json.loads((dist / 'areas.json').read_text('utf-8')).get('areas', [])
    except Exception: pass
    done = {}; special = {'dartboard': lambda: dartboard(dist), 'qa': lambda: qa(dist), 'email': lambda: email(dist), 'research': lambda: evidence(dist, 'research'), 'docs': lambda: evidence(dist, 'docs'),
               'kissed-frogs': lambda: kissed_frogs(dist), 'ebooks': lambda: ebooks(dist), 'parcels': lambda: parcels(dist)}
    for k, fn in special.items():
        try: j = fn()
        except Exception as e: j = None; print('graph_data', k, 'failed', e)
        if j and j['p']: done[k] = j
    for a in areas:
        aid = a.get('id')
        if not aid or aid in done or aid in ('blog',) or aid in VIEW_APPS: continue   # a view-backed app never falls back to its page list
        try: j = pages(dist, aid, a.get('title') or aid)
        except Exception as e: j = None; print('graph_data', aid, 'failed', e)
        if j: done[aid] = j
    SRC = {'qa': '/qa/questions.json', 'email': '/email/view/index.json', 'research': 'data/evidence-grades.json', 'docs': 'data/evidence-grades.json'}
    for k, j in done.items(): j.setdefault('source', SRC.get(k) or '/%s pages' % k)
    bad = sorted(k for k, j in done.items() if not own_source(k, j, dist))
    for k in bad: print('::warning::graph_data: the %s graph plots %s, not its own webapp database' % (k, done[k].get('source')))
    for k, j in done.items(): (out / (k + '.json')).write_text(json.dumps(j, ensure_ascii=False, separators=(',', ':')), 'utf-8')
    rep = {k: {'points': len(j['p']), 'source': j.get('source'), 'own_db': k not in bad} for k, j in done.items()}
    try: (dist / '_cedwyn' / 'reports').mkdir(parents=True, exist_ok=True); (dist / '_cedwyn' / 'reports' / 'graph_data.json').write_text(json.dumps(rep, indent=1))
    except Exception: pass
    print('graph_data 1.2.0:', rep)
    return rep

if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'dist')
