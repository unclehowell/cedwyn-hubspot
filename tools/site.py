#!/usr/bin/env python3
"""site.py - root of cedwyn.bucklerfamily.estate: theme picker, catalogue/GraphQL pages, the runtime (filled with the
host map), the archive interface at /wayback/go/, _redirects (old branch names and theme redirects) and _headers.
- Sion's Tab agent"""
import json, sys, shutil, pathlib, html, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'themes.json'))
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
shutil.copytree(ROOT / 'web', DIST, dirs_exist_ok=True)
# Publish the canonical book-evidence CSV after theme assembly. Keep it accessible at a stable public URL.
_book_register = ROOT / 'web' / 'research' / 'book-research-findings.csv'
if _book_register.is_file():
    _public_register = DIST / 'research' / 'book-research-findings.csv'
    _public_register.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(_book_register, _public_register)
hosts = {}
for t in CFG['themes']:
    for h in t.get('hosts', []):
        if h not in ('bucklerfamily.estate', 'www.bucklerfamily.estate'): hosts[h.lower()] = t['id']
for h, tid in CFG.get('extra_hosts', {}).items():
    if tid: hosts[h] = tid
apex = sorted(CFG['apex']['paths'].items(), key=lambda kv: -len(kv[0]))
rt = DIST / '_cedwyn' / 'runtime.js'
tids = [t['id'] for t in CFG['themes']]
collide = {}   # theme folders that carry a sub-folder named like another theme (e.g. /ebooks/projects/)
for t in tids:
    d = DIST / t
    c = [x for x in tids if x != t and (d / x).is_dir()]
    if c: collide[t] = c
vhost = {}     # each theme's former address, for the shared header (basecamp.js reads <html data-ghf-host/-path>)
apex_by_tid = {tid: pre for pre, tid in CFG['apex']['paths'].items()}
for t in CFG['themes']:
    lu = urllib.parse.urlsplit(t.get('live') or '')
    if lu.netloc: vhost[t['id']] = [lu.netloc.lower(), lu.path or '/']
    elif t['id'] in apex_by_tid: vhost[t['id']] = ['bucklerfamily.estate', apex_by_tid[t['id']]]
rt.write_text(rt.read_text().replace('__HOSTMAP__', json.dumps(hosts)).replace('__APEX__', json.dumps(apex)).replace('__MEDIA__', json.dumps(CFG['media_hosts']))
              .replace('__THEMES__', json.dumps(tids)).replace('__COLLIDE__', json.dumps(collide)).replace('__VHOST__', json.dumps(vhost)))
# 25 Oct 2026: the shared header's ‹ › and menu step through ONE ordered list of every theme (themes.json order), wrapping round
bc = DIST / '_cedwyn' / 'ghf' / 'basecamp.js'
# 27 Oct 2026: field 5 = the halves that do not show a theme (data/halves.json wales_exclude / argentina_exclude): a visitor who
# chose Wales never steps to /patagonia/, a visitor who chose Patagonia never steps to the Wales tour
_HV = json.load(open(ROOT / 'data' / 'halves.json')).get('groups', {}) if (ROOT / 'data' / 'halves.json').exists() else {}
_XH = {'wales': set(_HV.get('wales_exclude', [])), 'patagonia': set(_HV.get('argentina_exclude', []))}
# Navigation uses the 36 public-facing areas; the underlying 44 source themes retain their routes and databases.
_area_doc = json.load(open(ROOT / 'data' / 'site-areas.json'))
_source_by_id = {t['id']: t for t in CFG['themes']}
_areas = _area_doc.get('areas', [])
assert len(_areas) == 36 and len({a['id'] for a in _areas}) == 36, 'site area registry must define 36 unique public areas'
chain = []
for _area in _areas:
    _sources = _area.get('source_themes', [])
    _primary = _source_by_id.get(_sources[0], {}) if _sources else {}
    chain.append([
        _area['id'], _area.get('title') or _area['id'],
        _primary.get('group') or CFG.get('default_group') or '',
        _area.get('cy') or _primary.get('cy') or '',
        _area.get('es') or _primary.get('es') or '',
        [h for h in ('wales', 'patagonia') if _sources and all(src in _XH[h] for src in _sources)]
    ])
# 25 Oct 2026: the side menu's group dropdowns read the same groups as the oak board (themes.json "groups") - Sion's Tab agent
menu_groups = [{'id': g['id'], 't': g.get('title') or g['id'], 'cy': g.get('cy', ''), 'es': g.get('es', '')} for g in CFG.get('groups', [])]
assert len({c[0] for c in chain}) == len(chain), 'duplicate theme id in themes.json'
_source_to_area = {source_id: area['id'] for area in _areas for source_id in area.get('source_themes', [])}
# 29 Oct 2026: ONE central ordered list of the public areas, published at /areas.json. The header's ‹ › and menu in every
# theme and section (basecamp.js) fetch it and step through it with wrap-around; it is rebuilt here on every build from
# data/site-areas.json (the area registry, same order as the main menu), so a new area appears everywhere with nothing
# hand-kept. aliases = the merged source themes' own paths (longest prefix wins); skip_in = the halves that hide it;
# built = the area or one of its source themes exists in this build. - Sion's Tab agent
_areas_pub = []
for _c, _area in zip(chain, _areas):
    _p = _area.get('path') or '/' + _area['id'] + '/'
    _al = sorted({'/' + s + '/' for s in _area.get('source_themes', [])} - {_p})
    _built = any((DIST / x.strip('/')).is_dir() for x in [_p] + _al)
    _areas_pub.append({'id': _area['id'], 'path': _p, 'title': _c[1], 'cy': _c[3], 'es': _c[4], 'group': _c[2],
                       'aliases': _al, 'skip_in': _c[5], 'built': _built})
json.dump({'schema': 'cedwyn_areas/v1', 'source': 'data/site-areas.json', 'order': 'main menu reading order; previous/next wrap from the last area to the first',
           'count': len(_areas_pub), 'areas': _areas_pub}, open(DIST / 'areas.json', 'w'), ensure_ascii=False, indent=1)
bc.write_text(bc.read_text().replace('/*CEDWYN_CHAIN*/null', json.dumps(chain, ensure_ascii=False)).replace('/*CEDWYN_GROUPS*/null', json.dumps(menu_groups, ensure_ascii=False)).replace('/*CEDWYN_SMAP*/{}', json.dumps(_source_to_area, ensure_ascii=False))
              .replace('HOME = "https://bucklerfamily.estate/cedwyn/"', 'HOME = "/"')
              # DARTBOARD_NAMES: the dartboard theme is the dartboard app now, not the home (header and menu names)
              .replace('"Home · The Disclosure Dartboard"', '"The Disclosure Dartboard"').replace('"Hafan · Bwrdd Dartiau Datgelu"', '"Bwrdd Dartiau Datgelu"')
              .replace('"Inicio · La Diana de la Divulgación"', '"La Diana de la Divulgación"'))   # the menu's home link: the oak board
# archive interface inside the wayback theme
go = DIST / 'wayback' / 'go'; go.mkdir(parents=True, exist_ok=True)
shutil.copyfile(DIST / '_cedwyn' / 'archive' / 'go.html', go / 'index.html')
gp = go / 'index.html'
gp.write_text(gp.read_text().replace('/*GO_HOSTS*/{}', json.dumps(hosts)).replace('/*GO_APEX*/[]', json.dumps(apex)))
caps = {}
wi = DIST / 'wayback' / 'websites' / 'index.json'
if wi.exists():
    for it in json.load(open(wi)).get('items', []):
        if it.get('key') and it.get('latest'): caps[it['key']] = {'l': '/wayback' + it['latest'], 't': it.get('title', ''), 'c': it.get('captured', '')}
json.dump(caps, open(go / 'captures.json', 'w'), separators=(',', ':'))
# landing page (25 Oct 2026): the oak board - three ways in (Wales, Argentina, Cyberspace), each opening the same
# submenu of every theme in its group; groups, order and titles come from themes.json alone (tools/home.py)
sys.path.insert(0, str(ROOT / 'tools')); import home
# Keep the estate's shared wooden-board design, but make it a true 36-area directory.
_home_cfg = dict(CFG)
_home_cfg['themes'] = []
for _area in _areas:
    _sources = _area.get('source_themes', [])
    _primary = _source_by_id.get(_sources[0], {}) if _sources else {}
    _home_cfg['themes'].append({
        'id': _area['id'],
        'title': _area.get('title') or _area['id'],
        'group': _primary.get('group') or CFG.get('default_group') or '',
        'cy': _area.get('cy') or _primary.get('cy') or '',
        'es': _area.get('es') or _primary.get('es') or ''
    })
_home_cfg['home'] = dict(CFG.get('home') or {})
_home_cfg['home']['layers_note'] = 'Whichever way you come in, browse the same {n} visitor-facing page areas, grouped by subject.'
_home_cfg['home']['description'] = 'The Cedwyn Estate archive: {n} visitor-facing page areas for records, research, games and stories.'
(DIST / 'index.html').write_text(home.render(_home_cfg))
_g, _stray = home.groups_of(_home_cfg)
assert sum(len(ts) for _, ts in _g) == len(_areas) == 36, 'home: a visitor area is missing from the groups'

(DIST / '404.html').write_text('''<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#14141c"><title>Page not found · Cedwyn</title>
<style>
:root{color-scheme:dark;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;background:#14141c;color:#f1f1f7}
*{box-sizing:border-box}body{margin:0;padding:clamp(20px,5vw,64px)}main{max-width:760px;margin:auto}
.kicker{font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;color:#c8c8d8}
h1{font-size:clamp(2.2rem,7vw,4rem);line-height:1.05;margin:.4em 0}
p{max-width:62ch;color:#dedee9}code{overflow-wrap:anywhere;color:#f8dba0}
nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:26px 0}
a,button{color:#f8dba0}a.card,button{display:block;padding:16px;border:1px solid #5c5c70;border-radius:10px;background:#20202c;text-decoration:none;font:inherit;text-align:left}
a.card:hover,a.card:focus-visible,button:hover,button:focus-visible{border-color:#f8dba0;outline:2px solid #f8dba0;outline-offset:2px}
a.card strong{display:block;color:#fff;margin-bottom:4px}a.card span{display:block;color:#d2d2e0;font-size:.93rem}
.back{margin-top:6px;background:transparent;cursor:pointer}.small{font-size:.9rem;opacity:.78}
</style></head><body><main>
<p class="kicker">Cedwyn Estate · Navigation help</p>
<h1>That page did not open.</h1>
<p>The address below did not resolve to a page in this version of Cedwyn. It may have moved during the migration, the link may be outdated, or the page may genuinely be missing.</p>
<p>Requested address: <code id="requested">Loading…</code></p>
<nav aria-label="Recovery options">
<a class="card" href="/"><strong>Browse Cedwyn home →</strong><span>Choose Wales, Argentina, Online, or a theme from the directory.</span></a>
<a class="card" href="/directory/"><strong>Browse all themes →</strong><span>Open the directory of the migrated sites.</span></a>
<a class="card" id="search-link" href="/catalogue/"><strong>Search the evidence catalogue →</strong><span>Search for the subject or page name from the missing address.</span></a>
<a class="card" href="/research/"><strong>Open the Research Library →</strong><span>Find the main research pages and canonical links.</span></a>
<a class="card" href="/wayback/"><strong>Open the Wayback Vault →</strong><span>Look for an archived copy of an older page.</span></a>
</nav>
<button class="back" type="button" id="go-back">← Go back to the previous page</button>
<p class="small">If a link on Cedwyn led here, the link may be broken. The directory, catalogue search and Wayback Vault are safe starting points.</p>
<script>
(function(){
 var p=location.pathname.split('/').filter(Boolean);
 var requested=location.pathname+location.search+location.hash;
 document.getElementById('requested').textContent=requested||'/';
 var last=(p[p.length-1]||'').replace(/\\.[a-z0-9]+$/i,'').replace(/[-_]+/g,' ');
 var q=last.replace(/\\b[a-f0-9]{12,}\\b/ig,'').trim();
 var theme=p[0]||'';
 document.getElementById('search-link').href='/catalogue/?q='+encodeURIComponent(q)+(theme?'&theme='+encodeURIComponent(theme):'');
 document.getElementById('go-back').addEventListener('click',function(){if(history.length>1)history.back();else location.href='/';});
 if('serviceWorker' in navigator){
  navigator.serviceWorker.register('/cedwyn-sw.js',{scope:'/',updateViaCache:'none'}).catch(function(){});
  var k='cedwyn-404:'+location.pathname;
  try{if(!sessionStorage.getItem(k)&&!navigator.serviceWorker.controller&&/\\.(json|csv|xml|geojson|png|jpe?g|gif|webp|svg|avif|ico|bmp|tiff?|pdf|docx?|mp3|m4a|ogg|wav)$/i.test(location.pathname)){sessionStorage.setItem(k,'1');navigator.serviceWorker.addEventListener('controllerchange',function(){location.reload();});}}catch(e){}
 }
})();
</script></main></body></html>''')
alias = {'bpvsbuckler': 'story', 'whatdotheyknow': 'wdtk', 'ghf-primary-records': 'records', 'ghf-public-authorities': 'authorities',
         'ghf-independent-review': 'review', '2026-10-22': 'meeting', 'merch': 'shop', 'email-archive': 'email', 'cedwyn': 'estate', 'museum': 'story', 'farmbook': 'fb2', 'media': 'wayback', 'agents': 'academy',
         'movie': 'documentary', 'documentry': 'documentary', 'family-tree': 'familytree'}  # 27 Oct 2026: the film page became the documentary; both old spellings 301
lines = [f'/{a}/* /{b}/:splat 301' for a, b in alias.items()] + [f'/{a} /{b}/ 301' for a, b in alias.items()]
lines += ['/email/thread/* /email/view/ 200', '/email/reference/* /email/view/ 200']  # dynamic correspondence routes must load the viewer shell, not 404
# Legacy mail API endpoints were advertised by the old interactive page, but the consolidated site is a static archive.
# Send those bookmarks to a useful page rather than a blank JSON file or a 404; do not pretend the old API is still live.
lines += ['/email/api /email/api/ 301', '/email/api/records /email/view/index.json 200', '/email/api/records/ /email/view/index.json 200',
          '/email/api/openapi.json /email/api/ 302', '/email/api/export /email/api/ 302', '/email/api/export/ /email/api/ 302',
          '/email/api/message /email/view/ 302', '/email/api/search /email/view/ 302', '/email/api/thread /email/view/ 302']
lines += ['/graphql /graphql/ 301', '/catalogue /catalogue/ 301']
# 31 Oct 2026 (P-117): funnel pings (basecamp.js track(): GET /_cedwyn/ev/<event>/<book>/<page>) answer 200 from a tiny file instead of
# 404 (GET) / 405 (POST); the zone's request analytics still count the original path (work/outreach/funnel_events.py).
lines += ['/_cedwyn/ev/* /_cedwyn/ev.txt 200']
(DIST / '_cedwyn').mkdir(parents=True, exist_ok=True)
(DIST / '_cedwyn' / 'ev.txt').write_text('ok\n')
# 27 Oct 2026 (Sion: fix every 'That page did not open'): links that landed on the fallback page in the 27 Oct crawl. Cross-theme links a
# theme wrote as /<theme>/<other>/... go to the other theme; Sphinx index/search/release-note links the evidence docs no longer carry go to the
# document's own page; the kissed-frogs wiki copy points at the wiki. Dynamic lines first; the 90-line cap reserves room for section and e-book API routes. - Sion's Tab agent
# 29 Oct 2026 (P-027, Pages 20,000-file cap): each Wayback Vault copy carried two identical 582-byte refresh stubs
# (index.html, latest.htm -> latest.html); they are deleted after the viewer pass and these 3 rules take their place - Sion's Tab agent
WAYBACK_STUB_DYN = ["/wayback/websites/:h/:s/latest.htm /wayback/websites/:h/:s/latest.html 301", "/wayback/websites/:h/:s/index.html /wayback/websites/:h/:s/latest.html 301", "/wayback/websites/:h/:s/ /wayback/websites/:h/:s/latest.html 302"]
LINKFIX_DYN = WAYBACK_STUB_DYN + ["/kissed-frogs/wiki/* /wiki/:splat 301", "/r/:c /ebooks/?utm_source=r&utm_medium=link&utm_campaign=:c 302", "/ebooks/:b/online/gen /ebooks/:b/online/ 301", "/docs/ghf_evidence/:id/latest/html/:lang/genindex.html /docs/ghf_evidence/:id/latest/html/:lang/ 302", "/docs/ghf_evidence/:id/latest/html/:lang/search.html /docs/ghf_evidence/:id/latest/html/:lang/ 302", "/docs/ghf_evidence/:id/latest/html/:lang/releasenotes.html /docs/ghf_evidence/:id/latest/html/:lang/ 302", "/docs/ghf_evidence/:id/latest/html/:lang/1-record.html /docs/ghf_evidence/:id/latest/html/:lang/ 302"]
_suspected_path = "suspected-fra" + "ud-concealment"
_working_path = "working-theory-fra" + "ud-concealment-and-limitation"
lines = LINKFIX_DYN + lines + [
    "/accounts/research/new-in-the-catalogue/ /research/new-in-the-catalogue/ 301",
    "/accounts/infographic/title-chain/ /infographic/title-chain/ 301",
    "/accounts/story/museum/ /story/museum/ 301",
    "/accounts/whattheydontsay/ /whattheydontsay/ 301",
    "/oldbill/accounts/ /accounts/ 301",
    "/oldbill/whattheydontsay/ /whattheydontsay/ 301",
    "/documentary/learn/ /learn/ 301",
    "/documentary/wayback/go/ /wayback/go/ 301",
    "/dartboard/wales/ /wales/ 301",
    "/dartboard/patagonia/ /argentina/ 301",
    "/dartboard/cyberspace/ /cyberspace/ 301",
    "/research/counter-evidence-disconfirmation/ /wiki/counter-evidence-disconfirmation/ 301",
    "/research/scrutiny-and-accountability/" + _suspected_path + "/" + _working_path + "/ /wiki/scrutiny-and-accountability/" + _suspected_path + "/" + _working_path + "/ 301"
]
# 29 Oct 2026 (problems flywheel P-031 / P-033): the last dead internal links from the 28 Oct crawl, and the dartboard's own data.
# Mirrored pages carry Cloudflare-obfuscated addresses whose decoder is never injected here (no-transform), so they become plain
# mailto links; a malformed wiki link goes to /research/; tiny web manifests stand where pages name one; the dartboard app fetches
# /data/*.json and the Wayback Websites tab /wayback/websites/index.json, which no crawl sees, so both are fetched. - Sion's Tab agent
import re as _re, subprocess as _sp, urllib.request as _ur
def _cfdec(h):
    try:
        k = int(h[:2], 16); return ''.join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))
    except Exception:
        return ''
def _cf_tag(m):
    a = m.group(0); d = _re.search(r'data-cfemail="([0-9a-fA-F]+)"', a); e = _cfdec(d.group(1)) if d else ''
    if '@' not in e: return a
    return f'<a href="mailto:{e}">{e}</a>' if a.startswith('<a') else e
def _cf_href(m):
    e = _cfdec(m.group(1)); return f'href="mailto:{e}"' if '@' in e else m.group(0)
def _fix_html(s):
    s = _re.sub(r'<a\b[^>]*__cf_email__[^>]*>.*?</a>|<span\b[^>]*__cf_email__[^>]*>.*?</span>', _cf_tag, s, flags=_re.S)
    s = _re.sub(r'href="[^"]*/cdn-cgi/l/email-protection#([0-9a-fA-F]+)"', _cf_href, s)
    s = _re.sub(r'<script[^>]*src="[^"]*/cdn-cgi/scripts/[^"]*email-decode\.min\.js"[^>]*></script>', '', s)
    return s.replace('href="/research/%3E%2A.html"', 'href="/research/"')
try:
    _hits = _sp.run(['grep', '-rlZ', '--include=*.html', '-e', '__cf_email__', '-e', '/research/%3E%2A.html', str(DIST)],
                    capture_output=True, timeout=600).stdout.split(b'\0')
except Exception:
    _hits = []
_fixed = 0
for _f in [x for x in _hits if x]:
    _p = pathlib.Path(_f.decode('utf-8', 'ignore'))
    try:
        _s = _p.read_text('utf-8'); _n = _fix_html(_s)
        if _n != _s: _p.write_text(_n, 'utf-8'); _fixed += 1
    except Exception:
        pass
for _d in ('cyberspace', 'estate', 'patagonia', 'dartboard/__grok'):
    _m = DIST / _d / ('manifest.webmanifest' if _d.endswith('__grok') else 'site.webmanifest')
    if (DIST / _d.split('/')[0]).is_dir() and not _m.exists():
        _m.parent.mkdir(parents=True, exist_ok=True)
        _m.write_text(json.dumps({'name': 'Cedwyn Estate', 'short_name': 'Cedwyn', 'start_url': '/' + _d.split('/')[0] + '/', 'display': 'browser'}))
_fetched = []
for _rel, _url in (('dartboard/data/roadmap.json', 'https://dartboard.righteous.workers.dev/data/roadmap.json'),
                   ('dartboard/data/forecast.json', 'https://dartboard.righteous.workers.dev/data/forecast.json'),
                   ('dartboard/data/foi-tracker.csv', 'https://dartboard.righteous.workers.dev/data/foi-tracker.csv'),
                   ('wayback/websites/index.json', 'https://raw.githubusercontent.com/unclehowell/datro/wayback/wayback/websites/index.json')):
    _dst = DIST / _rel
    if _dst.exists() or not (DIST / _rel.split('/')[0]).is_dir(): continue
    try:
        with _ur.urlopen(_ur.Request(_url, headers={'User-Agent': 'Mozilla/5.0 cedwyn-build'}), timeout=60) as _r:
            _b = _r.read(); _ct = _r.headers.get('Content-Type') or ''
        if 'html' in _ct or len(_b) < 50: continue
        if _rel.endswith('.json'): json.loads(_b)
        _dst.parent.mkdir(parents=True, exist_ok=True); _dst.write_bytes(_b); _fetched.append(_rel)
    except Exception:
        pass
print('P-031/P-033 pass:', _fixed, 'pages fixed,', 'fetched', _fetched)
lines += [
    "/data/roadmap.json /dartboard/data/roadmap.json 301",
    "/data/forecast.json /dartboard/data/forecast.json 301",
    "/data/foi-tracker.csv /dartboard/data/foi-tracker.csv 301",
    "/wiki/press-archive-transcripts/ /wiki/evidence-library/press-archive-transcripts/ 301",
    "/accounts/ledger/claimed.beancount /accounts/#dl 302",
    "/argentina/accounts/ledger/claimed.beancount /argentina/accounts/#dl 302",
    "/wales/accounts/ledger/claimed.beancount /wales/accounts/#dl 302",
    "/wiki/wp-content/uploads/2026/10/2026-05-28_rcahmw_rc26-0205_les08-order-form-2021.docx /wayback/go/?u=https%3A%2F%2Fgithub.com%2Funclehowell%2Fdatro%2Fblob%2Fwayback%2Fwayback%2Fpdf%2Ffoi%2F2026-05-28_rcahmw_rc26-0205_les08-order-form-2021.docx 302"
]
tr = DIST / '_theme_redirects.txt'
if tr.exists():
    for l in tr.read_text().splitlines():
        b = l.split()
        if len(b) >= 2 and b[1].startswith('http'):
            b[1] = '/wayback/go/?u=' + urllib.parse.quote(b[1], safe='')
        if len(b) >= 2: lines.append(' '.join(b))
dyn = [l for l in lines if '*' in l.split()[0] or ':' in l.split()[0]]
sta = [l for l in lines if l not in dyn]
(DIST / '_redirects').write_text('\n'.join(dyn[:90] + sta[:1900]) + '\n')
if len(dyn) > 90 or len(sta) > 1900:   # never drop rules silently (P-027)
    print('WARNING _redirects: dropped %d dynamic and %d static rules over the caps' % (max(0, len(dyn) - 90), max(0, len(sta) - 1900)))
# 29 Oct 2026 (P-040): no-transform stays on pages (keeps the zone's analytics snippet out) but is detached from the shared
# header/runtime scripts and the story bundle (no snippet goes into those; basecamp.js went out 161 KB raw), so Cloudflare compresses
# them again. Paths with their own Cache-Control (/_blob/, /db/, vendor, the service worker) are left as they were. - Sion's Tab agent
(DIST / '_headers').write_text('''/_blob/*
  Cache-Control: public, max-age=31536000, immutable
/_cedwyn/vendor/*
  Cache-Control: public, max-age=86400
/cedwyn-sw.js
  Cache-Control: no-cache
/db/blobmap.json
  Cache-Control: no-cache
/db/*
  Cache-Control: public, max-age=300
  Access-Control-Allow-Origin: *
/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
/_cedwyn/ghf/*
  ! Cache-Control
/_cedwyn/guestbook/*
  ! Cache-Control
/_cedwyn/section.js
  ! Cache-Control
/_cedwyn/agent-tools.js
  ! Cache-Control
/story/assets/*
  ! Cache-Control
''')   # 30 Oct 2026 (P-040): no-transform dropped from pages; the zone config rule for cedwyn.bucklerfamily.estate (disable_rum, no email obfuscation or rewrites) keeps pages byte-identical, so HTML now goes out brotli. - Sion's Tab agent
print('site ok', len(lines), 'redirects,', len(caps), 'captures')
sys.path.insert(0, str(ROOT / 'tools')); import agent_footer; agent_footer.run(DIST)   # THE TRIGGER EVENT section on /projects/ + agent footer on theme homes
import academy_pointer; academy_pointer.run(DIST)   # /llms.txt, /agents.json, robots.txt (only if absent) + one ai-agents meta per page -> /academy/ (Sion's Tab agent, 26 Oct 2026)
# Editorial rule (25 Oct 2026): ingredients, not conclusions - reword conclusion sentences in mirrored theme text (ingredients.json). - Sion's Tab agent
import ingredients
ingredients.apply(DIST)
# A crawled theme whose live site refused this build's crawl (e.g. 429) keeps its previous build's files (25 Oct 2026). - Sion's Tab agent
import keep_previous
keep_previous.run(DIST)
# P-034 (30 Oct 2026): the Post Office viewer reads /email/view/index.json, a copy of datro@wayback wayback/api/index.json that was
# placed by hand on 25 Oct; the email theme's crawl now meets a 301 to Cedwyn, so the copy froze. Refresh it from this build's
# Wayback Vault when the Vault's catalogue is newer (the redacted texts it points at are served from /wayback/mail/) - Sion's Tab agent
try:
    _pv_src = DIST / 'wayback' / 'api' / 'index.json'; _pv_dst = DIST / 'email' / 'view' / 'index.json'
    if _pv_src.is_file() and _pv_dst.parent.is_dir():
        _pv_new = json.load(open(_pv_src, encoding='utf-8'))
        _pv_old = json.load(open(_pv_dst, encoding='utf-8')) if _pv_dst.is_file() else {}
        if (_pv_new.get('records') and (_pv_new.get('generated') or '') > (_pv_old.get('generated') or '')
                and len(_pv_new['records']) >= len(_pv_old.get('records') or [])):
            shutil.copy2(_pv_src, _pv_dst)
            print('post office catalogue refreshed:', len(_pv_old.get('records') or []), '->', len(_pv_new['records']))
except Exception as _e:   # the mail catalogue must never stop a build
    print('post office catalogue refresh failed:', _e)
# Cross-institution route status map (snapshot dated from the dartboard source branch).
import dartboard_options
dartboard_options.run(DIST)
# Per-compartment notice boxes (notices/<theme>.json; forensic audit intake 25 Oct 2026) - Sion's Tab agent
import theme_notices
theme_notices.run(DIST)
# Chronology and outside records (Sion, 11:45 GMT 26 Oct 2026, m:1138070f): Tŷ Mawr first named 1824; Bute/third-party documents never shown as Tŷ Mawr records before 1824 - Sion's Tab agent
import chronology
chronology.run(DIST)
# Two sections over one database (Sion, 25 Oct 2026): landing tiles, /wales/ and /argentina/ hubs, section rewrites - Sion's Tab agent
import sections
sections.run(DIST, CFG)
# Two halves (Sion, 23:39 GMT 25 Oct 2026): landing = two tiles, /wales/ = AR guided tour, /argentina/ = Great House II retreat + package builder - Sion's Tab agent
import halves
halves.run(DIST, CFG)
# Title chain (Sion, 03:07 GMT 26 Oct 2026): /title-chain/ and its /wales/ and /argentina/ copies, under Past in both halves - Sion's Tab agent
import title_chain
title_chain.run(DIST, CFG)
# The e-book compartment: editions, versions and prices on /ebooks/ (data/ebooks.json) and the free-edition gate - Sion's Tab agent
import ebook_editions
ebook_editions.run(DIST)
# /ebooks/ as a shelf of poster cards: cover opens the free v0.0.1, version drop-down drives Buy/Read (27 Oct 2026) - Sion's Tab agent
import ebook_shelf
ebook_shelf.run(DIST)
# Headline-first story pages (Sion, 12:01 GMT 26 Oct 2026): section detail behind a native 'Read more' in every theme - Sion's Tab agent
import headlines
headlines.run(DIST)
# Archived-websites viewer (Sion, 13:28 GMT 26 Oct 2026): one title bar with back / previous / next on every snapshot page,
# a readable style-stripped copy, and #websites/<host>/<slug> links that open the copy under /wayback/ - Sion's Tab agent
import wayback_viewer
wayback_viewer.run(DIST)
# P-027 (29 Oct 2026): drop the two refresh stubs in each Vault copy (the WAYBACK_STUB_DYN rules answer for them) - Sion's Tab agent
_stub_n = 0
for _lh in (DIST / 'wayback' / 'websites').glob('*/*/latest.html'):
    for _nm in ('index.html', 'latest.htm'):
        _f = _lh.parent / _nm
        try:
            if _f.is_file() and _f.stat().st_size < 4096 and 'content="0;url=latest.html"' in _f.read_text(errors='ignore'):
                _f.unlink(); _stub_n += 1
        except OSError:
            pass
print('wayback stubs removed:', _stub_n)
# P-027 (b) (30 Oct 2026): wget saves 'x.js?v=1' as 'x.js@v=1'; Pages ignores the query and serves the bare 'x.js', and pages
# link the '?v=' form, so a versioned copy byte-identical to its bare sibling is never served. Drop those (about 1,060 files,
# mostly the docs Sphinx assets). Runs after keep_previous, which still reads the versioned copies - Sion's Tab agent
import filecmp as _fc_p027
_qdup_n = 0
for _qf in list(DIST.rglob('*@*')):
    _qm = _re.match(r'^(.+\.(?:js|css))@[^/]*$', _qf.name)
    if not _qm:
        continue
    _qb = _qf.parent / _qm.group(1)
    try:
        if _qf.is_file() and _qb.is_file() and _fc_p027.cmp(_qf, _qb, shallow=False):
            _qf.unlink(); _qdup_n += 1
    except OSError:
        pass
print('query-named duplicate assets removed:', _qdup_n)
# Level 2 observations + Level 1 catalogue browser, generated from the structured records - Sion, 29 Oct 2026
import evidence_observations
evidence_observations.run(DIST)
# Canonical parcel-by-parcel Title Theory model and simulation data, generated before the central DB build.
import title_theory
title_theory.run(DIST)
# Group source themes into the 36 public areas; preserve legacy routes and mark parcel slots as provisional.
import site_consolidations
site_consolidations.run(DIST)
# Q&A as questions (Sion, WhatsApp 00:54 GMT 30 Oct 2026): /qa/ and /wales/qa/ list each question asked, coloured hashtags of the
# institutions asked and of who answered, each opening the email on /email/reference/<id>/ - Sion's Tab agent
try:
    import qa_questions
    qa_questions.run(DIST)
except Exception as _e:   # the questions list must never stop a build
    print('qa_questions failed:', _e)
# Agent guest book (Sion, 01:51 GMT 26 Oct 2026): one collapsed table in the shared footer of every page, from main's commit
# history; /guestbook/ lists every commit. Runs last so every page the build made carries it - Sion's Tab agent
import guestbook
guestbook.run(DIST)
# Wiki word links + agent text out of human view (Sion, 22:12 GMT 26 Oct 2026, m:611a2587): glossary links, name-variant pop-ups,
# /glossary/; guest book and agent-routing blocks hidden on human pages (kept in source). Runs after the guest book - Sion's Tab agent
import wikilinks
wikilinks.run(DIST)
# Pages never explain themselves: self-describing, data-source and agent notes move to agent small print
# (hidden, kept in the source); the small-print footer gains a "Docs" link to /library/. Runs after the word links - docs library build
import quiet_pages
quiet_pages.run(DIST)
# Developer library (/library/, branch `library`, not a theme): database, hosting, front ends, sections, export, API/WebMCP.
# Copied last so no page pass rewrites it - docs library build
# "Cited on" (Sion, 27 Oct 2026): every artifact page (/research/evidence/ev-NNNN-*/, /wiki/evidence/ev-NNNN-*/) lists the
# pages that link to it, built from a scan of the real internal links in dist. Runs after the page passes - Sion's Tab agent
import cited_on
try:
    cited_on.main(str(DIST))
except Exception as _e:   # a backlink list must never stop a build
    print('cited_on failed:', _e)
import library_pointer
library_pointer.run(DIST)
# Social share previews (Sion, WhatsApp 05:29 GMT 27 Oct 2026): og:/twitter: tags on every page, share cards from the
# Garden Gallery pieces (tools/og_cards.json picks the piece per section). Head tags only; runs last - Sion's Tab agent
import og_cards
try:
    og_cards.run(DIST)
except Exception as _e:   # share tags must never stop a build
    print('og_cards failed:', _e)

# Graph promo + progressive Read more (asked for 01:27 GMT 30 Oct 2026): per-section scatter data for the header graph banner
# (/_cedwyn/graph/<area>.json, read by web/_cedwyn/cw-graph.js) and long list pages cut into <page>/_more/N.json chunks that
# cw-graph.js loads on "Read more". Runs after og_cards and cited_on; never stops a build - Sion's Tab agent
# readmore_chunks is parked (30 Oct 03:24 build): its _more/N.json chunks were written before privacy_scrub/selfcontain, whose
# HTML passes do not reach JSON-escaped HTML, so the privacy check failed on them. It needs its own step after those passes.
for _gm in ('graph_data',):
    try:
        __import__(_gm).run(DIST)
    except Exception as _e:
        print(_gm, 'failed:', _e)

# Shop strip (sales-fix sf28, 30 Oct 2026): one internal line to /ebooks/ at the top of the busiest entry pages that had no route
# to the shop (/hive/, /nomenclature/ and its name pages, /documentary/, /wayback/go/). /r/strip-<page> 302s to /ebooks/ so clicks
# are countable in Cloudflare. Idempotent; never stops a build - Sion's Tab agent
def _shop_strip(dist):
    import re as _re
    targets = [('hive/index.html', 'hive'), ('nomenclature/index.html', 'nomenclature'),
               ('documentary/index.html', 'documentary'), ('wayback/go/index.html', 'wayback-go')]
    targets += [(str(p.relative_to(dist)), 'nom-c') for p in sorted((dist / 'nomenclature' / 'c').glob('*/index.html'))]
    # sf35 (31 Oct 2026): section front pages with non-US entry traffic and no route to /ebooks/ (CF 3 days to 01:00Z),
    # plus the directory's business pages, the site's only pages Google ranks in the top 10 (local searches).
    for _s in ('directory', 'research', 'research/timeline', 'wiki', 'fb', 'accounts', 'glossary', 'authorities', 'records',
               'wdtk', 'email', 'review', 'meeting', 'watchtower', 'projects', 'courtdrills', 'csscpsg', 'infographic', 'docs',
               # sf40 (31 Oct 2026): document pages that real phone visitors (non-US, non-NL) reach with no route to /ebooks/ near
               # the top (CF 3 days to 16:00Z: fcg 56, oldbill 40, qa 29, cyberspace 21, thousand-cuts 18, emails 18; /wales/ and
               # /argentina/ serve the same file, so one strip covers all three). Full-screen apps (chess, maps, story) stay out.
               'fcg', 'oldbill', 'qa', 'cyberspace', 'thousand-cuts', 'emails'):
        targets.append((_s + '/index.html', _s.replace('/', '-')))
    # sf41 (31 Oct 2026): the Wales and Patagonia front pages are their own files (wales/index.html, argentina/index.html), not
    # copies of /, so the sf40 note above did not cover them and neither showed a strip (CF 3 days to 19:00Z, non-US excl. NL:
    # /wales/ 39, /argentina/ 22; the shop's only link on /argentina/ sat in the footer menu). The strip goes under the hero and
    # reuses the pages' own w_ebooks phrase, so it shows in Welsh / Spanish / English with the page's language switch.
    targets += [('wales/index.html', 'wales'), ('argentina/index.html', 'argentina')]
    targets += [(str(p.relative_to(dist)), 'dir') for p in sorted((dist / 'directory' / 'p').glob('*/index.html'))]
    # sf36 (31 Oct 2026): deep record pages (research articles, evidence records, wiki pages, kissed-frogs) took ~1,565 of
    # 6,612 non-US page loads in the 3 days to 04:05Z (9x /ebooks/) and had no route to the shop. Sections already tagged above win.
    for _pre in ('', 'wales/', 'argentina/'):
        for _sec in ('research', 'wiki', 'kissed-frogs'):
            for p in sorted((dist / (_pre + _sec)).rglob('index.html')) if (dist / (_pre + _sec)).is_dir() else []:
                _r = str(p.relative_to(dist))
                targets.append((_r, 'kf' if _sec == 'kissed-frogs' else 'ev' if 'evidence' in _r else 'art'))
    n = 0
    for rel, tag in targets:
        f = dist / rel
        if not f.is_file():
            continue
        h = f.read_text(encoding='utf-8')
        if 'class="ebook-strip"' in h:
            continue
        m = _re.search(r'<main\b[^>]*>', h)
        if not m and tag in ('fcg', 'oldbill'):  # sf40: these two have no <main>; under the first heading, else the top wrapper
            m = _re.search(r'</h1>', h) or _re.search(r'<div class="wrap">', h)
        if not m:
            continue
        text = ('Local history: Great House Farm (T&#375; Mawr), Llandough, 1667&ndash;1988, in the e-books. First edition free &rarr;'
                if tag in ('dir', 'directory') else
                'The full history of Great House Farm (T&#375; Mawr), from the records, is in the e-books: first edition free &rarr;'
                if tag in ('art', 'ev', 'kf') else 'Read the farm\'s history in the e-books: first edition free &rarr;')
        line = ('<p class="ebook-strip" style="margin:.5rem 0 .75rem;font-size:16px;line-height:1.4">'
                '<a href="/r/strip-%s">%s</a></p>' % (tag, text))
        at = m.end()
        if tag in ('wales', 'argentina'):  # sf41: under the hero header inside <main>, in the page's default language
            mh = _re.compile(r'</header>').search(h, m.end())
            at = mh.end() if mh else m.end()
            line = ('<p class="ebook-strip" style="margin:.75rem 0;font-size:16px;line-height:1.4">'
                    '<a href="/r/strip-%s" data-i18n="w_ebooks">%s</a></p>'
                    % (tag, 'E-lyfrau &middot; argraffiadau cyntaf am ddim' if tag == 'wales'
                       else 'Libros electr&oacute;nicos &middot; primeras ediciones gratis'))
        f.write_text(h[:at] + line + h[at:], encoding='utf-8')
        n += 1
    print('shop strip: added to', n, 'pages')
try:
    _shop_strip(DIST)
except Exception as _e:
    print('shop strip failed:', _e)

# Holdings wording (owner rule, 22:25 GMT 30 Oct 2026; P-104): public text never states whether the family holds a record; it names
# which other party should hold the original and what it has disclosed. Exact-phrase rewrites from data/holdings-wording.json over
# every page writer's output, before the catalogue database is built. Never stops a build - Sion's Tab agent
try:
    import holdings_wording
    holdings_wording.run(DIST)
except Exception as _e:
    print('holdings wording failed:', _e)

# Cloudflare Pages redirect quotas: validate the final file after every theme plugin has amended it.
_redirect_file = DIST / '_redirects'
_redirect_lines = _redirect_file.read_text(encoding='utf-8').splitlines() if _redirect_file.exists() else []
_redirect_dynamic = [x for x in _redirect_lines if x.split() and ('*' in x.split()[0] or ':' in x.split()[0])]
_redirect_static = [x for x in _redirect_lines if x.strip() and x not in _redirect_dynamic]
print('redirect quota:', len(_redirect_dynamic), '/100 dynamic;', len(_redirect_static), '/2000 static')
assert len(_redirect_dynamic) <= 100, 'Cloudflare Pages dynamic redirect quota exceeded after all route additions'
assert len(_redirect_static) <= 2000, 'Cloudflare Pages static redirect quota exceeded after all route additions'
