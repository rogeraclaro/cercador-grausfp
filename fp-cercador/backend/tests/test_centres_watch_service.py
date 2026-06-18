"""
test_centres_watch_service.py — Tests unitaris de centres_watch_service (F4).
"""
import json
import pytest
import centres_watch_service


OFERTA_CENTRES = {
    "ADGG0408": ["M010001", "M010002", "M010003"],
    "12664": ["M020001"],
}

CENTRES_INDEX = {
    "M010001": {"id": "M010001", "nombre": "IES A", "provincia": "BARCELONA", "localitat": "BCN"},
    "M010002": {"id": "M010002", "nombre": "IES B", "provincia": "GIRONA", "localitat": "GIR"},
    "M010003": {"id": "M010003", "nombre": "IES C", "provincia": "BARCELONA", "localitat": "BCN"},
    "M020001": {"id": "M020001", "nombre": "IES D", "provincia": "MADRID", "localitat": "MAD"},
}


def test_get_new_centres_all():
    snapshot = {"M010001"}  # ja existia
    result = centres_watch_service._get_new_centres(
        "ADGG0408", snapshot, OFERTA_CENTRES, CENTRES_INDEX, None
    )
    ids = {c["id"] for c in result}
    assert ids == {"M010002", "M010003"}


def test_get_new_centres_provincia_filter():
    snapshot = {"M010001"}
    result = centres_watch_service._get_new_centres(
        "ADGG0408", snapshot, OFERTA_CENTRES, CENTRES_INDEX, "BARCELONA"
    )
    assert len(result) == 1
    assert result[0]["id"] == "M010003"


def test_get_new_centres_empty_snapshot():
    snapshot = set()
    result = centres_watch_service._get_new_centres(
        "ADGG0408", set(), OFERTA_CENTRES, CENTRES_INDEX, None
    )
    assert len(result) == 3


def test_get_new_centres_no_new():
    snapshot = {"M010001", "M010002", "M010003"}
    result = centres_watch_service._get_new_centres(
        "ADGG0408", snapshot, OFERTA_CENTRES, CENTRES_INDEX, None
    )
    assert result == []


def test_get_new_centres_unknown_key():
    result = centres_watch_service._get_new_centres(
        "ZZZZ9999", set(), OFERTA_CENTRES, CENTRES_INDEX, None
    )
    assert result == []


def test_build_email_body_contains_centre_name():
    watch = {"id": 1, "oferta_denom": "Gestió Administrativa", "provincia_filter": None}
    body = centres_watch_service._build_email_body(
        [CENTRES_INDEX["M010001"]], watch, "tok123", "https://example.com"
    )
    assert "IES A" in body
    assert "Gestió Administrativa" in body
    assert "unsubscribe" in body.lower() or "cw_1_tok123" in body


def test_build_email_body_with_provincia():
    watch = {"id": 2, "oferta_denom": "Ciberseguretat", "provincia_filter": "BARCELONA"}
    body = centres_watch_service._build_email_body(
        [CENTRES_INDEX["M010003"]], watch, "tok456", "https://example.com"
    )
    assert "BARCELONA" in body
