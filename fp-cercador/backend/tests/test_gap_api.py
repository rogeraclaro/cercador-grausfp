"""test_gap_api.py — POST /api/que-em-falta (Pla 083)."""
import json

import pytest

import app as app_module

flask_app = app_module.app
flask_app.config["TESTING"] = True

ADG = 'Administración y Gestión'
URL_SA = 'https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/servicios-administrativos.html'
REF_D = 'administracion-gestion~servicios-administrativos'


def _cataleg():
    base = [
        {'grado': 'B', 'codigo': 'ADG_B_3001', 'denominacion': 'Tratamiento informático de datos'},
        {'grado': 'B', 'codigo': 'ADG_B_3002', 'denominacion': 'Aplicaciones básicas de ofimática'},
        {'grado': 'C', 'codigo': 'ADG_C_001_3B', 'denominacion': 'Grabación de datos'},
        {'grado': 'C', 'codigo': 'ADGG0408', 'denominacion': 'Operaciones auxiliares', 'plan_antiguo': True},
        {'grado': 'D', 'codigo': None, 'denominacion': 'Servicios Administrativos', 'ficha_url': URL_SA},
        {'grado': 'A', 'codigo': 'UC0001_1', 'denominacion': 'Un grau A'},
    ]
    return [{'familia': ADG, 'nivel': 1, 'plan_antiguo': False, **r, 'id': i}
            for i, r in enumerate(base, start=1)]


@pytest.fixture
def paths(tmp_path, monkeypatch):
    contingut = {
        'DATA_PATH': _cataleg(),
        'BC_LOMLOE_PATH': {'ADG_C_001_3B': ['ADG_B_3001', 'ADG_B_3002']},
        'C_MODULOS_PATH': {'ADG_C_001_3B': [{'num': '3001', 'name': 'Tratamiento informático de datos'},
                                            {'num': '3002', 'name': 'Aplicaciones básicas de ofimática'}]},
        'D_MODULOS_PATH': {'5': {'modulos': [{'num': '3001', 'name': 'Tratamiento informático de datos'},
                                             {'num': None, 'name': 'Atención al cliente'}]}},
        'CICLOS_PATH': {'ADGG0408': [{'denominacion': 'Servicios Administrativos', 'familia': ADG,
                                      'ficha_url': URL_SA}]},
    }
    out = {}
    for attr, data in contingut.items():
        out[attr] = tmp_path / f'{attr}.json'
        out[attr].write_text(json.dumps(data), encoding='utf-8')
        monkeypatch.setattr(app_module, attr, str(out[attr]))
    for cache in ('_d_modulos_cache', '_bc_lomloe_cache', '_c_modulos_cache', '_ciclos_fp_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_catalog_cache', {'key': None, 'data': None})
    return out


@pytest.fixture
def client(paths):
    return flask_app.test_client()


def test_un_b_dona_el_c_i_el_cicle(client):
    r = client.post('/api/que-em-falta', json={'refs': ['ADG_B_3001']})
    assert r.status_code == 200
    objectius = {o['ref']: o for o in r.json['objectius']}
    assert set(objectius) == {'ADG_C_001_3B', REF_D}
    assert (objectius['ADG_C_001_3B']['tens'], objectius['ADG_C_001_3B']['total']) == (1, 2)
    assert objectius[REF_D]['falta'] == [{'tipus': 'modul', 'nom': 'Atención al cliente'}]
    assert r.json['held'][0]['codigo'] == 'ADG_B_3001'


def test_c_del_pla_antic_dona_relacionats(client):
    body = client.post('/api/que-em-falta', json={'refs': ['ADGG0408', 'no-existeix']}).json
    assert body['objectius'] == []
    assert body['ignorats'] == ['no-existeix']
    assert body['relacionats'] == [{'denominacion': 'Servicios Administrativos', 'familia': ADG,
                                    'ficha_url': URL_SA, 'via': 'ADGG0408'}]


def test_llista_buida(client):
    assert client.post('/api/que-em-falta', json={'refs': []}).json == {
        'held': [], 'ignorats': [], 'objectius': [], 'relacionats': []}


def test_sense_ciclos_fp_funciona_igual(client, paths):
    paths['CICLOS_PATH'].unlink()
    body = client.post('/api/que-em-falta', json={'refs': ['ADGG0408']}).json
    assert body['relacionats'] == [] and len(body['held']) == 1


@pytest.mark.parametrize('cos', [
    None, {}, [], {'refs': 'ADG_B_3001'}, {'refs': [1]}, {'refs': [None]}, {'refs': ['']},
    {'refs': ['x' * 201]}, {'refs': [f'r{i}' for i in range(51)]},
])
def test_cos_invalid_dona_400(client, cos):
    assert client.post('/api/que-em-falta', json=cos).status_code == 400


def test_limits_al_maxim_s_accepten(client):
    refs = ['x' * 200] + [f'r{i}' for i in range(49)]
    assert client.post('/api/que-em-falta', json={'refs': refs}).status_code == 200


def test_cataleg_illegible_dona_503(client, paths):
    paths['DATA_PATH'].unlink()
    assert client.post('/api/que-em-falta', json={'refs': ['ADG_B_3001']}).status_code == 503
