#!/usr/bin/env python3
"""chronology.py - chronology and outside records (Sion, 11:45 GMT 26 Oct 2026, m:1138070f). - Sion's Tab agent
Tŷ Mawr is first named in the record we have found in the 1824 David Stewart survey (EV-0211); in the family's account
Tŷ Mawr was acquired in 1667. Bute estate and other third-party documents are never shown as records of Tŷ Mawr dated
before 1824. Reads chronology.json and, over dist/<theme>/ (cedwyn copy only; datro and the WordPress wiki are untouched):
1. applies the ordered regex rewrites to text files (skip_prefixes = archived correspondence and third-party captures,
   kept verbatim; notice_only_themes = the wiki copy, whose own words are left as the wiki has them);
2. puts the "How we treat outside records" notice (en/cy/es) after the first </h1> (else after <body>) of every HTML page
   whose visible text still shows such a document (trigger_re, or all of trigger_all: Bute + a year before 1824 + a name of the house),
   and the same paragraph at the top of every llms.txt (for agents reading the site), linking to the method section on /values/.
Report: dist/_cedwyn/reports/chronology.json. site.py calls it after theme_notices.
Usage: python3 tools/chronology.py dist"""
import json, re, html, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
# Small ⓘ icon + popup, not a big block (Sion, 13:15 GMT 26 Oct 2026). Native <details>: no JS, the text stays in the HTML - Sion's Tab agent
BOX = ('<aside class="cedwyn-notice cw-ior" data-cedwyn-notice="{k}" role="note" style="position:relative;display:block;margin:6px 0;text-align:left;font-size:13px;line-height:1.45">'
       '<style>.cw-ior details{{border:0!important;margin:0!important;padding:0!important;background:none!important;box-shadow:none!important}}.cw-ior summary{{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:5px;color:inherit;font-weight:600;font-size:12px;padding:2px 0!important;margin:0!important;border:0!important;background:none!important}}'
       '.cw-ior summary::-webkit-details-marker{{display:none}}.cw-ior .cw-i{{display:inline-grid;place-items:center;width:18px;height:18px;border-radius:50%;border:1.5px solid currentColor;font:italic 700 12px/1 Georgia,serif}}'
       '.cw-ior .cw-p{{position:absolute;z-index:60;left:0;top:26px;width:min(92vw,520px);max-height:70vh;overflow:auto;border:1px solid #c8a03c;background:#fbf6e6;color:#1c1c22;border-radius:8px;padding:10px 12px;box-shadow:0 6px 24px rgba(0,0,0,.25)}}'
       '@media print,(max-width:640px){{.cw-ior .cw-p{{position:static;width:auto;max-width:100%;margin-top:4px;box-shadow:none}}}}</style>'
       '<details><summary title="{h}"><span class="cw-i" aria-hidden="true">i</span><span>__CWL__</span></summary><div class="cw-p"><strong>{h}</strong> {t} '
       '<a href="{l}" style="color:#4A1942;text-decoration:underline">{lt}</a><span lang="cy" style="display:block;margin-top:4px;opacity:.85">{cy}</span>'
       '<span lang="es" style="display:block;margin-top:2px;opacity:.85">{es}</span></div></details></aside>')
CWL = {'cy': 'Cofnodion allanol', 'es': 'Registros externos'}
def _bx(box, t):
    m = re.search(r'<html[^>]*\blang=["\']?([a-z]{2})', t[:3000], re.I)
    return box.replace('__CWL__', CWL.get(m.group(1).lower() if m else 'en', 'Outside records'))
# Reference and utility pages (dictionary, guest book, e-book list, maps index, subscribe, landing) carry no notice (Sion, 13:27 GMT 26 Oct 2026) - Sion's Tab agent
REF_PAGES = ('nomenclature/', 'guestbook/', 'subscribe/', 'glossary/')
REF_EXACT = ('index.html', 'ebooks/index.html', 'maps/index.html', 'directory/index.html')
def _ref_page(rel):
    return rel.startswith(REF_PAGES) or rel in REF_EXACT
def _visible(t):
    t = re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', t)
    return re.sub(r'<[^>]+>', ' ', t)
def run(dist, cfg_path=None):
    dist = pathlib.Path(dist); cfg = json.load(open(cfg_path or ROOT / 'chronology.json', encoding='utf-8'))
    rw = [(r['id'], re.compile(r['re']), r['replace']) for r in cfg['rewrites']]
    skip = tuple(cfg.get('skip_prefixes', [])); nonly = set(cfg.get('notice_only_themes', [])); exts = set(cfg.get('text_ext', []))
    N = cfg['notice']; trig = re.compile(N['trigger_re']); tall = [re.compile(x) for x in N.get('trigger_all', [])]
    hit = lambda v: bool(trig.search(v)) or (bool(tall) and all(x.search(v) for x in tall))
    llms_para = '## How we treat outside records\n\n' + N.get('llms_text', N['text']) + ' Method: ' + N['link'] + '\n\n'
    def llms_insert(t):   # after the H1 and its summary blockquote, so the llms.txt shape stays intact
        m = re.match(r'(\s*#[^\n]*\n(?:\s*\n)*(?:>[^\n]*\n)*\s*\n?)', t)
        return (t[:m.end()] + llms_para + t[m.end():]) if m and m.group(1).strip().startswith('#') else llms_para + t
    box = BOX.format(k=html.escape(N['id']), h=html.escape(N['heading']), t=html.escape(N['text']), l=html.escape(N['link']),
                     lt=html.escape(N['link_text']), cy=html.escape(N['cy']), es=html.escape(N['es']))
    rep = {'version': cfg.get('version'), 'rewrites': {}, 'files_changed': 0, 'notices': 0, 'notice_pages': []}
    for f in dist.rglob('*'):
        if not f.is_file() or f.suffix.lower() not in exts: continue
        rel = f.relative_to(dist).as_posix()
        if rel.startswith(skip) or rel.startswith('_cedwyn/'): continue
        theme = rel.split('/', 1)[0]
        try: t = f.read_text(encoding='utf-8')
        except Exception: continue
        if not (('15' in t) or ('Cydwin' in t) or ('219' in t) or ('Bute' in t) or f.name == 'llms.txt'): continue
        o = t
        if theme not in nonly:
            for i, c, r in rw:
                t, n = c.subn(r, t)
                if n: rep['rewrites'][i] = rep['rewrites'].get(i, 0) + n
        if f.name == 'llms.txt' and '## How we treat outside records' not in t:
            t = llms_insert(t)
        if f.suffix.lower() in ('.html', '.htm') and not _ref_page(rel) and 'data-cedwyn-notice="%s"' % N['id'] not in t and hit(_visible(t)):
            j = t.find('</h1>')
            if j >= 0: t = t[:j + 5] + _bx(box, t) + t[j + 5:]
            else:
                m = re.search(r'<body\b[^>]*>', t, re.I)
                if m: t = t[:m.end()] + _bx(box, t) + t[m.end():]
            if t != o or 'data-cedwyn-notice' in t: rep['notices'] += 1; rep['notice_pages'].append(rel)
        if t != o: f.write_text(t, encoding='utf-8'); rep['files_changed'] += 1
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'chronology.json', 'w'), indent=1, ensure_ascii=False)
    print('chronology:', sum(rep['rewrites'].values()), 'rewrites in', rep['files_changed'], 'files;', rep['notices'], 'notices')
    return rep
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
