# Phase 3: HTML Scrapers + Data Pipeline (Grados D, E) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 03-html-scrapers-data-pipeline-grados-d-e
**Areas discussed:** Integració pipeline, Família des d'HTML, Estructura del codi D/E

---

## Integració pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| Ampliació in-place | Afegir D i E al dict `by_grado` existent | ✓ |
| Wrapper / 2 funcions | `run()` crida `run_pdfs()` + `run_html()` internament | |
| Clau `by_type` separada | Clau addicional per distingir origen PDF vs HTML | |

**User's choice:** Ampliació in-place
**Notes:** La interfície pública de `run()` roman compatible. La Fase 4 llegirà `by_grado` dinàmicament.

| Option | Description | Selected |
|--------|-------------|----------|
| A → B → C → D → E | Ordre natural dels Grados | ✓ |
| PDF primer, HTML al final | Semànticament separa per font | |

**User's choice:** A → B → C → D → E
**Notes:** Consistent amb la nomenclatura de la llei.

---

## Família des d'HTML

| Option | Description | Selected |
|--------|-------------|----------|
| Igual que PDFs: 'Desconeguda' | Registre inclòs amb warning al log | (implícit per fuzzy match) |
| Inclou sense família (null) | `familia=null` — requereix canvis al frontend | |

| Option | Description | Selected |
|--------|-------------|----------|
| Text exacte de la capçalera | S'usa el text HTML normalitzat com a valor | |
| Normalitzat contra PREFIX_MAP | Fuzzy match contra les 26 famílies existents | ✓ |

**User's choice:** Normalitzat contra PREFIX_MAP
**Notes (aportació clau de l'usuari):** La família NO és un text sinó una imatge `<img alt="Logotipo Hostelería y Turismo">` dins de `<th rowspan="N" headers="familia">`. Cal extreure el nom traient el prefix "Logotipo " i usar el `rowspan` per saber quants títols pertanyen a cada família. Cal verificar si `rowspan` és l'únic mecanisme.

| Option | Description | Selected |
|--------|-------------|----------|
| Fuzzy match + warning si no encaixa | Normalitzar i comparar; 'Desconeguda' si falla | ✓ |
| Hardcode FAMILY_MAP D/E separat | Dict `{alt_text: familia_name}` exclusiu per D/E | |

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, només rowspan | Única informació de relació família↔títol | |
| No ho sé amb certesa | Cal que l'agent analitzi l'HTML real | ✓ |

**Notes:** L'agent de recerca ha d'analitzar l'HTML real de les pàgines de Grado D/E per confirmar el mecanisme de relació família↔títol.

---

## Estructura del codi D/E

| Option | Description | Selected |
|--------|-------------|----------|
| Un fitxer, funció per subtipus | `parse_grado_d_basico/medio/superior` + `parse_grado_e` | ✓ |
| Un fitxer, funció genèrica | `parse_grado_d(url, nivel)` + `parse_grado_e` | |

**User's choice:** Un fitxer, funció per subtipus
**Notes:** Consistent amb el patró `pdf_scraper.py`. L'agent pot refactoritzar internament si l'HTML és idèntic.

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, HTML_URLS hardcode | Igual que `PDF_URLS` a `pipeline.py` | |
| Configurable per .env | URLs via variables d'entorn | ✓ (amb fallback hardcode) |

**User's choice:** Configurable per `.env` amb fallback hardcode
**Notes:** `os.getenv('URL_GRADO_D_BASICO', 'https://...-default-...')`. Actualitzar `.env.example` amb les 4 noves variables.

---

## Claude's Discretion

- Implementació interna de `_parse_grado_d(url, nivel)` si l'HTML és idèntic entre subtipus
- Estratègia exacta de fuzzy match (ratio threshold, biblioteca)
- Mecanisme real de relació família↔títol a l'HTML (a confirmar en recerca)
- URLs exactes dels 3 subtipus Grado D i catàleg Grado E

## Deferred Ideas

Cap — la discussió s'ha mantingut dins l'abast de la fase.
