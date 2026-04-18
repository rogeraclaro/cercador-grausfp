"""
pipeline.py — Orquestrador del pipeline complet: descàrrega → parse → escriptura atòmica.

Exposa:
  run() -> dict  -- executa el pipeline i retorna un resum estructurat
  HEADERS: dict  -- headers HTTP requerits per a todofp.es
  PDF_URLS: dict -- URLs dels PDFs dels Grados A, B, C

Decisions aplicades:
  D-01: Fail fast — si qualsevol Grado falla, l'excepció es propaga
  D-02: Tot o res — ofertes.json NO s'escriu si qualsevol Grado falla
  D-03: Sense cache — cada PDF s'elimina un cop analitzat (bloc finally)
  D-08: run() retorna dict estructurat per a la Fase 4 (/api/refresh-status)
  D-09: app.py NO s'ha de tocar; aquest mòdul és independent de Flask
"""
import json
import logging
import os
import tempfile
import time

import requests

from scrapers.pdf_scraper import parse_grado_a, parse_grado_b, parse_grado_c
from scrapers.html_scraper import (
    parse_grado_d_basico,
    parse_grado_d_medio,
    parse_grado_d_superior,
    parse_grado_e,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": (
        "https://www.todofp.es/catalogos-registros-sistema-fp/"
        "catalogo-nacional-ofertas-sistema.html"
    ),
}

PDF_URLS = {
    'A': 'https://www.todofp.es/dam/jcr:a8580dd0-8106-4387-ae2a-8c6c1f23fa91/catalogo-grados-a.pdf',
    'B': 'https://www.todofp.es/dam/jcr:fbe95da3-7507-458a-ab0d-4202beea8d28/catalogo-grados-b.pdf',
    'C': 'https://www.todofp.es/dam/jcr:8b85fd78-c6d5-406f-ade8-891abd96613f/catalogo-grados-c.pdf',
}

HTML_URLS = {
    'D_BASICO':   os.getenv('URL_GRADO_D_BASICO',   'https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html'),
    'D_MEDIO':    os.getenv('URL_GRADO_D_MEDIO',    'https://www.todofp.es/que-estudiar/grados-d/grado-medio.html'),
    'D_SUPERIOR': os.getenv('URL_GRADO_D_SUPERIOR', 'https://www.todofp.es/que-estudiar/grados-d/grado-superior.html'),
    'E':          os.getenv('URL_GRADO_E',          'https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html'),
}

# Path absolut de la sortida — relatiu a la ubicació d'aquest fitxer per funcionar des de qualsevol cwd
DATA_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'ofertes.json')
)


# ---------------------------------------------------------------------------
# Funcions privades
# ---------------------------------------------------------------------------


def _download_pdf(url: str, timeout: int = 120) -> str:
    """
    Descarrega PDF a fitxer temporal i retorna el path.
    El caller és responsable d'eliminar-lo (D-03).

    IMPORTANT: Mai usar requests.head() — retorna 403. Sempre GET (Pitfall 3 RESEARCH.md).
    """
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()  # 4xx/5xx → excepció (fail fast D-01)
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(resp.content)
        return tmp.name


def _write_atomic(data: list, output_path: str) -> None:
    """
    Escriu JSON de manera atòmica: fitxer temporal al mateix directori + os.replace().

    os.replace() és una operació POSIX rename — atòmica en sistemes Unix.
    Si el disc és ple, NamedTemporaryFile elevarà OSError i el fitxer original roman intacte
    (T-02-06 del threat model).
    """
    dir_path = os.path.dirname(output_path)
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', suffix='.json',
        dir=dir_path, delete=False
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def run() -> dict:
    """
    Executa el pipeline complet per Grados A, B, C, D i E.

    Comportament:
    - Descarrega cada PDF amb GET + HEADERS (D-01 fail fast)
    - Crida el parser corresponent (parse_grado_a/b/c)
    - Afegeix 'grado' (lletra) i 'id' (seqüencial 1-based) a cada registre
    - Elimina el PDF temporal en el bloc finally (D-03, amb o sense error)
    - Si qualsevol Grado falla → excepció propagada, ofertes.json NO s'escriu (D-02)
    - Si tots els Grados s'extreuen → escriu ofertes.json de forma atòmica

    Retorna dict estructurat per a la Fase 4 (/api/refresh-status):
    {
        "total": int,
        "by_grado": {"A": int, "B": int, "C": int, "D": int, "E": int},
        "errors": [],
        "duration_seconds": float,
    }
    """
    start = time.time()

    parsers = {
        'A': (PDF_URLS['A'], parse_grado_a),
        'B': (PDF_URLS['B'], parse_grado_b),
        'C': (PDF_URLS['C'], parse_grado_c),
    }

    all_records: list = []
    by_grado: dict = {}

    for grado_letter, (url, parser_fn) in parsers.items():
        pdf_path = None
        try:
            pdf_path = _download_pdf(url)
            records = parser_fn(pdf_path)
            for r in records:
                r['grado'] = grado_letter
            by_grado[grado_letter] = len(records)
            all_records.extend(records)
        finally:
            # D-03: eliminar el PDF temporal sempre, fins i tot en error
            if pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)
        # Si _download_pdf() o parser_fn() fallen: l'excepció es propaga aquí (D-01)
        # _write_atomic no s'arriba a cridar → ofertes.json roman intacte (D-02)

    # -----------------------------------------------------------------------
    # Bloc HTML: Grados D (Basico/Medio/Superior) i E
    # Ordre D-03: IDs seqüencials A → B → C → D → E (garantit per l'ordre d'aquest
    # bloc DESPRÉS del loop PDF i ABANS de l'enumerate d'IDs).
    # Fail fast D-01: qualsevol excepció de parse_grado_* propaga i _write_atomic
    # NO es crida (ofertes.json roman intacte).
    # -----------------------------------------------------------------------
    html_parsers = [
        (HTML_URLS['D_BASICO'],   parse_grado_d_basico,   'D'),
        (HTML_URLS['D_MEDIO'],    parse_grado_d_medio,    'D'),
        (HTML_URLS['D_SUPERIOR'], parse_grado_d_superior, 'D'),
        (HTML_URLS['E'],          parse_grado_e,          'E'),
    ]

    html_by_grado: dict = {'D': 0, 'E': 0}
    for url, parser_fn, grado_letter in html_parsers:
        records = parser_fn(url)  # fail fast: excepció propagada (D-01)
        for r in records:
            r['grado'] = grado_letter
        html_by_grado[grado_letter] += len(records)
        all_records.extend(records)

    by_grado['D'] = html_by_grado['D']
    by_grado['E'] = html_by_grado['E']

    # Afegir id seqüencial 1-based
    for i, record in enumerate(all_records, start=1):
        record['id'] = i

    _write_atomic(all_records, DATA_PATH)

    return {
        "total": len(all_records),
        "by_grado": by_grado,
        "errors": [],
        "duration_seconds": round(time.time() - start, 2),
    }
