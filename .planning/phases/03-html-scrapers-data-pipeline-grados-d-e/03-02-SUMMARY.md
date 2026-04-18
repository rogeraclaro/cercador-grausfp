---
phase: 03-html-scrapers-data-pipeline-grados-d-e
plan: "02"
subsystem: backend/scrapers
tags: [html-scraper, tdd, green-phase, beautifulsoup4, grado-d, grado-e]
dependency_graph:
  requires:
    - "03-01: test_html_scraper.py RED tests (contracte de comportament)"
    - "02-01: pdf_scraper.py PREFIX_MAP (famílies canòniques)"
  provides:
    - "scrapers.html_scraper: 4 funcions parse_grado_*, HTML_FAMILY_ALIASES, _build_fam_map, _extract_titols"
  affects:
    - "03-03: pipeline.py importarà les 4 funcions públiques d'aquest mòdul"
tech_stack:
  added: []
  patterns:
    - "Mètode B: inferència de família via atribut headers del <td> (03-RESEARCH.md)"
    - "HTML_FAMILY_ALIASES: dict explícit per anomalies HTML (determinista, sense difflib)"
    - "Validació canònica: PREFIX_MAP.values() com a oracle de famílies vàlides"
    - "Pitfall 1 (BS4): isinstance(hv, list) per AttributeValueList"
key_files:
  created:
    - fp-cercador/backend/scrapers/html_scraper.py
  modified: []
decisions:
  - "D-01: raise_for_status() propaga HTTPError — fail fast garantit"
  - "D-07: Mètode B per inferència de família (headers del <td>) — recomanat a 03-RESEARCH.md"
  - "D-08: Família no canònica → 'Desconeguda' + logger.warning — consistent amb pdf_scraper"
  - "D-10: Schema fix: codigo=None, plan_antiguo=False, observaciones=''"
  - "Desviació auto-fixada: _build_fam_map valida contra PREFIX_MAP.values() — el pla original no especificava la validació explícita però és necessària per D-08 (Rule 2)"
  - "REFACTOR omès: sense duplicació significativa — consistent amb Fase 2 plans 01/02"
metrics:
  duration: "~10 min"
  completed: "2026-04-18T07:29:31Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 0
---

# Phase 03 Plan 02: HTML Scraper GREEN Phase Summary

**One-liner:** Implementació de `html_scraper.py` amb Mètode B (headers del `<td>`) + validació canònica contra `PREFIX_MAP`, fent passar 19/19 tests RED de la fase anterior.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Crear scrapers/html_scraper.py — GREEN TDD | 12cd15f | fp-cercador/backend/scrapers/html_scraper.py (creat) |
| 2 | REFACTOR opcional — revisió de duplicació i neteja | (omès — sense canvis) | — |

## What Was Built

El mòdul `scrapers/html_scraper.py` implementa el parsing HTML dels Grados D i E del ministeri todofp.es. Exposa:

- **4 funcions públiques:** `parse_grado_d_basico`, `parse_grado_d_medio`, `parse_grado_d_superior`, `parse_grado_e`
- **3 helpers privats:** `_build_fam_map`, `_extract_titols`, `_parse_grado_d`
- **`HTML_FAMILY_ALIASES`:** dict explícit per a les 2 anomalies conegudes de noms de família HTML
- **`HEADERS`:** duplicat intencionat de `pipeline.py` per evitar dependència circular

### Arquitectura de detecció de família

S'aplica el Mètode B (recomanat a 03-RESEARCH.md):

1. `_build_fam_map(soup)` — llegeix els `<th headers='familia'>` i construeix `{fam_id: nom_canonic}`. Aplica `HTML_FAMILY_ALIASES` per als 2 casos no canònics coneguts. Valida que el nom resultant sigui un valor de `PREFIX_MAP.values()` — si no ho és, no s'inclou al mapa.
2. `_extract_titols(soup, fam_map, nivel, grado)` — itera els `<td headers='... titulacion ...'>`, localitza el `fam_id` inicial amb `fam`, busca l'anchor `<a id='tit-*'>`, i mapeja via `fam_map`. Si `fam_id` no és al mapa → `'Desconeguda'` + `logger.warning`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Validació canònica de famílies a `_build_fam_map`**
- **Found during:** Task 1 — primer run de tests (1 test fallant)
- **Issue:** El pla especificava que famílies desconegudes havien de produir `'Desconeguda'`, però el codi inicial retornava el nom cru (p.ex. "Mantenimiento y Servicios a la Producción") sense validar contra `PREFIX_MAP`. Això feia fallar `test_family_unknown_becomes_desconeguda_and_warns`.
- **Fix:** Afegit `from scrapers.pdf_scraper import PREFIX_MAP` i validació `if canonical in PREFIX_MAP.values()` a `_build_fam_map`. Famílies no canòniques no s'inclouen al `fam_map`, i `_extract_titols` les gestiona com a `None` → `'Desconeguda'`.
- **Files modified:** `fp-cercador/backend/scrapers/html_scraper.py`
- **Commit:** 12cd15f

### Refactor

REFACTOR omès — cap duplicació significativa detectada. El pla ja anticipava aquest resultat (consistent amb Fase 2 plans 01/02).

## Test Results

```
19 passed in 0.24s  (test_html_scraper.py)
46 passed in 0.20s  (suite completa — cap regressió)
```

## Known Stubs

Cap — totes les funcions públiques retornen dades reals (mockejades en tests, reals en execució).

## Threat Flags

Cap superfície nova no contemplada al pla. Totes les amenaces T-03-04 a T-03-09 estan mitigades:
- `raise_for_status()` present (T-03-04)
- `isinstance(hv, list)` present — Pitfall 1 (T-03-09)
- `timeout=30` present (T-03-06)

## Self-Check

- [x] `fp-cercador/backend/scrapers/html_scraper.py` existeix
- [x] Commit `12cd15f` existeix
- [x] 19/19 tests `test_html_scraper.py` passen
- [x] 46/46 tests suite completa passen

## Self-Check: PASSED
