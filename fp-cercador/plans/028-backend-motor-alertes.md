# Plan 028: Backend motor d'alertes F3

> **Generat per /improve el 2026-06-16, contra el commit `2384666`.**
> **Executor**: llegeix aquest fitxer sencer abans de tocar cap codi.
> Cap STOP condition activa; el pla és executable directament.

## Status

- **Priority**: P1 (F3 és la killer feature del login)
- **Effort**: M
- **Risk**: MEDIUM (modifica la pipeline de dades i l'scheduler; tests cobreixen els casos crítics)
- **Depends on**: 023–027 DONE, 017 DONE (`plans/outputs/spike-alertes.md`)
- **Category**: feature
- **Planned at**: commit `2384666`, 2026-06-16

---

## Why this matters

F3 (alertes personalitzades) permet a un usuari registrat rebre un email quan apareixen nous ensenyaments FP que coincideixen amb un filtre ("Grado D · Informàtica", "qualsevol Grado A", "textos que continguin ciberseguretat"). És la raó de pes per registrar-se i tornar. La taula `alerts` ja existeix a la BD (migració 001). L'infraestructura d'email existeix (`email_service.send_email`). Aquest pla construeix el motor de matching i els endpoints CRUD.

---

## Arquitectura del canvi

```
pipeline.py          → afegeix meta_by_grado al resultat
history.py           → guarda meta_by_grado al snapshot; new_by_grado_meta als changes
alerts_service.py    → NOU: match_alert, dispatch_alerts, build_alert_description
app.py               → 5 endpoints nous + dispatch call + CORS per /api/alerts*
scheduler_service.py → dispatch call post-refresh
tests/test_alerts_service.py → NOU: 5 tests unitaris
```

---

## Current state (llegeix per verificar que no ha canviat)

### `backend/scrapers/pipeline.py` línies 173–189

```python
families = sorted({r['familia'] for r in all_records if r['familia'] != 'Desconeguda'})
denominacions = sorted({r['denominacion'] for r in all_records if r.get('denominacion')})
denominacions_by_grado = {
    g: sorted({r['denominacion'] for r in all_records if r.get('grado') == g and r.get('denominacion')})
    for g in ['A', 'B', 'C', 'D', 'E']
}

return {
    "total": len(all_records),
    "by_grado": by_grado,
    "families": families,
    "denominacions": denominacions,
    "denominacions_by_grado": denominacions_by_grado,
    "errors": [],
    "unknown_families": sorted(_unknown),
    "duration_seconds": round(time.time() - start, 2),
}
```

### `backend/history.py` funció `append()` línies 97–117

```python
def append(result: dict) -> None:
    full = {
        "total": result.get("total"),
        "by_grado": result.get("by_grado"),
        "families": result.get("families", []),
        "denominacions": result.get("denominacions", []),
        "denominacions_by_grado": result.get("denominacions_by_grado", {}),
    }
    prev = _load_json(SNAPSHOT_PATH)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "total": result.get("total"),
        "by_grado": result.get("by_grado"),
        "unknown_families": result.get("unknown_families", []),
        "duration_seconds": result.get("duration_seconds"),
        "changes": compute_changes(full, prev) if prev else None,
    }
    history = _load_json(HISTORY_PATH) or []
    history.insert(0, entry)
    history = history[:HISTORY_MAX]
    _write_atomic(history, HISTORY_PATH)
    _write_atomic(full, SNAPSHOT_PATH)
```

### `backend/history.py` funció `compute_changes()` línies 45–87

(Retorna `new_by_grado`, `removed_by_grado`, etc. amb llistes de strings. No té `new_by_grado_meta`.)

### `backend/app.py` funció `_needs_auth_cors` i `admin_refresh` (rellevant)

```python
def _needs_auth_cors(path):
    return path.startswith("/api/auth/") or path.startswith("/api/favorites")
```

En `admin_refresh`, dins de `_run()`:
```python
try:
    history.append(result)
except Exception as exc_h:
    logger.error("Could not write refresh history: %s", exc_h)
try:
    notifier.notify_if_new()
except Exception as exc_n:
    logger.error("Could not send Brevo notification: %s", exc_n)
```

### `backend/scheduler_service.py` funció `_scheduled_refresh()` línies 110–127

```python
try:
    history.append(result)
except Exception as exc_h:
    logger.error("Could not write refresh history: %s", exc_h)
```
(Just after `history.append` és on cal afegir el dispatch d'alertes.)

### `backend/migrations/001_initial_schema.sql` taula `alerts`

```sql
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filter_json  TEXT    NOT NULL,
    active       INTEGER NOT NULL DEFAULT 1,
    created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
    last_sent_at TEXT
);
```

### Estructura d'un registre a `ofertes.json`

```json
{"codigo": "ADG_A_3001_01", "denominacion": "Preparación de los equipos",
 "familia": "Administración y Gestión", "nivel": 1, "plan_antiguo": false,
 "observaciones": "", "ficha_id": 5793, "grado": "A", "id": 1}
```

---

## In scope

- `backend/scrapers/pipeline.py` — afegir `meta_by_grado` al resultat
- `backend/history.py` — guardar `meta_by_grado` al snapshot + `new_by_grado_meta` als changes
- `backend/alerts_service.py` — fitxer NOU
- `backend/app.py` — 5 endpoints + CORS + 1 import + dispatch call
- `backend/scheduler_service.py` — dispatch call
- `backend/tests/test_alerts_service.py` — fitxer NOU

## Out of scope

- Frontend (pla 029)
- `plans/README.md` (el reviewer ho fa)
- Qualsevol fitxer no llistat aquí

---

## Steps

### Step 1: Afegir `meta_by_grado` a `pipeline.py`

**Fitxer**: `backend/scrapers/pipeline.py`

Just BEFORE el `return` final (línies 180–189), afegeix el càlcul de `meta_by_grado`:

```python
meta_by_grado = {
    g: [
        {"denominacio": r["denominacion"], "familia": r["familia"], "nivel": r["nivel"]}
        for r in all_records
        if r.get("grado") == g and r.get("denominacion")
    ]
    for g in ["A", "B", "C", "D", "E"]
}

return {
    "total": len(all_records),
    "by_grado": by_grado,
    "families": families,
    "denominacions": denominacions,
    "denominacions_by_grado": denominacions_by_grado,
    "meta_by_grado": meta_by_grado,           # NOU — per a F3 alertes
    "errors": [],
    "unknown_families": sorted(_unknown),
    "duration_seconds": round(time.time() - start, 2),
}
```

**No tocar cap altra línia de pipeline.py.**

**Verificació Step 1:**
```bash
cd backend && python3 -c "
from scrapers import pipeline
import json
# No fem run() real (triga minuts); verifiquem que la funció retorna meta_by_grado
# llegint l'estructura del codi
import inspect
src = inspect.getsource(pipeline.run)
assert 'meta_by_grado' in src, 'meta_by_grado no trobat al codi de pipeline.run'
print('OK: meta_by_grado present a pipeline.run')
"
```

---

### Step 2: Actualitzar `history.py`

**Fitxer**: `backend/history.py`

**2a. Actualitzar `append()`** — guardar `meta_by_grado` al snapshot:

```python
def append(result: dict) -> None:
    full = {
        "total": result.get("total"),
        "by_grado": result.get("by_grado"),
        "families": result.get("families", []),
        "denominacions": result.get("denominacions", []),
        "denominacions_by_grado": result.get("denominacions_by_grado", {}),
        "meta_by_grado": result.get("meta_by_grado", {}),     # NOU
    }
    # ... resta igual ...
```

**2b. Actualitzar `compute_changes()`** — afegir `new_by_grado_meta` al resultat. Afegir al FINAL de `compute_changes`, just BEFORE `return`:

```python
    # Metadades enriquides per a F3 (alertes personalitzades)
    curr_meta = curr.get("meta_by_grado") or {}
    prev_meta = prev.get("meta_by_grado") or {}
    new_by_grado_meta = {}
    for g, items in curr_meta.items():
        curr_by_d = {item["denominacio"]: item for item in (items or [])}
        prev_d_set = {item["denominacio"] for item in (prev_meta.get(g) or [])}
        added = [curr_by_d[d] for d in sorted(curr_by_d) if d not in prev_d_set]
        if added:
            new_by_grado_meta[g] = added

    return {
        "new_families": new_families,
        "removed_families": removed_families,
        "grado_deltas": grado_deltas,
        "total_delta": total_delta,
        "new_denominacions": new_denominacions,
        "removed_denominacions": removed_denominacions,
        "new_by_grado": new_by_grado,
        "removed_by_grado": removed_by_grado,
        "has_changes": bool(new_families or removed_families or grado_deltas or new_denominacions or removed_denominacions),
        "new_by_grado_meta": new_by_grado_meta,               # NOU
    }
```

**ATENCIÓ**: El `return` de `compute_changes` és la ÚNICA sentència `return` a la funció. Substitueix-lo sencer per la versió anterior que inclou `new_by_grado_meta`.

**Verificació Step 2:**
```bash
cd backend && python3 -m pytest tests/test_history.py -v
```
Resultat esperat: tots els tests passen. Si en fallen, és perquè alguna cosa ha canviat al patró existent — STOP i informa.

---

### Step 3: Crear `backend/alerts_service.py`

**Fitxer NOU**: `backend/alerts_service.py`

```python
"""
alerts_service.py — Motor de matching i dispatching d'alertes personalitzades (F3).

Interfície pública:
  match_alert(filter_dict, changes)         → list[dict]  — items matchejats
  build_alert_description(filter_dict)      → str         — text llegible del filtre
  dispatch_alerts(result, conn=None)        → int         — nombre d'emails enviats
"""
import json
import logging
import unicodedata
from datetime import datetime, timezone, timedelta
import secrets

import db as _db
import email_service

logger = logging.getLogger(__name__)

ALERTS_MAX_PER_USER = 10
UNSUBSCRIBE_TOKEN_DAYS = 365


def _normalize(text: str) -> str:
    """NFD + elimina diacrítics + lowercase. Idèntic a index.html del frontend."""
    return (
        unicodedata.normalize("NFD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


def match_alert(filter_dict: dict, changes: dict) -> list:
    """
    Retorna la llista de dicts {denominacio, familia, nivel, grado} que encaixen
    amb el filtre. Utilitza `new_by_grado_meta` dels changes (Step 2 de history.py).

    Args:
        filter_dict: El filter_json deserialitzat.
        changes: El retorn de history.compute_changes() (ha de tenir new_by_grado_meta).

    Returns:
        Llista de dicts matchejats. Buida si cap match o si changes és None.
    """
    if not changes:
        return []

    new_by_grado_meta = changes.get("new_by_grado_meta") or {}
    if not new_by_grado_meta:
        return []

    grado_filter = filter_dict.get("grado")
    familia_filter = filter_dict.get("familia")
    nivel_filter = filter_dict.get("nivel")
    texto_filter = filter_dict.get("texto")

    # 1. Candidats inicials per grado
    if grado_filter:
        grado_items = new_by_grado_meta.get(grado_filter, [])
        candidates = [dict(item, grado=grado_filter) for item in grado_items]
    else:
        candidates = []
        for g, items in new_by_grado_meta.items():
            for item in items:
                candidates.append(dict(item, grado=g))

    if not candidates:
        return []

    # 2. Filtre per família (case-insensitive exact)
    if familia_filter:
        fam_q = familia_filter.lower()
        candidates = [c for c in candidates if (c.get("familia") or "").lower() == fam_q]

    # 3. Filtre per nivel (cast a int si cal per comparació)
    if nivel_filter is not None:
        try:
            niv_q = int(nivel_filter)
        except (TypeError, ValueError):
            niv_q = nivel_filter
        candidates = [c for c in candidates if c.get("nivel") == niv_q]

    # 4. Filtre per texto (substring NFD+lower)
    if texto_filter:
        q = _normalize(texto_filter)
        candidates = [c for c in candidates if q in _normalize(c.get("denominacio") or "")]

    return candidates


def build_alert_description(filter_dict: dict) -> str:
    """Genera una descripció llegible del filtre per a l'email i la UI."""
    parts = []
    if filter_dict.get("grado"):
        parts.append(f"Grado {filter_dict['grado']}")
    if filter_dict.get("familia"):
        parts.append(filter_dict["familia"])
    if filter_dict.get("nivel") is not None:
        parts.append(f"Nivell {filter_dict['nivel']}")
    if filter_dict.get("texto"):
        parts.append(f"Texto: «{filter_dict['texto']}»")
    return " · ".join(parts) if parts else "Tots els nous ensenyaments"


def _build_email_body(matched: list, description: str, alert_id: int, unsubscribe_token: str, base_url: str) -> str:
    """Genera el cos de l'email en text pla."""
    n = len(matched)
    bullets = "\n".join(f"  • {item['denominacio']}" for item in matched)
    unsubscribe_url = f"{base_url}/api/alerts/{alert_id}/unsubscribe?token={unsubscribe_token}"
    return (
        f"Hola,\n\n"
        f"Han aparegut {n} nous ensenyaments de Formació Professional que encaixen\n"
        f"amb la teva alerta \"{description}\":\n\n"
        f"{bullets}\n\n"
        f"Consulta els detalls a:\n{base_url}\n\n"
        f"---\n"
        f"Reps aquest email perquè tens una alerta activa al Cercador FP España.\n"
        f"Per deixar de rebre'l, clica aquí (sense necessitat d'entrar):\n"
        f"{unsubscribe_url}\n\n"
        f"Cercador FP España · {base_url}"
    )


def _get_or_create_unsubscribe_token(conn, alert_id: int, user_id: int) -> str:
    """Retorna el token de baixa de l'alerta, o en crea un de nou si no existeix."""
    row = _db.query_one(
        conn,
        "SELECT token FROM tokens WHERE user_id = ? AND type = 'alert_unsubscribe' "
        "AND token LIKE ?",
        (user_id, f"alert_{alert_id}_%"),
    )
    if row:
        return row["token"].split("_", 2)[2]  # extreu el token real

    raw_token = secrets.token_hex(32)
    stored_token = f"alert_{alert_id}_{raw_token}"
    expires = (datetime.now(timezone.utc) + timedelta(days=UNSUBSCRIBE_TOKEN_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'alert_unsubscribe', ?)",
        (user_id, stored_token, expires),
    )
    conn.commit()
    return raw_token


def dispatch_alerts(result: dict, base_url: str = "https://grausfp.masellas.info") -> int:
    """
    Crida `compute_changes` (ja present a result via history.append) i envia emails
    per a les alertes actives que tinguin matches.

    Idempotència: skip si `last_sent_at` és d'avui (format YYYY-MM-DD).
    Retorna el nombre d'emails enviats.
    """
    import history as _history

    # Obtenir changes del darrer entry de l'historial (ja calculat per history.append)
    history_data = _history._load_json(_history.HISTORY_PATH) or []
    if not history_data:
        return 0
    changes = history_data[0].get("changes")
    if not changes or not changes.get("has_changes"):
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = _db.get_db()
    sent = 0
    try:
        alerts = _db.query_all(
            conn,
            "SELECT a.id, a.user_id, a.filter_json, a.last_sent_at, u.email "
            "FROM alerts a JOIN users u ON u.id = a.user_id "
            "WHERE a.active = 1 AND u.verified = 1 AND u.deleted_at IS NULL",
        )
        for alert in alerts:
            # Idempotència: no enviar si ja s'ha enviat avui
            if alert["last_sent_at"] and alert["last_sent_at"][:10] == today:
                continue

            try:
                filter_dict = json.loads(alert["filter_json"])
            except (json.JSONDecodeError, TypeError):
                logger.warning("alerts_service: filter_json invàlid per alert id=%s", alert["id"])
                continue

            matched = match_alert(filter_dict, changes)

            # Afegir baixes si l'usuari les vol
            if filter_dict.get("alertar_baixes"):
                removed_meta = changes.get("new_by_grado_meta")  # no existeix per a removed; usar removed_by_grado
                # Nota: removed_by_grado és {grado: [str]} (sense meta). Afegim com a dict mínim.
                removed_by_grado = changes.get("removed_by_grado") or {}
                g_filter = filter_dict.get("grado")
                if g_filter:
                    for d in (removed_by_grado.get(g_filter) or []):
                        matched.append({"denominacio": f"[BAIXA] {d}", "grado": g_filter})
                else:
                    for g, denoms in removed_by_grado.items():
                        for d in denoms:
                            matched.append({"denominacio": f"[BAIXA] {d}", "grado": g})

            if not matched:
                continue

            description = build_alert_description(filter_dict)
            unsubscribe_token = _get_or_create_unsubscribe_token(conn, alert["id"], alert["user_id"])
            body = _build_email_body(matched, description, alert["id"], unsubscribe_token, base_url)
            subject = f"Novetats FP — {len(matched)} nous ensenyaments que t'interessen ({today})"

            try:
                email_service.send_email(alert["email"], subject, body)
                conn.execute(
                    "UPDATE alerts SET last_sent_at = ? WHERE id = ?",
                    (today, alert["id"]),
                )
                conn.commit()
                sent += 1
                logger.info("alerts_service: alerta %s → email enviat a %s (%d matches)",
                            alert["id"], alert["email"], len(matched))
            except Exception as exc:
                logger.error("alerts_service: error enviant email per alerta %s: %s", alert["id"], exc)

    finally:
        conn.close()

    return sent
```

**Verificació Step 3:**
```bash
cd backend && python3 -c "import alerts_service; print('OK: alerts_service importat correctament')"
```

---

### Step 4: Afegir endpoints a `app.py`

**Fitxer**: `backend/app.py`

**4a. CORS per a `/api/alerts*`**

Modifica la funció `_needs_auth_cors` per incloure `/api/alerts`:

```python
def _needs_auth_cors(path):
    return path.startswith("/api/auth/") or path.startswith("/api/favorites") or path.startswith("/api/alerts")
```

**4b. Afegir bloc d'endpoints just BEFORE la línia `if __name__ == "__main__":`**

Afegeix el bloc sencer just abans del comentari `# Punt d'entrada`:

```python
# ---------------------------------------------------------------------------
# Alertes — /api/alerts  (F3)
# ---------------------------------------------------------------------------

VALID_GRADOS = {"A", "B", "C", "D", "E"}


@app.route("/api/alerts", methods=["GET"])
def alerts_get():
    """Retorna les alertes actives i inactives de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        rows = _db.query_all(
            conn,
            "SELECT id, filter_json, active, created_at, last_sent_at FROM alerts "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return jsonify([dict(r) for r in rows]), 200
    finally:
        conn.close()


@app.route("/api/alerts", methods=["POST"])
def alerts_create():
    """Crea una nova alerta. Body: {"filter_json": {...}}. Màxim 10 alertes actives/usuari."""
    import db as _db
    import json as _json
    import secrets as _secrets
    from datetime import datetime, timezone, timedelta
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    data = request.get_json(silent=True) or {}
    filter_dict = data.get("filter_json")
    if not isinstance(filter_dict, dict):
        return jsonify({"error": "filter_json ha de ser un objecte JSON"}), 400
    # Almenys un criteri
    known_keys = {"grado", "familia", "nivel", "texto", "alertar_baixes"}
    criteria_keys = known_keys - {"alertar_baixes"}
    if not any(filter_dict.get(k) for k in criteria_keys):
        return jsonify({"error": "L'alerta ha de tenir almenys un criteri (grado, familia, nivel o texto)"}), 400
    # Validar grado
    if filter_dict.get("grado") and filter_dict["grado"] not in VALID_GRADOS:
        return jsonify({"error": "grado ha de ser A, B, C, D o E"}), 400
    conn = _db.get_db()
    try:
        count = _db.query_one(
            conn,
            "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND active = 1",
            (user_id,),
        )[0]
        if count >= 10:
            return jsonify({"error": "Màxim 10 alertes actives per usuari"}), 429
        filter_str = _json.dumps(filter_dict, ensure_ascii=False)
        conn.execute(
            "INSERT INTO alerts (user_id, filter_json) VALUES (?, ?)",
            (user_id, filter_str),
        )
        conn.commit()
        alert_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        # Generar token de baixa
        raw_token = _secrets.token_hex(32)
        stored_token = f"alert_{alert_id}_{raw_token}"
        expires = (datetime.now(timezone.utc) + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO tokens (user_id, token, type, expires_at) VALUES (?, ?, 'alert_unsubscribe', ?)",
            (user_id, stored_token, expires),
        )
        conn.commit()
        row = _db.query_one(
            conn,
            "SELECT id, filter_json, active, created_at, last_sent_at FROM alerts WHERE id = ?",
            (alert_id,),
        )
        return jsonify(dict(row)), 201
    finally:
        conn.close()


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def alerts_delete(alert_id):
    """Esborra una alerta de l'usuari autenticat."""
    import db as _db
    user_id = _get_session_user(request)
    if not user_id:
        return jsonify({"error": "No autenticat"}), 401
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn, "SELECT id FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
        )
        if not row:
            return jsonify({"error": "Alerta no trobada"}), 404
        conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
        conn.execute("DELETE FROM tokens WHERE token LIKE ?", (f"alert_{alert_id}_%",))
        conn.commit()
        return "", 204
    finally:
        conn.close()


@app.route("/api/alerts/<int:alert_id>", methods=["PATCH"])
def alerts_toggle(alert_id):
    """Activa o desactiva una alerta. Body: {"active": true/false}."""
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
            conn, "SELECT id FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id)
        )
        if not row:
            return jsonify({"error": "Alerta no trobada"}), 404
        conn.execute("UPDATE alerts SET active = ? WHERE id = ?", (active, alert_id))
        conn.commit()
        updated = _db.query_one(
            conn,
            "SELECT id, filter_json, active, created_at, last_sent_at FROM alerts WHERE id = ?",
            (alert_id,),
        )
        return jsonify(dict(updated)), 200
    finally:
        conn.close()


@app.route("/api/alerts/<int:alert_id>/unsubscribe", methods=["GET"])
def alerts_unsubscribe(alert_id):
    """Baixa sense login via token signat. GET /api/alerts/<id>/unsubscribe?token=<tok>"""
    import db as _db
    from flask import redirect
    raw_token = request.args.get("token", "")
    if not raw_token:
        return jsonify({"error": "Token invàlid"}), 400
    stored_token = f"alert_{alert_id}_{raw_token}"
    conn = _db.get_db()
    try:
        row = _db.query_one(
            conn,
            "SELECT id, user_id FROM tokens WHERE token = ? AND type = 'alert_unsubscribe' "
            "AND expires_at > datetime('now')",
            (stored_token,),
        )
        if not row:
            return jsonify({"error": "Token invàlid o caducat"}), 400
        conn.execute("UPDATE alerts SET active = 0 WHERE id = ?", (alert_id,))
        conn.execute("DELETE FROM tokens WHERE token = ?", (stored_token,))
        conn.commit()
    finally:
        conn.close()
    return redirect("/?unsubscribed=1")
```

**4c. Afegir el dispatch d'alertes a `admin_refresh`**

Dins de la funció `_run()` a `admin_refresh`, just AFTER el bloc de `notifier.notify_if_new()`:

```python
        try:
            notifier.notify_if_new()
        except Exception as exc_n:
            logger.error("Could not send Brevo notification: %s", exc_n)
        try:
            import alerts_service
            alerts_service.dispatch_alerts(result, base_url=BASE_URL)
        except Exception as exc_a:
            logger.error("Could not dispatch alerts: %s", exc_a)
```

**Verificació Step 4:**
```bash
cd backend && python3 -c "
import os; os.environ['ADMIN_TOKEN'] = 'test'
import app
# Verificar que les rutes estan registrades
rules = [str(r) for r in app.app.url_map.iter_rules()]
for path in ['/api/alerts', '/api/alerts/<alert_id>', '/api/alerts/<alert_id>/unsubscribe']:
    assert any(path in r for r in rules), f'Ruta {path} no trobada'
print('OK: totes les rutes /api/alerts registrades')
"
```

---

### Step 5: Afegir dispatch a `scheduler_service.py`

**Fitxer**: `backend/scheduler_service.py`

Dins de `_scheduled_refresh()`, just AFTER el bloc existent de `history.append(result)`:

```python
        try:
            history.append(result)
        except Exception as exc_h:
            logger.error("Could not write refresh history: %s", exc_h)
        try:
            import alerts_service
            alerts_service.dispatch_alerts(result)
        except Exception as exc_a:
            logger.error("Could not dispatch alerts: %s", exc_a)
```

`BASE_URL` no està accessible aquí (és variable d'`app.py`), però `dispatch_alerts` té el default `"https://grausfp.masellas.info"` que és correcte per al VPS. Si cal canviar-lo, s'afegirà via variable d'entorn en el futur.

**Verificació Step 5:**
```bash
cd backend && python3 -c "
import inspect, scheduler_service
src = inspect.getsource(scheduler_service._scheduled_refresh)
assert 'alerts_service' in src, 'dispatch_alerts no trobat a _scheduled_refresh'
print('OK: alerts_service present a _scheduled_refresh')
"
```

---

### Step 6: Crear `backend/tests/test_alerts_service.py`

**Fitxer NOU**: `backend/tests/test_alerts_service.py`

Segueix el patró de `tests/test_history.py`: fixtures simples, sense mocks de BD, tests unitaris purs de la funció de matching.

```python
"""
test_alerts_service.py — Tests unitaris del motor de matching d'alertes (F3).
"""
import pytest

import alerts_service


# Dades de test: changes amb new_by_grado_meta
CHANGES_WITH_META = {
    "has_changes": True,
    "new_by_grado_meta": {
        "D": [
            {"denominacio": "Tècnic Superior en Ciberseguretat en Entorns TI",
             "familia": "Informàtica i Comunicacions", "nivel": 2},
            {"denominacio": "Tècnic Superior en Desenvolupament Web",
             "familia": "Informàtica i Comunicacions", "nivel": 2},
        ],
        "A": [
            {"denominacio": "Operació d'instal·lacions elèctriques",
             "familia": "Electricitat i Electrònica", "nivel": 1},
        ],
    },
    "removed_by_grado": {
        "C": ["Certificat de Professionalitat de Cuina"]
    },
    "new_by_grado": {
        "D": ["Tècnic Superior en Ciberseguretat en Entorns TI",
              "Tècnic Superior en Desenvolupament Web"],
        "A": ["Operació d'instal·lacions elèctriques"],
    },
}

CHANGES_EMPTY = {
    "has_changes": False,
    "new_by_grado_meta": {},
    "removed_by_grado": {},
    "new_by_grado": {},
}


def test_match_by_grado():
    """Filtre per grado retorna tots els nous d'aquell grado."""
    result = alerts_service.match_alert({"grado": "D"}, CHANGES_WITH_META)
    denoms = [r["denominacio"] for r in result]
    assert "Tècnic Superior en Ciberseguretat en Entorns TI" in denoms
    assert "Tècnic Superior en Desenvolupament Web" in denoms
    assert len(result) == 2


def test_match_by_texto_normalized():
    """Filtre per text amb accents/majúscules matcheja correctament (NFD+lower)."""
    result = alerts_service.match_alert({"texto": "ciberseguretat"}, CHANGES_WITH_META)
    assert len(result) == 1
    assert "Ciberseguretat" in result[0]["denominacio"]


def test_match_combined_grado_and_texto():
    """AND implícit: grado D + text 'web' retorna únicament la titulació de web."""
    result = alerts_service.match_alert({"grado": "D", "texto": "web"}, CHANGES_WITH_META)
    assert len(result) == 1
    assert "Web" in result[0]["denominacio"]


def test_match_no_match_returns_empty():
    """Filtre que no coincideix amb res retorna llista buida."""
    result = alerts_service.match_alert({"grado": "E"}, CHANGES_WITH_META)
    assert result == []


def test_match_changes_none_returns_empty():
    """Si changes és None, retorna llista buida (primer refresh sense historial previ)."""
    result = alerts_service.match_alert({"grado": "D"}, {})
    assert result == []


def test_build_alert_description_combined():
    """Descripció llegible a partir de filtre combinat."""
    desc = alerts_service.build_alert_description(
        {"grado": "D", "familia": "Informàtica i Comunicacions"}
    )
    assert "Grado D" in desc
    assert "Informàtica" in desc


def test_build_alert_description_empty_filter():
    """Filtre buit retorna descripció genèrica."""
    desc = alerts_service.build_alert_description({})
    assert desc  # no buit
```

**Verificació Step 6:**
```bash
cd backend && python3 -m pytest tests/test_alerts_service.py -v
```
Resultat esperat: 7 tests passen (`test_match_by_grado`, `test_match_by_texto_normalized`, `test_match_combined_grado_and_texto`, `test_match_no_match_returns_empty`, `test_match_changes_none_returns_empty`, `test_build_alert_description_combined`, `test_build_alert_description_empty_filter`).

---

### Step 7: Verificació global

```bash
cd backend && python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```
Resultat esperat: tots els tests passen. Cap nou test trencat.

```bash
cd backend && python3 -c "
import os; os.environ['ADMIN_TOKEN'] = 'test'
import app
print('OK: app.py importa sense errors')
"
```

```bash
cd backend && git diff --stat
```
Verifica que els fitxers modificats siguin exactament:
- `backend/scrapers/pipeline.py`
- `backend/history.py`
- `backend/app.py`
- `backend/scheduler_service.py`
- `backend/alerts_service.py` (nou)
- `backend/tests/test_alerts_service.py` (nou)

---

## Done criteria

- [ ] `python3 -m pytest tests/test_alerts_service.py -v` → 7 tests passen
- [ ] `python3 -m pytest tests/test_history.py -v` → tots passen (cap regressió)
- [ ] `python3 -m pytest tests/ -v` → cap test trencat
- [ ] `python3 -c "import alerts_service"` → sense errors d'import
- [ ] `python3 -c "import os; os.environ['ADMIN_TOKEN']='test'; import app; ..."` → rutes `/api/alerts` registrades
- [ ] `git diff --stat` → 6 fitxers modificats/creats, cap fora de scope
- [ ] `backend/alerts_service.py` existeix i té `dispatch_alerts`, `match_alert`, `build_alert_description`
- [ ] Endpoints `GET /api/alerts`, `POST /api/alerts`, `DELETE /api/alerts/<id>`, `PATCH /api/alerts/<id>`, `GET /api/alerts/<id>/unsubscribe` presents a `app.py`
- [ ] `_needs_auth_cors` inclou `/api/alerts`
- [ ] `dispatch_alerts` cridat a `admin_refresh` i a `_scheduled_refresh`

---

## Test plan

Fitxer: `backend/tests/test_alerts_service.py` (creat al Step 6).

Tests existents que el pla **no ha de trencar**:
- `tests/test_history.py` — les modificacions a `history.py` afegeixen camps; els tests existents no comproven l'absència de `new_by_grado_meta`, per tant han de continuar passant.
- `tests/test_api.py` — no toca els nous endpoints.
- `tests/test_auth.py` — no tocat.

Tests que **no cal afegir** en aquest pla (cobertura addicional per al pla 029):
- Tests d'integració dels endpoints CRUD (requereixen client Flask de test i fixture de BD; fora de scope d'aquest pla backend pur).

---

## STOP conditions

- Si `tests/test_history.py` falla ABANS de fer cap canvi: STOP. L'estat base és trencada; informar.
- Si `compute_changes` té més d'un `return` (alguna versió futura): STOP i adaptar el Step 2b.
- Si `pipeline.run()` té un resultat diferent del mostrat al "Current state" (camps o ordre del `return` canviats): STOP i adaptar el Step 1.
- Si `_needs_auth_cors` no existeix o té una signatura diferent: STOP i informar.

---

## Maintenance notes

- **Primer refresh real post-deploy**: `new_by_grado_meta` al snapshot estarà buit si el snapshot anterior no tenia el camp. El primer dispatch NO enviarà alertes (no hi haurà dades meta per comparar). El segon refresh ja tindrà dades completes. Comportament esperat i acceptable.
- **Alertes amb `familia`/`nivel`**: el matching funciona ÚNICAMENT amb `meta_by_grado` del refresh actual. Si `pipeline.py` falla i no omple `meta_by_grado`, `new_by_grado_meta` serà `{}` i no s'enviarà cap alerta — comportament segur.
- **Token de baixa a `tokens`**: el prefix `alert_{id}_` és la convenció de la taula existent per a tokens d'alerta. Si en el futur es canvia, el `DELETE` del Step 4c (que usa `LIKE f"alert_{alert_id}_%"`) continuarà funcionant.
- **VPS**: cal fer `git pull && systemctl restart fp-cercador` per activar els canvis. No cal migració de BD (la taula `alerts` ja existeix a la migració 001).
