"""
centres_url_enricher.py — Pla 016b: enriquiment del camp url_web a centres.json.

Capa 1 — email domain (0 req): extreu www.{domain} si el domini no és genèric.
Capa 2 — centrorcd endpoint (~3.000 req a 1 req/s): per a centres tipo='rcd' sense URL.

Execució: python3 -m backend.scrapers.centres_url_enricher
"""

import json
import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

_BASE = 'https://registrosfp.educacion.gob.es/registroestatalentidadesformacion'
_BOOTSTRAP_URL = f'{_BASE}/buscarPublico'
_CENTRORCD_URL = f'{_BASE}/centrorcd'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': _BOOTSTRAP_URL,
}

_DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
_CENTRES_PATH = os.path.join(_DATA_DIR, 'centres.json')

RATE_LIMIT_SEC = 1.0

_GENERIC_DOMAINS = {
    'gmail.com', 'hotmail.com', 'yahoo.com', 'outlook.com', 'live.com',
    'hezkuntza.net', 'edu.gva.es', 'educa.jcyl.es', 'juntadeandalucia.es',
    'xunta.gal', 'educantabria.es', 'educastur.net', 'caib.es',
    'gobiernodecanarias.org', 'educacion.navarra.es', 'educacion.gob.es',
    'larioja.org', 'educa.madrid.org', 'educarm.es', 'educarex.es',
    'educa.aragon.es', 'educaweb.com',
}

_URL_CENTRO_RE = re.compile(r'name="urlCentro"\s+value="([^"]*)"')


def _url_from_email(email: str | None) -> str | None:
    if not email or '@' not in email:
        return None
    domain = email.split('@')[1].lower()
    if domain in _GENERIC_DOMAINS:
        return None
    return f'https://www.{domain}'


def _bootstrap() -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(_BOOTSTRAP_URL, timeout=30)
    resp.raise_for_status()
    if 'JSESSIONID' not in session.cookies:
        raise RuntimeError(f'Bootstrap sense JSESSIONID | HTTP {resp.status_code}')
    return session


def _fetch_url_centrorcd(session: requests.Session, cod_ministerio: str) -> str | None:
    for attempt in range(3):
        try:
            resp = session.get(f'{_CENTRORCD_URL}/{cod_ministerio}', timeout=30)
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                logger.warning('429 rate-limited, esperant %ds', wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            match = _URL_CENTRO_RE.search(resp.text)
            if match:
                url = match.group(1).strip()
                return url if url else None
            return None
        except requests.RequestException as exc:
            logger.warning('Error intent %d per %s: %s', attempt + 1, cod_ministerio, exc)
            if attempt == 2:
                return None
            time.sleep(5)
    return None


def enrich_url_web(save_every: int = 100):
    with open(_CENTRES_PATH, encoding='utf-8') as f:
        centres = json.load(f)

    # Capa 1: email domain (sense crides)
    capa1 = 0
    for c in centres:
        url = _url_from_email(c.get('email'))
        if url:
            c['url_web'] = url
            capa1 += 1
    logger.info('Capa 1 (email domain): %d/%d (%.1f%%)', capa1, len(centres), capa1 / len(centres) * 100)

    # Capa 2: centrorcd per als rcd sense URL
    candidats = [c for c in centres if c.get('tipo') == 'rcd' and not c.get('url_web')]
    logger.info('Capa 2 (centrorcd): %d candidats RCD sense URL', len(candidats))

    if not candidats:
        logger.info('Cap candidat per a Capa 2, saltant.')
    else:
        session = _bootstrap()
        capa2 = 0
        for i, c in enumerate(candidats):
            url = _fetch_url_centrorcd(session, c['id'])
            if url:
                c['url_web'] = url
                capa2 += 1

            if (i + 1) % 10 == 0:
                logger.info('Capa 2: %d/%d — urls trobades: %d', i + 1, len(candidats), capa2)

            if (i + 1) % save_every == 0:
                _save(centres)
                logger.info('Partial save a %d', i + 1)

            time.sleep(RATE_LIMIT_SEC)

        logger.info('Capa 2 complet: %d/%d centres RCD amb URL (%.1f%%)',
                    capa2, len(candidats), capa2 / len(candidats) * 100 if candidats else 0)

    # Resum cobertura
    total = len(centres)
    amb_url = sum(1 for c in centres if c.get('url_web'))
    sense_url = total - amb_url
    logger.info('Cobertura url_web final: %d/%d (%.1f%%)', amb_url, total, amb_url / total * 100)
    logger.info('  Capa 1 (email domain): %d centres', capa1)
    capa2_count = amb_url - capa1
    logger.info('  Capa 2 (centrorcd): %d centres', capa2_count)
    logger.info('  Sense URL: %d centres (%.1f%%)', sense_url, sense_url / total * 100)

    _save(centres)


def _save(centres: list):
    with open(_CENTRES_PATH, 'w', encoding='utf-8') as f:
        json.dump(centres, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    enrich_url_web()
