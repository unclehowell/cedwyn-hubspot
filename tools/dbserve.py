#!/usr/bin/env python3
"""dbserve.py - stage 3: the catalogue database becomes the one source of every theme's data and evidence files.
Runs last in the build, after the self-contained test passes. For each theme path the database holds (db/blobmap.json):
  - if the file on disk still has the exact bytes stored in the database (sha256), the file is removed from the deploy:
    the service worker (/cedwyn-sw.js) and the page fallback (runtime.js + dbfs.js) serve it from the database chunks;
  - if a later build step changed the file, the path is taken out of the map and the file serves as before;
  - files that browsers fetch outside a service worker stay as files too (favicons and touch icons, web manifests and the
    icons they list, <link>/<meta> images, sitemaps and feeds, images named in CSS, files named by pages that do not load
    the runtime); the database still serves them to the worker.
Writes _cedwyn/reports/dbserve.json. - Sion's Tab agent"""
import json, sys, re, hashlib, pathlib, posixpath, urllib.parse, collections
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
DBX = re.compile(r'\.(json|csv|xml|geojson|png|jpe?g|gif|webp|svg|avif|ico|bmp|tiff?|pdf|docx?|mp3|m4a|ogg|wav)$', re.I)
KEEPNAME = re.compile(r'(^|/)(favicon[^/]*|apple-touch-icon[^/]*|android-chrome[^/]*|mstile[^/]*|safari-pinned-tab[^/]*|[^/]*\.ico|sitemap[^/]*\.xml|'
                      r'[^/]*(feed|rss|atom)[^/]*\.xml|browserconfig\.xml|manifest\.json|opensearch[^/]*\.xml)$', re.I)
KEEPPREFIX = ('/wayback/snap/',)
APPDB = re.compile(r'/_db/view\.json$|/_ui/[^/]+\.a2ui\.json$|^/?projects/data/(programme|programme-office|data-architecture)\.json$|^/?(?:[^/]+/)?qa/questions\.json$|^/?(?:[^/]+/)?parcels/poster\.jpg$')   # + 30 Oct 2026 21:15Z: the Q&A app's own question list (/qa/questions.json, read by the Q&A page, the header graph, check_qa_built.py in CI and check_qa_served.py after deploy) stays a plain file; dbserve had dropped it, so build 41119909136 failed the Q&A completeness guard   # + 30 Oct 2026: the Projects programme data a page or an agent fetches by plain URL (/projects/data/programme.json 404'd outside the service worker)   # 30 Oct 2026 (ADR-002): each webapp's own database and its A2UI surfaces stay plain files so agents, webmcp and header graphs read them without the service worker - Sion's Tab agent   # data files a page fetches by an address built at run time - Sion's Tab agent
KIND = {'json': 'data', 'csv': 'data', 'xml': 'data', 'geojson': 'data', 'pdf': 'document', 'doc': 'document', 'docx': 'document',
        'mp3': 'audio', 'm4a': 'audio', 'ogg': 'audio', 'wav': 'audio'}
def kind(p): return KIND.get(p.rsplit('.', 1)[-1].lower(), 'image')
LINKTAG = re.compile(r'<(?:link|meta)\b[^>]*>', re.I | re.S)
ATTRV = re.compile(r"""(?:href|content|src)\s*=\s*["']([^"']+)["']""", re.I)
CSSURL = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", re.I)
SCRIPTS = re.compile(r'<script\b.*?</script>', re.I | re.S)
MARKUP = re.compile(r'<(?:img|source|video|audio|embed|object|iframe|input|image|use|track)\b[^>]*>', re.I | re.S)
MATTR = re.compile(r"""\s(?:src|data|poster|srcset|href|xlink:href)\s*=\s*["']([^"']+)["']""", re.I)
FETCHLIT = re.compile(r"""fetch\(\s*["']([^"'?#\s:]+\.(?:json|csv|xml|geojson))(?:\?[^"']*)?["']""")
QSTR = re.compile(r"""["'`]([^"'`\s<>]{1,300})["'`]""")
def resolve(base_rel, u):
    u = u.strip().split('#')[0].split('?')[0]
    if not u or u.startswith(('data:', 'blob:', 'javascript:', 'mailto:')): return None
    if re.match(r'(?i)^(https?:)?//', u):
        sp = urllib.parse.urlsplit(u if not u.startswith('//') else 'https:' + u)
        if (sp.hostname or '') != 'cedwyn.bucklerfamily.estate': return None
        u = sp.path
    p = u if u.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(base_rel), u))
    return urllib.parse.unquote(p)
def sha16(f):
    h = hashlib.sha256()
    with open(f, 'rb') as fh:
        for c in iter(lambda: fh.read(1 << 20), b''): h.update(c)
    return h.hexdigest()[:16]
def main():
    bmf = DIST / 'db' / 'blobmap.json'
    if not bmf.exists(): print('dbserve: no blobmap, nothing to do'); return 0
    bm = json.load(open(bmf)); paths = bm['paths']; blobs = bm['blobs']
    keep = {}
    for p in DIST.rglob('*'):
        if not p.is_file(): continue
        rel = '/' + p.relative_to(DIST).as_posix(); ext = p.suffix.lower()
        if rel.startswith(('/db/', '/_cedwyn/reports/')): continue
        if ext in ('.html', '.htm'):
            s = p.read_text('utf-8', 'ignore')
            for t in LINKTAG.findall(s):
                for v in ATTRV.findall(t):
                    r = resolve(rel, v)
                    if r: keep.setdefault(r, 'link/meta tag')
            for v in CSSURL.findall(s):
                r = resolve(rel, v)
                if r: keep.setdefault(r, 'css url()')
            # files named in the page markup itself (img/source/video/audio/embed/object/iframe/input): the browser's preload
            # scanner asks for them before any script runs, so on a first visit they must exist as files
            for t in MARKUP.findall(SCRIPTS.sub(' ', s)):
                for v in MATTR.findall(t):
                    for part in v.split(','):
                        r = resolve(rel, part.strip().split(' ')[0])
                        if r: keep.setdefault(r, 'named in page markup')
            for v in FETCHLIT.findall(s):   # data files the page's own scripts fetch (first visit: no service worker yet)
                r = resolve(rel, v)
                if r: keep.setdefault(r, 'fetched by script')
            if '/_cedwyn/runtime.js' not in s:   # a page that does not load the runtime: everything it names stays a file
                for v in QSTR.findall(s):
                    if DBX.search(v.split('?')[0].split('#')[0]):
                        r = resolve(rel, v)
                        if r: keep.setdefault(r, 'page without runtime')
        elif ext == '.css':
            s = p.read_text('utf-8', 'ignore')
            for v in CSSURL.findall(s):
                r = resolve(rel, v)
                if r: keep.setdefault(r, 'css url()')
        elif ext in ('.js', '.mjs'):
            # 26 Oct 2026: a data file a script fetches by its absolute path (the Post Office viewer's
            # fetch('/email/view/index.json')) must exist as a file: on a first visit no service worker is running yet,
            # so a removed file answered 404 and the viewer could not open any mail. - Sion's Tab agent
            s = p.read_text('utf-8', 'ignore')
            for v in FETCHLIT.findall(s):
                r = resolve(rel, v)
                if r: keep.setdefault(r, 'fetched by script')
        elif ext == '.webmanifest' or p.name == 'manifest.json':
            try:
                for ic in (json.load(open(p)).get('icons') or []):
                    r = resolve(rel, ic.get('src', ''))
                    if r: keep.setdefault(r, 'web manifest icon')
            except Exception: pass
    rep = collections.Counter(); kept_why = collections.Counter(); changed = []; dropped_bytes = collections.Counter(); kept_examples = []
    for path in sorted(paths):
        f = DIST / path.lstrip('/')
        if not f.is_file(): rep['indexed_no_file'] += 1; continue   # a copy the content store already folded into /_blob/
        if sha16(f) != blobs[paths[path]][5]:
            del paths[path]; changed.append(path); continue
        # 27 Oct 2026 (P-008): the Wayback snapshot page builds its bucket address at run time ('/wayback/snap/b/'+n+'.json'),
        # which FETCHLIT cannot see, so every bucket was dropped and /wayback/go/ found no captured copy (404). Keep them as files.
        why = keep.get(path) or ('fetched by browsers outside a service worker' if KEEPNAME.search(path) else None) \
            or ('fetched by script (built path)' if path.startswith(KEEPPREFIX) else None) \
            or ('webapp database / A2UI surface (read without a service worker)' if APPDB.search(path) else None) \
            or ('download file (.csv opened by a plain link, outside the service worker)' if path.lower().endswith('.csv') else None)
        # 31 Oct 2026 (P-132): a CSV is a download a reader opens by a plain <a href> link (the book register
        # /research/book-research-findings.csv and /research/books/findings.csv). An <a> link is not markup the preload
        # scanner fetches, so dbserve dropped every CSV and a first visit or a direct link answered 404. Keep CSVs as files. - Sion's Tab agent
        if why:
            kept_why[why] += 1; rep['kept_' + kind(path)] += 1
            if len(kept_examples) < 20: kept_examples.append([path, why])
            continue
        n = f.stat().st_size; f.unlink(); rep['dropped_' + kind(path)] += 1; dropped_bytes[kind(path)] += n
    for d in sorted((p for p in DIST.rglob('*') if p.is_dir()), key=lambda x: -len(x.parts)):
        try:
            if not any(d.iterdir()): d.rmdir()
        except Exception: pass
    json.dump(bm, open(bmf, 'w'), separators=(',', ':'))
    o = {'db_version': bm['v'], 'paths_served_from_db': len(paths), 'blobs': len(blobs),
         'files_dropped': {k[8:]: v for k, v in rep.items() if k.startswith('dropped_')},
         'bytes_dropped': dict(dropped_bytes), 'bytes_dropped_total': sum(dropped_bytes.values()),
         'files_kept_as_well': {k[5:]: v for k, v in rep.items() if k.startswith('kept_')}, 'kept_why': dict(kept_why), 'kept_examples': kept_examples,
         'changed_after_db_build_served_as_files': len(changed), 'changed_examples': changed[:20], 'indexed_without_file': rep['indexed_no_file']}
    r = DIST / '_cedwyn' / 'reports'; r.mkdir(parents=True, exist_ok=True)
    json.dump(o, open(r / 'dbserve.json', 'w'), indent=1)
    print('dbserve', json.dumps({k: o[k] for k in ('paths_served_from_db', 'files_dropped', 'bytes_dropped_total', 'files_kept_as_well', 'changed_after_db_build_served_as_files')}))
    return 0
if __name__ == '__main__': sys.exit(main())
