#!/usr/bin/env python3
"""readmore_chunks.py 1.0.0 - progressive "Read more" for long Cedwyn pages (asked for 01:27 GMT 30 Oct 2026: pages load
faster: long list pages ship their first screens in the HTML and load the rest from the site's own data as the reader scrolls).
Runs near the end of site.py (wrapped in try). For each built page over MIN_BYTES in a list-like area, the blocks of its
<main> after the first KEEP_BYTES of HTML move into <page>/_more/<n>.json ({"html": ...}, about CHUNK_BYTES each) and a
marker <div data-cw-more="<page>/_more/" data-cw-more-n="N" hidden> takes their place; cw-graph.js fetches the next chunk
as the reader nears the end, and all of them at once for a #link, a search box, print or the card levels. Interactive apps and machine-facing
areas are never cut. - Cedwyn editors"""
import json, os, re, sys, pathlib
from html.parser import HTMLParser

AREAS = ('research', 'wiki', 'docs', 'review', 'wdtk', 'authorities', 'records', 'watchtower', 'projects')
SKIP = re.compile(r'^(?:wales/|argentina/)?(?:academy|wayback|dartboard|documentary|movie|story|legal|terms|privacy|db|_cedwyn|ebooks|shop)(?:/|$)')
MIN_BYTES, KEEP_BYTES, CHUNK_BYTES, MAX_PAGES = 150_000, 30_000, 60_000, 400
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

class Kids(HTMLParser):
    """Offsets (within text[a:b]) of the top-level elements of an HTML fragment."""
    def __init__(self, text, a, b):
        super().__init__(convert_charrefs=False); self.t = text; self.a = a; self.lines = [0]
        for m in re.finditer('\n', text[a:b]): self.lines.append(m.end())
        self.depth = 0; self.kids = []; self.cur = None; self.tags = []
        self.feed(text[a:b]); self.close()
    def off(self): l, c = self.getpos(); return self.a + self.lines[l - 1] + c
    def handle_starttag(self, tag, at):
        if tag in VOID:
            if self.depth == 0: o = self.off(); self.kids.append([o, o + len(self.get_starttag_text() or ''), tag])
            return
        if self.depth == 0: self.cur = [self.off(), None, tag]
        self.depth += 1
    def handle_startendtag(self, tag, at):
        if self.depth == 0: o = self.off(); self.kids.append([o, o + len(self.get_starttag_text() or ''), tag])
    def handle_endtag(self, tag):
        if tag in VOID or self.depth == 0: return
        self.depth -= 1
        if self.depth == 0 and self.cur:
            o = self.off(); self.cur[1] = self.t.find('>', o) + 1; self.kids.append(self.cur); self.cur = None

def container(t):
    """The list-like block to cut: <main>'s inner HTML, descending while one child holds most of it."""
    m = re.search(r'<main\b[^>]*>', t)
    if not m: return None
    a = m.end(); b = t.rfind('</main>')
    if b < a: return None
    for _ in range(5):
        kids = [k for k in Kids(t, a, b).kids if k[1]]
        if not kids: return None
        big = max(kids, key=lambda k: k[1] - k[0])
        if len(kids) >= 8 and (big[1] - big[0]) < 0.6 * (b - a): return kids
        if (big[1] - big[0]) < 0.6 * (b - a) or big[2] in ('table', 'form', 'script', 'svg', 'pre', 'details'): return kids if len(kids) >= 8 else None
        a = t.find('>', big[0]) + 1; b = t.rfind('</', big[0], big[1])
    return None

def cut(path, rel):
    t = path.read_text('utf-8', 'ignore')
    if len(t.encode()) < MIN_BYTES or 'data-cw-more=' in t or 'data-cw-noclip' in t: return None
    kids = container(t)
    if not kids or len(kids) < 8: return None
    acc = 0; first = None
    for i, k in enumerate(kids):
        acc += k[1] - k[0]
        if acc > KEEP_BYTES and i >= 2: first = i + 1; break
    if first is None or first >= len(kids) - 1: return None
    rest = kids[first:]
    tail = t[rest[0][0]:rest[-1][1]]
    if re.search(r'<(script|form)\b', tail, re.I): return None          # scripts and forms stay with the page
    url = '/' + rel.rstrip('/') + '/_more/' if rel else '/_more/'
    chunks, buf, size = [], [], 0
    for k in rest:
        piece = t[k[0]:k[1]]; buf.append(piece); size += len(piece)
        if size >= CHUNK_BYTES: chunks.append(''.join(buf)); buf, size = [], 0
    if buf: chunks.append(''.join(buf))
    d = path.parent / '_more'; d.mkdir(exist_ok=True)
    for n, c in enumerate(chunks, 1): (d / ('%d.json' % n)).write_text(json.dumps({'v': 1, 'n': n, 'of': len(chunks), 'html': c}, ensure_ascii=False, separators=(',', ':')), 'utf-8')
    marker = ('<div data-cw-more="%s" data-cw-more-n="%d" hidden></div>' % (url, len(chunks)))
    new = t[:rest[0][0]] + marker + t[rest[-1][1]:]
    path.write_text(new, 'utf-8')
    return {'page': '/' + rel, 'before': len(t.encode()), 'after': len(new.encode()), 'chunks': len(chunks)}

def run(dist):
    dist = pathlib.Path(dist); rep = []
    for a in AREAS:
        for half in ('', 'wales/', 'argentina/'):
            base = dist / (half + a)
            if not base.is_dir(): continue
            for f in sorted(base.rglob('index.html')):
                if len(rep) >= MAX_PAGES: break
                rel = str(f.parent.relative_to(dist)).replace(os.sep, '/')
                if rel == '.': rel = ''
                if SKIP.match(rel) or '/_more' in rel: continue
                try: r = cut(f, rel)
                except Exception as e: r = None; print('readmore_chunks', rel, e)
                if r: rep.append(r)
    try: (dist / '_cedwyn' / 'reports').mkdir(parents=True, exist_ok=True); (dist / '_cedwyn' / 'reports' / 'readmore_chunks.json').write_text(json.dumps(rep, indent=1))
    except Exception: pass
    print('readmore_chunks 1.0.0: %d pages cut, %d KB moved behind Read more' % (len(rep), sum(r['before'] - r['after'] for r in rep) // 1024))
    return rep

if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / 'dist')
