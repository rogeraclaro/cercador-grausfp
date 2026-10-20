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
