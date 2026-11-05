#!/usr/bin/env python3
"""check_app_pages.py - interactive list/app pages must opt out of the cw-graph clip/levels collapse.

Regression guard for 30 Oct 2026 (HubSpot 536838257890): the site-wide card-levels feature folded the
Q&A card list into plain-text previews because (a) the task's written exemption for "app/list pages
(Q&A with filters...)" was implemented as a hand-maintained path regex that never listed qa, and
(b) no build check compared the plan against the shipped gate.

Layer honesty: static build-time check over dist HTML and the cw-graph.js source. It does not run a
browser; the rendered-layer verification is a separate manual/agent runbook (acceptance template).

Fail-closed rules (exit 1):
1. APP PAGES SELF-DECLARE. A dist page carrying a known interactive list app (marker id="qx")
   MUST declare data-cw-noclip AND data-cw-nolevels on its <html> tag, so the runtime collapse
   passes (cw-graph.js clip()/levels()) skip it.
2. NOCLIP NEVER NARROWS. The 29-path baseline frozen below (cw-graph.js line 303, 30 Oct 2026)
   must stay inside the NOCLIP regex. Additions are fine; removal/rename fails.
3. SANITY. dist must exist and contain HTML; cw-graph.js must exist and parse. A check that
   examines nothing has failed, not passed.

Advisory (never fails): pages with a search control and >=10 repeated <article> cards but no
opt-out attributes - the 01:27 design says pages with search boxes and filters load everything,
so each needs an explicit keep-or-exempt decision.

Usage: python3 tools/check_app_pages.py dist [--site-root PATH] [--warn-only]
--site-root defaults to dist's parent (repo root in CI)."""
import argparse, pathlib, re, sys

APP_MARKERS = ('id="qx"',)          # interactive list apps whose content IS the card list
BASELINE_NOCLIP = ['dartboard', 'documentary', 'movie', 'story', 'academy', 'wayback', 'legal',
                   'terms', 'privacy', 'cookies', 'chess', 'arcade', 'maps', 'chat', 'app',
                   'infographic', 'familytree', 'terrain', 'thousand-cuts', 'shop', 'ebooks',
                   'subscribe', 'nft-art', 'db', 'parcels', 'cyberspace', 'estate', 'directory',
                   'patagonia']     # 29 paths, frozen from web/_cedwyn/cw-graph.js line 303 on 30 Oct 2026

def main():
    ap = argparse.ArgumentParser(description='Interactive list/app pages must declare collapse opt-outs.')
    ap.add_argument('dist', nargs='?', default='dist')
    ap.add_argument('--site-root', help='repo root for cw-graph.js (default: dist parent)')
    ap.add_argument('--warn-only', action='store_true')
    a = ap.parse_args()
    warn_only = a.warn_only
    dist = pathlib.Path(a.dist)
    root = pathlib.Path(a.site_root) if a.site_root else dist.parent
    failures, advisories = [], []

    pages = sorted(dist.rglob('*.html')) if dist.is_dir() else []
    if not dist.is_dir():
        failures.append('dist directory %s does not exist - nothing was checked' % dist)
    elif not pages:
        failures.append('dist directory %s contains no HTML files - nothing was checked' % dist)

    for f in pages:
        try:
            h = f.read_text(errors='ignore')
        except OSError:
            continue
        rel = f.relative_to(dist).as_posix()
        htmltag = (re.search(r'<html\b[^>]*>', h) or [''])[0]
        declared = 'data-cw-noclip' in htmltag and 'data-cw-nolevels' in htmltag
        if any(m in h for m in APP_MARKERS) and not declared:
            failures.append('%s: interactive list app without data-cw-noclip/data-cw-nolevels' % rel)
        elif not declared:
            has_search = ('type="search"' in h) or ('role="search"' in h)
            if has_search and len(re.findall(r'<article\b', h)) >= 10:
                advisories.append('%s: search + card list, no opt-out declared (review)' % rel)

    cw = root / 'web' / '_cedwyn' / 'cw-graph.js'
    if not cw.is_file():
        failures.append('web/_cedwyn/cw-graph.js not found under %s - NOCLIP drift rule cannot run' % root)
    else:
        src = cw.read_text(errors='ignore')
        m = re.search(r'NOCLIP\s*=\s*/(.+?)/;', src)
        alts = re.findall(r'\(\?:([a-z0-9_|-]+)\)', m.group(1)) if m else []
        paths = max(alts, key=lambda a: a.count('|')) if alts else None
        if not paths:
            failures.append('web/_cedwyn/cw-graph.js: NOCLIP path alternation not found (format changed - re-review this check)')
        else:
            current = paths.split('|')
            missing = [p for p in BASELINE_NOCLIP if p not in current]
            if missing:
                failures.append('cw-graph.js NOCLIP narrowed; baseline paths removed: %s' % ', '.join(missing))

    if warn_only:
        advisories = advisories + ['would fail: ' + x for x in failures]
        failures = []
    for a in advisories:
        print('ADVISORY:', a)
    if failures:
        for x in failures:
            print('FAIL:', x)
        print('check_app_pages: %d failure(s). Interactive list pages must declare their own' % len(failures))
        print('data-cw-noclip data-cw-nolevels (see tools/qa_questions.py patch_page) and NOCLIP must not narrow.')
        return 1
    print('check_app_pages: OK (%d pages, %d advisory)' % (len(pages), len(advisories)))
    return 0

if __name__ == '__main__':
    sys.exit(main())
