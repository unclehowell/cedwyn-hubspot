#!/usr/bin/env python3
"""qa_questions.py - /qa/ and /wales/qa/ (and any /<section>/qa/) as a list of QUESTIONS, not emails.
Sion, WhatsApp 00:54 GMT 30 Oct 2026: a breakdown of what has been asked, coloured hashtags under each question for every
institution asked, and under the answer hashtags of who answered; each hashtag links to the email on /email/reference/<id>/.
Cause of the empty page it replaces: the crawled Q&A page fetched /kb.json and /correspondence.json from the site root,
files that only exist on qa.bucklerfamily.estate, so on Cedwyn both answered 404 and nothing listed.
Inputs: data/qa/questions-base.json (curated questions, each linked to its sent email and reply; written by
tools/qa_questions_base.py) + the live mail catalogue dist/email/view/index.json (rebuilt as mail is ingested). Any sent
thread not in the base becomes a question by subject rules below, so new mail shows up on the next build.
Writes the list into every dist/**/qa/index.html that carries the Q&A page, plus /qa/questions.json. - Sion's Tab agent"""
import json, re, html, pathlib, hashlib, urllib.parse, unicodedata, sys
from datetime import date
ROOT = pathlib.Path(__file__).resolve().parent.parent

TAGS = {'vale-foi':'ValeOfGlamorgan','vale-scrutiny':'ValeOfGlamorgan','glamorgan':'GlamorganArchives','cadw':'Cadw',
 'hmlr':'HMLR','hmlr-icr':'HMLR','moj':'MoJ','tna':'TNA','swp':'SouthWalesPolice','museum':'MuseumWales','mp':'MP',
 'mp-vale':'MP','nlw':'NLW','rcahmw':'RCAHMW','llandough':'LlandoughCC','senedd':'Senedd','nhs-cav':'CardiffAndValeUHB',
 'heneb':'Heneb','mod':'MoD','nactso':'CounterTerrorismPolicing','rct':'Coroner','itv':'ITVArchive','bp':'BP','cps':'CPS',
 'dwrcymru':'WelshWater','postal-museum':'PostalMuseum','phso':'PHSO','ico':'ICO','nio':'NIO','defra':'Defra',
 'os':'OrdnanceSurvey','cotswold':'CotswoldArchaeology','legal-regulators':'LegalRegulators','pacac':'PACAC',
 'historic-england':'HistoricEngland','bona-vacantia':'BonaVacantia','voa':'VOA','persimmon':'PersimmonHomes',
 'linklaters':'Linklaters','cardiff-reg':'RegisterOffice','audit-wales':'AuditWales','lga':'WLGA','mount-stuart':'MountStuart',
 'wales-office':'WalesOffice','tfw':'TransportForWales','cardiff-univ':'CardiffUniversity','psow':'PSOW',
 'blake-morgan':'BlakeMorgan','dcms':'DCMS','ads':'ArchaeologyDataService','bt-archives':'BTArchives',
 'church-of-england':'LambethPalaceLibrary','cardiff':'CardiffCouncil','nrw':'NaturalResourcesWales','sfo':'SFO',
 'pmo':'CabinetOffice'}
SKIP_INST = {'wdtk?'}
def tag(iid, name=''):
    if iid in TAGS: return TAGS[iid]
    w = re.sub(r'\(.*?\)', '', name or iid)
    return ''.join(x[:1].upper() + x[1:] for x in re.findall(r'[A-Za-z0-9]+', w))[:28] or iid
def hue(t):   # one stable colour per hashtag, the same on every page that uses this function
    return int(hashlib.sha1(t.encode()).hexdigest()[:6], 16) * 137 % 360

# Public-text rules: no private people, none of the banned words.
SUBS = [(r'\bMrs?\.? (?:Nancy |Mary )?(?:\(Nancy\) )?Buckler\b', 'a family member'), (r'\bWilliam (?:\(Billy\) )?Buckler\b', 'a family member'),
 (r'\bMary (?:\(Nancy\) )?Doreen Williams\b', 'a family member'), (r'\bMary Doreen\b', 'a family member'),
 (r'\bMary \(Nancy\) Williams\b', 'a family member'), (r'\bNancy\b', 'a family member'), (r'\bDoreen\b', 'a family member'),
 (r'\b(?:Cllr|Councillor)\.? (?:George )?Carroll\b', 'a community councillor'), (r'\bMr\.? (John Williams?)\b', r'\1'),
 (r'\b(?:Dr|Mr|Ms|Mrs|Miss)\.? (?:Andy )?(?:Wigley|Gill|Griffiths|Driver)\b', 'an official'),
 (r'\b(?:Sion|Branwen|Hywel)(?: ap)?(?: Buckler)?\b', 'the requester'),
 (r'(?<!v )(?<!v\. )\bBuckler(?! \[| \(19| 19)', 'the family'),
 (r'\bfraud\w*', 'irregularity'), (r'\bstolen\b', 'taken'), (r'\balleg(?:ed|ation|ations)\b', 'reported'),
 (r'\bclaims\b', 'assertions'), (r'\bclaim\b', 'assertion'), (r'\bsays\b', 'states'), (r'\baccording to\b', 'in'),
 (r'\bhearsay\b', 'second-hand account'), (r'\bunverified\b', 'not checked')]
WORDS = SUBS[-10:]; NAMES = SUBS[:-10]
def clean(s):
    s = str(s or '')
    for a, b in NAMES: s = re.sub(a, b, s)
    for a, b in WORDS: s = re.sub(a, b, s, flags=re.I)
    return re.sub(r'\b(a family member)( and a family member)+', r'\1s', s)
def short(s, n=300):
    s = re.sub(r'\s+', ' ', clean(s)).strip()
    if len(s) <= n: return s
    c = s[:n]; k = max(c.rfind('. '), c.rfind('; '))
    return (c[:k + 1] if k > n * 0.5 else c.rsplit(' ', 1)[0] + '…')

def topic(s): return re.sub(r'^\s*((re|fwd?|fw|atb/re)\s*:\s*)+', '', s or '', flags=re.I).strip()
def title_of(rec):
    t = topic(rec.get('subject', ''))
    t = re.sub(r'^(\[\d+\]\s*)?((subject|re|fwd?)\s*:\s*)*', '', t, flags=re.I)
    p = t.split(':')[0].strip()
    if len(p) < 10: p = t[:90]
    if not p or clean(p) != p: p = 'Email ' + ('to ' if rec.get('direction') == 'sent' else 'from ') + ', '.join(i['name'] for i in rec.get('institutions', []))
    return p[:110]
def ref_url(rec):
    gid = rec.get('gmailMessageId') or rec['id'].replace('gm-', '')
    return '/email/reference/%s/?%s' % (gid, urllib.parse.urlencode({'title': title_of(rec), 'date': rec['date'][:10]}))

# Neutral questions for sent threads the base does not cover yet (first rule that matches wins).
RULES = [
 (r'death|coroner|register office|registration service|certificate', 'death', 'What records are held about two family deaths in 1983 and 1990?'),
 (r'marconi|post office engineering|lavernock', 'marconi', "What records are held about the 1897 Marconi experiments and their link to Great House Farm?"),
 (r'furniture|cardiff castle', 'furniture', 'What is known about furniture from Great House Farm now linked to Cardiff Castle?'),
 (r'aerial', 'aerial', 'What aerial photographs or survey records show Great House Farm?'),
 (r'water', 'water', 'What historic water supply records are held for Great House Farm?'),
 (r'school', 'school', 'What records are held on the acquisition of land for Llandough Primary School?'),
 (r'documentary|footage|itv|1988', 'footage', 'What records or footage are held of the events at Great House Farm in November–December 1988?'),
 (r'defra|maf\b|wartime|1936', 'wartime', 'What wartime and post-war farm records (1936–1955) are held for Great House Farm?'),
 (r'court|hmcts|judgment|transcript', 'court', 'What historical court records exist for Great House Farm, and where can they be read?'),
 (r'preserv|litigation hold|do not destroy|disclosure notice', 'preserve', 'Will records about Great House Farm be kept while enquiries are open?'),
 (r'review|atisn|internal review', 'review', 'Will earlier answers about Great House Farm be reviewed?'),
 (r'petition|inquiry|deiseb|ymchwiliad|scrutiny|task and finish', 'inquiry', 'Will a public inquiry, petition or scrutiny review of the Great House Farm case be considered?'),
 (r'complain|maladministration|ombudsman|phso|psow|failure', 'complaint', 'How were complaints about the handling of the Great House Farm case dealt with?'),
 (r'wa231076|wa240304|registration|title|land registry|edd', 'title', 'What records are held on the 1982 first registration of Great House Farm (titles WA231076 and WA240304)?'),
 (r'planning|church view close', 'planning', 'What planning records are held for Church View Close, the former Great House Farm?'),
 (r'manor|mdr|tithe|plot|estate|bute', 'manor', 'What manorial and estate records mention Great House Farm (Tŷ Mawr)?'),
 (r'\bbp\b|bp properties|dispossession', 'bp', 'What records are held about BP Properties Ltd v Buckler (1987) and the 1988 dispossession?'),
 (r'', 'general', 'What information is held about Great House Farm (Tŷ Mawr), Llandough?')]
NOISE = re.compile(r'meeting of the council|acknowledg|contact us form|out of office|automatic reply|unsubscribe|newsletter|invoice', re.I)
BOUNCE = re.compile(r'undeliverable|automatic reply|auto-?reply|out of office|delivery status|mail delivery|delivery has failed|acknowledg|we have received your|thank you for your (email|enquiry|request)', re.I)
ANSWERED = {'answered', 'partly answered', 'statement only', 'contested', 'redirected', 'refused', 'not held', 'reply received'}

def d(s):
    try: return date.fromisoformat(str(s)[:10])
    except Exception: return None

def build(base, idx):
    recs = idx.get('records', [])
    byid = {r['id']: r for r in recs}
    used_threads = set()
    qs = []
    for q in base.get('questions', []):
        x = dict(q); x['asked_by'] = []; x['answered_by'] = []
        for a in q.get('asks', []):
            r = byid.get(a['sent'])
            if r: used_threads.add(r['threadId'])
            x['asked_by'].append({'inst': a['inst'], 'name': a['name'], 'email': r and ref_url(r), 'date': (r or {}).get('date', '')[:10] or q.get('asked', '')})
            rp = byid.get(a.get('reply') or '')
            if not rp and r and x.get('status') in ('pending', 'no reply', 'open'):   # a reply that arrived after the base was written
                later = [m for m in recs if m['direction'] == 'received' and m['threadId'] == r['threadId'] and m['date'] > r['date']]
                if later: rp = sorted(later, key=lambda m: m['date'])[0]; x['status'] = 'reply received'
            if rp and x.get('status') in ANSWERED:
                x['answered_by'].append({'inst': a['inst'], 'name': a['name'], 'email': ref_url(rp), 'date': rp['date'][:10]})
        qs.append(x)
    # sent threads the base does not cover: one neutral question per subject rule, every institution it went to
    def key_of(r):
        subj = topic(r.get('subject', '')) + ' ' + ' '.join(i['name'] for i in r['institutions'])
        return next((k for pat, k, _ in RULES if re.search(pat, subj, re.I)), 'general')
    bounced = {m['threadId'] for m in recs if m['direction'] == 'received' and BOUNCE.search(m.get('subject', ''))}
    first = {}
    for r in sorted(recs, key=lambda r: r['date']):
        if r['direction'] != 'sent' or r['threadId'] in used_threads or NOISE.search(r.get('subject', '')): continue
        first.setdefault(r['threadId'], r)
    texts = {k: t for _, k, t in RULES}
    auto = {}
    for tid, r in sorted(first.items(), key=lambda kv: kv[1]['date']):
        g = auto.setdefault(key_of(r), {})
        for i in r['institutions']:
            if i['id'] in SKIP_INST: continue
            t = tag(i['id'], i['name']); cur = g.get(t)
            ok = tid not in bounced
            # keep the newest delivered send per institution (a bounced send only when nothing else went through)
            if cur is None or (ok and (not cur['ok'] or r['date'] > cur['r']['date'])):
                g[t] = {'inst': i['id'], 'name': i['name'], 'r': r, 'ok': ok, 'first': (cur or {}).get('first') or r['date']}
    replies = [m for m in recs if m['direction'] == 'received' and not BOUNCE.search(m.get('subject', '')) and m['threadId'] not in used_threads]
    for key, g in auto.items():
        x = {'id': 'ask-' + key, 'question': texts[key], 'kind': 'request', 'status': 'no reply', 'asked': '', 'answer': '', 'asked_by': [], 'answered_by': []}
        for t, a in g.items():
            x['asked_by'].append({'inst': a['inst'], 'name': a['name'], 'email': ref_url(a['r']), 'date': a['r']['date'][:10]})
            x['asked'] = max(x['asked'], a['r']['date'][:10])
            reps = [m for m in replies if m['date'] >= a['first'] and any(tag(j['id'], j['name']) == t for j in m['institutions'])
                    and (m['threadId'] == a['r']['threadId'] or key_of(m) == key)]
            if reps:
                rp = sorted(reps, key=lambda m: m['date'])[-1]
                x['answered_by'].append({'inst': a['inst'], 'name': a['name'], 'email': ref_url(rp), 'date': rp['date'][:10]})
        if x['answered_by']:
            x['status'] = 'reply received'
            x['answer'] = 'Replies received from ' + ', '.join(sorted({a['name'] for a in x['answered_by']})) + '. Each hashtag opens that reply.'
        qs.append(x)
    for x in qs:
        x['question'] = clean(x['question']); x['answer'] = short(x.get('answer', ''), 240)
        for a in x['asked_by'] + x['answered_by']: a['tag'] = tag(a['inst'], a['name']); a['hue'] = hue(a['tag'])
    qs.sort(key=lambda x: x.get('asked') or '', reverse=True)
    return qs

E = html.escape
def chip(a, cls='tg'):
    lbl = '#' + a['tag']
    st = 'style="--h:%d"' % a['hue']
    if a.get('email'): return '<a class="%s" %s href="%s">%s</a>' % (cls, st, E(a['email']), E(lbl))
    return '<span class="%s" %s>%s</span>' % (cls, st, E(lbl))
SLABEL = {'answered': 'Answered', 'partly answered': 'Partly answered', 'not held': 'Not held', 'refused': 'Refused',
 'redirected': 'Redirected', 'statement only': 'Statement only', 'contested': 'Answered (contested)', 'reply received': 'Reply received'}
def fmt(s):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s or '')
    return '%d %s %s' % (int(m.group(3)), 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[int(m.group(2)) - 1], m.group(1)) if m else ''
def card(x):
    tags = ' '.join(sorted({a['tag'] for a in x['asked_by']}))
    st = x.get('status', '')
    ok = st in ANSWERED and (x['answered_by'] or st == 'not held')
    lab = SLABEL.get(st, 'No answer yet') if ok or st in ANSWERED else 'No answer yet'
    grp = 'nh' if st == 'not held' else ('ans' if ok or st in ANSWERED else 'open')
    h = ['<article class="q" id="q-%s" data-tags="%s" data-st="%s">' % (E(x['id'][:70]), E(tags), grp)]
    h.append('<h3>%s</h3>' % E(x['question']))
    h.append('<p class="meta">Asked %s%s</p>' % (fmt(x.get('asked')) or '—', (' · ref ' + E(clean(x['reference']))) if x.get('reference') else ''))
    h.append('<div class="tags">' + ''.join(chip(a) for a in x['asked_by']) + '</div>')
    h.append('<div class="ans %s"><p class="al">%s</p>' % (grp, E(lab)))
    if grp != 'open' and x.get('answer'): h.append('<p>%s</p>' % E(x['answer']))
    if x['answered_by']: h.append('<div class="tags">' + ''.join(chip(a) for a in x['answered_by']) + '</div>')
    h.append('</div></article>')
    return ''.join(h)

CSS = """<style id="qa-questions-css">
.qx-f{margin:4px 0 10px}.qx-f summary{cursor:pointer;font-size:.9rem;font-weight:600;color:var(--navy,#032d60);padding:6px 2px}
.qx-legend{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 12px}
.tg{--h:210;display:inline-block;margin:2px 4px 2px 0;padding:3px 9px;border-radius:999px;font-size:.82rem;font-weight:600;line-height:1.4;
 text-decoration:none;background:hsl(var(--h) 75% 93%);color:hsl(var(--h) 70% 24%);border:1px solid hsl(var(--h) 45% 72%);white-space:nowrap}
a.tg:hover{background:hsl(var(--h) 75% 86%)}
button.tg{cursor:pointer;font-family:inherit}button.tg[aria-pressed=true]{background:hsl(var(--h) 60% 32%);color:#fff;border-color:hsl(var(--h) 60% 32%)}
button.tg span{font-weight:400;opacity:.8;margin-left:3px}
.qx-st{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.qx-st button{border:1px solid var(--line,#e0e5ee);background:#fff;border-radius:999px;padding:5px 11px;font-size:.85rem;cursor:pointer}
.qx-st button[aria-pressed=true]{background:var(--blue,#0b5cab);color:#fff;border-color:var(--blue,#0b5cab)}
.q{background:var(--card,#fff);border:1px solid var(--line,#e0e5ee);border-radius:12px;padding:12px 14px;margin:0 0 10px;overflow-wrap:anywhere}
.q h3{font-size:1.02rem;line-height:1.35;margin:0 0 4px;color:var(--ink,#181818)}
.q .meta{margin:0 0 6px;font-size:.8rem;color:var(--muted,#5c5c5c)}
.q .tags{margin:2px 0 0}
.q .ans{margin-top:10px;padding:8px 10px;border-radius:8px;background:#f6f8fb;border-left:4px solid #9aa5b5}
.q .ans.ans{border-left-color:#1b7a3d;background:#f1f9f3}.q .ans.nh{border-left-color:#8a5300;background:#fff8ea}
.q .ans p{margin:0 0 6px;font-size:.92rem}.q .ans .al{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;font-weight:700;color:var(--muted,#5c5c5c)}
.qx-count{font-size:.9rem;color:var(--muted,#5c5c5c);margin:4px 2px 10px}
</style>"""
JS = """<script id="qa-questions-js">(function(){var L=document.getElementById('qx-list');if(!L)return;var st={t:'',s:'',q:''},Q=[].slice.call(L.querySelectorAll('article.q'));
Q.forEach(function(e){e._h=e.textContent.toLowerCase();});
function run(){var n=0,ts=st.q.toLowerCase().split(/\\s+/).filter(Boolean);Q.forEach(function(e){var ok=(!st.t||(' '+e.dataset.tags+' ').indexOf(' '+st.t+' ')>=0)&&(!st.s||e.dataset.st===st.s)&&ts.every(function(w){return e._h.indexOf(w)>=0;});e.hidden=!ok;if(ok)n++;});
document.getElementById('qx-count').textContent=n+(n===1?' question':' questions');
[].forEach.call(document.querySelectorAll('[data-ft]'),function(b){b.setAttribute('aria-pressed',b.dataset.ft===st.t);});
[].forEach.call(document.querySelectorAll('[data-fs]'),function(b){b.setAttribute('aria-pressed',b.dataset.fs===st.s);});}
document.addEventListener('click',function(e){var b=e.target.closest('[data-ft]');if(b){st.t=st.t===b.dataset.ft?'':b.dataset.ft;run();return;}b=e.target.closest('[data-fs]');if(b){st.s=b.dataset.fs;run();}});
var q=document.getElementById('q');if(q){q.addEventListener('input',function(){st.q=q.value.trim();run();});}
try{var p=new URLSearchParams(location.search);if(p.get('tag'))st.t=p.get('tag').replace(/^#/,'');if(p.get('q')){st.q=p.get('q');if(q)q.value=st.q;}}catch(e){}run();})();</script>"""

def render_main(qs):
    cnt = {}
    for x in qs:
        for t in {a['tag'] for a in x['asked_by']}: cnt[t] = cnt.get(t, 0) + 1
    hues = {a['tag']: a['hue'] for x in qs for a in x['asked_by']}
    leg = ''.join('<button class="tg" type="button" data-ft="%s" style="--h:%d" aria-pressed="false">#%s<span>%d</span></button>' % (E(t), hues[t], E(t), c)
                  for t, c in sorted(cnt.items(), key=lambda kv: -kv[1]))
    n_ans = sum(1 for x in qs if x.get('status') in ANSWERED and x.get('status') != 'not held')
    n_nh = sum(1 for x in qs if x.get('status') == 'not held')
    stb = ('<div class="qx-st" role="group" aria-label="Answer"><button type="button" data-fs="" aria-pressed="true">All %d</button>'
           '<button type="button" data-fs="ans" aria-pressed="false">Answered %d</button><button type="button" data-fs="nh" aria-pressed="false">Not held %d</button>'
           '<button type="button" data-fs="open" aria-pressed="false">No answer yet %d</button></div>') % (len(qs), n_ans, n_nh, len(qs) - n_ans - n_nh)
    return ('<main class="wrap" id="qx">\n<details class="qx-f"><summary>Filter by institution (%d)</summary><div class="qx-legend">' % len(cnt) + leg + '</div></details>' + stb +
            '<p class="qx-count" id="qx-count" aria-live="polite">%d questions</p>\n<div id="qx-list">\n' % len(qs) +
            '\n'.join(card(x) for x in qs) + '\n</div>\n</main>')

def patch_page(p, main_html):
    s = p.read_text(errors='ignore')
    if 'Questions &amp; answers' not in s and 'id="qx"' not in s: return False
    s2 = re.sub(r'<main class="wrap"[^>]*>.*?</main>', lambda m: main_html, s, count=1, flags=re.S)
    if s2 == s: return False
    s2 = re.sub(r'<script>(?:(?!</script>).)*fetch\(\'/kb\.json\'.*?</script>', '', s2, count=1, flags=re.S)  # the old loader
    s2 = re.sub(r'<script[^>]*src="[^"]*/qa/ledger\.js"[^>]*></script>', '', s2)
    s2 = re.sub(r'<style id="qa-questions-css">.*?</style>', '', s2, flags=re.S)
    s2 = re.sub(r'<script id="qa-questions-js">.*?</script>', '', s2, flags=re.S)
    s2 = s2.replace('</head>', CSS + '</head>', 1)
    s2 = s2.replace('<p class="sub">Every question put to a public body about Great House Farm, and the answer they gave.</p>',
                    '<p class="sub">What has been asked about Great House Farm, who was asked, and who has answered. Each hashtag opens the email.</p>')
    s2 = re.sub(r'<div class="stats" id="stats"[^>]*></div>', '', s2)
    s2 = s2.replace('<a href="/qa/kb.json">kb.json</a>', '<a href="/qa/questions.json">questions.json</a>')
    # QA pages render their own card list with search, filters and coloured
    # hashtag chips; the cw-graph clip/levels "Read more" passes must not
    # collapse them into plain-text preview cards (30 Oct regression).
    s2 = re.sub(r'<html\b(?![^>]*data-cw-noclip)', '<html data-cw-noclip data-cw-nolevels', s2, count=1)
    i = s2.rfind('</body>')
    s2 = s2[:i] + JS + s2[i:] if i >= 0 else s2 + JS
    p.write_text(s2)
    return True

def ensure_stubs(dist, qs):
    ref = dist / 'email' / 'reference'
    stub = next((f for f in ref.glob('*/index.html')), None) if ref.is_dir() else None
    made = 0
    for x in qs:
        for a in x['asked_by'] + x['answered_by']:
            m = re.match(r'/email/reference/([0-9a-z]+)/', a.get('email') or '')
            if m and stub and not (ref / m.group(1) / 'index.html').exists():
                (ref / m.group(1)).mkdir(parents=True, exist_ok=True); (ref / m.group(1) / 'index.html').write_bytes(stub.read_bytes()); made += 1
    return made

def run(dist):
    dist = pathlib.Path(dist)
    base = json.load(open(ROOT / 'data' / 'qa' / 'questions-base.json'))
    ip = dist / 'email' / 'view' / 'index.json'
    idx = json.load(open(ip)) if ip.exists() else {'records': []}
    qs = build(base, idx)
    made = ensure_stubs(dist, qs)
    main_html = render_main(qs)
    pages = [p for p in dist.glob('qa/index.html')] + [p for p in dist.glob('*/qa/index.html')]
    n = sum(1 for p in pages if patch_page(p, main_html))
    out = {'title': 'Great House Farm: questions asked and answers received', 'generated': idx.get('generated', ''),
           'count': len(qs), 'questions': [{k: x.get(k) for k in ('id', 'question', 'asked', 'status', 'answer', 'reference', 'asked_by', 'answered_by')} for x in qs]}
    (dist / 'qa').mkdir(parents=True, exist_ok=True)
    (dist / 'qa' / 'questions.json').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    print('qa_questions: %d questions, %d institutions, %d pages, %d reference stubs added' % (len(qs), len({a['tag'] for x in qs for a in x['asked_by']}), n, made))
    return qs

if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
