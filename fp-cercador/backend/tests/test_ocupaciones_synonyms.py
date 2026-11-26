"""
test_ocupaciones_synonyms.py — Tests per a _expand_token (pla 050).

Verifica el diccionari CA→ES i les regles de sufix per a la cerca d'ocupació
en català.
"""
import pytest

import app as app_module
import db


@pytest.fixture(autouse=True)
def _bd_sembrada(tmp_path, monkeypatch):
    """Pla 098: les equivalències surten de la taula search_terms; cada test, una BD nova
    sembrada per la migració 017 (mai la BD local)."""
    test_db = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", test_db)
    db.init_db(db_path=test_db)
    monkeypatch.setattr(app_module, "_search_terms_cache", {"key": None, "data": None})


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


@pytest.mark.parametrize('ca, es', [
    ('seguretat', 'seguridad'),          # -etat: la regla de sufix -itat no la cobreix
    ('disseny', 'diseno'),
    ('instal·lacions', 'instalaciones'),
    ('desenvolupament', 'desarrollo'),
    ('professional', 'profesional'),
])
def test_expand_token_sepe_terms(ca, es):
    """Pla 097: paraules freqüents dels títols del SEPE."""
    from app import _expand_token
    assert _expand_token(ca) == [ca, es]


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
    """Una sola font de veritat: l'endpoint exposa la taula search_terms (Pla 098), que la
    migració sembra amb el diccionari de partida, i els sufixos de app.py."""
    from app import _CA_ES_SUFFIXES
    from ca_es_terms import SEED_TERMS
    data = _client().get('/api/ca-es-terms').get_json()
    conn = db.get_db()
    taula = {r['ca']: r['es'] for r in conn.execute('SELECT ca, es FROM search_terms')}
    conn.close()
    assert data['terms'] == taula == SEED_TERMS
    assert [tuple(p) for p in data['suffixes']] == list(_CA_ES_SUFFIXES)


def test_ca_es_terms_endpoint_is_cacheable():
    resp = _client().get('/api/ca-es-terms')
    assert 'max-age' in resp.headers.get('Cache-Control', '')
