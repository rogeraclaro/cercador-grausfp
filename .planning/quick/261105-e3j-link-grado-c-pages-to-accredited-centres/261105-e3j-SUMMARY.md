---
quick_id: 261105-e3j
status: complete
date: 2026-11-05
commit: 4871115
deployed: false
---

# Summary: Link Grado C pages to the accredited-centres search

- `backend/grau_page.py`: `CENTRES_URL` constant; `_centres_html` adds a second button
  "Centros acreditados" for Grado C with centres → `https://centres.grausfp.es/es/search?cert=<ref>`
  (`data-lang-href` + `data-lang-suffix`, `target="_blank" rel="noopener"`, attributes via `_e()`).
- `frontend/i18n.js`: `[data-lang-href]` links append `data-lang-suffix` (default `/`; topbar unchanged).
- i18n.js cache-bust `20261104b` → `20261105a` in grau_page.py and 15 HTML pages (single version verified).
- Tests: 3 new + topbar version literal updated. Full backend suite 417 passed; `node --check` OK.

## Known limitation
The link condition uses GrausFP's own centre total. The centres site imports GrausFP's files daily
at 05:00, so for up to about a day after a GrausFP refresh adds a certificate, its link can land on a
centres search with zero results (a no-results page with suggestions, never an error). Accepted; no
runtime call to the centres site.

## Pending
Deploy (owner approval; not Sunday 11:10–11:45).
