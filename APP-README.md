# Cedwyn

**cedwyn.bucklerfamily.estate** — one central SQLite catalogue of Great House Farm evidence, browsed through 44 source themes and grouped into 36 visitor-facing page areas.

The 44 source themes remain separately buildable and retain their legacy routes. The public homepage and shared previous/next navigation use the 36 visitor-facing page areas. The 36-area index is a visitor-facing grouping layer, not a count of source themes. It merges the Legal Wiki with its nomenclature/dictionary reference tools, and groups the NFT gallery, cyber games and 3D world under one Arcade shell. The area-to-parcel links currently use editorial serendipity slots only: no website area is assigned a historic tithe plot number until the c.1841 schedule is checked row-by-row.

The central SQLite database remains the source of truth. The browser reads it through chunked, read-only SQLite; the build also emits smaller, theme-local SQLite slices containing relevant artifacts, assessments, observations and references. Multi-theme areas such as Wiki and Arcade receive an aggregate slice. The Wiki slice deliberately includes the full Level 1 register, including pending records and their explicit unassessed status; the other area slices remain relevance-filtered. These are static catalogue databases, not separate authoring stores or a server-side write API.

The old repo (`unclehowell/datro`) and the old subdomains are untouched: this repo only reads from them.

## What is in this repo

| Branch | What it holds |
|---|---|
| `main` | The build: `themes.json`, `tools/`, `web/`, workflows, build reports |
| `site` | The built site Cloudflare Pages serves (themes, `/_blob/` store, `/db/` chunks) |
| every other branch | A mirror of the datro branch of the same name, with its history (see "History rewrite") |

## How it works

1. **Mirror** (`.github/workflows/mirror.yml`): `git clone --mirror` of datro, then every branch and tag is pushed here.
2. **Assemble** (`tools/assemble.py`): each theme's site is copied out of its mirrored branch (the same folder its old Pages project served).
   Sites with no static branch output (Workers, the apex domain's own repo) are copied by a read-only crawl of the live site.
3. **Shared assets** (`tools/fetch_missing.py`): scripts, styles and images that one site loads from another (for example the shared header scripts on the apex domain) are copied read-only from the live site into the theme they belong to.
4. **Rewrite** (`tools/rewrite.py`):
   - cross-subdomain links `x.bucklerfamily.estate/...` become `/<theme>/...`;
   - root paths gain the theme prefix;
   - **no outbound links**: every external link goes to the archive interface at `/wayback/go/?u=…`, which opens our captured copy, or records the address as text when it has not been archived yet;
   - evidence files that appear in more than one theme are stored **once** in a content-addressed store `/_blob/<sha>.<ext>`.
5. **Runtime** (`web/_cedwyn/runtime.js`): loaded first in every page (`ghf-boot.js` stays last in `<head>`).
   It applies the same mapping to paths that page scripts build at run time, and guards links, `window.open` and forms against leaving the archive.
6. **Catalogue database** (`tools/build_db.py`): one SQLite file holding every artifact:
   - `artifacts` — one row per unique file, by sha256;
   - `locations` — every place an artifact appears, in every theme;
   - `blobs` — the evidence bytes themselves;
   - `fts` — an FTS5 full-text index;
   - `nodes` and `edges` — a graph: page→embeds/links→artifact, artifact→mentions→year, artifact→cites→source host, artifact→in_theme→theme. This is a ready base for graph-RAG.
   - `captures` — original URL → archived copy.
   - `layers`, `layer_items`, `layer_refs`, `layer_deps` — readings over the same evidence (first: 1000 Cuts): each item points at catalogued pages (artifact ids), never copies; dependencies are also graph edges (`depends_on`).
7. **The 25 MB limit**: the database is VACUUMed (page size 4096) and split into 512 KB chunk files (`/db/cedwyn.sqlite3.0000`, `.0001`, …), far under GitHub's and Pages' per-file limits.
   The browser fetches only the chunk files a query touches (sql.js-httpvfs, chunked mode). Each request is one whole chunk file, because Cloudflare Pages answers HTTP Range requests with the whole file. No server, no D1, no cron.
8. **GraphQL** (`/graphql/`): one schema (`web/_cedwyn/cat.js`) resolved in the browser against the database.
   It covers themes, artifacts, locations, full-text search, graph edges, nodes and captures. The catalogue page `/catalogue/` uses the same layer.
9. **Outbound-link test** (`tools/check_links.py`): the build fails if any external `<a>`/`<area>` href or form action survives,
   or if the excluded YouTube channel appears anywhere.

## Evidence hierarchy (Level 1 and Level 2)

- **Level 1 — Artifacts:** `evidence_catalogue` identifies the source entry and links it to a built artifact. `artifact_assessments` keeps a neutral description, transcript/transcription status, interpretation, source-verification status and limitations as separate fields. `data/artifact-assessments.json` seeds only reviewed working entries; every discovered EV page receives an explicit `not_assessed` default until a reviewer enters a value. A blank transcript is not an assertion that the source lacks text.
- **Level 2 — Observations:** `data/observations.json` records patterns derived from one or more Level 1 artifacts. `observations` and `observation_refs` store each observation, its limits, test questions and links to supporting artifacts. The first working observations cover recurrence of the twelve-year period, repeated permissive-occupancy framing, and name variants/dispersed records. Observations are not primary artifacts and do not by themselves establish intent, misconduct, title or legal effect.
- **Visitor views:** `/wiki/evidence/` mounts the database-backed Level 1/Level 2 browser above the original register; `/wiki/observations/` lists the observation pages. The source page and interpretation are kept distinct in both the UI and machine-readable records.
- **Agent access:** `web/_cedwyn/agent-tools.js` exposes read-only search/read tools for artifacts and observations. The central catalogue / GraphQL API stays available; each theme's compact database is advertised at `/<theme>/_db/config.json` and is generated from the central DB.
- **Public page areas:** `data/site-areas.json` maps all 44 source themes into 36 public-facing areas. `/arcade/` gives gallery, games and 3D world three toggles; `/wiki/reference/` gives names and dictionary two toggles. Legacy routes are retained for backward compatibility. `/parcels/site-areas/` makes the 36-slot serendipity index visible but explicitly marks actual tithe plot matching as pending verification.


### Why images are binary BLOBs, not base64 text

Base64 makes every image a third bigger, which works against "maximum efficient". So the database stores the raw bytes.
The catalogue and the GraphQL `dataUri` field turn them into base64 `data:` URIs when they are read, so you still get base64 images, without the extra size on disk or in the download.

Large media (video, very large PDFs) are not inlined. They stay referenced to the wayback-* and Internet Archive copies.

### History rewrite (cedwyn only)

The mirrored branches here have rewritten history; datro's history is unchanged. Two things were rewritten:
- `.github/workflows/*` was dropped from every commit. This stops datro's deploy workflows from running from this repo, and it is needed because the Actions token may not push workflow files.
- Secret-looking strings (ASP.NET machineKey values, API tokens, private keys) were replaced with `REMOVED-IN-CEDWYN`.

Because of the rewrite, commit IDs differ from datro's. Tags were mirrored too. `reports/mirror.json` lists what was pushed and what the scans found.

## Build numbers (first build, 24 Oct 2026)

- Database: 499.7 MB, in 954 chunk files of 512 KB each.
  - 8,616 unique artifacts, seen at 12,843 locations across the themes.
  - 2,182 evidence files stored as BLOBs (463 MB).
  - 5,963 full-text rows.
  - Graph: 933 nodes and 65,888 edges.
  - 183 archived-page captures.
- Site: about 13,600 files, about 2 GB.
  - 2,338 duplicate evidence files across themes were folded into the content-addressed store (`/_blob/`).
  - 2,143 copies stay in place, because page scripts name them directly.
- Outbound-link test: 4,239 pages and 74,926 links checked. Outbound links left: 0. The guard pass rewrote 2 links that the parser had missed.
- Mirror: all 70 datro branches and 2,184 tags.


See `reports/` (written by every build): `db.json` (database size, chunk count, artifacts, edges), `size.json`, `_assemble_report.json`, `_rewrite_report.json`, `_outbound_test.json`.

## Themes

| Theme | Path | Former address | Source |
|---|---|---|---|
| Primary Records | `/records/` | records.bucklerfamily.estate | branch `ghf-primary-records` |
| Docs · The Evidence Catalogue | `/docs/` | docs.bucklerfamily.estate | branch `docs` /public |
| The Wayback Vault | `/wayback/` | wayback.bucklerfamily.estate | branch `wayback` /wayback |
| Nomenclature | `/nomenclature/` | nomenclature.bucklerfamily.estate | branch `nomenclature` /public |
| The Map Room | `/maps/` | maps.bucklerfamily.estate | branch `maps` /public |
| The Land Changing Hands | `/infographic/` | infographic.bucklerfamily.estate | branch `infographic` /public |
| The Legal Wiki | `/wiki/` | greathousefarmwiki.wordpress.com | branch `wiki` /site |
| The E-book Shelf | `/ebooks/` | ebooks.bucklerfamily.estate | branch `ebooks` /public |
| The Story | `/story/` | bpvsbuckler.bucklerfamily.estate | branch `bpvsbuckler` /static/bpvsbuckler/dist |
| The Farm Album | `/fb/` | fb.bucklerfamily.estate | branch `fb` /site |
| The Chessboard | `/chess/` | chess.bucklerfamily.estate | branch `chess` /public |
| The Grammar House (CSSCPSGP) | `/csscpsg/` | csscpsg.bucklerfamily.estate | branch `csscpsg` /public |
| FCG · Security Clearance | `/fcg/` | fcg.bucklerfamily.estate | crawl of live site |
| Old Bill · Who Gained, Who Lost | `/oldbill/` | oldbill.bucklerfamily.estate | branch `oldbill` /public |
| The Counting House | `/accounts/` | accounts.bucklerfamily.estate | branch `accounts` /public |
| Public Authorities | `/authorities/` | authorities.bucklerfamily.estate | branch `ghf-public-authorities` |
| FOI Requests (WhatDoTheyKnow) | `/wdtk/` | whatdotheyknow.bucklerfamily.estate | branch `whatdotheyknow` /public |
| Independent Review | `/review/` | review.bucklerfamily.estate | branch `ghf-independent-review` |
| The Q&A Hall | `/qa/` | qa.bucklerfamily.estate | branch `qa` |
| The Council Chamber | `/meeting/` | 2026-10-22.bucklerfamily.estate | branch `2026-10-22` /static/2026-10-22 |
| The Project Office | `/projects/` | projects.bucklerfamily.estate | branch `projects` /projects/public |
| The Case Office | `/app/` | app.bucklerfamily.estate | crawl of live site |
| Ask the Archive | `/chat/` | chat.bucklerfamily.estate | crawl of live site |
| Watchtower | `/watchtower/` | watchtower.bucklerfamily.estate | branch `watchtower` /public |
| farmbook 2 · Today | `/fb2/` | fb2.bucklerfamily.estate | branch `fb` /site2 |
| The Post Office | `/email/` | email.bucklerfamily.estate | crawl of live site |
| The Post Office · Calendar | `/emails/` | email.bucklerfamily.estate/calendar | branch `emails` /public |
| Home · The Disclosure Dartboard | `/dartboard/` | bucklerfamily.estate | crawl of live site |
| Cedwyn Estate | `/estate/` | bucklerfamily.estate/cedwyn | crawl of live site |
| Cedwyn Estate Directory | `/directory/` | directory.bucklerfamily.estate | branch `directory` /public |
| Great House Farm II · Patagonia Museum | `/patagonia/` | bucklerfamily.estate/patagonia | crawl of live site |
| Virtual Tour · Wales | `/wales/` | bucklerfamily.estate/wales | crawl of live site |
| Terrain · Cedwyn Estate in 3D | `/terrain/` | terrain.bucklerfamily.estate | crawl of live site |
| The Digital Estate | `/cyberspace/` | bucklerfamily.estate/cyberspace | crawl of live site |
| Gift Shop & Marketplace | `/shop/` | shop.bucklerfamily.estate | branch `merch` /public |
| 1000 Cuts | `/thousand-cuts/` | (a layer, not a former subdomain; same page on research.bucklerfamily.estate/timeline/thousand-cuts/) | `web/thousand-cuts/` + `layer.json` → database tables `layers`, `layer_items`, `layer_refs`, `layer_deps` |

## What remains (stage 2)

- Convert each theme's own data files (JSON feeds, galleries) to read straight from the catalogue database, so every theme's text and records come from the one DB as well as its images.
- Add a service worker that serves `/_blob/` from the database, so the static copy of the store can go.
- Rebuild the crawl-based themes (Workers and the apex site) from source, so their script-loaded data comes along too.
- Add people and places to the graph (it currently has years, themes, source hosts and links), then embeddings for graph-RAG.


## Stage 2 (25 Oct 2026): shared header, fully self-contained, parity

### The shared 3-row header with the burger menu
- The header every datro subdomain draws is now **vendored into cedwyn** at `/_cedwyn/ghf/`: bar 1, then the Wales /
  Patagonia / Cyberspace strip with the language switch, then the stop bar with the burger menu. The vendored files are
  `ghf-boot.js`, `basecamp.js` (locations code inlined), `ghf-lang.js`, `ghf-theme.css`, the Barlow fonts, the site
  dictionaries and the brand icon. They were copied read-only from the live apex site. `basecamp.js` reads each theme's
  former address from `<html data-ghf-host / data-ghf-path>` (set by `/_cedwyn/runtime.js`), so every theme keeps its own
  colours and stop number.
- `tools/selfcontain.py --fix` places it last in `<head>` on the landing page and on every page of every theme. It also
  removes older inlined copies of the header. Every menu entry points to `/<theme>/` on cedwyn, never to a subdomain.
- The landing page shows the header as the Cedwyn Estate stop, without the first-visit chooser over the theme list.
- The second bar (the "Estate website tour": `estate-tour.js`, `data-estate-tour-shell`, `data-estate-tour-nav`) is
  **removed everywhere** in cedwyn. Only the 3-row header remains.

### Self-contained: the build fails on any outside reference
`tools/selfcontain.py` runs twice in the build.
1. `--fix` rewrites every remaining URL. It covers HTML attributes (href, src, srcset, poster, data, action, meta
   content, data-*, ...), inline `<script>`/`<style>` (JSON-LD too), and every `.js .mjs .css .json .webmanifest .svg .xml`
   file. Each URL is handled like this:
   - a former subdomain or apex path becomes `/<theme>/...`;
   - a CDN script, style or font (Google Fonts, jsDelivr, cdnjs, unpkg, plus ES-module imports such as the three.js
     add-ons) is downloaded once into `/_ext/<host>/...`;
   - anything else goes to the archive interface `/wayback/go/?u=<address>`.

   Files that a page names but its branch copy lacks are copied read-only from that theme's live address, in several
   rounds. Images, videos, app bundles and scripts are covered, including the images the vault builds from names in its
   JSON. A last full pass then runs over every file.
2. The strict test **fails the build** on any reference to a `*.bucklerfamily.estate` subdomain or to any external host.
   - Visible text, HTML comments and XML namespace names are not counted as references.
   - Exception: two map-tile URL templates (`themes.json` `allowed_tile_templates`). Tiles are fetched per zoom level
     and position, so they cannot be stored as fixed files.
- Live crawl after deploy (`s2/crawl_check.py`, the same rules applied to the served pages and their scripts, styles and
  JSON): **158 pages and 89 scripts, styles and data files across the landing page and all 36 themes: 0 subdomain references, 0 external references, 0 failed pages (25 Oct 02:40 UTC); the build's own test checked 8,314 files with the same result**.
- `_headers` sets `Cache-Control: no-transform` on every response, so the zone's automatic analytics snippet stays out of
  cedwyn pages.
- Runtime fix: links between themes were being re-prefixed (for example `/maps/` on `/fb2/` became `/fb2/maps/`). Parsed
  pages are now left as the build resolved them, and only links added by scripts are mapped.

### Thin themes and sources
- `tools/apex_source.py` fills the apex themes from the apex site's static files (repo `unclehowell/BucklerFamilyFarm`,
  `public/`, read-only): `/wales/`, `/patagonia/`, `/cyberspace/`, and the apex root `/dartboard/` (legal pages, fonts,
  location images, brand, evidence). Apex paths that stage 1 had prefixed twice are collapsed.
- qa serves the folder its live site serves (`static/qa`, via the `overlay` key in `themes.json`).
- records redirects to the research library's Sources and Archives page, as its live address does.
- `research` (the research library) is the 36th theme. It is built from a crawl of the live site.

### Single database
- The catalogue database (`/db/`, SQLite in 512 KB chunks) now also stores every theme's own data files (JSON, CSV, XML)
  as blobs, next to the images and documents (`tools/build_db.py`, kind `data`): 36 themes, 3,676 blobs (539 MB), 100,706 edges, 1,077 nodes, 7,289 full-text rows; 588 MB in 1,123 chunks of 512 KB.
- The themes still read their own copies of those files. A service worker that serves them from the database is the
  next step, so this clause is **partly** met.

### Per-theme parity (live subdomain vs `cedwyn/<theme>/`, 390 px and 1280 px, measured 25 Oct 2026 02:40 UTC)
Each pair was measured in a real browser for title, header height, burger, sideways scroll, font, background, text
volume, images, broken images and failed requests (`s2/parity.js`; screenshots in the working copy).
identical = same header, no sideways scroll, same font, text within 10 %, no failed loads;
close = only minor differences; gaps = listed.

| theme | score | what differs |
|---|---|---|
| docs | identical | — |
| records | identical | — |
| nomenclature | identical | — |
| wayback | identical | — |
| maps | identical | — |
| infographic | identical | — |
| ebooks | identical | — |
| wiki | gaps | background colour differs; font Barlow vs Jackwrite; header added (old site had none); less content (18% of the old page's text); less content (19% of the old page's text). cedwyn /wiki/ opens the vault copy of the old WordPress wiki; the live wiki is WordPress (its own theme, no shared header). The research theme carries the same wiki content with the shared header |
| story | identical | — |
| fb | close | 1 failed loads. login/profile API (/m/api/me) has no server in cedwyn |
| chess | identical | — |
| csscpsg | identical | — |
| fcg | identical | — |
| oldbill | identical | — |
| accounts | identical | — |
| authorities | identical | — |
| wdtk | identical | — |
| review | identical | — |
| qa | identical | — |
| meeting | identical | — |
| projects | identical | — |
| app | identical | — |
| chat | identical | — |
| watchtower | identical | — |
| fb2 | close | 1 failed loads. login/profile API (/m/api/me) has no server in cedwyn |
| email | identical | — |
| emails | identical | — |
| dartboard | gaps | background colour differs; font Barlow vs Georgia; header added (old site had none); less content (23% of the old page's text). measured against the apex home (bucklerfamily.estate); the cedwyn dartboard theme is the dartboard subdomain app (Disclosure Rings), which is what its branch builds. The apex home is cedwyn's landing page |
| estate | identical | — |
| directory | close | 1 failed loads. members API (/api/members) has no server in cedwyn |
| patagonia | identical | — |
| wales | identical | — |
| cyberspace | identical | — |
| terrain | close | 2 failed loads. scene and session APIs (/terrain/api/*) have no server in cedwyn; the 3D scene loads from its static data |
| shop | identical | — |
| research | gaps | 1 broken images |

Summary: 29 identical, 4 close, 3 with gaps; no theme scrolls sideways at 390 or 1280 px (fb and fb2 included); the shared header is on all 36 and the landing page.

### What remains (stage 3)
- Single database: themes still read their own JSON/CSV/XML copies. Those files are already stored as blobs in the
  catalogue database; a service worker (or a build step) that serves every theme's data from `/db/` would close this.
- Interactive features that need a server, which a static cedwyn has no backend for: fb/fb2 sign-in (`/m/api/me`),
  directory members (`/api/members`), terrain scene/session APIs, and chat answers.
- wiki: rebuild `/wiki/` from a crawl of the WordPress wiki (with its theme files vendored) instead of the vault copy.
- docs: the Sphinx build is not run in CI (sphinx missing), so the docs theme is a crawl of the live docs (identical in
  parity).
- The two map-tile templates stay as the only stated outside requests.

## Stage 3 (25 Oct 2026): the themes read from the one database

Every theme now reads its data and evidence from the catalogue database. Before this, each theme read its own file copies.

**How a theme reads from the database**
- `tools/dbmap.py` runs at build time. For every row of the `blobs` table it records where the bytes sit inside the SQLite file: the part in the row's b-tree cell, and the overflow pages that hold the rest. It reads every entry back through that map and checks it against the row's sha256; if any entry fails, the build stops. The map is written to `/db/blobmap.json`, together with every theme path from the `locations` table.
- `cedwyn-sw.js` is a service worker at the site root. It answers each theme request for JSON, CSV, XML, GeoJSON, images, PDFs or audio straight from the database chunk files, using `web/_cedwyn/dbfs.js`. Each answer carries the header `X-Cedwyn-Source: db`. Pages, scripts and styles still load as files.
- Each read first asks for only the bytes it needs (an HTTP Range request). Cloudflare Pages answers that with the whole chunk file, so the worker keeps each chunk in the browser cache and re-checks the sha256 before using any bytes.
- On a first visit, `runtime.js` pauses the page, starts the worker and reloads once (once per tab). Some browsers cannot run a service worker, such as Firefox private windows. There, the same reader runs inside the page: `fetch` and `XMLHttpRequest` data come from the database, and an image that fails to load is filled from the database too.
- The blob rows are written in clusters: every theme's data first, then media, each grouped by theme and path. The few chunks one page needs therefore sit next to each other.

**The database is the one source** (`tools/dbserve.py`, the last step after the self-contained test passes)
- A file the database holds byte for byte is removed from the deploy. Build 7 removed 5,828 files (1.39 GB): 1,295 data files, 1,210 images, 3,239 PDF and document copies, and 84 audio files.
- The deployed site went from 17,128 files (2.50 GB) to 11,304 files (1.10 GB). The database is unchanged: 3,958 blobs (571 MB) in one SQLite file.
- 547 files are also kept as files, because browsers fetch them before or outside a service worker:
  - 398 images named in page markup (the browser's preload scanner asks for these before any script runs);
  - 105 icons and `<link>`/`<meta>` images;
  - 25 images named in CSS;
  - 15 favicons, manifests and feeds;
  - 4 files named by pages that do not load the runtime.
  The worker still serves all of these from the database.
- In total, 6,395 theme paths are served from the database.

**Measured on the live site (build 7, all 36 themes at 390 and 1280 px, fresh browser each time):** 247 data and media requests were answered by the database, and 4 came from files. The 4 were the maps theme's 2 GeoJSON layers at each width, which were not stored as data; build 9 adds them. No theme regressed on header, burger, sideways scroll, broken images, failed requests or text length. Pages fetched 234 chunk requests (90 MB) for those 247 files, so build 9 halves the chunk size to 256 KB.

### Why images are binary BLOBs and base64 happens at display time
- Live database: 1,435 images take 87.7 MB as raw bytes. As base64 text they would take 117.0 MB, which is 29.2 MB more and 56 more 512 KB chunk files to download.
- Across all 3,958 blobs, base64 at rest would mean 760.8 MB instead of 570.6 MB.
- Chunk files are served uncompressed, so none of that overhead would be won back in transit.
- The catalogue and GraphQL `dataUri` field still give base64 `data:` URIs when asked, built when they are read.

**Build 9 (commit 972f0d7, live 04:18 UTC):**
- Database chunks are now 256 KB: 2,412 files for a 632 MB database. The maps theme's GeoJSON layers are stored as data.
- Across the 36 themes at both widths, 263 requests were served from the database and 0 from files. Pages read 62 MB of chunks in 295 requests; on build 7 it was 90 MB in 234 requests.
- The deploy is 13,256 files (1.20 GB). The database serves 6,410 paths.
- Self-contained test: 8,993 files, with 0 subdomain references and 0 external ones.
- The header and burger are on all 36 themes at both widths.

**/wiki/ is rebuilt from a crawl of greathousefarmwiki.wordpress.com.** The crawl used only GETs and followed robots.txt, starting from the wiki's own sitemap (976 pages).
- The crawl stopped at its 12-minute limit with 741 files. In a sample of 60 sitemap pages, 49 are present.
- The home page has the same amount of text as the live wiki.
- The theme's visible text grew from 563 to 3,010 characters, with 7 images and none broken.
- 9 WordPress.com scripts still fail to load: combined `_static` files, hovercards, likes, the marketing bar and Gutenberg helpers.
- Next pass: a longer crawl, and copies of the WordPress `/wp-content/` scripts.

## Stage 4 (25 Oct 2026): the whole Legal Wiki, no failed loads

**/wiki/ is a full copy of greathousefarmwiki.wordpress.com** (`tools/wiki.py`, run by the build in place of the wget crawl).
- Every page the wiki's own sitemap lists is fetched with GETs only, robots.txt obeyed, 6 at a time: **976 of 976 pages** in about 45 seconds. Each is saved as `<path>/index.html`. Addresses with encoded characters (for example the → arrows) are saved under their decoded folder name, which is what the host looks up.
- WordPress.com combines scripts and styles on the fly (`/_static/??...`). A static host cannot serve that address, so each combination is saved under a fixed name (`/_static/c-<hash>.css|js`) and the page points at it. Theme files, modules, fonts and uploads on the wiki's own host are saved at their own path. Fonts the wp.com CDN refuses (403) are read from the wiki's own host.
- Left out, because they only work against wordpress.com: stats, Gravatar hovercards, likes, the marketing bar, ad consent and the cookie banner, the subscribe bar, emoji images (the browser draws the same emoji), feed links and the hidden post-embed frames. Images the wiki loads from the datro repo's wayback folder point at the wayback theme.
- Live check (build 11, 06:05 UTC): all 976 sitemap addresses answer 200 on cedwyn. In a sample of 60 pages compared with the live wiki, all 60 have the same visible text length within 10 % (median ratio 1.00). On build 9 it was 741 files and 43 of the same 60 pages.

**Fixes found on the way**
- `selfcontain.py`: a protocol-relative attribute value (`src="//host/x.js"`) slipped past both the rewrite and the strict test. Both now catch it.
- Pages copied from a live site after the rewrite step (`fetch_pages`, such as `/story/story/`) now get their root paths mapped to the theme, as built pages do. This removed 5 missing files (`/assets/…`, `/agent-index.json`, `/agent-tools.js`, `/api/timeline.json`).
- research: the Wales at Six video thumbnail is copied into the archive. Its video was checked: it is from the Wales Broadcast Archive channel, not the excluded one. Only thumbnails listed in `themes.json` `ytimg_checked` are copied.

**Measured after build 11**
- Strict self-contained test: 9,320 files, 0 subdomain references, 0 external ones.
- Live crawl: 178 pages and 103 scripts/styles, 0 subdomain or outside links, 0 missing files. Build 9 had 25 missing.
- /wiki/ in a real browser: 0 failed requests at 390 and 1280 px (build 9: 9; build 10: 16), 0 broken images, visible text 2,963/2,986 characters against the live wiki's 2,960/2,983.
- Header and burger on 72 of 72 measurements. No theme scrolls sideways. 265 data and media requests were served from the database. The 2 served as files are the research thumbnail, a vendored copy under `/_ext/`.

**Parity now:** 30 identical, 5 close, 1 gap.
- research: gaps → identical (the broken thumbnail was its only difference).
- wiki: gaps → close. It has the same content and no failed loads. What still differs comes from the shared 3-row header, which the wiki never had: the header's theme sets one font (Barlow) and the page background. The live wiki also counts 9 more images (emoji, tracking pixels, the wordpress.com logo).
- dartboard stays in gaps. It is measured against the apex home, while the cedwyn dartboard theme is the dartboard app that its branch builds.
- Close, unchanged: fb, fb2, directory and terrain. Each calls a server API that a static site has none of.

## Editorial rule: ingredients, not conclusions

Since 25 Oct 2026 every page follows [EDITORIAL.md](EDITORIAL.md): the site presents cited ingredients (date, event, what changed, evidence link inside Cedwyn, label, open questions), never a finished conclusion. Conclusion sentences in mirrored theme text are reworded at build time from `ingredients.json` (`tools/ingredients.py`, run from `tools/site.py`); the datro sources are untouched.

## Two sections: Wales and Argentina (25 Oct 2026)

One database, two framings (owner's order, 25 Oct 2026). `tools/sections.py` (called at the end of `tools/site.py`, copy in `sections.json`):

| Address | What it is |
|---|---|
| `/` | Landing: two tiles, Wales (the Llandough augmented-reality tour, coming soon) and Argentina (Great House II, Puerto Madryn, coming soon) |
| `/wales/` | Wales hub (default language Cymraeg): the tour and its stops, vouchers / e-books / merch, seek-disclose-research-reconstruct |
| `/argentina/` | Argentina hub (default language Español): Great House II, the museum plans, the retelling |
| `/explore/` | The oak board (the former home) |
| `/wales/<theme>/…`, `/argentina/<theme>/…` | The same theme files, served through Pages rewrites (`_redirects`, status 200): nothing is copied |
| `/<theme>/…` | Unchanged |

The themes stay separate compartments (each from its own mirrored branch, assembled as before); the section layer is a thin
shell on top: the rewrites, the two hubs, `web/_cedwyn/section.js` (ribbon, default language, links kept in the section) and a
few lines in the shared runtime and header. The former "Virtual Tour · Wales" theme home was retired on 26 Oct 2026: `/wales/tour/`, `/wales/wales/` and `/argentina/wales/` 301 to `/wales/#stop-1`, and its gift vouchers moved to the hub's `#shop`.
Language (`ghf_lang`) and day/night (`ghf-theme`) are the shared choices, kept in the visitor's browser; a section only sets the
default language until the visitor picks one.
