"""
ce_acces_scraper.py — Requisits d'accés dels cursos d'especialització (Grau E):
quins títols D hi donen accés (Pla 074).

Cada registre E d'ofertes.json té ficha_url = pàgina todofp del curs, amb una
secció plegable <div class="cdsp"><h2>Requisitos de acceso</h2>…. Formats:
  - <ul> amb un enllaç a la fitxa del D per títol  → es lliga per URL
  - <ul> sense enllaços                            → es lliga per nom normalitzat
  - un paràgraf en prosa                           → overrides manuals
Després sempre hi ha una <ul> de la via del 20% ("Si no tienes dicha
titulación…") que s'exclou.

Genera backend/data/ce_acces.json: {str(id_e): {d_ids: [id_d], unmatched: [text]}}.
Els overrides són a backend/ce_acces_overrides.json (versionat):
{ficha_url_E: [ficha_url_D, …]}. Si un E hi és, els seus títols no lligats es
consideren revisats i se substitueixen pels D de l'override.

Rate-limit 1 req/s; reintent amb backoff (5/15/45 s), com d_modulos_scraper.
"""
import json
import logging
import os
import re
import tempfile
import time
import unicodedata
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from itinerary_graph import _norm_url
from scrapers.html_scraper import HEADERS

logger = logging.getLogger(__name__)

RATE_LIMIT_SEC = 1.0
BACKOFF = (5, 15, 45)
TODOFP = 'https://www.todofp.es/'
OVERRIDES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              'ce_acces_overrides.json')

_TITULO_DE_RE = re.compile(r'^t[ií]tulo de:?\s*', re.I)
_RD_TAIL_RE = re.compile(r',?\s*establecido en el real decreto.*$', re.I)
_VIA_20_RE = re.compile(r'^si no tienes|20\s*%')
# Enumeració dins d'un sol element: "…: a) Técnico en X, establecido… b) Técnico en Y…"
_ENUM_RE = re.compile(r'(?:^|\s)[a-z]\)\s+')


def _clean(text: str) -> str:
    return ' '.join(text.split())


def normalize_title(text: str) -> str:
    """Minúscules, sense accents ni 'Título de', ni cua del Real Decreto ni punt final."""
    t = _clean(text)
    t = _TITULO_DE_RE.sub('', t)
    t = _RD_TAIL_RE.sub('', t).rstrip(' .')
    t = unicodedata.normalize('NFKD', t)
    return ''.join(c for c in t if not unicodedata.combining(c)).lower()


def parse_requisitos(html: str) -> list[dict] | None:
    """
    [{'text', 'href'|None}] dels títols de 'Requisitos de acceso', sense la via
    del 20%. En prosa, un sol element amb el text del paràgraf. None si la
    pàgina no té la secció (estructura de todofp canviada).
    """
    soup = BeautifulSoup(html, 'html.parser')
    section = next((d for d in soup.find_all('div', class_='cdsp')
                    if d.h2 and d.h2.get_text(strip=True).startswith('Requisitos de acceso')),
                   None)
    if section is None:
        return None

    items = []
    for ul in section.find_all('ul'):
        if ul.find_parent('li') is not None:
            continue
        lis = ul.find_all('li', recursive=False)
        if not lis or _VIA_20_RE.search(normalize_title(lis[0].get_text(' '))):
            continue
        for li in lis:
            text = _clean(li.get_text(' '))
            if text:
                a = li.find('a', href=True)
                items.append({'text': text, 'href': a['href'] if a else None})
    if items:
        return items

    cte = section.find('div', class_='cte') or section
    prose = _clean(cte.get_text(' '))
    return [{'text': prose, 'href': None}] if prose else []


def build_d_index(records: list[dict]) -> dict:
    """Índexs dels D per URL normalitzada i per denominació normalitzada."""
    by_url: dict = {}
    by_name: dict = {}
    for r in records:
        if r.get('grado') != 'D' or r.get('id') is None:
            continue
        u = _norm_url(r.get('ficha_url'))
        if u:
            by_url.setdefault(u, r['id'])
        by_name.setdefault(normalize_title(r.get('denominacion') or ''), r['id'])
    return {'url': by_url, 'name': by_name}


def _add(ids: list, id_) -> None:
    if id_ not in ids:
        ids.append(id_)


def resolve(items: list[dict], d_index: dict) -> tuple[list, list]:
    """(d_ids, unmatched): primer per URL de l'enllaç, si no per nom (o per parts a) b) c))."""
    d_ids: list = []
    unmatched: list = []
    for it in items:
        id_ = None
        if it['href']:
            id_ = d_index['url'].get(_norm_url(urljoin(TODOFP, it['href'])))
        if id_ is None:
            id_ = d_index['name'].get(normalize_title(it['text']))
        if id_ is not None:
            _add(d_ids, id_)
            continue
        # Sense coincidència: si és una enumeració a) b) c), cada part per nom
        # (el text d'abans de la "a)" és una introducció i es descarta).
        parts = [p.strip() for p in _ENUM_RE.split(it['text'])[1:] if p.strip()]
        for part in parts or [it['text']]:
            id_ = d_index['name'].get(normalize_title(part))
            if id_ is None:
                unmatched.append(part)
            else:
                _add(d_ids, id_)
    return d_ids, unmatched


def load_overrides(path: str = OVERRIDES_PATH) -> dict:
    """{ficha_url_E: [ficha_url_D]}; {} si el fitxer no existeix."""
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith('_')}


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
            logger.warning('fitxa E %s intent %d fallit (%s), reintent en %ds',
                           url, attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError('unreachable')


def build_ce_acces(records: list[dict], overrides: dict | None = None,
                   session=None, on_progress=None) -> dict[str, dict]:
    """
    Retorna {str(id_e): {'d_ids': [...], 'unmatched': [...]}} per als E amb
    ficha_url. Les fitxes inabastables o sense secció se salten; si cap fitxa
    no té la secció, llança RuntimeError (el pipeline conserva el fitxer anterior).
    """
    e_recs = [r for r in records if r.get('grado') == 'E' and r.get('ficha_url')]
    if not e_recs:
        return {}
    if overrides is None:
        overrides = load_overrides()
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    d_index = build_d_index(records)
    overrides_norm = {_norm_url(k): v for k, v in overrides.items()}
    result: dict[str, dict] = {}
    total = len(e_recs)
    for i, r in enumerate(e_recs):
        if on_progress and i % 10 == 0:
            on_progress('Requisits accés E', i, total)
        try:
            html = _fetch_with_retry(session, r['ficha_url'])
        except Exception as exc:
            logger.warning('fitxa E %s (id %s) inabastable, saltada: %s',
                           r['ficha_url'], r['id'], exc)
            time.sleep(RATE_LIMIT_SEC)
            continue
        time.sleep(RATE_LIMIT_SEC)

        items = parse_requisitos(html)
        if items is None:
            logger.warning('fitxa E %s (id %s) sense secció "Requisitos de acceso"',
                           r['ficha_url'], r['id'])
            continue
        d_ids, unmatched = resolve(items, d_index)
        override = overrides_norm.get(_norm_url(r['ficha_url']))
        if override is not None:
            unmatched = []
            for d_url in override:
                id_ = d_index['url'].get(_norm_url(d_url))
                if id_ is None:
                    unmatched.append(f'override sense D: {d_url}')
                else:
                    _add(d_ids, id_)
        result[str(r['id'])] = {'d_ids': d_ids, 'unmatched': unmatched}

    if on_progress:
        on_progress('Requisits accés E', total, total)
    if not result:
        raise RuntimeError('cap fitxa E amb "Requisitos de acceso": estructura de todofp canviada?')
    logger.info('ce_acces: %d cursos E processats', len(result))
    return result


def unmatched_warnings(index: dict, records: list[dict]) -> list[str]:
    """Un avís per títol no lligat, per a l'estat del refresc de l'admin."""
    e_by_id = {str(r['id']): r for r in records if r.get('grado') == 'E'}
    warnings = []
    for e_id, entry in index.items():
        rec = e_by_id.get(e_id, {})
        for text in entry['unmatched']:
            warnings.append(f"Requisits E «{rec.get('denominacion', e_id)}» "
                            f"({rec.get('ficha_url', '')}): títol no lligat a cap D: {text}")
    return warnings


def write_ce_acces(index: dict, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    os.makedirs(dir_path, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=dir_path, delete=False) as tmp:
        json.dump(index, tmp, ensure_ascii=False, indent=1)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)
