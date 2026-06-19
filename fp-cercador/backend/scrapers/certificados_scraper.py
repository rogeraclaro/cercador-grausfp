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


_CICLOS_PAYLOAD_BASE = {
    'limite': '0', 'paso': '10', 'total': '588',
    'codigo': '', 'denominacion': '', 'familia': '0',
    'nivelFiltro': '0', 'origen': 'busquedaCP',
}


_D_PREFIXES = (
    'Título Profesional Básico en ',
    'Técnico Superior en ',
    'Técnico en ',
)


def _build_d_index(records: list[dict]) -> dict:
    """
    Construeix un índex per trobar la ficha_url d'un cicle D a partir del
    nom curt que retorna ciclosFP.

    Retorna dos nivells:
      primary:   {denominacion_curta.lower(): ficha_url}
      secondary: {(denominacion_curta.lower(), familia.lower()): ficha_url}

    La denominació curta s'obté eliminant els prefixos canònics de la
    denominació completa del registre D.
    """
    primary: dict[str, str] = {}
    secondary: dict[tuple, str] = {}
    for r in records:
        if r.get('grado') != 'D':
            continue
        ficha_url = r.get('ficha_url')
        if not ficha_url:
            continue
        den = r.get('denominacion') or ''
        fam = (r.get('familia') or '').lower()
        short = den
        for prefix in _D_PREFIXES:
            if den.startswith(prefix):
                short = den[len(prefix):]
                break
        key = short.lower()
        primary[key] = ficha_url
        secondary[(key, fam)] = ficha_url
    return {'primary': primary, 'secondary': secondary}


def fetch_ciclos_fp(
    session: requests.Session,
    cert_id: int,
    timeout: int = 20,
    d_index: dict | None = None,
) -> list[dict]:
    """
    POST /ciclosFP per a un cert_id → llista de cicles D que el convaliden.
    Cada cicle: {'denominacion': str, 'familia': str, 'ficha_url': str | None}

    d_index: sortida de _build_d_index(). Si és None, ficha_url serà None.
    """
    payload = {**_CICLOS_PAYLOAD_BASE, 'certificadoID': str(cert_id)}
    try:
        resp = session.post(BASE_CERT_URL + '/ciclosFP', data=payload, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("fetch_ciclos_fp cert_id=%s: error HTTP: %s", cert_id, exc)
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    ciclos = []
    primary   = (d_index or {}).get('primary', {})
    secondary = (d_index or {}).get('secondary', {})

    for row in soup.select('table tr'):
        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
        if len(cells) >= 2 and cells[0] and cells[0] != 'Ciclo formativo':
            den = cells[0]
            fam = cells[1] if len(cells) > 1 else ''
            key_primary = den.lower()
            key_secondary = (key_primary, fam.lower())
            ficha_url = secondary.get(key_secondary) or primary.get(key_primary)
            ciclos.append({'denominacion': den, 'familia': fam, 'ficha_url': ficha_url})
    return ciclos


def build_ciclos_index(
    cert_data: dict[str, dict],
    all_records: list[dict] | None = None,
) -> dict[str, list[dict]]:
    """
    Per a cada codi C LOE (clau de cert_data), crida ciclosFP i retorna
    {codigo_C: [{'denominacion': ..., 'familia': ..., 'ficha_url': ...}]}.

    cert_data:   sortida de fetch_all() → {codigo: {'cert_id': int, ...}}
    all_records: llista completa d'ofertes (conté els registres D amb ficha_url).
                 Si és None, ficha_url serà None per a tots els cicles.
    """
    if not cert_data:
        return {}

    d_index = _build_d_index(all_records) if all_records else None
    session = _bootstrap_session()
    result = {}
    for codigo, data in cert_data.items():
        cert_id = data.get('cert_id')
        if not cert_id:
            continue
        ciclos = fetch_ciclos_fp(session, cert_id, d_index=d_index)
        result[codigo] = ciclos
        logger.debug("build_ciclos_index: %s → %d cicles", codigo, len(ciclos))

    logger.info("build_ciclos_index: %d certificats processats", len(result))
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


# ── B→C LOE: extracció UC codes de l'Annexo PDF ─────────────────────────────

import io as _io
import re as _re

_UC_PAT = _re.compile(r'\bUC\d{4}_\d+\b')
_PDF_HEADERS = {**_HEADERS, 'Referer': 'https://www.todofp.es/'}


def fetch_uc_codes_from_pdf(codigo_c: str, timeout: int = 30) -> list[str]:
    """
    Descarrega l'Annexo PDF d'un C LOE i retorna la llista de codis UC únics.

    URL: BASE_DAM/anexos/{codigo_c.lower()}.pdf
    Retorna [] si el PDF no existeix (404) o no conté UC codes llegibles.
    Eleva requests.HTTPError per errors inesperats de xarxa (no 404).
    """
    import pdfplumber as _pdfplumber

    url = f"{BASE_DAM}/anexos/{codigo_c.lower()}.pdf"
    resp = requests.get(url, headers=_PDF_HEADERS, timeout=timeout)
    if resp.status_code == 404:
        logger.debug("fetch_uc_codes_from_pdf: PDF no trobat per %s", codigo_c)
        return []
    resp.raise_for_status()

    uc_codes: list[str] = []
    with _pdfplumber.open(_io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            uc_codes.extend(_UC_PAT.findall(text))

    return list(dict.fromkeys(uc_codes))  # dedup preservant ordre
