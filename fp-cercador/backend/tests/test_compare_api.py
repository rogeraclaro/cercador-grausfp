"""test_compare_api.py — GET /api/compara (Pla 085). Fitxers aïllats a tmp_path, com test_grau_page."""
import json

import pytest

import app as app_module
from tests import test_grau_page as base

C_MODULOS = {'ADG_C_001_3B': [{'num': '3001', 'name': 'Tratamiento informático de datos'},
                              {'num': '3003', 'name': 'Archivo y comunicación'}]}


@pytest.fixture
def client(tmp_path, monkeypatch):
    base._setup(tmp_path, monkeypatch)
    c_modulos = tmp_path / 'c_modulos.json'
    c_modulos.write_text(json.dumps(C_MODULOS), encoding='utf-8')
    monkeypatch.setattr(app_module, 'C_MODULOS_PATH', str(c_modulos))
    monkeypatch.setattr(app_module, '_c_modulos_cache', {'mtime': None, 'index': None})
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


REF_D = 'administracion-gestion~servicios-administrativos'


def _refs(client):
    return {r['codigo'] or r['grado']: r['ref'] for r in app_module._get_catalog()['records']}


def test_c_pla_nou_amb_el_seu_d(client):
    ref_d = _refs(client)['D']
    r = client.get(f'/api/compara?refs=ADG_C_001_3B,{ref_d}')
    assert r.status_code == 200, r.json
    assert r.headers['Cache-Control'] == 'public, max-age=3600'
    assert set(r.json) == {'graus', 'comuns', 'moduls_compartits'}
    c, d = r.json['graus']
    assert (c['grado'], d['grado']) == ('C', 'D')
    assert c['moduls'] == ['Tratamiento informático de datos', 'Archivo y comunicación']
    assert r.json['comuns']['moduls'] == ['Archivo y comunicación']
    assert r.json['moduls_compartits'] == {'n': 1, 'de': 2}
    assert c['centres'] == {'total': 3, 'per_ccaa': {'CATALUÑA': 2, 'PAÍS VASCO': 1}}
    assert c['ocupacions'] == ['Grabadores de datos']
    assert d['ocupacions'] == ['Auxiliar administrativo']


def test_barreja_de_lletres(client):
    refs = _refs(client)
    r = client.get(f"/api/compara?refs=ADG_A_3001_01,ADG_B_3001,{refs['E']}")
    assert r.status_code == 200
    a, b, e = r.json['graus']
    assert [g['grado'] for g in r.json['graus']] == ['A', 'B', 'E']
    assert b['ecp'] and b['ra']
    assert e['acces'] == ['Título Profesional Básico en Servicios Administrativos',
                          'Título de Técnico en Gestión (LOGSE)']
    assert r.json['comuns']['moduls'] == []
    assert a['seguents'] == [{'ref': 'ADG_B_3001', 'grado': 'B', 'denominacion': 'Tratamiento informático de datos'}]


def test_c_pla_antic_porta_les_unitats_de_competencia(client):
    r = client.get('/api/compara?refs=ADGG0408,ADG_C_001_3B')
    assert r.status_code == 200
    assert [u['codigo'] for u in r.json['graus'][0]['uc']] == ['UC0973_1', 'UC9999_1']
    assert r.json['graus'][0]['moduls'] == []


@pytest.mark.parametrize('refs, invalids', [
    (None, []),
    ('', []),
    ('ADG_B_3001', []),
    ('ADG_B_3001,ADG_B_3001', []),                               # duplicats: en queda un de sol
    ('ADG_B_3001,no-existeix', ['no-existeix']),
    ('ADG_B_3001,ADG_C_001_3B,no-existeix', ['no-existeix']),
    ('ADG_B_3001,<script>', ['<script>']),
    ('ADG_A_3001_01,ADG_B_3001,ADG_C_001_3B,ADGG0408', []),      # quatre
])
def test_refs_no_valids(client, refs, invalids):
    r = client.get('/api/compara', query_string={} if refs is None else {'refs': refs})
    assert r.status_code == 400
    assert r.json['invalids'] == invalids and r.json['error']


def test_els_duplicats_es_treuen(client):
    r = client.get('/api/compara?refs=ADG_B_3001,ADG_C_001_3B,ADG_B_3001')
    assert r.status_code == 200
    assert [g['ref'] for g in r.json['graus']] == ['ADG_B_3001', 'ADG_C_001_3B']


def test_sense_cataleg_dona_503(client, tmp_path):
    (tmp_path / 'ofertes.json').unlink()
    assert client.get('/api/compara?refs=ADG_B_3001,ADG_C_001_3B').status_code == 503
