"""
test_alerts_service.py — Tests unitaris del motor de matching d'alertes (F3).
"""
import pytest

import alerts_service


CHANGES_WITH_META = {
    "has_changes": True,
    "new_by_grado_meta": {
        "D": [
            {"denominacio": "Tècnic Superior en Ciberseguretat en Entorns TI",
             "familia": "Informàtica i Comunicacions", "nivel": 2},
            {"denominacio": "Tècnic Superior en Desenvolupament Web",
             "familia": "Informàtica i Comunicacions", "nivel": 2},
        ],
        "A": [
            {"denominacio": "Operació d'instal·lacions elèctriques",
             "familia": "Electricitat i Electrònica", "nivel": 1},
        ],
    },
    "removed_by_grado": {
        "C": ["Certificat de Professionalitat de Cuina"]
    },
    "new_by_grado": {
        "D": ["Tècnic Superior en Ciberseguretat en Entorns TI",
              "Tècnic Superior en Desenvolupament Web"],
        "A": ["Operació d'instal·lacions elèctriques"],
    },
}

CHANGES_EMPTY = {
    "has_changes": False,
    "new_by_grado_meta": {},
    "removed_by_grado": {},
    "new_by_grado": {},
}


def test_match_by_grado():
    result = alerts_service.match_alert({"grado": "D"}, CHANGES_WITH_META)
    denoms = [r["denominacio"] for r in result]
    assert "Tècnic Superior en Ciberseguretat en Entorns TI" in denoms
    assert "Tècnic Superior en Desenvolupament Web" in denoms
    assert len(result) == 2


def test_match_by_texto_normalized():
    result = alerts_service.match_alert({"texto": "ciberseguretat"}, CHANGES_WITH_META)
    assert len(result) == 1
    assert "Ciberseguretat" in result[0]["denominacio"]


def test_match_combined_grado_and_texto():
    result = alerts_service.match_alert({"grado": "D", "texto": "web"}, CHANGES_WITH_META)
    assert len(result) == 1
    assert "Web" in result[0]["denominacio"]


def test_match_no_match_returns_empty():
    result = alerts_service.match_alert({"grado": "E"}, CHANGES_WITH_META)
    assert result == []


def test_match_changes_none_returns_empty():
    result = alerts_service.match_alert({"grado": "D"}, {})
    assert result == []


def test_build_alert_description_combined():
    desc = alerts_service.build_alert_description(
        {"grado": "D", "familia": "Informàtica i Comunicacions"}
    )
    assert "Grado D" in desc
    assert "Informàtica" in desc


def test_build_alert_description_empty_filter():
    desc = alerts_service.build_alert_description({})
    assert desc
