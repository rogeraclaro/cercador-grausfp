# Pla 063 — FPO extern: especialitats sintètiques, estat "Finalitzat", endpoints i favorits

Origen: `docs/superpowers/specs/2026-09-25-fpo-pimec-foment-design.md` (§4, §6).
Depèn de: 062 DONE (`data/ext_cursos.json` i `scrapers/pipeline.refresh_ext_cursos`).
Segon dels 3 plans. Sessió neta. **TDD estricte**. **No cal decidir res** (excepte el
mapa àrea→família de la Fase 1, que és una proposta que l'usuari pot ajustar).

## Com executar els tests

Des de `fp-cercador/backend`:
`python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
(~3 s; 2 fallos coneguts a `test_db.py`, no relacionats). Mai encadenar `git stash pop`.

## Context (vist al codi)

- `app.py` construeix les files FPO a `_soc_espec_index()` (llista + `cursos_by_espec`) i
  les serveix a `/api/fpo/especialitats` i `/api/fpo/especialitat/<path:codi>`.
- Favorits: `fpo_favorites.especialitat_codi` i `fpo_favorite_courses.curs_id` són `TEXT`
  sense clau forana i el `POST` no valida el codi contra el catàleg → **cap migració**.
  Però el `GET /api/fpo/favorites` enriqueix amb `_fpo_espec_by_codi` / `_fpo_curs_by_id`
  (només SOC) i `_fpo_fav_course_public` usa `_soc_fitxa_url`: cal ampliar-los.
- La ruta `DELETE /api/fpo/favorites/<codi>` no admet `/` al codi → el codi sintètic
  no en pot portar (`_slug` ho garanteix). El `:` sí és vàlid.
- Els tests d'`app` aïllen els `soc_*.json` amb `monkeypatch`; cal fer el mateix amb
  `ext_cursos.json` (fixture `autouse` a `conftest.py`) perquè cap test llegeixi el
  `data/ext_cursos.json` real.

## Decisions de disseny

1. **Codi sintètic** `PIMEC:<slug-del-títol>` / `FOMENT:<slug-del-títol>` (títol en
   minúscules, sense accents, `[a-z0-9-]`, màx. 80). Les edicions d'un mateix títol
   d'una mateixa font formen una fila.
2. **Família** (per no barrejar dos vocabularis): PIMEC via `PIMEC_AREA_FAMILIA`;
   Foment via les 3 primeres lletres de `certCodi`. Si el codi no és una família
   existent al SOC, o no hi ha dades → **`FCO`** ("Formació complementària", família
   real del SOC). Per a una fila, s'agafa la primera família no-`FCO` de les seves
   edicions. El nom de la família surt dels `soc_especs.json`.
3. **Àrea** de la fila: primera àrea no buida (text de PIMEC), amb `codi: ''` (així no
   entra al desplegable d'àrees del SOC però es mostra a la columna).
4. **`finalitzat`** = `dataFi` anterior a avui (comparació de cadenes ISO). Es calcula
   **en llegir** amb `_fpo_today()` i la memòria cau inclou el dia a la clau.
5. **Ordre d'edicions** dins la fila: actives amb data (per `dataInici`) → sense data →
   finalitzades.
6. **Files SOC** passen a portar `font: 'soc'` i `tipus: ['Subvencionat']`
   (**suposició** meva: l'oferta del SOC és formació per a l'ocupació finançada; si
   l'usuari no ho vol, treure `tipus` de les files SOC a `_fpo_llista`).
7. `nCursos` d'una fila externa = edicions **no finalitzades**.
8. `/api/fpo/by-cert` no es toca (fora d'abast).

## Fitxers

- Crear `backend/fpo_ext.py`.
- Modificar `backend/app.py`, `backend/tests/conftest.py`,
  `backend/tests/test_admin_fpo.py`, `backend/tests/test_fpo_favorites_api.py`.
- Tests nous: `backend/tests/test_fpo_ext.py`, `backend/tests/test_fpo_ext_api.py`.

---

## Fase 1 — Mòdul pur `fpo_ext.py`

### 1.1 Tests (falla primer)

Crear `backend/tests/test_fpo_ext.py`:

```python
"""test_fpo_ext.py — Especialitats sintètiques dels cursos externs (Pla 063)."""
import fpo_ext as fx

TODAY = '2026-09-25'
FAMS = {c: {'ca': c, 'es': c} for c in ('IFC', 'ADG', 'CTR', 'COM', 'FCO')}


def _c(font, n, titol, **kw):
    base = {
        'idCurs': f'{font.upper()}:{n}', 'font': font, 'tipus': 'Subvencionat',
        'titol': {'ca': titol, 'es': titol}, 'area': '', 'certCodi': '', 'hores': 30.0,
        'modalitat': 'PRESENCIAL', 'estat': '', 'dataInici': '2026-10-01',
        'dataFi': '2026-12-01', 'municipi': 'BARCELONA', 'centre': {'nom': 'X'},
        'fitxaUrl': f'https://x/{n}',
    }
    base.update(kw)
    return base


def test_is_ext_codi():
    assert fx.is_ext_codi('PIMEC:abc') and fx.is_ext_codi('FOMENT:a:b')
    assert not fx.is_ext_codi('IFCD0112') and not fx.is_ext_codi(None)


def test_codi_especialitat_es_un_slug_sense_barres():
    c = _c('pimec', 1, 'Programació neurolingüística / Nivell I!')
    assert fx.codi_especialitat(c) == 'PIMEC:programacio-neurolinguistica-nivell-i'
    assert fx.codi_especialitat(_c('foment', 2, '')) == 'FOMENT:curs'
    assert '/' not in fx.codi_especialitat(_c('pimec', 3, 'a/b'))


def test_estat():
    assert fx.estat(_c('pimec', 1, 'x', dataFi='2026-09-24'), TODAY) == 'finalitzat'
    assert fx.estat(_c('pimec', 1, 'x', dataFi='2026-09-25'), TODAY) == ''   # avui encara compta
    assert fx.estat(_c('pimec', 1, 'x', dataFi=None), TODAY) == ''


def test_familia_pimec_per_area_sense_distingir_majuscules():
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Informàtica'), FAMS) == 'IFC'
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Docència I formació'), {'SSC': {}, 'FCO': {}}) == 'SSC'
    assert fx.familia_codi(_c('pimec', 1, 'x', area='docència i formació'), {'SSC': {}, 'FCO': {}}) == 'SSC'


def test_familia_per_defecte_fco():
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Inventada'), FAMS) == 'FCO'
    assert fx.familia_codi(_c('pimec', 1, 'x', area=''), FAMS) == 'FCO'
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Informàtica'), {'FCO': {}}) == 'FCO'  # IFC no existeix


def test_familia_foment_pel_prefix_del_certificat():
    assert fx.familia_codi(_c('foment', 1, 'x', certCodi='ADGG0208'), FAMS) == 'ADG'
    assert fx.familia_codi(_c('foment', 1, 'x', certCodi='ZZZZ0001'), FAMS) == 'FCO'
    assert fx.familia_codi(_c('foment', 1, 'x'), FAMS) == 'FCO'


def test_build_index_agrupa_edicions_i_ordena():
    cursos = [
        _c('pimec', '1', 'Mindfulness', dataInici='2026-06-01', dataFi='2026-07-01'),   # finalitzada
        _c('pimec', '2', 'Mindfulness', dataInici=None, dataFi=None, tipus='Altres', modalitat=''),
        _c('pimec', '3', 'Mindfulness', dataInici='2026-11-01', dataFi='2026-12-01'),
        _c('pimec', '4', 'Mindfulness', dataInici='2026-10-05', dataFi='2026-10-30',
           area='Idiomes', modalitat='TELEFORMACIÓ'),
        _c('foment', '5', 'Mindfulness'),
        _c('altra', '6', 'Ignorat'),                                                    # font desconeguda
    ]
    idx = fx.build_index(cursos, FAMS, TODAY)
    assert [e['codi'] for e in idx['list']] == ['FOMENT:mindfulness', 'PIMEC:mindfulness']
    e = idx['list'][1]
    assert [c['idCurs'] for c in idx['cursos_by_codi']['PIMEC:mindfulness']] == [
        'PIMEC:4', 'PIMEC:3', 'PIMEC:2', 'PIMEC:1']
    assert e['font'] == 'pimec' and e['titol'] == {'ca': 'Mindfulness', 'es': 'Mindfulness'}
    assert e['familia'] == {'codi': 'CTR', 'desc': {'ca': 'CTR', 'es': 'CTR'}}   # l'edició 4 té àrea Idiomes
    assert e['area']['desc']['ca'] == 'Idiomes' and e['area']['codi'] == ''
    assert e['nCursos'] == 3                       # 4, 3 i 2 no són finalitzades
    assert e['estats'] == ['finalitzat']
    assert e['tipus'] == ['Altres', 'Subvencionat']
    assert e['modalitats'] == ['PRESENCIAL', 'TELEFORMACIÓ']
    assert e['municipis'] == ['BARCELONA'] and e['comarques'] == []
    assert e['nivell'] == 0 and e['hores'] == 30.0 and e['esCertProf'] is False
    assert idx['list'][0]['familia']['codi'] == 'FCO'


def test_familia_de_la_fila_es_la_primera_no_fco():
    cursos = [_c('pimec', '1', 'Anglès'), _c('pimec', '2', 'Anglès', area='Idiomes')]
    e = fx.build_index(cursos, FAMS, TODAY)['list'][0]
    assert e['familia']['codi'] == 'CTR'


def test_es_cert_prof_si_alguna_edicio_te_codi():
    e = fx.build_index([_c('foment', '1', 'ADGG0208: Ofimática', certCodi='ADGG0208')],
                       FAMS, TODAY)['list'][0]
    assert e['esCertProf'] is True and e['familia']['codi'] == 'ADG'


def test_curs_public():
    p = fx.curs_public(_c('foment', '9', 'x', horariText='Lunes a Viernes', dataFi='2026-01-01'), TODAY)
    assert p['idCurs'] == 'FOMENT:9' and p['estat'] == 'finalitzat'
    assert p['font'] == 'foment' and p['tipus'] == 'Subvencionat' and p['hores'] == 30.0
    assert p['horariText'] == 'Lunes a Viernes' and p['fitxaUrl'] == 'https://x/9'
    assert set(p) >= {'titol', 'centre', 'dataInici', 'dataFi', 'modalitat'}
```

Executar: ha de **fallar** (`ModuleNotFoundError: fpo_ext`).

### 1.2 Implementació

Crear `backend/fpo_ext.py`:

```python
"""
fpo_ext.py — Cursos FPO externs (PIMEC, Foment) com a especialitats sintètiques (Pla 063).

Funcions pures: sense E/S ni estat global. `app.py` hi passa les dades, les famílies
del SOC i la data d'avui (ISO). Vegeu `scrapers/ext_cursos.py` per al format de curs.
"""
import re
import unicodedata

FONTS = ('pimec', 'foment')
CODI_PREFIXOS = tuple(f'{f.upper()}:' for f in FONTS)
FALLBACK_FAMILIA = 'FCO'   # "Formació complementària": família real del SOC

# Àrea de PIMEC -> codi de família del SOC (claus en minúscules). Proposta revisable.
PIMEC_AREA_FAMILIA = {
    'disseny gràfic': 'ARG',
    'docència i formació': 'SSC',
    'economia i finances': 'ADG',
    'gestió empresarial': 'ADG',
    'habilitats directives': 'CTR',
    'habilitats personals': 'CTR',
    'hostaleria i turisme': 'HOT',
    'idiomes': 'CTR',
    'informàtica': 'IFC',
    'logística i transport': 'TMV',
    'manteniment i producció': 'IMA',
    'marketing digital': 'COM',
    'prevenció de riscos laborals': 'SEA',
    'recursos humans i laboral': 'ADG',
    'sectorial': 'FCO',
    'tecnologia i innovació': 'IFC',
    'vendes i marketing': 'COM',
}


def is_ext_codi(codi) -> bool:
    """True per a un codi d'especialitat (`PIMEC:...`) o un idCurs (`FOMENT:...`) extern."""
    return isinstance(codi, str) and codi.startswith(CODI_PREFIXOS)


def _slug(text) -> str:
    s = unicodedata.normalize('NFKD', text or '')
    s = ''.join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:80].strip('-') or 'curs'


def codi_especialitat(curs: dict) -> str:
    return f"{curs['font'].upper()}:{_slug((curs.get('titol') or {}).get('ca'))}"


def estat(curs: dict, today_iso: str) -> str:
    """'finalitzat' si la data de fi és anterior a avui; si no, ''."""
    fi = curs.get('dataFi')
    return 'finalitzat' if fi and fi < today_iso else ''


def familia_codi(curs: dict, families: dict) -> str:
    if curs.get('font') == 'pimec':
        codi = PIMEC_AREA_FAMILIA.get((curs.get('area') or '').strip().lower(), FALLBACK_FAMILIA)
    else:
        codi = (curs.get('certCodi') or '')[:3]
    return codi if codi in families else FALLBACK_FAMILIA


def _familia(codi: str, families: dict) -> dict:
    return {'codi': codi, 'desc': families.get(codi) or {'ca': codi, 'es': codi}}


def _rank(curs: dict, today_iso: str) -> int:
    if estat(curs, today_iso):
        return 2
    return 0 if curs.get('dataInici') else 1


def curs_public(curs: dict, today_iso: str) -> dict:
    return {
        'idCurs': curs.get('idCurs', ''),
        'titol': curs.get('titol', {'ca': '', 'es': ''}),
        'centre': curs.get('centre', {}),
        'dataInici': curs.get('dataInici'),
        'dataFi': curs.get('dataFi'),
        'estat': estat(curs, today_iso),
        'modalitat': curs.get('modalitat', ''),
        'fitxaUrl': curs.get('fitxaUrl', ''),
        'font': curs.get('font', ''),
        'tipus': curs.get('tipus', ''),
        'hores': curs.get('hores', 0.0),
        'horariText': curs.get('horariText', ''),
    }


def build_index(cursos: list, families: dict, today_iso: str) -> dict:
    """{'list': [fila, ...], 'cursos_by_codi': {codi: [edicions ordenades]}}.

    `families` és {codi_familia: {'ca':.., 'es':..}} (dels soc_especs.json).
    """
    grups: dict = {}
    for c in cursos:
        if c.get('font') in FONTS:
            grups.setdefault(codi_especialitat(c), []).append(c)

    llista, per_codi = [], {}
    for codi, eds in grups.items():
        eds.sort(key=lambda c: (_rank(c, today_iso), c.get('dataInici') or '', c.get('idCurs') or ''))
        per_codi[codi] = eds
        fam = next((f for f in (familia_codi(c, families) for c in eds)
                    if f != FALLBACK_FAMILIA), FALLBACK_FAMILIA)
        area = next((c['area'] for c in eds if c.get('area')), '')
        llista.append({
            'codi': codi,
            'titol': eds[0].get('titol', {'ca': '', 'es': ''}),
            'familia': _familia(fam, families),
            'area': {'codi': '', 'desc': {'ca': area, 'es': area}},
            'nivell': 0,
            'hores': max((c.get('hores') or 0.0 for c in eds), default=0.0),
            'esCertProf': any(c.get('certCodi') for c in eds),
            'rd': None,
            'programaUrl': '',
            'nCursos': sum(1 for c in eds if not estat(c, today_iso)),
            'comarques': [],
            'municipis': sorted({c['municipi'] for c in eds if c.get('municipi')}),
            'estats': sorted({e for e in (estat(c, today_iso) for c in eds) if e}),
            'modalitats': sorted({c['modalitat'] for c in eds if c.get('modalitat')}),
            'font': eds[0]['font'],
            'tipus': sorted({c['tipus'] for c in eds if c.get('tipus')}),
        })
    llista.sort(key=lambda x: ((x['titol'].get('ca') or x['codi']).lower(), x['codi']))
    return {'list': llista, 'cursos_by_codi': per_codi}
```

Executar `tests/test_fpo_ext.py`: ha de **passar**.

### 1.3 Commit

```
git add backend/fpo_ext.py backend/tests/test_fpo_ext.py
git commit -m "feat(fpo): especialitats sintètiques dels cursos externs (fpo_ext)"
```

---

## Fase 2 — Endpoints i memòria cau a `app.py`

### 2.1 Tests (falla primer)

Crear `backend/tests/test_fpo_ext_api.py`:

```python
"""test_fpo_ext_api.py — /api/fpo/* amb cursos externs (Pla 063)."""
import json
import os

import pytest

import app as app_module

TODAY = '2026-09-25'
FAM = {'IFC': {'ca': 'INFORMÀTICA I COMUNICACIONS', 'es': 'INFORMÁTICA Y COMUNICACIONES'},
       'ADG': {'ca': 'ADMINISTRACIÓ I GESTIÓ', 'es': 'ADMINISTRACIÓN Y GESTIÓN'}}


def _espec(codi, fam):
    return {'codi': codi, 'titol': {'ca': f'Esp {codi}', 'es': f'Esp {codi}'},
            'familia': {'codi': fam, 'desc': FAM[fam]}, 'area': {'codi': 'X', 'desc': {'ca': 'X', 'es': 'X'}},
            'nivell': 3, 'hores': 100.0, 'preu': 0.0, 'esCertProf': False, 'rd': None,
            'programaUrl': '', 'moduls': [], 'cursIds': [], 'destacada': False}


def _soc_curs(idc, esp):
    return {'idCurs': idc, 'titol': {'ca': idc, 'es': idc},
            'especialitat': {'codi': esp, 'desc': {'ca': esp, 'es': esp}}, 'estat': 'inscripcio',
            'modalitat': 'PRESENCIAL', 'dataInici': '2026-10-01', 'dataFi': '2027-01-01',
            'comarca': 'BARCELONÈS', 'municipi': 'BARCELONA', 'centre': {'nom': 'C', 'idCentre': '1'},
            'programaUrl': ''}


def _ext(font, n, titol, **kw):
    base = {'idCurs': f'{font.upper()}:{n}', 'font': font, 'tipus': 'Subvencionat',
            'titol': {'ca': titol, 'es': titol}, 'area': '', 'certCodi': '', 'hores': 30.0,
            'modalitat': 'PRESENCIAL', 'estat': '', 'dataInici': '2026-10-05', 'dataFi': '2026-11-01',
            'comarca': '', 'municipi': 'BARCELONA', 'provincia': '',
            'centre': {'nom': 'PIMEC Formació', 'idCentre': ''},
            'fitxaUrl': f'https://pimecformacio.org/x/{n}'}
    base.update(kw)
    return base


EXT = [
    _ext('pimec', 'p1', 'Programació neurolingüística', area='Informàtica'),
    _ext('pimec', 'p2', 'Programació neurolingüística', area='Informàtica',
         dataInici='2026-06-01', dataFi='2026-07-01'),                      # finalitzada
    _ext('foment', 'f1', 'ADGG0208: Ofimática', certCodi='ADGG0208', tipus='Altres',
         fitxaUrl='https://www.fomentformacio.com/formacion/f1'),
]


@pytest.fixture
def fpo_ext_data(tmp_path, monkeypatch):
    (tmp_path / 'soc_especs.json').write_text(
        json.dumps([_espec('IFCD0112', 'IFC'), _espec('ADGG0408', 'ADG')]), encoding='utf-8')
    (tmp_path / 'soc_cursos.json').write_text(
        json.dumps([_soc_curs('111', 'IFCD0112'), _soc_curs('201', 'ADGG0408')]), encoding='utf-8')
    (tmp_path / 'soc_centres.json').write_text('[]', encoding='utf-8')
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(EXT), encoding='utf-8')
    for nom, fitxer in (('SOC_ESPECS_PATH', 'soc_especs.json'), ('SOC_CURSOS_PATH', 'soc_cursos.json'),
                        ('SOC_CENTRES_PATH', 'soc_centres.json'), ('EXT_CURSOS_PATH', 'ext_cursos.json')):
        monkeypatch.setattr(app_module, nom, str(tmp_path / fitxer))
    for nom in ('_soc_cursos_cache', '_soc_especs_cache', '_soc_centres_cache', '_ext_cursos_cache'):
        monkeypatch.setattr(app_module, nom, {'mtime': None, 'index': None})
    for nom in ('_soc_espec_index_cache', '_ext_index_cache'):
        monkeypatch.setattr(app_module, nom, {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_fpo_today', lambda: TODAY)
    return tmp_path


@pytest.fixture
def client(fpo_ext_data):
    os.environ['ADMIN_TOKEN'] = 'test-token'
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _rows(client):
    return {e['codi']: e for e in client.get('/api/fpo/especialitats').get_json()['especialitats']}


def test_llista_barreja_soc_i_externs(client):
    rows = _rows(client)
    assert set(rows) == {'IFCD0112', 'ADGG0408',
                         'PIMEC:programacio-neurolinguistica', 'FOMENT:adgg0208-ofimatica'}
    assert rows['IFCD0112']['font'] == 'soc' and rows['IFCD0112']['tipus'] == ['Subvencionat']
    p = rows['PIMEC:programacio-neurolinguistica']
    assert p['font'] == 'pimec' and p['tipus'] == ['Subvencionat']
    assert p['familia'] == {'codi': 'IFC', 'desc': FAM['IFC']}
    assert p['nCursos'] == 1 and p['estats'] == ['finalitzat']
    f = rows['FOMENT:adgg0208-ofimatica']
    assert f['font'] == 'foment' and f['familia']['codi'] == 'ADG' and f['esCertProf'] is True


def test_llista_ordenada_per_titol(client):
    titols = [(e['titol']['ca']).lower()
              for e in client.get('/api/fpo/especialitats').get_json()['especialitats']]
    assert titols == sorted(titols)


def test_sense_fitxer_extern_nomes_hi_ha_soc(client, fpo_ext_data):
    os.remove(fpo_ext_data / 'ext_cursos.json')
    assert set(_rows(client)) == {'IFCD0112', 'ADGG0408'}


def test_nomes_externs_si_falta_el_soc(client, fpo_ext_data):
    os.remove(fpo_ext_data / 'soc_especs.json')
    rows = _rows(client)
    assert set(rows) == {'PIMEC:programacio-neurolinguistica', 'FOMENT:adgg0208-ofimatica'}
    # sense famílies del SOC, tot cau a FCO (amb el codi com a nom)
    assert {r['familia']['codi'] for r in rows.values()} == {'FCO'}


def test_detall_extern_edicions_ordenades(client):
    d = client.get('/api/fpo/especialitat/PIMEC:programacio-neurolinguistica').get_json()
    assert d['descripcio']['ca'] == 'Programació neurolingüística'
    assert d['moduls'] == [] and d['programaUrl'] == ''
    assert [c['idCurs'] for c in d['cursos']] == ['PIMEC:p1', 'PIMEC:p2']   # activa abans que finalitzada
    assert [c['estat'] for c in d['cursos']] == ['', 'finalitzat']
    c = d['cursos'][0]
    assert c['font'] == 'pimec' and c['fitxaUrl'].startswith('https://pimecformacio.org')


def test_detall_extern_desconegut_404(client):
    r = client.get('/api/fpo/especialitat/PIMEC:no-existeix')
    assert r.status_code == 404 and r.get_json() == {}


def test_detall_soc_continua_igual(client):
    d = client.get('/api/fpo/especialitat/IFCD0112').get_json()
    assert [c['idCurs'] for c in d['cursos']] == ['111']


def test_finalitzat_es_recalcula_amb_el_dia(client, monkeypatch):
    monkeypatch.setattr(app_module, '_fpo_today', lambda: '2026-11-15')
    p = _rows(client)['PIMEC:programacio-neurolinguistica']
    assert p['nCursos'] == 0 and p['estats'] == ['finalitzat']
```

Executar: ha de **fallar** (`AttributeError: ... EXT_CURSOS_PATH`).

### 2.2 Implementació (a `backend/app.py`)

**a)** Imports. A `app.py` hi ha 6 línies `from datetime import datetime, timezone`;
**només s'ha de canviar la de nivell de mòdul (línia ~45, al bloc d'imports de dalt de
tot)** per `from datetime import date, datetime, timezone`; les de dins de funcions
es deixen intactes. Afegir `import fpo_ext` just després de `import cd_lomloe`.

**b)** Constants, després de `SOC_CENTRES_PATH = ...`:

```python
EXT_CURSOS_PATH = os.path.join(_DATA_DIR, "ext_cursos.json")   # Pla 062: cursos FPO de PIMEC i Foment
```

**c)** Dins la secció "Pla 059 — FPO (SOC Catalunya)", després de `_soc_espec_index_cache`:

```python
_ext_cursos_cache: dict = {"mtime": None, "index": None}
_ext_index_cache: dict = {"key": None, "data": None}
```

**d)** Després de `_get_soc_centres()`:

```python
def _get_ext_cursos() -> list:
    return _read_soc_list(EXT_CURSOS_PATH, _ext_cursos_cache)


def _fpo_today() -> str:
    """Data d'avui (ISO). Funció a part perquè els tests la puguin fixar (Pla 063)."""
    return date.today().isoformat()


def _fpo_families() -> dict:
    """{codi_familia: {'ca':.., 'es':..}} a partir dels soc_especs.json."""
    out: dict = {}
    for e in _get_soc_especs():
        f = e.get('familia') or {}
        if f.get('codi') and f['codi'] not in out:
            out[f['codi']] = f.get('desc') or {'ca': f['codi'], 'es': f['codi']}
    return out


def _ext_index() -> dict:
    """Índex dels cursos externs (fpo_ext.build_index). Cache per mtimes + dia (l'estat
    'finalitzat' depèn de la data)."""
    def _mt(path):
        return os.path.getmtime(path) if os.path.exists(path) else None

    key = (_mt(EXT_CURSOS_PATH), _mt(SOC_ESPECS_PATH), _fpo_today())
    if _ext_index_cache["key"] == key and _ext_index_cache["data"] is not None:
        return _ext_index_cache["data"]
    data = fpo_ext.build_index(_get_ext_cursos(), _fpo_families(), _fpo_today())
    _ext_index_cache.update(key=key, data=data)
    return data


def _fpo_llista() -> list:
    """Especialitats SOC (font='soc') + externes, ordenades per títol."""
    soc = [{**e, 'font': 'soc', 'tipus': ['Subvencionat']} for e in _soc_espec_index()['list']]
    llista = soc + _ext_index()['list']
    llista.sort(key=lambda x: ((x['titol'].get('ca') or x['codi']).lower(), x['codi']))
    return llista
```

**e)** `api_fpo_especialitats`: canviar `resp = {'especialitats': _soc_espec_index()['list']}`
per `resp = {'especialitats': _fpo_llista()}`.

**f)** `api_fpo_especialitat`: afegir **al principi** del cos (abans de `idx = _soc_espec_index()`):

```python
    if fpo_ext.is_ext_codi(codi):
        cursos = _ext_index()['cursos_by_codi'].get(codi)
        if not cursos:
            return jsonify({}), 404
        avui = _fpo_today()
        buit = {'ca': '', 'es': ''}
        return jsonify({
            'codi': codi,
            'descripcio': cursos[0].get('titol', buit),
            'queAprendras': buit, 'requisits': buit, 'sortides': buit,
            'moduls': [], 'programaUrl': '',
            'cursos': [fpo_ext.curs_public(c, avui) for c in cursos],
        })
```

Executar `tests/test_fpo_ext_api.py`: ha de **passar**. Després la regressió estàndard.

### 2.3 `conftest.py` — aïllar `ext_cursos.json` a tots els tests

Afegir al final de `backend/tests/conftest.py` (`import sys` a dalt si no hi és):

```python
@pytest.fixture(autouse=True)
def _isola_ext_cursos(tmp_path, monkeypatch):
    """Cap test llegeix el data/ext_cursos.json real (Pla 063). Només si `app` ja és importat."""
    app_module = sys.modules.get("app")
    if app_module is None:
        return
    monkeypatch.setattr(app_module, "EXT_CURSOS_PATH", str(tmp_path / "no_ext_cursos.json"), raising=False)
    monkeypatch.setattr(app_module, "_ext_cursos_cache", {"mtime": None, "index": None}, raising=False)
    monkeypatch.setattr(app_module, "_ext_index_cache", {"key": None, "data": None}, raising=False)
```

Regressió estàndard: ha de seguir passant (141 + els nous; només els 2 fallos coneguts).

### 2.4 Commit

```
git add backend/app.py backend/tests/conftest.py backend/tests/test_fpo_ext_api.py
git commit -m "feat(fpo): els endpoints /api/fpo/* serveixen els cursos de PIMEC i Foment"
```

---

## Fase 3 — Favorits amb codis externs

### 3.1 Tests (falla primer)

**a)** A `backend/tests/test_fpo_favorites_api.py`, ampliar la fixture `fpo_fav_env`
(després de les línies que fan `monkeypatch.setattr(... "_soc_espec_index_cache" ...)`):

```python
    ext = [
        {"idCurs": "PIMEC:p1", "font": "pimec", "tipus": "Subvencionat",
         "titol": {"ca": "Programació neurolingüística", "es": "Programació neurolingüística"},
         "area": "Informàtica", "certCodi": "", "hores": 30.0, "modalitat": "PRESENCIAL",
         "estat": "", "dataInici": "2026-10-05", "dataFi": "2026-11-01",
         "municipi": "BARCELONA", "comarca": "", "centre": {"nom": "PIMEC Formació", "idCentre": ""},
         "fitxaUrl": "https://pimecformacio.org/x/p1"},
        {"idCurs": "PIMEC:p2", "font": "pimec", "tipus": "Subvencionat",
         "titol": {"ca": "Programació neurolingüística", "es": "Programació neurolingüística"},
         "area": "Informàtica", "certCodi": "", "hores": 30.0, "modalitat": "PRESENCIAL",
         "estat": "", "dataInici": "2026-06-01", "dataFi": "2026-07-01",
         "municipi": "BARCELONA", "comarca": "", "centre": {"nom": "PIMEC Formació", "idCentre": ""},
         "fitxaUrl": "https://pimecformacio.org/x/p2"},
    ]
    (tmp_path / "ext_cursos.json").write_text(json.dumps(ext), encoding="utf-8")
    monkeypatch.setattr(app_module, "EXT_CURSOS_PATH", str(tmp_path / "ext_cursos.json"))
    monkeypatch.setattr(app_module, "_ext_cursos_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(app_module, "_ext_index_cache", {"key": None, "data": None})
    monkeypatch.setattr(app_module, "_fpo_today", lambda: "2026-09-25")
```

**b)** Afegir al final del mateix fitxer:

```python
def test_desa_especialitat_externa_i_marca_cursos(auth_client):
    codi = "PIMEC:programacio-neurolinguistica"
    assert _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": codi}).status_code == 201
    for curs_id in ("PIMEC:p1", "PIMEC:p2", "PIMEC:desaparegut"):
        r = _json(auth_client, "post", f"/api/fpo/favorites/{codi}/courses", {"curs_id": curs_id})
        assert r.status_code == 201

    e = auth_client.get("/api/fpo/favorites").get_json()[0]
    assert e["titol"]["ca"] == "Programació neurolingüística"
    assert e["font"] == "pimec"
    assert e["hores"] == 30.0
    per_id = {c["curs_id"]: c for c in e["cursos"]}
    p1 = per_id["PIMEC:p1"]
    assert p1["finalitzat"] is False and p1["estat"] == ""
    assert p1["font"] == "pimec" and p1["fitxaUrl"] == "https://pimecformacio.org/x/p1"
    assert p1["centre"]["nom"] == "PIMEC Formació" and p1["dataInici"] == "2026-10-05"
    assert per_id["PIMEC:p2"]["finalitzat"] is True         # dataFi passada
    assert per_id["PIMEC:desaparegut"]["finalitzat"] is True  # ja no és al snapshot


def test_treu_especialitat_externa(auth_client):
    codi = "PIMEC:programacio-neurolinguistica"
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": codi})
    assert auth_client.delete(f"/api/fpo/favorites/{codi}").status_code == 204
    assert auth_client.get("/api/fpo/favorites").get_json() == []


def test_favorit_soc_no_canvia(auth_client):
    _json(auth_client, "post", "/api/fpo/favorites", {"especialitat_codi": "IFCD0112"})
    _json(auth_client, "post", "/api/fpo/favorites/IFCD0112/courses", {"curs_id": "C1"})
    e = auth_client.get("/api/fpo/favorites").get_json()[0]
    assert e["font"] == "soc" and e["cursos"][0]["font"] == "soc"
    assert e["cursos"][0]["fitxaUrl"].startswith("https://serveiocupacio.gencat.cat")
```

Executar `python3 -m pytest -q tests/test_fpo_favorites_api.py`: els dos primers nous i
el tercer han de **fallar** (`KeyError: 'font'` / títol buit).

### 3.2 Implementació (a `backend/app.py`)

**a)** Substituir `_fpo_espec_by_codi` i `_fpo_curs_by_id`:

```python
def _fpo_espec_by_codi(codi):
    """Especialitat FPO per codi (SOC o externa), o {} si no hi és."""
    if fpo_ext.is_ext_codi(codi):
        return next((e for e in _ext_index()["list"] if e["codi"] == codi), {})
    for e in _get_soc_especs():
        if e.get("codi") == codi:
            return e
    return {}


def _fpo_curs_by_id(curs_id):
    """Curs FPO per idCurs (SOC o extern), o None si ja no hi és."""
    if fpo_ext.is_ext_codi(curs_id):
        return next((c for c in _get_ext_cursos() if c.get("idCurs") == curs_id), None)
    for c in _get_soc_cursos():
        if c.get("idCurs") == curs_id:
            return c
    return None
```

**b)** Substituir `_fpo_fav_course_public`:

```python
def _fpo_fav_course_public(row):
    """Enriqueix una fila de fpo_favorite_courses amb dades del snapshot (SOC o extern)."""
    curs = _fpo_curs_by_id(row["curs_id"])
    ext = curs is not None and curs.get("font") in fpo_ext.FONTS
    estat = ""
    if curs is not None:
        estat = fpo_ext.estat(curs, _fpo_today()) if ext else curs.get("estat", "")
    out = {
        "curs_id": row["curs_id"],
        "centre_id": row["centre_id"],
        "created_at": row["created_at"],
        # Els estats del SOC mai són 'finalitzat': aquest valor només surt dels externs.
        "finalitzat": curs is None or estat == "finalitzat",
    }
    if curs is not None:
        out.update({
            "titol": curs.get("titol", {"ca": "", "es": ""}),
            "centre": curs.get("centre", {}),
            "dataInici": curs.get("dataInici"),
            "dataFi": curs.get("dataFi"),
            "estat": estat,
            "modalitat": curs.get("modalitat", ""),
            "fitxaUrl": curs.get("fitxaUrl", "") if ext else _soc_fitxa_url(curs),
            "font": curs.get("font", "soc"),
            "tipus": curs.get("tipus", ""),
            "horariText": curs.get("horariText", ""),
        })
    return out
```

**c)** A `fpo_favorites_get`, dins del `result.append({...})`, afegir la clau
`"font": espec.get("font", "soc"),` (després de `"especialitat_codi": codi,`).

Executar `tests/test_fpo_favorites_api.py` + regressió estàndard: han de **passar**.

### 3.3 Commit

```
git add backend/app.py backend/tests/test_fpo_favorites_api.py
git commit -m "feat(fpo): els favorits accepten especialitats i cursos de PIMEC i Foment"
```

---

## Fase 4 — Hook del refresc d'admin

`POST /api/admin/refresh-fpo` només regenerava el SOC; ha de refrescar també PIMEC/Foment.

### 4.1 Tests (falla primer)

A `backend/tests/test_admin_fpo.py`:

**a)** Afegir, després de la fixture `soc_paths`, una fixture `autouse` (perquè els tests
existents **no toquin la xarxa** un cop el hook existeixi):

```python
@pytest.fixture(autouse=True)
def ext_mock():
    with patch("scrapers.pipeline.refresh_ext_cursos", return_value={"pimec": 0, "foment": 0}) as m:
        yield m
```

**b)** Afegir al final:

```python
def test_refresh_fpo_tambe_refresca_pimec_i_foment(client, ext_mock, soc_paths):
    with patch("scrapers.soc_scraper.build_soc_data", return_value=_FAKE_SOC):
        assert client.post("/api/admin/refresh-fpo", headers=_AUTH).status_code == 200
        _wait_status(client, "done")
    ext_mock.assert_called_once_with(str(soc_paths))


def test_refresh_fpo_no_falla_si_pimec_i_foment_peten(client, ext_mock):
    ext_mock.side_effect = RuntimeError("PIMEC caigut")
    with patch("scrapers.soc_scraper.build_soc_data", return_value=_FAKE_SOC):
        client.post("/api/admin/refresh-fpo", headers=_AUTH)
        st = _wait_status(client, "done")
    assert st["last_error"] is None
```

Executar `python3 -m pytest -q tests/test_admin_fpo.py`: el primer test nou ha de
**fallar** (`called once` → 0 crides).

### 4.2 Implementació

A `_run_fpo_refresh` (`app.py`), **després** de la línia
`_soc_espec_index_cache.update(key=None, data=None)` i abans de
`n = {k: len(soc.get(k, [])) ...}`:

```python
        try:
            from scrapers.pipeline import refresh_ext_cursos
            refresh_ext_cursos(data_dir)
        except Exception as ext_exc:  # una font extra no ha de tombar el refresc del SOC
            logger.warning("refresh-fpo: PIMEC/Foment ha fallat: %s", ext_exc)
        _ext_cursos_cache.update(mtime=None, index=None)
        _ext_index_cache.update(key=None, data=None)
```

Actualitzar el docstring de `admin_refresh_fpo`: "Regenera els soc_*.json i
ext_cursos.json (PIMEC/Foment) en background (no el pipeline sencer)."

Executar `tests/test_admin_fpo.py` + regressió estàndard: han de **passar**.

### 4.3 Commit

```
git add backend/app.py backend/tests/test_admin_fpo.py
git commit -m "feat(fpo): el refresc d'admin també actualitza PIMEC i Foment"
```

---

## Verificació final

1. Regressió estàndard (141 + nous, només els 2 fallos coneguts de `test_db.py`).
2. `python3 -m pytest -q tests/test_pimec_scraper.py tests/test_foment_scraper.py tests/test_ext_refresh.py tests/test_soc_scraper.py` (pla 062 + SOC): passen.
3. Comprovar que `git status` només mostra els fitxers d'aquest pla i que **no** hi ha
   cap `data/ext_cursos.json` nou versionat sense voler (mirar `.gitignore` de `data/`).

## Fora d'abast

- `/api/fpo/by-cert`, cerca per ocupació, migracions de BD.
- Tota la UI (insígnies, filtres, i18n, perfil, `fonts.html`, `historial.html`) → Pla 064.
- Desplegament: es fa després del 064 (backend primer, després frontend; reiniciar
  `fp-cercador` i executar un refresc d'admin per generar `ext_cursos.json` al VPS).
