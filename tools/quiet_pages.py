#!/usr/bin/env python3
"""quiet_pages.py - human pages never explain themselves.
Notes that describe the page, the site, its data sources, its build or its agents ("This page shows ...", "Machine-readable
index · Agent reading guide", "About this page type -> Read the Docs", "For AI agents ...", signatures of the agent that built a
page) are moved out of human view: the element gets `hidden data-for-agents` (still in the page source for agents, as agent small
print), or, when such a sentence opens a paragraph that goes on with record content, only that sentence is wrapped in a hidden span.
No wording is changed or deleted. How the site works is documented in the developer library at /library/.
Also adds a small 'Docs' link (-> /library/) beside the small-print 'For agents' link in the shared footer.
Skips the landing page, /ebooks/, archived mail and third-party captures, the database, /academy/ and /library/.
Report: dist/_cedwyn/reports/quiet_pages.json. Usage: python3 tools/quiet_pages.py dist  (site.py calls it last) - docs library build, 27 Oct 2026"""
import json, pathlib, re, sys
SKIP_FILES = {'index.html'}
SKIP_DIRS = ('wayback/mail/', 'wayback/websites/', '_ext/', 'db/', '_blob/', 'academy/', 'library/', '_cedwyn/')   # never touched
TEXT_SKIP = ('ebooks/', 'email/', 'emails/', 'wdtk/', 'wayback/', 'guestbook/', 'graphql/', 'catalogue/')   # footer only: archived records stay verbatim
GAF_IN = '<div class="gaf-in">'
AP = "(?:[\u2019']|&#39;|&#x27;|&rsquo;|&apos;)"
# whole-element notes (matched against the element's visible text)
WHOLE = [re.compile(p, re.I) for p in (
    r'^machine-readable\b', r'^ai agent entry point\b', r'^(about this page type|what this page is about)\s*(\u2192|->)\s*read the docs\s*\.?$',
    r'^for ai agents\b', r'^agent roles\s*\u2014', r'^agent reading guide\b', r'^agent index\b',
    r'^[\u2014\u2013-]\s*sion' + AP + r's tab agent\.?$', r'^(template )?(prepared|built|made|compiled|maintained) by sion' + AP + r's tab agent\.?$',
    r'^new here\?\s', r'^this page sets out words, framing and timing\b',
    r'^tap agent at the bottom right\b',   # chat UI help line (owner decision 27 Oct)
)]
# a leading self-description sentence inside a paragraph that continues with content
LEAD = re.compile(r'^(\s*)((?:This page|These pages|This index|This section|This site|This theme|This register)\s(?:isolates|tracks|shows|lists|collects|gathers|'
                  r'brings together|describes|explains|sets out|presents|records|is built|was built|holds|keeps|follows|maps)\b[^<]{0,400}?\.)(\s)', re.S)
# inline phrases (text only, never inside tags or scripts)
PHRASES = [re.compile(p) for p in (
    r'\s*[\u2014\u2013]\s*Sion' + AP + r's Tab agent\b\.?',
    r'\s*(?:Template prepared|Built|Prepared|Made|Compiled|Maintained) by Sion' + AP + r's Tab agent\.?',
    r'Programme Office flywheel \u00b7 reviewed weekly \u00b7 last review [0-9-]+ \u00b7 maintained by an agent of the estate\.\s*',
    r'Record each event as more evidence only for the specific proposition it actually supports;\s*',   # editor instruction (research timeline)
)]
LEAF = re.compile(r'<(p|small|em|span|li|div|figcaption|aside)(\s[^>]*)?>((?:(?!<(?:p|div|section|ul|ol|table|article|aside|figure|header|footer|main|nav)\b)(?!</\1>).){8,1600}?)</\1>', re.S | re.I)
TAGS = re.compile(r'<[^>]+>'); WS = re.compile(r'\s+')
SPLIT = re.compile(r'(<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->|<[^>]+>)', re.S | re.I)
CONT = re.compile(r'<(section|div|aside|details|p)\b((?=[^>]*\b(?:id="(?:agent-access|page-version-log|webmcp-status)"|class="[^"]*\b(?:ghf-version-log|ai-sign|agent-access|ghf-page-header)\b))[^>]*)>', re.I)
def cont(m):
    if 'data-for-agents' in m.group(2): return m.group(0)
    return '<%s%s hidden data-for-agents>' % (m.group(1), m.group(2).rstrip('/'))
CSS = '<style id="cw-agents-css">[data-for-agents]{display:none!important}</style>'
DOCS = ' \u00b7 <a href="/library/">Docs</a>'
import html as H
def vis(s): return WS.sub(' ', H.unescape(TAGS.sub(' ', s))).strip()
def process(t, rep, rel, text_ok=True):
    n = 0
    def leaf(m):
        nonlocal n
        tag, attrs, inner = m.group(1), m.group(2) or '', m.group(3)
        if 'data-for-agents' in attrs or ' hidden' in attrs: return m.group(0)
        tx = vis(inner)
        if not (8 <= len(tx) <= 700): return m.group(0)
        for rx in WHOLE:
            if rx.search(tx):
                n += 1; rep.setdefault('samples', []).append([rel, tx[:120]]) if len(rep.get('samples', [])) < 400 else None
                return '<%s%s hidden data-for-agents>%s</%s>' % (tag, attrs.rstrip('/'), inner, tag)
        if tag.lower() == 'p':
            lm = LEAD.match(inner)
            if lm and len(vis(inner[lm.end():])) > 40:
                n += 1; rep.setdefault('samples', []).append([rel, 'lead: ' + vis(lm.group(2))[:110]]) if len(rep.get('samples', [])) < 400 else None
                return '<%s%s>%s<span hidden data-for-agents>%s</span>%s%s</%s>' % (tag, attrs, lm.group(1), lm.group(2), lm.group(3), inner[lm.end():], tag)
        return m.group(0)
    parts = SPLIT.split(t); out = []; inside_hidden = 0
    # 1) phrase pass on text tokens only
    for p in parts:
        if text_ok and p and not p.startswith('<'):
            q = p
            for rx in PHRASES:
                q = rx.sub(lambda m: '<span hidden data-for-agents>%s</span>' % m.group(0), q)
            if q != p: n += 1
            out.append(q)
        else: out.append(p)
    t = ''.join(out)
    # 2) element pass, outside scripts/styles
    segs = re.split(r'(<script\b.*?</script>|<style\b.*?</style>|<footer id="ghf-agent-footer".*?</footer>|<[a-z]+[^>]*\bdata-for-agents[^>]*>)', t, flags=re.S | re.I)
    nb = t.count('data-for-agents')
    t = ''.join(s if s[:7].lower() == '<script' or s[:6].lower() == '<style' or s.startswith('<footer id="ghf-agent-footer"') or 'data-for-agents' in s[:400] and s.startswith('<') else CONT.sub(cont, LEAF.sub(leaf, s) if text_ok else s) for s in segs)
    n += max(0, t.count('data-for-agents') - nb - n)
    return t, n
def run(dist):
    dist = pathlib.Path(dist); rep = {'pages': 0, 'notes_hidden': 0, 'docs_links': 0}
    for f in sorted(dist.rglob('*.html')):
        rel = f.relative_to(dist).as_posix()
        if rel in SKIP_FILES or rel.startswith(SKIP_DIRS): continue
        try:
            if f.stat().st_size > 3_000_000: continue
            t = f.read_text(encoding='utf-8', errors='surrogateescape')
        except Exception: continue
        o = t; n = 0
        if not (rel.startswith(TEXT_SKIP) and rel != 'wayback/index.html'):
            t, n = process(t, rep, rel, not re.search(r'<div id="(root|app)">\s*</div>', t))
        if 'id="ghf-agent-footer"' in t and GAF_IN in t and 'class="gaf-agents"' not in t:
            # fold the footer's own block (on /projects/ the visible TRIGGER EVENT section has an earlier gaf-in that must stay visible)
            gi = t.find(GAF_IN, max(0, t.find('<footer id="ghf-agent-footer"')))
            if gi >= 0:
                t = t[:gi] + '<p class="gaf-agents"><a href="/library/">Docs</a></p><div class="gaf-in" hidden data-for-agents>' + t[gi + len(GAF_IN):]; n += 1
            rep['footers_folded'] = rep.get('footers_folded', 0) + 1
        # no visible "For agents" link on human pages (27 Oct 2026): drop any baked-in one; agents use the hidden head tags below
        t = re.sub(r'(<p class="gaf-agents">)<a href="[^"]*">For agents</a>(?:\s*\u00b7\s*)?', r'\1', t)
        if 'class="gaf-agents"' in t and '/library/' not in t:
            t = t.replace('<p class="gaf-agents">', '<p class="gaf-agents">' + DOCS.lstrip(' \u00b7'), 1); rep['docs_links'] += 1
        if 'id="ghf-agent-footer"' in t and 'href="/agents.json"' not in t:   # hidden machine discovery in <head> (pages rebuilt after academy_pointer)
            try:
                from academy_pointer import TAG as AP_TAG
                i = t.lower().find('</head>')
                if i >= 0: t = t[:i] + AP_TAG + t[i:]
            except Exception: pass
        if n:
            rep['pages'] += 1; rep['notes_hidden'] += n
            if 'id="cw-agents-css"' not in t:
                i = t.lower().find('</head>'); t = (t[:i] + CSS + t[i:]) if i >= 0 else CSS + t
        if t != o: f.write_text(t, encoding='utf-8', errors='surrogateescape')
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'quiet_pages.json', 'w'), indent=1, ensure_ascii=False)
    print('quiet_pages:', rep['pages'], 'pages,', rep['notes_hidden'], 'notes moved to agent small print,', rep['docs_links'], 'footer Docs links')
    return rep
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
