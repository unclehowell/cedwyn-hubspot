#!/usr/bin/env python3
"""home.py - the Cedwyn home page (/): the oak board of the family estate directory (the look of the former
bucklerfamily.estate home), with three ways in - Wales, Argentina, Cyberspace. Whichever way is opened, the same
submenu appears: every theme, gathered in the groups named in themes.json ("groups", and each theme's "group").
themes.json is the one source: theme order, titles, groups and the three ways in are read from it, nothing is
listed here. Every link is an internal /<theme>/ route. - Sion's Tab agent"""
import html, json, sys, pathlib

CSS = '\n:root{color-scheme:dark;--page:#130905;--wood1:#321a0d;--wood2:#241006;--wood3:#4b2914;--gold:#f0d48a;--gold2:#b98b38;--ink:#f6e8c6;--muted:#c6ab73;--hair:rgba(244,211,137,.3);--shade:rgba(0,0,0,.48)}\n*{box-sizing:border-box}\nhtml{background:var(--page);scroll-behavior:smooth}\nbody{margin:0;min-height:100vh;background:radial-gradient(ellipse at 50% 0%,#402211 0%,#1b0e07 48%,#100703 100%);color:var(--ink);font:16px/1.55 Georgia,"Times New Roman",serif;padding:16px 0 44px}\nbutton,a{font:inherit}\na{color:inherit}\na:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid #fff0b8;outline-offset:4px}\n.page-kicker{margin:0 auto 12px;text-align:center;color:#b98e45;letter-spacing:.24em;text-transform:uppercase;font:600 10px/1.4 Georgia,serif}\n.plaque{position:relative;isolation:isolate;width:min(1120px,calc(100% - 24px));margin:0 auto;padding:clamp(20px,4vw,48px);border:5px solid #8b622c;border-radius:4px;background-color:var(--wood2);background-image:repeating-linear-gradient(91deg,rgba(6,3,1,.13) 0,rgba(6,3,1,.13) 1px,transparent 1px,transparent 5px),repeating-linear-gradient(0deg,rgba(207,144,72,.055) 0,rgba(207,144,72,.055) 2px,rgba(13,5,2,.08) 3px,transparent 7px),radial-gradient(ellipse at 18% 8%,rgba(179,104,47,.2),transparent 40%),radial-gradient(ellipse at 86% 56%,rgba(106,52,19,.2),transparent 34%),linear-gradient(104deg,#291307 0%,#432311 19%,#2a1408 42%,#3b1d0d 68%,#241006 100%);box-shadow:inset 0 0 0 2px #2a1608,inset 0 0 0 5px #a77a37,inset 0 0 0 8px rgba(20,8,2,.88),inset 0 0 38px rgba(0,0,0,.68),0 22px 54px rgba(0,0,0,.62)}\n.plaque:before{content:"";position:absolute;inset:13px;z-index:-1;border:1px solid rgba(229,185,101,.48);box-shadow:inset 0 0 0 1px rgba(0,0,0,.45);pointer-events:none}\n.corner{position:absolute;width:19px;height:19px;border:2px solid #b68a42;border-radius:50%;background:radial-gradient(circle at 35% 30%,#f3d89b 0,#9a6c28 35%,#39200b 68%);box-shadow:0 2px 5px rgba(0,0,0,.7),inset 0 0 0 2px rgba(30,13,4,.75)}\n.tl{top:20px;left:20px}.tr{top:20px;right:20px}.bl{bottom:20px;left:20px}.br{bottom:20px;right:20px}\n.masthead{text-align:center;padding:4px 8px 24px}\n.utility{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 4px 30px;color:#d3b878;font:600 10px/1.4 Georgia,serif;letter-spacing:.18em;text-transform:uppercase}\n.theme-toggle{flex:0 0 auto;border:1px solid #a77a37;background:rgba(11,5,2,.45);color:#f6dc99;padding:8px 12px;min-height:36px;letter-spacing:.08em;text-transform:uppercase;font:600 10px/1 Georgia,serif;cursor:pointer;box-shadow:inset 0 0 0 1px rgba(255,226,158,.08)}\n.theme-toggle:hover{background:rgba(242,205,120,.12)}\n.crest{display:grid;place-items:center;margin:0 auto 15px;width:112px;height:112px;border:2px solid #d3ad60;border-radius:50%;box-shadow:0 0 0 5px rgba(13,5,1,.48),0 0 0 6px rgba(208,166,80,.48),inset 0 0 16px #100602;color:#f7dfa0;font-size:24px;letter-spacing:.03em;text-shadow:0 2px #3b2009;overflow:hidden}.crest img{display:block;width:100%;height:100%;object-fit:contain;padding:7px}\n.eyebrow{margin:0 0 9px;color:#d6b66d;font:600 10px/1.5 Georgia,serif;letter-spacing:.34em;text-transform:uppercase}\nh1{margin:0;color:#f2d68e;font:normal clamp(36px,7.2vw,76px)/1.05 "Palatino Linotype","Book Antiqua",Georgia,serif;letter-spacing:.035em;text-shadow:0 1px 0 #fff0bb,0 2px 0 #8e6526,0 4px 2px #160801,0 7px 15px rgba(0,0,0,.78)}\n.family{margin:12px 0 0;color:#f0d99f;font:normal clamp(14px,2vw,20px)/1.5 "Palatino Linotype","Book Antiqua",Georgia,serif;letter-spacing:.09em;text-shadow:0 2px 3px #120702}\n.family span{white-space:nowrap}\n.rule{display:flex;align-items:center;gap:14px;max-width:560px;margin:26px auto 0;color:#c49b4f}\n.rule:before,.rule:after{content:"";height:1px;flex:1;background:linear-gradient(90deg,transparent,#c39a4a)}\n.rule:after{background:linear-gradient(90deg,#c39a4a,transparent)}\n.rule span{font-size:18px;line-height:1}\nmain{display:grid;gap:18px}\n.menu-section{position:relative;padding:22px clamp(14px,2.4vw,30px) 20px;border:1px solid rgba(221,179,99,.62);background:linear-gradient(110deg,rgba(8,3,1,.35),rgba(68,34,13,.25) 48%,rgba(7,3,1,.3));box-shadow:inset 0 0 0 3px rgba(5,2,1,.24),inset 0 0 22px rgba(0,0,0,.2)}\n.menu-section:before{content:"";position:absolute;top:-1px;left:26px;right:26px;height:2px;background:linear-gradient(90deg,transparent,#dbb66c 18%,#dbb66c 82%,transparent)}\nh2{margin:0 0 6px;color:#f0d48a;font:normal clamp(20px,3.3vw,29px)/1.2 "Palatino Linotype","Book Antiqua",Georgia,serif;letter-spacing:.045em;text-shadow:0 2px 2px #170902}\n.section-note{margin:0 0 15px;color:#d0b780;font-size:13px;font-style:italic}\n.submenu{border-top:1px solid rgba(222,180,100,.25)}\n.submenu:last-child{border-bottom:1px solid rgba(222,180,100,.25)}\n.submenu summary{position:relative;display:flex;align-items:center;gap:10px;list-style:none;cursor:pointer;padding:12px 28px 12px 2px;color:#f3dfa8;font:600 12px/1.4 Georgia,serif;letter-spacing:.13em;text-transform:uppercase}\n.submenu summary::-webkit-details-marker{display:none}\n.submenu summary:before{content:"✦";color:#c6a052;font-size:12px}\n.submenu summary:after{content:"＋";position:absolute;right:4px;top:9px;color:#d9b66b;font-size:16px;font-weight:400}\n.submenu[open] summary:after{content:"−"}\n.entries{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px;padding:4px 0 16px 18px}\n.entry{position:relative;display:flex;align-items:center;justify-content:space-between;gap:12px;min-width:0;padding:9px 10px;border:1px solid rgba(221,180,100,.23);background:rgba(10,4,1,.24);text-decoration:none;transition:background .15s,border-color .15s}\n.entry:hover{border-color:#d7b565;background:rgba(201,153,69,.12)}\n.entry-copy{display:block;min-width:0}\n.entry-title{display:block;color:#f5e5bc;font-size:14px;line-height:1.25}\n.entry-domain{display:block;margin-top:4px;color:#c2a66f;font:10px/1.35 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}\n.entry-arrow{flex:0 0 auto;color:#d9b76d;font-size:15px}\n.endmark{text-align:center;color:#c6a45c;font-size:13px;letter-spacing:.2em;padding:24px 0 0}\n.endline{margin:8px auto 0;max-width:300px;height:1px;background:linear-gradient(90deg,transparent,rgba(219,180,103,.6),transparent)}\n.footer{text-align:center;margin:18px 0 0;color:#ac8e55;font:10px/1.6 Georgia,serif;letter-spacing:.13em;text-transform:uppercase}\nhtml[data-ghf-mode="day"]{color-scheme:light;--page:#4e321f}\nhtml[data-ghf-mode="day"] body{background:radial-gradient(ellipse at 50% 0%,#6f4827 0%,#3e2818 58%,#2b1b11 100%)}\nhtml[data-ghf-mode="day"] .plaque{filter:brightness(1.13);box-shadow:inset 0 0 0 2px #3f250f,inset 0 0 0 5px #bd944e,inset 0 0 0 8px rgba(42,21,7,.8),inset 0 0 38px rgba(0,0,0,.5),0 22px 54px rgba(0,0,0,.42)}\n@media(max-width:640px){body{padding-top:8px}.plaque{width:calc(100% - 12px);padding:22px 16px;border-width:4px}.plaque:before{inset:9px}.corner{width:14px;height:14px}.tl{top:14px;left:14px}.tr{top:14px;right:14px}.bl{bottom:14px;left:14px}.br{bottom:14px;right:14px}.utility{margin:0 0 25px;align-items:flex-start;font-size:8px;letter-spacing:.12em}.theme-toggle{padding:7px 8px;font-size:9px}.crest{width:82px;height:82px;font-size:20px}.masthead{padding-left:2px;padding-right:2px;padding-bottom:19px}.eyebrow{letter-spacing:.2em;font-size:9px}h1{font-size:clamp(34px,10vw,54px)}.family{letter-spacing:.03em}.menu-section{padding:18px 12px 16px}.entries{grid-template-columns:1fr;padding-left:10px}.entry{padding:9px}.entry-domain{font-size:9px}}\n@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.entry{transition:none}}\n@media print{body{background:white;padding:0}.plaque{width:100%;filter:none;box-shadow:none}.theme-toggle{display:none}details:not([open])>*:not(summary){display:block!important}}\n\n.realm{position:relative;border:1px solid rgba(221,179,99,.62);background:linear-gradient(110deg,rgba(8,3,1,.35),rgba(68,34,13,.25) 48%,rgba(7,3,1,.3));box-shadow:inset 0 0 0 3px rgba(5,2,1,.24),inset 0 0 22px rgba(0,0,0,.2)}\n.realm:before{content:"";position:absolute;top:-1px;left:26px;right:26px;height:2px;background:linear-gradient(90deg,transparent,#dbb66c 18%,#dbb66c 82%,transparent)}\n.realm>summary{position:relative;display:block;list-style:none;cursor:pointer;padding:20px 54px 18px clamp(14px,2.4vw,30px)}\n.realm>summary::-webkit-details-marker{display:none}\n.realm>summary .kick{display:block;margin:0 0 4px;color:#c9a457;font:600 10px/1.4 Georgia,serif;letter-spacing:.28em;text-transform:uppercase}\n.realm>summary h2{margin:0 0 4px}\n.realm>summary .section-note{margin:0}\n.realm>summary:after{content:"＋";position:absolute;right:clamp(14px,2.4vw,28px);top:50%;transform:translateY(-50%);width:30px;height:30px;display:grid;place-items:center;border:1px solid #a77a37;border-radius:50%;color:#f0d48a;font-size:16px;background:rgba(11,5,2,.45)}\n.realm[open]>summary:after{content:"−"}\n.realm>summary:hover h2{color:#fff0bb}\n.slot{padding:0 clamp(14px,2.4vw,30px) 18px}\n.layers-intro{margin:0 0 10px;color:#d0b780;font-size:13px;font-style:italic}\n.submenu summary b{font-weight:600}\n.submenu summary .n{margin-left:auto;color:#c2a66f;font:11px/1 ui-monospace,SFMono-Regular,Consolas,monospace;letter-spacing:0}\n.submenu summary .gnote{display:block;color:#c8ae78;font:italic 12px/1.4 Georgia,serif;letter-spacing:0;text-transform:none;margin-top:2px}\n.submenu summary .gt{display:block}\n.entry-num{flex:0 0 auto;min-width:26px;color:#b98e45;font:11px/1 ui-monospace,SFMono-Regular,Consolas,monospace}\n.entry-arrow{flex:0 0 auto;color:#d9b76d;font-size:15px}\n.home-search{display:flex;gap:6px;max-width:560px;margin:20px auto 0}\n.home-search input{flex:1;min-width:0;font:15px Georgia,serif;padding:9px 11px;border:1px solid #a77a37;background:rgba(11,5,2,.45);color:#f6e8c6}\n.home-search input::placeholder{color:#b99c66}\n.home-search button{font:600 11px/1 Georgia,serif;letter-spacing:.12em;text-transform:uppercase;border:1px solid #a77a37;background:rgba(242,205,120,.14);color:#f6dc99;padding:0 14px;cursor:pointer}\n.footer a{color:#e7c983;text-decoration:none;border-bottom:1px solid rgba(231,201,131,.35)}\n@media(max-width:640px){.realm>summary{padding:16px 50px 15px 12px}.slot{padding:0 12px 14px}.home-search{margin-top:16px}}\n\n.entry-copy{flex:1;text-align:left}\nhtml.ghf-shell .plaque,html.ghf-shell .plaque :is(p,a,span,b,summary,small,nav,header,footer,input,button,label){font-family:Georgia,"Times New Roman",serif}\nhtml.ghf-shell .plaque :is(h1,h2){font-family:"Palatino Linotype","Book Antiqua",Georgia,serif!important;font-weight:400!important;text-transform:none!important}\nhtml.ghf-shell .plaque h1{letter-spacing:.035em}\nhtml.ghf-shell .plaque h2{letter-spacing:.045em}\nhtml.ghf-shell .plaque .entry-domain,html.ghf-shell .plaque .entry-num,html.ghf-shell .plaque summary .n{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}\n@media (max-width:480px){html.ghf-shell .plaque h1{font-size:clamp(34px,10vw,54px)!important}html.ghf-shell .plaque h2{font-size:22px!important}}\n'

def groups_of(cfg):
    """[(group, [theme, ...]), ...] in themes.json order; a theme whose group is missing or unknown goes to the
    default group (and is reported), so no theme can fall off the home page"""
    gs = cfg.get('groups') or []
    ids = [g['id'] for g in gs]
    dflt = cfg.get('default_group') or (ids[0] if ids else 'all')
    if not gs: gs = [{'id': dflt, 'title': 'Every theme'}]; ids = [dflt]
    out = {g: [] for g in ids}; stray = []
    for t in cfg['themes']:
        g = t.get('group')
        if g not in out: stray.append(t['id']); g = dflt if dflt in out else ids[0]
        out[g].append(t)
    if stray: print('home: no known group for', stray, '-> placed in', dflt, file=sys.stderr)
    return [(g, out[g['id']]) for g in gs], stray

def render(cfg):
    e = html.escape
    H = cfg.get('home') or {}
    themes = cfg['themes']; n = len(themes)
    pos = {t['id']: i + 1 for i, t in enumerate(themes)}
    grouped, _ = groups_of(cfg)
    def entry(t):
        return (f'<a class="entry" href="/{e(t["id"])}/" data-theme-id="{e(t["id"])}"><span class="entry-num">{pos[t["id"]]:02d}</span>'
                f'<span class="entry-copy"><span class="entry-title">{e(t.get("title") or t["id"])}</span>'
                f'<span class="entry-domain">/{e(t["id"])}/</span></span><span class="entry-arrow" aria-hidden="true">›</span></a>')
    subs = ''.join(
        f'<details class="submenu" data-group="{e(g["id"])}"><summary><span class="gt"><b>{e(g["title"])}</b>'
        + (f'<span class="gnote">{e(g["note"])}</span>' if g.get('note') else '')
        + f'</span><span class="n">{len(ts)}</span></summary>'
        f'<nav class="entries" aria-label="{e(g["title"])}">' + ''.join(entry(t) for t in ts) + '</nav></details>'
        for g, ts in grouped if ts)
    intro = (H.get('layers_note') or 'Every way in leads to the same {n} layers of one archive.').replace('{n}', str(n))
    layers = f'<div id="layers"><p class="layers-intro">{e(intro)}</p>{subs}</div>'
    realms = H.get('realms') or [{'id': 'all', 'title': 'Every theme'}]
    rs = []
    for i, r in enumerate(realms):
        slot = layers if i == 0 else ''
        rs.append(f'<details class="realm" name="realm" data-realm="{e(r["id"])}"><summary>'
                  + (f'<span class="kick">{e(r["kick"])}</span>' if r.get('kick') else '')
                  + f'<h2>{e(r["title"])}</h2>'
                  + (f'<p class="section-note">{e(r["note"])}</p>' if r.get('note') else '')
                  + f'</summary><div class="slot">{slot}</div></details>')
    title = H.get('title') or 'Cedwyn Estate'
    fam = H.get('family') or ''
    est = H.get('est') or ''
    eyebrow = H.get('eyebrow') or ''
    desc = (H.get('description') or 'One archive of Great House Farm, {n} layers to explore it.').replace('{n}', str(n))
    return f"""<!doctype html>
<html lang="en-GB" data-ghf-host="bucklerfamily.estate" data-ghf-path="/cedwyn/home/" data-ghf-native="dark" data-ghf-theme-default="night">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)} · {e(fam or 'Cedwyn')}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#1b0d06">
<link rel="alternate" type="application/rss+xml" title="Cedwyn blog (RSS)" href="/blog/rss.xml"><link rel="alternate" type="application/atom+xml" title="Cedwyn blog (Atom)" href="/blog/atom.xml"><link rel="alternate" type="application/feed+json" title="Cedwyn blog (JSON Feed)" href="/blog/feed.json">
<style>
{CSS}
</style>
<script src="/_cedwyn/ghf/ghf-boot.js?v=2.1.19"></script>
</head>
<body>
<article class="plaque" aria-label="{e(title)} directory board">
<span class="corner tl" aria-hidden="true"></span><span class="corner tr" aria-hidden="true"></span><span class="corner bl" aria-hidden="true"></span><span class="corner br" aria-hidden="true"></span>
<header class="masthead">
<div class="utility"><span>{e(H.get('kicker') or 'The family estate directory')}</span><span>{n} layers</span></div>
<div class="crest" aria-hidden="true">{e(H.get('monogram') or 'CE')}</div>
<p class="eyebrow">{e(eyebrow)}</p>
<h1>{e(title)}</h1>
<p class="family">{e(fam)} <span>{e(est)}</span></p>
<div class="rule" aria-hidden="true"><span>✦</span></div>
<form class="home-search" action="/catalogue/" role="search"><input name="q" placeholder="Search the whole archive" aria-label="Search the whole archive"><button>Search</button></form>
</header>
<main>
{''.join(rs)}
</main>
<div class="endmark" aria-hidden="true">✦ &nbsp; C E D W Y N &nbsp; ✦</div>
<div class="endline" aria-hidden="true"></div>
<p class="footer">{e(fam)} · {e(title)} · <a href="/catalogue/">Catalogue</a> · <a href="/graphql/">GraphQL</a> · <span id="st"></span></p>
</article>
<script>
(function(){{
  /* one submenu, three ways in: whichever way is opened, the same groups move into it */
  var L=document.getElementById('layers'),R=[].slice.call(document.querySelectorAll('details.realm'));
  function show(d){{var s=d.querySelector('.slot');if(s&&L.parentNode!==s)s.appendChild(L);}}
  R.forEach(function(d){{d.addEventListener('toggle',function(){{if(!d.open)return;show(d);
    R.forEach(function(o){{if(o!==d&&o.open)o.open=false;}});try{{sessionStorage.setItem('cedwyn-realm',d.getAttribute('data-realm'));}}catch(e){{}}}});}});
  var k=null;try{{k=sessionStorage.getItem('cedwyn-realm');}}catch(e){{}}
  if(k){{R.forEach(function(d){{if(d.getAttribute('data-realm')===k)d.open=true;}});}}
}})();
</script>
<script>if('serviceWorker' in navigator)navigator.serviceWorker.register('/cedwyn-sw.js',{{scope:'/',updateViaCache:'none'}}).catch(function(){{}});</script>
<script>fetch('/db/stats.json').then(function(r){{return r.json()}}).then(function(s){{document.getElementById('st').textContent=s.artifacts.toLocaleString()+' artifacts in one database'}}).catch(function(){{}});</script>
</body>
</html>
"""

if __name__ == '__main__':
    root = pathlib.Path(__file__).resolve().parent.parent
    cfg = json.load(open(root / 'themes.json'))
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else 'dist') / 'index.html'
    out.write_text(render(cfg)); print('home ok', out)
