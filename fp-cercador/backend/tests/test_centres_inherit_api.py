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
    # LOMLOE (Pla 057)
    {'id': 60, 'codigo': 'HOT_C_005_5B', 'grado': 'C', 'plan_antiguo': False, 'denominacion': 'C nou', 'familia': 'H', 'nivel': 3},
    {'id': 50, 'codigo': 'HOT_B_0171', 'grado': 'B', 'plan_antiguo': False, 'denominacion': 'B nou', 'familia': 'H', 'nivel': 3},
    {'id': 51, 'codigo': 'HOT_A_0171_01', 'grado': 'A', 'plan_antiguo': False, 'denominacion': 'A nou', 'familia': 'H', 'nivel': 3},
    {'id': 52, 'codigo': 'HOT_B_9999', 'grado': 'B', 'plan_antiguo': False, 'denominacion': 'B nou orfe', 'familia': 'H', 'nivel': 3},
    # Pla 058: un cicle D de la mateixa família que HOT_C_005_5B
    {'id': 700, 'codigo': None, 'grado': 'D', 'plan_antiguo': False, 'denominacion': 'T.S. Prova',
     'familia': 'H', 'nivel': 3, 'ficha_url': 'https://x/y.html'},
]
CENTRES = [
    {'id': 'M1', 'nombre': 'IES A', 'provincia': 'BARCELONA', 'localitat': 'BCN'},
    {'id': 'M2', 'nombre': 'IES B', 'provincia': 'GIRONA', 'localitat': 'GIR'},
    {'id': 'M3', 'nombre': 'IES C', 'provincia': 'LLEIDA', 'localitat': 'LLE'},
]
OFERTA_CENTRES = {'ADGG0408': ['M1', 'M2'], '60': ['M3']}
BC_LOE = {'ADGG0408': ['UC0969_1']}
BC_LOMLOE = {'HOT_C_005_5B': ['HOT_B_0171']}
# Pla 058: el mòdul del D 700 coincideix amb la denominació del B id 50 ('B nou').
D_MODULOS = {'700': {'modulos': [{'num': None, 'name': 'B nou'}], 'ensenanzaFP': None}}
CICLOS_FP = {'ADGG0408': [{'denominacion': 'X', 'familia': 'F', 'ficha_url': None}]}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    paths = {
        'ofertes': tmp_path / 'ofertes.json',
        'centres': tmp_path / 'centres.json',
        'oferta_centres': tmp_path / 'oferta_centres.json',
        'bc_loe': tmp_path / 'bc_loe.json',
        'bc_lomloe': tmp_path / 'bc_lomloe.json',
        'd_modulos': tmp_path / 'd_modulos.json',
        'ciclos': tmp_path / 'ciclos_fp.json',
    }
    paths['ofertes'].write_text(json.dumps(OFERTES), encoding='utf-8')
    paths['centres'].write_text(json.dumps(CENTRES), encoding='utf-8')
    paths['oferta_centres'].write_text(json.dumps(OFERTA_CENTRES), encoding='utf-8')
    paths['bc_loe'].write_text(json.dumps(BC_LOE), encoding='utf-8')
    paths['bc_lomloe'].write_text(json.dumps(BC_LOMLOE), encoding='utf-8')
    paths['d_modulos'].write_text(json.dumps(D_MODULOS), encoding='utf-8')
    paths['ciclos'].write_text(json.dumps(CICLOS_FP), encoding='utf-8')

    monkeypatch.setattr(app_module, 'DATA_PATH', str(paths['ofertes']))
    monkeypatch.setattr(app_module, 'CICLOS_PATH', str(paths['ciclos']))
    monkeypatch.setattr(app_module, 'D_MODULOS_PATH', str(paths['d_modulos']))
    monkeypatch.setattr(app_module, '_d_modulos_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_cd_lomloe_cache', {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_CENTRES_PATH', str(paths['centres']))
    monkeypatch.setattr(app_module, '_OFERTA_CENTRES_PATH', str(paths['oferta_centres']))
    monkeypatch.setattr(app_module, 'BC_LOE_PATH', str(paths['bc_loe']))
    monkeypatch.setattr(app_module, 'BC_LOMLOE_PATH', str(paths['bc_lomloe']))
    monkeypatch.setattr(app_module, '_bc_lomloe_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_centres_index', None)
    monkeypatch.setattr(app_module, '_oferta_centres', None)
    monkeypatch.setattr(app_module, '_itinerary_index_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_bc_loe_inverse_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_effective_oc_cache', {'key': None, 'data': None})

    monkeypatch.setattr(centres_watch_service, '_OFERTA_CENTRES_PATH', str(paths['oferta_centres']))
    monkeypatch.setattr(centres_watch_service, '_CENTRES_PATH', str(paths['centres']))
    monkeypatch.setattr(centres_watch_service, '_OFERTES_PATH', str(paths['ofertes']))
    monkeypatch.setattr(centres_watch_service, '_BC_LOE_PATH', str(paths['bc_loe']))
    monkeypatch.setattr(centres_watch_service, '_BC_LOMLOE_PATH', str(paths['bc_lomloe']))
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
    assert set(centres_index) == {'M1', 'M2', 'M3'}


def test_watch_service_load_sense_bc_loe_es_fail_soft(data_dir):
    os.remove(data_dir['bc_loe'])
    oferta_centres, _ = centres_watch_service._load_centres_data()
    assert oferta_centres['ADGG0408'] == ['M1', 'M2']
    assert '2' not in oferta_centres
    assert oferta_centres['50'] == ['M3']  # LOMLOE segueix funcionant


# ---------------------------------------------------------------------------
# Pla 057 — LOMLOE: centres heretats + /api/itinerari
# ---------------------------------------------------------------------------

def test_api_centres_b_lomloe_hereta_del_c_per_id(client):
    r = client.get('/api/centres?id=50')
    assert [c['id'] for c in r.get_json()] == ['M3']


def test_api_centres_a_lomloe_hereta_via_b(client):
    r = client.get('/api/centres?id=51')
    assert [c['id'] for c in r.get_json()] == ['M3']


def test_api_centres_count_lomloe(client):
    count = client.get('/api/centres/count').get_json()
    assert count['50'] == 1
    assert count['51'] == 1
    assert '52' not in count


def test_watch_service_load_inclou_lomloe(data_dir):
    oferta_centres, _ = centres_watch_service._load_centres_data()
    assert oferta_centres['50'] == ['M3']
    assert oferta_centres['51'] == ['M3']


def test_itinerari_b_lomloe_retorna_children_c(client):
    d = client.get('/api/itinerari?grado=B&codigo=HOT_B_0171').get_json()
    assert [c['codigo'] for c in d['children_c']] == ['HOT_C_005_5B']
    assert d['children_c_loe'] == d['children_c']  # àlies de compatibilitat


def test_itinerari_b_loe_children_c_es_alies(client):
    d = client.get('/api/itinerari?grado=B&codigo=MF0969_1').get_json()
    assert [c['codigo'] for c in d['children_c']] == ['ADGG0408']
    assert d['children_c_loe'] == d['children_c']


def test_itinerari_c_lomloe_retorna_parent_b_lomloe(client):
    d = client.get('/api/itinerari?grado=C&codigo=HOT_C_005_5B').get_json()
    assert [b['codigo'] for b in d['parent_b_lomloe']] == ['HOT_B_0171']


def test_itinerari_c_lomloe_ciclos_d(client):
    d = client.get('/api/itinerari?grado=C&codigo=HOT_C_005_5B').get_json()
    assert d['ciclos_d'] == [{
        'id': 700, 'denominacion': 'T.S. Prova', 'familia': 'H',
        'ficha_url': 'https://x/y.html', 'shared': 1, 'total': 1,
    }]


def test_itinerari_c_loe_ciclos_d_no_canvia(client):
    d = client.get('/api/itinerari?grado=C&codigo=ADGG0408').get_json()
    assert d['ciclos_d'] == [{'denominacion': 'X', 'familia': 'F', 'ficha_url': None}]
