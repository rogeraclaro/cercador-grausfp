#!/usr/bin/env python3
"""
build_c_modulos.py — Pla 078: genera backend/data/c_modulos.json (i reescriu
bc_lomloe.json, perquè tots dos surtin de la mateixa passada) sense esperar el
refresc setmanal.

Els ficha_id d'ofertes.json caduquen a cada refresc de todofp: abans de llegir
les fitxes se substitueixen pels ids vius del buscador (una sola consulta).

~400 fitxes a 1 req/s ≈ 10–16 min. No executar diumenge 11:10–11:45 (refresc).

Ús: python3 scripts/build_c_modulos.py [--dry-run N]
  --dry-run N  Processa només els primers N certificats C i no escriu res
"""
import argparse
import datetime
import json
import logging
import os
import sys

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'backend'))

from scrapers import buscador_scraper  # noqa: E402
from scrapers.bc_lomloe_scraper import build_bc_lomloe, write_bc_lomloe, write_c_modulos  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(_REPO_ROOT, 'backend', 'data')


def _during_refresh(now: datetime.datetime) -> bool:
    return now.weekday() == 6 and datetime.time(11, 10) <= now.time() <= datetime.time(11, 45)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N')
    args = parser.parse_args()

    if _during_refresh(datetime.datetime.now()):
        logger.error('Diumenge 11:10–11:45: hi ha el refresc setmanal en marxa. Torna-ho a provar més tard.')
        return 1

    with open(os.path.join(DATA_DIR, 'ofertes.json'), encoding='utf-8') as f:
        records = json.load(f)

    live_ids = {r['codigo']: r['ficha_id']
                for recs in buscador_scraper.parse_buscador_all().values() for r in recs
                if r.get('codigo') and r.get('ficha_id') is not None}
    for r in records:
        if r.get('grado') == 'C' and not r.get('plan_antiguo'):
            r['ficha_id'] = live_ids.get(r.get('codigo'))

    if args.dry_run:
        c_codes = [r['codigo'] for r in records
                   if r.get('grado') == 'C' and not r.get('plan_antiguo') and r.get('ficha_id')]
        keep = set(c_codes[:args.dry_run])
        records = [r for r in records if r.get('grado') != 'C' or r.get('codigo') in keep]

    c_modulos: dict = {}
    bc_lomloe = build_bc_lomloe(records, modulos_out=c_modulos,
                                on_progress=lambda phase, i, n: logger.info('%s %d/%d', phase, i, n))

    if args.dry_run:
        print(json.dumps(c_modulos, ensure_ascii=False, indent=1))
        return 0

    write_bc_lomloe(bc_lomloe, os.path.join(DATA_DIR, 'bc_lomloe.json'))
    write_c_modulos(c_modulos, os.path.join(DATA_DIR, 'c_modulos.json'))
    logger.info('Escrits bc_lomloe.json (%d) i c_modulos.json (%d)', len(bc_lomloe), len(c_modulos))
    return 0


if __name__ == '__main__':
    sys.exit(main())
