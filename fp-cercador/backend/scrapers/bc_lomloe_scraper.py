"""
bc_lomloe_scraper.py — Relació C LOMLOE → [B LOMLOE] via la fitxa web de todofp.

Un Grau B LOMLOE és un mòdul professional: el seu codi FAM_B_NNNN porta el
número de mòdul. La fitxa de cada C LOMLOE llista els seus mòduls com
"( NNNN ) Nom" dins la secció "Módulos Profesionales". El match és
(família del C, NNNN) → FAM_B_NNNN.

Genera backend/data/bc_lomloe.json: {codigo_c: [codigo_b, ...]}.

Els ficha_id només són vàlids just després d'un refresc d'ofertes (canvien a
cada refresc): per això build_bc_lomloe s'executa dins pipeline.run(). Cada
fitxa es verifica comparant el "Código:" de la pàgina amb l'esperat.

Rate-limit 1 req/s; todofp triga ~2,5 s per fitxa i té finestres de fallades
transitòries → reintent amb backoff (5/15/45 s). ~400 fitxes ≈ 10–16 min.
"""
import html as _html
import json
import logging
import os
import re
import tempfile
import time

from scrapers import buscador_scraper

logger = logging.getLogger(__name__)

RATE_LIMIT_SEC = 1.0
BACKOFF = (5, 15, 45)

_CODIGO_RE = re.compile(r'Código:\s*([A-Z]{3}_C_\d+_\w+)')
_MODULO_RE = re.compile(r'\(\s*(\d{4})\s*\)\s*([^()]+?)\s*(?=\(|$)')
_B_LOMLOE_RE = re.compile(r'^([A-Z]{3})_B_(\d{4})$')
_TAG_RE = re.compile(r'<(script|style).*?</\1>|<[^>]+>', re.S)


def _to_text(html: str) -> str:
    return _html.unescape(re.sub(r'\s+', ' ', _TAG_RE.sub(' ', html))).strip()


def parse_codigo(html: str) -> str | None:
    m = _CODIGO_RE.search(_to_text(html))
    return m.group(1) if m else None


def parse_modulos(html: str) -> list[tuple[str, str]]:
    """[(num_modul, nom), ...] de la secció 'Módulos Profesionales' … 'Nota:'."""
    text = _to_text(html)
    if 'Módulos Profesionales' not in text:
        return []
    section = text.split('Módulos Profesionales', 1)[1].split('Nota:', 1)[0]
    return [(num, nom.strip()) for num, nom in _MODULO_RE.findall(section)]


def _fetch_ficha_html(session, ficha_id: int, timeout: int = 30) -> str:
    resp = session.get(f'{buscador_scraper.BASE_URL}/ficha',
                       params={'grado': 'C', 'id': ficha_id}, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _fetch_with_retry(session, ficha_id: int) -> str:
    for attempt, wait in enumerate((*BACKOFF, None)):
        try:
            return _fetch_ficha_html(session, ficha_id)
        except Exception as exc:
            if wait is None:
                raise
            logger.warning('ficha %s intent %d fallit (%s), reintent en %ds',
                           ficha_id, attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError('unreachable')


def build_bc_lomloe(records: list[dict], session=None, on_progress=None) -> dict[str, list[str]]:
    """
    Retorna {codigo_c: [codigo_b, ...]} per als C LOMLOE amb ficha_id.
    Els mòduls sense B (transversals, ex. PRL) s'ignoren. Una fitxa el
    "Código:" de la qual no coincideix amb l'esperat (ficha_id obsolet) es
    salta amb WARNING.
    """
    c_lomloe = [r for r in records
                if r.get('grado') == 'C' and not r.get('plan_antiguo') and r.get('ficha_id')]
    b_by_fam_num: dict[tuple[str, str], str] = {}
    for r in records:
        if r.get('grado') == 'B' and not r.get('plan_antiguo'):
            m = _B_LOMLOE_RE.match(r.get('codigo') or '')
            if m:
                b_by_fam_num[(m.group(1), m.group(2))] = r['codigo']

    if not c_lomloe:
        return {}
    if session is None:
        session = buscador_scraper._bootstrap_session()

    result: dict[str, list[str]] = {}
    total = len(c_lomloe)
    for i, r in enumerate(c_lomloe):
        codigo = r['codigo']
        if on_progress and i % 25 == 0:
            on_progress('B→C LOMLOE', i, total)
        html = _fetch_with_retry(session, r['ficha_id'])
        found = parse_codigo(html)
        if found != codigo:
            logger.warning('ficha_id %s: esperava %s, la fitxa diu %s — saltat (id obsolet?)',
                           r['ficha_id'], codigo, found)
            time.sleep(RATE_LIMIT_SEC)
            continue
        fam = codigo[:3]
        b_codes = [b_by_fam_num[(fam, num)] for num, _ in parse_modulos(html)
                   if (fam, num) in b_by_fam_num]
        result[codigo] = sorted(set(b_codes))
        time.sleep(RATE_LIMIT_SEC)

    if on_progress:
        on_progress('B→C LOMLOE', total, total)
    logger.info('bc_lomloe: %d/%d certificats C resolts', len(result), total)
    return result


def write_bc_lomloe(index: dict, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=dir_path, delete=False) as tmp:
        json.dump(index, tmp, ensure_ascii=False, indent=1)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)
