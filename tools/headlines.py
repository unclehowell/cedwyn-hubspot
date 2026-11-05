#!/usr/bin/env python3
"""headlines.py - three-line "read more" on every human page (Sion, 23:32 GMT 26 Oct 2026). - Sion's Tab agent
Sion: "You've gone overkill on the 'read more' whereby its literally a header then 'read more'. Thats not how read more works.
You basically are supposed to have a rule like don't show more than 3 lines of text on any page load, just crop it at 3 lines
and end the last of the 3rd line with 'read more' to expand to see more. But also have 'read more' become 'less' link, to
collapse that expanded segment. Apply this site wide."

This replaces the heading-then-"Learn more" folds (PRs #7-#11). One pass over every page the build wrote:
1. unwrap: any old fold (<details class="cw-more">, levels 2 and 3, its "Show less" button and its CSS), which section snapshots
   taken while the folds were live still carry, goes; its content returns to the normal flow, word for word.
2. clamp: the page gets /_cedwyn/clamp.js and its small CSS. In the browser every text block shows its first three lines and,
   only when it runs longer, ends the third line with "… read more", which opens it in place and turns into "less".
   Headings, images, video, tables, navigation, tiles, buttons and forms are never cropped; no JavaScript = every word shows.
Never touched: the landing page (/), archived copies of outside websites (/wayback/websites/), letters (/email/), the e-book
shop and readers, the database, /agents/, /academy/, single-page shells keep the script only (it clamps what they render).
Runs from tools/site.py after ebook_editions and before guestbook. Report: dist/_cedwyn/reports/headlines.json.

27 Oct 2026 (Sion, WhatsApp 06:16 GMT): clamp.js v2 reads a run of paragraphs as ONE segment: the first three lines show, then
"read more" opens one paragraph at a time, a new "read more" at the end of each, and "less" closes it back to the opening lines.
A page can mark its own segment with data-cw-seg (its children are the paragraphs); opt out with data-cw-noclamp, .cw-noclamp or
.no-readmore. Every word stays in the HTML. - Sion's Tab agent
"""
import json, pathlib, re, sys

SKIP_DIRS = ('_blob/', '_ext/', 'db/', '_cedwyn/', 'wayback/websites/', 'email/', 'emails/view/', 'graphql/', 'catalogue/',
             'guestbook/', 'explore/', 'ebooks/', 'shop/', 'app/', 'chess/', 'chat/', 'agents/', 'academy/')
SKIP_FILES = {'index.html', '404.html'}          # index.html = the landing page: two tiles, stays as it is
JS = '<script src="/_cedwyn/clamp.js?v=2" defer></script>'   # v2: paragraph-at-a-time read more (27 Oct 2026)
CSS = '<style id="cw-clamp-css">.cw-c{display:-webkit-box!important;-webkit-box-orient:vertical!important;-webkit-line-clamp:3!important;line-clamp:3;overflow:hidden!important;position:relative}.cw-h{display:none!important}@media print{.cw-c{display:block!important;-webkit-line-clamp:unset!important;overflow:visible!important}.cw-h{display:revert!important}}</style>'   # the rest of the styling ships inside clamp.js v2

OPEN = re.compile(r'<details class="cw-more(?: cw-more-3)?"><summary data-cw-more><span class="cw-more-l">[^<]*</span></summary><div class="cw-more-b">')
CLOSE = re.compile(r'<button type="button" class="cw-less" data-cw-less(?: hidden)?>[^<]*</button></div></details>')
OLDCSS = re.compile(r'<style id="cw-more-css">.*?</style>(?:<noscript><style>details\.cw-more::details-content.*?</style></noscript>)?', re.S)

def unwrap(t):
    a = len(OPEN.findall(t)); b = len(CLOSE.findall(t))
    if not a and 'id="cw-more-css"' not in t: return t, 0
    if a != b: return t, -1                              # unbalanced: leave the page as it is (reported)
    t = OPEN.sub('', t); t = CLOSE.sub('', t); t = OLDCSS.sub('', t); t = t.replace(' data-cw-lead', '')
    return t, a

def inject(t):
    if '/_cedwyn/clamp.js' in t:   # a snapshot that already carries the script: move it to the current version and CSS
        return re.sub(r'<style id="cw-clamp-css">.*?</style>', lambda m: CSS, t.replace('/_cedwyn/clamp.js?v=1', '/_cedwyn/clamp.js?v=2'), count=1, flags=re.S)
    i = t.lower().find('</head>')
    add = CSS + JS
    return (t[:i] + add + t[i:]) if i >= 0 else add + t


# The research pages' own older "read more" (section snapshots): <details class="ghf-rm">, a cut-off lead line, then
# "… read more". Unwrapped the same way, so a page has one kind of read more: the lead line is a cut-off copy of the text
# below it and goes. Native <details> that are menus, map keys or timeline entries stay as they are. - Sion's Tab agent
FOLD = re.compile(r'<details\b[^>]*\bclass="(?:[^"]*\s)?(ghf-rm)(?:\s[^"]*)?"[^>]*>', re.I)
TAG = re.compile(r'<(/?)details\b[^>]*>', re.I)
SUM = re.compile(r'\s*<summary\b[^>]*>(.*?)</summary>', re.I | re.S)

def unfold(t):
    n = 0; pos = 0
    while True:
        m = FOLD.search(t, pos)
        if not m: return t, n
        depth, end = 0, None
        for k in TAG.finditer(t, m.start()):
            depth += -1 if k.group(1) else 1
            if depth == 0: end = k; break
        s = SUM.match(t, m.end())
        if end is None or not s or s.end() > end.start(): pos = m.end(); continue
        lab = s.group(1); im = re.search(r'\bid="([^"]+)"', m.group(0)); ida = (' id="%s"' % im.group(1)) if im else ''
        if m.group(1).lower() == 'ghf-rm': head = ('<span%s></span>' % ida) if ida else ''
        else: head = '<p class="cw-unfold"%s><strong>%s</strong></p>' % (ida, lab.strip())
        t = t[:m.start()] + head + t[s.end():end.start()] + t[end.end():]
        n += 1; pos = m.start()

def apply(t):
    t, u = unwrap(t)
    if u >= 0:
        t, f = unfold(t); u += f
    return inject(t), u

def run(dist):
    dist = pathlib.Path(dist); rep = {'pages': 0, 'unwrapped_pages': 0, 'unwrapped_folds': 0, 'unbalanced': [], 'themes': {}}
    for f in sorted(dist.rglob('*.html')):
        rel = f.relative_to(dist).as_posix()
        if rel in SKIP_FILES or rel.startswith(SKIP_DIRS): continue
        try: t = f.read_text(encoding='utf-8', errors='surrogateescape')
        except Exception: continue
        if len(t) > 30_000_000 or 'data-cw-headlines-off' in t: continue
        out, u = apply(t)
        if u < 0: rep['unbalanced'].append(rel)
        elif u: rep['unwrapped_pages'] += 1; rep['unwrapped_folds'] += u
        if out != t:
            f.write_text(out, encoding='utf-8', errors='surrogateescape'); rep['pages'] += 1
            th = rel.split('/')[0] if '/' in rel else '(root)'; rep['themes'][th] = rep['themes'].get(th, 0) + 1
    rep['unbalanced'] = rep['unbalanced'][:50]
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'headlines.json', 'w'), indent=1)
    print('headlines: clamp on', rep['pages'], 'pages; old folds unwrapped on', rep['unwrapped_pages'], 'pages;', len(rep['unbalanced']), 'unbalanced')
    return rep

if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
