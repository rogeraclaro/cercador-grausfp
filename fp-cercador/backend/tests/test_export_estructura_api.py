"""test_export_estructura_api.py — GET /api/export/estructura (Pla 093)."""
import csv
import io
import json

import pytest

import app as app_module

flask_app = app_module.app
flask_app.config["TESTING"] = True

FAM = 'Electricidad y Electrónica'
URL_TEL = ('https://www.todofp.es/que-estudiar/familias-profesionales/electricidad-electronica/'
           'instalaciones-telecomunicaciones.html')
REF_TEL = 'electricidad-electronica~instalaciones-telecomunicaciones'

ESTRUCTURA = {'ELEE0109': {
    'total_h': 920,
    'mf': [{'codigo': 'MF0820_2', 'h': 170, 'uc': 'UC0820_2',
            'ufs': [{'codigo': 'UF0884', 'h': 60}, {'codigo': 'UF0886', 'h': 30}]},
           {'codigo': 'MF0821_2', 'h': 230, 'uc': 'UC0821_2', 'ufs': [{'codigo': 'UF0886', 'h': 30}]},
           {'codigo': 'MF0825_2', 'h': 180, 'uc': 'UC0825_2', 'ufs': []}],
    'mp': {'codigo': 'MP0183', 'h': 80}}}
CORR = {REF_TEL: {'decret': 'BOE-A-2009-1', 'vigent': 'BOE-A-2009-1', 'notes': [], 'acredita': [],
                  'convalida': [{'uc': ['UC0820_2', 'UC0821_2'],
                                 'moduls': [{'num': '0362', 'name': 'Instalaciones eléctricas básicas'}]}]}}


def _cataleg():
    base = [
        {'grado': 'C', 'codigo': 'ELEE0109', 'denominacion': 'Montaje de instalaciones de baja tensión',
         'plan_antiguo': True, 'duracion_horas': 900},
        {'grado': 'C', 'codigo': 'ELE_C_001_2', 'denominacion': 'Certificat del pla nou'},
        {'grado': 'C', 'codigo': 'ELEM0311', 'denominacion': 'Sense annex', 'plan_antiguo': True,
         'duracion_horas': 500},
        {'grado': 'B', 'codigo': 'MF0820_2', 'denominacion': 'Instalaciones en viviendas', 'plan_antiguo': True},
        {'grado': 'B', 'codigo': 'MF1978_2', 'denominacion': 'Mòdul sense UF', 'plan_antiguo': True},
        {'grado': 'A', 'codigo': 'UF0884', 'denominacion': 'Montaje de enlace', 'plan_antiguo': True},
        {'grado': 'A', 'codigo': 'UF0886', 'denominacion': '=Prevención', 'plan_antiguo': True},
        {'grado': 'B', 'codigo': 'ELE_B_3001', 'denominacion': 'Mòdul B nou'},
        {'grado': 'A', 'codigo': 'ELE_A_3001_01', 'denominacion': 'Unitat A nova'},
        {'grado': 'D', 'codigo': None, 'denominacion': 'Técnico en Telecomunicaciones', 'ficha_url': URL_TEL},
    ]
    return [{'familia': FAM, 'nivel': 2, 'plan_antiguo': False, **r, 'id': i} for i, r in enumerate(base, 1)]


@pytest.fixture
def client(tmp_path, monkeypatch):
    contingut = {
        'DATA_PATH': _cataleg(), 'C_LOE_ESTRUCTURA_PATH': ESTRUCTURA, 'D_UC_CORR_PATH': CORR,
        'BC_LOE_PATH': {'ELEE0109': ['UC0820_2', 'UC0821_2', 'UC0825_2'], 'ELEM0311': ['UC1978_2']},
        'BC_LOMLOE_PATH': {'ELE_C_001_2': ['ELE_B_3001']},
        'D_MODULOS_PATH': {'10': {'modulos': [{'num': None, 'name': 'Instalaciones eléctricas básicas'},
                                              {'num': None, 'name': 'Electrónica'}]}},
    }
    for attr, data in contingut.items():
        path = tmp_path / f'{attr}.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        monkeypatch.setattr(app_module, attr, str(path))
    monkeypatch.setattr(app_module, 'UC_CORR_OVERRIDES_PATH', str(tmp_path / 'overrides.json'))
    for cache in ('_d_modulos_cache', '_d_uc_corr_cache', '_bc_lomloe_cache', '_c_modulos_cache',
                  '_itinerary_index_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    for attr in ('C_MODULOS_PATH', 'A_LOE_PARES_PATH'):
        monkeypatch.setattr(app_module, attr, str(tmp_path / f'{attr}-absent.json'))
    monkeypatch.setattr(app_module, '_catalog_cache', {'key': None, 'data': None})
    return flask_app.test_client()


def _csv(resp):
    text = resp.get_data(as_text=True)
    assert text.startswith('﻿')
    return list(csv.reader(io.StringIO(text[1:]), delimiter=';'))


def test_certificat_loe_una_fila_per_uf_amb_hores_i_transversals(client):
    resp = client.get('/api/export/estructura', query_string={'refs': 'ELEE0109'})
    assert resp.status_code == 200 and 'text/csv' in resp.content_type
    assert 'attachment' in resp.headers['Content-Disposition']
    rows = _csv(resp)
    assert rows[0][:2] == ['Codi certificat', 'Nom certificat'] and len(rows) == 1 + 5
    uf884 = rows[1]
    assert uf884[4:] == ['920', 'MF0820_2', 'Instalaciones en viviendas', '170', 'UC0820_2',
                         'UF0884', 'Montaje de enlace', '60', 'no']
    assert [r[9:] for r in rows[2:4]] == [["UF0886", "'=Prevención", '30', 'sí']] * 2  # transversal + guard fórmula
    assert rows[4][5:] == ['MF0825_2', '', '180', 'UC0825_2', '', '', '', '']  # MF sense UF
    assert rows[5][5:8] == ['MP0183', 'Mòdul de pràctiques professionals no laborals', '80']


def test_certificat_loe_sense_annex_cau_a_les_uc_sense_hores(client):
    rows = _csv(client.get('/api/export/estructura', query_string={'refs': 'ELEM0311'}))
    assert rows[1][4:] == ['500', 'MF1978_2', 'Mòdul sense UF', '', 'UC1978_2', '', '', '', '']


def test_certificat_lomloe_files_per_a(client):
    rows = _csv(client.get('/api/export/estructura', query_string={'refs': 'ELE_C_001_2'}))
    assert len(rows) == 2
    assert rows[1][5:] == ['ELE_B_3001', 'Mòdul B nou', '', '', 'ELE_A_3001_01', 'Unitat A nova', '', 'no']


def test_cicle_una_fila_per_modul_i_uc(client):
    rows = _csv(client.get('/api/export/estructura', query_string={'refs': REF_TEL}))
    assert rows[0][4:] == ['Codi mòdul', 'Nom mòdul', 'UC', "Grup d'UC que el convalida",
                           'Certificats LOE del grup', 'Decret']
    assert [r[4:] for r in rows[1:3]] == [
        ['0362', 'Instalaciones eléctricas básicas', uc, 'UC0820_2 + UC0821_2', 'ELEE0109', 'BOE-A-2009-1']
        for uc in ('UC0820_2', 'UC0821_2')]
    assert rows[3][4:] == ['', 'Electrónica', '', '', '', 'BOE-A-2009-1']  # mòdul sense UC: una fila


@pytest.mark.parametrize('refs,status', [
    ('', 400), ('NO-EXISTEIX', 404), ('ELEE0109,' + REF_TEL, 400), ('mal ref!', 400),
    (','.join(f'X{i:04d}' for i in range(101)), 400)])
def test_errors(client, refs, status):
    assert client.get('/api/export/estructura', query_string={'refs': refs}).status_code == status
