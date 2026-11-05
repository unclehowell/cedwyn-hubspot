#!/usr/bin/env python3
"""page_journal.py 1.1.0 - a short dated journal of each page's OWN changes, inline in that page's footer area.
1.1.0 (31 Oct 2026, site audit: the footer changelog was missing on ~3,100 of ~8,900 pages): footer_pass() runs first, on EVERY
HTML page of the build (this step runs after site.py and selfcontain, so it sees every page any tool wrote): a page without the shared
agent footer gets it (tools/agent_footer/footer.html, folded in the closed "Page versions & agent info" disclosure, agent text hidden
for humans exactly as wikilinks.hide_agent_text does), a page without the guest-book shell gets it (gb.js shows the page's own versions),
and an older footer version is swapped for the current one only when its THE TRIGGER EVENT section is byte-identical (else kept and
reported). Journal entries may carry "agent" (the signing agent's name), shown as the signature. Report keys: footer_*.
Owner, 30 Oct 2026 14:50 GMT: journal the page changes on the footer of each page. ADR-002 item 7 (work/cedwyn-data-arch/PLAN.md).
Sources (data, never hand-edited HTML):
  data/journal/pages.json            {"/path/": [{"v": "2.0.1", "date": "YYYY-MM-DD", "note": "neutral change line"}, ...]}
  <dist>/<app>/_db/view.json         records of data-driven apps: each record page lists its record's 'changes'
                                     ([{date, rev, note}]) or, when none are recorded, its revision and date.
Writes one <details id="cedwyn-journal"> block before </body> of each page that has entries (no extra files: the host's
file cap), newest first, at most 6 lines, neutral wording only. Never fails the build. Report: _cedwyn/reports/page_journal.json.
Usage: python3 tools/page_journal.py dist  - Cedwyn editors"""
import json, sys, html, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
MAX = 6
STYLE = ('<style id="cedwyn-journal-css">#cedwyn-journal{max-width:960px;margin:24px auto 8px;padding:0 16px;font:12px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;opacity:.72;color:inherit}'
         '#cedwyn-journal summary{cursor:pointer;letter-spacing:.06em;text-transform:uppercase;font-size:11px}#cedwyn-journal ol{margin:6px 0 0;padding-left:18px}'
         '#cedwyn-journal li{margin:2px 0}#cedwyn-journal b{font-weight:600}</style>')
def _who(e):
    a = str(e.get('agent') or '').strip()
    return (' · <span class="cw-j-who">agent: %s</span>' % html.escape(a)) if a else ''
def block(entries):
    rows = ''.join('<li><b>%s</b> · %s — %s%s</li>' % (html.escape(str(e.get('v') or '')), html.escape(str(e.get('date') or '')), html.escape(str(e.get('note') or '')), _who(e))
                   for e in entries[:MAX])
    return STYLE + '<details id="cedwyn-journal" class="cw-journal"><summary>Page journal</summary><ol>' + rows + '</ol></details>'
def page_file(dist, path):
    p = dist / path.strip('/')
    return p / 'index.html' if not path.endswith('.html') else p
def entries_from_view(app, vj):
    out = {}
    for rows in (vj.values() if isinstance(vj, dict) else []):
        if not isinstance(rows, list): continue
        for r in rows:
            if not isinstance(r, dict) or not r.get('slug'): continue
            ch = r.get('changes') or []
            es = [{'v': 'rev %s' % c.get('rev', ''), 'date': c.get('date', ''), 'note': c.get('note', '')} for c in ch if c.get('note')]
            if not es and r.get('updated'):
                es = [{'v': ('rev %s' % r['rev']) if r.get('rev') else r.get('id', ''), 'date': r.get('updated'), 'note': 'Card last revised in the central catalogue.'}]
            if es: out['/%s/%s/' % (app, r['slug'])] = es
    return out

# ---- footer_pass (1.1.0): the folded, signable footer changelog on every page ------------------------------------------------
SKIP = ('_cedwyn/', '_ext/', '_blob/', 'db/')
FOOT_RX = re.compile(r'<footer id="ghf-agent-footer"[^>]*>.*?</footer>', re.S)
TRIG_RX = re.compile(r'<section class="gaf-trigger".*?</section>', re.S)
def _pages(dist):
    for p in dist.rglob('*.htm*'):
        if not p.is_file(): continue
        rel = p.relative_to(dist).as_posix()
        if rel.startswith(SKIP) or '/_db/' in rel or '/_cedwyn/' in rel: continue
        yield p, rel
def footer_pass(dist, rep):
    sys.path.insert(0, str(ROOT / 'tools'))
    import wikilinks, guestbook
    snip = (ROOT / 'tools' / 'agent_footer' / 'footer.html').read_text(encoding='utf-8')
    head = (ROOT / 'tools' / 'agent_footer' / 'head.html').read_text(encoding='utf-8')
    cur = re.search(r'data-agent-footer="([^"]+)"', snip).group(1)
    cur_el = FOOT_RX.search(snip).group(0); cur_trig = TRIG_RX.search(cur_el).group(0)
    small = wikilinks._small_footer(snip, '/academy/')
    shell = guestbook.shell()
    c = {'footer_version': cur, 'footer_added': 0, 'footer_upgraded': 0, 'footer_stale_kept': [], 'footer_gb_added': 0, 'footer_skipped': 0}
    for p, rel in _pages(dist):
        try: t = p.read_text(encoding='utf-8', errors='surrogateescape')
        except Exception: continue
        low = t.lower(); o = t
        if '<body' not in low and '<html' not in low: c['footer_skipped'] += 1; continue           # a fragment, not a page
        if re.search(r'<meta[^>]+http-equiv\s*=\s*["\']?refresh', low) and len(t) < 2000: c['footer_skipped'] += 1; continue   # redirect stub
        m = FOOT_RX.search(t)
        if m:
            v = re.search(r'data-agent-footer="([^"]+)"', m.group(0)[:400])
            if v and v.group(1) != cur:
                ot = TRIG_RX.search(m.group(0))
                if ot and ot.group(0) == cur_trig:
                    el = cur_el
                    if 'class="gaf-agents"' in m.group(0):   # keep the page's form: agent text hidden from humans as before
                        el = wikilinks._small_footer(cur_el, '/academy/')
                    t = t[:m.start()] + el + t[m.end():]; c['footer_upgraded'] += 1
                else: c['footer_stale_kept'].append('/' + rel)
        elif 'id="trigger-event"' not in t:
            i = t.lower().rfind('</body>')
            if i < 0: i = t.lower().rfind('</html>')
            t = (t[:i] + small + t[i:]) if i >= 0 else t + small
            if 'name="agent-instruction"' not in t:
                j = t.lower().find('</head>')
                if j >= 0: t = t[:j] + head + t[j:]
            if 'id="cw-agents-css"' not in t:
                j = t.lower().find('</head>')
                if j >= 0: t = t[:j] + wikilinks.AGENT_CSS + t[j:]
            c['footer_added'] += 1
        if 'id="cedwyn-guestbook"' not in t:
            i = t.lower().rfind('</body>')
            if i < 0: i = t.lower().rfind('</html>')
            t = (t[:i] + shell + t[i:]) if i >= 0 else t + shell
            c['footer_gb_added'] += 1
        if t != o: p.write_text(t, encoding='utf-8', errors='surrogateescape')
    c['footer_stale_kept'] = c['footer_stale_kept'][:50]
    rep.update(c)
    print('page_journal footer_pass:', json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in c.items()}))

def run(dist):
    dist = pathlib.Path(dist); rep = {'pages': 0, 'missing': [], 'sources': {}}
    try: footer_pass(dist, rep)
    except Exception as e: print('::warning::page_journal footer_pass did not complete:', e)
    J = {}
    try: J.update({k: list(v) for k, v in json.load(open(ROOT / 'data/journal/pages.json', encoding='utf-8')).get('pages', {}).items()})
    except Exception as e: print('page_journal: no pages.json', e)
    rep['sources']['pages.json'] = len(J)
    for vf in sorted((ROOT / 'data/views').glob('*.view.json')):
        app = vf.name[:-len('.view.json')]; db = dist / app / '_db' / 'view.json'
        if not db.exists(): continue
        try:
            got = entries_from_view(app, json.load(open(db, encoding='utf-8')))
            for k, v in got.items(): J.setdefault(k, []).extend(v)
            rep['sources'][app] = len(got)
        except Exception as e: print('page_journal', app, 'failed', e)
    for path, es in J.items():
        es = sorted(es, key=lambda e: (str(e.get('date') or ''), str(e.get('v') or '')), reverse=True)
        f = page_file(dist, path)
        if not f.exists(): rep['missing'].append(path); continue
        t = f.read_text('utf-8', 'ignore')
        t = re.sub(r'<style id="cedwyn-journal-css">.*?</style><details id="cedwyn-journal".*?</details>', '', t, flags=re.S)
        i = t.lower().rfind('</body>')
        t = (t[:i] + block(es) + t[i:]) if i >= 0 else t + block(es)
        f.write_text(t, 'utf-8'); rep['pages'] += 1
    try:
        (dist / '_cedwyn' / 'reports').mkdir(parents=True, exist_ok=True)
        (dist / '_cedwyn' / 'reports' / 'page_journal.json').write_text(json.dumps(rep, indent=1))
    except Exception: pass
    print('page_journal 1.1.0:', json.dumps({k: (v if k != 'missing' else len(v)) for k, v in rep.items()}))
    return rep
if __name__ == '__main__':
    try: run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
    except Exception as e: print('::warning::page_journal did not complete:', e)
