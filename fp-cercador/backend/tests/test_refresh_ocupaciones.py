"""
test_refresh_ocupaciones.py — Tests per a POST /api/admin/refresh-ocupaciones
i GET /api/admin/ocupaciones-status (Pla 049).

Usa unittest.mock.patch per evitar subprocess real i xarxa.
"""
import threading
import time
import unittest.mock as mock
import os

import pytest


@pytest.fixture(autouse=True)
def reset_ocup_state():
    """Restableix _ocup_build_state i allibera _ocup_build_lock entre tests."""
    import app as flask_app_module
    flask_app_module._ocup_build_state.update(
        status="idle", started_at=None,
        finished_at=None, total_entries=None, error=None,
    )
    if flask_app_module._ocup_build_lock.locked():
        flask_app_module._ocup_build_lock.release()
    yield
    # Cleanup post-test
    if flask_app_module._ocup_build_lock.locked():
        flask_app_module._ocup_build_lock.release()


@pytest.fixture
def client():
    os.environ["ADMIN_TOKEN"] = "test-token"
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# OCUP-01: POST sense token → 401
# ---------------------------------------------------------------------------

def test_refresh_ocupaciones_no_token_401(client):
    """OCUP-01: POST /api/admin/refresh-ocupaciones sense token retorna 401."""
    r = client.post("/api/admin/refresh-ocupaciones")
    assert r.status_code == 401
    assert "error" in r.get_json()


# ---------------------------------------------------------------------------
# OCUP-02: POST amb token vàlid → 200 {"status": "started"}
# ---------------------------------------------------------------------------

def test_refresh_ocupaciones_with_token_200(client):
    """OCUP-02: POST amb token vàlid retorna 200 i status=started."""
    with mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = mock.Mock(returncode=0, stdout="ok", stderr="")
        # Patch os.path.exists i json.load per al recompte d'entrades
        with mock.patch("app.os.path.exists", return_value=False):
            r = client.post(
                "/api/admin/refresh-ocupaciones",
                headers={"Authorization": "Bearer test-token"},
            )
    assert r.status_code == 200
    assert r.get_json() == {"status": "started"}


# ---------------------------------------------------------------------------
# OCUP-03: POST dos cops seguits → segon retorna 409
# ---------------------------------------------------------------------------

def test_refresh_ocupaciones_409_when_running(client):
    """OCUP-03: Segon POST mentre el primer és en curs retorna 409."""
    import app as flask_app_module

    # Simula que el lock ja està adquirit (regeneració en curs)
    flask_app_module._ocup_build_lock.acquire()
    flask_app_module._ocup_build_state["status"] = "running"

    r = client.post(
        "/api/admin/refresh-ocupaciones",
        headers={"Authorization": "Bearer test-token"},
    )
    assert r.status_code == 409
    body = r.get_json()
    assert "error" in body


# ---------------------------------------------------------------------------
# OCUP-04: GET /api/admin/ocupaciones-status → 200 amb status field
# ---------------------------------------------------------------------------

def test_ocupaciones_status_200(client):
    """OCUP-04: GET /api/admin/ocupaciones-status retorna 200 amb status."""
    r = client.get("/api/admin/ocupaciones-status")
    assert r.status_code == 200
    body = r.get_json()
    assert "status" in body
    assert body["status"] in ("idle", "running", "done", "error")
