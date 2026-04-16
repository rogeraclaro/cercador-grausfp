# Phase 2: PDF Scrapers (Grados A, B, C) - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Descarregar els 3 PDFs oficials de todofp.es i parsejar-los en registres JSON estructurats (familia, codigo, denominacion, nivel, plan_antiguo, observaciones) per als Grados A, B i C. El resultat és `fp-cercador/backend/data/ofertes.json` amb ~700 registres.

No inclou: scrapers HTML (Grados D i E — Fase 3), API endpoints (Fase 4), ni execució en thread separat (Fase 4).

</domain>

<decisions>
## Implementation Decisions

### Gestió d'Errors del Refresh

- **D-01:** **Fail fast** — Si qualsevol dels 3 PDFs falla (error de xarxa o error de parse), el refresh s'atura completament. L'`ofertes.json` existent NO s'actualitza ni s'elimina. L'error es reporta amb detall del PDF fallit.
- **D-02:** No hi ha comportament de "continua amb els altres" ni escritura parcial. Tot o res.

### Cache de PDFs

- **D-03:** **Sense cache** — Cada execució del scraper descarrega els PDFs frescos i els elimina un cop analitzats. No es guarden fitxers PDF al disc entre scrapes. Garanteix dades actualitzades i evita gestió d'invalidació.

### Registres amb Família Desconeguda

- **D-04:** Si el parser no pot assignar família a un registre (header de secció no reconegut), **inclou el registre amb `familia='Desconeguda'`** — cap pèrdua de dades.
- **D-05:** Sempre es genera un **warning als logs** quan es detecta un registre sense família reconeguda. Facilita la detecció de problemes de parsing.
- **D-06:** El registre amb familia='Desconeguda' S'INCLOU a ofertes.json — no es descarta ni s'atura el scraping.

### Estructura del Mòdul Scraper

- **D-07:** **Un únic `fp-cercador/backend/scrapers/pdf_scraper.py`** amb funcions per cada Grado: `parse_grado_a()`, `parse_grado_b()`, `parse_grado_c()`. La lògica compartida (detecció de nivel, plan_antiguo, headers de família) es reutilitza internament.
- **D-08:** **`fp-cercador/backend/scrapers/pipeline.py`** orquestra el pipeline complet: descarrega PDFs → crida pdf_scraper.py → (Fase 3 afegirà html_scraper.py) → escriu ofertes.json. La Fase 4 importarà `pipeline.run()` per llançar el refresh.
- **D-09:** La lògica de refresh NO viu a `app.py`. `app.py` roman com un stub fins a la Fase 4.

### Claude's Discretion

- URLs exactes dels 3 PDFs a todofp.es (a obtenir per l'agent de recerca)
- Valors exactes dels headers `Referer` i `User-Agent` requerits
- Implementació interna del parsing: estratègia de detecció de taules vs text raw amb pdfplumber
- Regex exacta per detectar codis de pla antic (`XXXN0000NN`)
- Tractament de pàgines 1–5 (portada/intro) — skip per número de pàgina o per contingut

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements del projecte
- `.planning/REQUIREMENTS.md` §Scraper PDFs (Grados A, B, C) — PDF-01 a PDF-06 (tots els criteris d'acceptació)
- `.planning/PROJECT.md` §Context — URLs fonts, estructura dels PDFs, volums esperats, headers requerits

### Fase anterior
- `.planning/phases/01-project-setup/01-CONTEXT.md` — Estructura de directoris i paquet scrapers/ establerts (D-01–D-10)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `fp-cercador/backend/scrapers/__init__.py` — Paquet Python existent, importable. Fase 2 hi afegirà `pdf_scraper.py` i `pipeline.py`.
- `fp-cercador/backend/data/ofertes.json` — Fitxer de mostra existent. El pipeline el sobreescriurà en acabar (si tot va bé).

### Established Patterns
- Fail fast: consistent amb D-01 — errors bloquen l'operació i preserven l'estat anterior.
- Sense cache persistent: els artefactes intermedis (PDFs) s'eliminen un cop usats.

### Integration Points
- `fp-cercador/backend/scrapers/pipeline.py` → Fase 4 importa `from scrapers.pipeline import run` per llançar en thread separat
- `fp-cercador/backend/data/ofertes.json` → Fase 4 llegeix per servir `GET /api/ofertes`; Fase 5 consumeix via API

</code_context>

<specifics>
## Specific Ideas

- `pipeline.run()` ha de retornar un resum: `{"total": N, "by_grado": {"A": N, "B": N, "C": N}, "errors": [], "duration_seconds": N}` — la Fase 4 exposarà aquest resum via `GET /api/refresh-status`
- Els warnings de família desconeguda van al mecanisme de logging estàndard de Python (`logging.warning(...)`) — no a stdout/print

</specifics>

<deferred>
## Deferred Ideas

- Scrapers HTML per Grados D i E — Fase 3
- Execució en thread separat i gestió d'estat (idle/running/done/error) — Fase 4
- Endpoint `POST /api/admin/refresh` que crida `pipeline.run()` — Fase 4

</deferred>

---

*Phase: 02-pdf-scrapers-grados-a-b-c*
*Context gathered: 2026-04-16*
