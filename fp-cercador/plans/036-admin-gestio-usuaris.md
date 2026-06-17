# Pla 036: Panell admin — llistat d'usuaris, desactivar i donar de baixa

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
> `git diff --stat d9a4728..HEAD -- fp-cercador/backend/app.py fp-cercador/backend/migrations/ fp-cercador/frontend/admin.html`
> Si algun d'aquests fitxers ha canviat des de `d9a4728`, compara els
> excerpts de "Current state" amb el codi viu; en cas de discrepància
> significativa, tracta-ho com a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M (3–5h)
- **Risk**: MED — afecta la lògica d'autenticació (login + sessions); canvis al backend
- **Depends on**: plans 023–026 DONE (sistema de login existent)
- **Category**: direction / feature
- **Planned at**: commit `d9a4728`, 2026-06-17

## Why this matters

L'admin necessita poder veure qui s'ha registrat, bloquejar comptes problemàtics (sense perdre les dades de l'usuari) i eliminar comptes quan calgui. Ara mateix no hi ha cap interfície per gestionar usuaris: l'únic control és directament a la BD. Aquest pla afegeix tres coses: (1) una migració que introdueix la columna `is_active` a `users`, (2) tres endpoints admin protegits per `ADMIN_TOKEN` (`GET /api/admin/users`, `PATCH /api/admin/users/<id>`, `DELETE /api/admin/users/<id>`), i (3) una nova secció a `admin.html` que mostra la taula d'usuaris amb botons per desactivar/activar i eliminar.

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

No hi ha cap columna `is_active`. La migració 002 afegeix `observatory_snapshots` i marca `schema_version = 2`.

### Helper d'autenticació admin (`backend/app.py:147–153`)

```python
def _check_auth(req) -> bool:
    """Verifica el token Bearer amb comparació constant-time (evita timing attacks)."""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    provided = auth[7:]
    return hmac.compare_digest(provided, ADMIN_TOKEN)
```

Tots els endpoints nous han d'usar `_check_auth(request)` i retornar `401` si falla.

### Funció `_get_session_user` (`backend/app.py:551–566`)

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

Aquesta funció s'ha de modificar per invalidar immediatament els usuaris desactivats (sense esperar a que expiri la sessió).

### Queries de login que filtren per `deleted_at IS NULL` (app.py)

Tres queries que cal actualitzar per afegir també `AND is_active = 1`:

- **app.py:653** (login): `"SELECT id, password_hash, verified FROM users WHERE email = ? AND deleted_at IS NULL"`
- **app.py:712** (auth_me): `"SELECT id, email FROM users WHERE id = ? AND deleted_at IS NULL"`
- **app.py:734** (forgot-password): `"SELECT id FROM users WHERE email = ? AND deleted_at IS NULL"`

### Patró d'endpoint admin existent (`backend/app.py:382–389`)

```python
@app.route("/api/admin/scheduler", methods=["GET"])
def scheduler_get():
    """D-08: Retorna l'estat actual del scheduler periòdic."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    cfg = scheduler_service.load_config()
    cfg["next_run"] = scheduler_service.get_next_run_iso()
    return jsonify(cfg), 200
```

Tots els endpoints nous han de seguir exactament aquest patró: `_check_auth` primer, lògica BD a continuació.

### `admin.html` — estructura rellevant

- `getToken()` (línia ~265): retorna el valor de `#token-input`.
- `API_BASE` (línia ~261): `'http://localhost:5001'` en local, `''` en producció.
- `escapeHtml(s)` (línia ~284): escapa `&<>"'` — usar-lo per renderitzar emails.
- `setStatus(html, kind)` / `.status-msg.success` / `.status-msg.error` — patró de missatges d'estat.
- Secció existent final: `<section class="section" id="section-scheduler">` tancada amb `</section>` i llavors `</main>`.

## Scope

**In scope** (únics fitxers a modificar):
- `fp-cercador/backend/migrations/003_add_is_active.sql` (crear nou)
- `fp-cercador/backend/app.py`
- `fp-cercador/frontend/admin.html`

**Out of scope** (NO tocar):
- `backend/tests/` — hi ha 2 failures pre-existents (`test_schema_version_is_1`, `test_run_migrations_idempotent`) que passen de versió 1 → 3 amb la nova migració; no formen part d'aquest pla.
- `backend/db.py` — no requereix canvis.
- Qualsevol altre fitxer frontend (`index.html`, `alertes.html`, etc.).

## Commands you will need

| Propòsit | Comanda | Resultat esperat |
|---|---|---|
| Tests backend | `cd fp-cercador && python -m pytest backend/tests/ -q` | ≥78 passed (les 2 failures de schema_version pre-existents no compten) |
| Verificar migració nova | `grep -c "is_active" fp-cercador/backend/migrations/003_add_is_active.sql` | ≥2 |
| Verificar endpoints nous | `grep -c "admin/users" fp-cercador/backend/app.py` | ≥3 |
| Verificar is_active al login | `grep -c "is_active" fp-cercador/backend/app.py` | ≥6 |
| Verificar secció admin.html | `grep -c "section-users" fp-cercador/frontend/admin.html` | ≥2 |

## Steps

---

### Step 1: Crear la migració 003

Crear el fitxer `fp-cercador/backend/migrations/003_add_is_active.sql` amb el contingut:

```sql
-- Migration 003: Afegeix is_active a users (gestió admin de comptes)

ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;

INSERT INTO schema_version (version) VALUES (3);
```

**Verificació**: `grep -c "is_active" fp-cercador/backend/migrations/003_add_is_active.sql` retorna `2`.

---

### Step 2: Actualitzar `_get_session_user` per bloquejar usuaris inactius

A `backend/app.py`, localitza `_get_session_user` (línia ~551). Substitueix el bloc:

```python
        row = _db.query_one(
            conn,
            "SELECT user_id FROM sessions WHERE token = ? AND expires_at > datetime('now')",
            (token,),
        )
```

Per:

```python
        row = _db.query_one(
            conn,
            """SELECT s.user_id FROM sessions s
               JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > datetime('now')
               AND u.is_active = 1 AND u.deleted_at IS NULL""",
            (token,),
        )
```

Això invalida immediatament les sessions d'usuaris desactivats o eliminats, sense esperar que expiri el cookie.

**Verificació**: `grep -c "u.is_active" fp-cercador/backend/app.py` retorna `1`.

---

### Step 3: Actualitzar les tres queries de login per incloure `is_active = 1`

A `backend/app.py`, modifica les tres queries indicades als excerpts de "Current state":

**app.py línia ~653** (dins `auth_login`):
```python
# ABANS:
"SELECT id, password_hash, verified FROM users WHERE email = ? AND deleted_at IS NULL",
# DESPRÉS:
"SELECT id, password_hash, verified FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1",
```

**app.py línia ~712** (dins `auth_me`):
```python
# ABANS:
"SELECT id, email FROM users WHERE id = ? AND deleted_at IS NULL",
# DESPRÉS:
"SELECT id, email FROM users WHERE id = ? AND deleted_at IS NULL AND is_active = 1",
```

**app.py línia ~734** (dins `auth_forgot_password`):
```python
# ABANS:
conn, "SELECT id FROM users WHERE email = ? AND deleted_at IS NULL", (email,)
# DESPRÉS:
conn, "SELECT id FROM users WHERE email = ? AND deleted_at IS NULL AND is_active = 1", (email,)
```

**Verificació**: `grep -c "is_active = 1" fp-cercador/backend/app.py` retorna `4` (3 queries + 1 la del `_get_session_user` del step 2).

---

### Step 4: Afegir els tres endpoints admin nous a `backend/app.py`

Localitza el bloc de Scraping de centres (línia ~427, cerca `# Scraping de centres`). Afegeix el bloc nou JUST ABANS d'aquest comentari:

```python
# ---------------------------------------------------------------------------
# Gestió d'usuaris (admin)
# ---------------------------------------------------------------------------


@app.route("/api/admin/users", methods=["GET"])
def admin_users_list():
    """Retorna la llista d'usuaris registrats (sense password_hash)."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            "SELECT id, email, verified, is_active, created_at FROM users WHERE deleted_at IS NULL ORDER BY created_at DESC",
        )
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/admin/users/<int:user_id>", methods=["PATCH"])
def admin_users_toggle(user_id):
    """Activa o desactiva un compte d'usuari."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    body = request.get_json(silent=True) or {}
    if "is_active" not in body:
        return jsonify({"error": "Cal el camp is_active (0 o 1)"}), 400
    is_active = 1 if body["is_active"] else 0
    conn = _db.get_db()
    try:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ? AND deleted_at IS NULL",
            (is_active, user_id),
        )
        conn.commit()
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            return jsonify({"error": "Usuari no trobat"}), 404
        return jsonify({"id": user_id, "is_active": is_active}), 200
    finally:
        conn.close()


@app.route("/api/admin/users/<int:user_id>", methods=["DELETE"])
def admin_users_delete(user_id):
    """Elimina permanentment un usuari i totes les seves dades (CASCADE)."""
    if not _check_auth(request):
        return jsonify({"error": "Unauthorized"}), 401
    import db as _db
    conn = _db.get_db()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if conn.execute("SELECT changes()").fetchone()[0] == 0:
            return jsonify({"error": "Usuari no trobat"}), 404
        return jsonify({"deleted": user_id}), 200
    finally:
        conn.close()


```

Notes:
- `GET /api/admin/users` retorna tots els camps excepte `password_hash` i `deleted_at`.
- `PATCH` toggle amb `{"is_active": 0}` o `{"is_active": 1}`. Invalida immediatament sessions gràcies al Step 2.
- `DELETE` és un hard delete; el `ON DELETE CASCADE` de `001_initial_schema.sql` s'encarrega d'esborrar sessions, tokens, lists, list_items i alerts relacionats.
- `conn.execute("SELECT changes()")` detecta si l'UPDATE/DELETE ha afectat alguna fila (retorna 404 si no).

**Verificació**: `grep -c "admin/users" fp-cercador/backend/app.py` retorna `3` (les tres rutes).

---

### Step 5: Afegir la secció "Gestió d'usuaris" a `admin.html`

Localitza el tancament `</main>` (línia ~255, just después de `</section>` del scheduler). Afegeix la nova secció JUST ABANS de `</main>`:

```html
    <!-- ── Secció 4: Gestió d'usuaris ── -->
    <section class="section" id="section-users">
      <h2>Usuaris registrats</h2>
      <p style="color: var(--warm); font-size: 13px; margin-bottom: 12px;">
        Necessita el token introduït a la secció de Refresh manual.
      </p>
      <button id="users-load-btn">Carregar usuaris</button>
      <div id="users-container" style="margin-top: 16px;"></div>
    </section>
```

I, a la secció `<script>`, afegeix el bloc de JS al final (just abans del `</script>` de tancament):

```js
    // ── Gestió d'usuaris ──────────────────────────────────────
    const usersLoadBtn = document.getElementById('users-load-btn');
    const usersContainer = document.getElementById('users-container');

    function renderUsers(users) {
      if (!users.length) {
        usersContainer.innerHTML = '<p style="color:var(--warm);font-size:13px;">Cap usuari registrat.</p>';
        return;
      }
      const rows = users.map(u => `
        <tr id="user-row-${u.id}">
          <td style="font-family:'Geist Mono',monospace;font-size:12px;">${u.id}</td>
          <td>${escapeHtml(u.email)}</td>
          <td>${u.verified ? '✓' : '—'}</td>
          <td id="user-active-${u.id}">${u.is_active ? 'Sí' : 'No'}</td>
          <td style="font-family:'Geist Mono',monospace;font-size:12px;">${escapeHtml(u.created_at || '')}</td>
          <td style="white-space:nowrap;">
            <button onclick="toggleUser(${u.id}, ${u.is_active})"
              style="margin-top:0;padding:6px 12px;font-size:12px;background:${u.is_active ? 'var(--warm)' : 'var(--dark)'};"
              id="user-toggle-${u.id}">${u.is_active ? 'Desactivar' : 'Activar'}</button>
            <button onclick="deleteUser(${u.id}, '${escapeHtml(u.email).replace(/'/g, '')}')"
              style="margin-top:0;margin-left:6px;padding:6px 12px;font-size:12px;background:#dc2626;">
              Eliminar</button>
          </td>
        </tr>`).join('');
      usersContainer.innerHTML = `
        <table class="by-grado-table">
          <thead><tr>
            <th>ID</th><th>Email</th><th>Verificat</th><th>Actiu</th><th>Creat</th><th>Accions</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>`;
    }

    usersLoadBtn.addEventListener('click', async () => {
      const token = getToken();
      if (!token) { usersContainer.innerHTML = '<div class="status-msg error">Introdueix el token.</div>'; return; }
      usersLoadBtn.disabled = true;
      usersContainer.innerHTML = '<span class="spinner"></span> Carregant…';
      try {
        const res = await fetch(API_BASE + '/api/admin/users', {
          headers: { 'Authorization': 'Bearer ' + token },
        });
        if (res.status === 401) { usersContainer.innerHTML = '<div class="status-msg error">Token incorrecte.</div>'; return; }
        if (!res.ok) { usersContainer.innerHTML = '<div class="status-msg error">Error HTTP ' + res.status + '</div>'; return; }
        renderUsers(await res.json());
      } catch (e) {
        usersContainer.innerHTML = '<div class="status-msg error">Error de connexió.</div>';
      } finally {
        usersLoadBtn.disabled = false;
      }
    });

    async function toggleUser(userId, currentActive) {
      const token = getToken();
      if (!token) { alert('Introdueix el token.'); return; }
      const newActive = currentActive ? 0 : 1;
      try {
        const res = await fetch(API_BASE + '/api/admin/users/' + userId, {
          method: 'PATCH',
          headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_active: newActive }),
        });
        if (!res.ok) { alert('Error: HTTP ' + res.status); return; }
        // Actualitzar la fila sense recarregar tota la taula
        document.getElementById('user-active-' + userId).textContent = newActive ? 'Sí' : 'No';
        const btn = document.getElementById('user-toggle-' + userId);
        btn.textContent = newActive ? 'Desactivar' : 'Activar';
        btn.style.background = newActive ? 'var(--warm)' : 'var(--dark)';
        btn.setAttribute('onclick', `toggleUser(${userId}, ${newActive})`);
      } catch (e) {
        alert('Error de connexió.');
      }
    }

    async function deleteUser(userId, email) {
      const token = getToken();
      if (!token) { alert('Introdueix el token.'); return; }
      if (!confirm(`Eliminar permanentment l'usuari "${email}"?\nAquesta acció no es pot desfer.`)) return;
      try {
        const res = await fetch(API_BASE + '/api/admin/users/' + userId, {
          method: 'DELETE',
          headers: { 'Authorization': 'Bearer ' + token },
        });
        if (!res.ok) { alert('Error: HTTP ' + res.status); return; }
        const row = document.getElementById('user-row-' + userId);
        if (row) row.remove();
      } catch (e) {
        alert('Error de connexió.');
      }
    }
```

Notes:
- La taula reutilitza la classe `.by-grado-table` (ja definida al CSS d'`admin.html`).
- `escapeHtml` ja existeix a `admin.html` — no el redefineixis.
- `toggleUser` modifica la fila in-place sense recarregar tota la llista.
- `deleteUser` elimina la fila del DOM quan el backend confirma el `DELETE`.

**Verificació**: `grep -c "section-users" fp-cercador/frontend/admin.html` retorna `2` (l'id al HTML + ús al JS o selector; si no hi ha referència JS retorna 1 — acceptable, comprova que la secció existeix).

---

### Step 6: Commit

```bash
git add fp-cercador/backend/migrations/003_add_is_active.sql \
        fp-cercador/backend/app.py \
        fp-cercador/frontend/admin.html
git commit -m "feat(admin): gestió d'usuaris — llistar, desactivar, eliminar (pla 036)"
```

## Test plan

No hi ha tests automatitzats de frontend. Per al backend, els tests existents a `backend/tests/` no cobreixen els nous endpoints (no és responsabilitat d'aquest pla crear-ne). Els criteris done cobreixen l'existència i la forma correcta del codi.

Verificació manual recomanada (necessita servidor actiu: `cd fp-cercador && python backend/app.py`):
1. `curl -s http://localhost:5001/api/admin/users -H "Authorization: Bearer TOKEN"` → llista JSON d'usuaris
2. `curl -s -X PATCH http://localhost:5001/api/admin/users/1 -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"is_active":0}'` → `{"id":1,"is_active":0}`
3. Intentar login amb l'usuari 1 → `401 Email o contrasenya incorrectes` (o similar)
4. `curl -s -X PATCH ... -d '{"is_active":1}'` → `{"id":1,"is_active":1}` (reactivar)
5. `curl -s -X DELETE http://localhost:5001/api/admin/users/1 -H "Authorization: Bearer TOKEN"` → `{"deleted":1}`
6. Comprovar al admin.html que la taula es carrega, els botons funcionen i el confirm d'eliminació apareix

## Done criteria

- [ ] `grep -c "is_active" fp-cercador/backend/migrations/003_add_is_active.sql` retorna `2`
- [ ] `grep -c "is_active = 1" fp-cercador/backend/app.py` retorna `4` (3 queries login + 1 `_get_session_user`)
- [ ] `grep -c "u.is_active" fp-cercador/backend/app.py` retorna `1` (`_get_session_user`)
- [ ] `grep -c "admin/users" fp-cercador/backend/app.py` retorna `3` (les tres rutes)
- [ ] `grep -c "section-users" fp-cercador/frontend/admin.html` retorna `1` (la secció HTML)
- [ ] `grep -c "toggleUser\|deleteUser\|usersLoadBtn" fp-cercador/frontend/admin.html` retorna `≥3`
- [ ] `git status` — cap fitxer fora de l'scope modificat (3 fitxers: migrations/003, app.py, admin.html)
- [ ] `cd fp-cercador && python -m pytest backend/tests/ -q` — no regredeix (≥78 passed; les 2 failures de schema_version pre-existents seguiran fallant, ara passaran a esperar versió 3 en lloc de 1, però ja fallaven abans)

## STOP conditions

- Si el codi als excerpts de "Current state" no coincideix amb el codi real (drift): ATURA i reporta.
- Si `ALTER TABLE users ADD COLUMN is_active` falla perquè la columna ja existeix: ATURA — pot ser que algú hagi afegit la columna manualment.
- Si `_check_auth` no es troba a app.py o ha canviat de signatura: ATURA.
- Si el tancament `</main>` no es troba just après del bloc scheduler a admin.html: cerca manualment on acaba el `<main>` i insereix la secció just abans, però documenta la desviació.
- Si `conn.execute("SELECT changes()")` no funciona al context de SQLite del projecte: substituir per un `SELECT COUNT(*) FROM users WHERE id = ?` previ i retornar 404 si és 0.

## Maintenance notes

- **`is_active` vs `deleted_at`**: `deleted_at` és un soft-delete que actualment no s'usa per eliminar de veritat (els users existents en producció no en tenen). `is_active = 0` és una suspensió temporal; `DELETE` és l'eliminació real. No barrejar els dos mecanismes.
- **Actualitzar tests pre-existents** (fora d'aquest pla): `test_schema_version_is_1` i `test_run_migrations_idempotent` fallaran ara que la versió és 3. Caldria actualitzar-los a un pla futur de tests.
- **Sessió invalidada immediatament**: gràcies a la JOIN a `_get_session_user`, desactivar un usuari invalida les seves sessions actives sense esperar expiració. Si s'afegeix un cache de sessions en memòria en el futur, cal mantenir aquesta garantia.
- **Sense paginació**: el `GET /api/admin/users` retorna tots els usuaris. Si la base d'usuaris creix molt, caldria afegir paginació. Per ara, no és necessari.
