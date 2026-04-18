---
phase: 02-pdf-scrapers-grados-a-b-c
plan: "03"
subsystem: backend/data
tags: [pipeline, integration, real-data, ofertes.json, checkpoint]
dependency_graph:
  requires:
    - scrapers.pipeline.run
    - fp-cercador/backend/scrapers/pdf_scraper.py
  produces:
    - fp-cercador/backend/data/ofertes.json
status: complete
---

## Objectiu

Execució real del pipeline contra todofp.es i verificació que `ofertes.json` conté dades correctes i completes per als Grados A, B i C. Checkpoint humà aprovat.

## Resultat

Pipeline executat correctament. `ofertes.json` actualitzat amb **12.143 registres** dels Grados A, B i C.

| Grado | Registres |
|-------|-----------|
| A     | 8.537     |
| B     | 2.786     |
| C     | 820       |
| **Total** | **12.143** |

Durada d'execució: ~55 segons.

## Verificacions

- ✓ IDs seqüencials 1..N sense buits
- ✓ Estructura de camps correcta: `id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones`
- ✓ `familia=Desconeguda`: **0 registres** (resolt durant checkpoint)
- ✓ Grado C nou pla: 0 registres amb `nivel=null` (318 registres amb nivel correcte)
- ✓ `plan_antiguo=True`: 5.130 registres, codis nets (sense marcador `(Plan antiguo)`)
- ✓ `app.py` no modificat (roman com a stub de Fase 1)
- ✓ Checkpoint humà: aprovat

## Desviació documentada

**PREFIX_MAP ampliat durant checkpoint**: Durant la verificació humana es va detectar que 5.130 registres de pla antic tenien `familia='Desconeguda'` perquè els codis LOGSE/Certificats de Professionalitat no segueixen el format `PREFIXFAMÍLIA_grado_número`. Es va ampliar el PREFIX_MAP i la lògica d'extracció de prefix per cobrir:

- `ART` → 'Artesanía' (codis tipus ARTA####, ARTB####...)
- `SAN` → 'Sanidad' (codis tipus SANT####)
- `UF` → 'Certificados de Profesionalidad' (2.794 registres)
- `MF` → 'Certificados de Profesionalidad' (1.834 registres)
- Codis 4-char (ADGD, AFDA, AGAN...): resolts per fallback als 3 primers caràcters

La lògica `_get_family_prefix` al `_extract_records` ara extreu el prefix alfabètic del segment primari del codi i prova progressivament fins a 2 caràcters. Resultat: 27 famílies úniques, `familia=Desconeguda` = 0.

Tests actualitzats: `test_prefix_map_completeness` ara verifica 28 entrades.

## Fitxers produïts

- `fp-cercador/backend/data/ofertes.json` — 12.143 registres, JSON vàlid (~4.2 MB)

## Fitxers modificats (correctiu checkpoint)

- `fp-cercador/backend/scrapers/pdf_scraper.py` — PREFIX_MAP ampliat (28 entrades), lògica d'extracció de prefix millorada
- `fp-cercador/backend/tests/test_pdf_scraper.py` — `test_prefix_map_completeness` actualitzat a 28

## Self-Check: PASSED

- `len(ofertes.json records) = 12143 > 10000` ✓
- `set(r['grado'] for r in records) = {'A', 'B', 'C'}` ✓
- IDs seqüencials ✓
- `familia=Desconeguda` count = 0 ✓
- Tots els tests passen (`python3 -m pytest tests/ -v`) ✓
