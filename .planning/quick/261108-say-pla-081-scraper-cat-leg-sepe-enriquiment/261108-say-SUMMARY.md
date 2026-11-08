---
phase: 261108-say-pla-081-scraper-cat-leg-sepe-enriquiment
plan: 01
subsystem: fpo
tags: [sepe, scraper, fpo, i18n, flask, alpine]
requires: [PLA-059-061]
provides:
  - sepe_scraper (build_sepe_data / write_sepe_data) and local data/sepe_especs.json (7544 rows)
  - pipeline.refresh_sepe_especs (7-day gate, non-fatal)
  - /api/fpo vinculacio, vigenciaFi, competenciaTransversal, modalitatOficial, sepe block
  - FPO UI badges, explanation, chip, vigencia notice, "Tipus de formacio" filter (CA/ES)
affects: [fp-cercador/backend, fp-cercador/frontend/index.html, fp-cercador/frontend/i18n.js]
key-files:
  created:
    - fp-cercador/backend/scrapers/sepe_scraper.py
    - fp-cercador/backend/tests/test_sepe_scraper.py
    - fp-cercador/backend/tests/test_sepe_refresh.py
    - fp-cercador/backend/tests/fixtures/sepe_paginacion_3.latin1.json
  modified:
    - fp-cercador/backend/scrapers/pipeline.py
    - fp-cercador/backend/app.py
    - fp-cercador/backend/tests/test_fpo_api.py
    - fp-cercador/frontend/index.html
    - fp-cercador/frontend/i18n.js
    - fp-cercador/frontend/*.html (i18n.js?v= only, 14 pages)
    - fp-cercador/backend/grau_page.py
    - fp-cercador/backend/tests/test_grau_page.py
decisions:
  - "vinculacio is null (not propiaSoc) for non-CP entries when sepe_especs.json is missing"
  - "SEPE familia/area cell '-' normalised to None, like competenciaTransversal"
  - "POST timeout 90 s (GET stays 30 s) because the SEPE server was slow on 2026-11-08"
status: complete
commits: 3
plan_head_before: 5e8e7dfb8601d879526e71aa393095d5a94ab4fa
plan_head_after: 7d46fee0c023167b4ff18e512fb7be3deccc4652
actuals:
  tokens: 30000
  tasks: 3
  commits: 3
---

# Phase 261108-say Plan 01: Pla 081 SEPE catalogue scraper and FPO enrichment Summary

SEPE Catalogo de Especialidades Formativas scraped into `sepe_especs.json` (7544 unique rows), refreshed weekly and non-fatally by the pipeline, and used to classify each SOC FPO specialty as Grado C / formacio en el treball / propia del SOC with badges, explanation and a new filter in CA and ES.

## Commits

| Task | Commit | Message |
| ---- | ------ | ------- |
| 1 | f0a99b0 | feat(sepe): scrape the SEPE training specialties catalogue |
| 2 | a54b18c | feat(fpo): classify SOC specialties against the SEPE catalogue |
| 3 | 7d46fee | feat(fpo): show training type badges and filter |

## Results

- Offline: `tests/test_sepe_scraper.py` 17 passed; routine suite (`--ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`) 427 passed.
- Live scrape (2026-11-08): 7544 rows, unique codi, 165 s total (see deviation 1). `data/sepe_especs.json` is gitignored, present locally only.
- Real-data API: SOC entries split grauC 132 / sepe 82 / propiaSoc 6, no None. `ADGD0073` -> sepe {idSepe 59414, versio 1, vigencia 2024-02-26..2031-12-31}; `ADGD0108` -> sepe null. No `programaSepeUrl` anywhere, no `/api/sepe/*` route.
- Browser check (system Chrome via Playwright, static frontend on :8765 + backend on :5001), CA and ES:
  - ADGD0073 shows "Formacio en el treball" badge with title tooltip; detail shows the explanatory paragraph.
  - ADGD0108 shows "Cert. prof."; CTRD0012 shows "Propia del SOC".
  - Filter "Tipus de formacio": all 749, grauC 137 (includes external CP courses), sepe 82, propiaSoc 6; combined with certprof toggle it ANDs (sepe + certprof = 0, expected as the sets are disjoint); clear button resets it; ES copy verified.
  - Only console errors: CORS on `/api/auth/me` caused by my cross-origin dev setup (frontend on :8765, API on :5001), unrelated to this change.
  - Not exercised in the browser: competencia transversal chip and vigencia notice (no specialty checked) — covered by API data only.
- Both local servers were stopped afterwards.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] POST timeout raised from 30 s to 90 s**
- **Found during:** Task 1 live run
- **Issue:** The SEPE server was slow on 2026-11-08 (2000-row page took ~40 s, 50 rows ~6 s, independent of User-Agent), so the 30 s read timeout failed the first live run. The spike had measured ~4 s total earlier.
- **Fix:** Added `POST_TIMEOUT = 90` for the paginated POST; the bootstrap GET keeps `TIMEOUT = 30`. TLS verification untouched. `MAX_PAGES` still bounds the loop and the step is weekly and non-fatal.
- **Files modified:** fp-cercador/backend/scrapers/sepe_scraper.py
- **Commit:** f0a99b0

**2. [Plan wording] Competencia transversal rendered as a badge inside a paragraph**
- The detail block uses `x-show` paragraphs; the chip is an `.fpo-badge` span (margin-left reset inline) inside one. Same behaviour as specified.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. SEPE values are rendered only with `x-text`; tags stripped and entities unescaped in the scraper; `write_sepe_data` validates (>= 5000 rows, unique codi) before the atomic replace.

## Notes for the owner

- Not deployed. The VPS needs a first manual SEPE refresh (`refresh_sepe_especs`) to create `sepe_especs.json`; until then non-CP SOC entries have `vinculacio: null` and no SEPE badge shows. Do not restart during the Sunday 11:10-11:45 refresh.
- A first full scrape can take minutes when the SEPE server is slow (165 s observed).
- Working tree still contains unrelated untracked/modified files that were not touched (.DS_Store, ESTAT.md, plans 081/082, grausfp-launch/, pt.log, .playwright-mcp logs).

## Self-Check: PASSED

- Files present: sepe_scraper.py, test_sepe_scraper.py, test_sepe_refresh.py, sepe_paginacion_3.latin1.json.
- Commits f0a99b0, a54b18c, 7d46fee are ancestors of HEAD; `git rev-list --count` from plan base = 3.
