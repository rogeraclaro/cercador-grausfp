"""
test_d_modulos_scraper.py — Mòduls ("Plan de formación") de cada cicle D via
fitxa todofp (Pla 058).

Sense xarxa: _fetch_ficha_html / _fetch_with_retry i time.sleep mockejats.
"""
import pytest

from scrapers import d_modulos_scraper as dms


FICHA_HTML = """
<div class="cdsp"><h2>Plan de formaci&oacute;n<span class="cruz"></span></h2>
<div class="desplegable"><div class="cte"><p>Si estudias 1&ordm; ... vas a cursar:</p>
<ul>
  <li>Estructura del mercado tur&iacute;stico.</li>
  <li>0179. Ingl&eacute;s Profesional (Grado Superior)</li>
  <li>M&oacute;dulo profesional optativo (competencia de cada Comunidad Aut&oacute;noma)</li>
</ul></div></div></div>
<a href="https://www.educacion.gob.es/centros/buscarCentros?ensenanzaFP=122_2403">Centros</a>
"""


def _rec(id_, grado, ficha_url=None):
    return {'id': id_, 'codigo': None, 'grado': grado, 'plan_antiguo': False,
            'ficha_url': ficha_url, 'denominacion': 'X', 'familia': 'F', 'nivel': 1}


def test_parse_modulos_noms_i_codis():
    assert dms.parse_modulos(FICHA_HTML) == [
        {'num': None, 'name': 'Estructura del mercado turístico'},
        {'num': '0179', 'name': 'Inglés Profesional (Grado Superior)'},
        {'num': None, 'name': 'Módulo profesional optativo (competencia de cada Comunidad Autónoma)'},
    ]


def test_parse_modulos_sense_seccio_retorna_buit():
    assert dms.parse_modulos('<html><body><p>res</p></body></html>') == []


def test_parse_ensenanza_fp():
    assert dms.parse_ensenanza_fp(FICHA_HTML) == '122_2403'
    assert dms.parse_ensenanza_fp('<html><body>sense enllaç</body></html>') is None


def test_build_d_modulos_clau_per_id_i_salta_sense_ficha_url(monkeypatch):
    monkeypatch.setattr(dms, '_fetch_with_retry', lambda session, url: FICHA_HTML)
    monkeypatch.setattr(dms.time, 'sleep', lambda s: None)

    records = [
        _rec(12774, 'D', ficha_url='https://www.todofp.es/d/12774.html'),
        _rec(999, 'D'),
        _rec(50, 'C', ficha_url='https://www.todofp.es/c/50.html'),
    ]

    assert dms.build_d_modulos(records, session=object()) == {
        '12774': {
            'modulos': [
                {'num': None, 'name': 'Estructura del mercado turístico'},
                {'num': '0179', 'name': 'Inglés Profesional (Grado Superior)'},
                {'num': None, 'name': 'Módulo profesional optativo (competencia de cada Comunidad Autónoma)'},
            ],
            'ensenanzaFP': '122_2403',
        }
    }


def test_build_d_modulos_salta_fitxa_que_falla_i_continua(monkeypatch, caplog):
    def fetch(session, url):
        if 'boom' in url:
            raise RuntimeError('Exceeded 30 redirects.')
        return FICHA_HTML

    monkeypatch.setattr(dms, '_fetch_with_retry', fetch)
    monkeypatch.setattr(dms.time, 'sleep', lambda s: None)

    records = [
        _rec(1, 'D', ficha_url='https://www.todofp.es/d/boom.html'),
        _rec(2, 'D', ficha_url='https://www.todofp.es/d/ok.html'),
    ]

    import logging
    with caplog.at_level(logging.WARNING):
        result = dms.build_d_modulos(records, session=object())

    assert list(result) == ['2']
    assert 'boom' in caplog.text


def test_build_d_modulos_sense_d_recs_no_fa_xarxa(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError('no hauria de fer xarxa')

    monkeypatch.setattr(dms, '_fetch_with_retry', boom)
    assert dms.build_d_modulos([_rec(50, 'C', ficha_url='x')]) == {}


def test_fetch_reintenta_amb_backoff(monkeypatch):
    calls = []
    sleeps = []

    def flaky(session, url, timeout=30):
        calls.append(url)
        if len(calls) < 3:
            raise RuntimeError('boom')
        return FICHA_HTML

    monkeypatch.setattr(dms, '_fetch_ficha_html', flaky)
    monkeypatch.setattr(dms.time, 'sleep', lambda s: sleeps.append(s))

    assert dms._fetch_with_retry(object(), 'https://x/y.html') == FICHA_HTML
    assert len(calls) == 3
    assert sleeps == [5, 15]


def test_fetch_reintenta_i_finalment_falla(monkeypatch):
    monkeypatch.setattr(dms, '_fetch_ficha_html',
                        lambda session, url, timeout=30: (_ for _ in ()).throw(RuntimeError('boom')))
    monkeypatch.setattr(dms.time, 'sleep', lambda s: None)

    with pytest.raises(RuntimeError):
        dms._fetch_with_retry(object(), 'https://x/y.html')
