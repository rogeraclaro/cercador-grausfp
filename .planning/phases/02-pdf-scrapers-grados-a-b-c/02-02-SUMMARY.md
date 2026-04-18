---
phase: 02-pdf-scrapers-grados-a-b-c
plan: "02"
subsystem: backend/scrapers
tags: [pipeline, tdd, requests, tempfile, atomic-write, python, scrapers]
dependency_graph:
  requires:
    - scrapers.pdf_scraper.parse_grado_a
    - scrapers.pdf_scraper.parse_grado_b
    - scrapers.pdf_scraper.parse_grado_c
  provides:
    - scrapers.pipeline.run
    - scrapers.pipeline.HEADERS
    - scrapers.pipeline.PDF_URLS
  affects:
    - fp-cercador/backend/data/ofertes.json  # escrit per pipeline.run()
    - fp-cercador/backend/app.py             # consumidor futur (Fase 4)
tech_stack:
  added: []
  patterns: [TDD RED-GREEN-REFACTOR, escriptura-atomica-tempfile-os.replace, fail-fast-D01-D02]
key_files:
  created:
    - fp-cercador/backend/scrapers/pipeline.py
    - fp-cercador/backend/tests/test_pipeline.py
  modified: []
decisions:
  - "REFACTOR omès: implementació directa del pla sense duplicació ni necessitat de refactorització"
  - "app.py roman intacte (D-09): pipeline.py és independent de Flask fins a la Fase 4"
  - "os.path.exists() en el finally garanteix que os.unlink no falla si _download_pdf no ha creat el fitxer"
metrics:
  duration_minutes: 8
  completed: "2026-04-17T11:00:00Z"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
---

# Phase 02 Plan 02: pipeline.py — Orquestrador del Pipeline (Summary)

**One-liner:** pipeline.py amb run(), _download_pdf() i _write_atomic() — descàrrega amb GET+headers, fail fast D-01/D-02, eliminació de PDFs temporals en finally (D-03) i escriptura atòmica amb tempfile+os.replace(); 7 tests unitaris amb mocks passen sense xarxa.

## What Was Built

Mòdul `fp-cercador/backend/scrapers/pipeline.py` que exposa la funció pública `run()`, les constants `HEADERS` i `PDF_URLS`, i les funcions privades `_download_pdf()` i `_write_atomic()`. El pipeline orquestra la descàrrega dels 3 PDFs (Grados A, B, C), crida els parsers del Pla 01, afegeix `grado` i `id` als registres, i escriu `ofertes.json` de forma atòmica. Cobert per 7 tests unitaris amb mocks (sense xarxa real).

## TDD Cycle

| Fase | Resultat |
|------|---------|
| RED | `test_pipeline.py` creat; tots 7 tests fallen (ModuleNotFoundError — pipeline.py inexistent) |
| GREEN | `pipeline.py` implementat; 7/7 tests passen |
| REFACTOR | Omès — implementació directa del pla sense duplicació |

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 (RED+GREEN) | Tests de pipeline + implementació de pipeline.py | tests/test_pipeline.py, scrapers/pipeline.py |

## Tests Passats (7/7)

- `test_pipeline_run_returns_correct_schema` — retorna dict amb total, by_grado, errors, duration_seconds
- `test_pipeline_adds_id_and_grado` — camps 'grado' i 'id' seqüencial (1-based) afegits als registres
- `test_pipeline_fail_fast_on_download_error` — excepció propagada si download falla; os.replace no cridat
- `test_pipeline_deletes_pdf_on_success` — os.unlink cridat 3 cops en cas d'èxit
- `test_pipeline_deletes_pdf_on_error` — os.unlink cridat en el finally fins i tot si parse falla
- `test_pipeline_atomic_write` — os.replace cridat exactament 1 cop; dst = DATA_PATH
- `test_pipeline_headers_used` — headers User-Agent (Mozilla/5.0) i Referer (todofp.es) presents a totes les crides

## Suite Completa

34/34 tests passen (27 de test_pdf_scraper.py + 7 de test_pipeline.py).

## Deviations from Plan

Cap. El pla va ser executat exactament tal com estava especificat.

- app.py no ha estat modificat (D-09 respectat)
- `os.path.exists()` al bloc `finally` usat tal com especifica el pla (si `_download_pdf` falla abans de crear el fitxer, `pdf_path` és `None` i `os.path.exists` evita un `os.unlink(None)`)

## Known Stubs

Cap. `pipeline.run()` és completament funcional i crida els parsers reals del Pla 01. El caller real (app.py amb el thread de refresh) es connectarà a la Fase 4.

## Threat Flags

Cap nova superfície de seguretat més enllà del threat model original (T-02-04 a T-02-07).
- T-02-04: `raise_for_status()` detecta 4xx/5xx — implementat
- T-02-05: timeout=120s explícit a `_download_pdf` — implementat
- T-02-06: escriptura atòmica amb tempfile al mateix directori — implementat
- T-02-07: User-Agent necessari per evitar 403 — acceptat

## Self-Check: PASSED

- [x] `fp-cercador/backend/scrapers/pipeline.py` existeix
- [x] `fp-cercador/backend/tests/test_pipeline.py` existeix
- [x] `grep "def run" scrapers/pipeline.py` → línia 98
- [x] `grep "from scrapers.pdf_scraper import" scrapers/pipeline.py` → línia 24
- [x] `grep "os.replace" scrapers/pipeline.py` → línies 77, 79, 90
- [x] `grep "os.unlink" scrapers/pipeline.py` → línia 141
- [x] `grep "raise_for_status" scrapers/pipeline.py` → línia 69
- [x] `grep "Mozilla/5.0" scrapers/pipeline.py` → línia 34
- [x] `grep "todofp.es/catalogo" scrapers/pipeline.py` → línia 39
- [x] 7/7 tests de test_pipeline.py passen
- [x] 34/34 tests de tota la suite passen
- [x] app.py no modificat (183B, stub Flask pur)
- [x] `from scrapers.pipeline import run` → OK
- [x] Constants HEADERS i PDF_URLS correctes (User-Agent, Referer, claus A/B/C)
