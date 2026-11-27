"""test_sepe_entity_alerts.py — alertes d'entitats autoritzades noves del SEPE (Pla 102).

Servei, API, baixa i embolcall del pipeline. Cap xarxa ni correu real: el SEPE
(sepe_scraper.fetch_entitats) i email_service.send_email sempre substituïts; BD i dades a tmp_path.
"""
import json
import os
from unittest.mock import patch

import pytest

import alerts_service
import app as app_module
import db
import sepe_entity_alerts_service as svc
from scrapers import pipeline, sepe_scraper
from tests.test_fpo_alerts_api import _login
from tests.test_fpo_api import fpo_data  # noqa: F401  (fixture: soc_*.json a tmp_path)
from tests.test_sepe_api import SEPE_ROWS

ROWS = [dict(r) for r in SEPE_ROWS]
ROWS[1]['codiAntic'] = 'SSCE0022'

E1 = {'id': '1', 'nom': 'ACADEMIA UNO', 'tipus': 'teleformacio', 'provincia': 'Madrid', 'adreca': 'CL A 1',
      'telefon': '911111111', 'web': 'http://uno.example', 'email': 'secret-uno@example.com'}
E2 = {'id': '2', 'nom': 'CENTRE DOS', 'tipus': 'presencial', 'provincia': 'Málaga', 'adreca': None,
      'telefon': None, 'web': None, 'email': 'secret-dos@example.com'}
E3 = {'id': '3', 'nom': 'CENTRE TRES', 'tipus': 'presencial', 'provincia': 'Madrid', 'adreca': None,
      'telefon': None, 'web': None, 'email': 'secret-tres@example.com'}
E4 = {'id': '4', 'nom': 'ACADEMIA QUATRE', 'tipus': 'teleformacio', 'provincia': 'Barcelona', 'adreca': None,
      'telefon': None, 'web': None, 'email': None}

BASE = 'https://grausfp.test'


@pytest.fixture(autouse=True)
def _no_real_email():
    with patch('email_service.send_email') as send:
        yield send


@pytest.fixture
def env(fpo_data, monkeypatch):  # noqa: F811
    """tmp_path amb el catàleg SEPE, una BD pròpia i les cadenes de cache de l'app reiniciades."""
    (fpo_data / 'sepe_especs.json').write_text(json.dumps(ROWS), encoding='utf-8')
    monkeypatch.setattr(app_module, '_sepe_llista_cache', {'key': None, 'data': None})
    monkeypatch.setattr(app_module, 'SEPE_ENTITATS_DIR', str(fpo_data / 'sepe_entitats'))
    test_db = str(fpo_data / 'test.db')
    monkeypatch.setenv('DB_PATH', test_db)
    db.init_db(db_path=test_db)
    return fpo_data


@pytest.fixture
def conn(env):
    c = db.get_db()
    yield c
    c.close()


@pytest.fixture
def fetch(monkeypatch):
    """Mock de sepe_scraper.fetch_entitats: `calls['by_id'][idSepe]` és la llista (o l'excepció)."""
    calls = {'ids': [], 'by_id': {}}

    def fake(id_sepe, session=None):
        calls['ids'].append(id_sepe)
        result = calls['by_id'].get(id_sepe, [])
        if isinstance(result, Exception):
            raise result
        return [dict(e) for e in result]

    monkeypatch.setattr(sepe_scraper, 'fetch_entitats', fake)
    return calls


def _user(conn, email, verified=1, is_active=1, deleted=False):
    cur = conn.execute("INSERT INTO users (email, password_hash, verified, is_active, deleted_at) "
                       "VALUES (?, 'x', ?, ?, ?)", (email, verified, is_active, '2026-01-01' if deleted else None))
    conn.commit()
    return cur.lastrowid


def _ealert(conn, user_id, codi='SSCE22', provincia=None, tele=0, active=1):
    cur = conn.execute("INSERT INTO sepe_entity_alerts (user_id, codi, provincia, nomes_teleformacio, active) "
                       "VALUES (?, ?, ?, ?, ?)", (user_id, codi, provincia, tele, active))
    conn.commit()
    return cur.lastrowid


def _run(env, pause_s=0):
    return svc.check_new_entities(str(env), BASE, BASE, pause_s=pause_s)


def _snapshot(conn, codi='SSCE22'):
    return svc.load_snapshot(conn, codi)


# --- peces petites -------------------------------------------------------------

def test_entity_key_inclou_el_tipus():
    assert svc.entity_key(E1) == '1|teleformacio'
    assert svc.entity_key({'id': '1', 'tipus': 'presencial'}) != svc.entity_key({'id': '1', 'tipus': 'teleformacio'})


def test_match_provincia_sense_majuscules_ni_accents():
    a = {'provincia': 'malaga', 'nomes_teleformacio': 0}
    assert svc.match(a, E2)
    assert not svc.match(a, E1)
    assert svc.match({'provincia': None, 'nomes_teleformacio': 0}, E1)
    assert svc.match({'provincia': '  MÁLAGA ', 'nomes_teleformacio': 0}, E2)


def test_match_nomes_teleformacio():
    a = {'provincia': None, 'nomes_teleformacio': 1}
    assert svc.match(a, E1)
    assert not svc.match(a, E2)


def test_snapshot_ordenat_i_substituit(conn):
    assert svc.load_snapshot(conn, 'SSCE22') is None
    svc.save_snapshot(conn, 'SSCE22', {'2|presencial', '1|teleformacio'})
    assert svc.load_snapshot(conn, 'SSCE22') == {'1|teleformacio', '2|presencial'}
    raw = conn.execute("SELECT entitat_keys FROM sepe_entity_snapshots WHERE codi = 'SSCE22'").fetchone()[0]
    assert json.loads(raw) == ['1|teleformacio', '2|presencial']
    svc.save_snapshot(conn, 'SSCE22', {'9|presencial'})
    assert svc.load_snapshot(conn, 'SSCE22') == {'9|presencial'}


# --- servei --------------------------------------------------------------------

def test_primera_passada_desa_la_instantania_sense_correu(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u)
    fetch['by_id'][97614] = [E1]
    assert _run(env) == 0
    assert _no_real_email.call_count == 0
    assert _snapshot(conn) == {'1|teleformacio'}


def test_segona_passada_amb_una_entitat_nova_envia_un_correu(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    alert_id = _ealert(conn, u)
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2]
    assert _run(env) == 1
    assert _no_real_email.call_count == 1
    to, subject, body = _no_real_email.call_args[0]
    assert to == 'a@example.com'
    assert '1' in subject
    assert 'CENTRE DOS' in body and 'Málaga' in body and 'presencial' in body
    assert 'ACADEMIA UNO' not in body                      # ja era a la instantània
    assert 'AUTORITZADA' in body.upper() and 'SSCE22' in body
    assert 'TUTORIZACION EN TELEFORMACIÓN'.lower() in body.lower()
    assert f'{BASE}/index.html?grado=SEPE&q=SSCE22' in body
    assert f'{BASE}/api/sepe/entity-alerts/{alert_id}/unsubscribe?token=' in body
    # Mai el correu de l'entitat (només per a admins) ni dades fiscals
    assert 'secret-dos@example.com' not in body and 'secret-uno@example.com' not in body
    assert conn.execute("SELECT last_sent_at FROM sepe_entity_alerts WHERE id = ?", (alert_id,)).fetchone()[0]
    assert _snapshot(conn) == {'1|teleformacio', '2|presencial'}


def test_el_text_diu_que_no_es_un_curs_amb_dates(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u)
    fetch['by_id'][97614] = []
    _run(env)
    fetch['by_id'][97614] = [E2]
    _run(env)
    body = _no_real_email.call_args[0][2].lower()
    assert 'no vol dir' in body and 'dates' in body


def test_filtre_de_provincia(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, provincia='madrid')
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2, E3]
    assert _run(env) == 1
    body = _no_real_email.call_args[0][2]
    assert 'CENTRE TRES' in body and 'CENTRE DOS' not in body


def test_filtre_de_provincia_ignora_accents(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, provincia='malaga')
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2, E3]
    assert _run(env) == 1
    assert 'CENTRE DOS' in _no_real_email.call_args[0][2]


def test_filtre_nomes_teleformacio(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, tele=1)
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2, E4]
    assert _run(env) == 1
    body = _no_real_email.call_args[0][2]
    assert 'ACADEMIA QUATRE' in body and 'CENTRE DOS' not in body


def test_sense_entitats_noves_per_a_aquell_filtre_no_s_envia_res(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, provincia='Sevilla')
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2]
    assert _run(env) == 0
    assert _no_real_email.call_count == 0


def test_un_usuari_amb_dues_alertes_rep_un_sol_correu_amb_les_dues_seccions(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, codi='SSCE22')
    _ealert(conn, u, codi='IFCD0112')
    fetch['by_id'][97614] = [E1]
    fetch['by_id'][777] = [E3]
    _run(env)
    fetch['by_id'][97614] = [E1, E2]
    fetch['by_id'][777] = [E3, E4]
    assert _run(env) == 1
    assert _no_real_email.call_count == 1
    body = _no_real_email.call_args[0][2]
    assert 'SSCE22' in body and 'IFCD0112' in body
    assert 'CENTRE DOS' in body and 'ACADEMIA QUATRE' in body
    assert body.count('/api/sepe/entity-alerts/') == 2     # una baixa per alerta


def test_cada_usuari_rep_el_seu_correu(env, conn, fetch, _no_real_email):
    a = _user(conn, 'a@example.com')
    b = _user(conn, 'b@example.com')
    _ealert(conn, a)
    _ealert(conn, b, provincia='Madrid')
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2, E3]
    assert _run(env) == 2
    assert fetch['ids'].count(97614) == 2                  # una crida per passada, no per alerta
    sent = {c[0][0]: c[0][2] for c in _no_real_email.call_args_list}
    assert 'CENTRE DOS' in sent['a@example.com'] and 'CENTRE DOS' not in sent['b@example.com']


def test_nomes_es_demanen_les_especialitats_amb_alertes_actives_d_usuaris_valids(env, conn, fetch, _no_real_email):
    ok = _user(conn, 'ok@example.com')
    unverified = _user(conn, 'u@example.com', verified=0)
    inactive = _user(conn, 'i@example.com', is_active=0)
    deleted = _user(conn, 'd@example.com', deleted=True)
    _ealert(conn, ok, codi='SSCE22')
    _ealert(conn, ok, codi='IFCD0112', active=0)           # en pausa
    for u in (unverified, inactive, deleted):
        _ealert(conn, u, codi='IFCD0112')
    _run(env)
    assert fetch['ids'] == [97614]
    assert _no_real_email.call_count == 0


def test_un_error_en_una_especialitat_no_atura_les_altres_i_conserva_la_instantania(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, codi='SSCE22')
    _ealert(conn, u, codi='IFCD0112')
    svc.save_snapshot(conn, 'SSCE22', {'1|teleformacio'})
    svc.save_snapshot(conn, 'IFCD0112', {'3|presencial'})
    fetch['by_id'][97614] = ConnectionError('SEPE caigut')
    fetch['by_id'][777] = [E3, E4]
    assert _run(env) == 1
    assert _snapshot(conn, 'SSCE22') == {'1|teleformacio'}                       # intacta
    assert _snapshot(conn, 'IFCD0112') == {'3|presencial', '4|teleformacio'}
    assert 'ACADEMIA QUATRE' in _no_real_email.call_args[0][2]


def test_una_entitat_que_desapareix_i_torna_no_s_anuncia_dues_vegades(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u)
    fetch['by_id'][97614] = [E1, E2]
    _run(env)
    fetch['by_id'][97614] = [E1]                            # E2 desapareix un cop
    _run(env)
    assert _snapshot(conn) == {'1|teleformacio', '2|presencial'}
    fetch['by_id'][97614] = [E1, E2]                        # i torna
    assert _run(env) == 0
    assert _no_real_email.call_count == 0


def test_una_entitat_que_passa_a_teleformacio_compta_com_a_nova(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u)
    fetch['by_id'][97614] = [E3]
    _run(env)
    fetch['by_id'][97614] = [E3, dict(E3, tipus='teleformacio')]
    assert _run(env) == 1


def test_s_esborren_les_instantanies_sense_cap_alerta(env, conn, fetch):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u, codi='SSCE22')
    _ealert(conn, u, codi='IFCD0112', active=0)             # en pausa: la fila existeix, la instantània es conserva
    svc.save_snapshot(conn, 'SSCE22', {'1|teleformacio'})
    svc.save_snapshot(conn, 'IFCD0112', {'3|presencial'})
    svc.save_snapshot(conn, 'ZZZZ9999', {'8|presencial'})   # ningú no la vol
    _run(env)
    assert _snapshot(conn, 'ZZZZ9999') is None
    assert _snapshot(conn, 'IFCD0112') == {'3|presencial'}
    assert _snapshot(conn, 'SSCE22') is not None


def test_el_correu_resumeix_el_que_passa_del_maxim(env, conn, fetch, _no_real_email):
    u = _user(conn, 'a@example.com')
    _ealert(conn, u)
    fetch['by_id'][97614] = [E1]
    _run(env)
    many = [E1] + [dict(E3, id=str(100 + i), nom=f'ENTITAT {i:03d}') for i in range(svc.MAX_ENTITATS_PER_ALERTA + 5)]
    fetch['by_id'][97614] = many
    assert _run(env) == 1
    body = _no_real_email.call_args[0][2]
    assert 'ENTITAT 000' in body and f'ENTITAT {svc.MAX_ENTITATS_PER_ALERTA + 4:03d}' not in body
    assert '… i 5 més' in body


def test_un_error_amb_un_usuari_no_bloqueja_els_altres(env, conn, fetch, _no_real_email):
    a = _user(conn, 'a@example.com')
    b = _user(conn, 'b@example.com')
    _ealert(conn, a)
    _ealert(conn, b)
    fetch['by_id'][97614] = [E1]
    _run(env)
    fetch['by_id'][97614] = [E1, E2]
    _no_real_email.side_effect = [RuntimeError('SMTP'), None]
    assert _run(env) == 1
    assert _no_real_email.call_count == 2


def test_embolcall_del_pipeline_no_falla_si_el_servei_falla(env):
    with patch('sepe_entity_alerts_service.check_new_entities', side_effect=RuntimeError('boom')):
        assert pipeline.notify_sepe_entity_alerts(str(env)) == 0


def test_embolcall_del_pipeline_retorna_els_correus_enviats(env):
    with patch('sepe_entity_alerts_service.check_new_entities', return_value=3) as check:
        assert pipeline.notify_sepe_entity_alerts(str(env)) == 3
    assert check.call_args[0][0] == str(env)


# --- API -----------------------------------------------------------------------

@pytest.fixture
def client(env):
    return _login('ent@example.com')


def _sql(query, params=()):
    c = db.get_db()
    try:
        rows = c.execute(query, params).fetchall()
        c.commit()
        return rows
    finally:
        c.close()


def test_api_sense_sessio_dona_401(env):
    c = app_module.app.test_client()
    assert c.get('/api/sepe/entity-alerts').status_code == 401
    assert c.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).status_code == 401
    assert c.patch('/api/sepe/entity-alerts/1', json={'active': False}).status_code == 401
    assert c.delete('/api/sepe/entity-alerts/1').status_code == 401


def test_api_crear_i_llistar(client):
    assert client.get('/api/sepe/entity-alerts').json == []
    r = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': ' Madrid ',
                                                      'nomes_teleformacio': True})
    assert r.status_code == 201, r.json
    r2 = client.post('/api/sepe/entity-alerts', json={'codi': 'IFCD0112'})
    assert r2.status_code == 201
    items = client.get('/api/sepe/entity-alerts').json
    assert [i['codi'] for i in items] == ['IFCD0112', 'SSCE22']          # la més nova primer
    ssce = items[1]
    assert set(ssce) == {'id', 'codi', 'titol', 'provincia', 'nomes_teleformacio', 'active', 'created_at',
                         'last_sent_at'}
    assert ssce['provincia'] == 'Madrid' and ssce['nomes_teleformacio'] is True and ssce['active'] is True
    assert ssce['titol']['es'] and ssce['titol']['ca']
    assert items[0]['provincia'] is None and items[0]['nomes_teleformacio'] is False


def test_api_el_codi_antic_es_desa_com_a_net(client):
    assert client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE0022'}).status_code == 201
    assert client.get('/api/sepe/entity-alerts').json[0]['codi'] == 'SSCE22'


def test_api_provincia_buida_es_qualsevol(client):
    assert client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': ''}).status_code == 201
    assert client.get('/api/sepe/entity-alerts').json[0]['provincia'] is None


@pytest.mark.parametrize('body', [
    {},
    {'codi': 'ZZZZ9999'},
    {'codi': 12},
    {'codi': ''},
    {'codi': 'S' * 41},
    {'codi': 'SSCE22', 'provincia': 7},
    {'codi': 'SSCE22', 'provincia': 'P' * 61},
    {'codi': 'SSCE22', 'nomes_teleformacio': 'si'},
    {'codi': 'SSCE22', 'nomes_teleformacio': 1},
])
def test_api_cos_invalid_dona_400(client, body):
    assert client.post('/api/sepe/entity-alerts', json=body).status_code == 400
    assert client.get('/api/sepe/entity-alerts').json == []


def test_api_duplicada_reactiva_i_diu_already_exists(client):
    first = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': 'Madrid'})
    alert_id = first.json['id']
    client.patch(f'/api/sepe/entity-alerts/{alert_id}', json={'active': False})
    r = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': 'MADRID'})
    assert r.status_code == 200 and r.json['status'] == 'already_exists' and r.json['id'] == alert_id
    assert client.get('/api/sepe/entity-alerts').json[0]['active'] is True
    assert len(client.get('/api/sepe/entity-alerts').json) == 1


def test_api_onzena_alerta_dona_429(client):
    for i in range(svc.ALERTS_MAX_PER_USER):
        assert client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': f'P{i}'}).status_code == 201
    assert client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': 'P-extra'}).status_code == 429
    # Una duplicada d'una existent no compta com a nova
    assert client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22', 'provincia': 'P0'}).status_code == 200


def test_api_la_creacio_desa_la_instantania_des_de_la_cache_d_entitats(client, env):
    os.makedirs(env / 'sepe_entitats')
    (env / 'sepe_entitats' / 'SSCE22.json').write_text(
        json.dumps({'entitats': [E1, E2], 'actualitzat': '2026-11-27T00:00:00+00:00'}), encoding='utf-8')
    assert client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).status_code == 201
    c = db.get_db()
    try:
        assert svc.load_snapshot(c, 'SSCE22') == {'1|teleformacio', '2|presencial'}
    finally:
        c.close()


def test_api_la_creacio_no_trepitja_una_instantania_existent_ni_en_crea_sense_cache(client, env):
    c = db.get_db()
    try:
        svc.save_snapshot(c, 'IFCD0112', {'3|presencial'})
    finally:
        c.close()
    os.makedirs(env / 'sepe_entitats')
    (env / 'sepe_entitats' / 'IFCD0112.json').write_text(json.dumps({'entitats': [E1]}), encoding='utf-8')
    client.post('/api/sepe/entity-alerts', json={'codi': 'IFCD0112'})
    client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'})        # sense fitxer de cache
    c = db.get_db()
    try:
        assert svc.load_snapshot(c, 'IFCD0112') == {'3|presencial'}
        assert svc.load_snapshot(c, 'SSCE22') is None
    finally:
        c.close()


def test_api_patch_pausa_i_reprèn(client):
    alert_id = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).json['id']
    assert client.patch(f'/api/sepe/entity-alerts/{alert_id}', json={'active': False}).status_code == 200
    assert client.get('/api/sepe/entity-alerts').json[0]['active'] is False
    assert client.patch(f'/api/sepe/entity-alerts/{alert_id}', json={'active': 'no'}).status_code == 400
    assert client.patch(f'/api/sepe/entity-alerts/{alert_id}', json={'active': True}).status_code == 200
    assert client.get('/api/sepe/entity-alerts').json[0]['active'] is True


def test_api_una_alerta_aliena_dona_404(client, env):
    alert_id = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).json['id']
    other = _login('other@example.com')
    assert other.patch(f'/api/sepe/entity-alerts/{alert_id}', json={'active': False}).status_code == 404
    assert other.delete(f'/api/sepe/entity-alerts/{alert_id}').status_code == 404
    assert client.get('/api/sepe/entity-alerts').json[0]['active'] is True
    assert other.get('/api/sepe/entity-alerts').json == []


def test_api_delete_esborra_l_alerta_i_els_seus_tokens(client):
    alert_id = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).json['id']
    keep_id = client.post('/api/sepe/entity-alerts', json={'codi': 'IFCD0112'}).json['id']
    user_id = _sql("SELECT id FROM users WHERE email = 'ent@example.com'")[0][0]
    conn = db.get_db()
    try:
        alerts_service._get_or_create_unsubscribe_token(conn, alert_id, user_id, kind=svc.TOKEN_KIND,
                                                        token_type=svc.TOKEN_TYPE)
        alerts_service._get_or_create_unsubscribe_token(conn, keep_id, user_id, kind=svc.TOKEN_KIND,
                                                        token_type=svc.TOKEN_TYPE)
    finally:
        conn.close()
    assert client.delete(f'/api/sepe/entity-alerts/{alert_id}').status_code == 204
    assert [r[0] for r in _sql("SELECT id FROM sepe_entity_alerts")] == [keep_id]
    tokens = [r[0] for r in _sql("SELECT token FROM tokens WHERE type = ?", (svc.TOKEN_TYPE,))]
    assert len(tokens) == 1 and tokens[0].startswith(f'{svc.TOKEN_KIND}_{keep_id}_')


def test_api_baixa_per_enllac_pausa_l_alerta(client):
    alert_id = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).json['id']
    user_id = _sql("SELECT id FROM users WHERE email = 'ent@example.com'")[0][0]
    conn = db.get_db()
    try:
        token = alerts_service._get_or_create_unsubscribe_token(conn, alert_id, user_id, kind=svc.TOKEN_KIND,
                                                                token_type=svc.TOKEN_TYPE)
    finally:
        conn.close()
    anon = app_module.app.test_client()                    # sense sessió
    r = anon.get(f'/api/sepe/entity-alerts/{alert_id}/unsubscribe?token={token}')
    assert r.status_code == 302 and r.headers['Location'].endswith('/?unsubscribed=1')
    assert client.get('/api/sepe/entity-alerts').json[0]['active'] is False
    # El token és d'un sol ús
    again = anon.get(f'/api/sepe/entity-alerts/{alert_id}/unsubscribe?token={token}')
    assert again.headers['Location'].endswith('/?unsubscribe_error=1')


def test_api_baixa_amb_token_dolent(client):
    alert_id = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).json['id']
    anon = app_module.app.test_client()
    r = anon.get(f'/api/sepe/entity-alerts/{alert_id}/unsubscribe?token=nope')
    assert r.status_code == 302 and r.headers['Location'].endswith('/?unsubscribe_error=1')
    assert anon.get(f'/api/sepe/entity-alerts/{alert_id}/unsubscribe').headers['Location'].endswith(
        '/?unsubscribe_error=1')
    assert client.get('/api/sepe/entity-alerts').json[0]['active'] is True


def test_api_el_token_d_una_alerta_fpo_no_serveix_per_a_una_d_entitats(client):
    alert_id = client.post('/api/sepe/entity-alerts', json={'codi': 'SSCE22'}).json['id']
    user_id = _sql("SELECT id FROM users WHERE email = 'ent@example.com'")[0][0]
    conn = db.get_db()
    try:
        token = alerts_service._get_or_create_unsubscribe_token(conn, alert_id, user_id, kind='fpoalert',
                                                                token_type='fpo_alert_unsubscribe')
    finally:
        conn.close()
    r = app_module.app.test_client().get(f'/api/sepe/entity-alerts/{alert_id}/unsubscribe?token={token}')
    assert r.headers['Location'].endswith('/?unsubscribe_error=1')


def test_api_cors_amb_credencials_per_a_les_rutes_noves(env):
    assert app_module._needs_auth_cors('/api/sepe/entity-alerts')
    assert app_module._needs_auth_cors('/api/sepe/entity-alerts/3')
