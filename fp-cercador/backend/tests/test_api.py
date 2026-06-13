"""
test_api.py — Tests d'integració de les rutes Flask (API-01 a API-09).

Tests sense xarxa real: pipeline.run i os.path.exists estan mockejats.
Fase RED: tots fallen fins que app.py implementa les rutes (Pla 02).
"""
import os
import unittest.mock as mock

import pytest

# ---------------------------------------------------------------------------
# Patch paths (convencions: constants al top del mòdul, com a test_pipeline.py)
# ---------------------------------------------------------------------------
PATCH_PIPELINE_RUN = "app.pipeline.run"
PATCH_OS_PATH_EXISTS = "app.os.path.exists"

MOCK_PIPELINE_RESULT = {
    "total": 100,
    "by_grado": {"A": 20, "B": 20, "C": 20, "D": 20, "E": 20},
    "duration_seconds": 1.5,
    "errors": [],
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_refresh_state():
    """Restableix _state i allibera _lock entre tests (evita contaminació)."""
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
    # Cleanup post-test: alliberar lock si algun test el va adquirir sense alliberar
    if refresh_state._lock.locked():
        refresh_state._lock.release()


@pytest.fixture(autouse=True)
def isolate_history(tmp_path, monkeypatch):
    """Evita que els tests escriguin a backend/data/refresh_history.json real."""
    import history
    monkeypatch.setattr(history, "HISTORY_PATH", str(tmp_path / "refresh_history.json"))


@pytest.fixture
def client():
    os.environ["ADMIN_TOKEN"] = "test-token"
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# API-07: GET /health
# ---------------------------------------------------------------------------

def test_health(client):
    """API-07: GET /health retorna {"status": "ok"} sense autenticació."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# API-01: GET /api/ofertes — 200 quan el fitxer existeix
# ---------------------------------------------------------------------------

def test_ofertes_200(client, monkeypatch):
    """API-01: GET /api/ofertes retorna 200 i una llista JSON quan ofertes.json existeix."""
    import app as flask_app_module
    monkeypatch.setattr(flask_app_module, "_ofertes_cache", {"mtime": None, "body": None})
    fake_body = '[{"id": 1, "denominacion": "Test", "grado": "A"}]'
    with mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch("app.os.path.getmtime", return_value=1.0), \
         mock.patch("builtins.open", mock.mock_open(read_data=fake_body)):
        r = client.get("/api/ofertes")
    assert r.status_code == 200
    data = r.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == 1


# ---------------------------------------------------------------------------
# API-02: GET /api/ofertes — 503 quan el fitxer no existeix
# ---------------------------------------------------------------------------

def test_ofertes_503_when_no_file(client):
    """API-02: GET /api/ofertes retorna 503 amb {"error": ...} si ofertes.json no existeix."""
    with mock.patch(PATCH_OS_PATH_EXISTS, return_value=False):
        r = client.get("/api/ofertes")
    assert r.status_code == 503
    body = r.get_json()
    assert "error" in body
    assert isinstance(body["error"], str)
    assert len(body["error"]) > 0


# ---------------------------------------------------------------------------
# API-08: CORS headers presents a les respostes
# ---------------------------------------------------------------------------

def test_cors_headers(client):
    """API-08: Les respostes inclouen el header Access-Control-Allow-Origin."""
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200
    assert "Access-Control-Allow-Origin" in r.headers


# ---------------------------------------------------------------------------
# API-04: POST /api/admin/refresh — 401 amb token incorrecte
# ---------------------------------------------------------------------------

def test_refresh_401_wrong_token(client):
    """API-04: POST /api/admin/refresh retorna 401 si el token Bearer és incorrecte."""
    r = client.post("/api/admin/refresh",
                    headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 401
    assert "error" in r.get_json()


def test_refresh_401_no_header(client):
    """API-04: POST /api/admin/refresh retorna 401 si no hi ha header Authorization."""
    r = client.post("/api/admin/refresh")
    assert r.status_code == 401
    assert "error" in r.get_json()


# ---------------------------------------------------------------------------
# API-05: POST /api/admin/refresh — 409 si procés en curs
# ---------------------------------------------------------------------------

def test_refresh_409_while_running(client):
    """API-05: POST /api/admin/refresh retorna 409 si el lock ja està adquirit (procés en curs)."""
    import refresh_state
    refresh_state._lock.acquire()
    try:
        r = client.post("/api/admin/refresh",
                        headers={"Authorization": "Bearer test-token"})
        assert r.status_code == 409
        assert "error" in r.get_json()
    finally:
        refresh_state._lock.release()


# ---------------------------------------------------------------------------
# API-03: POST /api/admin/refresh — retorna {"status": "started"} immediatament
# ---------------------------------------------------------------------------

def test_refresh_started(client):
    """API-03: POST /api/admin/refresh llança el pipeline en background i retorna {"status": "started"}."""
    import time
    with mock.patch(PATCH_PIPELINE_RUN, return_value=MOCK_PIPELINE_RESULT):
        r = client.post("/api/admin/refresh",
                        headers={"Authorization": "Bearer test-token"})
    assert r.status_code == 200
    assert r.get_json() == {"status": "started"}
    # Espera que el thread daemon completi el pipeline mockejat abans que el
    # fixture reset_refresh_state intenti alliberar el lock (WR-06: race condition).
    time.sleep(0.05)


# ---------------------------------------------------------------------------
# API-06: GET /api/refresh-status — retorna estat complet
# ---------------------------------------------------------------------------

def test_refresh_status_idle(client):
    """API-06: GET /api/refresh-status retorna l'estat complet (status, last_run, total, by_grado, duration_seconds, errors)."""
    r = client.get("/api/refresh-status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "idle"
    assert "last_run" in data
    assert "total" in data
    assert "by_grado" in data
    assert "duration_seconds" in data
    assert "errors" in data
