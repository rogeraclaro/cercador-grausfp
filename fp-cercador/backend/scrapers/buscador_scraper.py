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


def _fetch(grado: str, nivel: str, cookies: str, timeout: int = 30) -> list[dict]:
    url = f"{BASE_URL}/{_ENDPOINTS[grado]}?nivel={nivel}&idFamilia=&grado={grado}&uuid="
    headers = {**HEADERS, "Cookie": cookies}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(
            f"El servidor ha retornat HTML en lloc de JSON (Grado {grado} nivel {nivel}). "
            "La sessió BUSCADOR_COOKIES ha caducat. Segueix les instruccions del docstring "
            "per obtenir les cookies noves i actualitza BUSCADOR_COOKIES al fitxer .env."
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
    }


def parse_grado(grado: str) -> list[dict]:
    """Retorna tots els registres d'un grado (A, B o C) fent 3 crides per nivell."""
    cookies = os.environ.get('BUSCADOR_COOKIES', '')
    if not cookies:
        raise RuntimeError(
            "BUSCADOR_COOKIES no configurat. Segueix les instruccions del docstring "
            "per obtenir les cookies del navegador i afegeix BUSCADOR_COOKIES=<valor> al fitxer .env."
        )
    records = []
    for nivel in ['1', '2', '3']:
        items = _fetch(grado, nivel, cookies)
        records.extend(_map_record(r) for r in items)
        logger.info(f"Grado {grado} nivel {nivel}: {len(items)} registres")
    return records
