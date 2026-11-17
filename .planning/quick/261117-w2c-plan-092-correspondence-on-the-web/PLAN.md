---
quick_id: 261117-w2c
description: "Plan 092: certificate ↔ cycle module correspondence on the web"
date: 2026-11-17
---

# Quick task 261117-w2c — Plan 092: correspondence on the web

Full spec: `fp-cercador/plans/092-correspondencia-a-la-web.md` (owner-approved; repealed tables are shown,
clearly marked — owner decision of 2026-11-17). Planned and executed inline by the orchestrator, in the
same session as plan 091.

## Tasks

1. Backend: BOE correspondence on the C→D edges of `/api/itinerari/complet`, certificates per UC and
   remaining modules in `/api/correspondencia`, `convalidacions` in `/api/que-em-falta`, with tests.
2. `itinerari.html`: pills, legend and detail blocks for a LOE certificate and for a cycle.
3. Public cycle page (`grau_page.py`).
4. `que-em-falta.html`: «Convalidacions oficials» section.
5. Texts (ca/es), `i18n.js?v=`, browser check, plan docs. No deploy.

## Deviations from plan 092 (decided while executing)

- «Què em falta?» keeps `objectius` untouched (STOP rule); the official convalidations are a separate
  section instead of being merged into the percentage targets.
- When someone holds old and new UC codes of the same cycle, both the table in force and the repealed
  one are returned (`uc_corr.cycles_for_ucs`), instead of the repealed one being hidden.
- The cycle table lists UC → modules they convalidate (annex V A) rather than annex V B.
