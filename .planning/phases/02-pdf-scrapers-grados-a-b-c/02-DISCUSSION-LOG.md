# Phase 2: PDF Scrapers (Grados A, B, C) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 02-pdf-scrapers-grados-a-b-c
**Areas discussed:** Errors durant el refresh, Cache de PDFs, Família desconeguda, Estructura del mòdul

---

## Errors durant el refresh

| Option | Description | Selected |
|--------|-------------|----------|
| Continua amb els altres | Refresh conté els Grados processats; error registrat a refresh-status | |
| S'atura tot | Qualsevol error atura el refresh completament | ✓ |

**User's choice:** S'atura tot (fail fast)
**Notes:** Consistent amb la segona resposta — si el refresh s'atura, l'ofertes.json anterior es conserva.

| Option | Description | Selected |
|--------|-------------|----------|
| Sobreescriu amb les dades parcials | Sempre actualitza amb el que s'ha pogut extreure | |
| Conserva l'anterior si hi ha errors | Només sobreescriu si tot ha anat bé | ✓ |

**User's choice:** Conserva l'anterior si hi ha errors

---

## Cache de PDFs

| Option | Description | Selected |
|--------|-------------|----------|
| No, sempre re-descarregar | Descarrega frescos, elimina en acabar | ✓ |
| Sí, guardar a data/pdfs/ | PDFs queden al disc per reutilitzar | |

**User's choice:** No, sempre re-descarregar

---

## Família desconeguda

| Option | Description | Selected |
|--------|-------------|----------|
| Inclou amb familia='Desconeguda' | Registre inclòs amb sentinel, cap pèrdua de dades | ✓ |
| Descarta el registre | Registres sense família omesos | |
| Atura el scraping | Tracta com error fatal | |

**User's choice:** Inclou amb familia='Desconeguda'

| Option | Description | Selected |
|--------|-------------|----------|
| Sí, warning als logs | Facilita detecció de problemes | ✓ |
| No, silenciós | Cap avís generat | |

**User's choice:** Sí, warning als logs

---

## Estructura del mòdul scraper

| Option | Description | Selected |
|--------|-------------|----------|
| Un únic pdf_scraper.py | Funcions parse_grado_a/b/c en un mòdul | ✓ |
| Fitxers separats per Grado | pdf_a.py, pdf_b.py, pdf_c.py | |

**User's choice:** Un únic pdf_scraper.py

| Option | Description | Selected |
|--------|-------------|----------|
| pipeline.py a scrapers/ | Orquestrador separat, API importa pipeline.run() | ✓ |
| Directament a app.py | Lògica de refresh barrejada amb l'API | |

**User's choice:** pipeline.py a scrapers/

---

## Claude's Discretion

- URLs exactes dels PDFs a todofp.es
- Valors dels headers Referer i User-Agent
- Estratègia interna de parsing amb pdfplumber
- Regex per codis de pla antic

## Deferred Ideas

- Scrapers HTML (Grados D/E) → Fase 3
- Thread separat i gestió d'estat → Fase 4
- Endpoint POST /api/admin/refresh → Fase 4
