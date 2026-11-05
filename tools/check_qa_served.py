#!/usr/bin/env python3
"""check_qa_served.py - post-deploy STATIC served-HTML check for the interactive Q&A pages.

Layer honesty: this checks the HTML the server returns (curl-equivalent plus stdlib HTMLParser).
It does NOT execute JavaScript, so it cannot see runtime collapse (cw-graph.js cwl cards). The
rendered-layer checks (visible chips, search/filter round trips, zero .cwl-card) are a separate
manual/agent browser runbook in the HubSpot acceptance template; there is no automatic visual
gate in the pipeline today (CI has node for syntax/unit tests but no browser automation).

Expectations are derived at run time from the authoritative source data, never frozen counts,
and PINNED to the published revision so they cannot race a moving main branch:
  - data/qa/questions-base.json at the commit named by the site's published build stamp
    (<base>/_cedwyn/reports/build.json, written by the build workflow from $GITHUB_SHA - the
    main commit the build ran from, which is the ref raw source fetches need), or an explicit
    --ref / --base-file override;
  - the mail catalogue <base>/email/view/index.json - same origin and normally the same deploy
    as the Q&A pages, but NOT a guaranteed atomic snapshot (CDN caching can skew it); the atomic
    exact comparison is the build-time layer, tools/check_qa_built.py;
recomputed through tools/qa_questions.py's own build() - the same code that renders the pages.
Uniform truncation of every alias fails because the truth comes from the source, not the site.

Parsing is structural (html.parser), not substring matching: article IDs are compared as exact
multisets (duplicate IDs fail), chip labels as exact per-question multisets ('#AB' never matches
'#ABC'), and the class="tg" total counts actual elements.

Fails closed (exit 1): unreachable alias or source, missing build stamp without --ref, empty
source data, missing opt-out attributes, any ID/chip multiset mismatch, wrong .tg total.

Usage: python3 tools/check_qa_served.py [base-url] [--ref COMMIT] [--base-file F] [--index-file F]
CHECK_QA_RAW_BASE env var overrides the raw-source URL template (used by the test runner)."""
import argparse, json, os, pathlib, re, sys, urllib.request
from collections import Counter
from html.parser import HTMLParser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qa_questions import build   # the same derivation the renderer uses

ALIASES = ('/qa/', '/wales/qa/', '/argentina/qa/')
RAW_BASE = os.environ.get('CHECK_QA_RAW_BASE',
                          'https://raw.githubusercontent.com/unclehowell/cedwyn/%s/data/qa/questions-base.json')
STAMP = '/_cedwyn/reports/build.json'

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'check-qa-served/1.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore')

class QAPage(HTMLParser):
    """Structural parse: ordered article.q IDs (duplicates visible), per-article chip labels, .tg element total."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.articles = []
        self.tg_total = 0
        self._art = None
        self._chips = None
        self._cap = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get('class') or '').split()
        if tag == 'article' and 'q' in cls and a.get('id') and self._art is None:
            self._art = a['id']; self._chips = []
        if 'tg' in cls:
            self.tg_total += 1
            if self._art is not None and self._cap is None:
                self._cap = [tag, 1, []]
            elif self._cap is not None and self._cap[0] == tag:
                self._cap[1] += 1
    def handle_endtag(self, tag):
        if self._cap is not None and tag == self._cap[0]:
            self._cap[1] -= 1
            if self._cap[1] == 0:
                self._chips.append(''.join(self._cap[2]).strip())
                self._cap = None
        if tag == 'article' and self._art is not None:
            self.articles.append((self._art, self._chips or []))
            self._art = None; self._chips = None
    def handle_data(self, data):
        if self._cap is not None:
            self._cap[2].append(data)

def expected_totals(qs):
    chips = sum(len(x['asked_by']) + len(x['answered_by']) for x in qs)
    legend = len({a['tag'] for x in qs for a in x['asked_by']})
    return chips + legend

def page_problems(name, html_text, qs):
    """Static served-HTML problems for one Q&A page against the expected question list."""
    problems = []
    htmltag = (re.search(r'<html\b[^>]*>', html_text) or [''])[0]
    if not ('data-cw-noclip' in htmltag and 'data-cw-nolevels' in htmltag):
        problems.append('%s: missing data-cw-noclip/data-cw-nolevels on <html>' % name)
    page = QAPage()
    page.feed(html_text)
    got = Counter(qid for qid, _ in page.articles)
    want = Counter('q-' + x['id'][:70] for x in qs)   # renderer writes E(id[:70]); the parser decodes entities back, so compare RAW
    dups = sorted(q for q, n in got.items() if n > 1)
    if dups:
        problems.append('%s: duplicate question ID(s) served: %s' % (name, ', '.join(dups[:3])))
    missing = sorted((want - got).elements())
    extra = sorted((got - want).elements())
    if missing:
        problems.append('%s: %d expected question(s) not served, e.g. %s' % (name, len(missing), ', '.join(missing[:3])))
    if extra:
        problems.append('%s: %d served question(s) not in source data, e.g. %s' % (name, len(extra), ', '.join(extra[:3])))
    amap = {}
    for qid, chips in page.articles:
        amap.setdefault(qid, chips)
    for x in qs:
        qid = 'q-' + x['id'][:70]   # raw: E() round-trips through the parser's entity decoding
        if qid not in amap:
            continue
        w = Counter('#' + a['tag'] for a in x['asked_by'] + x['answered_by'])
        g = Counter(amap[qid])
        if g != w:
            short = ['%s x%d served, x%d expected' % (t, g.get(t, 0), n) for t, n in w.items() if g.get(t, 0) != n]
            extra_c = ['%s x%d unexpected' % (t, g[t]) for t in g if t not in w]
            problems.append('%s: %s chip mismatch: %s' % (name, qid, ', '.join((short + extra_c)[:4])))
    want_tg = expected_totals(qs)
    if page.tg_total != want_tg:
        problems.append('%s: %d class="tg" elements served, expected %d (chips + legend)' % (name, page.tg_total, want_tg))
    return problems

def main():
    ap = argparse.ArgumentParser(description='Post-deploy static served-HTML check for the Q&A pages.')
    ap.add_argument('base_url', nargs='?', default='https://cedwyn.bucklerfamily.estate')
    ap.add_argument('--ref', help='git commit for questions-base.json (default: the published build stamp)')
    ap.add_argument('--base-file', help='local questions-base.json (overrides --ref)')
    ap.add_argument('--index-file', help='local mail catalogue index.json (overrides the published one)')
    a = ap.parse_args()
    base = a.base_url.rstrip('/')
    failures = []

    if a.base_file:
        pin = 'base-file ' + a.base_file
        try:
            base_src = json.load(open(a.base_file))
        except Exception as e:
            print('FAIL: cannot load %s: %s' % (a.base_file, e)); return 1
    else:
        ref = a.ref
        if ref:
            pin = '--ref ' + ref
        else:
            try:
                ref = json.loads(get(base + STAMP))['commit']
                pin = 'published build stamp ' + ref[:12]
            except Exception as e:
                print('FAIL: no --ref given and %s%s unavailable (%s).' % (base, STAMP, e))
                print('Refusing an unpinned expectation - it could race a moving main branch.')
                return 1
        try:
            base_src = json.loads(get(RAW_BASE % ref))
        except Exception as e:
            print('FAIL: cannot load questions-base.json at %s: %s' % (ref, e)); return 1
    try:
        idx_src = json.load(open(a.index_file)) if a.index_file else json.loads(get(base + '/email/view/index.json'))
    except Exception as e:
        print('FAIL: cannot load the mail catalogue index: %s' % e); return 1

    qs = build(base_src, idx_src)
    if not qs:
        print('FAIL: source data produced zero questions - refusing to pass an empty expectation')
        return 1
    print('source expectation: %d questions, %d class="tg" chips+legend (base: %s, index: %s records%s)'
          % (len(qs), expected_totals(qs), pin, len(idx_src.get('records', [])),
             ' served (not guaranteed atomic - see docstring)' if not a.index_file else ' from ' + a.index_file))

    for alias in ALIASES:
        try:
            h = get(base + alias)
        except Exception as e:
            failures.append('%s: fetch failed: %s' % (alias, e))
            print('FAIL %-16s fetch failed' % alias)
            continue
        problems = page_problems(alias, h, qs)
        if problems:
            failures.extend(problems)
            print('FAIL %-16s %d problem(s)' % (alias, len(problems)))
        else:
            print('PASS %-16s %d questions, attrs present, chips complete' % (alias, len(qs)))

    if failures:
        print('\ncheck_qa_served: FAIL (static served layer); rendered-layer browser runbook still required')
        for f in failures[:40]:
            print(' -', f)
        return 1
    print('\ncheck_qa_served: PASS (static served layer only). Still run the rendered-layer browser runbook.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
