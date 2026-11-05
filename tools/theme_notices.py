#!/usr/bin/env python3
"""theme_notices.py - per-theme notice boxes (25 Oct 2026, forensic audit intake). - Sion's Tab agent
Optional "link": {"href","label"} on a notice adds one internal link after its text (27 Oct 2026, correction notices -> /disproven/).
Each compartment keeps its own notices in notices/<theme>.json; this step touches only dist/<theme>/ pages listed there.
A notice goes directly after the page's first </h1>; on the theme home ("home_before_details") directly above the first <details>.
Usage: python3 tools/theme_notices.py dist   (site.py calls it right after the ingredients pass)"""
import json, html, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
# Small ⓘ icon + popup instead of a block (Sion, 13:15 and 13:24 GMT 26 Oct 2026): native <details>, text stays in the HTML - Sion's Tab agent
BOX = ('<aside class="cedwyn-notice cw-ior" data-cedwyn-notice="{k}" role="note" style="position:relative;display:block;margin:6px 0;text-align:left;font-size:13px;line-height:1.45">'
       '<style>.cw-ior details{{border:0!important;margin:0!important;padding:0!important;background:none!important;box-shadow:none!important}}.cw-ior summary{{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:5px;color:inherit;font-weight:600;font-size:12px;padding:2px 0!important;margin:0!important;border:0!important;background:none!important}}'
       '.cw-ior summary::-webkit-details-marker{{display:none}}.cw-ior .cw-i{{display:inline-grid;place-items:center;width:18px;height:18px;border-radius:50%;border:1.5px solid currentColor;font:italic 700 12px/1 Georgia,serif}}'
       '.cw-ior .cw-p{{position:absolute;z-index:60;left:0;top:26px;width:min(92vw,520px);max-height:70vh;overflow:auto;border:1px solid #c8a03c;background:#fbf6e6;color:#1c1c22;border-radius:8px;padding:10px 12px;box-shadow:0 6px 24px rgba(0,0,0,.25)}}'
       '@media print,(max-width:640px){{.cw-ior .cw-p{{position:static;width:auto;max-width:100%;margin-top:4px;box-shadow:none}}}}</style>'
       '<details><summary title="{h}"><span class="cw-i" aria-hidden="true">i</span><span>{lab}</span></summary><div class="cw-p"><strong>{h}</strong> {t}</div></details></aside>')
def run(dist):
    dist = pathlib.Path(dist); done = 0; miss = []
    for cf in sorted((ROOT / 'notices').glob('*.json')):
        N = json.load(open(cf, encoding='utf-8')); theme = N['theme']
        for n in N['notices']:
            box = BOX.format(k=html.escape(n['id']), h=html.escape(n.get('heading', '')), t=html.escape(n['text']) + ((' <a href="%s">%s</a>' % (html.escape(n['link']['href']), html.escape(n['link']['label']))) if n.get('link') else ''), lab=html.escape(n.get('label') or n.get('heading', '').rstrip('.') or 'Note'))
            for pg in n.get('pages', []):
                rel = pg.strip('/').split('/', 1)
                if rel[0] != theme: miss.append(pg); continue   # a compartment's notices stay in that compartment
                f = dist / theme / ((rel[1] + '/') if len(rel) > 1 else '') / 'index.html'
                if not f.exists(): miss.append(pg); continue
                t = f.read_text(encoding='utf-8', errors='surrogateescape')
                if 'data-cedwyn-notice="%s"' % n['id'] in t: continue
                i = t.find('</h1>')
                if i < 0: miss.append(pg); continue
                f.write_text(t[:i + 5] + box + t[i + 5:], encoding='utf-8', errors='surrogateescape'); done += 1
            if n.get('home_before_details'):
                f = dist / theme / 'index.html'
                if f.exists():
                    t = f.read_text(encoding='utf-8', errors='surrogateescape'); i = t.find('<details')
                    if i >= 0 and ('data-cedwyn-notice="%s"' % n['id']) not in t[:i]:
                        f.write_text(t[:i] + box + t[i:], encoding='utf-8', errors='surrogateescape'); done += 1
                    elif i < 0: miss.append('/%s/ (no <details>)' % theme)
    print('theme_notices:', done, 'placed;', len(miss), 'not found', miss[:4])
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
