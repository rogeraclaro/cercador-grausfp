# Plan 005: Fer que el refresh programat també escrigui a l'historial públic

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- backend/app.py backend/scheduler_service.py backend/tests/`
> Compara els extractes de "Current state" amb el codi viu si hi ha canvis;
> el pla 001 haurà tocat `tests/test_api.py` (esperat). En cas de mismatch
> a `app.py` o `scheduler_service.py`, STOP.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/001-aillar-tests-de-dades-reals.md (convenció d'aïllament de HISTORY_PATH als tests)
- **Category**: bug
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

L'historial públic d'actualitzacions (`historial.html` → `/api/refresh-history`)
només registra els refreshos llançats manualment des del panell admin. El
refresh programat (`scheduler_service._scheduled_refresh`) NO crida mai la
funció d'escriptura d'historial, perquè aquesta (`_append_history`) viu a
`app.py` i importar `app` des de `scheduler_service` crearia un import
circular. Resultat: quan el scheduler setmanal estigui actiu, l'historial
públic quedarà silenciosament congelat. La solució és extreure la lògica
d'historial a un mòdul propi sense dependències de Flask.

## Current state

Fitxers rellevants (rutes relatives a `fp-cercador/`):

- `backend/app.py`:
  - Línies 52–56: constants `HISTORY_PATH` i `HISTORY_MAX = 20`.
  - Línies 85–127: `_compute_changes(curr, prev) -> dict` — diff entre dues
    entrades (famílies, deltas per grado, denominacions noves/eliminades).
  - Línies 130–162: `_append_history(result) -> None` — construeix l'entrada
    (ts, total, by_grado, families, denominacions, denominacions_by_grado,
    unknown_families, duration_seconds), llegeix el JSON existent, calcula
    `entry["changes"]` contra `history[0]`, insereix al davant, retalla a
    `HISTORY_MAX` i escriu atòmicament (tempfile + `os.replace`).
  - Línies 241–244 (dins `admin_refresh._run`): únic punt de crida:
    ```python
    try:
        _append_history(result)
    except Exception as exc_h:
        logger.error("Could not write refresh history: %s", exc_h)
    ```
  - Línies 196–206: ruta `/api/refresh-history` llegeix `HISTORY_PATH`.
- `backend/scheduler_service.py`:
  - Línies 95–122: `_scheduled_refresh()` — adquireix `refresh_state._lock`,
    crida `pipeline.run()`, fa `set_state(...)` i allibera el lock. **No
    escriu historial.**
  - Imports actuals (línies 8–19): json, logging, os, tempfile, threading,
    datetime, apscheduler, `refresh_state`, `scrapers.pipeline`. NO importa
    `app` (i no ho ha de fer mai — `app` importa `scheduler_service`).
- Convenció del repo: mòduls d'estat/serveis sense dependència de Flask
  (vegeu el docstring de `refresh_state.py`: "Cap import de Flask ni de
  app.py per evitar importacions circulars"). El nou mòdul segueix això.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Suite | `python -m pytest tests/ -q` | 0 failed |
| Import circular check | `python -c "import history, scheduler_service, app; print('OK')"` | OK |

## Scope

**In scope**:
- `backend/history.py` (crear)
- `backend/app.py` (treure la lògica moguda; mantenir les rutes)
- `backend/scheduler_service.py` (afegir la crida a historial)
- `backend/tests/test_scheduler.py` (crear)
- `backend/tests/test_api.py` (ajustar la fixture `isolate_history` del pla
  001 perquè apunti al nou mòdul)

**Out of scope**:
- El FORMAT de les entrades d'historial — es mou tal qual; l'aprimament és
  el pla 006.
- `frontend/historial.html`.
- `refresh_state.py`.

## Git workflow

- Un commit a `master`:
  `fix(scheduler): el refresh programat escriu a l'historial — extreure history.py`
- NO push sense instrucció.

## Steps

### Step 1: Crear backend/history.py

Mou-hi VERBATIM (talla i enganxa, sense canviar lògica) des d'`app.py`:
`HISTORY_PATH`, `HISTORY_MAX`, `_compute_changes` i `_append_history`,
reanomenant les funcions com a API pública del mòdul:

```python
"""
history.py — Persistència de l'historial públic de refreshos.

Sense imports de Flask ni d'app.py (el consumeixen tant app.py com
scheduler_service.py). Mateix patró que refresh_state.py.
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

HISTORY_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "refresh_history.json")
)
HISTORY_MAX = 20


def compute_changes(curr: dict, prev: dict) -> dict:
    # cos idèntic a l'antic app._compute_changes
    ...


def append(result: dict) -> None:
    # cos idèntic a l'antic app._append_history, amb la crida interna
    # canviada a compute_changes(...)
    ...
```

Nota: l'antic `_append_history` fa `import tempfile` dins la funció —
en moure'l, posa l'import a dalt del mòdul.

**Verify**: `python -c "import history; print(history.HISTORY_MAX)"` → `20`

### Step 2: Adaptar app.py

- Elimina d'`app.py`: `HISTORY_PATH`, `HISTORY_MAX`, `_compute_changes`,
  `_append_history` (i l'import de `tempfile` si ja no s'usa enlloc més —
  comprova-ho amb grep).
- Afegeix `import history` al bloc d'imports.
- A `admin_refresh._run` (antiga línia 242): `_append_history(result)` →
  `history.append(result)`.
- A la ruta `/api/refresh-history` (antigues línies 196–206): substitueix
  `HISTORY_PATH` per `history.HISTORY_PATH`.

**Verify**: `python -c "import app; print('OK')"` → OK (cap NameError).

### Step 3: Cridar l'historial des del scheduler

A `backend/scheduler_service.py`, afegeix `import history` i, dins
`_scheduled_refresh`, just després del `set_state(status="done", ...)`
(rèplica exacta del patró d'app.py):

```python
        try:
            history.append(result)
        except Exception as exc_h:
            logger.error("Could not write refresh history: %s", exc_h)
```

**Verify**: `python -c "import scheduler_service, app; print('OK')"` → OK.

### Step 4: Actualitzar la fixture d'aïllament dels tests

A `backend/tests/test_api.py`, la fixture `isolate_history` (creada al pla
001) patcheja `app.HISTORY_PATH`, que ja no existeix. Canvia-la per:

```python
@pytest.fixture(autouse=True)
def isolate_history(tmp_path, monkeypatch):
    """Evita que els tests escriguin a backend/data/refresh_history.json real."""
    import history
    monkeypatch.setattr(history, "HISTORY_PATH", str(tmp_path / "refresh_history.json"))
```

**Verify**: `python -m pytest tests/test_api.py -q` → tots passen, i el md5
de `data/refresh_history.json` no canvia.

### Step 5: Test nou del comportament del scheduler

Crea `backend/tests/test_scheduler.py`:

```python
"""test_scheduler.py — _scheduled_refresh escriu historial i gestiona el lock."""
import json
import unittest.mock as mock

import pytest

import history
import refresh_state
import scheduler_service

RESULT = {
    "total": 5, "by_grado": {"A": 5}, "families": ["Química"],
    "denominacions": ["X"], "denominacions_by_grado": {"A": ["X"]},
    "errors": [], "unknown_families": [], "duration_seconds": 1.0,
}


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setattr(history, "HISTORY_PATH", str(tmp_path / "h.json"))
    if refresh_state._lock.locked():
        refresh_state._lock.release()
    yield
    if refresh_state._lock.locked():
        refresh_state._lock.release()


def test_scheduled_refresh_appends_history(tmp_path):
    with mock.patch("scheduler_service.pipeline.run", return_value=RESULT):
        scheduler_service._scheduled_refresh()
    data = json.load(open(history.HISTORY_PATH, encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["total"] == 5


def test_scheduled_refresh_skips_if_lock_held():
    refresh_state._lock.acquire()
    try:
        with mock.patch("scheduler_service.pipeline.run") as run_mock:
            scheduler_service._scheduled_refresh()
        run_mock.assert_not_called()
    finally:
        refresh_state._lock.release()


def test_scheduled_refresh_history_failure_does_not_break_state():
    with mock.patch("scheduler_service.pipeline.run", return_value=RESULT), \
         mock.patch("scheduler_service.history.append", side_effect=OSError("disc ple")):
        scheduler_service._scheduled_refresh()
    assert refresh_state.get_state()["status"] == "done"
    assert not refresh_state._lock.locked()
```

**Verify**: `python -m pytest tests/test_scheduler.py -q` → 3 passed.

### Step 6: Suite completa

**Verify**: `python -m pytest tests/ -q` → 0 failed, i md5 de
`data/refresh_history.json` invariant.

## Test plan

3 tests nous a `backend/tests/test_scheduler.py` (Step 5): escriptura
d'historial, respecte del lock, i robustesa si l'historial falla. Patró
estructural: `tests/test_api.py`.

## Done criteria

- [ ] `backend/history.py` existeix; `grep -n "_append_history\|_compute_changes" backend/app.py` → buit
- [ ] `grep -n "history.append" backend/scheduler_service.py` → 1 resultat
- [ ] `cd backend && python -m pytest tests/ -q` → 0 failed
- [ ] `python -c "import history, scheduler_service, app"` → sense errors
- [ ] md5 de `backend/data/refresh_history.json` invariant en executar la suite
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- `app.py` ja no conté `_append_history` a les línies indicades (el codi ha
  derivat o el pla ja s'ha aplicat parcialment).
- Apareix un import circular (ImportError en `python -c "import app"`) —
  revisa que `history.py` NO importi `app` ni `scheduler_service`.
- La fixture `isolate_history` del pla 001 no existeix a `test_api.py`
  (el pla 001 no s'ha executat — fes-lo primer).

## Maintenance notes

- El pla 006 modifica `history.append` (entrades aprimades + snapshot
  separat); aquest pla deixa el format intacte deliberadament perquè els
  dos canvis siguin revisables per separat.
- Revisor: el punt delicat és que `history.append` es crida DINS del bloc
  try del scheduler però en un try/except propi — un error d'historial no
  ha de marcar el refresh com a "error" (les dades d'ofertes SÍ s'han
  escrit correctament).
