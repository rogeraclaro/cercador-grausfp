"""
test_ocupaciones_synonyms.py — Tests per a _expand_token (pla 050).

Verifica el diccionari CA→ES i les regles de sufix per a la cerca d'ocupació
en català.
"""
import pytest


def test_expand_token_suffix_acio():
    from app import _expand_token
    assert _expand_token('comunicacio') == ['comunicacio', 'comunicacion']


def test_expand_token_suffix_itat():
    from app import _expand_token
    assert _expand_token('electricitat') == ['electricitat', 'electricidad']


def test_expand_token_suffix_ment():
    from app import _expand_token
    assert _expand_token('manteniment') == ['manteniment', 'mantenimiento']


def test_expand_token_suffix_atge():
    from app import _expand_token
    assert _expand_token('muntatge') == ['muntatge', 'montaje']


def test_expand_token_dict_cuina():
    from app import _expand_token
    assert _expand_token('cuina') == ['cuina', 'cocina']


def test_expand_token_no_expansion():
    from app import _expand_token
    assert _expand_token('soldador') == ['soldador']


def test_expand_token_already_es():
    from app import _expand_token
    # 'comunicacion' ja és castellà — cap suffix CA coincideix
    assert _expand_token('comunicacion') == ['comunicacion']


def test_expand_token_dict_infermeria():
    from app import _expand_token
    assert _expand_token('infermeria') == ['infermeria', 'enfermeria']


def test_expand_token_dict_comerc():
    from app import _expand_token
    assert _expand_token('comerc') == ['comerc', 'comercio']


def test_expand_token_dict_esport():
    from app import _expand_token
    assert _expand_token('esport') == ['esport', 'deporte']


def test_expand_token_dict_transport():
    from app import _expand_token
    assert _expand_token('transport') == ['transport', 'transporte']


# --- GET /api/ca-es-terms: la taula principal reutilitza l'expansió CA→ES --------


def _client():
    from app import app
    return app.test_client()


def test_ca_es_terms_endpoint_shape():
    resp = _client().get('/api/ca-es-terms')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data['terms'], dict) and data['terms']
    assert isinstance(data['suffixes'], list) and data['suffixes']


def test_ca_es_terms_endpoint_matches_backend_tables():
    """Una sola font de veritat: l'endpoint exposa exactament les taules de app.py."""
    from app import _CA_ES_TERMS, _CA_ES_SUFFIXES
    data = _client().get('/api/ca-es-terms').get_json()
    assert data['terms'] == _CA_ES_TERMS
    assert [tuple(p) for p in data['suffixes']] == list(_CA_ES_SUFFIXES)


def test_ca_es_terms_endpoint_is_cacheable():
    resp = _client().get('/api/ca-es-terms')
    assert 'max-age' in resp.headers.get('Cache-Control', '')
