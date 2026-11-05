#!/usr/bin/env python3
"""holdings_wording.py - holdings wording (owner rule, 22:25 GMT 30 Oct 2026). - Sion's Tab agent
Public text never states whether the family holds a record; it records which other party should hold the original and what
each has disclosed. Reads data/holdings-wording.json and, over dist/ (skip_themes and skip_prefixes are left verbatim), applies
the ordered exact-phrase regex rewrites to text files ("cap": keep a capital first letter when the matched text began with one).
A JSON file whose rewrite would not parse is left as it was. Phrases still matching report_re in visible text are listed in
dist/_cedwyn/reports/holdings-wording.json for an editor; nothing here fails a build. site.py calls it after the page writers.
Usage: python3 tools/holdings_wording.py dist (P-104)"""
import json, re, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
def _rule(r):
    c = re.compile(r['re']); rep = r['replace']; cap = r.get('cap')
    def f(m):
        out = m.expand(rep)
        if cap and m.group(0)[:1].isupper() and out: out = out[:1].upper() + out[1:]
        return out
    return r['id'], c, f
def run(dist, cfg_path=None):
    dist = pathlib.Path(dist); cfg = json.load(open(cfg_path or ROOT / 'data' / 'holdings-wording.json', encoding='utf-8'))
    rw = [_rule(r) for r in cfg['rewrites']]; exts = set(cfg.get('text_ext', ['.html']))
    skip = tuple(cfg.get('skip_prefixes', [])); sth = set(cfg.get('skip_themes', [])); left_re = re.compile(cfg['report_re'])
    rep = {'version': cfg.get('version'), 'rewrites': {}, 'files_changed': 0, 'json_left': [], 'left': []}
    for f in dist.rglob('*'):
        if not f.is_file() or f.suffix.lower() not in exts: continue
        rel = f.relative_to(dist).as_posix()
        if rel.startswith(skip) or rel.split('/', 1)[0] in sth: continue
        try: t = f.read_text(encoding='utf-8')
        except Exception: continue
        o = t
        for i, c, fn in rw:
            t, n = c.subn(fn, t)
            if n: rep['rewrites'][i] = rep['rewrites'].get(i, 0) + n
        if t != o and f.suffix.lower() == '.json':
            try: json.loads(t)
            except Exception: rep['json_left'].append(rel); t = o
        if t != o: f.write_text(t, encoding='utf-8'); rep['files_changed'] += 1
        if f.suffix.lower() in ('.html', '.htm') and len(rep['left']) < 400:
            v = re.sub(r'<[^>]+>', ' ', re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', t))
            for m in left_re.finditer(v):
                rep['left'].append(rel + ' :: ' + re.sub(r'\s+', ' ', v[max(0, m.start() - 80):m.end() + 60]))
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'holdings-wording.json', 'w'), indent=1, ensure_ascii=False)
    print('holdings wording:', sum(rep['rewrites'].values()), 'rewrites in', rep['files_changed'], 'files;', len(rep['left']), 'left for an editor')
    return rep
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
