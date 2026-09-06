"""
test_admin_fpo.py — POST /api/admin/refresh-fpo i GET /api/admin/fpo-status (Pla 061).

`build_soc_data` mockejat: el test no toca la xarxa.
"""
import json
import os
import time
from unittest.mock import patch

import pytest

os.environ.setdefault("ADMIN_TOKEN", "test-token")

from app import app as flask_app  # noqa: E402
import app as app_module  # noqa: E402

flask_app.config["TESTING"] = True

_FAKE_SOC = {
    "cursos": [{"idCurs": "C1", "especialitat": {"codi": "IFCD0112"}}],
    "especs": [{"codi": "IFCD0112", "titol": {"ca": "x", "es": "x"}}],
    "centres": [{"idCentre": "97428"}],
}


@pytest.fixture(autouse=True)
def soc_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "SOC_CURSOS_PATH", str(tmp_path / "soc_cursos.json"))
    monkeypatch.setattr(app_module, "SOC_ESPECS_PATH", str(tmp_path / "soc_especs.json"))
    monkeypatch.setattr(app_module, "SOC_CENTRES_PATH", str(tmp_path / "soc_centres.json"))
    monkeypatch.setattr(app_module, "_soc_cursos_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_soc_especs_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_soc_centres_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_soc_espec_index_cache", {"key": None, "data": None})
    return tmp_path


@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c


_AUTH = {"Authorization": "Bearer test-token"}


def _wait_status(client, want, tries=50):
    for _ in range(tries):
        st = client.get("/api/admin/fpo-status").get_json()
        if st["status"] == want:
            return st
        time.sleep(0.05)
    raise AssertionError(f"fpo-status no ha arribat a {want!r}: {st}")


def test_refresh_fpo_sense_token_rebutjat(client):
    r = client.post("/api/admin/refresh-fpo")
    assert r.status_code in (401, 403)


def test_refresh_fpo_executa_i_escriu(client, soc_paths):
    with patch("scrapers.soc_scraper.build_soc_data", return_value=_FAKE_SOC):
        r = client.post("/api/admin/refresh-fpo", headers=_AUTH)
        assert r.status_code == 200
        assert r.get_json()["status"] == "started"
        st = _wait_status(client, "done")

    assert st["cursos"] == 1 and st["especs"] == 1 and st["centres"] == 1
    assert st["last_error"] is None
    assert os.path.exists(soc_paths / "soc_cursos.json")
    assert json.loads((soc_paths / "soc_especs.json").read_text())[0]["codi"] == "IFCD0112"


def test_refresh_fpo_error_reporta(client):
    boom = RuntimeError("Algolia 500")
    with patch("scrapers.soc_scraper.build_soc_data", side_effect=boom), \
         patch("scrapers.pipeline._notify_admin_soc_failure") as notify:
        r = client.post("/api/admin/refresh-fpo", headers=_AUTH)
        assert r.status_code == 200
        st = _wait_status(client, "error")
        notify.assert_called_once()

    assert "Algolia 500" in (st["last_error"] or "")
