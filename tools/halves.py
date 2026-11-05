#!/usr/bin/env python3
"""halves.py - Cedwyn in two halves (Sion, 23:39 GMT 25 Oct 2026, m:2a7c8c27). - Sion's Tab agent
- /            two tiles that fit the first screen (390x844 and desktop): "Cedwyn Estate, Wales" (the AR-headset tour image) and
               "Cedwyn Estate II, Patagonia" (the house regenerated as new). Opens in English unless the visitor picked a language on
               this page this visit; the Wales tile opens Welsh (?lang=cy), the Patagonia tile Spanish (?lang=es). One language
               selector: the header's, top right.
- /wales/      the augmented-reality guided tour of Cedwyn Estate, Wales: eight stops (map, AR view, narration, records with EV links,
               prev/next, read-aloud). Tŷ Mawr is the former manorial house (never "farm" on this half). No museum stop. Tickets are
               not on sale: gift-voucher pre-order (#vouchers in #shop, the existing Stripe voucher flow). Menu: every theme, grouped
               Past / Present (data/halves.json "groups"; a new theme falls into "default"); the museum themes are left out on Wales.
- /argentina/  Cedwyn Estate II / Great House II, Patagonia: the retreat (house, rooms, stables, barn, cottage, weddings, museum with
               wax Marconi and "Peerless" Jim), a BookMyTravel-style package builder (stay + flights + hire car -> summary ->
               pre-order request sent to Cedwyn's own mailing list, where the visitor confirms by email; indicative prices; nothing charged), the family's
               case (tools/family_case.py, when present) and every theme grouped Past / Present.
Copy: data/halves.json (en/cy/es; Welsh and Spanish are first drafts). Images: web/_cedwyn/halves/img/ (AI renders marked
"artist's impression"). Runs at the end of site.py, after sections.run(); it replaces the three pages sections.py wrote and nothing else."""
import json, html, re, pathlib, math
ROOT = pathlib.Path(__file__).resolve().parent.parent
E = html.escape
VERSION = '1.3.0'
# 1.2.1 (27 Oct 2026, Sion 11:34 GMT): /argentina/ pictures purged of four pieces that are not the farm (NFA-0139, NFA-0049,
# NFA-0103, NFA-0081); NFA-0015 replaced by REC-0001, a line drawing from the 1974 measured survey (see ARG_REC). - Sion's Tab agent
# 1.2.0 (27 Oct 2026, Sion 09:45 GMT): the in-content pictures of /wales/ and /argentina/ are thumbnails; a tap opens the shared
# full-screen viewer (web/_cedwyn/halves/lb.js + lb.css): full width, the picture's own title as caption, swipe / arrows loop
# round every picture on the page, Escape / X / swipe down / backdrop closes. The landing page is unchanged. - Sion's Tab agent
LB_CSS = '<link rel="stylesheet" href="/_cedwyn/halves/lb.css?v=1.0.0">'
LB_JS = '<script src="/_cedwyn/halves/lb.js?v=1.0.0" defer></script>'

def tx(T, k, l):
    v = T.get(k) or {}
    return v.get(l) or v.get('en') or ''

def sp(T, k, l, tag='span', cls='', extra=''):
    c = f' class="{cls}"' if cls else ''
    return f'<{tag} data-i18n="{E(k)}"{c}{extra}>{E(tx(T, k, l))}</{tag}>'

def lt(T, d, l, key, tag='span', cls=''):
    """an inline {en,cy,es} object registered under key"""
    T[key] = d
    return sp(T, key, l, tag, cls)

CSS = r"""
.hv{--hv-a:#00843D;--hv-b:#C8102E}
.hv-tag{position:absolute;right:8px;bottom:8px;z-index:3;padding:3px 8px;border-radius:999px;background:rgba(0,0,0,.62);color:#fff;font:600 10.5px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.06em}
.hv img{max-width:100%;height:auto;display:block}
/* landing */
body[data-cedwyn-page=landing] .wrap{padding-top:6px;padding-bottom:6px}
.hv-land{display:flex;flex-direction:column;gap:8px;height:calc(100svh - var(--hv-top,96px));min-height:420px}
.hv-land .eyebrow{margin:0}
.hv-tiles{flex:1 1 auto;display:grid;grid-template-rows:1fr 1fr;gap:8px;min-height:0}
@media (min-width:783px){.hv-tiles{grid-template-rows:none;grid-template-columns:1fr 1fr;gap:16px}.hv-land{gap:12px}}
.hv-tile{position:relative;display:flex;flex-direction:column;justify-content:flex-end;min-height:0;border-radius:14px;overflow:hidden;text-decoration:none;color:#fff;isolation:isolate;box-shadow:0 8px 24px rgba(0,0,0,.35);background:#111}
.hv-tile img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:0}
.hv-tile .tb{position:relative;z-index:2;padding:12px 14px 14px;background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.7) 38%,rgba(0,0,0,.86))}
.hv-tile .tn{display:block;font:400 clamp(22px,6.4vw,40px)/1.08 Barlow,system-ui,sans-serif;letter-spacing:.04em}
.hv-tile .ts{display:block;font:500 14px/1.35 Barlow,system-ui,sans-serif;opacity:.92;margin-top:4px}
.hv-tile .tc{display:inline-flex;align-items:center;margin-top:8px;padding:8px 14px;border:1px solid rgba(255,255,255,.85);border-radius:999px;font:600 12px/1 Barlow,system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase}
.hv-tile:hover .tc,.hv-tile:focus-visible .tc{background:#fff;color:#000}
.hv-tile .stripe{position:absolute;left:0;right:0;top:0;height:8px;z-index:2}
.hv-tile img.hv-flag{position:absolute;inset:auto;left:12px;top:12px;width:56px;height:auto;aspect-ratio:5/3;object-fit:fill;z-index:3;border-radius:4px;box-shadow:0 2px 8px rgba(0,0,0,.45)}@media (min-width:783px){.hv-tile img.hv-flag{width:72px}}
.hv-sr{position:absolute!important;width:1px!important;height:1px!important;margin:-1px!important;padding:0!important;overflow:hidden!important;clip:rect(0 0 0 0)!important;white-space:nowrap!important;border:0!important}.hv-a .stripe{background:linear-gradient(180deg,#74ACDF 0 33%,#fff 33% 66%,#74ACDF 66%)}
.hv-tile .hv-tag{top:14px;bottom:auto}
.hv-foot{display:flex;flex-wrap:wrap;justify-content:center;gap:8px 14px;font-size:12px;color:var(--mut)}.hv-foot a{color:var(--mut)}
.hv-eb{flex:0 0 auto;display:flex;align-items:center;justify-content:center;gap:8px;min-height:48px;padding:10px 16px;border-radius:12px;background:#d9a441;color:#111!important;font-weight:700;font-size:16px;line-height:1.2;text-align:center;text-decoration:none;box-shadow:0 4px 14px rgba(0,0,0,.25)}.hv-eb:hover,.hv-eb:focus-visible{background:#e8b553;outline:2px solid #fff;outline-offset:2px}.hv-eb .ar{font-size:18px}
/* hub common */
.hv-hero{position:relative;border-radius:14px;overflow:hidden;margin:4px 0 14px;color:#fff;background:#111}
.hv-hero img{width:100%;aspect-ratio:16/9;object-fit:cover}
.hv-hero .hb{position:absolute;left:0;right:0;bottom:0;padding:14px;background:linear-gradient(180deg,rgba(0,0,0,0),rgba(0,0,0,.8) 45%)}
.hv-hero h1{font-size:clamp(28px,7.5vw,54px)}
.hv-hero .hv-tag{top:8px;bottom:auto}
.hv-btns{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 4px}
.hv-btn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 16px;border-radius:999px;border:1px solid var(--line);color:var(--fg);background:var(--card);text-decoration:none;font:600 13px/1.1 Barlow,system-ui,sans-serif;letter-spacing:.06em;cursor:pointer}
.hv-btn.pri{background:var(--hv-a);border-color:var(--hv-a);color:#fff}
.hv-btn[disabled]{opacity:.45;cursor:default}
.hv sec,.hv section{margin:22px 0}
.hv h2{margin-top:6px}
/* menu (Past / Present) */
.hv-menu{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:6px 12px}
.hv-menu>summary{cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;min-height:44px;font:600 15px/1.2 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.hv-menu>summary::-webkit-details-marker{display:none}.hv-menu>summary:after{content:"\25BE";opacity:.7}
.hv-cols{display:grid;gap:12px;padding:6px 0 10px}@media (min-width:783px){.hv-cols{grid-template-columns:1fr 1fr}}
.hv-cols h3{margin:6px 0 2px;color:var(--hv-b);letter-spacing:.12em;text-transform:uppercase;font-size:14px}
.hv-cols p{margin:0 0 6px;font-size:13px}
.hv-cols ul{list-style:none;margin:0;padding:0;columns:1}.hv-cols li a{display:block;padding:8px 2px;border-bottom:1px solid var(--line);text-decoration:none}
.hv-cols li a:hover{color:var(--hv-b)}
/* tour */
.hv-map{width:100%;height:auto;display:block;border-radius:12px;background:var(--card);border:1px solid var(--line)}
.hv-map .rt{fill:none;stroke:var(--hv-b);stroke-width:2.4;stroke-dasharray:5 5}
.hv-map .sea{fill:rgba(78,140,200,.18)}
.hv-map .dot{cursor:pointer}.hv-map .dot circle{fill:var(--hv-a);stroke:#fff;stroke-width:2}.hv-map .dot.on circle{fill:var(--hv-b)}
.hv-map .dot text{fill:#fff;font:700 11px/1 Barlow,system-ui,sans-serif;text-anchor:middle;dominant-baseline:central;pointer-events:none}
.hv-map .lb{fill:var(--fg);font:500 10.5px Barlow,system-ui,sans-serif}
.hv-map .sl{fill:var(--mut);font:italic 11px Barlow,system-ui,sans-serif}
.hv-stop{display:none}.hv-stop.on{display:block}
.hv-ar{position:relative;border-radius:12px;overflow:hidden;background:#000}
.hv-ar img{width:100%;aspect-ratio:3/2;object-fit:cover}
.hv-ar:before,.hv-ar:after{content:"";position:absolute;z-index:2;width:28px;height:28px;border:2px solid rgba(120,230,255,.9)}
.hv-ar:before{left:10px;top:10px;border-right:0;border-bottom:0}.hv-ar:after{right:10px;top:10px;border-left:0;border-bottom:0}
.hv-ar .scan{position:absolute;left:0;right:0;height:2px;top:0;z-index:2;background:linear-gradient(90deg,transparent,rgba(120,230,255,.8),transparent);animation:hvscan 4.5s linear infinite}
@keyframes hvscan{0%{top:0}100%{top:100%}}@media (prefers-reduced-motion:reduce){.hv-ar .scan{display:none}}
.hv-ar .chip{position:absolute;left:10px;bottom:10px;z-index:3;padding:4px 9px;border-radius:6px;background:rgba(0,30,40,.72);color:#bff3ff;font:600 11px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.hv-ra{display:flex;flex-direction:column;gap:4px;margin:8px 0 0;font-size:13px;line-height:1.35}
.hv-ra-b{display:inline-block;min-width:0;padding:1px 7px;border-radius:999px;font:700 11px/1.5 Barlow,system-ui,sans-serif;letter-spacing:.06em;text-transform:uppercase;vertical-align:1px}
.hv-ra-b.r{background:#1f6f43;color:#fff}.hv-ra-b.a{background:transparent;color:var(--fg);border:1px dashed currentColor}
.hv-sn{display:flex;align-items:baseline;gap:8px;margin:12px 0 2px;color:var(--mut);font:600 12px/1.2 Barlow,system-ui,sans-serif;letter-spacing:.16em;text-transform:uppercase}
.hv-stop h3{font-size:22px;margin:0}
.hv-stop .pl{color:var(--mut);margin:0 0 8px}
.hv-stop .chap{font-size:17px;border-left:3px solid var(--hv-a);padding-left:10px}
.hv-stop h4{margin:12px 0 4px;font:600 13px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--hv-b)}
.hv-stop ul.rec{margin:0;padding-left:18px}.hv-stop ul.rec li{margin:6px 0}
.hv-ev a{display:inline-block;margin:2px 4px 0 0;padding:0 6px;border:1px solid var(--line);border-radius:4px;font:600 11.5px/1.6 Barlow,system-ui,sans-serif;text-decoration:none}
.hv-nav{position:sticky;bottom:0;z-index:5;display:flex;gap:8px;justify-content:space-between;align-items:center;padding:8px 0;background:var(--bg)}
.hv-tl{list-style:none;margin:6px 0;padding:0}.hv-tl li{display:grid;grid-template-columns:62px 1fr;gap:8px;padding:7px 0;border-bottom:1px solid var(--line)}
.hv-tl b{color:var(--hv-b)}
.hv-note{border:1px dashed var(--line);border-radius:12px;padding:12px;background:var(--card)}
/* patagonia */
.hv-gal{display:grid;grid-template-columns:1fr 1fr;gap:8px}@media (min-width:783px){.hv-gal{grid-template-columns:repeat(4,1fr)}}
.hv-gal figure{position:relative;margin:0;border-radius:10px;overflow:hidden;background:#111}
.hv-gal img{width:100%;aspect-ratio:3/2;object-fit:cover}
.hv-gal figcaption{padding:6px 8px 26px;font-size:12.5px;line-height:1.3}
.hv-gal .wide{grid-column:1/-1}.hv-gal .wide img{aspect-ratio:16/9}
.hv-feat{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0;padding:0;list-style:none}.hv-feat li{padding:5px 10px;border:1px solid var(--line);border-radius:999px;font-size:13px}
.hv-bk{border:2px solid var(--hv-a);border-radius:14px;padding:12px;background:var(--card)}
.hv-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;margin:0 0 10px;padding:0;list-style:none;counter-reset:s}
.hv-steps li{counter-increment:s;text-align:center;font:600 11.5px/1.2 Barlow,system-ui,sans-serif;padding:6px 2px;border-bottom:3px solid var(--line);color:var(--mut)}
.hv-steps li:before{content:counter(s) ". "}.hv-steps li.on{border-color:var(--hv-a);color:var(--fg)}
.hv-pane{display:none}.hv-pane.on{display:block}
.hv-opts{display:grid;gap:8px}@media (min-width:783px){.hv-opts{grid-template-columns:1fr 1fr}}
.hv-opt{display:grid;grid-template-columns:88px 1fr;gap:10px;align-items:center;padding:8px;border:1px solid var(--line);border-radius:10px;cursor:pointer}
.hv-opt input{position:absolute;opacity:0;pointer-events:none}
.hv-opt img{width:88px;height:62px;object-fit:cover;border-radius:6px}
.hv-opt b{display:block}.hv-opt small{display:block;color:var(--mut);line-height:1.3}.hv-opt .pr{font-weight:700;color:var(--hv-a)}
.hv-opt:has(input:checked){border-color:var(--hv-a);box-shadow:0 0 0 2px var(--hv-a) inset}
.hv-opt.ro{grid-template-columns:1fr}
.hv-f{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:10px 0}
.hv-f label,.hv-1 label{display:flex;flex-direction:column;gap:3px;font-size:13px;color:var(--mut)}
.hv-f input,.hv-f select,.hv-1 input,.hv-1 select,.hv-1 textarea{font:16px Barlow,system-ui,sans-serif;min-height:44px;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);width:100%}
.hv-1{display:grid;gap:8px;margin:10px 0}
.hv-ck{display:flex!important;flex-direction:row!important;gap:8px;align-items:flex-start}.hv-ck input{width:22px!important;min-height:22px!important;margin-top:2px}
.hv-sum{list-style:none;margin:0;padding:0}.hv-sum li{display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px solid var(--line)}
.hv-sum li.tot{font-weight:700;font-size:18px;border-bottom:0}
.hv-ind{font-size:12.5px;color:var(--mut)}
.hv-err{color:#ff8a8a;font-weight:600}
.hv-done{padding:12px;border-radius:10px;border:2px solid var(--hv-a);background:var(--bg)}
.hv-done b{font-size:20px;letter-spacing:.06em}
"""

LANDING_CSS = r"""

/* Bare two-choice landing with location-specific webapp modals */
body[data-cedwyn-page="landing"]{min-height:100svh;overflow-x:hidden}
body[data-cedwyn-page="landing"] .wrap{width:100%;max-width:none;margin:0;padding:0}
body[data-cedwyn-page="landing"] .hv-land{height:100svh;height:100dvh;min-height:0;max-height:none;padding:clamp(8px,1.7vw,20px);gap:0}
body[data-cedwyn-page="landing"] .hv-tiles{height:100%;min-height:0;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr;gap:clamp(8px,1.5vw,18px)}
body[data-cedwyn-page="landing"] .land-place{position:relative;display:flex;min-width:0;min-height:0;align-items:flex-end;justify-content:center;overflow:hidden;border:0;border-radius:clamp(10px,1.4vw,20px);padding:0;background:#101820;color:#fff;cursor:pointer;isolation:isolate;box-shadow:0 8px 30px rgba(0,0,0,.28);text-align:center;-webkit-tap-highlight-color:transparent}
body[data-cedwyn-page="landing"] .land-place:focus-visible{outline:3px solid #fff;outline-offset:-6px}
body[data-cedwyn-page="landing"] .land-place>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;z-index:-2;transition:transform .35s ease}
body[data-cedwyn-page="landing"] .land-place:before{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(180deg,rgba(0,0,0,.04) 25%,rgba(0,0,0,.22) 52%,rgba(0,0,0,.78) 100%)}
body[data-cedwyn-page="landing"] .land-place:hover>img,body[data-cedwyn-page="landing"] .land-place:focus-visible>img{transform:scale(1.025)}
body[data-cedwyn-page="landing"] .land-place .land-place-label{display:block;max-width:100%;padding:clamp(12px,2.8vw,34px);font:600 clamp(20px,4.2vw,52px)/1.1 Barlow,system-ui,sans-serif;letter-spacing:.025em;text-wrap:balance;text-shadow:0 2px 18px rgba(0,0,0,.9)}
body[data-cedwyn-page="landing"] .ghf-v2,body[data-cedwyn-page="landing"] #ghf-agent-footer,body[data-cedwyn-page="landing"] .ghf-agent-footer{display:none!important}
.land-modal{width:min(1160px,calc(100vw - 18px));max-width:1160px;max-height:calc(100dvh - 18px);margin:auto;padding:0;overflow:hidden;border:1px solid rgba(219,229,240,.25);border-radius:18px;background:#0c1117;color:#f4f6f8;box-shadow:0 24px 90px rgba(0,0,0,.65)}
.land-modal::backdrop{background:rgba(2,5,9,.84);backdrop-filter:blur(5px)}
.land-modal-inner{display:flex;flex-direction:column;max-height:calc(100dvh - 20px);min-height:0}
.land-modal-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 18px;border-bottom:1px solid rgba(255,255,255,.12);background:#0d141c}
.land-modal-head h2{margin:0;color:#f5f7fa;font:600 clamp(20px,3.6vw,30px)/1.2 Barlow,system-ui,sans-serif;letter-spacing:.015em;text-transform:none}
.land-modal-close{display:grid;place-items:center;flex:0 0 42px;width:42px;height:42px;border:1px solid rgba(255,255,255,.25);border-radius:50%;background:#18212a;color:#fff;font:300 30px/1 system-ui,sans-serif;cursor:pointer}
.land-modal-close:hover{background:#263440}
.land-modal-content{overflow:auto;overscroll-behavior:contain;padding:16px clamp(12px,2vw,22px) 24px}
.land-app-section{margin:0 0 22px}
.land-app-section h3{margin:0 0 10px;color:#aebdca;font:600 12px/1.3 Barlow,system-ui,sans-serif;letter-spacing:.13em;text-transform:uppercase}
.land-app-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:11px}
.land-app{display:flex;flex-direction:column;min-width:0;overflow:hidden;border:1px solid rgba(255,255,255,.13);border-radius:11px;background:#121a23;color:#f3f5f7;text-decoration:none;transition:transform .15s ease,border-color .15s ease,background .15s ease}
.land-app:hover,.land-app:focus-visible{transform:translateY(-2px);border-color:rgba(185,215,238,.7);background:#192531}
.land-app>img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#111820}
.land-app-label{display:block;padding:9px 10px 10px;font:600 13px/1.25 Barlow,system-ui,sans-serif;overflow-wrap:anywhere}
.land-app-soon{cursor:default;border-style:dashed;border-color:rgba(185,215,238,.35)}
.land-app-soon:hover{transform:none;background:#121a23;border-color:rgba(185,215,238,.35)}
.land-app-soon .land-app-label small{display:block;margin-top:4px;color:#aebdca;font-size:11px;font-weight:500;letter-spacing:.04em}
.land-specific{margin-bottom:24px}
@media(max-width:780px){.land-app-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:540px){
 body[data-cedwyn-page="landing"] .hv-land{padding:7px}
 body[data-cedwyn-page="landing"] .hv-tiles{grid-template-columns:1fr;grid-template-rows:1fr 1fr;gap:7px}
 body[data-cedwyn-page="landing"] .land-place{border-radius:11px}
 body[data-cedwyn-page="landing"] .land-place .land-place-label{font-size:clamp(22px,7.2vw,34px);padding:18px}
 .land-modal{width:calc(100vw - 10px);max-height:calc(100dvh - 10px);border-radius:13px}
 .land-modal-inner{max-height:calc(100dvh - 12px)}
 .land-modal-head{padding:11px 12px}
 .land-modal-close{flex-basis:38px;width:38px;height:38px}
 .land-modal-content{padding:12px 9px 18px}
 .land-app-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
 .land-app-label{padding:8px;font-size:12px}
}
@media(prefers-reduced-motion:reduce){body[data-cedwyn-page="landing"] .land-place>img,.land-app{transition:none}}
"""

# ---------- shared bits
def ev_links(H, ids):
    if not ids: return ''
    return '<span class="hv-ev">' + ''.join(f'<a href="{E(H["ev_href"].get(i, "/research/evidence/"))}">{E(i)}</a>' for i in ids) + '</span>'

def img(H, name):
    return f'{H["img"]}{name}.webp?v={H.get("img_v","1")}'

def grouping(H, cfg, sec):
    G = H['groups']; past = set(G['past']); pres = set(G['present']); excl = set(G.get('wales_exclude' if sec == 'wales' else 'argentina_exclude', []))
    out = {'past': [], 'present': []}
    for t in cfg['themes']:
        if t['id'] in excl: continue
        g = 'past' if t['id'] in past else 'present' if t['id'] in pres else G.get('default', 'present')
        out[g].append(t)
    return out

def menu(H, T, cfg, l, sec, open_=False):
    gr = grouping(H, cfg, sec); n = sum(len(v) for v in gr.values())
    wmap = H.get('wales_title_map', {}) if sec == 'wales' else {}
    if wmap:
        for t in cfg['themes']:
            k = 'th_' + t['id']
            if k in T: T[k] = {x: wmap.get(v, v) for x, v in T[k].items()}
    cols = []
    for g in ('past', 'present'):
        li = ''.join(f'<li><a href="/{sec}/{E(t["id"])}/" data-i18n="th_{E(t["id"])}">{E(tx(T, "th_" + t["id"], l))}</a></li>' for t in gr[g])
        if g == 'past':   # pages outside themes.json (data/halves.json groups.past_pages, e.g. the title chain), listed first under Past - Sion's Tab agent
            pre = ''
            for p in H['groups'].get('past_pages', []):
                T['pg_' + p['id']] = p['title']
                pre += f'<li><a href="/{sec}/{E(p["id"])}/" data-i18n="pg_{E(p["id"])}">{E(tx(T, "pg_" + p["id"], l))}</a></li>'
            li = pre + li
        cols.append(f'<div><h3 data-i18n="g_{g}">{E(tx(T, "g_" + g, l))}</h3><p class="mut" data-i18n="g_{g}_p">{E(tx(T, "g_" + g + "_p", l))}</p><ul>{li}</ul></div>')
    T['menu_p_n'] = {k: v.replace('{n}', str(n)) for k, v in T['menu_p'].items()}
    return (f'<details class="hv-menu" id="menu"{" open" if open_ else ""}><summary><span data-i18n="w_menu">{E(tx(T, "w_menu", l))}</span></summary>'
            f'<h2 data-i18n="menu_h">{E(tx(T, "menu_h", l))}</h2><p class="mut" data-i18n="menu_p_n">{E(tx(T, "menu_p_n", l))}</p>'
            f'<div class="hv-cols">{"".join(cols)}</div></details>'), gr

JS = r"""
(function(){
  var de=document.documentElement,T=window.CEDWYN_T||{};
  function L(){try{if(window.CedwynSection)return CedwynSection.lang()}catch(e){}var l=(de.getAttribute('lang')||'en').slice(0,2);return /^(en|cy|es)$/.test(l)?l:'en'}
  function tr(k){var v=T[k];if(!v)return '';return v[L()]||v.en||''}
  window.__hvTr=tr;
  var page=document.body.getAttribute('data-cedwyn-page');
  if(page==='landing'){
    var hd=null,fix=function(){hd=document.querySelector('.ghf-v2');var top=document.querySelector('.hv-land');if(!top)return;var r=top.getBoundingClientRect();de.style.setProperty('--hv-top',Math.max(0,Math.round(r.top+window.scrollY))+'px')};
    fix();window.addEventListener('load',fix);window.addEventListener('resize',fix);setTimeout(fix,600);setTimeout(fix,1600);
    var t0=Date.now(),leaving=false;
    document.addEventListener('ghf-lang-change',function(e){if(leaving||Date.now()-t0<1500)return;try{sessionStorage.setItem('cedwyn-land-lang',e.detail&&e.detail.lang||L())}catch(x){}});
    [].forEach.call(document.querySelectorAll('.hv-tile'),function(a){a.addEventListener('click',function(){leaving=true})});
    var strip=function(){try{if(/[?&]lang=/.test(location.search)&&history.replaceState)history.replaceState(null,'',location.pathname+location.hash)}catch(e){}};
    document.addEventListener('ghf-lang-change',function(){setTimeout(strip,300)});setTimeout(strip,6000);
  }
  if(page==='wales'){
    var stops=[].slice.call(document.querySelectorAll('.hv-stop')),dots=[].slice.call(document.querySelectorAll('.hv-map .dot')),cur=0;
    var prev=document.getElementById('hv-prev'),next=document.getElementById('hv-next'),cnt=document.getElementById('hv-cnt');
    function show(i,scroll){cur=Math.max(0,Math.min(stops.length-1,i));stops.forEach(function(s,j){s.classList.toggle('on',j===cur)});dots.forEach(function(d,j){d.classList.toggle('on',j===cur)});
      if(cnt)cnt.textContent=(cur+1)+' / '+stops.length;prev.disabled=cur===0;next.disabled=cur===stops.length-1;
      if(scroll){try{history.replaceState(null,'',location.pathname+location.search+'#stop-'+(cur+1))}catch(e){}}
      if(scroll){var el=document.getElementById('tour');if(el)el.scrollIntoView({behavior:'smooth',block:'start'})}stopSpeak()}
    prev.addEventListener('click',function(){show(cur-1,true)});next.addEventListener('click',function(){show(cur+1,true)});
    dots.forEach(function(d,j){d.addEventListener('click',function(){show(j,true)});d.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();show(j,true)}})});
    [].forEach.call(document.querySelectorAll('[data-hv-go]'),function(a){a.addEventListener('click',function(e){var j=+a.getAttribute('data-hv-go');if(stops[j]){e.preventDefault();show(j,true)}})});
    var m=/#stop-(\d+)/.exec(location.hash);show(m?+m[1]-1:0,false);
    // open at the top (Sion, WhatsApp 06:31 GMT 27 Oct 2026: "when I select wales I dont anchor to half way down the page"): the first
    // show() writes no #stop-N; a #stop-N link selects its stop, leaves the URL clean and the page at the top - Sion's Tab agent
    if(m||!location.hash){var userMoved=false,top0=function(){if(!userMoved)window.scrollTo(0,0)};
      try{if('scrollRestoration' in history)history.scrollRestoration='manual'}catch(e){}
      if(m){try{history.replaceState(null,'',location.pathname+location.search)}catch(e){}}
      ['touchstart','wheel','keydown','mousedown'].forEach(function(t){window.addEventListener(t,function(){userMoved=true},{once:true,passive:true})});
      top0();setTimeout(top0,0);window.addEventListener('load',function(){top0();setTimeout(top0,80)})}
    var sy=window.speechSynthesis,btn=document.getElementById('hv-say'),speaking=false;
    function stopSpeak(){if(sy&&speaking){sy.cancel()}speaking=false;if(btn)btn.textContent=tr('w_listen')}
    if(!sy&&btn)btn.hidden=true;
    if(btn)btn.addEventListener('click',function(){if(speaking){stopSpeak();return}var s=stops[cur];var txt=[].map.call(s.querySelectorAll('h3,.pl,.chap,.ov,ul.rec li .rt,.nw,.op'),function(x){return x.textContent}).join('. ');
      var u=new SpeechSynthesisUtterance(txt);var l=L();u.lang=l==='cy'?'cy-GB':l==='es'?'es-AR':'en-GB';u.rate=.98;u.onend=function(){speaking=false;btn.textContent=tr('w_listen')};
      sy.cancel();sy.speak(u);speaking=true;btn.textContent=tr('w_stoplisten')});
    document.addEventListener('ghf-lang-change',function(){setTimeout(function(){if(btn&&!speaking)btn.textContent=tr('w_listen')},50)});
  }
  if(page==='argentina'){
    var B=window.HV_BOOK||{},f=document.getElementById('hv-book');if(!f)return;
    var panes=[].slice.call(f.querySelectorAll('.hv-pane')),steps=[].slice.call(f.querySelectorAll('.hv-steps li')),st=0;
    function money(n){return '\u00a3'+Math.round(n).toLocaleString('en-GB')}
    function d(id){return f.querySelector('#'+id)}
    function val(n){var x=f.querySelector('[name="'+n+'"]:checked')||f.querySelector('[name="'+n+'"]');return x?x.value:''}
    function nights(){var a=new Date(d('bk-in').value),b=new Date(d('bk-out').value);if(isNaN(a)||isNaN(b))return 0;return Math.round((b-a)/864e5)}
    function venue(){var v=val('venue');for(var i=0;i<B.venues.length;i++)if(B.venues[i].id===v)return B.venues[i];return null}
    function calc(){var v=venue(),nn=nights(),g=+d('bk-g').value||1,rm=+d('bk-r').value||1,lines=[],tot=0,q=false;
      if(v){var n=v.id==='wed'?1:Math.max(nn,0),u=v.id==='room'?rm:1,a=v.price*u*(v.id==='wed'?1:n);
        lines.push([tr('v_'+v.id)+(v.id==='room'?' \u00d7 '+rm:'')+(v.id==='wed'?'':' \u00b7 '+n+' '+tr('b_nights')),a]);tot+=a}
      var ap=val('fly'),fl=+d('bk-fp').value||0;if(ap&&ap!=='NONE'){var A=null;for(var i=0;i<B.airports.length;i++)if(B.airports[i][0]===ap)A=B.airports[i];
        if(A){if(A[2]==null){lines.push([tr('b_s2')+' \u00b7 '+A[1]+' \u00d7 '+fl,null]);q=true}else{lines.push([tr('b_s2')+' \u00b7 '+A[1]+' \u2192 REL \u00d7 '+fl,A[2]*fl]);tot+=A[2]*fl}}}
      var c=val('car');if(c&&c!=='none'){var C=null;for(var j=0;j<B.cars.length;j++)if(B.cars[j][0]===c)C=B.cars[j];var days=Math.max(nn,1);
        if(C){lines.push([tr('b_car')+' \u00b7 '+tr('c_'+C[0])+' \u00b7 '+days+' \u00d7 '+money(C[1]),C[1]*days]);tot+=C[1]*days}}
      return {lines:lines,tot:tot,quote:q,nights:nn,g:g,rm:rm,v:v,ap:ap,fl:fl,car:c,pick:d('bk-pick').value}}
    function render(){var c=calc(),ul=d('bk-sum'),h='';c.lines.forEach(function(x){h+='<li><span></span><b></b></li>'});ul.innerHTML=h+'<li class="tot"><span></span><b></b></li>';
      var li=ul.querySelectorAll('li');c.lines.forEach(function(x,i){li[i].firstChild.textContent=x[0];li[i].lastChild.textContent=x[1]==null?tr('b_quote'):money(x[1])});
      li[li.length-1].firstChild.textContent=tr('b_total');li[li.length-1].lastChild.textContent=money(c.tot)+(c.quote?' +':'');return c}
    function ok(i){var e=d('bk-err');e.hidden=true;if(i===0){var v=venue(),n=nights();if(!v||(v.id!=='wed'&&n<1)||!d('bk-in').value){e.textContent=tr('b_err');e.hidden=false;return false}}return true}
    function go(i){if(i>st&&!ok(st))return;st=Math.max(0,Math.min(panes.length-1,i));panes.forEach(function(p,j){p.classList.toggle('on',j===st)});steps.forEach(function(s,j){s.classList.toggle('on',j<=st)});
      d('bk-back').hidden=st===0;d('bk-next').hidden=st===panes.length-1;if(st===panes.length-1)render();var top=f.getBoundingClientRect().top+window.scrollY-70;if(window.scrollY>top)window.scrollTo({top:top,behavior:'smooth'})}
    d('bk-next').addEventListener('click',function(){go(st+1)});d('bk-back').addEventListener('click',function(){go(st-1)});
    f.addEventListener('change',function(e){var v=venue();d('bk-rw').hidden=!(v&&v.id==='room');d('bk-outw').hidden=!!(v&&v.id==='wed');
      if(e.target&&e.target.id==='bk-g'){d('bk-fp').value=d('bk-g').value}if(st===panes.length-1)render()});
    var today=new Date();today.setDate(today.getDate()+1);var mn=today.toISOString().slice(0,10);d('bk-in').min=mn;d('bk-out').min=mn;
    document.addEventListener('ghf-lang-change',function(){setTimeout(function(){if(st===panes.length-1)render()},60)});
    f.addEventListener('submit',function(ev){ev.preventDefault();var e=d('bk-err2');e.hidden=true;var em=(d('bk-em').value||'').trim(),nm=(d('bk-nm').value||'').trim();
      if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(em)||!d('bk-ok').checked||!nm){e.textContent=tr('b_err');e.hidden=false;return}
      var c=render(),ref='GH2-'+Date.now().toString(36).toUpperCase().slice(-6);
      var sum=(/\btest\b/i.test(nm)?'TEST ':'')+'PREORDER '+ref+' | '+nm.slice(0,40)+' | '+(c.v?c.v.id:'-')+' '+d('bk-in').value+(c.v&&c.v.id!=='wed'?'..'+d('bk-out').value:'')+' g'+c.g+(c.v&&c.v.id==='room'?' r'+c.rm:'')+' | fly '+(c.ap||'-')+(c.ap&&c.ap!=='NONE'?' x'+c.fl:'')+' | car '+(c.car||'-')+'@'+c.pick+' | est GBP'+Math.round(c.tot)+(c.quote?'+':'')+' | '+L()+' | '+(d('bk-note').value||'').slice(0,60);
      sum=sum.slice(0,250);
      var sb=f.querySelector('[type=submit]');if(sb)sb.disabled=true;
      // 26 Oct 2026: the request goes to Cedwyn's own mailing list (replaces Mailchimp); the visitor confirms by the link in their email
      fetch('/api/list/subscribe',{method:'POST',credentials:'omit',headers:{'content-type':'application/json'},body:JSON.stringify({email:em,name:nm.slice(0,80),lang:L(),topic:'argentina-preorder',source:location.pathname,note:sum})})
      .then(function(r){return r.json().catch(function(){return {}})}).then(function(j){if(sb)sb.disabled=false;
      if(!j||!j.ok){e.textContent=(j&&j.message)||tr('b_err_send');e.hidden=false;return}
      try{var a=JSON.parse(localStorage.getItem('cedwyn-gh2-preorders')||'[]');a.push({ref:ref,at:new Date().toISOString(),sum:sum});localStorage.setItem('cedwyn-gh2-preorders',JSON.stringify(a.slice(-10)))}catch(x){}
      d('bk-form').hidden=true;var dn=d('bk-done');dn.hidden=false;d('bk-ref').textContent=ref;dn.setAttribute('data-ref',ref);dn.scrollIntoView({block:'center',behavior:'smooth'})},
      function(){if(sb)sb.disabled=false;e.textContent=tr('b_err_send');e.hidden=false})});
    go(0);
  }
})();
"""

def headlines(H, T, l, sec, lead='', tail=''):
    """The story in headlines (Sion, 12:01 GMT 26 Oct 2026, m:2c8d96e9): bold evidence-backed points first, the detail behind
    a native <details> "Read more" (Darllen mwy / Leer más); folded text stays in the HTML for search and AI readers. - Sion's Tab agent"""
    hs = (H.get('headlines') or {}).get(sec) or []
    if not hs: return (f'<section id="headlines" class="hv-seg" data-cw-seg>{lead}{tail}</section>' if lead else '')
    for k, v in (H.get('headlines') or {}).get('t', {}).items(): T[k] = v
    items = []
    for j, x in enumerate(hs):
        kh, kd = f'hl_{sec}_{j}_h', f'hl_{sec}_{j}_d'
        T[kh] = x['h']; T[kd] = x['d']
        hrefs = x.get('href') or []
        links = ' · '.join(f'<a href="{E(u)}"><span data-i18n="hl_rec">{E(tx(T, "hl_rec", l))}</span>{(" " + str(n + 1)) if len(hrefs) > 1 else ""}</a>' for n, u in enumerate(hrefs))
        ev = f'<p class="hv-hl-ev">{links}</p>' if links else ''
        # no heading-then-"Read more" fold (Sion, 23:32 GMT 26 Oct 2026): the point and its detail show; clamp.js crops the detail
        # at three lines with "read more" / "less" - Sion's Tab agent
        items.append(f'<div class="hv-hl"><b data-i18n="{kh}">{E(tx(T, kh, l))}</b>'
                     f'<p data-i18n="{kd}">{E(tx(T, kd, l))}</p>{ev}</div>')
    css = ('<style>.hv-hls{margin:18px 0 22px}.hv-hls>h2{margin-bottom:6px}.hv-hl{border-top:1px solid rgba(127,127,127,.35);padding:12px 0}'
           '.hv-hl:last-child{border-bottom:1px solid rgba(127,127,127,.35)}.hv-hl>b{display:block;font-size:1.25em;line-height:1.25;font-weight:800}'
           '.hv-hl p{margin:.55em 0}.hv-hl-ev a{font-weight:600}</style>')
    if lead:
        # One text segment (Sion, WhatsApp 06:16 GMT 27 Oct 2026, m:12fcf64f: "One segment of text on this page ... only please"):
        # the lede, every headline and any closing note sit in ONE block under the title; clamp.js shows its first three lines and
        # "read more" opens it a paragraph at a time, "less" closes it. Same words, same order; the section label rides as the
        # first point's kicker. Without JavaScript every word shows - Sion's Tab agent
        if items:
            items[0] = items[0].replace('<div class="hv-hl">', f'<div class="hv-hl"><span class="hv-hl-k" data-i18n="hl_h">{E(tx(T, "hl_h", l))}</span>', 1)
        css = css.replace('</style>', '.hv-seg>.lede{margin-bottom:.4em}.hv-hl-k{display:block;font-size:.78em;letter-spacing:.06em;text-transform:uppercase;opacity:.75;margin-bottom:4px}</style>')
        return f'{css}<section id="headlines" class="hv-hls hv-seg" data-cw-seg>{lead}{"".join(items)}{tail}</section>'
    return f'<section id="headlines" class="hv-hls">{css}<h2 data-i18n="hl_h">{E(tx(T, "hl_h", l))}</h2>{"".join(items)}</section>'

def projection(stops):
    la = [s['lat'] for s in stops]; lo = [s['lon'] for s in stops]
    a0, a1, o0, o1 = min(la), max(la), min(lo), max(lo)
    kx = math.cos(math.radians((a0 + a1) / 2))
    W, Hh, pad = 360, 300, 34
    sx = (W - 2 * pad) / ((o1 - o0) * kx or 1); sy = (Hh - 2 * pad) / ((a1 - a0) or 1); k = min(sx, sy)
    def p(lat, lon):
        return pad + (lon - o0) * kx * k, Hh - pad - (lat - a0) * k
    return p, W, Hh

def tour_map(H, T, l):
    st = H['stops']; p, W, Hh = projection(st)
    pts = [p(s['lat'], s['lon']) for s in st]
    route = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)
    sea = f'<path class="sea" d="M0,{Hh} L0,{Hh-28} C90,{Hh-40} 150,{Hh-22} 220,{Hh-56} S{W},{Hh-120} {W},{Hh-130} L{W},{Hh} Z"/>'
    dots = []
    seen = {}
    for i, ((x, y), s) in enumerate(zip(pts, st)):
        key = (round(x / 14), round(y / 14)); off = seen.get(key, 0); seen[key] = off + 1
        dx = off * 15
        nm = tx(T, f'stop_{s["id"]}_name', l)
        anchor = 'end' if x > W * 0.62 else 'start'
        lx = x + dx + (-14 if anchor == 'end' else 14)
        dots.append(f'<g class="dot" data-i="{i}" role="button" tabindex="0" aria-label="{E(str(i+1))}"><circle cx="{x+dx:.1f}" cy="{y:.1f}" r="10"/>'
                    f'<text x="{x+dx:.1f}" y="{y:.1f}">{i+1}</text></g>')
        if off == 0 and i < len(st) - 1:
            dots.append(f'<text class="lb" x="{lx:.1f}" y="{y+4:.1f}" text-anchor="{anchor}" data-i18n="stop_{s["id"]}_short">{E(tx(T, f"stop_{s[chr(105)+chr(100)]}_short", l))}</text>')
    return (f'<svg class="hv-map" viewBox="0 0 {W} {Hh}" role="img" aria-labelledby="hv-map-t"><title id="hv-map-t">{E(tx(T,"w_map_h",l))}</title>{sea}'
            f'<text class="sl" x="{W-12}" y="{Hh-10}" text-anchor="end">Môr Hafren · Bristol Channel</text>'
            f'<polyline class="rt" points="{route}"/>' + ''.join(dots) + '</svg>')

def ra_html(T, l, key, s):
    """Real vs augmented, per stop (Sion, WhatsApp 12:11 GMT 27 Oct 2026: the Celtic cross and St Dochdwy's church are physically
    there, never holograms; what is lost is shown in AR). One small "Real" and one "Augmented (AR)" line. - Sion's Tab agent"""
    out = ''
    for kind, cls in (('real', 'r'), ('ar', 'a')):
        if not s.get(kind): continue
        T[f'{key}_{kind}'] = s[kind]
        out += (f'<span class="hv-ra-i"><span class="hv-ra-b {cls}" data-i18n="ra_{kind}">{E(tx(T, "ra_" + kind, l))}</span> '
                f'<span data-i18n="{key}_{kind}">{E(tx(T, f"{key}_{kind}", l))}</span></span>')
    return f'<p class="hv-ra">{out}</p>' if out else ''

def stop_html(H, T, l, i, s, n):
    """One tour stop (Sion 02:12 GMT 26 Oct: a warm guided tour; every legal citation lives only in the "court" stop)."""
    sid = s['id']
    for k in ('name', 'place', 'overlay', 'now', 'open', 'story'):
        if k in s: T[f'stop_{sid}_{k}'] = s[k]
    if s.get('holo') and s.get('holo_overlay'):
        T[f'stop_{sid}_holo'] = s['holo_overlay']
    T[f'stop_{sid}_short'] = s['place'] if sid in ('driscoll', 'bay', 'lavernock', 'brynwell') else s['name']
    T[f'stop_{sid}_short'] = {k: re.split(r'[,:·]', v)[0] for k, v in T[f'stop_{sid}_short'].items()}
    recs = []
    for j, (txt, ids) in enumerate(s.get('recs', [])):
        T[f'stop_{sid}_r{j}'] = txt
        recs.append(f'<li><span class="rt" data-i18n="stop_{sid}_r{j}">{E(tx(T, f"stop_{sid}_r{j}", l))}</span> {ev_links(H, ids)}</li>')
    alt = tx(T, f'stop_{sid}_overlay', l)
    extra = ''
    if s.get('timeline'):
        tl = []
        for j, (yr, txt) in enumerate(s['timeline']):
            T[f'tl_{sid}_{j}'] = txt
            tl.append(f'<li><b>{E(yr)}</b><span data-i18n="tl_{sid}_{j}">{E(tx(T, f"tl_{sid}_{j}", l))}</span></li>')
        extra = f'<ol class="hv-tl">{"".join(tl)}</ol>'
    if s.get('links'):
        extra += '<div class="hv-btns">' + ''.join(f'<a class="hv-btn" href="{E(u)}" data-i18n="{E(k)}">{E(tx(T, k, l) or u)}</a>' for k, u in s['links']) + '</div>'
    return (f'<article class="hv-stop{" on" if i == 0 else ""}" id="stop-{i+1}" data-stop="{E(sid)}" aria-label="{E(str(i+1))}">'
            f'<div class="hv-ar cwlb-th" data-lb=""><img src="{img(H, s["img"])}" width="1280" height="853" alt="{E(alt)}" data-i18n-al="stop_{sid}_overlay" loading="{"eager" if i == 0 else "lazy"}" decoding="async"><span class="scan"></span>'
            f'<span class="chip" data-i18n="{E(s.get("chip", "ar_tag"))}">{E(tx(T, s.get("chip", "ar_tag"), l))}</span></div>'
            + (f'<div class="hv-ar cwlb-th" id="recreations" data-lb="" style="clear:right"><img src="{img(H, s["holo"])}" width="1280" height="853" alt="{E(tx(T, f"stop_{sid}_holo", l))}" data-i18n-al="stop_{sid}_holo" loading="lazy" decoding="async"><span class="scan"></span>'
               f'<span class="chip" data-i18n="holo_tag">{E(tx(T, "holo_tag", l))}</span></div>' if s.get('holo') else '')
            + ra_html(T, l, f'stop_{sid}', s) +
            f'<p class="hv-sn"><span data-i18n="w_stop">{E(tx(T, "w_stop", l))}</span> {i+1} / {n}</p>'
            f'{sp(T, f"stop_{sid}_name", l, "h3")}{sp(T, f"stop_{sid}_place", l, "p", "pl")}'
            f'<p class="chap" data-i18n="stop_{sid}_story">{E(tx(T, f"stop_{sid}_story", l))}</p>'
            f'{sp(T, "w_overlay", l, "h4")}{sp(T, f"stop_{sid}_overlay", l, "p", "ov")}'
            + (f'{sp(T, "w_records", l, "h4")}<ul class="rec">{"".join(recs)}</ul>' if recs else '') + extra +
            f'{sp(T, "w_now", l, "h4")}{sp(T, f"stop_{sid}_now", l, "p", "nw")}'
            + (f'{sp(T, "w_open", l, "h4")}{sp(T, f"stop_{sid}_open", l, "p", "op")}' if 'open' in s else '') + '</article>')

def base_T(sections, S, cfg, sec, H):
    T = sections.page_t(S, cfg, sec)
    T.update(H['t'])
    return T

def page(sections, title, desc, lang, bpath, sec, T, n, body):
    h = sections.head(title, desc, lang, bpath, sec, T, n)
    h = h.replace('</style>', CSS + '</style>', 1)
    return h + body

# Every catalogued webapp is available in both location modals unless a page belongs to one
# physical/virtual reconstruction. Images are vendored under web/_cedwyn/halves/img/ and stay on Cedwyn.
APP_LABELS = {
    'wiki': 'Legal Wiki',
    'records': 'Primary Records',
    'docs': 'Evidence Catalogue',
    'infographic': 'Title chain · infographic',
    'story': 'Full story · BP vs Buckler',
    'terrain': '3D map',
    'patagonia': 'Patagonia Museum',
    'wales': 'Virtual reconstruction',
    'qa': 'Q&A',
    'familytree': 'Family tree',
    'chat': 'Ask the Archive',
    'nft-art': 'Gallery',
    'thousand-cuts': '1000 Cuts',
}
APP_IMAGES = {
    'wiki': 'ghf2-drawing-room', 'records': 'ty-mawr-1974-reconstruction',
    'docs': 'wales-ar-forest', 'wayback': 'wales-stop-brynwell',
    'nomenclature': 'wales-ar-green', 'maps': 'wales-ar-villa',
    'infographic': 'ty-mawr-1974-reconstruction', 'ebooks': 'ghf2-bedroom',
    'story': 'ty-mawr-1974-reconstruction', 'thousand-cuts': 'ghf2-exterior',
    'fb': 'ghf2-museum', 'chess': 'wales-ar-forest',
    'csscpsg': 'ghf2-drawing-room', 'courtdrills': 'ghf2-museum',
    'fcg': 'wales-ar-forest', 'oldbill': 'ghf2-exterior',
    'accounts': 'ghf2-bedroom', 'authorities': 'wales-ar-forest',
    'wdtk': 'ghf2-drawing-room', 'review': 'ty-mawr-1974-reconstruction',
    'research': 'wales-ar-villa', 'qa': 'wales-stop-brynwell',
    'meeting': 'ghf2-drawing-room', 'projects': 'ghf2-exterior',
    'app': 'wales-ar-green', 'chat': 'wales-stop-brynwell',
    'watchtower': 'wales-ar-forest', 'fb2': 'ghf2-museum',
    'email': 'ghf2-drawing-room', 'emails': 'ghf2-bedroom',
    'dartboard': 'wales-ar-villa', 'estate': 'tile-wales',
    'directory': 'tile-patagonia', 'terrain': 'wales-ar-villa',
    'cyberspace': 'network-datacentre', 'shop': 'ghf2-drawing-room',
    'documentary': 'wales-hologram', 'familytree': 'wales-ar-forest',
    'kissed-frogs': 'ghf2-wedding', 'nft-art': 'ghf2-museum',
    'whattheydontsay': 'wales-ar-villa', 'blog': 'ghf2-drawing-room',
}
APP_EXCLUDED = {'wales', 'patagonia'}

# Menu tile pictures per half (Sion, WhatsApp 01:54 GMT 30 Oct 2026). Wales: wireframe-hologram renders of building photographs from
# the wayback archive's Great House Farm Part 1 series (holo-ghf1-<n>.webp = 'Great House Farm Part 1 - <n>'; edge-detected locally,
# work/tile-images/holo.py; committed under web/_cedwyn/halves/img/). Argentina: the digitally restored farm pieces ('restored to former
# glory', v0.0.2, no flowers, no people) by their own /nft-art/ thumbs, never copies; the flowery gallery pieces stay on the NFT pages only.
WALES_TILE_IMAGES = {'infographic': 'holo-ghf1-101', 'chess': 'holo-ghf1-124', 'csscpsg': 'holo-ghf1-038', 'courtdrills': 'holo-ghf1-022', 'app': 'holo-ghf1-010', 'chat': 'holo-ghf1-039', 'dartboard': 'holo-ghf1-015', 'estate': 'holo-ghf1-025', 'directory': 'holo-ghf1-096', 'terrain': 'holo-ghf1-020', 'cyberspace': 'holo-ghf1-013', 'nft-art': 'holo-ghf1-119', 'fcg': 'holo-ghf1-018', 'accounts': 'holo-ghf1-084', 'authorities': 'holo-ghf1-100', 'wdtk': 'holo-ghf1-123', 'review': 'holo-ghf1-115', 'research': 'holo-ghf1-011', 'meeting': 'holo-ghf1-053', 'projects': 'holo-ghf1-016', 'watchtower': 'holo-ghf1-023', 'fb2': 'holo-ghf1-099', 'email': 'holo-ghf1-126', 'emails': 'holo-ghf1-092', 'kissed-frogs': 'holo-ghf1-124', 'whattheydontsay': 'holo-ghf1-039', 'blog': 'holo-ghf1-096', 'wiki': 'holo-ghf1-038', 'records': 'holo-ghf1-084', 'docs': 'holo-ghf1-076', 'wayback': 'holo-ghf1-098', 'nomenclature': 'holo-ghf1-011', 'maps': 'holo-ghf1-025', 'fb': 'holo-ghf1-099', 'ebooks': 'holo-ghf1-115', 'story': 'holo-ghf1-098', 'thousand-cuts': 'holo-ghf1-010', 'oldbill': 'holo-ghf1-084', 'qa': 'holo-ghf1-039', 'shop': 'holo-ghf1-119', 'documentary': 'holo-ghf1-101', 'familytree': 'holo-ghf1-099'}
ARG_TILE_IMAGES = {'infographic': '0021', 'chess': '0094', 'csscpsg': '0078', 'courtdrills': '0082', 'app': '0035', 'chat': '0057', 'dartboard': '0029', 'estate': '0014', 'directory': '0048', 'terrain': '0106', 'cyberspace': '0044', 'nft-art': '0058', 'fcg': '0122', 'accounts': '0131', 'authorities': '0055', 'wdtk': '0072', 'review': '0083', 'research': '0087', 'meeting': '0050', 'projects': '0020', 'watchtower': '0026', 'fb2': '0023', 'email': '0071', 'emails': '0147', 'kissed-frogs': '0067', 'whattheydontsay': '0084', 'blog': '0076', 'wiki': '0088', 'records': '0117', 'docs': '0058', 'wayback': '0141', 'nomenclature': '0123', 'maps': '0093', 'fb': '0038', 'ebooks': '0060', 'story': '0032', 'thousand-cuts': '0130', 'oldbill': '0052', 'qa': '0080', 'shop': '0145', 'documentary': '0133', 'familytree': '0126'}

def arg_restored(nfa):
    return f'/nft-art/art/nfa-{nfa}-v0.0.2-t.webp'

def app_image(H, key):
    if key == 'network-datacentre':
        return f'{H["img"]}network-datacentre.svg?v=1'
    if key.startswith('nfa:'):
        return arg_restored(key[4:])
    return img(H, key)

def app_tile(H, section, theme):
    tid = theme['id']
    label = APP_LABELS.get(tid, theme.get('title') or tid)
    if section == 'wales' and tid in WALES_TILE_IMAGES:
        image = WALES_TILE_IMAGES[tid]
    elif section == 'argentina' and tid in ARG_TILE_IMAGES:
        image = 'nfa:' + ARG_TILE_IMAGES[tid]
    else:
        image = APP_IMAGES.get(tid, 'ty-mawr-1974-reconstruction')
    return (f'<a class="land-app" href="/{E(section)}/{E(tid)}/" aria-label="{E(label)}">'
            f'<img src="{E(app_image(H, image))}" alt="" loading="lazy" decoding="async">'
            f'<span class="land-app-label">{E(label)}</span></a>')

def specific_tile(H, title, href, image):
    return (f'<a class="land-app" href="{E(href)}" aria-label="{E(title)}">'
            f'<img src="{E(app_image(H, image))}" alt="" loading="lazy" decoding="async">'
            f'<span class="land-app-label">{E(title)}</span></a>')

def network_tile(H):
    return (f'<div class="land-app land-app-soon" aria-label="Network, coming soon">'
            f'<img src="{E(app_image(H, "network-datacentre"))}" alt="" loading="lazy" decoding="async">'
            f'<span class="land-app-label">Network<small>Coming soon</small></span></div>')

def modal_apps(H, cfg, section):
    out = []
    for group in cfg.get('groups', []):
        items = [t for t in cfg['themes'] if t.get('group') == group['id'] and t['id'] not in APP_EXCLUDED]
        if not items:
            continue
        out.append('<section class="land-app-section"><h3>' + E(group['title']) + '</h3><div class="land-app-grid">')
        out.append(''.join(app_tile(H, section, t) for t in items))
        out.append('</div></section>')
    out.append('<section class="land-app-section"><h3>Coming soon</h3><div class="land-app-grid">')
    out.append(network_tile(H))
    out.append('</div></section>')
    return ''.join(out)

def place_modal(H, cfg, section):
    if section == 'wales':
        title = 'Wales, Britain'
        specific = specific_tile(H, 'Virtual reconstruction · AR glasses', '/wales/', 'holo-ghf1-098')
    else:
        title = 'Patagonia, Argentina'
        special = [
            ('Great House II · physical reconstruction', '/argentina/#house', 'nfa:0157'),
            ('Wedding venue', '/argentina/#book', 'nfa:0100'),
            ('B&B · guest rooms', '/argentina/#book', 'nfa:0059'),
            ('Stables', '/argentina/#house', 'nfa:0016'),
            ('Barn and cottage', '/argentina/#house', 'nfa:0019'),
            ('Museum', '/argentina/#museum', 'nfa:0089'),
        ]
        specific = ''.join(specific_tile(H, t, u, im) for t, u, im in special)
    return (f'<dialog class="land-modal" id="modal-{E(section)}" aria-labelledby="modal-{E(section)}-title">'
            f'<div class="land-modal-inner"><div class="land-modal-head">'
            f'<h2 id="modal-{E(section)}-title">{E(title)}</h2>'
            f'<button type="button" class="land-modal-close" data-close-modal aria-label="Close">×</button></div>'
            f'<div class="land-modal-content">'
            f'<section class="land-app-section land-specific"><h3>For this place</h3>'
            f'<div class="land-app-grid">{specific}</div></section>'
            f'{modal_apps(H, cfg, section)}'
            f'</div></div></dialog>')

def network_page(H):
    image = app_image(H, 'network-datacentre')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Network · Coming soon</title><meta name="description" content="Cedwyn Network — coming soon.">
<style>
*{{box-sizing:border-box}}html,body{{margin:0;min-height:100%;background:#0c1117;color:#f3f6f8;font:16px/1.5 system-ui,sans-serif}}
main{{min-height:100svh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:20px;text-align:center}}
img{{display:block;width:min(920px,100%);max-height:68vh;object-fit:cover;border-radius:14px;border:1px solid #34414d}}
h1{{margin:20px 0 2px;font-size:clamp(30px,6vw,56px);font-weight:600}}p{{margin:0;color:#aebdca;letter-spacing:.12em;text-transform:uppercase;font-size:13px}}
</style></head><body><main><img src="{E(image)}" alt="Rows of server racks in a data centre"><h1>Network</h1><p>Coming soon</p></main></body></html>'''

def landing(sections, S, cfg, H):
    l = 'en'; n = len(cfg['themes']); T = base_T(sections, S, cfg, None, H)
    pre = ("<script>(function(){try{var p=sessionStorage.getItem('cedwyn-land-lang');var l=/^(en|cy|es)$/.test(p||'')?p:'en';window.__cedwynLang=l;"
           "try{localStorage.setItem('ghf_lang',l)}catch(e){}var s=location.protocol==='https:'?'; Secure':'';var c='ghf_lang='+l+'; path=/; max-age=31536000; SameSite=Lax'+s;document.cookie=c;"
           "if(/(^|\\.)bucklerfamily\\.estate$/.test(location.hostname))document.cookie=c+'; domain=.bucklerfamily.estate';"
           "if(!/[?&]lang=/.test(location.search)&&history.replaceState)history.replaceState(null,'',location.pathname+'?lang='+l+location.hash)}catch(e){}})();</script>")
    wales_src = img(H, 'tile-wales')
    patagonia_src = img(H, 'tile-patagonia')
    body = f"""
<body data-cedwyn-page="landing">
<main class="wrap hv" data-no-translate>
<div class="hv-land"><a class="hv-eb" style="margin-bottom:10px" href="/ebooks/?utm_source=home&amp;utm_medium=button&amp;utm_campaign=sf27"><span>E-books · first editions free</span><span class="ar" aria-hidden="true">→</span></a><div class="hv-tiles" aria-label="Choose a place">
<button type="button" class="land-place" data-open-modal="modal-wales" aria-haspopup="dialog" aria-controls="modal-wales">
<img src="{E(wales_src)}" alt="" fetchpriority="high"><span class="land-place-label">Wales, Britain</span></button>
<button type="button" class="land-place" data-open-modal="modal-argentina" aria-haspopup="dialog" aria-controls="modal-argentina">
<img src="{E(patagonia_src)}" alt="" fetchpriority="high"><span class="land-place-label">Patagonia, Argentina</span></button>
</div>
</div>
{place_modal(H, cfg, 'wales')}
{place_modal(H, cfg, 'argentina')}
</main>
<script>
(function(){{
var openers=[].slice.call(document.querySelectorAll('[data-open-modal]'));
openers.forEach(function(button){{
 button.addEventListener('click',function(){{
  var dialog=document.getElementById(button.getAttribute('data-open-modal'));
  if(!dialog)return;
  if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','');
  var close=dialog.querySelector('[data-close-modal]');if(close)close.focus();
 }});
}});
[].forEach.call(document.querySelectorAll('.land-modal'),function(dialog){{
 var close=dialog.querySelector('[data-close-modal]');
 if(close)close.addEventListener('click',function(){{if(typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open')}});
 dialog.addEventListener('click',function(e){{if(e.target===dialog){{if(typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open')}}}});
 dialog.addEventListener('close',function(){{
  var opener=document.querySelector('[aria-controls="'+dialog.id+'"]');if(opener)opener.focus();
 }});
 dialog.addEventListener('cancel',function(){{}});
}});
}})();
</script>
<script>{JS}</script>
</body>
</html>
"""
    out = page(sections, 'Cedwyn Estate', 'Select Wales, Britain or Patagonia, Argentina.', l, '/cedwyn/home/', None, T, n, body)
    out = out.replace('</style>', LANDING_CSS + '</style>', 1)
    return out.replace('<head>\n', '<head>\n' + pre + '\n', 1)

VOUCHERS = [  # the Stripe voucher links of the retired /wales/tour/ page (Sion 08:08 GMT 26 Oct 2026: purge /wales/tour/, keep /wales/#stop-1)
    ('w_v1', 'https%3A%2F%2Fbuy.stripe.com%2FbJecN60ht4U74a88sD6Zy0j', {'en': 'Gift voucher · one guest £25', 'cy': 'Taleb rodd · un gwestai £25', 'es': 'Vale regalo · una persona £25'}),
    ('w_v2', 'https%3A%2F%2Fbuy.stripe.com%2F6oUcN6aW786jfSQ7oz6Zy0k', {'en': 'Gift voucher · two guests £45', 'cy': 'Taleb rodd · dau westai £45', 'es': 'Vale regalo · dos personas £45'}),
    ('w_v4', 'https%3A%2F%2Fbuy.stripe.com%2F7sY14o1lxeuH6ig38j6Zy0l', {'en': 'Gift voucher · group of four £90', 'cy': 'Taleb rodd · grŵp o bedwar £90', 'es': 'Vale regalo · grupo de cuatro £90'})]
VOUCHER_TERMS = {'en': 'Voucher terms', 'cy': 'Telerau’r daleb', 'es': 'Condiciones del vale'}

def wales(sections, S, cfg, H):
    l = 'cy'; n = len(cfg['themes']); T = base_T(sections, S, cfg, 'wales', H)
    st = H['stops']; ns = len(st)
    stops = ''.join(stop_html(H, T, l, i, s, ns) for i, s in enumerate(st))
    mp = tour_map(H, T, l)
    mn, gr = menu(H, T, cfg, l, 'wales')
    # gift vouchers (moved here 26 Oct 2026 from the retired /wales/tour/ page, same Stripe links via the archive route) - Sion's Tab agent
    vouchers = ''.join(f'<a class="hv-btn{" pri" if i == 0 else ""}" href="/wayback/go/?u={u}" rel="noopener">{lt(T, d, l, k)}</a>' for i, (k, u, d) in enumerate(VOUCHERS))
    body = f"""
<body data-cedwyn-page="wales">
<main class="wrap hv" data-no-translate>{LB_CSS}
<header class="hv-hero"><img src="{img(H,'wales-hero-house')}" width="1280" height="725" alt="" fetchpriority="high"><span class="hv-tag" data-i18n="ai_tag">{E(tx(T,'ai_tag',l))}</span>
<div class="hb"><p class="eyebrow" style="color:#ddd" data-i18n="w_kick">{E(tx(T,'w_kick',l))}</p><h1 data-i18n="w_h1">{E(tx(T,'w_h1',l))}</h1></div></header>
<h2 data-i18n="w_h2">{E(tx(T,'w_h2',l))}</h2>
{headlines(H, T, l, 'wales', lead=f'<p class="lede" data-i18n="w_lede">{E(tx(T,"w_lede",l))}</p>', tail=f'<div class="hv-hl" id="no-museum"><b data-i18n="w_nomuseum_h">{E(tx(T,"w_nomuseum_h",l))}</b><p data-i18n="w_nomuseum_p">{E(tx(T,"w_nomuseum_p",l))}</p></div>')}
<div class="hv-btns"><a class="hv-btn pri" href="#tour" data-hv-go="0" data-i18n="w_start">{E(tx(T,'w_start',l))}</a><a class="hv-btn" href="#shop" data-i18n="w_tickets">{E(tx(T,'w_tickets',l))}</a><a class="hv-btn" href="#menu" data-i18n="w_menu">{E(tx(T,'w_menu',l))}</a></div>
{mn}
<section id="route"><h2 data-i18n="w_map_h">{E(tx(T,'w_map_h',l))}</h2><p class="mut" data-i18n="w_map_p">{E(tx(T,'w_map_p',l))}</p>{mp}</section>
<section id="tour">{stops}
<div class="hv-nav"><button type="button" class="hv-btn" id="hv-prev" data-i18n="w_prev">{E(tx(T,'w_prev',l))}</button><span id="hv-cnt" class="mut">1 / {ns}</span>
<button type="button" class="hv-btn" id="hv-say" data-i18n="w_listen">{E(tx(T,'w_listen',l))}</button><button type="button" class="hv-btn pri" id="hv-next" data-i18n="w_next">{E(tx(T,'w_next',l))}</button></div></section>
<section id="shop"><h2 data-i18n="w_shop_h">{E(tx(T,'w_shop_h',l))}</h2><p data-i18n="w_shop_p">{E(tx(T,'w_shop_p',l))}</p>
<div class="hv-btns" id="vouchers">{vouchers}<a class="hv-btn" href="/ebooks/" data-i18n="w_ebooks">{E(tx(T,'w_ebooks',l))}</a></div>
<p class="mut"><a href="/wales/vouchers/terms/">{lt(T, VOUCHER_TERMS, l, 'w_vterms')}</a></p></section>
<section><a class="hv-btn" style="width:100%;justify-content:flex-start;min-height:64px;border-radius:12px" href="/argentina/?lang=es" hreflang="es"><span><b data-i18n="w_cross_h">{E(tx(T,'w_cross_h',l))}</b><br><span class="mut" data-i18n="w_cross_p">{E(tx(T,'w_cross_p',l))}</span></span></a></section>
<p class="endnote"><a href="/" data-i18n="home">{E(tx(T,'home',l) or 'Home')}</a> · <a href="/explore/" data-i18n="land_more">{E(tx(T,'land_more',l))}</a></p>
</main>
<script>{JS}</script>{LB_JS}
</body>
</html>
"""
    return page(sections, 'Cedwyn Estate, Wales · augmented-reality guided tour', 'Cedwyn Estate, Wales: an augmented-reality guided tour from Tŷ Mawr, the former manorial house at Llandough, to Lavernock Point. Every fact linked to its record.', l, '/wales/', 'wales', T, n, body)

# ---------- /argentina/ images: the Garden Gallery's NFT pieces (Sion, WhatsApp 08:16 GMT 27 Oct 2026: "The images on this page
# should be all the ones from nft ... Except any with excessive flowers"). Every /nft-art/ piece except the flower-heavy ones:
# the 73 restored v0.0.2 pieces plus the unrestored pieces the flower audit found clear, less four where flowers still fill the
# frame (NFA-0065, NFA-0066, NFA-0104, NFA-0125). Images are the gallery's own /nft-art/ files, never copies; captions are each
# piece's own title. Restored Tŷ Mawr pieces belong on the Patagonia/Argentina side only, never on Wales pages. Text and pictures
# alternate: after each block of text one picture shows, and a sideways swipe moves to the next one in that row. - Sion's Tab agent
ARG_NFT = {
    'NFA-0094': ('The Long Farmhouse', '/nft-art/art/nfa-0094-v0.0.2.webp', '/nft-art/art/nfa-0094-v0.0.2-t.webp', 1200, 1200),
    'NFA-0059': ('The Quilted Bedroom', '/nft-art/art/nfa-0059-v0.0.2.webp', '/nft-art/art/nfa-0059-v0.0.2-t.webp', 1200, 800),
    'NFA-0141': ('The Long Cottage', '/nft-art/art/nfa-0141-v0.0.2.webp', '/nft-art/art/nfa-0141-v0.0.2-t.webp', 1200, 1200),
    'NFA-0107': ('From Above', '/nft-art/art/nfa-0107.webp', '/nft-art/art/nfa-0107-t.webp', 1200, 800),
    'NFA-0100': ('Tables for the Party', '/nft-art/art/nfa-0100-v0.0.2.webp', '/nft-art/art/nfa-0100-v0.0.2-t.webp', 1200, 1200),
    'NFA-0157': ('The Farmhouse Over the Wall', '/nft-art/art/nfa-0157-v0.0.2.webp', '/nft-art/art/nfa-0157-v0.0.2-t.webp', 1200, 1200),
    'NFA-0035': ('Lime-Washed House', '/nft-art/art/nfa-0035-v0.0.2.webp', '/nft-art/art/nfa-0035-v0.0.2-t.webp', 1200, 1200),
    'NFA-0026': ('The Gable End', '/nft-art/art/nfa-0026-v0.0.2.webp', '/nft-art/art/nfa-0026-v0.0.2-t.webp', 1200, 1200),
    'NFA-0076': ('The House Over the Hedge', '/nft-art/art/nfa-0076-v0.0.2.webp', '/nft-art/art/nfa-0076-v0.0.2-t.webp', 1200, 1200),
    'NFA-0032': ('The Old Porch', '/nft-art/art/nfa-0032-v0.0.2.webp', '/nft-art/art/nfa-0032-v0.0.2-t.webp', 1200, 1200),
    'NFA-0011': ('Fields of 1824, Replanted', '/nft-art/art/nfa-0011.webp', '/nft-art/art/nfa-0011-t.webp', 816, 816),
    'NFA-0046': ('The Field Plan in Bloom', '/nft-art/art/nfa-0046.webp', '/nft-art/art/nfa-0046-t.webp', 1200, 900),
    'NFA-0111': ('The Estate in Flower', '/nft-art/art/nfa-0111.webp', '/nft-art/art/nfa-0111-t.webp', 800, 1200),
    'NFA-0112': ('Boundaries in Bloom', '/nft-art/art/nfa-0112.webp', '/nft-art/art/nfa-0112-t.webp', 800, 1200),
    'NFA-0137': ('The House Plan in Flower', '/nft-art/art/nfa-0137.webp', '/nft-art/art/nfa-0137-t.webp', 1200, 900),
    'NFA-0138': ('The Kitchen Garden Plan', '/nft-art/art/nfa-0138.webp', '/nft-art/art/nfa-0138-t.webp', 1200, 800),
    'NFA-0047': ('The Valley Fold', '/nft-art/art/nfa-0047.webp', '/nft-art/art/nfa-0047-t.webp', 800, 1200),
    'NFA-0093': ('The Village Track', '/nft-art/art/nfa-0093-v0.0.2.webp', '/nft-art/art/nfa-0093-v0.0.2-t.webp', 1200, 1200),
    'NFA-0115': ('The Bend by the Cottages', '/nft-art/art/nfa-0115-v0.0.2.webp', '/nft-art/art/nfa-0115-v0.0.2-t.webp', 1200, 1200),
    'NFA-0114': ('Two Barns Beyond the Meadow', '/nft-art/art/nfa-0114-v0.0.2.webp', '/nft-art/art/nfa-0114-v0.0.2-t.webp', 1200, 1200),
    'NFA-0043': ('Lane to the Paddock', '/nft-art/art/nfa-0043-v0.0.2.webp', '/nft-art/art/nfa-0043-v0.0.2-t.webp', 1200, 1200),
    'NFA-0050': ('The Chapel Walls', '/nft-art/art/nfa-0050-v0.0.2.webp', '/nft-art/art/nfa-0050-v0.0.2-t.webp', 1200, 800),
    'NFA-0090': ('Below the Chapel Windows', '/nft-art/art/nfa-0090-v0.0.2.webp', '/nft-art/art/nfa-0090-v0.0.2-t.webp', 1200, 1200),
    'NFA-0106': ('The Churchyard Meadow', '/nft-art/art/nfa-0106-v0.0.2.webp', '/nft-art/art/nfa-0106-v0.0.2-t.webp', 900, 1200),
    'NFA-0121': ('By the Churchyard Wall', '/nft-art/art/nfa-0121-v0.0.2.webp', '/nft-art/art/nfa-0121-v0.0.2-t.webp', 1200, 1200),
    'NFA-0057': ('The Porch Door', '/nft-art/art/nfa-0057-v0.0.2.webp', '/nft-art/art/nfa-0057-v0.0.2-t.webp', 1200, 1200),
    'NFA-0122': ('The Gabled Porch', '/nft-art/art/nfa-0122-v0.0.2.webp', '/nft-art/art/nfa-0122-v0.0.2-t.webp', 1200, 1200),
    'NFA-0038': ('Parterre and Porch', '/nft-art/art/nfa-0038-v0.0.2.webp', '/nft-art/art/nfa-0038-v0.0.2-t.webp', 1200, 1200),
    'NFA-0014': ('The Yard Gate in June', '/nft-art/art/nfa-0014-v0.0.2.webp', '/nft-art/art/nfa-0014-v0.0.2-t.webp', 1200, 1200),
    'NFA-0048': ('Through the Garden Gate', '/nft-art/art/nfa-0048-v0.0.2.webp', '/nft-art/art/nfa-0048-v0.0.2-t.webp', 1200, 1200),
    'NFA-0023': ('Chimneys Through the Pear', '/nft-art/art/nfa-0023-v0.0.2.webp', '/nft-art/art/nfa-0023-v0.0.2-t.webp', 1200, 1200),
    'NFA-0092': ('White Gable, White Blossom', '/nft-art/art/nfa-0092-v0.0.2.webp', '/nft-art/art/nfa-0092-v0.0.2-t.webp', 1200, 1200),
    'NFA-0126': ('The Cottage Gable', '/nft-art/art/nfa-0126-v0.0.2.webp', '/nft-art/art/nfa-0126-v0.0.2-t.webp', 1200, 1200),
    'NFA-0133': ('The Blossom Lawn', '/nft-art/art/nfa-0133-v0.0.2.webp', '/nft-art/art/nfa-0133-v0.0.2-t.webp', 1200, 1200),
    'NFA-0144': ('The Terrace Steps', '/nft-art/art/nfa-0144-v0.0.2.webp', '/nft-art/art/nfa-0144-v0.0.2-t.webp', 1200, 1200),
    'NFA-0123': ('The Narrow Garden Path', '/nft-art/art/nfa-0123-v0.0.2.webp', '/nft-art/art/nfa-0123-v0.0.2-t.webp', 1200, 1200),
    'NFA-0021': ('Field Road Home', '/nft-art/art/nfa-0021-v0.0.2.webp', '/nft-art/art/nfa-0021-v0.0.2-t.webp', 1200, 800),
    'NFA-0044': ("The Visitor's Car", '/nft-art/art/nfa-0044-v0.0.2.webp', '/nft-art/art/nfa-0044-v0.0.2-t.webp', 1200, 1200),
    'NFA-0150': ('The Blue Van and Trailer', '/nft-art/art/nfa-0150-v0.0.2.webp', '/nft-art/art/nfa-0150-v0.0.2-t.webp', 1200, 1200),
    'NFA-0113': ('The Old Cart', '/nft-art/art/nfa-0113-v0.0.2.webp', '/nft-art/art/nfa-0113-v0.0.2-t.webp', 1200, 1200),
    'NFA-0117': ('Cartwheel Row', '/nft-art/art/nfa-0117-v0.0.2.webp', '/nft-art/art/nfa-0117-v0.0.2-t.webp', 1200, 800),
    'NFA-0052': ('The Hay Rake', '/nft-art/art/nfa-0052-v0.0.2.webp', '/nft-art/art/nfa-0052-v0.0.2-t.webp', 1200, 1200),
    'NFA-0051': ('Tractor by the Barn', '/nft-art/art/nfa-0051-v0.0.2.webp', '/nft-art/art/nfa-0051-v0.0.2-t.webp', 1200, 1200),
    'NFA-0128': ('Through to the Hall', '/nft-art/art/nfa-0128-v0.0.2.webp', '/nft-art/art/nfa-0128-v0.0.2-t.webp', 1200, 1200),
    'NFA-0071': ('The Lamp in the Hall', '/nft-art/art/nfa-0071-v0.0.2.webp', '/nft-art/art/nfa-0071-v0.0.2-t.webp', 1200, 1200),
    'NFA-0072': ('The Tall Doorway', '/nft-art/art/nfa-0072-v0.0.2.webp', '/nft-art/art/nfa-0072-v0.0.2-t.webp', 1200, 1200),
    'NFA-0087': ('The Dining Room Door', '/nft-art/art/nfa-0087-v0.0.2.webp', '/nft-art/art/nfa-0087-v0.0.2-t.webp', 1200, 1200),
    'NFA-0088': ('The Inglenook', '/nft-art/art/nfa-0088-v0.0.2.webp', '/nft-art/art/nfa-0088-v0.0.2-t.webp', 1200, 1200),
    'NFA-0060': ('The Fireside Corner', '/nft-art/art/nfa-0060-v0.0.2.webp', '/nft-art/art/nfa-0060-v0.0.2-t.webp', 1200, 800),
    'NFA-0016': ('Stable Row at Noon', '/nft-art/art/nfa-0016-v0.0.2.webp', '/nft-art/art/nfa-0016-v0.0.2-t.webp', 1200, 1200),
    'NFA-0029': ('The Barn Door, Evening', '/nft-art/art/nfa-0029-v0.0.2.webp', '/nft-art/art/nfa-0029-v0.0.2-t.webp', 1200, 1200),
    'NFA-0019': ('Long Barn, Long Grass', '/nft-art/art/nfa-0019-v0.0.2.webp', '/nft-art/art/nfa-0019-v0.0.2-t.webp', 1200, 900),
    'NFA-0055': ('Barn End and Meadow', '/nft-art/art/nfa-0055-v0.0.2.webp', '/nft-art/art/nfa-0055-v0.0.2-t.webp', 1200, 1200),
    'NFA-0020': ('Cart Track and Barrel', '/nft-art/art/nfa-0020-v0.0.2.webp', '/nft-art/art/nfa-0020-v0.0.2-t.webp', 1200, 900),
    'NFA-0067': ('Water Butt and Shed', '/nft-art/art/nfa-0067-v0.0.2.webp', '/nft-art/art/nfa-0067-v0.0.2-t.webp', 1200, 1200),
    'NFA-0089': ('The China Cabinets', '/nft-art/art/nfa-0089-v0.0.2.webp', '/nft-art/art/nfa-0089-v0.0.2-t.webp', 1200, 1200),
    'NFA-0131': ('Brass on the Sideboard', '/nft-art/art/nfa-0131-v0.0.2.webp', '/nft-art/art/nfa-0131-v0.0.2-t.webp', 1200, 1200),
    'NFA-0130': ('The Long-Case Clock', '/nft-art/art/nfa-0130-v0.0.2.webp', '/nft-art/art/nfa-0130-v0.0.2-t.webp', 1200, 1200),
    'NFA-0069': ('A Wall of Small Pictures', '/nft-art/art/nfa-0069-v0.0.2.webp', '/nft-art/art/nfa-0069-v0.0.2-t.webp', 1200, 1200),
    'NFA-0058': ('The Dresser Room', '/nft-art/art/nfa-0058-v0.0.2.webp', '/nft-art/art/nfa-0058-v0.0.2-t.webp', 1200, 900),
    'NFA-0070': ('The Back Kitchen', '/nft-art/art/nfa-0070-v0.0.2.webp', '/nft-art/art/nfa-0070-v0.0.2-t.webp', 1200, 1200),
    'NFA-0145': ('The Kitchen Hearth', '/nft-art/art/nfa-0145-v0.0.2.webp', '/nft-art/art/nfa-0145-v0.0.2-t.webp', 1200, 1200),
    'NFA-0077': ('The Green Quilt', '/nft-art/art/nfa-0077-v0.0.2.webp', '/nft-art/art/nfa-0077-v0.0.2-t.webp', 1200, 1200),
    'NFA-0082': ('The Old Bedstead', '/nft-art/art/nfa-0082-v0.0.2.webp', '/nft-art/art/nfa-0082-v0.0.2-t.webp', 1200, 1200),
    'NFA-0146': ('The Pink Bedhead', '/nft-art/art/nfa-0146-v0.0.2.webp', '/nft-art/art/nfa-0146-v0.0.2-t.webp', 1200, 1200),
    'NFA-0083': ('The Window Seat', '/nft-art/art/nfa-0083-v0.0.2.webp', '/nft-art/art/nfa-0083-v0.0.2-t.webp', 1200, 1200),
    'NFA-0080': ('Window Over the Valley', '/nft-art/art/nfa-0080-v0.0.2.webp', '/nft-art/art/nfa-0080-v0.0.2-t.webp', 1200, 1200),
    'NFA-0078': ('The Turn of the Stair', '/nft-art/art/nfa-0078-v0.0.2.webp', '/nft-art/art/nfa-0078-v0.0.2-t.webp', 1200, 1200),
    'NFA-0079': ('The Landing', '/nft-art/art/nfa-0079-v0.0.2.webp', '/nft-art/art/nfa-0079-v0.0.2-t.webp', 1200, 1200),
    'NFA-0129': ('The Banister', '/nft-art/art/nfa-0129-v0.0.2.webp', '/nft-art/art/nfa-0129-v0.0.2-t.webp', 1200, 1200),
    'NFA-0152': ('The Curving Stair', '/nft-art/art/nfa-0152-v0.0.2.webp', '/nft-art/art/nfa-0152-v0.0.2-t.webp', 1200, 1200),
    'NFA-0084': ('Stone Steps Up', '/nft-art/art/nfa-0084-v0.0.2.webp', '/nft-art/art/nfa-0084-v0.0.2-t.webp', 1200, 1200),
    'NFA-0153': ('Steps Under the Lintel', '/nft-art/art/nfa-0153-v0.0.2.webp', '/nft-art/art/nfa-0153-v0.0.2-t.webp', 1200, 1200),
    'NFA-0147': ('The Cottage Window', '/nft-art/art/nfa-0147-v0.0.2.webp', '/nft-art/art/nfa-0147-v0.0.2-t.webp', 1200, 1200),
    'NFA-0148': ('The White Door', '/nft-art/art/nfa-0148-v0.0.2.webp', '/nft-art/art/nfa-0148-v0.0.2-t.webp', 1200, 1200),
    'NFA-0149': ('The Hall Door', '/nft-art/art/nfa-0149-v0.0.2.webp', '/nft-art/art/nfa-0149-v0.0.2-t.webp', 1200, 1200),
    'REC-0001': ('Tŷ Mawr, reconstruction from the 1974 measured survey', '/_cedwyn/halves/img/ty-mawr-1974-reconstruction.webp', '/_cedwyn/halves/img/ty-mawr-1974-reconstruction-t.webp', 1200, 1200),
}
# Survey drawings shown among the pieces (27 Oct 2026, Sion 11:34 GMT: four pieces that are not the farm came out, NFA-0139,
# NFA-0049, NFA-0103, NFA-0081; NFA-0015 showed the right farm poorly and is replaced by REC-0001, a line drawing made from the
# H.J. Thomas measured plan and sketch plan, RCAHMW NA/GL/89/208, visited 26 Apr 1974; massing from a 1988 press photograph;
# roof height estimated. Source files: work/nft-art/reconstruction/). - Sion's Tab agent
ARG_REC = {
    'REC-0001': {'en': 'Tŷ Mawr: reconstruction from the 1974 measured survey; roof height estimated',
                 'cy': 'Tŷ Mawr: ail-greu o arolwg mesuredig 1974; uchder y to wedi’i amcangyfrif',
                 'es': 'Tŷ Mawr: reconstrucción a partir del levantamiento medido de 1974; altura del tejado estimada'},
}
ARG_NFT_HERO = 'NFA-0094'
ARG_NFT_VENUE = {'room': 'NFA-0059', 'cottage': 'NFA-0141', 'villa': 'NFA-0107', 'wed': 'NFA-0100'}
ARG_NFT_SLOTS = {
    'hl0': ['NFA-0157', 'NFA-0035', 'NFA-0026', 'NFA-0076', 'NFA-0032'],
    'hl1': ['NFA-0011', 'NFA-0046', 'NFA-0111', 'NFA-0112', 'NFA-0137', 'NFA-0138'],
    'hl2': ['NFA-0047', 'NFA-0093', 'NFA-0115', 'NFA-0114', 'NFA-0043'],
    'hl3': ['NFA-0050', 'NFA-0090', 'NFA-0106', 'NFA-0121'],
    'hl4': ['NFA-0057', 'NFA-0122', 'NFA-0038', 'NFA-0014', 'NFA-0048'],
    'hl5': ['NFA-0023', 'NFA-0092', 'NFA-0126', 'NFA-0133', 'NFA-0144', 'NFA-0123'],
    'lede': ['NFA-0021', 'NFA-0044', 'NFA-0150'],
    'menu': ['NFA-0113', 'NFA-0117', 'NFA-0052', 'NFA-0051'],
    'house': ['NFA-0128', 'NFA-0071', 'NFA-0072', 'NFA-0087', 'NFA-0088', 'NFA-0060'],
    'feats': ['NFA-0016', 'NFA-0029', 'NFA-0019', 'NFA-0055', 'NFA-0020', 'NFA-0067'],
    'museum': ['NFA-0089', 'NFA-0131', 'NFA-0130', 'NFA-0069', 'NFA-0058', 'NFA-0070', 'NFA-0145'],
    'book': ['NFA-0077', 'NFA-0082', 'NFA-0146', 'NFA-0083', 'NFA-0080'],
    'form': ['NFA-0078', 'NFA-0079', 'NFA-0129', 'NFA-0152', 'NFA-0084', 'NFA-0153', 'NFA-0147', 'NFA-0148', 'NFA-0149'],
    'retell': ['REC-0001'],
}
NFT_CSS = ('<style>.nf-s{display:flex;gap:10px;overflow-x:auto;overscroll-behavior-x:contain;scroll-snap-type:x mandatory;-webkit-overflow-scrolling:touch;margin:14px 0 18px;padding:0 0 6px}'
           '.nf-s>.nf-f{flex:0 0 86%;scroll-snap-align:start}.nf-s>.nf-f:only-child{flex-basis:100%}@media (min-width:783px){.nf-s>.nf-f{flex-basis:calc(50% - 5px)}}'
           '.nf-f{position:relative;margin:0;border-radius:10px;overflow:hidden;background:#111}.nf-f a{display:block;color:inherit;text-decoration:none}'
           '.nf-f img{width:100%;aspect-ratio:1/1;object-fit:cover;display:block}.nf-f figcaption{padding:6px 8px 8px;font-size:12.5px;line-height:1.3;color:#eee}'
           '.nf-f .hv-tag{top:8px;bottom:auto}.hv-hls>.nf-s{margin:4px 0 12px}</style>')

def nft_img(i, sizes='(min-width:783px) 560px, 86vw', eager=False, extra=''):
    t, im, tb, w, h = ARG_NFT[i]
    return (f'<img src="{tb}" srcset="{tb} 520w, {im} {w}w" sizes="{sizes}" width="{w}" height="{h}" alt="{E(t)}"'
            f'{" fetchpriority=high" if eager else " loading=lazy"} decoding="async"{extra}>')

def nft_strip(ids, T, l):
    """A row of small square thumbnails; each opens the full picture in the shared viewer (lb.js). The plain link to the
    piece in /nft-art/ stays as the no-script fallback. One artist's-impression label per row. A survey drawing (an id in
    ARG_REC, not an /nft-art/ piece) links to its own file and carries its own caption instead of the label. - Sion's Tab agent"""
    ids = [i for i in ids if i in ARG_NFT]
    if not ids: return ''
    def fig(i):
        t, im, tb, w, h = ARG_NFT[i]
        href = im if i in ARG_REC else f'/nft-art/#/{E(i)}'
        cap = lt(T, ARG_REC[i], l, 'rec_' + i.lower().replace('-', '_'), tag='figcaption') if i in ARG_REC else ''
        return (f'<figure class="nf-f"><a href="{href}" data-lb="{E(im)}">'
                f'<img src="{tb}" width="{w}" height="{h}" alt="{E(t)}" loading="lazy" decoding="async"></a>{cap}</figure>')
    tag = f'<p class="nf-tg" data-i18n="ai_tag">{E(tx(T,"ai_tag",l))}</p>' if any(i not in ARG_REC for i in ids) else ''
    return '<div class="nf-s nf-th">' + ''.join(fig(i) for i in ids) + tag + '</div>'


def nft_between(html, strips):
    """Put one strip after each headline block (between clamp.js read-more blocks, never inside one)."""
    segs = html.split('<div class="hv-hl">')
    if len(segs) < 2: return html
    out = segs[0]
    for k, s in enumerate(segs[1:]):
        st = strips[k] if k < len(strips) else ''
        if k == len(segs) - 2 and s.endswith('</section>'):
            out += '<div class="hv-hl">' + s[:-len('</section>')] + st + '</section>'
        else:
            out += '<div class="hv-hl">' + s + st
    return out

def argentina(sections, S, cfg, H):
    l = 'es'; n = len(cfg['themes']); T = base_T(sections, S, cfg, 'argentina', H)
    fc_card = ''
    try:
        import family_case
        T.update(family_case.strings()[0])
        if T.get('fc_link_h'):
            fc_card = (f'<a class="hv-btn" style="width:100%;justify-content:flex-start;min-height:64px;border-radius:12px" href="/argentina/caso/">'
                       f'<span><b data-i18n="fc_link_h">{E(tx(T,"fc_link_h",l))}</b><br><span class="mut" data-i18n="fc_link_p">{E(tx(T,"fc_link_p",l))}</span></span></a>')
    except Exception as e:
        print('halves: family_case not available:', e)
    if not fc_card:
        fc_card = f'<a class="hv-btn" href="/argentina/caso/" data-i18n="a_caso">{E(tx(T,"a_caso",l))}</a>'
    NS = ARG_NFT_SLOTS; st = lambda k: nft_strip(NS.get(k, []), T, l)
    g = st('feats')
    # Real vs augmented (Sion, WhatsApp 12:11 GMT 27 Oct 2026): in Patagonia the house, stables and barn are real buildings;
    # St Dochdwy's church and the Celtic cross appear in augmented reality. - Sion's Tab agent
    FEAT_RA = {1: 'real', 2: 'real', 3: 'real', 4: 'real', 6: 'real', 7: 'ar'}
    feats = ''.join(f'<li><span data-i18n="a_feat{i}">{E(tx(T,"a_feat"+str(i),l))}</span>'
                    + (f' <span class="hv-ra-b {"r" if FEAT_RA[i] == "real" else "a"}" data-i18n="ra_{FEAT_RA[i]}">{E(tx(T,"ra_"+FEAT_RA[i],l))}</span>' if i in FEAT_RA else '')
                    + '</li>' for i in range(1, 8) if tx(T, 'a_feat' + str(i), l))
    vimg = ARG_NFT_VENUE
    unit = {'room_night': '/', 'night': '/', 'day': '/'}
    vo = ''.join(f'<label class="hv-opt"><input type="radio" name="venue" value="{v["id"]}"{" checked" if v["id"] == "room" else ""}><img src="{ARG_NFT[vimg[v["id"]]][2]}" width="88" height="62" alt="" loading="lazy">'
                 f'<span><b data-i18n="v_{v["id"]}">{E(tx(T,"v_"+v["id"],l))}</b><small data-i18n="v_{v["id"]}_d">{E(tx(T,"v_"+v["id"]+"_d",l))}</small><span class="pr">£{v["price"]:,}</span></span></label>' for v in H['venues'])
    ap = '<option value="NONE" data-i18n="b_nofly">' + E(tx(T, 'b_nofly', l)) + '</option>' + ''.join(
        f'<option value="{a}"{" selected" if a == "LHR" else ""}>{E(nm)} ({a})' + (f' · £{p:,}' if p else '') + '</option>' if a != 'OTHER' else f'<option value="OTHER">…</option>' for a, nm, p in H['airports'])
    cars = ('<label class="hv-opt ro"><input type="radio" name="car" value="none"><span><b data-i18n="b_nocar">' + E(tx(T, 'b_nocar', l)) + '</b></span></label>' +
            ''.join(f'<label class="hv-opt ro"><input type="radio" name="car" value="{c}"{" checked" if c == "4x4" else ""}><span><b data-i18n="c_{c}">{E(tx(T,"c_"+c,l))}</b><span class="pr">£{p} </span><small data-i18n="b_perday">{E(tx(T,"b_perday",l))}</small></span></label>' for c, p in H['cars']))
    book = {'venues': H['venues'], 'airports': H['airports'], 'cars': H['cars']}
    mn, gr = menu(H, T, cfg, l, 'argentina')
    body = f"""
<body data-cedwyn-page="argentina">
<main class="wrap hv" data-no-translate style="--hv-a:#2f78b8;--hv-b:#F6B40E">
{NFT_CSS}{LB_CSS}<header class="hv-hero">{nft_img(ARG_NFT_HERO, sizes='(min-width:783px) 900px, 100vw', eager=True)}<span class="hv-tag" data-i18n="ai_tag">{E(tx(T,'ai_tag',l))}</span>
<div class="hb"><p class="eyebrow" style="color:#ddd" data-i18n="a_kick">{E(tx(T,'a_kick',l))}</p><h1 data-i18n="a_h1">{E(tx(T,'a_h1',l))}</h1><p style="margin:0" data-i18n="a_h2">{E(tx(T,'a_h2',l))}</p></div></header>
{nft_between(headlines(H, T, l, 'argentina'), [st('hl%d' % j) for j in range(len((H.get('headlines') or {}).get('argentina') or []))])}
<span class="soon" data-i18n="a_soon">{E(tx(T,'a_soon',l))}</span>
<p class="lede" data-i18n="a_lede">{E(tx(T,'a_lede',l))}</p>
{st('lede')}
<div class="hv-btns"><a class="hv-btn pri" href="#book" data-i18n="a_build">{E(tx(T,'a_build',l))}</a><a class="hv-btn" href="#museum" data-i18n="mu_h">{E(tx(T,'mu_h',l))}</a><a class="hv-btn" href="#menu" data-i18n="a_menu">{E(tx(T,'a_menu',l))}</a></div>
{mn}
{st('menu')}
<section id="house"><h2 data-i18n="a_house_h">{E(tx(T,'a_house_h',l))}</h2><p data-i18n="a_house_p">{E(tx(T,'a_house_p',l))}</p>
{st('house')}
<ul class="hv-feat">{feats}</ul>
{g}</section>
<section id="museum"><h2 data-i18n="mu_h">{E(tx(T,'mu_h',l))}</h2>
{st('museum')}
<p data-i18n="mu_p">{E(tx(T,'mu_p',l))}</p></section>
<section id="book"><h2 data-i18n="b_h">{E(tx(T,'b_h',l))}</h2><p data-i18n="b_p">{E(tx(T,'b_p',l))}</p>
{st('book')}
<form class="hv-bk" id="hv-book" novalidate>
<ol class="hv-steps"><li class="on" data-i18n="b_s1">{E(tx(T,'b_s1',l))}</li><li data-i18n="b_s2">{E(tx(T,'b_s2',l))}</li><li data-i18n="b_s3">{E(tx(T,'b_s3',l))}</li><li data-i18n="b_s4">{E(tx(T,'b_s4',l))}</li></ol>
<div class="hv-pane on" data-step="1"><h3 data-i18n="b_venue">{E(tx(T,'b_venue',l))}</h3><div class="hv-opts">{vo}</div>
<div class="hv-f"><label><span data-i18n="b_in">{E(tx(T,'b_in',l))}</span><input type="date" id="bk-in" name="in" required></label><label id="bk-outw"><span data-i18n="b_out">{E(tx(T,'b_out',l))}</span><input type="date" id="bk-out" name="out"></label>
<label><span data-i18n="b_guests">{E(tx(T,'b_guests',l))}</span><input type="number" id="bk-g" name="guests" min="1" max="120" value="2" inputmode="numeric"></label><label id="bk-rw"><span data-i18n="b_rooms">{E(tx(T,'b_rooms',l))}</span><input type="number" id="bk-r" name="rooms" min="1" max="10" value="1" inputmode="numeric"></label></div></div>
<div class="hv-pane" data-step="2"><h3 data-i18n="b_from">{E(tx(T,'b_from',l))}</h3><p class="mut" data-i18n="b_fly_d">{E(tx(T,'b_fly_d',l))}</p>
<div class="hv-1"><label><span data-i18n="b_from">{E(tx(T,'b_from',l))}</span><select name="fly" id="bk-fly">{ap}</select></label><label><span data-i18n="b_flyers">{E(tx(T,'b_flyers',l))}</span><input type="number" id="bk-fp" name="flyers" min="0" max="120" value="2" inputmode="numeric"></label></div></div>
<div class="hv-pane" data-step="3"><h3 data-i18n="b_car">{E(tx(T,'b_car',l))}</h3><div class="hv-opts">{cars}</div>
<div class="hv-1"><label><span data-i18n="b_pick">{E(tx(T,'b_pick',l))}</span><select id="bk-pick" name="pick"><option value="REL" data-i18n="p_rel">{E(tx(T,'p_rel',l))}</option><option value="PMY" data-i18n="p_pmy">{E(tx(T,'p_pmy',l))}</option></select></label></div></div>
<div class="hv-pane" data-step="4"><h3 data-i18n="b_s4">{E(tx(T,'b_s4',l))}</h3><ul class="hv-sum" id="bk-sum"></ul><p class="hv-ind" data-i18n="b_ind">{E(tx(T,'b_ind',l))}</p>
<div id="bk-form"><div class="hv-1"><label><span data-i18n="b_name">{E(tx(T,'b_name',l))}</span><input id="bk-nm" name="name" autocomplete="name" maxlength="80" required></label>
<label><span data-i18n="b_email">{E(tx(T,'b_email',l))}</span><input id="bk-em" type="email" name="email" autocomplete="email" maxlength="160" required></label>
<label><span data-i18n="b_note">{E(tx(T,'b_note',l))}</span><textarea id="bk-note" name="note" rows="2" maxlength="300"></textarea></label>
<label class="hv-ck"><input type="checkbox" id="bk-ok"><span><span data-i18n="b_ok">{E(tx(T,'b_ok',l))}</span> <a href="/dartboard/legal/" data-i18n="privacy">{E(tx(T,'privacy',l))}</a></span></label></div>
<p class="hv-err" id="bk-err2" role="alert" hidden></p><button type="submit" class="hv-btn pri" id="bk-send" data-i18n="b_send">{E(tx(T,'b_send',l))}</button></div>
<div class="hv-done" id="bk-done" role="status" hidden><p data-i18n="b_done">{E(tx(T,'b_done',l))}</p><b id="bk-ref"></b><p data-i18n="b_mc">{E(tx(T,'b_mc',l))}</p><p class="mut" data-i18n="b_done2">{E(tx(T,'b_done2',l))}</p></div></div>
<p class="hv-err" id="bk-err" role="alert" hidden></p>
<div class="hv-btns" style="justify-content:space-between"><button type="button" class="hv-btn" id="bk-back" hidden data-i18n="b_back">{E(tx(T,'b_back',l))}</button><button type="button" class="hv-btn pri" id="bk-next" data-i18n="b_cont">{E(tx(T,'b_cont',l))}</button></div>
</form>
{st('form')}</section>
<section id="retelling"><h2 data-i18n="a_retell_h">{E(tx(T,'a_retell_h',l))}</h2><p class="mut" data-i18n="a_retell_p">{E(tx(T,'a_retell_p',l))}</p>
{st('retell')}
{fc_card}
<div class="hv-btns"><a class="hv-btn" href="/argentina/thousand-cuts/" data-i18n="th_thousand-cuts">{E(tx(T,'th_thousand-cuts',l))}</a><a class="hv-btn" href="/argentina/story/" data-i18n="th_story">{E(tx(T,'th_story',l))}</a><a class="hv-btn" href="/argentina/research/timeline/" data-i18n="tl_link">{E(tx(T,'tl_link',l))}</a></div>
</section>
<section><a class="hv-btn" style="width:100%;justify-content:flex-start;min-height:64px;border-radius:12px" href="/wales/?lang=cy" hreflang="cy"><span><b data-i18n="a_cross_h">{E(tx(T,'a_cross_h',l))}</b><br><span class="mut" data-i18n="a_cross_p">{E(tx(T,'a_cross_p',l))}</span></span></a></section>
<p class="endnote"><a href="/" data-i18n="home">{E(tx(T,'home',l) or 'Home')}</a> · <a href="/explore/" data-i18n="land_more">{E(tx(T,'land_more',l))}</a></p>
</main>
<script>window.HV_BOOK={json.dumps(book, ensure_ascii=False)};</script>
<script>{JS}</script>{LB_JS}
</body>
</html>
"""
    out = page(sections, 'Cedwyn Estate II, Patagonia · Great House II retreat', 'Cedwyn Estate II: Great House II at Puerto Madryn, Patagonia. A replica of the Great House: rooms, cottage, whole-house hire, weddings, stables, barn and museum. Build a trip and send a pre-order request.', l, '/patagonia/', 'argentina', T, n, body)
    return out.replace('--a:#00843D;--b:#C8102E', '--a:#4E8CC8;--b:#F6B40E', 1)

WALES_NO_FARM = re.compile(r'\b(?:farm|fferm|granja)\b', re.I)

def check_wales_house(text):
    """Wales half (Sion 23:39): Tŷ Mawr is a former manorial house, never a farm. Allowed: the quoted RCAHMW words about
    Brynwell ("a medieval farmhouse") and the Cadw building name; every other 'farm' in the visible tour copy fails the build."""
    m = re.search(r'<main\b.*?</main>', text, flags=re.S)
    body = re.sub(r'<script\b.*?</script>', ' ', m.group(0) if m else text, flags=re.S)
    body = re.sub(r'<[^>]+>', ' ', body)
    hits = [x for x in WALES_NO_FARM.findall(body)]
    assert not hits, 'wales page calls the house a farm: %s' % hits[:5]

LEGAL = re.compile(r'EWCA|\bs\.\s?\d|\bAct\b|\bLRA\b|\[19\d\d\]|\bEV-\d|High Court|Court of Appeal|registered proprietor|Order 14|possession order|14464|Uchel Lys|Llys Apêl|Tribunal Superior|Tribunal de Apelaci')

def check_tour_citations(text, H):
    """Sion 02:12 GMT 26 Oct: legal material only in the Court and lawfare stop; the rest of the tour is narration."""
    m = re.search(r'<main\b.*?</main>', text, flags=re.S); body = m.group(0) if m else text
    body = re.sub(r'<article class="hv-stop[^"]*"[^>]*data-stop="court".*?</article>', ' ', body, flags=re.S)
    body = re.sub(r'<script\b.*?</script>', ' ', body, flags=re.S); body = re.sub(r'<[^>]+>', ' ', body)
    bad = LEGAL.findall(body)
    for s in H['stops']:
        if s['id'] == 'court': continue
        for k in ('name', 'place', 'overlay', 'story', 'now', 'open'):
            for lang, v in (s.get(k) or {}).items(): bad += LEGAL.findall(v)
        if s.get('recs'): bad.append('recs on ' + s['id'])
    assert not bad, 'wales tour carries legal citations outside the court stop: %s' % bad[:6]

def run(dist, cfg):
    dist = pathlib.Path(dist)
    import sections, agent_footer, unsub   # unsub: passages marked substantiated:false render small italic (tools/unsub.py)
    H = json.load(open(ROOT / 'data' / 'halves.json', encoding='utf-8'))
    S = json.load(open(ROOT / 'sections.json', encoding='utf-8'))
    pages = {dist / 'index.html': landing(sections, S, cfg, H),
             dist / 'wales' / 'index.html': wales(sections, S, cfg, H),
             dist / 'argentina' / 'index.html': argentina(sections, S, cfg, H),
             dist / 'network' / 'index.html': network_page(H)}
    for pth, txt in pages.items():
        pth.parent.mkdir(parents=True, exist_ok=True); pth.write_text(unsub.html(txt), encoding='utf-8')
        # The Network placeholder is a deliberately unlinked, link-free page; other generated pages keep the agent footer.
        if pth.parent.name != 'network': agent_footer.inject(pth, False)
    w = (dist / 'wales' / 'index.html').read_text(encoding='utf-8')
    sections.check_wales(w); sections.check_wales((dist / 'index.html').read_text(encoding='utf-8')); check_wales_house(w); check_tour_citations(w, H)
    for pth in pages:
        t = pth.read_text(encoding='utf-8'); m = re.search(r'<main\b.*?</main>', t, flags=re.S)
        out = [h for h in re.findall(r'href="([^"]+)"', m.group(0)) if re.match(r'^(https?:)?//', h)]
        assert not out, 'halves: outbound link on %s: %s' % (pth, out[:3])
    print('halves ok:', len(H['stops']), 'tour stops;', 'menu', {k: len(v) for k, v in grouping(H, cfg, 'wales').items()}, 'wales /', {k: len(v) for k, v in grouping(H, cfg, 'argentina').items()}, 'argentina')

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    run(sys.argv[1] if len(sys.argv) > 1 else 'dist', json.load(open(ROOT / 'themes.json')))
