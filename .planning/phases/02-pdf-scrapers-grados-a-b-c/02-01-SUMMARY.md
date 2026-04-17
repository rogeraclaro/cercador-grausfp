---
phase: 02-pdf-scrapers-grados-a-b-c
plan: "01"
subsystem: backend/scrapers
tags: [pdf-parsing, tdd, pdfplumber, python, scrapers]
dependency_graph:
  requires: []
  provides:
    - scrapers.pdf_scraper.parse_grado_a
    - scrapers.pdf_scraper.parse_grado_b
    - scrapers.pdf_scraper.parse_grado_c
    - scrapers.pdf_scraper.PREFIX_MAP
  affects:
    - fp-cercador/backend/scrapers/pipeline.py  # consumidor futur (Pla 02)
tech_stack:
  added: [pytest]
  patterns: [TDD RED-GREEN-REFACTOR, pdfplumber.extract_table, diccionari keyed per deduplicació]
key_files:
  created:
    - fp-cercador/backend/scrapers/pdf_scraper.py
    - fp-cercador/backend/tests/__init__.py
    - fp-cercador/backend/tests/conftest.py
    - fp-cercador/backend/tests/test_pdf_scraper.py
  modified: []
decisions:
  - "pytest instal·lat com a dep de dev (no al requirements.txt — nom separat de runtime)"
  - "REFACTOR omès: codi sense duplicació significativa post-GREEN"
  - "T-02-01 implementat: try/except per pàgina a _extract_records (no en el pla original, afegit per threat model)"
metrics:
  duration_minutes: 12
  completed: "2026-04-17T10:15:00Z"
  tasks_completed: 3
  files_created: 4
  files_modified: 0
---

# Phase 02 Plan 01: pdf_scraper.py — Parsing de PDFs dels Grados A, B, C (Summary)

**One-liner:** Implementació TDD de pdf_scraper.py amb pdfplumber — PREFIX_MAP de 24 famílies, detecció de plan_antiguo, derivació de nivel per sufix, deduplicació per diccionari i 27 tests unitaris passats sense xarxa.

## What Was Built

Mòdul `fp-cercador/backend/scrapers/pdf_scraper.py` que exposa tres funcions públiques (`parse_grado_a`, `parse_grado_b`, `parse_grado_c`) i la lògica privada compartida per extreure registres de PDFs pdfplumber. Cobert per 27 tests unitaris que usen fixtures i mocks (sense xarxa, sense PDFs reals).

## TDD Cycle

| Fase | Commit | Resultat |
|------|--------|---------|
| RED | `85bda5e` | 3 fitxers de test creats; 1 error de col·lecció (ModuleNotFoundError — pdf_scraper.py inexistent) |
| GREEN | `9f2f1e4` | pdf_scraper.py implementat; 27/27 tests passen |
| REFACTOR | (omès) | Codi sense duplicació; tests seguirien passant sense canvis |

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| Wave 0 + RED | Infraestructura de tests + tests fallits | `85bda5e` | tests/__init__.py, tests/conftest.py, tests/test_pdf_scraper.py |
| GREEN | Implementació pdf_scraper.py | `9f2f1e4` | scrapers/pdf_scraper.py |

## Tests Passats (27/27)

- `test_prefix_map_completeness` — 24 entrades exactes
- `test_prefix_map_afd` — AFD=Actividades Físicas y Deportivas
- `test_prefix_map_iex_not_imagen` — IEX=Industrias Extractivas (no Imagen)
- `test_prefix_map_ims_is_imagen` — IMS=Imagen y Espectáculos
- `test_prefix_map_vic` — VIC=Vidrio y Cerámica
- `test_plan_antiguo_uf_code` — UF0297 (Plan antiguo) → is_old=True
- `test_plan_antiguo_new_code` — AFD_A_3003_01 → is_old=False
- `test_plan_antiguo_mf_code` — MF2268_2 (Plan antiguo) → is_old=True
- `test_nivel_grado_a_new` — AFD_A_3003_01 → None
- `test_nivel_grado_a_old` — UF0297 → None
- `test_nivel_grado_b_new` — AFD_B_3003 → None
- `test_nivel_grado_b_old_2` — MF2268_2 → 2
- `test_nivel_grado_b_old_1` — MF2268_1 → 1
- `test_nivel_grado_b_old_3` — MF2268_3 → 3
- `test_nivel_grado_b_old_no_suffix` — MF2268 → None
- `test_nivel_grado_c_3b` — AFD_C_001_3B → 1
- `test_nivel_grado_c_4b` — AFD_C_001_4B → 2
- `test_nivel_grado_c_5b` — AFD_C_001_5B → 3
- `test_nivel_grado_c_old` — AFDA0511 → None
- `test_familia_known_prefix` — AFD → Actividades Físicas y Deportivas, cap warning
- `test_familia_unknown_prefix_warning` — XXX → Desconeguda + logging.warning
- `test_record_schema_grado_c` — exactament {codigo, denominacion, familia, nivel, plan_antiguo, observaciones}; sense 'id' ni 'grado'
- `test_page_skip_index_4_no_records` — pàgina índex 4 → cap registre
- `test_page_skip_index_5_has_records` — pàgina índex 5 → registre extret
- `test_duplicate_deduplication` — codi duplicat a 2 pàgines → 1 registre
- `test_continuation_rows_ignored` — fila buida → cap registre
- `test_public_api_exports` — parse_grado_a/b/c importables, retornen list[dict]

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] T-02-01 implementat: try/except per pàgina a _extract_records**
- **Found during:** GREEN — revisió del threat model
- **Issue:** El threat model (T-02-01) requereix encapsular `page.extract_table()` en try/except per pàgina per continuar si una pàgina és malformada. No estava al pla explícitament però sí al threat model com a disposició `mitigate`.
- **Fix:** Afegit try/except al bucle de pàgines de `_extract_records`; pàgines malformades emeten `logger.warning` i continuen.
- **Files modified:** scrapers/pdf_scraper.py
- **Commit:** `9f2f1e4`

### REFACTOR omès

El codi implementat al GREEN no presenta duplicació significativa. Les tres funcions `parse_grado_[abc]` deleguen a `_extract_records` amb la `nivel_fn` corresponent. Cap refactorització necessària.

## Known Stubs

Cap. Totes les funcions estan completament implementades. L'únic que manca és el caller real (pipeline.py — Pla 02) que passi el path d'un PDF real.

## Threat Flags

Cap nova superfície de seguretat introduïda més enllà del que ja estava al threat model original.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test commit) | `85bda5e` | PASS |
| GREEN (feat commit) | `9f2f1e4` | PASS |
| REFACTOR (optional) | — | OMÈS (justificat) |

## Self-Check: PASSED

- [x] `fp-cercador/backend/scrapers/pdf_scraper.py` existeix
- [x] `fp-cercador/backend/tests/__init__.py` existeix
- [x] `fp-cercador/backend/tests/conftest.py` existeix
- [x] `fp-cercador/backend/tests/test_pdf_scraper.py` existeix
- [x] Commit RED `85bda5e` existent al log
- [x] Commit GREEN `9f2f1e4` existent al log
- [x] 27/27 tests passen
- [x] `from scrapers.pdf_scraper import parse_grado_a, parse_grado_b, parse_grado_c, PREFIX_MAP` → OK 24 prefixos
