# Pla 066 — FPO extern: Cecot i CCOO (Fundació Paco Puerto)

Origen: `cursos_fpo_altres.md` (fonts proposades per l'usuari) + verificació 2026-09-25.
Depèn de: **062, 063 i 064 DONE** (reutilitza `ext_cursos.json`, `refresh_ext_cursos`, `fpo_ext.py` i la UI de font/tipus).
Sessió neta. **TDD estricte**, tests **sense xarxa**. **No cal decidir res.**

## Fonts descartades (no re-investigar)

UGT/IDFO (TLS obsolet; des del VPS no connecta; "no hi ha cursos programats"), Diputació/`ocupacio.diba.cat`
(formació per a tècnics, no per al públic), FUNDAE (no respon), SEPE (residual a Catalunya), Barcelona Activa
(oferta repartida en 3–4 webs Liferay, sobretot tallers digitals curts; cost alt, poc encaix).

## Fets verificats (2026-09-25; no re-investigar)

**Cecot** (`formacio.cecot.org`):
- Llista: `GET https://formacio.cecot.org/courses/list?public=1` → `{"success": true, "data": {"items": {"list": [...]}}}`.
  **25 cursos en total**, sense paginació. Camps: `Codi`, `Descripcio`, `Hores`, `Inici` (dd/mm/aaaa), `Poblacio`
  (`Terrassa` o `Virtual`), `Modalitat` (`Presencial`/`Virtual`/`Online`), `Pagament` (`N`/`S`).
- Fitxa: `https://formacio.cecot.org/Cursos/Curs/(code)/<Codi>` (el `(code)` és literal). Porta
  `<div class="folder-date-start" data-date="dd/mm/aaaa">` i `folder-date-finish` (la data de **fi només és aquí**),
  i una taula `.course-features-block` amb parelles `<th scope="row">Clau</th><td>Valor</td>`:
  `Tipus`, `Adreçat a`, `Modalitat`, `Sector`, `Durada`, `Dies` (`DL DM DC DJ DV`), `Horari laboral`, `Adreça`
  (`Vapor Universitari<br />Carrer Colon, 114 2a planta<br />08223 - Terrassa`).
- `Pagament: N` = gratuït (els codis `A…FOAP…` són FOAP del SOC, que **no surten** al cercador del SOC; els `F…`,
  formació subvencionada). `S` = de pagament (`P…`, jornades i seminaris curts).

**CCOO → Fundació Paco Puerto** (`fundaciopacopuerto.cat`, WordPress + WooCommerce):
- Llista: `GET /wp-json/wp/v2/product?per_page=100&page=N&_fields=id,link,title,product_cat,localitat` → **85 productes**.
- Taxonomies: `/wp-json/wp/v2/product_cat?per_page=100` (arbre per `parent`) i `/wp-json/wp/v2/localitat?per_page=100`.
- Arrels que **no** són FPO i s'exclouen: `funcio-publica-oposicions` (oposicions) i `formacio-sindical`.
- Fitxa (HTML): `h1` = títol; blocs `.cursos-meta.dates` ("Inici: dd/mm/aaaa · Fi: dd/mm/aaaa", **61 de 85**),
  `.duration` ("30h"), `.modality` (`Presencial`/`Teleformacio`/`Aula Virtual`), `.timetable` (text lliure, opcional).
  La descripció és a `.fpp-single-product-tab-information-wrapper`; si diu "subvencionat" el curs és subvencionat
  (59 de 85). No hi ha preu publicat.
- Localitat `(A determinar)` = sense municipi.

## Decisions de disseny

1. Dues fonts noves a `ext_cursos.json`: `font = 'cecot'` i `font = 'ccoo'`, amb el mateix format que PIMEC/Foment.
2. **Tipus:** Cecot `Pagament N` → `Subvencionat`, `S` → `Altres`. CCOO: "subvencionat" a la descripció → `Subvencionat`, si no → `Altres`.
3. **Família:** camp nou opcional `familiaCodi` al curs, que el scraper omple quan la font en té (CCOO, per categoria
   arrel; vegeu `ROOT_FAMILIA`). `fpo_ext.familia_codi` el fa servir primer. Cecot no en té → `FCO`.
4. **Àrea:** CCOO = nom de la subcategoria; Cecot = buida.
5. `idCurs`: `CECOT:<Codi>` i `CCOO:<id del producte>`.
6. Si una fitxa falla, el curs de Cecot es manté amb les dades de la llista (sense data de fi); el de CCOO s'omet.
7. Pausa de cortesia 0,2 s entre fitxes (25 + ~70 peticions: < 1 min).

## Fitxers

- Crear `backend/scrapers/cecot_scraper.py`, `backend/scrapers/ccoo_scraper.py`.
- Modificar `backend/fpo_ext.py`, `backend/scrapers/pipeline.py`, `frontend/index.html`, `frontend/i18n.js`,
  `frontend/fonts.html`, `frontend/historial.html`.
- Tests nous: `backend/tests/test_cecot_scraper.py`, `backend/tests/test_ccoo_scraper.py`; ampliar `backend/tests/test_fpo_ext.py`.

Tests per ruta (des de `fp-cercador/backend`):
`python3 -m pytest -q tests/test_cecot_scraper.py tests/test_ccoo_scraper.py tests/test_fpo_ext.py tests/test_ext_refresh.py`
+ regressió estàndard `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`.

---

## Fase 1 — Scraper Cecot

### 1.1 Tests (falla primer)

Crear `backend/tests/test_cecot_scraper.py`:

```python
"""test_cecot_scraper.py — Cursos de Cecot Formació (Pla 066). Sense xarxa."""
import requests

from scrapers import cecot_scraper as ce

ITEM = {'Codi': 'A2025FOAP0015000015', 'Descripcio': 'Atenció sociosanitària', 'Hores': '480',
        'Inici': '01/09/2026', 'Poblacio': 'Terrassa', 'Modalitat': 'Presencial', 'Pagament': 'N'}

DETAIL = '''
<div class="folder-date d-flex">
  <div class="folder-date-start" data-date="01/09/2026"><div class="folder-date-when">Inici</div></div>
  <div class="folder-date-finish" data-date="04/01/2027"><div class="folder-date-when">Final</div></div>
</div>
<div class="course-features-block"><table class="table"><tbody>
  <tr><th scope="row">Tipus</th><td>Curs</td><th scope="row">Adreçat a</th><td>Treballadors/es a l'atur</td></tr>
  <tr><th scope="row">Durada</th><td>480 hores</td><th scope="row">Dies</th><td>DL DM DC DJ DV</td></tr>
  <tr><th scope="row">Pagament</th><td><img src="x.png"/></td><th scope="row">Horari laboral</th><td>De 09:00 a 14:00</td></tr>
  <tr><th scope="row">Adreça</th><td>Vapor Universitari<br />Carrer Colon, 114 2a planta<br />08223 - Terrassa</td>
      <th scope="row"></th><td></td></tr>
</tbody></table></div>
'''


def test_parse_detail():
    d = ce.parse_detail(DETAIL)
    assert (d['dataInici'], d['dataFi']) == ('2026-09-01', '2027-01-04')
    assert d['camps']['Dies'] == 'DL DM DC DJ DV' and d['camps']['Horari laboral'] == 'De 09:00 a 14:00'
    assert d['adreca'] == ['Vapor Universitari', 'Carrer Colon, 114 2a planta', '08223 - Terrassa']


def test_parse_detail_buit():
    assert ce.parse_detail('<html></html>') == {'dataInici': None, 'dataFi': None, 'camps': {}, 'adreca': []}


def test_normalize_amb_fitxa():
    c = ce.normalize(ITEM, ce.parse_detail(DETAIL))
    assert c['idCurs'] == 'CECOT:A2025FOAP0015000015' and c['font'] == 'cecot'
    assert c['tipus'] == 'Subvencionat' and c['estat'] == '' and c['familiaCodi'] == ''
    assert c['titol'] == {'ca': 'Atenció sociosanitària', 'es': 'Atenció sociosanitària'}
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-09-01', '2027-01-04', 480.0)
    assert (c['modalitat'], c['municipi']) == ('PRESENCIAL', 'Terrassa')
    assert c['horariText'] == 'DL DM DC DJ DV · De 09:00 a 14:00'
    assert c['centre']['nom'] == 'Cecot · Vapor Universitari'
    assert (c['centre']['carrer'], c['centre']['cp'], c['centre']['municipi']) == (
        'Carrer Colon, 114 2a planta', '08223', 'Terrassa')
    assert c['fitxaUrl'] == 'https://formacio.cecot.org/Cursos/Curs/(code)/A2025FOAP0015000015'


def test_normalize_sense_fitxa_de_pagament_virtual():
    item = dict(ITEM, Codi='P1', Poblacio='Virtual', Modalitat='Virtual', Pagament='S', Hores='3')
    c = ce.normalize(item, None)
    assert c['tipus'] == 'Altres' and c['modalitat'] == 'VIDEOCONFERÈNCIA' and c['municipi'] == ''
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-09-01', None, 3.0)
    assert c['centre']['nom'] == 'Cecot' and c['horariText'] == ''


class _Resp:
    def __init__(self, text='', data=None, exc=None):
        self.text, self._data, self._exc = text, data, exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._data


class _Sess:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, headers=None, timeout=None):
        return self.pages[url]


def test_build_llista_i_fitxes_i_tolera_una_fitxa_que_falla(monkeypatch):
    monkeypatch.setattr(ce, 'PAUSA_S', 0)
    ko = dict(ITEM, Codi='KO')
    sess = _Sess({
        ce.LIST_URL: _Resp(data={'success': True, 'data': {'items': {'list': [ITEM, ko]}}}),
        ce.DETAIL_URL.format(codi=ITEM['Codi']): _Resp(text=DETAIL),
        ce.DETAIL_URL.format(codi='KO'): _Resp(exc=requests.HTTPError('500')),
    })
    out = ce.build_cecot_cursos(session=sess)
    assert [c['idCurs'] for c in out] == ['CECOT:A2025FOAP0015000015', 'CECOT:KO']
    assert out[0]['dataFi'] == '2027-01-04' and out[1]['dataFi'] is None


def test_build_resposta_inesperada_peta():
    sess = _Sess({ce.LIST_URL: _Resp(data={'success': False})})
    try:
        ce.build_cecot_cursos(session=sess)
    except ValueError:
        return
    raise AssertionError('havia de fallar')
```

Executar: ha de **fallar** (`ModuleNotFoundError`).

### 1.2 Implementació

Crear `backend/scrapers/cecot_scraper.py`:

```python
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
```

Executar els tests de la fase: han de **passar**.

### 1.3 Commit
```
git add backend/scrapers/cecot_scraper.py backend/tests/test_cecot_scraper.py
git commit -m "feat(fpo): scraper de cursos de Cecot"
```

---

## Fase 2 — Scraper CCOO (Fundació Paco Puerto)

### 2.1 Tests (falla primer)

Crear `backend/tests/test_ccoo_scraper.py`:

```python
"""test_ccoo_scraper.py — Cursos de CCOO / Fundació Paco Puerto (Pla 066). Sense xarxa."""
from scrapers import ccoo_scraper as cc

CATS = [
    {'id': 147, 'slug': 'informatica-i-comunicacions', 'name': 'Informàtica i comunicacions', 'parent': 0},
    {'id': 158, 'slug': 'ofimatica-i-internet', 'name': 'Ofimàtica i internet', 'parent': 147},
    {'id': 140, 'slug': 'funcio-publica-oposicions', 'name': 'Funció pública', 'parent': 0},
    {'id': 142, 'slug': 'autonomica-generalitat', 'name': 'Autonòmica', 'parent': 140},
    {'id': 149, 'slug': 'formacio-transversal', 'name': 'Formació transversal', 'parent': 0},
]
LOCS = [{'id': 289, 'name': 'Barcelona'}, {'id': 306, 'name': '(A determinar)'}]

PAGE = '''<html><body><h1>Excel &amp; Word avançat</h1>
<div class="cursos-meta alone dates"><div class="content">
  <p class="uppercase"><strong>Inici:</strong> 21/10/2026</p><p class="uppercase"><strong>Fi:</strong> 11/11/2026</p></div></div>
<div class="cursos-meta alone duration"><div class="content">30h</div></div>
<div class="cursos-meta alone modality"><div class="content">Teleformacio</div></div>
<div class="cursos-meta alone timetable"><div class="content">dimarts i dijous de 18:00 a 21:00 hores</div></div>
<div class="fpp-single-product-tab-information-wrapper">Aquest curs subvencionat proporcionarà...</div>
</body></html>'''

PAGE_SENSE = '''<html><body><h1>Curs obert</h1>
<div class="cursos-meta alone duration"><div class="content">12h</div></div>
<div class="cursos-meta alone modality"><div class="content">Aula Virtual</div></div>
<div class="fpp-single-product-tab-information-wrapper">Curs per a persones interessades.</div></body></html>'''


def test_roots():
    r = cc.roots(CATS)
    assert r[158] == 'informatica-i-comunicacions' and r[142] == 'funcio-publica-oposicions' and r[147] == 'informatica-i-comunicacions'


def test_parse_page():
    d = cc.parse_page(PAGE)
    assert d['titol'] == 'Excel & Word avançat'
    assert (d['dataInici'], d['dataFi'], d['hores']) == ('2026-10-21', '2026-11-11', 30.0)
    assert d['modalitat'] == 'TELEFORMACIÓ' and d['horariText'].startswith('dimarts i dijous')
    assert d['subvencionat'] is True


def test_parse_page_sense_dates():
    d = cc.parse_page(PAGE_SENSE)
    assert (d['dataInici'], d['dataFi'], d['hores']) == (None, None, 12.0)
    assert d['modalitat'] == 'VIDEOCONFERÈNCIA' and d['subvencionat'] is False and d['horariText'] == ''


def test_normalize():
    prod = {'id': 90288, 'link': 'https://fundaciopacopuerto.cat/cursos-formacio/x/excel-90288/',
            'product_cat': [158], 'localitat': [289]}
    c = cc.normalize(prod, cc.parse_page(PAGE), cc.roots(CATS), {c['id']: c for c in CATS},
                     {l['id']: l['name'] for l in LOCS})
    assert c['idCurs'] == 'CCOO:90288' and c['font'] == 'ccoo' and c['tipus'] == 'Subvencionat'
    assert c['familiaCodi'] == 'IFC' and c['area'] == 'Ofimàtica i internet'
    assert c['municipi'] == 'Barcelona' and c['centre']['nom'] == 'Fundació Paco Puerto (CCOO)'
    assert c['fitxaUrl'] == prod['link'] and c['estat'] == ''


def test_localitat_a_determinar_i_sense_area():
    prod = {'id': 1, 'link': 'https://x/1/', 'product_cat': [149], 'localitat': [306]}
    c = cc.normalize(prod, cc.parse_page(PAGE_SENSE), cc.roots(CATS), {c['id']: c for c in CATS},
                     {l['id']: l['name'] for l in LOCS})
    assert c['municipi'] == '' and c['familiaCodi'] == 'FCO' and c['area'] == '' and c['tipus'] == 'Altres'


def test_es_fpo_exclou_oposicions_i_sindical():
    r = cc.roots(CATS)
    assert cc.es_fpo({'product_cat': [158]}, r) is True
    assert cc.es_fpo({'product_cat': [142]}, r) is False
    assert cc.es_fpo({'product_cat': [158, 142]}, r) is False


class _Resp:
    def __init__(self, data=None, text=''):
        self._data, self.text = data, text

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _Sess:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(url)
        if url.endswith('/product_cat'):
            return _Resp(CATS if (params or {}).get('page', 1) == 1 else [])
        if url.endswith('/localitat'):
            return _Resp(LOCS if (params or {}).get('page', 1) == 1 else [])
        if url.endswith('/product'):
            if (params or {}).get('page') == 1:
                return _Resp([{'id': 1, 'link': 'https://x/ok/', 'product_cat': [158], 'localitat': [289]},
                              {'id': 2, 'link': 'https://x/opo/', 'product_cat': [142], 'localitat': [289]}])
            return _Resp([])
        return _Resp(text=PAGE)


def test_build_filtra_i_no_baixa_les_fitxes_excloses(monkeypatch):
    monkeypatch.setattr(cc, 'PAUSA_S', 0)
    sess = _Sess()
    out = cc.build_ccoo_cursos(session=sess)
    assert [c['idCurs'] for c in out] == ['CCOO:1']
    assert 'https://x/opo/' not in sess.calls
```

Executar: ha de **fallar**.

### 2.2 Implementació

Crear `backend/scrapers/ccoo_scraper.py`:

```python
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
```

> Nota: al fake de test, `_all` acaba quan un lot té menys de 100 elements, i per això la segona pàgina
> no es demana; el fake també retorna `[]` si es demanés.

Executar els tests de la fase: han de **passar**.

### 2.3 Commit
```
git add backend/scrapers/ccoo_scraper.py backend/tests/test_ccoo_scraper.py
git commit -m "feat(fpo): scraper de cursos de CCOO (Fundació Paco Puerto)"
```

---

## Fase 3 — Integració (`fpo_ext`, pipeline)

### 3.1 Tests (falla primer)

Afegir al final de `backend/tests/test_fpo_ext.py`:

```python
def test_fonts_noves_i_familia_explicita():
    assert fx.is_ext_codi('CECOT:x') and fx.is_ext_codi('CCOO:1')
    c = _c('ccoo', 1, 'Excel', familiaCodi='IFC')
    assert fx.familia_codi(c, FAMS) == 'IFC'
    assert fx.familia_codi(_c('ccoo', 2, 'Excel', familiaCodi='ZZZ'), FAMS) == 'FCO'
    assert fx.familia_codi(_c('cecot', 3, 'Anglès'), FAMS) == 'FCO'
    idx = fx.build_index([_c('cecot', 'a', 'Anglès B1'), _c('ccoo', 'b', 'Anglès B1')], FAMS, TODAY)
    assert [e['codi'] for e in idx['list']] == ['CCOO:angles-b1', 'CECOT:angles-b1']
```

I a `backend/tests/test_ext_refresh.py`, substituir `test_refresh_ok_escriu_les_dues_fonts` per:

```python
def test_refresh_ok_escriu_les_quatre_fonts(tmp_path):
    with patch('scrapers.pimec_scraper.build_pimec_cursos',
               return_value=[_c('pimec', 'a'), _c('pimec', 'b')]), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[_c('foment', 'x')]), \
         patch('scrapers.cecot_scraper.build_cecot_cursos', return_value=[_c('cecot', 'c')]), \
         patch('scrapers.ccoo_scraper.build_ccoo_cursos', return_value=[_c('ccoo', 'd')]):
        res = pipeline.refresh_ext_cursos(str(tmp_path))
    assert res == {'pimec': 2, 'foment': 1, 'cecot': 1, 'ccoo': 1}
    assert _ids(tmp_path) == ['CCOO:d', 'CECOT:c', 'FOMENT:x', 'PIMEC:a', 'PIMEC:b']
```

Els altres tests de `test_ext_refresh.py` que només posen `patch` a PIMEC i Foment **també han de mockejar Cecot i
CCOO**, o farien xarxa. Afegir a dalt del fitxer una fixture `autouse` que els mockegi per defecte:

```python
import pytest


@pytest.fixture(autouse=True)
def _sense_cecot_ni_ccoo():
    with patch('scrapers.cecot_scraper.build_cecot_cursos', return_value=[{'idCurs': 'CECOT:0', 'font': 'cecot'}]), \
         patch('scrapers.ccoo_scraper.build_ccoo_cursos', return_value=[{'idCurs': 'CCOO:0', 'font': 'ccoo'}]):
        yield
```
(Els `patch` del test nou tenen prioritat perquè s'apliquen dins; els asserts dels tests existents que comproven
`_ids` o recomptes de PIMEC/Foment s'han d'ajustar: `test_font_que_falla_conserva_l_anterior_i_avisa` passa a esperar
`['CCOO:0', 'CECOT:0', 'FOMENT:y', 'PIMEC:a', 'PIMEC:b']`, i `test_no_sobreescriu_si_baixa_a_menys_de_la_meitat`
`len(_ids(tmp_path)) == 6`.)

Executar: ha de **fallar**.

### 3.2 Implementació

**a) `backend/fpo_ext.py`.** `FONTS = ('pimec', 'foment', 'cecot', 'ccoo')`, i substituir `familia_codi`:

```python
def familia_codi(curs: dict, families: dict) -> str:
    codi = curs.get('familiaCodi') or ''
    if not codi:
        if curs.get('font') == 'pimec':
            codi = PIMEC_AREA_FAMILIA.get((curs.get('area') or '').strip().lower(), FALLBACK_FAMILIA)
        else:
            codi = (curs.get('certCodi') or '')[:3]
    return codi if codi in families else FALLBACK_FAMILIA
```

**b) `backend/scrapers/pipeline.py`, `refresh_ext_cursos`.** Canviar l'import i la tupla de fonts:

```python
    from scrapers import ccoo_scraper, cecot_scraper, ext_cursos, foment_scraper, pimec_scraper
```
```python
    fonts = (('pimec', pimec_scraper.build_pimec_cursos),
             ('foment', foment_scraper.build_foment_cursos),
             ('cecot', cecot_scraper.build_cecot_cursos),
             ('ccoo', ccoo_scraper.build_ccoo_cursos))
```
Actualitzar el docstring: "PIMEC, Foment, Cecot i CCOO -> ext_cursos.json (Plans 062, 066)".

Executar els tests de la fase + regressió: han de **passar**.

### 3.3 Commit
```
git add backend/fpo_ext.py backend/scrapers/pipeline.py backend/tests/test_fpo_ext.py backend/tests/test_ext_refresh.py
git commit -m "feat(fpo): Cecot i CCOO entren al snapshot de cursos externs"
```

---

## Fase 4 — Frontend

**a) `frontend/index.html`, `fpoFontsOpcions`:**
`old`: `return ['soc', 'pimec', 'foment'].filter(f => presents.has(f));`
`new`: `return ['soc', 'pimec', 'foment', 'cecot', 'ccoo'].filter(f => presents.has(f));`

**b) `frontend/i18n.js`.** Després de `'fpo.font.foment': 'Foment',` (apareix 2 cops: un per idioma, afegir a tots dos):
```js
      'fpo.font.cecot': 'Cecot',
      'fpo.font.ccoo': 'CCOO',
```

Claus per a `fonts.html`: després de `'fonts.r14.us': ...` de cada idioma.

CA:
```js
      'fonts.s9.h2': 'Cecot Formació',
      'fonts.s9.host': 'formacio.cecot.org',
      'fonts.s9.p': 'Patronal amb seu a Terrassa i entitat formadora acreditada. Es llegeix el seu cercador públic de cursos. Els cursos gratuïts es marquen com a «Subvencionat» i els de pagament com a «Altres».',
      'fonts.r15.font': 'Cursos de Cecot',
      'fonts.r15.detall': 'Títol, dates, hores, modalitat, horari, adreça i enllaç a la fitxa de Cecot.',
      'fonts.r15.us': 'Mode «Cursos FPO (Catalunya)» del cercador, marcats amb la font Cecot.',
      'fonts.s10.h2': 'Fundació Paco Puerto (CCOO)',
      'fonts.s10.host': 'fundaciopacopuerto.cat',
      'fonts.s10.p': 'Entitat formadora de CCOO de Catalunya. Es llegeix el seu catàleg públic de cursos, sense les oposicions ni la formació sindical.',
      'fonts.r16.font': 'Cursos de la Fundació Paco Puerto',
      'fonts.r16.detall': 'Títol, família, dates, hores, modalitat, horari, localitat i enllaç a la fitxa.',
      'fonts.r16.us': 'Mode «Cursos FPO (Catalunya)» del cercador, marcats amb la font CCOO.',
```

ES:
```js
      'fonts.s9.h2': 'Cecot Formació',
      'fonts.s9.host': 'formacio.cecot.org',
      'fonts.s9.p': 'Patronal con sede en Terrassa y entidad formadora acreditada. Se lee su buscador público de cursos. Los cursos gratuitos se marcan como «Subvencionado» y los de pago como «Otros».',
      'fonts.r15.font': 'Cursos de Cecot',
      'fonts.r15.detall': 'Título, fechas, horas, modalidad, horario, dirección y enlace a la ficha de Cecot.',
      'fonts.r15.us': 'Modo «Cursos FPO (Cataluña)» del buscador, marcados con la fuente Cecot.',
      'fonts.s10.h2': 'Fundació Paco Puerto (CCOO)',
      'fonts.s10.host': 'fundaciopacopuerto.cat',
      'fonts.s10.p': 'Entidad formadora de CCOO de Cataluña. Se lee su catálogo público de cursos, sin las oposiciones ni la formación sindical.',
      'fonts.r16.font': 'Cursos de la Fundació Paco Puerto',
      'fonts.r16.detall': 'Título, familia, fechas, horas, modalidad, horario, localidad y enlace a la ficha.',
      'fonts.r16.us': 'Modo «Cursos FPO (Cataluña)» del buscador, marcados con la fuente CCOO.',
```

**c) `frontend/fonts.html`.** Just abans de `<h2 data-i18n="fonts.s3.h2">`, afegir dues seccions amb la
mateixa estructura que les de PIMEC i Foment (Pla 064, Fase 5a): `fonts.s9.*` + fila `fonts.r15.*`, i
`fonts.s10.*` + fila `fonts.r16.*`, amb els textos CA de dalt com a contingut per defecte.

**d) `frontend/historial.html`.**
`old`: `const FONT_LABEL = { soc: 'SOC', pimec: 'PIMEC', foment: 'Foment' };`
`new`: `const FONT_LABEL = { soc: 'SOC', pimec: 'PIMEC', foment: 'Foment', cecot: 'Cecot', ccoo: 'CCOO' };`

Verificació: `node --check frontend/i18n.js` i el script de paritat de claus del Pla 064 (Fase 1) ha d'imprimir `OK`.

### Commit
```
git add frontend/index.html frontend/i18n.js frontend/fonts.html frontend/historial.html
git commit -m "feat(fpo): la UI mostra Cecot i CCOO com a fonts"
```

---

## Fase 5 — Verificació real i desplegament

1. Xarxa, a un directori temporal:
```
python3 - <<'EOF'
import collections, tempfile
from scrapers import cecot_scraper, ccoo_scraper
for nom, f in (('cecot', cecot_scraper.build_cecot_cursos), ('ccoo', ccoo_scraper.build_ccoo_cursos)):
    c = f()
    print(nom, len(c), collections.Counter(x['tipus'] for x in c),
          'amb dataFi:', sum(1 for x in c if x['dataFi']), 'famílies:', collections.Counter(x['familiaCodi'] for x in c))
EOF
```
Esperat (verificat en sec el 2026-09-25): `cecot` 25 (19 Subvencionat / 6 Altres; 25 amb `dataFi`; tots FCO),
`ccoo` 70 (58 Subvencionat / 12 Altres; 58 amb dates; 13 famílies: FCO 18, IFC 16, SSC 7, SEA 6, COM 5, SAN 5…). Si `ccoo` < 40 o `cecot` = 0, **aturar-se i informar**.
2. Comprovacions de UI de la Fase 6 del Pla 064, repetint 3–7 amb `Font = Cecot` i `Font = CCOO`.
3. Desplegament amb ordre de l'usuari (igual que el Pla 064, Fase 7): backend → `systemctl restart fp-cercador` →
   refresc d'admin → comprovar `/api/fpo/especialitats` amb `font: cecot` i `font: ccoo`.

## Fora d'abast

UGT/IDFO, Barcelona Activa, Diputació, FUNDAE, SEPE (vegeu dalt). Estat d'inscripció real de Cecot o CCOO (no el publiquen).
