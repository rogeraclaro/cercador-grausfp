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
  Cookies obtingudes automàticament via bootstrap GET (sense captcha ni config).
Grados D, E: scraping HTML de todofp.es (html_scraper.py).
"""
import json
import logging
import os
import tempfile
import time

from dotenv import load_dotenv

from scrapers.buscador_scraper import parse_buscador_all
from scrapers.families import FAMILY_ALIASES, PREFIX_MAP
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


def run(on_progress=None) -> dict:
    """
    Executa el pipeline complet per Grados A, B, C, D i E.

    on_progress(phase: str) — callback opcional cridat a l'inici de cada fase
    (Buscador A/B/C, cada bloc HTML de D/E, enriquiment de certificats). Mai
    ha de trencar el pipeline si falla, per això els errors s'ignoren.

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
    # Recarrega .env a cada run perquè canvis de configuració (p. ex. URLs
    # dels Grados D/E) prenguin efecte sense reiniciar el servei.
    load_dotenv(override=True)

    start = time.time()

    def _report(phase: str) -> None:
        if on_progress:
            try:
                on_progress(phase)
            except Exception:
                pass

    all_records: list = []
    by_grado: dict = {}

    # Una sola Session compartida per A/B/C — todofp.es rota JSESSIONID a cada
    # resposta i la Session propaga les cookies actualitzades (D-Phase6 fix).
    _report('Buscador Graus A/B/C')
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
        (HTML_URLS['D_BASICO'],   parse_grado_d_basico,   'D', 'Grau D bàsic'),
        (HTML_URLS['D_MEDIO'],    parse_grado_d_medio,    'D', 'Grau D mitjà'),
        (HTML_URLS['D_SUPERIOR'], parse_grado_d_superior, 'D', 'Grau D superior'),
        (HTML_URLS['E'],          parse_grado_e,          'E', 'Grau E'),
    ]

    html_by_grado: dict = {'D': 0, 'E': 0}
    for url, parser_fn, grado_letter, label in html_parsers:
        _report(label)
        records = parser_fn(url)  # fail fast: excepció propagada (D-01)
        for r in records:
            r['grado'] = grado_letter
        html_by_grado[grado_letter] += len(records)
        all_records.extend(records)

    by_grado['D'] = html_by_grado['D']
    by_grado['E'] = html_by_grado['E']

    # Enriquiment Grado C LOE (plan_antiguo=True) amb dades del buscador de certificats
    _report('Enriquiment certificats (Grau C pla antic)')
    try:
        from scrapers.certificados_scraper import fetch_all as fetch_certificados, enrich_record
        cert_data = fetch_certificados()
        for record in all_records:
            if record.get('grado') == 'C' and record.get('plan_antiguo'):
                enrichment = cert_data.get(record['codigo'])
                if enrichment:
                    record.update(enrich_record(record, enrichment))
        logger.info("Enriquiment Grado C: %d certificats processats", len(cert_data))

        # --- F5: Ciclos FP (C→D) ---
        try:
            from scrapers.certificados_scraper import build_ciclos_index
            ciclos_index = build_ciclos_index(cert_data, all_records=all_records)
            ciclos_path = os.path.join(os.path.dirname(DATA_PATH), 'ciclos_fp.json')
            with open(ciclos_path, 'w', encoding='utf-8') as f:
                import json as _json
                _json.dump(ciclos_index, f, ensure_ascii=False)
            logger.info("pipeline: ciclos_fp.json escrit (%d entrades)", len(ciclos_index))
        except Exception as exc:
            logger.warning("pipeline: build_ciclos_index ha fallat (no fatal): %s", exc)

    except Exception as exc:
        logger.warning("Enriquiment Grado C fallat (continua sense dades extra): %s", exc)

    # Normalitza noms de família per garantir unicitat entre fonts (A–E).
    for record in all_records:
        record['familia'] = FAMILY_ALIASES.get(record['familia'], record['familia'])

    # Detecta famílies desconegudes (no al catàleg canònic).
    _known = set(PREFIX_MAP.values())
    _unknown = {r['familia'] for r in all_records if r['familia'] not in _known}
    for fam in sorted(_unknown):
        logger.warning("Família nova detectada al refresh: %r — afegeix-la a FAMILY_ALIASES o PREFIX_MAP", fam)

    # Afegir id seqüencial 1-based
    for i, record in enumerate(all_records, start=1):
        record['id'] = i

    _write_atomic(all_records, DATA_PATH)

    families = sorted({r['familia'] for r in all_records if r['familia'] != 'Desconeguda'})
    denominacions = sorted({r['denominacion'] for r in all_records if r.get('denominacion')})
    denominacions_by_grado = {
        g: sorted({r['denominacion'] for r in all_records if r.get('grado') == g and r.get('denominacion')})
        for g in ['A', 'B', 'C', 'D', 'E']
    }

    meta_by_grado = {
        g: [
            {"denominacio": r["denominacion"], "familia": r["familia"], "nivel": r["nivel"]}
            for r in all_records
            if r.get("grado") == g and r.get("denominacion")
        ]
        for g in ["A", "B", "C", "D", "E"]
    }

    return {
        "total": len(all_records),
        "by_grado": by_grado,
        "families": families,
        "denominacions": denominacions,
        "denominacions_by_grado": denominacions_by_grado,
        "meta_by_grado": meta_by_grado,           # NOU — per a F3 alertes
        "errors": [],
        "unknown_families": sorted(_unknown),
        "duration_seconds": round(time.time() - start, 2),
    }
