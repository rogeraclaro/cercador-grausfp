"""
test_sepe_api.py — Catàleg estatal d'especialitats del SEPE: /api/sepe/* (Pla 082).

Fitxers SOC i SEPE aïllats a tmp_path; el SEPE real mai no es crida (fetch mockejat).
"""
import json
import os
import time

import pytest
import requests

import app as app_module
from scrapers import sepe_scraper
from tests.test_fpo_api import _curs, _espec, fpo_data  # noqa: F401  (fixture: soc_*.json a tmp_path)

SEPE_ROWS = [
    # Té cursos al SOC (fixture de test_fpo_api: 2 cursos IFCD0112)
    {'codi': 'IFCD0112', 'idSepe': 777, 'titol_es': 'PROGRAMACIÓN', 'versio': 2,
     'familia_es': 'INFORMÁTICA Y COMUNICACIONES', 'area_es': 'DESARROLLO',
     'familia_codi': 'IFC', 'area_codi': 'IFCD', 'competenciaTransversal': None, 'nivell': 3,
     'modalitat': 'Presencial', 'hores': 590.0, 'vigenciaInici': '2020-01-15', 'vigenciaFi': '2031-12-31'},
    # Sense cursos a Catalunya ni equivalent al SOC
    {'codi': 'SSCE22', 'idSepe': 97614, 'titol_es': 'TUTORIZACION EN TELEFORMACIÓN', 'versio': 1,
     'familia_es': 'SERVICIOS SOCIOCULTURALES Y A LA COMUNIDAD', 'area_es': 'FORMACIÓN Y EDUCACIÓN',
     'familia_codi': 'SSC', 'area_codi': 'SSCE', 'competenciaTransversal': 'Digitales', 'nivell': None,
     'modalitat': 'Presencial y teleformación', 'hores': 50.0,
     'vigenciaInici': '2025-04-25', 'vigenciaFi': '2030-04-25'},
]
FAKE_PDF = b'%PDF-1.4 fake'


@pytest.fixture
def client(fpo_data, monkeypatch):  # noqa: F811
    (fpo_data / 'sepe_especs.json').write_text(json.dumps(SEPE_ROWS), encoding='utf-8')
    monkeypatch.setattr(app_module, 'SEPE_PROGRAMES_DIR', str(fpo_data / 'sepe_programes'))
    monkeypatch.setattr(app_module, '_sepe_llista_cache', {'key': None, 'data': None})
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


@pytest.fixture
def fetch_calls(monkeypatch):
    """Mock de sepe_scraper.fetch_programa_pdf: retorna `calls['result']` i compta les crides."""
    calls = {'n': 0, 'result': FAKE_PDF}

    def fake(id_sepe, session=None):
        calls['n'] += 1
        calls['id'] = id_sepe
        if isinstance(calls['result'], Exception):
            raise calls['result']
        return calls['result']

    monkeypatch.setattr(sepe_scraper, 'fetch_programa_pdf', fake)
    return calls


# --- Llistat ---

def test_llistat_format_compacte(client):
    d = client.get('/api/sepe/especialitats').get_json()
    by_codi = {e['c']: e for e in d['especialitats']}
    assert set(by_codi) == {'IFCD0112', 'SSCE22'}
    ssce = by_codi['SSCE22']
    assert ssce == {'c': 'SSCE22', 't': 'TUTORIZACION EN TELEFORMACIÓN', 'tca': None,
                    'tm': 'Tutorizacion en teleformación', 'ca': None, 'sx': None,
                    'f': 'SSC', 'a': 'SSCE', 'n': None, 'm': 'Presencial y teleformación',
                    'h': 50.0, 'ct': 'Digitales', 'v': 1, 'vi': '2025-04-25', 'vf': '2030-04-25',
                    'nc': 0}
    assert d['actualitzat']
    assert 'warning' not in d


def test_llistat_creua_amb_soc(client):
    d = client.get('/api/sepe/especialitats').get_json()
    ifc = next(e for e in d['especialitats'] if e['c'] == 'IFCD0112')
    assert ifc['nc'] == 2                                   # 2 cursos SOC actius
    assert ifc['tca'] == 'Especialitat IFCD0112'            # títol en català del SOC
    # Famílies: CA del SOC quan n'hi ha, ES del SEPE; només les usades al catàleg SEPE
    assert d['families']['IFC'] == {'ca': 'IFC', 'es': 'INFORMÁTICA Y COMUNICACIONES'}
    assert d['families']['SSC'] == {'ca': 'SERVICIOS SOCIOCULTURALES Y A LA COMUNIDAD',
                                    'es': 'SERVICIOS SOCIOCULTURALES Y A LA COMUNIDAD'}
    assert 'ADG' not in d['families']
    assert d['arees']['SSCE']['es'] == 'FORMACIÓN Y EDUCACIÓN'


def test_llistat_sense_fitxer_avisa(client, fpo_data):  # noqa: F811
    os.remove(fpo_data / 'sepe_especs.json')
    d = client.get('/api/sepe/especialitats').get_json()
    assert d['especialitats'] == [] and d['warning']


# --- Pla 096: codi antic (parèntesi), transversals, sufixos ---

CTR_ROW = {'codi': 'CTRC0001', 'codiAntic': 'FCOV0001', 'sufix': None, 'idSepe': 31528,
           'titol_es': 'RESOLUCIÓN DE CONFLICTOS', 'titol_mostra': 'Resolución de conflictos',
           'versio': 1, 'familia_es': None, 'area_es': None, 'familia_codi': 'CTR',
           'area_codi': 'CTRC', 'competenciaTransversal': 'Competencias básicas para la empleabilidad',
           'nivell': 1, 'modalitat': 'Presencial', 'hores': 30.0,
           'vigenciaInici': '2023-03-09', 'vigenciaFi': '2030-12-31'}


@pytest.fixture
def ctr_client(client, fpo_data):  # noqa: F811
    """El SEPE dona «CTRC0001 (FCOV0001)» i el SOC fa servir el codi net CTRC0001."""
    rows = SEPE_ROWS + [CTR_ROW, dict(SEPE_ROWS[1], codi='ADGA12DCP', sufix='DCP', idSepe=107)]
    (fpo_data / 'sepe_especs.json').write_text(json.dumps(rows), encoding='utf-8')
    especs = json.loads((fpo_data / 'soc_especs.json').read_text(encoding='utf-8'))
    especs.append(dict(_espec('CTRC0001', fam='CTR', area='CTRC'),
                       titol={'ca': 'RESOLUCIÓ DE CONFLICTES', 'es': 'RESOLUCIÓN DE CONFLICTOS'}))
    (fpo_data / 'soc_especs.json').write_text(json.dumps(especs), encoding='utf-8')
    cursos = json.loads((fpo_data / 'soc_cursos.json').read_text(encoding='utf-8'))
    cursos.append(_curs('301', 'CTRC0001', fam='CTR', area='CTRC'))
    (fpo_data / 'soc_cursos.json').write_text(json.dumps(cursos), encoding='utf-8')
    return client


def test_codi_net_es_creua_amb_soc(ctr_client):
    d = ctr_client.get('/api/sepe/especialitats').get_json()
    ctr = next(e for e in d['especialitats'] if e['c'] == 'CTRC0001')
    assert ctr['ca'] == 'FCOV0001'
    assert ctr['nc'] == 1
    assert ctr['tca'] == 'Resolució de conflictes'          # el SOC en majúscules → display_title
    assert ctr['tm'] == 'Resolución de conflictos'
    assert ctr['f'] == 'CTR'
    assert d['families']['CTR'] == {'ca': 'Competències transversals', 'es': 'Competencias transversales'}
    assert next(e for e in d['especialitats'] if e['c'] == 'ADGA12DCP')['sx'] == 'DCP'


def test_fpo_codi_net_vinculacio_sepe(ctr_client):
    llista = ctr_client.get('/api/fpo/especialitats').get_json()['especialitats']
    ctr = next(e for e in llista if e['codi'] == 'CTRC0001')
    assert ctr['vinculacio'] == 'sepe'
    assert ctr['competenciaTransversal'] == 'Competencias básicas para la empleabilidad'


@pytest.mark.parametrize('codi', ['CTRC0001', 'FCOV0001', 'CTRC0001 (FCOV0001)'])
def test_programa_accepta_codi_net_i_antic(ctr_client, fetch_calls, fpo_data, codi):  # noqa: F811
    r = ctr_client.get('/api/sepe/programa/' + codi)
    assert r.status_code == 200
    assert fetch_calls['id'] == 31528
    assert (fpo_data / 'sepe_programes' / 'CTRC0001.pdf').exists()   # cache pel codi net


# --- Programa (PDF) ---

def test_programa_codi_desconegut_404(client, fetch_calls):
    r = client.get('/api/sepe/programa/NOEXISTEIX')
    assert r.status_code == 404
    assert fetch_calls['n'] == 0


def test_programa_descarrega_i_cache(client, fetch_calls, fpo_data):  # noqa: F811
    r = client.get('/api/sepe/programa/SSCE22')
    assert r.status_code == 200 and r.data == FAKE_PDF
    assert r.mimetype == 'application/pdf'
    assert r.headers['Content-Disposition'] == 'inline; filename="SSCE22.pdf"'
    assert fetch_calls['id'] == 97614                       # id de l'índex, no de l'usuari
    assert (fpo_data / 'sepe_programes' / 'SSCE22.pdf').read_bytes() == FAKE_PDF

    r = client.get('/api/sepe/programa/SSCE22')             # segon cop: de la cache
    assert r.status_code == 200 and r.data == FAKE_PDF
    assert fetch_calls['n'] == 1


def test_programa_cache_caducada_es_refa(client, fetch_calls, fpo_data):  # noqa: F811
    client.get('/api/sepe/programa/SSCE22')
    vell = time.time() - app_module._SEPE_PDF_TTL - 10
    os.utime(fpo_data / 'sepe_programes' / 'SSCE22.pdf', (vell, vell))
    client.get('/api/sepe/programa/SSCE22')
    assert fetch_calls['n'] == 2


def test_programa_sense_pdf_desa_marcador(client, fetch_calls, fpo_data):  # noqa: F811
    fetch_calls['result'] = None
    r = client.get('/api/sepe/programa/SSCE22')
    assert r.status_code == 404 and r.get_json() == {'error': 'sense_programa'}
    assert (fpo_data / 'sepe_programes' / 'SSCE22.nopdf').exists()
    client.get('/api/sepe/programa/SSCE22')                 # el marcador evita tornar-hi
    assert fetch_calls['n'] == 1


def test_programa_error_sepe_502(client, fetch_calls):
    fetch_calls['result'] = requests.ConnectionError('caigut')
    r = client.get('/api/sepe/programa/SSCE22')
    assert r.status_code == 502


def test_programa_rate_limit(client, fetch_calls):
    fetch_calls['result'] = requests.ConnectionError('caigut')   # res no es cacheja
    codes = [client.get('/api/sepe/programa/SSCE22').status_code
             for _ in range(app_module._SEPE_PDF_RATE_LIMIT + 1)]
    assert codes[:-1] == [502] * app_module._SEPE_PDF_RATE_LIMIT
    assert codes[-1] == 429


# --- Pont amb l'FPO (Pla 081 fase 3) ---

def test_fpo_programa_sepe_url_nomes_sense_programa_soc(client, fpo_data):  # noqa: F811
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert 'programaSepeUrl' not in d                       # el SOC ja dona programaUrl
    especs = json.loads((fpo_data / 'soc_especs.json').read_text(encoding='utf-8'))
    for e in especs:
        e['programaUrl'] = ''
    (fpo_data / 'soc_especs.json').write_text(json.dumps(especs), encoding='utf-8')
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert d['programaSepeUrl'] == '/api/sepe/programa/IFCD0112'


# --- Scraper: detecció de PDF ---

class _Resp:
    def __init__(self, content=b'', ctype=''):
        self.content, self.headers = content, {'Content-Type': ctype}

    def raise_for_status(self):
        pass


class _Session:
    def __init__(self, post_resp):
        self.post_resp, self.posted = post_resp, None

    def get(self, url, timeout):
        return _Resp()

    def post(self, url, files, timeout):
        self.posted = files
        return self.post_resp


def test_fetch_programa_pdf_detecta_pdf():
    s = _Session(_Resp(FAKE_PDF, 'pdf'))
    assert sepe_scraper.fetch_programa_pdf(107, session=s) == FAKE_PDF
    assert s.posted['formulario:codigoPropuesta'] == (None, '107')


def test_fetch_programa_pdf_html_es_none():
    s = _Session(_Resp(b'<html>no tiene documento asociado</html>', 'text/html'))
    assert sepe_scraper.fetch_programa_pdf(107, session=s) is None
