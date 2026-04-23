"""
buscador_scraper.py — Scraping de l'API del Buscador de Graus FP (todofp.es).

Fa 9 crides GET (3 grados × 3 nivells) i retorna tots els registres A, B i C
amb família i nivell correctes, incloent codis de pla antic (UF/MF).

Requereix BUSCADOR_UUID a .env — UUID obtingut resolent el reCAPTCHA del buscador.
Si caduca: obrir https://www.todofp.es/buscadorgradosfp/buscador, resoldre captcha,
copiar UUID de la variable `uuid` a la consola del navegador i actualitzar .env.

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


def _fetch(grado: str, nivel: str, uuid: str, timeout: int = 30) -> list[dict]:
    url = f"{BASE_URL}/{_ENDPOINTS[grado]}?nivel={nivel}&idFamilia=&grado={grado}&uuid={uuid}"
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(
            f"El servidor ha retornat HTML en lloc de JSON (Grado {grado} nivel {nivel}). "
            "El BUSCADOR_UUID ha caducat. Visita https://www.todofp.es/buscadorgradosfp/buscador, "
            "resol el captcha, copia la variable `uuid` de la consola del navegador "
            "i actualitza BUSCADOR_UUID al fitxer .env."
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
    uuid = os.environ.get('BUSCADOR_UUID', '')
    if not uuid:
        raise RuntimeError(
            "BUSCADOR_UUID no configurat. Visita https://www.todofp.es/buscadorgradosfp/buscador, "
            "resol el captcha i afegeix BUSCADOR_UUID=<uuid> al fitxer .env."
        )
    records = []
    for nivel in ['1', '2', '3']:
        items = _fetch(grado, nivel, uuid)
        records.extend(_map_record(r) for r in items)
        logger.info(f"Grado {grado} nivel {nivel}: {len(items)} registres")
    return records
