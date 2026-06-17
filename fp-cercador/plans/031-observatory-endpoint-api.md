# Pla 031: [F7] Endpoint `/api/observatory` (dades agregades per a gràfics)

## Status

- **Priority**: P2
- **Effort**: S (2-3h)
- **Risk**: LOW — endpoint públic de lectura; cap canvi a lògica existent
- **Depends on**: Pla 030 DONE (taula `observatory_snapshots` existent amb dades)
- **Category**: backend
- **Planned at**: commit `b84ffb4`, 2026-06-17

## Why this matters

La pàgina `observatori.html` (pla 032) necessita un endpoint únic que retorni les dades agregades per a tots els gràfics en una sola crida: la sèrie temporal per a les línies de tendència, la distribució actual per a les barres, i les darreres novetats per a la llista. Sense aquest endpoint, el frontend hauria de fer múltiples crides i calcular els agregats al client, fent el codi més fràgil.

## Codebase context

**`backend/app.py` — patró d'endpoint públic existent (línies 224–234):**
```python
@app.route("/api/refresh-history")
def refresh_history():
    """Retorna l'historial de refreshos (públic, sense auth)."""
    if not os.path.exists(history.HISTORY_PATH):
        return jsonify([]), 200
    try:
        with open(history.HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return jsonify([]), 200
    return jsonify(data), 200
```

**`backend/db.py` — patró de query:**
```python
def query_all(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()
```

**Taula `observatory_snapshots` (post-pla 030):**
```
id | ts | total | total_a | total_b | total_c | total_d | total_e
   | n_altes | n_baixes | families_amb_altes | source
```

**`backend/data/last_snapshot.json` (post-pla 006)** — conté `by_grado`, `families`, `denominacions` del darrer refresh. Serveix per a la foto "actual".

## Scope

**In scope**:
- `backend/app.py` — afegir 1 endpoint + 1 funció helper privada
- `backend/db.py` — afegir 1 funció `query_observatory(conn)`

**Out of scope**: cap altre fitxer. No tocar `history.py`, cap fitxer de frontend, ni cap test existent.

## Steps

### Step 1: Afegir `query_observatory()` a `backend/db.py`

Afegir al final de `db.py`, just abans del final del fitxer:

```python
def query_observatory(conn, limit: int = 200):
    """Retorna les darreres `limit` files d'observatory_snapshots, ordre cronològic."""
    return conn.execute(
        """
        SELECT ts, total, total_a, total_b, total_c, total_d, total_e,
               n_altes, n_baixes, families_amb_altes
        FROM observatory_snapshots
        ORDER BY ts ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
```

**Verificació**: `python -c "import sys; sys.path.insert(0,'backend'); from db import init_db, query_observatory; conn=init_db(); rows=query_observatory(conn); print(len(rows), 'files')"` — ha de mostrar el nombre de files migrades (mínim les 10 de l'historial).

### Step 2: Afegir l'endpoint `/api/observatory` a `backend/app.py`

Afegir just DESPRÉS de l'endpoint `/api/refresh-history` (línia ~234):

```python
@app.route("/api/observatory")
def observatory():
    """Retorna les dades agregades de l'Observatori FP (públic, sense auth)."""
    try:
        conn = db.init_db()
        rows = db.query_observatory(conn)
        conn.close()
    except Exception as exc:
        logger.warning("observatory endpoint error: %s", exc)
        return jsonify({"error": "unavailable"}), 503

    series = [
        {
            "ts": row["ts"],
            "total": row["total"],
            "A": row["total_a"],
            "B": row["total_b"],
            "C": row["total_c"],
            "D": row["total_d"],
            "E": row["total_e"],
            "n_altes": row["n_altes"],
            "n_baixes": row["n_baixes"],
        }
        for row in rows
    ]

    current = series[-1] if series else {}

    # Darreres novetats: de refresh_history.json (les 5 darreres amb altes)
    recent_changes = []
    try:
        import json as _json
        with open(history.HISTORY_PATH, "r", encoding="utf-8") as f:
            hist = _json.load(f)
        for entry in hist[:10]:
            c = entry.get("changes") or {}
            if not c.get("has_changes"):
                continue
            recent_changes.append({
                "ts": entry["ts"],
                "new_by_grado": c.get("new_by_grado") or {},
            })
            if len(recent_changes) >= 5:
                break
    except Exception:
        pass

    return jsonify({
        "current": current,
        "series": series,
        "recent_changes": recent_changes,
    }), 200
```

**Prerequisit**: verificar que `db` ja és importat a `app.py`. Si no, afegir `from backend import db` o `import db` (el patró existent del fitxer). Comprovar el top del fitxer per veure com s'importen els mòduls interns.

**Verificació**:
1. Iniciar el servidor: `cd backend && python app.py` (o `flask run --port 5001`)
2. `curl -s http://localhost:5001/api/observatory | python3 -m json.tool | head -40`
3. Ha de retornar `{"current": {...}, "series": [...], "recent_changes": [...]}` sense errors.
4. Aturar el servidor.

### Step 3: Afegir el comentari al bloc de rutes de `app.py`

Al bloc de comentaris que descriu les rutes (línies 1–15 d'`app.py`), afegir:
```
#  GET    /api/observatory              → dades agregades Observatori FP (públic)
```

## Done criteria

- [ ] `db.py` té la funció `query_observatory(conn, limit=200)`
- [ ] `app.py` té la ruta `/api/observatory` que retorna `current`, `series`, `recent_changes`
- [ ] `curl http://localhost:5001/api/observatory` retorna 200 amb JSON vàlid
- [ ] `series` conté almenys les entrades migrades (mínim 1)
- [ ] `current` conté els camps `total`, `A`, `B`, `C`, `D`, `E`
- [ ] Si `observatory_snapshots` és buida, retorna `{"current": {}, "series": [], "recent_changes": []}` sense error 500
- [ ] `git status` — cap fitxer fora de l'scope modificat

## STOP conditions

- Si `db` no és importat a `app.py` i el patró d'import existent és diferent del que suposem (e.g. usa `from . import db` per a un paquet): ATURA i reporta el patró exacte — no improvisar.
- Si la taula `observatory_snapshots` no existeix (pla 030 no executat): ATURA, el pla 030 és prerequisit.

## Git workflow

```
git add backend/app.py backend/db.py
git commit -m "feat(F7): endpoint /api/observatory (dades agregades per a gràfics) (pla 031)"
```

## Maintenance notes

- El `limit=200` a `query_observatory` cobreix ~4 anys de refreshos setmanals. Augmentar si cal.
- `recent_changes` llegeix de `refresh_history.json` (no de SQLite) per aprofitar les denominacions completes que l'historial JSON ja té. Si en el futur es migra tot a SQLite, revisar aquest bloc.
- Afegir caching (e.g. `@cache.cached(timeout=300)`) quan hi hagi Flask-Caching al projecte — avui no hi és.
