---
phase: 04-flask-api
fixed_at: 2026-04-18T00:00:00Z
review_path: .planning/phases/04-flask-api/04-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-04-18
**Source review:** .planning/phases/04-flask-api/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (WR-01 a WR-06; IN-* exclosos per fix_scope=critical_warning)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### WR-01: Lock leaked if `Thread.start()` raises

**Files modified:** `fp-cercador/backend/app.py`
**Commit:** 034c01a
**Applied fix:** Embolcalla `t.start()` en un bloc `try/except Exception`: si el SO no pot crear el thread, allibera el lock amb `refresh_state._lock.release()` i retorna 500 en lloc de deixar el lock bloquejat indefinidament. El `_run` intern queda inalterat.

---

### WR-02 + WR-03: `get_state()` shallow copy / `set_state` sense lock

**Files modified:** `fp-cercador/backend/refresh_state.py`
**Commit:** ba80975
**Applied fix:** Fixes combinats al mateix fitxer. Afegit `import copy`. `get_state()` ara retorna `copy.deepcopy(_state)`. `set_state()` ara protegeix `_state.update()` amb un lock intern dedicat (`_state_lock`).

**Nota de disseny:** No es podia usar el mateix `_lock` per a `set_state` perquè `_lock` és adquirit per `admin_refresh()` (thread principal) i alliberat per `_run()` (thread fill) al `finally`; si `set_state` intentés adquirir `_lock` des de `_run`, entraria en deadlock. La solució és un segon lock `_state_lock` exclusivament per a lectura/escriptura de `_state`, independent del mutex de concurrència de refresh.

---

### WR-04: `json.load` pot llançar `JSONDecodeError` — 500 no gestionat

**Files modified:** `fp-cercador/backend/app.py`
**Commit:** 49f9676
**Applied fix:** Embolcalla `json.load(f)` en un bloc `try/except json.JSONDecodeError`: registra l'error amb `logger.error` i retorna 503 amb missatge clar en lloc d'un stack trace.

---

### WR-05: `ADMIN_TOKEN` capturat en temps d'import — fixture pot no tenir efecte

**Files modified:** `fp-cercador/backend/tests/conftest.py`
**Commit:** 75e7aac
**Applied fix:** Afegit `os.environ.setdefault("ADMIN_TOKEN", "test-token")` al `conftest.py` (el primer fitxer que pytest carrega). Garanteix que el valor estigui present quan Python importa `app.py` per primera vegada, independent de l'ordre d'execució o caché de mòduls.

---

### WR-06: Fixture allibera lock mentre thread background encara l'usa

**Files modified:** `fp-cercador/backend/tests/test_api.py`
**Commit:** 1f450c3
**Applied fix:** Afegit `time.sleep(0.05)` al final de `test_refresh_started`, després dels asserts. Dona temps al thread daemon a completar el pipeline mockejat i alliberar el lock al `finally` de `_run` abans que el fixture `reset_refresh_state` l'intenti alliberar en el teardown.

---

_Fixed: 2026-04-18_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
