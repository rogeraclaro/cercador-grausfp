"""
ccoo_scraper.py — Cursos de CCOO a través de la Fundació Paco Puerto (Pla 066).

WordPress + WooCommerce: la llista surt de l'API REST (`/wp-json/wp/v2/product`, 85 productes el 2026-09-25);
les dates, hores, modalitat i horari només són a l'HTML de cada fitxa. S'exclouen oposicions i formació sindical.
"""
import html as _html
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

API = 'https://fundaciopacopuerto.cat/wp-json/wp/v2'
PAUSA_S = 0.2
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

EXCLOSES = {'funcio-publica-oposicions', 'formacio-sindical'}
ROOT_FAMILIA = {
    'administracio-i-gestio': 'ADG', 'comerc-i-marqueting': 'COM', 'electricitat-i-electronica': 'ELE',
    'energia-i-aigua': 'ENA', 'ensenyament-i-formacio': 'SSC', 'formacio-transversal': 'FCO',
    'hostaleria-i-turisme': 'HOT', 'idiomes': 'CTR', 'industria-alimentaria': 'INA',
    'informatica-i-comunicacions': 'IFC', 'sanitat': 'SAN', 'seguretat-i-medi-ambient': 'SEA',
    'serveis-socioculturals-i-a-la-comunitat': 'SSC', 'transport-i-manteniment-de-vehicles': 'TMV',
}
_MODALITATS = {'presencial': 'PRESENCIAL', 'teleformacio': 'TELEFORMACIÓ', 'teleformació': 'TELEFORMACIÓ',
               'aula virtual': 'VIDEOCONFERÈNCIA'}


def _iso(s):
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', s or '')
    return f'{m[3]}-{m[2]}-{m[1]}' if m else None


def roots(cats: list[dict]) -> dict:
    """{id_categoria: slug de la seva arrel}."""
    by_id = {c['id']: c for c in cats}
    out = {}
    for c in cats:
        cur, seen = c, set()
        while cur.get('parent') and cur['parent'] in by_id and cur['id'] not in seen:
            seen.add(cur['id'])
            cur = by_id[cur['parent']]
        out[c['id']] = cur['slug']
    return out


def es_fpo(prod: dict, root_of: dict) -> bool:
    return not any(root_of.get(c) in EXCLOSES for c in prod.get('product_cat') or [])


def parse_page(html: str) -> dict:
    soup = BeautifulSoup(html or '', 'html.parser')

    def meta(cls):
        el = soup.select_one(f'.cursos-meta.{cls}')
        return el.get_text(' ', strip=True) if el else ''

    dates = meta('dates')
    ini = fi = None
    m = re.search(r'Inici:\s*(\S+).*?Fi:\s*(\S+)', dates)
    if m:
        ini, fi = _iso(m[1]), _iso(m[2])
    hm = re.search(r'[\d.,]+', meta('duration'))
    h1 = soup.select_one('h1')
    desc = soup.select_one('.fpp-single-product-tab-information-wrapper')
    return {
        'titol': h1.get_text(' ', strip=True) if h1 else '',
        'dataInici': ini,
        'dataFi': fi,
        'hores': float(hm.group().replace(',', '.')) if hm else 0.0,
        'modalitat': _MODALITATS.get(meta('modality').strip().lower(), ''),
        'horariText': meta('timetable'),
        'subvencionat': bool(desc and re.search(r'subvencionat', desc.get_text(' '), re.I)),
    }


def normalize(prod: dict, page: dict, root_of: dict, cats_by_id: dict, locs: dict) -> dict:
    cat_ids = prod.get('product_cat') or []
    root = next((root_of.get(c) for c in cat_ids if root_of.get(c)), '')
    fulla = next((cats_by_id[c] for c in cat_ids if c in cats_by_id and cats_by_id[c].get('parent')), None)
    municipi = next((locs.get(l, '') for l in prod.get('localitat') or []), '')
    if municipi.startswith('('):
        municipi = ''
    titol = page['titol'] or _html.unescape((prod.get('title') or {}).get('rendered', ''))
    return {
        'idCurs': f"CCOO:{prod['id']}",
        'font': 'ccoo',
        'tipus': 'Subvencionat' if page['subvencionat'] else 'Altres',
        'titol': {'ca': titol, 'es': titol},
        'area': _html.unescape(fulla['name']) if fulla else '',
        'certCodi': '',
        'familiaCodi': ROOT_FAMILIA.get(root, 'FCO'),
        'hores': page['hores'],
        'modalitat': page['modalitat'],
        'estat': '',
        'dataInici': page['dataInici'],
        'dataFi': page['dataFi'],
        'comarca': '', 'municipi': municipi, 'provincia': '',
        'centre': {
            'nom': 'Fundació Paco Puerto (CCOO)', 'carrer': '', 'cp': '', 'municipi': municipi,
            'comarca': '', 'telefon': '', 'email': '', 'web': '', 'idCentre': '',
            'horari': {}, 'lat': None, 'lon': None,
        },
        'horariText': page['horariText'],
        'fitxaUrl': prod.get('link', ''),
    }


def _all(session, path, fields=None) -> list:
    out = []
    for page in range(1, 50):
        params = {'per_page': 100, 'page': page}
        if fields:
            params['_fields'] = fields
        r = session.get(f'{API}/{path}', params=params, headers={'User-Agent': _UA}, timeout=30)
        r.raise_for_status()
        batch = r.json() or []
        if not batch:
            break
        out.extend(batch)
        if len(batch) < 100:
            break
    return out


def build_ccoo_cursos(session=None) -> list[dict]:
    session = session or requests.Session()
    cats = _all(session, 'product_cat')
    root_of = roots(cats)
    cats_by_id = {c['id']: c for c in cats}
    locs = {l['id']: _html.unescape(l['name']) for l in _all(session, 'localitat')}
    prods = _all(session, 'product', 'id,link,title,product_cat,localitat')
    out = []
    for p in prods:
        if not es_fpo(p, root_of):
            continue
        try:
            r = session.get(p['link'], headers={'User-Agent': _UA}, timeout=30)
            r.raise_for_status()
            out.append(normalize(p, parse_page(r.text), root_of, cats_by_id, locs))
        except requests.RequestException as exc:
            logger.warning('ccoo: fitxa %s no disponible: %s', p.get('link'), exc)
        time.sleep(PAUSA_S)
    return out
