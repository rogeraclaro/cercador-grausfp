"""
buscador_scraper.py — Scraping de l'API del Buscador de Graus FP (todofp.es).

Flow auto-cookies (sense captcha, sense intervenció humana):
  1. GET https://www.todofp.es/buscadorgradosfp/buscador
     → el servidor retorna l'HTML de la pàgina i emet JSESSIONID + __Host-todofp.es
  2. 9 GETs (3 grados × 3 nivells) a buscadorGeneralA|B|C reusant la Session
     → l'API retorna JSON amb tots els registres

Per què el captcha no és necessari:
  El captcha és client-side (variable JS `mostrarCaptcha=false`, comptador `times`
  en una sola pàgina, max 50). Cada execució del scraper és una sessió nova de
  Python, així que el comptador mai s'incrementa al servidor. El uuid pot anar
  buit a la query string i la API el accepta.

Si en algun moment el servidor canvia i exigeix el captcha de veritat, la
resposta serà HTML i `_dump_failure` desarà el cos sencer a data/last_failure.html
per a diagnòstic.

Cada registre retornat té exactament:
  {codigo, denominacion, familia, nivel, plan_antiguo, observaciones, ficha_id}

Camp 'id' i 'grado' els afegeix pipeline.py, NO aquest mòdul.
"""
import os
import re
import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.todofp.es/buscadorgradosfp'
BOOTSTRAP_URL = f'{BASE_URL}/buscador'

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": BOOTSTRAP_URL,
}

_ENDPOINTS = {
    'A': 'buscadorGeneralA',
    'B': 'buscadorGeneralB',
    'C': 'buscadorGeneralC',
}

_NEW_CODE_RE = re.compile(r'^[A-Z]{2,4}_[ABC]_')


def _is_old_plan(codigo: str) -> bool:
    return not bool(_NEW_CODE_RE.match(codigo))


_FAILURE_DUMP_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "last_failure.html")
)


def _dump_failure(resp, context: str) -> dict:
    """Guarda la resposta sencera i retorna metadades clau per al missatge d'error."""
    snippet = (resp.text or "")[:500]
    try:
        os.makedirs(os.path.dirname(_FAILURE_DUMP_PATH), exist_ok=True)
        with open(_FAILURE_DUMP_PATH, "w", encoding="utf-8") as f:
            f.write(f"<!-- {context} | status {resp.status_code} -->\n")
            f.write(resp.text or "")
    except OSError as exc:
        logger.error("No s'ha pogut guardar last_failure.html: %s", exc)
    return {
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "snippet": snippet,
    }


def _bootstrap_session(timeout: int = 30) -> requests.Session:
    """GET inicial a /buscador per obtenir cookies fresques (JSESSIONID + __Host-todofp.es)."""
    session = requests.Session()
    session.headers.update(HEADERS)
    resp = session.get(BOOTSTRAP_URL, timeout=timeout)
    resp.raise_for_status()
    if 'JSESSIONID' not in session.cookies:
        info = _dump_failure(resp, "bootstrap GET /buscador")
        raise RuntimeError(
            f"Bootstrap no ha retornat JSESSIONID | HTTP {info['status']} | "
            f"Content-Type: {info['content_type']} | Snippet: {info['snippet']}"
        )
    return session


def _fetch(session: requests.Session, grado: str, nivel: str, timeout: int = 30) -> list[dict]:
    url = f"{BASE_URL}/{_ENDPOINTS[grado]}?nivel={nivel}&idFamilia=&grado={grado}&uuid="
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        info = _dump_failure(resp, f"Grado {grado} nivel {nivel}")
        raise RuntimeError(
            f"Resposta no-JSON per Grado {grado} nivel {nivel} | "
            f"HTTP {info['status']} | Content-Type: {info['content_type']} | "
            f"Snippet: {info['snippet']}"
        )
    if not isinstance(data, list):
        raise RuntimeError(f"Resposta inesperada de l'API per Grado {grado} nivel {nivel}: {type(data)}")
    return data


def _map_record(item: dict) -> dict:
    return {
        'codigo': item['codigo'],
        'denominacion': item.get('denominacion') or '',
        'familia': item.get('familia') or 'Desconeguda',
        'nivel': item.get('nivel'),
        'plan_antiguo': _is_old_plan(item['codigo']),
        'observaciones': '',
        'ficha_id': item.get('id'),
    }


def parse_buscador_all() -> dict:
    """Scraping de A, B i C amb cookies obtingudes automàticament del bootstrap."""
    session = _bootstrap_session()

    result = {}
    for grado in ['A', 'B', 'C']:
        records = []
        for nivel in ['1', '2', '3']:
            items = _fetch(session, grado, nivel)
            records.extend(_map_record(r) for r in items)
            logger.info(f"Grado {grado} nivel {nivel}: {len(items)} registres")
        result[grado] = records
    return result


def parse_grado(grado: str) -> list[dict]:
    """Compatibilitat: scraping d'un sol grado. Internament usa parse_buscador_all."""
    return parse_buscador_all()[grado]
