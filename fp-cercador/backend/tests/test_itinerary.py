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

RECORDS_LOE = [
    {'grado': 'A', 'codigo': 'UF0038', 'denominacion': 'Aprovisionamiento', 'nivel': 1, 'familia': 'AGA'},
    {'grado': 'B', 'codigo': 'MF0038_3', 'denominacion': 'Análisis enológico', 'nivel': 3, 'familia': 'AGA'},
]


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


def test_build_ab_index_loe():
    idx = itinerary.build_ab_index(RECORDS_LOE)
    assert '0038' in idx['b_by_uf_num']
    assert idx['b_by_uf_num']['0038']['codigo'] == 'MF0038_3'


def test_get_parent_b_loe():
    idx = itinerary.build_ab_index(RECORDS_LOE)
    a_rec = {'grado': 'A', 'codigo': 'UF0038'}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is not None
    assert parent['codigo'] == 'MF0038_3'


def test_get_parent_b_invalid_codigo():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': None}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is None
