"""
test_centres_inherit_api.py — /api/centres i /api/centres/count amb herència A/B LOE
(Pla 056). Fitxers de dades aïllats a tmp_path.
"""
import json
import os

import pytest

import app as app_module
import centres_watch_service


OFERTES = [
    {'id': 1, 'codigo': 'ADGG0408', 'grado': 'C', 'plan_antiguo': True, 'denominacion': 'C1', 'familia': 'F', 'nivel': 1},
    {'id': 2, 'codigo': 'MF0969_1', 'grado': 'B', 'plan_antiguo': True, 'denominacion': 'B1', 'familia': 'F', 'nivel': 1},
    {'id': 3, 'codigo': 'UF0969', 'grado': 'A', 'plan_antiguo': True, 'denominacion': 'A1', 'familia': 'F', 'nivel': 1},
    {'id': 4, 'codigo': 'MF9999_9', 'grado': 'B', 'plan_antiguo': True, 'denominacion': 'B orfe', 'familia': 'F', 'nivel': 1},
]
CENTRES = [
    {'id': 'M1', 'nombre': 'IES A', 'provincia': 'BARCELONA', 'localitat': 'BCN'},
    {'id': 'M2', 'nombre': 'IES B', 'provincia': 'GIRONA', 'localitat': 'GIR'},
]
OFERTA_CENTRES = {'ADGG0408': ['M1', 'M2']}
BC_LOE = {'ADGG0408': ['UC0969_1']}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    paths = {
        'ofertes': tmp_path / 'ofertes.json',
        'centres': tmp_path / 'centres.json',
        'oferta_centres': tmp_path / 'oferta_centres.json',
        'bc_loe': tmp_path / 'bc_loe.json',
    }
    paths['ofertes'].write_text(json.dumps(OFERTES), encoding='utf-8')
    paths['centres'].write_text(json.dumps(CENTRES), encoding='utf-8')
    paths['oferta_centres'].write_text(json.dumps(OFERTA_CENTRES), encoding='utf-8')
    paths['bc_loe'].write_text(json.dumps(BC_LOE), encoding='utf-8')

    monkeypatch.setattr(app_module, 'DATA_PATH', str(paths['ofertes']))
    monkeypatch.setattr(app_module, '_CENTRES_PATH', str(paths['centres']))
    monkeypatch.setattr(app_module, '_OFERTA_CENTRES_PATH', str(paths['oferta_centres']))
    monkeypatch.setattr(app_module, 'BC_LOE_PATH', str(paths['bc_loe']))
    monkeypatch.setattr(app_module, '_centres_index', None)
    monkeypatch.setattr(app_module, '_oferta_centres', None)
    monkeypatch.setattr(app_module, '_itinerary_index_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_bc_loe_inverse_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_effective_oc_cache', {'key': None, 'data': None})

    monkeypatch.setattr(centres_watch_service, '_OFERTA_CENTRES_PATH', str(paths['oferta_centres']))
    monkeypatch.setattr(centres_watch_service, '_CENTRES_PATH', str(paths['centres']))
    monkeypatch.setattr(centres_watch_service, '_OFERTES_PATH', str(paths['ofertes']))
    monkeypatch.setattr(centres_watch_service, '_BC_LOE_PATH', str(paths['bc_loe']))
    return paths


@pytest.fixture
def client(data_dir):
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def test_api_centres_b_loe_hereta_del_c_pare(client):
    r = client.get('/api/centres?id=2')
    assert r.status_code == 200
    assert sorted(c['id'] for c in r.get_json()) == ['M1', 'M2']


def test_api_centres_a_loe_hereta_via_b(client):
    r = client.get('/api/centres?id=3')
    assert sorted(c['id'] for c in r.get_json()) == ['M1', 'M2']


def test_api_centres_count_inclou_heretats_i_no_orfes(client):
    count = client.get('/api/centres/count').get_json()
    assert count['ADGG0408'] == 2
    assert count['2'] == 2
    assert count['3'] == 2
    assert '4' not in count


def test_api_centres_directes_no_canvien(client):
    r = client.get('/api/centres?codigo=ADGG0408')
    assert sorted(c['id'] for c in r.get_json()) == ['M1', 'M2']


def test_watch_service_load_inclou_heretats(data_dir):
    oferta_centres, centres_index = centres_watch_service._load_centres_data()
    assert oferta_centres['ADGG0408'] == ['M1', 'M2']
    assert oferta_centres['2'] == ['M1', 'M2']
    assert '4' not in oferta_centres
    assert set(centres_index) == {'M1', 'M2'}


def test_watch_service_load_sense_bc_loe_es_fail_soft(data_dir):
    os.remove(data_dir['bc_loe'])
    oferta_centres, _ = centres_watch_service._load_centres_data()
    assert oferta_centres == OFERTA_CENTRES
