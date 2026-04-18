---
phase: "03"
plan: "03"
subsystem: "pipeline"
tags: ["pipeline", "scraping", "html", "pdf", "data-generation", "bug-fix"]
dependency_graph:
  requires: ["03-01", "03-02"]
  provides: ["ofertes.json complert A-E", "pipeline.run() 5 Grados"]
  affects: ["fp-cercador/backend/data/ofertes.json", "fp-cercador/backend/scrapers/pipeline.py"]
tech_stack:
  added: []
  patterns: ["progressive prefix matching per codis LOGSE sense guió baix", "dual alt-text detection per img logos HTML"]
key_files:
  created: []
  modified:
    - "fp-cercador/backend/scrapers/pipeline.py"
    - "fp-cercador/backend/scrapers/pdf_scraper.py"
    - "fp-cercador/backend/scrapers/html_scraper.py"
    - "fp-cercador/backend/data/ofertes.json"
    - "fp-cercador/backend/tests/test_pipeline.py"
    - "fp-cercador/backend/tests/test_pdf_scraper.py"
    - "fp-cercador/backend/tests/conftest.py"
    - ".planning/REQUIREMENTS.md"
decisions:
  - "Pipeline integra PDF (A,B,C) + HTML (D,E) en un sol run() amb IDs seqüencials globals"
  - "PREFIX_MAP expandit a 30 entrades (24 nou pla + 6 pla antic/LOGSE/HTML)"
  - "DATA-04 actualitzat: ~12.000-12.500 registres (era 800-900, estimació inicial incorrecta)"
  - "_build_fam_map accepta alt sense prefix 'Logotipo ' per Grado E"
  - "Matching progressiu alpha[:N] per codis LOGSE sense guió baix (UF0296, VICF0311)"
metrics:
  duration: "~140 min (inclou re-execució pipeline real ~70s)"
  completed: "2026-04-18"
  tasks_completed: 7
  files_modified: 8
---

# Phase 03 Plan 03: Pipeline Integration A-E + Bug Fixes Summary

**One-liner:** Pipeline complet A-E amb 12.374 registres, 0 Desconeguda, 29 famílies; bugs LOGSE i Grado E corregits.

## What Was Built

Integració del pipeline complet per als 5 Grados (A, B, C via PDF; D, E via HTML):

- `pipeline.py` estès amb `HTML_URLS` i bloc de scraping D/E, retornant `by_grado` per tots 5 Grados
- `test_pipeline.py` actualitzat amb mocks per D/E i 2 nous tests (`test_pipeline_id_order_a_b_c_d_e`, `test_pipeline_fail_fast_on_html_error`)
- Bugs corregits i pipeline re-executat contra todofp.es → `ofertes.json` regenerat
- `REQUIREMENTS.md §DATA-04` actualitzat: ~12.000–12.500 (era 800–900)
- Suite de tests actualitzada: 55/55 passen

## Result Metrics

| Grado | Registres |
|-------|-----------|
| A     | 8.537     |
| B     | 2.786     |
| C     | 820       |
| D     | 195       |
| E     | 36        |
| **Total** | **12.374** |

- Famílies úniques: 29
- Registres Desconeguda: 0
- IDs seqüencials 1–12.374: verificats

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Prefix matching simplificat al worktree no reconeixia codis LOGSE sense guió baix**

- **Found during:** Task 3b (re-execució pipeline)
- **Issue:** La versió de `_extract_records` al worktree usava `split('_')[0] if '_' in clean_code else ''`, produint prefix='' per codis com `UF0296`, `VICF0311`, `MF2268_2`. Resultava en 5.145 registres "Desconeguda".
- **Fix:** Matching progressiu `alpha[:N]` des de longitud màxima fins a 2, igual que la versió del main. Afegit `ART`, `SAN`, `UF`, `MF` a PREFIX_MAP (presents al main però absents al worktree).
- **Files modified:** `fp-cercador/backend/scrapers/pdf_scraper.py`
- **Commit:** 3250b0b

**2. [Rule 1 - Bug] `_build_fam_map` descartava imatges sense prefix "Logotipo " (Grado E)**

- **Found during:** Task 3a (análisi del checkpoint anterior)
- **Issue:** `fam011118` (Inteligencia Artificial y Data) tenia `alt="Inteligencia Artificial y Data"` sense el prefix "Logotipo " habitual dels Grados D. La condició `if not alt.startswith('Logotipo '): continue` el descartava.
- **Fix:** Acceptar els dos formats; si `alt.startswith('Logotipo ')` extreure sufix, sinó usar `alt` directament.
- **Files modified:** `fp-cercador/backend/scrapers/html_scraper.py`
- **Commit:** c7d77f5

**3. [Rule 1 - Bug] fam018/fam011112 (Sanidad) i fam02 (Artesanía) no reconeguts per PREFIX_MAP incomplet**

- **Found during:** Task 3b (warnings html_scraper al re-executar)
- **Issue:** La pàgina D_Medio/D_Superior tenia `fam018`→"Sanidad" i `fam02`→"Artes y Artesanias"→"Artesanía". Cap d'aquests valors existia a PREFIX_MAP del worktree.
- **Fix:** `'SAN': 'Sanidad'` i `'ART': 'Artesanía'` ja inclosos a PREFIX_MAP (cobert per fix 1 anterior).
- **Files modified:** `fp-cercador/backend/scrapers/pdf_scraper.py`
- **Commit:** 3250b0b

**4. [Rule 1 - Bug] Tests fallaven per PREFIX_MAP ampliat i fixture obsoleta**

- **Found during:** Task 5 (suite de tests)
- **Issue:** `test_prefix_map_completeness` esperava 24 entrades (ara 30); `minimal_html_unknown_family` usava "Mantenimiento y Servicios a la Producción" que ara és reconeguda.
- **Fix:** Actualitzat el test a 30; fixture canviada a "Família Inexistent XYZ".
- **Files modified:** `fp-cercador/backend/tests/test_pdf_scraper.py`, `fp-cercador/backend/tests/conftest.py`
- **Commit:** f37e02a

## Commits

| Hash    | Tipus   | Descripció |
|---------|---------|------------|
| 2b7cf13 | feat    | pipeline.py: HTML_URLS + bloc D/E |
| 6c7b086 | feat    | test_pipeline.py: mocks D/E + 2 nous tests |
| c7d77f5 | fix     | Bug 1+2: MSP/IAD a PREFIX_MAP, _build_fam_map relaxat |
| 3250b0b | fix     | Bug LOGSE: prefix matching progressiu + ART/SAN/UF/MF |
| 8104aaf | docs    | REQUIREMENTS.md DATA-04: 800-900 → 12.000-12.500 |
| daf19e9 | chore   | ofertes.json regenerat (12.374 registres, 0 Desconeguda) |
| f37e02a | fix     | Tests: PREFIX_MAP 24→30, fixture unknown_family corregida |

## Known Stubs

Cap — tots els registres tenen família coneguda i el pipeline genera dades reals.

## Self-Check: PASSED

- SUMMARY.md: FOUND
- ofertes.json: FOUND
- pipeline.py: FOUND
- Commit f37e02a: FOUND
- Commit 3250b0b: FOUND
- Commit c7d77f5: FOUND
