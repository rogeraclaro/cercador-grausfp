# Pla 038 — F4-A: Backend seguiment de centres (BD + servei + endpoints + hook)

**Escrit contra el commit:** `4c11047`
**Feature:** F4 del roadmap (plans/futures/ROADMAP-FEATURES.md)
**Depèn de:** 022 (centres API), 028 (alertes backend, patró a replicar), 037 (auth via sessió)
**Esforç:** M
**Pla germà:** 039 (frontend — executa DESPRÉS d'aquest)

---

## Context i valor

F4 permet que un usuari registrat segueixi un ensenyament concret i rebi un email quan
el scraping detecta nous centres que l'impartiran. És la versió personalitzada de la
feature de centres (pla 022).

La infraestructura d'alertes de F3 (pla 028) ja existeix i serveix de referència exacta.
Questo pla la replica per als centres: nova taula SQLite, nou servei de dispatch, 4
endpoints CRUD i un hook al pipeline de scraping de centres.

**Fitxers de referència que l'executor ha de llegir abans de començar:**
- `backend/alerts_service.py` — patró de dispatch, unsubscribe token, email body
- `backend/app.py` línies 964–1120 — patró CRUD d'alertes (GET/POST/PATCH/DELETE)
- `backend/app.py` línies 528–565 — hook `admin_refresh_centres` on caldrà inserir la crida
- `backend/migrations/001_initial_schema.sql` — format de migracions
- `backend/tests/test_alerts_service.py` — patró de tests unitaris a replicar

---

## Fitxers en scope

| Acció | Fitxer |
|-------|--------|
| CREAR | `backend/migrations/005_centres_watch.sql` |
| CREAR | `backend/centres_watch_service.py` |
| MODIFICAR | `backend/app.py` |
| CREAR | `backend/tests/test_centres_watch_service.py` |

**Fora de scope (no tocar):** `frontend/`, `backend/alerts_service.py`, qualsevol fitxer de dades.

---

## Pas 1 — Migració de base de dades

Crea `backend/migrations/005_centres_watch.sql`:

```sql
-- Migration 005: F4 — Seguiment de centres per oferta

CREATE TABLE IF NOT EXISTS centres_watch (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    oferta_key      TEXT    NOT NULL,
    oferta_denom    TEXT    NOT NULL,
    provincia_filter TEXT,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_sent_at    TEXT,
    snapshot_json   TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_centres_watch_user_oferta
    ON centres_watch(user_id, oferta_key);

INSERT INTO schema_version (version) VALUES (5);
```

**Notes del model:**
- `oferta_key`: per a Grado C LOE és el `codigo` (p. ex. `"ADGG0408"`); per a D/E és l'`id` numèric com a string (p. ex. `"12664"`). Correspon a les claus de `backend/data/oferta_centres.json`.
- `oferta_denom`: nom llegible (p. ex. `"Gestió Administrativa"`) — es desa a la creació perquè la UI el mostri sense carregar `ofertes.json`.
- `provincia_filter`: string nullable (p. ex. `"BARCELONA"`). Si és NULL l'usuari rep notificació per centres de qualsevol província. El valor ha de coincidir exactament amb el camp `provincia` de `centres.json` (majúscules).
- `snapshot_json`: JSON array de IDs de centre (`["M010002906G", ...]`) que representaven l'estat dels centres en el darrer xec. NULL = sense snapshot previ (s'inicialitza a la creació del watch). El dispatch usa la diferència `current − snapshot` per trobar centres nous.
- `UNIQUE(user_id, oferta_key)`: un usuari no pot seguir la mateixa oferta dues vegades.

**Verificació:**
```bash
cd backend && python3 -c "import db; c = db.init_db(); print(c.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall())"
```
Esperat: la llista de taules ha d'incloure `centres_watch`.

---

## Pas 2 — Servei `centres_watch_service.py`

Crea `backend/centres_watch_service.py`. El patró és idèntic a `alerts_service.py`
però amb la lògica de diff de centres en lloc de diff d'ensenyaments.

```python
"""
centres_watch_service.py — Dispatch de notificacions de nous centres per oferta (F4).

Interfície pública:
  dispatch_centres_watch(base_url)  → int   nombre d'emails enviats
"""
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta

import db as _db
import email_service

logger = logging.getLogger(__name__)

WATCH_MAX_PER_USER = 10
UNSUBSCRIBE_TOKEN_DAYS = 365

_DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "data"))
_OFERTA_CENTRES_PATH = os.path.join(_DATA_DIR, "oferta_centres.json")
_CENTRES_PATH = os.path.join(_DATA_DIR, "centres.json")


def _load_centres_data() -> tuple[dict, dict]:
    """Llegeix oferta_centres.json i centres.json des de disc. Retorna (oferta_centres, centres_index)."""
    with open(_OFERTA_CENTRES_PATH, encoding="utf-8") as f:
        oferta_centres = json.load(f)
    with open(_CENTRES_PATH, encoding="utf-8") as f:
        centres_list = json.load(f)
    centres_index = {c["id"]: c for c in centres_list}
    return oferta_centres, centres_index


def _get_new_centres(oferta_key: str, snapshot_ids: set, oferta_centres: dict, centres_index: dict,
                     provincia_filter: str | None) -> list[dict]:
    """
    Retorna la llista de nous centres per a oferta_key respecte al snapshot.
    Aplica provincia_filter si és no-None.
    """
    current_ids = set(oferta_centres.get(oferta_key, []))
    new_ids = current_ids - snapshot_ids
    new_centres = [centres_index[i] for i in new_ids if i in centres_index]
    if provincia_filter:
        prov_q = provincia_filter.upper()
        new_centres = [c for c in new_centres if (c.get("provincia") or "").upper() == prov_q]
    return new_centres


def _build_email_body(new_centres: list, watch: dict, unsubscribe_token: str, base_url: str) -> str:
    n = len(new_centres)
    lines = []
    for c in new_centres:
        parts = [c["nombre"]]
        if c.get("localitat"):
            parts.append(c["localitat"])
        if c.get("provincia"):
            parts.append(c["provincia"])
        lines.append("  • " + ", ".join(parts))
    bullets = "\n".join(lines)
    prov_note = f" a {watch['provincia_filter']}" if watch.get("provincia_filter") else ""
    unsubscribe_url = (
        f"{base_url}/api/centres-watch/{watch['id']}/unsubscribe?token={unsubscribe_token}"
    )
    return (
        f"Hola,\n\n"
        f"Han aparegut {n} nous centres que impartiran «{watch['oferta_denom']}»{prov_note}:\n\n"
        f"{bullets}\n\n"
        f"Consulta'ls al cercador:\n{base_url}\n\n"
        f"---\n"
        f"Reps aquest email perquè segueixes centres d'aquest ensenyament al Cercador FP España.\n"
        f"Per deixar de rebre'l:\n{unsubscribe_url}\n\n"
        f"Cercador FP España · {base_url}"
    )


def _get_or_create_unsubscribe_token(conn, watch_id: int, user_id: int) -> str:
    row = _db.query_one(
        conn,
        "SELECT token FROM tokens WHERE user_id = ? AND type = 'centres_watch_unsubscribe' "
        "AND token LIKE ?",
        (user_id, f"cw_{watch_id}_%"),
    )
    if row:
        return row["token"].split("_", 2)[2]
    raw_token = secrets.token_hex(32)
    stored_token = f"cw_{watch_id}_{raw_token}"
    expires = (datetime.now(timezone.utc) + timedelta(days=UNSUBSCRIBE_TOKEN_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'centres_watch_unsubscribe', ?)",
        (user_id, stored_token, expires),
    )
    conn.commit()
    return raw_token


def dispatch_centres_watch(base_url: str = "https://grausfp.masellas.info") -> int:
    """
    Llegeix oferta_centres.json (ja actualitzat pel scraping), calcula nous centres
    per a cada watch actiu i envia emails.

    Idempotència: si last_sent_at és d'avui, l'watch s'omet.
    Actualitza snapshot_json a l'estat actual després d'enviar (o si no hi ha nous centres,
    l'actualitza igualment per reflectir l'estat actual).
    Retorna el nombre d'emails enviats.
    """
    try:
        oferta_centres, centres_index = _load_centres_data()
    except FileNotFoundError as exc:
        logger.warning("centres_watch_service: fitxers de centres no disponibles: %s", exc)
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _db.get_db()
    sent = 0
    try:
        watches = _db.query_all(
            conn,
            "SELECT cw.id, cw.user_id, cw.oferta_key, cw.oferta_denom, cw.provincia_filter, "
            "cw.last_sent_at, cw.snapshot_json, u.email "
            "FROM centres_watch cw JOIN users u ON u.id = cw.user_id "
            "WHERE cw.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
        )
        for watch in watches:
            if watch["last_sent_at"] and watch["last_sent_at"][:10] == today:
                continue

            snapshot_ids = set(json.loads(watch["snapshot_json"])) if watch["snapshot_json"] else set()
            watch_dict = dict(watch)

            new_centres = _get_new_centres(
                watch["oferta_key"], snapshot_ids, oferta_centres, centres_index,
                watch["provincia_filter"]
            )

            current_ids = list(oferta_centres.get(watch["oferta_key"], []))
            new_snapshot = json.dumps(current_ids)

            if new_centres:
                unsubscribe_token = _get_or_create_unsubscribe_token(conn, watch["id"], watch["user_id"])
                body = _build_email_body(new_centres, watch_dict, unsubscribe_token, base_url)
                subject = (
                    f"Nous centres FP — {len(new_centres)} nous centres per «{watch['oferta_denom']}» ({today})"
                )
                try:
                    email_service.send_email(watch["email"], subject, body)
                    conn.execute(
                        "UPDATE centres_watch SET last_sent_at = ?, snapshot_json = ? WHERE id = ?",
                        (today, new_snapshot, watch["id"]),
                    )
                    conn.commit()
                    sent += 1
                    logger.info(
                        "centres_watch: watch %s → email enviat a %s (%d nous centres)",
                        watch["id"], watch["email"], len(new_centres)
                    )
                except Exception as exc:
                    logger.error("centres_watch: error enviant email per watch %s: %s", watch["id"], exc)
            else:
                # Actualitza el snapshot sense enviar email
                conn.execute(
                    "UPDATE centres_watch SET snapshot_json = ? WHERE id = ?",
                    (new_snapshot, watch["id"]),
                )
                conn.commit()
    finally:
        conn.close()

    return sent
```

**Verificació:**
```bash
cd backend && python3 -c "import centres_watch_service; print('OK')"
```
Esperat: `OK` sense ImportError.

---

## Pas 3 — Endpoints CRUD a `app.py`

### 3a. Estendre `_needs_auth_cors`

Al fitxer `backend/app.py`, a la funció `_needs_auth_cors` (línia ~107), la línia actual és:

```python
return path.startswith("/api/auth/") or path.startswith("/api/favorites") or path.startswith("/api/alerts")
```

Substituïu-la per:

```python
return (path.startswith("/api/auth/") or path.startswith("/api/favorites")
        or path.startswith("/api/alerts") or path.startswith("/api/centres-watch"))
```

### 3b. Afegir constant de límit

Reutilitzar `ALERTS_MAX_PER_USER = 10` ja definit no és possible (és a `alerts_service.py`).
Afegiu al bloc de constants de `app.py` (a prop de `VALID_GRADOS`, línia ~967):

```python
CENTRES_WATCH_MAX_PER_USER = 10
```

### 3c. Afegir els 4 endpoints

Afegiu a continuació del bloc d'alertes (després de la ruta `/api/alerts/<int:alert_id>/unsubscribe`,
al voltant de la línia 1120). El patró és idèntic al del bloc d'alertes:

```python
# ---------------------------------------------------------------------------
# Seguiment de centres — /api/centres-watch  (F4)
# ---------------------------------------------------------------------------


@app.route("/api/centres-watch", methods=["GET"])
def centres_watch_get():
    """Retorna tots els seguiments (actius i inactius) de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, last_sent_at "
            "FROM centres_watch WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/centres-watch", methods=["POST"])
def centres_watch_create():
    """
    Crea un seguiment.
    Body: {"oferta_key": "ADGG0408", "oferta_denom": "Gestió Administrativa",
           "provincia_filter": "BARCELONA"}   (provincia_filter és opcional)
    """
    import db as _db
    import json as _json
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    oferta_key = data.get("oferta_key", "").strip()
    oferta_denom = data.get("oferta_denom", "").strip()
    provincia_filter = data.get("provincia_filter") or None
    if provincia_filter:
        provincia_filter = provincia_filter.strip().upper() or None
    if not oferta_key or not oferta_denom:
        return jsonify({"error": "oferta_key i oferta_denom són obligatoris"}), 400

    # Snapshot inicial: centres actuals per a aquesta oferta
    try:
        _load_centres_data()
        initial_ids = list(_oferta_centres.get(oferta_key, []))
    except Exception:
        initial_ids = []
    snapshot_json = _json.dumps(initial_ids)

    conn = _db.get_db()
    try:
        count = _db.query_one(
            conn,
            "SELECT COUNT(*) FROM centres_watch WHERE user_id = ? AND active = 1",
            (user_id,),
        )[0]
        if count >= CENTRES_WATCH_MAX_PER_USER:
            return jsonify({"error": "Màxim 10 seguiments actius per usuari"}), 429
        try:
            conn.execute(
                "INSERT INTO centres_watch (user_id, oferta_key, oferta_denom, provincia_filter, snapshot_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, oferta_key, oferta_denom, provincia_filter, snapshot_json),
            )
            conn.commit()
        except Exception as exc:
            if "UNIQUE" in str(exc):
                return jsonify({"error": "Ja segueixes aquest ensenyament"}), 409
            raise
        watch_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        row = _db.query_one(
            conn,
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, last_sent_at "
            "FROM centres_watch WHERE id = ?",
            (watch_id,),
        )
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.route("/api/centres-watch/<int:watch_id>", methods=["DELETE"])
def centres_watch_delete(watch_id):
    """Elimina un seguiment de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM centres_watch WHERE id = ? AND user_id = ?", (watch_id, user_id)
        )
        if not row:
            return jsonify({"error": "Seguiment no trobat"}), 404
        conn.execute("DELETE FROM centres_watch WHERE id = ?", (watch_id,))
        conn.execute("DELETE FROM tokens WHERE token LIKE ?", (f"cw_{watch_id}_%",))
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.route("/api/centres-watch/<int:watch_id>", methods=["PATCH"])
def centres_watch_toggle(watch_id):
    """Activa o desactiva un seguiment. Body: {"active": true/false}."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    if "active" not in data:
        return jsonify({"error": "Cal el camp active"}), 400
    active = 1 if data["active"] else 0
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM centres_watch WHERE id = ? AND user_id = ?", (watch_id, user_id)
        )
        if not row:
            return jsonify({"error": "Seguiment no trobat"}), 404
        conn.execute("UPDATE centres_watch SET active = ? WHERE id = ?", (active, watch_id))
        conn.commit()
        updated = _db.query_one(
            conn,
            "SELECT id, oferta_key, oferta_denom, provincia_filter, active, created_at, last_sent_at "
            "FROM centres_watch WHERE id = ?",
            (watch_id,),
        )
        return jsonify(dict(updated)), 200
    finally:
        conn.close()


@app.route("/api/centres-watch/<int:watch_id>/unsubscribe", methods=["GET"])
def centres_watch_unsubscribe(watch_id):
    """Baixa sense login via token a l'URL de l'email."""
    import db as _db
    token_param = request.args.get("token", "")
    if not token_param:
        return jsonify({"error": "Token requerit"}), 400
    stored_token = f"cw_{watch_id}_{token_param}"
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT user_id FROM tokens WHERE token = ? AND type = 'centres_watch_unsubscribe' "
            "AND expires_at > datetime('now')",
            (stored_token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 404
        conn.execute(
            "UPDATE centres_watch SET active = 0 WHERE id = ? AND user_id = ?",
            (watch_id, row["user_id"]),
        )
        conn.commit()
        return jsonify({"ok": True, "message": "Seguiment desactivat correctament"}), 200
    finally:
        conn.close()
```

**Verificació:**
```bash
cd backend && python3 -c "
from app import app
with app.test_client() as c:
    r = c.get('/api/centres-watch')
    print(r.status_code)  # esperat: 401
"
```

---

## Pas 4 — Hook de dispatch a `admin_refresh_centres`

A `backend/app.py`, dins la funció `_run()` de `admin_refresh_centres` (línia ~542),
el bloc actual és:

```python
def _run():
    global _centres_index, _oferta_centres
    try:
        build_centres_data()
        # Recarrega la cache en memòria perquè les noves dades siguin visibles
        _centres_index = None
        _oferta_centres = None
        _load_centres_data()
        _centres_scrape_state.update(
            status="done",
            finished_at=datetime.now(timezone.utc).isoformat(),
            total_centres=len(_centres_index),
            total_ofertes=len(_oferta_centres),
            error=None,
        )
    except Exception as exc:
        ...
    finally:
        _centres_scrape_lock.release()
```

Afegiu la crida al dispatch **just després de `_centres_scrape_state.update(...)`**:

```python
        _centres_scrape_state.update(
            status="done",
            finished_at=datetime.now(timezone.utc).isoformat(),
            total_centres=len(_centres_index),
            total_ofertes=len(_oferta_centres),
            error=None,
        )
        try:
            import centres_watch_service
            centres_watch_service.dispatch_centres_watch(base_url=BASE_URL)
        except Exception as exc_cw:
            logger.error("Could not dispatch centres watch notifications: %s", exc_cw)
```

**Verificació:**
```bash
cd backend && python3 -c "
from app import app
with app.test_client() as c:
    r = c.get('/health')
    print(r.status_code)  # 200 — confirma que l'app arrenca sense errors
"
```

---

## Pas 5 — Tests unitaris

Crea `backend/tests/test_centres_watch_service.py`. Patró: igual que `test_alerts_service.py`.

```python
"""
test_centres_watch_service.py — Tests unitaris de centres_watch_service (F4).
"""
import json
import pytest
import centres_watch_service


OFERTA_CENTRES = {
    "ADGG0408": ["M010001", "M010002", "M010003"],
    "12664": ["M020001"],
}

CENTRES_INDEX = {
    "M010001": {"id": "M010001", "nombre": "IES A", "provincia": "BARCELONA", "localitat": "BCN"},
    "M010002": {"id": "M010002", "nombre": "IES B", "provincia": "GIRONA", "localitat": "GIR"},
    "M010003": {"id": "M010003", "nombre": "IES C", "provincia": "BARCELONA", "localitat": "BCN"},
    "M020001": {"id": "M020001", "nombre": "IES D", "provincia": "MADRID", "localitat": "MAD"},
}


def test_get_new_centres_all():
    snapshot = {"M010001"}  # ja existia
    result = centres_watch_service._get_new_centres(
        "ADGG0408", snapshot, OFERTA_CENTRES, CENTRES_INDEX, None
    )
    ids = {c["id"] for c in result}
    assert ids == {"M010002", "M010003"}


def test_get_new_centres_provincia_filter():
    snapshot = {"M010001"}
    result = centres_watch_service._get_new_centres(
        "ADGG0408", snapshot, OFERTA_CENTRES, CENTRES_INDEX, "BARCELONA"
    )
    assert len(result) == 1
    assert result[0]["id"] == "M010003"


def test_get_new_centres_empty_snapshot():
    snapshot = set()
    result = centres_watch_service._get_new_centres(
        "ADGG0408", set(), OFERTA_CENTRES, CENTRES_INDEX, None
    )
    assert len(result) == 3


def test_get_new_centres_no_new():
    snapshot = {"M010001", "M010002", "M010003"}
    result = centres_watch_service._get_new_centres(
        "ADGG0408", snapshot, OFERTA_CENTRES, CENTRES_INDEX, None
    )
    assert result == []


def test_get_new_centres_unknown_key():
    result = centres_watch_service._get_new_centres(
        "ZZZZ9999", set(), OFERTA_CENTRES, CENTRES_INDEX, None
    )
    assert result == []


def test_build_email_body_contains_centre_name():
    watch = {"id": 1, "oferta_denom": "Gestió Administrativa", "provincia_filter": None}
    body = centres_watch_service._build_email_body(
        [CENTRES_INDEX["M010001"]], watch, "tok123", "https://example.com"
    )
    assert "IES A" in body
    assert "Gestió Administrativa" in body
    assert "unsubscribe" in body.lower() or "cw_1_tok123" in body


def test_build_email_body_with_provincia():
    watch = {"id": 2, "oferta_denom": "Ciberseguretat", "provincia_filter": "BARCELONA"}
    body = centres_watch_service._build_email_body(
        [CENTRES_INDEX["M010003"]], watch, "tok456", "https://example.com"
    )
    assert "BARCELONA" in body
```

**Verificació:**
```bash
cd backend && python3 -m pytest tests/test_centres_watch_service.py -v
```
Esperat: 7 tests PASSED.

---

## Verificació final del pla

```bash
cd backend && python3 -m pytest tests/ -v 2>&1 | tail -20
```
Esperat: tots els tests existents segueixen passant + els 7 nous.

```bash
cd backend && python3 -c "
from app import app
with app.test_client() as c:
    print(c.get('/health').status_code)         # 200
    print(c.get('/api/centres-watch').status_code) # 401
    print(c.get('/api/alerts').status_code)       # 401
"
```
Esperat: `200 401 401`

---

## Criteris de DONE

- [ ] `backend/migrations/005_centres_watch.sql` creat i la BD s'actualitza amb `init_db()`
- [ ] `backend/centres_watch_service.py` existent i importable sense errors
- [ ] 5 endpoints nous a `app.py` (GET/POST/PATCH/DELETE `/api/centres-watch`, GET `/api/centres-watch/<id>/unsubscribe`)
- [ ] CORS estès a `/api/centres-watch`
- [ ] Hook de dispatch inserit a `_run()` dins `admin_refresh_centres`
- [ ] 7 tests unitaris nous passant
- [ ] Tots els tests existents segueixen verts

## STOP conditions

- Si trobes que `oferta_centres.json` no existeix al servidor (arrencada en fred sense scraping), el dispatch retorna 0 i loga WARNING — comportament ja cobert pel `try/except FileNotFoundError`.
- Si la taula `centres_watch` ja existeix a la BD (migració anterior accidental), la migració usa `CREATE TABLE IF NOT EXISTS` — és idempotent.
- Si `UNIQUE` constraint viola en el POST, retorna 409 — no és un error del pla.

## Nota de manteniment

- `dispatch_centres_watch` es crida des del thread de scraping de centres (background). Si el scraping de centres s'integra al scheduler periòdic en el futur, caldrà afegir-hi la crida igual que `alerts_service.dispatch_alerts` ja està al `_scheduled_refresh` de `scheduler_service.py`.
- El camp `snapshot_json` creix amb el nombre de centres per oferta (fins ~200 IDs per oferta). Amb 100 usuaris × 10 watches = 1.000 files, el volum és negligible per SQLite.
