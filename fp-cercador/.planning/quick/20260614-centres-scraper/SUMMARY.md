---
status: complete
date: 2026-06-14
commit: ec61fc4
---

# Resum: Scraper de centres (Pla 016 + 016b)

## Entregables

### Pla 016 — centres_scraper.py
- **17.951 centres únics** (vs ~15.000 estimat a l'spike)
- **815 relacions oferta↔centres** (exacte: 584 C LOE + 195 D + 36 E)
- Temps d'execució real: ~18 min (vs ~15 min estimat)
- Mides: `centres.json` 6.9 MB, `oferta_centres.json` 3.3 MB

### Pla 016b — centres_url_enricher.py
- Capa 1 (email domain): **12.191 centres (67.9%)**
- Capa 2 (centrorcd detail): **1.182 centres (36.3% dels RCD candidats)**
- **Cobertura total: 13.373/17.951 (74.5%)**
- Centres sense URL: 4.578 (25.5%) → `url_web: null`

## Decisions tècniques

- Paràmetres correctes: `iDisplayLength` (no `length`) i `ofertaCodigo` (confirmats per inspecció del JS)
- Grado D/E: cerca per `ofertaDenominacion` (denominació completa sense prefix) + `gradoProfesional=4/5`
- Grado E: eliminació prèvia del sufix `(Acceso GM/GS)` per a cerques exitoses
- Clau D/E a `oferta_centres.json`: `str(oferta.id)` intern (ex. `"12664"`)
- Session refresh cada 200 req per evitar caducitat JSESSIONID

## Ampliació 2026-09-06 (Pla 055) — Grado C LOMLOE

- Spike previ: `plans/outputs/spike_centres_abc_results.md`. El mateix endpoint respon
  amb `ofertaCodigo={codi complet FAM_C_NNN_NL}`; A i B no existeixen al registre.
- +397 consultes C LOMLOE (mostra de 25: 16 amb centres). Total ~1.212 consultes, ~20 min.
- Clau a `oferta_centres.json`: `str(oferta.id)` (com D/E) — el frontend ja envia `id=`
  per a tot el que no és C LOE, així que no calen canvis a `index.html`/`perfil.html`.
- Tests: `backend/tests/test_centres_scraper.py` (nou).
- Xifres reals post-scraping a producció: _pendent d'omplir després del primer run_.

## Arxius modificats

- `backend/scrapers/centres_scraper.py` (nou)
- `backend/scrapers/centres_url_enricher.py` (nou)
- `backend/data/centres.json` (generat, a .gitignore)
- `backend/data/oferta_centres.json` (generat, a .gitignore)
