"""
test_bc_lomloe_scraper.py — Relació C LOMLOE → [B LOMLOE] via fitxa todofp (Pla 057).

Sense xarxa: _fetch_ficha_html i time.sleep mockejats.
"""
import logging

import pytest

from scrapers import bc_lomloe_scraper as bcs


FICHA_HTML = """
<html><head><title>Buscador FP</title><script>var x = 1;</script></head><body>
<h1>Organización de eventos turísticos</h1>
<p>Código: <strong>HOT_C_005_5B</strong></p>
<h2>Módulos Profesionales</h2>
<ul>
  <li>( 0171 )&nbsp; Estructura del mercado tur&iacute;stico</li>
  <li>( 1782 )&nbsp; Prevención de riesgos laborales</li>
</ul>
<p>Nota: El resto de especificaciones...</p>
</body></html>
"""


def _rec(id_, codigo, grado, ficha_id=None):
    return {'id': id_, 'codigo': codigo, 'grado': grado, 'plan_antiguo': False,
            'ficha_id': ficha_id, 'denominacion': 'X', 'familia': 'F', 'nivel': 1}


RECORDS = [
    _rec(60, 'HOT_C_005_5B', 'C', ficha_id=999),
    _rec(50, 'HOT_B_0171', 'B'),
    _rec(51, 'ADG_B_0171', 'B'),
]


def test_parse_modulos_extreu_numeros_i_noms():
    assert bcs.parse_modulos(FICHA_HTML) == [
        ('0171', 'Estructura del mercado turístico'),
        ('1782', 'Prevención de riesgos laborales'),
    ]


def test_parse_codigo_verifica_la_fitxa():
    assert bcs.parse_codigo(FICHA_HTML) == 'HOT_C_005_5B'


def test_build_bc_lomloe_resol_b_mateixa_familia(monkeypatch):
    monkeypatch.setattr(bcs, '_fetch_with_retry', lambda session, fid: FICHA_HTML)
    monkeypatch.setattr(bcs.time, 'sleep', lambda s: None)

    assert bcs.build_bc_lomloe(RECORDS, session=object()) == {'HOT_C_005_5B': ['HOT_B_0171']}


def test_build_bc_lomloe_salta_fitxa_amb_codi_diferent(monkeypatch, caplog):
    altra = FICHA_HTML.replace('HOT_C_005_5B', 'ADG_C_001_3B')
    monkeypatch.setattr(bcs, '_fetch_with_retry', lambda session, fid: altra)
    monkeypatch.setattr(bcs.time, 'sleep', lambda s: None)

    with caplog.at_level(logging.WARNING):
        result = bcs.build_bc_lomloe(RECORDS, session=object())

    assert result == {}
    assert 'HOT_C_005_5B' in caplog.text


def test_fetch_reintenta_amb_backoff(monkeypatch):
    calls = []
    sleeps = []

    def flaky(session, fid, timeout=30):
        calls.append(fid)
        if len(calls) < 3:
            raise RuntimeError('boom')
        return FICHA_HTML

    monkeypatch.setattr(bcs, '_fetch_ficha_html', flaky)
    monkeypatch.setattr(bcs.time, 'sleep', lambda s: sleeps.append(s))

    assert bcs._fetch_with_retry(object(), 999) == FICHA_HTML
    assert len(calls) == 3
    assert sleeps == [5, 15]


def test_fetch_reintenta_i_finalment_falla(monkeypatch):
    def always(session, fid, timeout=30):
        raise RuntimeError('boom')

    monkeypatch.setattr(bcs, '_fetch_ficha_html', always)
    monkeypatch.setattr(bcs.time, 'sleep', lambda s: None)

    with pytest.raises(RuntimeError):
        bcs._fetch_with_retry(object(), 999)
