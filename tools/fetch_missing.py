#!/usr/bin/env python3
"""fetch_missing.py - before rewriting: find scripts, styles, images and data files that theme pages load from another
bucklerfamily.estate site (e.g. the shared ghf-lang header scripts on the apex domain) and that no theme folder holds yet;
copy each one read-only from its live address into the theme folder it maps to. Old sites are only read. - Sion's Tab agent"""
import json, re, sys, pathlib, urllib.request, urllib.parse, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'themes.json'))
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist'); D = len(DIST.parts)
sys.argv = [sys.argv[0], str(DIST)]
HOST = {}
for t in CFG['themes']:
    for h in t.get('hosts', []):
        if h not in ('bucklerfamily.estate', 'www.bucklerfamily.estate'): HOST[h.lower()] = t['id']
for h, tid in CFG.get('extra_hosts', {}).items():
    if tid: HOST[h] = tid
APEX = sorted(CFG['apex']['paths'].items(), key=lambda kv: -len(kv[0]))
def target(host, path):
    if host in ('bucklerfamily.estate', 'www.bucklerfamily.estate'):
        for pre, tid in APEX:
            if path.startswith(pre): return tid + '/' + path[len(pre):]
    tid = HOST.get(host)
    return tid + path if tid else None
RX = re.compile(r'''(?:src|href|data-src)\s*=\s*["'](https?://([a-z0-9.-]*bucklerfamily\.estate)(/[^"'?#\s]*\.(?:js|mjs|css|json|png|jpe?g|gif|webp|svg|woff2?|ico))(?:\?[^"'#\s]*)?)["']''', re.I)
want = {}
for p in DIST.rglob('*.htm*'):
    if len(p.parts) <= D + 1: continue
    for full, host, path in RX.findall(p.read_text('utf-8', 'ignore')):
        t = target(host.lower(), urllib.parse.unquote(path))
        if t and not (DIST / t).exists(): want[t] = full
def get(item):
    t, u = item
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'cedwyn-archive (read-only)'}), timeout=30) as r:
            b = r.read(24 * 1024 * 1024)
        f = DIST / t; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b); return 1
    except Exception: return 0
items = list(want.items())[:800]
with cf.ThreadPoolExecutor(8) as ex: got = sum(ex.map(get, items))
json.dump({'missing_cross_site_assets': len(want), 'fetched': got}, open(DIST / '_fetch_missing.json', 'w'))
print('fetch_missing:', len(want), 'missing,', got, 'fetched')
