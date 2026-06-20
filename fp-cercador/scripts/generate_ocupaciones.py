#!/usr/bin/env python3
"""
generate_ocupaciones.py — Genera backend/data/ocupaciones.json: l'índex de cerca
per ocupació de F6.

DUES fonts (validades a .planning/spikes/001-003):
  - Graus C LOE: POST /buscadorcertificados/pdfPT → PDF amb "puestos de trabajo".
  - Graus D i E: pàgina ficha_url (que-estudiar) → secció "Salidas profesionales".

Execució única manual (~2-3 min). Necessita xarxa, pdfplumber i beautifulsoup4.
Escriu una llista plana d'entrades {ocupacio, norm, grado, codigo, id,
denominacion, ficha_url, familia}.

Ús: python3 scripts/generate_ocupaciones.py [--dry-run N]
  --dry-run N  Processa només els primers N de cada grau (proves ràpides).
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
import pdfplumber

# Reutilitza la sessió/bootstrap del scraper de certificats (NO el modifica)
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'backend'))
from scrapers import certificados_scraper as cs  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ofertes.json')
OUT_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ocupaciones.json')

_HTML_HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.todofp.es/'}

# Línia del PDF C: bullet (-, –, —) + CNO opcional + nom. Capturem nom; CNO es neteja a part.
_PDF_LINE = re.compile(r'^[-–—]+\s*(.+?)\.?\s*$')
_SECTION_C = 'Ocupaciones o puestos de trabajo relacionados'
_FOOTER_C = 'Subdirección General'
# Neteja de TOTS els formats CNO observats: NNNN.NNNN, NNNN.NNN.N, 8 dígits seguits.
# El separador pot ser espai o ': ' (format observat en alguns PDFs).
_CNO_CLEAN = re.compile(r'^\s*(?:\d{4}\.\d{3,4}(?:\.\d)?|\d{8})(?::\s+|\s+)')


def norm(s: str) -> str:
    """Minúscules + sense accents + col·lapsa soroll d'OCR ('/ as' → '/as')."""
    s = s.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'/\s+', '/', s)
    return re.sub(r'\s+', ' ', s).strip()


def clean_occ(text: str) -> str:
    """Treu el codi CNO inicial (qualsevol format) del nom d'ocupació."""
    return _CNO_CLEAN.sub('', text).strip()


# ── Font C: PDF /pdfPT ──────────────────────────────────────────────────────
def occupations_for_cert(session, cert_id: int, codigo: str) -> list[str]:
    r = session.post(cs.BASE_CERT_URL + '/pdfPT',
                     data={'certificadoID': str(cert_id), 'codigo': codigo}, timeout=30)
    r.raise_for_status()
    if r.content[:4] != b'%PDF':
        return []
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    out, in_section = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if _SECTION_C in line:
            in_section = True
            continue
        if not in_section:
            continue
        if _FOOTER_C in line:
            break
        m = _PDF_LINE.match(line)
        if m:
            occ = clean_occ(m.group(1))
            if occ and len(occ) > 2:
                out.append(occ)
    # dedup preservant ordre
    return list(dict.fromkeys(out))


# ── Font D/E: pàgina ficha_url ──────────────────────────────────────────────
def occupations_for_ficha(url: str) -> list[str]:
    try:
        r = requests.get(url, headers=_HTML_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        logger.warning("ficha %s: %s", url, exc)
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b']):
        if 'salidas profesionales' in tag.get_text(strip=True).lower():
            blk = tag.find_next(['p', 'ul', 'div'])
            if not blk:
                return []
            txt = blk.get_text(' ', strip=True)
            txt = re.sub(r'^.*?Trabajar como:?', '', txt, flags=re.I).strip()
            parts = [p.strip(' .') for p in re.split(r'[.\n]', txt) if p.strip(' .')]
            return list(dict.fromkeys(p for p in parts if 3 < len(p) < 90))[:30]
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N', help='Primers N de cada grau')
    args = parser.parse_args()

    if not os.path.exists(DATA_PATH):
        logger.error("ofertes.json no trobat: %s", DATA_PATH)
        sys.exit(1)
    with open(DATA_PATH, encoding='utf-8') as f:
        records = json.load(f)

    den_c = {r['codigo']: r for r in records if r.get('grado') == 'C' and r.get('codigo')}
    de = [r for r in records if r.get('grado') in ('D', 'E') and r.get('ficha_url')]

    entries: list[dict] = []

    # --- Font C ---
    cert_data = cs.fetch_all()  # {codigo: {cert_id, ...}}
    cert_items = list(cert_data.items())
    if args.dry_run:
        cert_items = cert_items[:args.dry_run]
    session = cs._bootstrap_session()
    c_ok = 0
    for i, (codigo, d) in enumerate(cert_items, 1):
        try:
            occs = occupations_for_cert(session, d['cert_id'], codigo)
        except Exception as exc:
            logger.warning("[C %d/%d] %s ERROR: %s", i, len(cert_items), codigo, exc)
            occs = []
        if occs:
            c_ok += 1
        rec = den_c.get(codigo)
        denom = rec['denominacion'] if rec else codigo
        fam = rec.get('familia', '') if rec else ''
        rid = rec.get('id') if rec else None
        for occ in occs:
            entries.append({'ocupacio': occ, 'norm': norm(occ), 'grado': 'C',
                            'codigo': codigo, 'id': rid, 'denominacion': denom,
                            'ficha_url': None, 'familia': fam})
        if i % 100 == 0:
            logger.info("  C ...%d/%d", i, len(cert_items))
    logger.info("Font C: %d/%d certs amb ocupacions", c_ok, len(cert_items))

    # --- Font D/E ---
    de_items = de[:args.dry_run] if args.dry_run else de
    de_ok = 0
    for i, r in enumerate(de_items, 1):
        occs = occupations_for_ficha(r['ficha_url'])
        if occs:
            de_ok += 1
        for occ in occs:
            entries.append({'ocupacio': occ, 'norm': norm(occ), 'grado': r['grado'],
                            'codigo': r.get('codigo'), 'id': r.get('id'),
                            'denominacion': r['denominacion'], 'ficha_url': r['ficha_url'],
                            'familia': r.get('familia', '')})
        if i % 50 == 0:
            logger.info("  D/E ...%d/%d", i, len(de_items))
        time.sleep(0.2)
    logger.info("Font D/E: %d/%d amb ocupacions", de_ok, len(de_items))

    json.dump(entries, open(OUT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    logger.info("═══ ocupaciones.json escrit: %d entrades, %d bytes ═══",
                len(entries), os.path.getsize(OUT_PATH))


if __name__ == '__main__':
    main()
