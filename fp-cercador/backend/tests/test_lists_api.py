"""test_lists_api.py — llistes de graus compartibles (Pla 084)."""
import json
from unittest.mock import patch

import pytest

import app as app_module
import db

flask_app = app_module.app
flask_app.config["TESTING"] = True

REFS = ['ADG_B_3001', 'ADG_B_3002', 'ADG_C_001_3B', 'UC0001_1']


def _cataleg():
    grados = ['B', 'B', 'C', 'A']
    return [{'id': i, 'grado': g, 'codigo': c, 'denominacion': f'Grau {c}',
             'familia': 'Administración y Gestión', 'nivel': 1, 'plan_antiguo': False}
            for i, (g, c) in enumerate(zip(grados, REFS), start=1)]


@pytest.fixture
def data(tmp_path, monkeypatch):
    ofertes = tmp_path / 'ofertes.json'
    ofertes.write_text(json.dumps(_cataleg()), encoding='utf-8')
    monkeypatch.setattr(app_module, 'DATA_PATH', str(ofertes))
    monkeypatch.setattr(app_module, '_catalog_cache', {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_get_effective_oferta_centres',
                        lambda: {'ADG_B_3001': ['c1', 'c2']})
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
    return _login('orientador@example.com')


def _sql(query, params=()):
    conn = db.get_db()
    try:
        rows = conn.execute(query, params).fetchall()
        conn.commit()
        return rows
    finally:
        conn.close()


def _shared_list_in_db(email, refs):
    """Llista 'shared' escrita directament a la BD, sense passar per l'API."""
    user_id = _sql("SELECT id FROM users WHERE email = ?", (email,))[0][0]
    _sql("INSERT INTO lists (user_id, name, kind) VALUES (?, 'Per a la Marta', 'shared')", (user_id,))
    list_id = _sql("SELECT MAX(id) FROM lists")[0][0]
    for ref in refs:
        _sql("INSERT INTO list_items (list_id, oferta_id, oferta_ref) VALUES (?, ?, ?)",
             (list_id, REFS.index(ref) + 1, ref))
    return list_id


def _refs_of(list_id):
    return [r[0] for r in _sql("SELECT oferta_ref FROM list_items WHERE list_id = ? ORDER BY id", (list_id,))]


# --- Fase 1: els favorits no es barregen amb les llistes compartides ---------

def test_els_favorits_no_veuen_els_graus_d_una_llista_compartida(client):
    list_id = _shared_list_in_db('orientador@example.com', ['ADG_B_3001'])
    assert client.get('/api/favorites').json == []
    assert client.post('/api/favorites', json={'ref': 'ADG_B_3002'}).status_code == 201
    assert [f['ref'] for f in client.get('/api/favorites').json] == ['ADG_B_3002']
    assert _refs_of(list_id) == ['ADG_B_3001']


def test_esborrar_un_favorit_no_toca_la_llista_compartida(client):
    list_id = _shared_list_in_db('orientador@example.com', ['ADG_B_3001'])
    client.post('/api/favorites', json={'ref': 'ADG_B_3001'})
    assert client.delete('/api/favorites/ADG_B_3001').status_code == 204
    assert client.get('/api/favorites').json == []
    assert _refs_of(list_id) == ['ADG_B_3001']


def test_els_centres_d_un_favorit_no_es_desen_a_la_llista_compartida(client):
    list_id = _shared_list_in_db('orientador@example.com', ['ADG_B_3001'])
    assert client.post('/api/favorites/ADG_B_3001/centres', json={'centre_id': 'c1'}).status_code == 404
    client.post('/api/favorites', json={'ref': 'ADG_B_3001'})
    assert client.post('/api/favorites/ADG_B_3001/centres', json={'centre_id': 'c1'}).status_code == 201
    shared_item = _sql("SELECT id FROM list_items WHERE list_id = ?", (list_id,))[0][0]
    assert _sql("SELECT COUNT(*) FROM list_item_centres WHERE list_item_id = ?", (shared_item,))[0][0] == 0
    assert client.get('/api/favorites').json[0]['centres'] == ['c1']
