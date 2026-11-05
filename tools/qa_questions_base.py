#!/usr/bin/env python3
"""qa_questions_base.py - writes data/qa/questions-base.json for tools/qa_questions.py (30 Oct 2026).
Source: the curated Q&A base (qa.bucklerfamily.estate/kb.json: one question per body, with status and answer) matched to
the mail catalogue (/email/view/index.json): each question gets the sent email it was asked in (reference number first,
else the nearest sent date to that body) and, when answered, the reply (same thread, else same reference, else a reply from
that body within 3 days of the answer date). Questions with the same wording put to several bodies are merged into one.
Run: python3 tools/qa_questions_base.py kb.json index.json > data/qa/questions-base.json - Sion's Tab agent"""
import json, re, sys, difflib, unicodedata, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qa_questions import clean, short
from datetime import date
BODY2IDS = {'Amgueddfa Cymru – Museum Wales': ['museum'], 'Cadw / Welsh Government': ['cadw'], 'Crown Prosecution Service': ['cps'], 'DCMS': ['dcms'],
 'Glamorgan Archives': ['glamorgan'], 'HM Land Registry': ['hmlr', 'hmlr-icr'], 'Heneb (former GGAT)': ['heneb'], "Information Commissioner's Office": ['ico'],
 'Llandough Community Council': ['llandough'], 'Ministry of Defence': ['mod'], 'Ministry of Justice / HMCTS': ['moj'], 'NPCC': ['nactso'],
 'National Library of Wales': ['nlw'], 'RCAHMW (Royal Commission)': ['rcahmw'], 'Royal Mail / Post Office': ['postal-museum', 'bt-archives'],
 'South Wales Police': ['swp'], 'The National Archives': ['tna'], 'Vale of Glamorgan Council': ['vale-foi', 'vale-scrutiny'], 'Wales Office': ['wales-office']}
ANS = {'answered', 'partly answered', 'not held', 'refused', 'redirected', 'statement only', 'contested'}
def d(s): return date.fromisoformat(s[:10])
def nr(s): return re.sub(r'[^a-z0-9]', '', (s or '').lower())
def nq(q):
    q = unicodedata.normalize('NFKD', q.lower()); q = re.sub(r'[^a-z0-9 ]', ' ', q); return re.sub(r'\s+', ' ', q).strip()
def main(kbp, idxp):
    kb = json.load(open(kbp)); R = json.load(open(idxp))['records']
    sent = [r for r in R if r['direction'] == 'sent']; BOUNCE = re.compile(r'undeliverable|automatic reply|auto-?reply|out of office|delivery status|mail delivery|delivery has failed|acknowledg|we have received your|thank you for your (email|enquiry|request)', re.I)
    rec = [r for r in R if r['direction'] == 'received' and not BOUNCE.search(r.get('subject', ''))]
    ins = lambda r: {i['id'] for i in r['institutions']}
    def m_sent(x, ids):
        c = [r for r in sent if ins(r) & ids]
        if not c: return None
        ref = nr(x.get('reference'))
        if ref:
            rc = [r for r in c if any(nr(f) == ref or ref in nr(f) or (len(nr(f)) > 3 and nr(f) in ref) for f in r['refs']) or ref in nr(r['subject'])]
            if rc: c = rc
        if x.get('asked'): c.sort(key=lambda r: abs((d(r['date']) - d(x['asked'])).days))
        return c[0]
    def m_reply(x, ids, s):
        c = [r for r in rec if ins(r) & ids]
        ref = nr(x.get('reference'))
        pool = [r for r in c if s and r['threadId'] == s['threadId']] or [r for r in c if ref and any(nr(f) == ref for f in r['refs'])]
        tgt = x.get('answered') or (s['date'] if s else None)
        if pool:
            if tgt: pool.sort(key=lambda r: abs((d(r['date']) - d(tgt)).days))
            return pool[0]
        if x.get('answered') and c:
            c.sort(key=lambda r: abs((d(r['date']) - d(x['answered'])).days))
            if abs((d(c[0]['date']) - d(x['answered'])).days) <= 3: return c[0]
        return None
    out = []
    for x in sorted((i for i in kb['items'] if i.get('kind') != 'case'), key=lambda i: i.get('asked') or ''):
        ids = set(BODY2IDS.get(x['body'], []))
        s = m_sent(x, ids) if ids else None
        rp = m_reply(x, ids, s) if (ids and x['status'] in ANS) else None
        nm = (s or rp or {}).get('institutions') or []
        nm = next((i for i in nm if i['id'] in ids), None)
        ask = {'inst': (nm or {}).get('id') or (sorted(ids)[0] if ids else x['body']), 'name': (nm or {}).get('name') or x['body'], 'sent': s and s['id'], 'reply': rp and rp['id']}
        k = nq(x['question'])
        g = next((g for g in out if difflib.SequenceMatcher(None, k, g['_k']).ratio() >= 0.86), None)
        if g:
            g['asks'].append(ask); g['asked'] = max(g['asked'], x.get('asked') or '')
            continue
        out.append({'_k': k, 'id': x['id'], 'question': clean(x['question']), 'answer': short(x.get('answer', ''), 420), 'status': x['status'], 'reference': clean(x.get('reference', '')),
                    'asked': x.get('asked') or '', 'answered': x.get('answered') or '', 'asks': [ask]})
    for g in out: g.pop('_k')
    json.dump({'source': 'kb.json ' + kb.get('meta', {}).get('generated', '') + ' + mail catalogue', 'count': len(out), 'questions': out},
              sys.stdout, ensure_ascii=False, separators=(',', ':'))
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
