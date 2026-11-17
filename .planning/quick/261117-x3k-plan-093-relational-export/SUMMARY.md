---
quick_id: 261117-x3k
status: complete
date: 2026-11-17
---

# Summary — Plan 093: relational export

- `scripts/generate_c_loe_estructura.py` (pdftotext -layout) → `c_loe_estructura.json`: 564/580 certificates.
- `backend/export_estructura.py` + `GET /api/export/estructura` (certificates LOE/LOMLOE, cycles); tests added; suite 882 passed.
- Buttons in `itinerari.html` and `index.html` (grau C/D filter), ca/es texts, `?v=20261117b`.
- Not done: Excel check by hand (phase 5), deploy (needs owner approval + copying the JSON to the VPS).
