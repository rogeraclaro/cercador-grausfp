#!/usr/bin/env python3
"""
generate_c_loe_estructura.py — Genera backend/data/c_loe_estructura.json (pla 093) a partir dels
Annexos PDF dels Certificats de Profesionalitat C LOE: per certificat, els MF amb hores, les UF de
cada MF amb hores, el mòdul de pràctiques i el total oficial de la formació.

Format: {codi_certificat: {"total_h": 920|None, "mf": [{"codigo": "MF0820_2", "h": 170,
         "uc": "UC0820_2", "ufs": [{"codigo": "UF0884", "h": 60}]}], "mp": {"codigo": "MP0183", "h": 80}|None}}
Només hi surt el que diu l'annex; si no dona una hora, el camp és None (no s'inventa).
Els certificats sense cap MF a l'annex (escanejat) no hi són: l'endpoint cau a bc_loe.json.

Ús: python3 scripts/generate_c_loe_estructura.py [--dry-run N] [--cache DIR]
Necessita `pdftotext` (poppler) i xarxa; la caché de PDFs és la mateixa que la de generate_bc_loe.py.
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

import requests  # noqa: E402

from generate_bc_loe import BASE_DAM, _HEADERS, own_segment  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ofertes.json')
BC_LOE_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'bc_loe.json')
OUT_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'c_loe_estructura.json')

_TOTAL_PAT = re.compile(r'Duración de la formación asociada:\s*(\d+)\s*horas', re.I)
# «Código: X» obre un mòdul o una unitat; la primera «Duración: N horas» que el segueix és la seva.
_TOKEN_PAT = re.compile(r'Código:?\s*(MF\s?\d{3,4}\s?[_-]\s?\d|UF\s?\d{3,4}|MP\s?\d{3,4})|Duración:\s*(\d+)\s*horas'
                        r'|Asociado a la Unidad de Competencia:\s*(UC\d{3,4}_\d)', re.I)


def _normalize(code: str) -> str:
    """Els annexos porten errades d'impremta (MF0121-2, MF 1323_1, «Código MF0881_1», UF425, MP093): es porten a MF0121_2, UF0425, MP0093."""
    num = re.search(r'\d+', code).group().zfill(4)
    return code[:2].upper() + num + ('_' + code.strip()[-1] if code.upper().startswith('MF') and re.search(r'[_-]\s*\d$', code) else '')


def parse_estructura(segment: str) -> dict:
    """Estructura del certificat a partir del tros de text del seu annex."""
    total = _TOTAL_PAT.search(segment)
    mfs: list[dict] = []
    mp = None
    current = None
    for m in _TOKEN_PAT.finditer(segment):
        code, hours, uc = m.groups()
        code = _normalize(code) if code else None
        if uc:
            if mfs and 'uc' not in mfs[-1]:  # alguns annexos escriuen UC820_2 sense el zero
                mfs[-1]['uc'] = 'UC' + uc[2:].zfill(6)
        elif code is None:
            if current is not None and current['h'] is None:
                current['h'] = int(hours)
        elif code.upper().startswith('MF'):
            current = {'codigo': code, 'h': None, 'ufs': []}
            mfs.append(current)
        elif code.upper().startswith('MP'):
            current = mp = {'codigo': code, 'h': None}
        elif mfs and not any(u['codigo'] == code for u in mfs[-1]['ufs']):
            current = {'codigo': code, 'h': None}
            mfs[-1]['ufs'].append(current)
        else:
            current = {'codigo': code, 'h': None}  # UF repetida o sense MF: la seva hora no compta
    return {'total_h': int(total.group(1)) if total else None, 'mf': mfs, 'mp': mp}


def _annex_text(codigo: str, cache_dir: str) -> str:
    """Text de l'annex amb `pdftotext -layout` (és el que ordena bé les columnes); '' si dona 404."""
    pdf = os.path.join(cache_dir, f'{codigo.lower()}.pdf')
    if not os.path.exists(pdf):
        resp = requests.get(f'{BASE_DAM}/anexos/{codigo.lower()}.pdf', headers=_HEADERS, timeout=60)
        time.sleep(1)
        if resp.status_code == 404:
            return ''
        resp.raise_for_status()
        with open(pdf, 'wb') as f:
            f.write(resp.content)
    return subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, check=True,
                          text=True, encoding='utf-8', errors='replace').stdout


def _read_json(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def _contradicts_bc_loe(codigo: str, info: dict, bc_loe: dict) -> bool:
    """Els MF de l'annex no són els números de les UC de bc_loe.json (que és el que la resta de la web usa).
    Els pocs certificats amb UC corregides a mà (uc_corr_overrides.json) no es comparen."""
    ucs = bc_loe.get(codigo)
    if not ucs:
        return False
    overrides = _read_json(os.path.join(_REPO_ROOT, 'backend', 'uc_corr_overrides.json'))
    return codigo not in overrides and {m['codigo'][2:6] for m in info['mf']} != {u[2:6] for u in ucs}


def blank_inconsistent_hours(info: dict) -> int:
    """Un MF amb UF sense hores o amb UF que no sumen les seves: les hores del MF i de les seves UF es
    buiden (el text d'alguns annexos va a dues columnes i la durada pot caure a un altre codi).
    Retorna quantes vegades ho ha fet."""
    blanked = 0
    for mf in info['mf']:
        known = [u['h'] for u in mf['ufs']]
        if mf['ufs'] and None not in known and mf['h'] is not None and sum(known) != mf['h']:
            mf['h'] = None
            for u in mf['ufs']:
                u['h'] = None
            blanked += 1
    return blanked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N')
    parser.add_argument('--cache', metavar='DIR', required=True)
    args = parser.parse_args()
    os.makedirs(args.cache, exist_ok=True)
    with open(DATA_PATH, encoding='utf-8') as f:
        records = json.load(f)
    c_loe = [r['codigo'] for r in records
             if r.get('grado') == 'C' and r.get('plan_antiguo') and r.get('codigo')]
    if args.dry_run:
        c_loe = c_loe[:args.dry_run]

    def load(codigo: str):
        try:
            return codigo, own_segment(_annex_text(codigo, args.cache), codigo)
        except Exception as exc:
            logger.error("%s — %s", codigo, exc)
            return codigo, None

    bc_loe = _read_json(BC_LOE_PATH)
    result: dict[str, dict] = {}
    blanked = 0
    with ThreadPoolExecutor(max_workers=3) as pool:  # 3 baixades alhora, cadascuna amb 1 s de pausa
        for i, (codigo, segment) in enumerate(pool.map(load, c_loe), 1):
            info = parse_estructura(segment or '')
            blanked += blank_inconsistent_hours(info)
            if info['mf'] and not _contradicts_bc_loe(codigo, info, bc_loe):
                result[codigo] = info
            elif info['mf']:
                logger.warning("%s: els MF de l'annex no quadren amb bc_loe.json; no s'hi desa l'estructura", codigo)
            elif segment is not None:
                logger.warning("[%d/%d] %s: cap MF a l'annex", i, len(c_loe), codigo)

    no_hours = [c for c, v in result.items() if v['total_h'] is None or any(m['h'] is None for m in v['mf'])]
    logger.info("MF amb hores buidades per incoherents: %d", blanked)
    logger.info("Certificats amb estructura: %d de %d; amb alguna hora absent: %d", len(result), len(c_loe), len(no_hours))
    if args.dry_run:
        logger.info("DRY-RUN: no s'escriu res.")
        return
    if len(result) < 0.8 * len(c_loe):
        logger.error("COBERTURA INSUFICIENT: no s'escriu el fitxer.")
        sys.exit(1)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))
    logger.info("Escrit %s", OUT_PATH)


if __name__ == '__main__':
    main()
