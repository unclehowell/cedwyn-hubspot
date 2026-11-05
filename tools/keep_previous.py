#!/usr/bin/env python3
"""keep_previous.py — a crawled theme whose live site answered the build's crawl with an error (the dartboard's own server
answered 429 "Too Many Requests" to the 7d0a5ef build on 25 Oct 2026, so the theme lost its home page and bundle and
/dartboard/ answered 404) keeps the files of its previous published build that this build did not get. Refused = no home page, or under 80% of
the previous build's file count (the old Worker origins answered 429 Error 1027 / 522 to whole crawls the same afternoon). Only missing files are
copied, never over a fresh one; the previous copies are already processed (runtime, links, base path), so this runs at the end
of tools/site.py, after the rewrite and ingredients passes. Report: dist/_cedwyn/reports/keep_previous.json. — Sion's Tab agent"""
import json, os, pathlib, shutil, subprocess, sys
LOOKBACK = 100   # site-branch commits searched for a dropped theme's last good copy
def run(dist):
    dist = pathlib.Path(dist); root = pathlib.Path(__file__).resolve().parent.parent
    themes = json.load(open(root / 'themes.json', encoding='utf-8'))['themes']
    crawled = [t['id'] for t in themes if t.get('crawl') or t.get('crawl_first')]
    def count(base):
        return sum(1 for f in base.rglob('*') if f.is_file() and 'db' not in f.relative_to(base).parts[:1]) if base.exists() else 0
    rep = {'checked': {}, 'restored': {}}
    repo = os.environ.get('GITHUB_REPOSITORY', 'unclehowell/cedwyn'); tmp = pathlib.Path('prev_site')
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        # the previous published builds, file names only (no file contents fetched until a theme needs them); the last
        # LOOKBACK commits, so a theme an earlier refused build already dropped is found in the last build that had it
        subprocess.run(['git', 'clone', '-q', '--depth', str(LOOKBACK), '--filter=blob:none', '--no-checkout', '-b', 'site', f'https://github.com/{repo}.git', str(tmp)], check=True, timeout=600)
        names = subprocess.run(['git', '-C', str(tmp), 'ls-tree', '-r', '--name-only', 'HEAD'], check=True, capture_output=True, text=True, timeout=300).stdout.split('\n')
    except Exception as e:
        names = []; rep['error'] = 'previous build not readable: ' + str(e)[:200]
    prev = {}
    for n in names:
        p = n.split('/')
        if len(p) > 1 and p[0] in crawled and p[1] != 'db': prev[p[0]] = prev.get(p[0], 0) + 1
    # A crawl counts as refused when the theme has no home page, or holds under 80% of the files it had last time (the
    # origin answered 429 / 1027 / 522 for part of it). Then the previous build's files fill the gaps (missing files only).
    # 25 Oct 2026 (task acf096da): the 7d0a5ef build (14:36 UTC) published before this guard existed, with fcg, research and
    # terrain refused (Workers daily limit, 429/522), so every later build found 0 previous files and restored nothing.
    # A refused theme that the previous build no longer holds is now taken from the newest earlier build that has its home page.
    def last_good(t):
        try:
            revs = subprocess.run(['git', '-C', str(tmp), 'rev-list', 'HEAD'], check=True, capture_output=True, text=True, timeout=120).stdout.split()
        except Exception: return None
        for c in revs:
            if subprocess.run(['git', '-C', str(tmp), 'cat-file', '-e', f'{c}:{t}/index.html'], capture_output=True, timeout=60).returncode == 0: return c
        return None
    need = []; src_of = {}; nameset = set(names)
    for t in crawled:
        now = count(dist / t); was = prev.get(t, 0); home = (dist / t / 'index.html').exists()
        rep['checked'][t] = {'files_now': now, 'files_previous_build': was, 'home': home}
        if (was and (not home or now < 0.8 * was)) or (not home and names):
            # the previous build is the source; when it has no home page for the theme either (a refused build already lost it),
            # the newest earlier build that has one fills what is still missing
            c = last_good(t) if not home and f'{t}/index.html' not in nameset else None
            if was or c:
                need.append(t)
                if c: src_of[t] = c; rep['checked'][t]['from_earlier_build'] = c[:9]
    rep['refused'] = need
    if need and names:
        try:
            subprocess.run(['git', '-C', str(tmp), 'sparse-checkout', 'set', '--no-cone'] + [f'/{t}/' for t in need] + [f'!/{t}/db/' for t in need], check=True, timeout=900)
            subprocess.run(['git', '-C', str(tmp), 'checkout', '-q'], check=True, timeout=1500)
            kept = set()   # files this pass copied from an earlier build (never a file this build crawled)
            def copy_missing(t):
                src = tmp / t; n = 0
                if not src.exists(): return 0
                for f in src.rglob('*'):
                    if not f.is_file() or 'db' in f.relative_to(src).parts[:1]: continue
                    dst = dist / t / f.relative_to(src)
                    if dst.exists(): continue
                    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(f, dst); n += 1; kept.add(dst)
                return n
            for t in need: rep['restored'][t] = copy_missing(t)
            for t in need:
                if t in src_of:
                    # one batched fetch of that build's blobs for the theme (a plain checkout of an old commit fetches them one by one)
                    ls = subprocess.run(['git', '-C', str(tmp), 'ls-tree', '-r', src_of[t], '--', t + '/'], check=True, capture_output=True, text=True, timeout=300).stdout
                    oids = '\n'.join(l.split()[2] for l in ls.splitlines() if l.split()[1:2] == ['blob'] and '/db/' not in l) + '\n'
                    subprocess.run(['git', '-C', str(tmp), '-c', 'fetch.negotiationAlgorithm=noop', 'fetch', '-q', 'origin', '--no-tags', '--no-write-fetch-head',
                                    '--recurse-submodules=no', '--filter=blob:none', '--stdin'], input=oids, text=True, timeout=1500)
                    subprocess.run(['git', '-C', str(tmp), 'checkout', '-q', src_of[t], '--', t], check=True, timeout=1500)
                    rep['restored'][t] += copy_missing(t)
            # 27 Oct 2026 (problems flywheel, terrain): a page that loads 'app.js?v=1.5.2' is crawled as 'app.js@v=1.5.2' (fresh), but the
            # server ignores the query and serves the bare 'app.js', which only ever came from an old kept build (the 27 Oct 00:59 copy
            # whose script brackets the old privacy scrub had stripped, so /terrain/ showed a broken map every build since). When a kept
            # bare file has a fresh versioned sibling from this build, the fresh copy wins. Only kept files are replaced. — Sion's Tab agent
            fresh_won = []
            for dst in sorted(kept):
                sibs = sorted(p for p in dst.parent.glob(dst.name + '@*') if p.is_file() and p not in kept)
                if sibs:
                    shutil.copy2(sibs[-1], dst); fresh_won.append(str(dst.relative_to(dist)))
            rep['fresh_versioned_copy_won'] = fresh_won
            # kept copies may come from a build whose ingredients pass was older than this one's: apply this build's rewords and
            # link repoints to the kept themes too, skipping any entry whose replacement is already in the file (so nothing is applied twice)
            try:
                import ingredients
                hits = 0
                for cp in ingredients.CONFIGS:
                    cpp = root / cp
                    if not cpp.exists(): continue
                    for e in json.load(open(cpp, encoding='utf-8')).get('rewords', []):
                        if e.get('theme') not in rep['restored']: continue
                        for f in ingredients._files(dist, e):
                            if not f.exists(): continue
                            s = f.read_text(encoding='utf-8', errors='surrogateescape')
                            if e['replace'] in s or e['find'] not in s: continue
                            f.write_text(s.replace(e['find'], e['replace']), encoding='utf-8', errors='surrogateescape'); hits += 1
                rep['rewords_on_kept'] = hits
            except Exception as e: rep['rewords_error'] = str(e)[:200]
        except Exception as e: rep['error'] = str(e)[:300]
    shutil.rmtree(tmp, ignore_errors=True)
    out = dist / '_cedwyn' / 'reports'; out.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(out / 'keep_previous.json', 'w'), indent=1)
    print('keep_previous:', rep)
    return rep
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
