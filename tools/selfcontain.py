#!/usr/bin/env python3
"""selfcontain.py - make every theme page fully self-contained, then prove it. - Sion's Tab agent

  python3 tools/selfcontain.py dist --fix   rewrite every remaining reference, vendor CDN files, add the shared header
  python3 tools/selfcontain.py dist         strict test: exit 1 if ANY reference to a *.bucklerfamily.estate subdomain
                                            or an external host survives

A "reference" is a URL in: any HTML attribute (a/area/link href, script/img/iframe/source/video/audio/embed src,
srcset, poster, object data, form action/formaction, meta content, data-* attributes, cite, xlink:href ...), inline
<script> and <style> blocks (JSON-LD included), and every .js .mjs .css .json .webmanifest .svg .xml file (fetch/XHR
URLs, nav JSON, data feeds). Visible text and HTML comments are not references and are left as written.
Rewrites: a former subdomain (or apex path) -> /<theme>/...; a CDN script/style/font -> a vendored copy under
/_ext/<host>/...; anything else -> the archive interface /wayback/go/?u=<address>. XML namespace URIs are names, not
references. Map-tile URL templates listed in themes.json "allowed_tile_templates" are the only stated exception.
The shared 3-row header (ghf-boot.js -> basecamp.js) is served from /_cedwyn/ghf/ and added to every theme page.
"""
import json, re, sys, os, pathlib, hashlib, html, urllib.parse, urllib.request, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'themes.json'))
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('-') else 'dist')
FIX = '--fix' in sys.argv
ONLY = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--only=')]
SELF = 'cedwyn.bucklerfamily.estate'
ABS = 'https://' + SELF
BOOT = '/_cedwyn/ghf/ghf-boot.js?v=2.1.19'
TIDS = [t['id'] for t in CFG['themes']]
HOST = {}
for t in CFG['themes']:
    for h in t.get('hosts', []):
        if h not in ('bucklerfamily.estate', 'www.bucklerfamily.estate'): HOST[h.lower()] = t['id']
for h, tid in CFG.get('extra_hosts', {}).items():
    if tid: HOST[h.lower()] = tid
APEX = sorted(CFG['apex']['paths'].items(), key=lambda kv: -len(kv[0]))
TILES = CFG.get('allowed_tile_templates', [])
CHECKOUT = ('buy.stripe.com', 'checkout.stripe.com', 'gumroad.com')   # checkout links stay direct (see classify)
# 31 Oct 2026 (P-114): the WordPress copy's privacy script asks public-api.wordpress.com/geo/ for the visitor's region with an
# XHR and JSON.parse()s the answer. Sent to /wayback/go/ it got an HTML page and threw "Unexpected token '<' ... is not valid
# JSON" on every wiki page. It now gets an empty JSON answer as a data: address (region '' = no state privacy rule applies; no
# outbound request). GEO_DONE also repairs pages rewritten by earlier builds. - Sion's Tab agent
GEO_EMPTY = 'data:application/json,%7B%7D'
GEO_DONE = re.compile(r'(?:https://cedwyn\.bucklerfamily\.estate)?/wayback/go/\?u=https%3A%2F%2Fpublic-api\.wordpress\.com%2Fgeo%2F', re.I)
NS = {'www.w3.org', 'w3.org', 'schema.org', 'purl.org', 'ogp.me', 'xmlns.com', 'ns.adobe.com', 'www.inkscape.org',
      'sodipodi.sourceforge.net', 'creativecommons.org', 'www.openarchives.org', 'www.sitemaps.org', 'docs.oasis-open.org',
      'rdfs.org', 'web.resource.org', 'www.google.com/schemas', 'search.yahoo.com', 'ns.attribution.cloudflare.com'}
CDN = {'cdn.jsdelivr.net', 'unpkg.com', 'cdnjs.cloudflare.com', 'fonts.googleapis.com', 'fonts.gstatic.com', 'ajax.googleapis.com',
       's0.wp.com', 's1.wp.com', 's2.wp.com', 'i0.wp.com', 'i1.wp.com', 'i2.wp.com', 's-ssl.wordpress.com'}   # the WordPress wiki's theme styles, scripts and resized images
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
# a URL: scheme-ful (also JSON-escaped https:\/\/), or protocol-relative right after a quote/paren/equals/space
URL = re.compile(r'''(?:(?<![\w.+-])(https?:)(//|\\/\\/)|(?<=["'(=`])(//))([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+)(:\d+)?((?:/|\\/)[^\s"'<>`\\]*(?:\\/[^\s"'<>`\\]*)*)?''', re.I)
stats = {'files': 0, 'changed': 0, 'sub': 0, 'ext': 0, 'cdn': 0, 'boot_added': 0, 'boot_moved': 0, 'tags_dropped': 0}
left = {}; examples = {}; vendor = {}; tiles_seen = set()

def theme_url(host, path):
    if host in ('bucklerfamily.estate', 'www.bucklerfamily.estate'):
        for pre, tid in APEX:
            if path.startswith(pre) or path + '/' == pre:
                return '/' + tid + '/' + path[len(pre):].lstrip('/')
        return None
    tid = HOST.get(host)
    if tid: return '/' + tid + (path if path.startswith('/') else ('/' + path if path else ''))
    return None

def ext_local(host, path, query):
    """vendored path for a CDN file (the query, e.g. Google Fonts families, is folded into the file name)"""
    p = path or '/'
    if query:
        h = hashlib.sha1(query.encode()).hexdigest()[:10]
        base, dot, ext = p.rpartition('.')
        p = (p.rstrip('/') or '/index') + '.' + h + ('.css' if host == 'fonts.googleapis.com' else '')
    if p.endswith('/'): return '/_ext/' + host + p          # a folder prefix that scripts add file names to
    return '/_ext/' + host + p

OWN_MEDIA = re.compile(r'(?i)^(?:(?:github\.com)/unclehowell/[^/]+/releases/download/|(?:raw|media)\.githubusercontent\.com/(?:media/)?unclehowell/)[^?#]*\.(?:webm|mp4|m4v|mov|mp3|m4a|ogg|opus|wav|vtt|png|jpe?g|webp|gif|avif)(?:[?#].*)?$')
def own_media(host, path):
    """a file in our own GitHub repos (release asset or raw file) that is a video, audio, subtitle or image"""
    return bool(OWN_MEDIA.match(host + (path or '')))

def classify(m):
    host = m.group(4).lower(); path = (m.group(6) or '').replace('\\/', '/')
    full = m.group(0).replace('\\/', '/')
    if host == SELF: return 'self', None
    hp = host + path
    if host in NS or any(hp.startswith(n) for n in NS if '/' in n): return 'ns', None
    if any(full.startswith(t) for t in TILES):
        return 'tile', None
    # 25 Oct 2026: any address a theme was served from (every *.bucklerfamily.estate site, and the Legal Wiki's own
    # greathousefarmwiki.wordpress.com) is a theme link: it goes to the internal /<theme>/ route, never to /wayback/go/
    if host in HOST or host == 'bucklerfamily.estate' or host.endswith('.bucklerfamily.estate'):
        return 'sub', None
    if host in CDN: return 'cdn', None
    # 27 Oct 2026: e-book Buy buttons go straight to checkout (Sion 13:01: never the interstitial; a payment step is not archived)
    if host in CHECKOUT or host.endswith('.gumroad.com'): return 'ns', None
    # 29 Oct 2026 (P-041): Stripe's buy-button script must load from js.stripe.com itself (Stripe requires it); it is part of
    # the checkout, like the Buy links above, so it is neither archived nor vendored. - Sion's Tab agent
    if host == 'js.stripe.com': return 'ns', None
    # 30 Oct 2026: our own film and image files (release downloads and raw files of the unclehowell repos) are media sources,
    # not outbound links: a <video>/<img> src or poster must be the file itself. /wayback/go/ answers an HTML page, which a
    # video element cannot play (the Dartboard's floating film showed only its poster this way). - Sion's Tab agent
    if own_media(host, path): return 'ns', None
    # a YouTube thumbnail whose video was checked (oEmbed author) and is not from the excluded channel: copied as an image
    if host == 'i.ytimg.com' and any('/vi/' + v + '/' in path for v in CFG.get('ytimg_checked', {})): return 'cdn', None
    # 30 Oct 2026: a YouTube player the site owner asked to embed (themes.json "yt_embed_allowed", by video id) stays a direct
    # youtube-nocookie embed: /wayback/go/ answers an HTML page, which an <iframe> player cannot play. - Sion's Tab agent
    if host in ('www.youtube-nocookie.com', 'youtube-nocookie.com') and any(path.startswith('/embed/' + v) for v in CFG.get('yt_embed_allowed', {})): return 'ns', None
    # 31 Oct 2026 (P-105): the click-to-play facade script (button.yt-facade) assembles its player address at run time as
    # 'https://www.youtube-nocookie.com/embed/' + data-yt; that bare prefix carries no id, so it fell to /wayback/go/ and the
    # old 'Wales at Six' Video 1 on /research/ loaded an HTML page instead of a player. The bare prefix stays direct; the ids
    # are the authored data-yt attributes, listed with their oEmbed check in themes.json. - Sion's Tab agent
    if host in ('www.youtube-nocookie.com', 'youtube-nocookie.com') and path == '/embed/': return 'ns', None
    if host == 'public-api.wordpress.com' and path.startswith('/geo'): return 'geo', None   # P-114, see GEO_EMPTY
    return 'ext', None

def replacement(m, absctx, css=False):
    kind, _ = classify(m)
    raw = m.group(0)
    if kind in ('self', 'ns'): return raw, None
    if kind == 'geo': return GEO_EMPTY, None
    esc = '\\/' in raw
    host = m.group(4).lower(); full = raw.replace('\\/', '/')
    if not full.lower().startswith('http'): full = 'https:' + full
    if kind == 'tile':
        tiles_seen.add(full[:120]); return raw, None
    pre = ABS if absctx else ''
    path_q = (m.group(6) or '').replace('\\/', '/')
    pm = re.match(r'([^?#]*)([?#].*)?$', path_q, re.S); path, rest = pm.group(1), pm.group(2) or ''
    if kind == 'sub':
        t = theme_url(host, path)
        if t is not None:
            if not path and t.endswith('/') and t.count('/') == 2 and not absctx: pass
            if not path: t = t.rstrip('/') if t.count('/') > 1 else t
            out = pre + t + rest
            return (out.replace('/', '\\/') if esc else out), 'sub'
    if kind == 'cdn':
        q = rest[1:] if rest.startswith('?') else ''
        q = html.unescape(q)
        loc = ext_local(host, path, q)
        vendor[loc] = full if not q else 'https://' + host + path + '?' + q
        out = pre + loc if absctx else loc
        return (out.replace('/', '\\/') if esc else out), 'cdn'
    # external, or a former subdomain cedwyn has no theme for: the archive interface
    target = html.unescape(full)
    out = pre + '/wayback/go/?u=' + urllib.parse.quote(target, safe='')
    if css: out = out.replace('(', '%28').replace(')', '%29')
    return (out.replace('/', '\\/') if esc else out), ('sub' if kind == 'sub' else 'ext')

TPL = re.compile(r'''(?:https?:)?//\{[a-z]\}\.([a-z0-9-]+(?:\.[a-z0-9-]+)+)[^\s"'<>`]*''', re.I)   # e.g. //{s}.tile.example.org/{z}/{x}/{y}.png
def process_text(s, absctx, css=False, where=None):
    for m in TPL.finditer(s):
        full = m.group(0) if m.group(0).startswith('http') else 'https:' + m.group(0)
        if any(full.startswith(t) for t in TILES): tiles_seen.add(full[:120])
        elif not FIX and where:
            key = (where[0], 'ext'); left[key] = left.get(key, 0) + 1; examples.setdefault(key, []).append(where[1] + ' :: ' + full[:100])
    """rewrite (FIX) or count every URL in a JS/CSS/JSON/attribute string"""
    if FIX:
        def r(m):
            out, k = replacement(m, absctx, css)
            if k: stats['cdn' if k == 'cdn' else k] += 1
            return out
        return URL.sub(r, s)
    for m in URL.finditer(s):
        kind, _ = classify(m)
        if kind in ('sub', 'ext', 'cdn'):
            key = (where[0], kind); left[key] = left.get(key, 0) + 1
            examples.setdefault(key, []).append(where[1] + ' :: ' + m.group(0)[:100]) if len(examples.get(key, [])) < 3 else None
        elif kind == 'tile': tiles_seen.add(m.group(0)[:120])
    return s

TAG = re.compile(r'<(/?)([a-zA-Z][\w:-]*)(\s[^<>]*?)?(/?)>', re.S)
ATTR = re.compile(r'''(\s)([^\s=/>"']+)(\s*=\s*)("[^"]*"|'[^']*'|[^\s>"']+)''', re.S)
BLOCK = re.compile(r'(<(script|style)\b[^>]*>)(.*?)(</\2\s*>)', re.S | re.I)
COMMENT = re.compile(r'<!--.*?-->', re.S)
DROP_SCRIPT = re.compile(r'<script\b[^>]*\bsrc\s*=\s*["\'][^"\']*followers\.bucklerfamily\.estate/follow\.js[^"\']*["\'][^>]*>\s*</script>', re.I)
GHF_SRC = re.compile(r'''(?<=["'=])((?:https?:)?//(?:www\.)?bucklerfamily\.estate|/dartboard|[^"'\s>=]*?)/?(?:ghf-lang/(ghf-boot|ghf-lang|basecamp)|(basecamp))\.js(\?[^"'\s>]*)?(?=["'\s>])''', re.I)
# P-136 (31 Oct 2026): inside a JSON string a link ends at an escaped quote (backslash + quote). The old tail class ate the
# backslash of that escape (or of a backslash-n) and left a bare quote, so story/api/qa.json came out as invalid JSON and the
# privacy scrub failed build 531e0a8. A backslash is now taken only as a whole JSON escape (backslash-slash or \uXXXX). — Sion's Tab agent
_YTC = r"""(?:\\/|\\u[0-9A-Fa-f]{4}|[^"'\s<>()\\])"""
YTBLOCK = re.compile(r'''(?:/wayback/go/\?u=|https?:(?:\\?/){2}|(?<=["'=(])//)'''+_YTC+r'''*?(?:sionbuckler5713|UC2sN1VEs1WeLfBH8VmbvLWw|c0UvjM-lwA)'''+_YTC+r'''*''')
INLINE_BOOT = re.compile(r'<script\b[^>]*data-ghf-boot-inline[^>]*>.*?</script>\s*', re.I | re.S)
TOUR_TAG = re.compile(r'<script\b[^>]*(?:estate-tour\.js|data-estate-tour-loader)[^>]*>\s*</script>\s*', re.I)
TOUR_SHELL = re.compile(r'<header\b[^>]*data-estate-tour-shell[^>]*>.*?</header>\s*', re.I | re.S)
TOUR_NAV = re.compile(r'<nav\b[^>]*data-estate-tour-nav[^>]*>.*?</nav>\s*', re.I | re.S)
TOUR_SRC = re.compile(r'''(?:https?:)?//research\.bucklerfamily\.estate/estate-tour\.js(\?[^"'\s>]*)?''', re.I)

def fix_attr(tag, name, val, tagtext, page):
    lname = name.lower()
    if lname.startswith('xmlns'): return val
    absctx = lname == 'content' or (tag == 'link' and re.search(r'rel\s*=\s*["\']?[^"\'>]*(canonical|alternate|shortlink)', tagtext, re.I) is not None)
    absctx = absctx or lname in ('itemid', 'itemtype')
    if val.lstrip().startswith('//'):   # a protocol-relative value (src="//host/x.js") has no quote in front of it once unquoted
        return process_text('=' + val, absctx, css=(lname == 'style'), where=page)[1:]
    return process_text(val, absctx, css=(lname == 'style'), where=page)

def do_tag(m, page):
    whole = m.group(0); tag = m.group(2).lower(); attrs = m.group(3)
    if not attrs or m.group(1): return whole
    if tag == 'link' and FIX and re.search(r'rel\s*=\s*["\']?\s*(preconnect|dns-prefetch)', attrs, re.I):
        hm = URL.search(attrs)
        if hm and classify(hm)[0] in ('ext', 'cdn', 'sub'): stats['tags_dropped'] += 1; return ''
    def a(mm):
        q = mm.group(4); quote = q[0] if q[0] in '"\'' else ''; inner = q[1:-1] if quote else q
        new = fix_attr(tag, mm.group(2), inner, whole, page)
        return mm.group(1) + mm.group(2) + mm.group(3) + quote + new + quote if new != inner else mm.group(0)
    return '<' + m.group(1) + m.group(2) + ATTR.sub(a, attrs) + m.group(4) + '>'

def do_html(s, page):
    if FIX:
        n0 = len(s)
        s, k = DROP_SCRIPT.subn('', s); stats['tags_dropped'] += k
        # Sion 25 Oct 00:59: the second bar ("Estate website tour") is removed everywhere; only the 3-row header stays
        s, k1 = TOUR_TAG.subn('', s); s, k2 = TOUR_SHELL.subn('', s); s, k3 = TOUR_NAV.subn('', s)
        s, k4 = INLINE_BOOT.subn('', s)   # an inlined older ghf-boot (strict-CSP sites) would win over the vendored one and load the header from the old host
        stats['inline_boot_removed'] = stats.get('inline_boot_removed', 0) + k4
        stats['tour_removed'] = stats.get('tour_removed', 0) + k1 + k2 + k3
        def ghf(m):
            pre = m.group(1) or ''
            if pre.startswith('/_cedwyn/'): return m.group(0)
            if m.group(3) and not re.match(r'(?:https?:)?//(?:www\.)?bucklerfamily\.estate$|/dartboard$', pre): return m.group(0)
            return '/_cedwyn/ghf/' + (m.group(2) or m.group(3)) + '.js?v=2.1.6'
        s = GHF_SRC.sub(ghf, s)
        s, k5 = GEO_DONE.subn(GEO_EMPTY, s); stats['geo_fixed'] = stats.get('geo_fixed', 0) + k5   # P-114
    # split into comments / script+style blocks / markup, keep comments and text as written
    out = []; pos = 0
    tokens = sorted([(mm.start(), mm.end(), 'c', mm) for mm in COMMENT.finditer(s)] + [(mm.start(), mm.end(), 'b', mm) for mm in BLOCK.finditer(s)])
    spans = []; last = -1
    for st, en, k, mm in tokens:
        if st < last: continue
        spans.append((st, en, k, mm)); last = en
    def markup(chunk): return TAG.sub(lambda m: do_tag(m, page), chunk)
    for st, en, k, mm in spans:
        out.append(markup(s[pos:st]))
        if k == 'c': out.append(s[st:en])
        else:
            open_, kind, body, close = mm.group(1), mm.group(2).lower(), mm.group(3), mm.group(4)
            open_ = markup(open_)
            if kind == 'style': body = process_text(body, False, css=True, where=page)
            else:
                ty = re.search(r'type\s*=\s*["\']?([^"\'\s>]+)', open_, re.I); ty = ty.group(1).lower() if ty else ''
                if ty in ('text/template', 'text/x-template', 'text/html'): body = do_html(body, page)
                else: body = process_text(body, True, where=page)
            out.append(open_ + body + close)
        pos = en
    out.append(markup(s[pos:]))
    s = ''.join(out)
    return s

def add_boot(s, rel):
    """Shared GHF header and Cedwyn's central-catalogue agent tools on every published HTML page."""
    if not re.search(r'</head\s*>', s, re.I): return s
    if rel.startswith(('db/', '_blob/', '_ext/', '_cedwyn/')): return s
    s2, k = re.subn(r'<script\b[^>]*src\s*=\s*["\']/_cedwyn/ghf/ghf-boot\.js[^"\']*["\'][^>]*>\s*</script>\s*', '', s, flags=re.I)
    header_tag = '<script src="' + BOOT + '"></script>'
    s3 = re.sub(r'</head\s*>', lambda m: header_tag + m.group(0), s2, count=1, flags=re.I)
    if k == 0: stats['boot_added'] += 1
    elif s3 != s: stats['boot_moved'] += 1

    # The home-page footer injects this on theme indexes, but nested evidence pages need it too.
    # Do not gate on navigator.modelContext: modern browsers expose document.modelContext instead.
    if not re.search(r'<script\b[^>]*src\s*=\s*["\'][^"\']*/_cedwyn/agent-tools\.js(?:[?#][^"\']*)?["\']', s3, re.I):
        agent_tag = '<script src="/_cedwyn/agent-tools.js?v=1" defer data-cedwyn-agent-tools></script>'
        s3 = re.sub(r'</head\s*>', lambda m: agent_tag + m.group(0), s3, count=1, flags=re.I)
        stats['agent_tools_added'] = stats.get('agent_tools_added', 0) + 1
    return s3

APEX_THEMES = ["estate", "patagonia", "wales", "cyberspace"]
APEX_ROOT_DIRS = ["1d", "3d", "campus", "webapp", "_headers", "_redirects", "accessibility", "ai-policy", "brand", "choose", "cookies", "disclaimer", "ebook", "enemy", "enquire", "evidence", "fonts", "ghf-lang", "legal", "licence", "locations-img", "press", "privacy", "terms", "cdn-cgi", "assets"]
APEXFIX = re.compile(r'(?<=["\'(=`])/(' + '|'.join(APEX_THEMES) + r')/(' + '|'.join(re.escape(d) for d in APEX_ROOT_DIRS) + r')/')
def apex_root(s):
    """pages of the apex-path themes (/wales/, /patagonia/ ...) name the apex site's own root folders (/fonts/, /ghf-lang/,
    /locations-img/ ...): those live at the apex root, i.e. the dartboard theme, not inside the theme"""
    def r(m):
        d = m.group(2)
        if d == 'ghf-lang': return '/_cedwyn/ghf/'
        return '/dartboard/' + d + '/'
    s = APEXFIX.sub(r, s)
    # stage-1 prefixed the apex paths once more: /wales/wales/..., /cyberspace/cyberspace/, /estate/cedwyn/... -> that theme's root
    return APEXDUP.sub(lambda m: '/' + APEX_KEY_THEME[m.group(1)] + '/', s)
APEX_KEY_THEME = {'cedwyn': 'estate', 'patagonia': 'patagonia', 'wales': 'wales', 'cyberspace': 'cyberspace'}
APEXDUP = re.compile(r'(?<=["\'(=`])/(?:' + '|'.join(APEX_THEMES) + r')/(cedwyn|patagonia|wales|cyberspace)/')

TEXT_EXT = {'.html', '.htm', '.js', '.mjs', '.cjs', '.css', '.json', '.webmanifest', '.svg', '.xml', '.map'}
def files():
    for p in DIST.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXT: continue
        rel = p.relative_to(DIST).as_posix()
        if rel.startswith(('db/', '.git/', '_blob/')) or '/.git/' in rel: continue
        if rel.startswith('_cedwyn/reports/') or rel.endswith('.map'): continue
        if ONLY and rel.split('/')[0] not in ONLY: continue
        yield p, rel

def run(only_paths=None):
    it = files() if only_paths is None else ((p, p.relative_to(DIST).as_posix()) for p in only_paths if p.suffix.lower() in TEXT_EXT)
    for p, rel in it:
        try: s = p.read_text('utf-8')
        except Exception:
            try: s = p.read_bytes().decode('latin-1')
            except Exception: continue
        stats['files'] += 1
        ext = p.suffix.lower(); theme = rel.split('/')[0] if '/' in rel else '(root)'
        page = (theme, rel)
        if FIX and theme in APEX_THEMES: s0 = s; s = apex_root(s)
        else: s0 = s
        if ext in ('.html', '.htm'):
            n = do_html(s, page)
            if FIX: n = add_boot(n, rel)
        elif ext == '.css': n = process_text(s, False, css=True, where=page)
        elif ext == '.svg' or ext == '.xml': n = do_html(s, page) if '<' in s[:2000] else process_text(s, True, where=page)
        else: n = process_text(s, True, where=page)
        if FIX and rel != '_cedwyn/runtime.js':   # standing rule: never link that YouTube channel or its videos
            n, kb = YTBLOCK.subn('#', n)
            if kb: stats['yt_links_removed'] = stats.get('yt_links_removed', 0) + kb
        if FIX and n != s0:
            p.write_text(n, 'utf-8'); stats['changed'] += 1

def fetch_vendor():
    """download each vendored CDN file once; CSS is scanned for its own url()s (fonts) recursively"""
    done = set(); got = 0; failed = []
    def get(loc, url):
        dst = DIST / loc.lstrip('/')
        if loc.endswith('/'): return loc, None, 'folder'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r: b = r.read()
            dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b); return loc, b, None
        except Exception as e: return loc, None, str(e)[:80]
    for u in CFG.get('vendor_extra', []):   # module files reached only through an import-map folder prefix (three.js add-ons)
        su = urllib.parse.urlsplit(u); vendor.setdefault(ext_local(su.hostname, su.path, ''), u)
    queue = dict(vendor)
    while queue:
        batch = {k: v for k, v in queue.items() if k not in done and not (DIST / k.lstrip('/')).exists()}; queue = {}
        with cf.ThreadPoolExecutor(12) as ex:
            for loc, b, err in ex.map(lambda kv: get(*kv), batch.items()):
                done.add(loc)
                if err == 'folder': continue
                if err: failed.append([loc, batch[loc], err]); continue
                got += 1
                if loc.endswith('.css') or 'fonts.googleapis.com' in loc:
                    css = b.decode('utf-8', 'ignore'); base = batch[loc]
                    def cu(mm):
                        u = mm.group(2).strip('\'"')
                        if u.startswith('data:'): return mm.group(0)
                        absu = urllib.parse.urljoin(base, u); pu = urllib.parse.urlsplit(absu)
                        if pu.netloc.lower() not in CDN: return mm.group(0)
                        l2 = ext_local(pu.netloc.lower(), pu.path, pu.query); queue[l2] = absu
                        return mm.group(1) + l2 + mm.group(3)
                    css2 = re.sub(r'''(url\(\s*['"]?)([^'")]+)(['"]?\s*\))''', cu, css)
                    (DIST / loc.lstrip('/')).write_text(css2, 'utf-8')
    # folder prefixes (scripts add file names): fetch the files the pages name next to them
    for loc, url in vendor.items():
        if not loc.endswith('/'): continue
        for name in ('pdf.min.js', 'pdf.worker.min.js', 'pdf.min.mjs', 'pdf.worker.min.mjs', 'pdf.js', 'pdf.worker.js', 'pdf.mjs', 'pdf.worker.mjs'):
            if 'pdfjs-dist' not in loc: break
            l, b, err = get(loc + name, url + name)
            if not err: got += 1
    return got, failed

MEDIA_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.avif', '.ico', '.bmp', '.pdf', '.mp3', '.m4a', '.ogg', '.wav', '.mp4', '.webm', '.mov',
             '.woff', '.woff2', '.ttf', '.otf', '.js', '.mjs', '.css', '.json', '.vtt', '.txt', '.csv', '.wasm'}
LOCALREF = re.compile(r'''(?<=["'(=\s,])/([a-z0-9][a-z0-9-]*)/([^\s"'<>`()\\?#]+\.([a-z0-9]{2,5}))(?=[\s"'<>`()\\?#,])''', re.I)
CRAWLED = {t['id'] for t in CFG['themes'] if t.get('crawl') or t.get('crawl_fallback') or t.get('crawl_first') or t.get('wp_copy')}
RELREF = re.compile(r'''["'`]((?:\.{1,2}/|/)?[\w@-][\w@.%-]*(?:/[\w@.%-]+)*\.(?:jpe?g|png|gif|webp|svg|avif|glb|gltf|bin|hdr|json|js|mjs|css|woff2?|mp4|webm|mp3|pdf|wasm|txt|csv))(?:\?[^"'`]*)?["'`]''', re.I)
ROOTREF = re.compile(r'''(\s(?:href|src|action|poster|data-src|content)\s*=\s*["']?)(/(?!/)[^"'\s>]*)''', re.I)
def prefix_root(s, url, tid):
    """a page copied from a live site after rewrite.py ran: its root paths (/assets/x.js) name that site's root, so they
    become the theme's (/story/assets/x.js), the same as rewrite.py does for every built page"""
    host = url.split('/')[2].lower()
    def r(m):
        p = m.group(2)
        if p.startswith(('/_cedwyn/', '/_ext/', '/_blob/', '/db/', '/wayback/', '/graphql', '/catalogue')): return m.group(0)
        t = theme_url(host, p)
        return m.group(1) + (t if t is not None else '/' + tid + p)
    return ROOTREF.sub(r, s)

def fill_missing(dry=False, scan=None):
    """files a theme page names under /<theme>/ that the theme's branch copy does not hold (the old site served them from
    elsewhere): copied read-only from the theme's live address, so images, videos and scripts load from cedwyn itself"""
    exists = None
    if os.environ.get('CEDWYN_EXISTS_LIST'): exists = set(open(os.environ['CEDWYN_EXISTS_LIST']).read().split('\n'))
    live = {}
    for t in CFG['themes']:
        base = t.get('crawl') or t.get('live')
        if base: live[t['id']] = base.rstrip('/') + '/'
    # P-037 (31 Oct 2026): themes marked "no_fill" in themes.json are never filled from their live address. The email theme's live
    # Worker no longer serves /api/message/*.json, /mail/*.txt, /text-corpus-N.json or /mail-index.json (the texts are served from
    # /wayback/mail/), so every build asked it for about 2,000 files that all answered 404: about 47.5k Worker requests a day,
    # half of the account's free daily limit, for nothing. - Sion's Tab agent
    NOFILL = {t['id'] for t in CFG['themes'] if t.get('no_fill')}
    want = {}
    for p, rel in files():
        if p.suffix.lower() not in ('.html', '.htm', '.json', '.css', '.js'): continue
        try: s = p.read_text('utf-8', 'ignore')
        except Exception: continue
        for m in LOCALREF.finditer(s):
            tid, rest, ext = m.group(1), m.group(2), '.' + m.group(3).lower()
            if tid not in live or tid in NOFILL or ext not in MEDIA_EXT: continue
            relp = urllib.parse.unquote(tid + '/' + rest)
            ok = (relp in exists) if exists is not None else (DIST / relp).exists()
            if not ok: want[relp] = live[tid] + urllib.parse.quote(urllib.parse.unquote(rest))
    # crawled themes (apps the crawler could not follow): files their scripts name by relative or root path
    for p in (scan or []):
        rel = p.relative_to(DIST).as_posix(); tid = rel.split('/')[0]
        if tid not in CRAWLED or tid not in live or tid in NOFILL or p.suffix.lower() not in ('.js', '.mjs', '.json', '.css', '.html'): continue
        try: s = p.read_text('utf-8', 'ignore')
        except Exception: continue
        for m in RELREF.finditer(s):
            ref = m.group(1)
            if ref.startswith('/'):
                first = ref.split('/')[1]
                if first in live or first.startswith('_'): continue
                relp = tid + ref
            else:
                relp = os.path.normpath(os.path.join(os.path.dirname(rel), ref)).replace(os.sep, '/')
                if not relp.startswith(tid + '/'): continue
            ok = (relp in exists) if exists is not None else (DIST / relp).exists()
            if not ok and relp not in want: want[relp] = live[tid] + urllib.parse.quote(relp[len(tid) + 1:])
    IMGNAME = re.compile(r'"(?:\./)?(?:images/)?([^"/\\<>]{3,200}\.(?:jpe?g|png|webp|gif))"', re.I)
    for th in ('wayback',):
        d = DIST / th
        for p in list(d.glob('*.json')) + list(d.glob('*/*.json')) + list(d.glob('*.js')) + list(d.glob('*.html')):
            try: s = p.read_text('utf-8', 'ignore')
            except Exception: continue
            for m in IMGNAME.finditer(s):
                name = m.group(1)
                if name.startswith(('http', '.')) or len(want) > 6000: continue
                relp = th + '/images/' + name
                ok = (relp in exists) if exists is not None else (DIST / relp).exists()
                if not ok and relp not in want: want[relp] = live[th] + 'images/' + urllib.parse.quote(name)
    if dry: return want, []
    LIMIT_FILE = 24 * 1024 * 1024; budget = [int(os.environ.get('CEDWYN_FILL_MB', '600')) * 1024 * 1024]; got = []; miss = []
    def get(item):
        relp, url = item
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                ct = r.headers.get('Content-Type', ''); n = int(r.headers.get('Content-Length') or 0)
                if 'text/html' in ct and not relp.endswith(('.html', '.htm')): return relp, None, 'html fallback (not on the live site either)'
                if n > LIMIT_FILE: return relp, None, 'over 24 MB'
                b = r.read(LIMIT_FILE + 1)
            if len(b) > LIMIT_FILE: return relp, None, 'over 24 MB'
            return relp, b, None
        except Exception as e: return relp, None, str(e)[:60]
    with cf.ThreadPoolExecutor(16) as ex:
        for relp, b, err in ex.map(get, sorted(want.items())[:4000]):
            if err or budget[0] - len(b) < 0: miss.append([relp, err or 'budget']); continue
            budget[0] -= len(b); dst = DIST / relp; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b); got.append(relp)
    return want, (got, miss)

IMPORT_REL = re.compile(r'''(?:\bfrom\s*|\bimport\s*\(?\s*)["'](\.{1,2}/[^"']+)["']''')
def module_deps():
    """ES modules: relative imports inside vendored files, and bare specifiers that an importmap sends to a vendored folder"""
    new = {}
    for loc, url in list(vendor.items()):
        f = DIST / loc.lstrip('/')
        if loc.endswith('/') or not f.is_file() or f.suffix not in ('.js', '.mjs'): continue
        for m in IMPORT_REL.finditer(f.read_text('utf-8', 'ignore')):
            u2 = urllib.parse.urljoin(url, m.group(1)); p2 = urllib.parse.urlsplit(u2)
            l2 = ext_local(p2.netloc.lower(), p2.path, '')
            if l2 not in vendor: new[l2] = u2
    maps = {}
    for p in DIST.rglob('*.htm*'):
        try: s = p.read_text('utf-8', 'ignore')
        except Exception: continue
        for mm in re.finditer(r'<script[^>]*type=["\']?importmap["\']?[^>]*>(.*?)</script>', s, re.S | re.I):
            try: im = json.loads(mm.group(1)).get('imports', {})
            except Exception: continue
            for k, v in im.items():
                if k.endswith('/') and '/_ext/' in v:
                    loc = v[v.index('/_ext/'):]; maps[k] = (loc, 'https://' + loc[len('/_ext/'):])
    if maps:
        rx = re.compile(r'''["'](' + '|'.join(re.escape(k) for k in maps) + r')([^"'\s]+)["']''')
        for p in list(DIST.rglob('*.js')) + list(DIST.rglob('*.mjs')) + list(DIST.rglob('*.htm*')):
            if '/db/' in p.as_posix(): continue
            try: s = p.read_text('utf-8', 'ignore')
            except Exception: continue
            for m in rx.finditer(s):
                loc, url = maps[m.group(1)]
                if loc + m.group(2) not in vendor: new[loc + m.group(2)] = url + m.group(2)
    vendor.update(new); return len(new)

def main():
    run()
    rep = DIST / '_cedwyn' / 'reports'; rep.mkdir(parents=True, exist_ok=True)
    if FIX:
        got, failed = fetch_vendor()
        global ONLY
        for _ in range(4):   # vendored files may name further CDN files / modules (and carry their own links): same rules, again
            before = set(vendor); ONLY = ['_ext']; run(); module_deps()
            if set(vendor) == before: break
            g2, f2 = fetch_vendor(); got += g2; failed += f2
        ONLY = ['_ext']; run(); ONLY = []
        filled = {'wanted': 0, 'copied': 0, 'not_found': [], 'rounds': 0}
        if '--no-fill' not in sys.argv:
            scan = [p for p, rel in files() if rel.split('/')[0] in CRAWLED]
            # whole pages a theme links to that its build or crawl does not produce (themes.json fetch_pages: path -> live address)
            fetched_pages = []
            for relp, url in CFG.get('fetch_pages', {}).items():
                dst = DIST / relp
                if dst.exists(): continue
                try:
                    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                        if 'html' not in (r.headers.get('Content-Type') or '') and not relp.endswith('.txt'): continue
                        b = r.read()
                    if relp.endswith('.html'): b = prefix_root(b.decode('utf-8', 'ignore'), url, relp.split('/')[0]).encode('utf-8')
                    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b); fetched_pages.append(relp); scan.append(dst)
                except Exception as e: filled['not_found'].append([relp, str(e)[:80]])
            if fetched_pages: run([DIST / r for r in fetched_pages])
            filled['pages_fetched'] = fetched_pages
            for rnd in range(3):   # files that fetched scripts/styles name in turn
                want, gm = fill_missing(scan=scan)
                scan = [DIST / r for r in gm[0]]
                filled['rounds'] += 1; filled['wanted'] += len(want); filled['copied'] += len(gm[0]); filled['not_found'] += gm[1]
                if not gm[0]: break
                run([DIST / r for r in gm[0]])
                v0 = set(vendor); module_deps()
                if set(vendor) != v0:
                    fetch_vendor(); ONLY = ['_ext']; run(); ONLY = []
        filled['not_found_n'] = len(filled['not_found']); filled['not_found'] = filled['not_found'][:80]
        # redirects that stage 1 sent to the archive but whose address is now a cedwyn theme (e.g. research) go to that theme
        rp = DIST / '_redirects'
        if rp.exists():
            out, nmap = [], 0
            for line in rp.read_text('utf-8').splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1].startswith('/wayback/go/?u='):
                    u = urllib.parse.unquote(parts[1][len('/wayback/go/?u='):]); su = urllib.parse.urlsplit(u)
                    tu = theme_url((su.hostname or '').lower(), su.path or '/')
                    if tu and (DIST / tu.strip('/').split('/')[0]).is_dir() and parts[0].strip('/').split('/')[0] != tu.strip('/').split('/')[0]:
                        parts[1] = tu + ('?' + su.query if su.query else ''); line = ' '.join(parts); nmap += 1
                out.append(line)
            # apex-root files some pages still name from the root (fonts, the chooser image, the apex copy of the header files)
            ROOT_RW = ['/assets/fonts/* /_cedwyn/ghf/fonts/:splat 200', '/locations-img/* /dartboard/locations-img/:splat 200',
                       '/dartboard/ghf-lang/* /_cedwyn/ghf/:splat 200']
            out = [l for l in ROOT_RW if l not in out] + out
            rp.write_text('\n'.join(out) + '\n', 'utf-8'); stats['redirects_to_themes'] = nmap
        for t in CFG['themes']:
            if t.get('redirect_to'):
                (DIST / t['id']).mkdir(parents=True, exist_ok=True)
                (DIST / t['id'] / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Moved</title>'
                    '<meta http-equiv="refresh" content="0; url=%s"><link rel="canonical" href="%s">'
                    '<script>location.replace(%s + location.hash)</script><a href="%s">Continue</a>\n'
                    % (t['redirect_to'], t['redirect_to'], json.dumps(t['redirect_to']), t['redirect_to']))
        run()   # one last full pass: every file, including everything copied above, goes through the same rules
        o = dict(stats, filled_missing=filled, vendored=got, vendor_failed=failed[:50], vendor_failed_n=len(failed), allowed_tile_templates=sorted(tiles_seen))
        json.dump(o, open(rep / 'selfcontain_fix.json', 'w'), indent=1)
        print(json.dumps({k: v for k, v in o.items() if k != 'vendor_failed'})[:900]); return 0
    by_theme = {}
    for (th, k), v in left.items(): by_theme.setdefault(th, {})[k] = v
    tot = {'sub': sum(v for (t, k), v in left.items() if k == 'sub'), 'ext': sum(v for (t, k), v in left.items() if k in ('ext', 'cdn'))}
    o = {'files_checked': stats['files'], 'subdomain_refs': tot['sub'], 'external_refs': tot['ext'], 'by_theme': by_theme,
         'examples': {f'{t}:{k}': v for (t, k), v in examples.items()}, 'allowed_tile_templates': sorted(tiles_seen)}
    json.dump(o, open(rep / 'selfcontain_test.json', 'w'), indent=1)
    print(json.dumps({k: o[k] for k in ('files_checked', 'subdomain_refs', 'external_refs', 'allowed_tile_templates')}))
    if tot['sub'] or tot['ext']:
        for k, v in list(o['examples'].items())[:12]: print(k, v[:2])
        print('SELF-CONTAINED TEST FAILED'); return 1
    print('SELF-CONTAINED TEST PASSED: 0 subdomain references, 0 external references')
    if not ONLY and (DIST / 'db' / 'blobmap.json').exists():   # stage 3: the database becomes the one source of data and evidence files
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import dbserve; dbserve.DIST = DIST; return dbserve.main()
    return 0

if __name__ == '__main__': sys.exit(main())
