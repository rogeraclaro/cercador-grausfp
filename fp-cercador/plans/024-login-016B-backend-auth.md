# Plan 024 — Login F1-B: Backend auth (endpoints + email)

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada
> comanda de verificació i confirma el resultat esperat abans de passar al
> pas següent. Si es dona qualsevol condició de la secció "STOP conditions",
> atura't i informa — no improvisis. En acabar, actualitza la fila d'aquest
> pla a `plans/README.md`.
>
> **Context previ**: Llegeix `plans/outputs/spike-login.md` (Step 1 i Step 3–5)
> i el pla 023 (ja DONE) ABANS de començar. L'esquema de BD és a
> `backend/migrations/001_initial_schema.sql`; la capa de connexió és a
> `backend/db.py`. No repeteixis la investigació.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> ```bash
> python3 -c "import backend.db as db; conn = db.init_db(db_path=':memory:'); print('db OK')"
> ls backend/email_service.py 2>/dev/null && echo "email_service JA EXISTEIX" || echo "email_service no existeix (esperat)"
> grep -n "api/auth" backend/app.py | head && echo "---" || echo "cap ruta /api/auth a app.py (esperat)"
> ```
> Si `email_service.py` ja existeix o app.py ja té rutes `/api/auth`, atura't.

## Status

- **Priority**: P2
- **Effort**: M (6–10h)
- **Risk**: MEDIUM (primer codi nou a app.py; cal no trencar els endpoints existents)
- **Depends on**: 023 (DONE)
- **Category**: feature (F1)
- **Planned at**: 2026-06-15

## Why this matters

Sense aquest pla no hi ha res amb què interactuar: la BD existeix però no
hi ha cap manera de registrar-se, entrar ni sortir. Aquest pla tanca el
primer increment demostrable: un usuari pot crear compte, verificar l'email,
fer login, consultar qui és i sortir — tot sense cap feature gated encara.

## Current state (fets verificats)

- `backend/db.py` — `get_db()`, `init_db()`, `query_one/all()` disponibles
- `backend/migrations/001_initial_schema.sql` — 8 taules; `fp_cercador.db` creat
- `backend/app.py` — Flask sense rutes `/api/auth/*`; auth existent via `ADMIN_TOKEN` Bearer
- `werkzeug.security` disponible (Flask la porta); `smtplib` és stdlib
- Brevo SMTP: `smtp-relay.brevo.com:587`; remitent: `roger@masellas.info`
- Sessió: cookie HttpOnly + Secure (en prod) + SameSite=Lax; caducitat 30 dies
- GDPR: avís mínim + checkbox des del primer dia (implementar al pla 025, frontend)

## Scope

**In scope**:
- `backend/email_service.py` — mòdul d'enviament via Brevo SMTP (smtplib)
- `backend/app.py` — 7 nous endpoints `/api/auth/*` + helper `_get_session_user()`
- `backend/.env.example` — noves variables SMTP + SECRET_KEY
- `backend/tests/test_auth.py` — tests unitaris amb mock d'email i BD en memòria

**Out of scope**: cap canvi al frontend, als endpoints existents d'ofertes/admin,
ni a `db.py` o a les migracions.

## Steps

### Step 1 — `backend/email_service.py`

Mòdul lleuger (~60 línies) per enviar emails via Brevo SMTP:

```python
"""email_service.py — Enviament d'emails transaccionals via Brevo SMTP."""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.environ.get("BREVO_SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.environ.get("BREVO_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("BREVO_SMTP_USER", "")
SMTP_KEY  = os.environ.get("BREVO_SMTP_KEY", "")
FROM_EMAIL = os.environ.get("EMAIL_FROM", "noreply@masellas.info")
FROM_NAME  = os.environ.get("EMAIL_FROM_NAME", "Cercador FP España")

def send_email(to: str, subject: str, body: str) -> None:
    """Envia un email de text pla. Llença excepció si falla."""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.ehlo()
        s.starttls()
        s.login(SMTP_USER, SMTP_KEY)
        s.sendmail(FROM_EMAIL, [to], msg.as_bytes())
```

Tres funcions d'alt nivell (plantilles en text pla):

```python
def send_verification_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/api/auth/verify?token={token}"
    send_email(to, "Verifica el teu compte — Cercador FP",
               f"Hola,\n\nClica aquest enllaç per verificar el teu compte:\n{link}\n\n"
               "L'enllaç caduca en 24 hores.\n\nCercador FP España")

def send_password_reset_email(to: str, token: str, base_url: str) -> None:
    link = f"{base_url}/reset-password.html?token={token}"
    send_email(to, "Restableix la teva contrasenya — Cercador FP",
               f"Hola,\n\nHas sol·licitat restablir la contrasenya:\n{link}\n\n"
               "L'enllaç caduca en 1 hora. Si no has fet cap sol·licitud, ignora aquest email.\n\n"
               "Cercador FP España")
```

**Verificació**:
```bash
python3 -c "import backend.email_service as e; print('email_service OK')"
```

### Step 2 — Variables d'entorn

Afegir a `backend/.env.example` (després de les variables Brevo existents):

```
# Brevo SMTP — autenticació d'usuaris (verificació email, reset contrasenya)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=roger@masellas.info
BREVO_SMTP_KEY=

# Email remitent
EMAIL_FROM=noreply@masellas.info
EMAIL_FROM_NAME=Cercador FP España

# URL base per als links dels emails (sense trailing slash)
BASE_URL=https://domini.com

# Clau secreta per a cookies de sessió (genera amb: python3 -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=canvia-aquest-valor-per-un-de-segur
```

Afegir a `backend/app.py` (al bloc d'inicialització, just sota `ADMIN_TOKEN`):
```python
SECRET_KEY = os.environ.get("SECRET_KEY", "")
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001")
```

### Step 3 — Helper `_get_session_user(req)` a `app.py`

Afegir just sota el helper `_check_auth` existent:

```python
def _get_session_user(req):
    """Retorna el user_id de la sessió activa, o None si no hi ha sessió vàlida."""
    import db as _db
    token = req.cookies.get("session")
    if not token:
        return None
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM sessions WHERE token = ? AND expires_at > datetime('now')",
            (token,),
        )
        return row["user_id"] if row else None
    finally:
        conn.close()
```

### Step 4 — 7 endpoints `/api/auth/*` a `app.py`

Afegir al final de `app.py`, abans del bloc `if __name__ == "__main__"` (si existeix):

#### 4a. POST `/api/auth/register`

```python
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    import secrets as _secrets
    import db as _db
    from werkzeug.security import generate_password_hash
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or "@" not in email or len(password) < 8:
        return jsonify({"error": "Email o contrasenya invàlids"}), 400
    conn = _db.get_db()
    try:
        existing = _db.query_one(conn, "SELECT id FROM users WHERE email = ?", (email,))
        if existing:
            return jsonify({"error": "Aquest email ja està registrat"}), 409
        pw_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)", (email, pw_hash)
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        token = _secrets.token_hex(32)
        from datetime import datetime, timezone, timedelta
        expires = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'email_verify', ?)",
            (user_id, token, expires),
        )
        conn.commit()
    finally:
        conn.close()
    try:
        import email_service
        email_service.send_verification_email(email, token, BASE_URL)
    except Exception as exc:
        logger.error("Error enviant email de verificació: %s", exc)
    return jsonify({"message": "Compte creat. Revisa el teu email per verificar-lo."}), 201
```

#### 4b. GET `/api/auth/verify`

```python
@app.route("/api/auth/verify", methods=["GET"])
def auth_verify():
    import db as _db
    token = request.args.get("token", "")
    if not token:
        return jsonify({"error": "Token invàlid"}), 400
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM tokens WHERE token = ? AND type = 'email_verify' AND expires_at > datetime('now')",
            (token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 400
        conn.execute("UPDATE users SET verified = 1 WHERE id = ?", (row["user_id"],))
        conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
    return redirect("/?verified=1")
```

#### 4c. POST `/api/auth/login`

```python
@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    import secrets as _secrets
    import db as _db
    from werkzeug.security import check_password_hash
    from datetime import datetime, timezone, timedelta
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    ip = request.remote_addr or ""
    conn = _db.get_db()
    try:
        # Rate limit: màx 5 intents fallits en 15 min per IP
        attempts = _db.query_one(
            conn,
            "SELECT COUNT(*) FROM login_attempts WHERE ip = ? AND success = 0 AND attempted_at > datetime('now', '-15 minutes')",
            (ip,),
        )[0]
        if attempts >= 5:
            return jsonify({"error": "Massa intents. Espera 15 minuts."}), 429
        user = _db.query_one(
            conn,
            "SELECT id, password_hash, verified FROM users WHERE email = ? AND deleted_at IS NULL",
            (email,),
        )
        ok = bool(user and check_password_hash(user["password_hash"], password))
        conn.execute(
            "INSERT INTO login_attempts (ip, email, success) VALUES (?, ?, ?)",
            (ip, email, 1 if ok else 0),
        )
        conn.commit()
        if not ok:
            return jsonify({"error": "Email o contrasenya incorrectes"}), 401
        if not user["verified"]:
            return jsonify({"error": "Compte no verificat. Revisa el teu email."}), 403
        session_token = _secrets.token_hex(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?)",
            (user["id"], session_token, expires, ip, request.headers.get("User-Agent", "")),
        )
        conn.commit()
    finally:
        conn.close()
    resp = jsonify({"user": {"id": user["id"], "email": email}})
    secure = not app.debug
    resp.set_cookie(
        "session", session_token,
        httponly=True, secure=secure, samesite="Lax",
        max_age=30 * 24 * 3600,
    )
    return resp
```

#### 4d. POST `/api/auth/logout`

```python
@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    import db as _db
    token = request.cookies.get("session")
    if token:
        conn = _db.get_db()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()
    resp = jsonify({"message": "Sessió tancada"})
    resp.set_cookie("session", "", max_age=0)
    return resp
```

#### 4e. GET `/api/auth/me`

```python
@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        user = _db.query_one(
            conn,
            "SELECT id, email FROM users WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        )
    finally:
        conn.close()
    if not user:
        return jsonify({"error": "Usuari no trobat"}), 404
    return jsonify({"id": user["id"], "email": user["email"]})
```

#### 4f. POST `/api/auth/forgot-password`

```python
@app.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    import secrets as _secrets
    import db as _db
    from datetime import datetime, timezone, timedelta
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    # Sempre retornem 200 per no enumerar emails
    if not email:
        return jsonify({"message": "Si l'email existeix, rebràs un missatge."}), 200
    conn = _db.get_db()
    try:
        user = _db.query_one(
            conn, "SELECT id FROM users WHERE email = ? AND deleted_at IS NULL", (email,)
        )
        if user:
            token = _secrets.token_hex(32)
            expires = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'password_reset', ?)",
                (user["id"], token, expires),
            )
            conn.commit()
            try:
                import email_service
                email_service.send_password_reset_email(email, token, BASE_URL)
            except Exception as exc:
                logger.error("Error enviant email de reset: %s", exc)
    finally:
        conn.close()
    return jsonify({"message": "Si l'email existeix, rebràs un missatge."}), 200
```

#### 4g. POST `/api/auth/reset-password`

```python
@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    import db as _db
    from werkzeug.security import generate_password_hash
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_password = data.get("password") or ""
    if not token or len(new_password) < 8:
        return jsonify({"error": "Token o contrasenya invàlids"}), 400
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM tokens WHERE token = ? AND type = 'password_reset' AND expires_at > datetime('now')",
            (token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 400
        pw_hash = generate_password_hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, row["user_id"])
        )
        conn.execute("DELETE FROM tokens WHERE token = ?", (token,))
        conn.commit()
    finally:
        conn.close()
    return jsonify({"message": "Contrasenya actualitzada correctament."})
```

**Verificació global dels endpoints** (amb el servidor aturat):
```bash
cd backend && python3 -c "
from app import app
assert any(r.rule.startswith('/api/auth/') for r in app.url_map.iter_rules()), 'cap ruta auth!'
rules = [r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/api/auth/')]
print('Rutes auth:', sorted(rules))
assert len(rules) == 7
print('OK')
"
```

### Step 5 — `backend/tests/test_auth.py`

Tests amb BD en memòria i email mockejat. No fan cap petició SMTP real.

Estructura de tests a implementar:

```python
"""Tests dels endpoints /api/auth/* — BD en memòria, email mockejat."""
import pytest, json
from unittest.mock import patch, MagicMock

# Configuració mínima per al test (ABANS d'importar app)
import os
os.environ.setdefault("ADMIN_TOKEN", "test-token")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("BASE_URL", "http://localhost")
os.environ.setdefault("DB_PATH", ":memory:")  # BD en memòria per a tots els tests

from app import app as flask_app
import db

@pytest.fixture
def client(tmp_path):
    """Client de test amb BD en memòria i cookie support."""
    test_db = str(tmp_path / "test.db")
    os.environ["DB_PATH"] = test_db
    db.init_db(db_path=test_db)
    flask_app.config["TESTING"] = True
    flask_app.config["DEBUG"] = True  # Secure=False per a cookies en tests
    with flask_app.test_client() as c:
        yield c

# Tests a implementar (mínim):

def test_register_ok(client):
    """Registre amb dades vàlides → 201."""

def test_register_email_duplicat(client):
    """Segon registre amb el mateix email → 409."""

def test_register_password_curta(client):
    """Password < 8 caràcters → 400."""

def test_login_sense_verificar(client):
    """Login d'un usuari no verificat → 403."""

def test_login_ok(client):
    """Login d'un usuari verificat → 200 + cookie session."""

def test_login_password_incorrecta(client):
    """Login amb password incorrecta → 401."""

def test_me_sense_sessio(client):
    """GET /api/auth/me sense cookie → 401."""

def test_me_amb_sessio(client):
    """GET /api/auth/me amb sessió vàlida → 200 + email."""

def test_logout_esborra_sessio(client):
    """POST /api/auth/logout esborra la cookie i la sessió de la BD."""

def test_forgot_password_sempre_200(client):
    """POST /api/auth/forgot-password → sempre 200 (evita enumeració)."""

def test_reset_password_token_invalid(client):
    """POST /api/auth/reset-password amb token inexistent → 400."""

def test_rate_limit_login(client):
    """6è intent de login → 429."""
```

Per a cada test que envia email, usar `@patch("email_service.send_email")` o
`@patch("app.email_service.send_verification_email")`.

**Verificació**:
```bash
cd backend && python3 -m pytest tests/test_auth.py -v
# Mínim: tots els tests passen (12+)
```

### Step 6 — Verificació final integrada

```bash
# 1. Tests de BD (no han de trencar-se)
cd backend && python3 -m pytest tests/test_db.py -v

# 2. Tests d'auth (nous)
python3 -m pytest tests/test_auth.py -v

# 3. Tests existents (no regressions)
python3 -m pytest tests/ -v --ignore=tests/test_html_scraper.py -q
# (test_html_scraper fa peticions reals a internet — ignorar en CI local)

# 4. Rutes registrades
python3 -c "
from app import app
auth_routes = sorted(r.rule for r in app.url_map.iter_rules() if '/api/auth/' in r.rule)
print('Auth routes:', auth_routes)
assert len(auth_routes) == 7
"

# 5. Cap fitxer existent modificat fora dels autoritzats
git diff --name-only
# Ha de mostrar NOMÉS: backend/app.py, backend/.env.example
```

## Done criteria

- [ ] `backend/email_service.py` existeix amb `send_email()`, `send_verification_email()`, `send_password_reset_email()`
- [ ] `app.py` té 7 rutes `/api/auth/*` i helper `_get_session_user()`
- [ ] `backend/.env.example` té les noves variables SMTP + SECRET_KEY + BASE_URL
- [ ] Tests d'auth: mínim 12 tests, tots passen, BD sempre en memòria
- [ ] Tests existents (test_db, test_api, test_feed, test_history) passen sense regressions
- [ ] `git diff --name-only` mostra NOMÉS `backend/app.py` i `backend/.env.example` com a modificats
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- Algun endpoint existent (ofertes, admin, historial) deixa de funcionar → no improvisis: atura't i informa
- La importació `import db` dins d'app.py crea importació circular → reestructurar com a importació local (dins de la funció), tal com indica el codi d'exemple d'aquest pla
- Temptació d'afegir lògica de frontend o de gating (comprovar si l'usuari té dret a veure X) → STOP: això és del pla 025
- `DB_PATH=":memory:"` en tests fa que cada request Flask obri una connexió nova (BD buida) → solució: usar `tmp_path` de pytest per crear un fitxer SQLite temporal per als tests d'integració d'app

## Maintenance notes

- `import db` es fa com a importació local dins de cada funció per evitar
  circulars amb els mòduls existents que `app.py` ja importa al nivell de mòdul
- El `SECRET_KEY` no s'usa per a sessions (les sessions van per token a BD, no
  per JWT ni Flask sessions) — és reservat per a futures necessitats de CSRF
- El rate limiting usa `login_attempts` (SQLite): senzill, sense Redis, sense
  memòria compartida entre workers (acceptable amb 1 worker + threads)
- Els emails de verificació/reset funcionen sense domini definitiu — el `BASE_URL`
  del `.env` determina els links; per al betatesting pot ser la IP del VPS
