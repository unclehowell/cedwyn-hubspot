#!/usr/bin/env python3
"""agent_lint.py — editorial checks for pull requests from AI agents (Cedwyn Academy, /academy/ACADEMY/CONTRIBUTING.html).
Fails on: banned public words, outbound links, pre-1824 outside catalogue dates, private names (checked by hash, so no name is
written here), working-process attributions (who found or catalogued a record, private instructions, research-cycle numbers), email addresses or phone numbers, payment offers, and content pages with no citation (EV-####, MR-####, an archive
reference, or a Source line). It only READS the files; pull-request code is never run.
Usage: python3 tools/agent_lint.py --root <checkout> --list <file of changed paths>   — Sion's Tab agent"""
import argparse, base64, hashlib, json, pathlib, re, sys
BANNED = json.loads(base64.b64decode('WyJzYXlzIiwgImNsYWltcyIsICJhY2NvcmRpbmcgdG8iLCAiaGVhcnNheSIsICJ1bnZlcmlmaWVkIiwgImFsbGVnZWQiLCAiZnJhdWQiLCAic3RvbGVuIl0='))
NAME_HASHES = set(["b5e91c059fd73705a35d6551ffc7ce5b673c9618f9a635ee43ddf61b5e842636", "4f8f44b4e2eb484e0f0d08aa378d387c829e910e11ab08acb9653e7a3e2a7c7c", "1208260b0c800782c9bd5f174f44c53673dfbf52415c260524c753b37780a918", "28d193a69746444e1698342d9039fe0b4faa289b9a0a2c289ba551123d61bbc0", "233def1823ddfc750df56bc709dc68fac77deafa35565926e600473301d925f3", "e7a180f7395e42da076c2fb756f83256c4e196f8071f5c9edd2172e7d29ed1ab"])
CONTENT = ('.md', '.html', '.htm', '.txt')
EXEMPT = ('tools/', '.github/', 'reports/', 'data/', 'notices/')
CITE = re.compile(r'\b(EV|MR)-\d{3,5}\b|\b[A-Z]{1,6}(/[A-Z0-9]{1,6}){2,}\b|\bSources?:|\b\[\d{4}\] EWCA|\bD ?\d{1,4}(/\d+)*\b')
CHECKS = [
    ('banned word', re.compile(r'\b(' + '|'.join(re.escape(b) for b in BANNED) + r')\b', re.I)),
    ('outbound link', re.compile(r'(href|src)\s*=\s*["\']?https?://(?!([\w-]+\.)*bucklerfamily\.estate)(?!cdn\.jsdelivr\.net/gh/unclehowell/cedwyn-movie@(?:[0-9a-f]{40}|main)/extras/parcels-1841(?:-30s)?\.webm)|\]\(https?://(?!([\w-]+\.)*bucklerfamily\.estate)(?!cdn\.jsdelivr\.net/gh/unclehowell/cedwyn-movie@(?:[0-9a-f]{40}|main)/extras/parcels-1841(?:-30s)?\.webm)', re.I)),
    ('pre-1824 outside date', re.compile(r'\b(1547|1552)\b')),
    ('email address', re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')),
    ('phone number', re.compile(r'(\+44|\+54)[\s\d()-]{8,}\d|\b0\d{3,4}\s?\d{6,7}\b')),
    ('payment offer', re.compile(r'happy to pay|will pay|agree to pay|enclose a cheque', re.I)),
    ('private working process', re.compile(r"Tab['\u2019]s research|\bby Tab\b|Tab agent|catalogued by Tab|\w+['\u2019]s request \(|\b(?:research|flywheel) cycle \d+|\(cycle \d+|\bowner['\u2019]s instruction\b|\bon WhatsApp\b", re.I)),
]
JOURNAL = 'data/journal/pages.json'
JOURNAL_KEYS = {'v', 'date', 'note', 'agent'}
KEY_PATH = re.compile(r'^/[A-Za-z0-9._~/-]*$')
KEY_LINE = re.compile(r'^(\s*)"(/[^"\\]*)"(:\s*\[\s*)$')


def journal_shape_ok(text):
    """True only when the file has the documented page-journal shape: {schema, note, pages{path: [entry]}}
    with every path key a plain site path and every entry a dict of the known string fields."""
    try:
        d = json.loads(text)
    except ValueError:
        return False
    if not isinstance(d, dict) or set(d) != {'schema', 'note', 'pages'}:
        return False
    if not isinstance(d['schema'], str) or not isinstance(d['note'], str) or not isinstance(d['pages'], dict):
        return False
    for key, entries in d['pages'].items():
        if not KEY_PATH.match(key) or not isinstance(entries, list):
            return False
        for e in entries:
            if not isinstance(e, dict) or not set(e) <= JOURNAL_KEYS or not all(isinstance(v, str) for v in e.values()):
                return False
    return True


def lint(path, text):
    out = []
    neutral = path == JOURNAL and journal_shape_ok(text)
    for i, line in enumerate(text.splitlines(), 1):
        scan = line
        if neutral:
            # A page path used as an object key is structure, not prose. Only the banned-word check reads the
            # neutralised copy of that key line. Every other check (and the private-name check below) still
            # reads the original line, and every entry field (v, date, note, agent) is scanned unchanged.
            mk = KEY_LINE.match(line)
            if mk:
                scan = mk.group(1) + '"/page/"' + mk.group(3)
        for name, rx in CHECKS:
            if name == 'private working process' and path.startswith(EXEMPT): continue
            m = rx.search(scan if name == 'banned word' else line)
            if m: out.append(f'{path}:{i}: {name}: {m.group(0)[:50]}')
        for tok in re.findall(r"[A-Za-zÀ-ÿŵŷ]+", line):
            if hashlib.sha256(tok.lower().encode()).hexdigest() in NAME_HASHES:
                out.append(f'{path}:{i}: private or protected name'); break
    if path.endswith(CONTENT) and not path.startswith(EXEMPT) and len(text) > 400 and not CITE.search(text):
        out.append(f'{path}: content page with no citation (add EV-####, MR-####, an archive reference or a Source line)')
    return out
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--root', default='.'); ap.add_argument('--list'); ap.add_argument('paths', nargs='*')
    a = ap.parse_args(); root = pathlib.Path(a.root)
    paths = a.paths + ([l.strip() for l in open(a.list) if l.strip()] if a.list else [])
    problems = []
    for p in paths:
        f = root / p
        if not f.is_file() or f.suffix.lower() not in CONTENT + ('.json', '.csv', '.xml'): continue
        problems += lint(p, f.read_text('utf-8', 'replace'))
    for x in problems: print('::error::' + x)
    print(json.dumps({'files': len(paths), 'problems': len(problems)}))
    sys.exit(1 if problems else 0)
