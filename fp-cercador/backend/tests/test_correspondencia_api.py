"""test_correspondencia_api.py — GET /api/correspondencia (Pla 091)."""
import json

import pytest

import app as app_module

flask_app = app_module.app
flask_app.config["TESTING"] = True

ELE = 'Electricidad y Electrónica'
URL_IEA = ('https://www.todofp.es/que-estudiar/familias-profesionales/electricidad-electronica/'
           'instalaciones-electricas-automaticas.html')
URL_TEL = ('https://www.todofp.es/que-estudiar/familias-profesionales/electricidad-electronica/'
           'instalaciones-telecomunicaciones.html')
URL_JOY = 'https://www.todofp.es/que-estudiar/familias-profesionales/fabricacion-mecanica/joyeria.html'
REF_IEA = 'electricidad-electronica~instalaciones-electricas-automaticas'
REF_TEL = 'electricidad-electronica~instalaciones-telecomunicaciones'


def _m(num, name):
    return {'num': num, 'name': name}


IEA_2008 = [
    {'uc': ['UC0822_2'], 'moduls': [_m('0232', 'Automatismos industriales'), _m('0238', 'Instalaciones domóticas')]},
    {'uc': ['UC0825_2'], 'moduls': [_m('0240', 'Máquinas eléctricas')]},
    {'uc': ['UC0820_2', 'UC0821_2'], 'moduls': [_m('0235', 'Instalaciones eléctricas interiores')]},
    {'uc': ['UC0823_2', 'UC0824_2'], 'moduls': [_m('0236', 'Instalaciones de distribución')]},
    {'uc': ['UC0836_2', 'UC0837_2'], 'moduls': [_m('0239', 'Instalaciones solares fotovoltaicas')]},
    {'uc': ['UC0120_2', 'UC0121_2'], 'moduls': [_m('0237', 'Infraestructuras comunes de telecomunicación')]},
]
IEA_2024 = [{'uc': ['UC2343_2'], 'moduls': [_m('0232', 'Automatismos industriales')]}]
CORR = {
    REF_IEA: {'decret': 'BOE-A-2008-3957', 'vigent': 'BOE-A-2024-10684', 'convalida': IEA_2024,
              'convalida_anterior': IEA_2008, 'notes': ['Nota del decret.'],
              'acredita': [{'moduls': [_m('0232', 'Automatismos industriales')], 'uc': ['UC2343_2']}]},
    REF_TEL: {'decret': 'BOE-A-2009-1', 'vigent': 'BOE-A-2009-1', 'notes': [], 'acredita': [],
              'convalida': [{'uc': ['UC0120_2', 'UC0121_2'], 'moduls': [_m('0237', 'Infraestructuras comunes')]},
                            {'uc': ['UC0820_2', 'UC9000_2'], 'moduls': [_m('0362', 'Instalaciones eléctricas básicas')]}]},
}


def _cataleg():
    base = [
        {'grado': 'C', 'codigo': 'ELEE0109', 'denominacion': 'Montaje de instalaciones de baja tensión',
         'plan_antiguo': True},
        {'grado': 'C', 'codigo': 'ELE_C_001_2', 'denominacion': 'Un certificat del pla nou'},
        {'grado': 'D', 'codigo': None, 'denominacion': 'Técnico en Instalaciones Eléctricas y Automáticas',
         'ficha_url': URL_IEA},
        {'grado': 'D', 'codigo': None, 'denominacion': 'Técnico en Instalaciones de Telecomunicaciones',
         'ficha_url': URL_TEL},
        {'grado': 'D', 'codigo': None, 'denominacion': 'Técnico en Joyería',
         'ficha_url': URL_JOY},
    ]
    return [{'familia': ELE, 'nivel': 2, 'plan_antiguo': False, **r, 'id': i} for i, r in enumerate(base, start=1)]


@pytest.fixture
def paths(tmp_path, monkeypatch):
    contingut = {
        'DATA_PATH': _cataleg(),
        'D_UC_CORR_PATH': CORR,
        'BC_LOE_PATH': {'ELEE0109': ['UC0820_2', 'UC0821_2', 'UC0822_2', 'UC0823_2', 'UC0824_2', 'UC0825_2']},
        'CICLOS_PATH': {'ELEE0109': [{'denominacion': 'Instalaciones de Telecomunicaciones', 'familia': ELE,
                                      'ficha_url': URL_TEL},
                                     {'denominacion': 'Joyería', 'familia': ELE, 'ficha_url': URL_JOY}]},
        'D_MODULOS_PATH': {'3': {'modulos': [
            {'num': None, 'name': n} for n in (
                'Automatismos industriales', 'Instalaciones domóticas', 'Máquinas eléctricas',
                'Instalaciones eléctricas interiores', 'Instalaciones de distribución',
                'Instalaciones solares fotovoltaicas', 'Infraestructuras comunes de telecomunicación',
                'Electrónica', 'Incluye una fase de formación en empresa')]}},
    }
    out = {}
    for attr, data in contingut.items():
        out[attr] = tmp_path / f'{attr}.json'
        out[attr].write_text(json.dumps(data), encoding='utf-8')
        monkeypatch.setattr(app_module, attr, str(out[attr]))
    monkeypatch.setattr(app_module, 'UC_CORR_OVERRIDES_PATH', str(tmp_path / 'overrides.json'))
    for cache in ('_d_modulos_cache', '_d_uc_corr_cache', '_ciclos_fp_cache', '_bc_lomloe_cache', '_c_modulos_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_itinerary_graph_cache', {'key': None, 'data': None})
    for attr in ('BC_LOMLOE_PATH', 'C_MODULOS_PATH', 'A_LOE_PARES_PATH', 'CE_ACCES_PATH'):
        monkeypatch.setattr(app_module, attr, str(tmp_path / f'{attr}-absent.json'))
    monkeypatch.setattr(app_module, '_catalog_cache', {'key': None, 'data': None})
    return out


@pytest.fixture
def client(paths):
    return flask_app.test_client()


def test_cicle_dona_les_taules_i_els_moduls_amb_numero(client):
    body = client.get('/api/correspondencia', query_string={'cicle': REF_IEA}).json
    assert body['cicle'] == {'ref': REF_IEA, 'denominacion': 'Técnico en Instalaciones Eléctricas y Automáticas',
                             'nivel': 2, 'familia': ELE}
    assert (body['decret'], body['vigent']) == ('BOE-A-2008-3957', 'BOE-A-2024-10684')
    assert body['convalida'] == IEA_2024 and body['convalida_anterior'] == IEA_2008
    assert body['notes'] == ['Nota del decret.']
    # El número surt de la taula vigent; la nota de la fitxa no és un mòdul.
    assert body['moduls'][0] == {'num': '0232', 'name': 'Automatismos industriales'}
    assert body['moduls'][1] == {'num': None, 'name': 'Instalaciones domóticas'}
    assert len(body['moduls']) == 8


def test_cicle_sense_taula_dona_llistes_buides(client):
    body = client.get('/api/correspondencia', query_string={'cicle': 'fabricacion-mecanica~joyeria'}).json
    assert (body['decret'], body['vigent'], body['convalida'], body['acredita']) == (None, None, [], [])


def test_cp_cas_de_referencia_elee0109(client):
    body = client.get('/api/correspondencia', query_string={'cp': 'ELEE0109'}).json
    assert body['cp']['codigo'] == 'ELEE0109' and len(body['cp']['uc']) == 6
    tel, iea = body['cicles']  # la taula vigent va davant de la substituïda
    assert iea['ref'] == REF_IEA
    assert iea['derogada'] is True and iea['substituida_per'] == 'BOE-A-2024-10684'
    assert iea['moduls_convalidats'] == ['0232', '0238', '0240', '0235', '0236']
    assert iea['a_mitges'] == []
    assert (iea['moduls_cicle'], iea['moduls_pendents']) == (8, 3)
    assert iea['uc'] == ['UC0822_2', 'UC0825_2', 'UC0820_2', 'UC0821_2', 'UC0823_2', 'UC0824_2']

    assert tel['ref'] == REF_TEL and tel['derogada'] is False
    assert tel['moduls_convalidats'] == [] and tel['uc'] == ['UC0820_2']
    assert tel['a_mitges'] == [{'moduls': [_m('0362', 'Instalaciones eléctricas básicas')],
                                'uc': ['UC0820_2', 'UC9000_2'], 'falten': ['UC9000_2']}]
    assert (tel['moduls_cicle'], tel['moduls_pendents']) == (None, None)


def test_les_uc_corregides_manen_sobre_bc_loe(client, tmp_path):
    (tmp_path / 'overrides.json').write_text(json.dumps({'_doc': 'x', 'ELEE0109': ['UC0825_2']}), encoding='utf-8')
    body = client.get('/api/correspondencia', query_string={'cp': 'ELEE0109'}).json
    assert body['cp']['uc'] == ['UC0825_2']
    assert [c['moduls_convalidats'] for c in body['cicles']] == [['0240']]


def test_el_fitxer_de_correccions_del_repo_es_valid():
    with open(app_module.UC_CORR_OVERRIDES_PATH, encoding='utf-8') as f:
        data = json.load(f)
    codes = [uc for cp, ucs in data.items() if cp != '_doc' for uc in ucs]
    assert codes and all(isinstance(uc, str) and uc.startswith('UC') for uc in codes)


def test_sense_index_el_certificat_no_te_cicles(client, paths):
    paths['D_UC_CORR_PATH'].unlink()
    assert client.get('/api/correspondencia', query_string={'cp': 'ELEE0109'}).json['cicles'] == []


@pytest.mark.parametrize('query, status', [
    ({}, 400),
    ({'cicle': REF_IEA, 'cp': 'ELEE0109'}, 400),
    ({'cicle': 'no vàlid!'}, 400),
    ({'cp': 'elee0109'}, 400),
    ({'cicle': 'electricidad-electronica~no-existeix'}, 404),
    ({'cicle': 'ELEE0109'}, 404),        # no és un cicle
    ({'cp': 'ELE_C_001_2'}, 404),        # certificat del pla nou: no va per UC
    ({'cp': 'XXXX0000'}, 404),
])
def test_parametres_dolents(client, query, status):
    assert client.get('/api/correspondencia', query_string=query).status_code == status


def test_cataleg_illegible_dona_503(client, paths):
    paths['DATA_PATH'].write_text('{', encoding='utf-8')
    assert client.get('/api/correspondencia', query_string={'cicle': REF_IEA}).status_code == 503


# ---------------------------------------------------------------------------
# Pla 092: certificats per UC, arestes de l'itinerari i «Què em falta?»
# ---------------------------------------------------------------------------

def test_cicle_dona_els_certificats_de_cada_uc_de_les_taules_vigents(client):
    body = client.get('/api/correspondencia', query_string={'cicle': REF_TEL}).json
    assert body['certificats'] == {'UC0820_2': [{'codigo': 'ELEE0109', 'ref': 'ELEE0109',
                                                 'denominacion': 'Montaje de instalaciones de baja tensión'}]}
    # A la taula vigent del cicle d'instal·lacions elèctriques no hi ha cap UC del certificat.
    assert client.get('/api/correspondencia', query_string={'cicle': REF_IEA}).json['certificats'] == {}


def test_itinerari_les_arestes_del_certificat_porten_la_correspondencia(client):
    body = client.get('/api/itinerari/complet', query_string={'grado': 'C', 'ref': 'ELEE0109'}).json
    edges = {e['to']: e for e in body['edges'] if e['kind'] == 'cd'}
    assert edges['D:' + REF_IEA] == {'from': 'C:ELEE0109', 'to': 'D:' + REF_IEA, 'kind': 'cd',
                                     'conv': 5, 'mods': 8, 'derogada': True}
    assert (edges['D:' + REF_TEL]['conv'], edges['D:' + REF_TEL]['derogada']) == (0, False)
    # El cicle que només ve de ciclos_fp.json es manté, sense detall.
    assert edges['D:fabricacion-mecanica~joyeria'] == {
        'from': 'C:ELEE0109', 'to': 'D:fabricacion-mecanica~joyeria', 'kind': 'cd'}


def test_que_em_falta_dona_convalidacions_i_deixa_relacionats_per_als_cicles_sense_taula(client):
    body = client.post('/api/que-em-falta', json={'refs': ['ELEE0109']}).json
    assert [(c['ref'], c['derogada'], c['moduls_convalidats']) for c in body['convalidacions']] == [
        (REF_TEL, False, []), (REF_IEA, True, ['0232', '0238', '0240', '0235', '0236'])]
    assert [r['denominacion'] for r in body['relacionats']] == ['Joyería']
    assert body['objectius'] == []


def test_que_em_falta_sense_graus_del_pla_antic_no_te_convalidacions(client):
    body = client.post('/api/que-em-falta', json={'refs': [REF_TEL]}).json
    assert body['convalidacions'] == []


def test_que_em_falta_no_proposa_un_cicle_que_ja_es_te(client):
    body = client.post('/api/que-em-falta', json={'refs': ['ELEE0109', REF_IEA]}).json
    assert [c['ref'] for c in body['convalidacions']] == [REF_TEL]
