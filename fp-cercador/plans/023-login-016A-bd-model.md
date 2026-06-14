# Plan 023 — Login F1-A: Base de dades i model de dades

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada
> comanda de verificació i confirma el resultat esperat abans de passar al
> pas següent. Si es dona qualsevol condició de la secció "STOP conditions",
> atura't i informa — no improvisis. En acabar, actualitza la fila d'aquest
> pla a `plans/README.md`.
>
> **Context previ**: Llegeix `plans/outputs/spike-login.md` ABANS de
> començar. Conté l'esquema SQLite complet (Step 2) i les decisions de
> disseny que aquest pla implementa. No repeteixis la investigació.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> ```bash
> python3 -c "import sqlite3; print(sqlite3.sqlite_version)"
> python3 -c "from werkzeug.security import generate_password_hash; print('werkzeug OK')"
> ls backend/db.py 2>/dev/null && echo "db.py JA EXISTEIX" || echo "db.py no existeix (esperat)"
> ls backend/migrations/ 2>/dev/null && echo "migrations/ JA EXISTEIX" || echo "migrations/ no existeix (esperat)"
> ls backend/data/fp_cercador.db 2>/dev/null && echo "DB JA EXISTEIX" || echo "DB no existeix (esperat)"
> ```
> Cap dels tres darrers hauria d'existir. Si existeixen, atura't.

## Status

- **Priority**: P2
- **Effort**: S (2–4h)
- **Risk**: LOW (fitxers nous; cap canvi als fitxers existents de backend/)
- **Depends on**: 016 (spike DONE), decisions resoltes el 2026-06-15
- **Category**: feature (fonament F1)
- **Planned at**: 2026-06-15

## Why this matters

El spike 016 va dissenyar l'esquema SQLite que sustenta F1 (login), F2
(favorits) i F3 (alertes). Sense aquest pla no hi ha base de dades, i els
plans de construcció que vénen (016-B backend auth, 016-C frontend) no
tenen on persistir l'estat dels usuaris.

Aquest pla és purament aditiu: crea fitxers nous (`db.py`, `migrations/`)
sense tocar cap fitxer existent de producció.

## Current state (fets verificats)

- `backend/app.py` — Flask sense BD; auth única via `ADMIN_TOKEN` Bearer
- `backend/data/` — fitxers JSON; directori ja ignorat per `.gitignore` (pla 010)
- `sqlite3` i `werkzeug.security` disponibles sense dependències noves
- Cap fitxer `db.py`, `migrations/` ni `fp_cercador.db` existent

## Scope

**In scope**:
- `backend/migrations/001_initial_schema.sql` — DDL complet de les 8 taules
- `backend/db.py` — connexió, `init_db()`, `run_migrations()`, helpers
- `backend/tests/test_db.py` — tests unitaris (BD en memòria `:memory:`)
- Actualitzar `backend/.env.example` amb `DB_PATH` (opcional, per a override)

**Out of scope**: cap canvi a `app.py`, `frontend/`, ni `deploy/`.

## Steps

### Step 1 — Crear `backend/migrations/001_initial_schema.sql`

DDL exacte de l'Step 2 del spike. Inclou les 8 taules:
`users`, `sessions`, `tokens`, `login_attempts`, `lists`, `list_items`,
`alerts`, `schema_version`.

Afegir al final del fitxer:
```sql
INSERT INTO schema_version (version) VALUES (1);
```

**Verificació**:
```bash
sqlite3 /tmp/test_schema.db < backend/migrations/001_initial_schema.sql
sqlite3 /tmp/test_schema.db ".tables"
# Ha de mostrar les 8 taules
rm /tmp/test_schema.db
```

### Step 2 — Crear `backend/db.py`

Mòdul amb 4 responsabilitats:

**2a. Connexió**
```python
import os, sqlite3

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "fp_cercador.db")
)

def get_db():
    """Retorna una connexió SQLite amb row_factory=sqlite3.Row."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
```

`WAL` permet lectures concurrents (gunicorn amb threads). `foreign_keys=ON`
fa complir els `ON DELETE CASCADE` de l'esquema.

**2b. `init_db(db_path=None)`**
- Accepta `db_path` opcional (per a tests amb `:memory:`)
- Obre connexió, aplica `run_migrations()`, tanca

**2c. `run_migrations(conn)`**
- Llegeix la versió actual de `schema_version` (0 si la taula no existeix)
- Aplica en ordre tots els fitxers `migrations/NNN_*.sql` amb versió > actual
- Usa `conn.executescript()` per aplicar cada fitxer com a transacció atòmica

**2d. Helper `query_one(conn, sql, params=())`** i **`query_all(conn, sql, params=())`**
- Wraps mínims per no repetir `.fetchone()` / `.fetchall()` per tot el codi

**Verificació**:
```bash
cd backend && python3 -c "
import db
db.init_db()
conn = db.get_db()
tables = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()
print([t['name'] for t in tables])
conn.close()
"
# Ha de mostrar les 8 taules
```

### Step 3 — Crear `backend/tests/test_db.py`

Tests amb `pytest` i BD en memòria (`:memory:`) — no toquen mai
`fp_cercador.db` de producció ni cap fitxer de `backend/data/`.

**Tests mínims**:

```python
import sqlite3, pytest
import db  # backend/db.py

@pytest.fixture
def mem_db(tmp_path):
    """BD SQLite en memòria amb l'esquema aplicat."""
    conn = db.init_db(db_path=":memory:")
    yield conn
    conn.close()

def test_schema_creates_all_tables(mem_db):
    tables = {r[0] for r in mem_db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    expected = {
        "users", "sessions", "tokens", "login_attempts",
        "lists", "list_items", "alerts", "schema_version"
    }
    assert expected == tables

def test_schema_version_is_1(mem_db):
    v = mem_db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert v == 1

def test_foreign_keys_cascade(mem_db):
    """Esborrar un user ha d'esborrar les seves sessions en cascada."""
    mem_db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("test@test.com", "hash")
    )
    uid = mem_db.execute("SELECT id FROM users WHERE email='test@test.com'").fetchone()[0]
    mem_db.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (uid, "tok123", "2099-01-01")
    )
    mem_db.execute("DELETE FROM users WHERE id=?", (uid,))
    mem_db.commit()
    count = mem_db.execute("SELECT COUNT(*) FROM sessions WHERE user_id=?", (uid,)).fetchone()[0]
    assert count == 0

def test_run_migrations_idempotent(mem_db):
    """Cridar run_migrations dues vegades no duplica schema_version."""
    db.run_migrations(mem_db)
    count = mem_db.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0]
    assert count == 1
```

**Nota sobre la fixture**: `init_db(db_path=":memory:")` ha de retornar la
connexió (no tancar-la) perquè la fixture pugui passar-la als tests.
Adaptar la signatura de `init_db` acordament: si `db_path` és `:memory:`,
retorna la connexió en lloc de tancar-la.

**Verificació**:
```bash
cd backend && python3 -m pytest tests/test_db.py -v
# Ha de passar: 4 tests OK
```

### Step 4 — Actualitzar `.env.example`

Afegir al final (sense canviar res existent):
```
# Base de dades SQLite (opcional — per defecte: backend/data/fp_cercador.db)
# DB_PATH=/ruta/alternativa/fp_cercador.db
```

### Step 5 — Verificació final

```bash
# 1. Tests passen
cd backend && python3 -m pytest tests/test_db.py -v

# 2. BD de producció creada correctament
python3 -c "import db; db.init_db()"
sqlite3 backend/data/fp_cercador.db ".tables"

# 3. Fitxers nous; cap fitxer existent modificat
cd .. && git status
# Ha de mostrar NOMÉS fitxers nous sota backend/ i .env.example modificat
# Cap modificació a app.py, frontend/, etc.

# 4. La BD no va al repo
grep fp_cercador.db .gitignore
# Ha de trobar la línia (backend/data/ ja és ignorat per pla 010)
```

## Done criteria

- [ ] `backend/migrations/001_initial_schema.sql` existeix amb les 8 taules
- [ ] `backend/db.py` existeix amb `get_db()`, `init_db()`, `run_migrations()`, helpers
- [ ] `backend/data/fp_cercador.db` es crea en executar `init_db()` i conté les 8 taules
- [ ] 4 tests passen a `tests/test_db.py` (inclòs el cascade i l'idempotència)
- [ ] `git status` no mostra cap fitxer existent modificat fora de `.env.example`
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- `backend/db.py` o `backend/migrations/` ja existeixen → atura't i informa
- Els tests fallen per causes que no són l'esquema (imports trencats, pytest
  no troba el mòdul) → revisar el `PYTHONPATH`; no improvisar canvis a
  l'estructura de tests existent
- Temptació d'afegir lògica d'aplicació a `db.py` (endpoints, hashing de
  contrasenyes, etc.) → STOP: això va al pla 016-B

## Maintenance notes

- `db.py` és la capa de connexió pura: res de lògica de negoci aquí
- Quan es construeixi F3, la migració `002_add_alerts_index.sql` o similar
  afegirà índexs addicionals a `alerts` sense modificar `001_`
- La BD viu a `backend/data/` (ignorat per git); el VPS necessitarà cron de
  backup (documentar al pla de desplegament 016-D)
