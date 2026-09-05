"""
centres_scraper.py — Scraping de centres de la Font 1 (Registre Estatal Entitats de Formació FP).

Flow:
  1. GET /buscarPublico → JSESSIONID (sense captcha)
  2. Per cada oferta C LOE: GET /datosTablaPublico?ofertaCodigo={code} → JSON centres
  3. Per cada oferta C LOMLOE: GET /datosTablaPublico?ofertaCodigo={code} (codi complet
     FAM_C_NNN_NL; el filtre és LIKE, mai passar prefixos)
  4. Per cada oferta D: GET /datosTablaPublico?ofertaDenominacion={short}&gradoProfesional=4
  5. Per cada oferta E: GET /datosTablaPublico?ofertaDenominacion={short}&gradoProfesional=5

Genera:
  backend/data/centres.json       — catàleg de centres únics
  backend/data/oferta_centres.json — relació {oferta_key: [codigoMinisterio, ...]}

Clau dels resultats:
  - Grado C LOE:    clau = código SEPE (ex. "ADGG0408")
  - Grado C LOMLOE: clau = id intern de l'oferta (com D/E), perquè el frontend
                    ja envia id= per a tot el que no sigui C LOE
  - Grado D/E:      clau = id intern de l'oferta a ofertes.json (ex. "12664")

Execució directa: python3 -m backend.scrapers.centres_scraper
Rate-limit: 1 req/s (~20 min per al conjunt complet de ~1.212 consultes).
"""

import json
import logging
import os
import re
import time
from datetime import date

import requests

logger = logging.getLogger(__name__)

_BASE = 'https://registrosfp.educacion.gob.es/registroestatalentidadesformacion'
_BOOTSTRAP_URL = f'{_BASE}/buscarPublico'
_DATA_URL = f'{_BASE}/datosTablaPublico'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': _BOOTSTRAP_URL,
}

_DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
_OFERTES_PATH = os.path.join(_DATA_DIR, 'ofertes.json')
_CENTRES_PATH = os.path.join(_DATA_DIR, 'centres.json')
_OFERTA_CENTRES_PATH = os.path.join(_DATA_DIR, 'oferta_centres.json')

RATE_LIMIT_SEC = 1.0
PAGE_SIZE = 10000
SESSION_REFRESH_EVERY = 200  # re-bootstrap cada N consultes

_DENOM_PREFIXES = [
    'Título Profesional Básico en ',
    'Técnico Superior en ',
    'Técnico en ',
    'Curso de Especialización en ',
    'Curso de especialización en ',
]


# ── sessió ──────────────────────────────────────────────────────────────────

def _bootstrap() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(_BOOTSTRAP_URL, timeout=30)
    resp.raise_for_status()
    if 'JSESSIONID' not in session.cookies:
        raise RuntimeError(
            f'Bootstrap sense JSESSIONID | HTTP {resp.status_code} | '
            f'{resp.text[:200]}'
        )
    return session


# ── fetch ────────────────────────────────────────────────────────────────────

def _fetch(session: requests.Session, params: dict, timeout: int = 60) -> list:
    for attempt in range(3):
        try:
            resp = session.get(_DATA_URL, params=params, timeout=timeout)
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                logger.warning('429 rate-limited, esperant %ds', wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data.get('data', [])
        except (requests.RequestException, ValueError) as exc:
            logger.warning('Error intent %d: %s', attempt + 1, exc)
            if attempt == 2:
                raise
            time.sleep(5)
    return []


# ── parse ────────────────────────────────────────────────────────────────────

def _parse_centre(row: list) -> dict:
    """
    row = [codigo, codigoMinisterio, nombre, localitat, cp, provincia,
           buit, ccaa, direccio, telefon, email, centrorcd, letrasgrado]
    """
    return {
        'id': row[1],
        'codigo': row[0] or None,
        'nombre': row[2],
        'localitat': row[3],
        'cp': row[4],
        'provincia': row[5],
        'ccaa': row[7],
        'direccio': row[8] or None,
        'telefon': row[9] or None,
        'email': row[10] or None,
        'tipo': 'rcd' if row[11] == '1' else 'acreditat',
        'url_web': None,
        'updated_at': date.today().isoformat(),
    }


_ACCESO_RE = re.compile(r'\s*\(Acceso\s+[GBS][MS]/?[GBS]?[MS]?\)\s*$', re.IGNORECASE)


def _short_denom(denominacion: str) -> str:
    """Extreu la part distintiva eliminant suffixos (Acceso GM/GS) i prefixos genèrics."""
    # Eliminar "(Acceso GM)", "(Acceso GS)", "(Acceso GM/GS)" etc. dels Cursos E
    denom = _ACCESO_RE.sub('', denominacion).strip()
    for prefix in _DENOM_PREFIXES:
        if denom.startswith(prefix):
            return denom[len(prefix):]
    return denom


# ── càrrega ofertes ──────────────────────────────────────────────────────────

def _load_ofertes() -> tuple[list, list, list, list]:
    with open(_OFERTES_PATH, encoding='utf-8') as f:
        all_ofertes = json.load(f)
    c_loe = [r for r in all_ofertes if r.get('grado') == 'C' and r.get('plan_antiguo')]
    c_lomloe = [r for r in all_ofertes if r.get('grado') == 'C' and not r.get('plan_antiguo')]
    d_list = [r for r in all_ofertes if r.get('grado') == 'D']
    e_list = [r for r in all_ofertes if r.get('grado') == 'E']
    return c_loe, c_lomloe, d_list, e_list


def _load_existing_centres() -> dict[str, dict]:
    """Carrega el catàleg de centres existent, si n'hi ha. Fail-soft: si el
    fitxer no existeix o està corrupte, torna un catàleg buit en lloc de
    trencar el scraping."""
    if not os.path.exists(_CENTRES_PATH):
        return {}
    try:
        with open(_CENTRES_PATH, encoding='utf-8') as f:
            centres_list = json.load(f)
        return {c['id']: c for c in centres_list}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning('No s\'ha pogut carregar el catàleg existent (%s) — es comença de zero', exc)
        return {}


# ── pipeline principal ───────────────────────────────────────────────────────

def scrape_centres(on_progress=None) -> tuple[dict, dict]:
    """
    Retorna:
      centres_by_id: {codigoMinisterio: centre_dict}
      oferta_centres: {oferta_key: [codigoMinisterio, ...]}

    on_progress(phase: str, current: int, total: int, unique_centres: int) —
    callback opcional cridat periòdicament (a l'inici de cada fase i cada
    50/10 ofertes processades). Mai ha de trencar el scraping si falla.
    """
    c_loe, c_lomloe, d_list, e_list = _load_ofertes()
    session = _bootstrap()

    # Catàleg acumulatiu: comença amb el que ja hi havia (si hi ha) perquè un
    # centre que deixi d'impartir cap oferta es mantingui amb les seves
    # últimes dades conegudes, en lloc de desaparèixer del catàleg. Els
    # centres que sí es tornen a veure sobreescriuen les seves dades amb les
    # fresques més avall (centres_by_id[c['id']] = c a _do_fetch).
    centres_by_id: dict[str, dict] = _load_existing_centres()
    oferta_centres: dict[str, list[str]] = {}
    req_count = 0

    def _report(phase: str, current: int, total: int) -> None:
        if on_progress:
            try:
                on_progress(phase, current, total, len(centres_by_id))
            except Exception:
                pass

    def _do_fetch(params: dict) -> list[str]:
        nonlocal session, req_count
        if req_count > 0 and req_count % SESSION_REFRESH_EVERY == 0:
            logger.info('Re-bootstrapping sessió (consulta %d)', req_count)
            session = _bootstrap()
        rows = _fetch(session, params)
        req_count += 1
        time.sleep(RATE_LIMIT_SEC)
        ids = []
        for row in rows:
            c = _parse_centre(row)
            centres_by_id[c['id']] = c
            ids.append(c['id'])
        return ids

    # ── Grado C LOE (per ofertaCodigo) ──
    logger.info('=== Grado C LOE: %d ofertes ===', len(c_loe))
    _report('Grau C (pla antic)', 0, len(c_loe))
    for i, oferta in enumerate(c_loe):
        codigo = oferta['codigo']
        ids = _do_fetch({
            'ofertaCodigo': codigo,
            'iDisplayLength': PAGE_SIZE,
            'iDisplayStart': 0,
            'draw': 1,
        })
        oferta_centres[codigo] = ids
        if (i + 1) % 50 == 0:
            logger.info('C LOE %d/%d — centres únics: %d', i + 1, len(c_loe), len(centres_by_id))
            _save(centres_by_id, oferta_centres)
            _report('Grau C (pla antic)', i + 1, len(c_loe))

    logger.info('C LOE complet: %d centres únics', len(centres_by_id))
    _save(centres_by_id, oferta_centres)
    _report('Grau C (pla antic)', len(c_loe), len(c_loe))

    # ── Grado C LOMLOE (per ofertaCodigo, clau = id intern com D/E) ──
    logger.info('=== Grado C LOMLOE: %d ofertes ===', len(c_lomloe))
    _report('Grau C (pla nou)', 0, len(c_lomloe))
    for i, oferta in enumerate(c_lomloe):
        key = str(oferta['id'])
        ids = _do_fetch({
            'ofertaCodigo': oferta['codigo'],
            'iDisplayLength': PAGE_SIZE,
            'iDisplayStart': 0,
            'draw': 1,
        })
        oferta_centres[key] = ids
        if (i + 1) % 50 == 0:
            logger.info('C LOMLOE %d/%d — centres únics: %d', i + 1, len(c_lomloe), len(centres_by_id))
            _save(centres_by_id, oferta_centres)
            _report('Grau C (pla nou)', i + 1, len(c_lomloe))

    logger.info('C LOMLOE complet: %d centres únics', len(centres_by_id))
    _save(centres_by_id, oferta_centres)
    _report('Grau C (pla nou)', len(c_lomloe), len(c_lomloe))

    # ── Grado D (per ofertaDenominacion + gradoProfesional=4) ──
    logger.info('=== Grado D: %d ofertes ===', len(d_list))
    _report('Grau D', 0, len(d_list))
    for i, oferta in enumerate(d_list):
        key = str(oferta['id'])
        denom = _short_denom(oferta['denominacion'])
        ids = _do_fetch({
            'ofertaDenominacion': denom,
            'gradoProfesional': '4',
            'iDisplayLength': PAGE_SIZE,
            'iDisplayStart': 0,
            'draw': 1,
        })
        oferta_centres[key] = ids
        if (i + 1) % 50 == 0:
            logger.info('D %d/%d — centres únics: %d', i + 1, len(d_list), len(centres_by_id))
            _save(centres_by_id, oferta_centres)
            _report('Grau D', i + 1, len(d_list))

    logger.info('D complet: %d centres únics', len(centres_by_id))
    _save(centres_by_id, oferta_centres)
    _report('Grau D', len(d_list), len(d_list))

    # ── Grado E (per ofertaDenominacion + gradoProfesional=5) ──
    logger.info('=== Grado E: %d ofertes ===', len(e_list))
    _report('Grau E', 0, len(e_list))
    for i, oferta in enumerate(e_list):
        key = str(oferta['id'])
        denom = _short_denom(oferta['denominacion'])
        ids = _do_fetch({
            'ofertaDenominacion': denom,
            'gradoProfesional': '5',
            'iDisplayLength': PAGE_SIZE,
            'iDisplayStart': 0,
            'draw': 1,
        })
        oferta_centres[key] = ids
        if (i + 1) % 10 == 0:
            logger.info('E %d/%d — centres únics: %d', i + 1, len(e_list), len(centres_by_id))
            _report('Grau E', i + 1, len(e_list))

    logger.info('E complet: %d centres únics', len(centres_by_id))
    _report('Grau E', len(e_list), len(e_list))

    return centres_by_id, oferta_centres


# ── escriptura ───────────────────────────────────────────────────────────────

def _save(centres_by_id: dict, oferta_centres: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    centres_list = sorted(centres_by_id.values(), key=lambda c: c['id'])
    with open(_CENTRES_PATH, 'w', encoding='utf-8') as f:
        json.dump(centres_list, f, ensure_ascii=False, indent=2)
    with open(_OFERTA_CENTRES_PATH, 'w', encoding='utf-8') as f:
        json.dump(oferta_centres, f, ensure_ascii=False, indent=2)


# ── entry point ──────────────────────────────────────────────────────────────

def build_centres_data(on_progress=None):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    centres_by_id, oferta_centres = scrape_centres(on_progress=on_progress)
    _save(centres_by_id, oferta_centres)

    total_c = len(centres_by_id)
    total_o = len(oferta_centres)
    logger.info('DONE: %d centres únics, %d relacions oferta↔centres', total_c, total_o)
    logger.info('Fitxers: %s, %s', _CENTRES_PATH, _OFERTA_CENTRES_PATH)


if __name__ == '__main__':
    build_centres_data()
