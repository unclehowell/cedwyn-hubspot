#!/usr/bin/env python3
"""ebook_editions.py - the e-book compartment's editions and prices (25 Oct 2026). - Sion's Tab agent
Touches only /ebooks/ (the e-book theme's own pages) and the /ebooks/api/ route:
- an "Editions and prices" table at the top of /ebooks/ and "version x.y.z · £" on each book card, from data/ebooks.json;
- the free-edition downloads: the e-book pages link /ebooks/api/free?book=..., a gate that lives on the shop
  (ebooks.bucklerfamily.estate/api/, which serves paying customers and is not retired), so /ebooks/api/* is sent there (302).
Usage: python3 tools/ebook_editions.py dist   (site.py calls it after sections.py)"""
import json, html, pathlib, sys, re
ROOT = pathlib.Path(__file__).resolve().parent.parent
STEP_GBP = 4.99  # whole-release price step: v0.0.1 free, each later release +STEP_GBP (Sion 05:13 GMT 27 Oct 2026) - Sion's Tab agent
def release_price(n): return '£%d.%02d' % divmod((n - 1) * round(STEP_GBP * 100), 100)  # whole pence
E = html.escape
CSS = ('<style id="eb-editions-css">.eb-eds{margin:0 auto 18px;max-width:1100px;padding:0 16px}.eb-eds h2{margin:6px 0 6px}.eb-eds p{margin:0 0 8px;opacity:.85;font-size:14px}'
       '.eb-eds .sc{overflow-x:auto;-webkit-overflow-scrolling:touch}.eb-eds table{border-collapse:collapse;width:100%;font-size:14px}'
       '.eb-eds th,.eb-eds td{text-align:left;padding:7px 8px;border-bottom:1px solid rgba(128,128,128,.35);vertical-align:top}.eb-eds th{font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.8}'
       '.eb-eds td.n{white-space:nowrap}.eb-eds small{opacity:.75;font-size:12px}.eb-eds a{color:inherit}'
       # rows become cards on phones, no sideways scroll (Sion, 13:15 GMT 26 Oct 2026) - Sion's Tab agent
       '@media(max-width:640px){.eb-eds{padding:0 12px}.eb-eds .sc{overflow:visible}.eb-eds table,.eb-eds tbody,.eb-eds tr,.eb-eds td{display:block;width:auto}.eb-eds thead{display:none}'
       '.eb-eds tr{border:1px solid rgba(128,128,128,.35);border-radius:10px;padding:8px 10px;margin:0 0 8px}.eb-eds td,.eb-eds td.n{border:0;padding:2px 0;white-space:normal;overflow-wrap:anywhere}'
       '.eb-eds td:first-child{font-weight:600}.eb-eds td:nth-child(2)::before{content:"Edition · ";opacity:.7;font-size:12px}.eb-eds td:nth-child(3)::before{content:"Price · ";opacity:.7;font-size:12px}}</style>')
ACADEMY = ('<section class="eb-about eb-bundle" id="academy-upsell"><h2>Cedwyn Academy · £49.99 a month</h2>'
           '<p>Members get the latest version of every e-book and the latest documentary scenes included, with the course on the case, module by module.</p>'
           '<div class="eb-actions2"><a class="sl-btn" href="/learn/">See the Academy</a></div></section>')
def table(D):
    rows = ''.join(f'<tr><td><a href="{E(b["page"] or "/ebooks/")}">{E(b["title"])}</a></td><td class="n">{E(b["edition"])}' + (f'<br><small><a href="{E(b["supplement"])}">+ supplement, 25 Oct 2026 (free PDF)</a></small>' if b.get('supplement') else '') + '</td>'
                   f'<td class="n">{E(b["price"])}</td></tr>' for b in D['books'])
    rows += ''.join(f'<tr><td><a href="{E(x["page"] or "/ebooks/")}">{E(x["title"])}</a></td><td class="n">newest<br><small>editions</small></td><td class="n">{E(x["price"])}</td></tr>' for x in D.get('bundles', []))
    return (f'<section class="eb-eds" id="editions" aria-label="Editions and prices">{CSS}<h2>Editions and prices</h2>'
            f'<p>Each book’s current edition, its version number and its price. Every book’s first whole release (v0.0.1) is free; each later release costs £4.99 more than the one before.</p>'
            f'<div class="sc"><table><thead><tr><th>Book</th><th>Edition</th><th>Price</th></tr></thead><tbody>{rows}</tbody></table></div></section>')
# 30 Oct 2026 (Cedwyn data architecture ADR-002 / WP10 and the 30 Oct shop patch bundle) - Sion's Tab agent
# 1. The shop's own database: dist/ebooks/_db/view.json (public rows only, derived from data/ebooks.json, never edited by hand).
#    The header graph (graph_data.py) plots this file and nothing else; agents read it as a plain file (dbserve keep-list).
# 2. Shelf copy under the editions table: "What's inside", a short trust line and the questions block with FAQPage JSON-LD.
#    Prices in the copy come from data/ebooks.json, so a price change updates them at the next build.
SITE = 'https://cedwyn.bucklerfamily.estate'
MONTHS = 'January February March April May June July August September October November December'.split()
def _iso(s):
    m = re.search(r'(\d{4})-(\d\d)-(\d\d)', s or '')
    if m: return m.group(0)
    m = re.search(r'(\d{1,2}) (%s|%s) (\d{4})' % ('|'.join(MONTHS), '|'.join(x[:3] for x in MONTHS)), s or '')
    if m:
        mi = [x[:3] for x in MONTHS].index(m.group(2)[:3]) + 1
        return '%s-%02d-%02d' % (m.group(3), mi, int(m.group(1)))
    return None
def view(D):
    books, rel = [], []
    for b in D['books']:
        free = b.get('price') in ('£0.00', '£0', 'free')
        books.append({k: b.get(k) for k in ('id', 'title', 'edition', 'semver', 'price', 'pages', 'date', 'free', 'page', 'supplement') if b.get(k) not in (None, '')})
        short = re.split(r' — | · | – ', b['title'])[0][:60]
        rel.append({'book': short, 'date': b.get('date'), 'kind': 'First edition · free' if free else 'Updated edition · %s' % b.get('price'),
                    'label': '%s · %s · %s' % (short, b.get('edition'), 'free' if free else b.get('price')), 'page': b.get('page') or '/ebooks/'})
        sd = _iso((b.get('supplement') or '').rsplit('/', 1)[-1])
        if sd: rel.append({'book': short, 'date': sd, 'kind': 'Supplement · free PDF', 'label': '%s · supplement' % short, 'page': b.get('page') or '/ebooks/'})
        wd = _iso(re.search(r'\(([^)]*\d{4})\)', b.get('whats_new') or '').group(1) if re.search(r'\(([^)]*\d{4})\)', b.get('whats_new') or '') else '')
        if wd and wd != sd: rel.append({'book': short, 'date': wd, 'kind': 'Revision', 'label': '%s · %s' % (short, (b.get('semver') or '')), 'page': b.get('page') or '/ebooks/'})
    bundles = [{k: x.get(k) for k in ('id', 'title', 'price', 'page', 'books')} for x in D.get('bundles', [])]
    return {'books': books, 'bundles': bundles, 'releases': sorted(rel, key=lambda r: (r['date'] or '', r['book'])),
            'meta': {'app': 'ebooks', 'view_version': '1.0.0', 'source': 'data/ebooks.json (the shop catalogue)', 'rule': 'tools/ebook_editions.py view()',
                     'counts': {'books': len(books), 'bundles': len(bundles), 'releases': len(rel)}, 'price_rule': D.get('price_rule')}}
def _paid_price(D):
    ps = sorted({b['price'] for b in D['books'] if b.get('price') not in ('£0.00', '£0')})
    return ps[0] if len(ps) == 1 else None
SHOP_CSS = ('<style id="eb-shop-copy-css">.eb-copy{max-width:1100px;margin:0 auto 18px;padding:0 16px}.eb-copy h2{margin:10px 0 8px}'
            '.eb-copy details{border-bottom:1px solid rgba(128,128,128,.35);padding:8px 0}.eb-copy summary{cursor:pointer;font-weight:600;line-height:1.35;min-height:28px}'
            '.eb-copy details p,.eb-copy details ol{margin:6px 0 2px;opacity:.9;font-size:15px;line-height:1.5}.eb-copy ol{padding-left:1.3em}.eb-copy a{color:inherit;text-decoration:underline}'
            '.eb-trust{max-width:1100px;margin:6px auto 14px;padding:0 16px;font-size:15px;line-height:1.45;opacity:.85}@media(max-width:640px){.eb-copy,.eb-trust{padding:0 12px}}</style>')
def whats_inside(D):
    pages = {b['id']: b.get('pages') for b in D['books']}
    return ('<section class="eb-copy" id="whats-inside" aria-label="What is inside the books"><h2>What’s inside</h2>'
            '<details open><summary>Great House Farm (Tŷ Mawr), Llandough — The Wiki · about 2,060 pages</summary><ol>'
            '<li><b>Start here</b> — where things stand and how to read the records</li>'
            '<li><b>The case</b> — the two parcels, the people, the 1877 agreement, the 1916 tenancy, the 1955 and 1962 possession orders, the 1974 licence letters and BP Properties Ltd v Buckler</li>'
            '<li><b>Timeline and chronologies</b> — the master timeline, year by year</li>'
            '<li><b>Evidence</b> — each record with what it is, where it is held and how it was seen</li>'
            '<li><b>Source conflicts, name variations and nomenclature</b></li>'
            '<li><b>Correspondence</b> — letters and replies from public bodies</li>'
            '<li><b>Research leads and lines of enquiry</b></li>'
            '<li><b>Scrutiny, legal analysis and accountability</b></li>'
            '<li><b>About the Wiki, change log and index</b></li></ol></details>'
            '<details><summary>Concealment and Government Involvement · 221 pages</summary><p>Our case and lines of enquiry, each graded: DOCUMENTED (a primary record in hand, cited by reference), INFERENCE (a reasoned reading of documented facts), TEST REQUIRED (needs a named record), SOURCE PENDING (identified, original not yet attached).</p></details>'
            '<details><summary>The Disclosure Dartboard · 404 pages</summary><p>Every route to a public record about the farm, institution by institution: the legal regimes that reach its records, each rung of its escalation ladder with its legal basis, time limit and cost, and what has been asked and answered.</p></details>'
            '<details><summary>Great House Farm Projects · 187 pages</summary><p>The PRINCE2 project dossier of the Tŷ Mawr digital estate and its evidence-recovery programme.</p></details>'
            '<p><a href="/ebooks/free/">Read the first editions free</a> before you buy.</p></section>')
def trust_line():
    return ('<p class="eb-trust" id="eb-trust">🔒 Card payment by Stripe · PDF download straight after payment · no account needed · '
            '<a href="/privacy/" style="color:inherit">privacy</a></p>')
def faq(D):
    paid = _paid_price(D) or '£4.99'
    bundle = (D.get('bundles') or [{}])[0]
    qa = [('What are the Cedwyn e-books?', 'PDF books built from the records of Great House Farm (Tŷ Mawr), Llandough, near Penarth: maps, tenancies, newspaper reports and court records, each with its source.'),
          ('Is any of it free?', 'Yes. The first edition of every book is free to download, so you can read before you buy. The first chapter is also free to read on the site.'),
          ('How much are the updated editions?', 'Each updated edition is %s.%s The price shown is the price you pay.' % (paid, (' All four core books together (four PDFs, 2,876 pages) are %s in one checkout.' % bundle['price']) if bundle.get('price') else '')),
          ('What format are they, and what can I read them on?', 'PDF. They open on a phone, tablet or computer in any PDF reader.'),
          ('How do I get the book after paying?', 'Checkout is by Stripe. The PDF download opens straight after payment, and no account is needed. Keep the file: it is yours to read on any of your devices.'),
          ('Do the books change?', 'Yes. Each book is dated, and the updated editions come with a dated supplement, so you can see what was added and when.'),
          ('Where do the facts come from?', 'From the archive’s evidence catalogue: every record is listed with what it is, where it is held and how it was seen, and the books cite those records.')]
    links = {'Is any of it free?': '<a href="/ebooks/sample-chapter/">first chapter</a>'}
    body = ''.join('<details><summary>%s</summary><p>%s</p></details>' % (E(q), E(a).replace('first chapter', links[q]) if q in links else E(a)) for q, a in qa)
    ld = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in qa]}
    return ('<section class="eb-copy" id="faq" aria-label="Questions"><h2>Questions</h2>' + body + '</section>'
            '<script type="application/ld+json" id="eb-faq-ld">' + json.dumps(ld, ensure_ascii=False).replace('</', '<\\/') + '</script>')
def shop_copy(D, t):
    """Idempotent: each block is added once, keyed by its id."""
    if 'id="eb-shop-copy-css"' not in t:
        m = re.search(r'</head\s*>', t, re.I)
        if m: t = t[:m.start()] + SHOP_CSS + t[m.start():]
    # 30 Oct 2026 (owner rule): no explanatory blocks above the books. The contents now open from each title's info button
    # (ebook_shelf.py 1.2.0); the payment line and the questions sit below the shelf.
    if 'id="faq"' not in t and 'FAQPage' not in t:
        at = t.find('<section class="sl-band eb-about" id="digital-estate-books"')
        if at < 0: at = t.rfind('</main>')
        if at >= 0: t = t[:at] + faq(D) + t[at:]
    if 'id="eb-trust"' not in t:
        at = t.find('<section class="eb-copy" id="faq"')
        if at >= 0: t = t[:at] + trust_line() + t[at:]
    return t
def write_view(dist, D):
    out = pathlib.Path(dist) / 'ebooks' / '_db'; out.mkdir(parents=True, exist_ok=True)
    v = view(D); v['meta']['generated'] = __import__('datetime').datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    (out / 'view.json').write_text(json.dumps(v, ensure_ascii=False, indent=1), 'utf-8')
    return v['meta']['counts']

def run(dist):
    dist = pathlib.Path(dist); D = json.load(open(ROOT / 'data' / 'ebooks.json', encoding='utf-8')); n = 0
    p = dist / 'ebooks' / 'index.html'
    if p.exists():
        t = p.read_text(encoding='utf-8', errors='ignore'); o = t
        # The Argentina and Wales paths rewrite to this shared shelf. Move its pitch
        # from the hero to the end of the main content, without duplicating the copy.
        if 'id="digital-estate-books"' not in t:
            m = re.search(
                r'(<p>The digital estate’s records as books you can keep:.*?</p>\s*'
                r'<div class="sl-actions">.*?Buy all four.*?</div>\s*'
                r'<p class="eb-proof"[^>]*>.*?Cardiff Times, 16 July 1904\..*?</p>)',
                t, flags=re.S)
            if m:
                pitch = m.group(1)
                t = t[:m.start()] + t[m.end():]
                pitch_section = ('<section class="sl-band eb-about" id="digital-estate-books" '
                                 'aria-label="Digital estate books">\n' + pitch + '\n</section>\n')
                at = t.rfind('</main>')
                if at >= 0:
                    t = t[:at] + pitch_section + t[at:]
        if 'id="editions"' not in t:
            m = re.search(r'<main\b[^>]*>', t)
            if m: t = t[:m.end()] + table(D) + t[m.end():]
        if 'id="academy-upsell"' not in t:   # cross-sell: membership includes the latest editions (27 Oct 2026) - Sion's Tab agent
            m = re.search(r'<section class="eb-about eb-bundle" id="all-four">.*?</section>', t, flags=re.S)
            if m: t = t[:m.end()] + ACADEMY + t[m.end():]
        for b in D['books']:   # "version x.y.z · £" on the book's own card
            m = re.search(r'(<article class="eb-card" id="%s".*?<p class="eb-facts">)' % re.escape(b['id']), t, flags=re.S)
            if m and ('data-eb-ver="%s"' % b['id']) not in t:
                t = t[:m.end()] + f'<span data-eb-ver="{E(b["id"])}">{E(b["edition"])} · {E(b["price"])}</span>' + t[m.end():]
        t = shop_copy(D, t)
        if t != o: p.write_text(t, encoding='utf-8'); n += 1
    rd = dist / '_redirects'
    gate = ['/ebooks/api/* https://ebooks.bucklerfamily.estate/api/:splat 302', '/wales/ebooks/api/* https://ebooks.bucklerfamily.estate/api/:splat 302',
            '/argentina/ebooks/api/* https://ebooks.bucklerfamily.estate/api/:splat 302']
    old = rd.read_text().splitlines() if rd.exists() else []
    rd.write_text('\n'.join(gate + [l for l in old if l not in gate]) + '\n')
    try: vc = write_view(dist, D)
    except Exception as e: vc = 'failed: %s' % e
    print('ebook_editions: pages changed', n, '; books', len(D['books']), '; ebooks/_db/view.json', vc)
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
