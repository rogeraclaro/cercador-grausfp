---
phase: 05-frontend-cercador
plan: 01
subsystem: ui
tags: [alpine.js, vanilla-js, html, css, paginació, filtratge, cercador]

# Dependency graph
requires:
  - phase: 04-backend
    provides: GET /api/ofertes retornant array JSON de 12.374 registres FP amb camps id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones
provides:
  - SPA cercador completa en fp-cercador/frontend/index.html amb Alpine.js 3.15.11
  - Filtratge en memòria per text (NFD), Grado, Família, Nivell, pla antic
  - Paginació kottenator amb ellipsis (50 resultats/pàgina)
  - Estats loading/error/buit reactius
affects: [05-frontend-cercador-plan-02, 06-admin-panel]

# Tech tracking
tech-stack:
  added: [Alpine.js 3.15.11 via CDN jsDelivr]
  patterns:
    - Alpine.data component declarat a alpine:init listener (script propi AVANT CDN tag)
    - Pre-normalització NFD a allRecords._normDen i _normCod al init() per cerca eficient
    - Filtratge 100% en memòria (cap crida API addicional)
    - DOM limitat a 50 <tr> actius via slice(start, start + pageSize)
    - Getters computats (filteredRecords, pagedRecords, totalPages, filteredCount)

key-files:
  created: []
  modified:
    - fp-cercador/frontend/index.html

key-decisions:
  - "Alpine.js 3.15.11 via CDN jsDelivr sense SRI hash (T-05-03 acceptat: risc baix, cerca pública sense auth)"
  - "Script propi (alpine:init) sempre AVANT del tag CDN Alpine per evitar race condition (Pitfall 5)"
  - "Pre-normalització NFD al init() sobre allRecords per evitar normalitzar a cada keystroke"
  - "x-text exclusivament per a tots els camps JSON (mai x-html) — mitigació T-05-01, T-05-02"
  - "hideOld: true per defecte (SRCH-05) — mostra 7.244 dels 12.374 registres inicials"
  - "filterNivel usa parseInt() per comparar amb r.nivel que és number al JSON (Pitfall 2)"
  - "URL API: http://localhost:5000 constant API_BASE al head (D-09)"

patterns-established:
  - "Alpine component declarat via Alpine.data() dins alpine:init event, no x-data inline complex"
  - "Paginació kottenator amb delta=2: always show first, last, current±2, amb ellipsis entre gaps"
  - "Getters JS purs (no efectes secundaris) per filteredRecords i pagedRecords"

requirements-completed: [SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, SRCH-07, SRCH-08, SRCH-09, SRCH-10]

# Metrics
duration: 12min
completed: 2026-04-19
---

# Phase 05 Plan 01: Frontend Cercador Summary

**SPA Alpine.js 3.15.11 amb filtratge NFD en memòria, paginació kottenator 50/pàg i estats reactius loading/error/buit sobre 12.374 registres FP**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-19T09:57:00Z
- **Completed:** 2026-04-19T10:09:31Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Stub de 10 línies substituït per SPA completa de 406 línies amb tota la lògica inline
- 24/24 criteris d'acceptació verificats automaticament (python script)
- Pre-normalització NFD a init() elimina el cost de normalitzar a cada filtratge
- Paginació kottenator amb ellipsis: `1 … 4 [5] 6 … 247` per a grans conjunts de dades

## Task Commits

1. **Task 1: HTML skeleton + API_BASE + Alpine.js + CSS inline** - `7a5047f` (feat)

## Files Created/Modified

- `fp-cercador/frontend/index.html` - SPA completa: HTML + CSS inline + JS Alpine.js (406 línies)

## Decisions Made

- Script propi (alpine:init) declarat AVANT del tag CDN Alpine.js al head — evita race condition on Alpine no esta disponible quan el script intenta registrar el component
- Pre-normalització NFD guardada a `_normDen` i `_normCod` a cada registre durant el `init()`, no al getter, per evitar normalitzar 12.374 × N cops a cada keystroke
- `parseInt(this.filterNivel)` per comparar amb `r.nivel` que és number al JSON — evita que "1" !== 1 filtri tots els registres (Pitfall 2 del RESEARCH.md)
- Emoji ⚠️ codificat com a entitats HTML numèriques (`&#9888;&#65039;`) per robustesa en encoding

## Deviations from Plan

Cap — el pla incloïa el codi complet a implementar. Executat exactament com especificat.

## Issues Encountered

Cap. RTK (proxy) interpreta alguns flags grep (-n) diferent, verificació final feta amb python3 directament per garantir resultats fiables.

## Known Stubs

Cap. Totes les dades provenen de l'API real (`fetch(API_BASE + '/api/ofertes')`). No hi ha dades hardcoded ni placeholders funcionals.

## Threat Flags

Cap superfície nova no documentada al threat_model del pla. Tots els camps renderitzats amb `x-text` (T-05-01, T-05-02 mitigats). CDN sense SRI acceptat com T-05-03.

## User Setup Required

Cap. El frontend és estàtic i es connecta a Flask al port 5000. Flask ha d'estar en marxa per veure dades.

## Next Phase Readiness

- `fp-cercador/frontend/index.html` llest per a verificació visual al browser
- El backend Flask (Fase 4) ha d'estar en marxa a `http://localhost:5000` per testejar
- Pla 02 (si existeix) pot afegir funcionalitats addicionals sobre aquesta base

## Self-Check

- [x] `fp-cercador/frontend/index.html` existeix i té 406 línies
- [x] Commit `7a5047f` existeix al git log
- [x] 24/24 criteris d'acceptació verificats (python3)
- [x] Cap modificació a STATE.md ni ROADMAP.md

## Self-Check: PASSED

---
*Phase: 05-frontend-cercador*
*Completed: 2026-04-19*
