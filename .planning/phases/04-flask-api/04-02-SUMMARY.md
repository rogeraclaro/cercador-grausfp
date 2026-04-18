---
phase: 04-flask-api
plan: 02
subsystem: api
tags: [flask, pytest, tdd, green-phase, hmac, threading, cors]

# Dependency graph
requires:
  - phase: 04-flask-api plan 01
    provides: refresh_state.py (_lock, get_state, set_state) i test_api.py (9 tests RED)
  - phase: 03-html-scrapers-data-pipeline-grados-d-e
    provides: scrapers/pipeline.py (pipeline.run())
provides:
  - app.py Flask amb 4 rutes operatives (/health, /api/ofertes, /api/refresh-status, /api/admin/refresh)
  - 9/9 tests de test_api.py en GREEN
  - 64/64 tests de la suite completa en GREEN
affects: [04-flask-api plan 03 (frontend integration)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "hmac.compare_digest per a comparació constant-time de tokens (evita timing attacks)"
    - "Lock.acquire(blocking=False) + finally: release() per a concurrència segura"
    - "Thread(daemon=True) per a background pipeline sense bloquejar aturada del servidor"
    - "DATA_PATH resolt des de __file__ (no des de cwd) per a portabilitat"
    - "RuntimeError guard a nivell de mòdul si ADMIN_TOKEN no configurat"

key-files:
  created: []
  modified:
    - fp-cercador/backend/app.py

key-decisions:
  - "Sense Blueprints: 4 rutes no justifiquen la complexitat addicional"
  - "ADMIN_TOKEN guard ABANS de app = Flask(): el servidor no arrenca sense token"
  - "hmac.compare_digest en lloc de == per a comparació de tokens (ASVS V2.1.12)"
  - "Thread daemon=True: el pipeline no bloqueja l'aturada del servidor"

# Metrics
duration: 10min
completed: 2026-04-18
---

# Phase 04 Plan 02: Flask API GREEN Summary

**app.py complet amb 4 rutes Flask (/health, /api/ofertes, /api/refresh-status, /api/admin/refresh) que fan passar els 9 tests RED del pla 01 — suite completa 64/64 en verd**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-04-18
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- `app.py` reimplementat completament: 4 rutes Flask, autenticació Bearer amb `hmac.compare_digest`, pipeline en background thread amb lock i finally garantit
- 9/9 tests de `tests/test_api.py` en GREEN (era fase RED del pla 01)
- 64/64 tests de la suite completa en verd (0 regressions als 55 tests existents)
- Tots els requisits de seguretat del threat model coberts: T-04-02-01 (hmac), T-04-02-02 (RuntimeError guard), T-04-02-03 (409 lock), T-04-02-04 (finally release)

## Task Commits

1. **Task 1: Implementar app.py complet (GREEN)** - `f9fa0a7` (feat)

## Files Created/Modified

- `fp-cercador/backend/app.py` — Flask app amb 4 rutes REST; 124 línies; exporta `app`

## Decisions Made

- **Sense Blueprints:** 4 rutes no justifiquen la complexitat; tot en un fitxer pla seguint el requisit de simplicity del CLAUDE.md
- **Guard ADMIN_TOKEN a nivell de mòdul:** `if not ADMIN_TOKEN: raise RuntimeError(...)` abans de `app = Flask(...)` — el servidor no pot arrencar sense token configurat
- **hmac.compare_digest:** Comparació constant-time del token Bearer per evitar timing attacks (T-04-02-01, ASVS V2.1.12)
- **Thread daemon=True + finally release:** Garanteix que el lock sempre s'allibera fins i tot si `pipeline.run()` llança excepció (T-04-02-03/04)

## Deviations from Plan

None — pla executat exactament com estava escrit. El codi de l'`<action>` del pla s'ha implementat directament sense cap ajustament.

## TDD Gate Compliance

| Gate | Commit | Status |
|------|--------|--------|
| RED (test) | `3ba7ad3` (pla 04-01) | PRESENT |
| GREEN (feat) | `f9fa0a7` feat(04-02): implement Flask routes — 9/9 tests GREEN | PRESENT |

Cicle TDD completat: RED (pla 01) → GREEN (pla 02).

## Known Stubs

Cap — totes les rutes retornen dades reals (refresh_state, pipeline, ofertes.json).

## Threat Flags

Cap nova superfície de seguretat no prevista al threat model del pla.

## Self-Check: PASSED

- `fp-cercador/backend/app.py` — FOUND
- Commit `f9fa0a7` — FOUND (git log)
- 9/9 tests GREEN — VERIFIED
- 64/64 suite completa GREEN — VERIFIED
- hmac.compare_digest — PRESENT
- daemon=True — PRESENT
- finally: — PRESENT
- os.path.dirname(__file__) — PRESENT
- if not ADMIN_TOKEN: — PRESENT
- No Blueprint — CONFIRMED

---
*Phase: 04-flask-api*
*Completed: 2026-04-18*
