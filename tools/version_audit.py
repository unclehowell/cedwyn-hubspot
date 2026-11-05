#!/usr/bin/env python3
"""Cedwyn version standard audit (docs/VERSION-STANDARD.md 1.0.0) - the flywheel's check. Stdlib only.
Usage (repo root): python3 tools/version_audit.py [--live] [--fix] [--root DIR]
Checks web/_cedwyn/version-gate.json against the standard and data/ebooks.json; --live also reads the public site.
--fix corrects minor drift in the manifest only (order, stray per-version prices, latest price from data/ebooks.json).
Exit 0 = clean (or every finding fixed), 1 = findings left. 1.0.0 (2026-11-01) - Cedwyn editors"""
import json, re, sys, os, urllib.request
SITE = "https://cedwyn.bucklerfamily.estate"
STEP = 4.99
BANNED = ["says", "claims", "according to", "hearsay", "unverified", "alleged", "fraud", "stolen"]
PER_UNIT = re.compile(r"\b(per page|a page|per day|a day|pennies|less than a coffee)\b|\d+p\s*(a|per)\s*page", re.I)
SEM = re.compile(r"^\d+\.\d+\.\d+$")
def key(v): return tuple(int(x) for x in v.split("."))
def gbp(s):
    m = re.search(r"\d+(?:\.\d+)?", str(s or "")); return float(m.group()) if m else 0.0
def ladder(n, top): return [0.0 if i == 0 else max(0.0, round(top - STEP * (n - 1 - i), 2)) for i in range(n)]
def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": "cedwyn-version-audit/1.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        b = r.read(); return (r.status, b) if binary else (r.status, b.decode("utf-8", "replace"))
def main(argv):
    root = argv[argv.index("--root") + 1] if "--root" in argv else "."
    live, fix = "--live" in argv, "--fix" in argv
    mp = os.path.join(root, "web/_cedwyn/version-gate.json"); dp = os.path.join(root, "data/ebooks.json")
    M = json.load(open(mp, encoding="utf-8")); D = json.load(open(dp, encoding="utf-8")) if os.path.exists(dp) else {"books": []}
    books = {b["id"]: b for b in D.get("books", [])}
    out, fixed = [], []
    def find(msg): out.append(msg)
    if M.get("standard") != "1.0.0": find("manifest: standard is not 1.0.0")
    if M.get("price_step_gbp") != STEP: find("manifest: price_step_gbp is not 4.99")
    for im in M.get("images", []):
        if not re.match(r"^/nft-art/art/[a-z0-9.-]+\.webp$", im): find(f"image {im}: not /nft-art/art/*.webp")
    for k, it in (M.get("ebooks") or {}).items():
        vs = it.get("versions") or []
        if not vs: find(f"{k}: no versions"); continue
        if [v.get("v") for v in vs] != sorted([v.get("v") for v in vs], key=lambda x: key(x) if SEM.match(str(x)) else (0,)):
            if fix: vs.sort(key=lambda v: key(v["v"])); fixed.append(f"{k}: versions re-sorted oldest first")
            else: find(f"{k}: versions not oldest first")
        seen = set()
        for v in vs:
            if not SEM.match(str(v.get("v", ""))): find(f"{k}: bad version {v.get('v')!r}")
            if v.get("v") in seen: find(f"{k}: duplicate version {v.get('v')}")
            seen.add(v.get("v"))
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v.get("date", ""))): find(f"{k} v{v.get('v')}: date not YYYY-MM-DD")
            if len(str(v.get("change", ""))) < 3: find(f"{k} v{v.get('v')}: no 'what changed' text")
            if "price" in v:
                if fix: v.pop("price"); fixed.append(f"{k} v{v['v']}: stored per-version price removed (prices are computed)")
                else: find(f"{k} v{v.get('v')}: stores its own price (prices are computed)")
            txt = str(v.get("change", ""))
            for w in BANNED:
                if re.search(r"\b" + re.escape(w) + r"\b", txt, re.I): find(f"{k} v{v.get('v')}: banned word '{w}' in change text")
            if PER_UNIT.search(txt): find(f"{k} v{v.get('v')}: per-page/per-day price wording")
        if vs[0].get("v") != "0.0.1": find(f"{k}: first version is v{vs[0].get('v')}, must be v0.0.1 (free)")
        cid = it.get("card") or next((b for b in books if b.split("-")[0] == k or b.startswith(k)), None)
        b = books.get(cid)
        if b and it.get("price"):
            if b.get("price") and gbp(b["price"]) != gbp(it["price"]) and gbp(b["price"]) > 0:
                if fix: it["price"] = b["price"]; fixed.append(f"{k}: latest price set to {b['price']} from data/ebooks.json")
                else: find(f"{k}: latest price {it['price']} != data/ebooks.json {b['price']}")
            if b.get("pages") and vs[-1].get("pages") and int(b["pages"]) != int(vs[-1]["pages"]): find(f"{k}: latest pages {vs[-1]['pages']} != data/ebooks.json {b['pages']}")
        it["_ladder"] = ladder(len(vs), gbp(it.get("price")))
    if live:
        try:
            st, _ = get(SITE + "/_cedwyn/version-gate.json")
            if st != 200: find(f"live: /_cedwyn/version-gate.json answered {st}")
        except Exception as e: find(f"live: /_cedwyn/version-gate.json not served ({str(e)[:60]})")
        try:
            st, html = get(SITE + "/ebooks/")
            for k, it in (M.get("ebooks") or {}).items():
                if not it.get("price"): continue
                cid = it.get("card"); m = re.search(r'<li class="sh-card" id="%s">(.*?)</li>' % re.escape(cid), html, re.S) if cid else None
                if not m: m = re.search(r'<li class="sh-card" id="[^"]*">(?:(?!</li>).)*data-gb="%s@(?:(?!</li>).)*</li>' % re.escape(k), html, re.S)
                if not m: find(f"live /ebooks/: no card for {k}"); continue
                opts = [re.sub(r"\s+", " ", o).strip() for o in re.findall(r"<option[^>]*>([^<]+)</option>", m.group(0))]
                want = ["v%s — %s" % (v["v"], "free" if p == 0 else "£%.2f" % p) for v, p in zip(it["versions"], it["_ladder"])]
                for w in want:
                    if not any(o.startswith(w) for o in opts): find(f"live /ebooks/ {k}: drop-down lacks '{w}' (has {opts})")
        except Exception as e: find(f"live: /ebooks/ not read ({str(e)[:60]})")
        for im in M.get("images", [])[:60]:
            try:
                st, b = get(SITE + im, binary=True)
                if st != 200 or len(b) > 400 * 1024: find(f"live image {im}: status {st}, {len(b)} bytes")
            except Exception as e: find(f"live image {im}: {str(e)[:50]}")
    for it in (M.get("ebooks") or {}).values(): it.pop("_ladder", None)
    if fix and fixed:
        open(mp, "w", encoding="utf-8").write(json.dumps(M, ensure_ascii=False, indent=1) + "\n")
    for f in fixed: print("FIXED  " + f)
    for f in out: print("FINDING " + f)
    print(f"version_audit: {len(out)} finding(s), {len(fixed)} fixed")
    return 1 if out else 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
