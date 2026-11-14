"""test_held_api.py — GET/PUT /api/held: graus que l'usuari ja té, desats al compte (Pla 083)."""
import json
from unittest.mock import patch

import pytest

import app as app_module
import db

flask_app = app_module.app
flask_app.config["TESTING"] = True


def _cataleg():
    base = [('B', 'ADG_B_3001'), ('B', 'ADG_B_3002'), ('C', 'ADG_C_001_3B'), ('A', 'UC0001_1')]
    return [{'id': i, 'grado': g, 'codigo': c, 'denominacion': c, 'familia': 'Administración y Gestión',
             'nivel': 1, 'plan_antiguo': False} for i, (g, c) in enumerate(base, start=1)]


@pytest.fixture
def data(tmp_path, monkeypatch):
    ofertes = tmp_path / 'ofertes.json'
    ofertes.write_text(json.dumps(_cataleg()), encoding='utf-8')
    monkeypatch.setattr(app_module, 'DATA_PATH', str(ofertes))
    monkeypatch.setattr(app_module, '_catalog_cache', {'key': None, 'data': None})
    test_db = str(tmp_path / 'test.db')
    monkeypatch.setenv('DB_PATH', test_db)
    db.init_db(db_path=test_db)
    return ofertes


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
    return _login('held@example.com')


def test_sense_sessio_dona_401(data):
    c = flask_app.test_client()
    assert c.get('/api/held').status_code == 401
    assert c.put('/api/held', json={'refs': []}).status_code == 401


def test_put_substitueix_la_llista_sencera(client):
    assert client.get('/api/held').json == {'refs': []}
    r = client.put('/api/held', json={'refs': ['ADG_B_3001', 'ADG_C_001_3B']})
    assert (r.status_code, r.json) == (200, {'refs': ['ADG_B_3001', 'ADG_C_001_3B']})
    client.put('/api/held', json={'refs': ['ADG_B_3002', 'ADG_B_3001']})
    assert sorted(client.get('/api/held').json['refs']) == ['ADG_B_3001', 'ADG_B_3002']
    client.put('/api/held', json={'refs': []})
    assert client.get('/api/held').json == {'refs': []}


def test_nomes_es_desen_graus_b_c_i_d_del_cataleg(client):
    r = client.put('/api/held', json={'refs': ['ADG_B_3001', 'no-existeix', 'UC0001_1', 'ADG_B_3001']})
    assert r.json == {'refs': ['ADG_B_3001']}


def test_aillament_entre_usuaris(client):
    client.put('/api/held', json={'refs': ['ADG_B_3001']})
    altre = _login('altre@example.com')
    assert altre.get('/api/held').json == {'refs': []}
    altre.put('/api/held', json={'refs': ['ADG_B_3002']})
    assert client.get('/api/held').json == {'refs': ['ADG_B_3001']}


@pytest.mark.parametrize('cos', [
    None, {}, {'refs': 'ADG_B_3001'}, {'refs': [1]}, {'refs': ['']}, {'refs': ['x' * 201]},
    {'refs': [f'r{i}' for i in range(51)]},
])
def test_limits(client, cos):
    client.put('/api/held', json={'refs': ['ADG_B_3001']})
    assert client.put('/api/held', json=cos).status_code == 400
    assert client.get('/api/held').json == {'refs': ['ADG_B_3001']}


def test_cataleg_illegible_dona_503_i_no_esborra(client, data):
    client.put('/api/held', json={'refs': ['ADG_B_3001']})
    data.unlink()
    assert client.put('/api/held', json={'refs': []}).status_code == 503
    assert client.get('/api/held').json == {'refs': ['ADG_B_3001']}


def test_esborrar_el_compte_esborra_la_llista(client):
    client.put('/api/held', json={'refs': ['ADG_B_3001']})
    conn = db.get_db()
    user_id = conn.execute("SELECT id FROM users WHERE email = 'held@example.com'").fetchone()[0]
    conn.close()
    r = flask_app.test_client().delete(f'/api/admin/users/{user_id}',
                                       headers={'Authorization': f'Bearer {app_module.ADMIN_TOKEN}'})
    assert r.status_code == 200
    conn = db.get_db()
    assert conn.execute("SELECT COUNT(*) FROM user_held").fetchone()[0] == 0
    conn.close()


def test_preflight_cors_admet_put(data):
    r = flask_app.test_client().options('/api/held', headers={'Origin': 'http://localhost:8765'})
    assert r.status_code == 204
    assert 'PUT' in r.headers['Access-Control-Allow-Methods']
    assert r.headers['Access-Control-Allow-Credentials'] == 'true'
