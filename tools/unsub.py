#!/usr/bin/env python3
"""unsub.py - text not yet backed by a record in this archive (Sion, 03:07 GMT 26 Oct 2026, m:891a9b2b). - Sion's Tab agent
"Make text smaller and italic if its not substantiated and backed by evidence in the website."
Data flag: in any data file, a passage between U+27E6 and U+27E7 (the two white square brackets) is "substantiated": false.
A whole entry may instead carry "substantiated": false (title chain: status fam / gap). Rendering, identical in every theme:
- server side, html(page) turns the marks into <span class="unsub">...</span> in visible text (marks inside tags and attribute
  values are dropped; inside <script> they stay, so the language switcher can render them);
- client side, section.js paints marked strings the same way on a language change;
- runtime.js (every theme page) and section.js (hub pages) carry the one .unsub style and add the one-line en/cy/es legend
  ("Small italic text = not yet backed by a record in this archive.") once per page that has any .unsub.
Mirrored theme text uses ingredients.json rewords whose replace wraps the passage in <span class="unsub">.
"""
import re
OPEN, CLOSE = '\u27e6', '\u27e7'
SPAN = '<span class="unsub">'

def strip(s):
    return s.replace(OPEN, '').replace(CLOSE, '')

def html(page):
    parts = re.split(r'(<script\b.*?</script>|<style\b.*?</style>)', page, flags=re.S | re.I)
    for i in range(0, len(parts), 2):
        p = re.sub(r'<[^>]*>', lambda m: strip(m.group(0)), parts[i])
        parts[i] = p.replace(OPEN, SPAN).replace(CLOSE, '</span>')
    return ''.join(parts)

def count(page):
    return len(re.findall(r'class="unsub"', page))
