"""
test_refs_migration.py — Migració 012 (Pla 076): list_items.oferta_ref i
centres_watch.oferta_key passen a la clau estable `ref`, emplenades amb el
catàleg actual. Un favorit desplaçat per un refresc anterior es corregeix si
en tenim el codi.
"""
import json
import os
import shutil

import pytest

import db

ADG = 'Administración y Gestión'
COM = 'Comercio y Marketing'
URL = 'https://www.todofp.es/que-estudiar/familias-profesionales/{}.html'

CATALEG = [
    {'id': 1, 'grado': 'A', 'codigo': 'MF0432_1', 'familia': ADG, 'denominacion': 'Manipulació ADG'},
    {'id': 2, 'grado': 'A', 'codigo': 'MF0432_1', 'familia': COM, 'denominacion': 'Manipulació COM'},
    {'id': 3, 'grado': 'A', 'codigo': 'UF0001', 'familia': ADG, 'denominacion': 'UF nova'},
    {'id': 4, 'grado': 'C', 'codigo': 'ADGG0408', 'familia': ADG, 'denominacion': 'Operacions'},
    {'id': 5, 'grado': 'D', 'codigo': None, 'familia': ADG, 'denominacion': 'Gestió administrativa',
     'ficha_url': URL.format('administracion-gestion/gestion-administrativa')},
    {'id': 6, 'grado': 'D', 'codigo': None, 'familia': ADG, 'denominacion': 'Informàtica d\'oficina',
     'ficha_url': URL.format('administracion-gestion/informatica-oficina')},
    {'id': 7, 'grado': 'C', 'codigo': 'ADG_C_001_3B', 'familia': ADG, 'denominacion': 'C LOMLOE'},
]


def _conn_v11(tmp_path, monkeypatch):
    """BD amb les migracions fins a la 011 (estat de producció abans del Pla 076)."""
    old_dir = tmp_path / 'migr11'
    old_dir.mkdir()
    for name in os.listdir(db._MIGRATIONS_DIR):
        if name.endswith('.sql') and int(name[:3]) <= 11:
            shutil.copy(os.path.join(db._MIGRATIONS_DIR, name), old_dir / name)
    monkeypatch.setattr(db, '_MIGRATIONS_DIR', str(old_dir))
    conn = db.init_db(str(tmp_path / 'test.db'))
    monkeypatch.undo()
    conn.execute("INSERT INTO users (id, email, password_hash) VALUES (1, 'a@b.c', 'x')")
    conn.execute("INSERT INTO lists (id, user_id, name) VALUES (1, 1, 'Favorits')")
    return conn


def _fav(conn, oferta_id, codigo=None):
    conn.execute("INSERT INTO list_items (list_id, oferta_id, oferta_codigo) VALUES (1, ?, ?)",
                 (oferta_id, codigo))


def _watch(conn, key, denom):
    conn.execute("INSERT INTO centres_watch (user_id, oferta_key, oferta_denom) VALUES (1, ?, ?)",
                 (key, denom))


def _migrar(conn, tmp_path, monkeypatch, cataleg=CATALEG):
    path = tmp_path / 'ofertes.json'
    if cataleg is not None:
        path.write_text(json.dumps(cataleg), encoding='utf-8')
    monkeypatch.setattr(db, '_OFERTES_PATH', str(path))
    conn.commit()
    db.run_migrations(conn)


def _refs(conn):
    return [r[0] for r in conn.execute("SELECT oferta_ref FROM list_items ORDER BY id")]


def test_bd_nova_te_la_columna_oferta_ref(tmp_path):
    conn = db.init_db(str(tmp_path / 'nova.db'))
    cols = {r[1] for r in conn.execute("PRAGMA table_info(list_items)")}
    assert 'oferta_ref' in cols
    assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 12


def test_backfill_favorits_per_id_i_per_codi(tmp_path, monkeypatch):
    conn = _conn_v11(tmp_path, monkeypatch)
    _fav(conn, 5)                     # D sense codi: per id
    _fav(conn, 2, 'MF0432_1')         # codi repetit, l'id hi coincideix: família COM
    _fav(conn, 3, 'ADGG0408')         # desplaçat: l'id 3 ja és un altre grau → es prioritza el codi
    _fav(conn, 99)                    # ja no existeix i sense codi: no es pot resoldre
    _migrar(conn, tmp_path, monkeypatch)
    assert _refs(conn) == ['administracion-gestion~gestion-administrativa', 'MF0432_1~COM',
                           'ADGG0408', None]
    # L'oferta_id es posa al dia amb l'id vigent del grau resolt.
    assert conn.execute("SELECT oferta_id FROM list_items WHERE oferta_ref = 'ADGG0408'").fetchone()[0] == 4


def test_backfill_retorna_recomptes(tmp_path, monkeypatch):
    conn = _conn_v11(tmp_path, monkeypatch)
    _migrar(conn, tmp_path, monkeypatch, cataleg=None)
    _fav(conn, 5)
    _fav(conn, 3, 'ADGG0408')
    _fav(conn, 99)
    _watch(conn, '6', "Informàtica d'oficina")
    _watch(conn, 'K0', 'desconegut')
    counts = db.backfill_refs(conn, CATALEG)
    assert counts == {'favorits': 3, 'favorits_resolts': 2, 'favorits_corregits': 1,
                      'favorits_sense_resoldre': 1, 'avisos': 2, 'avisos_actualitzats': 1,
                      'avisos_sense_resoldre': 1}


def test_backfill_avisos_de_centres(tmp_path, monkeypatch):
    conn = _conn_v11(tmp_path, monkeypatch)
    _watch(conn, '6', "Informàtica d'oficina")       # D per id
    _watch(conn, '5', "Informàtica d'oficina")       # id desplaçat: la denominació mana
    conn.execute("INSERT INTO users (id, email, password_hash) VALUES (2, 'x@y.z', 'x')")
    conn.execute("INSERT INTO centres_watch (user_id, oferta_key, oferta_denom) "
                 "VALUES (2, 'MF0432_1', 'Manipulació COM')")  # codi repetit: per denominació
    _watch(conn, 'ADGG0408', 'Operacions')          # C LOE: el codi ja és el ref
    _watch(conn, '7', 'C LOMLOE')                   # C LOMLOE per id → codi
    _migrar(conn, tmp_path, monkeypatch)
    keys = [r[0] for r in conn.execute("SELECT oferta_key FROM centres_watch ORDER BY id")]
    # El segon avís col·lidiria amb el primer (mateix usuari i ref): es deixa tal qual.
    assert keys == ['administracion-gestion~informatica-oficina', '5', 'MF0432_1~COM',
                    'ADGG0408', 'ADG_C_001_3B']


def test_migracio_sense_cataleg_no_peta(tmp_path, monkeypatch):
    conn = _conn_v11(tmp_path, monkeypatch)
    _fav(conn, 5)
    _migrar(conn, tmp_path, monkeypatch, cataleg=None)
    assert _refs(conn) == [None]
    assert conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == 12


def test_backfill_es_idempotent(tmp_path, monkeypatch):
    conn = _conn_v11(tmp_path, monkeypatch)
    _fav(conn, 5)
    _migrar(conn, tmp_path, monkeypatch)
    counts = db.backfill_refs(conn, CATALEG)
    assert counts['favorits'] == 0 and _refs(conn) == ['administracion-gestion~gestion-administrativa']
