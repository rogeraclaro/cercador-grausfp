# Pla 037: Admin s'autentica via sessió normal — admin.html protegit

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, do NOT update `plans/README.md` —
> the reviewer maintains the index. Before reporting, audit every claim in
> your report against an actual tool result from this session — only report
> what you can point to evidence for; if a verification failed or was
> skipped, say so plainly. When finished, reply with exactly the report
> format below.
>
> **Drift check (run first)**:
> `git diff --stat d9a4728..HEAD -- fp-cercador/backend/app.py fp-cercador/backend/migrations/ fp-cercador/frontend/admin.html fp-cercador/frontend/login.html fp-cercador/frontend/auth.js`
> Si algun d'aquests fitxers ha canviat des de `d9a4728`, compara els
> excerpts de "Current state" amb el codi viu. Si plan 036 ja s'ha aplicat
> (grep -c "admin/users" fp-cercador/backend/app.py retorna ≥3), els nous
> endpoints d'usuaris també usaran `_check_auth`; aquest pla els actualitza
> igualment — no és una condició STOP.

## Status

- **Priority**: P2
- **Effort**: M (3–5h)
- **Risk**: MED — modifica el flux d'autenticació d'admin i la protecció d'una pàgina sensible
- **Depends on**: plans 023–026 DONE (sistema de login base). Pot córrer en paral·lel o abans/després del pla 036.
- **Category**: security / direction
- **Planned at**: commit `d9a4728`, 2026-06-17

## Why this matters

Ara mateix, qualsevol persona que conegui la URL `admin.html` pot accedir-hi directament. L'autenticació dins la pàgina requereix enganxar manualment el `ADMIN_TOKEN`, que és un secret de servidor que no hauria de circular entre humans. Aquest pla: (1) afegeix un flag `is_admin` als usuaris, (2) fa que el login redirigeixi l'admin a `admin.html` automàticament, (3) protegeix `admin.html` amb un guard JS que redirigeix qualsevol no-admin, (4) canvia tots els endpoints admin perquè acceptin TANT Bearer ADMIN_TOKEN (per a scripts automàtics) COM sessió d'usuari admin (per a la UI), i (5) elimina l'input de token de `admin.html`.

## Codebase context

### Taula `users` actual (`backend/migrations/001_initial_schema.sql`)

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

Si el pla 036 s'ha aplicat primer, la taula ja tindrà `is_active INTEGER NOT NULL DEFAULT 1` i la versió de schema serà 3. La nova migració d'aquest pla afegirà `is_admin` i incrementarà la versió.

**Important**: si el pla 036 NO s'ha aplicat, la versió actual és 2 i la nova migració serà la 003. Si el pla 036 SÍ s'ha aplicat, la versió és 3 i la nova migració serà la 004. El fitxer de migració ha de tenir el número correcte — veure Step 1.

### Helper `_check_auth` actual (`backend/app.py:147–153`)

```python
def _check_auth(req) -> bool:
    """Verifica el token Bearer amb comparació constant-time (evita timing attacks)."""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[7:]
    return hmac.compare_digest(provided, ADMIN_TOKEN)
```

S'ha de mantenir intacte (el reutilitzarà el nou `_check_admin`).

### Endpoint `/api/auth/me` (`backend/app.py:702–719`)

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

Cal afegir `is_admin` a la query i al JSON retornat.

**Nota**: Si el pla 036 ja s'ha aplicat, la query ja inclourà `AND is_active = 1`. Adaptar en conseqüència.

### Endpoint `/api/auth/login` — resposta actual (`backend/app.py:676`)

```python
resp = jsonify({"user": {"id": uid, "email": email}})
```

Cal afegir `is_admin` a la resposta perquè `login.html` pugui decidir on redirigir.

### `login.html` — redirect post-login (línia ~168)

```js
if (res.ok) {
  window.location.href = 'index.html';
}
```

Cal canviar per redirigir a `admin.html` si `data.user.is_admin`.

### `admin.html` — estructura actual de la topbar i token (línia ~185–201)

```html
<header class="topbar">
  <div class="topbar-inner">
    <span class="topbar-logo">GrausFP</span>
  </div>
</header>

<main class="container">
  <h1>Administració</h1>

  <!-- ── Secció 1: Refresh manual ── -->
  <section class="section" id="section-refresh">
    <h2>Refresh manual</h2>
    <label for="token-input">ADMIN_TOKEN</label>
    <input id="token-input" type="password" autocomplete="off" placeholder="Enganxa el token">
    <button id="refresh-btn">Actualitzar dades</button>
```

La secció "Refresh manual" s'ha de mantenir, però sense el camp `ADMIN_TOKEN` (la sessió s'encarrega de l'autenticació). Cal eliminar el `<label>` i l'`<input id="token-input">`.

### `admin.html` — funció `getToken()` (línia ~265)

```js
function getToken() {
  return document.getElementById('token-input').value.trim();
}
```

Totes les crides fetch que usen `getToken()` han de canviar per no enviar cap header `Authorization` i afegir `credentials: 'include'` (les cookies de sessió s'envien automàticament en request same-origin).

### Crides fetch de `admin.html` que cal actualitzar

Busca totes les ocurrències de `'Authorization': 'Bearer ' + token` a `admin.html`. Cadascuna cal:
1. Eliminar la línia `'Authorization': 'Bearer ' + token`
2. Afegir `credentials: 'include'` a l'objecte de fetch (si no existeix ja)

Cerca també `const token = getToken();` — eliminar les declaracions i calls a `getToken()` dins els event listeners.

## Scope

**In scope** (únics fitxers a modificar):
- `fp-cercador/backend/migrations/003_add_is_admin.sql` o `004_add_is_admin.sql` (crear nou — el número depèn de si 036 s'ha aplicat; veure Step 1)
- `fp-cercador/backend/app.py`
- `fp-cercador/frontend/admin.html`
- `fp-cercador/frontend/login.html`

**Out of scope** (NO tocar):
- `frontend/auth.js` — no coneix el concepte d'admin; deixar-lo intacte
- `frontend/index.html` — no canvia
- `backend/tests/` — les failures de schema_version pre-existents no formen part d'aquest pla
- Cap altre fitxer de frontend

## Commands you will need

| Propòsit | Comanda | Resultat esperat |
|---|---|---|
| Tests backend | `cd fp-cercador && python -m pytest backend/tests/ -q` | ≥78 passed |
| Verificar migració | `ls fp-cercador/backend/migrations/` | fitxer nou `00N_add_is_admin.sql` present |
| Verificar `_check_admin` | `grep -c "_check_admin" fp-cercador/backend/app.py` | ≥8 (definició + totes les crides) |
| Verificar `is_admin` a me | `grep -c "is_admin" fp-cercador/backend/app.py` | ≥5 |
| Verificar guard admin.html | `grep -c "is_admin\|/api/auth/me" fp-cercador/frontend/admin.html` | ≥3 |
| Verificar token eliminat | `grep -c "token-input\|getToken" fp-cercador/frontend/admin.html` | `0` |
| Verificar redirect login | `grep -c "is_admin\|admin.html" fp-cercador/frontend/login.html` | ≥2 |

## Steps

---

### Step 1: Determinar el número de migració correcte i crear-la

Primer, determina quina versió de schema existeix:

```bash
ls fp-cercador/backend/migrations/
```

- Si només veus `001_initial_schema.sql` i `002_observatory.sql` → crea `003_add_is_admin.sql`
- Si també veus `003_add_is_active.sql` (pla 036 aplicat) → crea `004_add_is_admin.sql`

Crea el fitxer amb el número correcte (`003` o `004`) i aquest contingut:

```sql
-- Migration 00N: Afegeix is_admin a users (autenticació admin via sessió)

ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0;

INSERT INTO schema_version (version) VALUES (<N>);
```

Substitueix `<N>` per 3 o 4 segons correspongui.

**Verificació**: `ls fp-cercador/backend/migrations/` mostra el nou fitxer.

---

### Step 2: Afegir `_check_admin()` a `backend/app.py`

Localitza la funció `_check_auth` (línia ~147). Afegeix la nova funció `_check_admin` JUST DESPRÉS de `_check_auth` (deixa una línia en blanc entre elles):

```python
def _check_admin(req) -> bool:
    """Accepta Bearer ADMIN_TOKEN (scripts) O sessió d'usuari amb is_admin=1 (UI)."""
    if _check_auth(req):
        return True
    import db as _db
    token = req.cookies.get("session")
    if not token:
        return False
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            """SELECT u.id FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > datetime('now')
               AND u.is_admin = 1 AND u.is_active = 1 AND u.deleted_at IS NULL""",
            (token,),
        )
        return bool(row)
    finally:
        conn.close()
```

**Nota**: Si el pla 036 NO s'ha aplicat, la columna `is_active` no existirà encara. En aquest cas, elimina `AND u.is_active = 1` de la query (o assegura't d'aplicar primer el pla 036). Si no saps l'estat, executa: `python -c "import sqlite3; c=sqlite3.connect('fp-cercador/backend/data/fp_cercador.db'); print([x[1] for x in c.execute('PRAGMA table_info(users)')])"` — si `is_active` no apareix, elimina-la de la query.

**Verificació**: `grep -c "_check_admin" fp-cercador/backend/app.py` retorna `1` (la definició).

---

### Step 3: Substituir totes les crides `_check_auth` pels endpoints admin

Localitza totes les línies de `backend/app.py` que fan `if not _check_auth(request):`. Substitueix-les per `if not _check_admin(request):`.

Per trobar-les:
```bash
grep -n "_check_auth(request)" fp-cercador/backend/app.py
```

Cada línia trobada ha de passar de:
```python
    if not _check_auth(request):
```
a:
```python
    if not _check_admin(request):
```

No toques la definició de `_check_auth` en si (línia ~147) — segueix existint i és usada per `_check_admin`.

**Verificació**: `grep -c "_check_auth(request)" fp-cercador/backend/app.py` retorna `0` (cap crida directa queda). `grep -c "_check_admin(request)" fp-cercador/backend/app.py` retorna el número de rutes admin (≥5 si el pla 036 no s'ha aplicat, ≥8 si sí).

---

### Step 4: Actualitzar `/api/auth/me` per retornar `is_admin`

Localitza `auth_me` (línia ~702). Modifica la query:

```python
# ABANS:
        user = _db.query_one(
            conn,
            "SELECT id, email FROM users WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        )
# ...
    return jsonify({"id": user["id"], "email": user["email"]})

# DESPRÉS:
        user = _db.query_one(
            conn,
            "SELECT id, email, is_admin FROM users WHERE id = ? AND deleted_at IS NULL",
            (user_id,),
        )
# ...
    return jsonify({"id": user["id"], "email": user["email"], "is_admin": bool(user["is_admin"])})
```

**Nota**: Si el pla 036 ja ha modificat la query per incloure `AND is_active = 1`, mantén-ho.

**Verificació**: `grep -c "is_admin" fp-cercador/backend/app.py` retorna ≥ 3 (la nova migració no compta — és SQL, no Python).

---

### Step 5: Actualitzar `/api/auth/login` per retornar `is_admin`

Localitza la query de login (línia ~653):
```python
"SELECT id, password_hash, verified FROM users WHERE email = ? AND deleted_at IS NULL",
```

Canvia-la per:
```python
"SELECT id, password_hash, verified, is_admin FROM users WHERE email = ? AND deleted_at IS NULL",
```

(Si el pla 036 ja ha afegit `AND is_active = 1`, mantén-ho.)

Localitza la resposta de login (línia ~676):
```python
resp = jsonify({"user": {"id": uid, "email": email}})
```

Cal passar `is_admin` a la resposta. Modifica el codi de login per guardar `is_admin` de l'objecte `user` i incloure'l:

```python
# Abans de la línia resp = ..., afegeix:
is_admin = bool(user["is_admin"])
# Canvia la línia resp:
resp = jsonify({"user": {"id": uid, "email": email, "is_admin": is_admin}})
```

**Verificació**: `grep -c "is_admin" fp-cercador/backend/app.py` retorna ≥ 5.

---

### Step 6: Actualitzar `login.html` per redirigir l'admin

Localitza el bloc post-login (línia ~167–168):
```js
        if (res.ok) {
          window.location.href = 'index.html';
        }
```

Substitueix per:
```js
        if (res.ok) {
          window.location.href = data.user && data.user.is_admin ? 'admin.html' : 'index.html';
        }
```

**Verificació**: `grep -c "admin.html" fp-cercador/frontend/login.html` retorna `1`.

---

### Step 7: Afegir guard de sessió i logout a `admin.html`

#### 7a. Topbar: afegir botó de logout i info d'usuari

Localitza la topbar (línia ~185):
```html
  <header class="topbar">
    <div class="topbar-inner">
      <span class="topbar-logo">GrausFP</span>
    </div>
  </header>
```

Substitueix per:
```html
  <header class="topbar">
    <div class="topbar-inner" style="justify-content: space-between;">
      <span class="topbar-logo">GrausFP — Administració</span>
      <span id="admin-identity" style="color:#ccc;font-size:13px;"></span>
      <button id="btn-logout" style="background:transparent;border:1px solid #555;color:#ccc;padding:6px 14px;margin-top:0;font-size:13px;" onclick="adminLogout()">Sortir</button>
    </div>
  </header>
```

#### 7b. Eliminar el camp ADMIN_TOKEN de la secció "Refresh manual"

Localitza dins `<section class="section" id="section-refresh">`:
```html
      <label for="token-input">ADMIN_TOKEN</label>
      <input id="token-input" type="password" autocomplete="off" placeholder="Enganxa el token">
```

Elimina exactament aquestes dues línies. La secció queda amb `<h2>Refresh manual</h2>` directament seguida del `<button id="refresh-btn">`.

#### 7c. Afegir guard al `<script>` de `admin.html`

Localitza l'inici del `<script>` (línia ~257). Afegeix el bloc de guard i logout com a primeres línies del script, JUST DESPRÉS de la declaració `const API_BASE = ...`:

```js
    // Guard: redirigeix si no és admin
    (async function checkAdminSession() {
      try {
        const res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
        if (!res.ok) { window.location.href = 'login.html'; return; }
        const me = await res.json();
        if (!me.is_admin) { window.location.href = 'index.html'; return; }
        document.getElementById('admin-identity').textContent = me.email;
      } catch (_) {
        window.location.href = 'login.html';
      }
    })();

    async function adminLogout() {
      await fetch(API_BASE + '/api/auth/logout', { method: 'POST', credentials: 'include' });
      window.location.href = 'login.html';
    }
```

#### 7d. Eliminar `getToken()` i actualitzar totes les crides fetch

Localitza i elimina la funció `getToken()`:
```js
    // ADMN-08: el token viu només en memòria (input DOM). No es persisteix mai.
    function getToken() {
      return document.getElementById('token-input').value.trim();
    }
```

Elimina TOTES les línies `const token = getToken();` dins els event listeners. Elimina TOTES les línies `'Authorization': 'Bearer ' + token` dels objectes de headers. Afegeix `credentials: 'include'` a CADA crida `fetch(...)` que no el tingui.

Per trobar les crides a actualitzar:
```bash
grep -n "getToken\|Authorization.*token\|fetch(API_BASE" fp-cercador/frontend/admin.html
```

Verifica cada fetch per assegurar que té `credentials: 'include'` i NO té `Authorization: Bearer`.

Exemple de transformació:
```js
// ABANS:
const token = getToken();
if (!token) { setStatus('Introdueix el token.', 'error'); return; }
refreshBtn.disabled = true;
const res = await fetch(API_BASE + '/api/admin/refresh', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
});

// DESPRÉS:
refreshBtn.disabled = true;
const res = await fetch(API_BASE + '/api/admin/refresh', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
});
```

Si hi ha checks `if (!token) { ... return; }` → eliminar-los (no cal validar el token manualment; el servidor retornarà 401 si la sessió no és vàlida, i el codi `if (res.status === 401) { ... }` ja gestiona aquest cas en cada event listener).

**Nota sobre el pla 036**: Si el pla 036 s'ha aplicat i ha afegit `usersLoadBtn`, `toggleUser`, `deleteUser` amb crides que usen `getToken()` i `Authorization: Bearer`, actualitza-les de la mateixa manera.

**Verificació**:
```bash
grep -c "token-input\|getToken" fp-cercador/frontend/admin.html
```
Ha de retornar `0`.

```bash
grep -c "is_admin\|checkAdminSession" fp-cercador/frontend/admin.html
```
Ha de retornar ≥ 3.

---

### Step 8: Activar el primer usuari admin (acció manual — documentar, no executar)

**ATENCIÓ**: aquest step NO s'automatitza. L'executor ha de documentar-lo a NOTES però NO executar-lo, ja que requereix accés a la BD de producció.

El primer usuari admin s'ha d'activar manualment un cop desplegat:

```bash
# A l'entorn on corre l'app (local o VPS):
python3 -c "
import sys; sys.path.insert(0, 'fp-cercador/backend')
import db
conn = db.get_db()
conn.execute('UPDATE users SET is_admin=1 WHERE email=?', ('EMAIL_DE_LADMIN',))
conn.commit()
print('Files updated:', conn.execute('SELECT changes()').fetchone()[0])
conn.close()
"
```

Substituir `EMAIL_DE_LADMIN` per l'email real de l'admin. Reportar a NOTES que aquest step manual és pendent.

---

### Step 9: Commit

```bash
git add fp-cercador/backend/migrations/00N_add_is_admin.sql \
        fp-cercador/backend/app.py \
        fp-cercador/frontend/admin.html \
        fp-cercador/frontend/login.html
git commit -m "feat(admin): login via sessió + guard admin.html + is_admin a users (pla 037)"
```

## Test plan

No hi ha tests automatitzats de frontend. Per al backend:

Verificació manual (necessita servidor: `cd fp-cercador && python backend/app.py`):

1. `curl -s http://localhost:5001/api/auth/me -b "session=TOKEN_VALID"` → ha de retornar `{"id":...,"email":"...","is_admin":false}` per usuari normal
2. Activar is_admin per a l'usuari de test (Step 8) i repetir → `"is_admin":true`
3. Login amb usuari normal → redirigeix a `index.html`
4. Login amb usuari admin → redirigeix a `admin.html`
5. Accedir a `admin.html` sense sessió → redirigeix a `login.html`
6. Accedir a `admin.html` amb sessió de no-admin → redirigeix a `index.html`
7. `curl -s http://localhost:5001/api/admin/refresh -X POST -H "Authorization: Bearer TOKEN"` → segueix funcionant (Bearer ADMIN_TOKEN continua vàlid)

## Done criteria

- [ ] `ls fp-cercador/backend/migrations/` mostra el nou fitxer `00N_add_is_admin.sql`
- [ ] `grep -c "_check_admin" fp-cercador/backend/app.py` retorna ≥ 6 (definició + totes les crides)
- [ ] `grep -c "_check_auth(request)" fp-cercador/backend/app.py` retorna `0` (cap crida directa queda)
- [ ] `grep -c "is_admin" fp-cercador/backend/app.py` retorna ≥ 5
- [ ] `grep -c "token-input\|getToken" fp-cercador/frontend/admin.html` retorna `0`
- [ ] `grep -c "checkAdminSession\|is_admin" fp-cercador/frontend/admin.html` retorna ≥ 3
- [ ] `grep -c "admin.html" fp-cercador/frontend/login.html` retorna `1`
- [ ] `grep -c "credentials.*include" fp-cercador/frontend/admin.html` retorna ≥ 3 (una per cada crida fetch)
- [ ] `git status` — cap fitxer fora de l'scope modificat
- [ ] `cd fp-cercador && python -m pytest backend/tests/ -q` — no regredeix (≥78 passed)

## STOP conditions

- Si `ALTER TABLE users ADD COLUMN is_admin` falla (columna ja existeix): ATURA — algú l'ha afegida manualment.
- Si el número de migració correcte no es pot determinar (ambigüitat en `ls migrations/`): ATURA i reporta.
- Si `_check_auth` no es troba a app.py: ATURA — pot ser que el fitxer hagi canviat significativament.
- Si la columna `is_active` no existeix a la BD i `_check_admin` la referencia: elimina `AND u.is_active = 1` de la query i documenta-ho a NOTES.
- Si hi ha crides fetch a `admin.html` que no tens clar com transformar (mescla de lògica complexa): ATURA i reporta quines línies.

## Maintenance notes

- **Bearer ADMIN_TOKEN segueix funcionant**: scripts externs (cron, curl) que criden `/api/admin/refresh` o `/api/admin/scheduler` no necessiten canvis. La dualitat Bearer OR sessió és per disseny.
- **Primer admin**: no hi ha UI per crear admins. Si cal afegir un segon admin, cal accés directe a la BD o un nou endpoint admin protegit. Ara per ara és suficient el procés manual.
- **`auth.js` no coneix is_admin**: el widget de login a `index.html` no canvia; segueix mostrant email + botó "Sortir". No hi ha distinció visual entre admin i no-admin al cercador públic — és per disseny.
- **Sessió de 30 dies**: si un admin és degradat (`is_admin=0`), la seva sessió activa ja no passarà el guard de `_check_admin` gràcies a la JOIN. Efecte immediat sense necessitat d'invalidar la sessió manualment.
