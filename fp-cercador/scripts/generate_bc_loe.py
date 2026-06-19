#!/usr/bin/env python3
"""
generate_bc_loe.py — Genera backend/data/bc_loe.json a partir dels Annexos PDF
dels 584 Certificats de Profesionalitat C LOE.

Execució única (~6 min amb rate limiting). Necessita xarxa i pdfplumber.
Escriu backend/data/bc_loe.json (gitignored).

Ús: python3 scripts/generate_bc_loe.py [--dry-run N]
  --dry-run N  Processa només els primers N PDFs (per a proves ràpides)
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time

import requests
import pdfplumber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ofertes.json')
OUT_PATH  = os.path.join(_REPO_ROOT, 'backend', 'data', 'bc_loe.json')
BASE_DAM  = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.todofp.es/',
}
_UC_PAT = re.compile(r'\bUC\d{4}_\d+\b')


def _fetch_pdf_uc_codes(codigo: str) -> list[str]:
    url = f"{BASE_DAM}/anexos/{codigo.lower()}.pdf"
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    uc_codes: list[str] = []
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            uc_codes.extend(_UC_PAT.findall(text))
    return list(dict.fromkeys(uc_codes))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N',
                        help='Processa només els primers N PDFs')
    args = parser.parse_args()

    if not os.path.exists(DATA_PATH):
        logger.error("ofertes.json no trobat a: %s", DATA_PATH)
        sys.exit(1)

    with open(DATA_PATH, encoding='utf-8') as f:
        records = json.load(f)

    c_loe = [
        r for r in records
        if r.get('grado') == 'C' and r.get('plan_antiguo') and r.get('codigo')
    ]
    if args.dry_run:
        c_loe = c_loe[:args.dry_run]
        logger.info("DRY-RUN: processant %d PDFs (de %d totals)", args.dry_run, len(c_loe))
    else:
        logger.info("%d registres C LOE a processar (~6 min)", len(c_loe))

    result: dict[str, list[str]] = {}
    errors: list[str] = []
    no_codes: list[str] = []

    for i, r in enumerate(c_loe, 1):
        codigo = r['codigo']
        try:
            codes = _fetch_pdf_uc_codes(codigo)
            result[codigo] = codes
            if codes:
                logger.info("[%d/%d] %s → %d UC codes", i, len(c_loe), codigo, len(codes))
            else:
                no_codes.append(codigo)
                logger.warning("[%d/%d] 0 UC codes (404 o PDF sense texto): %s",
                               i, len(c_loe), codigo)
        except Exception as exc:
            logger.error("[%d/%d] ERROR: %s — %s", i, len(c_loe), codigo, exc)
            errors.append(codigo)
            result[codigo] = []

        if i < len(c_loe):
            time.sleep(1)

    # Estadística de cobertura
    with_codes = sum(1 for v in result.values() if v)
    total = len(result)
    pct = with_codes / total * 100 if total else 0
    logger.info("═══ Resultat ═══")
    logger.info("Total processats: %d", total)
    logger.info("PDFs amb UC codes: %d (%.0f%%)", with_codes, pct)
    logger.info("Sense UC codes:   %d", len(no_codes))
    logger.info("Errors HTTP:      %d", len(errors))
    if no_codes:
        logger.info("Sense UC codes: %s", no_codes[:10])
    if errors:
        logger.info("Errors: %s", errors[:10])

    if not args.dry_run and pct < 80:
        logger.error(
            "COBERTURA INSUFICIENT (%.0f%% < 80%%). bc_loe.json NO s'ha escrit. "
            "Investiga els PDFs problemàtics i reporta.", pct
        )
        sys.exit(1)

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    size = os.path.getsize(OUT_PATH)
    logger.info("bc_loe.json escrit: %d entrades, %d bytes", len(result), size)


if __name__ == '__main__':
    main()
