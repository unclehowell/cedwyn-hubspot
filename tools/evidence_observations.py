#!/usr/bin/env python3
"""Generate the Level 2 observation pages and mount the DB-backed evidence browser.

Artifact/observation content is sourced from data/*.json and the SQLite catalogue built
by tools/build_db.py. This script does not modify the original Wordpress evidence register.
"""
import html
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

def esc(value):
    return html.escape(str(value or ""), quote=True)

def link(path, label):
    if not path:
        return esc(label)
    return '<a href="' + esc(path) + '">' + esc(label) + '</a>'

def paragraphs(value):
    return ''.join('<p>' + esc(p.strip()) + '</p>' for p in str(value or '').split('\n\n') if p.strip())

def source_links(observation):
    out = []
    for ref in observation.get('refs', []):
        ev = ref.get('ev') or ''
        path = ref.get('path') or ''
        label = (ev + ' — ' if ev else '') + (ref.get('label') or ref.get('role') or path or 'Referenced record')
        out.append(
            '<li><div>' + link(path, label) + '</div>' +
            ('<p class="cw-observation-note">' + esc(ref.get('role', '')) + '</p>' if ref.get('role') else '') +
            ('<p>' + esc(ref.get('note', '')) + '</p>' if ref.get('note') else '') + '</li>'
        )
    return '<ul class="cw-observation-refs">' + ''.join(out) + '</ul>' if out else '<p>No artifact references recorded yet.</p>'

def head(title):
    return '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow">
<title>''' + esc(title) + ''' — Cedwyn</title>
<style>
:root{color-scheme:light;--wiki-bg:#f8f9fa;--wiki-paper:#fff;--wiki-text:#202122;--wiki-muted:#54595d;--wiki-border:#a2a9b1;--wiki-soft-border:#c8ccd1;--wiki-link:#0645ad}
html{background:var(--wiki-bg)}html[data-ghf-mode="night"]{--wiki-bg:#0f1115;--wiki-paper:#161a20;--wiki-text:#e8e8ee;--wiki-muted:#b6bdc8;--wiki-border:#4b5563;--wiki-soft-border:#303844;--wiki-link:#9cc8ff}body{margin:0;background:var(--wiki-bg);color:var(--wiki-text);font:14px/1.6 Arial,"Liberation Sans",sans-serif}
a{color:var(--wiki-link);text-decoration:none}a:hover{text-decoration:underline}
.cw-observation-main{max-width:1320px;min-height:60vh;margin:0 auto;padding:1.5rem clamp(1rem,3vw,2.5rem) 3rem;background:var(--wiki-paper);border-left:1px solid var(--wiki-soft-border);border-right:1px solid var(--wiki-soft-border);box-sizing:border-box}
.cw-observation-main h1,.cw-observation-main h2,.cw-observation-main h3{font-family:Georgia,"Times New Roman",serif;font-weight:normal;line-height:1.35}
.cw-observation-main h1{font-size:1.9rem;border-bottom:1px solid var(--wiki-border);padding-bottom:.25em}
.cw-observation-main h2{font-size:1.4rem;border-bottom:1px solid var(--wiki-soft-border);padding-bottom:.2em;margin-top:1.5em}
.cw-observation-main p,.cw-observation-main li{max-width:90ch;overflow-wrap:anywhere}
.cw-observation-main .cw-observation-meta{color:var(--wiki-muted);font-size:.85rem}
.cw-observation-main .cw-observation-note{color:var(--wiki-muted);font-size:.85rem}
.cw-observation-main .cw-observation-panel{border:1px solid var(--wiki-soft-border);padding:.8rem 1rem;margin:1rem 0;background:var(--wiki-paper)}
.cw-observation-main .cw-observation-limit{border-left:3px solid var(--wiki-border);padding:.4rem .8rem}
.cw-observation-main .cw-observation-nav{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}
.cw-observation-main .cw-observation-refs{padding-left:1.6rem}
.cw-observation-main .cw-observation-refs li{margin:.8rem 0;padding-bottom:.5rem;border-bottom:1px solid var(--wiki-soft-border)}
.cw-observation-main .cw-observation-questions li{margin:.4rem 0}
</style>
</head>
<body>'''

def observation_html(o):
    tests = o.get('test_questions', [])
    questions = '<ul class="cw-observation-questions">' + ''.join('<li>' + esc(q) + '</li>' for q in tests) + '</ul>' if tests else '<p>No test questions recorded yet.</p>'
    related = ''
    if o.get('related_page'):
        related = '<p>Existing analysis: ' + link(o['related_page'], 'Read the related page') + '</p>'
    return (head(o.get('title', 'Observation')) +
        '<main class="cw-observation-main"><nav class="cw-observation-nav">' +
        link('/wiki/evidence/', 'Level 1 · Evidence register') + link('/wiki/observations/', 'Level 2 · All observations') +
        '</nav><article><h1>' + esc(o.get('title', 'Observation')) + '</h1>' +
        '<p class="cw-observation-meta">' + esc(o.get('id', '')) + ' · ' + esc(o.get('observation_type', 'observation').replace('_', ' ')) +
        ' · ' + esc(o.get('status', 'working_observation').replace('_', ' ')) + '</p>' +
        '<section class="cw-observation-panel"><h2>Summary</h2>' + paragraphs(o.get('summary', '')) + '</section>' +
        '<section><h2>Analysis</h2>' + paragraphs(o.get('analysis', '')) + '</section>' +
        '<section class="cw-observation-limit"><h2>Limits and alternative explanations</h2>' + paragraphs(o.get('limits', '')) + '</section>' +
        '<section><h2>Tests and questions</h2>' + questions + '</section>' +
        '<section><h2>Underlying artifact references</h2>' + source_links(o) + '</section>' +
        related + '</article></main></body></html>')

def observations_index(items):
    cards = []
    for o in sorted(items, key=lambda x: (x.get('seq', 9999), x.get('id', ''))):
        cards.append('<article class="cw-observation-panel"><p class="cw-observation-meta">' +
            esc(o.get('id', '')) + ' · ' + esc(o.get('status', 'working_observation').replace('_', ' ')) +
            '</p><h2>' + link('/wiki/observations/' + esc(o.get('slug', '')) + '/', o.get('title', 'Observation')) +
            '</h2>' + paragraphs(o.get('summary', '')) +
            '<p>' + link('/wiki/observations/' + esc(o.get('slug', '')) + '/', 'Read observation and its references') + '</p></article>')
    return (head('Observations') + '<main class="cw-observation-main">' +
        '<nav class="cw-observation-nav">' + link('/wiki/evidence/', 'Level 1 · Evidence register') + '</nav>' +
        '<h1>Level 2 · Observations</h1>' +
        '<p>Observations are derived research records. Each one links back to its source artifacts and records its limits and test questions. They are not themselves original evidence.</p>' +
        ''.join(cards) + '</main></body></html>')

def browser_section():
    return '''<section class="cw-observation-panel" data-cedwyn-evidence-browser>
<h2>Browse the central evidence catalogue</h2>
<p>Level 1 · Artifacts and Level 2 · Observations. The source register remains below; the database view separates description, transcription and interpretation.</p>
</section>
<script defer src="/_cedwyn/evidence-browser.js"></script>'''

def generate_missing_assessment_pages(dist, observation_items):
    """Publish a Level 1 page for a referenced structured assessment when its source page is absent.

    The generated page is explicitly a research entry, never a substitute for an uninspected source
    document. It does not invent a grade, transcript, source-origin ID or primary-source status.
    """
    dist = pathlib.Path(dist)
    assessment_file = ROOT / 'data' / 'artifact-assessments.json'
    if not assessment_file.exists():
        return []
    assessment_doc = json.loads(assessment_file.read_text(encoding='utf-8'))
    referenced_paths = {}
    for observation in observation_items:
        for ref in observation.get('refs', []):
            ev = str(ref.get('ev') or '').strip().upper()
            path = str(ref.get('path') or '').strip()
            if ev and path.startswith('/research/evidence/'):
                referenced_paths.setdefault(ev, path if path.endswith('/') else path + '/')
    generated = []
    for item in assessment_doc.get('items', []):
        ev = str(item.get('ev') or '').strip().upper()
        path = referenced_paths.get(ev, '')
        match = re.fullmatch(r'/research/evidence/(ev-\d{4}-[a-z0-9-]+)/', path, re.I)
        # The page slug must actually identify the same EV record.
        if not match or not match.group(1).upper().startswith(ev + '-'):
            continue
        description = str(item.get('description') or '').strip()
        interpretation = str(item.get('interpretation') or '').strip()
        if not description and not interpretation:
            continue
        dest = dist / path.lstrip('/') / 'index.html'
        if dest.exists():
            continue
        slug = match.group(1).split('-', 2)[-1]
        title = ev + ' — ' + re.sub(r'(?<=\d)-(?=\d)', '–', slug.replace('-', ' ').title())
        transcript = str(item.get('transcript') or '').strip()
        transcript_status = str(item.get('transcript_status') or 'not_assessed')
        description_status = str(item.get('description_status') or 'not_assessed')
        interpretation_status = str(item.get('interpretation_status') or 'not_assessed')
        verification_status = str(item.get('source_verification_status') or 'not_assessed')
        limitations = str(item.get('limitations') or '').strip()
        referenced_by = [
            o for o in observation_items
            if any(str(r.get('ev') or '').strip().upper() == ev for r in o.get('refs', []))
        ]
        related_links = ''.join(
            '<li>' + link('/wiki/observations/' + str(o.get('slug') or '') + '/',
                          str(o.get('id') or '') + ' — ' + str(o.get('title') or 'Related observation')) + '</li>'
            for o in referenced_by if o.get('slug')
        )
        page = head(title) + (
            '<main class="cw-observation-main"><nav class="cw-observation-nav">' +
            link('/wiki/evidence/', 'Level 1 · Evidence register') +
            link('/wiki/observations/', 'Level 2 · Observations') +
            '</nav><article><h1>' + esc(title) + '</h1>' +
            '<p class="cw-observation-meta">Level 1 catalogue entry · legal research reference · evidence grade not assigned</p>' +
            '<section class="cw-observation-panel"><h2>Record status</h2>' +
            '<p>This is a generated research entry made from the structured assessment because a corresponding source page was not present in the section snapshots. It is not the original statutory text and does not establish that either Act has been independently inspected.</p>' +
            '<p>No evidence grade or independent source-origin ID has been assigned to this entry.</p></section>' +
            '<section><h2>Description</h2>' + paragraphs(description) +
            '<p class="cw-observation-meta">Description status: ' + esc(description_status.replace('_', ' ')) + '</p></section>' +
            '<section><h2>Transcription</h2>' +
            (paragraphs(transcript) if transcript else '<p>No transcription is recorded for this entry; statutory text has not been reproduced here.</p>') +
            '<p class="cw-observation-meta">Transcription status: ' + esc(transcript_status.replace('_', ' ')) + '</p></section>' +
            '<section><h2>Interpretation</h2>' + paragraphs(interpretation) +
            '<p class="cw-observation-meta">Interpretation status: ' + esc(interpretation_status.replace('_', ' ')) + '</p></section>' +
            '<section class="cw-observation-limit"><h2>Verification and limitations</h2>' +
            '<p>Source-verification status: ' + esc(verification_status.replace('_', ' ')) + '</p>' +
            paragraphs(limitations) +
            '<p>Use this entry as a legal-reference pointer for testing dated intervals, the land parcel concerned and the applicable statutory regime. Do not infer the legal effect of an interval from recurrence alone.</p></section>' +
            ('<section><h2>Related observations</h2><ul>' + related_links + '</ul></section>' if related_links else '') +
            '</article></main></body></html>'
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(page, encoding='utf-8')
        generated.append({'ev': ev, 'path': path, 'page': str(dest.relative_to(dist))})
    return generated

def run(dist):
    dist = pathlib.Path(dist)
    obs_file = ROOT / 'data' / 'observations.json'
    doc = json.loads(obs_file.read_text(encoding='utf-8'))
    items = doc.get('items', [])
    assessment_pages = generate_missing_assessment_pages(dist, items)
    outdir = dist / 'wiki' / 'observations'
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / 'index.html').write_text(observations_index(items), encoding='utf-8')
    generated = 0
    for item in items:
        slug = item.get('slug')
        if not slug or not re.fullmatch(r'[a-z0-9-]+', slug):
            continue
        path = outdir / slug / 'index.html'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(observation_html(item), encoding='utf-8')
        generated += 1

    # Enhance the existing register in-place; do not replace its legacy table or text.
    evidence_index = dist / 'wiki' / 'evidence' / 'index.html'
    if evidence_index.exists():
        page = evidence_index.read_text(encoding='utf-8', errors='replace')
        if 'data-cedwyn-evidence-browser' not in page:
            h1 = re.search(r'(<h1\b[^>]*>.*?Evidence\s+Register.*?</h1>)', page, re.I | re.S)
            table = re.search(r'<table\b', page, re.I)
            if h1:
                insert_at = h1.end()
            elif table:
                insert_at = table.start()
            else:
                insert_at = page.lower().find('</main>')
                if insert_at < 0:
                    insert_at = page.lower().find('</body>')
                if insert_at < 0:
                    insert_at = len(page)
            page = page[:insert_at] + '\n' + browser_section() + '\n' + page[insert_at:]
            evidence_index.write_text(page, encoding='utf-8')
    else:
        evidence_index.parent.mkdir(parents=True, exist_ok=True)
        evidence_index.write_text(head('Evidence Register') +
            '<main class="cw-observation-main"><h1>Evidence Register</h1>' + browser_section() +
            '<p>The original register was not present in this build output. The database-backed catalogue is available above; the register source should be checked in the wiki crawl report.</p></main></body></html>',
            encoding='utf-8')
    print('evidence observations: %d observation pages; %d missing Level 1 assessment pages generated; browser mounted where evidence register was found' % (generated, len(assessment_pages)))

if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
