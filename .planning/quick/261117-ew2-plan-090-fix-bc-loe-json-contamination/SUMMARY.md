---
quick_id: 261117-ew2
status: complete
date: 2026-11-17
---

# Summary — Plan 090: fix bc_loe.json contamination

- `scripts/generate_bc_loe.py`: reads only the certificate's own annex segment, takes codes from the
  `Código: MF####_N` headings, checks them against `scripts/data/sepe_cp_mf.json` and falls back to that
  list for scanned or incomplete annexes. `--cache DIR` added; `--dry-run` no longer overwrites the file.
- `backend/tests/test_generate_bc_loe.py`: 12 tests. Backend suite: 666 passed.
- `backend/data/bc_loe.json` regenerated locally (untracked): 140 certificates lose 399 foreign UCs,
  6 gain 15. Report: `fp-cercador/plans/outputs/audit_bc_loe.md`.
- Checked locally through `/api/itinerari` (ELEM0311, ELEM0411, MF1975_2, MAPU0112).
- Production has 4 active centre watches, none on a LOE module: the fix sends no email.
- Not deployed. Deploy needs `git pull` plus copying `bc_loe.json` to the VPS.
