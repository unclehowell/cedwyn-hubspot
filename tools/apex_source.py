#!/usr/bin/env python3
"""apex_source.py <bff public dir> <dist> - the apex site's own static files (repo unclehowell/BucklerFamilyFarm, folder
public/, read-only) for the apex themes: /wales/, /patagonia/, /cyberspace/ get their folders, and every other apex-root
file (legal pages, fonts, location images, brand, evidence, e-book widget ...) goes to /dartboard/ (the apex root).
Files the crawl already holds are kept; nothing over 24 MB. - Sion's Tab agent"""
import sys, shutil, pathlib, json
src, dist = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
OWN = {'wales', 'patagonia', 'cyberspace'}
SKIP = {'_headers', '_redirects'}
n = skipped = 0
for p in src.rglob('*'):
    if not p.is_file(): continue
    rel = p.relative_to(src).parts
    if rel[0] in SKIP or p.stat().st_size > 24 * 1024 * 1024: skipped += 1; continue
    dst = dist / (rel[0] if rel[0] in OWN else 'dartboard') / pathlib.Path(*(rel[1:] if rel[0] in OWN else rel))
    if dst.exists(): skipped += 1; continue
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, dst); n += 1
json.dump({'copied': n, 'kept_or_skipped': skipped}, open(dist / '_apex_source.json', 'w'))
print('apex source: copied', n, 'kept/skipped', skipped)
