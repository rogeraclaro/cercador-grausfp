"""
test_fpo_api.py — Endpoints /api/fpo/* (Pla 059).

Fitxers soc_*.json aïllats a tmp_path.
"""
import json
import os

import pytest

import app as app_module


def _curs(idc, esp_codi, *, fam='IFC', area='IFCD', estat='inscripcio',
          modalitat='PRESENCIAL', comarca='BARCELONÈS', municipi='BARCELONA',
          cert=False):
    return {
        'idCurs': idc,
        'titol': {'ca': f'Curs {idc}', 'es': f'Curso {idc}'},
        'familia': {'codi': fam, 'desc': {'ca': fam, 'es': fam}},
        'area': {'codi': area, 'desc': {'ca': area, 'es': area}},
        'especialitat': {'codi': esp_codi, 'desc': {'ca': esp_codi, 'es': esp_codi}},
        'esCertProf': cert, 'rd': 'RD 620/2013' if cert else None,
        'nivell': 3, 'hores': 590.0, 'modalitat': modalitat, 'estat': estat,
        'dataInici': '2026-10-01', 'dataFi': '2027-03-01',
        'comarca': comarca, 'municipi': municipi, 'provincia': 'BARCELONA',
        'centre': {'nom': f'Centre {idc}', 'carrer': 'C/ X 1', 'cp': '08001',
                   'municipi': municipi, 'comarca': comarca, 'telefon': '900000000',
                   'email': 'a@b.cat', 'web': '', 'idCentre': 'M' + idc,
                   'horari': {'dilluns': '09:00-14:00'}, 'lat': None, 'lon': None},
        'programaUrl': 'https://conforcat.gencat.cat/x.pdf',
        'queAprendras': {'ca': 'Aprendràs', 'es': 'Aprenderás'},
        'requisits': {'ca': 'Cap', 'es': 'Ninguno'},
        'sortides': {'ca': 'Programador', 'es': 'Programador'},
        'moduls': [{'codi': 'MF1', 'desc': {'ca': 'M1', 'es': 'M1'}, 'durada': 180.0}],
        'ocupacions': [],
    }


def _espec(codi, *, fam='IFC', area='IFCD', cert=False):
    return {
        'codi': codi,
        'titol': {'ca': f'Especialitat {codi}', 'es': f'Especialidad {codi}'},
        'familia': {'codi': fam, 'desc': {'ca': fam, 'es': fam}},
        'area': {'codi': area, 'desc': {'ca': area, 'es': area}},
        'nivell': 3, 'hores': 590.0, 'preu': 0.0,
        'esCertProf': cert, 'rd': 'RD 620/2013' if cert else None,
        'programaUrl': 'https://conforcat.gencat.cat/x.pdf',
        'moduls': [{'codi': 'MF1', 'desc': {'ca': 'M1', 'es': 'M1'}, 'durada': 180.0}],
        'cursIds': [], 'destacada': False,
    }


ESPECS = [_espec('IFCD0112'), _espec('XXXX0000'), _espec('ADGG0408', fam='ADG', area='ADGG', cert=True)]
CURSOS = [
    _curs('111', 'IFCD0112', estat='inscripcio', comarca='BARCELONÈS', municipi='BARCELONA'),
    _curs('112', 'IFCD0112', estat='informacio', comarca='VALLÈS OCCIDENTAL', municipi='TERRASSA',
          modalitat='TELEFORMACIÓ'),
    _curs('201', 'ADGG0408', fam='ADG', area='ADGG', cert=True),
]
CENTRES = [{'idCentre': 'M111', 'raoSocial': 'Centre 111', 'municipi': 'BARCELONA'}]


@pytest.fixture
def fpo_data(tmp_path, monkeypatch):
    (tmp_path / 'soc_especs.json').write_text(json.dumps(ESPECS), encoding='utf-8')
    (tmp_path / 'soc_cursos.json').write_text(json.dumps(CURSOS), encoding='utf-8')
    (tmp_path / 'soc_centres.json').write_text(json.dumps(CENTRES), encoding='utf-8')
    monkeypatch.setattr(app_module, 'SOC_ESPECS_PATH', str(tmp_path / 'soc_especs.json'))
    monkeypatch.setattr(app_module, 'SOC_CURSOS_PATH', str(tmp_path / 'soc_cursos.json'))
    monkeypatch.setattr(app_module, 'SOC_CENTRES_PATH', str(tmp_path / 'soc_centres.json'))
    monkeypatch.setattr(app_module, '_soc_cursos_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_soc_especs_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_soc_centres_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_soc_espec_index_cache', {'key': None, 'data': None})
    return tmp_path


@pytest.fixture
def client(fpo_data):
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def test_especialitats_nomes_amb_curs_actiu(client):
    d = client.get('/api/fpo/especialitats').get_json()
    by_codi = {e['codi']: e for e in d['especialitats']}
    assert set(by_codi) == {'IFCD0112', 'ADGG0408'}          # XXXX0000 exclosa
    ifc = by_codi['IFCD0112']
    assert ifc['nCursos'] == 2
    assert ifc['titol'] == {'ca': 'Especialitat IFCD0112', 'es': 'Especialidad IFCD0112'}
    assert ifc['familia']['codi'] == 'IFC' and ifc['area']['codi'] == 'IFCD'
    assert ifc['nivell'] == 3 and ifc['esCertProf'] is False
    assert sorted(ifc['comarques']) == ['BARCELONÈS', 'VALLÈS OCCIDENTAL']
    assert sorted(ifc['municipis']) == ['BARCELONA', 'TERRASSA']
    assert sorted(ifc['estats']) == ['informacio', 'inscripcio']
    assert sorted(ifc['modalitats']) == ['PRESENCIAL', 'TELEFORMACIÓ']
    assert by_codi['ADGG0408']['esCertProf'] is True


def test_especialitats_warning_si_falta_fitxer(client, fpo_data):
    os.remove(fpo_data / 'soc_especs.json')
    r = client.get('/api/fpo/especialitats')
    assert r.status_code == 200
    d = r.get_json()
    assert d['especialitats'] == [] and d.get('warning')


def test_especialitat_detall(client):
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert d['descripcio'] == {'ca': 'Especialitat IFCD0112', 'es': 'Especialidad IFCD0112'}
    assert d['requisits'] == {'ca': 'Cap', 'es': 'Ninguno'}
    assert d['sortides']['ca'] == 'Programador'
    assert [m['codi'] for m in d['moduls']] == ['MF1']
    assert len(d['cursos']) == 2
    c = d['cursos'][0]
    assert set(c) >= {'idCurs', 'centre', 'dataInici', 'dataFi', 'estat', 'modalitat', 'fitxaUrl'}
    assert c['fitxaUrl'].startswith('https://serveiocupacio.gencat.cat') and 'IFCD0112' in c['fitxaUrl']


def test_especialitat_detall_404(client):
    r = client.get('/api/fpo/especialitat/NOEXISTEIX')
    assert r.status_code == 404
    assert r.get_json() == {}


def test_by_cert_match(client):
    d = client.get('/api/fpo/by-cert?codigo=ADGG0408').get_json()
    assert d['especialitat'] == 'ADGG0408'
    assert d['nCursos'] == 1
    assert d['cursos'][0]['idCurs'] == '201'


def test_by_cert_sense_match(client):
    r = client.get('/api/fpo/by-cert?codigo=ZZZ9999')
    assert r.status_code == 200
    assert r.get_json() == {}
