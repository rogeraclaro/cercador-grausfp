"""
test_soc_scraper.py — Snapshot de l'oferta FPO del SOC via Algolia (Pla 059).

Sense xarxa: `_algolia_browse` / la sessió HTTP es mockegen.
"""
import json

import pytest

from scrapers import soc_scraper as soc


# --- Fixtures: hits crus copiant l'estructura real dels índexs Algolia ---

CURS_HIT = {
    "idCurs": "25/ATCC2/767/0192939/026",
    "titol": {"cat": "Mercaderies perilloses", "cas": "Mercancías peligrosas"},
    "famProf": {"codi": "TMV", "desc": {"cat": "TMV - Transport", "cas": "TMV - Transporte"}},
    "area": {"codi": "TMVI", "desc": {"cat": "TMVI - Conducció", "cas": "TMVI - Conducción"}},
    "especialitat": {"codi": "TMVI24", "desc": {"cat": "TMVI24 - Merc.", "cas": "TMVI24 - Merc."}},
    "certProf": "",
    "teCertProf": "No",
    "nivellEspecialitat": 1.0,
    "hores": 24.0,
    "modalitat": "PRESENCIAL",
    "estatInscripcio": "Curs en període d'informacio",
    "dataInici": "30/09/2026",
    "dataFi": "05/10/2026",
    "dataIniciOrdre": "20260930",
    "comarca": "PLA D'URGELL",
    "municipi": "MOLLERUSSA",
    "provincia": "LLEIDA",
    "centres": {
        "nomLoc": "TRACER FORMADORES", "calleLoc": "PP BEETHOVEN 6", "localidadLoc": "MOLLERUSSA",
        "codPostalLoc": "25230", "telefonLoc": "640863833", "mailLoc": "tecnica@tracer.es",
        "webLoc": "", "idCentre": "97428",
        "horariLoc": {"dilluns": "08:00-11:00", "dimarts": "", "dimecres": "08:00-15:00",
                      "dijous": "08:00-15:00", "divendres": "08:00-15:00", "dissabte": "", "diumenge": ""},
        "lat": "0", "lon": "0",
    },
    "programa": {"cat": "", "cas": "https://sede.sepe.gob.es/x/TMVI24.pdf"},
    "queAprendras": {"cat": "Aprendràs X", "cas": "Aprenderás X"},
    "dadesInteres": {"requisits": {"cat": "Cap", "cas": "Ninguno"},
                     "quePoderTreballar": {"cat": "Transportista", "cas": "Transportista"}},
    "unitatCompetencia": [{
        "codi": "NoUC_TMVI24", "desc": {"cat": "", "cas": ""},
        "modulFormatiu": [{"codi": "TMVI24/M01", "desc": {"cat": "Merc. perilloses", "cas": "Merc. peligrosas"},
                           "unitatFormativa": [], "durada": 24.0}],
    }],
    "codOcupacio": [{"codi": "", "desc": {"cat": "", "cas": ""}}],
    "esCifo": "N",
    "perDiscapacitats": "N",
}

CURS_HIT_CERTPROF = {
    **CURS_HIT,
    "idCurs": "25/AAA/1/0000000/001",
    "especialitat": {"codi": "ADGG0408", "desc": {"cat": "ADGG0408 - Admin.", "cas": "ADGG0408 - Admin."}},
    "famProf": {"codi": "ADG", "desc": {"cat": "ADG - Administració", "cas": "ADG - Administración"}},
    "area": {"codi": "ADGG", "desc": {"cat": "ADGG - Gestió", "cas": "ADGG - Gestión"}},
    "certProf": "RD 645/2011",
    "teCertProf": "Si",
    "estatInscripcio": "Curs en període d'inscripcio",
    "comarca": "BARCELONÈS",
    "municipi": "BARCELONA",
}

ESPEC_HIT = {
    "codi": "TMVI24",
    "desc": {"cat": "Mercaderies perilloses", "cas": "Mercancías peligrosas"},
    "familia": {"codi": "TMV", "desc": {"cat": "Transport", "cas": "Transporte"}},
    "area": {"codi": "TMVI", "desc": {"cat": "Conducció", "cas": "Conducción"}},
    "hores": 24.0, "preu": 0.0, "nivellEspecialitat": 1.0,
    "certProf": "undefined",
    "programa": {"cat": "https://conforcat.gencat.cat/x/TMVI24_CAT.pdf", "cas": "https://sede.sepe.gob.es/x"},
    "unitatCompetencia": [{
        "codi": "NoUC_TMVI24", "desc": {"cat": "", "cas": ""},
        "modulFormatiu": [{"codi": "TMVI24/M01", "desc": {"cat": "Merc.", "cas": "Merc."},
                           "unitatFormativa": [], "durada": 24.0}],
    }],
    "cursos": [{"idCursIntern": "111"}, {"idCursIntern": "112"}],
    "centres": [{"idCentre": "97428"}],
    "espDestacada": "S", "dataBaixa": "",
}

ESPEC_HIT_CERTPROF = {
    **ESPEC_HIT,
    "codi": "ADGG0408",
    "certProf": "RD 645/2011",
    "espDestacada": "N",
}

CENTRE_HIT = {
    "idCentre": "97428",
    "data": {
        "codiEntitat": "23919", "raoSocial": "TRACER FORMADORES", "cif": "B12345678",
        "numCens": "4160", "email": "tecnica@tracer.es", "web": "http://tracer.es/",
        "idCentre": "97428", "codiCentre": "2523000005", "carrer": "PP BEETHOVEN 6",
        "comarca": "PLA D'URGELL", "cp": "25230", "municipi": "MOLLERUSSA", "provincia": "LLEIDA",
        "telefon": "640863833", "lat": "0", "lng": "41.61", "numCursos": 3,
        "esCifo": "N", "perDiscapacitats": "S",
    },
}


# --- _fetch_all: paginació per `page` i error de clau ---

def test_fetch_all_pagina_per_pages(monkeypatch):
    calls = []

    def fake_query(index, key, params, session=None):
        calls.append(params)
        if "page=0" in params:
            return {"hits": [{"a": 1}, {"a": 2}], "nbPages": 2, "nbHits": 3}
        return {"hits": [{"a": 3}], "nbPages": 2}

    monkeypatch.setattr(soc, "_algolia_query", fake_query)
    out = soc._fetch_all("pro_SOC_CURSOS", "k")
    assert out == [{"a": 1}, {"a": 2}, {"a": 3}]
    assert len(calls) == 2 and "page=1" in calls[1]


def test_query_403_aixeca_error_clau():
    class Resp:
        status_code = 403
        text = "forbidden"

        def json(self):
            return {}

        def raise_for_status(self):
            raise AssertionError("no s'hauria d'arribar aquí")

    class Sess:
        headers = {}

        def post(self, *a, **kw):
            return Resp()

    with pytest.raises(soc.SocKeyError) as exc:
        soc._algolia_query("pro_SOC_CURSOS", "k", "query=&hitsPerPage=1000&page=0", session=Sess())
    assert "clau" in str(exc.value).lower()


# --- normalize_* ---

def test_normalize_curs():
    r = soc.normalize_curs(CURS_HIT)
    assert r == {
        "idCurs": "25/ATCC2/767/0192939/026",
        "titol": {"ca": "Mercaderies perilloses", "es": "Mercancías peligrosas"},
        "familia": {"codi": "TMV", "desc": {"ca": "TMV - Transport", "es": "TMV - Transporte"}},
        "area": {"codi": "TMVI", "desc": {"ca": "TMVI - Conducció", "es": "TMVI - Conducción"}},
        "especialitat": {"codi": "TMVI24", "desc": {"ca": "TMVI24 - Merc.", "es": "TMVI24 - Merc."}},
        "esCertProf": False,
        "rd": None,
        "nivell": 1,
        "hores": 24.0,
        "modalitat": "PRESENCIAL",
        "estat": "informacio",
        "dataInici": "2026-09-30",
        "dataFi": "2026-10-05",
        "comarca": "PLA D'URGELL",
        "municipi": "MOLLERUSSA",
        "provincia": "LLEIDA",
        "centre": {
            "nom": "TRACER FORMADORES", "carrer": "PP BEETHOVEN 6", "cp": "25230",
            "municipi": "MOLLERUSSA", "comarca": "PLA D'URGELL", "telefon": "640863833",
            "email": "tecnica@tracer.es", "web": "", "idCentre": "97428",
            "horari": {"dilluns": "08:00-11:00", "dimarts": "", "dimecres": "08:00-15:00",
                       "dijous": "08:00-15:00", "divendres": "08:00-15:00", "dissabte": "", "diumenge": ""},
            "lat": None, "lon": None,
        },
        "programaUrl": "https://sede.sepe.gob.es/x/TMVI24.pdf",
        "queAprendras": {"ca": "Aprendràs X", "es": "Aprenderás X"},
        "requisits": {"ca": "Cap", "es": "Ninguno"},
        "sortides": {"ca": "Transportista", "es": "Transportista"},
        "moduls": [{"codi": "TMVI24/M01", "desc": {"ca": "Merc. perilloses", "es": "Merc. peligrosas"}, "durada": 24.0}],
        "ocupacions": [],
    }


def test_normalize_curs_certprof_i_estat_inscripcio():
    r = soc.normalize_curs(CURS_HIT_CERTPROF)
    assert r["esCertProf"] is True
    assert r["rd"] == "RD 645/2011"
    assert r["estat"] == "inscripcio"


def test_normalize_espec():
    r = soc.normalize_espec(ESPEC_HIT)
    assert r == {
        "codi": "TMVI24",
        "titol": {"ca": "Mercaderies perilloses", "es": "Mercancías peligrosas"},
        "familia": {"codi": "TMV", "desc": {"ca": "Transport", "es": "Transporte"}},
        "area": {"codi": "TMVI", "desc": {"ca": "Conducció", "es": "Conducción"}},
        "nivell": 1,
        "hores": 24.0,
        "preu": 0.0,
        "esCertProf": False,
        "rd": None,
        "programaUrl": "https://conforcat.gencat.cat/x/TMVI24_CAT.pdf",
        "moduls": [{"codi": "TMVI24/M01", "desc": {"ca": "Merc.", "es": "Merc."}, "durada": 24.0}],
        "cursIds": ["111", "112"],
        "destacada": True,
    }


def test_normalize_espec_certprof_valid():
    r = soc.normalize_espec(ESPEC_HIT_CERTPROF)
    assert r["esCertProf"] is True
    assert r["rd"] == "RD 645/2011"
    assert r["destacada"] is False


def test_normalize_centre():
    r = soc.normalize_centre(CENTRE_HIT)
    assert r == {
        "idCentre": "97428",
        "raoSocial": "TRACER FORMADORES",
        "cif": "B12345678",
        "numCens": "4160",
        "email": "tecnica@tracer.es",
        "web": "http://tracer.es/",
        "codiCentre": "2523000005",
        "carrer": "PP BEETHOVEN 6",
        "cp": "25230",
        "municipi": "MOLLERUSSA",
        "comarca": "PLA D'URGELL",
        "provincia": "LLEIDA",
        "telefon": "640863833",
        "lat": None,
        "lon": 41.61,
        "numCursos": 3,
        "esCifo": False,
        "perDiscapacitats": True,
    }


# --- build_soc_data / write_soc_data ---

def test_build_soc_data(monkeypatch):
    def fake_fetch_all(index, key):
        return {
            "pro_SOC_CURSOS": [CURS_HIT, CURS_HIT_CERTPROF],
            "pro_SOC_ESPECS_r1a": [ESPEC_HIT, ESPEC_HIT_CERTPROF],
            "pro_SOC_CENTRES": [CENTRE_HIT],
        }[index]

    monkeypatch.setattr(soc, "_fetch_all", fake_fetch_all)
    d = soc.build_soc_data()
    assert set(d) == {"cursos", "especs", "centres"}
    assert len(d["cursos"]) == 2 and d["cursos"][0]["idCurs"] == "25/ATCC2/767/0192939/026"
    assert len(d["especs"]) == 2 and d["especs"][0]["codi"] == "TMVI24"
    assert len(d["centres"]) == 1 and d["centres"][0]["idCentre"] == "97428"


def test_write_soc_data_atomic(tmp_path):
    data = {
        "cursos": [{"idCurs": "1"}],
        "especs": [{"codi": "X"}],
        "centres": [{"idCentre": "9"}],
    }
    soc.write_soc_data(data, str(tmp_path))
    for name, key in (("soc_cursos.json", "cursos"), ("soc_especs.json", "especs"),
                      ("soc_centres.json", "centres")):
        p = tmp_path / name
        assert json.loads(p.read_text(encoding="utf-8")) == data[key]
