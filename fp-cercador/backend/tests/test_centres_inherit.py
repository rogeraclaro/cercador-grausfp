"""
test_centres_inherit.py — Herència de centres A/B LOE via certificat C pare (Pla 056).

Sense fitxers ni xarxa: dades inline.
"""
import itinerary
from centres_inherit import build_inherited


def _rec(id_, codigo, grado, plan_antiguo=True):
    return {'id': id_, 'codigo': codigo, 'grado': grado, 'plan_antiguo': plan_antiguo}


def _run(records, bc_loe_inverse, oferta_centres):
    ab_index = itinerary.build_ab_index(records)
    return build_inherited(records, ab_index, bc_loe_inverse, oferta_centres)


def test_b_loe_hereta_unio_de_c_pares():
    records = [_rec(10, 'MF0969_1', 'B')]
    inverse = {'UC0969_1': ['ADGG0408', 'ADGD0308']}
    oferta_centres = {'ADGG0408': ['x', 'y'], 'ADGD0308': ['z', 'y']}

    assert _run(records, inverse, oferta_centres) == {'10': ['x', 'y', 'z']}


def test_a_loe_hereta_via_b():
    records = [_rec(20, 'UF0038', 'A'), _rec(21, 'MF0038_3', 'B')]
    inverse = {'UC0038_3': ['HOTA0108']}
    oferta_centres = {'HOTA0108': ['c1', 'c2']}

    result = _run(records, inverse, oferta_centres)

    assert result['20'] == ['c1', 'c2']
    assert result['21'] == ['c1', 'c2']


def test_sense_c_pare_no_apareix():
    records = [_rec(30, 'MF1234_9', 'B')]

    assert _run(records, {}, {'ADGG0408': ['x']}) == {}


def test_c_pare_sense_centres_no_apareix():
    records = [_rec(31, 'MF0969_1', 'B')]
    inverse = {'UC0969_1': ['ADGG0408']}

    assert _run(records, inverse, {'ADGG0408': []}) == {}


def test_ignora_lomloe():
    records = [
        _rec(40, 'ADG_B_3001', 'B', plan_antiguo=False),
        _rec(41, 'ADG_A_3001_01', 'A', plan_antiguo=False),
    ]

    assert _run(records, {'UC0969_1': ['ADGG0408']}, {'ADGG0408': ['x']}) == {}
