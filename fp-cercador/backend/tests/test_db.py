"""Tests per a db.py — tots corren contra :memory:, mai contra dades de producció."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import db


@pytest.fixture
def mem_db():
    conn = db.init_db(db_path=":memory:")
    yield conn
    conn.close()


def test_schema_creates_all_tables(mem_db):
    tables = {
        r[0]
        for r in mem_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    expected = {
        "users", "sessions", "tokens", "login_attempts",
        "lists", "list_items", "alerts", "schema_version",
    }
    assert expected.issubset(tables)


def test_schema_version_is_1(mem_db):
    v = mem_db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
    assert v == 1


def test_foreign_keys_cascade(mem_db):
    mem_db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        ("test@test.com", "hash"),
    )
    mem_db.commit()
    uid = mem_db.execute(
        "SELECT id FROM users WHERE email='test@test.com'"
    ).fetchone()[0]
    mem_db.execute(
        "INSERT INTO sessions (user_id, token, expires_at) VALUES (?, ?, ?)",
        (uid, "tok123", "2099-01-01"),
    )
    mem_db.commit()
    mem_db.execute("DELETE FROM users WHERE id=?", (uid,))
    mem_db.commit()
    count = mem_db.execute(
        "SELECT COUNT(*) FROM sessions WHERE user_id=?", (uid,)
    ).fetchone()[0]
    assert count == 0


def test_run_migrations_idempotent(mem_db):
    db.run_migrations(mem_db)
    count = mem_db.execute(
        "SELECT COUNT(*) FROM schema_version"
    ).fetchone()[0]
    assert count == 1
