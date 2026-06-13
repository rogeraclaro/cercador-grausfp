"""
certificados_scraper.py — Enriquiment dels Grado C (LOE) amb dades del
Buscador de Certificados de Profesionalidad (todofp.es).

Flow:
  1. GET https://www.todofp.es/buscadorcertificados/buscador
     → obté cookie __Host-todofp.es (sense JSESSIONID)
  2. POST /busquedaCP (paso=600) → HTML amb tots els certificats
     → extreu certID i duracion_horas per a cadascun

La font retorna HTML, no JSON. BeautifulSoup per al parsing.
"""
import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_CERT_URL = 'https://www.todofp.es/buscadorcertificados'
BASE_DAM = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': BASE_CERT_URL + '/buscador',
}

_HOURS_RE = re.compile(r'(\d+)\s*horas')


def _bootstrap_session(timeout: int = 30) -> requests.Session:
    """GET /buscador → cookie __Host-todofp.es (sense JSESSIONID)."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(BASE_CERT_URL + '/buscador', timeout=timeout)
    resp.raise_for_status()
    return session


def fetch_all() -> dict[str, dict]:
    """
    POST /busquedaCP (paso=600) → dict keyed by codigo.
    Cada valor: {'cert_id': int, 'duracion_horas': int | None}
    """
    session = _bootstrap_session()
    payload = {
        'limite': '0',
        'paso': '600',
        'total': '0',
        'codigo': '',
        'denominacion': '',
        'familia': '0',
        'nivel': '0',
    }
    resp = session.post(BASE_CERT_URL + '/busquedaCP', data=payload, timeout=60)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = soup.select('table.tabla-resultados tbody tr')
    logger.info("fetch_all: %d files trobades a la resposta HTML", len(rows))

    result = {}
    for row in rows:
        id_input = row.find('input', {'name': 'certificadoID'})
        cod_td = row.find('td', class_='colCodigo')
        dur_td = row.find('td', {'headers': 'columna-cuatro'})

        if not id_input or not cod_td:
            continue

        cert_id_raw = id_input.get('value', '')
        codigo = cod_td.get_text(strip=True)

        try:
            cert_id = int(cert_id_raw)
        except (ValueError, TypeError):
            logger.warning("cert_id no numèric per a %s: %r", codigo, cert_id_raw)
            continue

        duracion_horas = None
        if dur_td:
            p = dur_td.find('p')
            if p:
                m = _HOURS_RE.search(p.get_text(strip=True))
                if m:
                    duracion_horas = int(m.group(1))

        result[codigo] = {'cert_id': cert_id, 'duracion_horas': duracion_horas}

    return result


def enrich_record(record: dict, cert_data: dict) -> dict:
    """
    Afegeix camps derivats a un registre Grado C plan_antiguo=True.
    Rep 'record' (el registre d'ofertes.json) i 'cert_data' (de fetch_all).
    Retorna el registre enriquit (no modifica l'original in-place).
    """
    codigo_lc = record['codigo'].lower()
    nivel_n = str(record['nivel'])

    return {
        **record,
        'duracion_horas': cert_data['duracion_horas'],
        'cert_id_buscador': cert_data['cert_id'],
        'url_anexo_pdf': f"{BASE_DAM}/anexos/{codigo_lc}.pdf",
        'url_europass_es': f"{BASE_DAM}/europass/n{nivel_n}-{codigo_lc}-es-pub.pdf",
        'url_europass_en': f"{BASE_DAM}/europass/n{nivel_n}-{codigo_lc}-in-pub.pdf",
    }
