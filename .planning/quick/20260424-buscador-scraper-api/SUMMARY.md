---
slug: buscador-scraper-api
date: 2026-04-24
status: complete
---

# Resum

## Canvis realitzats
- `fp-cercador/backend/scrapers/buscador_scraper.py` (NOU): API REST buscadorgradosfp, 9 GET, `parse_grado(grado)`
- `fp-cercador/backend/scrapers/pipeline.py`: substituït PDF loop per `parse_grado()` per A/B/C
- `fp-cercador/backend/.env`: BUSCADOR_UUID afegit (no al repo)
- `fp-cercador/backend/.env.example`: placeholder BUSCADOR_UUID

## Commits
- `ee47e35` — fix(scraper): llegir família pla antic del capçal (parcialment ineficaç, però corregeix syntax error)
- `9922870` — feat(scraper): substituir PDF scraper A/B/C per API REST del buscador

## Pendent
- Executar `/api/admin/refresh` per regenerar ofertes.json amb les dades correctes
- UUID pot caducar — renovar si el pipeline falla
