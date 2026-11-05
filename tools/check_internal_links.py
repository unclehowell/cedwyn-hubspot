#!/usr/bin/env python3
"""Audit internal destinations in the built Cedwyn site. Report-only by default.

Checks HTML navigation/resource URLs, srcset, inline styles and CSS url()/@import
against built files, the DB-backed file map and Cloudflare Pages redirects.
External URLs and form/API actions are deliberately not treated as static pages.
Use --strict only after current-site exceptions have been reviewed. — Sion's Tab agent
"""
from __future__ import annotations
import collections, html, html.parser, json, pathlib, posixpath, re, sys, urllib.parse

DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'dist').resolve()
STRICT = '--strict' in sys.argv
HOSTS = {'cedwyn.bucklerfamily.estate', 'www.cedwyn.bucklerfamily.estate'}
URL_ATTRS = {'href', 'src', 'poster', 'data', 'cite', 'xlink:href',
             'data-src', 'data-href', 'data-original', 'data-url', 'data-asset'}
CSS_URL = re.compile(r'''url\(\s*(?P<q>["']?)(?P<u>[^"')]+)(?P=q)\s*\)''', re.I)
CSS_IMPORT = re.compile(r'''@import\s+(?:url\(\s*)?["'](?P<u>[^"']+)["']\s*\)?''', re.I)
REFRESH = re.compile(r'''(?i)url\s*=\s*['"]?([^;'"]+)''')

def public_url(p: pathlib.Path) -> str:
    rel = p.relative_to(DIST).as_posix()
    if rel == 'index.html': return '/'
    if rel.endswith('/index.html'): return '/' + rel[:-10]
    return '/' + rel

def norm_path(p: str) -> str:
    try: p = urllib.parse.unquote(p)
    except Exception: pass
    if not p: p = '/'
    if not p.startswith('/'): p = '/' + p
    trail = p.endswith('/')
    p = posixpath.normpath(p)
    if not p.startswith('/'): p = '/' + p
    if trail and p != '/': p += '/'
    return p

class Parser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs if k}
        if a.get('id'): self.ids.add(a['id'])
        if tag.lower() == 'a' and a.get('name'): self.ids.add(a['name'])
        for name, val in attrs:
            if not name or val is None: continue
            name = name.lower()
            if name in URL_ATTRS:
                kind = 'nav' if name == 'href' and tag.lower() in ('a','area') else 'resource'
                if name == 'href' and tag.lower() == 'link':
                    rel = a.get('rel','').lower()
                    kind = 'resource' if any(x in rel for x in ('stylesheet','icon','preload','modulepreload','manifest','alternate')) else 'nav'
                self.refs.append((html.unescape(val.strip()), kind, tag.lower() + '[' + name + ']'))
            elif name in ('action', 'formaction'):
                self.refs.append((html.unescape(val.strip()), 'endpoint', tag.lower() + '[' + name + ']'))
            elif name == 'srcset':
                for item in val.split(','):
                    bits = item.strip().split()
                    if bits: self.refs.append((html.unescape(bits[0]), 'resource', tag.lower() + '[srcset]'))
            elif name == 'style':
                self._css(val, 'resource', 'inline-style')
            elif name == 'content' and tag.lower() == 'meta' and 'refresh' in a.get('http-equiv','').lower():
                m = REFRESH.search(val)
                if m: self.refs.append((html.unescape(m.group(1).strip()), 'nav', 'meta[refresh]'))
    def handle_startendtag(self, tag, attrs): self.handle_starttag(tag, attrs)
    def _css(self, s, kind, source):
        for m in CSS_URL.finditer(s):
            u = m.group('u').strip()
            if u: self.refs.append((html.unescape(u), kind, source + '[url()]'))
        for m in CSS_IMPORT.finditer(s):
            self.refs.append((html.unescape(m.group('u').strip()), kind, source + '[@import]'))

# Static binary/data assets held in the catalogue database count as present.
db_paths = set()
bm = DIST / 'db' / 'blobmap.json'
if bm.is_file():
    try:
        obj = json.loads(bm.read_text('utf-8'))
        db_paths = {norm_path(p) for p in obj.get('paths', {})}
    except Exception as e:
        print('warning: could not read db/blobmap.json:', str(e)[:200], file=sys.stderr)

rules = []
exact = {}
wild = collections.defaultdict(list)
redirect_file = DIST / '_redirects'
if redirect_file.is_file():
    for line in redirect_file.read_text('utf-8', errors='ignore').splitlines():
        s = line.strip()
        if not s or s.startswith('#'): continue
        bits = s.split()
        if len(bits) < 2: continue
        src, dst = bits[0], bits[1]
        status = 302
        if len(bits) >= 3 and bits[2].isdigit(): status = int(bits[2])
        rec = (src, dst, status)
        if '*' not in src:
            exact[src] = rec
            if src != '/': exact.setdefault(src.rstrip('/'), rec)
        else:
            first = src.split('/')[1] if len(src.split('/')) > 1 else ''
            wild[first].append(rec)
for key in wild: wild[key].sort(key=lambda r: len(r[0]), reverse=True)

def apply_redirect(path):
    if path in exact: return exact[path]
    if path.rstrip('/') in exact: return exact[path.rstrip('/')]
    parts = path.strip('/').split('/')
    keys = [parts[0] if parts and parts[0] else '']
    keys.append('')
    for key in keys:
        for src, dst, status in wild.get(key, []):
            rx = '^' + re.escape(src).replace(r'\*', '(.*)') + '$'
            m = re.match(rx, path)
            if m:
                splat = m.group(1) if m.lastindex else ''
                return src, dst.replace(':splat', splat), status
    return None

resolve_cache = {}
id_cache = {}
def file_for_url(path):
    p = norm_path(path)
    if p in resolve_cache: return resolve_cache[p]
    seen = set()
    original = p
    for _ in range(10):
        if p in seen: break
        seen.add(p)
        rule = apply_redirect(p)
        if rule:
            src, dst, status = rule
            u = urllib.parse.urlsplit(dst)
            if u.scheme in ('http','https') and (u.hostname or '').lower() not in HOSTS:
                resolve_cache[original] = ('redirect-external', None); return resolve_cache[original]
            p = norm_path(u.path or '/')
            # A 200 is an internal rewrite; 3xx rules redirect to the same final local destination.
            continue
        rel = p.lstrip('/')
        exact_path = DIST / rel
        candidates = [exact_path]
        if p.endswith('/'):
            candidates.insert(0, DIST / rel / 'index.html')
        else:
            if not pathlib.PurePosixPath(p).suffix:
                candidates += [DIST / (rel + '/index.html'), DIST / (rel + '.html'), DIST / (rel + '.htm')]
        for c in candidates:
            try:
                if c.is_file() and c.resolve().is_relative_to(DIST):
                    resolve_cache[original] = ('file', c.resolve()); return resolve_cache[original]
            except (OSError, ValueError): pass
        if p in db_paths:
            resolve_cache[original] = ('database', None); return resolve_cache[original]
        break
    resolve_cache[original] = ('missing', None)
    return resolve_cache[original]

def url_target(raw, page_url):
    raw = html.unescape((raw or '').strip())
    # A fragment-only link is a real intra-page navigation target; resolve it against the current page
    # so missing IDs are reported instead of silently skipped.
    if not raw or raw == '#' or raw.startswith(('data:','javascript:','mailto:','tel:','sms:','blob:','about:')):
        return None
    if any(x in raw for x in ('{{','}}','{path}','<escape>')) or ('$' + '{') in raw:
        return None
    try: full = urllib.parse.urljoin('https://' + 'cedwyn.bucklerfamily.estate' + page_url, raw)
    except Exception: return None
    u = urllib.parse.urlsplit(full)
    if u.scheme not in ('http','https'): return None
    if (u.hostname or '').lower() not in HOSTS: return None
    return norm_path(u.path or '/'), u.fragment

ref_counts = collections.Counter()
bad = collections.Counter()
bad_examples = collections.defaultdict(list)
frag_bad = collections.Counter()
frag_examples = collections.defaultdict(list)
endpoint_refs = collections.Counter()
pages = 0
for src in DIST.rglob('*'):
    if not src.is_file() or src.suffix.lower() not in ('.html','.htm','.css'): continue
    relp = src.relative_to(DIST)
    if relp.parts and relp.parts[0] in ('db','_blob'): continue
    if src.suffix.lower() in ('.html','.htm'):
        raw = src.read_text('utf-8', errors='ignore')
        page_url = public_url(src)
        bm0 = re.search(r'''(?is)<base\b[^>]*\bhref\s*=\s*["']([^"']+)["']''', raw)
        if bm0:
            try:
                bx = urllib.parse.urlsplit(urllib.parse.urljoin('https://cedwyn.bucklerfamily.estate' + page_url, bm0.group(1)))
                if (bx.hostname or '').lower() in HOSTS: page_url = bx.path or '/'
            except Exception: pass
        p = Parser(); p.feed(raw); refs = p.refs
        id_cache[norm_path(page_url)] = p.ids
        for block in re.findall(r'(?is)<style\b[^>]*>(.*?)</style>', raw):
            p._css(block, 'resource', 'style-block')
        refs = p.refs
        pages += 1
    else:
        raw = src.read_text('utf-8', errors='ignore')
        page_url = public_url(src)
        p = Parser(); p._css(raw, 'resource', 'css')
        refs = p.refs
    for raw_url, kind, attr in refs:
        if kind == 'endpoint':
            endpoint_refs[attr] += 1
            continue
        got = url_target(raw_url, page_url)
        if got is None: continue
        path, frag = got
        ref_counts[kind] += 1
        outcome, target = file_for_url(path)
        if outcome == 'missing':
            key = (kind, path)
            bad[key] += 1
            if len(bad_examples[key]) < 4: bad_examples[key].append({'from': page_url, 'attribute': attr, 'url': raw_url[:240]})
        elif frag and outcome == 'file' and target and target.suffix.lower() in ('.html','.htm'):
            try:
                target_url = public_url(target)
                ids = id_cache.get(norm_path(target_url))
                if ids is None:
                    tp = Parser(); tp.feed(target.read_text('utf-8', errors='ignore')); ids = tp.ids
                    id_cache[norm_path(target_url)] = ids
                if frag not in ids:
                    k = (path, frag)
                    frag_bad[k] += 1
                    if len(frag_examples[k]) < 3: frag_examples[k].append({'from': page_url, 'url': raw_url[:240]})
            except Exception: pass

def items(counter, examples, cap=150):
    out=[]
    for (kind,path),n in counter.most_common(cap):
        out.append({'kind':kind,'path':path,'references':n,'examples':examples.get((kind,path),[])})
    return out
report = {
  'audit':'Cedwyn internal HTML/CSS links and fragments',
  'pages_scanned':pages,
  'references_checked':dict(ref_counts),
  'database_backed_paths':len(db_paths),
  'unique_missing_destinations':len(bad),
  'missing_references':sum(bad.values()),
  'missing_navigation_references':sum(n for (k,_),n in bad.items() if k=='nav'),
  'missing_resource_references':sum(n for (k,_),n in bad.items() if k=='resource'),
  'unique_broken_fragments':len(frag_bad),
  'broken_fragment_references':sum(frag_bad.values()),
  'form_or_endpoint_actions_not_checked':dict(endpoint_refs),
  'top_missing_destinations':items(bad,bad_examples),
  'top_broken_fragments':[{'path':p,'fragment':f,'references':n,'examples':frag_examples[(p,f)]} for (p,f),n in frag_bad.most_common(150)],
}
report['pass'] = not bad and not frag_bad
out = DIST / '_internal_links_report.json'
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('pages_scanned','references_checked','unique_missing_destinations','missing_references','missing_navigation_references','missing_resource_references','unique_broken_fragments','broken_fragment_references','pass')},ensure_ascii=False))
if STRICT and not report['pass']: sys.exit(1)
