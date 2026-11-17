---
quick_id: 261117-u6p
description: "Plan 091: UC ↔ professional module correspondence from BOE (data + API)"
date: 2026-11-17
---

# Quick task 261117-u6p — Plan 091: UC ↔ module correspondence from BOE

Full spec: `fp-cercador/plans/091-correspondencia-uc-moduls-boe-dades.md` (owner-approved). Planned and
executed inline by the orchestrator (no planner/executor subagents): the plan already existed.

## Tasks

1. `backend/scrapers/boe_corr_scraper.py`: pure reader of the BOE open XML (tables A/B, notes, which
   decree and annex each table targets) and resolution of the tables in force for a title.
2. Tests with real BOE fragments as fixtures (`backend/tests/fixtures/boe_corr/`).
3. `scripts/build_d_uc_corr.py`: download with cache, write `backend/data/d_uc_corr.json` (untracked) and
   `plans/outputs/audit_d_uc_corr.md`; review the cycles left without a table.
4. `backend/uc_corr.py` (calculation rule) and `GET /api/correspondencia?cicle=|cp=`, with tests.
5. Update `plans/README.md` and `plans/ESTAT.md`. No deploy.

## Deviations from plan 091 (decided while executing)

- The 2024 decrees renumber the UCs, so the reference case (ELEE0109) no longer matches the table in
  force. The index keeps the replaced table as `convalida_anterior` and the API falls back to it, flagged
  `derogada`, only when no UC of the certificate is in the table in force.
- The 2023 «actualización» decrees also replace annexes; they are applied like RD 498–500/2024.
- Table kind is taken from the data, not the header (RD 1691/2007 prints the wrong header).
- `d_modulos.json` is not rewritten; module numbers are filled at read time by the API only.
