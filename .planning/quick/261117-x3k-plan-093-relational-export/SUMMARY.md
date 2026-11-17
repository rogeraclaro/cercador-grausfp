---
quick_id: 261117-x3k
status: complete
date: 2026-11-17
---

# Summary — Plan 093: relational export

- `scripts/generate_c_loe_estructura.py` (pdftotext -layout) → `c_loe_estructura.json`: 564/580 certificates.
- `backend/export_estructura.py` + `GET /api/export/estructura` (certificates LOE/LOMLOE, cycles); tests added; suite 882 passed.
- Buttons in `itinerari.html` and `index.html` (grau C/D filter), ca/es texts, `?v=20261117b`.
- Verified locally (Excel Mac, separator forced, UC join) and in production; found and fixed annex typos (MF0121-2, UF425, «Código MF…»);
  inconsistent hours blanked; 556/580 certificates with structure. Module codes written as text (`="0237"`).
- Deployed 2026-11-17 (prod `f925907`). Not tested: Excel with a ca/es regional setting.
