#!/usr/bin/env python3
"""Build the canonical Title Theory page and publish its machine-readable model."""
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def esc(value):
    return html.escape(str(value or ""), quote=True)

def link(path, label):
    return '<a href="' + esc(path) + '">' + esc(label) + '</a>'

def bullets(items):
    if not items:
        return "<p>None recorded.</p>"
    return "<ul>" + "".join("<li>" + esc(x) + "</li>" for x in items) + "</ul>"

def page(doc):
    hypotheses = []
    for h in sorted(doc.get("hypotheses", []), key=lambda x: x.get("rank", 999)):
        refs = []
        for ev in h.get("support", []):
            refs.append(link(next((r["path"] for r in doc.get("evidence_refs", []) if r.get("ev") == ev), "#"), ev))
        for ev in h.get("against_or_limits", []):
            if ev not in h.get("support", []):
                refs.append(link(next((r["path"] for r in doc.get("evidence_refs", []) if r.get("ev") == ev), "#"), ev))
        hypotheses.append(
            '<article class="hyp"><p class="meta">' + esc(h.get("id")) + " · Rank " + esc(h.get("rank")) +
            " · " + esc(h.get("class", "").replace("_", " ")) + "</p><h3>" + esc(h.get("title")) +
            "</h3><p><strong>Status:</strong> " + esc(h.get("status")) + "</p><p>" + esc(h.get("explanation")) +
            "</p><h4>What it explains</h4>" + bullets(h.get("what_it_explains", [])) +
            "<h4>Predictions if true</h4>" + bullets(h.get("predictions", [])) +
            "<h4>What would weaken or falsify it</h4>" + bullets(h.get("falsifiers", [])) +
            "<p><strong>Relevant artifacts:</strong> " + " · ".join(refs) + "</p>" +
            ("<p class='warning'>" + esc(h.get("publication_rule")) + "</p>" if h.get("publication_rule") else "") +
            "</article>"
        )
    stages = []
    for s in doc.get("working_mechanism", []):
        stage_refs = " · ".join(link(next((r["path"] for r in doc.get("evidence_refs", []) if r.get("ev") == ev), "#"), ev)
                                 for ev in s.get("source_evs", []))
        stages.append(
            "<article class='stage'><p class='meta'>" + esc(s.get("id")) + " · " + esc(s.get("period")) +
            "</p><h3>" + esc(s.get("stage")) + "</h3><p>" + esc(s.get("proposition")) +
            "</p><p><strong>If true:</strong> " + esc(s.get("if_true")) +
            "</p><p><strong>Alternative / evidence against:</strong> " + esc(s.get("against_or_alternative")) +
            "</p><p><strong>Artifacts:</strong> " + stage_refs + "</p></article>"
        )
    sims = []
    for s in doc.get("simulations", []):
        sims.append("<article class='sim'><h3>" + esc(s.get("id")) + " · " + esc(s.get("title")) +
                    "</h3><p>" + esc(s.get("purpose")) + "</p><p><strong>Inputs:</strong> " +
                    esc("; ".join(s.get("inputs", []))) + "</p><p><strong>Outputs:</strong> " +
                    esc("; ".join(s.get("outputs", []))) + "</p><p><strong>Rule:</strong> " +
                    esc(s.get("rule")) + "</p></article>")
    chronology = []
    for d in doc.get("date_conflicts", []):
        date_text = d.get("recorded_date") or (str(d.get("family_chronology_date", "")) + " / " + str(d.get("repository_probate_candidate", "")))
        chronology.append("<tr><th>" + esc(d.get("person")) + "</th><td>" + esc(date_text) + "</td><td>" + esc(d.get("status")) + "</td></tr>")
    graph_nodes = []
    for n in doc.get("causal_graph", {}).get("nodes", []):
        graph_nodes.append("<tr><th>" + esc(n.get("id")) + "</th><td>" + esc(n.get("label")) + "</td><td>" + esc(n.get("type")) + "</td></tr>")
    graph_edges = []
    for e in doc.get("causal_graph", {}).get("edges", []):
        graph_edges.append("<tr><td>" + esc(e.get("from")) + " → " + esc(e.get("to")) + "</td><td>" + esc(e.get("relation")) + "</td><td>" + esc(e.get("status")) + "</td></tr>")
    refs = []
    for r in doc.get("evidence_refs", []):
        refs.append("<li>" + link(r.get("path", "#"), r.get("ev", "Artifact")) +
                    " — " + esc(r.get("role")) +
                    (" — " + esc(r.get("note")) if r.get("note") else "") + "</li>")
    f = doc.get("fiction_only_mockumentary", {})
    fiction = "<section id='fiction'><h2>" + esc(f.get("title")) + "</h2><p class='warning'><strong>" + esc(f.get("label")) + "</strong></p><p>" + esc(f.get("premise")) + "</p><ol>" + "".join("<li>" + esc(x) + "</li>" for x in f.get("escalation", [])) + "</ol><p>" + esc(f.get("guardrail")) + "</p></section>"
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow"><title>Title Theory — The Paper Siege · Cedwyn</title>
<meta name="description" content="A falsifiable, parcel-by-parcel model of the Cedwyn / Tŷ Mawr title and possession history.">
<style>
:root{color-scheme:light;--bg:#f7f7f5;--paper:#fff;--ink:#202124;--muted:#5d6269;--line:#c9cdd1;--link:#0645ad}
html[data-ghf-mode="night"]{color-scheme:dark;--bg:#11151a;--paper:#181e25;--ink:#edf0f2;--muted:#b4bdc6;--line:#39434e;--link:#9bc9ff}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.65 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1000px;margin:auto;background:var(--paper);padding:clamp(18px,4vw,44px);box-sizing:border-box}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;font-weight:normal;line-height:1.25}
h1{font-size:clamp(2rem,5vw,3rem);margin:.3em 0}h2{font-size:1.65rem;border-bottom:1px solid var(--line);padding-bottom:.25em;margin-top:2em}
h3{font-size:1.25rem;margin:.3em 0 .6em}h4{font-size:1rem;margin:1.1em 0 .2em}
p,li{max-width:90ch}a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
.lede{font-size:1.08rem;max-width:78ch}.meta{font-size:.82rem;color:var(--muted);letter-spacing:.02em}
.note{border-left:3px solid var(--line);padding:.5rem 1rem;margin:1rem 0}
.warning{border-left:4px solid #b36b37;padding:.6rem 1rem;background:color-mix(in srgb,#b36b37 8%,var(--paper))}
.hyp,.stage,.sim{border-top:1px solid var(--line);padding:1rem 0;margin:0}
table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{padding:.45rem .6rem;border:1px solid var(--line);text-align:left;vertical-align:top}
.small{color:var(--muted);font-size:.9rem}.nav{display:flex;gap:1rem;flex-wrap:wrap;font-size:.9rem;margin-bottom:1.5rem}
</style></head><body><main>
<nav class="nav">""" + link("/wiki/", "Legal Wiki") + link("/research/", "Research Library") + link("/title-chain/", "Title chain") + link("/wiki/observations/", "Level 2 observations") + """</nav>
<p class="meta">""" + esc(doc.get("model_id")) + " · Version " + esc(doc.get("version")) + " · Updated " + esc(doc.get("updated_at")) + """</p>
<h1>""" + esc(doc.get("title")) + """</h1>
<p class="lede">""" + esc(doc.get("summary")) + """</p>
<p><strong>Status:</strong> """ + esc(doc.get("status")) + """</p>
<div class="note"><strong>How to read this:</strong> the model starts with a leading hypothesis so it can be tested. It does not treat a hypothesis as a fact. The court outcome, source gaps, alternative explanations and disconfirming tests remain visible alongside it.</div>
<h2>Scope and essential corrections</h2><p>""" + esc(doc.get("scope", {}).get("1841_correction")) + """</p>
<p>""" + esc(doc.get("scope", {}).get("williams_36_plot_claim")) + """</p>
<p>""" + esc(doc.get("scope", {}).get("distinction")) + """</p>
<table><tbody><tr><th>1939 agreement</th><td>""" + esc(doc.get("scope", {}).get("1939_parcel_b")) + """</td></tr>
<tr><th>Parcel A</th><td>""" + esc(doc.get("scope", {}).get("parcel_a")) + """</td></tr>
<tr><th>Parcel C</th><td>""" + esc(doc.get("scope", {}).get("parcel_c")) + """</td></tr></tbody></table>
<h2 id="if-true">If the leading hypothesis were true, it would explain…</h2><ol>""" + "".join("<li>" + esc(x) + "</li>" for x in doc.get("executive_if_true", [])) + """</ol>
<h2>Mechanism, stage by stage</h2><p>Each stage states the proposition, what it would explain if true, the alternative and the artifacts to test. Dates do not establish motive.</p>
""" + "".join(stages) + """
<h2>People and chronology: unresolved dates</h2><table><tbody><tr><th>Person</th><th>Date or conflict</th><th>Current status</th></tr>""" + "".join(chronology) + """</tbody></table>
<h2>Ranked hypothesis register</h2><p>The ranking is an order for testing and explanatory fit, not a probability estimate or a finding of criminal conduct. H2 records the operative court outcome; H5–H7 remain lower-confidence or fiction-only branches.</p>
""" + "".join(hypotheses) + """
<h2>Causal graph</h2><p>Nodes are dated stages or record states; edges are labelled as chronological, documented, unresolved or hypothetical.</p><h3>Nodes</h3><table><tbody>""" + "".join(graph_nodes) + """</tbody></table><h3>Edges</h3><table><tbody>""" + "".join(graph_edges) + """</tbody></table>
<h2>Simulation programme</h2><p>The purpose is to reverse-engineer the documents and parcel geometry, not to generate conclusions from dates alone.</p>
""" + "".join(sims) + """
<h2>Priority records</h2><ol>""" + "".join("<li>" + esc(x.get("item")) + "</li>" for x in doc.get("priorities", [])) + """</ol>
<h2>Underlying artifact register</h2><ul>""" + "".join(refs) + """</ul>
""" + fiction + """
<h2>Legal and evidential cautions</h2><ul>""" + "".join("<li>" + esc(x) + "</li>" for x in doc.get("legal_cautions", [])) + """</ul>
<p class="small">Machine-readable source model: """ + link("/wiki/title-theory/model.json", "title-theory/model.json") + """ · Generated from the canonical source file data/title-theory.json and incorporated into the central Cedwyn catalogue database at build time.</p>
</main></body></html>"""

def run(dist):
    dist = pathlib.Path(dist)
    source = ROOT / "data" / "title-theory.json"
    if not source.exists():
        raise FileNotFoundError(source)
    doc = json.loads(source.read_text(encoding="utf-8"))
    out = dist / "wiki" / "title-theory"
    out.mkdir(parents=True, exist_ok=True)
    (out / "model.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "index.html").write_text(page(doc), encoding="utf-8")
    old = dist / "research" / "working-theory-fraud-concealment-and-limitation" / "index.html"
    if old.exists():
        html_text = old.read_text(encoding="utf-8", errors="replace")
        if "data-title-theory-canonical" not in html_text:
            pointer = '<section data-title-theory-canonical><h2>Canonical Title Theory model</h2><p>The evidence-led, parcel-by-parcel working model is maintained centrally, with a machine-readable version for simulations. <a href="/wiki/title-theory/">Open Title Theory</a> · <a href="/wiki/title-theory/model.json">Open model data</a>.</p></section>'
            at = html_text.lower().find("</h1>")
            if at >= 0:
                at += len("</h1>")
                html_text = html_text[:at] + pointer + html_text[at:]
            old.write_text(html_text, encoding="utf-8")
    print("title theory: generated canonical page and model JSON")

if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "dist")
