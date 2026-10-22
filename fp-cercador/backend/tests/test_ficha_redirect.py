"""
test_ficha_redirect.py — /api/ficha-redirect no reconstrueix l'índex de todofp a cada codigo desconegut.

Sense xarxa: buscador_scraper.parse_buscador_all està mockejat i el rellotge és controlat.
"""
import pytest

import app as app_module
from app import app

KNOWN = "AGA_A_3050_01"


@pytest.fixture
def env(monkeypatch):
    calls = []
    clock = {"now": 10_000.0}

    def fake_parse_all():
        calls.append(clock["now"])
        return {"A": [{"codigo": KNOWN, "ficha_id": 7}]}

    monkeypatch.setattr(app_module.buscador_scraper, "parse_buscador_all", fake_parse_all)
    monkeypatch.setattr(app_module.time, "monotonic", lambda: clock["now"])
    monkeypatch.setattr(app_module, "_ficha_index",
                        {"built_at": 0.0, "map": {}, "last_attempt": float("-inf")})
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client, calls, clock


def _get(client, codigo):
    return client.get(f"/api/ficha-redirect?grado=A&codigo={codigo}")


def test_codigo_conegut_redirigeix_a_la_fitxa(env):
    client, calls, _ = env
    rv = _get(client, KNOWN)
    assert rv.status_code == 302
    assert rv.headers["Location"].endswith("&id=7")
    assert len(calls) == 1


def test_codigos_desconeguts_no_reconstrueixen_l_index_cada_cop(env):
    client, calls, clock = env
    _get(client, KNOWN)
    for i in range(5):
        clock["now"] += 1
        rv = _get(client, f"ZZZZ000{i}")
        assert rv.status_code == 302
        assert "/buscador?grado=A" in rv.headers["Location"]
    assert len(calls) == 1


def test_codigo_desconegut_reconstrueix_passat_el_marge(env):
    """Un codigo nou de debò (el ministeri n'afegeix) es resol quan ha passat el marge."""
    client, calls, clock = env
    _get(client, KNOWN)
    clock["now"] += app_module._FICHA_MISS_REBUILD_FLOOR + 1
    _get(client, "ZZZZ0000")
    assert len(calls) == 2


def test_error_de_todofp_no_es_reintenta_a_cada_peticio(env, monkeypatch):
    client, calls, clock = env

    def failing():
        calls.append(clock["now"])
        raise RuntimeError("todofp caigut")

    monkeypatch.setattr(app_module.buscador_scraper, "parse_buscador_all", failing)
    for _ in range(3):
        clock["now"] += 1
        rv = _get(client, KNOWN)
        assert "/buscador?grado=A" in rv.headers["Location"]
    assert len(calls) == 1
