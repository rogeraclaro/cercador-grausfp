"""
foment_scraper.py — Cursos de Foment Formació (Pla 062).

Font: WordPress amb tipus de contingut `curso_foment`. El sitemap llista les fitxes
(castellà `/formacion/<slug>` i català `/ca/formacio/<slug>`, duplicades: només el
castellà). Algunes URL porten un fragment `#edicion-...`: es treu i es dedupliquen.
Cada fitxa té 1–4 edicions (`[data-edition]`); cada edició és un curs. Alguns ids
d'edició es repeteixen entre pàgines: la clau és `slug + id`.
"""
import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SITEMAP_URL = 'https://www.fomentformacio.com/curso_foment-sitemap.xml'
PAUSA_S = 0.2

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

_CODI_RE = re.compile(r'^([A-Z]{4}\d{4})\s*:')
_COORD_RE = re.compile(r'query=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)')
_DATA_RE = re.compile(r'^(\d{2})/(\d{2})/(\d{4})$')
_ED_MOD_RE = re.compile(r'^edicion-([a-z]+)-')
_MODALITATS = {'presencial': 'PRESENCIAL', 'online': 'TELEFORMACIÓ', 'virtual': 'VIDEOCONFERÈNCIA'}


def _iso(text):
    m = _DATA_RE.match((text or '').strip())
    return f'{m[3]}-{m[2]}-{m[1]}' if m else None


def _hores(text) -> float:
    m = re.search(r'[\d.,]+', text or '')
    try:
        return float(m.group().replace(',', '.')) if m else 0.0
    except ValueError:
        return 0.0


def list_course_urls(sitemap_xml: str) -> list[str]:
    """Fitxes en castellà, sense fragment (`#edicion-...`, permalinks d'edició) ni repetits."""
    urls = (u.split('#')[0] for u in re.findall(r'<loc>([^<]+)</loc>', sitemap_xml or ''))
    return list(dict.fromkeys(u for u in urls if '/formacion/' in u))


def parse_course(html: str, url: str) -> list[dict]:
    """Una fitxa -> una llista de cursos (un per edició)."""
    soup = BeautifulSoup(html or '', 'html.parser')
    h1 = soup.select_one('h1.hero-curso__title')
    if not h1:
        return []
    titol = h1.get_text(' ', strip=True)
    slug = url.rstrip('/').rsplit('/', 1)[-1]
    cm = _CODI_RE.match(titol)
    out = []
    for ed in soup.select('.sidebar-card__list [data-edition]'):
        ed_id = ed.get('data-edition', '')
        camps, lat, lon = {}, None, None
        for box in ed.select('.detail-item__texts'):
            label = box.find('label')
            if not label:
                continue
            a = box.find('a')
            if a:
                mc = _COORD_RE.search(a.get('href', ''))
                if mc:
                    lat, lon = float(mc[1]), float(mc[2])
            clau = label.get_text(strip=True)
            label.extract()
            camps[clau] = ' '.join(box.get_text(' ', strip=True).split())
        mod = _ED_MOD_RE.match(ed_id)
        out.append({
            'idCurs': f'FOMENT:{slug}:{ed_id}',
            'font': 'foment',
            'tipus': 'Altres',            # Foment no publica un tipus per curs
            'titol': {'ca': titol, 'es': titol},
            'area': '',
            'certCodi': cm.group(1) if cm else '',
            'hores': _hores(camps.get('Horas')),
            'modalitat': _MODALITATS.get(mod.group(1), '') if mod else '',
            'estat': '',
            'dataInici': _iso(camps.get('Comienzo')),
            'dataFi': _iso(camps.get('Final')),
            'comarca': '', 'municipi': '', 'provincia': '',
            'centre': {
                'nom': camps.get('Centro', ''), 'carrer': '', 'cp': '', 'municipi': '',
                'comarca': '', 'telefon': '', 'email': '', 'web': '', 'idCentre': '',
                'horari': {}, 'lat': lat, 'lon': lon,
            },
            'horariText': camps.get('Horario', ''),
            'fitxaUrl': url,
        })
    return out


def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': _UA})
    return s


def build_foment_cursos(session=None) -> list[dict]:
    """Totes les edicions de Foment. Una fitxa que falla es salta (log) i no atura la resta."""
    session = session or _new_session()
    resp = session.get(SITEMAP_URL, timeout=30)
    resp.raise_for_status()
    out = []
    for url in list_course_urls(resp.text):
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
            out.extend(parse_course(r.text, url))
        except requests.RequestException as exc:
            logger.warning('foment: no s\'ha pogut llegir %s: %s', url, exc)
        time.sleep(PAUSA_S)
    return out
