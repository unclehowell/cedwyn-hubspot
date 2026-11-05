#!/usr/bin/env python3
"""dbmap.py - maps where each row of the `blobs` table sits inside the SQLite file, so a page's service worker can read a
theme's JSON/CSV/XML or an image straight out of the chunked database (/db/cedwyn.sqlite3.NNN) with plain HTTP reads.
For every blob: total length, the absolute byte offset/length of the part stored in its b-tree cell, and the overflow
pages that hold the rest (as runs of consecutive pages). Every entry is checked: the bytes read back through the map
must hash to the row's sha256, or the build stops. Paths come from the `locations` table (every place a file appears,
in every theme). - Sion's Tab agent"""
import sqlite3, hashlib, struct, sys, json

def varint(b, i):
    v = 0
    for k in range(9):
        c = b[i + k]
        if k == 8: return (v << 8) | c, i + 9
        v = (v << 7) | (c & 0x7f)
        if c < 0x80: return v, i + k + 1

def build(dbfile, chunk, prefix, suffix_len):
    con = sqlite3.connect(str(dbfile))
    root = con.execute("SELECT rootpage FROM sqlite_master WHERE type='table' AND name='blobs'").fetchone()[0]
    sha_of = {}; mime_of = {}
    for sha, mime in con.execute('SELECT a.sha, a.mime FROM artifacts a WHERE a.has_blob=1'): mime_of[sha] = mime
    locs = con.execute('SELECT l.path, a.sha FROM locations l JOIN artifacts a ON a.id=l.aid WHERE a.has_blob=1').fetchall()
    con.close()
    f = open(dbfile, 'rb'); hdr = f.read(100)
    ps = struct.unpack('>H', hdr[16:18])[0]; ps = 65536 if ps == 1 else ps
    U = ps - hdr[20]
    def page(n): f.seek((n - 1) * ps); return f.read(ps)
    X = U - 35; M = ((U - 12) * 32 // 255) - 23
    blobs = []; index = {}
    stack = [root]
    while stack:
        pn = stack.pop(); b = page(pn); h = 100 if pn == 1 else 0
        t = b[h]; nc = struct.unpack('>H', b[h + 3:h + 5])[0]
        if t == 0x05:   # interior table page: children then right-most pointer
            kids = [struct.unpack('>I', b[h + 8 + 0:h + 12])[0]]
            ptrs = [struct.unpack('>H', b[h + 12 + 2 * k:h + 14 + 2 * k])[0] for k in range(nc)]
            kids = [struct.unpack('>I', b[o:o + 4])[0] for o in ptrs] + kids
            stack.extend(reversed(kids)); continue
        if t != 0x0d: raise SystemExit('dbmap: unexpected page type %d at page %d' % (t, pn))
        for k in range(nc):
            o = struct.unpack('>H', b[h + 8 + 2 * k:h + 10 + 2 * k])[0]
            P, i = varint(b, o); _rowid, i = varint(b, i)
            local = P if P <= X else (lambda K: K if K <= X else M)(M + ((P - M) % (U - 4)))
            pay_abs = (pn - 1) * ps + i
            first_ovf = struct.unpack('>I', b[i + local:i + local + 4])[0] if P > local else 0
            # record header: sha (text) then data (blob)
            hs, j = varint(b, i); st1, j = varint(b, j); st2, j = varint(b, j)
            if not (st1 >= 13 and st1 % 2 == 1 and st2 >= 12 and st2 % 2 == 0): raise SystemExit('dbmap: unexpected record at page %d' % pn)
            sl = (st1 - 13) // 2; bl = (st2 - 12) // 2
            sha = bytes(b[i + hs:i + hs + sl]).decode()
            boff = hs + sl
            if boff > local: raise SystemExit('dbmap: blob starts in overflow')
            llen = min(bl, local - boff)
            runs = []; rem = bl - llen; pg = first_ovf
            while rem > 0:
                if not pg: raise SystemExit('dbmap: overflow chain ends early')
                ob = page(pg); take = min(U - 4, rem)
                if runs and runs[-1][0] + runs[-1][1] == pg: runs[-1][1] += 1
                else: runs.append([pg, 1])
                rem -= take; pg = struct.unpack('>I', ob[:4])[0]
            index[sha] = len(blobs)
            blobs.append([bl, pay_abs + boff, llen, [x for r in runs for x in r], mime_of.get(sha, 'application/octet-stream'), sha[:16]])
    # check every entry: read through the map, hash, compare
    for e in blobs:
        n, off, llen, flat = e[0], e[1], e[2], e[3]
        f.seek(off); parts = [f.read(llen)]; rem = n - llen
        for a in range(0, len(flat), 2):
            for pg in range(flat[a], flat[a] + flat[a + 1]):
                take = min(U - 4, rem); f.seek((pg - 1) * ps + 4); parts.append(f.read(take)); rem -= take
        if hashlib.sha256(b''.join(parts)).hexdigest()[:16] != e[5]: raise SystemExit('dbmap: sha mismatch for ' + e[5])
    f.seek(0); hh = hashlib.sha256()
    while True:
        c = f.read(1 << 20)
        if not c: break
        hh.update(c)
    f.close()
    paths = {p: index[s] for p, s in locs if s in index}
    return {'v': hh.hexdigest()[:12], 'ps': ps, 'u': U, 'chunk': chunk, 'prefix': prefix, 'suffixLength': suffix_len,
            'blobs': blobs, 'paths': paths}

if __name__ == '__main__':
    m = build(sys.argv[1], 524288, '/db/cedwyn.sqlite3.', 3)
    print(json.dumps({'blobs': len(m['blobs']), 'paths': len(m['paths']), 'v': m['v']}))
