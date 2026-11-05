#!/usr/bin/env python3
"""check_qa_built.py - build-time Q&A completeness guard (CI, fail-closed).

Runs in CI after tools/site.py (which calls qa_questions.run). qa_questions writes
dist/qa/questions.json - the exact built truth: every question ID with its asked/answered
hashtag chips. This check proves the canonical Q&A page serves all of it AND that the
alias routes survive.

Intended pipeline contract (verified 30 Oct 2026 against tools/site.py step comment line 9
and tools/sections.py run() step 5): /qa/ is the ONLY real Q&A page file. The aliases
/wales/qa/ and /argentina/qa/ are Cloudflare Pages 200 rewrites of the canonical files via
the generic rules in dist/_redirects:
    /wales/:theme/* /:theme/:splat 200
    /argentina/:theme/* /:theme/:splat 200
There are NO dist/wales/qa or dist/argentina/qa files by design - do not add them. (dbserve
used to drop dist/qa/questions.json into the DB, breaking this contract; fixed in 24f89c4
by keeping ^/?(?:[^/]+/)?qa/questions.json$ as a plain file.)

Layer honesty: static check over build output (stdlib HTMLParser, no browser). Live serving
of the aliases through the rewrites is covered by check_qa_served.py (post-deploy static)
plus the manual/agent rendered-layer runbook.

Fails closed (exit 1): dist/qa/questions.json missing/unparseable/empty; canonical page
missing, markerless, or with any ID/chip multiset mismatch or wrong class="tg" total;
dist/_redirects missing or lacking either generic section rewrite (a lost rule means dead
aliases on publish); no Q&A page found at all. Any REAL dist/<section>/qa/index.html that
ever materializes with id="qx" is checked too.

Usage: python3 tools/check_qa_built.py [dist]"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from check_qa_served import page_problems, expected_totals

REQUIRED_REWRITES = [
    '/wales/:theme/* /:theme/:splat 200',
    '/argentina/:theme/* /:theme/:splat 200',
]   # tools/sections.py step 5 - the routes behind /wales/qa/ and /argentina/qa/

def main():
    ap = argparse.ArgumentParser(description='Build-time Q&A completeness guard.')
    ap.add_argument('dist', nargs='?', default='dist')
    a = ap.parse_args()
    dist = pathlib.Path(a.dist)
    failures, checked = [], []

    qj = dist / 'qa' / 'questions.json'
    if not qj.is_file():
        print('FAIL: %s missing - qa_questions did not run or the file was dropped later; refusing to pass' % qj)
        return 1
    try:
        data = json.loads(qj.read_text(errors='ignore'))
        qs = data['questions']
        assert qs, 'empty questions list'
    except Exception as e:
        print('FAIL: %s unparseable or empty: %s' % (qj, e))
        return 1

    pages = {}
    canon = dist / 'qa' / 'index.html'
    if not canon.is_file():
        failures.append('canonical qa/index.html missing from dist')
        print('FAIL qa/index.html             canonical page missing')
    else:
        txt = canon.read_text(errors='ignore')
        if 'id="qx"' not in txt:
            failures.append('qa/index.html: expected Q&A app marker id="qx" absent (template replaced?)')
            print('FAIL qa/index.html             marker id="qx" absent')
        else:
            pages['qa/index.html'] = txt
    for p in sorted(dist.glob('*/qa/index.html')) + sorted(dist.glob('*/*/qa/index.html')):
        rel = p.relative_to(dist).as_posix()
        if rel not in pages and p.is_file():
            txt = p.read_text(errors='ignore')
            if 'id="qx"' in txt:
                pages[rel] = txt
    if not pages:
        print('FAIL: no dist Q&A page with id="qx" found - nothing was checked')
        return 1

    rd = dist / '_redirects'
    if not rd.is_file():
        failures.append('dist/_redirects missing - section alias routes cannot be verified')
        print('FAIL _redirects                file missing')
    else:
        rules = {ln.strip() for ln in rd.read_text(errors='ignore').splitlines()}
        for rule in REQUIRED_REWRITES:
            if rule not in rules:
                failures.append('dist/_redirects: required section rewrite %r absent - the Q&A aliases would not serve' % rule)
                print('FAIL _redirects                missing rule: %s' % rule)

    for rel, txt in sorted(pages.items()):
        problems = page_problems(rel, txt, qs)
        if problems:
            failures.extend(problems)
            print('FAIL %-28s %d problem(s)' % (rel, len(problems)))
        else:
            checked.append(rel)
            print('PASS %-28s %d questions, chips complete' % (rel, len(qs)))

    if failures:
        print('\ncheck_qa_built: FAIL')
        for f in failures[:40]:
            print(' -', f)
        return 1
    print('\ncheck_qa_built: OK (%d page file(s), %d alias route rule(s), %d questions, %d chips+legend expected)'
          % (len(checked), len(REQUIRED_REWRITES), len(qs), expected_totals(qs)))
    return 0

if __name__ == '__main__':
    sys.exit(main())
