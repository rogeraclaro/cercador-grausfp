"""
test_itinerari_complet.py — /api/itinerari/complet retorna la cadena sencera
A→B→C→D(→E) com a nodes + arestes (Pla 071). Fitxers aïllats a tmp_path.
"""
import json
import os

import pytest

import app as app_module

FAM = 'Administración y Gestión'
FAB = 'Fabricación Mecánica'


def _rec(id_, codigo, grado, plan_antiguo=False, denominacion='X', familia=FAM, ficha_url=None,
         ref=None):
    r = {'id': id_, 'codigo': codigo, 'grado': grado, 'plan_antiguo': plan_antiguo,
         'denominacion': denominacion, 'familia': familia, 'nivel': 1}
    if ficha_url is not None:
        r['ficha_url'] = ficha_url
    if ref is not None:
        r['ref'] = ref
    return r


URL_D_SA = 'https://www.todofp.es/que-estudiar/familias/servicios-administrativos.html'

OFERTES = [
    # LOMLOE: A → B → C
    _rec(1, 'ADG_A_3001_01', 'A'),
    _rec(2, 'ADG_A_3001_02', 'A'),
    _rec(3, 'ADG_A_3002_01', 'A'),
    _rec(4, 'ADG_B_3001', 'B'),
    _rec(5, 'ADG_B_3002', 'B'),
    _rec(6, 'ADG_C_001_3B', 'C', denominacion='Actividades de grabación'),
    # D (sense codi; clau de node = ref, Pla 076)
    _rec(12776, None, 'D', denominacion='Título Profesional Básico en Servicios Administrativos',
         ficha_url=URL_D_SA),
    _rec(12800, None, 'D', denominacion='Técnico en Mecanizado', familia=FAB,
         ficha_url='javascript:alert(1)', ref='fabricacion-mecanica~mecanizado'),
    # LOE: A amb dos B pare, cadascun en un C diferent
    _rec(20, 'UF0723', 'A', plan_antiguo=True, familia=FAB),
    _rec(21, 'MF0326_2', 'B', plan_antiguo=True, familia=FAB),
    _rec(22, 'MF0333_2', 'B', plan_antiguo=True, familia=FAB),
    _rec(23, 'FMEF0108', 'C', plan_antiguo=True, familia=FAB),
    _rec(24, 'FMEF0208', 'C', plan_antiguo=True, familia=FAB),
    # C LOE amb ciclos_fp: un cicle resolt per ficha_url, un altre no resolt
    _rec(30, 'UF0510', 'A', plan_antiguo=True),
    _rec(31, 'MF0973_1', 'B', plan_antiguo=True),
    _rec(32, 'ADGG0408', 'C', plan_antiguo=True),
]
A_LOE_PARES = {'UF0723': ['MF0326_2', 'MF0333_2'], 'UF0510': ['MF0973_1']}
BC_LOE = {'FMEF0108': ['UC0326_2'], 'FMEF0208': ['UC0333_2'], 'ADGG0408': ['UC0973_1']}
BC_LOMLOE = {'ADG_C_001_3B': ['ADG_B_3001', 'ADG_B_3002']}
D_MODULOS = {'12776': {'modulos': [{'num': '3001', 'name': 'a'}, {'num': '3002', 'name': 'b'}]}}
CICLOS_FP = {
    # Esquema, host i barra final diferents dels del registre D: ha de resoldre igualment.
    'ADGG0408': [
        {'denominacion': 'Servicios Administrativos', 'familia': FAM,
         'ficha_url': 'http://TODOFP.es/que-estudiar/familias/servicios-administrativos.html/'},
        {'denominacion': 'Cicle Inexistent', 'familia': FAM, 'ficha_url': None},
    ],
    # Sense ficha_url: es resol per denominació normalitzada + família.
    'FMEF0108': [{'denominacion': 'Mecanizado', 'familia': FAB, 'ficha_url': None}],
}


# Claus de node dels D (Pla 076: per ref, no per id)
D_SA = 'D:familias~servicios-administrativos'
D_MEC = 'D:fabricacion-mecanica~mecanizado'


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    files = {
        'ofertes': ('DATA_PATH', OFERTES),
        'a_loe_pares': ('A_LOE_PARES_PATH', A_LOE_PARES),
        'bc_loe': ('BC_LOE_PATH', BC_LOE),
        'bc_lomloe': ('BC_LOMLOE_PATH', BC_LOMLOE),
        'd_modulos': ('D_MODULOS_PATH', D_MODULOS),
        'ciclos': ('CICLOS_PATH', CICLOS_FP),
    }
    paths = {}
    for name, (attr, content) in files.items():
        p = tmp_path / f'{name}.json'
        p.write_text(json.dumps(content), encoding='utf-8')
        monkeypatch.setattr(app_module, attr, str(p))
        paths[name] = p
    monkeypatch.setattr(app_module, 'CE_ACCES_PATH', str(tmp_path / 'ce_acces.json'))
    for cache in ('_itinerary_index_cache', '_a_loe_pares_cache', '_bc_lomloe_cache',
                  '_d_modulos_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_cd_lomloe_cache', {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_itinerary_graph_cache', {'key': None, 'data': None})
    return paths


@pytest.fixture
def client(data_dir):
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _get(client, qs):
    resp = client.get(f'/api/itinerari/complet?{qs}')
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def _keys(body):
    return {n['key'] for n in body['nodes']}


def _edges(body):
    return {(e['from'], e['to'], e['kind']) for e in body['edges']}


def test_c_lomloe_cadena_completa(client):
    body = _get(client, 'grado=C&codigo=ADG_C_001_3B')
    assert body['focus'] == 'C:ADG_C_001_3B'
    assert _keys(body) == {
        'C:ADG_C_001_3B', 'B:ADG_B_3001', 'B:ADG_B_3002',
        'A:ADG_A_3001_01', 'A:ADG_A_3001_02', 'A:ADG_A_3002_01', D_SA,
    }
    assert _edges(body) == {
        ('A:ADG_A_3001_01', 'B:ADG_B_3001', 'ab'), ('A:ADG_A_3001_02', 'B:ADG_B_3001', 'ab'),
        ('A:ADG_A_3002_01', 'B:ADG_B_3002', 'ab'),
        ('B:ADG_B_3001', 'C:ADG_C_001_3B', 'bc'), ('B:ADG_B_3002', 'C:ADG_C_001_3B', 'bc'),
        ('C:ADG_C_001_3B', D_SA, 'cd'),
    }
    cd = next(e for e in body['edges'] if e['kind'] == 'cd')
    assert (cd['shared'], cd['total']) == (2, 2)
    focus = next(n for n in body['nodes'] if n['key'] == 'C:ADG_C_001_3B')
    assert focus == {
        'key': 'C:ADG_C_001_3B', 'ref': 'ADG_C_001_3B', 'grado': 'C', 'codigo': 'ADG_C_001_3B', 'id': None,
        'denominacion': 'Actividades de grabación', 'familia': FAM, 'nivel': 1,
        'plan_antiguo': False, 'ficha': '/api/ficha-redirect?grado=C&codigo=ADG_C_001_3B',
    }
    d = next(n for n in body['nodes'] if n['key'] == D_SA)
    assert (d['codigo'], d['id'], d['ficha']) == (None, 12776, URL_D_SA)
    assert body['warnings'] == []


def test_a_no_inclou_germans(client):
    body = _get(client, 'grado=A&codigo=ADG_A_3001_01')
    assert _keys(body) == {'A:ADG_A_3001_01', 'B:ADG_B_3001', 'C:ADG_C_001_3B', D_SA}


def test_a_loe_dos_pares_molts_a_molts(client):
    body = _get(client, 'grado=A&codigo=UF0723')
    assert _keys(body) == {'A:UF0723', 'B:MF0326_2', 'B:MF0333_2',
                           'C:FMEF0108', 'C:FMEF0208', D_MEC}
    assert ('B:MF0326_2', 'C:FMEF0108', 'bc') in _edges(body)
    assert ('B:MF0333_2', 'C:FMEF0208', 'bc') in _edges(body)
    # FMEF0108 → D resolt per denominació + família (ciclos_fp sense ficha_url)
    assert ('C:FMEF0108', D_MEC, 'cd') in _edges(body)


def test_d_relacio_inversa_i_descendents(client):
    body = _get(client, 'grado=D&id=12776')
    assert body['focus'] == D_SA
    assert _keys(body) == {
        D_SA, 'C:ADG_C_001_3B', 'C:ADGG0408',
        'B:ADG_B_3001', 'B:ADG_B_3002', 'B:MF0973_1',
        'A:ADG_A_3001_01', 'A:ADG_A_3001_02', 'A:ADG_A_3002_01', 'A:UF0510',
    }
    assert ('C:ADGG0408', D_SA, 'cd') in _edges(body)
    assert not any(e['kind'] == 'de' for e in body['edges'])
    assert body['warnings'] == []


def test_c_loe_ciclos_resolt_i_no_resolt(client):
    body = _get(client, 'grado=C&codigo=ADGG0408')
    assert ('C:ADGG0408', D_SA, 'cd') in _edges(body)
    loe_cd = next(e for e in body['edges'] if e['kind'] == 'cd')
    assert 'shared' not in loe_cd
    assert len(body['warnings']) == 1
    assert 'Cicle Inexistent' in body['warnings'][0]
    assert 'ADGG0408' in body['warnings'][0]


def test_ciclos_fp_absent_avisa(client, data_dir):
    data_dir['ciclos'].unlink()
    body = _get(client, 'grado=C&codigo=ADGG0408')
    assert not any(e['kind'] == 'cd' for e in body['edges'])
    assert any('ciclos_fp.json' in w for w in body['warnings'])


def test_depth_1_nomes_veins_directes(client):
    body = _get(client, 'grado=C&codigo=ADG_C_001_3B&depth=1')
    assert _keys(body) == {'C:ADG_C_001_3B', 'B:ADG_B_3001', 'B:ADG_B_3002', D_SA}
    assert _edges(body) == {
        ('B:ADG_B_3001', 'C:ADG_C_001_3B', 'bc'), ('B:ADG_B_3002', 'C:ADG_C_001_3B', 'bc'),
        ('C:ADG_C_001_3B', D_SA, 'cd'),
    }


@pytest.mark.parametrize('qs', [
    'grado=X&codigo=ADG_C_001_3B',
    'grado=C',
    'grado=C&codigo=adg<script>',
    'grado=C&id=12776',
    'grado=D&id=abc',
    'grado=D&codigo=ADG_C_001_3B',
    'grado=C&codigo=ADG_C_001_3B&depth=2',
])
def test_parametres_invalids_400(client, qs):
    assert client.get(f'/api/itinerari/complet?{qs}').status_code == 400


@pytest.mark.parametrize('qs', [
    'grado=C&codigo=ZZZ_C_999_9',
    'grado=D&id=99999',
    'grado=B&codigo=ADG_C_001_3B',   # existeix, però no és un B
])
def test_grau_inexistent_404(client, qs):
    assert client.get(f'/api/itinerari/complet?{qs}').status_code == 404


def test_ficha_d_no_http_es_null(client):
    body = _get(client, 'grado=D&id=12800')
    assert next(n for n in body['nodes'] if n['key'] == D_MEC)['ficha'] is None


# --- Pla 074: D → E via ce_acces.json ({id_e: {d_ids, unmatched}}) ---------

URL_E = 'https://www.todofp.es/que-estudiar/familias-profesionales/x/ce-curs.html'
E_CURS = 'E:x~ce-curs'


@pytest.fixture
def client_e(data_dir, monkeypatch, tmp_path):
    ofertes = OFERTES + [_rec(13000, None, 'E', denominacion='Curso E', ficha_url=URL_E)]
    data_dir['ofertes'].write_text(json.dumps(ofertes), encoding='utf-8')
    (tmp_path / 'ce_acces.json').write_text(json.dumps({
        # 99999 no existeix: s'ignora sense trencar res.
        '13000': {'d_ids': [12776, 99999], 'unmatched': ['Títol antic']},
    }), encoding='utf-8')
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def test_d_porta_a_e(client_e):
    body = _get(client_e, 'grado=D&id=12776')
    assert (D_SA, E_CURS, 'de') in _edges(body)
    e = next(n for n in body['nodes'] if n['key'] == E_CURS)
    assert (e['grado'], e['id'], e['ficha']) == ('E', 13000, URL_E)


def test_e_focus_mostra_els_seus_d_i_la_cadena(client_e):
    body = _get(client_e, 'grado=E&id=13000')
    assert body['focus'] == E_CURS
    assert (D_SA, E_CURS, 'de') in _edges(body)
    assert {D_SA, 'C:ADG_C_001_3B', 'C:ADGG0408', 'A:UF0510'} <= _keys(body)


def test_c_arriba_fins_a_e(client_e):
    body = _get(client_e, 'grado=C&codigo=ADG_C_001_3B')
    assert (D_SA, E_CURS, 'de') in _edges(body)


def test_ce_acces_canviat_invalida_cache(client_e, tmp_path):
    assert (D_SA, E_CURS, 'de') in _edges(_get(client_e, 'grado=E&id=13000'))
    p = tmp_path / 'ce_acces.json'
    p.write_text(json.dumps({'13000': {'d_ids': [], 'unmatched': []}}), encoding='utf-8')
    st = p.stat()
    os.utime(p, (st.st_atime, st.st_mtime + 10))
    assert not any(e['kind'] == 'de' for e in _get(client_e, 'grado=E&id=13000')['edges'])
