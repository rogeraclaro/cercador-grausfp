"""Alertes i seguiments: tokens de baixa aïllats per usuari i límit d'actius a tots els camins."""
import json
import os
from unittest.mock import patch

import pytest

os.environ.setdefault("ADMIN_TOKEN", "test-token")

from app import app as flask_app  # noqa: E402
import centres_watch_service  # noqa: E402
import db  # noqa: E402

flask_app.config["TESTING"] = True
flask_app.config["DEBUG"] = True


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    test_db = str(tmp_path / "test.db")
    original = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = test_db
    db.init_db(db_path=test_db)
    yield
    if original is None:
        os.environ.pop("DB_PATH", None)
    else:
        os.environ["DB_PATH"] = original


def _client_for(email):
    c = flask_app.test_client()
    with patch("email_service.send_verification_email"):
        c.post("/api/auth/register", data=json.dumps({"email": email, "password": "password123"}),
               content_type="application/json")
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    assert c.post("/api/auth/login", data=json.dumps({"email": email, "password": "password123"}),
                  content_type="application/json").status_code == 200
    return c


def _user_id(email):
    conn = db.get_db()
    uid = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()[0]
    conn.close()
    return uid


def _new_alert(c, i=0):
    return c.post("/api/alerts", data=json.dumps({"filter_json": {"texto": f"x{i}"}}),
                  content_type="application/json")


def _new_watch(c, i=0):
    return c.post("/api/centres-watch", data=json.dumps({"oferta_key": f"K{i}", "oferta_denom": "D"}),
                  content_type="application/json")


def _count_tokens(user_id, type_):
    conn = db.get_db()
    n = conn.execute("SELECT COUNT(*) FROM tokens WHERE user_id = ? AND type = ?", (user_id, type_)).fetchone()[0]
    conn.close()
    return n


def _insert_inactive(table, user_id, n):
    conn = db.get_db()
    for i in range(n):
        if table == "alerts":
            conn.execute("INSERT INTO alerts (user_id, filter_json, active) VALUES (?, '{}', 0)", (user_id,))
        else:
            conn.execute("INSERT INTO centres_watch (user_id, oferta_key, oferta_denom, active) "
                         "VALUES (?, ?, 'D', 0)", (user_id, f"filler{i}"))
    conn.commit()
    conn.close()


def test_esborrar_alerta_1_no_toca_el_token_de_l_alerta_10_d_un_altre():
    attacker = _client_for("a@test.com")
    victim = _client_for("v@test.com")
    assert _new_alert(attacker).get_json()["id"] == 1
    _insert_inactive("alerts", _user_id("a@test.com"), 8)          # ids 2-9
    assert _new_alert(victim).get_json()["id"] == 10
    before = _count_tokens(_user_id("v@test.com"), "alert_unsubscribe")
    assert attacker.delete("/api/alerts/1").status_code == 204
    assert before == 1
    assert _count_tokens(_user_id("v@test.com"), "alert_unsubscribe") == 1


def test_esborrar_seguiment_1_no_toca_el_token_del_seguiment_10_d_un_altre():
    attacker = _client_for("a@test.com")
    victim = _client_for("v@test.com")
    assert _new_watch(attacker).get_json()["id"] == 1
    _insert_inactive("centres_watch", _user_id("a@test.com"), 8)   # ids 2-9
    assert _new_watch(victim, 1).get_json()["id"] == 10
    conn = db.get_db()
    centres_watch_service._get_or_create_unsubscribe_token(conn, 10, _user_id("v@test.com"))
    conn.commit()
    conn.close()
    assert attacker.delete("/api/centres-watch/1").status_code == 204
    assert _count_tokens(_user_id("v@test.com"), "centres_watch_unsubscribe") == 1


@pytest.mark.parametrize("kind", ["alerts", "centres-watch"])
def test_reactivar_no_supera_el_maxim_d_actius(kind):
    c = _client_for("u@test.com")
    table = "alerts" if kind == "alerts" else "centres_watch"
    make = _new_alert if kind == "alerts" else _new_watch
    ids = [make(c, i).get_json()["id"] for i in range(10)]
    _insert_inactive(table, _user_id("u@test.com"), 1)
    conn = db.get_db()
    inactive_id = conn.execute(f"SELECT id FROM {table} WHERE active = 0").fetchone()[0]
    conn.close()
    rv = c.patch(f"/api/{kind}/{inactive_id}", data=json.dumps({"active": True}),
                 content_type="application/json")
    assert rv.status_code == 429
    # desactivar-ne una i reactivar la inactiva sí que val
    c.patch(f"/api/{kind}/{ids[0]}", data=json.dumps({"active": False}), content_type="application/json")
    rv = c.patch(f"/api/{kind}/{inactive_id}", data=json.dumps({"active": True}),
                 content_type="application/json")
    assert rv.status_code == 200
    # reactivar una que ja és activa no compta dues vegades
    rv = c.patch(f"/api/{kind}/{inactive_id}", data=json.dumps({"active": True}),
                 content_type="application/json")
    assert rv.status_code == 200
