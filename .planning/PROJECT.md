# Cercador FP España

## What This Is

Aplicació web per cercar l'oferta formativa completa del Sistema de Formació Professional espanyol (Llei Orgànica 3/2022), cobrint els Grados A, B, C, D i E. Consta d'un backend Flask (Python) que extreu dades de PDFs oficials i scraping HTML del ministeri, i un frontend estàtic (HTML/CSS/JS vanilla) amb cerca en temps real. Es desplegarà en un VPS amb CloudPanel (Ubuntu 24.04).

## Core Value

Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.

## Requirements

### Validated

(Cap encara — ship per validar)

### Active

- [ ] Scraper de PDFs per als Grados A, B, C (pdfplumber) amb detecció de família, nivell i pla antic
- [ ] Scraper HTML per als Grados D (Básico, Medio, Superior) i E (Cursos d'Especialització)
- [ ] Generació de `data/ofertes.json` amb el schema definit (id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones)
- [ ] API Flask amb endpoints: GET /api/ofertes, POST /api/admin/refresh (protegit per token), GET /api/refresh-status, GET /health
- [ ] Execució del refresh en thread separat (no bloquejant), amb estat idle/running/done/error
- [ ] Frontend estàtic sense dependències externes amb cerca en temps real (filtre simultani per text, grado, família, nivell, pla antic)
- [ ] Taula de resultats amb comptador dinàmic, badge "Pla antic" i scroll vertical (fins a 1.500 registres fluïts)
- [ ] Panell admin al client: input token + polling d'estat cada 3s + resum final
- [ ] CORS habilitat, ADMIN_TOKEN via .env, .gitignore correcte

### Out of Scope

- Paginació al frontend — el disseny és scroll vertical complet fins a ~1.500 registres
- Autenticació d'usuari final — el cercador és públic; only the admin endpoint is protected
- Base de dades — les dades es serveixen des d'un fitxer JSON estàtic
- Frameworks frontend (Bootstrap, React, Vue, jQuery) — vanilla pur per simplicitat i zero dependències
- Persistència del token admin al client — s'esborra en tancar el panell
- Scraping de detalls individuals per títol — només llistats agregats
- Multilingüe — la interfície és en català/castellà com les dades originals

## Context

- **Font de dades:** 3 PDFs oficials del Ministeri (todofp.es) per als Grados A/B/C + 4 pàgines HTML per als Grados D/E
- **Extracció PDFs:** text natiu (no escanejat), llegible amb pdfplumber. Taules amb columnes Código/Denominación/Observaciones agrupades per família i nivell (deduïble del sufix del codi: `_3B`→N1, `_4B`→N2, `_5B`→N3)
- **Extracció HTML:** elements amb atribut `id="tit-*"`, família inferida de capçaleres de secció
- **Volum esperat:** ~850 registres totals (A: ~120, B: ~200, C: ~380, D: ~150, E: ~36)
- **Desplegament:** VPS Ubuntu 24.04 amb CloudPanel; Flask serveix l'API, el frontend és estàtic
- **Codis pla antic:** format `XXXN0000NN` o ` (Plan antiguo)` a Observaciones → `plan_antiguo: true`

## Constraints

- **Tech Stack**: Flask + HTML/CSS/JS vanilla — sense frameworks frontend; requisit explícit del propietari
- **Dependencies**: pdfplumber, requests, beautifulsoup4, flask-cors, python-dotenv — cap altra
- **PDFs**: requereixen headers `Referer` i `User-Agent` per descarregar des de todofp.es
- **Rendiment**: el cercador ha de ser fluid fins a 1.500 registres sense paginació
- **Seguretat**: ADMIN_TOKEN NO al repositori; .env a .gitignore

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| JSON estàtic com a "base de dades" | Dades canvien molt poc (actualizació manual via admin); evita complexitat innecessària | — Pending |
| Thread separat per al refresh | No bloquejar l'API durant scraping (pot trigar 45s+) | — Pending |
| Frontend vanilla sense frameworks | Zero dependències, màxima portabilitat, requisit explícit | — Pending |
| Nivell deduït del sufix del codi (PDFs) | El PDF no té columna nivell explícita; el sufix és l'única font | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 after initialization*
