#!/usr/bin/env python3
"""wayback_viewer.py - the archived-websites viewer inside the Wayback Vault theme (26 Oct 2026).
Runs at the end of tools/site.py over dist/wayback/:
 1. every snapshot page (dist/wayback/websites/<host>/<slug>/latest.html and v*.html, the pages carrying the old
    #wbx-banner strip) gets one Cedwyn title bar: back to the list, source site, page title, capture date and
    version, previous / next archived page (relative links), source and screenshot links folded under "Source and
    versions", and a stylesheet that keeps the style-stripped copy readable (icon sprites and unsized SVG icons,
    hidden helpers and dropdown menus no longer print as huge blank blocks; the original site's header, menus and
    footer fold away behind a "Show the original site's menus" switch that needs no JavaScript; nothing is deleted).
 2. dist/wayback/index.html: a shared #websites/<host>/<slug> address opens /wayback/websites/<host>/<slug>/latest.html
    (it used to forward to /websites/... without the theme prefix, a 404 on Cedwyn), and tapping a card opens the
    copy itself instead of a full-screen frame that stacked the copy's own Cedwyn header under the Vault's.
Idempotent (marker cdw-wbx). Report: dist/_cedwyn/reports/wayback_viewer.json. - Sion's Tab agent"""
import json, pathlib, re, html, datetime
MARK = 'cdw-wbx'
CSS = """<style id="cdw-wbx">
#wbx-banner.cdw-wbx{position:static;margin:0 -1rem 1.1rem;padding:.75rem 1rem .7rem;background:#14141c;color:#f1f1f7;border-bottom:3px solid #f8dba0;font:14px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;box-sizing:border-box;max-width:none}
#wbx-banner.cdw-wbx *{box-sizing:border-box}
#wbx-banner.cdw-wbx a{color:#f8dba0;text-decoration:none;pointer-events:auto}
#wbx-banner.cdw-wbx a:hover,#wbx-banner.cdw-wbx a:focus-visible{text-decoration:underline}
#wbx-banner .cdw-top{display:flex;flex-wrap:wrap;gap:.25rem .75rem;align-items:baseline;justify-content:space-between;font-size:.8rem;letter-spacing:.02em}
#wbx-banner .cdw-back{font-weight:600}
#wbx-banner .cdw-pos{color:#c8c8d8;overflow-wrap:anywhere}
#wbx-banner .cdw-t{margin:.45rem 0 .2rem;font-size:1.12rem;line-height:1.3;font-weight:700;color:#fff;overflow-wrap:anywhere}
#wbx-banner .cdw-m{margin:0;color:#d2d2e0;font-size:.85rem}
#wbx-banner .cdw-act{display:flex;flex-wrap:wrap;gap:.5rem;margin:.6rem 0 .1rem}
#wbx-banner .cdw-act a,#wbx-banner .cdw-act span,#wbx-banner .cdw-act label{display:inline-flex;align-items:center;min-height:38px;padding:.3rem .8rem;border:1px solid #5c5c70;border-radius:8px;background:#20202c;color:#f8dba0;font-size:.85rem;cursor:pointer}
#wbx-banner .cdw-act span{opacity:.45;cursor:default}
#wbx-banner .cdw-act label{color:#d2d2e0}
#wbx-banner details{margin-top:.45rem;font-size:.8rem;color:#c8c8d8}
#wbx-banner summary{cursor:pointer;color:#d2d2e0;min-height:28px}
#wbx-banner .u{word-break:break-all;color:#cfcfe0}
.cdw-all{position:absolute;opacity:0;width:1px;height:1px;pointer-events:none}
.cdw-all:focus-visible+#wbx-page{outline:2px solid #f8dba0}
.cdw-foot{display:flex;flex-wrap:wrap;gap:.5rem;justify-content:space-between;margin:2rem -1rem 0;padding:.8rem 1rem;background:#14141c;font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}
.cdw-foot a{color:#f8dba0;text-decoration:none;padding:.3rem .2rem;min-height:38px;display:inline-flex;align-items:center}
#wbx-page{overflow-wrap:anywhere;max-width:100%;overflow-x:hidden;overflow-x:clip}
#wbx-page :is(input,select,textarea,button,embed,object),#wbx-page [style*="width"]{max-width:100%!important}
#wbx-page :is(ins.adsbygoogle,.adsbygoogle,[id^=aswift_],[id^=google_ads],[id^=div-gpt-ad]){display:none!important}
#wbx-page :is(.d-none,[hidden],template,.visually-hidden,.visually-hidden-focusable,.sr-only,.screen-reader-text,.skip-link,.dropdown-menu,.modal,.offcanvas,.tooltip,.popover,noscript){display:none!important}
#wbx-page :is(.osd,.openseadragon-container,canvas,.leaflet-container,.mapboxgl-map,.ol-viewport,.gm-style){display:none!important}
#wbx-page svg{max-width:1.5em!important;max-height:1.5em!important;width:auto;height:auto}
#wbx-page svg:not([viewBox]):not([width]){display:none}
.cdw-all:not(:checked)~#wbx-page :is(header,nav,footer,aside,[role=banner],[role=navigation],[role=contentinfo],[role=search],#cookie-banner,.cookie-banner,.cookies,.vector-header-container,.vector-sticky-header,.vector-column-start,.vector-page-toolbar,.vector-dropdown,.vector-page-titlebar-toc,.mw-jump-link,.mw-editsection,#mw-head,#mw-panel):not(main *):not(article *):not([role=main] *){display:none!important}
.cdw-all:checked~#wbx-page{border-top:1px dashed #bbb}
</style>"""

def esc(s): return html.escape(str(s or ''), quote=True)

def when(ts):
    try:
        d = datetime.datetime.strptime(ts[:19], '%Y-%m-%dT%H:%M:%S')
        return f"{d.day} {d.strftime('%b %Y')}, {d.strftime('%H:%M')} UTC"
    except Exception:
        return esc(ts)

def host_label(h): return re.sub(r'^www\.', '', h or '')

def order(items):
    """the same order the Vault list shows: sites by page count (then name), pages in index order"""
    by = {}
    for i in items: by.setdefault(i['host'], []).append(i)
    hosts = sorted(by, key=lambda h: (-len(by[h]), h))
    return [i for h in hosts for i in by[h]], by

def rel(frm, to):
    """relative link between two snapshot folders /websites/<host>/<slug>/"""
    a = frm.strip('/').split('/'); b = to.strip('/').split('/')
    if a[1] == b[1]: return f'../{b[2]}/latest.html'
    return f'../../{b[1]}/{b[2]}/latest.html'

def bar(i, meta, ver, captured, prev, nxt, n, of, vfiles):
    path = i['path'] if 'path' in i else '/websites/%s/%s/' % (i['host'], i['slug'])
    p = f'<a class="cdw-prev" rel="prev" href="{esc(rel(path, prev["path"]))}" title="{esc(prev["title"])}">‹ Previous</a>' if prev else '<span aria-disabled="true">‹ Previous</span>'
    x = f'<a class="cdw-next" rel="next" href="{esc(rel(path, nxt["path"]))}" title="{esc(nxt["title"])}">Next ›</a>' if nxt else '<span aria-disabled="true">Next ›</span>'
    src = meta.get('url') or i.get('url') or ''
    go = '/wayback/go/?u=' + __import__('urllib.parse').parse.quote(src, safe='') if src else ''
    shot = ''
    for v in meta.get('versions', []):
        if v.get('version') == ver and v.get('screenshot'): shot = v['screenshot']
    vers = ''
    if len(vfiles) > 1:
        vers = ' · Versions: ' + ', '.join(f'<a href="{esc(f)}">{esc(v)}</a>' for v, f in vfiles)
    more = (f'<details><summary>Source and versions</summary>Source: <span class="u">{esc(src)}</span>'
            + (f' · <a href="{esc(go)}" rel="noopener">Live website</a>' if go else '')
            + vers + '</details>')
    sh = f'<a class="cdw-shot" href="{esc(shot)}" target="_blank" rel="noopener">Screenshot of the original</a>' if shot else ''
    return (f'<nav id="wbx-banner" class="{MARK}" aria-label="Archived page">'
            f'<div class="cdw-top"><a class="cdw-back" href="../../../#websites">← All archived websites</a>'
            f'<span class="cdw-pos">{esc(host_label(i["host"]))}' + (f' · page {n} of {of}' if n else '') + '</span></div>'
            f'<p class="cdw-t">{esc(meta.get("title") or i.get("title"))}</p>'
            f'<p class="cdw-m">Archived copy {esc(ver)} · captured {when(captured)}</p>'
            f'<div class="cdw-act">{p}{x}{sh}<label for="cdw-all">Show the original site\'s menus</label></div>'
            f'{more}</nav><input type="checkbox" id="cdw-all" class="cdw-all">'), (p, x)

def run(dist):
    dist = pathlib.Path(dist); wb = dist / 'wayback'; rep = {'pages': 0, 'files': 0, 'skipped': [], 'index': []}
    wi = wb / 'websites' / 'index.json'
    if wi.exists():
        items = json.load(open(wi, encoding='utf-8')).get('items', [])
        for i in items: i.setdefault('path', '/websites/%s/%s/' % (i['host'], i['slug']))
        seq, by = order(items)
        for k, i in enumerate(seq):
            d = wb / i['path'].strip('/')
            mp = d / 'meta.json'
            try: meta = json.load(open(mp, encoding='utf-8'))
            except Exception: meta = {}
            vlist = [(v.get('version'), v.get('file')) for v in meta.get('versions', []) if v.get('file') and (d / v['file']).exists()]
            caps = {v.get('version'): v.get('captured_utc') for v in meta.get('versions', [])}
            prev = seq[k - 1] if k > 0 else None; nxt = seq[k + 1] if k + 1 < len(seq) else None
            hs = by[i['host']]; n = hs.index(i) + 1
            files = [d / 'latest.html'] + [d / f for _, f in vlist]
            done = 0
            for f in dict.fromkeys(files):
                if not f.exists(): continue
                t = f.read_text(encoding='utf-8', errors='replace')
                if MARK in t: done += 1; continue
                m = re.search(r'<div id="wbx-banner">.*?</div>', t, re.S)
                if not m: rep['skipped'].append(str(f.relative_to(dist))); continue
                mv = re.search(r'Archived copy (v[\d.]+)', m.group(0))
                ver = mv.group(1) if mv else (i.get('version') or meta.get('current_version') or '')
                captured = caps.get(ver) or i.get('captured') or meta.get('last_captured') or ''
                b, (p, x) = bar(i, meta, ver, captured, prev, nxt, n, len(hs), vlist)
                foot = (f'<nav class="cdw-foot" aria-label="Archived page navigation"><a href="../../../#websites">← All archived websites</a>'
                        + (p.replace('class="cdw-prev"', '') if prev else '') + (x.replace('class="cdw-next"', '') if nxt else '') + '</nav>')
                foot = re.sub(r'<span aria-disabled="true">[^<]*</span>', '', foot)
                t = t[:m.start()] + b + t[m.end():]
                t = t.replace('</head>', CSS + '</head>', 1) if '</head>' in t else CSS + t
                t = re.sub(r'(</body>)(?![\s\S]*</body>)', foot + r'\1', t, count=1) if '</body>' in t else t + foot
                f.write_text(t, encoding='utf-8'); done += 1; rep['files'] += 1
            if done: rep['pages'] += 1
        # snapshot folders the index does not list (moved or withdrawn pages): the same bar, back link only
        known = {(wb / i['path'].strip('/')).resolve() for i in seq}
        for d in sorted({f.parent for f in (wb / 'websites').glob('*/*/latest.html')}):
            if d.resolve() in known: continue
            try: meta = json.load(open(d / 'meta.json', encoding='utf-8'))
            except Exception: meta = {}
            i = {'host': d.parent.name, 'slug': d.name, 'path': '/websites/%s/%s/' % (d.parent.name, d.name), 'title': meta.get('title', '')}
            vlist = [(v.get('version'), v.get('file')) for v in meta.get('versions', []) if v.get('file') and (d / v['file']).exists()]
            caps = {v.get('version'): v.get('captured_utc') for v in meta.get('versions', [])}
            for f in dict.fromkeys([d / 'latest.html'] + [d / fn for _, fn in vlist]):
                if not f.exists(): continue
                t = f.read_text(encoding='utf-8', errors='replace')
                if MARK in t: continue
                m = re.search(r'<div id="wbx-banner">.*?</div>', t, re.S)
                if not m: rep['skipped'].append(str(f.relative_to(dist))); continue
                mv = re.search(r'Archived copy (v[\d.]+)', m.group(0)); ver = mv.group(1) if mv else meta.get('current_version', '')
                if not i['title']:
                    mt = re.search(r'<title>(.*?)</title>', t, re.S); i['title'] = html.unescape(mt.group(1)).strip() if mt else d.name
                b, _ = bar(i, meta, ver, caps.get(ver) or meta.get('last_captured', ''), None, None, None, None, vlist)
                foot = '<nav class="cdw-foot" aria-label="Archived page navigation"><a href="../../../#websites">← All archived websites</a></nav>'
                t = t[:m.start()] + b + t[m.end():]
                t = t.replace('</head>', CSS + '</head>', 1) if '</head>' in t else CSS + t
                t = re.sub(r'(</body>)(?![\s\S]*</body>)', foot + r'\1', t, count=1) if '</body>' in t else t + foot
                f.write_text(t, encoding='utf-8'); rep['files'] += 1; rep['unlisted'] = rep.get('unlisted', 0) + 1
    ix = wb / 'index.html'
    if ix.exists():
        t = ix.read_text(encoding='utf-8')
        reps = [
            ("location.replace(`/websites/${m[1]}/${m[2]}/`)", "location.replace(`/wayback/websites/${m[1]}/${m[2]}/latest.html`)"),
            ("function wsOpen(latest) {", "function wsOpen(latest) { if (latest) { location.href = '/wayback' + latest; return; }"),
            ("Tap a card to preview the copy here;", "Tap a card to open the archived copy, with back and next links;"),
            ('aria-label="Preview ${wsEsc(i.title)}"', 'aria-label="Open ${wsEsc(i.title)}"'),
        ]
        for a, b in reps:
            if b in t: rep['index'].append('already: ' + a[:40])
            elif a in t: t = t.replace(a, b); rep['index'].append('ok: ' + a[:40])
            else: rep['index'].append('MISSING: ' + a[:40])
        ix.write_text(t, encoding='utf-8')
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    rep['skipped'] = rep['skipped'][:50]
    json.dump(rep, open(out / 'wayback_viewer.json', 'w'), indent=1)
    print('wayback_viewer:', json.dumps({k: (v if k != 'skipped' else len(v)) for k, v in rep.items()}))
    return rep

if __name__ == '__main__':
    import sys; run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
