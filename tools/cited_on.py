#!/usr/bin/env python3
"""cited_on.py - build-time "Cited on" lists for artifact (evidence) pages.  Stdlib only.

Scans every built HTML page in dist, collects the internal <a href> links that point at an artifact page
(/research/evidence/ev-NNNN-*/ or /wiki/evidence/ev-NNNN-*/), and writes into each artifact page a
<section id="cited-on"> listing the pages that link to it, by page title. Real links only: a page appears
in the list only if it carries a plain <a href> to the artifact. Re-running replaces the previous list.
Usage: python3 tools/cited_on.py dist        (27 Oct 2026 - Sion's Tab agent)
"""
import os, re, sys, html, urllib.parse
TARGET = re.compile(r'^/(?:research|wiki)/evidence/(ev-\d{4}[^/]*)/$')
HOSTS = {'cedwyn.bucklerfamily.estate', 'www.cedwyn.bucklerfamily.estate'}
MAPPED = {'research.bucklerfamily.estate': '/research'}   # subdomain links not yet rewritten at this stage
HREF = re.compile(r'<a\b[^>]*?\bhref\s*=\s*("([^"]*)"|\'([^\']*)\')', re.I)
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.I | re.S)
OLD = re.compile(r'\s*<section id="cited-on"[^>]*data-built="cited_on".*?</section><!--/cited-on-->', re.S)
SKIP_SRC = re.compile(r'^/(?:wayback/go/|_cedwyn/|api/)')
MAX = 80

def page_path(dist, f):
    rel = '/' + os.path.relpath(f, dist).replace(os.sep, '/')
    return rel[:-10] if rel.endswith('/index.html') else rel

def norm(href, base):
    href = html.unescape(href.strip())
    if not href or href.startswith(('#', 'mailto:', 'tel:', 'javascript:', 'data:')): return None
    u = urllib.parse.urlsplit(urllib.parse.urljoin('https://cedwyn.bucklerfamily.estate' + base, href))
    host = u.netloc.lower()
    if host and host not in HOSTS and host not in MAPPED: return None
    p = MAPPED.get(host, '') + urllib.parse.unquote(u.path or '/')
    if p.endswith('/index.html'): p = p[:-10]
    if not p.endswith('/') and '.' not in p.rsplit('/', 1)[-1]: p += '/'
    return p

def title_of(txt, path):
    m = TITLE.search(txt)
    t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', m.group(1)))).strip() if m else ''
    for tail in (' — Great House Farm Wiki — Research Mirror', ' · Cedwyn', ' — Cedwyn'):
        if t.endswith(tail): t = t[:-len(tail)]
    return t or path

def main(dist):
    files = []
    for root, _, fs in os.walk(dist):
        for fn in fs:
            if fn.endswith('.html'): files.append(os.path.join(root, fn))
    targets, cites, titles = {}, {}, {}
    for f in files:
        p = page_path(dist, f)
        if TARGET.match(p): targets[p] = f
    for f in files:
        p = page_path(dist, f)
        if SKIP_SRC.match(p): continue
        try: txt = open(f, encoding='utf-8', errors='replace').read()
        except OSError: continue
        txt = OLD.sub('', txt)
        hit = False
        for m in HREF.finditer(txt):
            t = norm(m.group(2) if m.group(2) is not None else m.group(3), p)
            if t and t != p and t in targets:
                cites.setdefault(t, set()).add(p); hit = True
        if hit: titles[p] = title_of(txt, p)
    n = 0
    for p, f in targets.items():
        txt = open(f, encoding='utf-8', errors='replace').read()
        txt = OLD.sub('', txt)
        srcs = sorted(cites.get(p, ()), key=lambda s: (not s.startswith('/research/evidence/'), titles.get(s, s).lower()))
        if srcs:
            items = ''.join('<li><a href="%s">%s</a></li>' % (html.escape(s, True), html.escape(titles.get(s, s))) for s in srcs[:MAX])
            more = '<p class="cited-on-more">and %d more pages.</p>' % (len(srcs) - MAX) if len(srcs) > MAX else ''
            body = '<ul class="cited-on-list">%s</ul>%s' % (items, more)
        else:
            body = '<p class="cited-on-none">No page on this site links to this record yet.</p>'
        sec = ('<section id="cited-on" class="cited-on" data-built="cited_on"><h2>Cited on</h2>'
               '<p class="cited-on-count">%d page%s link%s here.</p>%s</section><!--/cited-on-->'
               % (len(srcs), '' if len(srcs) == 1 else 's', 's' if len(srcs) == 1 else '', body))
        for anchor in ('</article>', '</main>', '</body>'):
            i = txt.rfind(anchor)
            if i != -1:
                txt = txt[:i] + sec + txt[i:]; break
        open(f, 'w', encoding='utf-8').write(txt); n += 1
    print('cited_on: %d artifact pages, %d with citing pages, %d links' % (n, len(cites), sum(len(v) for v in cites.values())))

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'dist')
