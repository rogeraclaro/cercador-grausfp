# Phase 3: HTML Scrapers + Data Pipeline (Grados D, E) - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Scraping HTML del ministeri per als Grados D (Básico/Medio/Superior) i E (Cursos d'Especialització) + consolidació de tots 5 Grados (A, B, C, D, E) en un únic `fp-cercador/backend/data/ofertes.json`.

No inclou: API endpoints (Fase 4), execució en thread separat (Fase 4), frontend (Fases 5 i 6).

</domain>

<decisions>
## Implementation Decisions

### Errors del scraper HTML (no discutit — comportament per defecte)

- **D-01:** **Fail fast** — consistent amb D-01/D-02 de la Fase 2. Si qualsevol URL HTML falla (error de xarxa, 404, estructura inesperada), el pipeline s'atura i `ofertes.json` no s'actualitza. Cap escritura parcial.

### Integració amb pipeline.run()

- **D-02:** **Ampliació in-place** — `pipeline.run()` s'estén afegint D i E al dict `by_grado` existent. La interfície pública queda:
  ```python
  {
    "total": N,
    "by_grado": {"A": N, "B": N, "C": N, "D": N, "E": N},
    "errors": [],
    "duration_seconds": X
  }
  ```
  La Fase 4 llegirà `by_grado` dinàmicament; cap canvi addicional a la interfície.
- **D-03:** **Ordre IDs seqüencials: A → B → C → D → E**. Els IDs dels Grados A/B/C no canvien si D/E fallen (fail fast garanteix tot o res).

### Estructura del fitxer html_scraper.py

- **D-04:** **Un únic `fp-cercador/backend/scrapers/html_scraper.py`** amb funcions per subtipus, consistent amb el patró de `pdf_scraper.py`:
  ```python
  def parse_grado_d_basico(url: str) -> list[dict]
  def parse_grado_d_medio(url: str) -> list[dict]
  def parse_grado_d_superior(url: str) -> list[dict]
  def parse_grado_e(url: str) -> list[dict]
  ```
  Si l'estructura HTML dels subtipus D és idèntica, l'agent pot refactoritzar internament amb una funció genèrica `_parse_grado_d(url, nivel)` — a la seva discreció.

### URLs dels scrapers HTML

- **D-05:** **URLs via `.env` amb fallback hardcode**. Les 4 URLs (D_BASICO, D_MEDIO, D_SUPERIOR, E) es llegeixen amb `os.getenv('URL_GRADO_D_BASICO', 'https://...')`. Les URLs reals del ministeri estan al codi com a valors per defecte; `.env` les sobreescriu si canvien. El `.env.example` s'actualitza amb les 4 noves variables.
- **D-06:** Les URLs hardcode de fallback han de ser verificades per l'agent de recerca contra `https://www.todofp.es/que-estudiar/grados-d.html` i la URL del catàleg de Grado E.

### Detecció de família als Grados D/E

- **D-07:** **Estructura HTML real:** La família no és un text, sinó una imatge `<img alt="Logotipo Hostelería y Turismo">` dins de `<th rowspan="N" headers="familia">`. Cal:
  1. Trobar totes les `<th>` amb `headers="familia"` que continguin `<img>`
  2. Extreure el text de l'atribut `alt` i treure el prefix `"Logotipo "`
  3. Usar el `rowspan` per saber quants títols pertanyen a aquella família
  ⚠️ IMPORTANT: L'agent de recerca ha d'analitzar l'HTML real per confirmar que `rowspan` és l'únic mecanisme de relació família↔títol.

- **D-08:** **Normalitzat contra PREFIX_MAP de la Fase 2** — el nom extret de l'alt s'ha de mapar a les 26 famílies existents. Estratègia: normalització (minúscules, sense accents, espais trimats) + comparació fuzzy. Si no encaixa cap família coneguda, s'inclou el registre amb `familia='Desconeguda'` + warning al log (consistent amb D-04/D-05 de la Fase 2).

- **D-09:** **Referència de la pàgina d'entrada Grado D:** `https://www.todofp.es/que-estudiar/grados-d.html` — des d'aquí s'accedeix als 3 subtipus. L'agent de recerca ha de trobar les URLs exactes dels 3 llistats (Básico, Medio, Superior).

### Estructura de registres D/E

- **D-10:** Els registres Grados D i E segueixen l'esquema complet:
  ```python
  {
    "grado": "D" o "E",
    "nivel": 1 (Básico) | 2 (Medio) | 3 (Superior) | null (Grado E),
    "familia": "<nom de família>",
    "codigo": null,          # no hi ha codi per a HTML scrapers
    "denominacion": "<títol>",
    "plan_antiguo": false,   # sempre false per D/E
    "observaciones": ""      # camp buit
  }
  ```
  Els camps `id` i `grado` els afegeix `pipeline.py`, igual que als PDFs.

### Claude's Discretion

- Implementació interna de `_parse_grado_d(url, nivel)` si l'HTML és idèntic entre subtipus
- Estratègia exacta de fuzzy match per al mapeig família (ratio threshold, biblioteca a usar)
- Gestió de `rowspan` si no és l'únic mecanisme de relació família↔títol (a determinar en recerca)
- URLs exactes dels 3 subtipus Grado D i del catàleg Grado E (a verificar per l'agent de recerca)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements del projecte
- `.planning/REQUIREMENTS.md` §Scraper HTML (Grados D i E) — HTML-01 a HTML-06 (criteris d'acceptació)
- `.planning/REQUIREMENTS.md` §Generació de Dades — DATA-01 a DATA-04 (schema i volum)
- `.planning/PROJECT.md` §Context — URLs fonts, volums esperats (D: ~150, E: ~36 registres)

### Fases anteriors
- `.planning/phases/02-pdf-scrapers-grados-a-b-c/02-CONTEXT.md` — Decisions D-01–D-09 (fail fast, sense cache, PREFIX_MAP, estructura pipeline)
- `.planning/phases/02-pdf-scrapers-grados-a-b-c/02-03-SUMMARY.md` — Resultat real de l'execució del pipeline (volum confirmat)

### Codi existent a analitzar
- `fp-cercador/backend/scrapers/pipeline.py` — Interfície `run()` i `PDF_URLS` a estendre
- `fp-cercador/backend/scrapers/pdf_scraper.py` — PREFIX_MAP (26 famílies) a reutilitzar per al mapeig de famílies HTML

### URLs d'entrada per a recerca
- `https://www.todofp.es/que-estudiar/grados-d.html` — Pàgina d'entrada als 3 subtipus Grado D
- A trobar per l'agent: URLs exactes dels llistats Básico, Medio, Superior i catàleg Grado E

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `fp-cercador/backend/scrapers/pdf_scraper.py` — `PREFIX_MAP` (26 famílies) reutilitzable per al mapeig de famílies HTML (D-08)
- `fp-cercador/backend/scrapers/pipeline.py` — `HEADERS`, `_download_pdf()` (adaptable per a pàgines HTML), `_write_atomic()`, `run()` a estendre
- `fp-cercador/backend/scrapers/__init__.py` — Paquet existent; `html_scraper.py` s'hi afegirà

### Established Patterns
- Fail fast + tot o res: s'aplica als scrapers HTML igual que als PDFs
- Sense cache: les pàgines HTML es descarreguen freshques cada execució
- `_write_atomic()`: ja implementat, el pipeline el reutilitza sense canvis
- Funcions per subtipus: `parse_grado_d_basico/medio/superior` segueix el patró `parse_grado_a/b/c`

### Integration Points
- `pipeline.run()` → afegir crida a `html_scraper.py` i estendre `by_grado` amb D/E
- `fp-cercador/backend/data/ofertes.json` → passa de ~700 registres (A/B/C) a ~850–900 (tots 5 Grados)
- `.env.example` → afegir `URL_GRADO_D_BASICO`, `URL_GRADO_D_MEDIO`, `URL_GRADO_D_SUPERIOR`, `URL_GRADO_E`

</code_context>

<specifics>
## Specific Ideas

- **Estructura HTML clau** (confirmat per l'usuari): La família ve d'una `<img alt="Logotipo [Família]">` dins `<th rowspan="N" headers="familia">`. El `rowspan` és probablement el mecanisme de relació, però cal verificar-ho amb l'HTML real.
- **Pàgina d'entrada Grado D**: `https://www.todofp.es/que-estudiar/grados-d.html` té 3 botons per accedir als subtipus Básico/Medio/Superior.
- La implementació s'ha de confirmar analitzant l'HTML real abans de codificar — és la tasca de l'agent de recerca.

</specifics>

<deferred>
## Deferred Ideas

None — la discussió s'ha mantingut dins l'abast de la fase.

</deferred>

---

*Phase: 03-html-scrapers-data-pipeline-grados-d-e*
*Context gathered: 2026-04-17*
