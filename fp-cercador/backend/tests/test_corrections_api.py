"""
test_corrections_api.py — Pla 098: correccions de títol, equivalències de cerca, cerques sense
resultat i comentaris sobre una especialitat.

BD migrada a tmp_path per test; fitxers SOC/SEPE de test_fpo_api i test_sepe_api.
"""
import json
import re

import pytest

import app as app_module
import db
from ca_es_terms import SEED_TERMS
from tests.test_fpo_api import fpo_data  # noqa: F401  (fixture: soc_*.json a tmp_path)
from tests.test_sepe_api import SEPE_ROWS

_AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture
def client(fpo_data, monkeypatch):  # noqa: F811
    test_db = str(fpo_data / "test.db")
    monkeypatch.setenv("DB_PATH", test_db)
    db.init_db(db_path=test_db)
    (fpo_data / "sepe_especs.json").write_text(json.dumps(SEPE_ROWS), encoding="utf-8")
    monkeypatch.setattr(app_module, "ADMIN_TOKEN", "test-token")
    monkeypatch.setattr(app_module, "_sepe_llista_cache", {"key": None, "data": None})
    monkeypatch.setattr(app_module, "_title_overrides_cache", {"key": None, "data": None})
    monkeypatch.setattr(app_module, "_search_terms_cache", {"key": None, "data": None})
    monkeypatch.setattr(app_module, "_auth_rate_hits", {})
    monkeypatch.setattr(app_module, "_feedback_hits", {})
    monkeypatch.delenv("FEEDBACK_NOTIFY_EMAIL", raising=False)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def _sepe(client, codi):
    return next(e for e in client.get("/api/sepe/especialitats").get_json()["especialitats"] if e["c"] == codi)


def _fpo(client, codi):
    return next(e for e in client.get("/api/fpo/especialitats").get_json()["especialitats"] if e["codi"] == codi)


# --- Migració 017 ---

def test_migracio_carrega_la_correccio_d_ifcd0025(client):
    conn = db.get_db()
    row = conn.execute("SELECT titol_ca, titol_es, original_ca FROM title_overrides WHERE codi = 'IFCD0025'").fetchone()
    conn.close()
    assert row["titol_ca"] == "Fonaments de programació amb HTML, CSS i JavaScript"
    assert row["titol_es"] == "Fundamentos de programación con HTML, CSS y JavaScript"
    assert row["original_ca"].endswith("JAVASCRIP")


def test_migracio_sembra_les_equivalencies(client):
    conn = db.get_db()
    terms = {r["ca"]: r["es"] for r in conn.execute("SELECT ca, es FROM search_terms")}
    conn.close()
    assert terms == SEED_TERMS


# --- Correccions de títol ---

@pytest.mark.parametrize("method, path", [
    ("get", "/api/admin/title-overrides"),
    ("get", "/api/admin/title-overrides/IFCD0112"),
    ("put", "/api/admin/title-overrides/IFCD0112"),
    ("delete", "/api/admin/title-overrides/IFCD0112"),
    ("get", "/api/admin/search-terms"),
    ("put", "/api/admin/search-terms/fusteria"),
    ("delete", "/api/admin/search-terms/fusteria"),
    ("get", "/api/admin/empty-searches"),
])
def test_endpoints_admin_demanen_admin(client, method, path):
    resp = getattr(client, method)(path, json={"titol_ca": "X", "es": "x"})
    assert resp.status_code == 401


def test_override_codi_inexistent_404(client):
    resp = client.put("/api/admin/title-overrides/NOPE0000", json={"titol_ca": "X"}, headers=_AUTH)
    assert resp.status_code == 404
    assert client.get("/api/admin/title-overrides/NOPE0000", headers=_AUTH).status_code == 404


@pytest.mark.parametrize("body", [
    {},                                      # cap títol
    {"titol_ca": "   ", "titol_es": ""},     # només espais
    {"titol_ca": 42},                        # no és text
    {"titol_ca": "x" * 301},                 # massa llarg
    {"titol_ca": "a\x00b"},                  # caràcter de control
])
def test_override_validacio(client, body):
    resp = client.put("/api/admin/title-overrides/IFCD0112", json=body, headers=_AUTH)
    assert resp.status_code == 400


def test_override_s_aplica_i_invalida_les_caches(client):
    # Primer es llegeix (i es cacheja) el títol original
    assert _sepe(client, "IFCD0112")["tca"] == "Especialitat IFCD0112"
    assert _fpo(client, "IFCD0112")["titol"]["ca"] == "Especialitat IFCD0112"

    resp = client.put("/api/admin/title-overrides/IFCD0112", headers=_AUTH,
                      json={"titol_ca": "  Programació   web ", "titol_es": "Programación web"})
    assert resp.status_code == 200
    row = resp.get_json()
    assert row["titol_ca"] == "Programació web"                       # espais col·lapsats
    assert row["original_ca"] == "Especialitat IFCD0112"
    assert row["updated_by"] == "ADMIN_TOKEN"

    sepe = _sepe(client, "IFCD0112")
    assert (sepe["tca"], sepe["t"], sepe["tm"]) == ("Programació web", "Programación web", "Programación web")
    assert _fpo(client, "IFCD0112")["titol"] == {"ca": "Programació web", "es": "Programación web"}
    detall = client.get("/api/fpo/especialitat/IFCD0112").get_json()
    assert detall["descripcio"] == {"ca": "Programació web", "es": "Programación web"}

    # Desfer: torna l'original
    assert client.delete("/api/admin/title-overrides/IFCD0112", headers=_AUTH).status_code == 200
    assert _sepe(client, "IFCD0112")["tca"] == "Especialitat IFCD0112"
    assert _fpo(client, "IFCD0112")["titol"]["ca"] == "Especialitat IFCD0112"
    assert client.delete("/api/admin/title-overrides/IFCD0112", headers=_AUTH).status_code == 404


def test_override_nomes_un_idioma(client):
    client.put("/api/admin/title-overrides/SSCE22", json={"titol_ca": "Tutorització en teleformació"},
               headers=_AUTH)
    sepe = _sepe(client, "SSCE22")
    assert sepe["tca"] == "Tutorització en teleformació"
    assert sepe["t"] == "TUTORIZACION EN TELEFORMACIÓN"                # el castellà no es toca


def test_override_ja_no_cal(client):
    client.put("/api/admin/title-overrides/IFCD0112", json={"titol_ca": "Altre títol"}, headers=_AUTH)
    client.put("/api/admin/title-overrides/SSCE22", headers=_AUTH,
               json={"titol_es": "Tutorizacion en teleformación"})      # = títol que ja mostra el SEPE
    rows = {r["codi"]: r for r in client.get("/api/admin/title-overrides", headers=_AUTH).get_json()}
    assert rows["IFCD0112"]["ja_no_cal"] is False
    assert rows["SSCE22"]["ja_no_cal"] is True
    assert rows["SSCE22"]["actual_es"] == "Tutorizacion en teleformación"
    # IFCD0025 (migració) no és als fitxers de test: no se'l marca com a innecessari
    assert rows["IFCD0025"]["al_cataleg"] is False and rows["IFCD0025"]["ja_no_cal"] is False


def test_override_get_un(client):
    d = client.get("/api/admin/title-overrides/IFCD0112", headers=_AUTH).get_json()
    assert d == {"codi": "IFCD0112", "original_ca": "Especialitat IFCD0112",
                 "original_es": "Programación", "override": None}


# --- Equivalències de cerca ---

def test_ca_es_terms_llegeix_de_la_taula(client):
    client.put("/api/admin/search-terms/Xarcuteria", json={"es": "Charcutería"}, headers=_AUTH)
    terms = client.get("/api/ca-es-terms").get_json()["terms"]
    assert terms["xarcuteria"] == "charcuteria"                         # normalitzat
    assert app_module._expand_token("xarcuteria") == ["xarcuteria", "charcuteria"]


def test_search_terms_crud(client):
    resp = client.put("/api/admin/search-terms/fusteria", json={"es": "ebanisteria"}, headers=_AUTH)
    assert resp.status_code == 200 and resp.get_json()["es"] == "ebanisteria"
    llista = client.get("/api/admin/search-terms", headers=_AUTH).get_json()
    assert {"ca": "fusteria", "es": "ebanisteria"}.items() <= next(t for t in llista if t["ca"] == "fusteria").items()
    assert client.delete("/api/admin/search-terms/fusteria", headers=_AUTH).status_code == 200
    assert "fusteria" not in client.get("/api/ca-es-terms").get_json()["terms"]
    assert app_module._expand_token("fusteria") == ["fusteria"]
    assert client.delete("/api/admin/search-terms/fusteria", headers=_AUTH).status_code == 404


@pytest.mark.parametrize("ca, body", [
    ("dues paraules", {"es": "x"}),
    ("a", {"es": "x"}),
    ("fusteria", {"es": ""}),
    ("fusteria", {"es": 3}),
    ("fusteria", {"es": "x" * 61}),
])
def test_search_terms_validacio(client, ca, body):
    assert client.put(f"/api/admin/search-terms/{ca}", json=body, headers=_AUTH).status_code == 400


def test_cerca_d_ocupacio_fa_servir_les_equivalencies(client, fpo_data, monkeypatch):
    path = fpo_data / "ocupaciones.json"
    path.write_text(json.dumps([{"grado": "C", "codigo": "INAI0108", "id": 1, "denominacion": "Carnicería",
                                 "familia": "IND", "ocupacio": "Charcutero", "norm": "charcutero"}]),
                    encoding="utf-8")
    monkeypatch.setattr(app_module, "OCUPACIONES_PATH", str(path))
    monkeypatch.setattr(app_module, "_ocupaciones_cache", {"mtime": None, "entries": None})
    assert client.get("/api/ocupaciones?q=xarcuter").get_json()["n"] == 0
    client.put("/api/admin/search-terms/xarcuter", json={"es": "charcutero"}, headers=_AUTH)
    assert client.get("/api/ocupaciones?q=xarcuter").get_json()["n"] == 1


# --- Cerques sense resultat ---

def _misses():
    conn = db.get_db()
    rows = [dict(r) for r in conn.execute("SELECT * FROM empty_searches ORDER BY q")]
    conn.close()
    return rows


def test_search_miss_normalitza_i_agrega(client):
    assert client.post("/api/search-miss", json={"q": "  Xarcutería   FINA "}).status_code == 204
    assert client.post("/api/search-miss", json={"q": "xarcuteria fina"}).status_code == 204
    rows = _misses()
    assert len(rows) == 1
    assert rows[0]["q"] == "xarcuteria fina" and rows[0]["n"] == 2
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", rows[0]["last_seen"])    # només el dia


def test_search_miss_retalla_a_80(client):
    client.post("/api/search-miss", json={"q": "a" * 300})
    assert _misses()[0]["q"] == "a" * 80


@pytest.mark.parametrize("body", [{"q": "abc"}, {"q": 1234}, {}, ["xx"]])
def test_search_miss_rebutja(client, body):
    assert client.post("/api/search-miss", json=body).status_code == 400
    assert _misses() == []


def test_search_miss_limit_per_ip(client, monkeypatch):
    monkeypatch.setattr(app_module, "_SEARCH_MISS_RATE_LIMIT", 2)
    assert client.post("/api/search-miss", json={"q": "primera"}).status_code == 204
    assert client.post("/api/search-miss", json={"q": "segona"}).status_code == 204
    assert client.post("/api/search-miss", json={"q": "tercera"}).status_code == 429
    assert [r["q"] for r in _misses()] == ["primera", "segona"]


def test_search_miss_sostre_de_files(client, monkeypatch):
    monkeypatch.setattr(app_module, "_SEARCH_MISS_MAX_ROWS", 1)
    client.post("/api/search-miss", json={"q": "primera"})
    client.post("/api/search-miss", json={"q": "segona"})       # taula plena: no entra
    client.post("/api/search-miss", json={"q": "primera"})      # coneguda: suma
    assert _misses() == [{"q": "primera", "n": 2, "last_seen": _misses()[0]["last_seen"]}]


def test_search_miss_no_desa_res_identificable(client):
    client.set_cookie("session", "una-sessio-qualsevol")
    client.post("/api/search-miss", json={"q": "xarcuteria"}, headers={"X-Real-IP": "203.0.113.9"},
                environ_base={"REMOTE_ADDR": "198.51.100.7"})
    conn = db.get_db()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(empty_searches)")]
    dump = "\n".join(conn.iterdump())
    conn.close()
    assert cols == ["q", "n", "last_seen"]
    for secret in ("198.51.100.7", "203.0.113.9", "una-sessio-qualsevol"):
        assert secret not in dump


def test_empty_searches_admin_ordenat_per_frequencia(client):
    for q in ("primera", "segona", "segona"):
        client.post("/api/search-miss", json={"q": q})
    llista = client.get("/api/admin/empty-searches", headers=_AUTH).get_json()
    assert [(r["q"], r["n"]) for r in llista] == [("segona", 2), ("primera", 1)]


# --- Comentaris sobre una especialitat ---

def _feedback(client, **extra):
    return client.post("/api/feedback", json={"kind": "data", "message": "El títol té una errada",
                                              "email": "a@b.cat", **extra})


def test_feedback_amb_espec_valid(client):
    client.put("/api/admin/title-overrides/SSCE22", json={"titol_ca": "Tutorització en teleformació"},
               headers=_AUTH)
    assert _feedback(client, espec="SSCE22").status_code == 201
    item = client.get("/api/admin/feedback", headers=_AUTH).get_json()[0]
    assert item["espec_codi"] == "SSCE22"
    assert item["espec"] == {"codi": "SSCE22", "titol": "Tutorització en teleformació"}


def test_feedback_espec_del_soc(client):
    assert _feedback(client, espec="IFCD0112").status_code == 201
    assert client.get("/api/admin/feedback", headers=_AUTH).get_json()[0]["espec"]["titol"] == "Especialitat IFCD0112"


@pytest.mark.parametrize("espec", ["NOPE0000", "../x", 42, "x" * 50])
def test_feedback_amb_espec_invalid_s_ignora(client, espec):
    assert _feedback(client, espec=espec).status_code == 201
    item = client.get("/api/admin/feedback", headers=_AUTH).get_json()[0]
    assert item["espec_codi"] is None and item["espec"] is None
