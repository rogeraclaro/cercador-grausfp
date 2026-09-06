"""
test_cd_lomloe.py — Derivació pura C LOMLOE → [cicles D] via mòduls compartits
de la mateixa família (Pla 058).
"""
import json
import pathlib

from cd_lomloe import normalize_module_name, build_c_lomloe_to_d

_OUTPUTS = pathlib.Path(__file__).resolve().parents[2] / 'plans' / 'outputs'


def _c(codigo, familia):
    return {'id': None, 'codigo': codigo, 'grado': 'C', 'plan_antiguo': False,
            'denominacion': codigo, 'familia': familia, 'nivel': 3}


def _b(codigo, denominacion, familia='Hostelería y Turismo'):
    return {'id': None, 'codigo': codigo, 'grado': 'B', 'plan_antiguo': False,
            'denominacion': denominacion, 'familia': familia, 'nivel': 2}


def _d(id_, familia, modulos):
    return {'id': id_, 'codigo': None, 'grado': 'D', 'plan_antiguo': False,
            'denominacion': f'T.S. {id_}', 'familia': familia, 'nivel': 3}, \
           {str(id_): {'modulos': modulos, 'ensenanzaFP': None}}


def test_normalize():
    assert normalize_module_name('Inglés Profesional (Grado Superior)') == 'ingles profesional'
    assert normalize_module_name('Estructura del mercado turístico.') == 'estructura del mercado turistico'
    assert normalize_module_name('Protocolo y relaciones públicas') == 'protocolo y relaciones publicas'


def test_c_a_d_per_nom_mateixa_familia():
    d_rec, d_mod = _d(700, 'Hostelería y Turismo',
                      [{'num': None, 'name': 'Estructura del mercado turístico.'}])
    records = [
        _c('HOT_C_005_5B', 'Hostelería y Turismo'),
        _b('HOT_B_0171', 'Estructura del mercado turístico'),
        d_rec,
    ]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171']}
    assert build_c_lomloe_to_d(records, bc_lomloe, d_mod) == {
        'HOT_C_005_5B': [{'id': 700, 'shared': 1, 'total': 1}]
    }


def test_c_a_d_per_codi():
    d_rec, d_mod = _d(700, 'Hostelería y Turismo',
                      [{'num': '0171', 'name': 'qualsevol'}])
    records = [
        _c('HOT_C_005_5B', 'Hostelería y Turismo'),
        _b('HOT_B_0171', 'Estructura del mercado turístico'),
        d_rec,
    ]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171']}
    assert build_c_lomloe_to_d(records, bc_lomloe, d_mod) == {
        'HOT_C_005_5B': [{'id': 700, 'shared': 1, 'total': 1}]
    }


def test_ignora_altra_familia():
    d_rec, d_mod = _d(700, 'Comercio y Marketing',
                      [{'num': None, 'name': 'Estructura del mercado turístico.'}])
    records = [
        _c('HOT_C_005_5B', 'Hostelería y Turismo'),
        _b('HOT_B_0171', 'Estructura del mercado turístico'),
        d_rec,
    ]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171']}
    assert build_c_lomloe_to_d(records, bc_lomloe, d_mod) == {}


def test_ordena_per_fraccio_i_calcula_total():
    d1_rec, d1_mod = _d(1, 'Hostelería y Turismo',
                        [{'num': '0171', 'name': 'x'}, {'num': '0172', 'name': 'y'}])
    d2_rec, d2_mod = _d(2, 'Hostelería y Turismo', [{'num': '0171', 'name': 'x'}])
    records = [
        _c('HOT_C_005_5B', 'Hostelería y Turismo'),
        _b('HOT_B_0171', 'A'),
        _b('HOT_B_0172', 'B'),
        d1_rec, d2_rec,
    ]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171', 'HOT_B_0172']}
    d_modulos = {**d1_mod, **d2_mod}
    assert build_c_lomloe_to_d(records, bc_lomloe, d_modulos) == {
        'HOT_C_005_5B': [
            {'id': 1, 'shared': 2, 'total': 2},
            {'id': 2, 'shared': 1, 'total': 2},
        ]
    }


def test_fixture_real_cobertura():
    d_plans = json.loads((_OUTPUTS / 'spike_d_plans.json').read_text(encoding='utf-8'))['d']
    c_mods = json.loads((_OUTPUTS / 'spike_043_c_lomloe_modulos.json').read_text(encoding='utf-8'))['c']

    FAM = 'Hostelería y Turismo'
    c_code = 'HOT_C_005_5B'
    c_modulos = c_mods[c_code]['modulos']

    # bc_lomloe: cada mòdul del C amb num → un B LOMLOE de la seva família,
    # excepte transversals sense B (1782 PRL).
    b_codes = [f'HOT_B_{m["num"]}' for m in c_modulos if m['num'] and m['num'] != '1782']
    records = [_c(c_code, FAM)]
    for m in c_modulos:
        if m['num'] and m['num'] != '1782':
            records.append(_b(f'HOT_B_{m["num"]}', m['nombre'], FAM))

    d_modulos = {}
    for did, dv in d_plans.items():
        if dv['familia'] == FAM:
            d_modulos[did] = {'modulos': dv['modulos'], 'ensenanzaFP': None}
            records.append({'id': int(did), 'codigo': None, 'grado': 'D',
                            'plan_antiguo': False, 'denominacion': dv['denominacion'],
                            'familia': FAM, 'nivel': 3})

    result = build_c_lomloe_to_d(records, {c_code: b_codes}, d_modulos)
    entries = result[c_code]
    assert entries[0]['shared'] == entries[0]['total'] == 5
    first_den = next(r['denominacion'] for r in records
                     if r['grado'] == 'D' and r['id'] == entries[0]['id'])
    assert 'Agencias de Viajes' in first_den
