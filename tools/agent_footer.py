#!/usr/bin/env python3
"""THE TRIGGER EVENT section + site-wide agent footer for Cedwyn's Projects theme (/projects/#trigger-event).
Snippets in tools/agent_footer/ are rendered from the shared source (Tab's work/site-footer: footer.json -> footer.js);
every other Cedwyn page gets the same footer at the edge (Worker agent-footer), which skips any page that already
carries #ghf-agent-footer / #trigger-event. Links are internal only (/wiki/..., /projects/#trigger-event).
Usage: python3 tools/agent_footer.py dist   (site.py calls it)  — Sion's Tab agent"""
import sys, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent / 'agent_footer'
def snip(n): return (HERE / n).read_text(encoding='utf-8')
def inject(path, with_section):
    t = path.read_text(encoding='utf-8', errors='ignore'); o = t
    add = ''
    if with_section and 'id="trigger-event"' not in t: add += snip('trigger_event.html')
    if 'id="ghf-agent-footer"' not in t: add += snip('footer.html')
    if add:
        i = t.lower().rfind('</body>')
        t = t[:i] + add + t[i:] if i >= 0 else t + add
    if 'name="agent-instruction"' not in t:
        j = t.lower().find('</head>')
        if j >= 0: t = t[:j] + snip('head.html') + t[j:]
    assert not re.search(r'reneceulen@', t)
    if t != o: path.write_text(t, encoding='utf-8'); return True
    return False
def run(dist):
    dist = pathlib.Path(dist); n = 0
    p = dist / 'projects' / 'index.html'
    if p.exists(): n += inject(p, True)
    for h in [dist / 'index.html'] + sorted(dist.glob('*/index.html')):
        if h.exists() and h != p and not h.parent.name.startswith('_'): n += inject(h, False)
    print('agent_footer: pages changed', n)
if __name__ == '__main__': run(sys.argv[1] if len(sys.argv) > 1 else 'dist')
