"""
test_itinerary.py — Tests per a itinerary.py (derivació A→B local).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import itinerary

RECORDS_LOMLOE = [
    {'grado': 'A', 'codigo': 'ADG_A_3001_01', 'denominacion': 'Preparación equipos', 'nivel': 1, 'familia': 'ADG'},
    {'grado': 'A', 'codigo': 'ADG_A_3001_02', 'denominacion': 'Grabación datos',     'nivel': 1, 'familia': 'ADG'},
    {'grado': 'B', 'codigo': 'ADG_B_3001',    'denominacion': 'Tratamiento datos',   'nivel': 2, 'familia': 'ADG'},
    {'grado': 'B', 'codigo': 'COM_B_3001',    'denominacion': 'Comercio básico',     'nivel': 2, 'familia': 'COM'},
]

# Ampliació 068: el pare d'un A LOE ve de la seva fitxa (a_loe_pares.json), no del
# número: UF0038 → MF0706_1 (no MF0038_3). Alguns UF tenen diversos pares.
RECORDS_LOE = [
    {'grado': 'A', 'codigo': 'UF0038', 'denominacion': 'Aprovisionamiento', 'nivel': 1, 'familia': 'HOT'},
    {'grado': 'A', 'codigo': 'UF0723', 'denominacion': 'Dibujo técnico', 'nivel': 2, 'familia': 'QUI'},
    {'grado': 'A', 'codigo': 'UF0041', 'denominacion': 'Germana de UF0038', 'nivel': 1, 'familia': 'HOT'},
    {'grado': 'B', 'codigo': 'MF0038_3', 'denominacion': 'Análisis enológico', 'nivel': 3, 'familia': 'AGA'},
    {'grado': 'B', 'codigo': 'MF0706_1', 'denominacion': 'Servicio de habitaciones', 'nivel': 1, 'familia': 'HOT'},
    {'grado': 'B', 'codigo': 'MF0326_2', 'denominacion': 'Preparación de máquinas', 'nivel': 2, 'familia': 'QUI'},
    {'grado': 'B', 'codigo': 'MF0333_2', 'denominacion': 'Modelos y moldes', 'nivel': 2, 'familia': 'QUI'},
]
A_LOE_PARES = {
    'UF0038': ['MF0706_1'],
    'UF0723': ['MF0326_2', 'MF0333_2'],
    'UF0041': ['MF0706_1', 'MF9999_9'],   # MF9999_9 no és a ofertes → s'ignora
}


def test_build_ab_index_lomloe():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    assert 'ADG_B_3001' in idx['b_by_code']
    assert 'ADG_B_3001' in idx['a_by_b_code']
    assert len(idx['a_by_b_code']['ADG_B_3001']) == 2


def test_get_parent_b_lomloe():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': 'ADG_A_3001_01'}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is not None
    assert parent['codigo'] == 'ADG_B_3001'


def test_get_parent_b_different_fam_returns_none():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': 'INA_A_9999_01'}  # família no existent
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is None


def test_get_children_a_lomloe():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    b_rec = {'grado': 'B', 'codigo': 'ADG_B_3001'}
    children = itinerary.get_children_a(b_rec, idx)
    assert len(children) == 2
    codigos = {c['codigo'] for c in children}
    assert 'ADG_A_3001_01' in codigos
    assert 'ADG_A_3001_02' in codigos


def test_get_children_a_wrong_fam_empty():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    b_rec = {'grado': 'B', 'codigo': 'COM_B_3001'}  # cap A de COM_3001
    children = itinerary.get_children_a(b_rec, idx)
    assert children == []


def test_get_parent_b_loe_ve_del_mapa_no_del_numero():
    idx = itinerary.build_ab_index(RECORDS_LOE, A_LOE_PARES)
    parent = itinerary.get_parent_b({'grado': 'A', 'codigo': 'UF0038'}, idx)
    assert parent['codigo'] == 'MF0706_1'


def test_get_parents_b_loe_diversos_pares():
    idx = itinerary.build_ab_index(RECORDS_LOE, A_LOE_PARES)
    parents = itinerary.get_parents_b({'grado': 'A', 'codigo': 'UF0723'}, idx)
    assert [p['codigo'] for p in parents] == ['MF0326_2', 'MF0333_2']
    assert itinerary.get_parent_b({'grado': 'A', 'codigo': 'UF0723'}, idx)['codigo'] == 'MF0326_2'


def test_get_parents_b_loe_ignora_pares_absents():
    idx = itinerary.build_ab_index(RECORDS_LOE, A_LOE_PARES)
    parents = itinerary.get_parents_b({'grado': 'A', 'codigo': 'UF0041'}, idx)
    assert [p['codigo'] for p in parents] == ['MF0706_1']


def test_get_parent_b_loe_sense_mapa_es_none():
    # Millor cap pare que un pare fals: sense a_loe_pares no s'endevina pel número.
    idx = itinerary.build_ab_index(RECORDS_LOE)
    assert itinerary.get_parent_b({'grado': 'A', 'codigo': 'UF0038'}, idx) is None
    assert itinerary.get_parents_b({'grado': 'A', 'codigo': 'UF0038'}, idx) == []


def test_get_parents_b_lomloe_es_llista_d_un():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    parents = itinerary.get_parents_b({'grado': 'A', 'codigo': 'ADG_A_3001_01'}, idx)
    assert [p['codigo'] for p in parents] == ['ADG_B_3001']


def test_get_children_a_loe_reals():
    idx = itinerary.build_ab_index(RECORDS_LOE, A_LOE_PARES)
    children = itinerary.get_children_a({'grado': 'B', 'codigo': 'MF0706_1'}, idx)
    assert [c['codigo'] for c in children] == ['UF0038', 'UF0041']
    assert itinerary.get_children_a({'grado': 'B', 'codigo': 'MF0038_3'}, idx) == []


def test_get_parent_b_invalid_codigo():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': None}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is None


RECORDS_B_LOE_UC = [
    {'grado': 'B', 'codigo': 'MF0038_3', 'denominacion': 'Análisis enológico', 'nivel': 3, 'familia': 'AGA'},
    {'grado': 'B', 'codigo': 'MF0969_1', 'denominacion': 'Gestión contable',   'nivel': 1, 'familia': 'ADG'},
]


def test_build_ab_index_b_by_uc_present():
    idx = itinerary.build_ab_index(RECORDS_B_LOE_UC)
    assert 'b_by_uc' in idx
    assert 'UC0038_3' in idx['b_by_uc']
    assert idx['b_by_uc']['UC0038_3']['codigo'] == 'MF0038_3'


def test_build_ab_index_b_by_uc_maps_level():
    idx = itinerary.build_ab_index(RECORDS_B_LOE_UC)
    assert 'UC0969_1' in idx['b_by_uc']
    assert idx['b_by_uc']['UC0969_1']['codigo'] == 'MF0969_1'
    # UC0038_3 NO ha de correspondre a UC0038_1 (els nivells no es barregen)
    assert 'UC0038_1' not in idx['b_by_uc']


RECORDS_C_LOE = [
    {'grado': 'C', 'codigo': 'COML0110', 'denominacion': 'Gestió comptable', 'nivel': 2,
     'familia': 'COM', 'plan_antiguo': True},
    {'grado': 'C', 'codigo': 'ADGG0408', 'denominacion': 'Gestió comptable avançada', 'nivel': 3,
     'familia': 'ADG', 'plan_antiguo': True},
    {'grado': 'C', 'codigo': 'FAKELOMLOE', 'denominacion': 'LOMLOE cert', 'nivel': 2,
     'familia': 'ADG', 'plan_antiguo': False},  # NO ha d'aparèixer
]


def test_build_ab_index_c_loe_by_code():
    idx = itinerary.build_ab_index(RECORDS_C_LOE)
    assert 'c_loe_by_code' in idx
    assert 'COML0110' in idx['c_loe_by_code']
    assert 'ADGG0408' in idx['c_loe_by_code']
    # C LOMLOE (plan_antiguo=False) NO ha d'estar a l'índex
    assert 'FAKELOMLOE' not in idx['c_loe_by_code']


def test_build_ab_index_inclou_c_lomloe_by_code():
    """Pla 057: l'índex exposa els C LOMLOE per codi (per serialitzar-los a /api/itinerari)."""
    records = [
        {'grado': 'C', 'codigo': 'HOT_C_005_5B', 'plan_antiguo': False},
        {'grado': 'C', 'codigo': 'ADGG0408', 'plan_antiguo': True},
    ]
    idx = itinerary.build_ab_index(records)
    assert list(idx['c_lomloe_by_code']) == ['HOT_C_005_5B']
    assert list(idx['c_loe_by_code']) == ['ADGG0408']
