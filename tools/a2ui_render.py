#!/usr/bin/env python3
"""a2ui_render.py - renders an A2UI v0.9-shaped message list to static HTML with the Cedwyn component catalog.

Contract (see web/_cedwyn/a2ui/catalog.json and work/cedwyn-data-arch/PLAN.md section 2.3):
  messages = [{"version":"v0.9","createSurface":{"surfaceId","catalogId"}},
              {"version":"v0.9","updateComponents":{"surfaceId","components":[{id, component, ...props}]}},
              {"version":"v0.9","updateDataModel":{"surfaceId","path":"/","value":{...}}}]
  A prop is a literal or {"path": "/abs/pointer"} (from the data model root) or {"path": "rel/pointer"} (from the current
  template item). "children" is a list of ids, or {"path": "...", "componentId": "..."} to repeat a template per list item.
  Only catalog components render; an unknown component raises (local) so it never reaches a page. No HTML is accepted from
  data: every string is escaped. Links must be root-relative or relative (outbound links are refused).
Used by tools/views.py at build time. Stdlib only. - Cedwyn data-driven architecture, WP1 pilot, 30 Oct 2026."""
import html, json, re

CATALOG_ID = "https://cedwyn.bucklerfamily.estate/_cedwyn/a2ui/catalog.json"
E = lambda s: html.escape("" if s is None else str(s), quote=True)

class RenderError(Exception):
    pass

def _ptr(obj, path):
    cur = obj
    for part in [p for p in path.split("/") if p != ""]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, list):
            try: cur = cur[int(part)]
            except (ValueError, IndexError): return None
        elif isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
        if cur is None: return None
    return cur

def _safe_href(u):
    if u is None: return None
    u = str(u)
    if u.startswith("//") or re.match(r"^[a-z][a-z0-9+.-]*:", u, re.I):
        raise RenderError("outbound or scheme link refused: " + u[:80])
    return u

class Surface:
    def __init__(self, messages):
        self.components, self.data, self.surface = {}, {}, None
        for m in messages:
            if "createSurface" in m:
                cs = m["createSurface"]; self.surface = cs.get("surfaceId")
                if cs.get("catalogId") not in (CATALOG_ID, None):
                    raise RenderError("unknown catalog " + str(cs.get("catalogId")))
            elif "updateComponents" in m:
                for c in m["updateComponents"].get("components", []):
                    self.components[c["id"]] = c
            elif "updateDataModel" in m:
                u = m["updateDataModel"]
                if u.get("path", "/") in ("/", ""): self.data = u.get("value") or {}
                else: self.data[u["path"].strip("/")] = u.get("value")

    def val(self, v, ctx):
        if isinstance(v, dict) and set(v) <= {"path"} and "path" in v:
            p = v["path"]
            return _ptr(self.data, p) if p.startswith("/") else _ptr(ctx if ctx is not None else {}, p)
        if isinstance(v, dict) and "fmt" in v:          # {"fmt": "{n} entries", "args": {"n": {"path": ...}}}
            args = {k: self.val(a, ctx) for k, a in v.get("args", {}).items()}
            return v["fmt"].format(**args)
        return v

    def kids(self, c, ctx):
        ch = c.get("children")
        if ch is None:
            return [(c["child"], ctx)] if c.get("child") else []
        if isinstance(ch, dict):
            items = self.val({"path": ch["path"]}, ctx) or []
            return [(ch["componentId"], it) for it in items]
        return [(i, ctx) for i in ch]

    def render(self, cid="root", ctx=None):
        c = self.components.get(cid)
        if c is None: raise RenderError("missing component id " + cid)
        fn = COMPONENTS.get(c["component"])
        if fn is None: raise RenderError("component not in catalog: " + c["component"])
        return fn(self, c, ctx)

    def inner(self, c, ctx):
        return "".join(self.render(i, it) for i, it in self.kids(c, ctx))

# ---------------------------------------------------------------- catalog components (class names = the app's CSS)
def _cls(s, c, ctx, base):
    extra = s.val(c.get("className"), ctx)
    return E(base + (" " + extra if extra else ""))

def Page(s, c, ctx):
    css = "".join('<link rel="stylesheet" href="%s">' % E(_safe_href(u)) for u in c.get("css", []))
    hs = "".join('<script src="%s"%s></script>' % (E(_safe_href(x["src"])), " defer" if x.get("defer") else "") for x in c.get("headScripts", []))
    js = "".join('<script src="%s" defer></script>' % E(_safe_href(u)) for u in c.get("js", []))
    title, desc = s.val(c.get("title"), ctx), s.val(c.get("description"), ctx)
    lang = c.get("lang", "en")
    return ('<!doctype html><html lang="%s"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>%s</title><meta name="description" content="%s">%s%s'
            '<meta name="generator" content="cedwyn-a2ui/0.1 (A2UI v0.9 surface %s)"></head><body class="%s"><main class="%s">%s</main>%s</body></html>\n'
            % (E(lang), E(title), E(desc), css, hs, E(s.surface), E(c.get("bodyClass", "")), E(c.get("mainClass", "")), s.inner(c, ctx), js))

def HiddenHeading(s, c, ctx):
    return '<h1 class="vh">%s</h1>' % E(s.val(c.get("text"), ctx))

def Heading(s, c, ctx):
    lvl = int(c.get("level", 2)); lvl = min(max(lvl, 1), 4)
    return '<h%d class="%s">%s</h%d>' % (lvl, _cls(s, c, ctx, "a2-h"), E(s.val(c.get("text"), ctx)), lvl)

def Figure(s, c, ctx):
    src = _safe_href(s.val(c.get("src"), ctx)); alt = s.val(c.get("alt"), ctx)
    w, h = c.get("width"), c.get("height")
    dims = (' width="%s" height="%s"' % (int(w), int(h))) if w and h else ""
    return '<figure class="%s"><img src="%s" alt="%s"%s decoding="async"></figure>' % (_cls(s, c, ctx, "a2-figure"), E(src), E(alt), dims)

def Text(s, c, ctx):
    t = s.val(c.get("text"), ctx)
    if t in (None, ""): return ""
    label = s.val(c.get("label"), ctx)
    lab = "<b>%s:</b> " % E(label) if label else ""
    return '<p class="%s">%s%s</p>' % (_cls(s, c, ctx, "a2-text"), lab, E(t))

def Link(s, c, ctx):
    href = _safe_href(s.val(c.get("href"), ctx)); t = s.val(c.get("text"), ctx)
    return '<a href="%s">%s</a>' % (E(href), E(t)) if href else E(t)

def Inline(s, c, ctx):   # a paragraph made of child components (links, text runs)
    sep = c.get("separator", "")
    parts = [s.render(i, it) for i, it in s.kids(c, ctx)]
    return '<p class="%s">%s</p>' % (_cls(s, c, ctx, "a2-inline"), E(sep).join(p for p in parts if p))

def Run(s, c, ctx):
    return E(s.val(c.get("text"), ctx))

def Details(s, c, ctx):
    return '<details class="%s"><summary>%s</summary>%s</details>' % (_cls(s, c, ctx, "a2-details"), E(s.val(c.get("summary"), ctx)), s.inner(c, ctx))

def Section(s, c, ctx):
    head = s.val(c.get("heading"), ctx)
    h = "<h2>%s</h2>" % E(head) if head else ""
    body = s.inner(c, ctx)
    if not body and c.get("hideEmpty", True): return ""
    if c.get("list"):
        body = '<ul class="%s">%s</ul>' % (E(c.get("listClass", "")), body)
    if not body and c.get("hideEmpty", True): return ""
    return '<section class="%s">%s%s</section>' % (_cls(s, c, ctx, "a2-section"), h, body)

def ListItem(s, c, ctx):
    t = s.val(c.get("text"), ctx); href = s.val(c.get("href"), ctx); lead = s.val(c.get("lead"), ctx)
    core = ('<a href="%s">%s</a>' % (E(_safe_href(href)), E(t))) if href else E(t)
    if lead: core = "<b>%s</b>: %s" % (E(lead), core) if t else "<b>%s</b>" % E(lead)
    return "<li>%s%s</li>" % (core, s.inner(c, ctx))

def TextList(s, c, ctx):   # a plain list of strings from the data model
    items = s.val(c.get("items"), ctx) or []
    if not items: return ""
    return '<ul class="%s">%s</ul>' % (_cls(s, c, ctx, "a2-list"), "".join("<li>%s</li>" % E(x) for x in items))

def FilterBar(s, c, ctx):
    out = ['<form class="%s" role="search" onsubmit="return false">' % _cls(s, c, ctx, "a2-filter")]
    for f in c.get("fields", []):
        lab = E(s.val(f.get("label"), ctx)); fid = E(f["id"])
        if f["kind"] == "search":
            out.append('<label>%s <input type="search" id="%s" placeholder="%s"></label>' % (lab, fid, E(s.val(f.get("placeholder"), ctx))))
        else:
            opts = s.val(f.get("options"), ctx) or []
            o = ['<option value="">%s</option>' % E(s.val(f.get("allLabel"), ctx) or "All")]
            for op in opts:
                v, t = (op.get("value"), op.get("label")) if isinstance(op, dict) else (op, op)
                o.append('<option value="%s">%s</option>' % (E(v), E(t)))
            out.append('<label>%s <select id="%s">%s</select></label>' % (lab, fid, "".join(o)))
    if c.get("countId"):
        out.append('<span id="%s" class="%s" aria-live="polite">%s</span>' % (E(c["countId"]), E(c.get("countClass", "")), E(s.val(c.get("countText"), ctx) or "")))
    out.append("</form>")
    return "".join(out)

def CardList(s, c, ctx):
    return '<div class="%s" id="%s">%s</div>' % (_cls(s, c, ctx, "a2-cards"), E(c.get("domId", c["id"])), s.inner(c, ctx))

def Card(s, c, ctx):
    href = _safe_href(s.val(c.get("href"), ctx))
    kicker, title = s.val(c.get("kicker"), ctx), s.val(c.get("title"), ctx)
    attrs = "".join(' data-%s="%s"' % (E(k), E(s.val(v, ctx))) for k, v in c.get("attrs", {}).items())
    head = '<span class="a2-kicker">%s</span> %s' % (E(kicker), E(title)) if kicker else E(title)
    head = '<a href="%s">%s</a>' % (E(href), head) if href else head
    meta = []
    for m in c.get("meta", []):
        mv = s.val(m.get("value"), ctx)
        if mv not in (None, ""): meta.append('<span class="a2-meta-i"><span class="a2-l">%s</span> %s</span>' % (E(s.val(m.get("label"), ctx)), E(mv)))
    body = s.val(c.get("body"), ctx); bl = s.val(c.get("bodyLabel"), ctx)
    badge, bcls = s.val(c.get("badge"), ctx), s.val(c.get("badgeClass"), ctx)
    foot = s.val(c.get("foot"), ctx)
    return ('<article class="%s"%s><h3 class="a2-card-h">%s</h3>%s%s<p class="a2-card-f">%s%s</p></article>'
            % (_cls(s, c, ctx, "a2-card"), attrs, head,
               ('<p class="a2-meta">%s</p>' % "".join(meta)) if meta else "",
               ('<p class="a2-card-b"><span class="a2-l">%s</span> %s</p>' % (E(bl), E(body))) if body else "",
               ('<span class="%s">%s</span>' % (E(bcls or "a2-badge"), E(badge))) if badge else "",
               (' <small>%s</small>' % E(foot)) if foot else ""))

def Badge(s, c, ctx):
    return '<span class="%s">%s</span>' % (E(s.val(c.get("className"), ctx) or "a2-badge"), E(s.val(c.get("text"), ctx)))

def Row(s, c, ctx):
    return '<p class="%s">%s</p>' % (_cls(s, c, ctx, "a2-row"), " ".join(p for p in (s.render(i, it) for i, it in s.kids(c, ctx)) if p))

def Span(s, c, ctx):
    t = s.val(c.get("text"), ctx)
    return '<span class="%s">%s</span>' % (_cls(s, c, ctx, "a2-span"), E(t)) if t not in (None, "") else ""

def Repeat(s, c, ctx):   # a group without its own element (for nested templates)
    return s.inner(c, ctx)

def DetailSections(s, c, ctx):   # [{heading, text | items, form}] from the data model; form "term" groups into a <dl>
    out, dl = [], []
    def flush():
        if dl: out.append('<dl class="%s">%s</dl>' % (E(c.get("termClass", "")), "".join(dl))); dl.clear()
    for sec in s.val(c.get("sections"), ctx) or []:
        if sec.get("form") == "term":
            dl.append("<dt>%s</dt><dd>%s</dd>" % (E(sec.get("heading")), _runs(sec["runs"]) if sec.get("runs") else E(sec.get("text", ""))))
            continue
        flush()
        out.append("<h2>%s</h2>" % E(sec.get("heading")))
        if sec.get("items"): out.append('<ul class="%s">%s</ul>' % (E(c.get("listClass", "")), "".join("<li>%s</li>" % E(x) for x in sec["items"])))
        if sec.get("text"): out.append("<p>%s</p>" % E(sec["text"]))
    flush()
    return "".join(out)

def _runs(runs):
    return "".join(('<a href="%s">%s</a>' % (E(_safe_href(r["href"])), E(r["text"]))) if r.get("href") else E(r.get("text")) for r in runs)

def RichParas(s, c, ctx):   # [{class?, runs: [{text, href?}]}] -> one <p> per paragraph, class from the data if given
    out = []
    for para in s.val(c.get("paras"), ctx) or []:
        cls = para.get("class") or s.val(c.get("className"), ctx) or "a2-para"
        out.append('<p class="%s">%s</p>' % (E(cls), _runs(para.get("runs", []))))
    return "".join(out)

COMPONENTS = {k: v for k, v in globals().items() if k[:1].isupper() and callable(v) and k not in ("Surface", "RenderError", "E", "CATALOG_ID")}

def render(messages, root="root"):
    s = Surface(messages)
    return s.render(root)

def catalog():
    return {"catalogId": CATALOG_ID, "version": "0.1.0", "spec": "A2UI v0.9 message model (createSurface, updateComponents, updateDataModel)",
            "components": sorted(COMPONENTS)}

if __name__ == "__main__":
    import sys
    msgs = json.load(open(sys.argv[1]))
    sys.stdout.write(render(msgs))
