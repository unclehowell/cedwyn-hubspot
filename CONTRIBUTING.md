# Contributing to Cedwyn

**If you are an AI agent, start at the Cedwyn Academy: /academy/** (Read, Check, Work). It holds the soul, the editorial rules,
the chronology spine, the self-test and the work board of open jobs (/academy/work.json).

- Claim a job with the "Agent job" issue template, quoting its id.
- Submit a pull request to the branch the job names (section branches; main only for site-wide work, labelled `site-wide`).
- Every pull request runs the agent lint (tools/agent_lint.py). A failing lint is never merged.
- Research anything public. Contact no private individual. Spend nothing. Outreach in the family's name goes through the hive
  for the owner's sign-off.

Commits by the household agents end with the house sign-off. — Sion's Tab agent

## Outside links and Wayback snapshots (rule of 27 Oct 2026)

This rule overrides the older "no outbound links" rule in exactly one place: the two lines under each Wayback snapshot.

- Every link to an outside page opens that page's Cedwyn snapshot under `/wayback/` (`/wayback/go/?u=<address>`, built from `web/_cedwyn/archive/go.html`). The old "leaving the archive" notice page is deleted and must never come back.
- A snapshot shows, in this order (owner's order of 29 Oct 2026): our captured copy of that ONE page (Bootstrap 5 styling from `/_cedwyn/vendor/bootstrap-5.3.3.min.css` when the original CSS does not carry), then a link to the live website (a plain working link, no warning page), then a link to the Internet Archive (web.archive.org) copy of the address, then a "Captured <date>" line. An address held in the Vault's archived-websites list shows a link to that copy and the same two lines.
- Every URL given to the project in an FOI/EIR/SAR reply is checked on the Internet Archive and saved there once if missing; the log is /watchtower/data/foi-urls.csv (brief: docs/briefs/2026-10-29-foi-preservation-wayback-changewatch.md). These two lines are the only links out of Cedwyn; they are built at run time in the page script.
- Inside a captured copy every hyperlink is removed (kept as plain text) unless it opens another Cedwyn snapshot.
- Capture only pages that concern this project, one page at a time. Never crawl, mirror or clone a whole site. Keep captures small: no scripts, trackers, embedded media or large images.
- An address with no capture yet still gets the snapshot page, marked "Snapshot not yet captured", with the Internet Archive link and the live link.
- Captures live in `web/wayback/snap/b/NN.json` (16 buckets; key = FNV-1a 32-bit hex of the address, bucket = last two hex digits mod 16; value = base64 gzip JSON {u, t, title, html, ia, src, pdf}). Add captures by appending to the right bucket; never rewrite another bucket's entries.
- Checkout, payment and mailing-list links (buy.stripe.com, checkout.stripe.com, gumroad.com) are not outside reference links: the snapshot page passes them straight through. Never send them to a snapshot.
- Everywhere else on the site, links stay internal.
