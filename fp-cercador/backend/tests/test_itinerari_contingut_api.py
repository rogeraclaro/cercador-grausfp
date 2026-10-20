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
    _rec(5, 'UF1018', 'A', plan_antiguo=True),
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
BUIT = {'ra': None, 'ecp': []}


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    paths = {
        'ofertes': tmp_path / 'ofertes.json',
        'b_contingut': tmp_path / 'b_contingut.json',
    }
    paths['ofertes'].write_text(json.dumps(OFERTES), encoding='utf-8')
    paths['b_contingut'].write_text(json.dumps(B_CONTINGUT), encoding='utf-8')

    monkeypatch.setattr(app_module, 'DATA_PATH', str(paths['ofertes']))
    monkeypatch.setattr(app_module, '_itinerary_index_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, 'B_CONTINGUT_PATH', str(paths['b_contingut']))
    monkeypatch.setattr(app_module, '_b_contingut_cache', {'mtime': None, 'index': None})
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
    body = _get_a(client, 'UF1018')
    assert body['contingut'] == {'ra': None, 'ecp': ECP_1018}


def test_a_sense_b_pare(client):
    body = _get_a(client, 'ADG_A_9999_01')
    assert body['parent_b'] is None
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
