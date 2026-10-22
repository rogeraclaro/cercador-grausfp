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


def _login_via_proxy(client, real_ip, email="user@test.com", password="password123"):
    """Simula nginx: la connexió ve de loopback i la IP real arriba a X-Real-IP."""
    return client.post(
        "/api/auth/login",
        data=json.dumps({"email": email, "password": password}),
        content_type="application/json",
        headers={"X-Real-IP": real_ip},
        environ_base={"REMOTE_ADDR": "127.0.0.1"},
    )


def test_rate_limit_login_per_client_darrere_proxy(client):
    """Els intents fallits d'un client no bloquegen el login d'un altre client."""
    _register(client)
    _verify_user()
    for _ in range(5):
        _login_via_proxy(client, "203.0.113.66", password="malpassword")
    assert _login_via_proxy(client, "203.0.113.66").status_code == 429
    assert _login_via_proxy(client, "198.51.100.7").status_code == 200


def test_rate_limit_login_ignora_x_real_ip_si_no_ve_del_proxy(client):
    """Un client directe no pot esquivar el límit canviant X-Real-IP."""
    _register(client)
    _verify_user()
    for i in range(5):
        client.post(
            "/api/auth/login",
            data=json.dumps({"email": "user@test.com", "password": "malpassword"}),
            content_type="application/json",
            headers={"X-Real-IP": f"10.0.0.{i}"},
            environ_base={"REMOTE_ADDR": "192.0.2.10"},
        )
    rv = client.post(
        "/api/auth/login",
        data=json.dumps({"email": "user@test.com", "password": "password123"}),
        content_type="application/json",
        headers={"X-Real-IP": "10.0.0.99"},
        environ_base={"REMOTE_ADDR": "192.0.2.10"},
    )
    assert rv.status_code == 429


# ---------------------------------------------------------------------------
# Límits d'enviament d'emails (forgot-password / register)
# ---------------------------------------------------------------------------

def _forgot(client, email="user@test.com", real_ip=None):
    kwargs = {}
    if real_ip:
        kwargs = {"headers": {"X-Real-IP": real_ip}, "environ_base": {"REMOTE_ADDR": "127.0.0.1"}}
    return client.post(
        "/api/auth/forgot-password",
        data=json.dumps({"email": email}),
        content_type="application/json",
        **kwargs,
    )


def test_forgot_password_un_sol_email_per_compte_cada_15_minuts(client):
    _register(client)
    _verify_user()
    with patch("email_service.send_password_reset_email") as send:
        first = _forgot(client, real_ip="203.0.113.1")
        second = _forgot(client, real_ip="203.0.113.2")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.get_json() == first.get_json()
    assert send.call_count == 1


def test_forgot_password_limit_per_ip(client):
    with patch("email_service.send_password_reset_email"):
        codes = [_forgot(client, email=f"nobody{i}@test.com", real_ip="203.0.113.9").status_code
                 for i in range(21)]
    assert codes[:20] == [200] * 20
    assert codes[20] == 429
    with patch("email_service.send_password_reset_email"):
        assert _forgot(client, email="altre@test.com", real_ip="198.51.100.1").status_code == 200


def test_register_limit_per_ip(client):
    def reg(i, ip):
        with patch("email_service.send_verification_email") as send:
            rv = client.post(
                "/api/auth/register",
                data=json.dumps({"email": f"u{i}@test.com", "password": "password123"}),
                content_type="application/json",
                headers={"X-Real-IP": ip},
                environ_base={"REMOTE_ADDR": "127.0.0.1"},
            )
        return rv.status_code, send.call_count
    results = [reg(i, "203.0.113.20") for i in range(21)]
    assert all(r == (201, 1) for r in results[:20])
    assert results[20] == (429, 0)
    assert reg(99, "198.51.100.2") == (201, 1)


# ---------------------------------------------------------------------------
# Google OAuth: vinculació per email
# ---------------------------------------------------------------------------

def _google_callback(client, monkeypatch, userinfo):
    """Completa el callback amb Google mockejat; retorna la resposta."""
    from unittest.mock import MagicMock
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    token_resp = MagicMock(ok=True)
    token_resp.json.return_value = {"access_token": "at"}
    info_resp = MagicMock(ok=True)
    info_resp.json.return_value = userinfo
    client.set_cookie("oauth_state", "st")
    with patch("app.requests.post", return_value=token_resp), \
         patch("app.requests.get", return_value=info_resp):
        return client.get("/api/auth/google/callback?state=st&code=c")


def _google_id(email):
    conn = db.get_db()
    row = conn.execute("SELECT google_id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row[0] if row else None


def test_google_sobre_compte_no_verificat_invalida_la_contrasenya_previa(client, monkeypatch):
    """Pre-hijack: qui registra l'email d'un altre no pot entrar després que el titular usi Google."""
    _register(client, email="victim@test.com", password="attackerpass1")
    rv = _google_callback(client, monkeypatch,
                          {"sub": "g-victim", "email": "victim@test.com", "email_verified": True})
    assert rv.status_code == 302 and "google=1" in rv.headers["Location"]
    assert _google_id("victim@test.com") == "g-victim"
    with flask_app.test_client() as attacker:
        assert _login(attacker, email="victim@test.com", password="attackerpass1").status_code == 401


def test_google_sobre_compte_verificat_conserva_la_contrasenya(client, monkeypatch):
    _register(client, email="owner@test.com", password="ownerpass99")
    _verify_user("owner@test.com")
    rv = _google_callback(client, monkeypatch,
                          {"sub": "g-owner", "email": "owner@test.com", "email_verified": True})
    assert "google=1" in rv.headers["Location"]
    with flask_app.test_client() as other:
        assert _login(other, email="owner@test.com", password="ownerpass99").status_code == 200


@pytest.mark.parametrize("claim", [{"email_verified": False}, {}])
def test_google_sense_email_verificat_no_vincula_ni_inicia_sessio(client, monkeypatch, claim):
    _register(client, email="owner@test.com", password="ownerpass99")
    _verify_user("owner@test.com")
    rv = _google_callback(client, monkeypatch, {"sub": "g-x", "email": "owner@test.com", **claim})
    assert "google_error=" in rv.headers["Location"]
    assert _google_id("owner@test.com") is None
    assert "session=" not in rv.headers.get("Set-Cookie", "")
