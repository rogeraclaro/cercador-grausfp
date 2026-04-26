"""
buscador_scraper.py — Scraping de l'API del Buscador de Graus FP (todofp.es).

Fa 9 crides GET (3 grados × 3 nivells) i retorna tots els registres A, B i C
amb família i nivell correctes, incloent codis de pla antic (UF/MF).

Requereix BUSCADOR_COOKIES a .env — valor de la capçalera Cookie obtingut del
navegador després de resoldre el reCAPTCHA del buscador:
  1. Obrir https://www.todofp.es/buscadorgradosfp/buscador
  2. Resoldre el reCAPTCHA
  3. Fer una cerca (triant opcions als selects i clicant Buscar)
  4. DevTools → Network → Fetch/XHR → clic dret sobre buscadorGeneralA → Copy as cURL
  5. Copiar el valor de -b '...' i posar-lo com a BUSCADOR_COOKIES=... al .env

Si la sessió caduca, el pipeline retornarà HTML. Repetir els passos anteriors.

Cada registre retornat té exactament:
  {codigo, denominacion, familia, nivel, plan_antiguo, observaciones}

Camp 'id' i 'grado' els afegeix pipeline.py, NO aquest mòdul.
"""
import os
import re
import logging

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_URL = 'https://www.todofp.es/buscadorgradosfp'

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.todofp.es/buscadorgradosfp/buscador",
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


def _dump_failure(resp, grado: str, nivel: str, sent_headers: dict) -> dict:
    """Guarda la resposta sencera i retorna un diccionari amb metadades clau."""
    snippet = (resp.text or "")[:500]
    try:
        os.makedirs(os.path.dirname(_FAILURE_DUMP_PATH), exist_ok=True)
        with open(_FAILURE_DUMP_PATH, "w", encoding="utf-8") as f:
            f.write(f"<!-- Grado {grado} nivel {nivel} | status {resp.status_code} -->\n")
            f.write(f"<!-- Sent UA: {sent_headers.get('User-Agent', '')} -->\n")
            f.write(resp.text or "")
    except OSError as exc:
        logger.error("No s'ha pogut guardar last_failure.html: %s", exc)
    return {
        "status": resp.status_code,
        "content_type": resp.headers.get("Content-Type", ""),
        "set_cookie": resp.headers.get("Set-Cookie", ""),
        "location": resp.headers.get("Location", ""),
        "snippet": snippet,
    }


def _parse_cookie_string(s: str) -> dict:
    """Converteix 'name1=value1; name2=value2' en {name1: value1, name2: value2}."""
    result = {}
    for part in s.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        result[name.strip()] = value.strip()
    return result


def _fetch(session: requests.Session, grado: str, nivel: str, timeout: int = 30) -> list[dict]:
    url = f"{BASE_URL}/{_ENDPOINTS[grado]}?nivel={nivel}&idFamilia=&grado={grado}&uuid="
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        info = _dump_failure(resp, grado, nivel, dict(session.headers))
        raise RuntimeError(
            f"Resposta no-JSON per Grado {grado} nivel {nivel} | "
            f"HTTP {info['status']} | Content-Type: {info['content_type']} | "
            f"Set-Cookie: {info['set_cookie'][:120]} | "
            f"Location: {info['location']} | "
            f"UA enviat: {session.headers.get('User-Agent', '')[:80]} | "
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
    """Scraping de A, B i C amb una única requests.Session per propagar Set-Cookie.

    todofp.es rota el JSESSIONID després de cada petició exitosa (defensa
    anti-session-fixation). Cal una Session compartida perquè les 9 crides
    actualitzin automàticament les cookies del jar.
    """
    load_dotenv(override=True)
    cookies_str = os.environ.get('BUSCADOR_COOKIES', '')
    if not cookies_str:
        raise RuntimeError(
            "BUSCADOR_COOKIES no configurat. Segueix les instruccions del docstring "
            "per obtenir les cookies del navegador i afegeix BUSCADOR_COOKIES=<valor> al fitxer .env."
        )
    session = requests.Session()
    session.headers.update(HEADERS)
    for name, value in _parse_cookie_string(cookies_str).items():
        session.cookies.set(name, value, domain='www.todofp.es', path='/')

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
