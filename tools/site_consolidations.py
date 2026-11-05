#!/usr/bin/env python3
"""Build consolidated visitor-facing areas while preserving legacy theme routes.

The area registry is deliberately separate from historical parcel identification:
serendipity_slot is an editorial index, never a claimed tithe plot number.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
AREA_DATA = ROOT / "data" / "site-areas.json"
EV_LINK = "/research/evidence/ev-0215-tithe-apportionment-john-williams-c1841/"

def esc(v):
    return html.escape(str(v or ""), quote=True)

def a(href, label, cls=""):
    return '<a' + (' class="' + esc(cls) + '"' if cls else '') + ' href="' + esc(href) + '">' + esc(label) + '</a>'

def shell(title, description, body):
    return '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow"><title>''' + esc(title) + ''' — Cedwyn</title>
<meta name="description" content="''' + esc(description) + '''">
<style>
:root{color-scheme:light;--wiki-bg:#f8f9fa;--wiki-paper:#fff;--wiki-text:#202122;--wiki-muted:#54595d;--wiki-border:#a2a9b1;--wiki-soft-border:#c8ccd1;--wiki-link:#0645ad}
html{background:var(--wiki-bg)}html[data-ghf-mode="night"]{--wiki-bg:#0f1115;--wiki-paper:#161a20;--wiki-text:#e8e8ee;--wiki-muted:#b6bdc8;--wiki-border:#4b5563;--wiki-soft-border:#303844;--wiki-link:#9cc8ff}body{margin:0;background:var(--wiki-bg);color:var(--wiki-text);font:14px/1.6 Arial,"Liberation Sans",sans-serif}
a{color:var(--wiki-link);text-decoration:none}a:hover{text-decoration:underline}
main{max-width:1320px;min-height:60vh;margin:0 auto;padding:1.5rem clamp(1rem,3vw,2.5rem) 3rem;background:var(--wiki-paper);border-left:1px solid var(--wiki-soft-border);border-right:1px solid var(--wiki-soft-border);box-sizing:border-box}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;font-weight:normal;line-height:1.3}h1{font-size:1.9rem;border-bottom:1px solid var(--wiki-border);padding-bottom:.3em}h2{font-size:1.3rem;margin:.4rem 0}
.lede{max-width:85ch;color:var(--wiki-muted)}.note{border-left:3px solid var(--wiki-border);padding:.35rem .8rem;margin:1rem 0;color:var(--wiki-muted)}
.nav{display:flex;flex-wrap:wrap;gap:.75rem;margin:1rem 0}.nav a{border:1px solid var(--wiki-soft-border);padding:.35rem .6rem}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:.75rem;margin:1rem 0}
.card{border:1px solid var(--wiki-soft-border);background:var(--wiki-paper);padding:.85rem;min-width:0}.meta{font-size:.82rem;color:var(--wiki-muted)}.card p{margin:.4rem 0;overflow-wrap:anywhere}
button{font:inherit;border:1px solid var(--wiki-border);padding:.45rem .7rem;background:var(--wiki-paper);color:inherit;cursor:pointer}button[aria-pressed="true"]{border-bottom:3px solid var(--wiki-link);font-weight:bold}
.tabs{display:flex;gap:.5rem;flex-wrap:wrap;margin:.8rem 0}
.frame{display:block;width:100%;height:min(76vh,900px);min-height:480px;border:1px solid var(--wiki-soft-border);background:var(--wiki-paper)}
code{overflow-wrap:anywhere}
</style>
</head><body><main>''' + body + '''</main></body></html>'''

def render_area_index(doc):
    cards = []
    for area in doc.get("areas", []):
        slot = int(area.get("serendipity_slot") or 0)
        source = ", ".join(area.get("source_themes", []))
        target = area.get("path", "/")
        status = area.get("parcel_mapping_status", "historic_plot_number_pending_verification")
        parcel = area.get("tithe_parcel_number")
        parcel_label = ("Tithe plot no. " + str(parcel)) if parcel else ("Historic plot number: not yet verified (editorial slot %02d)" % slot)
        cards.append(
            '<article class="card"><p class="meta">Editorial serendipity slot %02d · %s</p>' % (slot, esc(parcel_label)) +
            '<h2>' + a(target, area.get("title", area.get("id", "Page area"))) + '</h2>' +
            '<p>' + esc(area.get("description", "")) + '</p>' +
            '<p class="meta">Source themes: <code>' + esc(source) + '</code></p>' +
            '<p class="meta">Parcel link status: ' + esc(status.replace("_", " ")) + '</p></article>'
        )
    body = (
        '<nav class="nav">' + a("/parcels/", "The 36 parcels") + a(EV_LINK, "Read the tithe artifact") +
        a("/wiki/evidence/", "Level 1 · Evidence register") + a("/wiki/observations/", "Level 2 · Observations") + '</nav>' +
        '<h1>36 page areas · 36 parcel research prompts</h1>' +
        '<p class="lede">The website currently has 44 source themes. This index groups them into 36 visitor-facing areas, keeping legacy routes available so old links continue to work. Each slot is an editorial prompt for serendipitous browsing, not a historical plot number or a claim that the website area occupies that land.</p>' +
        '<div class="note"><strong>Parcel matching is not yet established.</strong> The c.1841 tithe apportionment identifies 36 plots occupied by John Williams, but the original schedule and map have not yet been checked row-by-row against the proposed website-area pairings. No slot below should be read as a verified tithe number. Start with ' +
        a(EV_LINK, "EV-0215, the tithe artifact") + ' and replace an editorial slot with an actual plot number only after checking the source image and area row.</div>' +
        '<div class="nav">' + a("/wiki/reference/", "Wiki references: names and dictionary") + a("/arcade/", "Arcade: gallery, games and 3D world") + '</div>' +
        '<section class="grid">' + ''.join(cards) + '</section>'
    )
    return shell("36 page areas", "A transparent index that groups 44 source themes into 36 visitor-facing areas and records parcel matching as pending source review.", body)

def render_tabs(title, intro, tabs):
    tab_html = ''.join('<button type="button" data-src="' + esc(src) + '" data-label="' + esc(label) + '" aria-pressed="' + ('true' if i == 0 else 'false') + '">' + esc(label) + '</button>' for i, (label, src) in enumerate(tabs))
    iframe = '<iframe class="frame" title="' + esc(title + " — " + tabs[0][0]) + '" src="' + esc(tabs[0][1]) + '" loading="lazy" referrerpolicy="same-origin"></iframe>'
    script = '''<script>
(function(){var root=document.querySelector('[data-tabs]');if(!root)return;var frame=root.querySelector('iframe');root.querySelectorAll('button[data-src]').forEach(function(b){b.addEventListener('click',function(){var src=b.getAttribute('data-src');if(frame.getAttribute('src')!==src)frame.setAttribute('src',src);root.querySelectorAll('button[data-src]').forEach(function(x){x.setAttribute('aria-pressed',String(x===b))});frame.title=''' + json.dumps(title) + '''+' — '+b.getAttribute('data-label');});});})();
</script>'''
    body = '<nav class="nav">' + a("/parcels/site-areas/", "36 page areas") + a("/wiki/evidence/", "Evidence register") + '</nav><h1>' + esc(title) + '</h1><p class="lede">' + esc(intro) + '</p><div data-tabs><div class="tabs" role="group" aria-label="' + esc(title + " views") + '">' + tab_html + '</div>' + iframe + '</div>' + script
    return shell(title, intro, body)

def insert_link(page_path, marker, label, href):
    if not page_path.exists():
        return False
    page = page_path.read_text(encoding="utf-8", errors="replace")
    if href in page:
        return False
    link = '<p class="cedwyn-area-shortcut">' + a(href, label) + '</p>'
    h1 = re.search(r'</h1\s*>', page, re.I)
    pos = h1.end() if h1 else (page.lower().find('</main>') if page.lower().find('</main>') >= 0 else page.lower().find('</body>'))
    if pos < 0:
        return False
    page = page[:pos] + '\n' + link + '\n' + page[pos:]
    page_path.write_text(page, encoding="utf-8")
    return True

def run(dist):
    dist = pathlib.Path(dist)
    doc = json.loads(AREA_DATA.read_text(encoding="utf-8"))
    areas = dist / "parcels" / "site-areas" / "index.html"
    areas.parent.mkdir(parents=True, exist_ok=True)
    areas.write_text(render_area_index(doc), encoding="utf-8")

    arcade = dist / "arcade" / "index.html"
    arcade.parent.mkdir(parents=True, exist_ok=True)
    arcade.write_text(render_tabs(
        "Arcade",
        "Three interactive experiences share one page area: digital artwork, cyber games and the 3D estate. Existing source routes remain available, and each experience loads only when selected.",
        [("NFT gallery / digital garden", "/nft-art/"), ("Cyber games", "/cyberspace/"), ("3D estate", "/terrain/")]
    ), encoding="utf-8")

    reference = dist / "wiki" / "reference" / "index.html"
    reference.parent.mkdir(parents=True, exist_ok=True)
    reference.write_text(render_tabs(
        "Wiki reference tools",
        "The Legal Wiki keeps the name index and dictionary as two views within the same page area. They remain separate sources and retain their own legacy routes.",
        [("Names and spellings", "/nomenclature/"), ("Dictionary / glossary", "/glossary/")]
    ), encoding="utf-8")

    injects = [
        (dist / "wiki" / "index.html", "Wiki reference tools", "/wiki/reference/"),
        (dist / "wiki" / "evidence" / "index.html", "Wiki reference tools", "/wiki/reference/"),
        (dist / "nft-art" / "index.html", "Open Arcade", "/arcade/"),
        (dist / "cyberspace" / "index.html", "Open Arcade", "/arcade/"),
        (dist / "terrain" / "index.html", "Open Arcade", "/arcade/"),
        (dist / "parcels" / "index.html", "Browse 36 site areas", "/parcels/site-areas/")
    ]
    changed = sum(1 for p, label, href in injects if insert_link(p, label, label, href))
    print("site areas: %d areas, %d injects; arcade and wiki reference tabs generated" % (len(doc.get("areas", [])), changed))

if __name__ == "__main__":
    import sys
    run(sys.argv[1] if len(sys.argv) > 1 else "dist")
