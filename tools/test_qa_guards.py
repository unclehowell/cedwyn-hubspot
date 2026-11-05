#!/usr/bin/env python3
"""test_qa_guards.py - repeatable, hermetic test matrix for the Q&A guardrail checks
(tools/check_app_pages.py, tools/check_qa_built.py, tools/check_qa_served.py).

Builds tiny labelled fixtures in a temp dir (two-question source data, three alias pages, a
fixture cw-graph.js, a local HTTP server for the served-layer and raw-source pinning) and
asserts exit codes and key output for the full positive/negative matrix. Stdlib only, no
network beyond localhost. Run: python3 tools/test_qa_guards.py  (wired into build.yml preflight)"""
import functools, http.server, json, os, pathlib, subprocess, sys, tempfile, threading

TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from check_app_pages import BASELINE_NOCLIP

BASE = {"source": "fixture", "count": 2, "questions": [
    {"id": "alpha", "question": "Alpha?", "answer": "A.", "status": "answered", "reference": "",
     "asked": "2026-01-01", "answered": "2026-01-02",
     "asks": [{"inst": "cadw", "name": "Cadw", "sent": "s1", "reply": "r1"}]},
    {"id": "beta", "question": "Beta?", "answer": "", "status": "no reply", "reference": "",
     "asked": "2026-01-03", "answered": "",
     "asks": [{"inst": "heneb", "name": "Heneb", "sent": "s2", "reply": ""}]}]}
INDEX = {"generated": "2026-01-04", "records": [
    {"id": "s1", "threadId": "t1", "direction": "sent", "date": "2026-01-01", "subject": "Alpha",
     "institutions": [{"id": "cadw", "name": "Cadw"}]},
    {"id": "r1", "threadId": "t1", "direction": "received", "date": "2026-01-02", "subject": "Re: Alpha",
     "institutions": [{"id": "cadw", "name": "Cadw"}]},
    {"id": "s2", "threadId": "t2", "direction": "sent", "date": "2026-01-03", "subject": "Beta",
     "institutions": [{"id": "heneb", "name": "Heneb"}]}]}
CW = 'var NOCLIP = /^\\/(?:(?:wales|argentina)\\/)?(?:%s)(?:\\/|$)/;\n' % '|'.join(BASELINE_NOCLIP)
REDIRECTS = ('/wales/tour /wales/#stop-1 301\n'
             '/wales/:theme/* /:theme/:splat 200\n'
             '/argentina/:theme/* /:theme/:splat 200\n')   # tools/sections.py step 5 contract

def page(attrs=True, beta=True, alpha_answered='#Cadw', dup=False, marker=True):
    h = '<html lang="en"%s><body>' % (' data-cw-noclip data-cw-nolevels' if attrs else '')
    h += '<main id="qx">' if marker else '<main>'
    h += ('<button class="tg" data-ft="Cadw">#Cadw<span>1</span></button>'
          '<button class="tg" data-ft="Heneb">#Heneb<span>1</span></button>')
    a1 = ('<article class="q" id="q-alpha" data-tags="Cadw" data-st="ans"><h3>Alpha?</h3>'
          '<div class="tags"><a class="tg" href="/email/reference/s1/">#Cadw</a></div>')
    if alpha_answered:
        a1 += '<div class="ans"><div class="tags"><a class="tg" href="/email/reference/r1/">%s</a></div></div>' % alpha_answered
    a1 += '</article>'
    h += a1
    if dup:
        h += a1.replace('Alpha?', 'Alpha duplicate?')
    if beta:
        h += ('<article class="q" id="q-beta" data-tags="Heneb" data-st="open"><h3>Beta?</h3>'
              '<div class="tags"><a class="tg" href="/email/reference/s2/">#Heneb</a></div></article>')
    return h + '</main></body></html>'

def write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)

def built_dist(d, qj, redirects=REDIRECTS, **kw):
    # the intended contract: ONE canonical page file + questions.json + the Pages rewrite rules
    write(pathlib.Path(d) / 'qa' / 'index.html', page(**kw))
    if qj is not None:
        write(pathlib.Path(d) / 'qa' / 'questions.json', qj)
    if redirects is not None:
        write(pathlib.Path(d) / '_redirects', redirects)

def alias_pages(root, **kw):
    for alias in ('qa', 'wales/qa', 'argentina/qa'):
        write(pathlib.Path(root) / alias / 'index.html', page(**kw))

def main():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix='qa-guards-'))
    write(tmp / 'base.json', json.dumps(BASE))
    write(tmp / 'index.json', json.dumps(INDEX))
    # raw-source fixture for stamp pinning: /repo/<commit>/data/qa/questions-base.json
    write(tmp / 'repo' / 'deadbeef' / 'data' / 'qa' / 'questions-base.json', json.dumps(BASE))
    # served fixture sites
    alias_pages(tmp / 'site-full')
    write(tmp / 'site-full' / 'email' / 'view' / 'index.json', json.dumps(INDEX))
    write(tmp / 'site-full' / '_cedwyn' / 'reports' / 'build.json', '{"commit":"deadbeef"}')
    alias_pages(tmp / 'site-nostamp')   # no build stamp, no email index
    # cw-graph fixture root + dists for the app-page check
    write(tmp / 'root' / 'web' / '_cedwyn' / 'cw-graph.js', CW)
    write(tmp / 'root' / 'dist-ok' / 'qa' / 'index.html', page())
    write(tmp / 'root' / 'dist-noattrs' / 'qa' / 'index.html', page(attrs=False))
    write(tmp / 'root-nocw' / 'dist' / 'a.html', '<html><body>x</body></html>')
    write(tmp / 'root-narrowed' / 'web' / '_cedwyn' / 'cw-graph.js',
          CW.replace('|' + BASELINE_NOCLIP[-1], ''))
    write(tmp / 'root-narrowed' / 'dist' / 'qa' / 'index.html', page())
    (tmp / 'root-empty' / 'dist').mkdir(parents=True)
    # built-check fixture dists (questions.json = built truth)
    sys.path.insert(0, str(TOOLS))
    from qa_questions import build as qbuild
    qs = qbuild(BASE, INDEX)
    qj = json.dumps({'title': 't', 'generated': 'x', 'count': len(qs), 'questions': [
        {k: x.get(k) for k in ('id', 'question', 'asked', 'status', 'answer', 'reference', 'asked_by', 'answered_by')}
        for x in qs]})
    for name, kw in [('good', {}), ('truncated', {'beta': False}), ('chipless', {'alpha_answered': None}),
                     ('label-trap', {'alpha_answered': '#CadwExtra'}), ('dup-id', {'dup': True}),
                     ('no-marker', {'marker': False})]:
        built_dist(tmp / ('dist-' + name), qj, **kw)
    built_dist(tmp / 'dist-no-redirects', qj, redirects=None)
    built_dist(tmp / 'dist-one-rule', qj, redirects='/argentina/:theme/* /:theme/:splat 200\n')
    built_dist(tmp / 'dist-no-qj', None)
    d = tmp / 'dist-no-pages'
    write(d / 'qa' / 'questions.json', qj)
    write(d / '_redirects', REDIRECTS)
    # entity-containing question ID: renderer writes html.escape(id[:70]), the parser decodes it back
    import html as _html
    ent_base = {"source": "fixture", "count": 1, "questions": [
        {"id": 'a&b<c>"q"', "question": "Entity?", "answer": "A.", "status": "answered", "reference": "",
         "asked": "2026-01-01", "answered": "2026-01-02",
         "asks": [{"inst": "cadw", "name": "Cadw", "sent": "s1", "reply": "r1"},
                  {"inst": "heneb", "name": "Heneb", "sent": "s2", "reply": ""}]}]}
    ent_qs = qbuild(ent_base, INDEX)
    ent_qj = json.dumps({'title': 't', 'generated': 'x', 'count': len(ent_qs), 'questions': [
        {k: x.get(k) for k in ('id', 'question', 'asked', 'status', 'answer', 'reference', 'asked_by', 'answered_by')}
        for x in ent_qs]})
    ent_id = 'q-' + _html.escape('a&b<c>"q"'[:70])
    ent_page = ('<html lang="en" data-cw-noclip data-cw-nolevels><body><main id="qx">'
                '<button class="tg" data-ft="Cadw">#Cadw<span>1</span></button>'
                '<button class="tg" data-ft="Heneb">#Heneb<span>1</span></button>'
                '<article class="q" id="%s" data-tags="Cadw Heneb" data-st="ans"><h3>Entity?</h3>'
                '<div class="tags"><a class="tg" href="/email/reference/s1/">#Cadw</a>'
                '<a class="tg" href="/email/reference/s2/">#Heneb</a></div>'
                '<div class="ans"><div class="tags"><a class="tg" href="/email/reference/r1/">#Cadw</a></div></div>'
                '</article></main></body></html>' % ent_id)
    d = tmp / 'dist-entity'
    write(d / 'qa' / 'index.html', ent_page)
    write(d / 'qa' / 'questions.json', ent_qj)
    write(d / '_redirects', REDIRECTS)

    # truncated-over-HTTP fixture (uniform across all aliases)
    alias_pages(tmp / 'site-trunc', beta=False)
    write(tmp / 'site-trunc' / 'email' / 'view' / 'index.json', json.dumps(INDEX))
    write(tmp / 'site-trunc' / '_cedwyn' / 'reports' / 'build.json', '{"commit":"deadbeef"}')

    # localhost server for served-layer + pinning tests
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    handler = functools.partial(Quiet, directory=str(tmp))
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    env = dict(os.environ, CHECK_QA_RAW_BASE='http://127.0.0.1:%d/repo/%%s/data/qa/questions-base.json' % port,
               PYTHONDONTWRITEBYTECODE='1')

    def run(script, *args):
        p = subprocess.run([sys.executable, str(TOOLS / script), *args],
                           capture_output=True, text=True, timeout=120, env=env)
        return p.returncode, p.stdout + p.stderr

    full = 'http://127.0.0.1:%d/site-full' % port
    nostamp = 'http://127.0.0.1:%d/site-nostamp' % port
    bf, inf = str(tmp / 'base.json'), str(tmp / 'index.json')
    T = [
        # --- check_app_pages.py
        ('app: missing dist fails closed', *run('check_app_pages.py', str(tmp / 'no-such')), 1, 'does not exist'),
        ('app: empty dist fails closed', *run('check_app_pages.py', str(tmp / 'root-empty' / 'dist')), 1, 'no HTML files'),
        ('app: missing cw-graph fails closed', *run('check_app_pages.py', str(tmp / 'root-nocw' / 'dist')), 1, 'cw-graph.js not found'),
        ('app: qa without attrs fails', *run('check_app_pages.py', str(tmp / 'root' / 'dist-noattrs')), 1, 'without data-cw-noclip'),
        ('app: qa with attrs passes', *run('check_app_pages.py', str(tmp / 'root' / 'dist-ok')), 0, 'OK'),
        ('app: --site-root honoured', *run('check_app_pages.py', str(tmp / 'root-nocw' / 'dist'), '--site-root', str(tmp / 'root')), 0, 'OK'),
        ('app: narrowed NOCLIP fails', *run('check_app_pages.py', str(tmp / 'root-narrowed' / 'dist')), 1, 'NOCLIP narrowed'),
        ('app: --warn-only exits 0', *run('check_app_pages.py', str(tmp / 'root' / 'dist-noattrs'), '--warn-only'), 0, 'would fail'),
        ('app: --ref value not misparsed as dist', *run('check_app_pages.py', '--warn-only', '--site-root', str(tmp / 'root'), str(tmp / 'root' / 'dist-ok')), 0, 'OK'),
        # --- check_qa_built.py
        ('built: good dist passes', *run('check_qa_built.py', str(tmp / 'dist-good')), 0, 'OK (1 page file(s), 2 alias route rule(s), 2 questions'),
        ('built: uniform truncation fails', *run('check_qa_built.py', str(tmp / 'dist-truncated')), 1, 'not served'),
        ('built: dropped chip fails by name', *run('check_qa_built.py', str(tmp / 'dist-chipless')), 1, 'chip mismatch'),
        ('built: #CadwExtra is not #Cadw', *run('check_qa_built.py', str(tmp / 'dist-label-trap')), 1, 'chip mismatch'),
        ('built: duplicate article ID fails', *run('check_qa_built.py', str(tmp / 'dist-dup-id')), 1, 'duplicate question ID'),
        ('built: missing questions.json fails closed', *run('check_qa_built.py', str(tmp / 'dist-no-qj')), 1, 'questions.json missing'),
        ('built: no Q&A pages fails closed', *run('check_qa_built.py', str(tmp / 'dist-no-pages')), 1, 'nothing was checked'),
        ('built: missing _redirects fails', *run('check_qa_built.py', str(tmp / 'dist-no-redirects')), 1, '_redirects missing'),
        ('built: lost wales rewrite rule fails', *run('check_qa_built.py', str(tmp / 'dist-one-rule')), 1, 'wales/:theme'),
        ('built: markerless alias fails', *run('check_qa_built.py', str(tmp / 'dist-no-marker')), 1, 'id="qx" absent'),
        ('built: entity-containing question ID round-trips', *run('check_qa_built.py', str(tmp / 'dist-entity')), 0, 'OK'),
        # --- check_qa_served.py
        ('served: full site passes (pinned via stamp)', *run('check_qa_served.py', full), 0, 'published build stamp'),
        ('served: uniform truncation of all aliases fails', *run('check_qa_served.py', 'http://127.0.0.1:%d/site-trunc' % port), 1, 'not served'),
        ('served: no stamp and no --ref fails closed', *run('check_qa_served.py', nostamp), 1, 'Refusing an unpinned expectation'),
        ('served: unreachable base fails closed', *run('check_qa_served.py', 'http://127.0.0.1:9/x', '--base-file', bf, '--index-file', inf), 1, 'fetch failed'),
        ('served: unreachable stamp endpoint fails closed', *run('check_qa_served.py', 'http://127.0.0.1:9/x'), 1, 'unavailable'),
    ]

    failed = 0
    for name, code, out, want_code, want_sub in T:
        ok = code == want_code and (not want_sub or want_sub in out)
        print('%s %-46s exit=%d' % ('PASS' if ok else 'FAIL', name, code))
        if not ok:
            failed += 1
            print('  wanted exit=%d substring=%r; output tail: %s' % (want_code, want_sub, out[-400:]))
    srv.shutdown()
    print('\ntest_qa_guards: %s (%d/%d)' % ('FAIL' if failed else 'OK', len(T) - failed, len(T)))
    return 1 if failed else 0

if __name__ == '__main__':
    sys.exit(main())
