"""
test_centres_inherit.py — Herència de centres A/B LOE via certificat C pare (Pla 056).

Sense fitxers ni xarxa: dades inline.
"""
import itinerary
from centres_inherit import build_inherited


def _rec(id_, codigo, grado, plan_antiguo=True):
    return {'id': id_, 'codigo': codigo, 'grado': grado, 'plan_antiguo': plan_antiguo}


def _run(records, bc_loe_inverse, oferta_centres, a_loe_pares=None):
    ab_index = itinerary.build_ab_index(records, a_loe_pares)
    return build_inherited(records, ab_index, bc_loe_inverse, oferta_centres)


def test_b_loe_hereta_unio_de_c_pares():
    records = [_rec(10, 'MF0969_1', 'B')]
    inverse = {'UC0969_1': ['ADGG0408', 'ADGD0308']}
    oferta_centres = {'ADGG0408': ['x', 'y'], 'ADGD0308': ['z', 'y']}

    assert _run(records, inverse, oferta_centres) == {'10': ['x', 'y', 'z']}


def test_a_loe_hereta_via_b():
    # Ampliació 068: el pare ve de a_loe_pares (fitxa de l'A), no del número.
    records = [_rec(20, 'UF0038', 'A'), _rec(21, 'MF0706_1', 'B')]
    inverse = {'UC0706_1': ['HOTA0108']}
    oferta_centres = {'HOTA0108': ['c1', 'c2']}

    result = _run(records, inverse, oferta_centres, {'UF0038': ['MF0706_1']})

    assert result['20'] == ['c1', 'c2']
    assert result['21'] == ['c1', 'c2']


def test_a_loe_hereta_unio_de_tots_els_pares():
    records = [_rec(22, 'UF0723', 'A'), _rec(23, 'MF0326_2', 'B'), _rec(24, 'MF0333_2', 'B')]
    inverse = {'UC0326_2': ['QUIT0109'], 'UC0333_2': ['QUIT0209']}
    oferta_centres = {'QUIT0109': ['c2', 'c1'], 'QUIT0209': ['c3', 'c1']}

    result = _run(records, inverse, oferta_centres, {'UF0723': ['MF0326_2', 'MF0333_2']})

    assert result['22'] == ['c1', 'c2', 'c3']


def test_a_loe_sense_mapa_no_hereta_pel_numero():
    records = [_rec(25, 'UF0038', 'A'), _rec(26, 'MF0038_3', 'B')]
    inverse = {'UC0038_3': ['HOTA0108']}

    result = _run(records, inverse, {'HOTA0108': ['c1']})

    assert '25' not in result
    assert result['26'] == ['c1']


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


# ---------------------------------------------------------------------------
# Pla 057 — LOMLOE: B FAM_B_NNNN → C via bc_lomloe; clau del C = str(id)
# ---------------------------------------------------------------------------

def _run_lomloe(records, bc_lomloe, oferta_centres):
    ab_index = itinerary.build_ab_index(records)
    return build_inherited(records, ab_index, {}, oferta_centres, bc_lomloe=bc_lomloe)


def test_b_lomloe_hereta_dels_c_lomloe_per_id():
    records = [_rec(50, 'HOT_B_0171', 'B', plan_antiguo=False),
               _rec(60, 'HOT_C_005_5B', 'C', plan_antiguo=False)]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171']}

    assert _run_lomloe(records, bc_lomloe, {'60': ['m2', 'm1']}) == {'50': ['m1', 'm2']}


def test_a_lomloe_hereta_via_b_lomloe():
    records = [_rec(51, 'HOT_A_0171_01', 'A', plan_antiguo=False),
               _rec(50, 'HOT_B_0171', 'B', plan_antiguo=False),
               _rec(60, 'HOT_C_005_5B', 'C', plan_antiguo=False)]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171']}

    result = _run_lomloe(records, bc_lomloe, {'60': ['m1']})

    assert result['51'] == ['m1']
    assert result['50'] == ['m1']


def test_b_lomloe_unio_de_diversos_c():
    records = [_rec(50, 'HOT_B_0179', 'B', plan_antiguo=False),
               _rec(60, 'HOT_C_005_5B', 'C', plan_antiguo=False),
               _rec(61, 'HOT_C_006_5B', 'C', plan_antiguo=False)]
    bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0179'], 'HOT_C_006_5B': ['HOT_B_0179']}

    assert _run_lomloe(records, bc_lomloe, {'60': ['x'], '61': ['y', 'x']}) == {'50': ['x', 'y']}


def test_sense_bc_lomloe_no_trenca_i_loe_segueix():
    records = [_rec(10, 'MF0969_1', 'B'), _rec(50, 'HOT_B_0171', 'B', plan_antiguo=False)]
    ab_index = itinerary.build_ab_index(records)

    result = build_inherited(records, ab_index, {'UC0969_1': ['ADGG0408']}, {'ADGG0408': ['x']})

    assert result == {'10': ['x']}
