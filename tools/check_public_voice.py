#!/usr/bin/env python3
"""check_public_voice.py — public pages never address the site owner or carry agent instructions, to-dos or internal notes.
Scans the VISIBLE text of every human-facing HTML page in a built dist/ (scripts, styles, JSON-LD, HTML comments, attributes
and [data-for-agents] blocks removed). Machine-facing areas (/academy/, /agents/, llms.txt, agents.json) and archived third-party
material (/wayback/, /email/, /emails/, /mail/, /wdtk/) are skipped: quoted correspondence keeps its own words.
STRICT patterns fail the build (exit 1); FLAG patterns are reported as warnings in public-voice-report.json (build workspace, not published) for the next agent to
rewrite in neutral, third-person voice. Rule set by the site owner on 30 Oct 2026. Usage: python3 tools/check_public_voice.py dist [--warn-only]
— Sion's Tab agent"""
import json, pathlib, re, sys
SKIP = ('wayback/', 'email/', 'emails/', 'mail/', 'wdtk/', 'academy/', 'agents/', '_blob/', '_ext/', 'db/', '_cedwyn/')
STRICT = [
    (r"\b[Yy]our (working )?theory\b", 'owner address: "your theory"'),
    (r"\b[Pp]er Sion\b", 'owner reference: "per Sion"'),
    (r"\bSion[\u2019']s (decision|mailbox|Tab|agent|own messages)\b", 'owner reference'),
    (r"\b[Nn]ote to (Sion|the owner|self)\b", '"Note to" box'),
    (r"\bTODO\b|\bFIXME\b", 'to-do marker'),
    (r"\bhive turn\b|\bHIVE TURN\b|\bTAB_TASK_ID\b", 'agent/meta note'),
    (r"\bmust be reconciled\b", 'instruction voice'),
]
FLAG = [
    (r"\b(you asked|you should|we need you to|for you to)\b", 'second person / request'),
    (r"\b[Nn]ext step: ask\b|\b[Ss]end this\b|\bas instructed\b", 'instruction'),
    (r"\bHubSpot\b|\bflywheel\b|\bsibling worker\b|\bTab agent\b", 'agent/tooling name'),
    (r"\bSion\b", 'owner named'),
    (r"\b(I will|I\u2019ve|I've)\b", 'first person (fine inside quoted mail)'),
    (r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", 'internal task id'),
]
STRIP = [re.compile(p, re.S | re.I) for p in (r'<script\b.*?</script>', r'<style\b.*?</style>', r'<!--.*?-->',
         r'<(\w+)[^>]*\bdata-for-agents\b[^>]*>.*?</\1>', r'<template\b.*?</template>', r'<blockquote\b.*?</blockquote>',
         r'<div\b[^>]*\bclass="[^"]*\bghf-msg-body\b[^"]*"[^>]*>.*?</div>')]   # quoted mail bodies keep their own words (P-133)
def visible(html):
    for rx in STRIP: html = rx.sub(' ', html)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html))
def main(dist, warn_only=False):
    root = pathlib.Path(dist); strict, flags = [], []
    for f in root.rglob('*.html'):
        rel = f.relative_to(root).as_posix()
        if rel.startswith(SKIP): continue
        try: t = visible(f.read_text(errors='ignore'))
        except Exception: continue
        for rx, why in STRICT:
            for m in re.finditer(rx, t): strict.append({'page': '/' + rel, 'why': why, 'text': t[max(0, m.start()-60):m.end()+60]})
        for rx, why in FLAG:
            n = len(re.findall(rx, t))
            if n: flags.append({'page': '/' + rel, 'why': why, 'count': n})
    rep = {'rule': 'public pages never address the owner or carry agent instructions, to-dos or internal notes; neutral third-person only',
           'strict': strict, 'flags': flags}
    pathlib.Path('public-voice-report.json').write_text(json.dumps(rep, indent=1, ensure_ascii=False))   # build workspace, never published
    for s in strict[:50]: print(f"::error file={s['page']}::public voice ({s['why']}): {s['text']}")
    print(f'public voice: {len(strict)} strict hits, {len(flags)} flagged page/pattern pairs')
    return 1 if strict and not warn_only else 0
if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'dist', '--warn-only' in sys.argv))
