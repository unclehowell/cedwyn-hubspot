# Cedwyn editorial rule: ingredients, not conclusions

The public statement of these standards is the Values and Standards page, `/values/` (`web/values/index.html`), linked from the menu and the footer of every page. Theme text is benchmarked against it (five tests: cites evidence, keeps fact apart from theory, shows the evidence against, measured tone, respects named people).

Adopted 25 Oct 2026. Every page, theme, caption, summary and build on cedwyn.bucklerfamily.estate follows it.

**The rule.** Cedwyn presents the ingredients, never the finished conclusion. The reader builds the picture in their own head
from what the pages set out. Think of the site's text as one long prompt of cited evidence: every factual sentence carries a
link to its evidence or catalogue page inside Cedwyn, and the reader's own reading does the rest.

## Do
- State what happened, with its date, and link the evidence page (`[EV-xxxx]` → `/research/evidence/ev-xxxx-…/`). Links stay inside Cedwyn (no outbound links).
- State what an event changed in law or in fact, neutrally, and cite the source for it.
- Label every item: **Record** (court judgment, registry, archive, legislation, contemporaneous press), **Family testimony**, **Not yet confirmed**.
- Put what is not known as an **Open question**, with the record that would answer it.
- Cross-link related items (for example "depends on" / "enabled" in 1000 Cuts). Links are ingredients; the reader follows them.
- Set out what was decided, what was never decided, and what went against the family, side by side.
- Interpretation sections stay, labelled **working hypotheses**: each names what it rests on and what would confirm or refute it. Never a finding.

## Don't
- No closing verdict, "our reading" summary or sentence that tells the reader what to conclude.
- No drawn conclusion graphics (no pyramid diagrams, apex labels, "layer N of 9" progress framing, fill-in icons).
- No emotive verdict words in our own text ("the blow", "the fall", "the decisive cut", "ploy").
- Banned words in our own text: says, claims, according to, hearsay, unverified, alleged, fraud, stolen. "Squatters" appears only as a label others applied.
- Public text never names the family member who runs the project, and says nothing about family holdings or addresses.
- Mirrored theme content and evidence are never deleted. A conclusion sentence in mirrored text is reworded at build time through
  `ingredients.json` (applied by `tools/ingredients.py` from `tools/site.py`), in the Cedwyn copy only; datro and its subdomains are untouched.

## How to add a reword
Add an entry to `ingredients.json` (`theme`, `file`, exact `find`, `replace`, `why`). The build report `_cedwyn/reports/ingredients.json`
lists what was applied and any find that no longer matches.

## Small italic: not yet backed by a record (26 Oct 2026)

Text that no record in this archive backs yet is shown smaller and in italic, the same in every theme, with one line per page:
"Small italic text = not yet backed by a record in this archive." (Welsh and Spanish versions in the same line.)

- In data files, put the passage between ⟦ and ⟧, or give a whole entry `"substantiated": false`. `tools/unsub.py` turns the marks
  into `<span class="unsub">` when a page is written; `section.js` does the same after a language change.
- In mirrored theme text, an `ingredients.json` reword wraps the passage in `<span class="unsub">`.
- `runtime.js` (theme pages) and `section.js` (hub pages) carry the one `.unsub` style and add the legend once on any page that has one.
- Typical cases: family research notes whose documents are not held (1392 Cwm Cedwyn), traditions (Marconi, Driscoll),
  and gaps.

Words for title (26 Oct 2026). Bute and Mountjoy: lord of the manor, or the tithe's landowner column, quoted as the column's wording.
BP: registered proprietor from 1982/83. The 1938 and 1969 conveyances: recited only, not produced. A court's "owner" or "paper title"
is that court's wording, given with its date. A rent book does not identify a parcel unless it names one. The c.1841 tithe lists
John Williams as occupier of 36 numbered plots. Tŷ Mawr is first named in a record we have found in 1824 (David Stewart's survey, plan 19, EV-0211). The National Library of
Wales catalogue heading over a group of unread Bute leases (EV-0003) is the cataloguer's, not a record of Tŷ Mawr before 1824.
The title chain itself is on /title-chain/ (data/title-chain.json).

## Chronology and outside records (Sion, 11:45 GMT 26 Oct 2026, m:1138070f)

- We are the chronology and the central record of this story. The site asserts and defends our evidence and our interpretation of it;
  outside narratives (other websites, catalogue summaries, secondary books) are things we test, not sources we repeat.
- Tŷ Mawr is first named in the record we have found in the 1824 David Stewart survey of the Bute Glamorgan estates
  (Glamorgan Archives DB/E/1–2, plan 19 "Cedfin or Ty Mawr Farm", EV-0211).
- The Williams family acquired Tŷ Mawr in 1667. State it plainly with its sources (Mary Williams' statement in the 1974 newspapers; ITV News, 1988); never as "the family's account" (Sion, 13:21 GMT 26 Oct 2026). No document for it is invented.
- Bute estate and other third-party documents are never shown as records of Tŷ Mawr dated before 1824. Do not write "the 1547 lease"
  or "the 1552 Bute deed" as Tŷ Mawr records. Where such a document must be mentioned, it is a Bute (or third-party) document whose
  application to Tŷ Mawr is under forensic examination. Bute's freeholds are under forensic examination for validity.
- Names and dates have been played on: Cydwin, Cydfin, Cedfin, Ked Fen, Tŷ Mawr, Great House, Great House Farm, and the two
  Llandoughs (Llandough-juxta-Penarth, CF64, and Llandough near Cowbridge, CF71). The register is the e-book "Enwau" on /ebooks/.
- Build: `chronology.json` + `tools/chronology.py` (after theme_notices in site.py) reword the old phrasings in mirrored theme text
  and put the "How we treat outside records" notice (en/cy/es) on every page that still shows such a document; the method is on
  /values/#outside-records. Archived correspondence (/wayback/mail/, /email/) and third-party captures (/wayback/websites/) stay verbatim.

## Framing rule: the family's standing is the default; others' stature is tested (26 Oct 2026)

The Williams family of Tŷ Mawr is presented as what the records show it to be: a family of standing in Llandough, at the
Great House across generations (the c.1841 tithe: John Williams on 36 plots, the whole holding), the house the parish's
chief freehold holding and the seat of the manor courts in Heneb's historic environment record, John Williams "for many
years a juror of the court" (1908), Mary (Nancy) Williams refusing the tenancies offered in 1959 and 1965 and asserting
title through her grandfather. The Williams family acquired Tŷ Mawr in 1667 (Mary Williams' statement, 1974 newspapers; ITV News, 1988).

Outside parties' stature is tested against the record, never assumed:
- Bute: lord of the manor. A Bute survey, rate book or tithe column is the estate's own description of itself or of whom it
  charged; it is not a conveyance. No instrument putting the house into Bute's hands has been found; the first record of the
  holding is Bute's own 1824 survey. "Bute owned", "root freehold", "historic landowner" are not used of the house.
- BP: registered proprietor from 1982/83, never "owner". The 1938 and 1969 instruments are recited only.
- Courts: what each court decided (possession, limitation) and what none decided (ownership of the house) are set out
  together; a court's view is not put "first" with the family's as a rejoinder.
- Published histories, outside websites and catalogues: tested, quoted as theirs, never repeated as fact.
- The family is not reduced to "occupier" or "tenant" with nothing else: their standing and length of time travel with it.
  "Tenant" appears as the label Bute's own papers used.
Where the evidence does not yet back a strong statement, it is shown in small italic (.unsub), worded neutrally. No hedges on the family's evidence: not "the family's account", "family tradition", "the family dates" or "known only from"; state the fact and cite the record (Sion, 13:21 GMT 26 Oct 2026).
Audit and rewrites: framing-26oct entries in ingredients.json; data edits D01–D11 (title chain, halves, family case).

## Headline-first pages (26 Oct 2026)

Story pages lead with their headings and each section's first short paragraph; the rest of each section sits behind a native
<details>/<summary> "Read more" (Darllen mwy / Leer más), added at build time by tools/headlines.py in every theme. The text
stays in the HTML (search, the catalogue index, AI readers). The Wales and Argentina hubs open with "The story in headlines"
(data/halves.json → headlines). A page opts out with the attribute data-cw-headlines-off.

## Outside links and Wayback snapshots (rule of 27 Oct 2026)

This rule overrides the older "no outbound links" rule in exactly one place: the two lines under each Wayback snapshot.

- Every link to an outside page opens that page's Cedwyn snapshot under `/wayback/` (`/wayback/go/?u=<address>`, built from `web/_cedwyn/archive/go.html`). The old "leaving the archive" notice page is deleted and must never come back.
- A snapshot shows, in this order: our captured copy of that ONE page (Bootstrap 5 styling from `/_cedwyn/vendor/bootstrap-5.3.3.min.css` when the original CSS does not carry), then a link to the Internet Archive (web.archive.org) copy of the address, then a link to the live website, then a "Captured <date>" line. These two lines are the only links out of Cedwyn; they are built at run time in the page script.
- Inside a captured copy every hyperlink is removed (kept as plain text) unless it opens another Cedwyn snapshot.
- Capture only pages that concern this project, one page at a time. Never crawl, mirror or clone a whole site. Keep captures small: no scripts, trackers, embedded media or large images.
- An address with no capture yet still gets the snapshot page, marked "Snapshot not yet captured", with the Internet Archive link and the live link.
- Captures live in `web/wayback/snap/b/NN.json` (16 buckets; key = FNV-1a 32-bit hex of the address, bucket = last two hex digits mod 16; value = base64 gzip JSON {u, t, title, html, ia, src, pdf}). Add captures by appending to the right bucket; never rewrite another bucket's entries.
- Checkout, payment and mailing-list links (buy.stripe.com, checkout.stripe.com, gumroad.com) are not outside reference links: the snapshot page passes them straight through. Never send them to a snapshot.
- Everywhere else on the site, links stay internal.
