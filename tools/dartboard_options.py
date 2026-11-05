#!/usr/bin/env python3
"""Build a searchable, cross-institution status map for the Dartboard route inventory.

The source of truth is src/data/ramps.json on the mirrored dartboard branch.
This creates a separate static view so it remains available within Cedwyn even
when the interactive Worker cannot be crawled. It never changes the source app.
"""
from __future__ import annotations

import html
import json
import os
import pathlib
import re
import subprocess
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]

# State names are deliberately descriptive. "Open" means listed but not yet used;
# it does not mean that every listed route is appropriate for every matter.
STATE_ORDER = ("overdue", "pending", "open", "queued", "done", "na")
STATE_LABELS = {
    "overdue": "Overdue",
    "pending": "Waiting / pending",
    "open": "Available / not used",
    "queued": "Queued, not sent",
    "done": "Used / completed",
    "na": "Not used / N/A",
}
STATE_LONG = {
    "overdue": "A missed deadline is recorded",
    "pending": "Awaiting a reply or outcome",
    "open": "Listed as an available route not yet used",
    "queued": "Drafted or queued, not sent",
    "done": "Marked as completed in the route register",
    "na": "The source combines unavailable, inapplicable, or intentionally unpursued routes",
}
STATE_COLORS = {
    "overdue": "#f06a6a",
    "pending": "#e9b44c",
    "open": "#7198f0",
    "queued": "#b79bf3",
    "done": "#4fc58a",
    "na": "#8791a4",
}
PHASE_LABELS = {
    "enquiry": "Enquiry / records",
    "register": "Register / inspection",
    "foi": "FOI / EIR",
    "eir": "EIR",
    "sar": "Subject access",
    "review": "Review",
    "complaint": "Complaint",
    "ico": "Information Commissioner",
    "icr": "Independent reviewer",
    "psow": "Public Services Ombudsman for Wales",
    "phso": "Parliamentary Ombudsman",
    "tribunal": "Tribunal",
    "court": "Court",
    "disclosure": "Court disclosure",
    "preaction": "Pre-action",
    "democratic": "Democratic / representative",
    "petition": "Petition",
    "audit": "Audit",
    "regulator": "Regulator",
}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def load_routes() -> dict:
    mirror = pathlib.Path(os.environ.get("MIRROR", "mirror.git"))
    if not mirror.is_absolute():
        mirror = ROOT / mirror
    proc = subprocess.run(
        ["git", "--git-dir", str(mirror), "show",
         "refs/heads/dartboard:src/data/ramps.json"],
        cwd=ROOT, capture_output=True, text=True, timeout=45,
    )
    if proc.returncode:
        raise RuntimeError("Could not read src/data/ramps.json from the dartboard branch")
    data = json.loads(proc.stdout)
    if not isinstance(data.get("institutions"), list) or not data["institutions"]:
        raise ValueError("The route inventory has no institutions")
    return data


def route_counts(rungs: list[dict]) -> dict[str, int]:
    result = {state: 0 for state in STATE_ORDER}
    for rung in rungs:
        state = str(rung.get("st") or "na")
        result[state] = result.get(state, 0) + 1
    return result


def route_url(url: object) -> str:
    value = str(url or "").strip()
    if not value:
        return ""
    # Internal references stay internal. Outside references open the one-page
    # Cedwyn archive viewer rather than linking directly to another host.
    if value.startswith("/") and not value.startswith("//"):
        return value
    return "/wayback/go/?u=" + urllib.parse.quote(value, safe="")


def link_html(label: str, url: object) -> str:
    href = route_url(url)
    if not href:
        return ""
    return '<a class="source-link" href="' + esc(href) + '">' + esc(label) + '</a>'


def is_paid(cost: object) -> bool:
    text = str(cost or "")
    return bool(re.search(r"\bPAID\b|costs risk|fee order", text, re.I))


def render_step(rung: dict) -> str:
    state = str(rung.get("st") or "na")
    if state not in STATE_LABELS:
        state = "na"
    cost = str(rung.get("cost") or "Cost not stated in this entry")
    timing = str(rung.get("time") or "Time limit not stated in this entry")
    phase = PHASE_LABELS.get(str(rung.get("ph") or "").lower(),
                              str(rung.get("ph") or "Route").replace("-", " ").title())
    searchable = " ".join(str(rung.get(key) or "") for key in
                          ("t", "s", "w", "ph", "cost", "time", "law", "pol",
                           "did", "next", "url", "polurl"))
    parts = [
        '<article class="route-step" data-state="' + esc(state) + '" data-cost="' +
        ("paid" if is_paid(cost) else "other") + '" data-search="' + esc(searchable.lower()) + '">',
        '<div class="step-heading"><span class="state-chip state-' + esc(state) + '">' +
        esc(STATE_LABELS[state]) + '</span><h3>' + esc(rung.get("t") or rung.get("s") or "Route step") + '</h3></div>',
        '<div class="step-meta"><span>' + esc(phase) + '</span><span class="cost' +
        (' cost-paid' if is_paid(cost) else '') + '">' + esc(cost) + '</span><span>' + esc(timing) + '</span></div>',
    ]
    explanation = rung.get("w") or rung.get("s")
    if explanation:
        parts.append('<p>' + esc(explanation) + '</p>')
    if rung.get("did"):
        parts.append('<p class="recorded"><strong>Recorded position:</strong> ' + esc(rung["did"]) + '</p>')
    if rung.get("next"):
        parts.append('<p class="recorded"><strong>Next note in the register:</strong> ' + esc(rung["next"]) + '</p>')
    if rung.get("law"):
        parts.append('<p class="basis"><strong>Legal basis / rule:</strong> ' + esc(rung["law"]) + '</p>')
    sources = []
    if rung.get("url"):
        sources.append(link_html("Source page", rung["url"]))
    if rung.get("polurl"):
        sources.append(link_html(rung.get("pol") or "Policy page", rung["polurl"]))
    for entry in rung.get("ev") or []:
        if isinstance(entry, dict) and (entry.get("url") or entry.get("href")):
            label = entry.get("id") or entry.get("ref") or entry.get("title") or "Related record"
            sources.append(link_html(str(label), entry.get("url") or entry.get("href")))
    sources = [s for s in sources if s]
    if sources:
        parts.append('<div class="source-links">' + " <span aria-hidden=\"true\">·</span> ".join(sources) + '</div>')
    parts.append('</article>')
    return "".join(parts)


def render_institution(inst: dict) -> str:
    name = str(inst.get("name") or "Unnamed institution")
    kind = str(inst.get("kind") or "")
    rungs = inst.get("rungs") or []
    counts = route_counts(rungs)
    total = len(rungs) or 1
    segments = []
    for state in STATE_ORDER:
        count = counts.get(state, 0)
        if count:
            percent = count * 100.0 / total
            segments.append(
                '<span class="bar-segment" style="width:' + format(percent, ".4f") +
                '%;background:' + STATE_COLORS[state] + '" title="' + esc(
                    str(count) + " · " + STATE_LABELS[state]) + '"></span>'
            )
    summary = " · ".join(
        str(counts.get(s, 0)) + " " + STATE_LABELS[s].lower()
        for s in ("overdue", "pending", "open", "queued", "done", "na")
        if counts.get(s, 0)
    )
    needle = " ".join([name, kind] + [
        " ".join(str(r.get(k) or "") for k in
                 ("t", "s", "w", "ph", "cost", "time", "law", "pol", "did", "next"))
        for r in rungs
    ]).lower()
    # Priority data is used only to make the first view useful: missed deadlines
    # and waiting items sort first. It is not a ranking of merits.
    return (
        '<details class="institution" data-name="' + esc(name.lower()) +
        '" data-kind="' + esc(kind.lower()) + '" data-search="' + esc(needle) +
        '" data-overdue="' + str(counts.get("overdue", 0)) +
        '" data-pending="' + str(counts.get("pending", 0)) +
        '" data-open-count="' + str(counts.get("open", 0)) +
        '" data-queued="' + str(counts.get("queued", 0)) +
        '" data-done="' + str(counts.get("done", 0)) +
        '" data-na="' + str(counts.get("na", 0)) + '">'
        '<summary><div class="institution-head"><span class="institution-name">' + esc(name) +
        '</span><span class="step-count">' + str(len(rungs)) + ' steps</span></div>'
        + ('<p class="institution-kind">' + esc(kind) + '</p>' if kind else '')
        + '<div class="stacked-bar" role="img" aria-label="' + esc(name + ": " + summary) + '">' +
        "".join(segments) + '</div><p class="institution-stats">' + esc(summary) + '</p></summary>'
        '<div class="route-steps">' + "".join(render_step(r) for r in rungs) + '</div></details>'
    )


def render_page(data: dict) -> str:
    institutions = data["institutions"]
    dated = str(data.get("asOf") or "date not stated")
    counts = route_counts([r for i in institutions for r in (i.get("rungs") or [])])
    total_steps = sum(len(i.get("rungs") or []) for i in institutions)
    def prio(inst: dict) -> tuple:
        c = route_counts(inst.get("rungs") or [])
        return (-c.get("overdue", 0), -c.get("pending", 0), -c.get("open", 0),
                -c.get("queued", 0), -c.get("done", 0), str(inst.get("name") or "").lower())
    institutions = sorted(institutions, key=prio)
    metric_html = []
    for state in STATE_ORDER:
        metric_html.append(
            '<button class="metric state-' + state + '" type="button" data-set-state="' + state +
            '" aria-pressed="false" title="' + esc(STATE_LONG[state]) + '">'
            '<span class="metric-value">' + str(counts.get(state, 0)) + '</span>'
            '<span class="metric-label">' + esc(STATE_LABELS[state]) + '</span>'
            '<span class="metric-detail">' + esc(STATE_LONG[state]) + '</span></button>'
        )
    institution_html = "".join(render_institution(i) for i in institutions)
    state_options = '<option value="all">All statuses</option>' + "".join(
        '<option value="' + s + '">' + esc(STATE_LABELS[s]) + '</option>' for s in STATE_ORDER
    )
    # The renderer emits one copy of the route data; browser filtering is applied
    # to these static rows, so no second data source can drift out of sync.
    page = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#101219"><meta name="description" content="Searchable status map of the route options recorded for each institution in the Disclosure Dartboard.">
<title>All route options · Disclosure Dartboard</title>
<style>
:root{color-scheme:dark;--bg:#101219;--panel:#191d27;--panel2:#202633;--line:#343c4b;--ink:#eef1f6;--muted:#aeb7c7;--brass:#d2b26b;--done:#4fc58a;--pending:#e9b44c;--open:#7198f0;--queued:#b79bf3;--overdue:#f06a6a;--na:#8791a4}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#e3c781;text-underline-offset:3px}a:hover{color:#fff}button,input,select{font:inherit}button,select,input{color:var(--ink);background:#171b24;border:1px solid #485164;border-radius:10px;min-height:42px;padding:8px 11px}button{cursor:pointer}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,summary:focus-visible{outline:3px solid var(--brass);outline-offset:2px}
.wrap{width:min(1220px,100%);margin:0 auto;padding:24px 16px 80px}.topline{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:24px}.eyebrow{font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:var(--brass);font-weight:750;margin:0 0 5px}.back{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:999px;padding:8px 12px;text-decoration:none;color:var(--ink);white-space:nowrap}
h1{font-size:clamp(1.9rem,4vw,3.15rem);line-height:1.08;letter-spacing:-.035em;margin:0 0 12px}h2{font-size:1.35rem;line-height:1.2;margin:0 0 8px}h3{font-size:1rem;line-height:1.35;margin:0;font-weight:700}.lede{color:#c5ccda;max-width:880px;font-size:1.03rem;margin:0 0 18px}.snapshot{display:inline-flex;align-items:center;gap:7px;flex-wrap:wrap;color:var(--muted);font-size:.9rem;margin:0 0 23px}.snapshot strong{color:var(--ink)}
.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:18px 0 22px}.metric{display:flex;flex-direction:column;align-items:flex-start;gap:3px;text-align:left;min-width:0;border:1px solid var(--line);background:var(--panel);padding:12px;border-radius:13px;min-height:120px}.metric[aria-pressed=true]{border-color:var(--brass);box-shadow:inset 0 0 0 1px var(--brass);background:#28271f}.metric-value{font-size:1.8rem;line-height:1.1;font-weight:800;font-variant-numeric:tabular-nums}.metric-label{font-weight:750;font-size:.94rem}.metric-detail{color:var(--muted);font-size:.78rem;line-height:1.3}.state-overdue .metric-value{color:var(--overdue)}.state-pending .metric-value{color:var(--pending)}.state-open .metric-value{color:var(--open)}.state-queued .metric-value{color:var(--queued)}.state-done .metric-value{color:var(--done)}.state-na .metric-value{color:var(--na)}
.explainer{border:1px solid #554b32;background:#211f1a;border-radius:12px;padding:13px 15px;color:#d8d1c0;margin:0 0 24px}.explainer p{margin:0 0 6px}.explainer p:last-child{margin-bottom:0}.explainer strong{color:#fff1c7}.toolbar{display:grid;grid-template-columns:minmax(200px,2fr) minmax(150px,1fr) minmax(140px,1fr) minmax(140px,1fr) auto;gap:8px;align-items:center;margin:16px 0 10px}.toolbar input{width:100%;min-width:0}.resultsline{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:.87rem;margin:8px 0 13px}.map-legend{display:flex;gap:7px 13px;align-items:center;flex-wrap:wrap;margin:16px 0;color:var(--muted);font-size:.8rem}.legend-item{display:inline-flex;gap:6px;align-items:center}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;flex:0 0 9px}.dot-overdue{background:var(--overdue)}.dot-pending{background:var(--pending)}.dot-open{background:var(--open)}.dot-queued{background:var(--queued)}.dot-done{background:var(--done)}.dot-na{background:var(--na)}
.institution-list{display:flex;flex-direction:column;gap:9px}.institution{border:1px solid var(--line);border-radius:13px;overflow:hidden;background:var(--panel)}.institution[hidden]{display:none!important}.institution>summary{list-style:none;cursor:pointer;padding:14px 15px}.institution>summary::-webkit-details-marker{display:none}.institution>summary:after{content:"＋";float:right;color:var(--brass);font-size:1.1rem;margin:-22px 2px 0 8px}.institution[open]>summary:after{content:"−"}.institution-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding-right:26px}.institution-name{font-size:1.02rem;font-weight:780}.step-count{color:var(--muted);font-size:.78rem;white-space:nowrap;border:1px solid var(--line);padding:3px 8px;border-radius:999px}.institution-kind{color:var(--muted);margin:3px 0 9px;font-size:.81rem}.stacked-bar{height:8px;display:flex;gap:2px;overflow:hidden;border-radius:999px;background:#313846}.bar-segment{display:block;height:100%;min-width:2px}.institution-stats{margin:7px 0 0;color:#b7c0cf;font-size:.78rem}.route-steps{border-top:1px solid var(--line);padding:2px 12px 12px}.route-step{margin:10px 0 0;padding:12px;border:1px solid #384151;border-radius:10px;background:var(--panel2)}.route-step[hidden]{display:none!important}.step-heading{display:flex;align-items:flex-start;gap:9px}.step-heading h3{flex:1;overflow-wrap:anywhere}.state-chip{display:inline-block;flex:0 0 auto;padding:3px 7px;border-radius:999px;font-size:.72rem;line-height:1.35;font-weight:750;background:#323947;color:#f2f4f8}.state-overdue{border-color:var(--overdue)}.state-chip.state-overdue{background:#4d282c;color:#ffb0b0}.state-chip.state-pending{background:#493c21;color:#ffe0a0}.state-chip.state-open{background:#26365b;color:#c0d2ff}.state-chip.state-queued{background:#3b3152;color:#ddceff}.state-chip.state-done{background:#203e32;color:#a3f0c4}.state-chip.state-na{background:#343946;color:#d1d6df}
.step-meta{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;color:var(--muted);font-size:.77rem}.step-meta span{padding:3px 7px;border:1px solid #424b5b;border-radius:6px}.step-meta .cost-paid{color:#ffd19b;border-color:#765637}.route-step p{margin:8px 0;color:#d1d7e2;overflow-wrap:anywhere}.route-step p strong{color:#f5e9cb}.route-step .recorded{color:#c2ccdc}.route-step .basis{font-size:.87rem;color:#e0d4b7}.source-links{display:flex;gap:5px 9px;flex-wrap:wrap;margin-top:10px;font-size:.82rem}.empty{display:none;border:1px dashed #596174;border-radius:12px;padding:22px;text-align:center;color:var(--muted)}.empty.visible{display:block}.show-all{display:block;margin:16px auto 0;min-width:230px}.method{margin-top:28px;padding-top:20px;border-top:1px solid var(--line)}.method p{color:var(--muted);max-width:920px}.method details{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin-top:10px}.method summary{cursor:pointer;font-weight:700}.change-log{font-size:.81rem!important;color:var(--muted)!important}.small{font-size:.8rem;color:var(--muted)}
@media(min-width:720px){.metrics{grid-template-columns:repeat(6,minmax(0,1fr))}.metric{min-height:137px}.step-heading h3{font-size:1.02rem}.route-steps{padding:3px 16px 16px}.route-step{padding:14px 16px}}
@media(max-width:760px){.toolbar{grid-template-columns:1fr 1fr}.toolbar input{grid-column:1/-1}.toolbar #route-clear{grid-column:1/-1}.institution-head{padding-right:23px}}
@media(max-width:420px){.wrap{padding:17px 11px 65px}.metrics{gap:7px}.metric{padding:10px;min-height:112px}.metric-value{font-size:1.55rem}.metric-label{font-size:.84rem}.metric-detail{font-size:.73rem}.step-heading{flex-direction:column;gap:6px}.step-meta{font-size:.73rem}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important;animation:none!important}}
</style></head><body><main class="wrap">
<div class="topline"><div><p class="eyebrow">Disclosure Dartboard · route inventory</p><p class="small" style="margin:0">Cross-institution view</p></div><a class="back" href="/dartboard/" aria-label="Return to the Disclosure Dartboard">← Back to Dartboard</a></div>
<h1>All route options, side by side</h1>
<p class="lede"><a href="/research/read-the-docs/#analysis-pages">What this page is about → Read the Docs</a></p>
<p class="snapshot"><strong>%%INST_COUNT%% roadmaps · %%TOTAL%% route steps</strong><span>·</span><span>Status snapshot: <strong>%%DATE%%</strong></span></p>
<section class="metrics" aria-label="Route status counts">%%METRICS%%</section>
<div class="explainer"><p><strong>How to read this:</strong> each count represents a recorded route step, not a request, a court case, or a percentage chance of success. Each bar shows the mix of statuses within one institution’s own route list.</p><p>These routes are not one compulsory ladder. Some run in parallel; a status of “available” means listed but not marked as used. “Not used / N/A” combines routes the source labels unavailable, inapplicable, or intentionally unpursued. Check time limits and current rules before relying on an entry.</p></div>
<div class="toolbar" aria-label="Filter route inventory">
<input id="route-search" type="search" placeholder="Search institutions, routes, law or notes" aria-label="Search all route options">
<select id="route-state" aria-label="Filter by status">%%STATE_OPTIONS%%</select>
<select id="route-cost" aria-label="Filter by cost"><option value="any">Any cost status</option><option value="paid">Marked paid / cost risk</option></select>
<select id="route-sort" aria-label="Sort route maps"><option value="priority">Overdue / waiting first</option><option value="remaining">Most untried / queued</option><option value="name">Institution A–Z</option></select>
<button id="route-clear" type="button">Clear filters</button>
</div>
<div class="map-legend" aria-label="Status key">
<span class="legend-item"><i class="dot dot-overdue"></i>Overdue</span>
<span class="legend-item"><i class="dot dot-pending"></i>Waiting / pending</span>
<span class="legend-item"><i class="dot dot-open"></i>Available / not used</span>
<span class="legend-item"><i class="dot dot-queued"></i>Queued, not sent</span>
<span class="legend-item"><i class="dot dot-done"></i>Used / completed</span>
<span class="legend-item"><i class="dot dot-na"></i>Not used / N/A</span>
</div>
<div class="resultsline"><span id="route-results" aria-live="polite">Showing the first route maps</span><span>Open a row for all its recorded steps.</span></div>
<section class="institution-list" id="route-institutions" aria-label="Institution route maps">%%INSTITUTIONS%%</section>
<div class="empty" id="route-empty">No route maps match those filters. Clear the filters or try a broader search.</div>
<button class="show-all" id="route-show-all" type="button">Show all institutions</button>
<section class="method" aria-label="Source and change log">
<h2>Source, limits and change log</h2>
<p>Source: the Dartboard route register (<code>src/data/ramps.json</code> on the <code>dartboard</code> branch), with each institution’s route status and notes reproduced as recorded in that file.</p>
<p>The list is only as current as its dated source. It is a way to compare the recorded position, not legal advice, a finding that a remedy is available, or a recommendation to take every route. Where the source flags a payment or costs risk, that wording is shown rather than turned into an instruction.</p>
<details><summary>Change log</summary><p class="change-log">v1.0.0 · 27 October 2026 · Added a searchable, cross-institution route-status map and a Dartboard entry point. Source status snapshot: 20 October 2026. Signed: ChatGPT.<br>v1.0.1 · 27 October 2026 · Added the required Read-the-Docs anchor and standard AI-agent footer. Signed: ChatGPT.</p></details>
</section></main>
<script>
(function(){
  "use strict";
  var list=document.getElementById("route-institutions");
  var cards=Array.prototype.slice.call(list.querySelectorAll(".institution"));
  var search=document.getElementById("route-search");
  var stateSelect=document.getElementById("route-state");
  var costSelect=document.getElementById("route-cost");
  var sortSelect=document.getElementById("route-sort");
  var results=document.getElementById("route-results");
  var empty=document.getElementById("route-empty");
  var showAll=document.getElementById("route-show-all");
  var clear=document.getElementById("route-clear");
  var expanded=false;
  function currentState(){return stateSelect.value||"all";}
  function cmpPriority(a,b){
    var keys=["overdue","pending","open-count","queued","done"];
    for(var i=0;i<keys.length;i++){
      var key=keys[i],av=Number(a.dataset[key]||0),bv=Number(b.dataset[key]||0);
      if(av!==bv)return bv-av;
    }
    return a.dataset.name.localeCompare(b.dataset.name);
  }
  function applyFilters(){
    var q=(search.value||"").trim().toLowerCase();
    var wantedState=currentState(), wantedCost=costSelect.value||"any";
    var matches=[];
    cards.forEach(function(card){
      var nameMatch=(card.dataset.name+" "+card.dataset.kind).indexOf(q)>=0;
      var visibleSteps=0;
      Array.prototype.forEach.call(card.querySelectorAll(".route-step"),function(step){
        var statusOK=wantedState==="all"||step.dataset.state===wantedState;
        var costOK=wantedCost==="any"||step.dataset.cost==="paid";
        var textOK=!q||nameMatch||(step.dataset.search||"").indexOf(q)>=0;
        step.hidden=!(statusOK&&costOK&&textOK);
        if(!step.hidden)visibleSteps++;
      });
      card.hidden=visibleSteps===0;
      if(!card.hidden)matches.push(card);
    });
    var mode=sortSelect.value||"priority";
    matches.sort(function(a,b){
      if(mode==="name")return a.dataset.name.localeCompare(b.dataset.name);
      if(mode==="remaining"){
        var ar=Number(a.dataset.openCount||0)+Number(a.dataset.queued||0)+Number(a.dataset.pending||0);
        var br=Number(b.dataset.openCount||0)+Number(b.dataset.queued||0)+Number(b.dataset.pending||0);
        if(ar!==br)return br-ar;
      }
      return cmpPriority(a,b);
    });
    matches.forEach(function(card){list.appendChild(card);});
    var forced=(q!==""||wantedState!=="all"||wantedCost!=="any");
    var limit=(forced||expanded)?matches.length:Math.min(12,matches.length);
    matches.forEach(function(card,index){
      card.style.display=index<limit?"":"none";
    });
    cards.filter(function(card){return card.hidden;}).forEach(function(card){card.style.display="";});
    results.textContent="Showing "+limit+" of "+matches.length+" matching institution route maps"+(forced?" · filters active":"");
    empty.classList.toggle("visible",matches.length===0);
    showAll.hidden=forced||matches.length<=12;
    showAll.textContent=expanded?"Show fewer institutions":"Show all "+matches.length+" institutions";
    Array.prototype.forEach.call(document.querySelectorAll("[data-set-state]"),function(button){
      button.setAttribute("aria-pressed",String(button.dataset.setState===wantedState));
    });
  }
  Array.prototype.forEach.call(document.querySelectorAll("[data-set-state]"),function(button){
    button.addEventListener("click",function(){
      stateSelect.value=button.dataset.setState===currentState()?"all":button.dataset.setState;
      expanded=false;applyFilters();
    });
  });
  search.addEventListener("input",applyFilters);
  stateSelect.addEventListener("change",function(){expanded=false;applyFilters();});
  costSelect.addEventListener("change",function(){expanded=false;applyFilters();});
  sortSelect.addEventListener("change",applyFilters);
  showAll.addEventListener("click",function(){expanded=!expanded;applyFilters();});
  clear.addEventListener("click",function(){
    search.value="";stateSelect.value="all";costSelect.value="any";sortSelect.value="priority";expanded=false;applyFilters();search.focus();
  });
  applyFilters();
})();
</script></body></html>
"""
    return (page.replace("%%DATE%%", esc(dated))
            .replace("%%INST_COUNT%%", str(len(institutions)))
            .replace("%%TOTAL%%", str(total_steps))
            .replace("%%METRICS%%", "".join(metric_html))
            .replace("%%STATE_OPTIONS%%", state_options)
            .replace("%%INSTITUTIONS%%", institution_html))


def inject_launcher(index_file: pathlib.Path, institution_count: int, step_count: int) -> bool:
    if not index_file.exists():
        return False
    source = index_file.read_text(encoding="utf-8", errors="replace")
    if 'id="cedwyn-route-launcher"' in source:
        return False
    launcher = (
        '<style id="cedwyn-route-launcher-css">'
        '#cedwyn-route-launcher{position:fixed;right:max(12px,env(safe-area-inset-right));'
        'bottom:max(12px,env(safe-area-inset-bottom));z-index:2147483000;display:flex;flex-direction:column;'
        'gap:2px;max-width:calc(100vw - 24px);padding:10px 15px;border:1px solid #d2b26b;border-radius:13px;'
        'background:#191d27;color:#f4f0e7;text-decoration:none;box-shadow:0 5px 24px #0008;'
        'font:700 14px/1.25 system-ui,-apple-system,"Segoe UI",sans-serif}'
        '#cedwyn-route-launcher small{color:#d8c99d;font-size:11px;font-weight:500}'
        '#cedwyn-route-launcher:hover{background:#28271f;color:#fff}'
        '@media(max-width:420px){#cedwyn-route-launcher{right:10px;bottom:max(10px,env(safe-area-inset-bottom));'
        'padding:9px 12px;font-size:13px}}'
        '</style><a id="cedwyn-route-launcher" href="/dartboard/options/" '
        'aria-label="Open all route options across ' + str(institution_count) + ' institution roadmaps">'
        '<span>All route options ↗</span><small>' + str(institution_count) + ' roadmaps · ' +
        str(step_count) + ' steps · dated status</small></a>'
    )
    source, changed = re.subn(r"</body\s*>", launcher + "</body>", source, count=1, flags=re.I)
    if not changed:
        source += launcher
    # The legacy tile counts request items. Naming it that way avoids conflating
    # request status with the separate route-step inventory created above.
    source = re.sub(r'(<span[^>]*>)Options used(</span>)',
                    r'\1Options by institution\2', source, count=1, flags=re.I)
    source = re.sub(r'(\d+)\s+items open', r'\1 tracked items open', source, count=1, flags=re.I)
    index_file.write_text(source, encoding="utf-8")
    return True


def run(dist: pathlib.Path | str) -> bool:
    dist = pathlib.Path(dist)
    try:
        data = load_routes()
        institutions = data["institutions"]
        step_count = sum(len(i.get("rungs") or []) for i in institutions)
        target = dist / "dartboard" / "options" / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render_page(data), encoding="utf-8")
        # Nested /dartboard/options/ is outside agent_footer.run()'s immediate-child glob.
        # Inject the shared anti-boilerplate instructions and page-local version log explicitly.
        import agent_footer
        agent_footer.inject(target, False)
        launcher_added = inject_launcher(dist / "dartboard" / "index.html", len(institutions), step_count)
        print("dartboard options: %s roadmaps, %s route steps, snapshot %s; launcher %s" % (
            len(institutions), step_count, data.get("asOf") or "date not stated",
            "added" if launcher_added else "not added (page unavailable or already linked)",
        ))
        return True
    except Exception as exc:
        # This view must never prevent the rest of the estate from building.
        print("dartboard options: skipped; source unavailable or invalid (%s)" % type(exc).__name__)
        return False


if __name__ == "__main__":
    import sys
    run(sys.argv[1] if len(sys.argv) > 1 else "dist")
