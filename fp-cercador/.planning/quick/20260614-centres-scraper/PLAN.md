---
slug: centres-scraper
date: 2026-06-14
status: in-progress
---

# Quick Task: Scraper de centres (Pla 016 + 016b)

## Resultat del scraping (completat)

- `centres.json`: **17.951 centres únics** (vs ~15.000 estimat)
- `oferta_centres.json`: **815 relacions oferta↔centres**
- Mides: 6.9 MB + 3.3 MB
- Temps d'execució: ~18 min (584 C LOE + 195 D + 36 E, 1 req/s)

## 016b url_web (en curs)

- Capa 1 (email domain): **12.191/17.951 (67.9%)** ← completat
- Capa 2 (centrorcd): 3.260 candidats RCD ← en background (~54 min)

## Commit

`ec61fc4` — feat(backend): scraper de centres (Pla 016) + enriquiment url_web (016b)

## Tasks

- [x] Crear `centres_scraper.py` amb bootstrap, fetch i parsejat
- [x] Testejar amb mostres reals (3 C LOE, 3 D, 3 E)
- [x] Executar pipeline complet: 17.951 centres, 815 ofertes
- [x] Crear `centres_url_enricher.py` (Capa 1 + Capa 2)
- [x] Capa 1: 67.9% cobertura
- [ ] Capa 2: en execució (finalitzarà ~18:58)
- [ ] Commit final amb SUMMARY.md
