"""
test_itinerari_contingut_api.py — /api/itinerari?grado=A retorna el contingut
(RA + ECP) del B pare via b_contingut.json (Pla 068). Fitxers aïllats a tmp_path.
"""
import json
import os

import pytest

import app as app_module


def _rec(id_, codigo, grado, plan_antiguo=False, denominacion='X'):
    return {'id': id_, 'codigo': codigo, 'grado': grado, 'plan_antiguo': plan_antiguo,
            'denominacion': denominacion, 'familia': 'F', 'nivel': 1}


OFERTES = [
    _rec(1, 'ADG_B_3001', 'B', denominacion='Tratamiento informático de datos'),
    _rec(2, 'ADG_A_3001_01', 'A'),
    _rec(3, 'ADG_A_3001_05', 'A'),                    # sense RA a la fitxa del B
    _rec(4, 'MF1018_2', 'B', plan_antiguo=True, denominacion='Atención residencial'),
    _rec(5, 'UF0127', 'A', plan_antiguo=True),        # pare real MF1018_2 (no MF0127_*)
    _rec(7, 'MF0127_2', 'B', plan_antiguo=True, denominacion='Pare fals pel número'),
    _rec(8, 'UF0723', 'A', plan_antiguo=True),        # dos pares
    _rec(9, 'MF0326_2', 'B', plan_antiguo=True, denominacion='Preparación de máquinas'),
    _rec(10, 'MF0333_2', 'B', plan_antiguo=True, denominacion='Modelos y moldes'),
    _rec(6, 'ADG_A_9999_01', 'A'),                    # sense B pare
]
ECP_3001 = [{'codigo': 'ECP0973_1', 'text': 'Introducir datos y textos en terminales informáticos'}]
ECP_1018 = [{'codigo': 'ECP1018_2', 'text': 'Facilitar la atención residencial'}]
RA_01 = {'codigo': 'ADG_RA_3001_01', 'text': 'Prepara los equipos y materiales necesarios'}
B_CONTINGUT = {
    'ADG_B_3001': {'ecp': ECP_3001,
                   'ra': [RA_01, {'codigo': 'ADG_RA_3001_02', 'text': 'Graba datos'}]},
    'MF1018_2': {'ecp': ECP_1018, 'ra': []},
}
ECP_0326 = [{'codigo': 'ECP0326_2', 'text': 'Preparar máquinas'}]
B_CONTINGUT.update({
    'MF0326_2': {'ecp': ECP_0326, 'ra': []},
    # ECP repetit amb MF0326_2 → a la unió només hi surt un cop
    'MF0333_2': {'ecp': ECP_0326 + [{'codigo': 'ECP0333_2', 'text': 'Construir moldes'}], 'ra': []},
})
A_LOE_PARES = {'UF0127': ['MF1018_2'], 'UF0723': ['MF0326_2', 'MF0333_2']}
BUIT = {'ra': None, 'ecp': []}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    paths = {
        'ofertes': tmp_path / 'ofertes.json',
        'b_contingut': tmp_path / 'b_contingut.json',
        'a_loe_pares': tmp_path / 'a_loe_pares.json',
    }
    paths['a_loe_pares'].write_text(json.dumps(A_LOE_PARES), encoding='utf-8')
    paths['ofertes'].write_text(json.dumps(OFERTES), encoding='utf-8')
    paths['b_contingut'].write_text(json.dumps(B_CONTINGUT), encoding='utf-8')

    monkeypatch.setattr(app_module, 'DATA_PATH', str(paths['ofertes']))
    monkeypatch.setattr(app_module, '_itinerary_index_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, 'B_CONTINGUT_PATH', str(paths['b_contingut']))
    monkeypatch.setattr(app_module, '_b_contingut_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, 'A_LOE_PARES_PATH', str(paths['a_loe_pares']))
    monkeypatch.setattr(app_module, '_a_loe_pares_cache', {'mtime': None, 'index': None})
    return paths


@pytest.fixture
def client(data_dir):
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _get_a(client, codigo):
    resp = client.get(f'/api/itinerari?grado=A&codigo={codigo}')
    assert resp.status_code == 200
    return resp.get_json()


def test_a_lomloe_amb_ra(client):
    body = _get_a(client, 'ADG_A_3001_01')
    assert body['contingut'] == {'ra': RA_01, 'ecp': ECP_3001}


def test_a_lomloe_sense_ra_a_la_fitxa(client):
    body = _get_a(client, 'ADG_A_3001_05')
    assert body['contingut'] == {'ra': None, 'ecp': ECP_3001}


def test_a_loe_retorna_ecp_del_mf_pare(client):
    body = _get_a(client, 'UF0127')
    assert body['parent_b']['codigo'] == 'MF1018_2'
    assert [b['codigo'] for b in body['parents_b']] == ['MF1018_2']
    assert body['contingut'] == {'ra': None, 'ecp': ECP_1018}


def test_a_loe_diversos_pares_i_ecp_unio(client):
    body = _get_a(client, 'UF0723')
    assert body['parent_b']['codigo'] == 'MF0326_2'
    assert [b['codigo'] for b in body['parents_b']] == ['MF0326_2', 'MF0333_2']
    assert body['contingut'] == {
        'ra': None,
        'ecp': ECP_0326 + [{'codigo': 'ECP0333_2', 'text': 'Construir moldes'}],
    }


def test_a_loe_sense_mapa_no_endevina_pel_numero(client, data_dir):
    data_dir['a_loe_pares'].unlink()
    body = _get_a(client, 'UF0127')
    assert body['parent_b'] is None
    assert body['parents_b'] == []
    assert body['contingut'] == BUIT


def test_b_loe_retorna_fills_reals(client):
    resp = client.get('/api/itinerari?grado=B&codigo=MF1018_2')
    assert [a['codigo'] for a in resp.get_json()['children_a']] == ['UF0127']
    resp = client.get('/api/itinerari?grado=B&codigo=MF0127_2')
    assert resp.get_json()['children_a'] == []


def test_api_a_loe_pares_retorna_el_mapa(client):
    resp = client.get('/api/a-loe-pares')
    assert resp.status_code == 200
    assert resp.get_json() == A_LOE_PARES


def test_api_a_loe_pares_fitxer_absent(client, data_dir):
    data_dir['a_loe_pares'].unlink()
    resp = client.get('/api/a-loe-pares')
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_a_sense_b_pare(client):
    body = _get_a(client, 'ADG_A_9999_01')
    assert body['parent_b'] is None
    assert body['parents_b'] == []
    assert body['contingut'] == BUIT


def test_fitxer_absent_no_peta(client, data_dir):
    data_dir['b_contingut'].unlink()
    body = _get_a(client, 'ADG_A_3001_01')
    assert body['contingut'] == BUIT
    assert body['parent_b']['codigo'] == 'ADG_B_3001'


def test_parent_b_sense_regressio(client):
    body = _get_a(client, 'ADG_A_3001_01')
    assert body['parent_b'] == {
        'codigo': 'ADG_B_3001', 'denominacion': 'Tratamiento informático de datos',
        'grado': 'B', 'nivel': 1, 'familia': 'F',
    }
