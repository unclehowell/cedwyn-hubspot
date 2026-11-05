# Cedwyn version standard 1.0.0 (1 Nov 2026)

One rule for every versioned thing on the site (e-books, documentary cuts, and any course, piece or item that gains versions).
The owner's words (1 Nov 2026 01:31): latest versions are paid; each previous semantic version is £4.99 less, down to v0.0.1,
which is free; an info icon beside the drop-down opens a table of the changelog; the same everywhere, kept that way by a flywheel.

## 1. Versions and prices
- Versions are semantic (`vMAJOR.MINOR.PATCH`), listed oldest first. The first is always `v0.0.1` and it is always free.
- Only the **latest** version's price is stored (`price`, e.g. `£4.99`). Every other price is computed:
  `price(i) = max(0, latest − £4.99 × steps back)`, and `v0.0.1` is £0 whatever the arithmetic gives.
  Two versions today: v0.0.1 free, v0.0.2 £4.99. A third at £9.98 would make the middle one £4.99.
- An item with no paid version (latest price £0 or no price) gets **no gate**: its normal link or player.
- Never a per-page or per-day price; never "was" or "save". Whole price with a size.

## 2. Drop-down labels (exact)
- Free: `v0.0.1 — free (20 pages)` · paid: `v0.0.2 — £4.99 (221 pages)`. Size = pages, or length for video (`12 min`).
- Welsh / Spanish: `am ddim` / `gratis`, `tudalen` / `páginas`. The free version is preselected.

## 3. The (i) version table
An (i) button sits beside every version drop-down. It opens a dialog (inside the media slot) with one row per version, newest
first: **Version · Date · What changed · Pages or length · Price** (prices computed as in §1). Rows come from the item's
`versions[].change`; an item without them gets them built from its existing changelog (data/ebooks.json, the e-book archive,
the documentary manifest). Esc and × close it and focus returns to (i).

## 4. Where it lives
- Data: `web/_cedwyn/version-gate.json` (schema `web/_cedwyn/version-manifest.schema.json`).
- Behaviour: `web/_cedwyn/version-gate.js` + `.css`, loaded by `ghf-boot.js` on every page (spec of the gate: docs/VERSION-GATE.md).
- A webapp with its own version picker (the /ebooks/ shelf cards, the documentary chips, the NFT garden) follows §1–§3 in its
  own markup; the audit reads the live pages and reports drift.

## 5. The audit (the flywheel)
`python3 tools/version_audit.py [--live]` checks, and with `--fix` corrects minor drift in the manifest only:
- schema fields and types; versions ascending and unique; first `0.0.1`; dates ISO; change text present;
- the latest price equals data/ebooks.json's current price for the book; computed ladder; no stored per-version prices;
- banned public words and per-page wording in change text; images are `/nft-art/art/*.webp`;
- `--live`: each book on /ebooks/ shows `v0.0.1 — free` and the latest at its computed price, every manifest image answers 200
  and is under 400 KB, and /_cedwyn/version-gate.json is served.
It prints one line per finding and exits 1 when a finding is not auto-fixable. Run it every 6 h; anything it cannot fix goes to
the problems queue.

## CHANGELOG
- 1.0.0 (2026-11-01): first version. — Cedwyn editors
