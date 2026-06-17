# Pla 030: [F7] Migració 002 SQLite + persistència observatory_snapshots

## Status

- **Priority**: P2
- **Effort**: S (3-4h)
- **Risk**: LOW — cap canvi de lògica existent; el bloc try/except fa l'operació no-fatal
- **Depends on**: Pla 018 (spike DONE — decisions documentades a `plans/outputs/spike-observatori.md`)
- **Category**: backend
- **Planned at**: commit `b84ffb4`, 2026-06-17

## Why this matters

`HISTORY_MAX = 20` a `history.py` trunca l'historial a 20 entrades (~5 mesos). L'Observatori necessita una sèrie temporal indefinida. Aquest pla crea la taula `observatory_snapshots` al SQLite existent i hi persisteix cada refresh — el primer pas imprescindible abans de poder construir cap gràfic.

## Codebase context

**`backend/history.py` — funció `append()` (línies 102–130):**
```python
def append(result: dict) -> None:
    full = { ... }
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
    _write_atomic(full, SNAPSHOT_PATH)   # ← enganxar AQUÍ, just després
```

**`backend/db.py` — patró existent:**
```python
def init_db(db_path=None):
    conn = get_db(db_path=db_path)
    run_migrations(conn)   # llegeix migrations/*.sql, aplica les que no s'han aplicat
    return conn
```

**`backend/migrations/001_initial_schema.sql` — patró de migració:**
```sql
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
INSERT INTO schema_version (version) VALUES (1);
```

**`backend/data/refresh_history.json` — estructura existent (10 entrades):**
```json
[
  {
    "ts": "2026-06-17T...",
    "total": 12894,
    "by_grado": {"A": 8730, "B": 2952, "C": 981, "D": 195, "E": 36},
    "unknown_families": [],
    "duration_seconds": 14.2,
    "changes": {
      "new_denominacions": [...],
      "removed_denominacions": [...],
      "new_by_grado": {...},
      "removed_by_grado": {...},
      "has_changes": true,
      ...
    }
  }
]
```

## Scope

**In scope**:
- `backend/migrations/002_observatory.sql` (fitxer nou)
- `backend/history.py` (afegir `_persist_observatory()` + crida a `append()`)
- `scripts/migrate_history_to_observatory.py` (fitxer nou, one-shot)

**Out of scope**: cap altre fitxer. No tocar `app.py`, `db.py`, ni cap fitxer de frontend.

## Steps

### Step 1: Crear `backend/migrations/002_observatory.sql`

Contingut exacte:

```sql
-- Migration 002: Taula de l'Observatori FP (sèrie temporal indefinida)

CREATE TABLE IF NOT EXISTS observatory_snapshots (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  TEXT    NOT NULL,
    total               INTEGER NOT NULL,
    total_a             INTEGER NOT NULL DEFAULT 0,
    total_b             INTEGER NOT NULL DEFAULT 0,
    total_c             INTEGER NOT NULL DEFAULT 0,
    total_d             INTEGER NOT NULL DEFAULT 0,
    total_e             INTEGER NOT NULL DEFAULT 0,
    n_altes             INTEGER NOT NULL DEFAULT 0,
    n_baixes            INTEGER NOT NULL DEFAULT 0,
    families_amb_altes  TEXT,
    source              TEXT    NOT NULL DEFAULT 'refresh'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_observatory_ts ON observatory_snapshots(ts);
CREATE INDEX IF NOT EXISTS idx_observatory_ts_lookup ON observatory_snapshots(ts DESC);

INSERT INTO schema_version (version) VALUES (2);
```

**Verificació**: `sqlite3 backend/data/fp_cercador.db ".tables"` ha de mostrar `observatory_snapshots`. Executar `python -c "from backend.db import init_db; init_db()"` des de la rel del projecte — no ha de llançar errors. Si la migració ja s'ha aplicat (reruns), `run_migrations` és idempotent i la salta.

### Step 2: Afegir `_persist_observatory()` a `backend/history.py`

Afegir la funció auxiliar just ABANS de la funció `append()`:

```python
def _persist_observatory(entry: dict, changes: dict) -> None:
    """Persisteix una fila a observatory_snapshots (no-fatal si el SQLite falla)."""
    import json as _json
    from db import get_db, run_migrations
    by_grado = entry.get("by_grado") or {}
    new_denoms = changes.get("new_denominacions") or []
    removed_denoms = changes.get("removed_denominacions") or []
    new_by_grado = changes.get("new_by_grado") or {}
    families_amb_altes = sorted(new_by_grado.keys()) if new_by_grado else []
    conn = get_db()
    run_migrations(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO observatory_snapshots
            (ts, total, total_a, total_b, total_c, total_d, total_e,
             n_altes, n_baixes, families_amb_altes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry["ts"],
            entry.get("total") or 0,
            by_grado.get("A") or 0,
            by_grado.get("B") or 0,
            by_grado.get("C") or 0,
            by_grado.get("D") or 0,
            by_grado.get("E") or 0,
            len(new_denoms),
            len(removed_denoms),
            _json.dumps(families_amb_altes, ensure_ascii=False) if families_amb_altes else None,
        ),
    )
    conn.commit()
    conn.close()
```

Afegir la crida a `append()` just DESPRÉS de `_write_atomic(full, SNAPSHOT_PATH)` (línia 130 actual):

```python
    _write_atomic(full, SNAPSHOT_PATH)
    # Persistència a l'Observatori (no-fatal)
    try:
        _persist_observatory(entry, entry.get("changes") or {})
    except Exception as exc:
        logger.warning("observatory_persist failed: %s", exc)
```

**Verificació**: executar `python -c "import sys; sys.path.insert(0,'backend'); from history import append; append({'total':100,'by_grado':{'A':80,'B':20},'unknown_families':[],'duration_seconds':1.0})"` des de la rel. Comprovar `sqlite3 backend/data/fp_cercador.db "SELECT * FROM observatory_snapshots LIMIT 1;"` — ha de mostrar una fila.

### Step 3: Crear `scripts/migrate_history_to_observatory.py`

```python
#!/usr/bin/env python3
"""
One-shot: migra les entrades de refresh_history.json a observatory_snapshots.
Idempotent: INSERT OR IGNORE per ts UNIQUE.
Executa des de la rel del projecte: python scripts/migrate_history_to_observatory.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from db import init_db

HISTORY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "backend", "data", "refresh_history.json"
)


def main():
    with open(HISTORY_PATH, encoding="utf-8") as f:
        history = json.load(f)

    conn = init_db()
    inserted = 0
    skipped = 0

    for entry in reversed(history):  # ordre cronològic
        changes = entry.get("changes") or {}
        by_grado = entry.get("by_grado") or {}
        new_denoms = changes.get("new_denominacions") or []
        removed_denoms = changes.get("removed_denominacions") or []
        new_by_grado = changes.get("new_by_grado") or {}
        families_amb_altes = sorted(new_by_grado.keys()) if new_by_grado else []

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO observatory_snapshots
                (ts, total, total_a, total_b, total_c, total_d, total_e,
                 n_altes, n_baixes, families_amb_altes, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'history_migration')
            """,
            (
                entry["ts"],
                entry.get("total") or 0,
                by_grado.get("A") or 0,
                by_grado.get("B") or 0,
                by_grado.get("C") or 0,
                by_grado.get("D") or 0,
                by_grado.get("E") or 0,
                len(new_denoms),
                len(removed_denoms),
                json.dumps(families_amb_altes, ensure_ascii=False) if families_amb_altes else None,
            ),
        )
        if cursor.rowcount:
            inserted += 1
        else:
            skipped += 1

    conn.commit()
    conn.close()
    print(f"Migració completada: {inserted} inserts, {skipped} ignorats (ja existien).")


if __name__ == "__main__":
    main()
```

**Verificació**: `python scripts/migrate_history_to_observatory.py` ha de mostrar `Migració completada: N inserts, 0 ignorats.` (N = nombre d'entrades a refresh_history.json, fins a 10). Executar-lo dues vegades — la segona ha de mostrar `0 inserts, N ignorats` (idempotent).

Comprovar el resultat: `sqlite3 backend/data/fp_cercador.db "SELECT COUNT(*) FROM observatory_snapshots;"` ha de retornar N.

## Done criteria

- [ ] `backend/migrations/002_observatory.sql` existeix amb la taula i l'índex UNIQUE
- [ ] `sqlite3 backend/data/fp_cercador.db ".tables"` mostra `observatory_snapshots`
- [ ] `python scripts/migrate_history_to_observatory.py` inserta les entrades existents
- [ ] Executar-lo dues vegades confirma idempotència (0 inserts al segon run)
- [ ] `python -c "from backend.history import append; append({...})"` afegeix 1 fila a observatory_snapshots
- [ ] `git status` — cap fitxer fora de l'scope modificat

## STOP conditions

- Si `run_migrations()` llança error al Step 2 en el test manual: ATURA i reporta — pot ser un conflicte de versió amb la migració 001.
- Si `INSERT OR IGNORE` mai insereix res (sempre retorna rowcount=0): ATURA — potser el UNIQUE INDEX falla o la migració no s'ha aplicat.

## Git workflow

Commit atòmic amb tots els fitxers de l'scope:
```
git add backend/migrations/002_observatory.sql backend/history.py scripts/migrate_history_to_observatory.py
git commit -m "feat(F7): taula observatory_snapshots + persistència post-refresh (pla 030)"
```

## Maintenance notes

- La taula `observatory_snapshots` és acumulativa i no es trunca mai. Protegir-la a les còpies de seguretat del VPS.
- Si en el futur s'afegeix el pla de centres (016b → pla futur), afegir `n_centres INTEGER DEFAULT NULL` via migració 003 — no cal tocar la lògica existent.
- L'`INSERT OR IGNORE` garanteix que un doble-trigger d'`append()` no dupliqui files.
