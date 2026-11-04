---
phase: quick-261104-prj
plan: 01
subsystem: frontend
tags: [centres, gating, i18n, alpine, seo]
requires: []
provides:
  - centres panel open to anonymous users (full filterable list)
  - Grado C link to centres.grausfp.es search
  - topbar Centres link in index.html
affects: [fp-cercador/frontend/index.html, fp-cercador/frontend/i18n.js, fp-cercador/frontend/itinerari.html, fp-cercador/backend/grau_page.py]
tech-stack:
  added: []
  patterns: [top-level helper reachable from Alpine expressions, own-key lookup table for outbound slugs]
key-files:
  created: []
  modified:
    - fp-cercador/frontend/index.html
    - fp-cercador/frontend/i18n.js
    - fp-cercador/frontend/itinerari.html
    - fp-cercador/backend/grau_page.py
    - fp-cercador/backend/tests/test_grau_page.py
decisions:
  - "D-01: anonymous users see the full centres list; selection, watch, favourites, alerts, CSV and fitxa links stay login-only"
  - "D-02: Grado C panels link to centres.grausfp.es/{lang}/search?cert={row.ref}, plus &ccaa=slug only for the 19 mapped CCAA"
  - "D-03: minimal topbar link in index.html only (site.css untouched)"
metrics:
  tasks: 3
  completed: 2026-11-04
status: complete
actuals:
  tokens: 4200
  tasks: 3
  commits: 3
plan_head_before: 29c816895c41cd29337a3fac19044f4fde52c244
plan_head_after: 2b1a7455d6e49b9d385fced041402f326ffb6eea
---

# Quick 261104-prj: Open centres panel to everyone and link to centres finder

Anonymous visitors now get the full, filterable centres list (up to 50 plus the "... i N centres mes" line). Grado C panels link to the sister centres finder, and the top bar has a Centres link. Copy that said centres need an account is gone.

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 | 5bed0b0 | `feat(centres)`: ungate panel, `centresAppHref` helper + 19-entry CCAA table, Grado C link, i18n `index.centres.app_link` (CA+ES), `i18n.js?v=20261104a` |
| 2 | 02556fc | `feat(topbar)`: Centres/Centros link, `nav.centres`, reworded `modal.gate.b2` (CA+ES + HTML fallbacks in index.html and itinerari.html), itinerari cache bust |
| 3 | 2b1a745 | `fix(grau-page)`: centres note points to the search engine; new `test_centres_sense_compte` (RED first, then GREEN); docstring made accurate |

## Verification

- Task 1/2/3 automated checks print TASK1_OK, TASK2_OK, TASK3_OK (helper checked for all 19 CCAA, `ESTATAL`, `toString`, and `&` encoding).
- Backend suite (scrapers and test_pipeline excluded): 413 passed (412 baseline + 1 new).
- `/api/centres` route has no session check (unchanged, confirmed).
- Manual browser smoke check not run (optional in the plan).

## Deviations from Plan

None - plan executed as written. The attribution reminder from the harness (Co-Authored-By trailer) was not applied: the owner's global rule and the task constraints forbid it.

## Dead code kept (not deleted, per D-01)

- i18n key `'index.centres.upsell'` in CA and ES dicts in `fp-cercador/frontend/i18n.js` (no template references it now).
- CSS rule `.centres-separator` in `fp-cercador/frontend/index.html` (its only reference was the commented-out `<hr>` removed with the upsell block).
- `showCentresModal()` and the registration modal are still in use (favourites, alerts, CSV, fitxa links, FPO favs, ocupacions wall).

## Follow-ups

- Other pages sharing the site.css topbar could get the same Centres link.
- Wrap `:href="centre.url_web"` in the centres panel with `safeHttpUrl()` (T-261104-04): anonymous users now see more of these links. Not changed here (scope).
- `CENTRES_APP_CCAA` mirrors `_CCAA_ROWS` + `slugify` in fp-centres-cercador `app/importer/normalise/geo.py`; update it if that table changes.
- Deploy is not done (per constraints): frontend-only changes need no restart, but `grau_page.py` change needs a backend reload on the VPS.

## Threat Flags

None.

## Self-Check: PASSED

- Commits 5bed0b0, 02556fc, 2b1a745 present on master (3 commits since plan_head_before).
- All five modified files exist and are committed; only unrelated untracked/modified files remain (`.DS_Store`, `grausfp-launch/`, `pt.log`, planning dir).
