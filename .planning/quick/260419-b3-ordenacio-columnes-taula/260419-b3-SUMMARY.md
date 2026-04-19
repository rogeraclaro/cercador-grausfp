---
phase: quick
plan: 260419-b3
subsystem: frontend
tags: [sorting, table, alpine, ux]
dependency_graph:
  requires: []
  provides: [column-sort-denominacio, column-sort-codi]
  affects: [fp-cercador/frontend/index.html]
tech_stack:
  added: []
  patterns: [tri-state sort cycle, Alpine reactive sort]
key_files:
  created: []
  modified:
    - fp-cercador/frontend/index.html
decisions:
  - Tri-estat (A→Z → Z→A → original) implementat via sortDir: 0/1/-1 sense estat addicional
  - Sort aplicat sobre el resultat filtrat (no sobre allRecords) per coherència amb paginació
metrics:
  duration: "5min"
  completed: "2026-04-19T16:21:26Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase quick Plan 260419-b3: Ordenació Columnes Taula Summary

**One-liner:** Ordenació tri-estat per click a capçaleres Denominació i Codi amb indicador visual ▲/▼/⇅ i reset de paginació.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Afegir estat d'ordenació i getter ordenat al component Alpine | 364f12b | fp-cercador/frontend/index.html |
| 2 | Fer clicables les capçaleres Denominació i Codi amb indicador visual | 1206227 | fp-cercador/frontend/index.html |

## What Was Built

- Propietats `sortCol: ''` i `sortDir: 0` afegides al component Alpine cercador
- Mètode `sortBy(col)` amb cicle tri-estat: primer click A→Z (dir=1), segon Z→A (dir=-1), tercer restaura original (dir=0)
- getter `filteredRecords` modificat per aplicar `Array.sort` condicionalment sobre el resultat filtrat
- CSS per a `.sortable`, `.sort-active`, `.sort-indicator` inserit just abans del tancament `</style>`
- Capçaleres Denominació i Codi actualitzades amb `@click`, `:class`, `:aria-sort` i `<span x-text>` per a l'indicador
- Capçaleres Família, Grado i Nivell no modificades

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None - canvis estrictament al costat del client, sense nous endpoints ni superfície de xarxa.

## Self-Check: PASSED

- `364f12b` present a git log
- `1206227` present a git log
- `fp-cercador/frontend/index.html` modificat en ambdós commits
- Verificació del pla: `grep -c "sortBy|sortCol|sortDir"` retorna 19 (≥6); `grep -c "sortable|sort-indicator"` retorna 8 (≥4)
