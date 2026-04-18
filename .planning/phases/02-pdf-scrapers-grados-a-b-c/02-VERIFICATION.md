---
phase: 02-pdf-scrapers-grados-a-b-c
verified: 2026-04-17T12:30:00Z
status: human_needed
score: 14/15
overrides_applied: 0
human_verification:
  - test: "Confirmar que el requisit PDF-02 accepta 27 famílies úniques (en lloc de les 29 indicades a REQUIREMENTS.md)"
    expected: "El propietari valida que 27 famílies úniques cobreixen tota l'oferta dels Grados A, B, C, o bé actualitza REQUIREMENTS.md a '27 famílies'"
    why_human: "REQUIREMENTS.md diu '29 famílies'; la implementació i les dades reals en contenen 27 úniques (28 entrades a PREFIX_MAP, UF i MF apunten a la mateixa família). Pot ser que la xifra 29 a REQUIREMENTS.md sigui un error d'enumeració inicial o que manquin 2 famílies al PREFIX_MAP. Cal decisió del propietari."
---

# Phase 02: PDF Scrapers (Grados A, B, C) — Informe de Verificació

**Objectiu de la fase:** Els tres PDFs oficials de todofp.es es descarreguen i es parsegen en registres estructurats nets.
**Verificat:** 2026-04-17T12:30:00Z
**Estat:** human_needed
**Re-verificació:** No — verificació inicial

---

## Assoliment de l'Objectiu

### Veritats Observables

| # | Veritat | Estat | Evidència |
|---|---------|-------|-----------|
| 1 | parse_grado_a(), parse_grado_b(), parse_grado_c() existeixen a pdf_scraper.py i retornen llistes de dicts | VERIFICAT | Importació `from scrapers.pdf_scraper import parse_grado_a, parse_grado_b, parse_grado_c` funciona; tests test_public_api_exports i test_record_schema_grado_c passen |
| 2 | Cada registre retornat té exactament els camps: codigo, denominacion, familia, nivel, plan_antiguo, observaciones | VERIFICAT | test_record_schema_grado_c verifica el conjunt exacte de claus; verificat en dades reals de 12.143 registres |
| 3 | El prefix del codi es mapeja correctament als noms de família via PREFIX_MAP | VERIFICAT (parcial) | 28 entrades, 27 famílies úniques, cobertura completa de les dades reals (Desconeguda=0). Pendent aclariment del nombre esperat — vegeu Verificació Humana |
| 4 | plan_antiguo=True quan la cel·la del codi conté '(Plan antiguo)'; clean_code no conté aquest marcador | VERIFICAT | 5.130 registres amb plan_antiguo=True als datos reals; 0 codis amb marcador als registres; tests test_plan_antiguo_* passen |
| 5 | Grado C nou pla: _3B→nivel=1, _4B→nivel=2, _5B→nivel=3; Grado A i B nou pla: nivel=None | VERIFICAT | 318 registres Grado C nou pla, 0 amb nivel=null; tests test_nivel_grado_c_* passen |
| 6 | Pla antic Grado B (MF2268_2): nivel=2 extret del sufix _N | VERIFICAT | test_nivel_grado_b_old_2 verifica _nivel_grado_b('MF2268_2', True)==2; passen tests _old_1/2/3/no_suffix |
| 7 | Família desconeguda produeix logging.warning i inclou el registre amb familia='Desconeguda' | VERIFICAT | test_familia_unknown_prefix_warning passa; dades reals: 0 registres Desconeguda |
| 8 | Les pàgines 1–5 (índex 0–4) no produeixen cap registre; el parsing comença a l'índex 5 | VERIFICAT | test_page_skip_index_4_no_records i test_page_skip_index_5_has_records passen; codi `pdf.pages[5:]` a pdf_scraper.py línia 145 |
| 9 | Codis duplicats entre pàgines: només el primer occurrence es conserva | VERIFICAT | test_duplicate_deduplication passa; diccionari `records` a _extract_records garanteix unicitat |
| 10 | La suite de tests unitaris passa completament sense xarxa (usant fixtures) | VERIFICAT | `python3 -m pytest tests/ -v` → 34/34 passed en 0.14s, zero xarxa |
| 11 | pipeline.run() existeix i és importable des de scrapers.pipeline | VERIFICAT | `from scrapers.pipeline import run` funciona; test_pipeline_run_returns_correct_schema passa |
| 12 | pipeline.run() descarrega els 3 PDFs usant GET amb els headers User-Agent i Referer correctes | VERIFICAT | test_pipeline_headers_used passa; HEADERS conté Mozilla/5.0 i Referer todofp.es; requests.get amb headers verificat per grep |
| 13 | pipeline.run() elimina els PDFs temporals després del parse (amb o sense error) | VERIFICAT | test_pipeline_deletes_pdf_on_success (3 cridades os.unlink) i test_pipeline_deletes_pdf_on_error passen; finally block a línia 138 |
| 14 | Si tots els Grados s'extreuen correctament, pipeline.run() escriu ofertes.json de forma atòmica | VERIFICAT | test_pipeline_atomic_write passa; os.replace a línia 90; os.unlink a línia 141 |
| 15 | El pipeline s'executa completament i ofertes.json conté >10.000 registres amb estructura correcta | VERIFICAT | 12.143 registres; esquema correcte (set de camps); IDs seqüencials 1..12143; Grados {'A','B','C'} presents |

**Puntuació: 14/15 veritats verificades** (1 pendent de confirmació humana sobre el nombre de famílies)

---

### Artefactes Requerits

| Artefacte | Esperat | Estat | Detalls |
|-----------|---------|-------|---------|
| `fp-cercador/backend/scrapers/pdf_scraper.py` | Funcions parse_grado_a/b/c i PREFIX_MAP | VERIFICAT | 214 línies; exporta parse_grado_a, parse_grado_b, parse_grado_c, PREFIX_MAP (28 entrades) |
| `fp-cercador/backend/tests/test_pdf_scraper.py` | Suite tests unitaris PDF-02 a PDF-06 | VERIFICAT | 355 línies; 27 tests; tots passen |
| `fp-cercador/backend/tests/conftest.py` | Fixtures compartides | VERIFICAT | Fixtures sample_table_grado_c, grado_b_old, grado_a_new, etc. |
| `fp-cercador/backend/tests/__init__.py` | Paquet de tests | VERIFICAT | Existeix (0B) |
| `fp-cercador/backend/scrapers/pipeline.py` | Orquestrador amb run() | VERIFICAT | 157 línies; exposa run(), HEADERS, PDF_URLS |
| `fp-cercador/backend/tests/test_pipeline.py` | Tests del pipeline amb mocks | VERIFICAT | 336 línies; 7 tests; tots passen |
| `fp-cercador/backend/data/ofertes.json` | Dades reals Grados A, B, C | VERIFICAT | 12.143 registres, ~4.2 MB, JSON vàlid |

---

### Verificació d'Enllaços Clau

| De | A | Via | Estat | Detalls |
|----|---|-----|-------|---------|
| `scrapers/pipeline.py` | `scrapers/pdf_scraper.py` | `from scrapers.pdf_scraper import parse_grado_a, parse_grado_b, parse_grado_c` | CONECTAT | Línia 24 de pipeline.py; import real confirmat per grep |
| `scrapers/pipeline.py` | `data/ofertes.json` | `_write_atomic() → os.replace()` | CONECTAT | os.replace a línia 90; DATA_PATH apunta a ../data/ofertes.json |
| `scrapers/pipeline.py` | `https://www.todofp.es` | `requests.get() amb HEADERS` | CONECTAT | requests.get a línia 68; HEADERS amb User-Agent + Referer verificats |

---

### Traça de Flux de Dades (Nivell 4)

| Artefacte | Variable de Dades | Font | Produeix Dades Reals | Estat |
|-----------|------------------|------|----------------------|-------|
| `pipeline.py` → `ofertes.json` | `all_records` | parse_grado_a/b/c(pdf_path) | Sí — 12.143 registres reals | FLUINT |
| `pdf_scraper.py` → registres | `records` dict | pdfplumber.open(pdf_path).pages[5:] | Sí — taules extretes de PDFs reals | FLUINT |

---

### Comprovacions de Comportament (Spot-checks)

| Comportament | Comanda | Resultat | Estat |
|--------------|---------|----------|-------|
| Tests passen sense xarxa | `python3 -m pytest tests/ -v` | 34/34 passed en 0.14s | PASSA |
| Importació pdf_scraper OK | `from scrapers.pdf_scraper import parse_grado_a, ..., PREFIX_MAP` | OK 28 prefixos | PASSA |
| Importació pipeline OK | `from scrapers.pipeline import run, HEADERS, PDF_URLS` | Constants OK | PASSA |
| ofertes.json > 10.000 | `len(records) = 12143` | 12.143 | PASSA |
| Esquema de camps correcte | tots els 12.143 registres | True | PASSA |
| IDs seqüencials | `ids == list(range(1, 12144))` | True | PASSA |
| Grados presents | `{'A','B','C'}` | Correcte | PASSA |
| Família Desconeguda | count = 0 | 0 | PASSA |
| Grado C nou pla: 0 nivel=null | `grado_c_null_nivel = 0` | 0 | PASSA |
| plan_antiguo codis nets | 0 codis amb marcador | 0 | PASSA |
| app.py no modificat | stub Flask pur (11 línies) | Intacte | PASSA |

---

### Cobertura de Requisits

| Requisit | Pla Font | Descripció | Estat | Evidència |
|----------|----------|------------|-------|-----------|
| PDF-01 | 02-02, 02-03 | Descarrega PDFs amb headers Referer i User-Agent | SATISFET | HEADERS verifcat; requests.get amb headers; test_pipeline_headers_used passa |
| PDF-02 | 02-01, 02-02 | Detecta família professional (29 famílies) | PENDENT HUMÀ | 27 famílies úniques implementades, cobertura total (Desconeguda=0). REQUIREMENTS.md diu "29 famílies" |
| PDF-03 | 02-01 | Dedueix nivel del sufix: _3B→1, _4B→2, _5B→3 | SATISFET | tests nivel_grado_c_* passen; dades reals: 318 Grado C nous plans amb nivel correcte |
| PDF-04 | 02-01 | Detecta plan_antiguo per codis antics | SATISFET | 5.130 registres plan_antiguo=True; codis nets; tests plan_antiguo_* passen |
| PDF-05 | 02-01 | Omet pàgines 1–5 | SATISFET | `pdf.pages[5:]` a línia 145; tests page_skip passen |
| PDF-06 | 02-01 | Genera registres amb Código, Denominación, Observaciones | SATISFET | Schema exacte verificat en 12.143 registres reals |

**Requisits Orfes**: Cap. Tots els requisits de la fase (PDF-01 a PDF-06) estan coberts pels plans declarats.

---

### Anti-patrons Detectats

| Fitxer | Línia | Patró | Severitat | Impacte |
|--------|-------|-------|-----------|---------|
| Cap | — | Cap anti-patró detectat | — | — |

Notes:
- `return None` a `_nivel_grado_a` és implementació legítima (Grado A no té nivell).
- Els `return []` en tests amb mocks és comportament correcte de fixtures.
- No hi ha `TODO`, `FIXME`, `PLACEHOLDER` als fitxers de la fase.

---

### Verificació Humana Requerida

#### 1. Nombre de Famílies Professionals (PDF-02)

**Prova:** Comparar el nombre de famílies úniques esperat vs. implementat.

**Context:** `REQUIREMENTS.md` especifica "29 famílies" a PDF-02. La implementació actual conté:
- `PREFIX_MAP`: 28 entrades (24 del nou sistema + ART, SAN, UF, MF)
- Famílies úniques: **27** (UF i MF ambdues apunten a "Certificados de Profesionalidad")
- Dades reals: **27 famílies úniques** a `ofertes.json` (0 registres "Desconeguda")

Les 27 famílies cobreixen tota l'oferta dels Grados A, B i C sense deixar cap registre sense família. La discrepància amb "29" a REQUIREMENTS.md pot ser:
1. Un error de comptatge inicial al redactar els requisits
2. Dues famílies del sistema FP espanyol no presents als PDFs A/B/C (podrien aparèixer a Grados D/E)

**Esperat:** El propietari valida una d'aquestes opcions:
- **Opció A:** 27 famílies és correcte — actualitzar REQUIREMENTS.md de "29" a "27"
- **Opció B:** Manquen 2 famílies al PREFIX_MAP — identificar quines i afegir-les

**Per què cal humà:** No és possible determinar programàticament si "29" a REQUIREMENTS.md és un error tipogràfic o si hi ha dues famílies FP que s'han omès del mapatge.

---

### Resum de Desviacions

**Desviació documentada al Pla 03 (correcció durant checkpoint):**
- El `PREFIX_MAP` original tenia 24 entrades. Durant l'execució real, es va detectar que els codis LOGSE/Certificats de Professionalitat no seguien el format `PREFIX_GRADO_núm`. El PREFIX_MAP es va ampliar a 28 entrades (afegits ART, SAN, UF, MF) i la lògica d'extracció de prefix es va millorar amb fallback progressiu. Resultat: cobertura completa (0 "Desconeguda").
- El test `test_prefix_map_completeness` va ser actualitzat de 24 a 28 entrades per reflectir el correctiu.

**Impacte:** La desviació millora el requisit original. No hi ha degradació de funcionalitat.

---

_Verificat: 2026-04-17T12:30:00Z_
_Verificador: Claude (gsd-verifier)_
