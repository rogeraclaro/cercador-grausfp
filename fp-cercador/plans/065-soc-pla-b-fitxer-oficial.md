# Pla 065 — SOC: pla B amb el fitxer oficial de dades obertes

Origen: conversa 2026-09-25 (el SOC es consulta via Algolia, una API no oficial; existeix una font oficial).
Depèn de: **062 DONE** (afegeix `font` a `_soc_diff_entry`) i **064 DONE** (la UI amaga l'estat buit).
Sessió neta. **TDD estricte**, tests **sense xarxa**. **No cal decidir res.**

## Objectiu i abast

Si el refresc del SOC via Algolia **falla** (claus rotades, canvi d'API, caiguda), en comptes de
quedar-nos amb el snapshot vell, **refrescar `soc_cursos.json` des del fitxer oficial** i seguir servint dades
actuals. **Algolia continua sent la font principal**: el fitxer oficial és més pobre (vegeu sota).
Només es toca `soc_cursos.json`; `soc_especs.json` i `soc_centres.json` no canvien.

Fora d'abast: canviar la font principal, refrescar especialitats o centres des d'oficial, el conjunt
`eed3-6eca` (especialitats), qualsevol canvi de UI més enllà d'una etiqueta a l'historial.

## Fets verificats (2026-09-25; no re-investigar)

**Font:** `https://oficinadetreball.gencat.cat/opendata/recursos/ofertaCursos.json` (conjunt `sts9-unyu` de
Dades obertes de Catalunya). Llista JSON de 875 files, un sol GET (565 KB, 0,15 s), `Last-Modified` del mateix dia.
- **Codificació cp1252, no UTF-8** (`decode('utf-8')` falla al byte 0xF3).
- **Files duplicades exactes**: 74 `identificador_curs` repetits → **801 cursos únics** (= 801 valors de `curs`).
- Camps: `curs`, `tipus` (sempre "Formació ocupacional"), `identificador_curs`, `especialitat_formativa` (només el
  **nom**), `cifo`, `municipi_especialitat`, `provincia_especialitat`, `modalitat`, `data_inici`/`data_fi`
  (**mm/dd/aaaa**), `hores`, `estat_curs`, `adreca_curs`, `nom_centre`, `adreca_centre`, `telefon_centre`,
  `web_centre`, `municipi_centre`, `garantia_juvenil`.

**Fidelitat contra Algolia en viu** (809 cursos; una comparació amb un snapshot de 5 dies donava soroll fals):
- Els 801 cursos oficials **són tots a Algolia** (només 8 d'Algolia hi manquen: 6 en "gestió", 2 en "informació").
- Coincidència exacta a 801/801 de: `identificador_curs` = `idCurs`, `hores`, `modalitat`, `municipi_especialitat` =
  `municipi`, `provincia_especialitat` = `provincia`, `nom_centre` = `centre.nom`, `telefon_centre` =
  `centre.telefon`, `adreca_curs` = `centre.carrer`. Dates diferents: 7 de 801. Cap hora decimal, cap camp buit.
- `web_centre` de vegades és un **correu** (`@`): 801/801 coincideixen si es tracta com a `email` quan porta `@`, i com a `web` si no.
- **L'estat és més gros:** el fitxer només té "informació" i "inscripció". "Informació" és fiable (542/542 coincideixen).
  **"Inscripció" barreja tres estats d'Algolia:** 87 inscripció, **168 gestió**, 4 informació. Mostrar-ho tal qual
  donaria 172 estats falsos de 801 (21 %).

**Què li falta (vs Algolia):** codi d'especialitat, família, àrea, nivell, certificat/RD, programa (PDF),
què aprendràs/requisits/sortides, mòduls, ocupacions, horari setmanal, coordenades, comarca, `idCentre`, `cp`, correu propi.

**Resolució de l'especialitat (el codi que agrupa les files de la UI):**
- Amb el snapshot anterior (`idCurs` → especialitat) + el catàleg `soc_especs.json` (nom, i hores per desempatar):
  **800 de 801 correctes, 0 incorrectes**, 1 sense resoldre.
- Només per nom + hores (curs nou sense snapshot): 750 correctes, **2 incorrectes**, 49 sense resoldre.

## Decisions de disseny

1. **Requereix snapshot anterior.** El pla B parteix de `soc_cursos.json` i `soc_especs.json` que ja hi ha al disc. Si falten o
   són buits → `OfficialFallbackError` **abans de cap petició** (no és un mecanisme d'arrencada en fred).
2. **Cursos ja coneguts** (mateix `idCurs` al snapshot): es parteix del registre anterior (conserva `queAprendras`,
   `requisits`, `sortides`, `moduls`, `comarca`, `centre` complet…) i se sobreescriuen només els camps volàtils:
   `dataInici`, `dataFi`, `hores`, `modalitat`, `estat`.
3. **Cursos nous:** especialitat = coincidència **única** del nom normalitzat al catàleg; si n'hi ha diverses, es desempata per
   `hores`; si continua sense ser única → el curs **s'omet** (es registra el recompte). Registre "prim": família/àrea/nivell/
   cert/programa/mòduls de l'especialitat; `comarca` deduïda del mapa `municipi → comarca` del snapshot anterior; camps rics buits.
4. **Estat conservador** (mai es mostra un estat que pugui ser fals; simulat: 671 correctes, 130 desconeguts, **0 incorrectes**):
   - "informació" oficial → `informacio`.
   - "inscripció" oficial → `gestio` només si el snapshot anterior deia `gestio` (estat terminal); altrament **`''`** (desconegut; la UI l'amaga).
5. **Els cursos que no són al fitxer oficial desapareixen** del snapshot (els finalitzats o els que oficial no publica).
6. **Salvaguarda:** si el resultat té menys de la meitat dels cursos anteriors (o cap) → `OfficialFallbackError` i no s'escriu res.
7. **Quan s'activa:** només quan `build_soc_data()` llança una excepció, tant al pipeline com al refresc d'admin. Si el pla B també
   falla, es comporta com fins ara (snapshot vell + avís a l'admin).
8. L'historial (`soc_refresh_history.json`) rep una entrada `ok: true` amb `via: 'oficial'`; `historial.html` mostra "OK (font oficial)".
   L'avís per correu a l'admin per l'error d'Algolia **es manté** (és l'important).

## Fitxers

- Crear `backend/scrapers/soc_official.py`.
- Modificar `backend/scrapers/pipeline.py` (`_soc_diff_entry`, nova `soc_fallback_official`, bloc SOC de `run()`),
  `backend/app.py` (`_run_fpo_refresh`), `frontend/historial.html`.
- Tests nous: `backend/tests/test_soc_official.py`, `backend/tests/test_soc_fallback.py`; ampliar `backend/tests/test_admin_fpo.py`.

Tests: els de `*scraper*` s'exclouen de la comanda estàndard; **aquests s'executen per ruta**:
`python3 -m pytest -q tests/test_soc_official.py tests/test_soc_fallback.py` des de `fp-cercador/backend`.

---

## Fase 1 — Mòdul `soc_official.py`

### 1.1 Tests (falla primer)

Crear `backend/tests/test_soc_official.py`:

```python
"""test_soc_official.py — Pla B del SOC amb el fitxer oficial (Pla 065). Sense xarxa."""
import json

import pytest

from scrapers import soc_official as so
from scrapers.soc_scraper import normalize_curs

ESPEC = {
    'codi': 'IFCD0112', 'titol': {'ca': 'Programació amb Python', 'es': 'Programación con Python'},
    'familia': {'codi': 'IFC', 'desc': {'ca': 'INFORMÀTICA', 'es': 'INFORMÁTICA'}},
    'area': {'codi': 'IFCD', 'desc': {'ca': 'DESENVOLUPAMENT', 'es': 'DESARROLLO'}},
    'nivell': 3, 'hores': 590.0, 'esCertProf': True, 'rd': 'RD 1',
    'programaUrl': 'https://p/x.pdf',
    'moduls': [{'codi': 'MF1', 'desc': {'ca': 'M1', 'es': 'M1'}, 'durada': 90.0}],
}
ESPEC2 = dict(ESPEC, codi='IFCD0212', hores=300.0)          # mateix nom que ESPEC, altres hores
ESPECS = [ESPEC]


def _row(idc='25/X/1', nom='Programació amb Python', **kw):
    r = {
        'curs': '1', 'tipus': 'Formació ocupacional', 'identificador_curs': idc,
        'especialitat_formativa': nom, 'cifo': 'No', 'municipi_especialitat': 'LLEIDA',
        'provincia_especialitat': 'LLEIDA', 'modalitat': 'PRESENCIAL',
        'data_inici': '09/30/2026', 'data_fi': '12/02/2026', 'hores': '590',
        'estat_curs': "Curs en període d'informacio", 'adreca_curs': 'AV ESTUDI 29',
        'nom_centre': 'CENTRE X', 'adreca_centre': 'AV ESTUDI 29', 'telefon_centre': '973000000',
        'web_centre': 'www.x.cat', 'municipi_centre': 'LLEIDA', 'garantia_juvenil': 'NO',
    }
    r.update(kw)
    return r


def _prev(idc='25/X/1', estat='informacio', **kw):
    p = normalize_curs({})
    p.update({'idCurs': idc, 'estat': estat, 'comarca': 'SEGRIÀ', 'municipi': 'LLEIDA',
              'especialitat': {'codi': 'IFCD0112', 'desc': ESPEC['titol']},
              'dataInici': '2026-01-01', 'dataFi': '2026-02-02', 'hores': 1.0, 'modalitat': 'MIXTA',
              'queAprendras': {'ca': 'Aprendràs', 'es': 'Aprenderás'},
              'centre': dict(p['centre'], nom='CENTRE X', email='a@b.cat', lat=41.6, lon=0.6)})
    p.update(kw)
    return p


# --- lectura del fitxer ----------------------------------------------------

class _Resp:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        pass


class _Sess:
    def __init__(self, content):
        self.content, self.calls = content, 0

    def get(self, url, headers=None, timeout=None):
        self.calls += 1
        return _Resp(self.content)


def test_fetch_descodifica_cp1252():
    dades = json.dumps([_row()], ensure_ascii=False).encode('cp1252')
    assert so.fetch_official(_Sess(dades))[0]['tipus'] == 'Formació ocupacional'


def test_fetch_accepta_utf8_si_algun_dia_ho_arreglen():
    dades = json.dumps([_row()], ensure_ascii=False).encode('utf-8')
    assert so.fetch_official(_Sess(dades))[0]['tipus'] == 'Formació ocupacional'


def test_fetch_format_inesperat():
    with pytest.raises(so.OfficialFallbackError):
        so.fetch_official(_Sess(b'{"error": true}'))


def test_dedupe_conserva_el_primer():
    a, b = _row('A'), _row('B')
    assert [r['identificador_curs'] for r in so.dedupe([a, b, dict(a)])] == ['A', 'B']


# --- estat ------------------------------------------------------------------

@pytest.mark.parametrize('oficial, prev_estat, esperat', [
    ("Curs en període d'informacio", None, 'informacio'),
    ("Curs en període d'informacio", 'gestio', 'informacio'),
    ("Curs en període d'inscripcio", 'gestio', 'gestio'),       # "gestió" és terminal
    ("Curs en període d'inscripcio", 'inscripcio', ''),         # desconegut
    ("Curs en període d'inscripcio", 'informacio', ''),
    ("Curs en període d'inscripcio", None, ''),
])
def test_estat_conservador(oficial, prev_estat, esperat):
    prev = _prev(estat=prev_estat) if prev_estat else None
    assert so._estat(oficial, prev) == esperat


# --- construcció ------------------------------------------------------------

def test_curs_conegut_conserva_dades_riques_i_actualitza_les_volatils():
    rows = [_row(data_inici='10/05/2026', data_fi='01/15/2027', hores='600', modalitat='TELEFORMACIÓ')]
    out = so.build_from_official(rows, [_prev()], ESPECS)
    assert len(out) == 1
    c = out[0]
    assert c['queAprendras'] == {'ca': 'Aprendràs', 'es': 'Aprenderás'} and c['comarca'] == 'SEGRIÀ'
    assert c['centre']['email'] == 'a@b.cat' and c['centre']['lat'] == 41.6
    assert (c['dataInici'], c['dataFi'], c['hores'], c['modalitat']) == (
        '2026-10-05', '2027-01-15', 600.0, 'TELEFORMACIÓ')
    assert c['estat'] == 'informacio'


def test_curs_nou_per_nom_unic():
    prev = [_prev('OLD')]
    out = so.build_from_official([_row('NOU', municipi_especialitat='Lleida', web_centre='c@x.cat')], prev, ESPECS)
    assert [c['idCurs'] for c in out] == ['NOU']      # 'OLD' ja no és al fitxer: desapareix
    c = out[0]
    assert set(c) == set(normalize_curs({})) and set(c['centre']) == set(normalize_curs({})['centre'])
    assert c['especialitat'] == {'codi': 'IFCD0112', 'desc': ESPEC['titol']}
    assert c['familia']['codi'] == 'IFC' and c['nivell'] == 3 and c['esCertProf'] is True
    assert c['comarca'] == 'SEGRIÀ'                     # deduïda del mapa municipi -> comarca del snapshot
    assert c['centre']['email'] == 'c@x.cat' and c['centre']['web'] == ''
    assert c['centre']['nom'] == 'CENTRE X' and c['centre']['carrer'] == 'AV ESTUDI 29'
    assert c['queAprendras'] == {'ca': '', 'es': ''} and c['ocupacions'] == []
    assert c['moduls'] == ESPEC['moduls'] and c['estat'] == 'informacio'    # "informació" oficial és fiable


def test_curs_nou_amb_inscripcio_oficial_te_estat_desconegut():
    c = so.build_from_official([_row('N', estat_curs="Curs en període d'inscripcio")], [_prev('OLD')], ESPECS)[0]
    assert c['estat'] == ''


def test_curs_nou_web_no_es_correu():
    c = so.build_from_official([_row('N')], [_prev('OLD')], ESPECS)[0]
    assert c['centre']['web'] == 'www.x.cat' and c['centre']['email'] == ''


def test_nom_ambigu_es_desempata_per_hores():
    especs = [ESPEC, ESPEC2]
    out = so.build_from_official([_row('N1', hores='300'), _row('N2', hores='590')], [_prev('OLD')], especs)
    assert {c['idCurs']: c['especialitat']['codi'] for c in out} == {'N1': 'IFCD0212', 'N2': 'IFCD0112'}


def test_nom_sense_resoldre_s_omet():
    especs = [ESPEC, ESPEC2]                                   # mateix nom, 590 h i 300 h
    out = so.build_from_official([_row('N1', hores='999'), _row('OK', hores='590')], [_prev('OLD')], especs)
    assert [c['idCurs'] for c in out] == ['OK']                # 999 h no desempata


def test_curs_amb_especialitat_desconeguda_s_omet_i_no_peta():
    prev = [_prev('OLD'), _prev('K2'), _prev('K3')]
    rows = [_row('K2'), _row('K3'), _row('X', nom='Especialitat inexistent')]
    assert [c['idCurs'] for c in so.build_from_official(rows, prev, ESPECS)] == ['K2', 'K3']


def test_data_invalida_es_none():
    assert so._iso('13/45/2026') is None and so._iso('') is None and so._iso('09/30/2026') == '2026-09-30'


def test_salvaguarda_menys_de_la_meitat():
    prev = [_prev(str(i)) for i in range(4)]
    with pytest.raises(so.OfficialFallbackError):
        so.build_from_official([_row('0')], prev, ESPECS)          # 1 < 4/2


def test_fetch_and_build_sense_snapshot_falla_abans_de_la_xarxa(tmp_path):
    sess = _Sess(b'[]')
    with pytest.raises(so.OfficialFallbackError):
        so.fetch_and_build(str(tmp_path), session=sess)
    assert sess.calls == 0


def test_fetch_and_build_de_punta_a_punta(tmp_path):
    (tmp_path / 'soc_cursos.json').write_text(json.dumps([_prev('25/X/1')]), encoding='utf-8')
    (tmp_path / 'soc_especs.json').write_text(json.dumps(ESPECS), encoding='utf-8')
    dades = json.dumps([_row('25/X/1'), _row('25/X/1')], ensure_ascii=False).encode('cp1252')  # duplicat exacte
    out = so.fetch_and_build(str(tmp_path), session=_Sess(dades))
    assert [c['idCurs'] for c in out] == ['25/X/1']
```

Executar: ha de **fallar** (`ModuleNotFoundError: scrapers.soc_official`).

### 1.2 Implementació

Crear `backend/scrapers/soc_official.py`:

```python
"""
soc_official.py — Pla B del SOC: cursos des del fitxer de dades obertes (Pla 065).

Font: https://oficinadetreball.gencat.cat/opendata/recursos/ofertaCursos.json (conjunt `sts9-unyu`
de Dades obertes de Catalunya). Llista JSON en cp1252 amb files duplicades. Coincideix amb Algolia
(mateixos cursos, dates, hores, modalitat i centre) però és MÉS POBRE i té l'estat més gros: no
distingeix "gestió". Per això no substitueix Algolia: s'usa només si Algolia falla, i sempre sobre
el snapshot anterior (que aporta especialitat, família, mòduls, comarca…).
"""
import copy
import json
import logging
import os
import re
import unicodedata

import requests

logger = logging.getLogger(__name__)

OFFICIAL_URL = 'https://oficinadetreball.gencat.cat/opendata/recursos/ofertaCursos.json'
_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

_VOLATILS = ('dataInici', 'dataFi', 'hores', 'modalitat', 'estat')


class OfficialFallbackError(Exception):
    """El pla B no pot produir un snapshot fiable."""


# ---------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------

def fetch_official(session=None) -> list[dict]:
    resp = (session or requests).get(OFFICIAL_URL, headers={'User-Agent': _UA}, timeout=60)
    resp.raise_for_status()
    text = None
    for enc in ('utf-8', 'cp1252', 'latin-1'):        # el fitxer és cp1252; si un dia és UTF-8, també va bé
        try:
            text = resp.content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    rows = json.loads(text)
    if not isinstance(rows, list):
        raise OfficialFallbackError('format inesperat del fitxer oficial (no és una llista)')
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    """El fitxer repeteix files idèntiques: es conserva la primera de cada `identificador_curs`."""
    seen, out = set(), []
    for r in rows:
        i = r.get('identificador_curs')
        if i and i not in seen:
            seen.add(i)
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iso(s) -> str | None:
    """'mm/dd/aaaa' -> 'aaaa-mm-dd'; buit o invàlid -> None."""
    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', (s or '').strip())
    if not m or not (1 <= int(m[1]) <= 12 and 1 <= int(m[2]) <= 31):
        return None
    return f'{m[3]}-{m[1]}-{m[2]}'


def _num(v) -> float:
    try:
        return float(str(v).replace(',', '.'))
    except ValueError:
        return 0.0


def _norm(s) -> str:
    s = unicodedata.normalize('NFKD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^A-Z0-9]+', ' ', s.upper()).strip()


def _estat(estat_oficial: str, prev: dict | None) -> str:
    """Estat conservador: mai es mostra un estat que pugui ser fals.

    "Informació" oficial és fiable. "Inscripció" oficial barreja inscripció, gestió i informació
    d'Algolia; només "gestió" és terminal, així que només es manté si el snapshot ja el tenia.
    Altrament es deixa buit (la UI l'amaga)."""
    if 'informaci' in (estat_oficial or '').lower():
        return 'informacio'
    return 'gestio' if prev and prev.get('estat') == 'gestio' else ''


def _resolve_espec(row: dict, by_norm: dict):
    cands = by_norm.get(_norm(row.get('especialitat_formativa')), [])
    if len(cands) > 1:
        h = _num(row.get('hores'))
        cands = [e for e in cands if e.get('hores') == h]
    return cands[0] if len(cands) == 1 else None


def _update_prev(row: dict, prev: dict) -> dict:
    c = copy.deepcopy(prev)
    c['dataInici'], c['dataFi'] = _iso(row.get('data_inici')), _iso(row.get('data_fi'))
    c['hores'] = _num(row.get('hores'))
    c['modalitat'] = row.get('modalitat', '') or ''
    c['estat'] = _estat(row.get('estat_curs'), prev)
    return c


def _new_curs(row: dict, espec: dict, comarca_de: dict) -> dict:
    web = (row.get('web_centre') or '').strip()
    email, web = (web, '') if '@' in web else ('', web)
    municipi = (row.get('municipi_especialitat') or '').strip()
    comarca = comarca_de.get(municipi.upper(), '')
    titol = (row.get('especialitat_formativa') or '').strip()
    return {
        'idCurs': row['identificador_curs'],
        'titol': {'ca': titol, 'es': titol},
        'familia': espec.get('familia', {}),
        'area': espec.get('area', {}),
        'especialitat': {'codi': espec['codi'], 'desc': espec.get('titol', {'ca': '', 'es': ''})},
        'esCertProf': bool(espec.get('esCertProf')),
        'rd': espec.get('rd'),
        'nivell': espec.get('nivell', 0),
        'hores': _num(row.get('hores')),
        'modalitat': row.get('modalitat', '') or '',
        'estat': _estat(row.get('estat_curs'), None),
        'dataInici': _iso(row.get('data_inici')),
        'dataFi': _iso(row.get('data_fi')),
        'comarca': comarca,
        'municipi': municipi,
        'provincia': (row.get('provincia_especialitat') or '').strip(),
        'centre': {
            'nom': (row.get('nom_centre') or '').strip(),
            'carrer': (row.get('adreca_curs') or '').strip(),
            'cp': '',
            'municipi': (row.get('municipi_centre') or '').strip(),
            'comarca': comarca,
            'telefon': (row.get('telefon_centre') or '').strip(),
            'email': email,
            'web': web,
            'idCentre': '',
            'horari': {},
            'lat': None,
            'lon': None,
        },
        'programaUrl': espec.get('programaUrl', ''),
        'queAprendras': {'ca': '', 'es': ''},
        'requisits': {'ca': '', 'es': ''},
        'sortides': {'ca': '', 'es': ''},
        'moduls': espec.get('moduls', []),
        'ocupacions': [],
    }


# ---------------------------------------------------------------------------
# Orquestració
# ---------------------------------------------------------------------------

def build_from_official(rows: list[dict], prev_cursos: list[dict], especs: list[dict]) -> list[dict]:
    """Cursos actuals (fitxer oficial) enriquits amb el snapshot anterior i el catàleg d'especialitats."""
    prev = {c.get('idCurs'): c for c in prev_cursos}
    by_codi = {e['codi']: e for e in especs if e.get('codi')}
    by_norm: dict = {}
    for e in especs:
        by_norm.setdefault(_norm((e.get('titol') or {}).get('ca')), []).append(e)
    comarca_de = {(c.get('municipi') or '').upper(): c['comarca']
                  for c in prev_cursos if c.get('municipi') and c.get('comarca')}

    out, omesos = [], 0
    for r in dedupe(rows):
        p = prev.get(r['identificador_curs'])
        if p is not None:
            out.append(_update_prev(r, p))
            continue
        espec = _resolve_espec(r, by_norm)
        if espec is None:
            omesos += 1
            continue
        out.append(_new_curs(r, by_codi.get(espec['codi'], espec), comarca_de))
    if omesos:
        logger.warning('soc_official: %d cursos nous omesos (especialitat no identificable)', omesos)
    if not out or len(out) < len(prev_cursos) / 2:
        raise OfficialFallbackError(
            f'el fitxer oficial dóna {len(out)} cursos i el snapshot en tenia {len(prev_cursos)}')
    return out


def _read_list(path: str) -> list:
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def fetch_and_build(data_dir: str, session=None) -> list[dict]:
    """Llegeix el snapshot anterior, baixa el fitxer oficial i retorna els cursos nous.

    Falla ABANS de fer cap petició si no hi ha snapshot anterior (el pla B no serveix en fred)."""
    prev = _read_list(os.path.join(data_dir, 'soc_cursos.json'))
    especs = _read_list(os.path.join(data_dir, 'soc_especs.json'))
    if not prev or not especs:
        raise OfficialFallbackError('no hi ha snapshot anterior (soc_cursos.json / soc_especs.json)')
    return build_from_official(fetch_official(session), prev, especs)
```

Executar `tests/test_soc_official.py`: ha de **passar**.

### 1.3 Commit
```
git add backend/scrapers/soc_official.py backend/tests/test_soc_official.py
git commit -m "feat(soc): pla B amb el fitxer oficial de dades obertes"
```

---

## Fase 2 — Pipeline i refresc d'admin

### 2.1 Tests (falla primer)

Crear `backend/tests/test_soc_fallback.py`:

```python
"""test_soc_fallback.py — Activació del pla B del SOC (Pla 065). Sense xarxa."""
import json
from unittest.mock import patch

from scrapers import pipeline


def _c(i):
    return {'idCurs': i, 'estat': 'informacio'}


def test_diff_entry_via_nomes_si_s_indica():
    assert 'via' not in pipeline._soc_diff_entry([], [], ok=True)
    assert pipeline._soc_diff_entry([], [], ok=True, via='oficial')['via'] == 'oficial'


def test_fallback_escriu_els_cursos_i_l_historial(tmp_path):
    (tmp_path / 'soc_cursos.json').write_text(json.dumps([_c('A'), _c('B')]), encoding='utf-8')
    nous = [_c('A'), _c('C')]
    with patch('scrapers.soc_official.fetch_and_build', return_value=nous):
        res = pipeline.soc_fallback_official(str(tmp_path), RuntimeError('claus rotades'))
    assert res == nous
    assert [c['idCurs'] for c in json.loads((tmp_path / 'soc_cursos.json').read_text())] == ['A', 'C']
    e = json.loads((tmp_path / 'soc_refresh_history.json').read_text())[0]
    assert (e['font'], e['ok'], e['via'], e['n_cursos'], e['n_afegits'], e['n_retirats']) == (
        'soc', True, 'oficial', 2, 1, 1)


def test_fallback_que_falla_deixa_el_snapshot_i_retorna_none(tmp_path):
    original = json.dumps([_c('A')])
    (tmp_path / 'soc_cursos.json').write_text(original, encoding='utf-8')
    with patch('scrapers.soc_official.fetch_and_build', side_effect=RuntimeError('xarxa')):
        assert pipeline.soc_fallback_official(str(tmp_path), RuntimeError('algolia')) is None
    assert (tmp_path / 'soc_cursos.json').read_text() == original
    assert not (tmp_path / 'soc_refresh_history.json').exists()
```

I afegir al final de `backend/tests/test_admin_fpo.py`:

```python
def test_refresh_fpo_usa_el_pla_b_si_algolia_falla(client, soc_paths):
    nous = [{"idCurs": "N1"}, {"idCurs": "N2"}]
    with patch("scrapers.soc_scraper.build_soc_data", side_effect=RuntimeError("claus rotades")), \
         patch("scrapers.pipeline._notify_admin_soc_failure") as notify, \
         patch("scrapers.pipeline.soc_fallback_official", return_value=nous) as fb:
        client.post("/api/admin/refresh-fpo", headers=_AUTH)
        st = _wait_status(client, "done")
    notify.assert_called_once()                       # l'avís a l'admin es manté
    fb.assert_called_once()
    assert st["fallback"] == "oficial" and st["cursos"] == 2 and st["last_error"] is None


def test_un_refresc_normal_neteja_el_fallback_anterior(client):
    with patch("scrapers.soc_scraper.build_soc_data", side_effect=RuntimeError("claus rotades")), \
         patch("scrapers.pipeline._notify_admin_soc_failure"), \
         patch("scrapers.pipeline.soc_fallback_official", return_value=[{"idCurs": "N1"}]):
        client.post("/api/admin/refresh-fpo", headers=_AUTH)
        assert _wait_status(client, "done")["fallback"] == "oficial"
    with patch("scrapers.soc_scraper.build_soc_data", return_value=_FAKE_SOC):
        client.post("/api/admin/refresh-fpo", headers=_AUTH)
        st = _wait_status(client, "done")
    assert not st.get("fallback") and st["cursos"] == 1


def test_refresh_fpo_error_si_tampoc_va_el_pla_b(client):
    with patch("scrapers.soc_scraper.build_soc_data", side_effect=RuntimeError("Algolia 500")), \
         patch("scrapers.pipeline._notify_admin_soc_failure"), \
         patch("scrapers.pipeline.soc_fallback_official", return_value=None):
        client.post("/api/admin/refresh-fpo", headers=_AUTH)
        st = _wait_status(client, "error")
    assert "Algolia 500" in (st["last_error"] or "") and not st.get("fallback")
```

Executar `python3 -m pytest -q tests/test_soc_fallback.py tests/test_admin_fpo.py`: ha de **fallar**.

### 2.2 Implementació

**a) `pipeline.py`.** A `_soc_diff_entry` (que el Pla 062 ja ha deixat amb `font`), afegir el paràmetre `via` i la clau només si s'indica:

```python
def _soc_diff_entry(prev_cursos: list, curr_cursos: list, *, ok: bool,
                    error: str | None = None, font: str = 'soc', via: str | None = None) -> dict:
    prev_ids = {c.get('idCurs') for c in (prev_cursos or []) if isinstance(c, dict)}
    curr_ids = {c.get('idCurs') for c in (curr_cursos or []) if isinstance(c, dict)}
    entry = {
        'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'font': font,
        'ok': ok,
        'error': error,
        'n_cursos': len(curr_cursos or []),
        'n_afegits': len(curr_ids - prev_ids) if ok else 0,
        'n_retirats': len(prev_ids - curr_ids) if ok else 0,
    }
    if via:
        entry['via'] = via
    return entry
```

Afegir, després de `refresh_ext_cursos` (i abans de `# API pública`):

```python
def soc_fallback_official(data_dir: str, algolia_exc: Exception) -> list | None:
    """Pla B (Pla 065): si Algolia ha fallat, refresca soc_cursos.json des del fitxer oficial.

    Només reescriu soc_cursos.json (especialitats i centres queden com estan). Retorna els cursos nous,
    o None si el pla B tampoc funciona (aleshores tot queda com abans)."""
    from scrapers import soc_official
    path = os.path.join(data_dir, 'soc_cursos.json')
    prev = _read_json_or(path, [])
    try:
        cursos = soc_official.fetch_and_build(data_dir)
    except Exception as exc:
        logger.warning("pipeline: el pla B oficial del SOC també ha fallat: %s (Algolia: %s)", exc, algolia_exc)
        return None
    _write_atomic(cursos, path)
    _soc_history_append(data_dir, _soc_diff_entry(prev, cursos, ok=True, via='oficial'))
    logger.warning("pipeline: SOC refrescat des del fitxer oficial (%d cursos) perquè Algolia ha fallat: %s",
                   len(cursos), algolia_exc)
    return cursos
```

Al bloc `# --- Pla 059: cursos FPO del SOC ...` de `run()`, dins l'`except Exception as exc:`, **afegir com a última línia**
(després de `_notify_admin_soc_failure(_soc_dir, exc)`):

```python
        soc_fallback_official(_soc_dir, exc)
```

**b) `app.py`, `_run_fpo_refresh`.** Al `except Exception as exc:`, **substituir** el bloc actual per (manté l'avís a l'admin i afegeix el pla B):

```python
    except Exception as exc:
        logger.error("refresh-fpo: error: %r", exc)
        try:
            from scrapers.pipeline import _notify_admin_soc_failure
            _notify_admin_soc_failure(data_dir, exc)
        except Exception as notify_exc:
            logger.warning("refresh-fpo: no s'ha pogut avisar l'admin: %s", notify_exc)
        fallback = None
        try:
            from scrapers.pipeline import soc_fallback_official
            fallback = soc_fallback_official(data_dir, exc)
        except Exception as fb_exc:
            logger.warning("refresh-fpo: el pla B oficial ha fallat: %s", fb_exc)
        if fallback is not None:
            _soc_cursos_cache.update(mtime=None, index=None)
            _soc_espec_index_cache.update(key=None, data=None)
            _ext_index_cache.update(key=None, data=None)
            _fpo_refresh_state.update(
                status="done", finished_at=datetime.now(timezone.utc).isoformat(),
                last_error=None, fallback="oficial", cursos=len(fallback),
            )
        else:
            _fpo_refresh_state.update(
                status="error", finished_at=datetime.now(timezone.utc).isoformat(),
                last_error=str(exc),
            )
```
(Just la mateixa estructura `try/except/finally: _fpo_refresh_lock.release()` de la funció; només canvia el cos de l'`except`.)

**b2) `app.py`, `admin_refresh_fpo`.** L'estat `_fpo_refresh_state` és global: sense això, `fallback: "oficial"` es
quedaria enganxat després que Algolia es recuperi. Afegir `fallback=None` a l'`update` que marca l'inici:

`old`:
```
    _fpo_refresh_state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, last_error=None,
    )
```
`new`:
```
    _fpo_refresh_state.update(
        status="running",
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None, last_error=None, fallback=None,
    )
```

**c) `historial.html`.** A `loadFpoHistory`:
`old`: `<td>${e.ok ? 'OK' : ('Error' + (e.error ? ': ' + e.error : ''))}</td>`
`new`: `<td>${e.ok ? 'OK' + (e.via === 'oficial' ? ' (font oficial)' : '') : ('Error' + (e.error ? ': ' + e.error : ''))}</td>`

Executar els tests de la fase i la regressió estàndard: han de **passar**.

### 2.3 Commit
```
git add backend/scrapers/pipeline.py backend/app.py backend/tests/test_soc_fallback.py backend/tests/test_admin_fpo.py frontend/historial.html
git commit -m "feat(soc): si Algolia falla, el refresc usa el fitxer oficial com a pla B"
```

---

## Fase 3 — Verificació amb dades reals (xarxa)

Des de `fp-cercador/backend`, **sense escriure a `data/`**: copiar-hi els snapshots reals a un directori temporal.

```
python3 - <<'EOF'
import shutil, tempfile, collections, json
from scrapers import soc_official
d = tempfile.mkdtemp()
for f in ('soc_cursos.json', 'soc_especs.json'):
    shutil.copy('data/' + f, d)          # requereix haver executat abans un refresc amb Algolia
prev = {c['idCurs'] for c in json.load(open(d + '/soc_cursos.json'))}
out = soc_official.fetch_and_build(d)
print('cursos:', len(out), '| nous respecte del snapshot:', sum(1 for c in out if c['idCurs'] not in prev))
print('estats:', dict(collections.Counter(c['estat'] or '(desconegut)' for c in out)))
print('sense comarca:', sum(1 for c in out if not c['comarca']), '| sense codi d\'especialitat:', sum(1 for c in out if not c['especialitat']['codi']))
EOF
```

**Esperat** (2026-09-25; varia poc): ~800 cursos; 0 sense codi d'especialitat; estats `informacio` (~540), `gestio` (segons el snapshot) i
`(desconegut)` (~130 amb un snapshot d'avui; més si el snapshot és vell). Si dóna menys de 700 cursos o el recompte de "sense codi" és
gran, **aturar-se i informar**: el fitxer oficial o el catàleg han canviat.

**Resultat de la prova en sec (2026-09-25, snapshot de 5 dies + fitxer d'avui, comparat amb Algolia en viu):**
800 cursos (18 de nous respecte del snapshot, 1 omès per especialitat no identificable); estats `informacio` 542,
`gestio` 129, desconegut 129; sobre els 800 cursos comuns amb Algolia: **especialitat 800/800, hores 800/800, modalitat 800/800,
centre 800/800, família 800/800, comarca 799/800, `dataInici` 795/800, `dataFi` 796/800, estats falsos 0**.

**Simulació de fallada d'Algolia (local, opcional):** amb el servidor local, fer que `build_soc_data` llenci (p. ex. `SOC` amb una clau
falsa via un `patch` en una sessió de Python) i comprovar que `POST /api/admin/refresh-fpo` acaba amb `fallback: "oficial"`
a `GET /api/admin/fpo-status`. **No fer aquesta prova a producció.**

## Fora d'abast

- Canviar Algolia per l'oficial com a font principal; usar el conjunt d'especialitats `eed3-6eca` per a l'arrencada en fred.
- Mostrar a la UI un avís "dades reduïdes" (l'historial i l'avís a l'admin ja ho deixen constatat).
- Refrescar centres des d'oficial.
