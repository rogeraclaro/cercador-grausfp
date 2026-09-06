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
# Pla 059 — historial i avís d'admin del snapshot FPO (SOC)
# ---------------------------------------------------------------------------

_SOC_ALERT_INTERVAL = 24 * 3600  # 1 avís per dia com a màxim


def _read_json_or(path: str, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _soc_diff_entry(prev_cursos: list, curr_cursos: list, *, ok: bool, error: str | None = None) -> dict:
    prev_ids = {c.get('idCurs') for c in (prev_cursos or []) if isinstance(c, dict)}
    curr_ids = {c.get('idCurs') for c in (curr_cursos or []) if isinstance(c, dict)}
    return {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'font': 'soc',
        'ok': ok,
        'error': error,
        'n_cursos': len(curr_cursos or []),
        'n_afegits': len(curr_ids - prev_ids) if ok else 0,
        'n_retirats': len(prev_ids - curr_ids) if ok else 0,
    }


def _soc_history_append(data_dir: str, entry: dict) -> None:
    """Insereix una entrada a data/soc_refresh_history.json (fail-soft)."""
    path = os.path.join(data_dir, 'soc_refresh_history.json')
    hist = _read_json_or(path, [])
    if not isinstance(hist, list):
        hist = []
    hist.insert(0, entry)
    try:
        _write_atomic(hist, path)
    except OSError as exc:
        logger.warning("pipeline: no s'ha pogut escriure soc_refresh_history.json: %s", exc)


def _notify_admin_soc_failure(data_dir: str, exc: Exception) -> None:
    """Avisa l'admin per email que el snapshot FPO ha fallat (rate-limit 24 h)."""
    stamp_path = os.path.join(data_dir, 'last_soc_alert.json')
    last = _read_json_or(stamp_path, {}) or {}
    if time.time() - float(last.get('ts', 0)) < _SOC_ALERT_INTERVAL:
        return
    try:
        import email_service
        to = os.environ.get('ADMIN_ALERT_EMAIL') or os.environ.get('EMAIL_FROM', 'noreply@masellas.info')
        email_service.send_email(
            to,
            'Snapshot FPO (SOC) ha fallat',
            f"El snapshot de cursos FPO del SOC ha fallat.\n\n{exc!r}\n\n"
            f"Hora (UTC): {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}",
        )
    except Exception as send_exc:  # no bloquejar el pipeline si l'email falla
        logger.warning("pipeline: no s'ha pogut avisar l'admin del fallo FPO: %s", send_exc)
    try:
        _write_atomic({'ts': time.time()}, stamp_path)
    except OSError:
        pass


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

    # --- Pla 057: relació B→C LOMLOE via fitxes todofp (no fatal) ---
    # Es fa just després d'escriure ofertes.json perquè els ficha_id acaben de
    # refrescar-se (canvien a cada refresc) i perquè triga ~10–16 min: les
    # ofertes ja són fresques encara que això falli o s'aturi.
    _report('Relació B→C LOMLOE (fitxes todofp)')
    try:
        from scrapers.bc_lomloe_scraper import build_bc_lomloe, write_bc_lomloe
        bc_lomloe = build_bc_lomloe(
            all_records,
            on_progress=lambda phase, i, n: _report(f'{phase} {i}/{n}'),
        )
        bc_lomloe_path = os.path.join(os.path.dirname(DATA_PATH), 'bc_lomloe.json')
        write_bc_lomloe(bc_lomloe, bc_lomloe_path)
        logger.info("pipeline: bc_lomloe.json escrit (%d certificats C)", len(bc_lomloe))
    except Exception as exc:
        logger.warning("pipeline: build_bc_lomloe ha fallat (no fatal): %s", exc)

    # --- Pla 058: mòduls de cada cicle D via fitxes todofp (no fatal) ---
    _report('Mòduls dels cicles D (fitxes todofp)')
    try:
        from scrapers.d_modulos_scraper import build_d_modulos, write_d_modulos
        d_modulos = build_d_modulos(
            all_records,
            on_progress=lambda phase, i, n: _report(f'{phase} {i}/{n}'),
        )
        write_d_modulos(d_modulos, os.path.join(os.path.dirname(DATA_PATH), 'd_modulos.json'))
        logger.info("pipeline: d_modulos.json escrit (%d cicles D)", len(d_modulos))
    except Exception as exc:
        logger.warning("pipeline: build_d_modulos ha fallat (no fatal): %s", exc)

    # --- Pla 059: cursos FPO del SOC (Catalunya) via Algolia (no fatal) ---
    _report('Cursos FPO (SOC Catalunya)')
    try:
        from scrapers.soc_scraper import build_soc_data, write_soc_data
        _soc_dir = os.path.dirname(DATA_PATH)
        _prev_cursos = _read_json_or(os.path.join(_soc_dir, 'soc_cursos.json'), [])
        soc = build_soc_data()
        write_soc_data(soc, _soc_dir)
        logger.info("pipeline: soc_*.json escrit (%d cursos, %d especialitats, %d centres)",
                    len(soc['cursos']), len(soc['especs']), len(soc['centres']))
        _soc_history_append(_soc_dir, _soc_diff_entry(_prev_cursos, soc['cursos'], ok=True))
    except Exception as exc:
        logger.warning("pipeline: build_soc_data ha fallat (no fatal): %s", exc)
        _soc_dir = os.path.dirname(DATA_PATH)
        _soc_history_append(_soc_dir, _soc_diff_entry([], [], ok=False, error=repr(exc)))
        _notify_admin_soc_failure(_soc_dir, exc)

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
