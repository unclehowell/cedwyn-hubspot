#!/usr/bin/env python3
"""title_chain.py - /title-chain/: the chain of freehold / manorial title and the chain of occupiers and leaseholders of Tŷ Mawr,
link by link (Sion, 03:07 GMT 26 Oct 2026, m:891a9b2b: "I'm no clearer on the chain or freehold and chain of leaseholder").
- Sion's Tab agent
Each row = one link: date, document and what it shows, its own words (quoted, original language), source / EV link, status:
ev (evidenced) / cat (catalogue only) / sec (secondary) / rec (recited only) / court (court's view) / fam (family account) /
gap (no record found). fam and gap rows are "substantiated": false and render small italic (.unsub, tools/unsub.py).
Gaps stay gaps; nothing is filled by assumption. Copy: data/title-chain.json (en/cy/es; quotations stay in the record's language).
Written to dist/title-chain/ (English), dist/wales/title-chain/ (Welsh default) and dist/argentina/title-chain/ (Spanish
default); both halves list it under Past in their menus (data/halves.json groups.past_pages). Runs after halves.run()."""
import html, json, pathlib, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
E = lambda s: html.escape(str(s), quote=True)
OPEN, CLOSE = '\u27e6', '\u27e7'
UNSUB_ST = ('fam', 'gap')
BANNED = re.compile(r'\b(says|claims|according to|hearsay|unverified|alleged|fraud|stolen)\b', re.I)

CSS = """
.tc h1{margin:4px 0 8px}.tc .lede{font-size:16px;line-height:1.5}.tc .frame{font-size:14px;color:var(--mut);border-left:3px solid var(--a,#00843D);padding:2px 0 2px 10px;margin:10px 0 16px}
.tc h2{font:700 clamp(18px,4.6vw,22px)/1.25 Barlow,system-ui,sans-serif;letter-spacing:.04em;margin:26px 0 8px}
.tc-t{width:100%;border-collapse:collapse;font-size:14.5px;line-height:1.42}
.tc-t th{text-align:left;font:700 12px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);border-bottom:2px solid var(--line);padding:6px 8px}
.tc-t td{vertical-align:top;border-bottom:1px solid var(--line);padding:9px 8px;overflow-wrap:anywhere}
.tc-t td.d{white-space:nowrap;font-weight:700}.tc-t td.q{font-family:Georgia,"Times New Roman",serif}
.tc-t .lb{display:none}
.tc-t a.ev{display:inline-block;margin:2px 4px 0 0;padding:1px 6px;border:1px solid var(--line);border-radius:4px;text-decoration:none;font:600 11.5px/1.5 Barlow,system-ui,sans-serif}
.tc-t .src{display:block;font-size:12px;color:var(--mut);margin-top:2px}
.tc .chip{display:inline-block;padding:2px 8px;border-radius:999px;font:700 11px/1.4 Barlow,system-ui,sans-serif;letter-spacing:.05em;text-transform:uppercase;border:1px solid currentColor;white-space:nowrap}
.tc .st-ev{color:#2e9d5b}.tc .st-cat,.tc .st-sec{color:#5b8fd6}.tc .st-rec{color:#c98a12}.tc .st-court{color:#9a6fd0}.tc .st-fam,.tc .st-gap{color:#c8102e}
.tc-t tr.r-gap td{background:rgba(200,16,46,.05)}
.tc dl.key{display:grid;grid-template-columns:max-content 1fr;gap:6px 10px;font-size:13px;margin:8px 0 0}.tc dl.key dd{margin:0;color:var(--mut)}
.tc .n{font-size:12.5px;color:var(--mut);margin-top:14px}
@media (max-width:700px){.tc-t,.tc-t tbody,.tc-t tr,.tc-t td{display:block;width:auto}.tc-t thead{display:none}
.tc-t tr{border:1px solid var(--line);border-radius:10px;margin:0 0 10px;padding:6px 10px}.tc-t td{border:0;padding:4px 0}.tc-t td.d{white-space:normal}
.tc-t .lb{display:block;font:700 10.5px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mut)}
.tc-t tr{display:grid;grid-template-columns:1fr auto;column-gap:8px}.tc-t td{grid-column:1/-1}.tc-t td.d{grid-column:1;grid-row:1}.tc-t td.s{grid-column:2;grid-row:1;align-self:center}.tc-t td.d .lb,.tc-t td.s .lb{display:none}}
"""

def load():
    return json.load(open(ROOT / 'data' / 'title-chain.json', encoding='utf-8'))

def strings(D):
    T = dict(D['t'])
    for k, s in D['status'].items():
        T['tc_st_' + k] = s['label']; T['tc_sd_' + k] = s['desc']
    for ch in ('freehold', 'occupiers'):
        for i, r in enumerate(D[ch]):
            doc = r['doc']
            if r['st'] in UNSUB_ST or r.get('substantiated') is False:
                doc = {l: OPEN + v + CLOSE for l, v in doc.items()}
            T[f'tc_{ch[0]}{i}'] = doc
            if r.get('note'): T[f'tc_{ch[0]}{i}n'] = r['note']
    return T

def table(D, T, l, ch):
    tx = lambda k: (T.get(k) or {}).get(l) or (T.get(k) or {}).get('en') or ''
    lb = lambda k: f'<span class="lb" data-i18n="{k}">{E(tx(k))}</span>'
    head = ''.join(f'<th data-i18n="{k}">{E(tx(k))}</th>' for k in ('tc_c_date', 'tc_c_doc', 'tc_c_q', 'tc_c_src', 'tc_c_st'))
    rows = []
    for i, r in enumerate(D[ch]):
        k = f'tc_{ch[0]}{i}'
        evs = ''.join(f'<a class="ev" href="{E(D["ev_href"].get(e, "/research/evidence/"))}">{E(e)}</a>' for e in r['ev'])
        src = (f'<span class="src">{E(r["src"])}</span>' if r.get('src') else '')
        note = (f' <span class="src" data-i18n="{k}n">{E(tx(k + "n"))}</span>' if r.get('note') else '')
        q = E(r['q']) if r.get('q') else '<span aria-hidden="true">—</span>'
        rows.append(f'<tr class="r-{E(r["st"])}" id="{ch[0]}{i+1}"><td class="d">{lb("tc_c_date")}{E(r["date"])}</td>'
                    f'<td>{lb("tc_c_doc")}<span data-i18n="{k}">{E(tx(k))}</span>{note}</td>'
                    f'<td class="q">{lb("tc_c_q")}{q}</td><td>{lb("tc_c_src")}{evs}{src}</td>'
                    f'<td class="s">{lb("tc_c_st")}<span class="chip st-{E(r["st"])}" data-i18n="tc_st_{E(r["st"])}">{E(tx("tc_st_" + r["st"]))}</span></td></tr>')
    return f'<table class="tc-t"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'

def page(sections, S, cfg, D, sec, l):
    import unsub
    T = sections.page_t(S, cfg, sec); T.update(strings(D))
    tx = lambda k: (T.get(k) or {}).get(l) or (T.get(k) or {}).get('en') or ''
    bpath = f'/{sec}/title-chain/' if sec else '/title-chain/'
    key = ''.join(f'<dt><span class="chip st-{k}" data-i18n="tc_st_{k}">{E(tx("tc_st_" + k))}</span></dt><dd data-i18n="tc_sd_{k}">{E(tx("tc_sd_" + k))}</dd>' for k in D['status'])
    back = ('<a href="/wales/" lang="cy" data-i18n="tc_back_w">%s</a> · <a href="/argentina/" lang="es" data-i18n="tc_back_a">%s</a>'
            % (E(tx('tc_back_w')), E(tx('tc_back_a'))))
    desc = 'Title chain of Tŷ Mawr, Llandough: the Williams family line at the house, then every title others assert over it, tested link by link against its source; gaps shown as gaps.'
    hd = sections.head('Title chain · Tŷ Mawr · Cedwyn', desc, l, bpath, sec, T, len(cfg['themes']))
    hd = hd.replace('</style>', CSS + '</style>', 1)
    body = f"""
<body data-cedwyn-page="title-chain">
<main class="wrap tc" data-no-translate>
{sections.langbar(T, l)}
<p class="eyebrow"><span data-i18n="tc_kicker">{E(tx('tc_kicker'))}</span></p>
<h1 data-i18n="tc_h1">{E(tx('tc_h1'))}</h1>
<p class="lede" data-i18n="tc_lede">{E(tx('tc_lede'))}</p>
<p class="frame" data-i18n="tc_frame">{E(tx('tc_frame'))}</p>
<details><summary data-i18n="tc_key_h">{E(tx('tc_key_h'))}</summary><dl class="key">{key}</dl></details>
<h2 id="occupiers" data-i18n="tc_o_h">{E(tx('tc_o_h'))}</h2>
{table(D, T, l, 'occupiers')}
<h2 id="freehold" data-i18n="tc_f_h">{E(tx('tc_f_h'))}</h2>
{table(D, T, l, 'freehold')}
<p class="n" data-i18n="tc_n">{E(tx('tc_n'))}</p>
<p class="endnote">{back} · <a href="/catalogue/" data-i18n="tc_cat">{E(tx('tc_cat'))}</a></p>
</main>
</body>
</html>
"""
    return unsub.html(hd + body)

def check(text):
    m = re.search(r'<main\b.*?</main>', text, flags=re.S)
    main = m.group(0)
    out = [h for h in re.findall(r'href="([^"]+)"', main) if re.match(r'^(https?:)?//', h)]
    assert not out, 'title-chain: outbound link %s' % out[:3]
    vis = re.sub(r'<td class="q">.*?</td>', ' ', main, flags=re.S)
    vis = re.sub(r'<[^>]+>', ' ', vis)
    hit = BANNED.findall(vis)
    assert not hit, 'title-chain: banned word %s' % hit[:3]

def run(dist, cfg):
    import sections, sys
    dist = pathlib.Path(dist); D = load()
    S = json.load(open(ROOT / 'sections.json', encoding='utf-8'))
    try:
        import agent_footer
    except Exception:
        agent_footer = None
    out = {dist / 'title-chain' / 'index.html': (None, 'en'), dist / 'wales' / 'title-chain' / 'index.html': ('wales', 'cy'),
           dist / 'argentina' / 'title-chain' / 'index.html': ('argentina', 'es')}
    for p, (sec, l) in out.items():
        t = page(sections, S, cfg, D, sec, l); check(t)
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(t, encoding='utf-8')
        if agent_footer and hasattr(agent_footer, 'inject'):
            try: agent_footer.inject(p, False)
            except Exception as e: print('title-chain: footer skipped', e)
    print('title-chain ok:', len(D['freehold']), 'freehold links,', len(D['occupiers']), 'occupier links,',
          sum(1 for r in D['freehold'] + D['occupiers'] if r['st'] in UNSUB_ST), 'small italic')

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    run(sys.argv[1] if len(sys.argv) > 1 else 'dist', json.load(open(ROOT / 'themes.json')))
