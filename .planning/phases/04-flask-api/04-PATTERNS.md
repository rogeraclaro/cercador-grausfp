# Phase 4: Flask API - Pattern Map

**Mapped:** 2026-04-18
**Files analyzed:** 3 (1 modify + 2 create)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `fp-cercador/backend/app.py` | controller | request-response | `fp-cercador/backend/app.py` (stub actual) | self — ampliar |
| `fp-cercador/backend/refresh_state.py` | utility / shared state | event-driven | `fp-cercador/backend/scrapers/pipeline.py` (constants + DATA_PATH) | role-partial |
| `fp-cercador/backend/tests/test_api.py` | test | request-response | `fp-cercador/backend/tests/test_pipeline.py` | role-match |

---

## Pattern Assignments

### `fp-cercador/backend/app.py` (controller, request-response — ampliar stub)

**Analog:** `fp-cercador/backend/app.py` (stub actual, línies 1-11)

**Imports pattern — stub actual** (línies 1-4):
```python
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
```

**Ampliar afegint** (imports nous a afegir al bloc inicial):
```python
import hmac
import json
import logging
import os
import threading
from datetime import datetime, timezone

from flask import Flask, abort, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

import refresh_state
from scrapers import pipeline
```

**Guard ADMIN_TOKEN** (afegir just després de `load_dotenv()`):
```python
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN not set. Create .env from .env.example.")
```

**DATA_PATH pattern** — copiat de `fp-cercador/backend/scrapers/pipeline.py` línies 64-66:
```python
DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
)
```

**Auth helper** (funció privada):
```python
def _check_auth(req) -> bool:
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[7:]
    return hmac.compare_digest(provided, ADMIN_TOKEN)
```

**Core endpoint — GET /health** (trivial, sense autenticació):
```python
@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200
```

**Core endpoint — GET /api/ofertes** (request-response + file I/O):
```python
@app.route("/api/ofertes")
def get_ofertes():
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data not available. Run /api/admin/refresh first."}), 503
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data), 200
```

**Core endpoint — GET /api/refresh-status** (lectura d'estat compartit):
```python
@app.route("/api/refresh-status")
def refresh_status():
    return jsonify(refresh_state.get_state()), 200
```

**Core endpoint — POST /api/admin/refresh** (auth + lock + thread):
```python
@app.route("/api/admin/refresh", methods=["POST"])
def admin_refresh():
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401

    acquired = refresh_state._lock.acquire(blocking=False)
    if not acquired:
        return jsonify({"error": "Refresh already running"}), 409

    def _run():
        try:
            refresh_state.set_state(
                status="running",
                last_run=datetime.now(timezone.utc).isoformat(),
                errors=[],
            )
            result = pipeline.run()
            refresh_state.set_state(
                status="done",
                total=result["total"],
                by_grado=result["by_grado"],
                duration_seconds=result["duration_seconds"],
                errors=result["errors"],
            )
        except Exception as exc:
            refresh_state.set_state(status="error", errors=[str(exc)])
        finally:
            refresh_state._lock.release()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"status": "started"}), 200
```

**Bloc main — preservar** (línies 10-11 del stub):
```python
if __name__ == "__main__":
    app.run(debug=True)
```

---

### `fp-cercador/backend/refresh_state.py` (utility, event-driven — crear nou)

**Analog parcial:** `fp-cercador/backend/scrapers/pipeline.py` (patró de constants de mòdul + DATA_PATH lines 64-66)

**No hi ha analog exacte** — cap mòdul d'estat compartit existeix al projecte. Seguir el patró de RESEARCH.md Pattern 1.

**Mòdul complet a crear:**
```python
# refresh_state.py — Estat compartit thread-safe per al pipeline de refresh.
# Dependència unidireccional: app.py → refresh_state.py (cap import de Flask aquí).
import threading

_lock = threading.Lock()

_state = {
    "status": "idle",        # idle | running | done | error
    "last_run": None,        # ISO 8601 string o null
    "total": None,
    "by_grado": None,
    "duration_seconds": None,
    "errors": [],
}


def get_state() -> dict:
    """Retorna una còpia superficial de l'estat actual."""
    return dict(_state)


def set_state(**kwargs) -> None:
    """Actualitza camps de l'estat. Cridar únicament des del thread de refresh."""
    _state.update(kwargs)
```

**Nota:** `_lock` és accessible directament com `refresh_state._lock` des de `app.py` i des dels tests (per simular el cas 409 adquirint el lock manualment).

---

### `fp-cercador/backend/tests/test_api.py` (test, request-response — crear nou)

**Analog:** `fp-cercador/backend/tests/test_pipeline.py` (línies 1-101)

**Imports pattern** (copiar convenció de test_pipeline.py línies 1-11):
```python
"""
test_api.py — Tests d'integració de les rutes Flask (API-01 a API-09).

Tests sense xarxa real: pipeline.run i os.path.exists estan mockejats.
"""
import os
import unittest.mock as mock

import pytest
```

**Fixture principal — Flask test_client** (patró del projecte: fixture amb `tmp_path`, mock del pipeline):
```python
# Patch paths — convenció de test_pipeline.py (constants de string al top)
PATCH_PIPELINE_RUN = "app.pipeline.run"
PATCH_OS_PATH_EXISTS = "app.os.path.exists"

MOCK_PIPELINE_RESULT = {
    "total": 100,
    "by_grado": {"A": 20, "B": 20, "C": 20, "D": 20, "E": 20},
    "duration_seconds": 1.5,
    "errors": [],
}


@pytest.fixture(autouse=True)
def reset_refresh_state():
    """Restableix _state i allibera _lock entre tests."""
    import refresh_state
    refresh_state._state.update({
        "status": "idle",
        "last_run": None,
        "total": None,
        "by_grado": None,
        "duration_seconds": None,
        "errors": [],
    })
    if refresh_state._lock.locked():
        refresh_state._lock.release()
    yield


@pytest.fixture
def client():
    os.environ["ADMIN_TOKEN"] = "test-token"
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c
```

**Core test pattern** (copiar estructura assertion de test_pipeline.py línies 92-101):
```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


def test_ofertes_200(client, tmp_path):
    fake_data = [{"id": 1, "denominacion": "Test", "grado": "A"}]
    fake_json = tmp_path / "ofertes.json"
    fake_json.write_text("[...]")
    with mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch("app.open", mock.mock_open(read_data='[{"id":1}]')), \
         mock.patch("app.json.load", return_value=fake_data):
        r = client.get("/api/ofertes")
    assert r.status_code == 200
    assert isinstance(r.get_json(), list)


def test_ofertes_503_when_no_file(client):
    with mock.patch(PATCH_OS_PATH_EXISTS, return_value=False):
        r = client.get("/api/ofertes")
    assert r.status_code == 503
    assert "error" in r.get_json()


def test_refresh_401_wrong_token(client):
    r = client.post("/api/admin/refresh",
                    headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401


def test_refresh_401_no_header(client):
    r = client.post("/api/admin/refresh")
    assert r.status_code == 401


def test_refresh_409_while_running(client):
    import refresh_state
    refresh_state._lock.acquire()
    try:
        r = client.post("/api/admin/refresh",
                        headers={"Authorization": "Bearer test-token"})
        assert r.status_code == 409
    finally:
        refresh_state._lock.release()


def test_refresh_started(client):
    with mock.patch(PATCH_PIPELINE_RUN, return_value=MOCK_PIPELINE_RESULT):
        r = client.post("/api/admin/refresh",
                        headers={"Authorization": "Bearer test-token"})
    assert r.status_code == 200
    assert r.get_json() == {"status": "started"}


def test_refresh_status_idle(client):
    r = client.get("/api/refresh-status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "idle"
    assert "last_run" in data
    assert "total" in data
    assert "by_grado" in data
    assert "duration_seconds" in data
    assert "errors" in data
```

---

## Shared Patterns

### DATA_PATH resolt des del fitxer (no del cwd)

**Source:** `fp-cercador/backend/scrapers/pipeline.py` línies 64-66
**Apply to:** `app.py`
```python
DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
)
```

### Patch paths com a constants de mòdul

**Source:** `fp-cercador/backend/tests/test_pipeline.py` línies 34-45
**Apply to:** `tests/test_api.py`
```python
PATCH_PIPELINE_RUN = "app.pipeline.run"
PATCH_OS_PATH_EXISTS = "app.os.path.exists"
```

### Mock amb context manager `with mock.patch(...) as mock_X`

**Source:** `fp-cercador/backend/tests/test_pipeline.py` línies 65-76
**Apply to:** `tests/test_api.py` — qualsevol test que moqui `os.path.exists` o `pipeline.run`
```python
with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response) as mock_get, \
     mock.patch(PATCH_PARSE_A, return_value=records_a) as mock_a, \
     ...
     mock.patch(PATCH_OS_REPLACE, side_effect=lambda src, dst: None):
    result = pipeline_mod.run()
```

### Fixture `autouse=True` per a reset d'estat entre tests

**No existeix al projecte** — patró nou necessari per `refresh_state` (mutable dict de mòdul persistent entre tests del mateix procés). Aplicar el patró descrit a RESEARCH.md Open Question #1.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `fp-cercador/backend/refresh_state.py` | utility | event-driven | Cap mòdul d'estat compartit existeix al projecte. Seguir RESEARCH.md Pattern 1 literalment. |

---

## Metadata

**Analog search scope:** `fp-cercador/backend/` (app.py, scrapers/pipeline.py, tests/test_pipeline.py, tests/conftest.py)
**Files scanned:** 5
**Pattern extraction date:** 2026-04-18
