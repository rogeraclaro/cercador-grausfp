# Pla 053 — Preferències d'email: toggle global per a notificacions automàtiques

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> ```bash
> git diff --stat 08f43f7..HEAD -- backend/app.py backend/migrations/ backend/alerts_service.py backend/centres_watch_service.py frontend/perfil.html frontend/i18n.js
> ```
> Si algun d'aquests fitxers ha canviat des que el pla va ser escrit, compara
> els excerpts de "Current state" amb el codi viu. Si no coincideixen, STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: 023–026 (auth DONE), 051 (perfil.html DONE)
- **Category**: direction
- **Planned at**: commit `08f43f7`, 2026-06-21

## Why this matters

Ara mateix si un usuari no vol rebre emails automàtics (alertes de graus, avisos de nous centres) l'única opció és desactivar cada alerta i cada seguiment individualment. No hi ha cap control global. Afegir un toggle "Vull rebre notificacions per email" al perfil d'usuari cobreix el cas d'ús més comú (pausa temporal de tots els avisos) i és el primer pas necessari per al compliment RGPD en comunicacions de màrqueting.

**Exclusions explícites**: els emails transaccionals (verificació de compte, recuperació de contrasenya) mai s'han de bloquejar per aquesta preferència — seguiran enviant-se sempre. El `notifier.py` (newsleter Brevo) gestiona la seva pròpia llista de subscriptors i queda fora d'àmbit d'aquest pla.

## Current state

### Fitxers rellevants

- `backend/migrations/006_google_oauth.sql` — última migració existent (versió 6)
- `backend/app.py` — endpoint `/api/auth/me` (línia 1379); no retorna `email_notifications`
- `backend/alerts_service.py` — `dispatch_alerts()`: query a línia ~173 filtra per `active=1 AND verified=1` però NO per `email_notifications`
- `backend/centres_watch_service.py` — `dispatch_centres_watch()`: query a línia ~124, mateix problema
- `backend/email_service.py` — `send_email()`, `send_verification_email()`, `send_password_reset_email()` — transaccionals, fora d'àmbit
- `backend/notifier.py` — notificacions newsletter via Brevo API a la seva pròpia llista — fora d'àmbit
- `frontend/perfil.html` — dashboard amb tabs "Favorits", "Alertes", "Seguiment"
- `frontend/i18n.js` — diccionari CA+ES; claus `perfil.*` a les línies ~25–30 (CA) i ~330–342 (ES)

### Excerpt: query alerts_service.py (~173-178)

```python
alerts = _db.query_all(
    conn,
    "SELECT a.id, a.user_id, a.filter_json, a.last_sent_at, u.email "
    "FROM alerts a JOIN users u ON u.id = a.user_id "
    "WHERE a.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
)
```

### Excerpt: query centres_watch_service.py (~124-129)

```python
watches = _db.query_all(
    conn,
    "SELECT cw.id, cw.user_id, cw.oferta_key, cw.oferta_denom, cw.provincia_filter, "
    "cw.last_sent_at, cw.snapshot_json, u.email "
    "FROM centres_watch cw JOIN users u ON u.id = cw.user_id "
    "WHERE cw.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
)
```

### Excerpt: endpoint /api/auth/me (app.py ~1379-1397)

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
            "SELECT id, email, is_admin FROM users WHERE id = ? AND deleted_at IS NULL AND is_active = 1",
            (user_id,),
        )
    finally:
        conn.close()
    if not user:
        return jsonify({"error": "Usuari no trobat"}), 404
    return jsonify({"id": user["id"], "email": user["email"], "is_admin": bool(user["is_admin"])})
```

### Excerpt: nav i seccions de perfil.html (~459-478)

```html
<nav class="section-nav" aria-label="Seccions del perfil">
  <a href="#favorits" class="section-nav-link active" id="tab-favorits" data-i18n="perfil.nav.favorits">Favorits</a>
  <a href="#alertes" class="section-nav-link" id="tab-alertes" data-i18n="perfil.nav.alertes">Alertes</a>
  <a href="#seguiment" class="section-nav-link" id="tab-seguiment" data-i18n="perfil.nav.seguiment">Seguiment</a>
</nav>

<main class="content">
  <div id="section-favorits"> ... </div>
  <div id="section-alertes" hidden> ... </div>
  <div id="section-seguiment" hidden> ... </div>
</main>
```

### Excerpt: tabs JS de perfil.html (~501-513)

```javascript
var tabs = ['favorits', 'alertes', 'seguiment'];
// ... clic en tab → amaga totes les seccions, mostra la clicada
```

### Excerpt: claus i18n CA de perfil (i18n.js ~25-30)

```javascript
'perfil.hero.sub': 'Favorits, alertes i seguiment de centres en un sol lloc',
'perfil.nav.favorits': 'Favorits',
'perfil.nav.alertes': 'Alertes',
'perfil.nav.seguiment': 'Seguiment',
```

### Convenció de tests (test_auth.py)

Patró estàndard (model per a tests nous):

```python
def _register_and_login(client, email="user@test.com", password="password123"):
    with patch("email_service.send_verification_email"):
        client.post("/api/auth/register",
                    data=json.dumps({"email": email, "password": password}),
                    content_type="application/json")
    conn = db.get_db()
    conn.execute("UPDATE users SET verified = 1 WHERE email = ?", (email,))
    conn.commit(); conn.close()
    client.post("/api/auth/login",
                data=json.dumps({"email": email, "password": password}),
                content_type="application/json")
```

Fixture `fresh_db` (autouse) crea BD temporal per test; fixture `client` retorna `flask_app.test_client()`.

## Commands you will need

| Propòsit | Comanda | Esperat |
|----------|---------|---------|
| Backend tests | `cd backend && python -m pytest tests/ -v` | ≥118 passed (+ nous) |
| Import check | `cd backend && python3 -c "import app; print('OK')"` | `OK` |
| Drift check | veure capçalera | 0 canvis o excerpts coincideixen |

No hi ha typecheck ni build frontend (vanilla JS).

## Scope

**En àmbit** (els únics fitxers a modificar o crear):
- `backend/migrations/007_email_notifications.sql` (crear)
- `backend/app.py` — modificar `auth_me()` i afegir endpoint `PATCH /api/auth/email-prefs`
- `backend/alerts_service.py` — afegir `AND u.email_notifications = 1` a la query
- `backend/centres_watch_service.py` — afegir `AND u.email_notifications = 1` a la query
- `backend/tests/test_auth.py` — afegir tests nous al final
- `frontend/perfil.html` — afegir tab "Compte" + secció toggle
- `frontend/i18n.js` — afegir claus `perfil.compte.*`

**Fora d'àmbit** (NO tocar):
- `backend/email_service.py` — els emails transaccionals mai es bloquegen
- `backend/notifier.py` — newsletter Brevo, gestió pròpia de subscriptors
- `backend/migrations/001_initial_schema.sql` — mai modificar migracions existents
- `frontend/auth.js` — widget topbar, no té relació
- Qualsevol altra pàgina frontend

## Git workflow

- Branca: `feat/053-email-preferences`
- Commits: conventional commits, ex: `feat(auth): preferències d'email — toggle global notificacions`
- No fer push ni PR tret que el reviewer ho demani.

---

## Steps

### Pas 1 — Migració 007: columna `email_notifications` a `users`

Crea `backend/migrations/007_email_notifications.sql`:

```sql
-- Migration 007: Preferències d'email — toggle global de notificacions automàtiques

ALTER TABLE users ADD COLUMN email_notifications INTEGER NOT NULL DEFAULT 1;

INSERT OR IGNORE INTO schema_version (version) VALUES (7);
```

`DEFAULT 1` significa que tots els usuaris existents reben notificacions per defecte (opt-out, no opt-in), que és el comportament actual.

**Verificació**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'backend')
import db
conn = db.init_db()
cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
print('email_notifications in cols:', 'email_notifications' in cols)
conn.close()
"
```
Expected: `email_notifications in cols: True`

---

### Pas 2 — Filtrar `alerts_service.py`

Localitza la query de `dispatch_alerts` a `backend/alerts_service.py`. La línia actual és:

```python
"WHERE a.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
```

Canvia-la a:

```python
"WHERE a.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL AND u.email_notifications = 1",
```

**Verificació**:
```bash
grep "email_notifications" backend/alerts_service.py
```
Expected: 1 línia amb `u.email_notifications = 1`

---

### Pas 3 — Filtrar `centres_watch_service.py`

Localitza la query de `dispatch_centres_watch` a `backend/centres_watch_service.py`. La línia actual és:

```python
"WHERE cw.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
```

Canvia-la a:

```python
"WHERE cw.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL AND u.email_notifications = 1",
```

**Verificació**:
```bash
grep "email_notifications" backend/centres_watch_service.py
```
Expected: 1 línia amb `u.email_notifications = 1`

---

### Pas 4 — Afegir endpoint `PATCH /api/auth/email-prefs` i actualitzar `/api/auth/me`

#### 4a — Actualitzar `auth_me()` per retornar `email_notifications`

Localitza `auth_me()` a `backend/app.py` (línia ~1379). Modifica la SELECT per incloure el camp nou:

Canvia:
```python
"SELECT id, email, is_admin FROM users WHERE id = ? AND deleted_at IS NULL AND is_active = 1",
```
Per:
```python
"SELECT id, email, is_admin, email_notifications FROM users WHERE id = ? AND deleted_at IS NULL AND is_active = 1",
```

Canvia la línia `return jsonify(...)` de:
```python
return jsonify({"id": user["id"], "email": user["email"], "is_admin": bool(user["is_admin"])})
```
Per:
```python
return jsonify({
    "id": user["id"],
    "email": user["email"],
    "is_admin": bool(user["is_admin"]),
    "email_notifications": bool(user["email_notifications"]),
})
```

#### 4b — Afegir l'endpoint PATCH just després de `auth_me()`

Afegeix el bloc següent **immediatament després** de la funció `auth_me()` (abans de `auth_forgot_password`):

```python
@app.route("/api/auth/email-prefs", methods=["PATCH"])
def auth_email_prefs():
    """Actualitza la preferència d'email de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    if "email_notifications" not in data:
        return jsonify({"error": "Falta el camp email_notifications"}), 400
    value = 1 if data["email_notifications"] else 0
    conn = _db.get_db()
    try:
        conn.execute(
            "UPDATE users SET email_notifications = ? WHERE id = ?",
            (value, user_id),
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({"email_notifications": bool(value)})
```

**Verificació**:
```bash
cd backend && python3 -c "import app; print('OK')"
```
Expected: `OK`

```bash
grep -c "email_notifications" backend/app.py
```
Expected: `≥4` (SELECT, jsonify, endpoint, UPDATE)

---

### Pas 5 — Afegir claus i18n a `frontend/i18n.js`

Localitza el bloc CA i afegeix **just després de** `'perfil.nav.seguiment': 'Seguiment',`:

```javascript
      'perfil.nav.compte': 'Compte',
      'perfil.compte.emails.label': 'Rebre notificacions per email',
      'perfil.compte.emails.desc': 'Alertes de nous graus i avisos de centres. Els emails de verificació i de recuperació de contrasenya sempre s\'envien.',
      'perfil.compte.emails.saved': 'Preferència desada.',
      'perfil.compte.emails.error': 'Error desant la preferència.',
```

Localitza el bloc ES i afegeix **just després de** `'perfil.nav.seguiment': 'Seguimiento',`:

```javascript
      'perfil.nav.compte': 'Cuenta',
      'perfil.compte.emails.label': 'Recibir notificaciones por email',
      'perfil.compte.emails.desc': 'Alertas de nuevos grados y avisos de centros. Los emails de verificación y recuperación de contraseña siempre se envían.',
      'perfil.compte.emails.saved': 'Preferencia guardada.',
      'perfil.compte.emails.error': 'Error al guardar la preferencia.',
```

**Verificació**:
```bash
/usr/bin/grep -c "perfil.compte" frontend/i18n.js
```
Expected: `10` (5 claus × 2 locales)

---

### Pas 6 — Afegir tab "Compte" i secció toggle a `frontend/perfil.html`

#### 6a — Afegir el tab "Compte" a la nav

Localitza:
```html
<a href="#seguiment" class="section-nav-link" id="tab-seguiment" data-i18n="perfil.nav.seguiment">Seguiment</a>
```

Afegeix **just després**:
```html
    <a href="#compte" class="section-nav-link" id="tab-compte" data-i18n="perfil.nav.compte">Compte</a>
```

#### 6b — Afegir la secció "Compte" a `<main class="content">`

Localitza la darrera secció existent:
```html
<div id="section-seguiment" hidden>
```

Afegeix **just després** de tancar `</div>` d'`id="section-seguiment"`:
```html
    <div id="section-compte" hidden>
      <div class="pref-row">
        <label class="pref-label">
          <input type="checkbox" id="chk-email-notif">
          <span data-i18n="perfil.compte.emails.label">Rebre notificacions per email</span>
        </label>
        <p class="pref-desc" data-i18n="perfil.compte.emails.desc">Alertes de nous graus i avisos de centres. Els emails de verificació i de recuperació de contrasenya sempre s'envien.</p>
        <p id="pref-msg" class="msg" hidden></p>
      </div>
    </div>
```

#### 6c — Afegir estils CSS per a `.pref-row` i `.pref-label`

Localitza el bloc `<style>` de `perfil.html` i afegeix **just abans** de `</style>`:

```css
    .pref-row { padding: 16px 0; }
    .pref-label { display: flex; align-items: center; gap: 10px; cursor: pointer; font-weight: 500; }
    .pref-label input[type="checkbox"] { width: 18px; height: 18px; cursor: pointer; }
    .pref-desc { margin: 8px 0 0 28px; font-size: 13px; color: var(--warm); }
```

#### 6d — Afegir "compte" a l'array de tabs i la lògica del toggle al JS

Localitza la línia:
```javascript
var tabs = ['favorits', 'alertes', 'seguiment'];
```

Canvia-la a:
```javascript
var tabs = ['favorits', 'alertes', 'seguiment', 'compte'];
```

Localitza el bloc `async function loadFavorits()` o el punt on es fa el primer `fetch('/api/auth/me')` (línia ~526). Just **sota** de la línia on s'assigna `user` des de la resposta de `/api/auth/me`, afegeix la inicialització del toggle. Busca el context exacte:

```javascript
var res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
```

Després d'obtenir el `user` d'aquesta resposta, afegeix (en el bloc on `user` és disponible — típicament dins un `if (res.ok)`):

```javascript
          // Inicialitza toggle email
          var chk = document.getElementById('chk-email-notif');
          if (chk && user.email_notifications !== undefined) {
            chk.checked = !!user.email_notifications;
            chk.addEventListener('change', async function() {
              var msgEl = document.getElementById('pref-msg');
              try {
                var r = await fetch(API_BASE + '/api/auth/email-prefs', {
                  method: 'PATCH', credentials: 'include',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ email_notifications: chk.checked }),
                });
                if (r.ok) {
                  msgEl.textContent = t('perfil.compte.emails.saved');
                  msgEl.style.color = 'var(--success, green)';
                } else {
                  msgEl.textContent = t('perfil.compte.emails.error');
                  msgEl.style.color = 'var(--danger, red)';
                  chk.checked = !chk.checked; // reverteix
                }
                msgEl.removeAttribute('hidden');
                setTimeout(function() { msgEl.setAttribute('hidden', ''); }, 3000);
              } catch (e) {
                msgEl.textContent = t('perfil.compte.emails.error');
                msgEl.style.color = 'var(--danger, red)';
                msgEl.removeAttribute('hidden');
                chk.checked = !chk.checked;
              }
            });
          }
```

**Verificació**:
```bash
/usr/bin/grep -c "section-compte\|tab-compte\|chk-email-notif" frontend/perfil.html
```
Expected: `≥3`

---

### Pas 7 — Tests de backend

Afegeix al final de `backend/tests/test_auth.py` (seguint el patró de fixtures existent):

```python
# ---------------------------------------------------------------------------
# Preferències d'email
# ---------------------------------------------------------------------------

def test_email_prefs_default_is_true(client):
    """Un usuari nou té email_notifications=True per defecte a /api/auth/me."""
    _register(client)
    _verify_user()
    _login(client)
    r = client.get("/api/auth/me", content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["email_notifications"] is True


def test_email_prefs_toggle_off(client):
    """PATCH /api/auth/email-prefs desactiva les notificacions."""
    _register(client)
    _verify_user()
    _login(client)
    r = client.patch(
        "/api/auth/email-prefs",
        data=json.dumps({"email_notifications": False}),
        content_type="application/json",
    )
    assert r.status_code == 200
    assert r.get_json()["email_notifications"] is False
    # Confirma via /api/auth/me
    r2 = client.get("/api/auth/me")
    assert r2.get_json()["email_notifications"] is False


def test_email_prefs_toggle_on(client):
    """PATCH /api/auth/email-prefs torna a activar les notificacions."""
    _register(client)
    _verify_user()
    _login(client)
    client.patch("/api/auth/email-prefs",
                 data=json.dumps({"email_notifications": False}),
                 content_type="application/json")
    r = client.patch("/api/auth/email-prefs",
                     data=json.dumps({"email_notifications": True}),
                     content_type="application/json")
    assert r.status_code == 200
    assert r.get_json()["email_notifications"] is True


def test_email_prefs_unauthenticated(client):
    """Sense sessió, PATCH /api/auth/email-prefs retorna 401."""
    r = client.patch(
        "/api/auth/email-prefs",
        data=json.dumps({"email_notifications": False}),
        content_type="application/json",
    )
    assert r.status_code == 401


def test_email_prefs_missing_field(client):
    """Cos JSON sense email_notifications retorna 400."""
    _register(client)
    _verify_user()
    _login(client)
    r = client.patch(
        "/api/auth/email-prefs",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert r.status_code == 400
```

**Verificació**:
```bash
cd backend && python -m pytest tests/test_auth.py -v -k "email_pref" 2>&1 | tail -10
```
Expected: `5 passed`

```bash
cd backend && python -m pytest tests/ -v 2>&1 | grep -E "passed|failed"
```
Expected: ≥123 passed (118 base + 5 nous)

---

## Test plan

5 tests unitaris nous a `backend/tests/test_auth.py`:

| Test | Cas |
|------|-----|
| `test_email_prefs_default_is_true` | `/api/auth/me` retorna `email_notifications: true` per a usuari nou |
| `test_email_prefs_toggle_off` | PATCH desactiva i `/api/auth/me` confirma |
| `test_email_prefs_toggle_on` | PATCH reactiva |
| `test_email_prefs_unauthenticated` | 401 sense sessió |
| `test_email_prefs_missing_field` | 400 si falta el camp |

El filtratge als serveis (`alerts_service`, `centres_watch_service`) no es pot testar automàticament sense mocks complexos — la verificació és el grep que confirma el canvi a la query SQL.

---

## Criteris de done

```bash
# 1. Migració aplicada
python3 -c "
import sys; sys.path.insert(0, 'backend')
import db; conn = db.init_db()
cols = [r[1] for r in conn.execute('PRAGMA table_info(users)').fetchall()]
print('email_notifications' in cols)
conn.close()
"
# Expected: True

# 2. Filtre alerts_service
grep "email_notifications" backend/alerts_service.py | wc -l
# Expected: 1

# 3. Filtre centres_watch_service
grep "email_notifications" backend/centres_watch_service.py | wc -l
# Expected: 1

# 4. Endpoint nou + me() actualitzat
grep -c "email_notifications" backend/app.py
# Expected: ≥4

# 5. Claus i18n
/usr/bin/grep -c "perfil.compte" frontend/i18n.js
# Expected: 10

# 6. UI perfil.html
/usr/bin/grep -c "section-compte\|tab-compte\|chk-email-notif" frontend/perfil.html
# Expected: ≥3

# 7. db.py i email_service.py no tocats
git diff --name-only | grep -E "backend/db.py|backend/email_service.py" && echo "FAIL" || echo "OK"
# Expected: OK

# 8. Tests
cd backend && python -m pytest tests/ -v 2>&1 | grep -E "passed|failed"
# Expected: ≥123 passed
```

---

## STOP conditions

- Si la query de `alerts_service.py` o `centres_watch_service.py` ha canviat de forma significativa respecte als excerpts — compara amb el codi viu i adapta el punt d'inserció, però STOP si la lògica és irreconeixible.
- Si `python3 -c "import app"` falla per sintaxi — STOP i reporta el missatge exacte.
- Si els tests fallen per una raó diferent als 2 pre-existents (`test_schema_version_is_1`, `test_run_migrations_idempotent`) — STOP i reporta.
- No afegeixis cap nova dependència Python.
- Si `email_service.py` sembla necessitar canvis per implementar qualsevol pas — STOP: queda fora d'àmbit per disseny.

## Maintenance notes

- **Emails transaccionals exclosos per disseny**: `send_verification_email` i `send_password_reset_email` a `email_service.py` s'envien sempre, independentment d'`email_notifications`. Si s'afegeix un nou tipus d'email automàtic al futur, cal recordar afegir `AND u.email_notifications = 1` a la seva query.
- **El notifier.py (newsletter Brevo)** usa la seva pròpia llista de subscriptors de Brevo — si es vol que el toggle afecti també les newsletters, cal un pla separat que cridi la Brevo API per afegir/treure l'usuari de la llista.
- **RGPD**: aquest toggle implementa opt-out (actiu per defecte). Si cal opt-in explícit (usuaris nous han de marcar activament que volen rebre notificacions), cal canviar el `DEFAULT 1` de la migració a `DEFAULT 0` i afegir la casella al formulari de registre. Decisió de negoci, fora d'àmbit aquí.
- Si en el futur es volen preferències granulars per tipus (alertes sí, centres no), el toggle global d'aquest pla és el primer pas — es pot estendre amb columnes addicionals (`alert_emails`, `centres_emails`) sense trencar res.
