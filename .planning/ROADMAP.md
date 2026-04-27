# Roadmap: Cercador FP España

## Overview

Six phases that take the project from empty directory to a deployed, fully-functional FP catalog searcher. The work flows naturally: scaffold the project, build the two scraper families (PDF then HTML), consolidate into a JSON data pipeline, expose it via Flask API, build the search frontend, and finish with the admin panel. Each phase delivers something verifiable before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Project Setup** - Scaffold directory structure, dependencies, and config files (completed 2026-04-16)
- [ ] **Phase 2: PDF Scrapers (Grados A, B, C)** - Download and parse the 3 official PDFs into structured records
- [ ] **Phase 3: HTML Scrapers + Data Pipeline (Grados D, E)** - Scrape ministry HTML pages and consolidate all data into ofertes.json
- [ ] **Phase 4: Flask API** - Expose the data via REST endpoints with async refresh and token-protected admin
- [x] **Phase 5: Frontend — Cercador** - Static search UI with real-time filtering across all 5 Grados (completed 2026-04-19)
- [ ] **Phase 6: Frontend — Admin Panel** - Admin token panel with refresh trigger and live status polling

## Phase Details

### Phase 1: Project Setup
**Goal**: The project has a working skeleton that any developer can clone, install, and run
**Depends on**: Nothing (first phase)
**Requirements**: PROJ-01, PROJ-02, PROJ-03
**Success Criteria** (what must be TRUE):
  1. Directory structure `fp-cercador/backend/` and `fp-cercador/frontend/` exists with all required files in place
  2. Running `pip install -r requirements.txt` installs all 6 declared dependencies without errors
  3. `.gitignore` correctly excludes `.env`, Python cache files, and optionally `data/ofertes.json`
  4. A `.env.example` or README makes it clear how to configure `ADMIN_TOKEN`
**Plans**: 2 plans
Plans:
- [x] 01-01-PLAN.md — Backend scaffold: app.py stub, requirements.txt, .env.example, .gitignore, scrapers/__init__.py
- [x] 01-02-PLAN.md — Frontend stubs i dades: index.html, admin.html, ofertes.json (mostra), README.md

### Phase 2: PDF Scrapers (Grados A, B, C)
**Goal**: The three official PDFs from todofp.es are downloaded and parsed into clean structured records
**Depends on**: Phase 1
**Requirements**: PDF-01, PDF-02, PDF-03, PDF-04, PDF-05, PDF-06
**Success Criteria** (what must be TRUE):
  1. Running the scraper downloads all 3 PDFs using the required `Referer` and `User-Agent` headers
  2. Pages 1–5 (cover and intro) are skipped; only catalog data rows are extracted
  3. Each record has the correct `familia`, `codigo`, `denominacion`, and `observaciones` fields
  4. `nivel` is correctly derived from the code suffix (`_3B`→1, `_4B`→2, `_5B`→3) for every record
  5. Records with old-plan codes (`XXXN0000NN` format) or "(Plan antiguo)" in observations have `plan_antiguo: true`
**Plans**: 3 plans
Plans:
- [x] 02-01-PLAN.md — pdf_scraper.py (TDD): parse_grado_a/b/c, PREFIX_MAP, nivel i plan_antiguo amb suite de tests
- [x] 02-02-PLAN.md — pipeline.py: descàrrega PDFs, orquestració, escriptura atòmica ofertes.json
- [x] 02-03-PLAN.md — Execució real contra todofp.es + checkpoint de verificació de volum i estructura

### Phase 3: HTML Scrapers + Data Pipeline (Grados D, E) ✓ Complete (2026-04-18)
**Goal**: Grados D and E are scraped from ministry HTML pages and all 5 Grados are consolidated into a single ofertes.json
**Depends on**: Phase 2
**Requirements**: HTML-01, HTML-02, HTML-03, HTML-04, HTML-05, HTML-06, DATA-01, DATA-02, DATA-03, DATA-04
**Status**: Complete — 10/10 must-haves verified
**Success Criteria** (what must be TRUE):
  1. All Grado D titles (Básico, Medio, Superior) are extracted from the 3 HTML URLs via `id="tit-*"` elements
  2. All Grado E titles (Cursos d'Especialització) are extracted from the correct URL
  3. Family is correctly inferred from section headings for every D/E record
  4. `backend/data/ofertes.json` is generated with the full schema: id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones
  5. The file contains 12,374 total records (updated from 800–900 initial estimate) with unique, sequential IDs spanning all 5 Grados
**Plans**: 3 plans
Plans:
- [x] 03-01-PLAN.md — Tests RED: fixtures HTML + test_html_scraper.py + .env.example
- [x] 03-02-PLAN.md — Implementació html_scraper.py (GREEN)
- [x] 03-03-PLAN.md — Integració pipeline.py + execució real + checkpoint DATA-04

### Phase 4: Flask API
**Goal**: The data is accessible via a clean REST API with async refresh capability and protected admin endpoint
**Depends on**: Phase 3
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09
**Success Criteria** (what must be TRUE):
  1. `GET /api/ofertes` returns all records (status 200) when `ofertes.json` exists, or 503 with an error message when it does not
  2. `GET /health` returns `{"status": "ok"}` without authentication
  3. `POST /api/admin/refresh` with a valid Bearer token launches the pipeline in a background thread and returns `{"status": "started"}` immediately (non-blocking)
  4. `POST /api/admin/refresh` returns 401 for a wrong token and 409 if a refresh is already running
  5. `GET /api/refresh-status` returns the correct state (idle/running/done/error) with last_run, total, by_grado, duration_seconds, and errors
**Plans**: 3 plans
Plans:
- [x] 04-01-PLAN.md — TDD RED: refresh_state.py + test_api.py amb 9 tests per a tots els endpoints
- [x] 04-02-PLAN.md — Implementació GREEN: app.py complet amb totes les rutes Flask
- [x] 04-03-PLAN.md — Integració real: curl verification + checkpoint humà del refresh en background

### Phase 5: Frontend — Cercador
**Goal**: Users can search the full FP catalog in real time from a static HTML page with Alpine.js via CDN
**Depends on**: Phase 4
**Requirements**: SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, SRCH-07, SRCH-08, SRCH-09, SRCH-10
**Success Criteria** (what must be TRUE):
  1. Typing in the search box instantly filters the results table by `denominacion` and `codigo` with no button press
  2. Dropdowns for Grado, Família, and Nivell each filter the results independently and in combination
  3. The "Ocultar pla antic" checkbox is active by default and correctly shows/hides old-plan records
  4. Each row with `plan_antiguo: true` displays a visible "Pla antic" badge
  5. The live counter shows the correct number of matching results after every filter change, and the table scrolls fluidly through up to 1.500 records
**Plans**: 2 plans
Plans:
- [x] 05-01-PLAN.md — index.html complet: Alpine.js data layer + HTML template + CSS inline (Wave 1)
- [x] 05-02-PLAN.md — Verificació estructural automatitzada + checkpoint humà funcional al navegador (Wave 2)

### Phase 6: Frontend — Admin Panel
**Goal**: An operator can trigger a full data refresh from the browser and monitor its progress without leaving the page
**Depends on**: Phase 5
**Requirements**: ADMN-01, ADMN-02, ADMN-03, ADMN-04, ADMN-05, ADMN-06, ADMN-07, ADMN-08
**Success Criteria** (what must be TRUE):
  1. The admin panel shows an input for the token and a "Actualitzar dades" button
  2. Clicking the button calls `POST /api/admin/refresh` with the entered token as Bearer; a 401 response shows "Token incorrecte"
  3. On success (200), the panel polls `GET /api/refresh-status` every 3 seconds and shows "Actualitzant..." while running
  4. When status becomes "done", the panel displays total records, per-Grado breakdown, and duration in seconds
  5. When status becomes "error", the panel displays the detailed error messages; the token is never saved to localStorage or any persistent storage
**Plans**: 3 plans
Plans:
- [ ] 06-01-PLAN.md — Backend: bug fix refresh + endpoints update-cookies + scheduler + scheduler_service.py + load_dotenv a pipeline
- [ ] 06-02-PLAN.md — Frontend: admin.html complet (refresh manual + cookies + scheduler) amb estil de index.html
- [ ] 06-03-PLAN.md — Docs DEPLOY.md actualitzat + checkpoint humà end-to-end al navegador
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Setup | 2/2 | Complete   | 2026-04-16 |
| 2. PDF Scrapers (Grados A, B, C) | 2/3 | In progress | - |
| 3. HTML Scrapers + Data Pipeline | 3/3 | Complete | 2026-04-18 |
| 4. Flask API | 0/3 | Planned | - |
| 5. Frontend — Cercador | 2/2 | Complete | 2026-04-19 |
| 6. Frontend — Admin Panel | 0/? | Not started | - |
