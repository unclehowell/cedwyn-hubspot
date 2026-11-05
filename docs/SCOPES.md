# Cedwyn scopes: Wales, Argentina, Online (convention v1.0.0, 1 Nov 2026)

Every Cedwyn webapp (each numbered "NN of 59" to an estate parcel) is shown in one of three scopes, chosen by the visitor
in the strip under the header (Wales / Patagonia / Online; Welsh: Cymru / Patagonia / Ar-lein; Spanish: Gales / Patagonia / En línea).
The scope works like the language: one shared helper, read the same way by every page.

| Scope | Address | Shows | Never shows |
|---|---|---|---|
| wales | /wales/... | on-the-ground Wales content: the guided tour in Llandough, visits | the planned replica, online-only blocks |
| argentina | /argentina/... | the planned replica in Patagonia (always "planned") | Wales visit blocks, online-only blocks |
| online | every other address (/research/, /arcade/, ...) | online-only content: games/arcade, research and legal wiki, library/docs, photos, evidence catalogue, movie | Wales visit blocks, planned-replica blocks |

## How a page knows its scope
- `/_cedwyn/scope.js` (loaded synchronously by `/_cedwyn/ghf/ghf-boot.js` on every page, before the first paint) sets
  `<html data-cedwyn-scope="wales|argentina|online">` from the address: `/wales/` prefix (or `data-cedwyn-sec="wales"`) = wales,
  `/argentina/` prefix = argentina, anything else = online. This is the behaviour visitors already had (the strip already
  highlighted the scope from the address).
- `?scope=wales|argentina|online` on any address opens the same page in that scope and remembers the choice.
- The last explicit choice is remembered like the language (`ghf_lang`): localStorage + cookie `ghf_loc`. The stored words
  stay `wales | patagonia | cyberspace` so older code keeps working; `scope.js` maps them to wales / argentina / online.
- JS API: `CedwynScope.get()`, `.stored()`, `.set(s)`, `.href(s[, path])` (the same page in scope s), `.label(s[, lang])`, `.apply()`.

## How content is tagged
1. In markup: `data-scope="wales"`, `"argentina"`, `"online"` or `"all"` (several words allowed, space-separated).
   Untagged = all, so nothing disappears by default.
2. Optional `data-scope-href="/internal/path/"` names where the cross-link goes (internal links only); default is the same page in that scope.
3. Without editing a webapp (mirrored or generated pages): `/_cedwyn/scope-map.json` (repo `web/_cedwyn/scope-map.json`):
   - `areas.<id>.home`: the scope a whole webapp belongs to (`all` for most). A webapp opened in another scope shows one
     line pointing to its own scope in place of its body (e.g. /patagonia/ under Online -> "see Argentina").
   - `areas.<id>.blocks`: `[{"sel": CSS selector, "text": optional substring, "scope": ..., "href": optional}]`.
   - `pages.<path prefix>`: the same, for one sub-page (e.g. `/projects/replica/` home argentina).

## What a hidden block becomes
The block is hidden (CSS rule on `html[data-cedwyn-scope]`, no flash) and one neutral line takes its place, in the visitor's language:
- to Wales: "Visiting in person? See Wales" / "Ymweld yn bersonol? Gweler Cymru" / "¿Visita en persona? Vea Gales"
- to Argentina: "The planned replica: see Argentina" / "Y replica arfaethedig: gweler yr Ariannin" / "La réplica planificada: vea Argentina"
- to Online: "Games, library and records: see Online" / "Gemau, llyfrgell a chofnodion: gweler Ar-lein" / "Juegos, biblioteca y registros: vea En línea"
Adjacent hidden blocks for the same scope share one line. Clicking the link switches the scope (stored) and opens the matching page.
Content generated after load is handled too (a MutationObserver re-applies the rules).

## Rules for authors and agents
- Tag new Wales visit content `wales`, planned-replica content `argentina`, online-only content `online`; shared reference
  material (records, evidence, research) stays untagged (= all).
- Argentina is always "planned"; no money or booking wording in stubs or tags.
- Never hide a block without a stub (`data-scope-nostub` only for decorative duplicates).
- Visual: stubs use the page's own text colour on a translucent band; never a white background; must read at 390 px.
- Changing scope.js: bump its `?v=` in ghf-boot.js and bump ghf-boot's `?v=` (tools/selfcontain.py, tools/sections.py, tools/home.py BOOT) - /_cedwyn/* is edge-cached for 4 h.
