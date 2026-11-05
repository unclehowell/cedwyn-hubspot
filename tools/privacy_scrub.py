#!/usr/bin/env python3
"""privacy_scrub.py — removes working-process attributions from every public file before the catalogue database is built.
Public pages carry sources only: no statement of who found, read or catalogued a record, no attribution to an assistant
or agent, no personal name of the family's representative in correspondence, no quotation of private instructions and no research-cycle numbers. Fixes in place, then fails (exit 1) if any
pattern in CHECK survives, so a page that leaks cannot be published.
Usage: python3 tools/privacy_scrub.py dist [--check-only]"""
import pathlib, re, sys, json
A = r"(?:['\u2019]|&#8217;|&rsquo;|&#x2019;|&#039;|&#39;|&#x27;|\\u2019|'')"     # apostrophe forms (html, json, sql)
QO = r"(?:\u201c|&#8220;|&ldquo;|\\u201c|\")"; QC = r"(?:\u201d|&#8221;|&rdquo;|\\u201d|\")"
SION = r"(?<![A-Za-z])Sion(?: Buckler)?"
EXT = ('.html', '.htm', '.json', '.jsonl', '.txt', '.xml', '.md', '.csv', '.js', '.webmanifest', '.svg', '.rss', '.atom')
R = [
  # quoted private instructions with their date, e.g. (“Just be sure …”, 19 Oct 2026) after a request or instruction
  (rf"\s*(?:at|on)\s+(?:{SION}|the owner|the Owner){A}s\s+(?:request|instruction)s?\s*\({QO}[^)]{{0,400}}?{QC}[^)]{{0,40}}\)", ""),
  (rf"\s*(?:at|on)\s+(?:{SION}|the owner|the Owner){A}s\s+(?:request|instruction)s?\b", ""),
  (rf"\s*\((?:the owner|Owner|{SION}),\s*\d{{1,2}} \w{{3}} \d{{4}}[^)]{{0,30}}\)", ""),
  (rf"\s*\({QO}[^)]{{0,400}}?{QC}[^)]{{0,10}}\)(?=\.\s*Lead from another AI)", ""),
  (r"\s*Lead from another AI; verified by Tab against the source\.", " Checked against the source."),
  (rf"\b(?:GPT-\d+|Tab|Claude|Grok) \(on Owner{A}s instruction\)", "Cedwyn editors"),
  (rf"\bOwner{A}s (?:instruction|request)(?:,\s*\d{{1,2}} \w{{3}} \d{{4}}(?: \d{{1,2}}:\d{{2}}(?: [A-Z]{{3}})?)?)?", "Editorial review"),
  (rf"{SION}{A}s (?:instruction|request)(?:,\s*\d{{1,2}} \w{{3}} \d{{4}}(?: \d{{1,2}}:\d{{2}}(?: [A-Z]{{3}})?)?)?", "Editorial review"),
  # catalogued / compiled by
  (rf"\bCatalogued by Tab for {SION}, ", "Catalogued "),
  (rf";?\s*catalogued by Tab(?: for {SION})?(?=[\s,.;<)\"]|$)", "", re.I),
  (rf"\b(Catalogued|Compiled|Prepared|Written|Edited|Maintained|Checked|Transcribed) by {SION}{A}s Tab agent\b", r"\1 by Cedwyn editors"),
  (rf"\bTab \(for (?:{SION}|the Executive)\)", "Cedwyn editors"),
  (rf"Sion(?: Buckler)?{A}s Tab agent", "Cedwyn editors"),
  (r"\bTab agent", "Cedwyn editors"),
  (rf"\s+by Tab{A}s(?=&hellip;|\u2026)", ""),
  # research attributions
  (rf"\s+by Tab{A}s research(?: cycle)?(?: \d+)?", ""),
  (rf"\bTab{A}s research(?: cycle)?(?: \d+)?", "research"),
  (rf"\b(?:captured )?from Tab{A}s machine", "captured locally"),
  (rf"\bTab{A}s machine", "a local machine"),
  (rf"\b[Tt]he owner{A}s instruction\b(?:\s*\(voice note,[^)]*\))?(?:,\s*\d{{1,2}} \w{{3}} \d{{4}}(?: \d{{1,2}}:\d{{2}}(?: [A-Z]{{3}})?)?)?", "Editorial review"),
  (r"\b(\w+ed|kept privately|held) by Tab\b(?![\w-])", r"\1"),
  (r"\b(found|read|verified|checked|catalogued|compiled|transcribed|added|captured|downloaded|logged|kept privately|noted|confirmed|located) by Tab\b(?!\w)", r"\1", re.I),
  (r"\s*\((?:finding F\d+)\)", ""), (r",\s*finding F\d+", ""), (r"\s*\(finding F\d+\)", ""),
  (r"\s*\((?:flywheel |research )?cycle \d+\)", "", re.I),
  (r"\(\s*(?:flywheel |research )?cycle \d+\s*[;,]\s*", "(", re.I),
  (r"[;,]\s*(?:flywheel |research )?cycle \d+(?=[)\s;,.<])", "", re.I),
  (r"\b(?:flywheel |research )cycle \d+\b", "research", re.I),
  (r"\bcycle (\d+) audit\b", "audit"),
  (r"\s+by Tab(?:, for the owner)?(?![\w\u2019'-])", ""),
  # P-133 (31 Oct 2026): public pages never name the owner as a source or decision-maker, and never carry instruction
  # voice. "per <owner>" becomes the family's account; "<owner>'s decision" goes (or rests with the family); "must be
  # reconciled" becomes a plain statement that it is not yet reconciled. The public voice check (tools/check_public_voice.py)
  # flagged 32 such lines in build 1a2de65. — Sion's Tab agent
  (rf"\bper {SION}(?:\s*\(voice note, (\d{{1,2}} \w{{3}} \d{{4}})\))?\s*:", r"from the family’s account (voice note, \1):"),
  (rf"\bper {SION}\s*\(voice note, (\d{{1,2}} \w{{3}} \d{{4}})\)", r"in the family’s account (voice note, \1)"),
  (rf"\bper {SION}\s*\((\d{{1,2}} \w{{3}} \d{{4}})\)", r"in the family’s account (\1)"),
  (rf"\bPer {SION},\s*", "In the family’s account, "),
  (rf"\bper {SION}(?=\s*\))", "from the family’s account"),
  (rf"\bper {SION}\b", "in the family’s account"),
  (rf";\s*it is {SION}{A}s decision whether to visit(?=\.)", ""),
  (rf";\s*{SION}{A}s decision(?=\.)", ""),
  (rf"\bis {SION}{A}s decision\b", "rests with the family"),
  (rf"\b{SION}{A}s decision\b", "a decision for the family"),
  (r"\bmust be reconciled against civil and probate records before drawing a timeline\b", "are not yet reconciled against civil and probate records, so no timeline is drawn from it"),
  (r"\b(\w+s|identity and date) must be reconciled\b", r"\1 are not yet reconciled"),
  (r"\bmust be reconciled\b", "has not yet been reconciled"),
  (r"\(\s*\)", ""),
]
R = [(re.compile(x[0], x[2] if len(x) > 2 else 0), x[1]) for x in R]
CHECK = re.compile(rf"Tab{A}s research|\bby Tab\b(?![\w-])|Sion{A}s Tab agent|Buckler{A}s request|\bTab agent|catalogued by Tab\b|(?<!site )\bowner{A}s instruction\b(?!s)|\b(?:flywheel|research) cycle \d+", re.I)
PRE = re.compile(r"Tab|[Cc]ycle|[Oo]wner|Sion|reconciled")
EMPTY = R.pop()   # the "()" tidy-up: prose only. Applied to code it turns function(){ into function{ and breaks every script.
PROTECT = re.compile(r"<(script|style|code|pre|textarea)\b[^>]*>.*?</\1\s*>", re.S | re.I)
def _prose_only(t, rx, rep):
    out, n, last = [], 0, 0
    for m in PROTECT.finditer(t):
        seg, k = rx.subn(rep, t[last:m.start()]); out.append(seg); out.append(m.group(0)); n += k; last = m.end()
    seg, k = rx.subn(rep, t[last:]); out.append(seg); n += k
    return ''.join(out), n
def scrub(t, kind='text'):
    n = 0
    if not PRE.search(t): return t, 0
    for rx, rep in R:
        t, k = rx.subn(rep, t); n += k
    if kind == 'html':
        t, k = _prose_only(t, *EMPTY); n += k
    elif kind == 'text':
        t, k = EMPTY[0].subn(EMPTY[1], t); n += k
    return t, n
# Correspondence never names the family's representative (Cedwyn editors, 27 Oct 2026). The site's own mail pages
# (/email/..., /wayback/mail/<id>.txt, /wayback/email/, the What They Don't Say and WhatDoTheyKnow sections) are built from
# exported mail whose From lines, salutations and signatures carry a personal name. Here the sender becomes "Requester"
# (the label the What They Don't Say section uses), the signature title lines go, and any email handle or phone number of the
# family is redacted site-wide. Any path segment containing "correspondence" (research/wiki evidence pages, docs co_*correspondence)
# is correspondence too (27-28 Oct 2026: research/evidence/justice-courts-correspondence/ still signed with the name). Runs on every build, so a later mail import cannot bring the name back; CORR_CHECK then fails the
# build if the name survives in a correspondence file. The agent instruction meta in the shared footer is left as written.
CORR_PATH = re.compile(r"^(?:email|whattheydontsay|whatdotheyknow)/|^wayback/(?:mail|api|email|text)/|(?:^|/)[^/]*correspondence[^/]*/")
_S = r"(?:[\s\u2009]|\\u2009|&#8201;|&thinsp;)+"
_RETD = rf"Ret{A}d"
_FIRST = r"(?i:\bsi(?:[o\u00f4]|\\u00f4|&ocirc;|&#244;)n\b)"
# P-061 (30 Oct 2026): the owner's given name and mail handle are hex-encoded too, so this public file spells neither.
_GN = bytes.fromhex('487977656c').decode(); _EM = bytes.fromhex('687977656c61706275636b6c6572').decode()
NAME = re.compile(
    rf"(?:{_RETD}{_S}(?:Sergeant|Sgt)\.?{_S})?{_FIRST}(?:{_S}\(?{_GN}\)?)?(?:{_S}(?i:buckler)\b)?(?:,?{_S}Esq\.?)?"
    rf"(?:[\s,]*\(?[\s]*(?:{_RETD}{_S}(?:Sergeant|Sergenant|Sgt)\.?|Sgt\.?[\s]*\({_RETD}\))[\s]*\)?)?")
KEEP = 'Sion Buckler (Williams heir'          # the shared footer's agent instruction, not correspondence
# P-054: the private names are stored hex-encoded so this public file does not spell them.
_PN = [bytes.fromhex(h).decode() for h in ('526567616e', '57656262', '4d6172696e61', '4a6166666565', '4272616e77656e')]
_PRIV_RX = r"\b%s(?:\s*>)*\s*%s\b|\b%s(?:\s*>)*\s*%s\b|\b%s(?:(?:\s*>)*\s*(?i:buckler))?\b" % tuple(_PN)
CORR_R = [(re.compile(x[0], x[2] if len(x) > 2 else 0), x[1]) for x in [
  (r"\b(Dear|Hello|Hi|Good (?:morning|afternoon|evening)|Morning|Afternoon)(,?\s+)Mr\.?\s+(?:S\.?\s+)?(?i:buckler)\b", r"\1\2Requester", re.I),
  (rf"\b{_GN} ap Buckler\b", "Requester", re.I),
  (rf"\b{_GN}\s*\.?\s*ap\s*buckler\b", "Requester", re.I),
  (rf"(skype(?:\s+ID)?:\s*)(?:{_GN}|(?i:si[oô]n))\.buckler\b", r"\1[contact redacted]", re.I),
  (rf"\b{_GN}(?=\s+B\.)", "Requester"),
  (rf"\b{_GN}\b(?!\s+Dda\b)", "Requester"),
  (r"\b(Dear|Hello|Hi|Good (?:morning|afternoon|evening)|Morning|Afternoon|Shw ?mae|Helo|Annwyl)(,?\s+)"+_GN+r"\b", r"\1\2Requester", re.I),
  (rf"(Requester\**)\s*\(\s*Ret{A}d (?:Army )?(?:Sergeant|Sergenant|Sgt)\.?\s*\)", r"\1"),
  (r",\s*"+_GN+r"(?=[,.!?])", ""),
  (r"^((?:>[ \t]*)*)"+_GN+r"[ \t]*$", r"\1Requester", re.M),
  (rf"^((?:>[ \t]*)*)\(\s*Ret{A}d (?:Army )?(?:Sergeant|Sergenant|Sgt)\.?\s*\)[ \t]*$", r"\1", re.M),
  (r"[ \t]*Royal Signals Cyber\s*(?:/|and|&amp;|&)\s*Electronic Warfare Professional(?:\s*(?:and|&amp;|&)\s*Life Member)?", ""),
  # P-054 (30 Oct 2026): quoted replies split the signature and the private names across '>' markers, and the private
  # people named in exported mail (a family member and two members of the public) were not covered, so 18 mail texts
  # published them. The Wayback Vault's own redaction (datro@wayback pass 3) is mirrored here for every build.
  (rf"\(?\s*Ret{A}?d\.?(?:\s*>)*\s*Sergeant\s*\)?", ""),
  (r"Royal(?:\s*>)*\s*Signals(?:\s*>)*\s*Cyber(?:\s*>)*\s*(?:/|&amp;|&|and)(?:\s*>)*\s*Electronic(?:\s*>)*\s*Warfare(?:\s*>)*\s*Professional(?:(?:\s*>)*\s*and(?:\s*>)*\s*Life(?:\s*>)*\s*Member)?", "", re.I),
  (_PRIV_RX, "[member of the public]"),
  (r"Requester(\s+Requester)+", "Requester"),
]]
CONTACT_R = [(re.compile(x[0], re.I), x[1]) for x in [
  (rf"\b{_EM}(?:\s*@\s*gmail\.com)?\b", "[email redacted]"),
  (r"\b(?!BG|GB|NK|KN|TN|NT|ZZ)[A-CEGHJ-PR-TW-Z][A-CEGHJ-NPR-TW-Z]\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b", "[NI number redacted]"),
  (r"(?:\+|\b00\s?)?\b44\s?\(?0?\)?\s?7845[\s.-]?933[\s.-]?262\b|\b07845[\s.-]?933[\s.-]?262\b", "[phone redacted]"),
]]
CORR_CHECK = re.compile(r"(?i:\bsi(?:[o\u00f4]|\\u00f4|&ocirc;|&#244;)n\b)(?! Buckler \(Williams heir)")
PRIV_CHECK = re.compile(_PRIV_RX + rf"|Royal Signals Cyber|Ret{A}d Sergeant", re.I)
CONTACT_CHECK = re.compile(_EM + r"|7845[\s.-]?933[\s.-]?262", re.I)
def corr(t, rel):
    n = 0
    for rx, rep in CONTACT_R:
        t, k = rx.subn(rep, t); n += k
    if CORR_PATH.search(rel):
        t = t.replace(KEEP, '\ue000')
        t, k = NAME.subn('Requester', t); n += k
        for rx, rep in CORR_R:
            t, k = rx.subn(rep, t); n += k
        t = t.replace('\ue000', KEEP)
    return t, n
def main(root, check_only=False):
    root = pathlib.Path(root); changed = hits = 0; left = []
    for f in root.rglob('*'):
        if not f.is_file() or f.suffix.lower() not in EXT or f.stat().st_size > 40_000_000: continue
        if any(p in ('db', '.git', 'node_modules') for p in f.relative_to(root).parts[:1]): continue
        try: t = f.read_text('utf-8')
        except Exception: continue
        rel = f.relative_to(root).as_posix()
        if not check_only:
            sx = f.suffix.lower()
            new, n = scrub(t, 'code' if sx in ('.js', '.mjs', '.json', '.jsonl', '.webmanifest', '.svg') else 'html' if sx in ('.html', '.htm', '.xml', '.rss', '.atom') else 'text')
            new, k = corr(new, rel); n += k
            if n and new != t:
                if f.suffix.lower() == '.json':
                    # P-136 (31 Oct 2026): blame the scrub only for JSON it broke. A file an earlier step already left invalid
                    # (build 531e0a8: selfcontain's link removal ate a quote escape in story/api/qa.json) keeps the scrubbed
                    # text, so the attribution still goes, and is named as a warning. — Sion's Tab agent
                    try: json.loads(new)
                    except Exception:
                        try: json.loads(t); was_valid = True
                        except Exception: was_valid = False
                        if was_valid: new = t; left.append(f'{f}: json would break, left for review')
                        else: print(f'::warning::privacy: {rel} was not valid JSON before the scrub; scrubbed text kept')
                if new != t: f.write_text(new, 'utf-8'); changed += 1; hits += n; t = new
        for m in CHECK.finditer(t): left.append(f'{f.relative_to(root)}: {t[max(0,m.start()-60):m.end()+40]!r}')
        for m in CONTACT_CHECK.finditer(t): left.append(f'{rel}: contact detail {t[max(0,m.start()-40):m.end()+20]!r}')
        if CORR_PATH.search(rel) and PRIV_CHECK.search(t): print(f'::warning::privacy: private name left in {rel}')
        if CORR_PATH.search(rel):
            for m in CORR_CHECK.finditer(t): left.append(f'{rel}: name in correspondence {t[max(0,m.start()-60):m.end()+40]!r}')
    print(json.dumps({'files_changed': changed, 'rewrites': hits, 'remaining': len(left)}))
    for x in left[:200]: print('::error::privacy: ' + x)
    return 1 if left else 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1], '--check-only' in sys.argv))
