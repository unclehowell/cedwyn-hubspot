#!/usr/bin/env python3
"""rewrite.py - turn dist/<theme>/ copies into one site under one URL.
1. Content-addressed store: binary evidence files (images, PDFs, audio, video, fonts) that occur more than once across
   all themes are kept ONCE at /_blob/<sha16>.<ext>; HTML/CSS references are pointed there (a copy stays in place only
   where page scripts or data files name the file, so script-driven views keep working).
2. Cross-subdomain links (x.bucklerfamily.estate/...) become /<theme>/...; root-absolute paths gain the theme prefix.
3. No outbound links: every external <a>/<area> href and form action goes to /wayback/go/?u=<url> (the archive interface).
4. /_cedwyn/runtime.js is inserted first in <head> (ghf-boot.js stays last). It prefixes script-made paths and guards links.
Writes dist/_rewrite_report.json. - Sion's Tab agent"""
import json, os, re, sys, hashlib, pathlib, posixpath, shutil, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'themes.json'))
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
TIDS = [t['id'] for t in CFG['themes']]
HOST = {}
for t in CFG['themes']:
    for h in t.get('hosts', []):
        if h not in ('bucklerfamily.estate', 'www.bucklerfamily.estate'): HOST[h.lower()] = t['id']
for h, tid in CFG.get('extra_hosts', {}).items():
    if tid: HOST[h] = tid
APEX = sorted(CFG['apex']['paths'].items(), key=lambda kv: -len(kv[0]))
MEDIA = set(CFG['media_hosts'])
RESERVED = ('/_cedwyn/', '/_blob/', '/db/', '/graphql', '/catalogue')
BANNED = re.compile(r'UC2sN1VEs1WeLfBH8VmbvLWw|sionbuckler5713', re.I)
BLOG_FEEDS = '<link rel="alternate" type="application/rss+xml" title="Cedwyn blog (RSS)" href="/blog/rss.xml"><link rel="alternate" type="application/atom+xml" title="Cedwyn blog (Atom)" href="/blog/atom.xml"><link rel="alternate" type="application/feed+json" title="Cedwyn blog (JSON Feed)" href="/blog/feed.json">'
LISTFORM = re.compile(r'list-manage\.com/subscribe', re.I)   # 26 Oct 2026: a Mailchimp sign-up form posts to Cedwyn's own list, with or without JS
BIN = {'.jpg','.jpeg','.png','.gif','.webp','.svg','.avif','.ico','.bmp','.tif','.tiff','.pdf','.mp3','.m4a','.ogg','.wav','.mp4','.webm','.mov','.woff','.woff2','.ttf','.otf','.eot'}
TXT_DATA = {'.js','.mjs','.json','.xml','.txt','.csv','.md','.webmanifest'}
stats = dict(pages=0, css=0, cross=0, prefixed=0, outbound=0, blobbed_refs=0, banned=0, injected=0, listform=0)
D = len(DIST.parts)
import time as _tt; _T0 = _tt.time()

# ---------- 1. dedupe plan
files = [p for p in DIST.rglob('*') if p.is_file() and len(p.parts) > D + 1 and p.parts[D] in TIDS]
by_sha = {}
for p in files:
    if p.suffix.lower() in BIN:
        h = hashlib.sha256(p.read_bytes()).hexdigest(); by_sha.setdefault(h, []).append(p)
named_in_data = {}
NAMERX = re.compile(r'[\w\-.%]+\.(?:jpe?g|png|gif|webp|svg|avif|ico|pdf|mp3|m4a|ogg|wav|mp4|webm|mov|woff2?|ttf|otf|eot)', re.I)
for p in files:
    if p.suffix.lower() in TXT_DATA and p.stat().st_size < 30_000_000:
        try: s = p.read_text('utf-8', 'ignore')
        except Exception: continue
        named_in_data.setdefault('*', set()).update(x.lower() for x in NAMERX.findall(s))
    elif p.suffix.lower() in ('.html', '.htm'):
        try: s = p.read_text('utf-8', 'ignore')
        except Exception: continue
        for sc in re.findall(r'<script\b[^>]*>(.*?)</script>', s, re.S | re.I):
            named_in_data.setdefault('*', set()).update(x.lower() for x in NAMERX.findall(sc))
BLOB = DIST / '_blob'; BLOB.mkdir(exist_ok=True)
moved = {}; saved = 0; kept_for_scripts = 0
for h, ps in by_sha.items():
    if len(ps) < 2: continue
    ext = ps[0].suffix.lower(); name = f'{h[:16]}{ext}'
    dst = BLOB / name
    if not dst.exists(): shutil.copyfile(ps[0], dst)
    for p in ps:
        tid = p.parts[D]
        rel = '/' + '/'.join(p.parts[D:])
        moved[rel] = '/_blob/' + name
        nm = named_in_data.get('*', set())   # any theme's scripts may load any theme's file (e.g. fb loads wayback images)
        if p.name.lower() in nm or urllib.parse.quote(p.name).lower() in nm:
            kept_for_scripts += 1; continue
        saved += p.stat().st_size; p.unlink()
blob_bytes = sum(f.stat().st_size for f in BLOB.iterdir())
json.dump(moved, open(DIST / '_blob_map.json', 'w'))

# ---------- 2. URL rewriting
def theme_url_for(host, path):
    host = host.lower()
    if host in ('bucklerfamily.estate', 'www.bucklerfamily.estate'):
        for pre, tid in APEX:
            if path.startswith(pre) or path + '/' == pre:
                return '/' + tid + '/' + path[len(pre):].lstrip('/')
    if host == 'cedwyn.bucklerfamily.estate': return path or '/'
    tid = HOST.get(host)
    if tid: return '/' + tid + (path if path.startswith('/') else '/' + path)
    return None
def resolve_blob(u, page_rel):
    if u.startswith(('/_blob/', 'data:', 'http', '//', '#', 'mailto:', 'tel:', 'javascript:')): return u
    m = re.match(r'([^?#]*)(.*)$', u, re.S); base, tail = m.group(1), m.group(2)
    if not base: return u
    absp = base if base.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(page_rel), base))
    absp = urllib.parse.unquote(absp)
    b = moved.get(absp)
    if b and not (DIST / absp.lstrip('/')).exists():
        stats['blobbed_refs'] += 1; return b
    return u
def rw(u, tid, link, page_rel):
    if u is None: return u
    s = u.strip()
    if not s or s.startswith(('#', 'data:', 'javascript:', 'mailto:', 'tel:', 'blob:', 'about:', '{', '$')): return u
    if BANNED.search(s): stats['banned'] += 1; return '#'
    if s.startswith('//'): s = 'https:' + s
    m = re.match(r'(?i)https?://([^/?#:]+)(?::\d+)?([^?#]*)(.*)$', s, re.S)
    if m:
        host, path, rest = m.group(1).lower(), m.group(2), m.group(3)
        tu = theme_url_for(host, path or '/')
        if tu is not None:
            stats['cross'] += 1; return resolve_blob(tu + rest, page_rel)
        if host in MEDIA and not link: return u
        # 27 Oct 2026: e-book Buy buttons go straight to checkout, never via /wayback/go/ (Sion 13:01: never the interstitial)
        if link and (host in ('buy.stripe.com', 'checkout.stripe.com', 'gumroad.com') or host.endswith('.gumroad.com')):
            stats['checkout'] = stats.get('checkout', 0) + 1; return u
        if link:
            stats['outbound'] += 1; return '/wayback/go/?u=' + urllib.parse.quote(s, safe='')
        return u
    if re.match(r'(?i)^[a-z][a-z0-9+.-]*:', s): return u if not link else '#'
    if s.startswith('/'):
        if s == '/': stats['prefixed'] += 1; return '/' + tid + '/'
        if s.startswith(RESERVED): return u
        stats['prefixed'] += 1
        return resolve_blob('/' + tid + s, page_rel)
    return resolve_blob(s, page_rel)
ATTR = re.compile(r"""(\s)(href|src|action|poster|data-src|data-href|data-original|srcset|style|content)(\s*=\s*)("[^"]*"|'[^']*'|[^\s"'>]+)""", re.I)
TAG = re.compile(r'''<([a-zA-Z][\w:-]*)(\s(?:[^<>"']|"[^"]*"|'[^']*')*?)?(/?)>''', re.S)
CSSURL = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)
CSSIMP = re.compile(r"""@import\s+(['"])([^'"]+)\1""", re.I)
def rw_css(text, tid, page_rel):
    text = CSSURL.sub(lambda m: 'url(' + m.group(1) + rw(m.group(2), tid, False, page_rel) + m.group(1) + ')', text)
    return CSSIMP.sub(lambda m: '@import ' + m.group(1) + rw(m.group(2), tid, False, page_rel) + m.group(1), text)
def rw_tag(m, tid, page_rel):
    name = m.group(1).lower(); body = m.group(2)
    if not body: return m.group(0)
    mc = []
    def one(a):
        attr = a.group(2).lower(); raw = a.group(4); q = raw[0] if raw[0] in '"\'' else ''; v = raw[1:-1] if q else raw
        if attr == 'content':
            if name == 'meta' and re.search(r'(?i)http-equiv\s*=\s*["\']?refresh', body):
                v2 = re.sub(r'(?i)(url\s*=\s*)(\S+)', lambda k: k.group(1) + rw(k.group(2).strip('\'"'), tid, True, page_rel), v)
                return a.group(1) + a.group(2) + a.group(3) + q + v2 + q
            return a.group(0)
        if attr == 'style': return a.group(1) + a.group(2) + a.group(3) + q + rw_css(v, tid, page_rel) + q
        if attr == 'srcset':
            parts = []
            for c in v.split(','):
                c = c.strip()
                if not c: continue
                bits = c.split(None, 1); parts.append(rw(bits[0], tid, False, page_rel) + (' ' + bits[1] if len(bits) > 1 else ''))
            return a.group(1) + a.group(2) + a.group(3) + q + ', '.join(parts) + q
        if name == 'form' and attr == 'action' and LISTFORM.search(v):
            stats['listform'] += 1; mc.append(1); return a.group(1) + a.group(2) + a.group(3) + '"/api/list/subscribe"'
        link = (name in ('a', 'area') and attr == 'href') or (name == 'form' and attr == 'action')
        if name == 'iframe' and attr == 'src' and BANNED.search(v): stats['banned'] += 1; return a.group(1) + 'src' + a.group(3) + '"about:blank"'
        nv = rw(v, tid, link, page_rel)
        if nv == v: return a.group(0)
        if q == '': q = '"'
        return a.group(1) + a.group(2) + a.group(3) + q + nv.replace(q, '%22' if q == '"' else '%27') + q
    nb = ATTR.sub(one, body)
    if name in ('a', 'area') and '/wayback/go/' in nb:
        nb = re.sub(r"""(?i)\starget\s*=\s*("_blank"|'_blank'|_blank)""", '', nb)
    if mc:   # the list form: same tab (the list answers with its own page when JS is off), marked for the runtime's in-page send
        nb = re.sub(r"""(?i)\starget\s*=\s*("_blank"|'_blank'|_blank)""", '', nb) + ' data-cedwyn-mc="1"'
    return '<' + m.group(1) + nb + m.group(3) + '>'
STYLE = re.compile(r'(<style[^>]*>)(.*?)(</style>)', re.S | re.I)
# 31 Oct 2026 (P-115): a 'This material now lives at <full address>' note (p.ghf-moved-note, the old WordPress wiki's
# moved-page notice) shows a long address in bold that cannot wrap; at 390 px it pushed the page to 409 px wide
# (/wiki/constructive-criticism-counterarguments/). The note may now break anywhere. - Sion's Tab agent
MOVED = re.compile(r'<p\b[^>]*\bghf-moved-note\b[^>]*>', re.I)
def _moved(m):
    t = m.group(0)
    if re.search(r'\sstyle\s*=', t, re.I):
        return t if 'overflow-wrap' in t else re.sub(r'''(\sstyle\s*=\s*["'])''', r'\1overflow-wrap:anywhere;', t, count=1, flags=re.I)
    return t[:-1].rstrip('/').rstrip() + ' style="overflow-wrap:anywhere">'
SCRIPT = re.compile(r'(<script\b[^>]*>)(.*?)(</script>)', re.S | re.I)
def rw_html(html, tid, page_rel):
    keep = []
    def stash(m): keep.append(m.group(2)); return m.group(1) + '\x00%d\x00' % (len(keep) - 1) + m.group(3)
    html = SCRIPT.sub(stash, html)
    html = STYLE.sub(lambda m: m.group(1) + rw_css(m.group(2), tid, page_rel) + m.group(3), html)
    html = TAG.sub(lambda m: rw_tag(m, tid, page_rel), html)
    html = re.sub('\x00(\\d+)\x00', lambda m: keep[int(m.group(1))], html)
    html = MOVED.sub(_moved, html)   # P-115
    inj = '<script src="/_cedwyn/runtime.js?v=13" data-theme="%s"></script>' % tid
    if 'href="/blog/rss.xml"' not in html: inj += BLOG_FEEDS   # 27 Oct 2026: blog feed autodiscovery on every page
    mh = re.search(r'<head\b[^>]*>', html, re.I)
    if mh: html = html[:mh.end()] + inj + html[mh.end():]
    else:
        mh = re.search(r'<html\b[^>]*>', html, re.I)
        html = (html[:mh.end()] + inj + html[mh.end():]) if mh else inj + html
    stats['injected'] += 1
    return html
def do_file(p):
    st0 = dict.fromkeys(stats, 0); stats.clear(); stats.update(st0)
    tid = p.parts[D]; rel = '/' + '/'.join(p.parts[D:]); ext = p.suffix.lower()
    try:
        if ext in ('.html', '.htm'):
            b = p.read_bytes()
            try: s = b.decode('utf-8')
            except UnicodeDecodeError: s = b.decode('latin-1')
            p.write_text(rw_html(s, tid, rel), 'utf-8'); stats['pages'] += 1
        elif ext == '.css':
            s = p.read_text('utf-8', 'ignore'); p.write_text(rw_css(s, tid, rel), 'utf-8'); stats['css'] += 1
    except Exception as e:
        stats['errors'] = stats.get('errors', 0) + 1
    return dict(stats)
import time as _t, multiprocessing as _mp
_t0 = _t.time()
todo = [p for p in DIST.rglob('*') if p.is_file() and len(p.parts) > D + 1 and p.parts[D] in TIDS and p.suffix.lower() in ('.html', '.htm', '.css')]
print('rewrite: files', len(todo), 'dedupe done in', round(_t.time() - _T0), 's', flush=True)
tot = dict.fromkeys(stats, 0); tot['errors'] = 0
with _mp.Pool(4) as pool:
    for d in pool.imap_unordered(do_file, todo, chunksize=64):
        for k, v in d.items(): tot[k] = tot.get(k, 0) + v
stats.clear(); stats.update(tot)
print('rewrite: done in', round(_t.time() - _t0), 's', flush=True)
red = []
for tid in TIDS:
    f = DIST / tid / '_redirects'
    if f.exists():
        for line in f.read_text('utf-8', 'ignore').splitlines():
            b = line.split()
            if len(b) >= 2 and b[0] in ('/*', '/') and b[1].startswith('http'): continue   # 25 Oct 2026: a whole-theme redirect away would take the theme out of the ‹ › loop; its own pages stay
            if len(b) >= 2 and b[0].startswith('/'):
                tgt = b[1] if b[1].startswith('http') else '/' + tid + b[1]
                red.append(' '.join(['/' + tid + b[0], tgt] + b[2:]))
        f.unlink()
    h = DIST / tid / '_headers'
    if h.exists(): h.unlink()
rep = dict(stats, dedupe_files_moved=len(moved), dedupe_bytes_saved=saved, blob_store_bytes=blob_bytes, kept_for_scripts=kept_for_scripts, theme_redirects=len(red))
(DIST / '_theme_redirects.txt').write_text('\n'.join(red[:1500]))
json.dump(rep, open(DIST / '_rewrite_report.json', 'w'), indent=1)
print(json.dumps(rep))
