#!/usr/bin/env python3
"""guestbook.py - the Agent guest book: one collapsed table in the shared footer of every Cedwyn page.
Sion, 01:51 GMT 26 Oct 2026: "agent guest book table (collapsed) in the footers ... feed github commit users ... hyperlink
to github commit for details ... semantic version in column 1 (the hyperlink), the date of change in column 2, note about
the change in column 3 ... Who made the change. A standardised table across all pages, no exceptions."

At build time (site.py calls run() last) this reads main's commit history and writes ONE data file,
/guestbook/guestbook.json, that every page reads; /guestbook/ lists every commit; and every HTML page gets the same
constant shell (<section id="cedwyn-guestbook">) plus /_cedwyn/guestbook/gb.js, which moves it into the shared footer and
fills the newest 20 rows. The shell never changes between builds, so pages do not churn.
Commit links open GitHub directly (allowed out by the owner, 01:54 GMT 26 Oct; runtime.js and /wayback/go/ pass them).
Versions: the repo's tags are theme-branch tags (none on main), so versions are derived (RULE below).
History source: git (the build's shallow checkout is deepened first); if git cannot give the history, data/guestbook.json
(the snapshot committed with this file) is used. - Sion's Tab agent"""
import json, re, sys, html, pathlib, subprocess, datetime, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = 'unclehowell/cedwyn'
SHOW = 20
SHELL_VER = '1.1.1'
RULE = ('Versions are derived from main\'s commit history (the repo has no release tags on main): the first commit is '
        '1.0.0; each later commit bumps the minor number (1.N.0), except a fix (first word fix/typo/repair/correct/restore, '
        'or "typo" anywhere in the first line) and the automated build-log commits, which bump the patch number (1.N.P).')
FIX = re.compile(r'^\s*(?:[\w./-]+:\s*)?(?:fix|fixes|fixed|hotfix|typo|typos|repair|repairs|repaired|correct|corrects|corrected|restore|restores|restored)\b|\btypos?\b', re.I)
SUFFIX = re.compile(r'\s+[\u2014\u2013-]+\s*(?:Sion[\'\u2019]s\s+)?([A-Za-z][\w.+-]*(?:\s+[A-Za-z][\w.+-]*){0,2}?)\s+agent\s*$', re.I)
BOTS = re.compile(r'(^cedwyn-bot$|\[bot\]$|^github-actions)', re.I)
US, RS = '\x1f', '\x1e'

def git(*a, timeout=120):
    return subprocess.run(['git', '-C', str(ROOT)] + list(a), capture_output=True, text=True, timeout=timeout)

def history():
    try:
        if git('rev-parse', '--is-shallow-repository').stdout.strip() == 'true':
            r = git('fetch', '--quiet', '--unshallow', '--no-tags', '--filter=blob:none', 'origin', 'HEAD', timeout=300)
            if r.returncode != 0: git('fetch', '--quiet', '--unshallow', '--no-tags', 'origin', 'HEAD', timeout=300)
        if git('rev-parse', '--is-shallow-repository').stdout.strip() == 'true': return None
        fmt = US.join(['%H', '%an', '%cI', '%s', '%b']) + RS
        r = git('log', '--first-parent', '--reverse', '--format=' + fmt, 'HEAD')
        if r.returncode != 0: return None
        out = []
        for rec in r.stdout.split(RS):
            rec = rec.strip('\n')
            if not rec: continue
            sha, an, ci, subj, body = (rec.split(US) + [''] * 5)[:5]
            co = re.findall(r'(?im)^co-authored-by:\s*([^<\n]+?)\s*<', body)
            out.append({'sha': sha, 'author': an, 'date': ci, 'subject': subj, 'coauthors': co})
        return out or None
    except Exception as e:
        print('guestbook: git history unavailable:', e); return None

def who_and_note(c):
    subj = c['subject'].strip(); who = None
    m = SUFFIX.search(subj)
    if m:
        who = m.group(1).strip(); subj = subj[:m.start()].rstrip()
        if who.lower() in ('tab', "sion's tab"): who = 'Tab'
    if not who:
        a = (c.get('author') or '').strip()
        who = a if a and '@' not in a else 'unknown'
    co = [x.strip() for x in c.get('coauthors', []) if x.strip() and '@' not in x and x.strip() != who]
    if co: who += ' + ' + ', '.join(co)
    return who, subj or c['subject']

def gmt(iso):
    d = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
    return d.strftime('%d/%m/%Y %H:%M GMT'), d.strftime('%Y-%m-%dT%H:%MZ')

def rows_from(commits):
    rows = []; v = [1, 0, 0]
    for i, c in enumerate(commits):
        bot = bool(BOTS.search(c.get('author') or ''))
        kind = 'build' if bot else ('fix' if FIX.search(c['subject']) else 'change')
        if i:
            if kind == 'change': v = [v[0], v[1] + 1, 0]
            else: v = [v[0], v[1], v[2] + 1]
        who, note = who_and_note(c)
        d, iso = gmt(c['date'])
        rows.append({'v': '%d.%d.%d' % tuple(v), 'sha': c['sha'], 'date': d, 'iso': iso, 'note': note, 'who': who, 'kind': kind})
    return rows

def collect():
    commits = history(); snap = ROOT / 'data' / 'guestbook.json'
    if commits:
        rows = rows_from(commits); src = 'git'
    else:
        rows = json.load(open(snap, encoding='utf-8'))['rows'][::-1] if snap.exists() else []; src = 'snapshot'
        print('guestbook: using the committed snapshot (%d rows)' % len(rows))
    rows = rows[::-1]   # newest first
    return {'repo': REPO, 'commit_url': 'github.com/' + REPO + '/commit/<sha>', 'rule': RULE, 'source': src,
            'generated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
            'version': rows[0]['v'] if rows else '', 'count': len(rows), 'show': SHOW, 'rows': rows}

def go(sha):
    return '/wayback/go/?u=' + urllib.parse.quote('https://github.com/%s/commit/%s' % (REPO, sha), safe='')

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent guest book · Cedwyn</title><meta name="description" content="Every change to Cedwyn, newest first: version, date, note and who made it.">
<style>:root{color-scheme:light dark}body{margin:0;font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:64rem;margin:0 auto;padding:16px}h1{font-size:1.5rem;margin:.6em 0 .3em}.muted{opacity:.75;font-size:.9em}
.gbw{overflow-x:auto;-webkit-overflow-scrolling:touch;max-width:100%}table{border-collapse:collapse;width:100%;font-size:.92em}
th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid color-mix(in srgb,currentColor 18%,transparent)}
th{white-space:nowrap}td.v,td.w{white-space:nowrap}td.d{min-width:6.6em;width:6.6em}td.n{min-width:13em}@media(min-width:700px){td.d{white-space:nowrap;width:auto}}tr.build td{opacity:.6}</style></head><body>
<main id="guestbook" data-no-translate translate="no"><h1 data-gb-l="title">Agent guest book</h1>
<p class="muted"><span data-gb-l="intro">Every change to this site, newest first. Each version opens the change on GitHub.</span> __VERSION__ · __COUNT__</p>
<p class="muted">__RULE__</p>
<div class="gbw"><table><thead><tr><th data-gb-l="v">Version</th><th data-gb-l="d">Date</th><th data-gb-l="n">Change</th><th data-gb-l="w">Who</th></tr></thead><tbody>
__ROWS__</tbody></table></div></main>
<script src="/_cedwyn/guestbook/gb.js?v=__SV__" defer></script></body></html>
"""

def page(data):
    e = html.escape; rs = []
    for r in data['rows']:
        rs.append('<tr class="%s"><td class="v"><a href="%s">%s</a></td><td class="d">%s</td><td class="n">%s</td><td class="w">%s</td></tr>\n'
                  % (r['kind'], go(r['sha']), e(r['v']), e(r['date']), e(r['note']), e(r['who'])))
    return (PAGE.replace('__VERSION__', 'v' + e(data['version'])).replace('__COUNT__', '%d changes' % data['count'])
            .replace('__RULE__', e(data['rule'])).replace('__ROWS__', ''.join(rs)).replace('__SV__', SHELL_VER))

def shell():
    return (pathlib.Path(__file__).resolve().parent / 'guestbook' / 'shell.html').read_text(encoding='utf-8').strip().replace('__SV__', SHELL_VER)

SKIP_DIRS = ('_cedwyn/', '_ext/', '_blob/', 'db/')
def inject(dist, sh):
    n = skipped = 0
    for p in dist.rglob('*.htm*'):
        if not p.is_file(): continue
        rel = p.relative_to(dist).as_posix()
        if rel.startswith(SKIP_DIRS): continue
        t = p.read_text(encoding='utf-8', errors='ignore')
        if 'id="cedwyn-guestbook"' in t: continue
        low = t.lower()
        if '<body' not in low and '<html' not in low: skipped += 1; continue          # a fragment, not a page
        if re.search(r'<meta[^>]+http-equiv\s*=\s*["\']?refresh', low) and len(t) < 2000: skipped += 1; continue   # a redirect stub
        i = low.rfind('</body>')
        if i < 0: i = low.rfind('</html>')
        t = t[:i] + sh + t[i:] if i >= 0 else t + sh
        p.write_text(t, encoding='utf-8'); n += 1
    return n, skipped

def run(dist):
    dist = pathlib.Path(dist); data = collect()
    gd = dist / 'guestbook'; gd.mkdir(parents=True, exist_ok=True)
    (gd / 'guestbook.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (gd / 'index.html').write_text(page(data), encoding='utf-8')
    n, sk = inject(dist, shell())
    print('guestbook: %d rows (%s), version %s; shell on %d pages, %d redirect stubs/fragments skipped' % (data['count'], data['source'], data['version'], n, sk))
    return data

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('--snapshot', '--snapshot-print'):   # data/guestbook.json (the fallback) from git
        d = collect(); d.pop('generated', None); d['source'] = 'snapshot'; s = json.dumps(d, ensure_ascii=False, indent=0) + '\n'
        if sys.argv[1] == '--snapshot-print': sys.stdout.write(s)
        else: (ROOT / 'data' / 'guestbook.json').write_text(s, encoding='utf-8'); print(d['count'], d['version'])
    else:
        run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
