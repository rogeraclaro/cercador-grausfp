"""
test_refs_api.py — L'API va per la clau estable `ref` (Pla 076): favorits,
centres, avisos de centres nous i itinerari sobreviuen a un refresc que
renumera els id. Els paràmetres antics (oferta_id, ?id=, ?codigo=) es
continuen acceptant (millor esforç).
"""
import json
import os
from unittest.mock import patch

import pytest

import app as app_module
import db

flask_app = app_module.app
flask_app.config["TESTING"] = True

ADG = 'Administración y Gestión'
URL = 'https://www.todofp.es/que-estudiar/familias-profesionales/{}.html'
REF_D = 'administracion-gestion~gestion-administrativa'


def _cataleg(desplacament=0):
    """Catàleg; amb desplacament > 0, hi ha registres nous al davant i tots els id canvien."""
    nous = [{'id': i + 1, 'grado': 'A', 'codigo': f'UF900{i}', 'familia': ADG,
             'denominacion': f'Nou {i}', 'nivel': 1, 'plan_antiguo': True} for i in range(desplacament)]
    base = [
        {'grado': 'C', 'codigo': 'ADGG0408', 'familia': ADG, 'denominacion': 'Operacions',
         'nivel': 1, 'plan_antiguo': True},
        {'grado': 'C', 'codigo': 'ADG_C_001_3B', 'familia': ADG, 'denominacion': 'C nou',
         'nivel': 3, 'plan_antiguo': False},
        {'grado': 'A', 'codigo': 'MF0432_1', 'familia': ADG, 'denominacion': 'Manipulació ADG',
         'nivel': 1, 'plan_antiguo': True},
        {'grado': 'A', 'codigo': 'MF0432_1', 'familia': 'Comercio y Marketing',
         'denominacion': 'Manipulació COM', 'nivel': 1, 'plan_antiguo': True},
        {'grado': 'D', 'codigo': None, 'familia': ADG, 'denominacion': 'Técnico en Gestión Administrativa',
         'nivel': 2, 'plan_antiguo': False, 'ficha_url': URL.format('administracion-gestion/gestion-administrativa')},
        {'grado': 'E', 'codigo': None, 'familia': ADG, 'denominacion': 'Curso de especialización X',
         'nivel': 3, 'plan_antiguo': False, 'ficha_url': URL.format('administracion-gestion/curso-x')},
    ]
    for i, r in enumerate(base, start=desplacament + 1):
        r['id'] = i
    return nous + base


def _id_of(records, ref):
    from oferta_ref import ensure_refs
    return next(r['id'] for r in ensure_refs(records) if r['ref'] == ref)


@pytest.fixture
def data(tmp_path, monkeypatch):
    paths = {name: tmp_path / f'{name}.json' for name in
             ('ofertes', 'centres', 'oferta_centres', 'ce_acces')}

    def escriu(records):
        paths['ofertes'].write_text(json.dumps(records), encoding='utf-8')
        # mtime diferent encara que el sistema de fitxers tingui resolució d'1 s
        st = os.stat(paths['ofertes'])
        os.utime(paths['ofertes'], (st.st_atime, st.st_mtime + 10))

    escriu(_cataleg())
    paths['centres'].write_text(json.dumps([{'id': 'M1', 'nombre': 'IES A', 'provincia': 'GIRONA'},
                                            {'id': 'M2', 'nombre': 'IES B', 'provincia': 'GIRONA'}]))
    paths['oferta_centres'].write_text(json.dumps({REF_D: ['M1', 'M2'], 'ADGG0408': ['M1'],
                                                   'ADG_C_001_3B': ['M2']}))
    missing = str(tmp_path / 'no_existeix.json')
    monkeypatch.setattr(app_module, 'DATA_PATH', str(paths['ofertes']))
    monkeypatch.setattr(app_module, '_CENTRES_PATH', str(paths['centres']))
    monkeypatch.setattr(app_module, '_OFERTA_CENTRES_PATH', str(paths['oferta_centres']))
    for attr in ('BC_LOE_PATH', 'BC_LOMLOE_PATH', 'A_LOE_PARES_PATH', 'D_MODULOS_PATH',
                 'CICLOS_PATH', 'CE_ACCES_PATH'):
        monkeypatch.setattr(app_module, attr, missing)
    monkeypatch.setattr(app_module, '_centres_index', None)
    monkeypatch.setattr(app_module, '_oferta_centres', None)
    for cache in ('_d_modulos_cache', '_bc_lomloe_cache', '_a_loe_pares_cache',
                  '_itinerary_index_cache', '_bc_loe_inverse_cache'):
        monkeypatch.setattr(app_module, cache, {'mtime': None, 'index': None})
    for cache in ('_cd_lomloe_cache', '_effective_oc_cache', '_itinerary_graph_cache'):
        monkeypatch.setattr(app_module, cache, {'key': None, 'data': None})

    test_db = str(tmp_path / 'test.db')
    monkeypatch.setenv('DB_PATH', test_db)
    db.init_db(db_path=test_db)
    paths['escriu'] = escriu
    return paths


@pytest.fixture
def client(data):
    c = flask_app.test_client()
    email = 'fav@example.com'
    with patch("email_service.send_verification_email"):
        c.post("/api/auth/register", json={"email": email, "password": "password123"})
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    assert c.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 200
    return c


# --- Favorits ---------------------------------------------------------------

def test_afegir_favorit_per_ref(client):
    assert client.post('/api/favorites', json={'ref': REF_D}).status_code == 201
    assert client.post('/api/favorites', json={'ref': REF_D}).json['status'] == 'already_exists'
    favs = client.get('/api/favorites').json
    assert [f['ref'] for f in favs] == [REF_D]
    assert favs[0]['oferta_id'] == _id_of(_cataleg(), REF_D)


@pytest.mark.parametrize('ref', ['NO_EXISTEIX', 'a b', '', None, 12])
def test_ref_invalid_o_desconegut_es_rebutja(client, ref):
    assert client.post('/api/favorites', json={'ref': ref}).status_code == 400


def test_favorit_antic_per_oferta_id_es_guarda_amb_ref(client):
    # Codi repetit: l'id hi coincideix, i el ref en conserva la família.
    oferta_id = _id_of(_cataleg(), 'MF0432_1~COM')
    r = client.post('/api/favorites', json={'oferta_id': oferta_id, 'oferta_codigo': 'MF0432_1'})
    assert r.status_code == 201
    assert [f['ref'] for f in client.get('/api/favorites').json] == ['MF0432_1~COM']


def test_favorits_i_centres_sobreviuen_a_la_renumeracio(client, data):
    client.post('/api/favorites', json={'ref': REF_D})
    client.post('/api/favorites', json={'ref': 'MF0432_1~ADG'})
    assert client.post(f'/api/favorites/{REF_D}/centres', json={'centre_id': 'M2'}).status_code == 201

    data['escriu'](_cataleg(desplacament=3))  # refresc: tots els id es desplacen

    favs = {f['ref']: f for f in client.get('/api/favorites').json}
    assert set(favs) == {REF_D, 'MF0432_1~ADG'}
    assert favs[REF_D]['centres'] == ['M2']
    assert favs[REF_D]['oferta_id'] == _id_of(_cataleg(3), REF_D)
    assert client.delete(f'/api/favorites/{REF_D}/centres/M2').status_code == 204
    assert client.delete('/api/favorites/MF0432_1~ADG').status_code == 204
    assert [f['ref'] for f in client.get('/api/favorites').json] == [REF_D]


def test_esborrar_favorit_per_id_antic(client):
    client.post('/api/favorites', json={'ref': 'ADGG0408'})
    assert client.delete(f"/api/favorites/{_id_of(_cataleg(), 'ADGG0408')}").status_code == 204
    assert client.get('/api/favorites').json == []


# --- Centres ----------------------------------------------------------------

def test_centres_per_ref(data):
    c = flask_app.test_client()
    assert [x['id'] for x in c.get(f'/api/centres?ref={REF_D}').json] == ['M1', 'M2']
    assert [x['id'] for x in c.get('/api/centres?ref=ADG_C_001_3B').json] == ['M2']


def test_centres_parametres_antics(data):
    c = flask_app.test_client()
    assert [x['id'] for x in c.get('/api/centres?codigo=ADGG0408').json] == ['M1']
    id_d = _id_of(_cataleg(), REF_D)
    assert [x['id'] for x in c.get(f'/api/centres?id={id_d}').json] == ['M1', 'M2']


def test_recompte_de_centres_per_ref(data):
    counts = flask_app.test_client().get('/api/centres/count').json
    assert counts[REF_D] == 2 and counts['ADG_C_001_3B'] == 1


def test_avis_de_centres_per_ref_sobreviu_a_la_renumeracio(client, data):
    r = client.post('/api/centres-watch', json={'oferta_key': REF_D, 'oferta_denom': 'Gestió'})
    assert r.status_code == 201
    data['escriu'](_cataleg(desplacament=2))
    data['oferta_centres'].write_text(json.dumps({REF_D: ['M1', 'M2', 'M3']}))
    import centres_watch_service
    with patch.object(centres_watch_service, '_OFERTA_CENTRES_PATH', str(data['oferta_centres'])), \
         patch.object(centres_watch_service, '_CENTRES_PATH', str(data['centres'])), \
         patch.object(centres_watch_service, '_OFERTES_PATH', str(data['ofertes'])):
        oc, _ = centres_watch_service._load_centres_data()
    watch = client.get('/api/centres-watch').json[0]
    assert watch['oferta_key'] == REF_D and oc[watch['oferta_key']] == ['M1', 'M2', 'M3']


def test_avis_amb_id_antic_es_desa_amb_ref(client):
    id_d = _id_of(_cataleg(), REF_D)
    client.post('/api/centres-watch', json={'oferta_key': str(id_d), 'oferta_denom': 'Gestió'})
    assert client.get('/api/centres-watch').json[0]['oferta_key'] == REF_D


# --- Itinerari --------------------------------------------------------------

def test_itinerari_per_ref(data):
    c = flask_app.test_client()
    body = c.get(f'/api/itinerari/complet?grado=D&ref={REF_D}').json
    assert body['focus'] == f'D:{REF_D}'
    node = body['nodes'][0]
    assert node['ref'] == REF_D and node['key'] == f'D:{REF_D}'


def test_itinerari_per_ref_de_codi_repetit(data):
    body = flask_app.test_client().get('/api/itinerari/complet?grado=A&ref=MF0432_1~COM').json
    assert body['focus'] == 'A:MF0432_1~COM'
    assert body['nodes'][0]['denominacion'] == 'Manipulació COM'


def test_itinerari_amb_id_antic_continua_funcionant(data):
    id_d = _id_of(_cataleg(), REF_D)
    body = flask_app.test_client().get(f'/api/itinerari/complet?grado=D&id={id_d}').json
    assert body['focus'] == f'D:{REF_D}'


def test_itinerari_ref_desconegut_o_invalid(data):
    c = flask_app.test_client()
    assert c.get('/api/itinerari/complet?grado=D&ref=x~no-existeix').status_code == 404
    assert c.get('/api/itinerari/complet?grado=D&ref=<script>').status_code == 400
    # El ref ha de ser del grau indicat.
    assert c.get('/api/itinerari/complet?grado=E&ref=' + REF_D).status_code == 404
