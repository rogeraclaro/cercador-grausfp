"""
pimec_scraper.py — Cursos de PIMEC Formació (Pla 062).

Font: endpoint AJAX del cercador de cursos de pimecformacio.org (Drupal).
  GET /ca/formacio-inici/ajax?paraula_clau=&field_fo_tipus[]=<tipus>...&formacioPagina=<n>
retorna JSON {listcursos: <HTML de 12 targetes>, formulari, ...}. Sense captcha ni
cookies. Dues trampes verificades el 2026-09-25:
  1. El `paginador` anuncia 19 pàgines i n'hi ha 35: es pagina fins a una pàgina buida.
  2. Les targetes no porten l'àrea: s'obté escanejant un cop per àrea (`field_fo_area[]`).
"""
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE = 'https://pimecformacio.org'
AJAX_URL = f'{BASE}/ca/formacio-inici/ajax'
TIPUS = ['Altres', 'Bonificable', 'Diàleg Social (Subvencionat)', 'Subvencionat']
MAX_PAGES = 100   # xarxa de seguretat contra bucles
PAUSA_S = 0.2     # cortesia entre peticions

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

_MESOS = {'gen': 1, 'febr': 2, 'març': 3, 'abr': 4, 'maig': 5, 'juny': 6,
          'jul': 7, 'ag': 8, 'set': 9, 'oct': 10, 'nov': 11, 'des': 12}

# Vocabulari de modalitat del SOC (el frontend en fa `tc()`).
_MODALITATS = {'presencial': 'PRESENCIAL', 'online': 'TELEFORMACIÓ', 'mixta': 'MIXTA',
               'videoconferència': 'VIDEOCONFERÈNCIA', 'videoconferencia': 'VIDEOCONFERÈNCIA'}

_TOKEN = r'(\d{1,2}) ([a-zç]+)\.?(?: (\d{4}))?'
_FECHA_RE = re.compile(rf'^{_TOKEN}(?: - {_TOKEN})?\s*\(([\d.,]+)h\)$', re.IGNORECASE)
_HORES_RE = re.compile(r'\(([\d.,]+)h\)')
_LLOC_RE = re.compile(r'^(?P<lloc>.*?)\s*(?P<mod>Presencial|Online|Mixta|Videoconfer[eè]ncia)$',
                      re.IGNORECASE)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _hores(text) -> float:
    try:
        return float(str(text).replace(',', '.'))
    except ValueError:
        return 0.0


def _iso(year, month, day):
    if not (year and month):
        return None
    return f'{int(year):04d}-{month:02d}-{int(day):02d}'


def _parse_fecha(text: str):
    """'28 set. - 26 oct. 2026 (30h)' -> ('2026-09-28', '2026-10-26', 30.0).
    'Dates a concretar (20h)' -> (None, None, 20.0)."""
    text = ' '.join((text or '').split())
    m = _FECHA_RE.match(text)
    if not m:
        h = _HORES_RE.search(text)
        return None, None, _hores(h.group(1)) if h else 0.0
    d1, m1, y1, d2, m2, y2, hores = m.groups()
    mes1 = _MESOS.get(m1.lower())
    if d2 is None:                      # data única: "29 set. 2026"
        iso = _iso(y1, mes1, d1)
        return iso, iso, _hores(hores)
    mes2 = _MESOS.get(m2.lower())
    if y1 is None:                      # "15 des. - 20 gen. 2027": l'inici és l'any anterior
        y1 = int(y2) - (1 if mes1 and mes2 and mes1 > mes2 else 0)
    return _iso(y1, mes1, d1), _iso(y2, mes2, d2), _hores(hores)


def _parse_lloc(text: str):
    """'BADALONA Presencial' -> ('BADALONA', 'PRESENCIAL'); 'Aula Virtual Online' -> ('', 'TELEFORMACIÓ')."""
    m = _LLOC_RE.match((text or '').strip())
    if not m:
        return '', ''
    lloc = m.group('lloc').strip()
    if lloc.lower() == 'aula virtual':
        lloc = ''
    return lloc, _MODALITATS.get(m.group('mod').lower(), '')


def parse_cards(html: str) -> list[dict]:
    """Targetes de `listcursos` -> dicts crus (sense àrea)."""
    soup = BeautifulSoup(html or '', 'html.parser')
    out = []
    for card in soup.select('div.curso-lista'):
        a = card.select_one('.datos h2 a')
        if not a:
            continue
        href = a.get('href', '')
        ini, fi, hores = _parse_fecha(card.select_one('.fecha').get_text(' ', strip=True))
        lloc, modalitat = _parse_lloc(card.select_one('.lugar').get_text(' ', strip=True))
        out.append({
            'slug': href.rstrip('/').rsplit('/', 1)[-1],
            'url': BASE + href if href.startswith('/') else href,
            'titol': a.get_text(' ', strip=True),
            'tipus': card.select_one('div.categoria').get_text(strip=True),
            'dataInici': ini, 'dataFi': fi, 'hores': hores,
            'municipi': lloc, 'modalitat': modalitat,
        })
    return out


def parse_arees(formulari_html: str) -> list[str]:
    soup = BeautifulSoup(formulari_html or '', 'html.parser')
    return [i['value'] for i in soup.select('input[name="field_fo_area[]"]') if i.get('value')]


def normalize_curs(card: dict, area: str = '') -> dict:
    titol = card['titol']
    return {
        'idCurs': f"PIMEC:{card['slug']}",
        'font': 'pimec',
        'tipus': card['tipus'],
        'titol': {'ca': titol, 'es': titol},
        'area': area,
        'certCodi': '',
        'hores': card['hores'],
        'modalitat': card['modalitat'],
        'estat': '',
        'dataInici': card['dataInici'],
        'dataFi': card['dataFi'],
        'comarca': '',
        'municipi': card['municipi'],
        'provincia': '',
        'centre': {
            'nom': 'PIMEC Formació', 'carrer': '', 'cp': '', 'municipi': card['municipi'],
            'comarca': '', 'telefon': '', 'email': '', 'web': '', 'idCentre': '',
            'horari': {}, 'lat': None, 'lon': None,
        },
        'fitxaUrl': card['url'],
    }


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': _UA})
    return s


def _get_page(session, page: int, area: str | None = None) -> dict:
    params = [('paraula_clau', '')]
    params += [('field_fo_tipus[]', t) for t in TIPUS]
    if area:
        params.append(('field_fo_area[]', area))
    params.append(('formacioPagina', str(page)))
    resp = session.get(AJAX_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _scan(session, area: str | None = None):
    """Recorre pàgines fins a una de buida. Retorna (targetes, formulari de la pàgina 1)."""
    cards, formulari = [], ''
    for page in range(1, MAX_PAGES + 1):
        data = _get_page(session, page, area)
        if page == 1:
            formulari = data.get('formulari', '')
        page_cards = parse_cards(data.get('listcursos', ''))
        if not page_cards:
            break
        cards.extend(page_cards)
        time.sleep(PAUSA_S)
    else:
        logger.warning('pimec: MAX_PAGES=%d assolit (area=%s)', MAX_PAGES, area)
    return cards, formulari


# ---------------------------------------------------------------------------
# Orquestració
# ---------------------------------------------------------------------------

def build_pimec_cursos(session=None) -> list[dict]:
    """Tots els cursos de PIMEC normalitzats (un per edició, sense duplicats)."""
    session = session or _new_session()
    cards, formulari = _scan(session)
    area_de: dict = {}
    for area in parse_arees(formulari):
        sub, _ = _scan(session, area)
        for c in sub:
            area_de.setdefault(c['slug'], area)
    vistos, out = set(), []
    for c in cards:
        if c['slug'] in vistos:
            continue
        vistos.add(c['slug'])
        out.append(normalize_curs(c, area_de.get(c['slug'], '')))
    return out
