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
    # Pla 081: catàleg SEPE a tmp_path (no s'escriu per defecte: cada test el crea si el vol)
    monkeypatch.setattr(app_module, 'SEPE_ESPECS_PATH', str(tmp_path / 'sepe_especs.json'))
    monkeypatch.setattr(app_module, '_sepe_especs_cache', {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_sepe_index_cache', {'key': None, 'data': None})
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
    # Fitxa del curs concret (centre triat), no el llistat de l'especialitat
    assert c['fitxaUrl'] == ('https://serveiocupacio.gencat.cat/ca/persones/vull-formar-me/'
                             'cercadors-formacio-especialitats/cercador-integrat/fitxa-curs.html'
                             f"?codi_curso_seleccionado={c['idCurs']}")


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


# --- Pla 081: vinculació amb el catàleg d'especialitats del SEPE ---

SEPE_ROWS = [
    {'codi': 'IFCD0112', 'idSepe': 777, 'titol_es': 'ESPECIALIDAD SEPE', 'versio': 2,
     'competenciaTransversal': 'Idiomas / Lingüísticas', 'nivell': None,
     'modalitat': 'Presencial y teleformación', 'hores': 100.0,
     'vigenciaInici': '2020-01-15', 'vigenciaFi': '2031-12-31'},
    # També al SEPE, però és certificat de professionalitat: guanya 'grauC'
    {'codi': 'ADGG0408', 'idSepe': 888, 'titol_es': 'CERT', 'versio': 1,
     'competenciaTransversal': None, 'nivell': 3, 'modalitat': 'Presencial', 'hores': 50.0,
     'vigenciaInici': '2020-01-15', 'vigenciaFi': '2030-01-01'},
]
SEPE_KEYS = ('vinculacio', 'vigenciaFi', 'competenciaTransversal', 'modalitatOficial')


def _write_sepe(tmp_path, rows=SEPE_ROWS):
    (tmp_path / 'sepe_especs.json').write_text(json.dumps(rows), encoding='utf-8')


def _with_propia_soc(tmp_path):
    """Afegeix una especialitat CTRA0001 (pròpia del SOC) amb un curs, només a tmp_path."""
    especs = ESPECS + [_espec('CTRA0001', fam='CTR', area='CTRA')]
    cursos = CURSOS + [_curs('301', 'CTRA0001', fam='CTR', area='CTRA')]
    (tmp_path / 'soc_especs.json').write_text(json.dumps(especs), encoding='utf-8')
    (tmp_path / 'soc_cursos.json').write_text(json.dumps(cursos), encoding='utf-8')


def _by_codi(client):
    d = client.get('/api/fpo/especialitats').get_json()
    return {e['codi']: e for e in d['especialitats']}


def test_vinculacio_tres_classes(client, fpo_data):
    _write_sepe(fpo_data)
    _with_propia_soc(fpo_data)
    by = _by_codi(client)
    assert by['ADGG0408']['vinculacio'] == 'grauC'
    ifc = by['IFCD0112']
    assert ifc['vinculacio'] == 'sepe'
    assert ifc['vigenciaFi'] == '2031-12-31'
    assert ifc['competenciaTransversal'] == 'Idiomas / Lingüísticas'
    assert ifc['modalitatOficial'] == 'Presencial y teleformación'
    propia = by['CTRA0001']
    assert propia['vinculacio'] == 'propiaSoc'
    assert all(propia[k] is None for k in SEPE_KEYS[1:])


def test_sense_sepe_tot_continua_igual_amb_camps_a_none(client):
    by = _by_codi(client)
    assert set(by) == {'IFCD0112', 'ADGG0408'}
    assert by['IFCD0112']['vinculacio'] is None          # no s'etiqueta 'propiaSoc' sense dades
    assert by['ADGG0408']['vinculacio'] == 'grauC'
    for e in by.values():
        assert all(e[k] is None for k in SEPE_KEYS[1:])
    assert by['IFCD0112']['nCursos'] == 2


def test_cache_s_invalida_en_aparèixer_el_fitxer_sepe(client, fpo_data):
    assert _by_codi(client)['IFCD0112']['vinculacio'] is None
    _write_sepe(fpo_data)
    assert _by_codi(client)['IFCD0112']['vinculacio'] == 'sepe'


def test_detall_inclou_bloc_sepe(client, fpo_data):
    _write_sepe(fpo_data)
    _with_propia_soc(fpo_data)
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert d['sepe'] == {'idSepe': 777, 'vigenciaInici': '2020-01-15',
                         'vigenciaFi': '2031-12-31', 'versio': 2}
    assert 'programaSepeUrl' not in d
    propia = client.get('/api/fpo/especialitat/CTRA0001').get_json()
    assert propia['sepe'] is None
    assert 'programaSepeUrl' not in propia


def test_detall_sense_sepe_te_bloc_a_none(client):
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert d['sepe'] is None
