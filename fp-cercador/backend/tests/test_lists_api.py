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


# --- Fase 2: API de llistes ---------------------------------------------------

def _crea(client, name='Per a la Marta', **extra):
    r = client.post('/api/lists', json={'name': name, **extra})
    assert r.status_code == 201, r.json
    return r.json['id']


def test_sense_sessio_dona_401(data):
    c = flask_app.test_client()
    for method, path in [('get', '/api/lists'), ('post', '/api/lists'), ('get', '/api/lists/1'),
                         ('patch', '/api/lists/1'), ('delete', '/api/lists/1'),
                         ('put', '/api/lists/1/items/ADG_B_3001'), ('delete', '/api/lists/1/items/ADG_B_3001'),
                         ('post', '/api/lists/1/share'), ('delete', '/api/lists/1/share')]:
        assert getattr(c, method)(path).status_code == 401, (method, path)


def test_crear_llistar_i_llegir(client):
    assert client.get('/api/lists').json == []
    list_id = _crea(client, name='  Per a la Marta ', message=' Mira aquests ')
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001', json={'notes': 'Té sortida'})
    resum = client.get('/api/lists').json
    assert len(resum) == 1
    assert set(resum[0]) == {'id', 'name', 'message', 'n_items', 'shared', 'updated_at'}
    assert (resum[0]['name'], resum[0]['message'], resum[0]['n_items'], resum[0]['shared']) == \
        ('Per a la Marta', 'Mira aquests', 1, False)
    detall = client.get(f'/api/lists/{list_id}').json
    assert detall['share_token'] is None
    assert detall['items'] == [{
        'ref': 'ADG_B_3001', 'notes': 'Té sortida', 'grado': 'B', 'codigo': 'ADG_B_3001',
        'denominacion': 'Grau ADG_B_3001', 'familia': 'Administración y Gestión', 'nivel': 1,
        'n_centres': 2, 'disponible': True}]


def test_la_llista_de_favorits_no_surt_ni_es_pot_tocar(client):
    client.post('/api/favorites', json={'ref': 'ADG_B_3001'})
    fav_id = _sql("SELECT id FROM lists WHERE kind = 'favorites'")[0][0]
    assert client.get('/api/lists').json == []
    assert client.get(f'/api/lists/{fav_id}').status_code == 404
    assert client.delete(f'/api/lists/{fav_id}').status_code == 404
    assert client.post(f'/api/lists/{fav_id}/share').status_code == 404
    assert [f['ref'] for f in client.get('/api/favorites').json] == ['ADG_B_3001']


def test_aillament_entre_usuaris_dona_404(client):
    list_id = _crea(client)
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001')
    altre = _login('altre@example.com')
    assert altre.get('/api/lists').json == []
    assert altre.get(f'/api/lists/{list_id}').status_code == 404
    assert altre.patch(f'/api/lists/{list_id}', json={'name': 'Meva'}).status_code == 404
    assert altre.delete(f'/api/lists/{list_id}').status_code == 404
    assert altre.put(f'/api/lists/{list_id}/items/ADG_B_3002').status_code == 404
    assert altre.delete(f'/api/lists/{list_id}/items/ADG_B_3001').status_code == 404
    assert altre.post(f'/api/lists/{list_id}/share').status_code == 404
    assert altre.delete(f'/api/lists/{list_id}/share').status_code == 404
    detall = client.get(f'/api/lists/{list_id}').json
    assert (detall['name'], [i['ref'] for i in detall['items']], detall['share_token']) == \
        ('Per a la Marta', ['ADG_B_3001'], None)


def test_patch_canvia_nom_i_missatge(client):
    list_id = _crea(client, message='Hola')
    assert client.patch(f'/api/lists/{list_id}', json={'name': 'Nou nom'}).status_code == 200
    assert client.get(f'/api/lists/{list_id}').json['message'] == 'Hola'
    assert client.patch(f'/api/lists/{list_id}', json={'message': ''}).status_code == 200
    detall = client.get(f'/api/lists/{list_id}').json
    assert (detall['name'], detall['message']) == ('Nou nom', None)


def test_esborrar_la_llista(client):
    list_id = _crea(client)
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001')
    assert client.delete(f'/api/lists/{list_id}').status_code == 204
    assert client.get('/api/lists').json == []
    assert _sql("SELECT COUNT(*) FROM list_items")[0][0] == 0


def test_afegir_anotar_i_treure_un_grau(client):
    list_id = _crea(client)
    assert client.put(f'/api/lists/{list_id}/items/ADG_B_3001').status_code == 201
    assert client.put(f'/api/lists/{list_id}/items/ADG_B_3001', json={'notes': ' Bona opció '}).status_code == 200
    assert client.put(f'/api/lists/{list_id}/items/ADG_B_3001').status_code == 200  # sense cos: la nota es queda
    client.put(f'/api/lists/{list_id}/items/ADG_C_001_3B', json={'notes': None})
    items = client.get(f'/api/lists/{list_id}').json['items']
    assert [(i['ref'], i['notes']) for i in items] == [('ADG_B_3001', 'Bona opció'), ('ADG_C_001_3B', None)]
    assert client.delete(f'/api/lists/{list_id}/items/ADG_B_3001').status_code == 204
    assert [i['ref'] for i in client.get(f'/api/lists/{list_id}').json['items']] == ['ADG_C_001_3B']


@pytest.mark.parametrize('ref', ['no-existeix', 'ADG_B_9999', '999'])
def test_un_ref_que_no_es_al_cataleg_es_rebutja(client, ref):
    list_id = _crea(client)
    assert client.put(f'/api/lists/{list_id}/items/{ref}').status_code == 400
    assert client.get(f'/api/lists/{list_id}').json['items'] == []


@pytest.mark.parametrize('cos', [
    None, [], 'text', {}, {'name': ''}, {'name': '   '}, {'name': 7}, {'name': 'x' * 81},
    {'name': 'ok', 'message': 7}, {'name': 'ok', 'message': 'x' * 501},
])
def test_crear_valida_el_cos(client, cos):
    assert client.post('/api/lists', json=cos).status_code == 400
    assert client.get('/api/lists').json == []


@pytest.mark.parametrize('cos', [
    None, [], {}, {'name': ''}, {'name': 'x' * 81}, {'message': 7}, {'message': 'x' * 501},
])
def test_patch_valida_el_cos(client, cos):
    list_id = _crea(client, message='Hola')
    assert client.patch(f'/api/lists/{list_id}', json=cos).status_code == 400
    detall = client.get(f'/api/lists/{list_id}').json
    assert (detall['name'], detall['message']) == ('Per a la Marta', 'Hola')


@pytest.mark.parametrize('cos', [[], 'text', {'notes': 7}, {'notes': 'x' * 301}])
def test_la_nota_es_valida(client, cos):
    list_id = _crea(client)
    assert client.put(f'/api/lists/{list_id}/items/ADG_B_3001', json=cos).status_code == 400
    assert client.get(f'/api/lists/{list_id}').json['items'] == []


def test_limit_de_llistes_per_usuari(client, monkeypatch):
    monkeypatch.setattr(app_module, '_LISTS_MAX_PER_USER', 2)
    _crea(client, name='u')
    _crea(client, name='dos')
    assert client.post('/api/lists', json={'name': 'tres'}).status_code == 429
    assert len(client.get('/api/lists').json) == 2


def test_limit_de_graus_per_llista(client, monkeypatch):
    monkeypatch.setattr(app_module, '_LISTS_MAX_ITEMS', 2)
    list_id = _crea(client)
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001')
    client.put(f'/api/lists/{list_id}/items/ADG_B_3002')
    assert client.put(f'/api/lists/{list_id}/items/ADG_C_001_3B').status_code == 429
    assert client.put(f'/api/lists/{list_id}/items/ADG_B_3001', json={'notes': 'encara'}).status_code == 200


def test_updated_at_es_mou_amb_cada_canvi(client):
    list_id = _crea(client)
    _sql("UPDATE lists SET updated_at = '2000-01-01 00:00:00' WHERE id = ?", (list_id,))
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001')
    assert client.get('/api/lists').json[0]['updated_at'] > '2026'


# --- Fase 3: compartir ---------------------------------------------------------

def _comparteix(client, list_id):
    r = client.post(f'/api/lists/{list_id}/share')
    assert r.status_code == 200
    return r.json['share_token']


def test_la_vista_publica_no_porta_cap_dada_de_l_autor(client):
    list_id = _crea(client, message='Mira aquests')
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001', json={'notes': 'Té sortida'})
    token = _comparteix(client, list_id)
    assert len(token) >= 32
    assert client.get(f'/api/lists/{list_id}').json['share_token'] == token
    assert client.get('/api/lists').json[0]['shared'] is True

    r = flask_app.test_client().get(f'/api/llista/{token}')
    assert r.status_code == 200
    assert r.headers['X-Robots-Tag'] == 'noindex'
    assert set(r.json) == {'name', 'message', 'items'}
    assert (r.json['name'], r.json['message']) == ('Per a la Marta', 'Mira aquests')
    assert set(r.json['items'][0]) == {'ref', 'grado', 'codigo', 'denominacion', 'familia', 'nivel',
                                       'notes', 'n_centres', 'disponible'}
    assert 'orientador@example.com' not in r.get_data(as_text=True)


def test_regenerar_l_enllac_mata_l_antic(client):
    list_id = _crea(client)
    antic = _comparteix(client, list_id)
    nou = _comparteix(client, list_id)
    assert nou != antic
    anon = flask_app.test_client()
    assert anon.get(f'/api/llista/{antic}').status_code == 404
    assert anon.get(f'/api/llista/{nou}').status_code == 200


def test_revocar_l_enllac(client):
    list_id = _crea(client)
    token = _comparteix(client, list_id)
    assert client.delete(f'/api/lists/{list_id}/share').status_code == 204
    r = flask_app.test_client().get(f'/api/llista/{token}')
    assert r.status_code == 404
    assert r.headers['X-Robots-Tag'] == 'noindex'
    assert client.get(f'/api/lists/{list_id}').json['share_token'] is None


def test_esborrar_la_llista_mata_l_enllac(client):
    list_id = _crea(client)
    token = _comparteix(client, list_id)
    client.delete(f'/api/lists/{list_id}')
    assert flask_app.test_client().get(f'/api/llista/{token}').status_code == 404


def test_un_grau_que_ja_no_es_al_cataleg_surt_no_disponible(client, data):
    list_id = _crea(client)
    client.put(f'/api/lists/{list_id}/items/ADG_B_3001', json={'notes': 'Nota'})
    client.put(f'/api/lists/{list_id}/items/ADG_B_3002')
    token = _comparteix(client, list_id)
    data.write_text(json.dumps([r for r in _cataleg() if r['codigo'] != 'ADG_B_3001']), encoding='utf-8')
    app_module._catalog_cache.update(key=None, data=None)
    items = flask_app.test_client().get(f'/api/llista/{token}').json['items']
    assert items[0] == {'ref': 'ADG_B_3001', 'notes': 'Nota', 'disponible': False, 'grado': None,
                        'codigo': None, 'denominacion': None, 'familia': None, 'nivel': None, 'n_centres': 0}
    assert items[1]['disponible'] is True
    # i l'autor el pot treure encara que ja no sigui al catàleg
    assert client.delete(f'/api/lists/{list_id}/items/ADG_B_3001').status_code == 204


def test_nomes_els_tokens_inexistents_gasten_el_limit_per_ip(client, monkeypatch):
    monkeypatch.setattr(app_module, '_AUTH_EMAIL_IP_LIMIT', 3)
    token = _comparteix(client, _crea(client))
    anon = flask_app.test_client()
    # una classe sencera darrere la mateixa IP ha de poder obrir l'enllaç bo
    assert all(anon.get(f'/api/llista/{token}').status_code == 200 for _ in range(10))
    assert [anon.get(f'/api/llista/dolent{i}').status_code for i in range(5)] == [404, 404, 404, 429, 429]
    # qui ha gastat el límit provant tokens tampoc no pot distingir els bons
    assert anon.get(f'/api/llista/{token}').status_code == 429


def test_la_llista_de_favorits_no_es_pot_obrir_per_token(client):
    client.post('/api/favorites', json={'ref': 'ADG_B_3001'})
    _sql("UPDATE lists SET share_token = 'abc' WHERE kind = 'favorites'")
    assert flask_app.test_client().get('/api/llista/abc').status_code == 404
