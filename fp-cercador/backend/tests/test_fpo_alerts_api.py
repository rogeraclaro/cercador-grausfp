"""test_fpo_alerts_api.py — /api/fpo/alerts (Pla 086): CRUD amb sessió i baixa per enllaç."""
import json
from unittest.mock import patch

import pytest

import alerts_service
import app as app_module
import db
import fpo_alerts_service as svc
from tests.test_fpo_agenda import FAMILIES

flask_app = app_module.app
flask_app.config["TESTING"] = True

ESPECS = [{'codi': 'ADGG0408', 'titol': {'ca': 'Operacions auxiliars', 'es': 'Operaciones auxiliares'},
           'familia': {'codi': 'ADG', 'desc': FAMILIES['ADG']}}]


@pytest.fixture
def data(tmp_path, monkeypatch):
    (tmp_path / 'soc_especs.json').write_text(json.dumps(ESPECS), encoding='utf-8')
    monkeypatch.setattr(app_module, 'SOC_ESPECS_PATH', str(tmp_path / 'soc_especs.json'))
    monkeypatch.setattr(app_module, 'SOC_CURSOS_PATH', str(tmp_path / 'soc_cursos.json'))
    for cache in ('_soc_cursos_cache', '_soc_especs_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    test_db = str(tmp_path / 'test.db')
    monkeypatch.setenv('DB_PATH', test_db)
    db.init_db(db_path=test_db)


def _login(email):
    c = flask_app.test_client()
    with patch("email_service.send_verification_email"):
        c.post("/api/auth/register", json={"email": email, "password": "password123"})
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    assert c.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 200
    return c


@pytest.fixture
def client(data):
    return _login('fpo@example.com')


def _sql(query, params=()):
    conn = db.get_db()
    try:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def test_sense_sessio_dona_401(data):
    c = flask_app.test_client()
    assert c.get('/api/fpo/alerts').status_code == 401
    assert c.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).status_code == 401
    assert c.patch('/api/fpo/alerts/1', json={'active': False}).status_code == 401
    assert c.delete('/api/fpo/alerts/1').status_code == 401


def test_crear_i_llistar(client):
    assert client.get('/api/fpo/alerts').json == []
    r = client.post('/api/fpo/alerts', json={'comarca': ' Gironès ', 'familia_codi': 'ADG'})
    assert r.status_code == 201, r.json
    alerts = client.get('/api/fpo/alerts').json
    assert len(alerts) == 1
    a = alerts[0]
    assert set(a) == {'id', 'comarca', 'familia_codi', 'familia_desc', 'espec_codi', 'espec_titol',
                      'inclou_en_linia', 'active', 'created_at', 'last_sent_at'}
    assert (a['comarca'], a['familia_codi'], a['espec_codi'], a['inclou_en_linia'], a['active']) == \
        ('Gironès', 'ADG', None, True, True)
    assert a['familia_desc'] == FAMILIES['ADG'] and a['id'] == r.json['id']


def test_la_mateixa_alerta_no_es_duplica(client):
    assert client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).status_code == 201
    r = client.post('/api/fpo/alerts', json={'comarca': 'gironès', 'inclou_en_linia': True})
    assert (r.status_code, r.json['status']) == (200, 'already_exists')
    assert len(client.get('/api/fpo/alerts').json) == 1
    assert client.post('/api/fpo/alerts', json={'comarca': 'Gironès', 'inclou_en_linia': False}).status_code == 201


@pytest.mark.parametrize('cos', [
    None, [], 'text', {}, {'inclou_en_linia': False}, {'comarca': ''}, {'comarca': 7}, {'comarca': 'x' * 61},
    {'familia_codi': 'adg'}, {'familia_codi': 'ADGG'}, {'familia_codi': 7}, {'espec_codi': 'x' * 161},
    {'espec_codi': ['ADGG0408']}, {'comarca': 'Gironès', 'inclou_en_linia': 'si'},
])
def test_crear_valida_el_cos(client, cos):
    assert client.post('/api/fpo/alerts', json=cos).status_code == 400
    assert client.get('/api/fpo/alerts').json == []


def test_limit_de_files_per_usuari_comptant_les_pausades(client, monkeypatch):
    monkeypatch.setattr(svc, 'ALERTS_MAX_PER_USER', 2)
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    client.post('/api/fpo/alerts', json={'comarca': 'Segrià'})
    client.patch(f'/api/fpo/alerts/{a}', json={'active': False})
    assert client.post('/api/fpo/alerts', json={'comarca': 'Bages'}).status_code == 429
    assert client.delete(f'/api/fpo/alerts/{a}').status_code == 204
    assert client.post('/api/fpo/alerts', json={'comarca': 'Bages'}).status_code == 201


def test_pausa_i_reactiva(client):
    a = client.post('/api/fpo/alerts', json={'espec_codi': 'ADGG0408'}).json['id']
    assert client.get('/api/fpo/alerts').json[0]['espec_titol'] == ESPECS[0]['titol']
    assert client.patch(f'/api/fpo/alerts/{a}', json={'active': False}).status_code == 200
    assert client.get('/api/fpo/alerts').json[0]['active'] is False
    assert client.patch(f'/api/fpo/alerts/{a}', json={'active': True}).status_code == 200
    assert client.get('/api/fpo/alerts').json[0]['active'] is True
    for cos in (None, {}, {'active': 'no'}, {'active': 1}):
        assert client.patch(f'/api/fpo/alerts/{a}', json=cos).status_code == 400


def test_aillament_entre_usuaris(client):
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    altre = _login('altre@example.com')
    assert altre.get('/api/fpo/alerts').json == []
    assert altre.patch(f'/api/fpo/alerts/{a}', json={'active': False}).status_code == 404
    assert altre.delete(f'/api/fpo/alerts/{a}').status_code == 404
    assert client.get('/api/fpo/alerts').json[0]['active'] is True


def _token(alert_id):
    conn = db.get_db()
    try:
        user_id = conn.execute("SELECT user_id FROM fpo_alerts WHERE id = ?", (alert_id,)).fetchone()[0]
        return alerts_service._get_or_create_unsubscribe_token(
            conn, alert_id, user_id, kind=svc.TOKEN_KIND, token_type=svc.TOKEN_TYPE)
    finally:
        conn.close()


def test_baixa_per_enllac_sense_sessio(client):
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    b = client.post('/api/fpo/alerts', json={'comarca': 'Segrià'}).json['id']
    token = _token(a)
    r = flask_app.test_client().get(f'/api/fpo/alerts/{a}/unsubscribe?token={token}')
    assert (r.status_code, r.headers['Location']) == (302, '/?unsubscribed=1')
    actives = {x['id']: x['active'] for x in client.get('/api/fpo/alerts').json}
    assert actives == {a: False, b: True}
    # el token és d'un sol ús
    r = flask_app.test_client().get(f'/api/fpo/alerts/{a}/unsubscribe?token={token}')
    assert r.headers['Location'] == '/?unsubscribe_error=1'


@pytest.mark.parametrize('token', ['', 'dolent', 'x' * 64])
def test_baixa_amb_token_dolent_redirigeix_amb_avis(client, token):
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    r = flask_app.test_client().get(f'/api/fpo/alerts/{a}/unsubscribe?token={token}')
    assert (r.status_code, r.headers['Location']) == (302, '/?unsubscribe_error=1')
    assert client.get('/api/fpo/alerts').json[0]['active'] is True


def test_el_token_d_una_alerta_no_serveix_per_a_una_altra(client):
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    b = client.post('/api/fpo/alerts', json={'comarca': 'Segrià'}).json['id']
    r = flask_app.test_client().get(f'/api/fpo/alerts/{b}/unsubscribe?token={_token(a)}')
    assert r.headers['Location'] == '/?unsubscribe_error=1'
    assert all(x['active'] for x in client.get('/api/fpo/alerts').json)


def test_baixa_amb_token_caducat(client):
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    token = _token(a)
    _sql("UPDATE tokens SET expires_at = '2000-01-01 00:00:00'")
    r = flask_app.test_client().get(f'/api/fpo/alerts/{a}/unsubscribe?token={token}')
    assert r.headers['Location'] == '/?unsubscribe_error=1'


def test_esborrar_l_alerta_esborra_el_seu_token(client):
    a = client.post('/api/fpo/alerts', json={'comarca': 'Gironès'}).json['id']
    _token(a)
    assert client.delete(f'/api/fpo/alerts/{a}').status_code == 204
    assert _sql("SELECT COUNT(*) FROM tokens WHERE type = 'fpo_alert_unsubscribe'")[0][0] == 0
