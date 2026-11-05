#!/usr/bin/env python3
"""sections.py - Cedwyn as two sections over one database (Sion, 12:06 GMT 25 Oct 2026). - Sion's Tab agent
- /            the landing: two tiles, WALES (the Llandough augmented-reality tour) and ARGENTINA (Great House II).
- /explore/    the oak board (the former home, tools/home.py), unchanged.
- /wales/      the Wales hub: the AR guided tour (coming soon), vouchers / e-books / merch, seek-disclose-research-reconstruct.
               The former "Virtual Tour · Wales" theme home is retired (26 Oct 2026); /wales/tour/ 301s to /wales/#stop-1.
- /argentina/  the Argentina hub: Great House II, former courthouse / coach house, Puerto Madryn (coming soon), the museum
               plans and the retelling.
- /wales/<theme>/... and /argentina/<theme>/... serve the SAME theme files through Pages rewrites (_redirects, status 200):
  no theme file, record or blob is copied. runtime.js reads the section from the address and loads section.js (ribbon,
  default language, links kept in the section). Old /<theme>/ addresses keep working as before.
Copy: sections.json (en / cy / es). Called at the end of site.py."""
import json, html, re, shutil, pathlib, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
E = html.escape
BOOT = '/_cedwyn/ghf/ghf-boot.js?v=2.1.19'
SJS = '/_cedwyn/section.js?v=1.2.0'
ICON_AR = ('<svg class="ar-ic" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><g fill="none" stroke="currentColor" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">'
           '<path d="M6 34c0-3 2-5 5-5h42c3 0 5 2 5 5v8c0 4-3 7-7 7H43l-5-6H26l-5 6H13c-4 0-7-3-7-7z"/>'
           '<path d="M20 22 32 12l12 10" stroke-dasharray="3 4"/><path d="M23 22v6M29 22v6M35 22v6M41 22v6" stroke-dasharray="2 3"/>'
           '<rect x="12" y="35" width="15" height="8" rx="3"/><rect x="37" y="35" width="15" height="8" rx="3"/></g></svg>')

CSS = r"""
:root{color-scheme:dark;--bg:#07090b;--fg:#f4f4f2;--mut:#b8bcc0;--card:#12161a;--line:rgba(255,255,255,.16);--a:#00843D;--b:#C8102E}
html[data-ghf-mode=day]{color-scheme:light;--bg:#f6f5f1;--fg:#121417;--mut:#4a5056;--card:#ffffff;--line:rgba(0,0,0,.14)}
*{box-sizing:border-box}html{background:var(--bg)}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 Barlow,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:inherit}a:focus-visible,button:focus-visible,summary:focus-visible,input:focus-visible{outline:2px solid var(--b);outline-offset:3px}
.wrap{width:min(1100px,100%);margin:0 auto;padding:18px 16px 40px}
.eyebrow{margin:6px 0 4px;color:var(--mut);font:600 12px/1.4 Barlow,system-ui,sans-serif;letter-spacing:.22em;text-transform:uppercase}
h1{margin:0;font:300 clamp(34px,8vw,64px)/1.05 Barlow,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase}
h2{margin:0 0 8px;font:400 clamp(21px,4.6vw,30px)/1.2 Barlow,system-ui,sans-serif;letter-spacing:.05em;text-transform:uppercase}
h3{margin:0 0 4px;font:600 17px/1.3 Barlow,system-ui,sans-serif}
p{margin:0 0 12px}.mut{color:var(--mut)}.lede{font-size:18px;max-width:46em}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;margin:2px 0 14px}
.langs{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}
.langs button,.mode{font:600 12px/1 Barlow,system-ui,sans-serif;letter-spacing:.08em;color:var(--fg);background:none;border:0;padding:10px 12px;min-height:40px;cursor:pointer}
.langs button[aria-pressed=true]{background:var(--fg);color:var(--bg)}
.ghf-v2-loc:has(.ghf-lang.ghf-open){overflow:visible!important}.ghf-v2-lang .ghf-lang.ghf-up .ghf-lang-menu{top:calc(100% + 6px)!important;bottom:auto!important}.ghf-v2-lang .ghf-lang.ghf-left .ghf-lang-menu{left:auto!important;right:0!important}.ghf-v2-sp{display:none!important}
.mode{border:1px solid var(--line);border-radius:999px;display:inline-flex;gap:6px;align-items:center}
.soon{display:inline-block;margin:0 0 8px;padding:4px 10px;border-radius:999px;border:1px solid currentColor;font:600 11px/1.2 Barlow,system-ui,sans-serif;letter-spacing:.16em;text-transform:uppercase}
.tiles{display:grid;gap:14px;margin:14px 0 18px}
@media (min-width:783px){.tiles{grid-template-columns:1fr 1fr}}
.tile{position:relative;display:flex;flex-direction:column;justify-content:flex-end;min-height:min(62vh,440px);border-radius:14px;overflow:hidden;text-decoration:none;color:#fff;isolation:isolate;box-shadow:0 10px 30px rgba(0,0,0,.35)}
.tile .tl-body{position:relative;z-index:2;padding:16px 16px 18px;background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.72) 32%,rgba(0,0,0,.86))}
.tile .tl-name{display:block;font:300 clamp(40px,11vw,62px)/1 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.tile .tl-line{display:block;font:500 17px/1.35 Barlow,system-ui,sans-serif;margin:6px 0 2px}.tile .tl-sub{display:block;font-size:14px;opacity:.88}
.tile .tl-cta{display:inline-flex;align-items:center;gap:8px;margin-top:12px;padding:10px 16px;border:1px solid rgba(255,255,255,.8);border-radius:999px;font:600 13px/1 Barlow,system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase}
.tile:hover .tl-cta,.tile:focus-visible .tl-cta{background:#fff;color:#000}
.t-wales{background:linear-gradient(180deg,#fff 0,#fff 50%,#00843D 50%,#00843D 100%)}
.t-wales .ar-wrap{position:absolute;inset:0 0 auto 0;height:62%;display:grid;place-items:center;z-index:1}
.t-wales .ar-disc{width:min(44vw,170px);height:min(44vw,170px);border-radius:50%;display:grid;place-items:center;background:#C8102E;color:#fff;box-shadow:0 0 0 6px #fff,0 0 0 8px #C8102E,0 14px 30px rgba(0,0,0,.35)}
.ar-ic{width:66%;height:66%}
.t-arg{background:#4E8CC8}.t-arg img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0}
.t-arg:before{content:"";position:absolute;left:0;right:0;top:0;height:10px;z-index:2;background:linear-gradient(180deg,#74ACDF 0 33%,#fff 33% 66%,#74ACDF 66%)}
.cap{font-size:12px;color:var(--mut);margin:-8px 0 14px}
.links{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0 12px}
.btn{display:inline-flex;align-items:center;min-height:42px;padding:9px 16px;border:1px solid var(--line);border-radius:999px;text-decoration:none;font:600 13px/1.2 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;background:var(--card)}
.btn:hover{border-color:var(--b)}
.search{display:flex;gap:6px;margin:4px 0 16px}.search input{flex:1;min-width:0;padding:12px;border-radius:10px;border:1px solid var(--line);background:var(--card);color:var(--fg);font:inherit}
.search button{padding:0 16px;border-radius:10px;border:1px solid var(--line);background:var(--fg);color:var(--bg);font:600 13px/1 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase;cursor:pointer}
.hero{position:relative;margin:0 -16px 18px;padding:26px 16px 22px;border-bottom:4px solid var(--b);background:linear-gradient(180deg,rgba(255,255,255,.04),rgba(255,255,255,0));overflow:hidden}
.hero .flag{position:absolute;inset:0 0 auto 0;height:8px;background:linear-gradient(90deg,var(--a) 0 50%,var(--b) 50%)}
.hero-row{display:flex;gap:14px;align-items:center}.hero .ar-disc{flex:0 0 auto;width:74px;height:74px;border-radius:50%;display:grid;place-items:center;background:#C8102E;color:#fff;box-shadow:0 0 0 4px #fff,0 0 0 6px var(--a)}
.hero-photo{position:relative;margin:0 -16px 6px;height:min(56vw,360px);overflow:hidden}.hero-photo img{width:100%;height:100%;object-fit:cover;display:block}
.hero-photo:after{content:"";position:absolute;inset:auto 0 0 0;height:50%;background:linear-gradient(180deg,rgba(0,0,0,0),var(--bg))}
section.blk{margin:26px 0;padding-top:18px;border-top:1px solid var(--line)}
.fig{margin:4px 0 12px}.fig img{width:100%;height:auto;display:block;border-radius:12px}.fig figcaption{font-size:12px;color:var(--mut);margin-top:6px}
.stops{list-style:none;margin:8px 0;padding:0;display:grid;gap:8px}
@media (min-width:783px){.stops{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}}
.stop{display:flex;gap:12px;align-items:flex-start;padding:12px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.stop .n{flex:0 0 auto;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:var(--a);color:#fff;font:600 14px/1 Barlow,system-ui,sans-serif}
.stop p{margin:2px 0 6px;font-size:14px;color:var(--mut)}.stop a{font-size:13px;font-weight:600}
.tag{display:inline-block;font:600 10px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;border:1px solid var(--line);border-radius:4px;padding:2px 6px;margin-left:4px;color:var(--mut)}
.cards{display:grid;gap:10px;margin:8px 0}@media (min-width:783px){.cards{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}}
.card{padding:14px;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.card .soon{color:var(--b)}
details.nt summary{cursor:pointer;display:inline-flex;align-items:center;min-height:40px;padding:8px 14px;border:1px solid var(--line);border-radius:999px;font:600 12px/1 Barlow,system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;list-style:none}
details.nt summary::-webkit-details-marker{display:none}
form.cn{margin:10px 0 0}form.cn input[type=email]{width:100%;padding:11px;border-radius:10px;border:1px solid var(--line);background:transparent;color:inherit;font:inherit}
form.cn label.ck{display:flex;gap:10px;align-items:flex-start;font-size:13px;margin:10px 0}form.cn label.ck input{width:20px;height:20px;flex:0 0 auto;margin-top:1px}
form.cn button{min-height:40px;padding:8px 16px;border-radius:999px;border:1px solid currentColor;background:none;color:inherit;font:600 12px/1 Barlow,system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;cursor:pointer}
.cn-err{color:var(--b);font-size:13px;margin:8px 0 0}.cn-done{font-size:14px}
ul.plain{margin:6px 0 12px;padding-left:20px}ul.plain li{margin:6px 0}
.grp{margin:10px 0;border:1px solid var(--line);border-radius:12px;background:var(--card)}
.grp summary{cursor:pointer;padding:12px 14px;font:600 14px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;display:flex;justify-content:space-between;gap:10px}
.grp ol{margin:0;padding:0 14px 12px 36px}.grp li{margin:7px 0}.grp li a{text-decoration:none;border-bottom:1px solid var(--line)}
.cross{display:block;padding:16px;border-radius:12px;text-decoration:none;background:var(--card);border:1px solid var(--line);border-left:6px solid var(--b)}
img[data-patagonia-pencil]{filter:url(#patagonia-pencil) sepia(.10) contrast(1.05)}
.cross h2{font-size:20px}.endnote{font-size:12px;color:var(--mut);margin-top:24px}
"""

PENCIL_DEFS = """<svg xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false" width="0" height="0" style="position:absolute;overflow:hidden;pointer-events:none">
<filter id="patagonia-pencil" color-interpolation-filters="sRGB" x="-5%" y="-5%" width="110%" height="110%">
<feColorMatrix in="SourceGraphic" type="saturate" values="0" result="mono"/>
<feGaussianBlur in="mono" stdDeviation="2.1" result="soft-mono"/>
<feComponentTransfer in="soft-mono" result="inverted-soft">
<feFuncR type="table" tableValues="1 0"/><feFuncG type="table" tableValues="1 0"/><feFuncB type="table" tableValues="1 0"/>
</feComponentTransfer>
<feBlend in="mono" in2="inverted-soft" mode="color-dodge" result="pencil-lines"/>
<feTurbulence type="fractalNoise" baseFrequency="0.82" numOctaves="2" seed="8" result="paper-grain"/>
<feColorMatrix in="paper-grain" type="saturate" values="0" result="grain-gray"/>
<feComponentTransfer in="grain-gray" result="fine-grain"><feFuncA type="table" tableValues="0 0.045"/></feComponentTransfer>
<feBlend in="pencil-lines" in2="fine-grain" mode="multiply"/>
</filter></svg>"""

def tx(T, k, l):
    v = T.get(k) or {}
    return v.get(l) or v.get('en') or ''

def i18n(T, k, l, tag='span', attrs='', n=None):
    s = tx(T, k, l)
    if n is not None: s = s.replace('{n}', str(n))
    return f'<{tag} data-i18n="{E(k)}"{attrs}>{E(s)}</{tag}>'

def head(title, desc, lang, bpath, sec, T, n):
    sec_attrs = f' data-cedwyn-sec="{sec}" data-cedwyn-sec-url="{sec}" data-ghf-lang-default="{lang}"' if sec else ''
    html_lang = 'en-GB' if lang == 'en' else lang
    return f"""<!doctype html>
<html lang="{html_lang}" data-ghf-host="bucklerfamily.estate" data-ghf-path="{bpath}" data-ghf-native="auto" data-cedwyn-n="{n}"{sec_attrs}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<script>window.CEDWYN_T={json.dumps(T, ensure_ascii=False)};window.__cedwynLP="/";{"try{sessionStorage.setItem('cedwyn-sec','"+sec+"')}catch(e){}" if sec else ""}</script>
<style>{CSS}</style>
<script src="{BOOT}"></script>
<script src="{SJS}" defer></script>
</head>"""

def langbar(T, l):
    # Sion 25 Oct 14:07: one language selector only, the header's top-right one (cy/en/es, remembered; Wales cy / Argentina es
    # defaults come from data-ghf-lang-default). The page's own CY/EN/ES row is gone; the day/night toggle stays.
    return (f'<div class="bar" data-no-translate>'
            f'<button class="mode" data-ghf-mode-toggle type="button">{E(tx(T,"mode",l))}</button></div>')

def notify(T, l, key, consent, n):
    return (f'<details class="nt"><summary data-i18n="notify">{E(tx(T,"notify",l))}</summary>'
            f'<form class="cn" data-cedwyn-notify="{key}" novalidate><label class="mut" for="cn-{n}" data-i18n="email">{E(tx(T,"email",l))}</label>'
            f'<input id="cn-{n}" type="email" name="EMAIL" autocomplete="email" required placeholder="you@example.com">'
            f'<label class="ck"><input type="checkbox" class="cn-ok"><span><span data-i18n="{consent}">{E(tx(T,consent,l))}</span> <a href="/dartboard/legal/" data-i18n="privacy">{E(tx(T,"privacy",l))}</a></span></label>'
            f'<button type="submit" data-i18n="notify">{E(tx(T,"notify",l))}</button><p class="cn-err" role="alert" hidden></p></form>'
            f'<p class="cn-done" role="status" hidden data-i18n="thanks">{E(tx(T,"thanks",l))}</p></details>')

def layers(cfg, T, l, sec, amap):
    n = len(cfg['themes']); pos = {t['id']: i + 1 for i, t in enumerate(cfg['themes'])}
    out = [f'<section class="blk" id="layers"><h2>{i18n(T,"layers_h",l,n=n)}</h2><p class="mut">{i18n(T,"layers_p",l)}</p>']
    for g in cfg.get('groups', []):
        ts = [t for t in cfg['themes'] if (t.get('group') or cfg.get('default_group')) == g['id']]
        if not ts: continue
        items = ''.join(f'<li value="{pos[t["id"]]}"><a href="/{sec}/{E(t["id"])}/" data-i18n="th_{E(t["id"])}">{E(tx(T,"th_"+t["id"],l))}</a></li>' for t in ts)
        out.append(f'<details class="grp"><summary><span data-i18n="g_{E(g["id"])}">{E(tx(T,"g_"+g["id"],l))}</span><span class="mut">{len(ts)}</span></summary><ol>{items}</ol></details>')
    out.append('</section>')
    return ''.join(out)

def ebook_prices():
    try:
        D = json.load(open(ROOT / 'data' / 'ebooks.json', encoding='utf-8'))
        p2 = next((b['price'] for b in D['books'] if b['edition'] == 'v0.0.2'), '£4.99'); pb = (D.get('bundles') or [{}])[0].get('price', '')
        return p2, pb
    except Exception:
        return None, None

def page_t(S, cfg, sec):
    T = {k: v for k, v in S['t'].items() if sec == 'argentina' or not re.match(r'^(re\d|mu\d|mu_h|c\d)', k)}; amap = S.get('argentina_title_map', {}) if sec == 'argentina' else {}
    for t in cfg['themes']:
        v = {'en': t.get('title') or t['id'], 'cy': t.get('cy') or t.get('title'), 'es': t.get('es') or t.get('title')}
        T['th_' + t['id']] = {k: amap.get(x, x) for k, x in v.items()}
    p2, pb = ebook_prices()
    if p2 and 'e_ed' in T: T['e_ed'] = {k: v.replace('{p2}', p2).replace('{pb}', pb) for k, v in T['e_ed'].items()}
    elif 'e_ed' in T: del T['e_ed']
    for g in cfg.get('groups', []):
        T['g_' + g['id']] = {'en': g.get('title'), 'cy': g.get('cy') or g.get('title'), 'es': g.get('es') or g.get('title')}
    return T

def footer_note(T, l):
    return ''

def landing(S, cfg):
    l = 'en'; n = len(cfg['themes']); T = page_t(S, cfg, None); ph = S['photo']
    return head('Cedwyn · Wales and Argentina', 'Cedwyn: one archive of the Great House at Llandough, two ways in: Wales, with an augmented-reality tour of Llandough (coming soon), and Argentina, with Great House II in Puerto Madryn (coming soon).', l, '/cedwyn/home/', None, T, n) + f"""
<body data-cedwyn-page="landing">
<main class="wrap" data-no-translate>
{langbar(T, l)}
<p class="eyebrow">{i18n(T,'land_eyebrow',l)}</p>
<h1>Cedwyn</h1>
<p class="lede" style="margin-top:10px">{i18n(T,'land_lede',l)}</p>
<div class="tiles">
<a class="tile t-wales" href="/wales/" lang="cy"><span class="ar-wrap"><span class="ar-disc">{ICON_AR}</span></span>
<span class="tl-body"><span class="soon" data-i18n="soon">{E(tx(T,'soon',l))}</span><span class="tl-name" data-i18n="w_name">{E(tx(T,'w_name',l))}</span>
<span class="tl-line" data-i18n="w_tile">{E(tx(T,'w_tile',l))}</span><span class="tl-cta"><span data-i18n="w_cta">{E(tx(T,'w_cta',l))}</span> →</span></span></a>
<a class="tile t-arg" href="/argentina/" lang="es"><img src="{E(ph['src'])}" width="{ph['w']}" height="{ph['h']}" alt="" loading="eager" decoding="async">
<span class="tl-body"><span class="soon" data-i18n="soon">{E(tx(T,'soon',l))}</span><span class="tl-name" data-i18n="a_name">{E(tx(T,'a_name',l))}</span>
<span class="tl-line" data-i18n="a_tile">{E(tx(T,'a_tile',l))}</span><span class="tl-sub" data-i18n="a_tile2">{E(tx(T,'a_tile2',l))}</span>
<span class="tl-cta"><span data-i18n="a_cta">{E(tx(T,'a_cta',l))}</span> →</span></span></a>
</div>
<p class="cap" data-i18n="photo_cap">{E(tx(T,'photo_cap',l))}</p>
<form class="search" action="/catalogue/" role="search"><input name="q" data-i18n-ph="search_ph" data-i18n-al="search_ph" placeholder="{E(tx(T,'search_ph',l))}" aria-label="{E(tx(T,'search_ph',l))}"><button data-i18n="search">{E(tx(T,'search',l))}</button></form>
<div class="links"><a class="btn" href="/explore/" data-i18n="explore">{E(tx(T,'explore',l).replace('{n}',str(n)))}</a><a class="btn" href="/values/">Values &amp; Standards</a></div>
</main>
</body>
</html>
"""

def wales(S, cfg):
    l = 'cy'; n = len(cfg['themes']); T = page_t(S, cfg, 'wales')
    stops = [('s1', 's1n', 'roman villa', None), ('s2', 's2n', 'roundhouse', None), ('s3', 's3n', 'monastery', None), ('s4', 's4n', 'courthouse', 'tag_family'), ('s5', 's5n', 'marconi', 'tag_record')]
    st = ''.join(f'<li class="stop"><span class="n">{i+1}</span><div><h3>{i18n(T,a,l)}' + (f' <span class="tag" data-i18n="{tg}">{E(tx(T,tg,l))}</span>' if tg else '') +
                 f'</h3><p data-i18n="{b}">{E(tx(T,b,l))}</p><a href="/catalogue/?q={urllib.parse.quote(q)}"><span data-i18n="records">{E(tx(T,"records",l))}</span> →</a></div></li>'
                 for i, (a, b, q, tg) in enumerate(stops))
    links = [('l_timeline', '/wales/research/timeline/'), ('l_cuts', '/wales/thousand-cuts/'), ('l_story', '/wales/story/'), ('l_research', '/wales/research/'),
             ('l_foi', '/wales/wdtk/'), ('l_docs', '/wales/docs/'), ('l_projects', '/wales/projects/')]
    lk = ''.join(f'<li><a href="{u}" data-i18n="{k}">{E(tx(T,k,l))}</a></li>' for k, u in links)
    return head('Cymru · Wales · Cedwyn', 'Wales: the Llandough augmented-reality guided tour (coming soon), gift vouchers, e-books and merch, and the record gathered piece by piece.', l, '/wales/', 'wales', T, n) + f"""
<body data-cedwyn-page="wales">
<main class="wrap" data-no-translate>
{langbar(T, l)}
<header class="hero"><span class="flag" aria-hidden="true"></span><div class="hero-row"><span class="ar-disc">{ICON_AR}</span><div>
<p class="eyebrow">{i18n(T,'w_kicker',l)}</p><h1 data-i18n="w_name">{E(tx(T,'w_name',l))}</h1></div></div></header>
<section id="tour"><span class="soon" data-i18n="soon">{E(tx(T,'soon',l))}</span><h2>{i18n(T,'w_tour_h',l)}</h2><p class="lede">{i18n(T,'w_tour_p',l)}</p>
<figure class="fig"><img src="/dartboard/locations-img/wales-ar-tour-wide.webp" width="1600" height="907" alt="{E(tx(T,'w_tour_img',l))}" data-i18n-al="w_tour_img" loading="lazy" decoding="async"><figcaption data-i18n="w_tour_img">{E(tx(T,'w_tour_img',l))}</figcaption></figure>
<h3 data-i18n="w_stops_h">{E(tx(T,'w_stops_h',l))}</h3><p class="mut" data-i18n="w_stops_p">{E(tx(T,'w_stops_p',l))}</p><ol class="stops">{st}</ol></section>
<section class="blk" id="shop"><h2>{i18n(T,'w_shop_h',l)}</h2><div class="cards">
<div class="card"><span class="soon" data-i18n="soon">{E(tx(T,'soon',l))}</span><h3 data-i18n="v_h">{E(tx(T,'v_h',l))}</h3><p data-i18n="v_p">{E(tx(T,'v_p',l))}</p>{notify(T,l,'wales-vouchers','consent_vouchers',1)}</div>
<div class="card"><h3 data-i18n="e_h">{E(tx(T,'e_h',l))}</h3><p data-i18n="e_p">{E(tx(T,'e_p',l))}</p>{('<p class="mut" data-i18n="e_ed">' + E(tx(T,'e_ed',l)) + '</p>') if 'e_ed' in T else ''}<a class="btn" href="/ebooks/" data-i18n="e_cta">{E(tx(T,'e_cta',l))}</a></div>
<div class="card"><span class="soon" data-i18n="soon">{E(tx(T,'soon',l))}</span><h3 data-i18n="m_h">{E(tx(T,'m_h',l))}</h3><p data-i18n="m_p">{E(tx(T,'m_p',l))}</p>{notify(T,l,'wales-merch','consent_merch',2)}</div>
</div></section>
<section class="blk" id="story"><h2>{i18n(T,'w_story_h',l)}</h2><p>{i18n(T,'w_story_p',l)}</p><ul class="plain">{lk}</ul></section>
<section class="blk"><a class="cross" href="/argentina/" lang="es"><h2>{i18n(T,'w_cross_h',l)}</h2><p class="mut">{i18n(T,'w_cross_p',l)}</p></a></section>
{layers(cfg, T, l, 'wales', {})}
<p class="endnote"><a href="/" data-i18n="home">{E(tx(T,'home',l))}</a> · <a href="/explore/" data-i18n="explore">{E(tx(T,'explore',l).replace('{n}',str(n)))}</a></p>
</main>
</body>
</html>
"""

def argentina(S, cfg):
    l = 'es'; n = len(cfg['themes']); T = page_t(S, cfg, 'argentina'); ph = S['photo']
    # The family's case (Sion 23:07 GMT 25 Oct 2026): its own page at /argentina/caso/ (tools/family_case.py); the hub links to it
    import family_case
    T.update(family_case.strings()[0])
    cards = ''.join(f'<div class="card"><span class="soon" data-i18n="soon">{E(tx(T,"soon",l))}</span><h3 data-i18n="{a}">{E(tx(T,a,l))}</h3><p data-i18n="{b}">{E(tx(T,b,l))}</p></div>'
                    for a, b in (('c1', 'c1n'), ('c2', 'c2n'), ('c3', 'c3n'), ('c4', 'c4n')))
    links = [('l_story', '/argentina/story/'), ('l_cuts', '/argentina/thousand-cuts/'), ('l_timeline', '/argentina/research/timeline/'), ('l_meeting', '/argentina/meeting/'),
             ('l_fcg', '/argentina/fcg/'), ('l_oldbill', '/argentina/oldbill/'), ('l_museum', '/argentina/patagonia/')]
    lk = ''.join(f'<li><a href="{u}" data-i18n="{k}">{E(tx(T,k,l))}</a></li>' for k, u in links)
    return head('Great House II · Argentina · Cedwyn', 'Argentina: Great House II, former courthouse / coach house, a replica on a Cedwyn II estate in Puerto Madryn, Patagonia (coming soon): B&B, wedding venue, stables and museum, and the story retold.', l, '/patagonia/', 'argentina', T, n).replace('--a:#00843D;--b:#C8102E', '--a:#4E8CC8;--b:#F6B40E') + f"""
<body data-cedwyn-page="argentina">
{PENCIL_DEFS}
<main class="wrap" data-no-translate>
{langbar(T, l)}
<div class="hero-photo"><img data-patagonia-pencil src="{E(ph['src'])}" width="{ph['w']}" height="{ph['h']}" alt="" decoding="async"></div>
<p class="cap" data-i18n="photo_cap">{E(tx(T,'photo_cap',l))}</p>
<header><p class="eyebrow">{i18n(T,'a_kicker',l)}</p><h1>Great House II</h1><p class="lede" style="margin-top:6px"><b data-i18n="a_sub">{E(tx(T,'a_sub',l))}</b></p>
<span class="soon" data-i18n="soon">{E(tx(T,'soon',l))}</span><p class="lede">{i18n(T,'a_lede',l)}</p></header>
<a class="cross" href="/argentina/caso/" style="margin:4px 0 14px"><h2>{i18n(T,'fc_link_h',l)}</h2><p class="mut">{i18n(T,'fc_link_p',l)}</p></a>
<div class="cards">{cards}</div>
<div class="card" style="margin-top:10px"><h3 data-i18n="a_notify_h">{E(tx(T,'a_notify_h',l))}</h3>{notify(T,l,'argentina-opening','consent_arg',3)}</div>
<section class="blk" id="museum"><h2>{i18n(T,'mu_h',l)}</h2><ul class="plain"><li data-i18n="mu1">{E(tx(T,'mu1',l))}</li><li data-i18n="mu2">{E(tx(T,'mu2',l))}</li><li data-i18n="mu3">{E(tx(T,'mu3',l))}</li></ul></section>
<section class="blk" id="retelling"><h2>{i18n(T,'re_h',l)}</h2><p>{i18n(T,'re1',l)}</p><p>{i18n(T,'re2',l)}</p><p class="mut">{i18n(T,'re3',l)}</p><ul class="plain">{lk}</ul></section>
<section class="blk"><a class="cross" href="/wales/" lang="cy"><h2>{i18n(T,'a_cross_h',l)}</h2><p class="mut">{i18n(T,'a_cross_p',l)}</p></a></section>
{layers(cfg, T, l, 'argentina', S.get('argentina_title_map', {}))}
<p class="endnote"><a href="/" data-i18n="home">{E(tx(T,'home',l))}</a> · <a href="/explore/" data-i18n="explore">{E(tx(T,'explore',l).replace('{n}',str(n)))}</a></p>
</main>
</body>
</html>
"""

WALES_BANNED = ['says', 'claims', 'according to', 'hearsay', 'unverified', 'alleged', 'fraud', 'stolen']

def check_wales(text):
    """the page's own visible copy (<main>) carries none of the banned words (the agent footer's Trigger Event notice is the stated exception)"""
    m = re.search(r'<main\b.*?</main>', text, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', m.group(0) if m else text)
    bad = [w for w in WALES_BANNED if re.search(r'\b' + re.escape(w) + r'\b', body, re.I)]
    assert not bad, 'wales/landing page carries banned words: %s' % bad

def run(dist, cfg):
    dist = pathlib.Path(dist)
    S = json.load(open(ROOT / 'sections.json', encoding='utf-8'))
    tids = [t['id'] for t in cfg['themes']]
    # 1. the oak board moves to /explore/ (same file)
    ex = dist / 'explore'; ex.mkdir(exist_ok=True)
    shutil.move(str(dist / 'index.html'), str(ex / 'index.html'))
    # 2. the former Virtual Tour · Wales home is retired (Sion 08:08 GMT 26 Oct 2026: "Purge the former, keep the latter"):
    #    the hub's tour (/wales/#stop-1) replaces it and old links 301 there (rules below). The theme's other files
    #    (/wales/vouchers/terms/, favicons) stay; a copy kept from an earlier build (keep_previous) is removed too.
    shutil.rmtree(dist / 'wales' / 'tour', ignore_errors=True)
    if (dist / 'wales' / 'index.html').exists(): (dist / 'wales' / 'index.html').unlink()
    # 3. landing and hubs
    (dist / 'index.html').write_text(landing(S, cfg), encoding='utf-8')
    (dist / 'wales').mkdir(exist_ok=True)
    (dist / 'wales' / 'index.html').write_text(wales(S, cfg), encoding='utf-8')
    (dist / 'argentina').mkdir(exist_ok=True)
    (dist / 'argentina' / 'index.html').write_text(argentina(S, cfg), encoding='utf-8')
    import agent_footer, sys as _sys, family_case
    fc_page = family_case.write(_sys.modules[__name__], dist, S, cfg)   # /argentina/caso/ (via /argentina/:theme/* -> /caso/)
    for pth in (dist / 'index.html', dist / 'wales' / 'index.html', dist / 'argentina' / 'index.html', fc_page): agent_footer.inject(pth, False)
    check_wales((dist / 'wales' / 'index.html').read_text(encoding='utf-8'))
    check_wales((dist / 'index.html').read_text(encoding='utf-8'))
    # 4. scripts: section.js gets the ribbon/footer strings and the theme ids; runtime.js the client-router list; basecamp.js the Argentina names
    keys = ['rib_w', 'rib_a', 'rib_v', 'rib_e', 'rib_mu', 'rib_re', 'rib_close', 'w_name', 'a_name', 'f_log', 'f_cur', 'f_proto']
    sj = dist / '_cedwyn' / 'section.js'
    sj.write_text(sj.read_text(encoding='utf-8').replace('/*SECTION_T*/{}', json.dumps({k: S['t'][k] for k in keys}, ensure_ascii=False))
                  .replace('/*SECTION_THEMES*/[]', json.dumps(tids)), encoding='utf-8')
    rt = dist / '_cedwyn' / 'runtime.js'
    rt.write_text(rt.read_text(encoding='utf-8').replace('__SECTION_SPA__', json.dumps(S.get('spa', []))), encoding='utf-8')
    bc = dist / '_cedwyn' / 'ghf' / 'basecamp.js'
    bc.write_text(bc.read_text(encoding='utf-8').replace('/*CEDWYN_AMAP*/null', json.dumps(S.get('argentina_title_map', {}), ensure_ascii=False)), encoding='utf-8')
    # 5. _redirects: section rewrites first (first match wins). Wales lists each theme (the /wales/ folder also holds the
    #    former Wales theme's own files); Argentina has no folder of its own, so one placeholder rule covers every theme.
    # Keep section rewrites equivalent without allocating one dynamic rule per theme.
    # Specific legacy routes must precede the generic parameterised routes (first match wins).
    sec = [
        '/wales/tour /wales/#stop-1 301', '/wales/tour/ /wales/#stop-1 301',
        '/wales/tour/* /wales/#stop-1 301',
        '/wales/emails /emails/ 301', '/wales/emails/ /emails/ 301',
        '/wales/emails/* /emails/:splat 301',
        '/wales/wales/ /wales/#stop-1 301', '/argentina/wales/ /wales/#stop-1 301',
        '/wales/wales/* /wales/:splat 200',
        '/wales/movie/* /documentary/:splat 301',
        '/argentina/movie/* /documentary/:splat 301',
        '/wales/:theme/* /:theme/:splat 200',
        '/argentina/:theme/* /:theme/:splat 200'
    ]
    rd = dist / '_redirects'
    old = rd.read_text().splitlines() if rd.exists() else []
    is_dynamic = lambda x: bool(x.split()) and ('*' in x.split()[0] or ':' in x.split()[0])
    dyn_old = [x for x in old if is_dynamic(x)]
    dyn_sec = [x for x in sec if is_dynamic(x)]
    assert len(dyn_old) + len(dyn_sec) <= 100, 'Pages allows 100 dynamic redirects'
    rd.write_text('\n'.join(sec + old) + '\n')
    print('sections ok:', len(sec), 'section rewrites (', len(dyn_sec), 'dynamic );', len(dyn_old), 'other dynamic rules')

if __name__ == '__main__':
    import sys
    run(sys.argv[1] if len(sys.argv) > 1 else 'dist', json.load(open(ROOT / 'themes.json')))
