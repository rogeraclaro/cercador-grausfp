"""
b_contingut_scraper.py — Contingut de la fitxa web de cada Grau B (Pla 068).

La fitxa d'un B llista, cada element com "(CODI) text" dins un <li>:
  - "Estándares de competencia": (ECPnnnn_n) text — B LOMLOE i B LOE.
  - "Resultados de aprendizaje": (FAM_RA_NNNN_PP) text — només B LOMLOE. El
    sufix _PP coincideix amb el del Grau A (ADG_A_3001_01 ↔ ADG_RA_3001_01).
La resta de <li> (A inclosos, menús) no casen amb cap dels dos patrons.

Genera backend/data/b_contingut.json:
  {codigo_b: {"ecp": [{codigo, text}], "ra": [{codigo, text}]}}.

Com a bc_lomloe_scraper, els ficha_id només són vàlids just després d'un
refresc d'ofertes i cada fitxa es verifica pel "Código:". Són ~3.000 fitxes:
4 fils amb una sessió cadascun (todofp triga ~2,5 s per fitxa, així que la
càrrega queda per sota de ~2 req/s) i reintent amb backoff (5/15/45 s). Una
fitxa inabastable es salta amb WARNING.
"""
import html as _html
import json
import logging
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from scrapers import buscador_scraper

logger = logging.getLogger(__name__)

BACKOFF = (5, 15, 45)

_CODIGO_RE = re.compile(r'Código:\s*([A-Z0-9_]+)')
_LI_RE = re.compile(r'<li[^>]*>(.*?)</li>', re.S)
_ITEM_RE = re.compile(r'^\(\s*([A-Z0-9_]+)\s*\)\s*(.+)$', re.S)
_ECP_RE = re.compile(r'^ECP\d+_\d+$')
_RA_RE = re.compile(r'^[A-Z]{3}_RA_\d+_\d+$')
_TAG_RE = re.compile(r'<(script|style).*?</\1>|<[^>]+>', re.S)

_local = threading.local()


def _to_text(html: str) -> str:
    # unescape abans de col·lapsar: '&nbsp' (sense ';') esdevé \xa0, que \s també cobreix
    return re.sub(r'\s+', ' ', _html.unescape(_TAG_RE.sub(' ', html))).strip()


def parse_codigo(html: str) -> str | None:
    m = _CODIGO_RE.search(_to_text(html))
    return m.group(1) if m else None


def parse_b_ficha(html: str) -> dict:
    """{'ecp': [{codigo, text}], 'ra': [{codigo, text}]} de la fitxa d'un B."""
    parsed = {'ecp': [], 'ra': []}
    for raw in _LI_RE.findall(html):
        m = _ITEM_RE.match(_to_text(raw))
        if not m:
            continue
        codigo, text = m.group(1), m.group(2).strip()
        if _ECP_RE.match(codigo):
            parsed['ecp'].append({'codigo': codigo, 'text': text})
        elif _RA_RE.match(codigo):
            parsed['ra'].append({'codigo': codigo, 'text': text})
    return parsed


def _thread_session():
    """Una sessió (amb cookies del bootstrap) per fil del pool."""
    if getattr(_local, 'session', None) is None:
        _local.session = buscador_scraper._bootstrap_session()
    return _local.session


def _fetch_ficha_html(session, ficha_id: int, timeout: int = 30) -> str:
    resp = session.get(f'{buscador_scraper.BASE_URL}/ficha',
                       params={'grado': 'B', 'id': ficha_id}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _fetch_with_retry(session, ficha_id: int) -> str:
    for attempt, wait in enumerate((*BACKOFF, None)):
        try:
            return _fetch_ficha_html(session, ficha_id)
        except Exception as exc:
            if wait is None:
                raise
            logger.warning('fitxa B %s intent %d fallit (%s), reintent en %ds',
                           ficha_id, attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError('unreachable')


def _scrape_one(rec: dict) -> dict | None:
    codigo = rec['codigo']
    try:
        html = _fetch_with_retry(_thread_session(), rec['ficha_id'])
    except Exception as exc:
        logger.warning('fitxa B %s (id %s) inabastable, saltada: %s',
                       codigo, rec['ficha_id'], exc)
        return None
    found = parse_codigo(html)
    if found != codigo:
        logger.warning('ficha_id %s: esperava %s, la fitxa diu %s — saltat (id obsolet?)',
                       rec['ficha_id'], codigo, found)
        return None
    return parse_b_ficha(html)


def build_b_contingut(records: list[dict], on_progress=None, max_workers: int = 4) -> dict[str, dict]:
    """
    Retorna {codigo_b: {'ecp': [...], 'ra': [...]}} per a tots els B (LOMLOE i
    LOE) amb ficha_id. Sense cap B → {} sense fer xarxa.
    """
    b_recs = [r for r in records
              if r.get('grado') == 'B' and r.get('codigo') and r.get('ficha_id')]
    if not b_recs:
        return {}

    result: dict[str, dict] = {}
    total = len(b_recs)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_scrape_one, r): r['codigo'] for r in b_recs}
        for done, fut in enumerate(as_completed(futures), start=1):
            parsed = fut.result()
            if parsed is not None:
                result[futures[fut]] = parsed
            if on_progress and (done % 25 == 0 or done == total):
                on_progress('Contingut fitxes B', done, total)

    logger.info('b_contingut: %d/%d fitxes B resoltes', len(result), total)
    return result


def write_b_contingut(index: dict, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=dir_path, delete=False) as tmp:
        json.dump(index, tmp, ensure_ascii=False, indent=1)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)
