"""test_fpo_ext_api.py — /api/fpo/* amb cursos externs (Pla 063)."""
import json
import os

import pytest

import app as app_module

TODAY = '2026-09-25'
FAM = {'IFC': {'ca': 'INFORMÀTICA I COMUNICACIONS', 'es': 'INFORMÁTICA Y COMUNICACIONES'},
       'ADG': {'ca': 'ADMINISTRACIÓ I GESTIÓ', 'es': 'ADMINISTRACIÓN Y GESTIÓN'}}


def _espec(codi, fam):
    return {'codi': codi, 'titol': {'ca': f'Esp {codi}', 'es': f'Esp {codi}'},
            'familia': {'codi': fam, 'desc': FAM[fam]}, 'area': {'codi': 'X', 'desc': {'ca': 'X', 'es': 'X'}},
            'nivell': 3, 'hores': 100.0, 'preu': 0.0, 'esCertProf': False, 'rd': None,
            'programaUrl': '', 'moduls': [], 'cursIds': [], 'destacada': False}


def _soc_curs(idc, esp):
    return {'idCurs': idc, 'titol': {'ca': idc, 'es': idc},
            'especialitat': {'codi': esp, 'desc': {'ca': esp, 'es': esp}}, 'estat': 'inscripcio',
            'modalitat': 'PRESENCIAL', 'dataInici': '2026-10-01', 'dataFi': '2027-01-01',
            'comarca': 'BARCELONÈS', 'municipi': 'BARCELONA', 'centre': {'nom': 'C', 'idCentre': '1'},
            'programaUrl': ''}


def _ext(font, n, titol, **kw):
    base = {'idCurs': f'{font.upper()}:{n}', 'font': font, 'tipus': 'Subvencionat',
            'titol': {'ca': titol, 'es': titol}, 'area': '', 'certCodi': '', 'hores': 30.0,
            'modalitat': 'PRESENCIAL', 'estat': '', 'dataInici': '2026-10-05', 'dataFi': '2026-11-01',
            'comarca': '', 'municipi': 'BARCELONA', 'provincia': '',
            'centre': {'nom': 'PIMEC Formació', 'idCentre': ''},
            'fitxaUrl': f'https://pimecformacio.org/x/{n}'}
    base.update(kw)
    return base


EXT = [
    _ext('pimec', 'p1', 'Programació neurolingüística', area='Informàtica'),
    _ext('pimec', 'p2', 'Programació neurolingüística', area='Informàtica',
         dataInici='2026-06-01', dataFi='2026-07-01'),                      # finalitzada
    _ext('foment', 'f1', 'ADGG0208: Ofimática', certCodi='ADGG0208', tipus='Altres',
         fitxaUrl='https://www.fomentformacio.com/formacion/f1'),
]


@pytest.fixture
def fpo_ext_data(tmp_path, monkeypatch):
    (tmp_path / 'soc_especs.json').write_text(
        json.dumps([_espec('IFCD0112', 'IFC'), _espec('ADGG0408', 'ADG')]), encoding='utf-8')
    (tmp_path / 'soc_cursos.json').write_text(
        json.dumps([_soc_curs('111', 'IFCD0112'), _soc_curs('201', 'ADGG0408')]), encoding='utf-8')
    (tmp_path / 'soc_centres.json').write_text('[]', encoding='utf-8')
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(EXT), encoding='utf-8')
    for nom, fitxer in (('SOC_ESPECS_PATH', 'soc_especs.json'), ('SOC_CURSOS_PATH', 'soc_cursos.json'),
                        ('SOC_CENTRES_PATH', 'soc_centres.json'), ('EXT_CURSOS_PATH', 'ext_cursos.json')):
        monkeypatch.setattr(app_module, nom, str(tmp_path / fitxer))
    for nom in ('_soc_cursos_cache', '_soc_especs_cache', '_soc_centres_cache', '_ext_cursos_cache'):
        monkeypatch.setattr(app_module, nom, {'mtime': None, 'index': None})
    for nom in ('_soc_espec_index_cache', '_ext_index_cache'):
        monkeypatch.setattr(app_module, nom, {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_fpo_today', lambda: TODAY)
    return tmp_path


@pytest.fixture
def client(fpo_ext_data):
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _rows(client):
    return {e['codi']: e for e in client.get('/api/fpo/especialitats').get_json()['especialitats']}


def test_llista_barreja_soc_i_externs(client):
    rows = _rows(client)
    assert set(rows) == {'IFCD0112', 'ADGG0408',
                         'PIMEC:programacio-neurolinguistica', 'FOMENT:adgg0208-ofimatica'}
    assert rows['IFCD0112']['font'] == 'soc' and rows['IFCD0112']['tipus'] == ['Subvencionat']
    p = rows['PIMEC:programacio-neurolinguistica']
    assert p['font'] == 'pimec' and p['tipus'] == ['Subvencionat']
    assert p['familia'] == {'codi': 'IFC', 'desc': FAM['IFC']}
    assert p['nCursos'] == 1 and p['estats'] == ['finalitzat']
    f = rows['FOMENT:adgg0208-ofimatica']
    assert f['font'] == 'foment' and f['familia']['codi'] == 'ADG' and f['esCertProf'] is True


def test_llista_ordenada_per_titol(client):
    titols = [(e['titol']['ca']).lower()
              for e in client.get('/api/fpo/especialitats').get_json()['especialitats']]
    assert titols == sorted(titols)


def test_sense_fitxer_extern_nomes_hi_ha_soc(client, fpo_ext_data):
    os.remove(fpo_ext_data / 'ext_cursos.json')
    assert set(_rows(client)) == {'IFCD0112', 'ADGG0408'}


def test_nomes_externs_si_falta_el_soc(client, fpo_ext_data):
    os.remove(fpo_ext_data / 'soc_especs.json')
    rows = _rows(client)
    assert set(rows) == {'PIMEC:programacio-neurolinguistica', 'FOMENT:adgg0208-ofimatica'}
    # sense famílies del SOC, tot cau a FCO (amb el codi com a nom)
    assert {r['familia']['codi'] for r in rows.values()} == {'FCO'}


def test_detall_extern_edicions_ordenades(client):
    d = client.get('/api/fpo/especialitat/PIMEC:programacio-neurolinguistica').get_json()
    assert d['descripcio']['ca'] == 'Programació neurolingüística'
    assert d['moduls'] == [] and d['programaUrl'] == ''
    assert [c['idCurs'] for c in d['cursos']] == ['PIMEC:p1', 'PIMEC:p2']   # activa abans que finalitzada
    assert [c['estat'] for c in d['cursos']] == ['', 'finalitzat']
    c = d['cursos'][0]
    assert c['font'] == 'pimec' and c['fitxaUrl'].startswith('https://pimecformacio.org')


def test_detall_extern_desconegut_404(client):
    r = client.get('/api/fpo/especialitat/PIMEC:no-existeix')
    assert r.status_code == 404 and r.get_json() == {}


def test_detall_soc_continua_igual(client):
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert [c['idCurs'] for c in d['cursos']] == ['111']


def test_finalitzat_es_recalcula_amb_el_dia(client, monkeypatch):
    monkeypatch.setattr(app_module, '_fpo_today', lambda: '2026-11-15')
    p = _rows(client)['PIMEC:programacio-neurolinguistica']
    assert p['nCursos'] == 0 and p['estats'] == ['finalitzat']
