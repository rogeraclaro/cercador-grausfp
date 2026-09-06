"""
soc_scraper.py — Snapshot de l'oferta de formació professional per a l'ocupació
(FPO) del Servei Públic d'Ocupació de Catalunya (SOC) (Pla 059).

El cercador integrat del SOC està servit per Algolia. El frontend hi consulta
directament amb claus de lectura públiques incrustades al JS. Recorrem l'índex
sencer amb l'endpoint `browse` (sense captcha ni cookies, CORS obert).

Genera 3 fitxers a backend/data/:
  soc_cursos.json  — cursos FPO programats a Catalunya
  soc_especs.json  — catàleg d'especialitats formatives
  soc_centres.json — centres i entitats de formació

Els camps bilingües del SOC ({cat, cas}) es guarden com {ca, es}; el frontend
tria l'idioma. Si el SOC rota les claus API, `browse` retorna 401/403 i aixequem
`SocKeyError` (el pipeline ho tracta com a no-fatal i avisa l'admin).
"""
import json
import logging
import os
import tempfile

import requests

logger = logging.getLogger(__name__)

ALGOLIA_APP = 'GAVVNU5N19'
ALGOLIA_HOST = f'https://{ALGOLIA_APP}-dsn.algolia.net'

INDEXES = {
    'cursos':  ('pro_SOC_CURSOS',     '1a344732c2a6e07f1e8aded4b3ec5ee5'),
    'especs':  ('pro_SOC_ESPECS_r1a', 'a71db7100e3362cc9522f7c7f79f954f'),
    'centres': ('pro_SOC_CENTRES',    '08611804f7810c349cd2b2bc8a77e438'),
}

_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

_INVALID_RD = {'', 'undefined', 'null', None}


class SocKeyError(Exception):
    """La clau API del SOC ja no és vàlida (probablement rotada)."""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _new_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({'User-Agent': _UA, 'Content-Type': 'application/x-www-form-urlencoded'})
    return s


HITS_PER_PAGE = 1000


def _algolia_query(index: str, key: str, params: str, session=None, timeout: int = 30) -> dict:
    """POST /1/indexes/<index>/query. La clau pública només té l'ACL `search`
    (l'endpoint `browse` retorna 403), així que paginem amb `page`."""
    session = session or _new_session()
    url = f'{ALGOLIA_HOST}/1/indexes/{index}/query'
    headers = {'X-Algolia-Application-Id': ALGOLIA_APP, 'X-Algolia-API-Key': key}
    resp = session.post(url, headers=headers, data=json.dumps({'params': params}), timeout=timeout)
    if resp.status_code in (401, 403):
        raise SocKeyError(f'{index}: clau API rebutjada (HTTP {resp.status_code}) — possiblement rotada')
    resp.raise_for_status()
    return resp.json()


def _fetch_all(index: str, key: str) -> list[dict]:
    session = _new_session()
    first = _algolia_query(index, key, f'query=&hitsPerPage={HITS_PER_PAGE}&page=0', session=session)
    hits = list(first.get('hits', []))
    n_pages = int(first.get('nbPages') or 1)
    for page in range(1, n_pages):
        more = _algolia_query(index, key, f'query=&hitsPerPage={HITS_PER_PAGE}&page={page}', session=session)
        hits.extend(more.get('hits', []))
    return hits


# ---------------------------------------------------------------------------
# Helpers de normalització
# ---------------------------------------------------------------------------

def _t(obj) -> dict:
    """{'cat':..,'cas':..} -> {'ca':..,'es':..}"""
    obj = obj or {}
    return {'ca': obj.get('cat', '') or '', 'es': obj.get('cas', '') or ''}


def _date(s) -> str | None:
    """'dd/mm/aaaa' -> 'aaaa-mm-dd'; buit o invàlid -> None."""
    parts = (s or '').split('/')
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    d, m, y = parts
    return f'{y}-{m.zfill(2)}-{d.zfill(2)}'


def _num(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _coord(v) -> float | None:
    """lat/lon del SOC: '0' o buit vol dir "sense coordenades"."""
    n = _num(v)
    return None if n in (None, 0.0) else n


def _bool_sn(v) -> bool:
    return str(v).strip().upper() == 'S'


def _estat(s) -> str:
    low = (s or '').lower()
    if 'inscripci' in low:
        return 'inscripcio'
    if 'informaci' in low:
        return 'informacio'
    if 'gesti' in low:
        return 'gestio'
    return low.strip()


def _rd(cert_prof) -> str | None:
    cp = (cert_prof or '').strip()
    return None if cp in _INVALID_RD else cp


def _moduls(unitat_competencia) -> list[dict]:
    out = []
    for uc in unitat_competencia or []:
        for mf in uc.get('modulFormatiu') or []:
            out.append({
                'codi': mf.get('codi', ''),
                'desc': _t(mf.get('desc')),
                'durada': _num(mf.get('durada')) or 0.0,
            })
    return out


def _fam(obj) -> dict:
    obj = obj or {}
    return {'codi': obj.get('codi', '') or '', 'desc': _t(obj.get('desc'))}


# ---------------------------------------------------------------------------
# Normalitzadors
# ---------------------------------------------------------------------------

def normalize_curs(hit: dict) -> dict:
    c = hit.get('centres') or {}
    dades = hit.get('dadesInteres') or {}
    prog = hit.get('programa') or {}
    ocup = [o for o in (hit.get('codOcupacio') or []) if o.get('codi')]
    return {
        'idCurs': hit.get('idCurs', ''),
        'titol': _t(hit.get('titol')),
        'familia': _fam(hit.get('famProf')),
        'area': _fam(hit.get('area')),
        'especialitat': _fam(hit.get('especialitat')),
        'esCertProf': str(hit.get('teCertProf')).strip().lower() == 'si' or _rd(hit.get('certProf')) is not None,
        'rd': _rd(hit.get('certProf')),
        'nivell': int(_num(hit.get('nivellEspecialitat')) or 0),
        'hores': _num(hit.get('hores')) or 0.0,
        'modalitat': hit.get('modalitat', '') or '',
        'estat': _estat(hit.get('estatInscripcio')),
        'dataInici': _date(hit.get('dataInici')),
        'dataFi': _date(hit.get('dataFi')),
        'comarca': hit.get('comarca', '') or '',
        'municipi': hit.get('municipi', '') or '',
        'provincia': hit.get('provincia', '') or '',
        'centre': {
            'nom': c.get('nomLoc', '') or '',
            'carrer': c.get('calleLoc', '') or '',
            'cp': c.get('codPostalLoc', '') or '',
            'municipi': c.get('localidadLoc') or hit.get('municipi', '') or '',
            'comarca': hit.get('comarca', '') or '',
            'telefon': c.get('telefonLoc', '') or '',
            'email': c.get('mailLoc', '') or '',
            'web': c.get('webLoc', '') or '',
            'idCentre': c.get('idCentre', '') or '',
            'horari': c.get('horariLoc') or {},
            'lat': _coord(c.get('lat')),
            'lon': _coord(c.get('lon')),
        },
        'programaUrl': (prog.get('cat') or prog.get('cas') or ''),
        'queAprendras': _t(hit.get('queAprendras')),
        'requisits': _t(dades.get('requisits')),
        'sortides': _t(dades.get('quePoderTreballar')),
        'moduls': _moduls(hit.get('unitatCompetencia')),
        'ocupacions': [{'codi': o.get('codi', ''), 'desc': _t(o.get('desc'))} for o in ocup],
    }


def normalize_espec(hit: dict) -> dict:
    prog = hit.get('programa') or {}
    return {
        'codi': hit.get('codi', ''),
        'titol': _t(hit.get('desc')),
        'familia': _fam(hit.get('familia')),
        'area': _fam(hit.get('area')),
        'nivell': int(_num(hit.get('nivellEspecialitat')) or 0),
        'hores': _num(hit.get('hores')) or 0.0,
        'preu': _num(hit.get('preu')) or 0.0,
        'esCertProf': _rd(hit.get('certProf')) is not None,
        'rd': _rd(hit.get('certProf')),
        'programaUrl': (prog.get('cat') or prog.get('cas') or ''),
        'moduls': _moduls(hit.get('unitatCompetencia')),
        'cursIds': [str(x.get('idCursIntern')) for x in (hit.get('cursos') or []) if x.get('idCursIntern')],
        'destacada': str(hit.get('espDestacada')).strip().upper() == 'S',
    }


def normalize_centre(hit: dict) -> dict:
    d = hit.get('data') or {}
    return {
        'idCentre': d.get('idCentre') or hit.get('idCentre', ''),
        'raoSocial': d.get('raoSocial', '') or '',
        'cif': d.get('cif', '') or '',
        'numCens': d.get('numCens', '') or '',
        'email': d.get('email', '') or '',
        'web': d.get('web', '') or '',
        'codiCentre': d.get('codiCentre', '') or '',
        'carrer': d.get('carrer', '') or '',
        'cp': d.get('cp', '') or '',
        'municipi': d.get('municipi', '') or '',
        'comarca': d.get('comarca', '') or '',
        'provincia': d.get('provincia', '') or '',
        'telefon': d.get('telefon', '') or '',
        'lat': _coord(d.get('lat')),
        'lon': _coord(d.get('lng')),
        'numCursos': int(_num(d.get('numCursos')) or 0),
        'esCifo': _bool_sn(d.get('esCifo')),
        'perDiscapacitats': _bool_sn(d.get('perDiscapacitats')),
    }


# ---------------------------------------------------------------------------
# Orquestració
# ---------------------------------------------------------------------------

def build_soc_data() -> dict:
    """{'cursos': [...], 'especs': [...], 'centres': [...]} normalitzats."""
    cursos = [normalize_curs(h) for h in _fetch_all(*INDEXES['cursos'])]
    especs = [normalize_espec(h) for h in _fetch_all(*INDEXES['especs'])]
    centres = [normalize_centre(h) for h in _fetch_all(*INDEXES['centres'])]
    return {'cursos': cursos, 'especs': especs, 'centres': centres}


def write_soc_data(data: dict, data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    for name, key in (('soc_cursos.json', 'cursos'), ('soc_especs.json', 'especs'),
                      ('soc_centres.json', 'centres')):
        path = os.path.join(data_dir, name)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                         dir=data_dir, delete=False) as tmp:
            json.dump(data[key], tmp, ensure_ascii=False, indent=1)
            tmp_path = tmp.name
        os.replace(tmp_path, path)
