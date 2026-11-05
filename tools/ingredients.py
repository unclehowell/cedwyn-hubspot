#!/usr/bin/env python3
"""Cedwyn editorial rule: ingredients, not conclusions (25 Oct 2026).
Applies ingredients.json to the assembled site (dist/<theme>/<file>): exact find -> replace of sentences that hand the reader a
conclusion, in the cedwyn copy only (datro and its subdomains are never touched). Missing finds are reported, never fatal.
Also applies app-demo-factcheck.json (the app theme demo fact-check, same schema) and spa-basepath.json (the base path of a crawled single-page theme's router, so it does not show "Not Found" under /<theme>/); an entry's file may be a glob
(e.g. assets/webapp-*.js) so a re-hashed crawl still matches.
Called from tools/site.py so it runs before the self-contained pass and the catalogue database (the FTS index carries the
reworded text). Report: dist/_cedwyn/reports/ingredients.json. — Sion's Tab agent"""
import json, pathlib, re, sys
CONFIGS = ('ingredients.json', 'app-demo-factcheck.json', 'spa-basepath.json')   # spa-basepath.json: router base paths of crawled SPA themes
# 31 Oct 2026 (P-134): a record transcript is a verbatim quotation and is never reworded. Rewords apply only outside
# <blockquote class="... ev-transcript ..."> blocks; a find that occurs only inside one is reported as kept_verbatim, not missing.
# (Rule M12 had rewritten the 1988 RCAHMW card text inside the EV-0629 transcript, so the page quoted our words as the record's.)
TRANSCRIPT = re.compile(r'<blockquote\b[^>]*\bclass\s*=\s*["\'][^"\']*\bev-transcript\b[^"\']*["\'][^>]*>.*?</blockquote\s*>', re.S | re.I)
def _replace_outside_transcripts(t, find, rep_):
    out = []; n = 0; kept = 0; pos = 0
    for m in TRANSCRIPT.finditer(t):
        seg = t[pos:m.start()]; n += seg.count(find); out.append(seg.replace(find, rep_))
        kept += m.group(0).count(find); out.append(m.group(0)); pos = m.end()
    seg = t[pos:]; n += seg.count(find); out.append(seg.replace(find, rep_))
    return ''.join(out), n, kept
def _files(dist, e):
    rel = e.get('file', 'index.html'); base = dist / e['theme']
    if any(ch in rel for ch in '*?['): return sorted(base.glob(rel))
    return [base / rel]
def apply(dist, cfg_path=None):
    dist = pathlib.Path(dist); root = pathlib.Path(__file__).resolve().parent.parent
    paths = [pathlib.Path(cfg_path)] if cfg_path else [root / c for c in CONFIGS]
    rep = {'version': {}, 'applied': [], 'missing': [], 'kept_verbatim': []}
    for cp in paths:
        if not cp.exists(): rep['missing'].append({'config': cp.name, 'why': 'not found'}); continue
        cfg = json.load(open(cp, encoding='utf-8')); rep['version'][cp.name] = cfg.get('version')
        for e in cfg.get('rewords', []):
            fs = [f for f in _files(dist, e) if f.exists()]
            if not fs: rep['missing'].append({'config': cp.name, 'theme': e['theme'], 'file': str(e.get('file')), 'why': 'file not found'}); continue
            hit = 0
            for f in fs:
                t = f.read_text(encoding='utf-8', errors='surrogateescape')
                new, n, kept = _replace_outside_transcripts(t, e['find'], e['replace'])
                if kept: rep['kept_verbatim'].append({'config': cp.name, 'theme': e['theme'], 'file': str(f.relative_to(dist / e['theme'])), 'n': kept, 'find': e['find'][:60]})
                if n: f.write_text(new, encoding='utf-8', errors='surrogateescape'); hit += n; rep['applied'].append({'config': cp.name, 'theme': e['theme'], 'file': str(f.relative_to(dist / e['theme'])), 'n': n})
            if not hit and not any(k['find'] == e['find'][:60] and k['theme'] == e['theme'] for k in rep['kept_verbatim']): rep['missing'].append({'config': cp.name, 'theme': e['theme'], 'file': e.get('file'), 'find': e['find'][:60]})
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'ingredients.json', 'w'), indent=1, ensure_ascii=False)
    print('ingredients:', len(rep['applied']), 'applied,', len(rep['missing']), 'missing,', len(rep['kept_verbatim']), 'kept verbatim in transcripts')
    return rep
if __name__ == '__main__': apply(sys.argv[1] if len(sys.argv) > 1 else 'dist')
