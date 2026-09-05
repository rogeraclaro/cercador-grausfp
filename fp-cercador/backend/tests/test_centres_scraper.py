"""
test_centres_scraper.py — Tests del scraper de centres (Pla 055).

Sense xarxa: _bootstrap/_fetch/_save mockejats, _OFERTES_PATH a tmp_path.
"""
import json

import pytest

from scrapers import centres_scraper as cs


_FAKE_ROW = [
    '2800000577', 'M280006203G', 'TAJAMAR', 'Madrid', '28038', 'MADRID',
    '', 'MADRID', 'Calle Pio Felipe 12', '914783498', 'jaruiz@tajamar.es',
    '0', 'C',
]


def _rec(id_, codigo, grado, plan_antiguo, denominacion='X'):
    return {
        'id': id_, 'codigo': codigo, 'grado': grado,
        'plan_antiguo': plan_antiguo, 'denominacion': denominacion,
        'familia': 'F', 'nivel': 1, 'observaciones': '',
    }


@pytest.fixture
def ofertes_path(tmp_path, monkeypatch):
    path = tmp_path / 'ofertes.json'
    monkeypatch.setattr(cs, '_OFERTES_PATH', str(path))
    return path


@pytest.fixture
def no_network(monkeypatch):
    calls = []

    def fake_fetch(session, params, timeout=60):
        calls.append(dict(params))
        return [list(_FAKE_ROW)]

    monkeypatch.setattr(cs, '_bootstrap', lambda: object())
    monkeypatch.setattr(cs, '_fetch', fake_fetch)
    monkeypatch.setattr(cs, '_save', lambda *a, **k: None)
    monkeypatch.setattr(cs, 'RATE_LIMIT_SEC', 0)
    return calls


def test_load_ofertes_separa_c_lomloe(ofertes_path):
    ofertes_path.write_text(json.dumps([
        _rec(1, 'ADGG0408', 'C', True),
        _rec(2, 'ADG_C_001_3B', 'C', False),
        _rec(3, 'D1', 'D', False),
        _rec(4, 'E1', 'E', False),
        _rec(5, 'ADG_A_3001_01', 'A', False),
    ]), encoding='utf-8')

    c_loe, c_lomloe, d_list, e_list = cs._load_ofertes()

    assert [r['codigo'] for r in c_loe] == ['ADGG0408']
    assert [r['codigo'] for r in c_lomloe] == ['ADG_C_001_3B']
    assert [r['codigo'] for r in d_list] == ['D1']
    assert [r['codigo'] for r in e_list] == ['E1']


def test_scrape_centres_c_lomloe_usa_ofertacodigo_i_clau_id(ofertes_path, no_network):
    ofertes_path.write_text(json.dumps([
        _rec(11683, 'ADG_C_001_3B', 'C', False),
    ]), encoding='utf-8')

    centres_by_id, oferta_centres = cs.scrape_centres()

    assert len(no_network) == 1
    params = no_network[0]
    assert params['ofertaCodigo'] == 'ADG_C_001_3B'
    assert 'gradoProfesional' not in params
    assert 'ofertaDenominacion' not in params
    assert oferta_centres == {'11683': ['M280006203G']}
    assert 'ADG_C_001_3B' not in oferta_centres
    assert centres_by_id['M280006203G']['nombre'] == 'TAJAMAR'


def test_report_phase_c_lomloe(ofertes_path, no_network):
    ofertes_path.write_text(json.dumps([
        _rec(11683, 'ADG_C_001_3B', 'C', False),
    ]), encoding='utf-8')
    phases = []

    cs.scrape_centres(on_progress=lambda phase, cur, tot, uniq: phases.append((phase, cur, tot)))

    assert ('Grau C (pla nou)', 0, 1) in phases
    assert ('Grau C (pla nou)', 1, 1) in phases
