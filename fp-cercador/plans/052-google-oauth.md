# Pla 052 — Sign in with Google (OAuth 2.0)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> ```bash
> git diff --stat 95de37a..HEAD -- backend/app.py backend/migrations/ frontend/login.html frontend/register.html frontend/i18n.js
> ```
> Si algun d'aquests fitxers ha canviat des que el pla va ser escrit, compara
> els excerpts de "Current state" amb el codi viu. Si no coincideixen, STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: MED
- **Depends on**: plans 023–026 (F1 auth DONE)
- **Category**: direction
- **Planned at**: commit `95de37a`, 2026-06-21

## Why this matters

El registre amb email+contrasenya té fricció (verificació de correu, recordar password). Afegir "Continua amb Google" elimina aquesta barrera: un clic, l'usuari té compte i sessió activa sense cap email de verificació. La feature és purament additiva — no toca la lògica d'auth existent — i s'implementa amb les dependències ja presents (`requests` per al handshake OAuth 2.0 amb Google).

## Current state

### Fitxers rellevants

- `backend/app.py` — tots els endpoints d'auth (`/api/auth/*`) a partir de la línia 1090
- `backend/db.py` — capa de connexió SQLite; `run_migrations()` aplica fitxers `.sql` numerats
- `backend/migrations/001_initial_schema.sql` — taula `users` amb `password_hash TEXT NOT NULL`
- `backend/migrations/005_centres_watch.sql` — última migració existent (versió 5)
- `backend/.env.example` — variables d'entorn (BASE_URL, SECRET_KEY, BREVO_*, ADMIN_TOKEN)
- `frontend/login.html` — formulari login, JS inline, sense framework
- `frontend/register.html` — formulari registre, JS inline
- `frontend/i18n.js` — diccionari CA+ES, ~550 línies

### Excerpt: taula users (migrations/001_initial_schema.sql:3-10)

```sql
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    verified      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at    TEXT
);
```

**Nota crítica**: `password_hash TEXT NOT NULL`. SQLite no permet canviar constraints via ALTER TABLE. Per als usuaris de Google s'usarà el sentinel `'google'` com a valor de `password_hash`. `check_password_hash('google', ...)` sempre retorna False → aquests usuaris no podran fer login per contrasenya (comportament correcte).

### Excerpt: com es crea una sessió (app.py:1212-1229)

```python
session_token = _secrets.token_hex(32)
expires = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
conn.execute(
    "INSERT INTO sessions (user_id, token, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?)",
    (user["id"], session_token, expires, ip, request.headers.get("User-Agent", "")),
)
conn.commit()
resp = jsonify({"user": {"id": uid, "email": email, "is_admin": is_admin}})
secure = not app.debug
resp.set_cookie(
    "session", session_token,
    httponly=True, secure=secure, samesite="Lax",
    max_age=30 * 24 * 3600,
)
```

Cal replicar **exactament** aquest patró al callback de Google.

### Excerpt: variables d'entorn carregades (app.py, primeres línies)

```python
from dotenv import load_dotenv
load_dotenv()
BASE_URL = os.environ.get("BASE_URL", "http://localhost:5001")
```

`BASE_URL` ja existeix i s'usarà per al `redirect_uri` de Google.

### Excerpt: estructura login.html (línies 135-151)

```html
<div class="auth-page">
  <h1 data-i18n="login.h1">Inicia sessió</h1>
  <p id="msg" class="msg" hidden></p>
  <form id="form-login">
    ...
    <button type="submit" id="btn-submit" data-i18n="login.btn.submit">Entra</button>
  </form>
  <p class="auth-links"><a href="forgot-password.html" data-i18n="login.link.forgot">Has oblidat la contrasenya?</a></p>
  <p class="auth-links" data-i18n="login.link.register">Sense compte? <a href="register.html">Registra't</a></p>
</div>
```

### Excerpt: estructura register.html (línies 148-176)

```html
<div class="auth-page">
  <h1 data-i18n="register.h1">Crea un compte</h1>
  <p id="msg" class="msg" hidden></p>
  <form id="form-register">
    ...
    <button type="submit" id="btn-submit" data-i18n="register.btn.submit">Crea el compte</button>
  </form>
  <p class="auth-links" data-i18n="register.link.login">Ja tens compte? <a href="login.html">Inicia sessió</a></p>
</div>
```

### Excerpt: claus i18n nav CA (i18n.js:5-11)

```javascript
      'nav.greeting': 'Hola, {email}',
      'nav.logout': 'Sortir',
      'nav.login': 'Entra',
      'nav.register': "Registra't gratis",
      'nav.lang.ca': 'CA',
      'nav.lang.es': 'ES',
      'nav.admin': 'Admin',
```

## Commands you will need

| Propòsit | Comanda | Esperat |
|----------|---------|---------|
| Backend tests | `cd backend && python -m pytest tests/ -v` | ≥118 passed |
| Verificació drift | veure Drift check a dalt | 0 canvis o excerpts coincideixen |
| Variables .env | `grep GOOGLE backend/.env.example` | 2 línies |

No hi ha typecheck ni build frontend (vanilla JS).

## Configuració prèvia a Google Cloud Console (fer-ho ABANS d'executar el pla)

**Això ho ha de fer el propietari del projecte, no l'executor.**

1. Anar a https://console.cloud.google.com → Crear projecte (o usar-ne un d'existent)
2. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
3. Application type: **Web application**
4. Authorized redirect URIs: `https://TU_DOMINI/api/auth/google/callback` (i `http://localhost:5001/api/auth/google/callback` per a dev si cal)
5. Copiar `Client ID` i `Client Secret`
6. Afegir al `.env` del servidor:
   ```
   GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=xxxx
   ```

**L'executor assumeix que GOOGLE_CLIENT_ID i GOOGLE_CLIENT_SECRET ja estan al .env del servidor quan fa el desplegament.**

## Scope

**En àmbit** (els únics fitxers a modificar o crear):
- `backend/migrations/006_google_oauth.sql` (crear)
- `backend/app.py` (afegir 2 endpoints i llegir 2 env vars)
- `backend/.env.example` (afegir 2 variables)
- `frontend/login.html` (afegir botó Google)
- `frontend/register.html` (afegir botó Google)
- `frontend/i18n.js` (afegir claus `auth.google.*`)

**Fora d'àmbit** (NO tocar):
- `backend/db.py` — la migració s'aplica automàticament via `run_migrations()`
- `backend/tests/test_auth.py` — els tests existents no cal modificar-los
- `backend/migrations/001_initial_schema.sql` — NO modificar mai fitxers de migració existents
- `frontend/auth.js` — el widget de topbar no cal tocar-lo
- Cap altra pàgina frontend

## Git workflow

- Branca: `feat/052-google-oauth`
- Commits: conventional commits, ex: `feat(auth): Google OAuth 2.0 Sign in with Google`
- No fer push ni PR tret que el reviewer ho demani.

---

## Steps

### Pas 1 — Migració 006: afegir columna `google_id` a `users`

Crea el fitxer `backend/migrations/006_google_oauth.sql`:

```sql
-- Migration 006: Google OAuth — afegeix google_id a users

ALTER TABLE users ADD COLUMN google_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;

INSERT OR IGNORE INTO schema_version (version) VALUES (6);
```

**Per què `WHERE google_id IS NOT NULL`**: SQLite permet múltiples NULL en índexs UNIQUE; l'index parcial assegura la unicitat només per a valors no-nuls.

**Verificació**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'backend')
import db
conn = db.init_db()
cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
print('google_id in cols:', 'google_id' in cols)
conn.close()
"
```
Expected: `google_id in cols: True`

---

### Pas 2 — Afegir variables d'entorn a `.env.example`

Al fitxer `backend/.env.example`, afegeix just després de la línia `SECRET_KEY=...`:

```
# Google OAuth 2.0 (Sign in with Google)
# Obtén les credencials a: https://console.cloud.google.com → APIs & Services → Credentials
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

**Verificació**:
```bash
grep "GOOGLE_CLIENT_ID\|GOOGLE_CLIENT_SECRET" backend/.env.example | wc -l
```
Expected: `2`

---

### Pas 3 — Afegir els 2 endpoints OAuth a `backend/app.py`

Localitza la línia que conté `@app.route("/api/auth/me"` (línia ~1249) i afegeix el bloc següent **just abans**:

```python
@app.route("/api/auth/google", methods=["GET"])
def auth_google_start():
    """Pas 1 OAuth: redirigeix a Google amb state anti-CSRF."""
    import secrets as _secrets
    import urllib.parse
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    if not client_id:
        return jsonify({"error": "Google OAuth no configurat"}), 503
    state = _secrets.token_hex(16)
    redirect_uri = BASE_URL + "/api/auth/google/callback"
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email",
        "state": state,
        "prompt": "select_account",
    })
    resp = redirect("https://accounts.google.com/o/oauth2/v2/auth?" + params, code=302)
    secure = not app.debug
    resp.set_cookie("oauth_state", state, httponly=True, secure=secure,
                    samesite="Lax", max_age=300)
    return resp


@app.route("/api/auth/google/callback", methods=["GET"])
def auth_google_callback():
    """Pas 2 OAuth: intercanvia el codi, crea/troba l'usuari i inicia sessió."""
    import secrets as _secrets
    import db as _db
    from datetime import datetime, timezone, timedelta
    from flask import redirect as _redirect

    # Verificació anti-CSRF
    state_cookie = request.cookies.get("oauth_state", "")
    state_param  = request.args.get("state", "")
    if not state_cookie or state_cookie != state_param:
        return _redirect("/?google_error=state")

    code = request.args.get("code", "")
    if not code:
        return _redirect("/?google_error=no_code")

    client_id     = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    redirect_uri  = BASE_URL + "/api/auth/google/callback"

    # Intercanvi codi → tokens
    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=10,
    )
    if not token_resp.ok:
        logger.error("Google token error: %s", token_resp.text)
        return _redirect("/?google_error=token")

    access_token = token_resp.json().get("access_token", "")
    if not access_token:
        return _redirect("/?google_error=no_token")

    # Obtenir info de l'usuari
    userinfo_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": "Bearer " + access_token},
        timeout=10,
    )
    if not userinfo_resp.ok:
        return _redirect("/?google_error=userinfo")

    info       = userinfo_resp.json()
    google_sub = info.get("sub", "")
    email      = (info.get("email") or "").strip().lower()
    if not email or not google_sub:
        return _redirect("/?google_error=no_email")

    conn = _db.get_db()
    try:
        # Cerca per google_id primer, després per email (merge de compte existent)
        user = _db.query_one(conn, "SELECT id, is_admin FROM users WHERE google_id = ?", (google_sub,))
        if not user:
            user = _db.query_one(
                conn,
                "SELECT id, is_admin FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1",
                (email,),
            )
            if user:
                # Vincula google_id a compte existent
                conn.execute("UPDATE users SET google_id = ?, verified = 1 WHERE id = ?",
                             (google_sub, user["id"]))
            else:
                # Nou usuari
                conn.execute(
                    "INSERT INTO users (email, password_hash, verified, google_id) VALUES (?, 'google', 1, ?)",
                    (email, google_sub),
                )
                conn.commit()
                user = _db.query_one(conn, "SELECT id, is_admin FROM users WHERE google_id = ?", (google_sub,))

        conn.commit()
        uid      = user["id"]
        is_admin = bool(user["is_admin"])

        # Crea sessió (idèntic al login normal)
        session_token = _secrets.token_hex(32)
        expires = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        ip = request.remote_addr or ""
        conn.execute(
            "INSERT INTO sessions (user_id, token, expires_at, ip, user_agent) VALUES (?, ?, ?, ?, ?)",
            (uid, session_token, expires, ip, request.headers.get("User-Agent", "")),
        )
        conn.commit()
    finally:
        conn.close()

    secure = not app.debug
    resp = _redirect("/?google=1")
    resp.set_cookie("session", session_token,
                    httponly=True, secure=secure, samesite="Lax",
                    max_age=30 * 24 * 3600)
    resp.set_cookie("oauth_state", "", max_age=0)
    return resp

```

**Verificació**:
```bash
cd backend && python3 -c "import app; print('OK')"
```
Expected: `OK` (sense errors d'importació ni sintaxi)

```bash
grep "auth_google_start\|auth_google_callback" backend/app.py | wc -l
```
Expected: `2`

---

### Pas 4 — Afegir claus i18n a `frontend/i18n.js`

Localitza el bloc CA (cerca `'nav.admin': 'Admin',` dins el bloc `ca:`) i afegeix **just després**:

```javascript
      'nav.admin': 'Admin',
      'auth.google.btn': 'Continua amb Google',
      'auth.google.separator': 'o',
```

Localitza el bloc ES (cerca `'nav.admin': 'Admin',` dins el bloc `es:`) i afegeix **just després**:

```javascript
      'nav.admin': 'Admin',
      'auth.google.btn': 'Continuar con Google',
      'auth.google.separator': 'o',
```

**Verificació**:
```bash
/usr/bin/grep -c "auth.google" frontend/i18n.js
```
Expected: `4` (2 claus × 2 locales)

---

### Pas 5 — Afegir botó Google a `frontend/login.html`

Localitza el bloc `<div class="auth-page">` i afegeix el separador i el botó **just abans** del `<form id="form-login">`:

```html
    <div class="auth-page">
      <h1 data-i18n="login.h1">Inicia sessió</h1>
      <p id="msg" class="msg" hidden></p>

      <a id="btn-google" href="/api/auth/google" class="google-btn">
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.874 2.684-6.615z" fill="#4285F4"/>
          <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
          <path d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
          <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
        </svg>
        <span data-i18n="auth.google.btn">Continua amb Google</span>
      </a>

      <div class="auth-separator">
        <span data-i18n="auth.google.separator">o</span>
      </div>

      <form id="form-login">
```

Afegeix els estils CSS necessaris. Localitza el bloc `<style>` de `login.html` i afegeix **just abans** de `</style>`:

```css
    .google-btn {
      display: flex; align-items: center; justify-content: center; gap: 10px;
      width: 100%; padding: 10px 16px; border-radius: 4px;
      border: 1px solid var(--border); background: var(--white);
      color: var(--dark); text-decoration: none; font-size: 14px; font-weight: 500;
      font-family: inherit; cursor: pointer; transition: background 0.15s;
      margin-bottom: 4px;
    }
    .google-btn:hover { background: var(--warm2); }
    .auth-separator {
      display: flex; align-items: center; gap: 12px;
      margin: 16px 0; color: var(--warm); font-size: 12px;
    }
    .auth-separator::before, .auth-separator::after {
      content: ''; flex: 1; height: 1px; background: var(--border);
    }
```

**Verificació**:
```bash
/usr/bin/grep -c "btn-google\|google-btn\|auth-separator" frontend/login.html
```
Expected: `≥4`

---

### Pas 6 — Afegir botó Google a `frontend/register.html`

Repeteix el mateix patró que al Pas 5, però a `register.html`.

Localitza `<div class="auth-page">` i afegeix **just abans** del `<form id="form-register">` el mateix bloc HTML del botó Google i el separador (idèntic al Pas 5, canviant `form-login` → `form-register`).

Afegeix els mateixos estils CSS `.google-btn`, `.auth-separator` al `<style>` de `register.html`.

**Verificació**:
```bash
/usr/bin/grep -c "btn-google\|google-btn\|auth-separator" frontend/register.html
```
Expected: `≥4`

---

### Pas 7 — Tests de backend

```bash
cd backend && python -m pytest tests/ -v 2>&1 | tail -15
```

Expected: ≥118 passed. Cap dels tests existents hauria de fallar perquè:
- La migració 006 és additiva (nova columna nullable)
- Els endpoints nous no alteren cap endpoint existent
- `password_hash` segueix sent NOT NULL (sentinel `'google'` per a usuaris OAuth)

---

## Test plan

No hi ha tests d'integració E2E automàtics per als endpoints OAuth (el handshake requereix credencials reals de Google). La verificació és manual al VPS:

| Cas | Acció | Esperat |
|-----|-------|---------|
| Usuari nou | Clic "Continua amb Google" a login.html → selecciona compte Google | Redirigeix a `/?google=1`, widget topbar mostra email i "El meu perfil" |
| Compte existent (email coincideix) | Login Google amb email que ja té compte normal | Sessió iniciada, `google_id` vinculat a compte existent |
| Google ID ja vinculat | Segon login amb el mateix compte Google | Sessió iniciada normalment |
| GOOGLE_CLIENT_ID buit | `GET /api/auth/google` | Retorna 503 JSON `{"error": "Google OAuth no configurat"}` |
| State CSRF mismatch | Modificar manualment el cookie `oauth_state` | Redirigeix a `/?google_error=state` |
| Canvi d'idioma | Clic ES a login.html | Botó mostra "Continuar con Google" |

Per als tests unitaris de backend, afegeix a `backend/tests/test_auth.py` (seguint el patró dels tests existents al mateix fitxer):

```python
def test_google_oauth_start_no_config(client):
    """Sense GOOGLE_CLIENT_ID configurat, /api/auth/google retorna 503."""
    import os
    original = os.environ.pop("GOOGLE_CLIENT_ID", None)
    try:
        r = client.get("/api/auth/google")
        assert r.status_code == 503
    finally:
        if original:
            os.environ["GOOGLE_CLIENT_ID"] = original
```

---

## Criteris de done

```bash
# 1. Migració aplicada
python3 -c "
import sys; sys.path.insert(0, 'backend')
import db; conn = db.init_db()
cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
print('google_id' in cols)
conn.close()
"
# Expected: True

# 2. Endpoints existents
/usr/bin/grep "auth_google_start\|auth_google_callback" backend/app.py | wc -l
# Expected: 2

# 3. Variables al .env.example
/usr/bin/grep "GOOGLE_CLIENT_ID\|GOOGLE_CLIENT_SECRET" backend/.env.example | wc -l
# Expected: 2

# 4. Claus i18n
/usr/bin/grep -c "auth.google" frontend/i18n.js
# Expected: 4

# 5. Botó a login.html
/usr/bin/grep -c "btn-google" frontend/login.html
# Expected: ≥1

# 6. Botó a register.html
/usr/bin/grep -c "btn-google" frontend/register.html
# Expected: ≥1

# 7. Cap canvi a backend/db.py
git diff --name-only | grep "backend/db.py" && echo "FAIL" || echo "OK"
# Expected: OK

# 8. Tests backend
cd backend && python -m pytest tests/ -v 2>&1 | grep -E "passed|failed"
# Expected: ≥118 passed
```

---

## STOP conditions

- Si `backend/.env` del servidor **no té** `GOOGLE_CLIENT_ID` i `GOOGLE_CLIENT_SECRET` — para i avisa el propietari perquè configuri Google Cloud Console (veure secció "Configuració prèvia").
- Si la taula `users` ja té una columna `google_id` (migració ja aplicada parcialment) — verifica que l'índex existeix i continua des del Pas 2.
- Si `python3 -c "import app"` falla per error de sintaxi — para i reporta el missatge d'error exacte.
- Si els tests de backend fallen **per una raó diferent** a l'error pre-existent de sqlite3 als tests `test_db` — para i reporta.
- No afegeixis cap nova dependència Python. Tot el handshake OAuth usa `requests` (ja al projecte) i stdlib (`urllib.parse`, `secrets`).

## Maintenance notes

- Si en el futur es vol permetre als usuaris Google establir una contrasenya (per poder fer login per email+password), cal un endpoint nou `/api/auth/set-password` que comprovixi que `password_hash == 'google'` i permeti establir-ne una de nova.
- Si s'afegeix un altre provider OAuth (GitHub, Apple), el patró dels endpoints és idèntic: un endpoint `_start` que redirigeix i un `_callback` que crea sessió. Considera extraure la lògica de creació de sessió a una funció `_create_session(conn, user_id, request)` per evitar duplicació.
- El cookie `oauth_state` caduca als 5 minuts (`max_age=300`). Si l'usuari tarda més de 5 minuts a completar el flow a Google, rebrà un error `state` i haurà de tornar a clicar. És el comportament correcte per seguretat.
- `prompt=select_account` força Google a mostrar el selector de compte sempre, útil en dev per provar amb múltiples comptes. En producció és acceptable deixar-ho tal qual.
