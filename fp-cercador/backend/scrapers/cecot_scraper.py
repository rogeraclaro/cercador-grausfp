"""
cecot_scraper.py — Cursos de Cecot Formació (Pla 066).

Llista: GET https://formacio.cecot.org/courses/list?public=1 → JSON amb tots els cursos (25 el 2026-09-25,
sense paginació). La data de fi, l'horari i l'adreça només són a la fitxa de cada curs.
"""
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

LIST_URL = 'https://formacio.cecot.org/courses/list?public=1'
DETAIL_URL = 'https://formacio.cecot.org/Cursos/Curs/(code)/{codi}'
PAUSA_S = 0.2
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
_MODALITATS = {'presencial': 'PRESENCIAL', 'online': 'TELEFORMACIÓ', 'virtual': 'VIDEOCONFERÈNCIA'}


def _iso(s):
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', (s or '').strip())
    return f'{m[3]}-{m[2]}-{m[1]}' if m else None


def _hores(v) -> float:
    m = re.search(r'[\d.,]+', str(v or ''))
    try:
        return float(m.group().replace(',', '.')) if m else 0.0
    except ValueError:
        return 0.0


def parse_detail(html: str) -> dict:
    soup = BeautifulSoup(html or '', 'html.parser')
    ini = soup.select_one('.folder-date-start')
    fi = soup.select_one('.folder-date-finish')
    camps, adreca = {}, []
    for th in soup.select('.course-features-block th'):
        clau = th.get_text(strip=True)
        td = th.find_next_sibling('td')
        if not clau or td is None:
            continue
        if clau == 'Adreça':
            adreca = [s.strip() for s in td.get_text('\n').split('\n') if s.strip()]
        else:
            camps[clau] = td.get_text(' ', strip=True)
    return {
        'dataInici': _iso(ini.get('data-date')) if ini else None,
        'dataFi': _iso(fi.get('data-date')) if fi else None,
        'camps': camps,
        'adreca': adreca,
    }


def normalize(item: dict, detail: dict | None) -> dict:
    detail = detail or {}
    camps = detail.get('camps') or {}
    adreca = detail.get('adreca') or []
    poblacio = (item.get('Poblacio') or '').strip()
    municipi = '' if poblacio.lower() == 'virtual' else poblacio
    cp, carrer, lloc = '', '', ''
    if adreca:
        m = re.match(r'^(\d{5})\s*-\s*(.+)$', adreca[-1])
        if m:
            cp, municipi = m[1], m[2].strip()
            adreca = adreca[:-1]
        if len(adreca) >= 2:
            lloc, carrer = adreca[0], ', '.join(adreca[1:])
        elif adreca:
            carrer = adreca[0]
    horari = ' · '.join(v for v in (camps.get('Dies', ''), camps.get('Horari laboral', '')) if v)
    titol = (item.get('Descripcio') or '').strip()
    codi = item.get('Codi', '')
    return {
        'idCurs': f'CECOT:{codi}',
        'font': 'cecot',
        'tipus': 'Subvencionat' if item.get('Pagament') == 'N' else 'Altres',
        'titol': {'ca': titol, 'es': titol},
        'area': '',
        'certCodi': '',
        'familiaCodi': '',
        'hores': _hores(item.get('Hores')),
        'modalitat': _MODALITATS.get((item.get('Modalitat') or '').strip().lower(), ''),
        'estat': '',
        'dataInici': detail.get('dataInici') or _iso(item.get('Inici')),
        'dataFi': detail.get('dataFi'),
        'comarca': '', 'municipi': municipi, 'provincia': '',
        'centre': {
            'nom': 'Cecot · ' + lloc if lloc else 'Cecot', 'carrer': carrer, 'cp': cp, 'municipi': municipi,
            'comarca': '', 'telefon': '', 'email': '', 'web': '', 'idCentre': '',
            'horari': {}, 'lat': None, 'lon': None,
        },
        'horariText': horari,
        'fitxaUrl': DETAIL_URL.format(codi=codi),
    }


def build_cecot_cursos(session=None) -> list[dict]:
    session = session or requests.Session()
    headers = {'User-Agent': _UA, 'X-Requested-With': 'XMLHttpRequest'}
    resp = session.get(LIST_URL, headers=headers, timeout=45)
    resp.raise_for_status()
    data = resp.json() or {}
    if not data.get('success'):
        raise ValueError('cecot: resposta inesperada de /courses/list')
    items = ((data.get('data') or {}).get('items') or {}).get('list') or []
    out = []
    for item in items:
        detail = None
        try:
            r = session.get(DETAIL_URL.format(codi=item.get('Codi', '')), headers={'User-Agent': _UA}, timeout=30)
            r.raise_for_status()
            detail = parse_detail(r.text)
        except requests.RequestException as exc:
            logger.warning('cecot: fitxa %s no disponible: %s', item.get('Codi'), exc)
        out.append(normalize(item, detail))
        time.sleep(PAUSA_S)
    return out
