"""
db.py — Capa de connexió SQLite per al Cercador FP.

Funcions públiques:
  get_db(db_path=None)       → connexió sqlite3 amb WAL i foreign keys
  init_db(db_path=None)      → aplica migracions i retorna la connexió
  run_migrations(conn)       → aplica els fitxers SQL de migrations/ no executats
  query_one(conn, sql, params) → fetchone()
  query_all(conn, sql, params) → fetchall()
"""
import json
import logging
import os
import sqlite3

_FALLBACK_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "fp_cercador.db")

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def get_db(db_path=None):
    """Retorna una connexió SQLite configurada."""
    path = db_path if db_path is not None else os.environ.get("DB_PATH", _FALLBACK_DB_PATH)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def run_migrations(conn):
    """Aplica les migracions SQL pendents (idempotent)."""
    # Llegir versió actual (0 si schema_version no existeix)
    try:
        row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
        current = row[0] if row[0] is not None else 0
    except sqlite3.OperationalError:
        current = 0

    migration_files = sorted(
        f for f in os.listdir(_MIGRATIONS_DIR)
        if f.endswith(".sql") and f[:3].isdigit()
    )

    for filename in migration_files:
        version = int(filename[:3])
        if version <= current:
            continue
        filepath = os.path.join(_MIGRATIONS_DIR, filename)
        with open(filepath, encoding="utf-8") as fh:
            sql = fh.read()
        conn.executescript(sql)
        if version == 12:
            _backfill_refs_from_catalog(conn)

    conn.commit()


# ---------------------------------------------------------------------------
# Pla 076 — emplenat de la clau estable `ref` (migració 012)
# ---------------------------------------------------------------------------

_OFERTES_PATH = os.path.join(os.path.dirname(__file__), "data", "ofertes.json")
_logger = logging.getLogger(__name__)


def _pending_refs(conn) -> bool:
    return bool(conn.execute("SELECT 1 FROM list_items WHERE oferta_ref IS NULL LIMIT 1").fetchone()
                or conn.execute("SELECT 1 FROM centres_watch LIMIT 1").fetchone())


def _backfill_refs_from_catalog(conn):
    """Emplena els ref amb ofertes.json. Fail-soft: sense catàleg queden a NULL
    (scripts/add_refs_076.py ho pot tornar a fer)."""
    if not _pending_refs(conn):
        return None
    try:
        with open(_OFERTES_PATH, encoding="utf-8") as fh:
            records = json.load(fh)
        counts = backfill_refs(conn, records)
    except (OSError, ValueError) as exc:
        _logger.warning("migració 012: refs no emplenats (%s)", exc)
        return None
    _logger.warning("migració 012: %s", counts)
    return counts


def backfill_refs(conn, records) -> dict:
    """
    Tradueix al ref vigent els favorits sense oferta_ref i les claus d'avís de
    centres que encara no són un ref (codigo o str(id)). Idempotent.

    Favorits: l'oferta_id pot apuntar a un altre grau si hi ha hagut refrescos
    pel mig; si el favorit té oferta_codigo i no coincideix, mana el codi.
    Avisos: tenen la denominació, que desfà els id desplaçats i els codis repetits.
    """
    from oferta_ref import ensure_refs

    ensure_refs(records)
    by_id = {r["id"]: r for r in records}
    by_ref = {r["ref"]: r for r in records}
    by_codigo: dict = {}
    by_denom: dict = {}
    for r in records:
        if r.get("codigo"):
            by_codigo.setdefault(r["codigo"], []).append(r)
        by_denom.setdefault(r.get("denominacion"), r)

    counts = dict.fromkeys(("favorits", "favorits_resolts", "favorits_corregits",
                            "favorits_sense_resoldre", "avisos", "avisos_actualitzats",
                            "avisos_sense_resoldre"), 0)

    for item in conn.execute(
            "SELECT id, oferta_id, oferta_codigo FROM list_items WHERE oferta_ref IS NULL").fetchall():
        counts["favorits"] += 1
        at_id = by_id.get(item["oferta_id"])
        codigo = item["oferta_codigo"]
        rec = at_id
        if codigo and (not at_id or at_id.get("codigo") != codigo):
            rec = (by_codigo.get(codigo) or [None])[0]
            if rec and at_id:
                counts["favorits_corregits"] += 1
        if not rec:
            counts["favorits_sense_resoldre"] += 1
            continue
        conn.execute("UPDATE list_items SET oferta_ref = ?, oferta_id = ?, oferta_codigo = ? WHERE id = ?",
                     (rec["ref"], rec["id"], rec.get("codigo"), item["id"]))
        counts["favorits_resolts"] += 1

    for watch in conn.execute("SELECT id, oferta_key, oferta_denom FROM centres_watch").fetchall():
        key, denom = watch["oferta_key"], watch["oferta_denom"]
        if key in by_ref:
            continue
        counts["avisos"] += 1
        if key.isdigit():
            rec = by_id.get(int(key))
            if not rec or rec.get("denominacion") != denom:
                rec = by_denom.get(denom)
        else:
            candidates = by_codigo.get(key) or []
            rec = next((r for r in candidates if r.get("denominacion") == denom),
                       candidates[0] if candidates else None)
        # OR IGNORE: si l'usuari ja segueix aquest ref, l'avís vell es deixa tal qual.
        if rec and conn.execute("UPDATE OR IGNORE centres_watch SET oferta_key = ? WHERE id = ?",
                                (rec["ref"], watch["id"])).rowcount:
            counts["avisos_actualitzats"] += 1
        else:
            counts["avisos_sense_resoldre"] += 1

    conn.commit()
    return counts


def init_db(db_path=None):
    """Crea la BD (si no existeix), aplica migracions i retorna la connexió."""
    conn = get_db(db_path=db_path)
    run_migrations(conn)
    return conn


def query_one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()


def query_all(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()


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
