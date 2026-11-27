"""test_sepe_favorites_alerts.py — Favorits i alertes de cursos per a especialitats SEPE (Pla 102).

SOC i SEPE aïllats a tmp_path, BD pròpia, cap correu real (send_email substituït).
"""
import json
from unittest.mock import patch

import pytest

import app as app_module
import db
import fpo_alerts_service
from tests.test_fpo_agenda import FAMILIES, _soc
from tests.test_fpo_alerts_api import _login
from tests.test_fpo_api import fpo_data  # noqa: F401  (fixture: soc_*.json a tmp_path)
from tests.test_sepe_api import SEPE_ROWS


@pytest.fixture
def env(fpo_data, monkeypatch):  # noqa: F811
    (fpo_data / 'sepe_especs.json').write_text(json.dumps(SEPE_ROWS), encoding='utf-8')
    monkeypatch.setattr(app_module, '_sepe_llista_cache', {'key': None, 'data': None})
    test_db = str(fpo_data / 'test.db')
    monkeypatch.setenv('DB_PATH', test_db)
    db.init_db(db_path=test_db)
    return fpo_data


@pytest.fixture
def client(env):
    return _login('sepefav@example.com')


def test_favorit_nomes_sepe_surt_amb_les_dades_del_cataleg(client):
    assert client.post('/api/fpo/favorites', json={'especialitat_codi': 'SSCE22'}).status_code == 201
    favs = client.get('/api/fpo/favorites').json
    assert len(favs) == 1
    f = favs[0]
    assert f['especialitat_codi'] == 'SSCE22'
    assert f['font'] == 'sepe'
    assert f['titol']['es'] and f['titol']['ca']
    assert f['familia']['codi'] == 'SSC'
    assert f['familia']['desc']['es'] == 'SERVICIOS SOCIOCULTURALES Y A LA COMUNIDAD'
    assert f['familia']['desc']['ca']
    assert f['hores'] == 50.0
    assert f['modalitat'] == 'Presencial y teleformación'
    assert f['programaUrl'] == '/api/sepe/programa/SSCE22'
    assert f['esCertProf'] is False
    assert f['cursos'] == []


def test_favorit_soc_no_canvia(client):
    client.post('/api/fpo/favorites', json={'especialitat_codi': 'IFCD0112'})
    f = client.get('/api/fpo/favorites').json[0]
    assert f['font'] == 'soc'
    assert f['titol'] == {'ca': 'Especialitat IFCD0112', 'es': 'Especialidad IFCD0112'}   # el del SOC, no el SEPE
    assert f['modalitat'] == ''
    assert 'modalitat' in f


def test_favorit_desconegut_manté_la_forma_buida(client):
    client.post('/api/fpo/favorites', json={'especialitat_codi': 'ZZZZ9999'})
    f = client.get('/api/fpo/favorites').json[0]
    assert f['titol'] == {'ca': '', 'es': ''}
    assert f['font'] == 'soc'
    assert f['hores'] == 0.0


def test_alerta_amb_espec_sepe_sense_cursos_al_soc(client):
    r = client.post('/api/fpo/alerts', json={'espec_codi': 'SSCE22', 'inclou_en_linia': True})
    assert r.status_code == 201, r.json
    alerts = client.get('/api/fpo/alerts').json
    assert len(alerts) == 1
    a = alerts[0]
    assert a['espec_codi'] == 'SSCE22'
    assert a['espec_titol'] and a['espec_titol']['es']
    # No s'afegeix cap clau nova al contracte existent (test_fpo_alerts_api fixa aquest conjunt)
    assert set(a) == {'id', 'comarca', 'familia_codi', 'familia_desc', 'espec_codi', 'espec_titol',
                      'inclou_en_linia', 'active', 'created_at', 'last_sent_at'}


def test_alerta_amb_espec_inexistent_te_titol_null(client):
    client.post('/api/fpo/alerts', json={'espec_codi': 'ZZZZ9999'})
    assert client.get('/api/fpo/alerts').json[0]['espec_titol'] is None


def test_dispatch_d_un_curs_nou_ssce22_avisa_l_alerta_sepe(client):
    client.post('/api/fpo/alerts', json={'espec_codi': 'SSCE22', 'inclou_en_linia': True})
    nou = _soc('26/9', '2026-12-10')
    nou['especialitat'] = {'codi': 'SSCE22', 'desc': {'ca': 'SSCE22', 'es': 'SSCE22'}}
    with patch('email_service.send_email') as send:
        assert fpo_alerts_service.dispatch([nou], 'https://grausfp.test', FAMILIES) == 1
    assert send.call_count == 1
    assert send.call_args[0][0] == 'sepefav@example.com'
