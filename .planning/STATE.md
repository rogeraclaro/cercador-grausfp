---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: Phase 2 context gathered
last_updated: "2026-04-16T21:03:08.966Z"
last_activity: 2026-04-16
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.
**Current focus:** Phase 01 — project-setup

## Current Position

Phase: 2
Plan: Not started
Status: Phase complete — ready for verification
Last activity: 2026-04-16

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 2
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 2 | - | - |

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

### Pending Todos

None yet.

### Blockers/Concerns

- PDFs requereixen headers `Referer` i `User-Agent` — cal verificar que todofp.es no canvia la política d'accés durant el desenvolupament.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-16T21:03:08.958Z
Stopped at: Phase 2 context gathered
Resume file: .planning/phases/02-pdf-scrapers-grados-a-b-c/02-CONTEXT.md
