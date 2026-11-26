"""
sepe_scraper.py — Catàleg d'Especialitats Formatives del SEPE (Pla 081).

El catàleg estatal de la formació en el treball (Llei 3/2023 d'Ocupació) es
consulta a la seu electrònica del SEPE (JSF + DataTables). El llistat complet
surt d'un endpoint REST intern, sense captcha ni login:

  1. GET  /flows/main                    -> posa les cookies de sessió
  2. POST /rest/paginacionEspecialidades -> files paginades (length=2000)

La resposta és Latin-1 (no UTF-8) i cada fila és una llista d'11 cel·les, algunes
amb HTML. Genera backend/data/sepe_especs.json (un dict per especialitat).

Validació fail-soft: menys de MIN_ROWS registres o algun codi duplicat aixequen
`SepeDataError` i no s'escriu res (es conserva el JSON anterior). El pipeline ho
tracta com a no-fatal i avisa l'admin.
"""
import html
import json
import logging
import os
import re
import tempfile

import requests

from titols import display_title

logger = logging.getLogger(__name__)

BASE = 'https://sede.sepe.gob.es/FOET_CATALOGO_EEFF_SEDE'
SEPE_FILE = 'sepe_especs.json'
PAGE_LENGTH = 2000
MIN_ROWS = 5000
MAX_PAGES = 20  # guarda contra bucles si el servidor mai retorna una pàgina curta
TIMEOUT = 30
# Una pàgina de 2000 files pot trigar ~40 s quan la seu va lenta (mesurat 2026-11-08).
POST_TIMEOUT = 90

# Duplicat a propòsit de soc_scraper (mateix precedent que HEADERS d'html_scraper).
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

_N_CELLS = 11
_FILTER_WRAPPERS = ('tutoriaPresencial', 'aulaVirtualSeleccionada', 'vinculacion',
                    'centroMovil', 'otrosRequisitos')

_RE_INICI = re.compile(r'INICIO VIGENCIA:\s*(\d{2})/(\d{2})/(\d{4})')
_RE_FI = re.compile(r'FIN VIGENCIA:\s*(\d{2})/(\d{2})/(\d{4})')
_RE_ID = re.compile(r'getProgramaFormativoEspecialidad\((\d+)\)')
_RE_TAG = re.compile(r'<[^>]*>')
_RE_WS = re.compile(r'\s+')
# Pla 096: «CTRC0001 (FCOV0001)» → codi nou + codi anterior entre parèntesis.
_RE_CODI = re.compile(r'^(\S+)\s*\((\S+)\)$')
# Sufixos del codi després dels dígits (ADGA12DCP, FCOE001PO). Significat: plans/096.
_RE_SUFIX = re.compile(r'\d(PO|EXP|DCP|CCC|PTF)$')
# El SEPE envia «?» on hi havia cometes o ®: «?TERCER FUEGO?», «MICROSOFT?».
_RE_QPAIR = re.compile(r'(?<![\w¿?])\?(?=[^\s?])([^?¿]*?[^\s?])\?(?!\w)')


class SepeDataError(Exception):
    """La resposta del SEPE no és vàlida (canvi de format, truncada, sessió perduda…)."""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': _UA})
    return s


def _request_body(start: int, length: int) -> dict:
    columns = [{'data': i, 'name': '', 'searchable': True, 'orderable': i not in (0, 10),
                'search': {'value': '', 'regex': False}} for i in range(_N_CELLS)]
    filtro = [
        {'name': 'formulario:ultimaVersionCuadrado', 'value': 'true'},
        {'name': 'formulario_SUBMIT', 'value': '1'},
        {'name': 'javax.faces.ViewState', 'value': 'e1s1'},
    ]
    for name in _FILTER_WRAPPERS:
        filtro.append({
            'name': f'formulario:acordeonPrincipal:tabOpcionesAvanzadas:{name}Wrapper:{name}',
            'value': '000',
        })
    return {
        'dtInfo': [
            {'name': 'draw', 'value': 1},
            {'name': 'columns', 'value': columns},
            {'name': 'order', 'value': [{'column': 1, 'dir': 'asc'}]},
            {'name': 'start', 'value': start},
            {'name': 'length', 'value': length},
            {'name': 'search', 'value': {'value': '', 'regex': False}},
        ],
        'filtro': filtro,
        'enAltaIF': False,
        'enSEDE': True,
        'tipoBuscador': 'buscadorEspecialidades',
    }


def _fetch_raw_rows(session) -> list:
    """Totes les files crues (llistes d'11 cel·les) del catàleg."""
    resp = session.get(f'{BASE}/flows/main', timeout=TIMEOUT)
    resp.raise_for_status()

    length = PAGE_LENGTH  # llegit en temps de crida: els tests el poden parchejar
    rows: list = []
    for page in range(MAX_PAGES):
        resp = session.post(f'{BASE}/rest/paginacionEspecialidades',
                            json=_request_body(page * length, length), timeout=POST_TIMEOUT)
        resp.raise_for_status()
        try:
            payload = json.loads(resp.content.decode('latin-1'))
            data = payload['data']
        except (ValueError, KeyError, TypeError) as exc:
            # Sense sessió el SEPE redirigeix a /flows/error i serveix HTML.
            raise SepeDataError(f'resposta SEPE no vàlida a la pàgina {page}: {exc}') from exc
        if not isinstance(data, list):
            raise SepeDataError(f'resposta SEPE sense llista de dades a la pàgina {page}')
        rows.extend(data)
        if len(data) < length:
            return rows
    raise SepeDataError(f'més de {MAX_PAGES} pàgines de {length} files: es talla el bucle')


# ---------------------------------------------------------------------------
# Parseig
# ---------------------------------------------------------------------------

def _text(cell) -> str:
    """Text net d'una cel·la: sense tags, entitats resoltes, espais col·lapsats."""
    return _RE_WS.sub(' ', html.unescape(_RE_TAG.sub(' ', str(cell)))).strip()


def _opt_text(cell):
    """Text net o None si és buit o '-' (el SEPE usa '-' per a «no n'hi ha»)."""
    value = _text(cell)
    return None if value in ('', '-') else value


def _date(regex, cell0: str):
    m = regex.search(cell0)
    return f'{m.group(3)}-{m.group(2)}-{m.group(1)}' if m else None


def _split_codi(text: str) -> tuple:
    """(codi, codiAntic). El SOC fa servir el codi sense parèntesi."""
    m = _RE_CODI.match(text)
    if m:
        return m.group(1), m.group(2)
    return text.split(' ')[0], None


def _sufix(codi: str):
    m = _RE_SUFIX.search(codi)
    return m.group(1) if m else None


def clean_title(text: str) -> str:
    """Treu els «?» que substitueixen cometes o ®. Un «¿…?» es deixa intacte."""
    if '?' not in text:
        return text
    text = _RE_QPAIR.sub(r'«\1»', text)
    out = []
    obertes = 0
    for i, ch in enumerate(text):
        if ch == '¿':
            obertes += 1
        elif ch == '?':
            if obertes:
                obertes -= 1
            else:
                # Entre dues paraules («MICROSOFT?CERTIFIED») fa d'espai; si no, fora.
                entre = (i > 0 and text[i - 1].isalnum()
                         and i + 1 < len(text) and text[i + 1].isalnum())
                if entre:
                    out.append(' ')
                continue
        out.append(ch)
    return _RE_WS.sub(' ', ''.join(out)).strip()


def parse_row(cells) -> dict:
    if not isinstance(cells, list) or len(cells) != _N_CELLS:
        n = len(cells) if isinstance(cells, list) else type(cells).__name__
        raise SepeDataError(f'fila SEPE amb {n} cel·les (esperades {_N_CELLS}): canvi de format?')
    codi, codi_antic = _split_codi(_text(cells[1]))
    m_id = _RE_ID.search(str(cells[2]))
    nivell = _text(cells[7])
    titol = clean_title(_text(cells[2]))
    return {
        'codi': codi,
        'codiAntic': codi_antic,
        'sufix': _sufix(codi),
        'idSepe': int(m_id.group(1)) if m_id else None,
        'titol_es': titol,
        'titol_mostra': display_title(titol),
        'versio': int(cells[3]),
        'familia_es': _opt_text(cells[4]),
        'area_es': _opt_text(cells[5]),
        'familia_codi': codi[:3],
        'area_codi': codi[:4],
        'competenciaTransversal': _opt_text(cells[6]),
        'nivell': int(nivell) if nivell.isdigit() else None,
        'modalitat': _text(cells[8]),
        'hores': float(_text(cells[9]).replace(',', '.')),
        'vigenciaInici': _date(_RE_INICI, str(cells[0])),
        'vigenciaFi': _date(_RE_FI, str(cells[0])),
    }


def validate_rows(rows: list) -> None:
    if len(rows) < MIN_ROWS:
        raise SepeDataError(f'només {len(rows)} especialitats SEPE (mínim {MIN_ROWS})')
    seen = set()
    for row in rows:
        codi = row['codi']
        if codi in seen:
            raise SepeDataError(f'codi SEPE duplicat: {codi}')
        seen.add(codi)


# ---------------------------------------------------------------------------
# Orquestració
# ---------------------------------------------------------------------------

def build_sepe_data(session=None) -> list:
    """Totes les especialitats del catàleg, parsejades i validades."""
    session = session or _new_session()
    rows = [parse_row(cells) for cells in _fetch_raw_rows(session)]
    validate_rows(rows)
    logger.info('sepe: %d especialitats del catàleg', len(rows))
    return rows


def write_sepe_data(rows: list, data_dir: str) -> None:
    # Guarda: una llista dolenta mai no sobreescriu el snapshot anterior.
    validate_rows(rows)
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, SEPE_FILE)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=data_dir, delete=False) as tmp:
        tmp_path = tmp.name
        try:
            json.dump(rows, tmp, ensure_ascii=False, indent=1)
        except BaseException:
            tmp.close()
            os.unlink(tmp_path)
            raise
    os.replace(tmp_path, path)


# ---------------------------------------------------------------------------
# Programa formatiu (PDF) — Pla 082
# ---------------------------------------------------------------------------

def fetch_programa_pdf(id_sepe: int, session=None) -> bytes | None:
    """PDF del programa formatiu d'una especialitat, o None si el SEPE no en té.

    És el mateix POST JSF que fa el botó del cercador (verificat al pla 081): sense
    document, el servidor torna l'HTML del modal "no tiene documento asociado".
    Els errors de xarxa i HTTP es propaguen.
    """
    session = session or _new_session()
    resp = session.get(f'{BASE}/flows/main', timeout=TIMEOUT)
    resp.raise_for_status()
    fields = {
        'formulario_SUBMIT': '1',
        'javax.faces.ViewState': 'e1s1',
        'formulario:codigoPropuesta': str(int(id_sepe)),
        'formulario:invisibleClickTargetProgramaFormativoEspecialidad': '',
    }
    # files= amb (None, valor) fa un multipart/form-data sense fitxers, com el navegador.
    resp = session.post(f'{BASE}/flows/main?execution=e1s1',
                        files={k: (None, v) for k, v in fields.items()}, timeout=POST_TIMEOUT)
    resp.raise_for_status()
    # El SEPE envia "Content-type: pdf" (no application/pdf): es mira també la signatura.
    if 'pdf' not in resp.headers.get('Content-Type', '').lower() or not resp.content.startswith(b'%PDF-'):
        return None
    return resp.content
