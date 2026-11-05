#!/usr/bin/env python3
"""wikilinks.py - Cedwyn as a wiki for first-time visitors (Sion, 22:12 GMT 26 Oct 2026, m:611a2587). - Sion's Tab agent
"if a word can be a hyperlink to an anchor of where there's elaboration of the word or phrase, then be sure its hyperlinked
accordingly ... cater for nomenclatures ... a different color hyperlink whereby a modal opens with all the nomenclatures".

One pass over every human page the build wrote (after headlines.py):
- GLOSSARY links (data/glossary.json): the first time a term appears in each section (h1/h2/h3 starts a section) of body text
  it becomes <a class="cw-g" href="/glossary/#slug" data-tip="one-line definition">. Hover, focus or a first tap shows the
  one-line definition; the link opens the entry on /glossary/.
- NAME links (data/nomenclature.json): a name with spelling variants (Tŷ Mawr, Cedfin, Cydfin, Great House, Llandough, BP ...)
  becomes <a class="cw-n" ...> in a second accent (amber shading, dotted underline). Hover shows that spelling's one-liner;
  click or tap opens a pop-up listing every public variant, each linking to where it is explained. Without JavaScript the
  link opens the Nomenclature page for that name.
- Never inside headings, links, buttons, summaries, code, forms, navigation, headers, footers, notices, agent material or the
  guest book. Internal links only.
- Writes /glossary/ (A-Z, nested Learn more), /_cedwyn/glossary.json and /_cedwyn/nomenclature.json (public variants only),
  and a one-line legend in the page's small print. Report: dist/_cedwyn/reports/wikilinks.json.
Variants marked "not checked" in data/nomenclature.json are kept out of every public page.
"""
import html, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKIP_DIRS = ('_blob/', '_ext/', 'db/', '_cedwyn/', 'wayback/', 'email/', 'emails/', 'graphql/', 'catalogue/', 'guestbook/',
             'explore/', 'ebooks/', 'shop/', 'app/', 'chess/', 'chat/', 'agents/', 'academy/', 'nomenclature/', 'glossary/',
             'argentina/ebooks/', 'wales/ebooks/', 'argentina/nomenclature/', 'wales/nomenclature/', 'argentina/agents/',
             'wales/agents/', 'argentina/academy/', 'wales/academy/', 'argentina/email/', 'wales/email/', 'argentina/wayback/',
             'wales/wayback/', 'argentina/shop/', 'wales/shop/', 'argentina/chess/', 'wales/chess/', 'argentina/app/', 'wales/app/')
SKIP_FILES = {'404.html', 'index.html'}   # the landing page (/) belongs to the landing-fix work (root steer 22:24 GMT 26 Oct 2026)
SKIP_TAGS = {'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', 'summary', 'code', 'pre', 'kbd', 'samp', 'var', 'label', 'select',
             'option', 'nav', 'header', 'footer', 'title', 'textarea', 'noscript', 'svg', 'math', 'dialog', 'form', 'abbr', 'dfn',
             'script', 'style', 'template', 'iframe', 'object', 'canvas', 'figcaption', 'cite', 'time', 'head'}
RAW = {'script', 'style', 'textarea', 'template', 'svg', 'math', 'pre', 'code'}
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr', 'keygen'}
NEVER = re.compile(r'(ghf-agent|\bgaf|guestbook|cedwyn-(notice|rib|sec)|ghf-(header|eb|ui|lf)|ebook-strip|eb-strip|\bnav|menu|breadcrumb|'
                   r'modal|cw-legend|cw-tip|\bhv-|\btoc\b|lang-|translate|notranslate|ribbon|\bnotice\b|agent|machine|llms)', re.I)
SECTION = {'h1', 'h2', 'h3'}
TAG = re.compile(r'<!--.*?-->|<(/?)([a-zA-Z][a-zA-Z0-9:-]*)((?:[^>"\']|"[^"]*"|\'[^\']*\')*)>', re.S)
ATTR = re.compile(r'\b(class|id|role)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))', re.I)
ESC = lambda s: html.escape(s, quote=True)

def load():
    g = json.loads((ROOT / 'data' / 'glossary.json').read_text(encoding='utf-8'))
    n = json.loads((ROOT / 'data' / 'nomenclature.json').read_text(encoding='utf-8'))
    ents = []          # (pattern, case_insensitive, entry)
    for t in g['terms']:
        e = {'kind': 'g', 'key': t['slug'], 'href': t['anchor'], 'tip': '%s: %s' % (t['term'], t['definition'])}
        for m in t['match']: ents.append((m, bool(t.get('ci')), e))
    for grp in n['groups']:
        pub = {v['variant'].lower(): v for v in grp['variants'] if v.get('public')}
        first = re.split(r'(?<=[.!?])\s', grp['summary'])[0]
        for m in grp['match']:
            v = pub.get(m.lower())
            if v is None and not any(x.lower().startswith(m.lower()) or m.lower() in x.lower() for x in pub):
                continue   # a spelling with no public record is never linked
            tip = ('%s — %s' % (v['variant'], v['one_liner'])) if v else ('%s — %s' % (grp['name'], first))
            e = {'kind': 'n', 'key': ('n:' + m.lower()) if grp['id'] == 'tymawr' else ('n:' + grp['id']), 'href': grp['url'], 'tip': tip, 'grp': grp['id']}
            ents.append((m, False, e))
    ents.sort(key=lambda x: -len(x[0]))
    parts = []; lookup = {}
    for i, (m, ci, e) in enumerate(ents):
        pat = re.escape(m).replace(r'\ ', r'\s+')
        parts.append('(?P<t%d>%s%s)' % (i, '(?i:' if ci else '(?:', pat + ')'))
        lookup['t%d' % i] = e
    rx = re.compile(r'(?<![\w\-/&#@.])(?:' + '|'.join(parts) + r')(?![\w\-])')
    return g, n, rx, lookup

def attrs_skip(a):
    s = ' '.join((m.group(3) or m.group(4) or m.group(5) or '') for m in ATTR.finditer(a))
    return bool(s and NEVER.search(s))

def link_text(txt, rx, lookup, seen, stats):
    if not txt.strip() or len(txt) < 3: return txt
    out = []; last = 0
    for m in rx.finditer(txt):
        e = lookup[m.lastgroup]
        if e['key'] in seen: continue
        seen.add(e['key']); stats[e['kind']] += 1
        w = m.group(0)
        if e['kind'] == 'g':
            a = '<a class="cw-g" href="%s" data-tip="%s">%s</a>' % (e['href'], ESC(e['tip']), w)
        else:
            a = '<a class="cw-n" href="%s" data-n="%s" data-tip="%s" aria-haspopup="dialog">%s</a>' % (e['href'], e['grp'], ESC(e['tip']), w)
        out.append(txt[last:m.start()]); out.append(a); last = m.end()
    if not out: return txt
    out.append(txt[last:]); return ''.join(out)

def process(text, rx, lookup):
    lo = text.lower(); b = lo.find('<body')
    if b < 0: return text, {'g': 0, 'n': 0}
    stats = {'g': 0, 'n': 0}; out = [text[:b]]; pos = b; skip = []; seen = set()
    n = len(text)
    while pos < n:
        m = TAG.search(text, pos)
        if not m:
            seg = text[pos:]; out.append(seg if skip else link_text(seg, rx, lookup, seen, stats)); break
        seg = text[pos:m.start()]
        out.append(seg if skip else link_text(seg, rx, lookup, seen, stats))
        tok = m.group(0); out.append(tok); pos = m.end()
        if tok.startswith('<!--'): continue
        close, tag, a = m.group(1), m.group(2).lower(), m.group(3) or ''
        if not close:
            if tag in SECTION: seen = set()
            selfclose = a.rstrip().endswith('/')
            if tag in RAW and not selfclose:
                j = lo.find('</' + tag, pos)
                if j < 0: out.append(text[pos:]); break
                out.append(text[pos:j]); pos = j; continue
            if tag in VOID or selfclose: continue
            if skip:
                if tag == skip[-1][0]: skip[-1][1] += 1
                elif tag in SKIP_TAGS: skip.append([tag, 1])
            elif tag in SKIP_TAGS or attrs_skip(a):
                skip.append([tag, 1])
        else:
            if skip and tag == skip[-1][0]:
                skip[-1][1] -= 1
                if skip[-1][1] == 0: skip.pop()
            elif skip and tag == 'body':
                skip = []
    return ''.join(out), stats

CSS = ('<style id="cw-wiki-css">a.cw-g{color:inherit;text-decoration:underline dotted 1.5px;text-underline-offset:3px;cursor:help}'
       'a.cw-n{color:inherit;text-decoration:underline dotted 2px #c98200;text-decoration-color:#c98200;text-underline-offset:3px;'
       'background:rgba(214,145,0,.14);border-radius:3px;padding:0 2px;cursor:pointer}a.cw-g:focus-visible,a.cw-n:focus-visible'
       '{outline:2px solid currentColor;outline-offset:2px}.cw-tip{position:absolute;z-index:2147483647;display:none;max-width:min(300px,'
       'calc(100vw - 16px));box-sizing:border-box;background:#1c1c1e;color:#fff;font:400 14px/1.4 system-ui,-apple-system,"Segoe UI",'
       'Roboto,sans-serif;padding:9px 11px;border-radius:9px;box-shadow:0 6px 22px rgba(0,0,0,.35);text-align:left;pointer-events:auto}'
       '.cw-tip a{color:#ffcf70;font-weight:600;display:inline-block;margin-top:6px;min-height:28px}.cw-modal-bg{position:fixed;inset:0;'
       'background:rgba(0,0,0,.58);z-index:2147483646;display:flex;align-items:center;justify-content:center;padding:12px}'
       '.cw-modal{background:#fff;color:#141414;width:100%;max-width:520px;max-height:86vh;overflow:auto;box-sizing:border-box;'
       'border-radius:16px;padding:20px 18px 16px;font:400 16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;position:relative;'
       'text-align:left;box-shadow:0 18px 50px rgba(0,0,0,.4)}.cw-modal h2{margin:0 44px 6px 0;font-size:1.3em;line-height:1.2;color:#141414}'
       '.cw-modal .cw-ms{margin:0 0 10px;color:#3a3a3a;font-size:.95em}.cw-modal ul{margin:0 0 10px;padding-left:1.2em}.cw-modal li'
       '{margin:.5em 0}.cw-modal li a{color:#8a5300;font-weight:700;text-decoration:underline dotted 1.5px;text-underline-offset:3px}'
       '.cw-modal .cw-md{color:#666;font-size:.82em;margin-left:.3em}.cw-modal .cw-ol{display:block;color:#444;font-size:.88em}'
       '.cw-modal .cw-mf a{color:#141414;font-weight:600}.cw-x{position:absolute;top:6px;right:6px;width:44px;height:44px;border:0;'
       'background:transparent;color:#141414;font-size:28px;line-height:1;cursor:pointer;border-radius:22px}.cw-x:focus-visible'
       '{outline:2px solid #141414}@media (hover:hover) and (pointer:fine){.cw-modal .cw-ol{display:none}}'
       '.cw-legend{font:400 11px/1.4 system-ui,-apple-system,sans-serif;opacity:.72;margin:10px 12px;padding:0;text-align:left}'
       '.cw-legend a{color:inherit}.cw-legend .cw-lg-n{background:rgba(214,145,0,.14);text-decoration:underline dotted 2px #c98200}'
       '.cw-legend .cw-lg-g{text-decoration:underline dotted 1.5px}</style>')
JS = '<script src="/_cedwyn/wiki.js?v=1" defer></script><script src="/_cedwyn/glossary-modal.js?v=1.0.0" defer></script>'
LEGEND = ('<p class="cw-legend" data-cw-legend>Small print: <span class="cw-lg-g">dotted links</span> explain a word (see the '
          '<a href="/glossary/">glossary</a>); <span class="cw-lg-n">amber-shaded links</span> list every name the records use for '
          'the same thing.</p>')

def inject(t):
    if 'id="cw-wiki-css"' not in t:
        add = CSS + ('' if '/_cedwyn/wiki.js' in t else JS)
        i = t.lower().find('</head>')
        t = (t[:i] + add + t[i:]) if i >= 0 else add + t
    if 'data-cw-legend' not in t:
        i = t.lower().rfind('</body>')
        t = (t[:i] + LEGEND + t[i:]) if i >= 0 else t + LEGEND
    return t

def _clamp_head():
    # three-line "read more" / "less" (Sion, 23:32 GMT 26 Oct 2026): the glossary is written after headlines.run - Sion's Tab agent
    try:
        import headlines
        return headlines.CSS + headlines.JS
    except Exception:
        return '<script src="/_cedwyn/clamp.js?v=1" defer></script>'

def glossary_page(g, n):
    ents = []
    for t in g['terms']:
        ents.append((t['term'], t['slug'], t['definition'], t['learn_more'], None))
    for grp in n['groups']:
        pv = [v for v in grp['variants'] if v.get('public')]
        ents.append((grp['name'], 'name-' + grp['id'], grp['summary'], [{'label': 'Every name and its record', 'url': grp['url']}], (grp, pv)))
    ents.sort(key=lambda e: re.sub(r'[^a-z0-9]', '', e[0].lower().replace('ŷ', 'y').replace('ŵ', 'w')))
    letters = []
    body = []
    cur = None
    for term, slug, d, lm, grp in ents:
        L = re.sub(r'[^A-Z]', '', term.upper().replace('Ŷ', 'Y').replace('Ŵ', 'W'))[:1] or '#'
        if L != cur:
            cur = L; letters.append(L); body.append('<h2 class="gl-l" id="l-%s">%s</h2>' % (L, L))
        s = ['<section class="gl-e" id="%s"><h3>%s</h3><p class="gl-d">%s</p>' % (slug, ESC(term), ESC(d))]
        if lm or grp:
            s.append('<div class="gl-more">')   # no "Learn more" fold (Sion, 23:32 GMT 26 Oct 2026): on show; clamp.js crops long text - Sion's Tab agent
            if lm:
                s.append('<ul class="gl-lm">' + ''.join('<li><a href="%s">%s</a></li>' % (ESC(x['url']), ESC(x['label'])) for x in lm) + '</ul>')
            if grp:
                gr, pv = grp
                s.append('<p><a class="cw-n" href="%s" data-n="%s" data-tip="%s" aria-haspopup="dialog">Show every name in one list</a></p>' % (
                    ESC(gr['url']), gr['id'], ESC('%s: %d names in the records' % (gr['name'], len(pv)))))
                s.append('<ul class="gl-v">')
                for v in pv:
                    meta = ' · '.join(x for x in (v.get('first_record'), v.get('source_id')) if x)
                    nm = ('<a href="%s" data-tip="%s">%s</a>' % (ESC(v['url']), ESC(v['variant'] + ' — ' + v['one_liner']), ESC(v['variant']))) if v.get('url') else ESC(v['variant'])
                    s.append('<li>%s%s<br><span class="gl-ol">%s</span></li>' % (nm, (' <span class="gl-m">%s</span>' % ESC(meta)) if meta else '', ESC(v['one_liner'])))
                s.append('</ul>')
            s.append('</div>')
        s.append('</section>')
        body.append(''.join(s))
    az = ''.join('<a href="#l-%s">%s</a>' % (L, L) for L in letters)
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Glossary · the words of the Tŷ Mawr story · Cedwyn</title><meta name="description" content="Plain-English meanings of the '
            'legal, land and records words used across Cedwyn, and every name the records use for the same place or body.">'
            '<link rel="canonical" href="https://cedwyn.bucklerfamily.estate/glossary/"><link rel="alternate" type="application/json" '
            'href="/_cedwyn/glossary.json"><style>body{margin:0;background:#f6f3ee;color:#161616;font:400 17px/1.5 system-ui,-apple-system,'
            '"Segoe UI",Roboto,sans-serif}.gl{max-width:760px;margin:0 auto;padding:22px 18px 40px}.gl-top a{color:inherit;font-weight:600;'
            'text-decoration:none}.gl h1{font-size:clamp(2.1rem,9vw,3.4rem);line-height:1.02;margin:18px 0 8px;letter-spacing:-.02em}'
            '.gl-in{font-size:1.15em;margin:0 0 16px;color:#333}.gl-az{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 18px}.gl-az a{display:'
            'inline-flex;align-items:center;justify-content:center;min-width:40px;min-height:40px;border-radius:20px;background:#161616;'
            'color:#fff;font-weight:700;text-decoration:none}.gl-l{font-size:1.9em;margin:26px 0 4px;border-bottom:3px solid #161616}'
            '.gl-e{padding:12px 0 6px;border-bottom:1px solid #ddd5c8}.gl-e h3{font-size:1.35em;margin:0 0 4px;line-height:1.2}.gl-d{margin:0 0 8px;'
            'font-size:1.05em}.gl-lm,.gl-v{margin:6px 0 8px;padding-left:1.2em}.gl-lm li,.gl-v li{margin:.45em 0}.gl a{color:#5a3a00}'
            '.gl-m{color:#666;font-size:.85em}.gl-ol{color:#444;font-size:.92em}.cw-more{margin:.2em 0 .9em}.cw-more>summary{cursor:pointer;'
            'display:inline-flex;align-items:center;gap:.4em;min-height:44px;padding:0 16px;border:1px solid currentColor;border-radius:999px;'
            'font-weight:600;font-size:.92em;list-style:none}.cw-more>summary::-webkit-details-marker{display:none}.cw-more>summary::after{'
            'content:"\\25BE"}.cw-more[open]>summary::after{content:"\\25B4"}.cw-less{min-height:40px;padding:0 14px;border-radius:999px;'
            'border:1px dashed currentColor;background:transparent;color:inherit;font:inherit;font-size:.88em;cursor:pointer;margin:4px 0}.cw-less[hidden]{display:none}'
            '</style><noscript><style>details.cw-more::details-content{content-visibility:visible;display:block}details.cw-more>summary'
            '{display:none}</style></noscript><script src="/_cedwyn/runtime.js?v=13" defer></script><script src="/_cedwyn/glossary-modal.js?v=1.0.0" defer></script>' + _clamp_head() + '</head><body><main class="gl">'
            '<p class="gl-top"><a href="/">‹ Cedwyn</a></p><h1>The words of the story</h1><p class="gl-in">New here? Every legal, land '
            'and records word on Cedwyn, in one line each. Each one links on, all the way to the record itself.</p>'
            '<nav class="gl-az" aria-label="A to Z">' + az + '</nav>' + ''.join(body) + '</main></body></html>')


# Agent text out of human view (Sion, 22:12 GMT 26 Oct 2026: "Don't make humans viewing the webpage see agent instructions").
# The blocks stay in the page source for agents (hidden + data-for-agents) and the head points agents to /llms.txt.
# Shared agent footer (root steer 22:33 GMT): its visible content (change log, agent rules, THE TRIGGER EVENT note) becomes one
# small-print "For agents" link (/academy/ once that page exists in the build, else /llms.txt); the footer text stays in the source,
# and pages without the build-time footer get the same footer here so the edge copy is not added on top. The head
# <meta name="agent-instruction"> and its JSON-LD are kept exactly as the footer tool writes them (held for the owner).
AGENT_BLOCK = re.compile(r'<(section|div|details|aside|p)\b(?=[^>]*(?:\bid="cedwyn-guestbook"|\bclass="[^"]*\b(?:ghf-ai-agent-routing|gaf-ai)\b))([^>]*)>', re.I)
AGENT_CSS = '<style id="cw-agents-css">[data-for-agents]{display:none!important}</style><link rel="alternate" type="text/plain" href="/llms.txt" title="For AI agents">'
GAF_IN = '<div class="gaf-in">'
_FOOT = {}
def _footer_snips():
    if not _FOOT:
        d = ROOT / 'tools' / 'agent_footer'
        try: _FOOT['footer'] = (d / 'footer.html').read_text(encoding='utf-8'); _FOOT['head'] = (d / 'head.html').read_text(encoding='utf-8')
        except Exception: _FOOT['footer'] = _FOOT['head'] = ''
    return _FOOT
def _small_footer(t, href):
    link = '<p class="gaf-agents"><a href="/library/">Docs</a></p>'   # no visible "For agents" link on human pages (27 Oct 2026); agents find /academy/ via head tags, robots.txt, /llms.txt, /agents.json
    # fold the footer's own block: on /projects/ the visible TRIGGER EVENT section has an earlier gaf-in that must stay visible
    gi = t.find(GAF_IN, max(0, t.find('<footer id="ghf-agent-footer"')))
    if gi < 0: return t
    return t[:gi] + link + '<div class="gaf-in" hidden data-for-agents>' + t[gi + len(GAF_IN):]
def hide_agent_text(t, href='/llms.txt'):
    n = [0]
    def rep(m):
        if 'data-for-agents' in m.group(2) or 'trigger' in m.group(2).lower(): return m.group(0)
        n[0] += 1
        return '<%s%s hidden data-for-agents>' % (m.group(1), m.group(2).rstrip('/'))
    t = AGENT_BLOCK.sub(rep, t)
    if 'id="ghf-agent-footer"' in t:
        if GAF_IN in t and 'class="gaf-agents"' not in t: t = _small_footer(t, href); n[0] += 1
    elif 'id="trigger-event"' not in t:
        s = _footer_snips()
        if s['footer'] and GAF_IN in s['footer']:
            i = t.lower().rfind('</body>')
            if i >= 0:
                t = t[:i] + _small_footer(s['footer'], href) + t[i:]; n[0] += 1
                if s['head'] and 'name="agent-instruction"' not in t:
                    j = t.lower().find('</head>')
                    if j >= 0: t = t[:j] + s['head'] + t[j:]
    if n[0] and 'id="cw-agents-css"' not in t:
        i = t.lower().find('</head>')
        t = (t[:i] + AGENT_CSS + t[i:]) if i >= 0 else AGENT_CSS + t
    return t, n[0]

def run(dist):
    dist = pathlib.Path(dist)
    g, n, rx, lookup = load()
    rep = {'pages': 0, 'glossary_links': 0, 'name_links': 0, 'themes': {}, 'terms': len(g['terms']),
           'name_groups': len(n['groups']), 'variants': sum(len(x['variants']) for x in n['groups']),
           'public_variants': sum(1 for x in n['groups'] for v in x['variants'] if v.get('public'))}
    (dist / '_cedwyn').mkdir(parents=True, exist_ok=True)
    pub = {'version': n['version'], 'groups': {x['id']: {'name': x['name'], 'summary': x['summary'], 'url': x['url'],
           'variants': [{k: v.get(k) for k in ('variant', 'first_record', 'source_id', 'one_liner', 'url')} for v in x['variants'] if v.get('public')]}
           for x in n['groups']}}
    (dist / '_cedwyn' / 'nomenclature.json').write_text(json.dumps(pub, ensure_ascii=False), encoding='utf-8')
    (dist / '_cedwyn' / 'glossary.json').write_text(json.dumps({'version': g['version'], 'terms': [
        {k: t[k] for k in ('slug', 'term', 'definition', 'anchor', 'learn_more')} for t in g['terms']]}, ensure_ascii=False), encoding='utf-8')
    gp = dist / 'glossary' / 'index.html'; gp.parent.mkdir(parents=True, exist_ok=True)
    gp.write_text(glossary_page(g, n), encoding='utf-8')
    agents_href = '/academy/' if (dist / 'academy' / 'index.html').exists() else '/llms.txt'
    rep['agents_link'] = agents_href
    for f in sorted(dist.rglob('*.html')):
        rel = f.relative_to(dist).as_posix()
        if rel in SKIP_FILES or rel.startswith(SKIP_DIRS) or '/_cedwyn/' in rel: continue
        try:
            if f.stat().st_size > 3_000_000: continue
            t = f.read_text(encoding='utf-8', errors='surrogateescape')
        except Exception: continue
        t2, hid = hide_agent_text(t, agents_href)
        if hid: rep['agent_blocks_hidden'] = rep.get('agent_blocks_hidden', 0) + hid; rep['agent_pages'] = rep.get('agent_pages', 0) + 1
        st = {'g': 0, 'n': 0}; out = t2
        if not ('data-cw-wiki-off' in t or 'class="cw-g"' in t or 'class="cw-n"' in t or re.search(r'<div id="(root|app)">\s*</div>', t)):
            try: out, st = process(t2, rx, lookup)
            except Exception as ex:
                print('wikilinks: skipped', rel, str(ex)[:80]); out = t2
        if st['g'] or st['n']:
            out = inject(out)
            rep['pages'] += 1; rep['glossary_links'] += st['g']; rep['name_links'] += st['n']
            th = rel.split('/')[0] if '/' in rel else '(root)'; rep['themes'][th] = rep['themes'].get(th, 0) + 1
        if out != t: f.write_text(out, encoding='utf-8', errors='surrogateescape')
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'wikilinks.json', 'w'), indent=1)
    print('wikilinks:', rep['pages'], 'pages,', rep['glossary_links'], 'glossary links,', rep['name_links'], 'name links;',
          rep['terms'], 'terms,', rep['public_variants'], 'public name variants')
    return rep

if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
