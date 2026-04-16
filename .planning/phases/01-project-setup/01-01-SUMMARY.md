---
phase: 01-project-setup
plan: 01
subsystem: infra
tags: [flask, python, dotenv, flask-cors, pdfplumber, beautifulsoup4, requests]

# Dependency graph
requires: []
provides:
  - Estructura de directoris fp-cercador/backend/ (scrapers/, data/)
  - Stub Flask app.py amb CORS i dotenv configurat
  - requirements.txt amb 6 dependències Python sense versions fixes
  - .env.example amb ADMIN_TOKEN placeholder
  - .gitignore que exclou secrets i cache sense bloquejar ofertes.json
  - scrapers/ com a paquet Python importable (__init__.py)
affects: [02-scrapers, 03-api, 04-frontend]

# Tech tracking
tech-stack:
  added: [flask, flask-cors, python-dotenv, pdfplumber, requests, beautifulsoup4]
  patterns:
    - load_dotenv() crida abans de Flask(__name__) per garantir variables d'entorn disponibles al inicialitzar l'app
    - scrapers/ com a paquet Python (amb __init__.py) per permetre imports relatius a la Fase 2
    - .env exclòs del repositori; .env.example inclòs com a plantilla segura

key-files:
  created:
    - fp-cercador/backend/app.py
    - fp-cercador/backend/requirements.txt
    - fp-cercador/backend/.env.example
    - fp-cercador/backend/scrapers/__init__.py
    - fp-cercador/backend/data/.gitkeep
    - fp-cercador/.gitignore
  modified: []

key-decisions:
  - "app.py stub mínim sense rutes: les rutes s'afegiran a la Fase 4 per mantenir responsabilitats separades"
  - "requirements.txt sense versions fixes: permet pip resoldre les últimes compatibles; s'ancoraran si apareixen incompatibilitats"
  - "data/.gitkeep es pot eliminar quan Plan 02 afegeixi ofertes.json (D-09)"
  - ".env exclòs del repo (T-01-01); .env.example inclòs amb placeholder segur (T-01-02 accepted)"

patterns-established:
  - "Pattern stub Flask: imports + load_dotenv() + Flask() + CORS() + bloc __main__ — Fase 4 afegirà rutes"
  - "Pattern secrets: .env reals mai al repo; .env.example com a documentació de variables requerides"
  - "Pattern paquet Python: __init__.py mínim amb comentari indicant la fase on s'omplirà"

requirements-completed: [PROJ-01, PROJ-02, PROJ-03]

# Metrics
duration: 2min
completed: 2026-04-16
---

# Phase 01 Plan 01: Backend Python Skeleton Summary

**Skeleton Flask backend amb CORS, dotenv i paquet scrapers preparat: 5 fitxers de configuracio + 2 directoris creats per a build-zero de la Fase 2**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-16T20:28:17Z
- **Completed:** 2026-04-16T20:29:41Z
- **Tasks:** 3
- **Files modified:** 6 creats

## Accomplishments

- Estructura de directoris fp-cercador/backend/ creada (scrapers/ importable com a paquet Python, data/ llest per a ofertes.json)
- app.py stub amb load_dotenv() → Flask(__name__) → CORS(app) en l'ordre correcte, sense rutes
- requirements.txt amb exactament 6 dependències (flask, flask-cors, pdfplumber, requests, beautifulsoup4, python-dotenv), sense versions fixes
- .env.example amb placeholder ADMIN_TOKEN=canvia-aquest-token-per-un-de-segur (T-01-02 accepted)
- .gitignore que exclou .env, __pycache__, venv, *.pdf, IDE — sense excloure ofertes.json (D-09)

## Task Commits

Cada tasca commetjada atòmicament:

1. **Task 1: Crear estructura de directoris backend** - `3d45051` (chore)
2. **Task 2: Crear app.py stub Flask + CORS + dotenv** - `6777000` (feat)
3. **Task 3: Crear requirements.txt, .env.example i .gitignore** - `86a14f5` (chore)

## Files Created/Modified

- `fp-cercador/backend/app.py` (11 línies) - Stub Flask: 4 imports, load_dotenv(), app+CORS, bloc __main__
- `fp-cercador/backend/requirements.txt` (6 línies) - 6 dependències Python sense versions
- `fp-cercador/backend/.env.example` (1 línia) - Plantilla ADMIN_TOKEN amb placeholder segur
- `fp-cercador/backend/scrapers/__init__.py` (1 línia) - Marcador de paquet Python per a scrapers/
- `fp-cercador/backend/data/.gitkeep` (0 bytes) - Permet git rastrejar data/ fins que Plan 02 afegeixi ofertes.json
- `fp-cercador/.gitignore` (20 línies) - Exclou secrets, cache, venv, PDFs, IDE

## Decisions Made

- app.py manté stub mínim sense rutes: les rutes s'afegirien a Fase 4; separa responsabilitats i evita que canvis de Fase 4 trenquin l'esquelet
- requirements.txt sense versions fixes: pip resoldrà les últimes compatibles; s'ancoraran si apareixen incompatibilitats durant el desenvolupament
- data/.gitkeep: directori buit necessari per al repo; pot ser eliminat quan Plan 02 afegeixi ofertes.json (D-09 confirmat)

## Deviations from Plan

None - pla executat exactament tal com s'especificava.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

Nota operativa: Per arrencar el servidor Flask, cal:
1. `cp fp-cercador/backend/.env.example fp-cercador/backend/.env` i editar ADMIN_TOKEN
2. `pip install -r fp-cercador/backend/requirements.txt`
3. `cd fp-cercador/backend && python app.py`

## Next Phase Readiness

- Estructura del backend llesta per a la Fase 2 (scrapers PDF i HTML)
- scrapers/ importable: `from scrapers.pdf_scraper import ...` funcionara sense ModuleNotFoundError
- data/ existeix per rebre ofertes.json de Plan 02
- .env.example documenta la variable ADMIN_TOKEN que cal configurar abans de la Fase 3

---
*Phase: 01-project-setup*
*Completed: 2026-04-16*
