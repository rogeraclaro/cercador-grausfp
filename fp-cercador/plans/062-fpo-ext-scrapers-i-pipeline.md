# Pla 062 — FPO extern (PIMEC + Foment): scrapers, snapshot i pipeline

Origen: `docs/superpowers/specs/2026-09-25-fpo-pimec-foment-design.md` (§3, §4, §5).
Depèn de: 059 DONE (reutilitza historial i avís d'admin).
Primer dels 3 plans (062 dades, 063 backend, 064 frontend). Sessió neta per pla.
Executable per un agent sense context. **TDD estricte**: cada fase escriu primer
els tests, els veu fallar, i després implementa. Tots els tests són **sense xarxa**
(HTML/JSON escrit a mà amb l'estructura real observada). **No cal decidir res.**

## Com executar els tests

Des de `fp-cercador/backend`. Els tests de `*scraper*` queden fora de la comanda
estàndard del projecte (alguns toquen la xarxa), així que **aquests s'executen per
ruta explícita**:

```
python3 -m pytest -q tests/test_pimec_scraper.py tests/test_foment_scraper.py tests/test_ext_refresh.py
```

Regressió (comanda estàndard, ~3 s): `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
(2 fallos coneguts a `test_db.py`, no relacionats). Mai encadenar `git stash pop`.

## Fets verificats (2026-09-25; no re-investigar)

**PIMEC** (`pimecformacio.org`, Drupal):
- `GET https://pimecformacio.org/ca/formacio-inici/ajax` amb params `paraula_clau=`,
  `field_fo_tipus[]=<tipus>` (repetit) i `formacioPagina=<n>` → JSON
  `{data, listcursos, paginador, formulari, formacioPagina}`. `listcursos` és l'HTML
  de 12 targetes. Sense captcha ni cookies.
- Tipus reals: `Altres`, `Bonificable`, `Diàleg Social (Subvencionat)`, `Subvencionat`.
- **El `paginador` menteix**: anuncia 19 pàgines i n'hi ha 35 (417 cursos; la 36 és
  buida). Es pagina fins a una pàgina sense targetes.
- **Les targetes no porten l'àrea.** Es dedueix escanejant un cop per cada valor de
  `field_fo_area[]` (17 àrees; cada curs surt a una sola àrea o cap: 320 de 417).
  Les àrees es llegeixen del camp `formulari` de la primera pàgina.
- 160 dels 417 són `Altres` amb "Dates a concretar" i sense lloc.
- Targeta: `div.curso-lista` > `div.categoria` (tipus), `.datos h2 a` (títol + href),
  `.fecha` (dates + `<span class="duracion"> (30h) </span>`), `.lugar`.
- Formats de `.fecha` (text amb el span inclòs): `28 set. - 26 oct. 2026 (30h)`,
  `29 set. 2026 (2h)`, `19 oct. 2026 - 09 jul. 2027 (245h)`, `Dates a concretar (20h)`.
  Hores poden ser decimals (`1.5h`). Mesos vistos: gen. maig jul. set. oct. nov. des.
- `.lugar`: `BARCELONA Presencial`, `Aula Virtual Videoconferència`, `Aula Virtual Online`
  o buit. Modalitats: Presencial / Online / Mixta / Videoconferència.
- Fitxa: `https://pimecformacio.org` + href (`/ca/pimes-autonoms/formacio/<slug>`), 200.

**Foment** (`fomentformacio.com`, WordPress):
- Sitemap `https://www.fomentformacio.com/curso_foment-sitemap.xml`: 286 URL. Només les
  `/formacion/<slug>` (castellà, 142); les `/ca/formacio/` són duplicats.
  **27 d'aquestes 142 porten un fragment `#edicion-...` (permalink d'una edició): són la
  mateixa pàgina repetida → 114 pàgines úniques.** S'ha de treure el fragment i deduplicar.
- Cada fitxa té **1–4 edicions** (114 pàgines → **150 edicions**; 134 actives, 16 ja finalitzades).
  Cada edició és `<div data-edition="edicion-<modalitat>-dd-mm-aa-<id>">` dins
  `.sidebar-card__list`, amb `.detail-item__texts` = `<label>Etiqueta</label>` +
  `<span>valor</span>`. Etiquetes: `Centro` (amb `<a href="...query=LAT,LON">`),
  `Comienzo` / `Final` (`dd/mm/aaaa`), `Horario` (opcional, text lliure), `Horas`
  (`190 horas`).
- Títol: `h1.hero-curso__title`. Només 5 de 110 títols distints comencen amb codi de certificat
  (`ADGG0208: Ofimática`).
- 9 ids d'edició es repeteixen entre pàgines diferents: la clau és `slug + id`.
- Modalitat = prefix de l'id: `presencial` / `online` / `virtual`.
- Foment no publica un "tipus" per curs: es fixa `Altres`.

## Decisions de disseny

1. **Un curs extern = una edició**, mateix format que `soc_cursos.json` més camps
   propis (vegeu `ext_cursos.py`). Fitxer: `data/ext_cursos.json` (llista).
2. **Vocabulari de modalitat del SOC** (el frontend en fa `tc()`): PRESENCIAL,
   TELEFORMACIÓ, MIXTA, VIDEOCONFERÈNCIA. PIMEC Online→TELEFORMACIÓ; Foment
   `virtual`→VIDEOCONFERÈNCIA, `online`→TELEFORMACIÓ.
3. `estat` es guarda **sempre buit** al snapshot; `finalitzat` es deriva en llegir (Pla 063).
4. **Snapshot segur per font:** si un scraper falla, o retorna menys de la meitat dels
   cursos anteriors (o 0), es conserva el snapshot anterior d'aquesta font, s'anota
   l'error a l'historial i s'avisa l'admin (màx. 1/dia per font).
5. **Historial compartit:** les entrades van a `soc_refresh_history.json` amb el camp
   `font` (`pimec`/`foment`); `_soc_diff_entry` ja el té.
6. Pauses de cortesia de 0,2 s entre peticions; `MAX_PAGES = 100` com a xarxa de seguretat.

## Fitxers

- Crear `backend/scrapers/pimec_scraper.py`, `backend/scrapers/foment_scraper.py`,
  `backend/scrapers/ext_cursos.py`.
- Modificar `backend/scrapers/pipeline.py` (`_soc_diff_entry`, `_notify_admin_soc_failure`,
  nou `refresh_ext_cursos`, bloc a `run()`).
- Tests nous: `backend/tests/test_pimec_scraper.py`, `test_foment_scraper.py`, `test_ext_refresh.py`.

---

## Fase 1 — Scraper PIMEC

### 1.1 Tests (falla primer)

Crear `backend/tests/test_pimec_scraper.py`:

```python
"""test_pimec_scraper.py — Cursos de PIMEC Formació (Pla 062). Sense xarxa."""
import pytest

from scrapers import pimec_scraper as pim


def _card(slug, tipus, fecha, hores, lloc, titol='Curs X'):
    """Targeta amb l'estructura real de listcursos."""
    return (
        '<div class="col col-lg-4"><div class="curso-lista categoria-x">'
        f'<div class="imagen"><a href="/ca/pimes-autonoms/formacio/{slug}"><img src="i.jpg"/></a></div>'
        f'<div class="categoria"> {tipus} </div>'
        f'<div class="datos"><h2><a href="/ca/pimes-autonoms/formacio/{slug}">{titol}</a></h2>'
        f'<div class="fecha"> {fecha} <span class="duracion"> ({hores}h) </span></div>'
        f'<div class="lugar"> {lloc} </div><div class="precio"> </div></div></div></div>'
    )


def _one(fecha, hores=30, lloc='BARCELONA Presencial', tipus='Subvencionat'):
    return pim.parse_cards(_card('s-1', tipus, fecha, hores, lloc))[0]


def test_rang_dins_del_mateix_any():
    c = pim.parse_cards(_card('a-1', 'Subvencionat', '28 set. - 26 oct. 2026', 30,
                              'BADALONA Presencial', 'Manipulació d´equips'))[0]
    assert c['slug'] == 'a-1' and c['titol'] == 'Manipulació d´equips'
    assert c['tipus'] == 'Subvencionat'
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-09-28', '2026-10-26', 30.0)
    assert (c['municipi'], c['modalitat']) == ('BADALONA', 'PRESENCIAL')
    assert c['url'] == 'https://pimecformacio.org/ca/pimes-autonoms/formacio/a-1'


def test_data_unica_i_hores_decimals():
    c = _one('05 oct. 2026', hores='1.5')
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-10-05', '2026-10-05', 1.5)


def test_rang_que_creua_d_any_amb_any_explicit():
    c = _one('19 oct. 2026 - 09 jul. 2027', hores=245)
    assert (c['dataInici'], c['dataFi']) == ('2026-10-19', '2027-07-09')


def test_rang_que_creua_d_any_sense_any_a_l_inici():
    c = _one('15 des. - 20 gen. 2027')
    assert (c['dataInici'], c['dataFi']) == ('2026-12-15', '2027-01-20')


def test_dates_a_concretar():
    c = _one('Dates a concretar', hores=20, lloc='', tipus='Altres')
    assert (c['dataInici'], c['dataFi'], c['hores']) == (None, None, 20.0)
    assert (c['municipi'], c['modalitat']) == ('', '')
    assert c['tipus'] == 'Altres'


def test_mes_desconegut_no_peta():
    c = _one('05 xyz. 2026')
    assert (c['dataInici'], c['dataFi']) == (None, None)


@pytest.mark.parametrize('lloc, esperat', [
    ('Aula Virtual Videoconferència', ('', 'VIDEOCONFERÈNCIA')),
    ('Aula Virtual Online', ('', 'TELEFORMACIÓ')),
    ('GRANOLLERS Presencial', ('GRANOLLERS', 'PRESENCIAL')),
    ('TERRASSA Mixta', ('TERRASSA', 'MIXTA')),
    ('', ('', '')),
])
def test_lloc_i_modalitat(lloc, esperat):
    c = _one('05 oct. 2026', lloc=lloc)
    assert (c['municipi'], c['modalitat']) == esperat


def test_parse_arees():
    form = ('<form><input type="checkbox" name="field_fo_area[]" value="Idiomes"> Idiomes'
            '<input type="checkbox" name="field_fo_area[]" value="Informàtica">'
            '<input type="checkbox" name="field_fo_tipus[]" value="Altres"></form>')
    assert pim.parse_arees(form) == ['Idiomes', 'Informàtica']


def test_build_pagina_fins_pagina_buida_i_assigna_area(monkeypatch):
    monkeypatch.setattr(pim, 'PAUSA_S', 0)
    form = '<input name="field_fo_area[]" value="Idiomes">'
    pagines = {
        (None, 1): (_card('c1', 'Subvencionat', '28 set. - 26 oct. 2026', 30, 'BARCELONA Presencial')
                    + _card('c2', 'Altres', 'Dates a concretar', 12, '')),
        (None, 2): _card('c3', 'Bonificable', '29 set. 2026', 2, 'Aula Virtual Online'),
        ('Idiomes', 1): _card('c2', 'Altres', 'Dates a concretar', 12, ''),
    }

    def fake(session, page, area=None):
        return {'listcursos': pagines.get((area, page), ''),
                'formulari': form if (area is None and page == 1) else ''}

    monkeypatch.setattr(pim, '_get_page', fake)
    out = pim.build_pimec_cursos(session=object())
    per_id = {c['idCurs']: c for c in out}
    assert set(per_id) == {'PIMEC:c1', 'PIMEC:c2', 'PIMEC:c3'}
    assert per_id['PIMEC:c2']['area'] == 'Idiomes' and per_id['PIMEC:c1']['area'] == ''
    c1 = per_id['PIMEC:c1']
    assert c1['font'] == 'pimec' and c1['tipus'] == 'Subvencionat' and c1['estat'] == ''
    assert c1['titol'] == {'ca': 'Curs X', 'es': 'Curs X'}
    assert c1['centre']['nom'] == 'PIMEC Formació' and c1['centre']['municipi'] == 'BARCELONA'
    assert c1['fitxaUrl'].endswith('/formacio/c1')
    assert per_id['PIMEC:c3']['modalitat'] == 'TELEFORMACIÓ'


def test_build_no_duplica_cursos_repetits(monkeypatch):
    monkeypatch.setattr(pim, 'PAUSA_S', 0)
    dup = _card('c1', 'Subvencionat', '05 oct. 2026', 2, 'BARCELONA Presencial')
    pagines = {(None, 1): dup + dup}
    monkeypatch.setattr(pim, '_get_page',
                        lambda s, p, a=None: {'listcursos': pagines.get((a, p), ''), 'formulari': ''})
    assert len(pim.build_pimec_cursos(session=object())) == 1
```

Executar: ha de **fallar** (`ModuleNotFoundError: scrapers.pimec_scraper`).

### 1.2 Implementació

Crear `backend/scrapers/pimec_scraper.py`:

```python
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
```

Executar els tests de la fase: han de **passar**.

### 1.3 Commit

```
git add backend/scrapers/pimec_scraper.py backend/tests/test_pimec_scraper.py
git commit -m "feat(fpo): scraper de cursos de PIMEC Formació"
```

---

## Fase 2 — Scraper Foment

### 2.1 Tests (falla primer)

Crear `backend/tests/test_foment_scraper.py`:

```python
"""test_foment_scraper.py — Cursos de Foment Formació (Pla 062). Sense xarxa."""
import requests

from scrapers import foment_scraper as fo

_DETALL = ('<div class="detail-item"><div class="detail-item__texts">'
           '<label>{k}</label><span>{v}</span></div></div>')

HTML = (
    '<html><body><h1 class="hero-curso__title">ADGG0208: Ofimática</h1>'
    '<div class="sidebar-card__list">'
    '<div data-edition="edicion-presencial-09-03-26-9689">'
    '<div class="detail-item"><div class="detail-item__texts"><label>Centro</label>'
    '<a href="https://www.google.com/maps/search/?api=1&#038;query=41.3856074,2.1772219">'
    ' FOMENT FORMACIO </a></div></div>'
    + _DETALL.format(k='Comienzo', v='09/03/2026')
    + _DETALL.format(k='Final', v='29/04/2026')
    + _DETALL.format(k='Horario', v='Lunes a Viernes de 09:00 a 15:00')
    + _DETALL.format(k='Horas', v='190 horas')
    + '</div>'
    '<div data-edition="edicion-virtual-21-09-26-9999">'
    '<div class="detail-item"><div class="detail-item__texts"><label>Centro</label>'
    '<a href="https://www.google.com/maps/search/?api=1&#038;query=41.5,2.1">CENEF, SL</a></div></div>'
    + _DETALL.format(k='Comienzo', v='21/09/2026')
    + _DETALL.format(k='Final', v='30/11/2026')
    + _DETALL.format(k='Horas', v='30 horas')
    + '</div></div></body></html>'
)
URL = 'https://www.fomentformacio.com/formacion/adgd0208-mf0233-ofimatica-5'


def test_parse_course_una_fila_per_edicio():
    eds = fo.parse_course(HTML, URL)
    assert [e['idCurs'] for e in eds] == [
        'FOMENT:adgd0208-mf0233-ofimatica-5:edicion-presencial-09-03-26-9689',
        'FOMENT:adgd0208-mf0233-ofimatica-5:edicion-virtual-21-09-26-9999',
    ]
    e = eds[0]
    assert e['font'] == 'foment' and e['tipus'] == 'Altres' and e['estat'] == ''
    assert e['titol'] == {'ca': 'ADGG0208: Ofimática', 'es': 'ADGG0208: Ofimática'}
    assert e['certCodi'] == 'ADGG0208'
    assert (e['dataInici'], e['dataFi'], e['hores']) == ('2026-03-09', '2026-04-29', 190.0)
    assert e['modalitat'] == 'PRESENCIAL'
    assert e['horariText'] == 'Lunes a Viernes de 09:00 a 15:00'
    assert e['centre']['nom'] == 'FOMENT FORMACIO'
    assert (e['centre']['lat'], e['centre']['lon']) == (41.3856074, 2.1772219)
    assert e['fitxaUrl'] == URL


def test_edicio_virtual_sense_horari_ni_codi():
    e = fo.parse_course(HTML.replace('ADGG0208: ', ''), URL)[1]
    assert e['modalitat'] == 'VIDEOCONFERÈNCIA' and e['horariText'] == '' and e['certCodi'] == ''
    assert e['centre']['nom'] == 'CENEF, SL'


def test_pagina_sense_titol_no_dona_res():
    assert fo.parse_course('<html><body>404</body></html>', URL) == []


def test_list_course_urls_castella_sense_fragment_ni_repetits():
    xml = ('<urlset>'
           '<url><loc>https://www.fomentformacio.com/formacion</loc></url>'
           '<url><loc>https://www.fomentformacio.com/ca/formacio</loc></url>'
           '<url><loc>https://www.fomentformacio.com/formacion/curso-a</loc></url>'
           '<url><loc>https://www.fomentformacio.com/formacion/curso-a#edicion-virtual-15-09-26-8615</loc></url>'
           '<url><loc>https://www.fomentformacio.com/formacion/curso-b#edicion-presencial-14-09-26-9709</loc></url>'
           '<url><loc>https://www.fomentformacio.com/ca/formacio/curs-a</loc></url>'
           '</urlset>')
    assert fo.list_course_urls(xml) == ['https://www.fomentformacio.com/formacion/curso-a',
                                        'https://www.fomentformacio.com/formacion/curso-b']


class _Resp:
    def __init__(self, text='', exc=None):
        self.text, self._exc = text, exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc


class _Sess:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, timeout=30):
        r = self.pages[url]
        return r if isinstance(r, _Resp) else _Resp(r)


def test_build_salta_les_fitxes_que_fallen(monkeypatch):
    monkeypatch.setattr(fo, 'PAUSA_S', 0)
    sitemap = ('<loc>https://www.fomentformacio.com/formacion/ok</loc>'
               '<loc>https://www.fomentformacio.com/formacion/ok#edicion-virtual-1-1</loc>'
               '<loc>https://www.fomentformacio.com/formacion/ko</loc>')
    sess = _Sess({
        fo.SITEMAP_URL: sitemap,
        'https://www.fomentformacio.com/formacion/ok': HTML,
        'https://www.fomentformacio.com/formacion/ko': _Resp(exc=requests.HTTPError('500')),
    })
    out = fo.build_foment_cursos(session=sess)     # 'ok#edicion...' no es torna a baixar
    assert len(out) == 2 and all(c['idCurs'].startswith('FOMENT:ok:') for c in out)
```

Executar: ha de **fallar** (`ModuleNotFoundError`).

### 2.2 Implementació

Crear `backend/scrapers/foment_scraper.py`:

```python
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
```

Executar els tests de la fase: han de **passar**.

### 2.3 Commit

```
git add backend/scrapers/foment_scraper.py backend/tests/test_foment_scraper.py
git commit -m "feat(fpo): scraper de cursos de Foment Formació"
```

---

## Fase 3 — Snapshot, historial i pipeline

### 3.1 Tests (falla primer)

Crear `backend/tests/test_ext_refresh.py`:

```python
"""test_ext_refresh.py — Snapshot ext_cursos.json + pipeline (Pla 062). Sense xarxa."""
import json
from unittest.mock import patch

from scrapers import ext_cursos, pipeline


def _c(font, n):
    return {'idCurs': f'{font.upper()}:{n}', 'font': font}


def _ids(tmp_path):
    return sorted(c['idCurs'] for c in json.loads((tmp_path / 'ext_cursos.json').read_text()))


def _hist(tmp_path):
    return json.loads((tmp_path / 'soc_refresh_history.json').read_text())


def test_is_plausible():
    assert ext_cursos.is_plausible([], [_c('pimec', 'a')]) is True
    assert ext_cursos.is_plausible([], []) is False
    assert ext_cursos.is_plausible([1, 2, 3, 4], [1, 2]) is True      # exactament la meitat
    assert ext_cursos.is_plausible([1, 2, 3, 4], [1]) is False


def test_diff_entry_conserva_font_soc_per_defecte():
    assert pipeline._soc_diff_entry([], [], ok=True)['font'] == 'soc'
    assert pipeline._soc_diff_entry([], [], ok=True, font='pimec')['font'] == 'pimec'


def test_refresh_ok_escriu_les_dues_fonts(tmp_path):
    with patch('scrapers.pimec_scraper.build_pimec_cursos',
               return_value=[_c('pimec', 'a'), _c('pimec', 'b')]), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[_c('foment', 'x')]):
        res = pipeline.refresh_ext_cursos(str(tmp_path))
    assert res == {'pimec': 2, 'foment': 1}
    assert _ids(tmp_path) == ['FOMENT:x', 'PIMEC:a', 'PIMEC:b']
    assert {(h['font'], h['ok'], h['n_cursos']) for h in _hist(tmp_path)} == {
        ('pimec', True, 2), ('foment', True, 1)}


def test_font_que_falla_conserva_l_anterior_i_avisa(tmp_path):
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(
        [_c('pimec', 'a'), _c('pimec', 'b'), _c('foment', 'x')]))
    with patch('scrapers.pimec_scraper.build_pimec_cursos', side_effect=RuntimeError('boom')), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[_c('foment', 'y')]), \
         patch('scrapers.pipeline._notify_admin_soc_failure') as notify:
        pipeline.refresh_ext_cursos(str(tmp_path))
    assert _ids(tmp_path) == ['FOMENT:y', 'PIMEC:a', 'PIMEC:b']
    assert notify.call_count == 1 and notify.call_args.kwargs['source'] == 'PIMEC'
    assert any(h['font'] == 'pimec' and h['ok'] is False and 'boom' in h['error']
               for h in _hist(tmp_path))


def test_no_sobreescriu_si_baixa_a_menys_de_la_meitat(tmp_path):
    prev = [_c('pimec', str(i)) for i in range(4)]
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(prev))
    with patch('scrapers.pimec_scraper.build_pimec_cursos', return_value=[_c('pimec', '0')]), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[]), \
         patch('scrapers.pipeline._notify_admin_soc_failure') as notify:
        pipeline.refresh_ext_cursos(str(tmp_path))
    assert len(_ids(tmp_path)) == 4                 # PIMEC intacte; Foment buit sense prèvia
    assert notify.call_count == 2                   # PIMEC (caiguda) + Foment (0 cursos)


def test_avis_admin_usa_font_i_fitxer_propis(tmp_path):
    with patch('email_service.send_email') as send:
        pipeline._notify_admin_soc_failure(
            str(tmp_path), RuntimeError('x'), source='PIMEC', stamp_name='last_pimec_alert.json')
    assert 'PIMEC' in send.call_args.args[1]
    assert (tmp_path / 'last_pimec_alert.json').exists()
    assert not (tmp_path / 'last_soc_alert.json').exists()
```

Executar: ha de **fallar** (`ModuleNotFoundError: scrapers.ext_cursos` / `AttributeError`).

### 3.2 Implementació

**a)** Crear `backend/scrapers/ext_cursos.py`:

```python
"""
ext_cursos.py — Snapshot dels cursos FPO externs (PIMEC, Foment) (Pla 062).

`data/ext_cursos.json` és una llista; cada element és una edició, amb el mateix
format que `soc_cursos.json` més:
  font ('pimec'|'foment'), tipus, area (str de la font), certCodi (str),
  fitxaUrl (str), horariText (str, només Foment).
`estat` es guarda sempre buit: `finalitzat` es deriva en llegir (Pla 063).
"""
import json
import os
import tempfile

EXT_FILE = 'ext_cursos.json'


def is_plausible(prev_font: list, fresh: list) -> bool:
    """Una font es dóna per bona si retorna algun curs i no menys de la meitat dels anteriors."""
    return bool(fresh) and len(fresh) >= len(prev_font) / 2


def write_ext(cursos: list, data_dir: str) -> None:
    os.makedirs(data_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json',
                                     dir=data_dir, delete=False) as tmp:
        json.dump(cursos, tmp, ensure_ascii=False, indent=1)
        tmp_path = tmp.name
    os.replace(tmp_path, os.path.join(data_dir, EXT_FILE))
```

**b)** `backend/scrapers/pipeline.py`. Substituir `_soc_diff_entry` (afegir `font`):

```python
def _soc_diff_entry(prev_cursos: list, curr_cursos: list, *, ok: bool,
                    error: str | None = None, font: str = 'soc') -> dict:
    prev_ids = {c.get('idCurs') for c in (prev_cursos or []) if isinstance(c, dict)}
    curr_ids = {c.get('idCurs') for c in (curr_cursos or []) if isinstance(c, dict)}
    return {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'font': font,
        'ok': ok,
        'error': error,
        'n_cursos': len(curr_cursos or []),
        'n_afegits': len(curr_ids - prev_ids) if ok else 0,
        'n_retirats': len(prev_ids - curr_ids) if ok else 0,
    }
```

Canviar la signatura i el cos de `_notify_admin_soc_failure` (els valors per defecte
mantenen el comportament del SOC):

```python
def _notify_admin_soc_failure(data_dir: str, exc: Exception, *, source: str = 'SOC',
                              stamp_name: str = 'last_soc_alert.json') -> None:
    """Avisa l'admin per email que el snapshot FPO ha fallat (rate-limit 24 h per font)."""
    stamp_path = os.path.join(data_dir, stamp_name)
```
i dins del `send_email`: assumpte `f'Snapshot FPO ({source}) ha fallat'` i cos
`f"El snapshot de cursos FPO ({source}) ha fallat.\n\n{exc!r}\n\n"` (la resta igual).

Afegir, just després de `_notify_admin_soc_failure`:

```python
def refresh_ext_cursos(data_dir: str) -> dict:
    """PIMEC + Foment -> ext_cursos.json (Pla 062).

    Cada font és independent i no fatal: si falla o cau a menys de la meitat, es
    conserva el snapshot anterior d'aquesta font, s'anota l'error a l'historial i
    s'avisa l'admin. Retorna {font: n_cursos del snapshot resultant}.
    """
    from scrapers import ext_cursos, foment_scraper, pimec_scraper

    prev = _read_json_or(os.path.join(data_dir, ext_cursos.EXT_FILE), [])
    if not isinstance(prev, list):
        prev = []
    cursos = list(prev)
    fonts = (('pimec', pimec_scraper.build_pimec_cursos),
             ('foment', foment_scraper.build_foment_cursos))
    for font, build in fonts:
        prev_font = [c for c in prev if c.get('font') == font]
        try:
            fresh = build()
            if not ext_cursos.is_plausible(prev_font, fresh):
                raise ValueError(f'{font}: {len(fresh)} cursos (abans {len(prev_font)}); '
                                 'es conserva el snapshot anterior')
            cursos = [c for c in cursos if c.get('font') != font] + fresh
            _soc_history_append(data_dir, _soc_diff_entry(prev_font, fresh, ok=True, font=font))
        except Exception as exc:
            logger.warning("pipeline: refresc de %s ha fallat (no fatal): %s", font, exc)
            _soc_history_append(data_dir, _soc_diff_entry([], [], ok=False, error=repr(exc), font=font))
            _notify_admin_soc_failure(data_dir, exc, source=font.upper(),
                                      stamp_name=f'last_{font}_alert.json')
    ext_cursos.write_ext(cursos, data_dir)
    return {f: sum(1 for c in cursos if c.get('font') == f) for f, _ in fonts}
```

Afegir a `run()`, just **després** del bloc `# --- Pla 059: cursos FPO del SOC ...`
i abans de `families = sorted(...)`:

```python
    # --- Pla 062: cursos FPO de PIMEC i Foment (no fatal; cada font és independent) ---
    _report('Cursos FPO (PIMEC i Foment)')
    try:
        refresh_ext_cursos(os.path.dirname(DATA_PATH))
    except Exception as exc:
        logger.warning("pipeline: refresh_ext_cursos ha fallat (no fatal): %s", exc)
```

Executar els tests de la fase: han de **passar**. Després la regressió estàndard i
`python3 -m pytest -q tests/test_admin_fpo.py` (no s'ha de trencar: els avisos del SOC
mantenen la signatura per defecte).

### 3.3 Commit

```
git add backend/scrapers/ext_cursos.py backend/scrapers/pipeline.py backend/tests/test_ext_refresh.py
git commit -m "feat(fpo): snapshot ext_cursos.json i bloc no fatal al pipeline"
```

---

## Fase 4 — Verificació real (xarxa)

Des de `fp-cercador/backend`, **sense escriure al repo** (usa un directori temporal):

```
python3 - <<'EOF'
import collections, tempfile
from scrapers import pipeline
d = tempfile.mkdtemp()
print(pipeline.refresh_ext_cursos(d))
import json
c = json.load(open(d + '/ext_cursos.json'))
print(collections.Counter(x['font'] for x in c))
print(collections.Counter(x['tipus'] for x in c if x['font'] == 'pimec'))
print('sense dates:', sum(1 for x in c if not x['dataInici']))
print('amb àrea (pimec):', sum(1 for x in c if x['font'] == 'pimec' and x['area']))
print(json.load(open(d + '/soc_refresh_history.json')))
EOF
```

**Esperat** (2026-09-25; pot variar poc): `pimec` ≈ 417, `foment` ≈ 150; tipus PIMEC
≈ 204 Subvencionat / 163 Altres / 38 Diàleg Social / 12 Bonificable; ≈ 160 sense dates;
≈ 320 PIMEC amb àrea; l'historial té 2 entrades `ok: true`. Tarda ~2–3 min. Si un
número s'allunya molt (p. ex. `pimec` < 300), **aturar-se i informar**: el parser o el
paginat han canviat.

## Fora d'abast d'aquest pla

- Hook d'admin (`/api/admin/refresh-fpo`) i memòria cau → Pla 063.
- Endpoints, famílies i estat `finalitzat` → Pla 063. UI → Pla 064.
- No es toca `soc_scraper.py` ni el mode Grados.
