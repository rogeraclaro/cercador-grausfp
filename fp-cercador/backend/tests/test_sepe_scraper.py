"""
test_sepe_scraper.py — Catàleg d'Especialitats Formatives del SEPE (Pla 081).

Sense xarxa: la sessió HTTP és un fals que serveix la fixture Latin-1 de 3 files
reals (ADGA12DCP, ADGD0073, FCOE001PO). El nom del fitxer coincideix amb
`*scraper*` i queda fora de la suite rutinària: s'executa explícitament.
"""
import json
import os

import pytest
import requests

from scrapers import sepe_scraper as sepe

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'sepe_paginacion_3.latin1.json')


def _fixture_bytes() -> bytes:
    with open(FIXTURE, 'rb') as f:
        return f.read()


def _fixture_rows() -> list:
    return json.loads(_fixture_bytes().decode('latin-1'))['data']


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}')


class FakeSession:
    """Serveix les files de la fixture paginant segons start/length del cos."""

    def __init__(self, rows=None, post_content=None, si=None, fail=()):
        self.rows = rows if rows is not None else _fixture_rows()
        self.post_content = post_content
        self.si = si or {}        # Pla 105: {wrapper: [índexs de files amb «SI»]}
        self.fail = set(fail)     # wrappers que fallen amb HTTP 500
        self.filtres = []         # filtres «SI» de cada POST
        self.calls = []  # (mètode, url, start)
        self.headers = {}

    def get(self, url, **kwargs):
        self.calls.append(('GET', url, None))
        return FakeResponse(b'<html>main</html>')

    def post(self, url, json=None, **kwargs):  # noqa: A002 - mateix nom que requests
        dt = {item['name']: item['value'] for item in json['dtInfo']}
        self.calls.append(('POST', url, dt['start']))
        if self.post_content is not None:
            return FakeResponse(self.post_content)
        prefix = 'formulario:acordeonPrincipal:tabOpcionesAvanzadas:'
        si = [f['name'][len(prefix):].split('Wrapper')[0] for f in json['filtro']
              if f['name'].startswith(prefix) and f['value'] == 'SI']
        self.filtres.append(si)
        rows = self.rows
        if si:
            if si[0] in self.fail:
                return FakeResponse(b'', status_code=500)
            rows = [self.rows[i] for i in self.si.get(si[0], range(len(self.rows)))]
        start, length = dt['start'], dt['length']
        page = rows[start:start + length]
        body = {'draw': 1, 'recordsTotal': len(self.rows),
                'recordsFiltered': len(rows), 'data': page}
        return FakeResponse(sepe_dumps(body))


def sepe_dumps(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False).encode('latin-1')


# --- Fixture i decode ---

def test_fixture_is_not_utf8():
    with pytest.raises(UnicodeDecodeError):
        _fixture_bytes().decode('utf-8')


def test_fetch_decodes_latin1_into_accented_text():
    rows = sepe._fetch_raw_rows(FakeSession())
    assert rows[0][4] == 'ADMINISTRACIÓN Y GESTIÓN'
    assert rows[2][6] == 'Idiomas / Lingüísticas'


# --- parse_row ---

def test_parse_row_adga12dcp():
    got = sepe.parse_row(_fixture_rows()[0])
    assert got == {
        'codi': 'ADGA12DCP', 'codiAntic': None, 'sufix': 'DCP', 'idSepe': 107,
        'titol_es': 'AUXILIAR DE EMPLEADO DE OFICINA',
        'titol_mostra': 'Auxiliar de empleado de oficina', 'versio': 1,
        'familia_es': 'ADMINISTRACIÓN Y GESTIÓN', 'area_es': 'ADMINISTRACIÓN / GESTIÓN',
        'familia_codi': 'ADG', 'area_codi': 'ADGA',
        'competenciaTransversal': None, 'nivell': 1, 'modalitat': 'Presencial',
        'hores': 410.0, 'vigenciaInici': '2004-05-24', 'vigenciaFi': '2029-12-31',
    }


def test_parse_row_fcoe001po_sense_nivell_ni_familia():
    got = sepe.parse_row(_fixture_rows()[2])
    assert got['codi'] == 'FCOE001PO'
    assert got['competenciaTransversal'] == 'Idiomas / Lingüísticas'
    assert got['nivell'] is None
    assert got['familia_es'] is None
    assert got['area_es'] is None
    assert got['modalitat'] == 'Presencial y teleformación'
    assert got['titol_es'] == 'ALEMÁN A1 (MARCO COMÚN EUROPEO)'


def test_parse_row_adgd0073():
    got = sepe.parse_row(_fixture_rows()[1])
    assert got['nivell'] == 2
    assert got['vigenciaInici'] == '2024-02-26'
    assert got['vigenciaFi'] == '2031-12-31'
    assert got['idSepe'] == 59414
    # el títol no arrossega l'espai final ni cap tag
    assert got['titol_es'] == 'PLANIFICADOR DE RECURSOS EMPRESARIALES (ERP)'


# --- Pla 096: codi antic, sufixos, interrogants ---

def test_parse_row_codi_amb_parentesi():
    cells = list(_fixture_rows()[2])
    cells[1] = 'CTRC0001 (FCOV0001)'
    got = sepe.parse_row(cells)
    assert got['codi'] == 'CTRC0001'
    assert got['codiAntic'] == 'FCOV0001'
    assert got['familia_codi'] == 'CTR' and got['area_codi'] == 'CTRC'
    assert got['sufix'] is None


@pytest.mark.parametrize('codi,sufix', [
    ('FCOE001PO', 'PO'), ('ADGA12DCP', 'DCP'), ('HOTR02EXP', 'EXP'), ('SSCE05CCC', 'CCC'),
    ('IFCT01PTF', 'PTF'), ('IFCD0112', None), ('ADGD0073', None),
])
def test_sufix(codi, sufix):
    assert sepe._sufix(codi) == sufix


def test_parse_row_fcoe001po_sufix():
    assert sepe.parse_row(_fixture_rows()[2])['sufix'] == 'PO'


@pytest.mark.parametrize('raw,net', [
    ('PRODUCCIÓN DE ?WEB SERIES?', 'PRODUCCIÓN DE «WEB SERIES»'),
    ('TÉCNICA DE ?CUERDA SECA?.', 'TÉCNICA DE «CUERDA SECA».'),
    ('MICROSOFT? CERTIFIED: AZURE', 'MICROSOFT CERTIFIED: AZURE'),
    ('MICROSOFT?CERTIFIED: AZURE', 'MICROSOFT CERTIFIED: AZURE'),
    ('¿QUÉ ES LA IA?', '¿QUÉ ES LA IA?'),
    ('¿QUÉ ES ?BIG DATA??', '¿QUÉ ES «BIG DATA»?'),
    ('SENSE INTERROGANTS', 'SENSE INTERROGANTS'),
])
def test_clean_title_interrogants(raw, net):
    assert sepe.clean_title(raw) == net


def test_parse_row_titol_net_i_mostra():
    cells = list(_fixture_rows()[1])
    cells[2] = cells[2].replace('PLANIFICADOR DE RECURSOS EMPRESARIALES (ERP)',
                                'INGENIERÍA DE SISTEMAS EN ?RED HAT LINUX?')
    got = sepe.parse_row(cells)
    assert got['titol_es'] == 'INGENIERÍA DE SISTEMAS EN «RED HAT LINUX»'
    assert got['titol_mostra'] == 'Ingeniería de sistemas en «Red Hat Linux»'


def test_parse_row_sense_familia_es_transversal():
    got = sepe.parse_row(_fixture_rows()[2])
    assert got['familia_es'] is None
    assert got['competenciaTransversal'] == 'Idiomas / Lingüísticas'
    assert got['titol_mostra'] == 'Alemán A1 (marco común europeo)'


def test_validate_unicitat_sobre_codi_net(monkeypatch):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    rows = [{'codi': 'CTRC0001', 'codiAntic': 'FCOV0001'}, {'codi': 'CTRC0001', 'codiAntic': None}]
    with pytest.raises(sepe.SepeDataError, match='CTRC0001'):
        sepe.validate_rows(rows)


def test_parse_row_wrong_cell_count_raises():
    with pytest.raises(sepe.SepeDataError):
        sepe.parse_row(_fixture_rows()[0][:10])


def test_parse_row_comma_decimal_hours():
    cells = list(_fixture_rows()[0])
    cells[9] = '12,5'
    assert sepe.parse_row(cells)['hores'] == 12.5


# --- Paginació ---

def test_pagination_bootstrap_then_two_posts(monkeypatch):
    monkeypatch.setattr(sepe, 'PAGE_LENGTH', 2)
    session = FakeSession()
    rows = sepe._fetch_raw_rows(session)
    assert len(rows) == 3
    methods = [(m, s) for m, _u, s in session.calls]
    assert methods == [('GET', None), ('POST', 0), ('POST', 2)]
    assert session.calls[0][1].endswith('/flows/main')
    assert session.calls[1][1].endswith('/rest/paginacionEspecialidades')


def test_non_json_response_raises():
    session = FakeSession(post_content=b'<html><body>Error</body></html>')
    with pytest.raises(sepe.SepeDataError):
        sepe._fetch_raw_rows(session)


def test_json_without_data_list_raises():
    session = FakeSession(post_content=b'{"draw": 1}')
    with pytest.raises(sepe.SepeDataError):
        sepe._fetch_raw_rows(session)


def test_max_pages_guard(monkeypatch):
    monkeypatch.setattr(sepe, 'PAGE_LENGTH', 1)
    monkeypatch.setattr(sepe, 'MAX_PAGES', 2)
    with pytest.raises(sepe.SepeDataError):
        sepe._fetch_raw_rows(FakeSession())


def test_request_body_shape():
    body = sepe._request_body(2000, 2000)
    dt = {item['name']: item['value'] for item in body['dtInfo']}
    assert dt['start'] == 2000 and dt['length'] == 2000
    assert len(dt['columns']) == 11
    assert dt['columns'][0]['orderable'] is False and dt['columns'][10]['orderable'] is False
    assert dt['columns'][1]['orderable'] is True
    filtro = {item['name']: item['value'] for item in body['filtro']}
    assert filtro['formulario:ultimaVersionCuadrado'] == 'true'
    assert filtro['javax.faces.ViewState'] == 'e1s1'
    assert filtro['formulario:acordeonPrincipal:tabOpcionesAvanzadas:vinculacionWrapper:vinculacion'] == '000'
    assert body['tipoBuscador'] == 'buscadorEspecialidades'
    assert body['enSEDE'] is True and body['enAltaIF'] is False


# --- build_sepe_data / validació ---

def test_build_with_default_min_rows_raises():
    with pytest.raises(sepe.SepeDataError):
        sepe.build_sepe_data(FakeSession())


def test_build_with_patched_min_rows(monkeypatch):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    got = sepe.build_sepe_data(FakeSession())
    assert [r['codi'] for r in got] == ['ADGA12DCP', 'ADGD0073', 'FCOE001PO']


# --- Pla 105: aula virtual i tutoria presencial ---

def test_request_body_filtres_si():
    body = sepe._request_body(0, 2000, {'aulaVirtualSeleccionada': 'SI'})
    filtro = {item['name']: item['value'] for item in body['filtro']}
    pre = 'formulario:acordeonPrincipal:tabOpcionesAvanzadas:'
    assert filtro[pre + 'aulaVirtualSeleccionadaWrapper:aulaVirtualSeleccionada'] == 'SI'
    assert filtro[pre + 'tutoriaPresencialWrapper:tutoriaPresencial'] == '000'


def test_build_aula_virtual_i_tutoria(monkeypatch):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    session = FakeSession(si={'aulaVirtualSeleccionada': [0], 'tutoriaPresencial': [1, 2]})
    got = {r['codi']: r for r in sepe.build_sepe_data(session)}
    assert got['ADGA12DCP']['aulaVirtual'] is True
    assert got['ADGD0073']['aulaVirtual'] is False
    assert got['FCOE001PO']['aulaVirtual'] is False
    assert got['ADGA12DCP']['tutoriaPresencial'] is False
    assert got['FCOE001PO']['tutoriaPresencial'] is True
    # una sola sessió: un GET i, després, el llistat complet i una consulta «SI» per filtre
    assert [m for m, _u, _s in session.calls] == ['GET', 'POST', 'POST', 'POST']
    assert session.filtres == [[], ['aulaVirtualSeleccionada'], ['tutoriaPresencial']]


def test_build_filtre_que_falla_deixa_none(monkeypatch, caplog):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    session = FakeSession(si={'tutoriaPresencial': [1]}, fail={'aulaVirtualSeleccionada'})
    rows = sepe.build_sepe_data(session)
    assert len(rows) == 3
    assert all(r['aulaVirtual'] is None for r in rows)
    assert [r['tutoriaPresencial'] for r in rows] == [False, True, False]
    assert 'aulaVirtualSeleccionada' in caplog.text


def test_build_filtre_amb_resposta_no_json_deixa_none(monkeypatch):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)

    class HtmlSession(FakeSession):
        def post(self, url, json=None, **kwargs):  # noqa: A002
            resp = super().post(url, json=json, **kwargs)
            return FakeResponse(b'<html>error</html>') if self.filtres[-1] else resp

    rows = sepe.build_sepe_data(HtmlSession(si={'aulaVirtualSeleccionada': [0]}))
    assert all(r['aulaVirtual'] is None and r['tutoriaPresencial'] is None for r in rows)


@pytest.mark.parametrize('si', [[], [0, 1, 2]])
def test_build_filtre_amb_0_o_tots_es_error_de_format(monkeypatch, caplog, si):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    rows = sepe.build_sepe_data(FakeSession(si={'aulaVirtualSeleccionada': si, 'tutoriaPresencial': [2]}))
    assert all(r['aulaVirtual'] is None for r in rows)
    assert [r['tutoriaPresencial'] for r in rows] == [False, False, True]
    assert 'format inesperat' in caplog.text


def _rows(n: int) -> list:
    return [{'codi': f'AAAA{i:04d}', 'idSepe': i} for i in range(n)]


def test_write_too_few_rows_keeps_previous(tmp_path):
    path = tmp_path / 'sepe_especs.json'
    path.write_bytes(b'[{"codi": "OLD"}]')
    with pytest.raises(sepe.SepeDataError):
        sepe.write_sepe_data(_rows(10), str(tmp_path))
    assert path.read_bytes() == b'[{"codi": "OLD"}]'
    assert os.listdir(tmp_path) == ['sepe_especs.json']


def test_write_duplicate_codi_keeps_previous(tmp_path, monkeypatch):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    path = tmp_path / 'sepe_especs.json'
    path.write_bytes(b'[{"codi": "OLD"}]')
    rows = _rows(3) + [{'codi': 'AAAA0001', 'idSepe': 99}]
    with pytest.raises(sepe.SepeDataError, match='AAAA0001'):
        sepe.write_sepe_data(rows, str(tmp_path))
    assert path.read_bytes() == b'[{"codi": "OLD"}]'


def test_write_ok_valid_json_and_no_temp_files(tmp_path, monkeypatch):
    monkeypatch.setattr(sepe, 'MIN_ROWS', 2)
    rows = [dict(r, titol_es='AUXILIAR ÑÓ') for r in _rows(3)]
    sepe.write_sepe_data(rows, str(tmp_path))
    assert os.listdir(tmp_path) == ['sepe_especs.json']
    text = (tmp_path / 'sepe_especs.json').read_text(encoding='utf-8')
    assert 'AUXILIAR ÑÓ' in text  # ensure_ascii=False
    assert json.loads(text) == rows
