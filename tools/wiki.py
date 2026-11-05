#!/usr/bin/env python3
"""wiki.py - copy the Legal Wiki (greathousefarmwiki.wordpress.com) into dist/wiki/ by read-only GETs. - Sion's Tab agent

  python3 tools/wiki.py dist/wiki [--limit=N]

- Every page the wiki's own sitemap lists is fetched (robots.txt obeyed, a few requests at a time) and saved as
  <path>/index.html, so /wiki/<path>/ serves it.
- The scripts and styles WordPress.com combines on the fly (/_static/??...) cannot be served by a static host under that
  address, so each one is saved under a fixed name (/_static/c-<hash>.css|js) and the page points at it. Other theme
  files, scripts, modules, fonts and images on the wiki's own host are saved at their own path.
- Tracking, advertising and social add-ons that need wordpress.com to work (stats, hovercards, likes, the marketing bar,
  ad consent, cookie banner) are left out; feeds, the editing API and other machine links are removed from <head>.
Writes <out>/_wiki_report.json; the caller falls back to the branch copy when too few pages arrive.
"""
import sys, re, os, json, time, zlib, base64, hashlib, pathlib, threading, urllib.request, urllib.parse, urllib.robotparser
import concurrent.futures as cf
HOST = 'greathousefarmwiki.wordpress.com'
BASE = 'https://' + HOST
UA = 'Mozilla/5.0 (compatible; cedwyn-archive; read-only copy for cedwyn.bucklerfamily.estate)'
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist/wiki')
LIMIT = next((int(a.split('=', 1)[1]) for a in sys.argv if a.startswith('--limit=')), 0)
WORKERS = 6
DROP_SRC = re.compile(r'gravatar\.com/js/hovercards|gravatar-hovercards|marketing-bar|stats\.wp\.com|bilmur|comment-likes|'
                      r'widgets\.wp\.com/likes|/likes/|wordads|cmp-non-gdpr|cmp/v2|watl|rlt-proxy|eu-cookie-law|pubmine|'
                      r'pixel\.wp\.com|mobile-useragent-info|actionbar|tos-prompt', re.I)
DROP_INLINE_ID = re.compile(r'id\s*=\s*["\'](?:wpgroho-js-extra|comment-like-js-extra|wpcom-actionbar-placeholder-js-extra|'
                            r'rlt-proxy-js-after|wpcom-marketing-bar-js-extra|eu-cookie-law[\w-]*|bilmur)["\']', re.I)
DROP_LINK = re.compile(r'<link\b[^>]*\brel\s*=\s*["\']?(?:alternate|EditURI|search|pingback|https://api\.w\.org/|wlwmanifest|'
                       r'shortlink|openid\.server|openid\.delegate|dns-prefetch|preconnect)\b[^>]*>\s*', re.I)
rep = {'sitemap': 0, 'robots_blocked': 0, 'pages_ok': 0, 'pages_failed': [], 'assets_ok': 0, 'assets_failed': [],
       'scripts_dropped': 0, 'bytes': 0}
lock = threading.Lock()

def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=40) as r:
                return r.status, r.headers.get('Content-Type', ''), r.read()
        except urllib.error.HTTPError as e:
            if e.code in (404, 403, 410): return e.code, '', b''
            last = e.code
        except Exception as e: last = str(e)[:60]
        time.sleep(1.5 * (i + 1))
    return last or 0, '', b''

def static_list(q):
    """the files a /_static/??... address combines: '??/a.js,/b.js' as written, or '??-<base64(zlib)>' compressed"""
    if q.startswith('-'):
        try:
            b = q[1:]; b += '=' * (-len(b) % 4)
            return zlib.decompress(base64.b64decode(b.replace('-', '+').replace('_', '/'))).decode('utf-8', 'ignore').split(',')
        except Exception: return []
    return q.split(',')

assets = {}   # local root path -> source url
def local_for(path_q):
    if path_q.startswith('/_static/??'):
        lst = path_q[len('/_static/??'):].split('?', 1)[0]
        files = static_list(lst)
        ext = '.css' if any(f.strip().split('?')[0].endswith('.css') for f in files) or 'cssminify' in path_q else '.js'
        return '/_static/c-' + hashlib.sha1(path_q.encode()).hexdigest()[:14] + ext, BASE + path_q
    return path_q.split('?', 1)[0].split('#', 1)[0], BASE + path_q

REF = re.compile(r'(?:(?:https?:)?//(?:' + re.escape(HOST) + r'|s[0-2]\.wp\.com))?(/(?:_static/\?\?|wp-content/|wp-includes/|i/)[^"\'\s<>)\\*]*?)(?=&apos;|&quot;|&gt|&lt|["\'\s<>)\\*]|$)')
def unesc(u): return u.replace('&#038;', '&').replace('&amp;', '&')
def localise(text):
    def r(m):
        pq = unesc(m.group(1))
        if pq.startswith('/_static/??'):
            files = static_list(pq[len('/_static/??'):].split('?', 1)[0])
            if files and all(DROP_SRC.search(f) for f in files): return m.group(0)
        elif (DROP_SRC.search(pq) and re.search(r'\.m?js$', pq.split('?')[0])) or pq.split('?')[0].endswith('/') or m.end() < len(m.string) and m.string[m.end()] == '*': return m.group(0)
        loc, src = local_for(pq)
        cdn = re.match(r'(?:https?:)?//(s[0-2]\.wp\.com)', m.group(0))
        with lock:   # theme files named on the wp.com CDN are read from the wiki's own host first (the CDN refuses some fonts)
            c = assets.setdefault(loc, [src])
            if cdn and len(c) == 1: c.append('https://' + cdn.group(1) + pq)
        # an address written with the wiki's host keeps it (inline scripts and import maps are mapped by host later)
        return (BASE + loc) if len(m.group(0)) > len(m.group(1)) else loc
    return REF.sub(r, text)

SCRIPT_TAG = re.compile(r'<script\b([^>]*)>(.*?)</script>\s*', re.S | re.I)
def page(html):
    def sc(m):
        attrs, body = m.group(1), m.group(2)
        srcm = re.search(r'\bsrc\s*=\s*["\']([^"\']+)', attrs)
        if srcm:
            src = unesc(srcm.group(1))
            if '/_static/??' in src:
                q = src.split('/_static/??', 1)[1]; lst = q.split('?', 1)[0]; files = static_list(lst)
                keep = [f.split('?')[0] for f in files if f and not DROP_SRC.search(f)]
                if files and not keep: rep['scripts_dropped'] += 1; return ''
                if files and len(keep) < len(files):
                    tail = ('?' + q.split('?', 1)[1]) if '?' in q else ''
                    return '<script' + attrs.replace(srcm.group(1), '/_static/??' + ','.join(keep) + tail) + '>' + body + '</script>\n'
            elif DROP_SRC.search(src): rep['scripts_dropped'] += 1; return ''
        elif DROP_INLINE_ID.search(attrs) or re.search(r'type\s*=\s*["\']?speculationrules', attrs, re.I): rep['scripts_dropped'] += 1; return ''
        elif re.search(r'wp-emoji-settings', attrs) or re.search(r'wp-emoji|concatemoji|twemoji', body[:4000]) and 'importmap' not in attrs:
            rep['scripts_dropped'] += 1; return ''   # emoji images from wordpress.com: the browser draws the same emoji itself
        elif re.search(r'action-bar\.js|jetpack-newsletter', body) and len(body) < 6000:
            rep['scripts_dropped'] += 1; return ''   # the wordpress.com subscribe bar
        elif re.search(r'_tkq|_stq|bilmur|wpcom_wpl|wpgroho', body) and len(body) < 4000 and 'importmap' not in attrs:
            rep['scripts_dropped'] += 1; return ''
        return m.group(0)
    html = SCRIPT_TAG.sub(sc, html)
    html = DROP_LINK.sub('', html)
    html = re.sub(r'<meta\b[^>]*\bid\s*=\s*["\']bilmur["\'][^>]*>\s*', '', html, flags=re.I)
    html = re.sub(r'<noscript><img[^>]*pixel\.wp\.com[^>]*></noscript>', '', html, flags=re.I)
    html = re.sub(r'href\s*=\s*(["\'])(?:https?://' + re.escape(HOST) + r')?/(?:comments/)?feed/?\1', 'href="/"', html)
    # WordPress post embeds: a hidden iframe that only shows after a handshake with wordpress.com; the quoted link stays
    html, k = re.subn(r'<iframe\b[^>]*class\s*=\s*["\'][^"\']*wp-embedded-content[^>]*>\s*</iframe>\s*', '', html, flags=re.I)
    rep['embeds_removed'] = rep.get('embeds_removed', 0) + k
    # images and video the wiki loads from the datro repo's wayback folder: the wayback theme holds the same files
    html = re.sub(r'https://raw\.githubusercontent\.com/unclehowell/datro/[0-9a-f]{7,40}/wayback/', 'https://wayback.bucklerfamily.estate/', html)
    return localise(html)

def save(rel, data):
    f = OUT / rel.lstrip('/')
    f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(data)
    with lock: rep['bytes'] += len(data)

def do_page(url):
    st, ct, b = get(url)
    if st != 200 or not b:
        with lock: rep['pages_failed'].append([url, st])
        return
    path = urllib.parse.unquote(urllib.parse.urlparse(url).path or '/')   # the host decodes %e2%86%92 to '→' before it looks for the file
    save((path if path.endswith('/') else path + '/') + 'index.html', page(b.decode('utf-8', 'ignore')).encode('utf-8'))
    with lock: rep['pages_ok'] += 1

def do_asset(loc, srcs):
    for src in srcs:
        st, ct, b = get(src)
        if st == 200: break
    if st != 200:
        with lock: rep['assets_failed'].append([loc, st])
        return
    if loc.endswith('.css') or 'css' in ct:
        b = localise(b.decode('utf-8', 'ignore')).encode('utf-8')
    save(loc, b)
    with lock: rep['assets_ok'] += 1

def main():
    t0 = time.time()
    rp = urllib.robotparser.RobotFileParser(); rp.set_url(BASE + '/robots.txt')
    try: rp.read()
    except Exception: pass
    st, ct, sm = get(BASE + '/sitemap.xml')
    locs = re.findall(r'<loc>([^<]+)</loc>', sm.decode('utf-8', 'ignore'))
    rep['sitemap'] = len(locs)
    urls = []
    for u in locs:
        u = u.strip()
        if not u.startswith(BASE): continue
        if not rp.can_fetch(UA, u): rep['robots_blocked'] += 1; continue
        urls.append(u if urllib.parse.urlparse(u).path else u + '/')
    if LIMIT: urls = urls[:LIMIT]
    OUT.mkdir(parents=True, exist_ok=True)
    with cf.ThreadPoolExecutor(WORKERS) as ex: list(ex.map(do_page, urls))
    done = set()
    for rnd in range(3):
        todo = [(k, v) for k, v in list(assets.items()) if k not in done]
        if not todo: break
        done.update(k for k, _ in todo)
        with cf.ThreadPoolExecutor(WORKERS) as ex: list(ex.map(lambda kv: do_asset(*kv), todo))
    rep['assets_total'] = len(assets); rep['secs'] = round(time.time() - t0)
    rep['pages_failed_n'] = len(rep['pages_failed']); rep['assets_failed_n'] = len(rep['assets_failed'])
    rep['assets_failed'] = rep['assets_failed'][:60]
    json.dump(rep, open(OUT / '_wiki_report.json', 'w'), indent=1)
    print('wiki:', {k: rep[k] for k in ('sitemap', 'robots_blocked', 'pages_ok', 'pages_failed_n', 'assets_ok', 'assets_failed_n', 'scripts_dropped', 'bytes', 'secs')}, flush=True)
    return rep['pages_ok']

if __name__ == '__main__':
    main()
