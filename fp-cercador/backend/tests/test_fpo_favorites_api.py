"""
test_fpo_favorites_api.py — Endpoints /api/fpo/favorites (Pla 061).

Combina BD migrada temporal + sessió d'usuari real + soc_*.json aïllats.
"""
import json
import os

import pytest

os.environ.setdefault("ADMIN_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("BASE_URL", "http://localhost")

from app import app as flask_app  # noqa: E402
import app as app_module  # noqa: E402
import db  # noqa: E402

flask_app.config["TESTING"] = True
flask_app.config["DEBUG"] = True


# --- dades SOC mínimes (mateixa forma que Pla 059) ---------------------------

def _curs(idc, esp_codi, *, centre_id="97428"):
    return {
        "idCurs": idc,
        "titol": {"ca": f"Curs {idc}", "es": f"Curso {idc}"},
        "especialitat": {"codi": esp_codi, "desc": {"ca": esp_codi, "es": esp_codi}},
        "estat": "inscripcio", "modalitat": "PRESENCIAL",
        "dataInici": "2026-10-01", "dataFi": "2027-03-01",
        "comarca": "BARCELONÈS", "municipi": "BARCELONA",
        "centre": {"nom": f"Centre {idc}", "carrer": "C/ X 1", "cp": "08001",
                   "municipi": "BARCELONA", "comarca": "BARCELONÈS",
                   "telefon": "900000000", "email": "a@b.cat", "web": "",
                   "idCentre": centre_id, "horari": {}, "lat": None, "lon": None},
        "programaUrl": "https://conforcat.gencat.cat/x.pdf",
    }


ESPECS = [{
    "codi": "IFCD0112",
    "titol": {"ca": "Especialitat IFCD0112", "es": "Especialidad IFCD0112"},
    "familia": {"codi": "IFC", "desc": {"ca": "IFC", "es": "IFC"}},
    "area": {"codi": "IFCD", "desc": {"ca": "IFCD", "es": "IFCD"}},
    "nivell": 3, "hores": 590.0, "esCertProf": True, "rd": "RD 620/2013",
    "programaUrl": "https://conforcat.gencat.cat/x.pdf",
    "moduls": [{"codi": "MF1", "desc": {"ca": "M1", "es": "M1"}, "durada": 180.0}],
}]
CURSOS = [_curs("C1", "IFCD0112"), _curs("C2", "IFCD0112")]
CENTRES = []


@pytest.fixture(autouse=True)
def fpo_fav_env(tmp_path, monkeypatch):
    # BD migrada temporal
    test_db = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", test_db)
    db.init_db(db_path=test_db)
    # soc_*.json aïllats
    (tmp_path / "soc_especs.json").write_text(json.dumps(ESPECS), encoding="utf-8")
    (tmp_path / "soc_cursos.json").write_text(json.dumps(CURSOS), encoding="utf-8")
    (tmp_path / "soc_centres.json").write_text(json.dumps(CENTRES), encoding="utf-8")
    monkeypatch.setattr(app_module, "SOC_ESPECS_PATH", str(tmp_path / "soc_especs.json"))
    monkeypatch.setattr(app_module, "SOC_CURSOS_PATH", str(tmp_path / "soc_cursos.json"))
    monkeypatch.setattr(app_module, "SOC_CENTRES_PATH", str(tmp_path / "soc_centres.json"))
    monkeypatch.setattr(app_module, "_soc_cursos_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_soc_especs_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_soc_centres_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_soc_espec_index_cache", {"key": None, "data": None})
    ext = [
        {"idCurs": "PIMEC:p1", "font": "pimec", "tipus": "Subvencionat",
         "titol": {"ca": "Programació neurolingüística", "es": "Programació neurolingüística"},
         "area": "Informàtica", "certCodi": "", "hores": 30.0, "modalitat": "PRESENCIAL",
         "estat": "", "dataInici": "2026-10-05", "dataFi": "2026-11-01",
         "municipi": "BARCELONA", "comarca": "", "centre": {"nom": "PIMEC Formació", "idCentre": ""},
         "fitxaUrl": "https://pimecformacio.org/x/p1"},
        {"idCurs": "PIMEC:p2", "font": "pimec", "tipus": "Subvencionat",
         "titol": {"ca": "Programació neurolingüística", "es": "Programació neurolingüística"},
         "area": "Informàtica", "certCodi": "", "hores": 30.0, "modalitat": "PRESENCIAL",
         "estat": "", "dataInici": "2026-06-01", "dataFi": "2026-07-01",
         "municipi": "BARCELONA", "comarca": "", "centre": {"nom": "PIMEC Formació", "idCentre": ""},
         "fitxaUrl": "https://pimecformacio.org/x/p2"},
    ]
    (tmp_path / "ext_cursos.json").write_text(json.dumps(ext), encoding="utf-8")
    monkeypatch.setattr(app_module, "EXT_CURSOS_PATH", str(tmp_path / "ext_cursos.json"))
    monkeypatch.setattr(app_module, "_ext_cursos_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_ext_index_cache", {"key": None, "data": None})
    monkeypatch.setattr(app_module, "_fpo_today", lambda: "2026-09-25")
    yield tmp_path


@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(client):
    """Client amb sessió vàlida (usuari verificat + login)."""
    from unittest.mock import patch
    with patch("email_service.send_verification_email"):
        client.post("/api/auth/register",
                    data=json.dumps({"email": "u@test.com", "password": "password123"}),
                    content_type="application/json")
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1 WHERE email = 'u@test.com'")
    conn.commit()
    conn.close()
    client.post("/api/auth/login",
                data=json.dumps({"email": "u@test.com", "password": "password123"}),
                content_type="application/json")
    return client


def _json(client, method, url, body=None):
    kw = {"content_type": "application/json"}
    if body is not None:
        kw["data"] = json.dumps(body)
    return getattr(client, method)(url, **kw)


# --- tests -----------------------------------------------------------------

def test_get_sense_sessio_401(client):
    assert client.get("/api/fpo/favorites").status_code == 401


def test_desa_i_llista_especialitat(auth_client):
    r = _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    assert r.status_code in (200, 201)

    data = auth_client.get("/api/fpo/favorites").get_json()
    assert len(data) == 1
    e = data[0]
    assert e["especialitat_codi"] == "IFCD0112"
    assert e["titol"] == {"ca": "Especialitat IFCD0112", "es": "Especialidad IFCD0112"}
    assert e["familia"]["codi"] == "IFC"
    assert e["nivell"] == 3
    assert e["hores"] == 590.0
    assert e["cursos"] == []


def test_marca_curs(auth_client):
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    r = _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses",
              {"curs_id": "C1", "centre_id": "97428"})
    assert r.status_code in (200, 201)

    e = auth_client.get("/api/fpo/favorites").get_json()[0]
    assert len(e["cursos"]) == 1
    c = e["cursos"][0]
    assert c["curs_id"] == "C1"
    assert c["finalitzat"] is False
    assert c["estat"] == "inscripcio"
    assert c["centre"]["nom"] == "Centre C1"
    assert c["dataInici"] == "2026-10-01"


def test_curs_finalitzat(auth_client):
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses",
          {"curs_id": "GHOST", "centre_id": "55555"})

    c = auth_client.get("/api/fpo/favorites").get_json()[0]["cursos"][0]
    assert c["curs_id"] == "GHOST"
    assert c["finalitzat"] is True
    assert c["centre_id"] == "55555"


def test_delete_especialitat_esborra_cursos(auth_client):
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses",
          {"curs_id": "C1", "centre_id": "97428"})

    assert auth_client.delete("/api/fpo/favorites/IFCD0112").status_code in (200, 204)
    assert auth_client.get("/api/fpo/favorites").get_json() == []

    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM fpo_favorite_courses").fetchone()[0]
    conn.close()
    assert n == 0


def test_delete_curs(auth_client):
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses",
          {"curs_id": "C1", "centre_id": "97428"})
    _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses",
          {"curs_id": "C2", "centre_id": "97428"})

    assert auth_client.delete("/api/fpo/favorites/IFCD0112/courses/C1").status_code in (200, 204)

    e = auth_client.get("/api/fpo/favorites").get_json()[0]
    assert [c["curs_id"] for c in e["cursos"]] == ["C2"]


def test_desa_especialitat_externa_i_marca_cursos(auth_client):
    codi = "PIMEC:programacio-neurolinguistica"
    assert _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": codi}).status_code == 201
    for curs_id in ("PIMEC:p1", "PIMEC:p2", "PIMEC:desaparegut"):
        r = _json(auth_client, "post", f"/api/fpo/favorites/{codi}/courses", {"curs_id": curs_id})
        assert r.status_code == 201

    e = auth_client.get("/api/fpo/favorites").get_json()[0]
    assert e["titol"]["ca"] == "Programació neurolingüística"
    assert e["font"] == "pimec"
    assert e["hores"] == 30.0
    per_id = {c["curs_id"]: c for c in e["cursos"]}
    p1 = per_id["PIMEC:p1"]
    assert p1["finalitzat"] is False and p1["estat"] == ""
    assert p1["font"] == "pimec" and p1["fitxaUrl"] == "https://pimecformacio.org/x/p1"
    assert p1["centre"]["nom"] == "PIMEC Formació" and p1["dataInici"] == "2026-10-05"
    assert per_id["PIMEC:p2"]["finalitzat"] is True         # dataFi passada
    assert per_id["PIMEC:desaparegut"]["finalitzat"] is True  # ja no és al snapshot


def test_treu_especialitat_externa(auth_client):
    codi = "PIMEC:programacio-neurolinguistica"
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": codi})
    assert auth_client.delete(f"/api/fpo/favorites/{codi}").status_code == 204
    assert auth_client.get("/api/fpo/favorites").get_json() == []


def test_favorit_soc_no_canvia(auth_client):
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses", {"curs_id": "C1"})
    e = auth_client.get("/api/fpo/favorites").get_json()[0]
    assert e["font"] == "soc" and e["cursos"][0]["font"] == "soc"
    assert e["cursos"][0]["fitxaUrl"].startswith("https://serveiocupacio.gencat.cat")
