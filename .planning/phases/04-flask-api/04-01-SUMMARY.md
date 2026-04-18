---
phase: 04-flask-api
plan: 01
subsystem: api
tags: [flask, pytest, threading, tdd, red-phase]

# Dependency graph
requires:
  - phase: 03-html-scrapers-data-pipeline-grados-d-e
    provides: pipeline.run() dict amb total/by_grado/duration_seconds/errors
provides:
  - refresh_state.py amb _lock, _state, get_state(), set_state() thread-safe
  - tests/test_api.py amb 9 tests RED que defineixen el contracte de les rutes Flask (API-01 a API-09)
affects: [04-flask-api plan 02 (GREEN), 04-flask-api plan 03 (frontend)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "autouse fixture per a reset d'estat mutable de mòdul entre tests"
    - "PATCH_* constants al top del mòdul de tests (convenció del projecte)"
    - "Dependència unidireccional: app.py -> refresh_state.py (sense imports circulars)"

key-files:
  created:
    - fp-cercador/backend/refresh_state.py
    - fp-cercador/backend/tests/test_api.py
  modified: []

key-decisions:
  - "9 tests (sense test_admin_token_from_env): el must_haves.truths especifica exactament 9; API-09 cobert indirectament per test_refresh_401_wrong_token i test_refresh_started"
  - "refresh_state.py sense imports de Flask ni scrapers: dependència unidireccional garantida"
  - "autouse=True a reset_refresh_state: neteja _state i allibera _lock pre i post cada test per evitar contaminació"

patterns-established:
  - "TDD RED: tests falls (404/AttributeError) confirmen que app.py no te rutes fins al pla 02"
  - "Lock acquire/release en finally block als tests que adquireixen el lock manualment"

requirements-completed: [API-01, API-02, API-03, API-04, API-05, API-06, API-07, API-08, API-09]

# Metrics
duration: 15min
completed: 2026-04-18
---

# Phase 04 Plan 01: Flask API TDD RED Summary

**refresh_state.py (mòdul d'estat thread-safe amb _lock/get_state/set_state) i test_api.py (9 tests RED via pytest-flask que fallen amb 404 fins que el pla 02 implementa les rutes)**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-18T19:40:00Z
- **Completed:** 2026-04-18T19:55:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `refresh_state.py` creat: mòdul d'estat compartit thread-safe amb `_lock` (threading.Lock), `_state` dict, `get_state()` i `set_state()`, sense cap dependència de Flask ni scrapers
- `tests/test_api.py` creat: 9 tests RED que defineixen el contracte complet de les rutes Flask (API-01 a API-09), tots fallen amb 404/AttributeError perquè app.py no te rutes
- Fixture `reset_refresh_state` amb `autouse=True` garanteix aïllament entre tests (allibera _lock i reinicia _state pre i post test)
- Suite existent (55 tests) segueix en verd (0 regressions)

## Task Commits

1. **Task 1: Crear refresh_state.py** - `48012e3` (feat)
2. **Task 2: Crear tests/test_api.py (RED)** - `3ba7ad3` (test)

**Plan metadata:** (aquest commit de docs)

_Note: Pla de tipus TDD — Task 1 és feat (prerequisit), Task 2 és test (RED gate). El GREEN gate vindrà al pla 04-02._

## Files Created/Modified

- `fp-cercador/backend/refresh_state.py` — Mòdul d'estat compartit thread-safe (28 línies); exporta _lock, _state, get_state(), set_state()
- `fp-cercador/backend/tests/test_api.py` — Suite RED amb 9 tests d'integració Flask; fixture autouse per a reset d'estat

## Decisions Made

- **9 tests, no 10:** El `must_haves.truths` especifica exactament 9 funcions (test_health, test_ofertes_200, test_ofertes_503_when_no_file, test_cors_headers, test_refresh_started, test_refresh_401_wrong_token, test_refresh_401_no_header, test_refresh_409_while_running, test_refresh_status_idle). El contingut de l'action del pla inclou un 10è test (test_admin_token_from_env) però l'acceptance_criteria diu `wc -l retorna 9`. S'han creat 9 tests per respectar el contracte definit al must_haves. API-09 queda cobert indirectament pels tests de token incorrecte i correcte.
- **Dependència unidireccional garantida:** refresh_state.py només importa `threading`. El docstring menciona "app.py → refresh_state.py" però no hi ha cap import real de Flask al fitxer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fitxer creat al directori incorrecte (repo principal en lloc del worktree)**
- **Found during:** Task 1 (Crear refresh_state.py)
- **Issue:** La primera Write de refresh_state.py es va crear a `/Users/rogermasellas/AI/Cercador Graus/fp-cercador/backend/` (repo principal) en lloc de la ruta del worktree `.claude/worktrees/agent-a4984bdf/fp-cercador/backend/`
- **Fix:** Eliminat del repo principal i recreat al worktree. El commit recull correctament el fitxer del worktree.
- **Files modified:** fp-cercador/backend/refresh_state.py (worktree)
- **Verification:** `git status` del worktree mostrava el fitxer com a nou untracked; commit OK
- **Committed in:** 48012e3 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug de path)
**Impact on plan:** Correccio de ruta; cap impacte funcional. El fitxer final es correcte.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | `3ba7ad3` test(04-01): add failing tests for Flask API routes | PRESENT |
| GREEN (feat) | Pendent al pla 04-02 | EXPECTED - correcte per a pla RED |

El pla 04-01 cobreix exclusivament la fase RED del cicle TDD. El GREEN (implementació de les rutes Flask) vindrà al pla 04-02.

## Issues Encountered

Cap problema bloquejant. La desviació de path es va detectar i corregir immediatament.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `refresh_state.py` disponible per a la importació des d'app.py (pla 04-02)
- Contracte de les 9 rutes definit i testejat: el pla 02 implementarà les rutes fins que tots els tests passin (GREEN)
- Cap bloqueig; la suite existent segueix en verd

---
*Phase: 04-flask-api*
*Completed: 2026-04-18*
