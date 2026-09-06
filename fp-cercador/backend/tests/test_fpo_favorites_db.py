"""
test_fpo_favorites_db.py — Migracions 009/010 (Pla 061).

BD en memòria migrada. No barreja amb els 2 tests preexistents de test_db.py
que fallen per schema_version.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import db


@pytest.fixture
def mem_db():
    conn = db.init_db(db_path=":memory:")
    yield conn
    conn.close()


def _cols(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def test_migracio_009_010_crea_taules(mem_db):
    tables = {
        r[0] for r in mem_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert "fpo_favorites" in tables
    assert "fpo_favorite_courses" in tables

    assert _cols(mem_db, "fpo_favorites") == {
        "user_id", "especialitat_codi", "created_at",
    }
    assert _cols(mem_db, "fpo_favorite_courses") == {
        "user_id", "especialitat_codi", "curs_id", "centre_id", "created_at",
    }


def test_fk_cascade(mem_db):
    mem_db.execute(
        "INSERT INTO users (id, email, password_hash) VALUES (1, 'a@b.cat', 'x')"
    )
    mem_db.execute(
        "INSERT INTO fpo_favorites (user_id, especialitat_codi) VALUES (1, 'IFCD0112')"
    )
    mem_db.execute(
        "INSERT INTO fpo_favorite_courses (user_id, especialitat_codi, curs_id, centre_id) "
        "VALUES (1, 'IFCD0112', 'C1', '97428')"
    )
    mem_db.commit()

    mem_db.execute("DELETE FROM users WHERE id = 1")
    mem_db.commit()

    assert mem_db.execute("SELECT COUNT(*) FROM fpo_favorites").fetchone()[0] == 0
    assert mem_db.execute("SELECT COUNT(*) FROM fpo_favorite_courses").fetchone()[0] == 0
