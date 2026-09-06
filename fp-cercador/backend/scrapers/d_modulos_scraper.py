"""
d_modulos_scraper.py — Mòduls ("Plan de formación") de cada cicle D via la
fitxa web de todofp (Pla 058).

La fitxa de cada D té una secció <h2>Plan de formación</h2> amb un <ul> que
llista els mòduls: "<li>Nom del mòdul.</li>" o "<li>0179. Nom (Grado
Superior)</li>". També porta un enllaç a buscarCentros amb ?ensenanzaFP=NNN.

Genera backend/data/d_modulos.json: {str(id_d): {modulos: [{num, name}],
ensenanzaFP: str|None}}. La relació C→D NO es persisteix: es deriva en
memòria a cd_lomloe.py.

Les fitxes D són pàgines estàtiques (ficha_url d'ofertes.json, grau D) i no
caduquen. Rate-limit 1 req/s; reintent amb backoff (5/15/45 s).
"""
import html as _html
import json
import logging
import os
import re
import tempfile
import time

import requests

from scrapers import buscador_scraper

logger = logging.getLogger(__name__)

RATE_LIMIT_SEC = 1.0
BACKOFF = (5, 15, 45)

_LI_RE = re.compile(r'<li[^>]*>(.*?)</li>', re.S)
_TAG_RE = re.compile(r'<[^>]+>')
_NUM_RE = re.compile(r'^(\d{4})\.\s*(.+)$', re.S)
_ENSENANZA_RE = re.compile(r'ensenanzaFP=([\w]+)')


def parse_modulos(html: str) -> list[dict]:
    """[{'num': str|None, 'name': str}] de la secció 'Plan de formación'."""
    idx = html.find('Plan de formaci')
    if idx == -1:
        return []
    end = html.find('</ul>', idx)
    seg = html[idx:end if end != -1 else None]

    modulos = []
    for raw in _LI_RE.findall(seg):
        it = _html.unescape(_TAG_RE.sub('', raw)).strip()
        if not it:
            continue
        m = _NUM_RE.match(it)
        num = m.group(1) if m else None
        name = (m.group(2) if m else it).rstrip('.').strip()
        modulos.append({'num': num, 'name': name})
    return modulos


def parse_ensenanza_fp(html: str) -> str | None:
    m = _ENSENANZA_RE.search(html)
    return m.group(1) if m else None


def _fetch_ficha_html(session, url: str, timeout: int = 30) -> str:
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def _fetch_with_retry(session, url: str) -> str:
    for attempt, wait in enumerate((*BACKOFF, None)):
        try:
            return _fetch_ficha_html(session, url)
        except Exception as exc:
            if wait is None:
                raise
            logger.warning('fitxa D %s intent %d fallit (%s), reintent en %ds',
                           url, attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError('unreachable')


def build_d_modulos(records: list[dict], session=None, on_progress=None) -> dict[str, dict]:
    """
    Retorna {str(id_d): {'modulos': [{num, name}], 'ensenanzaFP': str|None}}
    per als cicles D que tenen ficha_url. Sense cap D → {} sense fer xarxa.
    """
    d_recs = [r for r in records if r.get('grado') == 'D' and r.get('ficha_url')]
    if not d_recs:
        return {}
    if session is None:
        session = requests.Session()
        session.headers.update(buscador_scraper.HEADERS)

    result: dict[str, dict] = {}
    total = len(d_recs)
    for i, r in enumerate(d_recs):
        if on_progress and i % 25 == 0:
            on_progress('Mòduls D', i, total)
        try:
            html = _fetch_with_retry(session, r['ficha_url'])
        except Exception as exc:
            logger.warning('fitxa D %s (id %s) inabastable, saltada: %s',
                           r['ficha_url'], r['id'], exc)
            time.sleep(RATE_LIMIT_SEC)
            continue
        result[str(r['id'])] = {
            'modulos': parse_modulos(html),
            'ensenanzaFP': parse_ensenanza_fp(html),
        }
        time.sleep(RATE_LIMIT_SEC)

    if on_progress:
        on_progress('Mòduls D', total, total)
    logger.info('d_modulos: %d cicles D processats', len(result))
    return result


def write_d_modulos(index: dict, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=dir_path, delete=False) as tmp:
        json.dump(index, tmp, ensure_ascii=False, indent=1)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)
