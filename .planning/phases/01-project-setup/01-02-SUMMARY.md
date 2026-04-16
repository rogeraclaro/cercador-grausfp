---
phase: 01-project-setup
plan: 02
subsystem: frontend-stubs, sample-data, docs
tags: [html, json, readme, stub, scaffold]
dependency_graph:
  requires: [01-01]
  provides: [frontend-stub, sample-data, project-readme]
  affects: [phase-05-frontend, phase-06-admin]
tech_stack:
  added: []
  patterns: [html5-stub, json-schema-data01]
key_files:
  created:
    - fp-cercador/frontend/index.html
    - fp-cercador/frontend/admin.html
    - fp-cercador/backend/data/ofertes.json
    - fp-cercador/README.md
  modified: []
decisions:
  - "ofertes.json inclòs al repo (D-09): dades de mostra públiques, no secrets"
  - "Stubs HTML sense cap CSS/JS: tot diferit a Fases 5 i 6"
  - ".gitkeep eliminat de backend/data/ un cop ofertes.json ocupa el directori"
metrics:
  duration: "2 minutes"
  completed_date: "2026-04-16T20:32:22Z"
  tasks_completed: 2
  files_created: 4
---

# Phase 01 Plan 02: Frontend stubs, sample data and README Summary

**One-liner:** HTML stubs with lang="ca" for Phases 5/6, 7-record ofertes.json covering all 5 Grados with DATA-01 schema, and minimal 4-step setup README.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Crear stubs HTML del frontend | 219ac2c | fp-cercador/frontend/index.html, fp-cercador/frontend/admin.html |
| 2 | Crear ofertes.json (mostra) i README.md | e4db3a6 | fp-cercador/backend/data/ofertes.json, fp-cercador/README.md |

## What Was Built

**4 files created:**

1. `fp-cercador/frontend/index.html` — Stub HTML5 vàlid per al cercador. Conté `lang="ca"`, `charset="UTF-8"` i comentari `<!-- TODO: Phase 5 -->`. Cap CSS ni JS.

2. `fp-cercador/frontend/admin.html` — Stub HTML5 vàlid per al panell d'administració. Conté `lang="ca"`, `charset="UTF-8"` i comentari `<!-- TODO: Phase 6 -->`. Cap CSS ni JS.

3. `fp-cercador/backend/data/ofertes.json` — Array JSON amb 7 registres de mostra que cobreixen els 5 Grados (A, B, C, D×3, E). Segueix el schema DATA-01 exacte (8 camps per registre). Valors especials respectats: Grado C id=3 amb `plan_antiguo: true`; Grado D id=4,5,6 amb `codigo: null`; Grado E id=7 amb `nivel: null` i `codigo: null`.

4. `fp-cercador/README.md` — Document mínim de setup amb 4 passos numerats (D-08): `cp .env.example`, assignar `ADMIN_TOKEN`, `pip install`, `python app.py`. Cap secció addicional.

**Eliminat:** `fp-cercador/backend/data/.gitkeep` (substituït per ofertes.json).

## Verification Results

All smoke tests passed:
- frontend/ directory exists with both HTML stubs
- Both HTML files: `lang="ca"`, `charset="UTF-8"`, `DOCTYPE html`, correct TODO phase comments
- No `<script>`, `<link>` nor `<style>` in any HTML file
- ofertes.json: 7 records, all 5 Grados present, schema matches DATA-01 exactly
- README.md: contains `ADMIN_TOKEN`, `.env.example`, `pip install -r backend/requirements.txt`, `python app.py`
- Phase 1 global verification (Plans 01+02): all 9 expected files present, 6 deps in requirements.txt, .env in .gitignore

## Decisions Made

- **D-09 respected:** `ofertes.json` is committed to the repository. Data is public (FP course titles), no PII or secrets.
- **Stubs-only policy:** Both HTML files contain zero CSS, JS, links or scripts. All UI work deferred to Phases 5 and 6 as per plan constraints.
- **.gitkeep removal:** Now that `ofertes.json` occupies `backend/data/`, the `.gitkeep` placeholder was removed to keep the repository clean.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

The following files are intentional stubs (by plan design):

| File | Stub Type | Resolved By |
|------|-----------|-------------|
| fp-cercador/frontend/index.html | Empty HTML, no UI logic | Phase 5 |
| fp-cercador/frontend/admin.html | Empty HTML, no UI logic | Phase 6 |
| fp-cercador/backend/data/ofertes.json | Sample data (7 records), not scraped data | Phase 3 (scraping pipeline) |

These stubs are intentional and do NOT prevent this plan's goal (skeleton completion). The frontend UI and real data will be wired in later phases.

## Threat Flags

No new security-relevant surface introduced. All STRIDE threats assessed as `accept` or `mitigate` per plan threat model. README instructs users to assign a secure value to `ADMIN_TOKEN` (step 2), fulfilling T-02-04 mitigation.

## Self-Check: PASSED
