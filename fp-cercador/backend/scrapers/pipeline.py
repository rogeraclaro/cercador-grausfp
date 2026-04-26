"""
pipeline.py — Orquestrador del pipeline complet: scraping → escriptura atòmica.

Exposa:
  run() -> dict  -- executa el pipeline i retorna un resum estructurat

Decisions aplicades:
  D-01: Fail fast — si qualsevol Grado falla, l'excepció es propaga
  D-02: Tot o res — ofertes.json NO s'escriu si qualsevol Grado falla
  D-08: run() retorna dict estructurat per a la Fase 4 (/api/refresh-status)
  D-09: app.py NO s'ha de tocar; aquest mòdul és independent de Flask

Grados A, B, C: API REST del Buscador de Graus FP (buscador_scraper.py).
  Requereix BUSCADOR_UUID a .env (obtingut resolent el reCAPTCHA del buscador).
Grados D, E: scraping HTML de todofp.es (html_scraper.py).
"""
import json
import logging
import os
import tempfile
import time

from dotenv import load_dotenv

from scrapers.buscador_scraper import parse_buscador_all
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
    - Grados A/B/C: crida parse_grado() de buscador_scraper (API REST, 9 crides)
    - Grados D/E: scraping HTML de todofp.es
    - Afegeix 'grado' i 'id' (seqüencial 1-based) a cada registre
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
    # D-01 (Phase 6): Recarrega .env perquè un BUSCADOR_COOKIES actualitzat
    # via /api/admin/update-cookies prengui efecte sense reiniciar el servei.
    load_dotenv(override=True)

    start = time.time()

    all_records: list = []
    by_grado: dict = {}

    # Una sola Session compartida per A/B/C — todofp.es rota JSESSIONID a cada
    # resposta i la Session propaga les cookies actualitzades (D-Phase6 fix).
    buscador_data = parse_buscador_all()
    for grado_letter in ['A', 'B', 'C']:
        records = buscador_data[grado_letter]
        for r in records:
            r['grado'] = grado_letter
        by_grado[grado_letter] = len(records)
        all_records.extend(records)

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
