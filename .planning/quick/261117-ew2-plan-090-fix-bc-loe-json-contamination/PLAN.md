---
quick_id: 261117-ew2
description: "Plan 090: fix bc_loe.json contamination"
date: 2026-11-17
---

# Quick task 261117-ew2 — Plan 090: fix bc_loe.json contamination

Full spec: `fp-cercador/plans/090-corregir-bc-loe-contaminat.md` (owner-approved). Planned and executed
inline by the orchestrator (no planner/executor subagents): the plan already existed and the analysis
context was loaded in the session.

## Tasks

1. Test first: `backend/tests/test_generate_bc_loe.py` — segment cut to the certificate's own annex,
   source selection (annex vs SEPE list), truncated SEPE lists.
2. Rewrite the extraction in `scripts/generate_bc_loe.py`; add `scripts/data/sepe_cp_mf.json`.
3. Regenerate `backend/data/bc_loe.json` (untracked), diff against the previous file, write
   `plans/outputs/audit_bc_loe.md`.
4. Check consumers locally (itinerary, inherited centres) and whether `centres_watch_service` would
   fire alerts.
5. Update `plans/README.md` and `plans/ESTAT.md`. No deploy.

## Deviation from plan 090 (decided while executing)

Codes are derived from the `Código: MF####_N` headings, not the `Código: UC####_N` ones: UC headings are
missed in 82 annexes and carry typos in others (ADGD0210: UC7033_3 for MF1791_3), and every consumer maps
UC→MF by number. The SEPE list is capped at 8 codes per certificate, so it is treated as a prefix when
it has 8.
