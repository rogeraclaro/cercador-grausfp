"""test_fpo_alerts_service.py — alertes de cursos FPO nous (Pla 086): coincidència, enviament
i ganxo al refresc. Cap correu real: email_service.send_email sempre substituït."""
import json
from unittest.mock import patch

import pytest

import db
import fpo_alerts_service as svc
from scrapers import pipeline
from tests.test_fpo_agenda import FAMILIES, _ext, _soc


@pytest.fixture(autouse=True)
def _no_real_email():
    with patch('email_service.send_email') as send:
        yield send


@pytest.fixture
def conn(tmp_path, monkeypatch):
    path = str(tmp_path / 'test.db')
    monkeypatch.setenv('DB_PATH', path)
    c = db.init_db(db_path=path)
    yield c
    c.close()


def _user(conn, email, verified=1, is_active=1, deleted=False):
    cur = conn.execute("INSERT INTO users (email, password_hash, verified, is_active, deleted_at) "
                       "VALUES (?, 'x', ?, ?, ?)", (email, verified, is_active, '2026-01-01' if deleted else None))
    conn.commit()
    return cur.lastrowid


def _alert(conn, user_id, comarca=None, familia=None, espec=None, en_linia=1, active=1):
    cur = conn.execute("INSERT INTO fpo_alerts (user_id, comarca, familia_codi, espec_codi, inclou_en_linia, active) "
                       "VALUES (?, ?, ?, ?, ?, ?)", (user_id, comarca, familia, espec, en_linia, active))
    conn.commit()
    return cur.lastrowid


def _a(comarca=None, familia=None, espec=None, en_linia=1):
    return {'comarca': comarca, 'familia_codi': familia, 'espec_codi': espec, 'inclou_en_linia': en_linia}


def _row(curs):
    import fpo_agenda
    return fpo_agenda.row(curs, FAMILIES)


# --- match -------------------------------------------------------------------

def test_match_per_comarca_sense_distingir_majuscules():
    curs = _row(_soc('1', '2026-12-01', comarca='BARCELONÈS'))
    assert svc.match(_a(comarca='Barcelonès'), curs)
    assert not svc.match(_a(comarca='Gironès'), curs)


def test_match_en_linia_si_l_alerta_els_inclou():
    tele = _row(_soc('1', '2026-12-01', comarca='', modalitat='TELEFORMACIÓ', centre={}))
    assert svc.match(_a(comarca='Gironès', en_linia=1), tele)
    assert not svc.match(_a(comarca='Gironès', en_linia=0), tele)
    presencial_sense_comarca = _row(_ext('PIMEC:x:1', '2026-12-01'))
    assert not svc.match(_a(comarca='Gironès'), presencial_sense_comarca)


def test_match_per_familia_i_especialitat():
    curs = _row(_soc('1', '2026-12-01'))
    assert svc.match(_a(familia='ADG'), curs)
    assert not svc.match(_a(familia='IFC'), curs)
    assert svc.match(_a(espec='ADGG0408'), curs)
    assert not svc.match(_a(espec='IFCD0112'), curs)
    assert svc.match(_a(comarca='Barcelonès', familia='ADG', espec='ADGG0408'), curs)
    assert not svc.match(_a(comarca='Barcelonès', familia='IFC'), curs)


# --- dispatch ----------------------------------------------------------------

NOUS = [_soc('26/1', '2026-12-01', comarca='BARCELONÈS'), _soc('26/2', '2026-12-05', comarca='GIRONÈS'),
        _ext('PIMEC:excel:1', '2026-12-10', modalitat='TELEFORMACIÓ')]


def test_un_sol_correu_per_usuari_amb_els_cursos_agrupats_per_alerta(conn, _no_real_email):
    u = _user(conn, 'a@example.com')
    a1 = _alert(conn, u, comarca='Barcelonès', en_linia=0)
    a2 = _alert(conn, u, familia='ADG')
    _alert(conn, u, comarca='Segrià', en_linia=0)        # sense cap curs: no surt al correu
    assert svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES) == 1
    assert _no_real_email.call_count == 1
    to, subject, body = _no_real_email.call_args[0]
    assert to == 'a@example.com'
    assert '2 que encaixen' in subject                     # cursos diferents, no files
    assert body.count('Alerta «') == 2 and 'Segrià' not in body
    assert 'Curs 26/1' in body and 'Curs 26/2' in body and 'Excel' not in body
    assert 'codi_curso_seleccionado=26/1' in body
    assert f'/api/fpo/alerts/{a1}/unsubscribe?token=' in body and f'/api/fpo/alerts/{a2}/unsubscribe?token=' in body
    sent = dict(conn.execute("SELECT id, last_sent_at FROM fpo_alerts").fetchall())
    assert sent[a1] and sent[a2] and list(sent.values()).count(None) == 1


def test_cada_usuari_rep_el_seu(conn, _no_real_email):
    _alert(conn, _user(conn, 'a@example.com'), comarca='Barcelonès')
    _alert(conn, _user(conn, 'b@example.com'), comarca='Gironès', en_linia=0)
    _alert(conn, _user(conn, 'c@example.com'), comarca='Segrià', en_linia=0)
    assert svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES) == 2
    bodies = {c[0][0]: c[0][2] for c in _no_real_email.call_args_list}
    assert set(bodies) == {'a@example.com', 'b@example.com'}
    assert 'Excel' in bodies['a@example.com'] and 'en línia' in bodies['a@example.com']
    assert 'Curs 26/2' in bodies['b@example.com'] and 'Excel' not in bodies['b@example.com']


def test_no_s_avisa_usuaris_no_verificats_inactius_o_esborrats_ni_alertes_pausades(conn, _no_real_email):
    _alert(conn, _user(conn, 'nv@example.com', verified=0), familia='ADG')
    _alert(conn, _user(conn, 'in@example.com', is_active=0), familia='ADG')
    _alert(conn, _user(conn, 'del@example.com', deleted=True), familia='ADG')
    _alert(conn, _user(conn, 'pausa@example.com'), familia='ADG', active=0)
    assert svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES) == 0
    _no_real_email.assert_not_called()


def test_sense_cursos_nous_no_es_fa_res(conn, _no_real_email):
    _alert(conn, _user(conn, 'a@example.com'), familia='ADG')
    assert svc.dispatch([], 'https://grausfp.test', FAMILIES) == 0
    _no_real_email.assert_not_called()


def test_un_error_amb_un_usuari_no_atura_els_altres(conn, _no_real_email):
    _alert(conn, _user(conn, 'falla@example.com'), familia='ADG')
    b = _alert(conn, _user(conn, 'b@example.com'), familia='ADG')
    _no_real_email.side_effect = [RuntimeError('smtp'), None]
    assert svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES) == 1
    sent = dict(conn.execute("SELECT id, last_sent_at FROM fpo_alerts").fetchall())
    assert sent[b] and list(sent.values()).count(None) == 1


def test_el_token_de_baixa_es_reutilitza_i_es_renova_si_ha_caducat(conn, _no_real_email):
    a = _alert(conn, _user(conn, 'a@example.com'), familia='ADG')

    def _token():
        return _no_real_email.call_args[0][2].split(f'/api/fpo/alerts/{a}/unsubscribe?token=')[1].split()[0]

    svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES)
    primer = _token()
    svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES)
    assert _token() == primer
    conn.execute("UPDATE tokens SET expires_at = '2000-01-01 00:00:00' WHERE type = 'fpo_alert_unsubscribe'")
    conn.commit()
    svc.dispatch(NOUS, 'https://grausfp.test', FAMILIES)
    assert _token() != primer
    rows = conn.execute("SELECT token, expires_at FROM tokens WHERE type = 'fpo_alert_unsubscribe'").fetchall()
    assert len(rows) == 1 and rows[0][0] == f'fpoalert_{a}_{_token()}' and rows[0][1] > '2026'


def test_el_correu_resumeix_les_llistes_llargues(conn, _no_real_email):
    _alert(conn, _user(conn, 'a@example.com'), familia='ADG')
    molts = [_soc(f'26/{i}', '2026-12-01') for i in range(25)]
    svc.dispatch(molts, 'https://grausfp.test', FAMILIES)
    body = _no_real_email.call_args[0][2]
    assert body.count('  • ') == 20 and 'i 5 més' in body


# --- cursos nous i ganxo al refresc -------------------------------------------

def test_fpo_new_courses_per_idcurs():
    prev = [_soc('1', '2026-12-01'), _ext('PIMEC:a:1', '2026-12-01')]
    curr = [_soc('1', '2026-12-01'), _soc('2', '2026-12-02'), _ext('PIMEC:a:1', '2026-12-01'),
            _ext('PIMEC:b:1', '2026-12-03')]
    assert [c['idCurs'] for c in pipeline.fpo_new_courses(prev, curr)] == ['2', 'PIMEC:b:1']
    assert pipeline.fpo_new_courses(curr, prev) == []


def test_fpo_new_courses_amb_snapshot_anterior_buit_no_en_dona_cap():
    curr = [_soc('1', '2026-12-01'), _ext('PIMEC:a:1', '2026-12-01')]
    assert pipeline.fpo_new_courses([], curr) == []
    # una font sense snapshot anterior tampoc, encara que les altres en tinguin
    assert pipeline.fpo_new_courses([_soc('0', '2026-12-01')], curr + [_soc('2', '2026-12-02')]) == \
        [_soc('1', '2026-12-01'), _soc('2', '2026-12-02')]


def _write(tmp_path, soc, ext):
    (tmp_path / 'soc_cursos.json').write_text(json.dumps(soc), encoding='utf-8')
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(ext), encoding='utf-8')
    (tmp_path / 'soc_especs.json').write_text(json.dumps(
        [{'codi': 'ADGG0408', 'familia': {'codi': 'ADG', 'desc': FAMILIES['ADG']}}]), encoding='utf-8')


def test_notify_avisa_dels_cursos_apareguts_des_del_snapshot(conn, tmp_path, _no_real_email):
    _alert(conn, _user(conn, 'a@example.com'), familia='ADG')
    _write(tmp_path, [_soc('1', '2026-12-01')], [])
    before = pipeline.fpo_snapshot(str(tmp_path))
    _write(tmp_path, [_soc('1', '2026-12-01'), _soc('2', '2026-12-02')], [])
    assert pipeline.notify_fpo_new_courses(str(tmp_path), before) == 1
    body = _no_real_email.call_args[0][2]
    assert 'Curs 2' in body and 'Curs 1\n' not in body
    assert 'ADG - Administració' in body


def test_notify_no_envia_res_si_el_refresc_ha_fallat_o_el_snapshot_anterior_era_buit(conn, tmp_path, _no_real_email):
    _alert(conn, _user(conn, 'a@example.com'), familia='ADG')
    # refresc fallat: els fitxers queden com estaven
    _write(tmp_path, [_soc('1', '2026-12-01')], [])
    before = pipeline.fpo_snapshot(str(tmp_path))
    assert pipeline.notify_fpo_new_courses(str(tmp_path), before) == 0
    # snapshot anterior buit: primer refresc o fitxer perdut
    assert pipeline.notify_fpo_new_courses(str(tmp_path), []) == 0
    # fitxers il·legibles: tampoc peta
    (tmp_path / 'soc_cursos.json').write_text('{no json', encoding='utf-8')
    assert pipeline.notify_fpo_new_courses(str(tmp_path), before) == 0
    _no_real_email.assert_not_called()


def test_una_alerta_nova_no_rep_els_cursos_que_ja_existien(conn, tmp_path, _no_real_email):
    _write(tmp_path, [_soc('1', '2026-12-01')], [])
    before = pipeline.fpo_snapshot(str(tmp_path))
    _alert(conn, _user(conn, 'a@example.com'), familia='ADG')      # creada amb el curs 1 ja publicat
    assert pipeline.notify_fpo_new_courses(str(tmp_path), before) == 0
    _no_real_email.assert_not_called()
