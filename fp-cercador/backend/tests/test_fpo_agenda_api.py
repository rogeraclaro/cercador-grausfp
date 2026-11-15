"""test_fpo_agenda_api.py — GET /api/fpo/agenda (Pla 086). Fitxers aïllats a tmp_path."""
import json

import pytest

import app as app_module
from tests.test_fpo_agenda import FAMILIES, _ext, _soc

ESPECS = [{'codi': 'ADGG0408', 'titol': {'ca': 'E', 'es': 'E'}, 'familia': {'codi': 'ADG', 'desc': FAMILIES['ADG']}},
          {'codi': 'FCOO01', 'titol': {'ca': 'F', 'es': 'F'}, 'familia': {'codi': 'FCO', 'desc': FAMILIES['FCO']}}]
SOC = [_soc('26/1', '2026-11-20'), _soc('26/2', '2027-01-10', comarca='Gironès', modalitat='TELEFORMACIÓ'),
       _soc('26/3', '2027-04-01'), _soc('26/4', None), _soc('26/0', '2026-11-01')]
EXT = [_ext('PIMEC:excel:1', '2026-12-01'), _ext('PIMEC:excel:2', '')]


@pytest.fixture
def client(tmp_path, monkeypatch):
    for attr, name, content in (('SOC_ESPECS_PATH', 'soc_especs.json', ESPECS),
                                ('SOC_CURSOS_PATH', 'soc_cursos.json', SOC),
                                ('EXT_CURSOS_PATH', 'ext_cursos.json', EXT)):
        (tmp_path / name).write_text(json.dumps(content), encoding='utf-8')
        monkeypatch.setattr(app_module, attr, str(tmp_path / name))
    for cache in ('_soc_cursos_cache', '_soc_especs_cache', '_ext_cursos_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_fpo_agenda_cache', {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_fpo_today', lambda: '2026-11-15')
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _ids(resp):
    return [c['idCurs'] for c in resp.json['cursos']]


def test_agenda_per_defecte_a_90_dies(client):
    r = client.get('/api/fpo/agenda')
    assert r.status_code == 200
    assert _ids(r) == ['26/1', 'PIMEC:excel:1', '26/2']
    assert r.json['sense_data'] == 2
    assert r.json['comarques'] == ['Barcelonès', 'Gironès']
    assert r.json['generat'] == '2026-11-15'
    soc = r.json['cursos'][0]
    assert 'codi_curso_seleccionado=26/1' in soc['fitxaUrl']
    assert r.json['cursos'][1]['familia']['codi'] == 'FCO'
    assert r.json['cursos'][2]['enLinia'] is True


@pytest.mark.parametrize('dies, ids', [
    ('10', ['26/1']), ('180', ['26/1', 'PIMEC:excel:1', '26/2', '26/3']),
    ('9999', ['26/1', 'PIMEC:excel:1', '26/2', '26/3']),          # màxim 180
    ('abc', ['26/1', 'PIMEC:excel:1', '26/2']), ('0', []), ('-5', []),
])
def test_parametre_dies(client, dies, ids):
    assert _ids(client.get(f'/api/fpo/agenda?dies={dies}')) == ids


def test_la_finestra_es_mou_amb_el_dia(client, monkeypatch):
    assert _ids(client.get('/api/fpo/agenda?dies=10')) == ['26/1']
    monkeypatch.setattr(app_module, '_fpo_today', lambda: '2026-11-25')
    assert _ids(client.get('/api/fpo/agenda?dies=10')) == ['PIMEC:excel:1']


def test_sense_fitxers_torna_buit_amb_avis(client, tmp_path):
    for name in ('soc_especs.json', 'soc_cursos.json', 'ext_cursos.json'):
        (tmp_path / name).unlink()
    r = client.get('/api/fpo/agenda')
    assert r.status_code == 200
    assert r.json['cursos'] == [] and r.json['warning']
