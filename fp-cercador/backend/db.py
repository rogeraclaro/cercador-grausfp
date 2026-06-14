"""
db.py — Capa de connexió SQLite per al Cercador FP.

Funcions públiques:
  get_db(db_path=None)       → connexió sqlite3 amb WAL i foreign keys
  init_db(db_path=None)      → aplica migracions i retorna la connexió
  run_migrations(conn)       → aplica els fitxers SQL de migrations/ no executats
  query_one(conn, sql, params) → fetchone()
  query_all(conn, sql, params) → fetchall()
"""
import os
import sqlite3

_DEFAULT_DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "fp_cercador.db"),
)

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


def get_db(db_path=None):
    """Retorna una connexió SQLite configurada."""
    path = db_path if db_path is not None else _DEFAULT_DB_PATH
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

    conn.commit()


def init_db(db_path=None):
    """Crea la BD (si no existeix), aplica migracions i retorna la connexió."""
    conn = get_db(db_path=db_path)
    run_migrations(conn)
    return conn


def query_one(conn, sql, params=()):
    return conn.execute(sql, params).fetchone()


def query_all(conn, sql, params=()):
    return conn.execute(sql, params).fetchall()
