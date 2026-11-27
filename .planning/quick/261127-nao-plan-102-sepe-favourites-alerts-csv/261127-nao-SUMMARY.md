---
phase: quick-261127-nao
plan: 01
subsystem: sepe
tags: [sepe, favourites, alerts, csv, i18n, flask, alpine]
requires: [plan 096 clean codes, plan 099 entities endpoint, plan 086 FPO alerts]
provides:
  - SEPE-only favourites enriched from the SEPE catalogue
  - Catalonia course alert from SEPE rows
  - Weekly approximate "new authorised entity" alerts (migration 018, service, API, pipeline step)
  - CSV export of the filtered SEPE list
affects: [fp-cercador/backend/app.py, fp-cercador/backend/scrapers/pipeline.py, fp-cercador/frontend/index.html, fp-cercador/frontend/perfil.html]
tech-stack:
  added: []
  patterns: [snapshot-union diffing, shared csvText helper]
key-files:
  created:
    - fp-cercador/backend/sepe_entity_alerts_service.py
    - fp-cercador/backend/migrations/018_sepe_entity_alerts.sql
    - fp-cercador/backend/tests/test_sepe_favorites_alerts.py
    - fp-cercador/backend/tests/test_sepe_entity_alerts.py
  modified:
    - fp-cercador/backend/app.py
    - fp-cercador/backend/scrapers/pipeline.py
    - fp-cercador/backend/grau_page.py
    - fp-cercador/backend/tests/test_grau_page.py
    - fp-cercador/frontend/index.html
    - fp-cercador/frontend/perfil.html
    - fp-cercador/frontend/i18n.js
    - fp-cercador/frontend/search-tools.js
    - fp-cercador/scripts/test_search_tools.js
    - fp-cercador/plans/ESTAT.md
    - "fp-cercador/frontend/*.html (20 pages: i18n.js ?v= bump only)"
key-decisions:
  - "SEPE catalogue only fills favourites/alert titles when the SOC lacks the code"
  - "Entity snapshot is a union keyed by id+type, so each entity is announced once"
  - "Entity step runs only inside pipeline.run(), non-fatal, 1 s pause between specialties"
duration: ~1h
completed: 2026-11-27
status: complete
commits: 4
plan_head_before: b2ae4b304c91a8b2565b49cc3af74a6773d0eabb
plan_head_after: 85e1718fc698dbf2d2f24f9d5b4028eaae4468e7
actuals:
  tokens: 130000
  tasks: 3
  commits: 4
---

# Phase quick-261127-nao Plan 01: Plan 102 — SEPE favourites, alerts and CSV Summary

SEPE specialties now have a heart, a Catalonia course alert, a weekly "newly authorised entity" email alert (migration 018) and a CSV export of the filtered list, reusing the FPO favourites/alerts tables except for one new table pair.

The `actuals.tokens` value above is the plan's own estimate repeated, not a measurement. I did not compute chars/4 over the diff.

## Commits

| Task | Hash | Message |
| ---- | ---- | ------- |
| 1 (tracer) | `dd1b90d` | feat(sepe): favourites and Catalonia course alerts for SEPE specialties (plan 102) |
| 2 | `462bf82` | feat(sepe): weekly alerts for newly authorised training entities (plan 102) |
| 3 | `f349926` | feat(sepe): CSV export of the filtered SEPE list and asset version bumps (plan 102) |
| 3 (docs) | `85e1718` | docs(plans): record plan 102 done locally, not deployed |

No attribution trailers (`git log -4 --format=%B | rg -c 'Co-Authored-By|Claude-Session'` returned nothing). No unexpected file deletions in any commit. Nothing pushed or deployed.

## Test results (all green)

- `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py` (from `backend/`): **935 passed**
- `python3 -m pytest -q tests/test_sepe_scraper.py`: **42 passed**
- `node scripts/test_search_tools.js` (from `fp-cercador/`): **20 passed** (17 existing + 3 new `csvText` tests)
- New tests: `test_sepe_favorites_alerts.py` 6, `test_sepe_entity_alerts.py` 46.
- The two new Python test files were written before the code. They were red only in the trivial sense (the first on missing keys and values, the second on a missing module); I did not capture a red run for the second.
- `test_pipeline.py` and the scraper test files other than `test_sepe_scraper.py` were not run, as instructed (network).

## Decisions taken (revisable), as actually applied

1. Favourites: the SEPE catalogue fills a favourite only when the SOC/external sources lack the code. The entry carries `font: 'sepe'` and a `modalitat` field (`''` for SOC entries). In the profile a SEPE favourite links to `index.html?grado=SEPE&q=<codi>`. Its programme link is `API_BASE + programaUrl`, because `safeHttpUrl` drops relative URLs.
2. SEPE course alert = `fpo_alert` with only `espec_codi` and `inclou_en_linia: true`. It counts toward the existing FPO limit of 10. `describe()` still prints the raw code in the email (unchanged). `GET /api/fpo/alerts` only fills `espec_titol` from SEPE; the key set is unchanged.
3. Entity snapshot key = `"<id>|<tipus>"`. The snapshot only grows (union), so an entity is announced at most once per specialty and type. An entity authorised in person that becomes authorised for teleformation counts as new (tested).
4. First check of a specialty with no snapshot stores it silently. `POST /api/sepe/entity-alerts` seeds the snapshot from `SEPE_ENTITATS_DIR/<codi>.json` (the cache the panel just filled) if it exists and no snapshot exists. It never overwrites an existing snapshot (tested).
5. Each run deletes snapshots of specialties with no row in `sepe_entity_alerts` (paused rows count as rows).
6. Province and teleformation filters reuse the entities panel's own selects. Province options are those already present for the specialty. «Presencial» means any modality. Only «teleformació» is saved as the filter.
7. Email unsubscribe pauses the alert; the profile can resume (PATCH) or delete. Separate limit of 10 entity alerts per user. Duplicate (same code, casefolded province, flag) reactivates and returns 200 `already_exists`.
8. Emails are in Catalan. No opt-out check: **plan 053 (global email opt-out) is not implemented** — there is no `email_prefs` in the backend. When 053 lands, `check_new_entities` needs the same check as `fpo_alerts_service.dispatch`.
9. The entity step runs only inside `pipeline.run()` (right after `refresh_sepe_especs`), not in the FPO-only manual refresh. It does not write the public entities cache. 1 s pause between specialties (`PAUSE_S`).
10. Entity-alert controls are only in the SEPE row's entities panel (single `x-if` root kept), not in the FPO-mode copy.
11. CSV: button only in the SEPE tab toolbar. Title is in the current UI language, hours are rounded as in the table, validity dates are ISO `YYYY-MM-DD`, file `grausfp-sepe-export.csv`. A shared `GFPSearch.csvText` is used by both exports.
    - Byte-identity check for `exportCSV()`: I verified with `rg` that no `csv.header.*` or `csv.yes/no` value in ca or es contains `;`, `,`, `"` or a newline. The old code did not escape headers; the new code escapes them, which changes nothing for these values. Cell escaping and the BOM/CRLF logic are the same as before. I did not diff real exported files.

## Deviations from Plan

None to the scope. Notes:

- The Task 1 tracer gate was satisfied by re-running its automated `<verify>` (all green) before moving on; no human checkpoint was configured.
- The plan's `files_modified` lists `backend/tests/test_grau_page.py` and `grau_page.py` for the `I18N_VERSION` bump. Done as specified; the bump also changes the `auth.js?v=` that `grau_page.py` shares with `I18N_VERSION`, which is consistent with how that file already works.

### Side effects on `fp-cercador/backend/data/` (read this)

The plan's hard rule was "nothing under `backend/data/` created, modified or deleted". I did not touch it directly, but the mandated full pytest run did, through pre-existing behaviour:

1. **`backend/data/last_snapshot.json` was overwritten with test-fixture content** (`{"total": 5, "by_grado": {"A": 5}, "families": ["Química"], "denominacions": ["X"], ...}`). It was modified at 17:05:48, during my full-suite run. A pre-existing test (likely among `test_scheduler` / `test_api` / `test_audit_fixes`, which call `history.append` without redirecting `SNAPSHOT_PATH`) writes to the real path. Its previous content is lost. It is rebuilt by the next real refresh, but the first refresh after this may record bogus changes in `refresh_history.json`. Not caused by plan 102 code; I did not fix it (out of scope).
2. **The local dev DB `backend/data/fp_cercador.db` now has migration 018 applied** (`schema_version` 18, tables `sepe_entity_alerts` and `sepe_entity_snapshots`). `app.py` runs `init_db` on the real DB at import, so any test run does this. Harmless for the dev copy, and the same migration will be applied on the VPS at app start-up.
3. `sepe_programes.json` and `sepe-descarrega.log` were being written by the plan-100 download throughout; I never read, moved or deleted them, and did not touch any python process.

## Not done / not verified

- **Not browser-verified.** The UI (heart, course-alert button, entity-alert block, profile list, CSV button) is covered only by backend tests, `node --check` on the inline scripts of `index.html` and `perfil.html`, and the `rg` structure checks. Alpine bindings, layout and the CSV download in a real browser are untested.
- **Not deployed.** The VPS needs `git push` + pull, migration 018 (applied by the app start-up), and a restart outside a refresh window (check `/api/refresh-status` first).
- No real SEPE or email traffic was generated; both are mocked in every test. The weekly step has never run against the real SEPE.
- If the email send fails, the entities of that run are already in the snapshot, so they are not retried the next week (same trade-off as the FPO alert flow). Deliberate for simplicity; revisit if lost emails matter.
- Email titles use the raw catalogue title (`titol_mostra` or `titol_es`), without the plan-098 admin overrides that the UI and API apply.
- The FPO-mode copy of the entities panel has no alert controls (decision 10).

## Possibly now-unused or slightly off code (listed, nothing deleted)

- No code became unused.
- In `perfil.html`, a SEPE favourite's title link still carries the tooltip `index.itinerari.fpo_veure` ("Veure'ls al cercador FPO"), which is inaccurate now that it opens the SEPE tab. A SEPE-specific tooltip key would fix it.
- `_sepe_espec_as_fpo` looks the row up with a linear scan of `_sepe_llista()['especialitats']` (about 7,500 rows) per favourite or alert. This is fine at the current volumes (at most a few dozen per user).

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model (new endpoints `/api/sepe/entity-alerts*` are T-102-01..04). Mitigations applied: session required with ownership check returning 404; the 64-hex token has its own `sepeent_<id>_` prefix and type, and an FPO token does not work on an entity alert (tested); the email never contains the entity `email` (tested); the code must resolve via `_sepe_lookup`; province length ≤ 60; boolean flag type-checked; SQL parameterised; perfil strings go through `esc()`; `x-text` only.

## Self-Check: PASSED

- Created files exist: `sepe_entity_alerts_service.py`, `migrations/018_sepe_entity_alerts.sql`, `tests/test_sepe_favorites_alerts.py`, `tests/test_sepe_entity_alerts.py` (all committed).
- Commits `dd1b90d`, `462bf82`, `f349926`, `85e1718` are ancestors of HEAD.
- Untracked items left out of every commit: `grausfp-launch/`, `pt.log`, `.DS_Store`, `fp-cercador/plans/106-cerca-per-unitat-de-competencia.md`.

## Browser verification (orchestrator, 2026-11-27)

Local servers (5001 + 8765), throwaway verified user, Playwright; ca and es, 1280 and 375 px:
- SSCE22 (has SOC courses): heart toggles, "Avisa'm de cursos nous" creates the alert, entities panel shows the alert block; entity alert created and listed in the profile.
- SEAD0057 (no courses): button reads "Avisa'm quan hi hagi un curs a Catalunya".
- SEPE-only codes (ADGD221PO, SEAD003PO): favourites list returns `font: sepe` with title, family, hours and modality; profile shows them as "Catàleg SEPE".
- Profile: course alert and entity alert both deleted from the profile (the entity-alert section hides when empty).
- SEPE CSV: BOM, `;`, 10 columns, rows match the filtered list.
- No horizontal scroll at 375 px.
Test user and its rows removed from the local DB afterwards.

Follow-up fix found during verification: `test_scheduler.py` and `test_api.py` overwrote the real `data/last_snapshot.json`; isolated in 92b8fec.
