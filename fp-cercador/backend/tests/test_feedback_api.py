"""
test_feedback_api.py — Comentaris d'usuaris (Pla 069): taula, POST /api/feedback i admin.

BD migrada temporal per test + sessió d'usuari real (patró test_fpo_favorites_api.py).
"""
import json
import os

import pytest

os.environ.setdefault("ADMIN_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("BASE_URL", "http://localhost")

from app import app as flask_app  # noqa: E402
import app as app_module  # noqa: E402
import db  # noqa: E402

flask_app.config["TESTING"] = True
flask_app.config["DEBUG"] = True


@pytest.fixture(autouse=True)
def feedback_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", test_db)
    db.init_db(db_path=test_db)
    monkeypatch.delenv("FEEDBACK_NOTIFY_EMAIL", raising=False)
    # Límit per IP en memòria: cada test comença net.
    monkeypatch.setattr(app_module, "_feedback_hits", {})
    # L'avís per email s'envia en un fil; als tests, de manera síncrona.
    monkeypatch.setattr(app_module, "_run_in_background", lambda fn: fn())
    yield tmp_path


@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c


def _register_and_login(client, email, *, admin=False):
    from unittest.mock import patch
    with patch("email_service.send_verification_email"):
        client.post("/api/auth/register",
                    data=json.dumps({"email": email, "password": "password123"}),
                    content_type="application/json")
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1, is_admin = ? WHERE email = ?",
                 (1 if admin else 0, email))
    conn.commit()
    conn.close()
    client.post("/api/auth/login",
                data=json.dumps({"email": email, "password": "password123"}),
                content_type="application/json")
    return client


@pytest.fixture
def auth_client(client):
    return _register_and_login(client, "u@test.com")


def _rows():
    conn = db.get_db()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM feedback ORDER BY id")]
    finally:
        conn.close()


# --- Fase 1: migració 011 ----------------------------------------------------

def test_taula_feedback_te_les_columnes_i_estat_per_defecte():
    conn = db.get_db()
    try:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(feedback)")}
        assert cols == {"id", "user_id", "email", "kind", "message", "context",
                        "status", "admin_note", "created_at", "updated_at"}
        conn.execute("INSERT INTO feedback (email, kind, message) VALUES ('a@b.cat', 'idea', 'Hola')")
        row = conn.execute("SELECT status, created_at, updated_at FROM feedback").fetchone()
        assert row["status"] == "new"
        assert row["created_at"] and row["updated_at"]
        assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 11
    finally:
        conn.close()


def test_esborrar_usuari_esborra_els_seus_comentaris_pero_no_els_anonims():
    conn = db.get_db()
    try:
        conn.execute("INSERT INTO users (email, password_hash) VALUES ('x@y.cat', 'h')")
        uid = conn.execute("SELECT id FROM users WHERE email = 'x@y.cat'").fetchone()[0]
        conn.execute("INSERT INTO feedback (user_id, email, kind, message) VALUES (?, 'x@y.cat', 'idea', 'a')", (uid,))
        conn.execute("INSERT INTO feedback (email, kind, message) VALUES ('anon@y.cat', 'idea', 'b')")
        conn.commit()
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))
        conn.commit()
        emails = [r[0] for r in conn.execute("SELECT email FROM feedback")]
        assert emails == ["anon@y.cat"]
    finally:
        conn.close()


# --- Fase 2: POST /api/feedback ------------------------------------------------

def _post(client, body, **kw):
    return client.post("/api/feedback", data=json.dumps(body),
                       content_type="application/json", **kw)


VALID = {"kind": "idea", "message": "  Afegiu filtres per província  ",
         "context": {"path": "/index.html", "query": "?q=sanitat", "lang": "ca"}}


def test_anonim_sense_email_400(client):
    r = _post(client, VALID)
    assert r.status_code == 400
    assert "email" in r.get_json()["error"].lower()
    assert _rows() == []


def test_anonim_email_invalid_400(client):
    r = _post(client, {**VALID, "email": "no-es-un-email"})
    assert r.status_code == 400
    assert _rows() == []


def test_anonim_amb_email_desa(client):
    r = _post(client, {**VALID, "email": " Anna@Exemple.cat "})
    assert r.status_code == 201
    assert isinstance(r.get_json()["id"], int)
    [row] = _rows()
    assert row["user_id"] is None
    assert row["email"] == "anna@exemple.cat"
    assert row["kind"] == "idea"
    assert row["message"] == "Afegiu filtres per província"
    assert row["status"] == "new"
    assert json.loads(row["context"]) == VALID["context"]


def test_amb_sessio_fa_servir_lemail_del_compte(auth_client):
    r = _post(auth_client, {**VALID, "email": "altre@fals.cat"})
    assert r.status_code == 201
    [row] = _rows()
    assert row["email"] == "u@test.com"
    conn = db.get_db()
    uid = conn.execute("SELECT id FROM users WHERE email = 'u@test.com'").fetchone()[0]
    conn.close()
    assert row["user_id"] == uid


def test_amb_sessio_sense_email_desa(auth_client):
    assert _post(auth_client, VALID).status_code == 201


@pytest.mark.parametrize("body", [
    {**VALID, "kind": "scoring"},
    {**VALID, "kind": None},
    {**VALID, "message": "   "},
    {**VALID, "message": "x" * 2001},
    {**VALID, "message": 42},
])
def test_entrada_invalida_400(client, body):
    r = _post(client, {**body, "email": "a@b.cat"})
    assert r.status_code == 400
    assert _rows() == []


def test_missatge_de_2000_caracters_passa(client):
    assert _post(client, {**VALID, "message": "x" * 2000, "email": "a@b.cat"}).status_code == 201


def test_honeypot_ple_respon_ok_pero_no_desa(client, monkeypatch):
    sent = []
    monkeypatch.setenv("FEEDBACK_NOTIFY_EMAIL", "owner@test.cat")
    monkeypatch.setattr("email_service.send_email", lambda *a: sent.append(a))
    r = _post(client, {**VALID, "email": "a@b.cat", "website": "http://spam.example"})
    assert r.status_code == 201
    assert _rows() == []
    assert sent == []


def test_limit_de_5_anonims_per_hora_i_ip(client):
    body = {**VALID, "email": "a@b.cat"}
    for _ in range(5):
        assert _post(client, body).status_code == 201
    assert _post(client, body).status_code == 429
    assert len(_rows()) == 5
    other = _post(client, body, environ_base={"REMOTE_ADDR": "10.0.0.9"})
    assert other.status_code == 201


def test_limit_caduca_al_cap_duna_hora(client, monkeypatch):
    body = {**VALID, "email": "a@b.cat"}
    now = [1_000_000.0]
    monkeypatch.setattr(app_module, "_feedback_now", lambda: now[0])
    for _ in range(5):
        _post(client, body)
    assert _post(client, body).status_code == 429
    now[0] += 3601
    assert _post(client, body).status_code == 201


def test_ip_real_de_nginx_nomes_des_de_loopback(client):
    body = {**VALID, "email": "a@b.cat"}
    via_nginx = {"REMOTE_ADDR": "127.0.0.1"}
    for _ in range(5):
        _post(client, body, environ_base=via_nginx, headers={"X-Real-IP": "203.0.113.1"})
    assert _post(client, body, environ_base=via_nginx,
                 headers={"X-Real-IP": "203.0.113.1"}).status_code == 429
    # Un altre client real darrere del mateix nginx no queda bloquejat.
    assert _post(client, body, environ_base=via_nginx,
                 headers={"X-Real-IP": "203.0.113.2"}).status_code == 201
    # Des de fora de loopback la capçalera no es creu: no permet esquivar el límit.
    direct = {"REMOTE_ADDR": "198.51.100.7"}
    for i in range(5):
        _post(client, body, environ_base=direct, headers={"X-Real-IP": f"10.1.1.{i}"})
    assert _post(client, body, environ_base=direct,
                 headers={"X-Real-IP": "10.1.1.99"}).status_code == 429


def test_amb_sessio_no_hi_ha_limit_anonim(auth_client):
    for _ in range(6):
        assert _post(auth_client, VALID).status_code == 201


def test_context_nomes_claus_conegudes_i_tallat(client):
    ctx = {"path": "/p" + "a" * 600, "query": 5, "lang": "es", "cv": "secret", "x": {"y": 1}}
    _post(client, {**VALID, "context": ctx, "email": "a@b.cat"})
    stored = json.loads(_rows()[0]["context"])
    assert stored == {"path": ("/p" + "a" * 600)[:500], "lang": "es"}


def test_context_que_no_es_objecte_es_desa_buit(client):
    _post(client, {**VALID, "context": "brossa", "email": "a@b.cat"})
    assert json.loads(_rows()[0]["context"]) == {}


def test_avis_al_propietari_si_hi_ha_feedback_notify_email(client, monkeypatch):
    sent = []
    monkeypatch.setenv("FEEDBACK_NOTIFY_EMAIL", "owner@test.cat")
    monkeypatch.setattr("email_service.send_email", lambda *a: sent.append(a))
    _post(client, {**VALID, "email": "a@b.cat"})
    [(to, subject, body)] = sent
    assert to == "owner@test.cat"
    assert "a@b.cat" in body and "Afegiu filtres per província" in body
    assert "/index.html" in body


def test_sense_feedback_notify_email_no_senvia_res(client, monkeypatch):
    sent = []
    monkeypatch.setattr("email_service.send_email", lambda *a: sent.append(a))
    _post(client, {**VALID, "email": "a@b.cat"})
    assert sent == []


def test_error_de_lemail_no_fa_fallar_la_peticio(client, monkeypatch):
    def boom(*a):
        raise OSError("SMTP caigut")
    monkeypatch.setenv("FEEDBACK_NOTIFY_EMAIL", "owner@test.cat")
    monkeypatch.setattr("email_service.send_email", boom)
    assert _post(client, {**VALID, "email": "a@b.cat"}).status_code == 201
    assert len(_rows()) == 1


def test_preflight_cors_amb_credencials(client):
    r = client.options("/api/feedback", headers={
        "Origin": "http://localhost:8080",
        "Access-Control-Request-Method": "POST",
    })
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost:8080"
    assert r.headers.get("Access-Control-Allow-Credentials") == "true"
