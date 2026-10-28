---
gsd_state_version: "1.0"
milestone: v1.0
current_phase: 2
current_phase_name: PDF Scrapers (Grados A, B, C)
status: verifying
stopped_at: Phase 7 complete, ready to verify Phase 2
last_updated: "2026-10-28T20:08:45.266Z"
last_activity: 2026-10-28
last_activity_desc: Phase 7 complete, transitioned to Phase 2
state_head: 00c4877097abc78a0d6361abb5ce84306e46823f
progress:
  total_phases: 7
  completed_phases: 5
  total_plans: 19
  completed_plans: 18
  percent: 71
milestone_name: milestone
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.
**Current focus:** Phase 07 — Microanimacions GSAP

## Current Position

Phase: 2 — PDF Scrapers (Grados A, B, C)
Plan: 3
Status: Phase complete — ready for verification
Last activity: 2026-10-28 — Phase 7 complete, transitioned to Phase 2

Progress: [███████░░░] 71% (Fases 01, 02, 03, 04, 05 completades; 06 pendent)

## Performance Metrics

**Velocity:**

- Total plans completed: 8
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | - | - |
| 04 | 3 | - | - |
| 7 | 3 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-project-setup P01 | 2 | 3 tasks | 6 files |
| Phase 01-project-setup P02 | 3 | 2 tasks | 4 files |
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 07 P01 | multi-session | 5 tasks | 7 files |
| Phase 07 P02 | multi-session | 3 tasks | 3 files |
| Phase 07 P03 | multi-session | 4 tasks | 3 files |

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
- [Phase 07]: GSAP license: owner chose vendor-3142 (vendored GSAP 3.14.2 core, no CDN, no plugins) on 2026-10-28
- [Phase 07]: 07-02: observatori bars animate with scaleX in 410 ms; count-up goes through an aria-hidden copy so accessible text stays final; hero total untouched
- [Phase 07]: 07-03: itinerari timeline lines draw via pathLength=1 + dashoffset (no DrawSVG); dashed/dotted C->D links through userSpaceOnUse mask; stops light green in sequence (D-13/D-14)
- [Phase 07]: 07-03: deployed to production after explicit owner approval (D-16); Safari/Firefox result not reported by owner, clip-path fallback unused

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
| 260924-s2p | Subpàgines: tabs perfil, gràfic Observatori, main, badge privacitat, colors missatge | 2026-09-24 | 96837fe | — | [260924-s2p-subpages-specific-fixes](./quick/260924-s2p-subpages-specific-fixes/) |
| 260924-s3i | index.html usa site.css (renderitzat idèntic) | 2026-09-24 | 5a8faac | — | [260924-s3i-index-uses-site-css](./quick/260924-s3i-index-uses-site-css/) |
| 13 | fix(i18n): graus i ensenyaments al català de per-que-grausfp | 2026-09-25 | 92afc11 | — | — |

### Blockers/Concerns

- PDFs requereixen headers `Referer` i `User-Agent` — cal verificar que todofp.es no canvia la política d'accés durant el desenvolupament.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-10-28T18:44:15.686Z
Stopped at: Phase 7 complete, ready to verify Phase 2
Resume file: None

**Planned Phase:** 06 (Frontend — Admin Panel) — 3 plans — 2026-04-25T22:25:59.909Z
