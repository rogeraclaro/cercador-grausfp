---
quick_id: 261117-u6p
status: complete
date: 2026-11-17
---

# Summary — Plan 091: UC ↔ module correspondence from BOE

- `backend/scrapers/boe_corr_scraper.py`, `backend/uc_corr.py`, `scripts/build_d_uc_corr.py`,
  `GET /api/correspondencia` in `backend/app.py`.
- 55 new tests (scraper 34, rule 8, API 13). Backend suite: 852 passed.
- `backend/data/d_uc_corr.json` generated locally (untracked): 182 of 195 D cycles (basic 34/34,
  medium 63/67, higher 85/94); 92 take their table from a later decree. Report:
  `fp-cercador/plans/outputs/audit_d_uc_corr.md`.
- LOE certificates: 442 of 580 have a UC in a table in force (259 all of them); 12 more only in a
  replaced table.
- 13 cycles without a table, each with its reason in the report (pre-UC titles, no UC in the decree,
  annexes published as images).
- Reference case checked through the API: ELEE0109 → 0232, 0238, 0240, 0235, 0236 (replaced table).
- Not deployed. Deploy needs `git pull`, a restart and copying `d_uc_corr.json` to the VPS.
