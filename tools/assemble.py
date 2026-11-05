#!/usr/bin/env python3
"""assemble.py — copy every theme's site out of its mirrored branch (or a read-only crawl of its live site when it
has no static branch output) into dist/<theme>/. Never writes to datro or to any old subdomain. — Sion's Tab agent"""
import json, os, subprocess, shutil, sys, pathlib, time
ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'themes.json'))
DIST = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist')
MIRROR = os.environ.get('MIRROR', 'mirror.git')   # bare repo holding the cedwyn branches
MAXF = 24 * 1024 * 1024                           # Pages limit is 25 MiB per file
report = {}
def sh(cmd, cwd=None, t=900):
    try: return subprocess.run(['timeout', '-k', '5', str(t), 'bash', '-lc', cmd], cwd=cwd, capture_output=True, text=True)
    except Exception as e: return subprocess.CompletedProcess(cmd, 1, '', str(e))
def crawl(url, out, robots=False, quota='150m', t=420, sitemap=None):
    """read-only GET crawl; robots=True obeys the site's robots.txt (used for the WordPress wiki); sitemap: every page the
    site's own sitemap lists is a starting point too, so deep pages are not missed"""
    tmp = pathlib.Path('crawl_tmp_' + out.name); shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    rob = ("--wait=0.1 --reject-regex '[?&](share|replytocom|like_comment|nb|_wpnonce|subscribe|shared)=|/feed/|/amp/|/embed/'"
           if robots else '-e robots=off'); seeds = ''; level = 3
    if sitemap:
        try:
            import urllib.request, re as _re
            with urllib.request.urlopen(urllib.request.Request(sitemap, headers={'User-Agent': 'Mozilla/5.0 cedwyn-archive'}), timeout=60) as r0:
                locs = _re.findall(r'<loc>([^<]+)</loc>', r0.read().decode('utf-8', 'ignore'))
            lf = pathlib.Path('seeds_' + out.name + '.txt').resolve(); lf.write_text('\n'.join(locs) + '\n'); seeds = f'-i {lf}'; level = 1
            report.setdefault('_sitemap', {})[out.name] = len(locs)
        except Exception as e: report.setdefault('_sitemap', {})[out.name] = 'failed: ' + str(e)[:80]
    r = sh(f"wget -q {rob} {seeds} --mirror --level={level} --page-requisites --adjust-extension --convert-links=off --no-parent "
           f"--restrict-file-names=windows --timeout=20 --tries=4 --waitretry=20 --retry-on-http-error=429,503 --quota={quota} -U 'Mozilla/5.0 cedwyn-archive' -P {tmp} '{url}'", t=t)
    host = url.split('/')[2]; base = tmp / host
    sub = url.split(host, 1)[1].strip('/')
    src = base / sub if sub else base
    if not src.exists(): return 0
    shutil.copytree(src, out, dirs_exist_ok=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return sum(1 for _ in out.rglob('*') if _.is_file())
SECTIONS = set(os.environ.get('SECTIONS', '').split())      # assemble only these theme ids (snapshot runs, section checks)
FORCE_CRAWL = os.environ.get('FORCE_CRAWL') == '1'           # snapshot runs: crawl the live site even when a snapshot branch exists
# Production reproducibility note (29 Oct 2026): the committed sections.lock SHAs are authoritative, not the branch tips. Keep item-level evidence interpretations in section/research and legacy Wiki interpretations/navigation in section/wiki, update both pins, then rebuild; otherwise a queued build can replace manual site-only edits with an older snapshot.
LOCK = {}
try: LOCK = json.load(open(ROOT / 'sections.lock')).get('sections', {})
except Exception: pass
def snapshot(t, out):
    """26 Oct 2026: a crawled section is read from its own snapshot branch (section/<id>, made by snapshot-sections.yml)
    at the commit sections.lock pins, so a build no longer crawls the live Worker sites. Falls back to the crawl when the
    branch or the pinned commit cannot be read. - Sion's Tab agent"""
    br = t['snapshot_branch']; pin = (LOCK.get(t['id']) or {}).get('sha') or ''
    repo = os.environ.get('GITHUB_REPOSITORY', 'unclehowell/cedwyn')
    ref = f'refs/heads/{br}'
    if sh(f"git --git-dir={MIRROR} rev-parse --verify -q {ref}").returncode != 0:
        sh(f"git --git-dir={MIRROR} fetch -q --depth 1 https://github.com/{repo}.git +{ref}:{ref}", t=600)
    want = ref
    if pin:
        if sh(f"git --git-dir={MIRROR} cat-file -e {pin}^{{commit}}").returncode != 0:
            sh(f"git --git-dir={MIRROR} fetch -q --depth 1 https://github.com/{repo}.git {pin}", t=600)
        want = pin if sh(f"git --git-dir={MIRROR} cat-file -e {pin}^{{commit}}").returncode == 0 else ref
    r = sh(f"git --git-dir={MIRROR} archive --format=tar {want} | tar -x -C {out}")

    # A site build can accidentally be pinned instead of a section snapshot. Its root
    # contains several sibling theme directories; extracting it into /<theme>/ would
    # nest the entire site under that theme and duplicate the catalogue. Reject it and
    # fall back to the actual section branch, never to a live crawl for this condition.
    peer_theme_roots = sorted(
        x['id'] for x in CFG.get('themes', [])
        if x.get('id') and x.get('id') != t.get('id') and (out / x['id']).is_dir()
    )
    if r.returncode == 0 and len(peer_theme_roots) >= 3:
        report.setdefault('_snapshot_rejected', {})[t['id']] = {
            'ref': want,
            'reason': 'snapshot root contains multiple sibling theme directories; likely a full-site build',
            'peer_theme_roots': peer_theme_roots[:30]
        }
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True, exist_ok=True)
        fallback = f'refs/heads/{br}'
        r = sh(f"git --git-dir={MIRROR} archive --format=tar {fallback} | tar -x -C {out}")
        want = fallback

    for x in ('section.json', '.github'):
        p = out / x
        if p.is_dir(): shutil.rmtree(p, ignore_errors=True)
        elif p.exists(): p.unlink()
    n = sum(1 for _ in out.rglob('*') if _.is_file())
    report.setdefault('_snapshot', {})[t['id']] = {'ref': want, 'files': n, 'rc': r.returncode, 'peer_theme_roots_detected': peer_theme_roots[:30]}
    return n if r.returncode == 0 and (out / 'index.html').exists() else 0
def one(t):
    tid = t['id']; out = DIST / tid; shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    t0 = time.time(); how = None; n = 0
    if t.get('snapshot_branch') and not FORCE_CRAWL:
        n = snapshot(t, out); how = 'snapshot' if n else None
        if not n: shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
    if how: pass
    elif t.get('wp_copy'):   # the WordPress wiki: tools/wiki.py copies every sitemap page and its theme files (robots.txt obeyed)
        r = sh(f"python3 {ROOT / 'tools' / 'wiki.py'} {out}", t=t.get('crawl_secs', 1500))
        report.setdefault('_wiki_log', {})[tid] = r.stdout[-400:] + r.stderr[-600:]
        n = sum(1 for _ in out.rglob('*') if _.is_file()); how = 'wiki.py(robots)'
        if n < 200 or not (out / 'index.html').exists():
            shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True); n = 0; how = None
    elif t.get('crawl_first'):   # a live site crawled first (robots.txt obeyed); its branch copy is the fallback
        n = crawl(t['crawl_first'], out, robots=True, quota=t.get('crawl_quota', '150m'), t=t.get('crawl_secs', 420), sitemap=t.get('crawl_sitemap')); how = 'crawl(robots)'
        if n == 0 or not (out / 'index.html').exists():
            shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True); n = 0; how = None
    if how: pass
    elif t.get('branch'):
        work = pathlib.Path('src_tmp_' + tid); shutil.rmtree(work, ignore_errors=True); work.mkdir()
        r = sh(f"git --git-dir={MIRROR} archive --format=tar refs/heads/{t['branch']} | tar -x -C {work}")
        if r.returncode == 0:
            if t.get('build'):
                bdir = work / (t.get('root') or '')
                b = sh(t['build'], cwd=bdir, t=480)
                how = 'branch+build' if b.returncode == 0 else 'branch(build failed)'
                report.setdefault('_build_logs', {})[tid] = (b.stdout[-600:] + b.stderr[-900:])
            else:
                how = 'branch'
            d = work / t['dir'] if t['dir'] else work
            if d.exists() and any(d.iterdir()):
                shutil.copytree(d, out, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', 'node_modules', '.github'))
                if t.get('overlay') and (work / t['overlay']).is_dir():   # the folder the live site serves at its root (e.g. qa: static/qa)
                    shutil.copytree(work / t['overlay'], out, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git', 'node_modules', 'functions'))
                    how += '+overlay'
                n = sum(1 for _ in out.rglob('*') if _.is_file())
        shutil.rmtree(work, ignore_errors=True)
        if (n == 0 or not (out / 'index.html').exists()) and t.get('crawl_fallback'):
            shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
            n = crawl(t.get('crawl_url') or t['live'], out); how = 'crawl(fallback)'   # crawl_url: the theme's own origin when its public host now serves the Cedwyn copy (docs)
    elif t.get('crawl'):
        n = crawl(t['crawl'], out); how = 'crawl'
    big = []
    for f in out.rglob('*'):
        if f.is_file() and f.stat().st_size > MAXF:
            big.append(str(f.relative_to(DIST))); f.unlink()
    size = sum(f.stat().st_size for f in out.rglob('*') if f.is_file())
    report[tid] = {'how': how, 'files': n, 'bytes': size, 'has_index': (out / 'index.html').exists(), 'dropped_over_24MB': big, 'secs': round(time.time() - t0)}
    print(tid, report[tid]['how'], n, round(size / 1e6, 1), 'MB', flush=True)
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(6) as ex: list(ex.map(one, [t for t in CFG['themes'] if not SECTIONS or t['id'] in SECTIONS]))
json.dump(report, open(DIST / '_assemble_report.json', 'w'), indent=1)
