---
phase: 03-html-scrapers-data-pipeline-grados-d-e
plan: "01"
subsystem: backend/tests
tags: [tdd, red-phase, html-scraper, fixtures, env-config]
dependency_graph:
  requires:
    - fp-cercador/backend/tests/conftest.py (existing fixtures)
    - fp-cercador/backend/.env.example (existing ADMIN_TOKEN)
  provides:
    - fp-cercador/backend/tests/conftest.py (4 new HTML fixtures)
    - fp-cercador/backend/tests/test_html_scraper.py (RED suite, 19 tests)
    - fp-cercador/backend/.env.example (4 URL_GRADO_* vars)
  affects:
    - Plan 02 (implements scrapers/html_scraper.py to turn RED → GREEN)
    - Plan 03 (pipeline.py reads URL_GRADO_* from .env)
tech_stack:
  added: []
  patterns:
    - TDD RED phase with ImportError gate
    - HTML fixture strings reproducing todofp.es rowspan/img-alt structure
    - Mock-based unit tests (unittest.mock, no real network)
key_files:
  created:
    - fp-cercador/backend/tests/test_html_scraper.py
  modified:
    - fp-cercador/backend/tests/conftest.py
    - fp-cercador/backend/.env.example
decisions:
  - "Fixtures use exact HTML structure verified against todofp.es (rowspan + img alt='Logotipo ...')"
  - "HTML_FAMILY_ALIASES tested with 2 known exceptions: 'Imagen y Sonido' and 'Artes y Artesanias'"
  - "test_pipeline.py absent from worktree (not committed at base commit f059dee); test_pdf_scraper.py used as existing suite verification"
metrics:
  duration: "3 minutes"
  completed: "2026-04-18T07:25:35Z"
  tasks_completed: 3
  files_changed: 3
---

# Phase 03 Plan 01: HTML Scraper TDD RED Phase Summary

**One-liner:** Fixtures HTML minimalistes + suite RED de 19 tests per al html_scraper (HTML-01 a HTML-06) + 4 variables URL_GRADO_* al .env.example.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Ampliar conftest.py amb fixtures HTML | 764b448 | fp-cercador/backend/tests/conftest.py |
| 2 | Crear test_html_scraper.py (RED) | 3c9e411 | fp-cercador/backend/tests/test_html_scraper.py |
| 3 | Actualitzar .env.example amb URLs | bb8f132 | fp-cercador/backend/.env.example |

## What Was Built

### Task 1: conftest.py — 4 fixtures HTML noves

S'han afegit al final de `conftest.py` (sense tocar les 7 fixtures existents):

- `minimal_html_grado_d_one_record` — 1 títol, família canònica "Administración y Gestión"
- `minimal_html_grado_d_two_records_same_family` — 2 títols, rowspan=2, mateixa família
- `minimal_html_alias_imagen_y_sonido` — família "Imagen y Sonido" (requereix alias → "Imagen y Espectáculos")
- `minimal_html_unknown_family` — família "Mantenimiento y Servicios a la Producción" (no canònica → "Desconeguda")

L'estructura HTML reprodueix la verificada a todofp.es: `<th rowspan="N" headers="familia">` amb `<img alt="Logotipo [Família]">` i `<td headers="titulacion famN">` amb `<a id="tit-*">`.

### Task 2: test_html_scraper.py — Suite RED (19 tests)

19 tests cobreixen HTML-01 a HTML-06:

- **HTML-01/03:** Compte de títols i extracció per `id="tit-*"` (4 tests × subtipus + 1 rowspan)
- **HTML-04:** Família directa, alias Imagen y Sonido, contingut de HTML_FAMILY_ALIASES, família desconeguda + warning (4 tests)
- **HTML-05:** nivel=1/2/3/None per Básico/Medio/Superior/E (4 tests)
- **HTML-06:** codigo=None, plan_antiguo=False, observaciones="" (3 tests)
- **Helpers:** _build_fam_map ignora logo global, _extract_titols ignora td sense fam_id (2 tests)
- **Fail fast:** raise_for_status propaga HTTPError (1 test)

Tots els tests mocken `scrapers.html_scraper.requests.get` — cap trucada de xarxa real.

**Fase RED confirmada:** col·lecció falla amb `ModuleNotFoundError: No module named 'scrapers.html_scraper'`.

### Task 3: .env.example — 4 variables URL

```
URL_GRADO_D_BASICO=https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html
URL_GRADO_D_MEDIO=https://www.todofp.es/que-estudiar/grados-d/grado-medio.html
URL_GRADO_D_SUPERIOR=https://www.todofp.es/que-estudiar/grados-d/grado-superior.html
URL_GRADO_E=https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html
```

URLs verificades amb HTTP 200 (2026-04-17). Línia ADMIN_TOKEN intacta.

## Verification Results

```
Suite existent (test_pdf_scraper.py): 27 passed
RED phase (test_html_scraper.py --collect-only): ModuleNotFoundError confirmat
Fixtures conftest.py: 11 (7 existents + 4 noves)
URLs .env.example: 4 variables URL_GRADO_*
```

## Deviations from Plan

### Auto-fixed Issues

Cap desviació — el pla s'ha executat exactament com estava escrit.

**Nota contextual:** `test_pipeline.py` no existeix al worktree (no estava commitejat al commit base `f059dee`). La verificació de la suite existent s'ha fet únicament amb `test_pdf_scraper.py` (27 tests). Això és un artefacte del worktree, no un problema del codi produït.

## Known Stubs

Cap stub introduït en aquest pla. Els tests defineixen contractes, no implementació.

## Threat Flags

Cap superfície de seguretat nova introduïda. `.env.example` conté únament URLs públiques (todofp.es) i el placeholder `canvia-aquest-token-per-un-de-segur` (T-03-01 mitigat).

## TDD Gate Compliance

- RED gate: commit `3c9e411` — `test(03-01): create test_html_scraper.py RED suite` ✓
- GREEN gate: pendent (Plan 02 implementarà `scrapers/html_scraper.py`)
- REFACTOR gate: pendent (si escau, al Plan 02)

## Self-Check: PASSED

- `fp-cercador/backend/tests/conftest.py` — FOUND (11 fixtures)
- `fp-cercador/backend/tests/test_html_scraper.py` — FOUND (19 tests)
- `fp-cercador/backend/.env.example` — FOUND (4 URL_GRADO_* lines)
- Commit 764b448 — FOUND
- Commit 3c9e411 — FOUND
- Commit bb8f132 — FOUND
