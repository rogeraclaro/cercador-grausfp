#!/usr/bin/env python3
"""
add_refs_076.py — Migració d'un sol ús del Pla 076 (identificadors estables),
sense un refresc complet del catàleg:

  1. Afegeix `ref` a cada registre d'ofertes.json (stable_ref del pipeline). Els id no es toquen.
  2. Canvia les claus d'oferta_centres.json i centres_nous_per_oferta.json d'id
     (C LOMLOE, D, E, en text) al ref vigent. Els codis C ja són el seu ref.
  3. Aplica la migració 012 a la BD si cal i tradueix al ref els favorits i
     avisos de centres que encara no en tenen (idempotent).

Les claus per id es tradueixen amb el catàleg ACTUAL: si el darrer scraping de
centres es va fer amb un catàleg anterior, poden caure en un altre grau (és el
desfasament que el Pla 076 arregla). Un scraping de centres posterior ho deixa bé.

Ús (amb el servei aturat i després d'una còpia de la BD):
  python3 scripts/add_refs_076.py [--data-dir backend/data] [--db backend/data/fp_cercador.db]
Codi de sortida 2 si més del 10 % dels favorits queden sense resoldre.
"""
import argparse
import json
import os
import sys

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'backend'))
import db  # noqa: E402
from oferta_ref import REF_RE, assign_refs, ensure_refs  # noqa: E402
from scrapers.pipeline import _write_atomic  # noqa: E402

_MAX_SENSE_RESOLDRE = 0.10


def rekey_by_ref(index: dict, records: list) -> tuple[dict, list]:
    """{id o codi: valor} → {ref: valor}. Retorna també les claus que no s'han pogut traduir."""
    ensure_refs(records)
    by_id = {str(r['id']): r['ref'] for r in records}
    by_ref = {r['ref'] for r in records}
    by_codigo: dict = {}
    for r in records:
        if r.get('codigo'):
            by_codigo.setdefault(r['codigo'], r['ref'])
    nou, perduts = {}, []
    for key, value in index.items():
        if key in by_ref:
            ref = key
        elif key.isdigit():
            ref = by_id.get(key)
        else:
            ref = by_codigo.get(key)
        if ref and REF_RE.match(ref):
            nou[ref] = value
        else:
            perduts.append(key)
    return nou, perduts


def _rekey_file(path: str, records: list) -> None:
    if not os.path.exists(path):
        print(f'{os.path.basename(path)}: no existeix, res a fer')
        return
    with open(path, encoding='utf-8') as fh:
        index = json.load(fh)
    nou, perduts = rekey_by_ref(index, records)
    _write_atomic(nou, path)
    print(f'{os.path.basename(path)}: {len(nou)} claus per ref, {len(perduts)} descartades'
          + (f' ({", ".join(perduts[:10])})' if perduts else ''))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--data-dir', default=os.path.join(_REPO_ROOT, 'backend', 'data'))
    parser.add_argument('--db', default=None, help='per defecte, <data-dir>/fp_cercador.db')
    args = parser.parse_args(argv)
    ofertes_path = os.path.join(args.data_dir, 'ofertes.json')
    db_path = args.db or os.path.join(args.data_dir, 'fp_cercador.db')

    with open(ofertes_path, encoding='utf-8') as fh:
        records = json.load(fh)
    assign_refs(records)  # ValueError si n'hi ha de repetits: no s'escriu res
    _write_atomic(records, ofertes_path)
    print(f'ofertes.json: {len(records)} registres amb ref')

    for name in ('oferta_centres.json', 'centres_nous_per_oferta.json'):
        _rekey_file(os.path.join(args.data_dir, name), records)

    db._OFERTES_PATH = ofertes_path  # el hook de la migració 012 llegeix aquest catàleg
    conn = db.init_db(db_path)
    try:
        counts = db.backfill_refs(conn, records)
        total = conn.execute('SELECT COUNT(*) FROM list_items').fetchone()[0]
        sense_ref = conn.execute('SELECT COUNT(*) FROM list_items WHERE oferta_ref IS NULL').fetchone()[0]
    finally:
        conn.close()
    print(f'BD: {counts}')
    print(f'BD: {total} favorits, {sense_ref} sense ref')
    if total and sense_ref / total > _MAX_SENSE_RESOLDRE:
        print(f'ATENCIÓ: més del {_MAX_SENSE_RESOLDRE:.0%} dels favorits sense resoldre: no desplegar')
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
