---
gsd_state_version: "1.0"
milestone: v1.0
current_phase_name: 06
status: executing
stopped_at: context exhaustion at 90% (2026-04-23)
last_updated: "2026-09-24T17:24:39.626Z"
last_activity: 2026-09-24
last_activity_desc: Phase --phase execution started
state_head: 11169cd84a62d08360fbb4cd5425784f07dc984b
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 16
  completed_plans: 15
  percent: 94
milestone_name: milestone
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.
**Current focus:** Phase --phase — 06

## Current Position

Phase: --phase (06) — EXECUTING
Plan: 1 of --name
Status: Executing Phase --phase
Last activity: 2026-09-24 - Completed quick task 260924-s1c: shared site.css

Progress: [█████████░] 94% (Fases 01, 02, 03, 04, 05 completades; 06 pendent)

## Performance Metrics

**Velocity:**

- Total plans completed: 5
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | - | - |
| 04 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-project-setup P01 | 2 | 3 tasks | 6 files |
| Phase 01-project-setup P02 | 3 | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: JSON estàtic com a "base de dades" (dades quasi-estàtiques, evita complexitat)
- Init: Thread separat per al refresh (pipeline pot trigar 45s+, no bloquejar l'API)
- Init: Frontend vanilla sense frameworks (zero dependències, requisit explícit)
- Init: Nivell deduït del sufix del codi en PDFs (no hi ha columna explícita de nivell)
- [Phase 01-project-setup]: app.py stub minim sense rutes: les rutes s'afegiran a la Fase 4
- [Phase 01-project-setup]: requirements.txt sense versions fixes: pip resol les ultimes compatibles
- [Phase 01-project-setup]: .env exclòs del repo (T-01-01); .env.example inclòs amb placeholder segur
- [Phase 01-project-setup]: ofertes.json inclòs al repo (D-09): dades de mostra públiques sense PII ni secrets
- [Phase 01-project-setup]: Stubs HTML sense CSS/JS: tot UI diferit a Fases 5 i 6 per mantenir la fase 1 com a esquelet pur
- [Phase 02-01]: pytest instal·lat com a dep de dev (no al requirements.txt — separat de runtime)
- [Phase 02-01]: T-02-01 implementat: try/except per pàgina a _extract_records (threat model mitigate)
- [Phase 02-01]: REFACTOR omès (codi sense duplicació significativa post-GREEN)
- [Phase 02-02]: pipeline.py independent de Flask (D-09); app.py roman intacte fins a Fase 4
- [Phase 02-02]: REFACTOR omès (implementació directa del pla sense duplicació)
- [Phase 03-02]: Mètode B (headers del <td>) per inferència de família; HTML_FAMILY_ALIASES per 2 anomalies HTML
- [Phase 03-02]: HEADERS duplicat intencionalment a html_scraper.py per evitar dependència circular
- [Phase 03-03]: PREFIX_MAP expandit a 30 entrades (incl. ART, SAN, UF, MF per LOGSE/HTML)
- [Phase 03-03]: DATA-04 actualitzat: 12.374 registres reals (A:8537, B:2786, C:820, D:195, E:36)
- [Phase 03-03]: _build_fam_map accepta alt sense prefix "Logotipo " per Grado E (Inteligencia Artificial y Data)

### Pending Todos

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
| --- | ------------- | ------ | -------- | -------- | ----------- |
| 260419-wm | Descripció: Preparar deploy VPS Contabo + CloudPanel (gunicorn, systemd, nginx, API_BASE dinàmica) · Data: 2026-04-19 · Directori: [260419-wm-deploy-vps-contabo-cloudpanel](.planning/quick/260419-wm-deploy-vps-contabo-cloudpanel/) | — | 43267db | — | — |
| 260419-b3 | Descripció: Ordenació tri-estat per click a capçaleres Denominació i Codi de la taula de resultats · Data: 2026-04-19 · Directori: [260419-b3-ordenacio-columnes-taula](.planning/quick/260419-b3-ordenacio-columnes-taula/) | — | 1206227 | — | — |
| 260923-x1s | Corregeix la definició dels graus A–E (LO 3/2022) a Per què GrausFP i Fonts | 2026-09-23 | 584ba22 | — | [260923-x1s-fix-grade-a-e-descriptions-lo-3-2022-on-](./quick/260923-x1s-fix-grade-a-e-descriptions-lo-3-2022-on-/) |
| 260923-x98 | Colorize index.html: paleta càlida amb tokens, contrast AA, fora el blau | 2026-09-23 | 9e45914 | — | [260923-x98-colorize-index-html-warm-palette-tokens-](./quick/260923-x98-colorize-index-html-warm-palette-tokens-/) |
| 260924-09g | Harden index.html: teclat, favorits tàctils, main, paginació, plurals, reintent d'error | 2026-09-23 | b02419f | — | [260924-09g-harden-index-html-keyboard-rows-fav-a11y](./quick/260924-09g-harden-index-html-keyboard-rows-fav-a11y/) |
| 260924-0s3 | Adapt index.html mòbil: taula en targetes, barra superior, modes apilats, àrees tàctils 44px | 2026-09-23 | c81afab | — | [260924-0s3-adapt-index-html-for-mobile-table-to-car](./quick/260924-0s3-adapt-index-html-for-mobile-table-to-car/) |
| 260924-1rf | Typeset index.html: escala tipogràfica per rols, fora 7,6px, zoom iOS, fonts | 2026-09-24 | 6db9f1c | — | [260924-1rf-typeset-index-html-role-type-scale-token](./quick/260924-1rf-typeset-index-html-role-type-scale-token/) |
| 260924-d86 | Clarify: missatges de cap resultat (taula, ocupació, FPO) | 2026-09-24 | 89ed384 | — | [260924-d86-clarify-empty-state-copy-in-index-html](./quick/260924-d86-clarify-empty-state-copy-in-index-html/) |
| 260924-p1s | Polish index.html: targetes, filtres FPO mòbil, 44px, icones SVG | 2026-09-24 | b27a8c3 | — | [260924-p1s-polish-index-html](./quick/260924-p1s-polish-index-html/) |
| 260924-s1c | site.css compartit: tokens i barra superior a 13 pàgines | 2026-09-24 | 11169cd | — | [260924-s1c-shared-site-css](./quick/260924-s1c-shared-site-css/) |

### Blockers/Concerns

- PDFs requereixen headers `Referer` i `User-Agent` — cal verificar que todofp.es no canvia la política d'accés durant el desenvolupament.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-23T22:28:49.653Z
Stopped at: context exhaustion at 90% (2026-04-23)
Resume file: None

**Planned Phase:** 06 (Frontend — Admin Panel) — 3 plans — 2026-04-25T22:25:59.909Z
