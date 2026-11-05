#!/usr/bin/env python3
"""check_links.py - fails the build if any outbound link survives anywhere on the site.
Checks every HTML file: <a>/<area> href and <form> action must stay on cedwyn.bucklerfamily.estate (relative or
same-host); the never-share YouTube channel must not appear in any href or iframe src. - Sion's Tab agent"""
import re, sys, pathlib, json
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
A = re.compile(r'''<(a|area|form)\b(?:[^>"']|"[^"]*"|'[^']*')*?\s(href|action)\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)''', re.I | re.S)
IF = re.compile(r'''<iframe\b(?:[^>"']|"[^"]*"|'[^']*')*?\ssrc\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)''', re.I | re.S)
BANNED = re.compile(r'UC2sN1VEs1WeLfBH8VmbvLWw|sionbuckler5713', re.I)
SCRIPT = re.compile(r'<script\b.*?</script>', re.I | re.S)
FIX = '--fix' in sys.argv
CHECKOUT = ('buy.stripe.com', 'checkout.stripe.com', 'gumroad.com')   # 27 Oct 2026: e-book Buy buttons go straight to checkout (Sion 13:01)
import urllib.parse
CFG = json.load(open(pathlib.Path(__file__).resolve().parent.parent / 'themes.json'))
THOST = {h.lower(): t['id'] for t in CFG['themes'] for h in t.get('hosts', []) if h not in ('bucklerfamily.estate', 'www.bucklerfamily.estate')}
THOST.update({h.lower(): v for h, v in CFG.get('extra_hosts', {}).items() if v})
TAPEX = sorted(CFG['apex']['paths'].items(), key=lambda kv: -len(kv[0]))
def theme_link(full):
    sp = urllib.parse.urlsplit(full); h = (sp.hostname or '').lower(); p = sp.path or '/'
    q = ('?' + sp.query if sp.query else '') + ('#' + sp.fragment if sp.fragment else '')
    if h in ('bucklerfamily.estate', 'www.bucklerfamily.estate'):
        for pre, tid in TAPEX:
            if p.startswith(pre) or p + '/' == pre: return '/' + tid + '/' + p[len(pre):].lstrip('/') + q
        return None
    return ('/' + THOST[h] + p + q) if h in THOST else None
bad = []; pages = 0; links = 0; fixed = 0
for p in DIST.rglob('*.htm*'):
    if not p.is_file(): continue
    pages += 1
    raw = p.read_text('utf-8', 'ignore')
    if FIX:
        def fx(m):
            global fixed
            v = m.group(3); q = v[0] if v[0] in '"\'' else ''; u = v[1:-1] if q else v; u2 = u.strip()
            if BANNED.search(u2): fixed += 1; return m.group(0)[:-len(v)] + '"#"'
            if re.match(r'(?i)^(https?:)?//', u2) and re.sub(r'(?i)^(https?:)?//', '', u2).split('/')[0].split(':')[0].lower() not in ('cedwyn.bucklerfamily.estate',) + CHECKOUT and not re.sub(r'(?i)^(https?:)?//', '', u2).split('/')[0].split(':')[0].lower().endswith('.gumroad.com'):
                fixed += 1; full = ('https:' + u2) if u2.startswith('//') else u2
                t = theme_link(full)   # 25 Oct 2026: a theme's former address goes to the theme, not to /wayback/go/
                if t: return m.group(0)[:-len(v)] + '"' + t + '"'
                return m.group(0)[:-len(v)] + '"/wayback/go/?u=' + urllib.parse.quote(full, safe='') + '"'
            if BANNED.search(u2): fixed += 1; return m.group(0)[:-len(v)] + '"#"'
            return m.group(0)
        keep = []
        def stash(m): keep.append(m.group(0)); return '\x00S%d\x00' % (len(keep) - 1)
        t = SCRIPT.sub(stash, raw); t2 = A.sub(fx, t)
        t2 = IF.sub(lambda m: m.group(0)[:-len(m.group(1))] + '"about:blank"' if BANNED.search(m.group(1)) else m.group(0), t2)
        if t2 != t:
            raw = re.sub('\x00S(\d+)\x00', lambda m: keep[int(m.group(1))], t2); p.write_text(raw, 'utf-8')
    s = SCRIPT.sub('', raw)
    for tag, attr, v in A.findall(s):
        links += 1; v = v.strip('"\'').strip()
        if re.match(r'(?i)^(https?:)?//', v):
            host = re.sub(r'(?i)^(https?:)?//', '', v).split('/')[0].split('?')[0].split('#')[0].split(':')[0].lower()
            if host != 'cedwyn.bucklerfamily.estate' and host not in CHECKOUT and not host.endswith('.gumroad.com'): bad.append((str(p.relative_to(DIST)), v[:120]))
        if BANNED.search(v): bad.append((str(p.relative_to(DIST)), 'BANNED ' + v[:80]))
    for v in IF.findall(s):
        if BANNED.search(v): bad.append((str(p.relative_to(DIST)), 'BANNED iframe ' + v[:80]))
res = {'fixed_in_place': fixed, 'pages': pages, 'links_checked': links, 'outbound_found': len(bad), 'examples': bad[:30], 'pass': not bad}
json.dump(res, open(DIST / ('_outbound_fix.json' if FIX else '_outbound_test.json'), 'w'), indent=1)
print(json.dumps({k: res[k] for k in ('pages', 'links_checked', 'outbound_found', 'pass')}))
sys.exit(0 if (FIX or not bad) else 1)
