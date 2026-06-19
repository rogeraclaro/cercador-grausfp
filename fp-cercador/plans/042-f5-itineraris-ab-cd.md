# Pla 042: F5 Itineraris formatius — A→B local + C→D via ciclosFP

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada
> comanda de verificació i confirma el resultat esperat abans de passar al
> pas següent. Si es produeix alguna condició STOP, atura't i reporta —
> no improvisis. Quan acabis, actualitza la fila d'estat d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer)**:
> ```
> git diff --stat c752404..HEAD -- backend/app.py backend/scrapers/certificados_scraper.py backend/scrapers/pipeline.py frontend/index.html frontend/i18n.js
> ```
> Si algun fitxer in-scope ha canviat des que es va escriure el pla,
> compara els excerpts de "Current state" amb el codi viu abans de continuar.
>
> **Nota pre-existent**: `test_db.py::test_schema_version_is_1` falla perquè
> asserta `v == 1` però l'esquema és versió 5. És un bug pre-existent, no
> introduït per aquest pla — ignora'l quan comptis els tests nous.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED (nova ruta + scraper; pipeline s'alenteix ~580 crides extra; no toca dades existents)
- **Depends on**: 041 DONE (spike executat i conclusions documentades)
- **Category**: direction / feature
- **Planned at**: commit `c752404`, 2026-06-19

## Per què importa

La Llei 3/2022 defineix els graus A–E com acumulables: cada mòdul A forma
part d'una unitat B, i cada Certificat de Profesionalidad C (LOE) convalida
un o més cicles D (Grado Mitjà/Superior). Mostrar aquests itineraris és un
diferenciador fort que cap cercador existent mostra bé.

El spike 041 va confirmar:
- **A→B**: derivable 100% localment dels codis en `ofertes.json`, sense API. LOMLOE (5.858 A → 1.003 B via `FAM_A_NNNN_PP → FAM_B_NNNN`) i LOE (2.872 UF A → 1.949 MF B via `UF#### → MF####_N`).
- **C→D**: viable per als 584 C LOE (plan_antiguo=True) via `POST /ciclosFP` del buscadorcertificados, 1 crida REST per certificat. Confirmat: COML0110 (cert_id=308) → ADG_B_3006 / COM_B_3006.
- **B→C LOMLOE** i **D→E**: no viables (sense font oficial). Fora de l'abast d'aquest pla.

## Current state

### Registres a ofertes.json (backend/data/ofertes.json)

```
Total: 12.894 registres
A LOMLOE (FAM_A_NNNN_PP):   5.858  → p.ex. ADG_A_3001_01 "Preparación de los equipos"
A LOE (UF####):              2.872  → p.ex. UF0038 "Aprovisionamiento y organización del off..."
B LOMLOE (FAM_B_NNNN):      1.003  → p.ex. ADG_B_3001 "Tratamiento informático de datos"
B LOE (MF####_N):            1.949  → p.ex. MF0038_3 "Análisis enológico y cata"
C LOE (plan_antiguo=True):     584  → p.ex. ADGG0408, COML0110
C LOMLOE:                      397  → (fora d'abast d'aquest pla)
D:                             195  → sense codigo, té ficha_url
E:                              36  → sense codigo
```

**Relació A→B LOMLOE** (exemple):
```
ADG_A_3001_01 → ADG_B_3001  (fam=ADG, num=3001)
ADG_A_3001_02 → ADG_B_3001
ADG_A_3001_03 → ADG_B_3001
ADG_A_3001_04 → ADG_B_3001
```
Regla: `{FAM}_A_{NNNN}_{PP}` → `{FAM}_B_{NNNN}` (extreure FAM i NNNN del codi A).

**Relació A→B LOE** (exemple):
```
UF0038 → MF0038_3  (num=0038)
```
Regla: `UF{NNNN}` → buscar B amb `codigo` que coincideixi amb `MF{NNNN}_*`.

**C LOE sense cert_id_buscador al fitxer local**: el pipeline enriqueix en memòria
durant el refresh i escriu a `ofertes.json`. El fitxer local de desenvolupament
pot no tenir-ho si no s'ha fet refresh. Al VPS, `cert_id_buscador` és present
després de cada refresh. El pla 042b gestiona això usant `certificados_scraper.fetch_all()`.

### Endpoints del buscadorcertificados (confirmat al spike)

```
BASE = https://www.todofp.es/buscadorcertificados
POST {BASE}/busquedaCP  → HTML amb tots els C LOE (tabla-resultados), inclou cert_id + codigo
POST {BASE}/ciclosFP    → HTML taula: Cicle D | Familia | Mòdul num - Denominació
  payload: certificadoID=<int>, limite=0, paso=10, total=588,
           codigo='', denominacion='', familia=0, nivelFiltro=0, origen=busquedaCP
```

Exemple resposta `ciclosFP` per cert_id=308 (COML0110):
```
Ciclo             | Familia | Mòdul
Servicios Admin.  | ADG     | 3006 - Preparación de pedidos y venta de productos
Servicios Comerc. | COM     | 3006 - Preparación de pedidos y venta de productos
```

### Scraper de referència (backend/scrapers/certificados_scraper.py)

```python
# Bootstrap sessió (línies 34-40):
def _bootstrap_session(timeout: int = 30) -> requests.Session:
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(BASE_CERT_URL + '/buscador', timeout=timeout)
    resp.raise_for_status()
    return session

# fetch_all() retorna {codigo: {'cert_id': int, 'duracion_horas': int|None}}
```

### Endpoint existent de referència (backend/app.py, línies 584–640)

`GET /api/certificado/<codigo>` — crida fichaCP per a un C LOE i retorna `url_boe`.
Segueix el patró: validar `_CODIGO_RE`, llegir `DATA_PATH`, fer POST extern, retornar JSON.

### Pipeline (backend/scrapers/pipeline.py, línies 144–152)

```python
from scrapers.certificados_scraper import fetch_all as fetch_certificados, enrich_record
cert_data = fetch_certificados()
...
enrichment = cert_data.get(record['codigo'])
if enrichment:
    record.update(enrich_record(record, enrichment))
```
→ Aquí és on hem d'afegir el pas de ciclos.

### Frontend — Alpine data (frontend/index.html, línia 1110)

```javascript
async init() {
  const [res, authRes] = await Promise.all([...]);
  const data = await res.json();
  this.allRecords = data.map(r => ({
    ...r,
    familia: FAMILIA_ALIASES[r.familia] ?? r.familia,
    _normDen: ..., _normCod: ...
  }));
  this.families = [...new Set(this.allRecords.map(r => r.familia))].sort();
  this.state = 'ready';
  ...
}
```
→ Després de construir `allRecords`, afegir la construcció de l'índex B.

### Frontend — Patró fetchBoe (frontend/index.html, línia 1428)

```javascript
async fetchBoe(codigo) {
  try {
    const res = await fetch(API_BASE + '/api/certificado/' + codigo);
    const data = await res.json();
    if (data.url_boe) { window.open(data.url_boe, '_blank'); }
    else { alert(t('index.err.boe.missing')); }
  } catch (e) { alert(t('index.err.boe.fetch') + e.message); }
}
```
→ `fetchCiclosD(codigo)` seguirà el mateix patró però mostrarà una llista inline.

### Frontend — Expanded row per a C LOE (frontend/index.html, línies 1651–1660)

```html
<tr x-show="expandedId === row.id && row.grado === 'C' && row.plan_antiguo">
  <td colspan="5" class="detall-certificat">
    <div class="detall-inner">
      <span class="detall-hores" x-show="row.duracion_horas" x-text="row.duracion_horas + ' h.'"></span>
      <a :href="row.url_anexo_pdf" target="_blank" ...>Annexe</a>
      <a :href="row.url_europass_es" ...>Europass ES</a>
      <a :href="row.url_europass_en" ...>Europass EN</a>
      <button @click.stop="fetchBoe(row.codigo)" class="btn-doc">BOE / RD</button>
    </div>
  </td>
</tr>
```

### i18n (frontend/i18n.js, estructura)

Dues seccions: `ca` (catalán, primera) i `es` (español). Cada clau nova ha d'estar
en totes dues. Exemple de clau existent:
```javascript
'index.detall.annexe': 'Annexe PDF',   // CA
'index.detall.annexe': 'Annexo PDF',   // ES
```

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat en cas d'èxit |
|---|---|---|
| Tests | `cd backend && python3 -m pytest tests/ -x -q -k "not test_schema_version"` | tots passes (excl. schema_version pre-existent) |
| Verificar JSON | `python3 -c "import json; d=json.load(open('backend/data/ofertes.json')); print(len(d))"` | `12894` |
| Verificar ciclos JSON | `python3 -c "import json; d=json.load(open('backend/data/ciclos_fp.json')); print(len(d))"` | >0 (es crea al pas de scraping) |

## Àmbit

**In scope** (els únics fitxers que pots crear o modificar):
- `backend/itinerary.py` — crea nou: lògica pura A→B (sense I/O)
- `backend/app.py` — afegeix ruta `GET /api/itinerari`
- `backend/scrapers/certificados_scraper.py` — afegeix `fetch_ciclos_fp()` i `build_ciclos_index()`
- `backend/scrapers/pipeline.py` — integra pas de ciclos
- `backend/data/ciclos_fp.json` — fitxer creat pel pipeline (no en git, com ofertes.json)
- `frontend/index.html` — index B, parentBOf(), ciclosD, UI
- `frontend/i18n.js` — claus noves
- `backend/tests/test_itinerary.py` — crea nou

**Out of scope** (NO tocar):
- `backend/data/ofertes.json` — no modificar l'estructura de registres existents
- Cap altra pàgina de frontend (`alertes.html`, `seguiment.html`, etc.)
- `backend/scrapers/buscador_scraper.py`, `centres_scraper.py` — no tocar
- Qualsevol canvi al backend de login/auth, alertes, centres

## Git workflow

- Branca: `feat/f5-itineraris`
- Commits per fase: `feat(itinerari): A→B index local + endpoint` i `feat(itinerari): C→D via ciclosFP scraper + UI`
- No fer push ni PR tret que el propietari ho demani.

---

## FASE A — A→B derivació local

### Pas A1: Crea `backend/itinerary.py`

Crea el fitxer `backend/itinerary.py` amb la lògica pura (sense I/O, sense xarxa).

```python
"""
itinerary.py — Derivació local d'itineraris A→B a partir dels codis d'ofertes.json.

No fa cap crida de xarxa ni I/O. Rep `records` (la llista d'ofertes.json) i
retorna índexs o resultats puntuals.

Patrons de codi:
  LOMLOE: A = FAM_A_NNNN_PP  →  B = FAM_B_NNNN   (extreure fam+num)
  LOE:    A = UF####          →  B = MF####_N      (extreure num)
"""
import re
from typing import Optional

_PAT_A_LOMLOE = re.compile(r'^([A-Z]+)_A_(\d+)_\d+$')
_PAT_A_LOE    = re.compile(r'^UF(\d+)$')
_PAT_B_LOMLOE = re.compile(r'^([A-Z]+)_B_(\d+)$')
_PAT_B_LOE    = re.compile(r'^MF(\d+)_\d+$')


def build_ab_index(records: list[dict]) -> dict:
    """
    Construeix un índex per derivar A→B i B→[A] localment.

    Retorna:
      {
        'b_by_code':    {codigo_B: record_B},    # LOMLOE: FAM_B_NNNN
        'b_by_uf_num':  {uf_num_str: record_B},  # LOE: '0038' → MF0038_3
        'a_by_b_code':  {codigo_B: [record_A]},  # fills A per B (LOMLOE)
        'a_by_uf_num':  {uf_num_str: [record_A]},# fills A per B (LOE)
      }
    """
    b_by_code: dict   = {}
    b_by_uf_num: dict = {}
    a_by_b_code: dict = {}
    a_by_uf_num: dict = {}

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''

        if grado == 'B':
            m_lomloe = _PAT_B_LOMLOE.match(codigo)
            if m_lomloe:
                b_by_code[codigo] = r
            m_loe = _PAT_B_LOE.match(codigo)
            if m_loe:
                num = m_loe.group(1)
                b_by_uf_num[num] = r

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''

        if grado == 'A':
            m_lomloe = _PAT_A_LOMLOE.match(codigo)
            if m_lomloe:
                b_codigo = f"{m_lomloe.group(1)}_B_{m_lomloe.group(2)}"
                a_by_b_code.setdefault(b_codigo, []).append(r)

            m_loe = _PAT_A_LOE.match(codigo)
            if m_loe:
                num = m_loe.group(1)
                a_by_uf_num.setdefault(num, []).append(r)

    return {
        'b_by_code':   b_by_code,
        'b_by_uf_num': b_by_uf_num,
        'a_by_b_code': a_by_b_code,
        'a_by_uf_num': a_by_uf_num,
    }


def get_parent_b(record: dict, index: dict) -> Optional[dict]:
    """Retorna el registre B pare d'un registre A, o None si no n'hi ha."""
    codigo = record.get('codigo') or ''

    m_lomloe = _PAT_A_LOMLOE.match(codigo)
    if m_lomloe:
        b_codigo = f"{m_lomloe.group(1)}_B_{m_lomloe.group(2)}"
        return index['b_by_code'].get(b_codigo)

    m_loe = _PAT_A_LOE.match(codigo)
    if m_loe:
        return index['b_by_uf_num'].get(m_loe.group(1))

    return None


def get_children_a(record: dict, index: dict) -> list[dict]:
    """Retorna la llista de registres A fills d'un registre B."""
    codigo = record.get('codigo') or ''

    m_lomloe = _PAT_B_LOMLOE.match(codigo)
    if m_lomloe:
        return index['a_by_b_code'].get(codigo, [])

    m_loe = _PAT_B_LOE.match(codigo)
    if m_loe:
        return index['a_by_uf_num'].get(m_loe.group(1), [])

    return []
```

**Verifica**: `python3 -c "import sys; sys.path.insert(0,'backend'); import itinerary; print('OK')"` → `OK`

---

### Pas A2: Afegeix ruta `GET /api/itinerari` a `backend/app.py`

A `backend/app.py`, afegeix l'import d'`itinerary` just sota dels imports existents:

```python
import itinerary
```

(Afegeix-lo al bloc d'imports locals, al costat de `import feed`, `import history`, etc.)

Després, afegeix la ruta just sota de `/api/ficha-redirect` (al voltant de la línia 720):

```python
# ---------------------------------------------------------------------------
# F5 — Itineraris formatius A→B (local)
# ---------------------------------------------------------------------------

_itinerary_index_cache: dict = {"mtime": None, "index": None}


def _get_itinerary_index() -> dict:
    """Retorna l'índex A→B, reconstruint-lo si ofertes.json ha canviat."""
    if not os.path.exists(DATA_PATH):
        return {}
    mtime = os.path.getmtime(DATA_PATH)
    if _itinerary_index_cache["mtime"] == mtime and _itinerary_index_cache["index"]:
        return _itinerary_index_cache["index"]
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            records = json.load(f)
        idx = itinerary.build_ab_index(records)
        _itinerary_index_cache.update(mtime=mtime, index=idx)
        return idx
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("_get_itinerary_index: error: %s", exc)
        return {}


@app.route('/api/itinerari')
def api_itinerari():
    """F5: Retorna l'itinerari local per a un registre A o B.

    GET /api/itinerari?grado=A&codigo=ADG_A_3001_01
      → {"parent_b": {"codigo": "ADG_B_3001", "denominacion": "...", "grado": "B"}}

    GET /api/itinerari?grado=B&codigo=ADG_B_3001
      → {"children_a": [{"codigo": "ADG_A_3001_01", "denominacion": "...", "grado": "A"}, ...]}
    """
    grado = (request.args.get('grado') or '').upper()
    codigo = request.args.get('codigo') or ''

    if grado not in ('A', 'B'):
        return jsonify({'error': 'grado ha de ser A o B'}), 400
    if not codigo:
        return jsonify({'error': 'falta el paràmetre codigo'}), 400

    idx = _get_itinerary_index()
    if not idx:
        return jsonify({'error': 'Dades no disponibles'}), 503

    def _serialize(r):
        return {
            'codigo': r.get('codigo'),
            'denominacion': r.get('denominacion'),
            'grado': r.get('grado'),
            'nivel': r.get('nivel'),
            'familia': r.get('familia'),
        }

    if grado == 'A':
        # Construïm un record mínim per a get_parent_b
        mock_rec = {'grado': 'A', 'codigo': codigo}
        parent = itinerary.get_parent_b(mock_rec, idx)
        return jsonify({'parent_b': _serialize(parent) if parent else None})

    # grado == 'B'
    mock_rec = {'grado': 'B', 'codigo': codigo}
    children = itinerary.get_children_a(mock_rec, idx)
    return jsonify({'children_a': [_serialize(c) for c in children]})
```

**Verifica**: amb el servidor aturat, `python3 -c "
import sys; sys.path.insert(0,'backend')
import os; os.environ['ADMIN_TOKEN']='test'
from app import app
c = app.test_client()
r = c.get('/api/itinerari?grado=A&codigo=ADG_A_3001_01')
import json; d = json.loads(r.data)
assert d.get('parent_b',{}).get('codigo') == 'ADG_B_3001', d
print('OK:', d)
"` → imprimeix `OK: {'parent_b': {'codigo': 'ADG_B_3001', ...}}`

---

### Pas A3: Tests unitaris (`backend/tests/test_itinerary.py`)

Crea `backend/tests/test_itinerary.py` seguint l'estil de `test_api.py` (imports al top, fixtures, classes):

```python
"""
test_itinerary.py — Tests per a itinerary.py (derivació A→B local).
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import itinerary

RECORDS_LOMLOE = [
    {'grado': 'A', 'codigo': 'ADG_A_3001_01', 'denominacion': 'Preparación equipos', 'nivel': 1, 'familia': 'ADG'},
    {'grado': 'A', 'codigo': 'ADG_A_3001_02', 'denominacion': 'Grabación datos',     'nivel': 1, 'familia': 'ADG'},
    {'grado': 'B', 'codigo': 'ADG_B_3001',    'denominacion': 'Tratamiento datos',   'nivel': 2, 'familia': 'ADG'},
    {'grado': 'B', 'codigo': 'COM_B_3001',    'denominacion': 'Comercio básico',     'nivel': 2, 'familia': 'COM'},
]

RECORDS_LOE = [
    {'grado': 'A', 'codigo': 'UF0038', 'denominacion': 'Aprovisionamiento', 'nivel': 1, 'familia': 'AGA'},
    {'grado': 'B', 'codigo': 'MF0038_3', 'denominacion': 'Análisis enológico', 'nivel': 3, 'familia': 'AGA'},
]


def test_build_ab_index_lomloe():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    assert 'ADG_B_3001' in idx['b_by_code']
    assert 'ADG_B_3001' in idx['a_by_b_code']
    assert len(idx['a_by_b_code']['ADG_B_3001']) == 2


def test_get_parent_b_lomloe():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': 'ADG_A_3001_01'}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is not None
    assert parent['codigo'] == 'ADG_B_3001'


def test_get_parent_b_different_fam_returns_none():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': 'INA_A_9999_01'}  # família no existent
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is None


def test_get_children_a_lomloe():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    b_rec = {'grado': 'B', 'codigo': 'ADG_B_3001'}
    children = itinerary.get_children_a(b_rec, idx)
    assert len(children) == 2
    codigos = {c['codigo'] for c in children}
    assert 'ADG_A_3001_01' in codigos
    assert 'ADG_A_3001_02' in codigos


def test_get_children_a_wrong_fam_empty():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    b_rec = {'grado': 'B', 'codigo': 'COM_B_3001'}  # cap A de COM_3001
    children = itinerary.get_children_a(b_rec, idx)
    assert children == []


def test_build_ab_index_loe():
    idx = itinerary.build_ab_index(RECORDS_LOE)
    assert '0038' in idx['b_by_uf_num']
    assert idx['b_by_uf_num']['0038']['codigo'] == 'MF0038_3'


def test_get_parent_b_loe():
    idx = itinerary.build_ab_index(RECORDS_LOE)
    a_rec = {'grado': 'A', 'codigo': 'UF0038'}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is not None
    assert parent['codigo'] == 'MF0038_3'


def test_get_parent_b_invalid_codigo():
    idx = itinerary.build_ab_index(RECORDS_LOMLOE)
    a_rec = {'grado': 'A', 'codigo': None}
    parent = itinerary.get_parent_b(a_rec, idx)
    assert parent is None
```

**Verifica**: `cd backend && python3 -m pytest tests/test_itinerary.py -v` → 8 tests PASSED

---

### Pas A4: Frontend — Índex B i mètode `parentBOf()` a `index.html`

A `frontend/index.html`, dins del bloc `async init()`, **just després** de la línia que construeix `this.families`:
```javascript
this.families = [...new Set(this.allRecords.map(r => r.familia))].sort();
```

Afegeix (mantén la indentació del codi existent):
```javascript
// F5 — Índex B per a derivació A→B local (LOMLOE i LOE)
this._bByCode = {};     // {codigo_B: record} LOMLOE
this._bByUfNum = {};    // {'0038': record}  LOE
for (const r of this.allRecords) {
  if (r.grado === 'B') {
    if (r.codigo) this._bByCode[r.codigo] = r;
    const m = r.codigo && r.codigo.match(/^MF(\d+)_/);
    if (m) this._bByUfNum[m[1]] = r;
  }
}
```

Al bloc de mètodes Alpine (proper a `fetchBoe()`), afegeix:
```javascript
parentBOf(row) {
  if (row.grado !== 'A' || !row.codigo) return null;
  // LOMLOE: ADG_A_3001_01 → ADG_B_3001
  let m = row.codigo.match(/^([A-Z]+)_A_(\d+)_\d+$/);
  if (m) return this._bByCode[`${m[1]}_B_${m[2]}`] || null;
  // LOE: UF0038 → MF0038_*
  m = row.codigo.match(/^UF(\d+)$/);
  if (m) return this._bByUfNum[m[1]] || null;
  return null;
},
```

**No facis cap canvi al HTML de la taula** en aquest pas. Primer verifica el mètode.

**Verifica** (al navegador o amb un test de consola, un cop el servidor corre):
Obre DevTools → Console → `Alpine.$data(document.querySelector('[x-data]')).parentBOf({grado:'A',codigo:'ADG_A_3001_01'})` → ha de retornar un objecte amb `codigo: 'ADG_B_3001'`.

---

### Pas A5: UI — Badge "→ B" a les files Grado A

A la cel·la `<td class="col-nom">` de la taula (prop de la línia 1638 de `frontend/index.html`), **just abans del `</td>` final** de la cel·la de nom, afegeix el badge:

```html
<template x-if="parentBOf(row)">
  <span class="badge-itinerari-b"
    :title="t('index.itinerari.parent_b_title') + (parentBOf(row)||{}).denominacion"
    x-text="'→ ' + ((parentBOf(row)||{}).codigo || '')"></span>
</template>
```

Afegeix el CSS (prop dels estils de `.badge-centres`):
```css
.badge-itinerari-b {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.72em;
  background: #e8f4e8;
  color: #2a6e2a;
  cursor: default;
  vertical-align: middle;
}
```

Afegeix les claus i18n a `frontend/i18n.js` en **les dues seccions** (CA i ES):
```javascript
// Secció CA:
'index.itinerari.parent_b_title': 'Part de la unitat de competència: ',
'index.itinerari.ciclos_d_btn':   'Cicles FP (D)',
'index.itinerari.ciclos_d_cap':   'Cicles formatius que convaliden aquest certificat:',
'index.itinerari.ciclos_d_none':  'No hi ha cicles associats.',
'index.itinerari.ciclos_d_err':   'Error carregant cicles: ',

// Secció ES:
'index.itinerari.parent_b_title': 'Parte de la unidad de competencia: ',
'index.itinerari.ciclos_d_btn':   'Ciclos FP (D)',
'index.itinerari.ciclos_d_cap':   'Ciclos formativos que convalidan este certificado:',
'index.itinerari.ciclos_d_none':  'No hay ciclos asociados.',
'index.itinerari.ciclos_d_err':   'Error cargando ciclos: ',
```

**Verifica**: executa el servidor (`python3 backend/app.py`), obre `http://localhost:5000`, filtra per Grado A → les files A han de mostrar un badge verd petit amb el codi B pare (ex: `→ ADG_B_3001`).

---

## FASE B — C→D via ciclosFP

### Pas B1: Afegeix `fetch_ciclos_fp()` i `build_ciclos_index()` a `certificados_scraper.py`

Al final de `backend/scrapers/certificados_scraper.py`, afegeix:

```python
_CICLOS_PAYLOAD_BASE = {
    'limite': '0', 'paso': '10', 'total': '588',
    'codigo': '', 'denominacion': '', 'familia': '0',
    'nivelFiltro': '0', 'origen': 'busquedaCP',
}


def fetch_ciclos_fp(session: requests.Session, cert_id: int, timeout: int = 20) -> list[dict]:
    """
    POST /ciclosFP per a un cert_id → llista de cicles D que el convaliden.
    Cada cicle: {'denominacion': str, 'familia': str}
    """
    payload = {**_CICLOS_PAYLOAD_BASE, 'certificadoID': str(cert_id)}
    try:
        resp = session.post(BASE_CERT_URL + '/ciclosFP', data=payload, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("fetch_ciclos_fp cert_id=%s: error HTTP: %s", cert_id, exc)
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    ciclos = []
    for row in soup.select('table tr'):
        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
        if len(cells) >= 2 and cells[0] and cells[0] != 'Ciclo formativo':
            ciclos.append({'denominacion': cells[0], 'familia': cells[1] if len(cells) > 1 else ''})
    return ciclos


def build_ciclos_index(cert_data: dict[str, dict]) -> dict[str, list[dict]]:
    """
    Per a cada codi C LOE (clau de cert_data), crida ciclosFP i retorna
    {codigo_C: [{'denominacion': ..., 'familia': ...}]}.

    cert_data: sortida de fetch_all() → {codigo: {'cert_id': int, ...}}
    """
    if not cert_data:
        return {}

    session = _bootstrap_session()
    result = {}
    for codigo, data in cert_data.items():
        cert_id = data.get('cert_id')
        if not cert_id:
            continue
        ciclos = fetch_ciclos_fp(session, cert_id)
        result[codigo] = ciclos
        logger.debug("build_ciclos_index: %s → %d cicles", codigo, len(ciclos))

    logger.info("build_ciclos_index: %d certificats processats", len(result))
    return result
```

**Verifica** (en un entorn amb xarxa):
```python
import sys; sys.path.insert(0,'backend/scrapers')
import certificados_scraper as cs
sess = cs._bootstrap_session()
ciclos = cs.fetch_ciclos_fp(sess, 308)
print(ciclos)
# Esperat: [{'denominacion': 'Servicios Administrativos...', 'familia': 'ADG'}, ...]
```

---

### Pas B2: Integra ciclos al pipeline (`backend/scrapers/pipeline.py`)

Al fitxer `backend/scrapers/pipeline.py`, al bloc on ja es crida `fetch_certificados()` i `enrich_record()` (al voltant de la línia 146), afegeix just **sota** del bucle d'enriquiment:

```python
# --- F5: Ciclos FP (C→D) ---
try:
    from scrapers.certificados_scraper import build_ciclos_index
    ciclos_index = build_ciclos_index(cert_data)
    ciclos_path = os.path.join(os.path.dirname(data_path), 'ciclos_fp.json')
    with open(ciclos_path, 'w', encoding='utf-8') as f:
        import json as _json
        _json.dump(ciclos_index, f, ensure_ascii=False)
    logger.info("pipeline: ciclos_fp.json escrit (%d entrades)", len(ciclos_index))
except Exception as exc:
    logger.warning("pipeline: build_ciclos_index ha fallat (no fatal): %s", exc)
```

`data_path` és la variable local que ja conté el path a `ofertes.json` — comprova el nom exacte al fitxer pipeline.py i adapta-ho. L'error és `no fatal` perquè el cercador ha de continuar funcionant fins i tot si el scraping de ciclos falla.

**Verifica**: executa el pipeline localment (si tens xarxa) i comprova que es crea `backend/data/ciclos_fp.json`. Altrament, verifica que el pipeline no llança cap excepció en la nova ruta de codi.

---

### Pas B3: Endpoint `/api/itinerari` — amplia per a C LOE

Al fitxer `backend/app.py`, a la ruta `/api/itinerari` que has creat al Pas A2, afegeix el suport per a `grado=C`:

1. Afegeix la constant del path al bloc de constants (prop de `DATA_PATH`):
```python
CICLOS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'ciclos_fp.json')
```

2. Afegeix `grado == 'C'` a la validació (canvia `grado not in ('A', 'B')` per `grado not in ('A', 'B', 'C')`).

3. Afegeix la branca al final de la ruta, just abans del `return jsonify(...)` de grado B:

```python
if grado == 'C':
    if not os.path.exists(CICLOS_PATH):
        return jsonify({'ciclos_d': [], 'warning': 'ciclos_fp.json no disponible — cal fer un refresh'}), 200
    try:
        with open(CICLOS_PATH, 'r', encoding='utf-8') as f:
            ciclos_index = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("api_itinerari C: error llegint ciclos_fp.json: %s", exc)
        return jsonify({'error': 'Error llegint dades de cicles'}), 503
    ciclos = ciclos_index.get(codigo, [])
    return jsonify({'ciclos_d': ciclos})
```

**Verifica**: `python3 -c "
import sys; sys.path.insert(0,'backend')
import os; os.environ['ADMIN_TOKEN']='test'
from app import app
c = app.test_client()
r = c.get('/api/itinerari?grado=C&codigo=COML0110')
import json; d = json.loads(r.data)
# Si ciclos_fp.json no existeix al dev, ha de retornar {'ciclos_d':[], 'warning':...} amb 200
assert r.status_code == 200, r.status_code
print('OK:', d)
"`

---

### Pas B4: Frontend — Botó "Cicles FP" a l'expanded row del C LOE

Al bloc de mètodes Alpine (prop de `fetchBoe()`), afegeix:

```javascript
ciclosDData: {},   // {codigo: [{denominacion, familia}] | 'loading' | 'error'}

async fetchCiclosD(codigo) {
  if (this.ciclosDData[codigo] && this.ciclosDData[codigo] !== 'error') return;
  this.ciclosDData = { ...this.ciclosDData, [codigo]: 'loading' };
  try {
    const res = await fetch(API_BASE + '/api/itinerari?grado=C&codigo=' + encodeURIComponent(codigo));
    const data = await res.json();
    this.ciclosDData = { ...this.ciclosDData, [codigo]: data.ciclos_d || [] };
  } catch (e) {
    this.ciclosDData = { ...this.ciclosDData, [codigo]: 'error' };
  }
},
```

**Important**: `ciclosDData: {}` ha d'estar al bloc `data()` d'Alpine (al costat de les altres variables d'estat), no dins del mètode.

A la secció `<div class="detall-inner">` de l'expanded row (Pas A5, línia ~1658 de l'original):

```html
<!-- F5: Cicles D -->
<button @click.stop="fetchCiclosD(row.codigo)" class="btn-doc"
  x-text="t('index.itinerari.ciclos_d_btn')"></button>
<template x-if="ciclosDData[row.codigo] && ciclosDData[row.codigo] !== 'loading'">
  <div class="detall-ciclos-d">
    <template x-if="ciclosDData[row.codigo] === 'error'">
      <span x-text="t('index.itinerari.ciclos_d_err')"></span>
    </template>
    <template x-if="Array.isArray(ciclosDData[row.codigo]) && ciclosDData[row.codigo].length === 0">
      <span x-text="t('index.itinerari.ciclos_d_none')"></span>
    </template>
    <template x-if="Array.isArray(ciclosDData[row.codigo]) && ciclosDData[row.codigo].length > 0">
      <div>
        <span x-text="t('index.itinerari.ciclos_d_cap')"></span>
        <ul class="ciclos-d-list">
          <template x-for="cicle in ciclosDData[row.codigo]" :key="cicle.denominacion">
            <li x-text="cicle.denominacion + (cicle.familia ? ' (' + cicle.familia + ')' : '')"></li>
          </template>
        </ul>
      </div>
    </template>
  </div>
</template>
```

Afegeix CSS (prop dels estils de `.detall-inner`):
```css
.ciclos-d-list {
  margin: 4px 0 0 16px;
  padding: 0;
  font-size: 0.9em;
}
.detall-ciclos-d {
  margin-top: 8px;
  font-size: 0.9em;
}
```

**Verifica**: executa el servidor, filtra per Grado C i pla antic, expandeix una fila → ha d'aparèixer el botó "Cicles FP (D)". Fent clic, si `ciclos_fp.json` existeix, ha de mostrar la llista de cicles. Si no existeix, ha de mostrar el missatge "No hi ha cicles associats."

---

## Test plan

- Fitxer de tests nou: `backend/tests/test_itinerary.py` (ja escrit al Pas A3).
- Tests d'integració a `backend/tests/test_api.py`: afegeix 3 tests per a `/api/itinerari`:
  - `test_itinerari_grado_a_returns_parent_b` — mock `DATA_PATH` amb registres sintètics LOMLOE
  - `test_itinerari_grado_b_returns_children_a`
  - `test_itinerari_grado_invalide_returns_400`

  Segueix l'estil de `test_api.py` (usa `client` fixture, monkeypatch `DATA_PATH`).

- **Comanda de verificació final**: `cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -v -k "not test_schema_version"` → tots passes.

## Criteris de DONE

- [ ] `backend/itinerary.py` existeix i `python3 -c "import itinerary"` des de `backend/` exit 0
- [ ] `cd backend && python3 -m pytest tests/test_itinerary.py -v` → 8 tests PASSED
- [ ] `GET /api/itinerari?grado=A&codigo=ADG_A_3001_01` retorna `{"parent_b": {"codigo": "ADG_B_3001", ...}}`
- [ ] `GET /api/itinerari?grado=B&codigo=ADG_B_3001` retorna `{"children_a": [<llista amb >=4 elements>]}`
- [ ] `GET /api/itinerari?grado=C&codigo=COML0110` retorna 200 (amb ciclos o amb warning si ciclos_fp.json no existeix)
- [ ] `GET /api/itinerari?grado=D&codigo=X` retorna 400
- [ ] Les files Grado A a `index.html` mostren badge verd `→ FAM_B_NNNN` quan `parentBOf(row)` retorna valor
- [ ] L'expanded row del C LOE mostra el botó "Cicles FP (D)" i en fer clic carrega les dades
- [ ] Totes les cadenes de text de la UI usen `t('index.itinerari.*')` i les claus existeixen en CA i ES a `i18n.js`
- [ ] `git diff --name-only` mostra únicament els fitxers in-scope
- [ ] `plans/README.md` actualitzat amb estat DONE per al pla 042

## Condicions STOP

Atura't i reporta (no improvisis) si:

- El codi a les ubicacions de "Current state" no coincideix amb els excerpts (el codebase ha canviat des que es va escriure el pla).
- L'API `/ciclosFP` retorna HTTP 5xx o resposta sense cap `<table>` (el ministeri pot haver canviat el portal).
- El pipeline amb la nova ruta de codi llança una excepció `no fatal` però deixa `ofertes.json` corrupte o buit.
- `parentBOf()` retorna `null` per a **tots** els registres A a la UI (indica que `_bByCode` o `_bByUfNum` no s'ha construït).
- `fetch_ciclos_fp()` retorna llistes buides per a >50% dels cert_ids (pot indicar bloqueig IP o canvi d'endpoint).

## Notes de manteniment

- **Rate limiting**: `build_ciclos_index()` fa ~584 crides HTTP sense delay. Si el ministeri comença a bloquejar, afegir un `time.sleep(0.1)` entre crides. No afegir ara per no complicar el primer MVP.
- **Cache de ciclos_fp.json**: el fitxer es sobreescriu a cada refresh del pipeline. Si el refresh falla a meitat, el fitxer pot quedar incomplet. Considera escriure primer a `ciclos_fp.json.tmp` i fer rename atòmic (`os.replace`).
- **B→C LOE (pla futur)**: el spike va confirmar que és viable via Annexo PDF (pdfplumber, ~579 PDFs). No inclòs en aquest pla per cost alt. El pla 043 (si es crea) hauria de dependre d'aquest DONE.
- **Renovació de `_itinerary_index_cache`**: usa el mateix mecanisme de mtime que `_ofertes_cache` a app.py. Si en el futur `ofertes.json` es refresca molt freqüentment, el rebuild de l'índex (~0.1s per 12k registres) és negligible.
