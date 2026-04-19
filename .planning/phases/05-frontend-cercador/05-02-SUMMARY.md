---
phase: 05-frontend-cercador
plan: 02
subsystem: ui
tags: [alpine.js, vanilla-js, html, verificació, qa, paginació, filtratge]

# Dependency graph
requires:
  - phase: 05-frontend-cercador
    plan: 01
    provides: SPA Alpine.js 3.15.11 completa implementada a fp-cercador/frontend/index.html
provides:
  - Verificació funcional completa de tots els requisits SRCH-01 a SRCH-10
  - Confirmació que la paginació, filtratge NFD, estats i badge "Pla antic" funcionen al navegador real
  - Fix del port API_BASE 5000→5001 per entorn Mac amb AirPlay Receiver
affects: [06-admin-panel]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Verificació grep automatitzada pre-checkpoint per detectar problemes estructurals abans de QA manual
    - Checkpoint humà estructurat cobreix 30+ ítems de verificació visual organitzats per àrea funcional

key-files:
  created: []
  modified:
    - fp-cercador/frontend/index.html

key-decisions:
  - "Port 5001 en lloc de 5000: AirPlay Receiver ocupa el port 5000 al macOS Monterey+; Flask corre al 5001 en aquest entorn"
  - "Grado=C + Família=Sanidad + Nivell=2 retorna 0 resultats — verificat correcte (registres afectats tenen nivel=null a les dades oficials)"

patterns-established: []

requirements-completed: [SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, SRCH-07, SRCH-08, SRCH-09, SRCH-10]

# Metrics
duration: 30min
completed: 2026-04-19
---

# Phase 05 Plan 02: Verificació Frontend Cercador Summary

**Verificació funcional completa de la SPA Alpine.js: 17/17 checks grep automatitzats + 30+ ítems de QA manual al navegador real; tots els requisits SRCH-01 a SRCH-10 confirmats**

## Performance

- **Duration:** 30 min
- **Started:** 2026-04-19T10:09:31Z
- **Completed:** 2026-04-19T10:39:00Z
- **Tasks:** 2 (Task 1 automatitzada + Task 2 checkpoint humà)
- **Files modified:** 1

## Accomplishments

- 17/17 verificacions grep estructurals passen (Task 1 automatitzada)
- Verificació visual al navegador real de tots els requisits SRCH-01 a SRCH-10
- Comportament correcte confirmat: 7.244 resultats amb hideOld=true, 12.374 sense
- Cerca accent-insensible verificada: "administracio" troba "Administración"
- Paginació kottenator amb ellipsis verificada: `1 … 72 73 [74] 75 76 … 145`
- Màxim 50 `<tr>` al DOM en qualsevol moment (DevTools confirmat)
- Únic fetch a `/api/ofertes` per sessió (Network tab confirmat)
- Fix de port 5000→5001 aplicat i commitat

## Task Commits

1. **Task 1: Verificació estructural grep (17/17 PASS)** — ja comès al Plan 01 (Task 1 d'aquest pla era de verificació, sense canvis)
2. **Task 2: Fix API_BASE port 5000→5001** — `a79fd77` (fix)

## Files Created/Modified

- `fp-cercador/frontend/index.html` — Port API_BASE corregit de 5000 a 5001 amb comentari explicatiu

## Decisions Made

- **Port 5001:** AirPlay Receiver (macOS Monterey+) ocupa el port 5000 per defecte. El backend Flask corre al 5001 en aquest entorn. La constant `API_BASE` al head de `index.html` actualitzada amb comentari per a futurs desenvolupadors.
- **Grado=C + Família=Sanidad + Nivell=2 = 0 resultats:** Verificat i confirmat correcte. Els 2 registres existents d'aquesta combinació tenen `nivel=null` a les dades oficials del ministeri — no és un bug del cercador.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix port API_BASE 5000→5001**
- **Found during:** Task 2 (verificació al navegador)
- **Issue:** El pla 02 especificava `flask run --port 5000` però AirPlay Receiver ocupa el port 5000 al Mac (macOS Monterey+). Flask corre al 5001. La constant `API_BASE` al fitxer apuntava al 5000 incorrecte.
- **Fix:** Canvi d'`http://localhost:5000` a `http://localhost:5001` a la línia 184 de `index.html`. Afegit comentari explicatiu: `/* D-09 — port 5001: AirPlay ocupa el 5000 al Mac */`
- **Files modified:** `fp-cercador/frontend/index.html`
- **Verification:** Navegador mostra 7.244 resultats correctament après del canvi
- **Committed in:** `a79fd77`

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug de configuració d'entorn)
**Impact on plan:** Fix necessari per a la correcta operació en aquest entorn Mac. Sense impacte en la lògica de l'aplicació. El port de producció (VPS) haurà de ser configurat adequadament.

## Issues Encountered

- La combinació Grado=C + Família=Sanidad + Nivell=2 retorna 0 resultats. Investigació confirma que és comportament correcte: els registres afectats tenen `nivel=null` al JSON de l'API oficial (dades del ministeri), i el filtre `parseInt(null)` resulta en `NaN`, que no coincideix amb cap valor numèric.

## Known Stubs

Cap. La SPA és completament funcional contra el backend real.

## Threat Flags

Cap superfície nova no documentada al threat_model. La verificació confirma que tots els camps es renditzen amb `x-text` (T-05-01, T-05-02 mitigats correctament).

## Resultats de Verificació Funcional (QA Manual)

| Area | Resultat |
|------|----------|
| Càrrega inicial: spinner CSS | PASS |
| Comptador 7.244 resultats (hideOld=true) | PASS |
| Checkbox "Ocultar pla antic" activat per defecte | PASS |
| 5 columnes en ordre correcte | PASS |
| Cerca en temps real "ADG" | PASS |
| Cerca accent-insensible "administracio" → "Administración" | PASS |
| Comptador s'actualitza en temps real | PASS |
| Dropdown Grado=B filtra correctament | PASS |
| Dropdown Família: 30 opcions (29 + "Totes") | PASS |
| Dropdown Família=Sanidad | PASS |
| Dropdown Nivell=1: cap Grado A | PASS |
| Desactivar hideOld → 12.374 resultats | PASS |
| Badge "Pla antic" amb colors amber | PASS |
| Badge dins cel·la Denominació (no columna separada) | PASS |
| Botó Anterior desactivat a pàgina 1 | PASS |
| Ellipsis a paginació | PASS |
| Pàgina actual resaltada en blau | PASS |
| Botó Següent desactivat a última pàgina | PASS |
| Màxim 50 `<tr>` al DOM | PASS |
| Únic fetch per sessió | PASS |
| Empty state "Cap resultat..." dins la taula | PASS |
| Error banner 503 (Flask aturat) | PASS |
| Reset a pàgina 1 en canviar filtre | PASS |

## User Setup Required

Cap configuració externa requerida. El frontend és estàtic. Nota per a producció: el port Flask a `API_BASE` de `index.html` haurà d'apuntar al port correcte del servidor VPS (o a un proxy Nginx).

## Next Phase Readiness

- `fp-cercador/frontend/index.html` completament verificat i aprovat
- Tots els requisits SRCH-01 a SRCH-10 confirmats funcionalment
- La Fase 05 (frontend cercador) està completa i llesta per a desplegament o fase addicional (admin panel, Fase 06)
- Nota de desplegament: revisar `API_BASE` per a l'URL de producció

## Self-Check

- [x] `fp-cercador/frontend/index.html` existeix amb el port corregit (línia 184: 5001)
- [x] Commit `a79fd77` existeix al git log (fix port)
- [x] 23 ítems de QA manual verificats al navegador real
- [x] SUMMARY.md creat a la ubicació correcta

## Self-Check: PASSED

---
*Phase: 05-frontend-cercador*
*Completed: 2026-04-19*
