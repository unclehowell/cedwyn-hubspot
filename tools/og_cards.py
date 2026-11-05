#!/usr/bin/env python3
"""og_cards.py - social share previews for every Cedwyn page (Sion, WhatsApp 05:29 GMT 27 Oct 2026: "When i share my link on
social media no preview image and text comes up. Make it so it does and use the nft images for it").

Each human HTML page gets og:title/description/type/url/site_name, og:image (absolute, 1200x630 JPEG) with width, height and
alt, and twitter:card summary_large_image with title, description and image. A tag a theme already carries is never
overwritten (only the missing ones are added), so /ebooks/ keeps its own title, description and cover image.

Cards are made at build time from the Garden Gallery pieces (tools/og_cards.json lists which piece serves which section;
the same page always gets the same piece). The card file name carries the source hash, so a re-rendered piece gets a new
URL and social sites fetch it afresh. Without Pillow, or without the piece in this build, the committed card in
web/_cedwyn/og/<id>.jpg is used. Landscape pieces are cropped from the top (the signature sits bottom right); square,
portrait and plan pieces are shown whole on a blurred copy of themselves. Report: _cedwyn/reports/og_cards.json.
Runs at the end of site.py. - Sion's Tab agent

30 Oct 2026 (Sion, WhatsApp 00:32 GMT): every share preview names the family, the house and the site, then the webapp:
og:title and twitter:title read "Williams-Bucklers, Ty Mawr, Cedwyn – <webapp>", og:site_name reads "Williams-Bucklers, Ty Mawr,
Cedwyn", and og:image/twitter:image are one 1200x630 card per webapp with that exact text set on the webapp's Garden Gallery
piece. These five tags now replace whatever a theme or branch carried, so every branch and every new page inherits them;
descriptions stay page-specific. The webapp name comes from og_cards.json "webapps" (first path segment), else the theme's
own title, else the segment itself. Font: tools/fonts/PlayfairDisplay-Bold.ttf (SIL OFL, tools/fonts/OFL.txt)."""
import json, re, hashlib, html, io, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.load(open(ROOT / 'tools' / 'og_cards.json', encoding='utf-8'))
BASE = CFG['base'].rstrip('/')
W, H = 1200, 630
BRAND = CFG.get('brand', 'Williams-Bucklers, Ty Mawr, Cedwyn')
WEBAPPS = CFG.get('webapps', {})
FONT = ROOT / 'tools' / 'fonts' / 'PlayfairDisplay-Bold.ttf'
CARD_VERSION = 'wb1'
# tags the share card owns: a theme's own copy is removed so the brand line and the webapp card win everywhere
OWNED = ('og:title', 'twitter:title', 'og:site_name', 'og:image', 'og:image:secure_url', 'og:image:type', 'og:image:width',
         'og:image:height', 'og:image:alt', 'og:image:url', 'twitter:image', 'twitter:image:alt', 'twitter:card', 'og:url', 'og:type')
BANNED = re.compile(r'\b(says|claims?|claimed|according to|hearsay|unverified|alleged(ly)?|fraud\w*|stolen|sion)\b', re.I)
POSTCODE = re.compile(r'\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b')
EMAILISH = re.compile(r'@|\+?\d[\d\s]{8,}\d')
HEAD_END = re.compile(r'</head\s*>', re.I)
TITLE = re.compile(r'<title[^>]*>(.*?)</title>', re.I | re.S)
META = re.compile(r'<meta\b[^>]*>', re.I)
ATTR = re.compile(r'([a-zA-Z:-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')
P = re.compile(r'<p\b[^>]*>(.*?)</p>', re.I | re.S)
TAG = re.compile(r'<[^>]+>')
CANON = re.compile(r'<link\b[^>]*rel=["\']canonical["\'][^>]*>', re.I)
BLOCK = re.compile(r'<!-- og:cedwyn -->.*?<!-- /og:cedwyn -->', re.S)


def attrs(tag):
    return {m.group(1).lower(): html.unescape(m.group(3) if m.group(3) is not None else m.group(4)) for m in ATTR.finditer(tag)}


def clean(s):
    s = html.unescape(TAG.sub(' ', s or ''))
    return re.sub(r'\s+', ' ', s).strip()


def ok_text(s):
    return bool(s) and not BANNED.search(s) and not POSTCODE.search(s) and not EMAILISH.search(s)


NOISE = re.compile(r'\b(agents?|AI|updated|original source|e-?book editions?|click|tap|submit|edit|cookies?|javascript|loading|sign[ -]?in|menu|when answering|this site|page id)\b|[\U0001F300-\U0001FAFF\u2600-\u27BF]', re.I)
NEAR = re.compile(r'hidden|aria-hidden|agent|small-?print|notice|footer|guestbook|nav', re.I)


def first_sentence(body):
    for m in P.finditer(body[:400000]):
        t = clean(m.group(1))
        if len(t) < 60 or not ok_text(t) or NOISE.search(t) or t.count('·') > 1 or not t[0].isupper():
            continue
        if NEAR.search(body[max(0, m.start() - 400):m.start()]):
            continue
        out = ''
        for sent in re.split(r'(?<=[.!?])\s+', t):
            if len(out) + len(sent) > 200:
                break
            out = (out + ' ' + sent).strip()
        if len(out) < 70:
            out = t if len(t) <= 190 else t[:190].rsplit(' ', 1)[0] + '…'
        if len(out) >= 40:
            return out
    return ''


def webapp_name(sec, theme):
    if sec in WEBAPPS: return WEBAPPS[sec]
    t = (theme or {}).get('title') or ''
    t = re.split(r'\s+·\s+', t)[0].strip()
    t = re.sub(r'^The\s+', '', t)
    if t and ok_text(t): return t
    return sec.replace('-', ' ').title() if sec else WEBAPPS.get('', 'Home')


# 30 Oct 2026 (shop patch bundle item 9): a book's own page shares under its own name. The owner's brand line stays first
# ("Williams-Bucklers, Ty Mawr, Cedwyn – E-books"), then the book: "… – E-books · Enwau: the names of Tŷ Mawr".
# Only the book pages one level under /ebooks/ (ITEM_SECTIONS); every other page keeps the webapp title. - Sion's Tab agent
ITEM_SECTIONS = ('ebooks',)
def item_title(sec, rel_dir, head):
    parts = [x for x in rel_dir.strip('/').split('/') if x]
    if sec not in ITEM_SECTIONS or len(parts) != 2: return ''
    m = TITLE.search(head)
    if not m: return ''
    t = clean(html.unescape(TAG.sub('', m.group(1))))
    ps = [x.strip() for x in re.split(r'\s+[·—|]\s+|\s+–\s+E-books', t) if x.strip()]
    t = ps[0] if ps else ''
    if len(t) < 12 and len(ps) > 1: t = t + ': ' + ps[1]
    t = re.sub(r'^£0\.00 e-book:\s*', '', t); t = re.sub(r',?\s*v\d+(\.\d+)+$', '', t).strip()
    t = t[:1].upper() + t[1:]
    if not t or len(t) > 90 or not ok_text(t) or t.lower().startswith('not found'): return ''
    return t


def share_title(name):
    return BRAND + ' – ' + name if name else BRAND


def _fit(draw, text, font_path, size, max_w, min_size):
    from PIL import ImageFont
    while size >= min_size:
        f = ImageFont.truetype(str(font_path), size)
        if draw.textlength(text, font=f) <= max_w: return f
        size -= 2
    return ImageFont.truetype(str(font_path), min_size)


def titled(base_jpg, name):
    """Set 'Williams-Bucklers, Ty Mawr, Cedwyn –' and the webapp name on a 1200x630 card: a dark band from the left keeps the
    painting visible on the right, cream brand line, gold webapp name, thin gold rule."""
    from PIL import Image, ImageDraw, ImageChops
    im = Image.open(io.BytesIO(base_jpg)).convert('RGB')
    row = bytes(int(238 * max(0.0, min(1.0, 1.3 - x / (W * 0.88)))) for x in range(W))
    side = Image.frombytes('L', (W, 1), row).resize((W, H))
    col = bytes(int(150 * max(0.0, (y / H - 0.45) / 0.55)) for y in range(H))
    low = Image.frombytes('L', (1, H), col).resize((W, H))
    shade = ImageChops.lighter(side, low)
    im = Image.composite(Image.new('RGB', (W, H), (16, 22, 18)), im, shade)
    d = ImageDraw.Draw(im)
    if not FONT.exists():
        return None
    x0 = 72; maxw = W - 2 * x0
    f1 = _fit(d, BRAND + ' –', FONT, 50, maxw, 30)
    f2 = _fit(d, name, FONT, 112, maxw, 44)
    h1 = f1.getbbox(BRAND + ' –')[3]; h2 = f2.getbbox(name + 'gy')[3]
    y1 = (H - (h1 + 34 + h2)) // 2 - 10
    d.rectangle((x0, y1 - 30, x0 + 120, y1 - 26), fill=(201, 162, 75))
    d.text((x0 + 2, y1 + 2), BRAND + ' –', font=f1, fill=(0, 0, 0))
    d.text((x0, y1), BRAND + ' –', font=f1, fill=(246, 239, 222))
    y2 = y1 + h1 + 34
    d.text((x0 + 3, y2 + 3), name, font=f2, fill=(0, 0, 0))
    d.text((x0, y2), name, font=f2, fill=(226, 190, 104))
    d.rectangle((x0, y2 + h2 + 26, x0 + 120, y2 + h2 + 30), fill=(201, 162, 75))
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=84, optimize=True, progressive=True)
    return buf.getvalue()


def esc(s):
    return html.escape(s, quote=True)


class Cards:
    def __init__(self, dist):
        self.dist = dist; self.made = {}; self.meta = {}; self.titled = {}; self.untitled = []
        self.titles = CFG.get('pieces', {})
        bm = dist / '_blob_map.json'
        self.blobmap = json.load(open(bm)) if bm.exists() else {}
        try:
            from PIL import Image, ImageFilter, ImageEnhance  # noqa: F401
            self.pil = True
        except Exception:
            self.pil = False
        self.out = dist / '_cedwyn' / 'og'; self.out.mkdir(parents=True, exist_ok=True)

    def source(self, nfa):
        name = nfa.lower() + '.webp'
        for rel in ('nft-art/art/' + name,):
            p = self.dist / rel
            if p.exists(): return p.read_bytes()
            for k in ('/' + rel, rel):
                b = self.blobmap.get(k)
                if b and (self.dist / b.lstrip('/')).exists(): return (self.dist / b.lstrip('/')).read_bytes()
        return None

    def render(self, data, plan):
        from PIL import Image, ImageFilter, ImageEnhance
        im = Image.open(io.BytesIO(data)).convert('RGB')
        if im.width / im.height >= 1.3 or (not plan and im.width >= im.height):
            s = W / im.width; im2 = im.resize((W, max(H, round(im.height * s))), Image.LANCZOS)
            out = im2.crop((0, im2.height - H, W, im2.height))   # keep the bottom edge: the signature
        else:
            s = max(W / im.width, H / im.height); bg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            l = (bg.width - W) // 2; t = (bg.height - H) // 2
            out = ImageEnhance.Brightness(bg.crop((l, t, l + W, t + H)).filter(ImageFilter.GaussianBlur(28))).enhance(0.6)
            s = min(W / im.width, H / im.height); fg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            out.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2))
        buf = io.BytesIO(); out.save(buf, 'JPEG', quality=82, optimize=True, progressive=True)
        return buf.getvalue()

    def get(self, nfa):
        if nfa in self.made: return self.made[nfa]
        url = None; data = self.source(nfa) if self.pil else None
        plan = 'plan' in (self.titles.get(nfa, {}).get('title', '').lower()) or nfa == 'NFA-0011'
        if data:
            try:
                jpg = self.render(data, plan)
                name = '%s-%s.jpg' % (nfa.lower(), hashlib.sha1(data).hexdigest()[:8])
                (self.out / name).write_bytes(jpg); url = '/_cedwyn/og/' + name
            except Exception as e:
                print('og_cards: render failed', nfa, e)
        if url is None and (self.out / (nfa.lower() + '.jpg')).exists():
            url = '/_cedwyn/og/' + nfa.lower() + '.jpg'
        if url is None:
            return self.get(CFG['default']) if nfa != CFG['default'] else None
        a = self.titles.get(nfa, {})
        alt = (a.get('alt') or a.get('title') or 'A painted scene of Great House Farm, Llandough')
        alt = alt if ok_text(alt) else 'A painted scene of Great House Farm, Llandough'
        self.made[nfa] = (BASE + url, alt + ' (' + nfa + ', Garden Gallery)')
        return self.made[nfa]

    def webapp_card(self, name, nfa):
        """One card per webapp: the brand line and the webapp name set on the webapp's piece. Falls back to the plain piece."""
        key = (name, nfa)
        if key in self.titled: return self.titled[key]
        res = None; data = self.source(nfa) if self.pil else None
        if data is None and nfa != CFG['default'] and self.pil:
            nfa = CFG['default']; data = self.source(nfa)
        if data is not None and FONT.exists():
            try:
                plan = 'plan' in (self.titles.get(nfa, {}).get('title', '').lower()) or nfa == 'NFA-0011'
                jpg = titled(self.render(data, plan), name)
                if jpg:
                    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') or 'home'
                    h = hashlib.sha1(data + name.encode() + CARD_VERSION.encode()).hexdigest()[:8]
                    fn = 'share-%s-%s.jpg' % (slug, h); (self.out / fn).write_bytes(jpg)
                    res = (BASE + '/_cedwyn/og/' + fn, share_title(name) + ': share card on a Garden Gallery painting (' + nfa + ')')
            except Exception as e:
                print('og_cards: titled card failed', name, e)
        if res is None:
            plain = self.get(nfa)
            res = (plain[0], share_title(name)) if plain else None
            self.untitled.append(name)
        self.titled[key] = res
        return res


def pick(rel_dir):
    sec = rel_dir.split('/')[0] if rel_dir else ''
    pool = CFG['sections'].get(sec)
    if not pool:
        allp = CFG['pool']; k = int(hashlib.sha1(sec.encode()).hexdigest(), 16) % len(allp)
        pool = [allp[(k + j) % len(allp)] for j in range(3)]
    if rel_dir.strip('/') == sec:   # a section's own home page gets its first piece
        return pool[0]
    return pool[int(hashlib.sha1(rel_dir.encode()).hexdigest(), 16) % len(pool)]


def run(dist):
    dist = pathlib.Path(dist)
    themes = {t['id']: t for t in json.load(open(ROOT / 'themes.json', encoding='utf-8'))['themes']}
    skip = tuple(s.strip('/') + '/' for s in CFG.get('skip_dirs', []))
    cards = Cards(dist); n = 0; added = 0; untouched = 0; samples = {}
    for p in sorted(dist.rglob('*.html')):
        rel = p.relative_to(dist).as_posix()
        if rel.startswith(skip) or rel.startswith('_') and not rel.startswith('_cedwyn/og'):
            continue
        try:
            n, added, untouched = page(p, rel, dist, themes, cards, n, added, untouched, samples)
        except Exception as e:
            print('og_cards: skipped', rel, e)
    # Pages served by Workers (/learn/, /hive/) cannot be rewritten here: they point at a stable copy of their webapp card
    stable = {}
    for name, sec in CFG.get('stable_cards', {}).items():
        pool = CFG['sections'].get(sec) or [pick(sec)]
        c = cards.webapp_card(name, pool[0])
        if c and '/share-' in c[0]:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            src_f = cards.out / c[0].rsplit('/', 1)[1]; dst = cards.out / ('share-%s.jpg' % slug)
            dst.write_bytes(src_f.read_bytes()); stable[name] = BASE + '/_cedwyn/og/' + dst.name
    rep = {'stable_cards': stable, 'pages_changed': n, 'tags_added': added, 'pages_already_complete': untouched, 'pillow': cards.pil,
           'font': FONT.exists(), 'brand': BRAND, 'webapp_cards': {k[0]: v[0] for k, v in cards.titled.items() if v},
           'untitled_fallbacks': sorted(set(cards.untitled)), 'samples': samples}
    (dist / '_cedwyn' / 'reports').mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(dist / '_cedwyn' / 'reports' / 'og_cards.json', 'w'), indent=1)
    print('og_cards: %d pages, %d tags, %d webapp cards, %d untitled (pillow %s, font %s)' % (n, added, len(cards.titled), len(set(cards.untitled)), cards.pil, FONT.exists()))


def page(p, rel, dist, themes, cards, n, added, untouched, samples):
    try: txt = p.read_text('utf-8')
    except Exception: return n, added, untouched
    m = HEAD_END.search(txt[:600000])
    if not m: return n, added, untouched
    head = txt[:m.start()]
    if re.search(r'http-equiv=["\']refresh', head, re.I) and len(txt) < 3000:
        return n, added, untouched   # a redirect stub, not a page
    head_clean = BLOCK.sub('', head)
    have = {}; drop = []
    for t in META.findall(head_clean):
        a = attrs(t); key = (a.get('property') or a.get('name') or '').lower()
        if not key: continue
        val = a.get('content', '')
        if key in OWNED:   # the share card owns these on every page (30 Oct 2026)
            drop.append(t); continue
        bad = False
        if key in ('og:description', 'twitter:description', 'description'):
            bad = not ok_text(val) or bool(NOISE.search(val)) or not val.strip()
        if bad:
            drop.append(t); continue
        have.setdefault(key, val)
    for t in drop:
        head_clean = head_clean.replace(t, '', 1)
    rel_dir = rel[:-len('index.html')] if rel.endswith('index.html') else rel
    sec = rel_dir.split('/')[0] if '/' in rel_dir else ''
    theme = themes.get(sec, {})
    url = BASE + '/' + rel_dir
    cm = CANON.search(head_clean)
    if cm:
        cu = attrs(cm.group(0)).get('href', '')
        if cu.startswith('/') and not cu.startswith('//'):   # 30 Oct 2026: a relative canonical becomes absolute (same address) - Sion's Tab agent
            cu = BASE + cu; head_clean = head_clean.replace(cm.group(0), '<link rel="canonical" href="%s">' % esc(cu), 1)
        if cu.startswith(BASE + '/'): url = cu
    name = webapp_name(sec, theme)
    title = share_title(name)
    book = item_title(sec, rel_dir, head_clean)
    if book: title = title + ' · ' + book
    desc = have.get('og:description') or have.get('description', '')
    tdesc = CFG.get('section_desc', {}).get(sec) or (theme.get('desc', '') if ok_text(theme.get('desc', '')) and len(theme.get('desc', '')) > 40 else '')
    if not ok_text(desc) or len(desc) < 30 or NOISE.search(desc):
        desc = (tdesc if rel_dir.strip('/') == sec else '') or first_sentence(txt[m.end():]) or tdesc or CFG['home_description']
    if rel_dir == '' and not ok_text(have.get('description', '')):
        desc = CFG['home_description']
    pool = CFG['sections'].get(sec) or [pick(sec)]
    nfa = CFG['default'] if not sec else pool[0]
    img = cards.webapp_card(name, nfa)
    want = [('property', 'og:title', title), ('property', 'og:type', 'website'),
            ('property', 'og:url', url), ('property', 'og:site_name', BRAND)]
    if 'og:description' not in have: want.append(('property', 'og:description', desc))
    if img:
        want += [('property', 'og:image', img[0]), ('property', 'og:image:secure_url', img[0]),
                 ('property', 'og:image:type', 'image/jpeg'), ('property', 'og:image:width', str(W)),
                 ('property', 'og:image:height', str(H)), ('property', 'og:image:alt', img[1])]
    want += [('name', 'twitter:card', 'summary_large_image'), ('name', 'twitter:title', title)]
    if 'twitter:description' not in have: want.append(('name', 'twitter:description', have.get('og:description') or desc))
    if img: want += [('name', 'twitter:image', img[0]), ('name', 'twitter:image:alt', img[1])]
    if 'description' not in have and desc:
        want.append(('name', 'description', desc))
    tags = ['<meta %s="%s" content="%s">' % (k, v, esc(c)) for k, v, c in want if c]
    block = '<!-- og:cedwyn -->' + ''.join(tags) + '<!-- /og:cedwyn -->'
    new = head_clean + block + txt[m.start():]
    if new == txt:
        return n, added, untouched + 1
    p.write_text(new, 'utf-8'); n += 1; added += len(tags)
    if len(samples) < 80 and sec not in samples: samples[sec or '/'] = [title, img[0] if img else '']
    return n, added, untouched


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
