#!/usr/bin/env python3
"""library_pointer.py - the developer library (/library/): how Cedwyn's database, hosting, front ends and sections work, the
data export and the API/WebMCP guide. Lives on its own branch `library` (dir public/); copied into dist/library/ at build time.
Like /academy/ it is NOT a theme: it never enters the human menu, the directory or the tiles; the shared footer links it in
small print as 'Docs'. Usage: python3 tools/library_pointer.py dist   (site.py calls it) - docs library build, 27 Oct 2026"""
import io, os, pathlib, shutil, subprocess, sys, tarfile
BRANCH = 'library'
def run(dist):
    d = pathlib.Path(dist); out = d / 'library'
    repo = os.environ.get('GITHUB_REPOSITORY', 'unclehowell/cedwyn'); mirror = os.environ.get('MIRROR', 'mirror.git')
    try:
        if not pathlib.Path(mirror).exists(): subprocess.run(['git', 'init', '-q', '--bare', mirror], check=True)
        subprocess.run(['git', '--git-dir', mirror, 'fetch', '-q', '--depth', '1', f'https://github.com/{repo}.git',
                        f'+refs/heads/{BRANCH}:refs/heads/{BRANCH}'], timeout=300, check=True)
        tar = subprocess.run(['git', '--git-dir', mirror, 'archive', '--format=tar', f'refs/heads/{BRANCH}', 'public'],
                             capture_output=True, timeout=300, check=True).stdout
        shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True); n = 0
        with tarfile.open(fileobj=io.BytesIO(tar)) as tf:
            for m in tf.getmembers():
                if not m.isfile() or not m.name.startswith('public/'): continue
                dst = out / m.name[len('public/'):]; dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(tf.extractfile(m).read()); n += 1
        print('library_pointer: library files', n); return n
    except Exception as e:
        print('library_pointer: library copy failed:', str(e)[:200]); return 0
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
