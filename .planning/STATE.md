---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: context exhaustion at 90% (2026-04-19)
last_updated: "2026-04-19T11:31:53.629Z"
last_activity: 2026-04-19
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 13
  completed_plans: 13
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.
**Current focus:** Phase 06 — admin-panel

## Current Position

Phase: 5
Plan: Complete
Status: Phase 05 completada (2026-04-19) — 2/2 plans, verificació aprovada
Last activity: 2026-04-19

Progress: [█████████░] 83% (Fases 01, 02, 03, 04, 05 completades; 06 pendent)

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

| # | Descripció | Data | Commit | Directori |
|---|------------|------|--------|-----------|
| 260419-wm | Preparar deploy VPS Contabo + CloudPanel (gunicorn, systemd, nginx, API_BASE dinàmica) | 2026-04-19 | 43267db | [260419-wm-deploy-vps-contabo-cloudpanel](.planning/quick/260419-wm-deploy-vps-contabo-cloudpanel/) |

### Blockers/Concerns

- PDFs requereixen headers `Referer` i `User-Agent` — cal verificar que todofp.es no canvia la política d'accés durant el desenvolupament.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-19T11:31:53.623Z
Stopped at: context exhaustion at 90% (2026-04-19)
Resume file: None
