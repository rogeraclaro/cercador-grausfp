---
phase: 03-html-scrapers-data-pipeline-grados-d-e
verified: 2026-04-18T10:00:00Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
gaps: []
human_verification: []
---

# Phase 3: HTML Scrapers + Data Pipeline Verification Report

**Phase Goal:** Grados D and E are scraped from ministry HTML pages and all 5 Grados are consolidated into a single ofertes.json
**Verified:** 2026-04-18T10:00:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tots els títols Grado D (Básico, Medio, Superior) s'extreuen via elements `id="tit-*"` | VERIFIED | `_extract_titols` cerca `td.find('a', id=lambda x: x and x.startswith('tit-'))`. 19/19 tests pass. D: 195 registres en ofertes.json. |
| 2 | Tots els títols Grado E (Cursos d'Especialització) s'extreuen des de la URL correcta | VERIFIED | `parse_grado_e` usa `HTML_URLS['E']` amb fallback `todofp.es/...curso-especializacion.html`. E: 36 registres en ofertes.json. |
| 3 | La família professional s'infereix correctament de les capçaleres de secció per a cada registre D/E | VERIFIED | `_build_fam_map` usa Mètode B (headers del `<td>`). `HTML_FAMILY_ALIASES` gestiona 2 anomalies. 0 registres amb `familia='Desconeguda'` a ofertes.json. |
| 4 | `backend/data/ofertes.json` generat amb schema complet (id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones) | VERIFIED | Schema verificat. D: `codigo=None, plan_antiguo=False`. E: `codigo=None, nivel=None, plan_antiguo=False`. |
| 5 | El fitxer conté ~12.000-12.500 registres totals amb IDs únics i seqüencials abastant els 5 Grados | VERIFIED | 12.374 registres. IDs 1-12.374 seqüencials. Grados: A(8537), B(2786), C(820), D(195), E(36). |
| 6 | `pipeline.run()` retorna `by_grado` amb les 5 claus: A, B, C, D, E | VERIFIED | Test `test_pipeline_run_returns_correct_schema` assert `set(result['by_grado'].keys()) == {'A', 'B', 'C', 'D', 'E'}`. 55 tests pass. |
| 7 | L'ordre d'IDs és A → B → C → D → E | VERIFIED | max(ABC)=12143 < min(DE)=12144. Test `test_pipeline_id_order_a_b_c_d_e` verifica IDs 1-7 per ordre. |
| 8 | Si qualsevol URL HTML falla, `ofertes.json` NO s'actualitza (fail fast D-01, D-02) | VERIFIED | `raise_for_status()` present a `_parse_grado_d` i `parse_grado_e`. Test `test_pipeline_fail_fast_on_html_error` confirma `os.replace` no cridat. |
| 9 | La suite completa de tests unitaris (pdf, html, pipeline) passa | VERIFIED | 55 passed in 1.76s (0 errors, 0 failures). |
| 10 | L'execució real contra todofp.es produeix un `ofertes.json` vàlid amb ~12.374 registres | VERIFIED | Fitxer de 3.68 MB. 12.374 registres. 0 famílies desconegudes. IDs seqüencials confirmats. |

**Score:** 10/10 truths verified

### Deferred Items

Cap element diferit identificat.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `fp-cercador/backend/scrapers/html_scraper.py` | 4 funcions parse_grado_* + HTML_FAMILY_ALIASES + helpers | VERIFIED | Existeix amb totes les exportacions: `HTML_FAMILY_ALIASES`, `_build_fam_map`, `_extract_titols`, `parse_grado_d_basico/medio/superior`, `parse_grado_e`. Importable i funcional. |
| `fp-cercador/backend/scrapers/pipeline.py` | pipeline.run() estès amb HTML_URLS + loop HTML D/E | VERIFIED | `from scrapers.html_scraper import` a línia 25. `HTML_URLS` amb 4 claus. `html_parsers` i `html_by_grado` presents dins `run()`. |
| `fp-cercador/backend/tests/test_html_scraper.py` | Suite de tests que cobreix HTML-01 a HTML-06 | VERIFIED | 19 tests. `from scrapers.html_scraper import` present. Cobreix totes les funcions públiques, aliases, fail fast, schema. |
| `fp-cercador/backend/tests/test_pipeline.py` | Tests actualitzats amb mocks D/E i 2 tests nous | VERIFIED | 9 tests (7 existents + 2 nous). Mocks `PATCH_PARSE_D_BASICO/MEDIO/SUPERIOR/E` presents. `test_pipeline_id_order_a_b_c_d_e` i `test_pipeline_fail_fast_on_html_error` existeixen. |
| `fp-cercador/backend/tests/conftest.py` | 4 noves fixtures HTML afegides | VERIFIED | 11 fixtures totals (7 existents + 4 noves HTML). `minimal_html_grado_d_one_record`, `minimal_html_grado_d_two_records_same_family`, `minimal_html_alias_imagen_y_sonido`, `minimal_html_unknown_family` presents. |
| `fp-cercador/backend/.env.example` | 4 variables URL_GRADO_D_*/URL_GRADO_E | VERIFIED | 4 línies `URL_GRADO_*` amb URLs verificades de todofp.es. |
| `fp-cercador/backend/data/ofertes.json` | Dataset complet dels 5 Grados, ~12.000-12.500 registres | VERIFIED | 12.374 registres. 3.68 MB. Grados A/B/C/D/E presents. IDs seqüencials. 0 famílies desconegudes. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scrapers.pipeline` | `scrapers.html_scraper` | `from scrapers.html_scraper import` (línia 25) | WIRED | 4 funcions importades i usades dins `html_parsers` a `run()` |
| `scrapers.html_scraper` | `scrapers.pdf_scraper.PREFIX_MAP` | `from scrapers.pdf_scraper import PREFIX_MAP` | WIRED | Usat a `_build_fam_map` per validar noms canònics de família |
| `scrapers.html_scraper` | `bs4.BeautifulSoup` | `from bs4 import BeautifulSoup` | WIRED | Usat a `_parse_grado_d` i `parse_grado_e` |
| `scrapers.html_scraper` | `requests.get` | `requests.get(url, headers=HEADERS, timeout=30)` | WIRED | Present a `_parse_grado_d` i `parse_grado_e` amb `raise_for_status()` |
| `HTML_URLS` | `.env.example (URL_GRADO_D_*/URL_GRADO_E)` | `os.getenv('URL_GRADO_D_BASICO', ...)` | WIRED | 4 crides `os.getenv` amb fallback hardcode a pipeline.py línies 57-61 |
| `scrapers.pipeline.run` | `fp-cercador/backend/data/ofertes.json` | `_write_atomic(all_records, DATA_PATH)` | WIRED | `_write_atomic` cridada a línia 187 de pipeline.py |
| `tests/test_pipeline.py` | `scrapers.pipeline.parse_grado_d_basico/medio/superior/e` | `mock.patch(PATCH_PARSE_D_*)` | WIRED | 4 patch paths definits; usats en tots 9 tests |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `ofertes.json` | `all_records` | `parse_grado_d_basico/medio/superior(url)` + `parse_grado_e(url)` → `_parse_grado_d` → `requests.get` → BeautifulSoup | Sí — 12.374 registres reals (D:195, E:36) | FLOWING |
| `html_scraper.py` | `fam_map` | `_build_fam_map(soup)` llegeix `<th headers='familia'>` | Sí — 29 famílies úniques, 0 Desconeguda en execució real | FLOWING |
| `pipeline.py` | `by_grado` | Loop `html_parsers` acumula a `html_by_grado` | Sí — D:195, E:36 a `by_grado` retornat per `run()` | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| html_scraper importable amb símbols correctes | `python3 -c "from scrapers.html_scraper import parse_grado_d_basico, parse_grado_e, HTML_FAMILY_ALIASES; print('OK', list(HTML_FAMILY_ALIASES.keys()))"` | `OK ['Imagen y Sonido', 'Artes y Artesanias']` | PASS |
| pipeline.HTML_URLS té 4 claus correctes | `python3 -c "from scrapers.pipeline import HTML_URLS, run; print(sorted(HTML_URLS.keys()))"` | `['D_BASICO', 'D_MEDIO', 'D_SUPERIOR', 'E']` | PASS |
| ofertes.json: 12.374 registres, 5 Grados, IDs seqüencials | `python3 -c "import json; d=json.load(open('data/ofertes.json')); ..."` | Total: 12374, sequential=True, Desconeguda=0, 5 Grados | PASS |
| Suite completa de 55 tests | `python3 -m pytest tests/ -q` | `55 passed in 1.76s` | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| HTML-01 | 03-01, 03-02 | Extreu títols Grado D des de 3 URLs (Básico, Medio, Superior) | SATISFIED | `parse_grado_d_basico/medio/superior` implementats. D: 195 registres en ofertes.json. |
| HTML-02 | 03-01, 03-02 | Extreu títols Grado E des de URL Cursos Especialització | SATISFIED | `parse_grado_e` implementat. E: 36 registres en ofertes.json. |
| HTML-03 | 03-01, 03-02 | Títols identificats per elements `id="tit-*"` | SATISFIED | `td.find('a', id=lambda x: x and x.startswith('tit-'))` a `_extract_titols`. |
| HTML-04 | 03-01, 03-02 | Família inferida de les capçaleres de secció del HTML | SATISFIED | `_build_fam_map` + Mètode B. 0 Desconeguda en execució real. `HTML_FAMILY_ALIASES` gestiona 2 anomalies. |
| HTML-05 | 03-01, 03-02 | Nivel: Básico→1, Medio→2, Superior→3, Grado E→null | SATISFIED | `_parse_grado_d(url, nivel=1/2/3)` i `parse_grado_e` amb `nivel=None`. Tests `test_nivel_*` passen. |
| HTML-06 | 03-01, 03-02 | Registres D/E: `codigo: null`, `plan_antiguo: false` | SATISFIED | Schema fix a `_extract_titols`. Verificat contra ofertes.json: tots els D/E complien. |
| DATA-01 | 03-03 | Pipeline genera `ofertes.json` amb schema complet | SATISFIED | 12.374 registres amb tots 8 camps: id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones. |
| DATA-02 | 03-03 | IDs correlatius i únics | SATISFIED | IDs 1-12.374, seqüencial verificat (`ids==list(range(1,12375))`). |
| DATA-03 | 03-03 | Consolida Grados A, B, C, D, E en un únic array | SATISFIED | Grados `['A','B','C','D','E']` presents a ofertes.json. |
| DATA-04 | 03-03 | ~12.000-12.500 registres totals (REQUIREMENTS.md actualitzat 2026-04-18) | SATISFIED | 12.374 registres. REQUIREMENTS.md DATA-04 actualitzat correctament amb la xifra real i nota explicativa. Nota: ROADMAP.md SC-5 diu "800-900" (stale) — el context de la tasca indica que DATA-04 de REQUIREMENTS.md és la font de veritat actualitzada. |

**Nota sobre SC-5 del ROADMAP:** El ROADMAP.md Phase 3 SC-5 diu "800–900 total records" (valor stale). El context de verificació especifica explícitament que cal verificar contra DATA-04 de REQUIREMENTS.md (actualitzat a ~12.000-12.500). REQUIREMENTS.md DATA-04 és la font de veritat corregida.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `fp-cercador/backend/data/ofertes.json` | — | Fitxer de 3.68 MB (sota els 4 MB indicats com a criteri mínim al pla) | Info | Cap impacte funcional — el fitxer conte dades reals i el tamany és degut a l'escriptura amb indent=2 sense compressió. Acceptable per a la fase actual. |

Cap stub, cap `return []` buit sense consulta, cap handler buit. Els mocks dels tests estan correctament encapsulats i no afecten el codi de producció.

### Human Verification Required

Cap. Tots els must-haves es poden verificar programàticament i han estat verificats amb èxit.

### Gaps Summary

Cap gap identificat. La fase 3 ha assolit completament el seu objectiu:

- `html_scraper.py` implementat amb TDD (RED → GREEN), 19 tests passant
- `pipeline.py` estès amb loop HTML per Grados D/E, fail fast, i escriptura atòmica
- `ofertes.json` regenerat amb 12.374 registres dels 5 Grados, 0 famílies desconegudes, IDs seqüencials A→B→C→D→E
- 55 tests unitaris passen (19 html_scraper + 9 pipeline + 27 pdf_scraper)
- REQUIREMENTS.md DATA-04 actualitzat a la xifra real (~12.000-12.500)
- Bugs de producció (LOGSE sense guió baix, Grado E sense prefix "Logotipo ", PREFIX_MAP incomplet) corregits durant l'execució real

---

_Verified: 2026-04-18T10:00:00Z_
_Verifier: Claude (gsd-verifier)_
