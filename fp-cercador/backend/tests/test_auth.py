"""Tests dels endpoints /api/auth/* — BD en fitxer temporal, email mockejat."""
import os
import json
import pytest
from unittest.mock import patch

# Establir totes les env vars ABANS de la primera importació d'app
os.environ.setdefault("ADMIN_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("BASE_URL", "http://localhost")

# Importació única de l'app (sense reload, evita reinici del scheduler)
from app import app as flask_app  # noqa: E402
import db  # noqa: E402

flask_app.config["TESTING"] = True
flask_app.config["DEBUG"] = True  # Secure=False per a cookies en tests locals


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    """Crea una BD temporal neta per a cada test i restaura DB_PATH al final."""
    test_db = str(tmp_path / "test.db")
    original = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = test_db
    db.init_db(db_path=test_db)
    yield test_db
    if original is None:
        os.environ.pop("DB_PATH", None)
    else:
        os.environ["DB_PATH"] = original


@pytest.fixture
def client():
    with flask_app.test_client() as c:
        yield c


def _register(client, email="user@test.com", password="password123"):
    with patch("email_service.send_verification_email"):
        return client.post(
            "/api/auth/register",
            data=json.dumps({"email": email, "password": password}),
            content_type="application/json",
        )


def _verify_user(email="user@test.com"):
    """Marca l'usuari com a verificat directament a la BD del test actiu."""
    conn = db.get_db()  # llegeix os.environ["DB_PATH"] — establert per fresh_db
    conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))
    conn.commit()
    conn.close()


def _login(client, email="user@test.com", password="password123"):
    return client.post(
        "/api/auth/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Registre
# ---------------------------------------------------------------------------

def test_register_ok(client):
    rv = _register(client)
    assert rv.status_code == 201
    assert "Compte creat" in rv.get_json()["message"]


def test_register_email_duplicat(client):
    _register(client)
    rv = _register(client)
    assert rv.status_code == 409


def test_register_password_curta(client):
    rv = _register(client, password="abc")
    assert rv.status_code == 400


def test_register_email_invalid(client):
    rv = _register(client, email="noesunemail")
    assert rv.status_code == 400


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_sense_verificar(client):
    _register(client)
    rv = _login(client)
    assert rv.status_code == 403


def test_login_ok(client):
    _register(client)
    _verify_user()
    rv = _login(client)
    assert rv.status_code == 200
    assert rv.get_json()["user"]["email"] == "user@test.com"
    assert "session" in rv.headers.get("Set-Cookie", "")


def test_login_password_incorrecta(client):
    _register(client)
    _verify_user()
    rv = _login(client, password="wrongpassword")
    assert rv.status_code == 401


def test_login_email_inexistent(client):
    rv = _login(client, email="nobody@test.com")
    assert rv.status_code == 401


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------

def test_me_sense_sessio(client):
    rv = client.get("/api/auth/me")
    assert rv.status_code == 401


def test_me_amb_sessio(client):
    _register(client)
    _verify_user()
    _login(client)
    rv = client.get("/api/auth/me")
    assert rv.status_code == 200
    assert rv.get_json()["email"] == "user@test.com"


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout_esborra_sessio(client):
    _register(client)
    _verify_user()
    _login(client)
    rv = client.post("/api/auth/logout")
    assert rv.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------

def test_forgot_password_sempre_200(client):
    with patch("email_service.send_password_reset_email"):
        rv = client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "ningú@test.com"}),
            content_type="application/json",
        )
    assert rv.status_code == 200


def test_reset_password_token_invalid(client):
    rv = client.post(
        "/api/auth/reset-password",
        data=json.dumps({"token": "tokeninexistent", "password": "novapassword123"}),
        content_type="application/json",
    )
    assert rv.status_code == 400


def test_reset_password_ok(client):
    """Flux complet: forgot → reset → login amb nova contrasenya."""
    _register(client)
    _verify_user()

    reset_token = None
    def capture_reset(email, token, base_url):
        nonlocal reset_token
        reset_token = token

    with patch("email_service.send_password_reset_email", side_effect=capture_reset):
        client.post(
            "/api/auth/forgot-password",
            data=json.dumps({"email": "user@test.com"}),
            content_type="application/json",
        )

    assert reset_token is not None
    rv = client.post(
        "/api/auth/reset-password",
        data=json.dumps({"token": reset_token, "password": "novapassword99"}),
        content_type="application/json",
    )
    assert rv.status_code == 200
    assert _login(client, password="novapassword99").status_code == 200


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_login(client):
    _register(client)
    _verify_user()
    for _ in range(5):
        _login(client, password="malpassword")
    rv = _login(client, password="malpassword")
    assert rv.status_code == 429
