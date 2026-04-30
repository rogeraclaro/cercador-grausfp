"""
html_scraper.py — Parsing de pàgines HTML dels Grados D i E del sistema FP espanyol.

Exposa:
  parse_grado_d_basico(url: str)   -> list[dict]   (nivel=1)
  parse_grado_d_medio(url: str)    -> list[dict]   (nivel=2)
  parse_grado_d_superior(url: str) -> list[dict]   (nivel=3)
  parse_grado_e(url: str)          -> list[dict]   (nivel=None)
  HTML_FAMILY_ALIASES: dict[str, str]  -- mapeig de famílies HTML no canòniques

Cada registre retornat té exactament:
  {denominacion, familia, nivel, codigo, plan_antiguo, observaciones}

Camps 'id' i 'grado' els afegeix pipeline.py, NO aquest mòdul.

Decisions aplicades:
  D-01: Fail fast — resp.raise_for_status() propaga HTTPError
  D-04: Funcions per subtipus amb helper intern _parse_grado_d compartit
  D-07: Detecció de família via Mètode B (headers del <td>) — recomanat a 03-RESEARCH.md
  D-08: Família no mapable → familia='Desconeguda' + logger.warning (consistent Fase 2)
  D-10: Schema fix dels registres (codigo=None, plan_antiguo=False, observaciones="")

IMPORTANT — Pitfall 1 (03-RESEARCH.md): BeautifulSoup4 retorna l'atribut `headers`
com a AttributeValueList (llista), no com a string. Cal isinstance(hv, list) sempre.

IMPORTANT — HEADERS duplicat: Es duplica el dict HEADERS de pipeline.py (comptem
com a dues constants independents) per evitar dependència circular, ja que pipeline.py
importarà funcions d'aquest mòdul al Plan 03. Font: fp-cercador/backend/scrapers/pipeline.py
línies 32-42. Si canvia pipeline.HEADERS, cal sincronitzar aquí.
"""
import logging

import requests
from bs4 import BeautifulSoup

from scrapers.pdf_scraper import FAMILY_ALIASES, PREFIX_MAP

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Font: pipeline.py línies 32-42 (duplicat intencionat — vegeu docstring).
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": (
        "https://www.todofp.es/catalogos-registros-sistema-fp/"
        "catalogo-nacional-ofertas-sistema.html"
    ),
}

# HTML_FAMILY_ALIASES és ara FAMILY_ALIASES importat de pdf_scraper.py.
# El conservem com a àlies local per no trencar cap codi extern que l'importi.
HTML_FAMILY_ALIASES = FAMILY_ALIASES


# ---------------------------------------------------------------------------
# Funcions privades
# ---------------------------------------------------------------------------


def _build_fam_map(soup: BeautifulSoup) -> dict:
    """
    Retorna {fam_id: nom_canonic} per a cada <th headers='familia'> amb <img>.

    Construeix el map UNICAMENT de <th headers='familia'>. Això ignora
    automàticament el logo de capçalera <img alt='Logotipo de TodoFP'> i
    qualsevol altra imatge fora de la taula principal.

    Accepta dos formats d'atribut alt:
      - "Logotipo <NomFamília>" (format habitual Grados D)
      - "<NomFamília>" sense prefix (detectat a Grado E, p.ex. 'Inteligencia Artificial y Data')
    """
    fam_map: dict = {}
    for th in soup.find_all('th', attrs={'headers': 'familia'}):
        fam_id = th.get('id', '')
        img = th.find('img')
        if not img:
            continue
        alt = img.get('alt', '')
        if not alt:
            continue
        # Extreu el nom de família: elimina el prefix "Logotipo " si present.
        if alt.startswith('Logotipo '):
            raw_name = alt[len('Logotipo '):].strip()
        else:
            raw_name = alt.strip()
        canonical = HTML_FAMILY_ALIASES.get(raw_name, raw_name)
        # Només incloem al mapa si el nom és canònic (valor de PREFIX_MAP).
        # Si no ho és, _extract_titols produirà 'Desconeguda' + warning (D-08).
        if canonical in PREFIX_MAP.values():
            fam_map[fam_id] = canonical
    return fam_map


def _extract_titols(soup: BeautifulSoup, fam_map: dict, nivel, grado: str) -> list[dict]:
    """
    Extreu tots els títols d'una pàgina HTML del ministeri.

    Recorre els <td> amb 'titulacion' al seu atribut headers. Per cada un:
      1. Localitza el fam_id dins l'atribut headers (la paraula que comença per 'fam').
      2. Cerca el primer <a id='tit-*'> dins el <td>.
      3. Mapeja fam_id → nom de família via fam_map (o 'Desconeguda' amb warning).
      4. Construeix el dict del registre amb el schema fix D-10.

    IMPORTANT: td.get('headers') retorna AttributeValueList (llista) en BeautifulSoup4.
    L'isinstance(hv, list) és obligatori (Pitfall 1 03-RESEARCH.md).
    """
    records: list = []
    for td in soup.find_all('td', attrs={'headers': True}):
        hv = td.get('headers', [])
        hl = hv if isinstance(hv, list) else hv.split()
        if 'titulacion' not in hl:
            continue
        fam_id = next((p for p in hl if p.startswith('fam')), None)
        if not fam_id:
            continue
        a = td.find('a', id=lambda x: x and x.startswith('tit-'))
        if not a:
            continue

        familia = fam_map.get(fam_id)
        if not familia:
            logger.warning(
                f"Família desconeguda per fam_id='{fam_id}' al Grado {grado}"
            )
            familia = 'Desconeguda'

        href = a.get('href', '')
        records.append({
            'denominacion': a.get_text(strip=True),
            'familia': familia,
            'nivel': nivel,
            'codigo': None,
            'plan_antiguo': False,
            'observaciones': '',
            'ficha_url': ('https://www.todofp.es' + href) if href else None,
        })
    return records


def _parse_grado_d(url: str, nivel: int) -> list[dict]:
    """
    Helper intern compartit pels 3 subtipus Grado D (estructura HTML idèntica).

    nivel: 1 (Básico), 2 (Medio), 3 (Superior).
    Fail fast D-01: raise_for_status() propaga HTTPError.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    fam_map = _build_fam_map(soup)
    return _extract_titols(soup, fam_map, nivel=nivel, grado='D')


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def parse_grado_d_basico(url: str) -> list[dict]:
    """Parseja la pàgina HTML de Grado D Básico (nivel=1) i retorna llista de registres."""
    return _parse_grado_d(url, nivel=1)


def parse_grado_d_medio(url: str) -> list[dict]:
    """Parseja la pàgina HTML de Grado D Medio (nivel=2) i retorna llista de registres."""
    return _parse_grado_d(url, nivel=2)


def parse_grado_d_superior(url: str) -> list[dict]:
    """Parseja la pàgina HTML de Grado D Superior (nivel=3) i retorna llista de registres."""
    return _parse_grado_d(url, nivel=3)


def parse_grado_e(url: str) -> list[dict]:
    """
    Parseja la pàgina HTML de Grado E (Cursos d'Especialització) i retorna llista de registres.

    nivel=None per a tots els registres Grado E (HTML-05).
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    fam_map = _build_fam_map(soup)
    return _extract_titols(soup, fam_map, nivel=None, grado='E')
