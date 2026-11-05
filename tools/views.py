#!/usr/bin/env python3
"""views.py - the central catalogue -> per-webapp database -> pages step of the Cedwyn build.

  data/core/records/*.json        the central master catalogue (schema: data/core/schema/core-record.schema.json)
  data/views/<app>.view.json      each webapp's selection rule, projection, page copy and page list
  <dist>/<app>/_ui/*.a2ui.json    the webapp's page templates (A2UI v0.9-shaped; shipped by the app branch)
  ->  <dist>/<app>/_db/view.json  the webapp's own database (public rows only, derived, never edited by hand)
  ->  <dist>/<app>/_ui/<page>.a2ui.json  the full surface (template + data model) for agents
  ->  <dist>/<app>/<page>.html     pages rendered by tools/a2ui_render.py with the app's own CSS classes

Build use:  python3 tools/views.py dist            (never fails the build: an app whose view fails keeps its static pages)
Local use:  python3 tools/views.py OUT --app kissed-frogs --strict [--ui <dir with _ui templates>]
Rollback for one app: "enabled": false in its view file. Plan: work/cedwyn-data-arch/PLAN.md (Cedwyn data-driven architecture, WP1).
Stdlib only."""
import json, os, re, sys, pathlib, datetime, traceback
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import a2ui_render as AR

BANNED = re.compile(r"\b(says|claims|according to|hearsay|unverified|alleged|fraud\w*|stolen|tenant farmers?)\b", re.I)
PRIVATE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|(?:\+44\s?7|\b07)\d{3}\s?\d{3}\s?\d{3}\b|(?i:api[_-]?key|secret|token)\s*[:=]")

# ------------------------------------------------------------------ core
def load_schema():
    return json.load(open(ROOT / "data/core/schema/core-record.schema.json", encoding="utf-8"))

def validate(rec, schema):
    """Small stdlib subset of JSON Schema 2020-12: required, enum, type of top-level props, id pattern, no extra props."""
    errs, props = [], schema["properties"]
    for k in schema.get("required", []):
        if k not in rec: errs.append("missing " + k)
    for k, v in rec.items():
        if k not in props: errs.append("unknown field " + k); continue
        p = props[k]
        if "enum" in p and v not in p["enum"]: errs.append("%s not allowed: %r" % (k, v))
        if "pattern" in p and isinstance(v, str) and not re.match(p["pattern"], v): errs.append("%s pattern: %r" % (k, v))
        if k == "scope" and isinstance(v, dict) and v.get("disposition") not in p["properties"]["disposition"]["enum"]:
            errs.append("scope.disposition not allowed: %r" % v.get("disposition"))
    return errs

def load_core(strict=False):
    schema, recs, seen, problems = load_schema(), [], set(), []
    for f in sorted((ROOT / "data/core/records").glob("*.json")):
        doc = json.load(open(f, encoding="utf-8"))
        for r in doc.get("records", []):
            e = validate(r, schema)
            if r.get("id") in seen: e.append("duplicate id")
            seen.add(r.get("id"))
            if e: problems.append("%s %s: %s" % (f.name, r.get("id"), "; ".join(e)))
            recs.append(r)
    # Adapter (until WP2 merges them): graded evidence from data/evidence-grades.json joins the catalogue as kind=evidence.
    eg = ROOT / "data/evidence-grades.json"
    if eg.exists():
        for x in json.load(open(eg, encoding="utf-8")).get("evidence", []):
            ev = (x.get("ev") or "").strip()
            if ev and ev not in seen:
                seen.add(ev)
                recs.append({"id": ev, "kind": "evidence", "title": ev, "grade": x.get("evidence_grade"), "page": "/" + (x.get("path") or "").lstrip("/"),
                             "aliases": x.get("aliases", []), "scope": {"disposition": "in_scope"}, "public": True})
    if problems and strict: raise SystemExit("core validation failed:\n" + "\n".join(problems))
    return recs, problems

# ------------------------------------------------------------------ views
def get(rec, dotted):
    cur = rec
    for k in dotted.split("."):
        cur = cur.get(k) if isinstance(cur, dict) else None
    return cur

def select(recs, rule):
    kinds = set(rule.get("select", {}).get("kind", [])) or None
    out = []
    for r in recs:
        if not r.get("public"): continue                      # public by construction
        if kinds and r.get("kind") not in kinds: continue
        ok = True
        for w in rule.get("select", {}).get("where", []):
            v = get(r, w["field"])
            if w["op"] == "eq": ok = v == w["value"]
            elif w["op"] == "in": ok = v in w["value"]
            elif w["op"] == "ne": ok = v != w["value"]
            elif w["op"] == "has": ok = isinstance(v, list) and w["value"] in v
            if not ok: break
        if ok: out.append(r)
    key = rule.get("order_by", "id")
    def sk(r):
        v = get(r, key)
        m = re.match(r"^([A-Z]+)-(\d+)$", str(v or ""))
        return (m.group(1), int(m.group(2))) if m else (str(v), 0)
    out.sort(key=sk)
    proj = rule.get("project")
    return [{k: r[k] for k in proj if k in r} if proj else dict(r) for r in out]

def slug_class(label):
    return "kf-st st-" + re.sub(r"[^a-z0-9]+", "-", (label or "").lower()).strip("-")

def enrich(app, view, data, recs):
    """App-neutral derived fields used by templates (links, labels, counts, facets)."""
    copy = view.get("copy", {})
    by_id = {r["id"]: r for r in recs}
    evbase = view.get("evidence_links", "/research/evidence/")
    for coll, rows in data.items():
        if not isinstance(rows, list): continue
        for r in rows:
            if r.get("slug"): r["href"] = r["slug"] + "/"
            sc = r.get("scope") or {}
            if sc.get("label"): r["status"] = sc["label"]; r["status_class"] = slug_class(sc["label"])
            if sc.get("reason"): r["why"] = sc["reason"]
            if r.get("origin"):
                r["origin_label"] = copy.get("origins", {}).get(r["origin"], r["origin"])
                r["origin_note"] = copy.get("origin_notes", {}).get(r["origin"], "")
            if isinstance(r.get("date"), dict): r["date_display"] = r["date"].get("display", "")
            if isinstance(r.get("provenance"), dict): r["source_text"] = r["provenance"].get("reference", "")
            rel = []
            for rid in r.get("related", []):
                t = by_id.get(rid)
                if t and t.get("public"):
                    rel.append({"id": rid, "text": "%s · %s" % (rid, t.get("title", ""))[:160], "href": ("../" + t["slug"] + "/") if t.get("slug") else None})
            if rel: r["related_links"] = rel
            evs = []
            for e in r.get("evidence", []):
                t = by_id.get(e)
                href = (t or {}).get("page") or None
                evs.append({"text": e, "href": href})
            if evs: r["evidence_links"] = evs
    if "frogs" in data:
        data["facets"] = {"status": sorted({r.get("status") for r in data["frogs"] if r.get("status")}),
                          "origin": [{"value": k, "label": v} for k, v in copy.get("origins", {}).items() if any(r.get("origin") == k for r in data["frogs"])]}
    return data

def check_public(app, obj):
    """Gate: no banned words, private data or outbound links in what the view publishes."""
    text = json.dumps(obj, ensure_ascii=False)
    hits = []
    for m in BANNED.finditer(text): hits.append("banned word: " + m.group(0))
    for m in PRIVATE.finditer(text): hits.append("private data pattern: " + m.group(0)[:30])
    for m in re.finditer(r'"href":\s*"([^"]+)"', text):
        if re.match(r"^(?:[a-z]+:|//)", m.group(1), re.I): hits.append("outbound link: " + m.group(1)[:60])
    return hits

def build_view(app, view, recs):
    data = {name: select(recs, rule) for name, rule in view.get("collections", {}).items()}
    data = enrich(app, view, data, recs)
    data["copy"] = view.get("copy", {})
    data["meta"] = {"app": app, "view_version": view.get("version"), "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "source": "data/core (Cedwyn central catalogue)", "rule": "data/views/%s.view.json" % app,
                    "counts": {k: len(v) for k, v in data.items() if isinstance(v, list)}}
    c = data["copy"]
    if "frogs" in data:
        n = len(data["frogs"])
        c = dict(c); c["count_text"] = c.get("count", "{n} entries").format(n=n)
        c["meta_text"] = c.get("meta", "").format(version=view.get("version"), date=data["meta"]["generated"][:10])
        data["copy"] = c
    return data

def fill(template, data, surface_suffix=""):
    msgs = json.loads(json.dumps(template))
    sid = None
    for m in msgs:
        if "createSurface" in m: sid = m["createSurface"]["surfaceId"] + surface_suffix; m["createSurface"]["surfaceId"] = sid
        if "updateComponents" in m: m["updateComponents"]["surfaceId"] = sid
    msgs = [m for m in msgs if "updateDataModel" not in m]
    msgs.append({"version": "v0.9", "updateDataModel": {"surfaceId": sid, "path": "/", "value": data}})
    return msgs

def run_app(app, view, recs, dist, ui_dir=None, strict=False):
    out = pathlib.Path(dist) / app
    ui = pathlib.Path(ui_dir) if ui_dir else out
    data = build_view(app, view, recs)
    hits = check_public(app, data)
    if hits:
        raise RuntimeError("public gate failed: " + "; ".join(sorted(set(hits))[:10]))
    (out / "_db").mkdir(parents=True, exist_ok=True)
    json.dump(data, open(out / "_db" / "view.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    written = []
    for pg in view.get("pages", []):
        tpl = json.load(open(ui / pg["template"], encoding="utf-8"))
        name = pathlib.Path(pg["template"]).name.replace(".a2ui.json", "")
        if pg.get("each"):
            for item in data.get(pg["each"], []):
                d = dict(data); d["item"] = item
                html = AR.render(fill(tpl, d, "-" + item.get("id", "")))
                p = out / pg["out"].format(**item); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html, encoding="utf-8"); written.append(p)
        else:
            msgs = fill(tpl, data)
            html = AR.render(msgs)
            p = out / pg["out"]; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html, encoding="utf-8"); written.append(p)
            (out / "_ui").mkdir(parents=True, exist_ok=True)
            json.dump(msgs, open(out / "_ui" / (name + ".surface.a2ui.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return data, written

def main():
    a = sys.argv[1:]
    dist = a[0] if a and not a[0].startswith("--") else "dist"
    only = a[a.index("--app") + 1] if "--app" in a else None
    ui_dir = a[a.index("--ui") + 1] if "--ui" in a else None
    strict = "--strict" in a
    try:
        recs, problems = load_core(strict=strict)
    except SystemExit:
        raise
    except Exception as e:
        print("views: core could not load, every app keeps its static pages:", e); return 0
    for p in problems: print("views: core warning:", p)
    report = {}
    for vf in sorted((ROOT / "data/views").glob("*.view.json")):
        app = vf.name[:-len(".view.json")]
        if only and app != only: continue
        try:
            view = json.load(open(vf, encoding="utf-8"))
            if not view.get("enabled"): report[app] = "disabled (static pages kept)"; continue
            if not only and not (pathlib.Path(dist) / app / "_ui").is_dir():
                report[app] = "no _ui templates in the app output (static pages kept)"; continue
            data, written = run_app(app, view, recs, dist, ui_dir=ui_dir, strict=strict)
            report[app] = "ok: %s, %d pages" % (data["meta"]["counts"], len(written))
        except Exception as e:
            if strict: raise
            report[app] = "FAILED, static pages kept: %s" % e
            traceback.print_exc(limit=2)
    print("views:", json.dumps(report, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
