"""
test_b_contingut_scraper.py — Contingut de les fitxes B (ECP + RA) via todofp (Pla 068).

Sense xarxa: _fetch_ficha_html / _fetch_with_retry, la sessió i time.sleep mockejats.
HTML retallat de les fitxes reals ADG_B_3001 (LOMLOE) i MF1018_2 (LOE).
"""
import json
import logging

import pytest

from scrapers import b_contingut_scraper as bcs


FICHA_LOMLOE_HTML = """
<html><head><title>Buscador FP</title><script>var x = 1;</script></head><body>
<h5><span class="card-text text-muted ml-1"><b>Código:</b> <b>ADG_B_3001</b></span></h5>
<h5><span class="recuadro-boton-b">Grado B - Certificado de competencia</span></h5>
<h2 class="mb-3 ">Programa de formación</h2>
<div class="mb-3 mx-auto">
  <h4>Estándares de competencia</h4>
  <ol class="list-group list-group-flush custom-list">
    <li class="list-group-item mb-2">
      (<span>ECP0973_1</span>)&nbsp<span>Introducir datos y textos en terminales informáticos</span>
    </li>
  </ol>
</div>
<div class="mb-3 mx-auto">
  <h4 class="mt-3">Resultados de aprendizaje</h4>
  <ol class="list-group  list-group-flush custom-list">
    <li class="list-group-item mb-2">(<span>ADG_RA_3001_01 </span>)&nbsp<span>Prepara los equipos y materiales necesarios para su trabajo, reconociendo sus principales funciones y aplicaciones y sus necesidades de mantenimiento</span></li>
    <li class="list-group-item mb-2">(<span>ADG_RA_3001_02 </span>)&nbsp<span>Graba informáticamente datos, textos y otros documentos, valorando la rapidez y exactitud del proceso</span></li>
    <li class="list-group-item mb-2">(<span>ADG_RA_3001_03 </span>)&nbsp<span>Trata textos y datos informáticamente, seleccionando las aplicaciones informáticas en función de la tarea</span></li>
    <li class="list-group-item mb-2">(<span>ADG_RA_3001_04 </span>)&nbsp<span>Tramita documentación mediante su archivo, impresión y transmisión de la misma, relacionando el tipo de documento con su ubicación</span></li>
  </ol>
</div>
<h2 class="mb-3 ">Acreditaciones parciales de competencia (Grados A incluidos)</h2>
<ol class="list-group list-group-flush custom-list">
  <li class="list-group-item mb-2">
   (<span>ADG_A_3001_01</span>)&nbsp<span>Preparación de los equipos</span>
  </li>
  <li class="list-group-item mb-2">
   (<span>ADG_A_3001_02</span>)&nbsp<span>Grabación de datos y textos</span>
  </li>
</ol>
<p class="mt-3 text-justify texto-explicacion text-dark fs-6 text">Nota: El resto de especificaciones a que hace referencia el artículo 10.4 de la Ley Orgánica 3/2022, de 31 de marzo, pueden consultarse en la norma por la que se establece esta formación.</p>
</body></html>
"""

FICHA_LOE_HTML = """
<html><head><title>Buscador FP</title></head><body>
<h5><span class="card-text text-muted ml-1"><b>Código:</b> <b>MF1018_2</b></span></h5>
<h2 class="mb-3 ">Programa de formación</h2>
<div class="mb-3 mx-auto">
  <h4>Estándares de competencia</h4>
  <ol class="list-group list-group-flush custom-list">
    <li class="list-group-item mb-2">
      (<span>ECP1018_2</span>)&nbsp<span>Facilitar la atención residencial en las actividades sociosanitarias en instituciones sociales</span>
    </li>
  </ol>
</div>
<p class="mt-3 text-justify texto-explicacion text-dark fs-6 text">Nota: El resto de especificaciones a que hace referencia el artículo 10.4 de la Ley Orgánica 3/2022, de 31 de marzo, pueden consultarse en la norma por la que se establece esta formación.</p>
</body></html>
"""


def _rec(id_, codigo, grado, ficha_id=None, plan_antiguo=False):
    return {'id': id_, 'codigo': codigo, 'grado': grado, 'plan_antiguo': plan_antiguo,
            'ficha_id': ficha_id, 'denominacion': 'X', 'familia': 'F', 'nivel': 1}


RECORDS = [
    _rec(1, 'ADG_B_3001', 'B', ficha_id=43),
    _rec(2, 'MF1018_2', 'B', ficha_id=2820, plan_antiguo=True),
    _rec(3, 'ADG_B_9999', 'B'),                       # sense ficha_id → no entra
    _rec(4, 'ADG_A_3001_01', 'A', ficha_id=11),
    _rec(5, 'ADG_C_001_3B', 'C', ficha_id=12),
    _rec(6, None, 'D', ficha_id=13),
    _rec(7, None, 'E', ficha_id=14),
]

HTML_BY_ID = {43: FICHA_LOMLOE_HTML, 2820: FICHA_LOE_HTML}


@pytest.fixture
def no_network(monkeypatch):
    monkeypatch.setattr(bcs, '_thread_session', lambda: object())
    monkeypatch.setattr(bcs.time, 'sleep', lambda s: None)


def test_parse_b_ficha_lomloe_extreu_ecp_i_ra():
    parsed = bcs.parse_b_ficha(FICHA_LOMLOE_HTML)
    assert parsed['ecp'] == [
        {'codigo': 'ECP0973_1', 'text': 'Introducir datos y textos en terminales informáticos'},
    ]
    assert [ra['codigo'] for ra in parsed['ra']] == [
        'ADG_RA_3001_01', 'ADG_RA_3001_02', 'ADG_RA_3001_03', 'ADG_RA_3001_04',
    ]
    assert parsed['ra'][0]['text'] == (
        'Prepara los equipos y materiales necesarios para su trabajo, reconociendo sus '
        'principales funciones y aplicaciones y sus necesidades de mantenimiento')
    assert parsed['ra'][3]['text'] == (
        'Tramita documentación mediante su archivo, impresión y transmisión de la misma, '
        'relacionando el tipo de documento con su ubicación')


def test_parse_b_ficha_loe_nomes_ecp():
    parsed = bcs.parse_b_ficha(FICHA_LOE_HTML)
    assert parsed == {
        'ecp': [{'codigo': 'ECP1018_2',
                 'text': 'Facilitar la atención residencial en las actividades '
                         'sociosanitarias en instituciones sociales'}],
        'ra': [],
    }


def test_parse_codigo():
    assert bcs.parse_codigo(FICHA_LOMLOE_HTML) == 'ADG_B_3001'
    assert bcs.parse_codigo(FICHA_LOE_HTML) == 'MF1018_2'
    assert bcs.parse_codigo('<html>res</html>') is None


def test_build_nomes_b_amb_ficha_id(monkeypatch, no_network):
    fetched = []

    def fake_fetch(session, ficha_id):
        fetched.append(ficha_id)
        return HTML_BY_ID[ficha_id]

    monkeypatch.setattr(bcs, '_fetch_with_retry', fake_fetch)

    result = bcs.build_b_contingut(RECORDS, max_workers=2)

    assert sorted(fetched) == [43, 2820]
    assert set(result) == {'ADG_B_3001', 'MF1018_2'}
    assert len(result['ADG_B_3001']['ra']) == 4
    assert result['MF1018_2']['ra'] == []


def test_build_salta_fitxa_amb_codi_diferent(monkeypatch, no_network, caplog):
    altra = FICHA_LOMLOE_HTML.replace('<b>ADG_B_3001</b>', '<b>ADG_B_3002</b>')
    monkeypatch.setattr(bcs, '_fetch_with_retry',
                        lambda session, fid: altra if fid == 43 else HTML_BY_ID[fid])

    with caplog.at_level(logging.WARNING):
        result = bcs.build_b_contingut(RECORDS)

    assert 'ADG_B_3001' not in result
    assert 'MF1018_2' in result
    assert 'ADG_B_3001' in caplog.text


def test_build_salta_fitxa_inabastable_sense_petar(monkeypatch, no_network, caplog):
    def fake_fetch(session, ficha_id):
        if ficha_id == 2820:
            raise RuntimeError('timeout')
        return HTML_BY_ID[ficha_id]

    monkeypatch.setattr(bcs, '_fetch_with_retry', fake_fetch)

    with caplog.at_level(logging.WARNING):
        result = bcs.build_b_contingut(RECORDS)

    assert set(result) == {'ADG_B_3001'}
    assert 'MF1018_2' in caplog.text


def test_build_informa_del_progres(monkeypatch, no_network):
    monkeypatch.setattr(bcs, '_fetch_with_retry', lambda session, fid: HTML_BY_ID[fid])
    calls = []

    bcs.build_b_contingut(RECORDS, on_progress=lambda phase, i, n: calls.append((i, n)))

    assert calls[-1] == (2, 2)


def test_build_sense_b_no_fa_xarxa(monkeypatch):
    def boom():
        raise AssertionError('no hauria de crear sessió')

    monkeypatch.setattr(bcs, '_thread_session', boom)
    assert bcs.build_b_contingut([_rec(1, 'ADG_A_3001_01', 'A', ficha_id=1)]) == {}


def test_fetch_reintenta_amb_backoff(monkeypatch):
    calls = []
    sleeps = []

    def flaky(session, fid, timeout=30, grado='B'):
        calls.append(fid)
        if len(calls) < 3:
            raise RuntimeError('boom')
        return FICHA_LOE_HTML

    monkeypatch.setattr(bcs, '_fetch_ficha_html', flaky)
    monkeypatch.setattr(bcs.time, 'sleep', lambda s: sleeps.append(s))

    assert bcs._fetch_with_retry(object(), 2820) == FICHA_LOE_HTML
    assert sleeps == list(bcs.BACKOFF[:2])


def test_write_b_contingut_atomic_i_rellegible(tmp_path):
    index = {'ADG_B_3001': {'ecp': [{'codigo': 'ECP0973_1', 'text': 'Introducir…'}], 'ra': []}}
    path = tmp_path / 'sub' / 'b_contingut.json'

    bcs.write_b_contingut(index, str(path))

    assert json.loads(path.read_text(encoding='utf-8')) == index
    assert [p.name for p in path.parent.iterdir()] == ['b_contingut.json']


# ---------------------------------------------------------------------------
# Ampliació 068 — pares reals dels Graus A LOE (fitxa de l'A)
# La fitxa d'un A LOE NO porta el codi de l'A: els "Código:" són els dels B pares.
# HTML retallat de les fitxes reals UF0038 (1 pare) i UF0723 (2 pares).
# ---------------------------------------------------------------------------

def _a_card(codigo_b, nom):
    return f"""
  <div class="col-md-10 mb-4 p-4 shadow rounded cuadro-estilo">
    <h2 class="fs-2 fs-md-3"><b class="card-text text-muted">{nom} (Plan Antiguo)</b></h2>
    <h5>
      <b class="card-text text-muted ml-1">Código: </b>
      <span class="card-text text-muted ml-1">
          <b>{codigo_b}</b>
      </span>
    </h5>
    <h5><span class="recuadro-boton-b">Grado B - Certificado de competencia</span></h5>
    <a href="/buscadorgradosfp/ficha?grado=B&amp;id=1578&amp;navegar=0" class="btn btn-dark">Ver ficha</a>
  </div>"""


_A_HEAD = """
<html><head><title>Buscador FP</title></head><body>
<!--<h1 class="card-title">Grado A: Microacreditaciones</h1>
    <h1><span class="card-text text-muted" th:text="${A.denominacion}"></span></h1>-->
<p id="mensaje1" class=" texto-explicacion ">Grados B que incluyen el grado A que estás cursando:</p>
"""

FICHA_A_UN_PARE_HTML = (_A_HEAD + _a_card('MF0706_1', 'Servicio de habitaciones') + '</body></html>')
FICHA_A_DOS_PARES_HTML = (_A_HEAD
                          + _a_card('MF0326_2', 'Preparación de máquinas e instalaciones')
                          + _a_card('MF0333_2', 'Construcción y acondicionamientos de modelos')
                          + '</body></html>')
FICHA_A_LOMLOE_HTML = (_A_HEAD + _a_card('QUI_B_3001', 'Un B nou') + '</body></html>')

A_RECORDS = [
    _rec(10, 'UF0038', 'A', ficha_id=7802, plan_antiguo=True),
    _rec(11, 'UF0723', 'A', ficha_id=8191, plan_antiguo=True),
    _rec(12, 'UF9999', 'A', plan_antiguo=True),             # sense ficha_id → no entra
    _rec(13, 'ADG_A_3001_01', 'A', ficha_id=11),           # LOMLOE → no entra
    _rec(14, 'MF0706_1', 'B', ficha_id=15, plan_antiguo=True),
]
A_HTML_BY_ID = {7802: FICHA_A_UN_PARE_HTML, 8191: FICHA_A_DOS_PARES_HTML}


def test_parse_a_loe_pares_un_pare():
    assert bcs.parse_a_loe_pares(FICHA_A_UN_PARE_HTML) == ['MF0706_1']


def test_parse_a_loe_pares_dos_pares():
    assert bcs.parse_a_loe_pares(FICHA_A_DOS_PARES_HTML) == ['MF0326_2', 'MF0333_2']


def test_parse_a_loe_pares_ignora_codis_que_no_son_mf():
    assert bcs.parse_a_loe_pares(FICHA_A_LOMLOE_HTML) == []


def test_build_a_loe_pares_nomes_uf_amb_ficha_id(monkeypatch, no_network):
    fetched = []

    def fake_fetch(session, ficha_id, grado='B'):
        fetched.append((ficha_id, grado))
        return A_HTML_BY_ID[ficha_id]

    monkeypatch.setattr(bcs, '_fetch_with_retry', fake_fetch)

    result = bcs.build_a_loe_pares(A_RECORDS, max_workers=2)

    assert sorted(fetched) == [(7802, 'A'), (8191, 'A')]
    assert result == {'UF0038': ['MF0706_1'], 'UF0723': ['MF0326_2', 'MF0333_2']}


def test_build_a_loe_pares_salta_fitxa_sense_mf(monkeypatch, no_network, caplog):
    # Sense "Código:" propi no es pot verificar l'A: una fitxa sense cap MF
    # (id obsolet que apunta a un A LOMLOE, pàgina d'error…) se salta.
    monkeypatch.setattr(bcs, '_fetch_with_retry',
                        lambda session, fid, grado='B': FICHA_A_LOMLOE_HTML if fid == 7802
                        else A_HTML_BY_ID[fid])

    with caplog.at_level(logging.WARNING):
        result = bcs.build_a_loe_pares(A_RECORDS)

    assert set(result) == {'UF0723'}
    assert 'UF0038' in caplog.text


def test_build_a_loe_pares_salta_inabastable(monkeypatch, no_network, caplog):
    def fake_fetch(session, ficha_id, grado='B'):
        if ficha_id == 8191:
            raise RuntimeError('timeout')
        return A_HTML_BY_ID[ficha_id]

    monkeypatch.setattr(bcs, '_fetch_with_retry', fake_fetch)

    with caplog.at_level(logging.WARNING):
        result = bcs.build_a_loe_pares(A_RECORDS)

    assert result == {'UF0038': ['MF0706_1']}
    assert 'UF0723' in caplog.text


def test_write_a_loe_pares_rellegible(tmp_path):
    path = tmp_path / 'a_loe_pares.json'
    bcs.write_a_loe_pares({'UF0038': ['MF0706_1']}, str(path))
    assert json.loads(path.read_text(encoding='utf-8')) == {'UF0038': ['MF0706_1']}
