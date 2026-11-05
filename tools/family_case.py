#!/usr/bin/env python3
"""family_case.py - "The family's case / El caso de la familia": its own page at /argentina/caso/ (Argentina half only). - Sion's Tab agent
The file is written to dist/caso/index.html and served at /argentina/caso/ by the existing /argentina/:theme/* rewrite; the
Argentina hub links to it. Built by sections.run() via write(); the Wales half never calls this module.
Advocacy, openly labelled, in the family's voice (Sion, 23:07 GMT 25 Oct 2026). Copy and sources: data/family-case.json (en/es; cy
falls back to en). Every item cites Cedwyn evidence pages (/research/evidence/ev-nnnn-.../) and, where one exists, its 1000 Cuts entry.
Rules kept in the data: charges framed as the family's position, never as court findings; Bute = lord of the manor; BP = registered
proprietor; no private person accused. The Wales half does not call this module."""
import html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
E = lambda s: html.escape(str(s), quote=True)
_EVMAP = None

CSS = """
.fc{margin:18px 0 8px;padding:16px 14px;border:2px solid var(--b);border-radius:14px;background:var(--card)}
.fc .fc-k{display:inline-block;margin:0 0 8px;padding:4px 10px;border-radius:4px;background:var(--b);color:#111;font:700 11px/1.2 Barlow,system-ui,sans-serif;letter-spacing:.16em;text-transform:uppercase}
.fc .fc-h{font:800 clamp(30px,9vw,46px)/1.05 Barlow,system-ui,sans-serif!important;font-weight:800!important;letter-spacing:.02em;text-transform:uppercase;margin:4px 0 12px}
.fc .fc-lab{font-size:12.5px;color:var(--mut);border-left:3px solid var(--b);padding:2px 0 2px 10px;margin:0 0 12px}
.fc p.fc-o{font-size:16.5px;line-height:1.55;margin:0 0 12px}
.fc h3{font:700 19px/1.25 Barlow,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;margin:22px 0 6px}
.fc .grp ol{padding-left:34px}.fc .grp li{margin:10px 0;line-height:1.45;overflow-wrap:anywhere}
.fc .fc-r{display:block;margin-top:3px;font-size:12px;color:var(--mut)}
.fc .fc-r a{display:inline-block;margin:2px 6px 0 0;padding:1px 6px;border:1px solid var(--line);border-radius:4px;text-decoration:none;font:600 11.5px/1.5 Barlow,system-ui,sans-serif;letter-spacing:.04em}
.fc ol.fc-l{margin:6px 0 10px;padding-left:24px}.fc ol.fc-l li{margin:10px 0;line-height:1.45}
.fc .fc-n{font-size:12px;color:var(--mut);margin-top:16px}
"""

def evmap():
    """EV id -> Cedwyn evidence page path (data/family-case.json "ev_paths", read from the live /research/evidence/ index 25 Oct 2026)."""
    global _EVMAP
    if _EVMAP is None:
        D = json.load(open(ROOT / 'data' / 'family-case.json', encoding='utf-8'))
        _EVMAP = dict(D.get('ev_paths', {}))
    return _EVMAP

def strings():
    D = json.load(open(ROOT / 'data' / 'family-case.json', encoding='utf-8'))
    T = dict(D['t'])
    n = 0
    for g in D['groups']:
        T[g['id']] = g['title']
        for it in g['items']:
            n += 1; T['fc_c%d' % n] = it['t']
    for pre, key in (('fc_f', 'flip'), ('fc_a', 'ask')):
        for i, it in enumerate(D[key], 1): T['%s%d' % (pre, i)] = it['t']
    return T, D

def _refs(it, T, l, cut_label):
    m = evmap(); out = []
    for ev in it['ev']:
        out.append(f'<a href="{E(m.get(ev, "/research/evidence/"))}">{E(ev)}</a>')
    if it.get('cut'):
        out.append(f'<a href="/argentina/thousand-cuts/#{E(it["cut"])}"><span data-i18n="fc_cut">{E(cut_label)}</span> {E(it["cut"].upper())}</a>')
    return '<span class="fc-r">' + ''.join(out) + '</span>'

def html_block(T, l, htag='h2'):
    _, D = strings()
    tx = lambda k: (T.get(k) or {}).get(l) or (T.get(k) or {}).get('en') or ''
    sp = lambda k, tag='span', cls='': f'<{tag} data-i18n="{k}"' + (f' class="{cls}"' if cls else '') + f'>{E(tx(k))}</{tag}>'
    cl = tx('fc_cut')
    o = ['<section class="fc" id="caso" aria-labelledby="fc-h">',
         sp('fc_kicker', 'span', 'fc-k'),
         f'<{htag} class="fc-h" id="fc-h" data-i18n="fc_h1">{E(tx("fc_h1"))}</{htag}>',
         sp('fc_label', 'p', 'fc-lab'), sp('fc_o1', 'p', 'fc-o'), sp('fc_o2', 'p', 'fc-o'), sp('fc_o3', 'p', 'fc-o'), sp('fc_toc', 'p', 'mut'),
         f'<h3 data-i18n="fc_cuts_h">{E(tx("fc_cuts_h"))}</h3>', sp('fc_cuts_p', 'p', 'mut')]
    n = 0
    for gi, g in enumerate(D['groups']):
        first = n + 1; lis = []
        for it in g['items']:
            n += 1
            lis.append(f'<li value="{n}">{sp("fc_c%d" % n)}{_refs(it, T, l, cl)}</li>')
        o.append(f'<details class="grp"{" open" if gi == 0 else ""}><summary><span data-i18n="{g["id"]}">{E(tx(g["id"]))}</span>'
                 f'<span class="mut">{first}–{n}</span></summary><ol start="{first}">{"".join(lis)}</ol></details>')
    o.append(f'<h3 data-i18n="fc_flip_h">{E(tx("fc_flip_h"))}</h3><ol class="fc-l">')
    for i, it in enumerate(D['flip'], 1): o.append(f'<li>{sp("fc_f%d" % i)}{_refs(it, T, l, cl)}</li>')
    o.append(f'</ol><h3 data-i18n="fc_ask_h">{E(tx("fc_ask_h"))}</h3><ol class="fc-l">')
    for i, it in enumerate(D['ask'], 1): o.append(f'<li>{sp("fc_a%d" % i)}{_refs(it, T, l, cl)}</li>')
    o.append('</ol>' + sp('fc_end', 'p', 'fc-n') + f'<p class="fc-n"><a href="/wales/" lang="cy" data-i18n="fc_wales">{E(tx("fc_wales"))}</a></p></section>')
    return ''.join(o), n


def page(sec, S, cfg):
    """the standalone page; sec = the sections module (head, langbar, page_t, tx, E)"""
    l = 'es'; n_th = len(cfg['themes']); T = sec.page_t(S, cfg, 'argentina'); T.update(strings()[0])
    T.setdefault('fc_back', {'en': 'Great House II · Argentina', 'es': 'Great House II · Argentina'})
    block, n = html_block(T, l, 'h1')
    desc = ("The family's case: Tŷ Mawr alias Cedfin and the Williams family, the “squatters” story turned the right way up, "
            "and the death of a thousand cuts: %d numbered points, each linked to its record. Advocacy, not a court finding." % n)
    hd = sec.head('El caso de la familia · Argentina · Cedwyn', desc, l, '/argentina/caso/', 'argentina', T, n_th)
    hd = hd.replace('--a:#00843D;--b:#C8102E', '--a:#4E8CC8;--b:#F6B40E').replace('</style>', CSS + '</style>', 1)
    return hd + f"""
<body data-cedwyn-page="argentina-caso">
<main class="wrap" data-no-translate>
{sec.langbar(T, l)}
<p class="eyebrow"><a href="/argentina/" data-i18n="fc_back">{E(sec.tx(T,'fc_back',l))}</a></p>
{block}
<p class="endnote"><a href="/argentina/" data-i18n="fc_back">{E(sec.tx(T,'fc_back',l))}</a> · <a href="/argentina/thousand-cuts/" data-i18n="l_cuts">{E(sec.tx(T,'l_cuts',l))}</a> · <a href="/" data-i18n="home">{E(sec.tx(T,'home',l))}</a></p>
</main>
</body>
</html>
"""

def write(sec, dist, S, cfg):
    d = pathlib.Path(dist) / 'caso'; d.mkdir(parents=True, exist_ok=True)
    (d / 'index.html').write_text(page(sec, S, cfg), encoding='utf-8')
    return d / 'index.html'
