#!/usr/bin/env python3
"""ebook_shelf.py - /ebooks/ as a title-shopping shelf of small poster cards (27 Oct 2026). - Sion's Tab agent
Runs after ebook_editions.py (site.py). Touches only dist/ebooks/index.html:
- the long book list (section.eb-list) becomes a responsive grid of poster cards: 2 per row on a phone, 4-5 on desktop;
- each card: 2:3 cover (webp under web/ebooks/posters/<id>.webp, else the book's existing cover), the title, a one-line hook,
  the existing version <select> (latest selected) and its Buy/Read button (same checkout links, same sv-js script);
- tapping the cover opens the book's free first release (v0.0.1) in the existing reader (a[data-edp-pdf]);
- the title is plain text unless the book has its own page (data/ebooks.json "page", not /ebooks/ itself);
- the editions table moves below the shelf; the bundle and Academy sections stay where they are.
1.2.0 (30 Oct 2026, owner rule: the shop page is header -> shelf of book cards -> FAQ/trust, no explanatory blocks):
- the "What's inside" block, the "Editions and prices" table, "About versions", the pitch band and the shelf version line leave the page;
- each card's title carries an info button (aria-label "What's inside") that opens a dark modal with the book's contents, page count and
  edition line (closes on the cross, Esc or a tap outside); the bundle (all four) becomes one card on the shelf with its own Buy button;
- the payment line (#eb-trust) sits below the shelf, just above the questions. tidy() is idempotent and also runs on an already-built page.
1.2.1 (30 Oct 2026, owner 19:21): the version drop-down is labelled "Select a version" (visible label), newest preselected, options read
  "v0.0.2 — £4.99" / "v0.0.1 — free"; the Buy/Read button still follows the choice (sv-js); 44 px select.
Prices, checkout links and utm parameters are copied from the page as they are; nothing new is created."""
import json, html, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
E = html.escape
VERSION = '1.2.1'
VERSIONS = [('1.2.1', '30 Oct 2026', 'Select a version label; price in each option'),
            ('1.2.0', '30 Oct 2026', 'Header, shelf, then questions: book details in an info modal per title; bundle card on the shelf'),
            ('1.1.0', '27 Oct 2026', 'Poster-card shelf; cover opens the free edition; titles link only to a book’s own page'),
            ('1.0.1', '26 Oct 2026', 'Editions table shown as cards on phones'),
            ('1.0.0', '25 Oct 2026', 'Editions and prices table')]
CSS = ('<style id="sh-css">.sh{max-width:1240px;margin:0 auto 22px;padding:0 12px}.sh h2.sh-h{margin:4px 0 12px;font-size:1.25rem}'
       '.sh-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 12px;margin:0;padding:0;list-style:none}'
       '@media(min-width:700px){.sh-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}@media(min-width:960px){.sh-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:20px 16px}}'
       '@media(min-width:1200px){.sh-grid{grid-template-columns:repeat(5,minmax(0,1fr))}}'
       '.sh-card{display:flex;flex-direction:column;min-width:0;margin:0;padding:0;list-style:none}.sh-card::before{content:none}'
       '.sh-cov{display:block;position:relative;aspect-ratio:2/3;overflow:hidden;border-radius:6px;background:#111;box-shadow:0 6px 18px rgba(0,0,0,.45);transition:transform .15s}'
       '.sh-cov:hover,.sh-cov:focus-visible{transform:translateY(-3px)}.sh-cov img{display:block;width:100%;height:100%;object-fit:cover}'
       '.sh-free{position:absolute;left:6px;top:6px;padding:2px 7px;border-radius:3px;font:700 .62rem/1.5 system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;background:#F2C94C;color:#1a1a1a}'
       '.sh-t{margin:9px 0 2px;font-size:.95rem;line-height:1.25;font-weight:700;overflow-wrap:anywhere}.sh-t a{color:inherit;text-decoration:underline;text-underline-offset:2px}'
       '.sh-hook{margin:0 0 7px;font-size:.8rem;line-height:1.3;opacity:.8}'
       '.sh-card .eb-edbox{margin:auto 0 0;max-width:none}.sh-card .sv-pick{margin:0}.sh-card .sv-lab{display:block;font-size:.66rem;letter-spacing:.1em;text-transform:uppercase;opacity:.7;margin:0 0 3px}'
       '.sh-card .sv-row{display:flex;flex-direction:column;gap:6px}.sh-card .sv-sel{width:100%;min-width:0;max-width:100%;font-size:.85rem;padding:6px 4px}'
       '.sh-card .sv-go{display:block;text-align:center;padding:9px 6px;font-size:.8rem;font-weight:700;border-radius:4px}'
       '.sh-card .sv-free{display:block;margin:5px 0 0;font-size:.72rem;opacity:.8}.sh-ver{margin:14px 0 0;font-size:.72rem;opacity:.65}.sh .sh-t{font-size:15px!important;line-height:1.25!important;letter-spacing:0!important;text-transform:none!important;margin:9px 0 3px!important;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.sh .sh-hook{font-size:12.5px!important;line-height:1.35!important;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}.sh .sh-card select.sv-sel{height:38px!important;min-height:0!important;max-height:38px!important;padding:4px 6px!important;font-size:13px!important;line-height:1.2!important;box-sizing:border-box}.sh .sh-card .sv-go{font-size:13px!important;line-height:1.2!important;min-height:0!important}@media(min-width:960px){.sh .sh-t{font-size:16px!important}}</style>')
def _attrs(tag):
    return dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
def card(art, pages):
    cid = re.search(r'id="([^"]+)"', art).group(1)
    title = re.sub(r'<[^>]+>', '', (re.search(r'<h2[^>]*>(.*?)</h2>', art, re.S) or [None, cid])[1]).strip()
    hook = re.search(r'<p class="eb-sub">(.*?)</p>', art, re.S) or re.search(r'<p class="eb-desc">(.*?)</p>', art, re.S)
    hook = re.sub(r'<[^>]+>', '', hook.group(1)).strip() if hook else ''
    if len(hook) > 90: hook = hook[:87].rsplit(' ', 1)[0] + '…'
    img = re.search(r'<img[^>]*src="([^"]+)"', art)
    poster = ROOT / 'web' / 'ebooks' / 'posters' / f'{cid}.webp'
    src = f'/ebooks/posters/{cid}.webp' if poster.exists() else (img.group(1) if img else '')
    box = re.search(r'(<div class="eb-edbox.*?)<div class="eb-actions2">', art, re.S)
    box = box.group(1) if box else ''
    free = re.search(r'<a class="sv-t" data-k="v0\.0\.1"[^>]*>', box) or re.search(r'<a class="sv-free"[^>]*>', box)
    fa = _attrs(free.group(0)) if free else {}
    keep = ''.join(f' {k}="{fa[k]}"' for k in ('data-edp-pdf', 'data-gb', 'data-title', 'data-ed', 'aria-haspopup') if k in fa)
    cov_img = f'<img src="{E(src)}" width="400" height="600" alt="Cover: {E(title)}" loading="lazy" decoding="async">'
    if fa.get('href'):
        cov = (f'<a class="sh-cov" href="{fa["href"]}" rel="nofollow"{keep} aria-label="Read the free edition of {E(title)}">'
               f'{cov_img}<span class="sh-free">Free v0.0.1</span></a>')
    else:
        cov = f'<span class="sh-cov">{cov_img}</span>'
    page = pages.get(cid)
    t = f'<a href="{E(page)}">{E(title)}</a>' if page else E(title)
    return (f'<li class="sh-card" id="{E(cid)}">{cov}<h3 class="sh-t">{t}</h3>'
            + (f'<p class="sh-hook">{E(hook)}</p>' if hook else '') + box + '</li>')
WI_CSS = ('<style id="wi-css">.sh-th{display:flex;align-items:flex-start;gap:2px}.sh-th .sh-t{flex:1 1 auto;min-width:0}'
          '.sh-i{flex:0 0 auto;background:none;border:0;color:var(--ghf-s,#F2C94C);font-size:18px;line-height:1;padding:8px 2px 6px 4px;'
          'margin:0;cursor:pointer;min-width:30px;min-height:30px;-webkit-tap-highlight-color:transparent}.sh-i:focus-visible{outline:2px solid var(--ghf-s,#F2C94C)}'
          'dialog.eb-wi{background:#121212;color:#ece8e1;border:1px solid #444;border-radius:10px;padding:0;width:min(560px,92vw);max-height:84vh;'
          'overflow:auto;box-sizing:border-box}dialog.eb-wi::backdrop{background:rgba(0,0,0,.72)}.eb-wi-in{position:relative;padding:18px 18px 16px;'
          'font-size:15px;line-height:1.5}.eb-wi-in h2{margin:0 34px 4px 0;font-size:18px;line-height:1.3}.eb-wi-ln{margin:0 0 12px;font-size:13px;'
          'opacity:.75}.eb-wi-in p,.eb-wi-in li{margin:0 0 8px}.eb-wi-in ol{margin:0 0 8px;padding-left:20px}.eb-wi-in a{color:var(--ghf-s,#F2C94C)}'
          '.eb-wi-x{position:absolute;top:8px;right:8px;background:none;border:0;color:inherit;font-size:20px;line-height:1;width:36px;height:36px;'
          'cursor:pointer}.sh-bcov{display:grid;grid-template-columns:1fr 1fr;gap:2px;aspect-ratio:2/3;background:#000}.sh-bcov img{width:100%;'
          'height:100%;object-fit:cover;display:block}.sh-bundle .sv-go{margin-top:6px}'
          '.sh .sh-grid .sh-card select.sv-sel{height:44px!important;max-height:44px!important}.sh .sh-card .sv-sel:focus-visible{outline:2px solid var(--ghf-s,#F2C94C)}</style>')
WI_JS = ('<script id="wi-js">(function(){document.addEventListener("click",function(e){var t=e.target;if(!t||!t.closest)return;'
         'var b=t.closest("[data-wi]");if(b){var d=document.getElementById(b.getAttribute("data-wi"));if(d){e.preventDefault();'
         'if(d.showModal){if(!d.open)d.showModal();}else{d.setAttribute("open","");}}return;}'
         'var x=t.closest(".eb-wi-x");if(x){var dx=x.closest("dialog");if(dx){dx.close?dx.close():dx.removeAttribute("open");}return;}'
         'if(t.tagName==="DIALOG"&&t.classList.contains("eb-wi")){t.close?t.close():t.removeAttribute("open");}});})();</script>')
INSIDE = {   # contents per book, moved from the page into the info modal (owner, 19:18 30 Oct 2026)
    'great-house-farm-wiki': '<ol><li><b>Start here</b>: where things stand and how to read the records</li>'
        '<li><b>The case</b>: the two parcels, the people, the 1877 agreement, the 1916 tenancy, the 1955 and 1962 possession orders, the 1974 licence letters and BP Properties Ltd v Buckler</li>'
        '<li><b>Timeline and chronologies</b>: the master timeline, year by year</li>'
        '<li><b>Evidence</b>: each record with what it is, where it is held and how it was seen</li>'
        '<li><b>Source conflicts, name variations and nomenclature</b></li><li><b>Correspondence</b>: letters and replies from public bodies</li>'
        '<li><b>Research leads and lines of enquiry</b></li><li><b>Scrutiny, legal analysis and accountability</b></li>'
        '<li><b>About the Wiki, change log and index</b></li></ol>',
    'fcg-fraud-concealment-and-government-involvement': '<p>The case and its lines of enquiry, each graded: DOCUMENTED (a primary record in hand, cited by reference), INFERENCE (a reasoned reading of documented facts), TEST REQUIRED (needs a named record), SOURCE PENDING (identified, original not yet attached).</p>',
    'dartboard-disclosure': '<p>Every route to a public record about the farm, institution by institution: the legal regimes that reach its records, each rung of its escalation ladder with its legal basis, time limit and cost, and what has been asked and answered.</p>',
    'project-management': '<p>The PRINCE2 project dossier of the Tŷ Mawr digital estate and its evidence-recovery programme.</p>',
}
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()
def _books(D): return {b['id']: b for b in (D or {}).get('books', [])}
def info_line(b):
    if not b: return ''
    bits = []
    if b.get('edition'): bits.append('Edition ' + b['edition'])
    if b.get('pages'): bits.append('{:,} pages'.format(int(b['pages'])))
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', b.get('supplement') or '')
    if m: bits.append('free supplement PDF %d %s %s' % (int(m.group(3)), MONTHS[int(m.group(2)) - 1], m.group(1)))
    return ' · '.join(bits)
def info_dialog(cid, title, body, line):
    return (f'<dialog class="eb-wi" id="wi-{E(cid)}" aria-labelledby="wi-{E(cid)}-h"><div class="eb-wi-in">'
            f'<button type="button" class="eb-wi-x" aria-label="Close">✕</button><h2 id="wi-{E(cid)}-h">{E(title)}</h2>'
            + (f'<p class="eb-wi-ln">{E(line)}</p>' if line else '') + body + '</div></dialog>')
def info_button(cid):
    return f'<button type="button" class="sh-i" data-wi="wi-{E(cid)}" aria-label="What’s inside" aria-haspopup="dialog">ⓘ</button>'
_DESC = {}   # full description per card id, read from the book list while the shelf is built
def tidy(t, D):
    """Idempotent: the shop page is header -> shelf -> questions and payment line; details live in each title's info modal."""
    if 'id="sh-css"' not in t: return t
    B = _books(D)
    for sid in ('whats-inside', 'editions', 'versions', 'digital-estate-books'):
        t = re.sub(r'<section\b[^>]*\bid="%s"[^>]*>.*?</section>\s*' % sid, '', t, flags=re.S)
    t = re.sub(r'<p class="sh-ver"[^>]*>.*?</p>', '', t, flags=re.S)
    # Version drop-down (owner 19:21 30 Oct; skills/version-selector-dropdown-label-default.md): a visible "Select a version" label,
    # newest preselected (sv-js selects the first option), each option with its price: "v0.0.2 — £4.99", "v0.0.1 — free".
    t = re.sub(r'(<label class="sv-lab"[^>]*>)Version(</label>)', r'\1Select a version\2', t)
    t = t.replace(' aria-label="Version, latest first"', '')
    def _opt(m):
        price = m.group(2).rsplit('·', 1)[-1].strip() if '·' in m.group(2) else ''
        return f'{m.group(0)[:m.group(0).find(">") + 1]}{m.group(1)}{" — " + price if price else ""}</option>'
    t = re.sub(r'<option value="(v[\d.]+)" data-go="([^"]*)"[^>]*>[^<]*</option>', _opt, t)
    t = re.sub(r'<a\b[^>]*href="#(?:versions|editions|whats-inside)"[^>]*>.*?</a>\s*(?:·\s*)?', '', t, flags=re.S)
    dialogs = []
    bm = re.search(r'<section\b[^>]*\bid="all-four"[^>]*>.*?</section>\s*', t, re.S)
    if bm and 'sh-bundle' not in t:
        sec = bm.group(0); buy = re.search(r'<a\b[^>]*href="(https://buy\.stripe\.com/[^"]+)"', sec)
        bun = ((D or {}).get('bundles') or [{}])[0]; price = bun.get('price') or (re.search(r'£[\d.]+', sec) or [''])[0]
        if buy:
            covs = ''.join(f'<img src="/ebooks/posters/{E(i)}.webp" width="200" height="300" alt="" loading="lazy" decoding="async">'
                           for i in bun.get('books', [])[:4] if (ROOT / 'web' / 'ebooks' / 'posters' / f'{i}.webp').exists())
            page = bun.get('page') or '/ebooks/all-four/'
            card_ = (f'<li class="sh-card sh-bundle" id="all-four-card"><a class="sh-cov sh-bcov" href="{E(page)}" aria-label="All four books">{covs}</a>'
                     f'<div class="sh-th"><h3 class="sh-t"><a href="{E(page)}">All four books</a></h3>{info_button("all-four")}</div>'
                     f'<p class="sh-hook">Four PDFs, one checkout</p><div class="eb-edbox"><a class="sv-go" href="{buy.group(1)}" rel="nofollow">Buy all four · {E(price)}</a></div></li>')
            g = t.find('</ul>', t.find('class="sh-grid"'))
            if g > 0:
                t = t[:g] + card_ + t[g:]
                t = t.replace(sec, '', 1)
                body = re.sub(r'<[^>]+>', '', (re.search(r'<p>(.*?)</p>', sec, re.S) or [None, ''])[1]).strip()
                titles = [B[i]['title'] for i in bun.get('books', []) if i in B]
                inner = ('<ul>' + ''.join(f'<li>{E(x)}</li>' for x in titles) + '</ul>') if titles else ''
                dialogs.append(info_dialog('all-four', 'All four books · ' + price, (f'<p>{E(body)}</p>' if body else '') + inner +
                                           f'<p><a href="{E(page)}">What’s in the bundle</a></p>', ''))
    def add_btn(m):
        li = m.group(0); cid = m.group(1)
        if 'class="sh-i"' in li: return li
        h = re.search(r'<h3 class="sh-t">.*?</h3>', li, re.S)
        if not h: return li
        b = B.get(cid, {}); title = re.sub(r'<[^>]+>', '', h.group(0)).strip()
        body = INSIDE.get(cid)
        if not body:
            d = _DESC.get(cid) or re.sub(r'<[^>]+>', '', (re.search(r'<p class="sh-hook">(.*?)</p>', li, re.S) or [None, ''])[1]).strip()
            body = f'<p>{E(html.unescape(d))}</p>' if d else ''
        if b.get('page') and b['page'].rstrip('/') != '/ebooks': body += f'<p><a href="{E(b["page"])}">The book’s own page</a></p>'
        dialogs.append(info_dialog(cid, title, body, info_line(b)))
        return li[:h.start()] + '<div class="sh-th">' + h.group(0) + info_button(cid) + '</div>' + li[h.end():]
    t = re.sub(r'<li class="sh-card" id="([^"]+)">.*?</li>', add_btn, t, flags=re.S)
    dialogs = [d for d in dialogs if ('id="%s"' % re.search(r'id="(wi-[^"]+)"', d).group(1)) not in t]
    if dialogs:
        at = t.rfind('</main>'); at = at if at >= 0 else t.rfind('</body>')
        t = t[:at] + '<div id="wi-dialogs">' + ''.join(dialogs) + '</div>' + t[at:]
    tm = re.search(r'<p class="eb-trust" id="eb-trust">.*?</p>', t, re.S); sh = t.find('id="shelf"')
    if tm and sh > 0 and tm.start() < sh:   # the payment line goes below the shelf, above the questions
        line = tm.group(0); t = t[:tm.start()] + t[tm.end():]
        at = t.find('<section class="eb-copy" id="faq"')
        if at < 0: at = t.find('</section>', t.find('id="shelf"')) + len('</section>')
        t = t[:at] + line + t[at:]
    if 'id="wi-css"' not in t:
        m = re.search(r'</head\s*>', t, re.I)
        if m: t = t[:m.start()] + WI_CSS + t[m.start():]
    if 'id="wi-js"' not in t:
        at = t.rfind('</body>')
        if at > 0: t = t[:at] + WI_JS + t[at:]
    return t

def run(dist):
    dist = pathlib.Path(dist); p = dist / 'ebooks' / 'index.html'
    if not p.exists(): print('ebook_shelf: no /ebooks/ page'); return
    t = p.read_text(encoding='utf-8', errors='ignore'); o = t
    try: D = json.load(open(ROOT / 'data' / 'ebooks.json', encoding='utf-8'))
    except Exception: D = {'books': []}
    if 'id="sh-css"' in t:
        print('ebook_shelf: shelf already built')
    else:
        pages = {b['id']: b['page'] for b in D.get('books', []) if b.get('page') and b['page'].rstrip('/') not in ('/ebooks', '')
                 and (dist / b['page'].strip('/') / 'index.html').exists()}
        m = re.search(r'<section class="eb-list"[^>]*>(.*?)</section>', t, re.S)
        if not m: print('ebook_shelf: no book list found'); return
        arts = re.findall(r'<article class="eb-card".*?</article>', m.group(1), re.S)
        if not arts: print('ebook_shelf: no cards'); return
        for a in arts:   # the full description goes into the card's info modal
            cid = re.search(r'id="([^"]+)"', a).group(1)
            d = re.search(r'<p class="eb-desc">(.*?)</p>', a, re.S) or re.search(r'<p class="eb-sub">(.*?)</p>', a, re.S)
            if d: _DESC[cid] = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', d.group(1)))).strip()
        shelf = (f'<section class="sh" id="shelf" aria-label="Books" data-shelf-version="{VERSION}">{CSS}<h2 class="sh-h">The books</h2>'
                 f'<ul class="sh-grid">' + ''.join(card(a, pages) for a in arts) + '</ul></section>')
        t = t[:m.start()] + shelf + t[m.end():]
        print('ebook_shelf: cards', len(arts), '; titles linked', sum(1 for a in arts if re.search(r'id="([^"]+)"', a).group(1) in pages))
    t = tidy(t, D)
    if t != o: p.write_text(t, encoding='utf-8')
    print('ebook_shelf: info buttons', t.count('class="sh-i"'), '; dialogs', t.count('<dialog class="eb-wi"'), '; bundle card', 'sh-bundle' in t,
          '; editions/whats-inside/versions left', sum(('id="%s"' % x) in t for x in ('editions', 'whats-inside', 'versions')))
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
