---
slug: fix-scraper-pla-antic-familia-pagina
date: 2026-04-23
status: complete
---

# Resum d'execució

## Canvis realitzats
- `fp-cercador/backend/scrapers/pdf_scraper.py`: nova funció `_get_familia_from_page`,
  lògica de deduplicació per (code_cell, familia_pagina) per codis antics,
  nivell via page_level per a tots els codis antics (A, B, C),
  correcció de syntax error preexistent (parèntesi no tancat a logger.warning).

## Commit
`ee47e35` — fix(scraper): llegir família pla antic del capçal de pàgina del PDF

## Pendent de validació
La funció `_get_familia_from_page` usa una crop box heurística (55% amplada, 100px alçada)
i un regex `Familia\s+Profesional\s*[\n\r]\s*(.+)`. Cal executar el pipeline i verificar
que les famílies resultants per als codis UF/MF coincideixen amb les del PDF.
