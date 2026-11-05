#!/usr/bin/env python3
"""db_export.py - the whole catalogue database as portable files, independent of any front end.
Called by build_db.py after the database is written and before the chunk source file is removed. Writes dist/db/export/:
  manifest.json                    one URL that lists everything below: tables, row counts, files, bytes, sha256, how to rebuild
  <table>.csv.gz                   every table except the raw blob bytes, as CSV (large tables roll over into -001, -002 parts)
  cedwyn-data.json.gz              every small table in one JSON document {table: [rows]}
  cedwyn-metadata.sqlite3.gz       the database without blob bytes and without the full-text index (when it fits under 24 MB)
  sections/<theme>.json.gz         one slice per section: that section's row in `themes` and every artifact it shows, with paths
  fetch-full.sh                    one command that rebuilds the complete database, blobs included, from /db/ chunk files
Never raises: a failure is printed and the build carries on. - docs library build, 27 Oct 2026"""
import csv, gzip, hashlib, io, json, os, pathlib, shutil, sqlite3, sys, time
PART = 20_000_000
SMALL = 60_000      # rows; tables up to this size also go into cedwyn-data.json.gz
def _sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()
def _tables(con):
    skip = {'blobs', 'sqlite_sequence'}
    names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    shadow = {n for n in names for v in ('fts',) if n.startswith(v + '_')}
    return [n for n in names if n not in skip and n not in shadow]
def _csv(con, table, ex):
    cur = con.execute('SELECT * FROM "%s"' % table); cols = [d[0] for d in cur.description]
    files = []; part = 0; raw = gz = w = None
    def open_part():
        nonlocal raw, gz, w, part
        name = '%s.csv.gz' % table if part == 0 else '%s-%03d.csv.gz' % (table, part)
        raw = open(ex / name, 'wb'); gz = gzip.GzipFile(fileobj=raw, mode='wb', compresslevel=6, mtime=0)
        w = csv.writer(io.TextIOWrapper(gz, encoding='utf-8', newline='', write_through=True)); w.writerow(cols); files.append(name)
    open_part(); n = 0
    for row in cur:
        w.writerow(['' if v is None else (v.hex() if isinstance(v, (bytes, memoryview)) else v) for v in row]); n += 1
        if n % 2000 == 0 and raw.tell() > PART:
            gz.close(); raw.close(); part += 1; open_part()
    gz.close(); raw.close()
    return cols, n, files
def run(dbf, out, stats=None):
    try:
        t0 = time.time(); dbf = pathlib.Path(dbf); out = pathlib.Path(out); ex = out / 'export'
        shutil.rmtree(ex, ignore_errors=True); (ex / 'sections').mkdir(parents=True)
        full_sha = _sha(dbf); con = sqlite3.connect(dbf)
        man = {'schema': 'cedwyn_export/v1', 'built_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'database': {'bytes': dbf.stat().st_size, 'sha256': full_sha, 'chunks_url_prefix': '/db/cedwyn.sqlite3.',
                            'chunk_config': '/db/config.json', 'stats': '/db/stats.json', 'rebuild': '/db/export/fetch-full.sh'},
               'tables': {}, 'files': [], 'sections': {}}
        if stats: man['database']['db_version'] = stats.get('db_version')
        data = {}
        for tb in _tables(con):
            cols, n, files = _csv(con, tb, ex)
            man['tables'][tb] = {'rows': n, 'columns': cols, 'files': files}
            if n <= SMALL and tb != 'fts':
                cur = con.execute('SELECT * FROM "%s"' % tb)
                data[tb] = [dict(zip(cols, r)) for r in cur]
        man['tables']['blobs'] = {'rows': con.execute('SELECT count(*) FROM blobs').fetchone()[0], 'columns': ['sha', 'data'],
                                  'files': [], 'note': 'raw bytes; in the full database (fetch-full.sh) and served one by one at /_blob/<sha>.<ext>'}
        with gzip.open(ex / 'cedwyn-data.json.gz', 'wt', encoding='utf-8', compresslevel=6) as f: json.dump(data, f, ensure_ascii=False, default=str)
        # per-section slices
        if 'themes' in man['tables'] and 'locations' in man['tables']:
            tcols = [d[1] for d in con.execute('PRAGMA table_info(themes)')]
            for trow in con.execute('SELECT * FROM themes').fetchall():
                th = dict(zip(tcols, trow)); tid = th['id']
                cur = con.execute('SELECT a.*, l.path AS path, l.url AS url FROM locations l JOIN artifacts a ON a.id=l.aid WHERE l.theme=? ORDER BY l.path', (tid,))
                cols = [d[0] for d in cur.description]; rows = [dict(zip(cols, r)) for r in cur]
                recs = []
                if 'section_records' in man['tables']:   # the section's own database rows (public/_db/section.sqlite), merged by build_db
                    for k, i, sq, dt in con.execute('SELECT kind, id, seq, data FROM section_records WHERE theme=? ORDER BY seq', (tid,)):
                        try: dt = json.loads(dt)
                        except Exception: pass
                        recs.append({'kind': k, 'id': i, 'seq': sq, 'data': dt})
                with gzip.open(ex / 'sections' / ('%s.json.gz' % tid), 'wt', encoding='utf-8', compresslevel=6) as f:
                    json.dump({'schema': 'cedwyn_section_slice/v1', 'section': th, 'records': recs, 'artifacts': rows}, f, ensure_ascii=False, default=str)
                sdb = out.parent / tid / '_db' / 'config.json'
                man['sections'][tid] = {'file': 'sections/%s.json.gz' % tid, 'artifacts': len(rows), 'records': len(recs),
                                        'section_db': ('/%s/_db/config.json' % tid) if sdb.exists() else None}
        # metadata-only sqlite
        tmp = pathlib.Path('cedwyn-metadata.sqlite3'); tmp.unlink(missing_ok=True)
        dst = sqlite3.connect(tmp); con.backup(dst); dst.execute('DROP TABLE IF EXISTS blobs')
        try: dst.execute('DROP TABLE IF EXISTS fts')
        except Exception: pass
        dst.commit(); dst.execute('VACUUM'); dst.close()
        with open(tmp, 'rb') as fi, gzip.open(ex / 'cedwyn-metadata.sqlite3.gz', 'wb', compresslevel=6) as fo: shutil.copyfileobj(fi, fo)
        tmp.unlink(missing_ok=True)
        if (ex / 'cedwyn-metadata.sqlite3.gz').stat().st_size > 24_000_000:
            (ex / 'cedwyn-metadata.sqlite3.gz').unlink(); man['metadata_sqlite'] = 'not written: over 24 MB; use the CSV files or fetch-full.sh'
        con.close()
        sh = ('#!/bin/sh\n# Rebuild the complete Cedwyn catalogue database (every table, blobs included) from its chunk files.\n'
              '# Usage: sh fetch-full.sh [site]   -> ./cedwyn.sqlite3, then open it with any SQLite tool.\nset -e\n'
              'B="${1:-https://cedwyn.bucklerfamily.estate}"\nN=%d\ni=0\n: > cedwyn.sqlite3\n'
              'while [ "$i" -lt "$N" ]; do curl -sfL "$B/db/cedwyn.sqlite3.$(printf %%03d "$i")" >> cedwyn.sqlite3; i=$((i+1)); done\n'
              'echo "expected sha256 %s"\n(sha256sum cedwyn.sqlite3 2>/dev/null || shasum -a 256 cedwyn.sqlite3)\n') % (
              (stats or {}).get('chunks') or -(-dbf.stat().st_size // int(os.environ.get('DB_CHUNK', 256 * 1024))), full_sha)
        (ex / 'fetch-full.sh').write_text(sh, encoding='utf-8')
        for p in sorted(ex.rglob('*')):
            if p.is_file(): man['files'].append({'path': '/db/export/' + p.relative_to(ex).as_posix(), 'bytes': p.stat().st_size, 'sha256': _sha(p)})
        man['seconds'] = round(time.time() - t0, 1)
        json.dump(man, open(ex / 'manifest.json', 'w'), indent=1, ensure_ascii=False, default=str)
        print('db_export: %d tables, %d sections, %d files, %.1f MB, %.0fs' % (len(man['tables']), len(man['sections']), len(man['files']),
              sum(f['bytes'] for f in man['files']) / 1e6, man['seconds']))
        return man
    except Exception as e:
        print('db_export: skipped:', repr(e)[:300]); return None
if __name__ == '__main__': run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'dist/db')
