"""
test_add_refs_076.py — Script d'un sol ús del Pla 076: afegeix `ref` a un
ofertes.json existent i canvia les claus dels fitxers de centres d'id a ref,
sense un refresc complet.
"""
import importlib.util
import json
import os

import pytest

import db

_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'add_refs_076.py')
_spec = importlib.util.spec_from_file_location('add_refs_076', _SCRIPT)
add_refs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(add_refs)

URL = 'https://www.todofp.es/que-estudiar/familias-profesionales/{}.html'
CATALEG = [
    {'id': 1, 'grado': 'C', 'codigo': 'ADGG0408', 'familia': 'Administración y Gestión', 'denominacion': 'C'},
    {'id': 2, 'grado': 'C', 'codigo': 'ADG_C_001_3B', 'familia': 'Administración y Gestión', 'denominacion': 'CN'},
    {'id': 3, 'grado': 'D', 'codigo': None, 'familia': 'X', 'denominacion': 'D',
     'ficha_url': URL.format('agraria/jardineria')},
]


def test_rekey_tradueix_ids_i_conserva_codis():
    index = {'ADGG0408': ['M1'], '2': ['M2'], '3': ['M3'], '99': ['M4']}
    nou, perduts = add_refs.rekey_by_ref(index, CATALEG)
    assert nou == {'ADGG0408': ['M1'], 'ADG_C_001_3B': ['M2'], 'agraria~jardineria': ['M3']}
    assert perduts == ['99']


def test_rekey_es_idempotent():
    nou, _ = add_refs.rekey_by_ref({'3': ['M3']}, CATALEG)
    assert add_refs.rekey_by_ref(nou, CATALEG) == (nou, [])


def test_main_afegeix_refs_i_migra_fitxers_i_bd(tmp_path, capsys):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'ofertes.json').write_text(json.dumps(CATALEG), encoding='utf-8')
    (data / 'oferta_centres.json').write_text(json.dumps({'3': ['M3'], 'ADGG0408': ['M1']}))
    (data / 'centres_nous_per_oferta.json').write_text(json.dumps({'2': ['M2']}))
    conn = db.init_db(str(data / 'fp.db'))
    conn.execute("INSERT INTO users (id, email, password_hash) VALUES (1, 'a@b.c', 'x')")
    conn.execute("INSERT INTO lists (id, user_id, name) VALUES (1, 1, 'Favorits')")
    conn.execute("INSERT INTO list_items (list_id, oferta_id) VALUES (1, 3)")
    conn.commit()
    conn.close()

    assert add_refs.main(['--data-dir', str(data), '--db', str(data / 'fp.db')]) == 0

    records = json.loads((data / 'ofertes.json').read_text())
    assert [r['ref'] for r in records] == ['ADGG0408', 'ADG_C_001_3B', 'agraria~jardineria']
    assert [r['id'] for r in records] == [1, 2, 3]  # els id no es toquen
    assert json.loads((data / 'oferta_centres.json').read_text()) == {
        'agraria~jardineria': ['M3'], 'ADGG0408': ['M1']}
    assert json.loads((data / 'centres_nous_per_oferta.json').read_text()) == {'ADG_C_001_3B': ['M2']}
    conn = db.get_db(str(data / 'fp.db'))
    assert conn.execute("SELECT oferta_ref FROM list_items").fetchone()[0] == 'agraria~jardineria'
    assert 'favorits_sense_resoldre' in capsys.readouterr().out


def test_main_falla_si_massa_favorits_sense_resoldre(tmp_path):
    data = tmp_path / 'data'
    data.mkdir()
    (data / 'ofertes.json').write_text(json.dumps(CATALEG), encoding='utf-8')
    conn = db.init_db(str(data / 'fp.db'))
    conn.execute("INSERT INTO users (id, email, password_hash) VALUES (1, 'a@b.c', 'x')")
    conn.execute("INSERT INTO lists (id, user_id, name) VALUES (1, 1, 'Favorits')")
    conn.execute("INSERT INTO list_items (list_id, oferta_id) VALUES (1, 999)")
    conn.commit()
    conn.close()
    assert add_refs.main(['--data-dir', str(data), '--db', str(data / 'fp.db')]) == 2
