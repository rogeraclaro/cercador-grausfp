# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-16)

**Core value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.
**Current focus:** Phase 1 — Project Setup

## Current Position

Phase: 1 of 6 (Project Setup)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2026-04-16 — Roadmap and state initialized

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Init: JSON estàtic com a "base de dades" (dades quasi-estàtiques, evita complexitat)
- Init: Thread separat per al refresh (pipeline pot trigar 45s+, no bloquejar l'API)
- Init: Frontend vanilla sense frameworks (zero dependències, requisit explícit)
- Init: Nivell deduït del sufix del codi en PDFs (no hi ha columna explícita de nivell)

### Pending Todos

None yet.

### Blockers/Concerns

- PDFs requereixen headers `Referer` i `User-Agent` — cal verificar que todofp.es no canvia la política d'accés durant el desenvolupament.

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-04-16
Stopped at: Roadmap created, ready to plan Phase 1
Resume file: None
