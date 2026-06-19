# Pla 046: [F5] Índex invers B→C LOE — des d'un Grado B mostrar els Certificats C que l'acrediten

> **Executor instructions**: Segueix el pla pas a pas. Executa cada comanda de
> verificació i confirma el resultat esperat abans de passar al pas següent. Si
> una condició STOP es dispara, atura't i reporta — no improvisis. Quan acabis,
> actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Drift check (executa primer)**:
> ```bash
> git diff --stat 2270a72..HEAD -- backend/itinerary.py backend/app.py backend/tests/test_itinerary.py backend/tests/test_api.py frontend/index.html frontend/i18n.js
> ```
> Si algun fitxer ha canviat, compara els excerpts de "Current state" amb el
> codi viu. Si hi ha desviació, tracta-ho com a condició STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW (les dades ja existeixen; cap nova dependència; canvis localitzats)
- **Depends on**: 045 DONE
- **Category**: direction (F5 itineraris)
- **Planned at**: commit `2270a72`, 2026-06-20

## Per què importa

El pla 045 va afegir que des d'un Certificat C LOE es vegin els Mòduls B LOE que
acredita. Ara cal la direcció inversa: des d'un Mòdul B LOE (codi `MF####_N`) l'usuari
ha de poder saber quins Certificats C LOE el contenen.

Les dades necessàries ja estan a `backend/data/bc_loe.json` (format
`{codigo_c: [uc_codes]}`). Només cal construir l'índex invers en memòria
(`{uc_key: [codigo_c]}`), ampliar l'endpoint `GET /api/itinerari?grado=B` per
retornar `children_c_loe`, i mostrar-ho al frontend quan l'usuari activi el panell
d'un Grado B LOE.

## Current state

### Fitxers rellevants

- `backend/itinerary.py` — `build_ab_index()` retorna índexs A/B. Afegim `c_loe_by_code`.
- `backend/app.py` — `api_itinerari()` grado=B retorna `children_a`. Afegim `children_c_loe`.
  Conté `_itinerary_index_cache` i `_get_itinerary_index()` com a patró de cache.
- `backend/tests/test_itinerary.py` — tests unitaris de `build_ab_index`.
- `backend/tests/test_api.py` — tests d'integració Flask. Patró de mock a `test_itinerari_grado_b_returns_children_a`.
- `frontend/index.html` — Alpine.js; conté `ciclosDData`, `parentBLoeData` com a patró.
- `frontend/i18n.js` — diccionari CA/ES; claus F5 al bloc `/* ── F5 */`.

### `itinerary.py` — `build_ab_index()` actual (línies 1–78)

```python
_PAT_B_LOE_FULL = re.compile(r'^MF(\d{4})_(\d+)$')

def build_ab_index(records: list[dict]) -> dict:
    b_by_code: dict   = {}
    b_by_uf_num: dict = {}
    a_by_b_code: dict = {}
    a_by_uf_num: dict = {}
    b_by_uc: dict = {}

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''
        if grado == 'B':
            ...
            m_loe_full = _PAT_B_LOE_FULL.match(codigo)
            if m_loe_full:
                uc_key = f"UC{m_loe_full.group(1)}_{m_loe_full.group(2)}"
                b_by_uc[uc_key] = r
    ...
    return {
        'b_by_code':   b_by_code,
        'b_by_uf_num': b_by_uf_num,
        'a_by_b_code': a_by_b_code,
        'a_by_uf_num': a_by_uf_num,
        'b_by_uc':     b_by_uc,
    }
```

### `app.py` — patró de cache (línies 722–741)

```python
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
```

Constants rellevants (línies 74–77):
```python
_DATA_DIR   = os.path.join(os.path.dirname(__file__), "data")
CICLOS_PATH = os.path.join(_DATA_DIR, "ciclos_fp.json")
BC_LOE_PATH = os.path.join(_DATA_DIR, "bc_loe.json")
```

### `app.py` — branca `grado == 'B'` de `api_itinerari()` (línies 813–816)

```python
    # grado == 'B'
    mock_rec = {'grado': 'B', 'codigo': codigo}
    children = itinerary.get_children_a(mock_rec, idx)
    return jsonify({'children_a': [_serialize(c) for c in children]})
```

### `app.py` — `_serialize()` (línia 764)

```python
    def _serialize(r):
        return {
            'codigo': r.get('codigo'),
            'denominacion': r.get('denominacion'),
            'grado': r.get('grado'),
            'nivel': r.get('nivel'),
            'familia': r.get('familia'),
        }
```

### `frontend/index.html` — estat Alpine (línies 1128–1130)

```javascript
        // F5 — Itineraris formatius
        ciclosDData: {},   // {codigo: [{denominacion, familia}] | 'loading' | 'error'}
        parentBLoeData: {},     // NOU — parent B LOE per codigo C
```

### `frontend/index.html` — funció `fetchCiclosD()` com a patró (línies 1517–1529)

```javascript
        async fetchCiclosD(codigo) {
          if (this.ciclosDData[codigo] && this.ciclosDData[codigo] !== 'error') return;
          this.ciclosDData = { ...this.ciclosDData, [codigo]: 'loading' };
          try {
            const res = await fetch(API_BASE + '/api/itinerari?grado=C&codigo=' + encodeURIComponent(codigo));
            const data = await res.json();
            this.ciclosDData = { ...this.ciclosDData, [codigo]: data.ciclos_d || [] };
            this.parentBLoeData = { ...this.parentBLoeData, [codigo]: data.parent_b_loe || [] };
          } catch (e) {
            this.ciclosDData = { ...this.ciclosDData, [codigo]: 'error' };
            this.parentBLoeData = { ...this.parentBLoeData, [codigo]: [] };
          }
        },
```

### `frontend/index.html` — badge B pare a les files A (línia 1749–1753, patró de badge)

```html
                  <template x-if="parentBOf(row)">
                    <span class="badge-itinerari-b"
                      :title="t('index.itinerari.parent_b_title') + (parentBOf(row)||{}).denominacion"
                      x-text="'→ ' + ((parentBOf(row)||{}).codigo || '')"></span>
                  </template>
```

### `frontend/index.html` — expanded row C LOE (línia 1760, patró de fila expandida)

```html
              <tr x-show="expandedId === row.id && row.grado === 'C' && row.plan_antiguo">
                <td colspan="5" class="detall-certificat">
                  <div class="detall-inner">
                    ...botons i llistes...
                  </div>
                </td>
              </tr>
```

La fila expandida B LOE seguirà el mateix patró: `<tr x-show="childrenCLoeVisible[row.id]">`.

### `frontend/i18n.js` — claus F5 existents (línies 124–129 CA, 390–395 ES)

```javascript
// CA (bloc ca):
'index.itinerari.ciclos_d_none':  'No hi ha cicles associats.',
'index.itinerari.ciclos_d_err':   'Error carregant cicles: ',
'index.itinerari.parent_b_loe_cap': 'Mòduls B (LOE) acreditats per aquest certificat:',

// ES (bloc es):
'index.itinerari.ciclos_d_none':  'No hay ciclos asociados.',
'index.itinerari.ciclos_d_err':   'Error cargando ciclos: ',
'index.itinerari.parent_b_loe_cap': 'Módulos B (LOE) acreditados por este certificado:',
```

### `backend/tests/test_api.py` — patró de test B existent (línies 213–227)

```python
def test_itinerari_grado_b_returns_children_a(client, monkeypatch):
    """F5: GET /api/itinerari?grado=B retorna la llista de fills A."""
    import app as flask_app_module
    monkeypatch.setattr(flask_app_module, "_itinerary_index_cache", {"mtime": None, "index": None})
    with mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch("app.os.path.getmtime", return_value=42.0), \
         mock.patch("builtins.open", mock.mock_open(read_data=_FAKE_OFERTES_ITINERARI)):
        r = client.get("/api/itinerari?grado=B&codigo=ADG_B_3001")
    assert r.status_code == 200
    data = r.get_json()
    assert "children_a" in data
```

**Important**: `ADG_B_3001` és LOMLOE (no coincideix amb `^MF\d{4}_\d+$`), de manera que
el codi nou de `children_c_loe` no s'activa per a aquest test i no cal modificar-lo.

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat en cas d'èxit |
|---|---|---|
| Tests filtrats | `cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -q` | tots passen |
| Suite completa | `cd backend && python3 -m pytest tests/ -q` | exit 0, cap regressió |

## Àmbit

**In scope** (els ÚNICS fitxers que has de modificar):
- `backend/itinerary.py` — afegir `c_loe_by_code` a `build_ab_index()`
- `backend/app.py` — afegir `_bc_loe_inverse_cache`, `_get_bc_loe_inverse()`, ampliar grado=B
- `backend/tests/test_itinerary.py` — 1 test nou per `c_loe_by_code`
- `backend/tests/test_api.py` — 1 test nou per grado=B LOE → children_c_loe
- `frontend/index.html` — `childrenCLoeData`, `childrenCLoeVisible`, `fetchChildrenCLoe()`, badge i expanded row
- `frontend/i18n.js` — claus `children_c_loe_*` (CA + ES)
- `plans/README.md` — actualitzar estat pla 046

**Out of scope** (NO tocar):
- `backend/data/bc_loe.json` — fitxer de dades generat; no el commitis mai.
- `backend/scrapers/` — res a canviar aquí.
- `scripts/generate_bc_loe.py` — ja complet.
- `backend/tests/test_api.py::test_itinerari_grado_b_returns_children_a` — **NO el modifiquis**;
  el codi nou no l'afecta perquè `ADG_B_3001` no és B LOE.

## Git workflow

- Branca: `feat/046-b-children-c-loe`
- Estil de commit: `feat(f5): ...` (convencional, com els commits recents)
- Un commit al final o per etapa lògica (backend / frontend).
- NO fas push ni PR.

---

## Pas 1: Afegir `c_loe_by_code` a `build_ab_index()` en `itinerary.py`

### 1a. Afegir la inicialització del dict (just a continuació de `b_by_uc: dict = {}`, línia ~37)

```python
    b_by_uc: dict = {}
    c_loe_by_code: dict = {}   # NOU
```

### 1b. Omplir `c_loe_by_code` dins del primer bucle `for r in records`

Afegeix un nou bloc `if grado == 'C':` **just a continuació** del bloc `if grado == 'B':` existent
(no dins d'ell — són blocs al mateix nivell):

```python
        if grado == 'C' and r.get('plan_antiguo') and codigo:
            c_loe_by_code[codigo] = r
```

### 1c. Afegir `c_loe_by_code` al dict retornat

```python
    return {
        'b_by_code':      b_by_code,
        'b_by_uf_num':    b_by_uf_num,
        'a_by_b_code':    a_by_b_code,
        'a_by_uf_num':    a_by_uf_num,
        'b_by_uc':        b_by_uc,
        'c_loe_by_code':  c_loe_by_code,   # NOU
    }
```

**Verifica** (sense xarxa):
```bash
cd backend && python3 -c "
import json, itinerary
recs = json.load(open('data/ofertes.json'))
idx = itinerary.build_ab_index(recs)
print('c_loe_by_code count:', len(idx['c_loe_by_code']))
assert 'c_loe_by_code' in idx
assert len(idx['c_loe_by_code']) > 0, 'Ha de tenir entrades C LOE'
print('OK')
"
```
Esperat: `c_loe_by_code count: 584` (o proper a 584) i `OK`.

---

## Pas 2: Afegir `_bc_loe_inverse_cache` i `_get_bc_loe_inverse()` a `app.py`

Afegeix immediatament **a continuació de `_get_itinerary_index()`** (aprox. línia 741,
just abans del comentari de la secció següent):

```python
_bc_loe_inverse_cache: dict = {"mtime": None, "index": None}


def _get_bc_loe_inverse() -> dict:
    """
    Retorna l'índex invers de bc_loe.json: {uc_key: [codigo_c]}.
    Cache invalidat per mtime. Retorna {} si bc_loe.json no existeix.
    """
    if not os.path.exists(BC_LOE_PATH):
        return {}
    mtime = os.path.getmtime(BC_LOE_PATH)
    if _bc_loe_inverse_cache["mtime"] == mtime and _bc_loe_inverse_cache["index"] is not None:
        return _bc_loe_inverse_cache["index"]
    try:
        with open(BC_LOE_PATH, 'r', encoding='utf-8') as f:
            bc_loe = json.load(f)
        inverse: dict = {}
        for codigo_c, uc_codes in bc_loe.items():
            for uc in uc_codes:
                inverse.setdefault(uc, []).append(codigo_c)
        _bc_loe_inverse_cache.update(mtime=mtime, index=inverse)
        return inverse
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_bc_loe_inverse: error llegint bc_loe.json: %s", exc)
        return {}
```

**Verifica** (necessita `backend/data/bc_loe.json` al servidor o en local):
```bash
cd backend && python3 -c "
import os, json
os.environ['FLASK_ENV'] = 'testing'
import app
inv = app._get_bc_loe_inverse()
print('Inverse keys sample:', list(inv.keys())[:3])
assert len(inv) > 0, 'Ha de tenir entrades'
print('OK')
" 2>/dev/null || echo "bc_loe.json no disponible localment — OK (es prova als tests)"
```

---

## Pas 3: Ampliar la branca `grado == 'B'` de `api_itinerari()` a `app.py`

Substitueix el bloc `# grado == 'B'` existent (línies 813–816 aprox.) per:

```python
    # grado == 'B'
    mock_rec = {'grado': 'B', 'codigo': codigo}
    children = itinerary.get_children_a(mock_rec, idx)
    response: dict = {'children_a': [_serialize(c) for c in children]}

    # B→C LOE: certificats C que contenen aquest mòdul B (només per a B LOE: MF####_N)
    import re as _re_itinerari
    _m_b_loe = _re_itinerari.match(r'^MF(\d{4})_(\d+)$', codigo)
    if _m_b_loe:
        uc_key = f"UC{_m_b_loe.group(1)}_{_m_b_loe.group(2)}"
        inverse = _get_bc_loe_inverse()
        c_codigos = inverse.get(uc_key, [])
        c_loe_by_code = idx.get('c_loe_by_code', {})
        children_c_loe = []
        for cc in c_codigos:
            c_rec = c_loe_by_code.get(cc)
            if c_rec:
                children_c_loe.append(_serialize(c_rec))
        response['children_c_loe'] = children_c_loe
    else:
        response['children_c_loe'] = []

    return jsonify(response)
```

Notes d'implementació:
- `import re as _re_itinerari` és un import dins de la funció (evita contaminar el namespace
  del mòdul; `re` ja és importat en altres parts d'`app.py` si cal, però aquí és local per
  seguretat). Si `re` ja és importat al top del fitxer, usa el nom existent en lloc d'aquest.
- `response['children_c_loe'] = []` per a B LOMLOE (no B LOE) garanteix que la clau sempre
  existeix a la resposta, el frontend no ha de comprovar `if 'children_c_loe' in data`.

**Nota sobre `import re`**: Abans d'afegir `import re as _re_itinerari`, comprova si `re`
ja és importat al top d'`app.py` (`grep -n "^import re" backend/app.py`). Si ja hi és,
usa directament `re.match(...)` en lloc del nom local.

**Verifica** (en local amb test_client — no necessita bc_loe.json):
```bash
cd backend && python3 -c "
import os, json
os.environ['FLASK_ENV'] = 'testing'
import app
client = app.app.test_client()
# Prova LOMLOE B: ha de tenir children_c_loe=[]
import unittest.mock as mock
with mock.patch('app.os.path.exists', return_value=False):
    r = client.get('/api/itinerari?grado=B&codigo=ADG_B_3001')
data = json.loads(r.data)
print('LOMLOE B keys:', list(data.keys()))
assert 'children_c_loe' in data
assert data['children_c_loe'] == []
print('OK LOMLOE B')
"
```
Esperat: `LOMLOE B keys: ['children_a', 'children_c_loe']` i `OK LOMLOE B`.

---

## Pas 4: Tests — `test_itinerary.py` i `test_api.py`

### 4a. `backend/tests/test_itinerary.py` — 1 test nou per `c_loe_by_code`

Afegeix al **final** del fitxer (a continuació dels tests `b_by_uc` existents):

```python
RECORDS_C_LOE = [
    {'grado': 'C', 'codigo': 'COML0110', 'denominacion': 'Gestió comptable', 'nivel': 2,
     'familia': 'COM', 'plan_antiguo': True},
    {'grado': 'C', 'codigo': 'ADGG0408', 'denominacion': 'Gestió comptable avançada', 'nivel': 3,
     'familia': 'ADG', 'plan_antiguo': True},
    {'grado': 'C', 'codigo': 'FAKELOMLOE', 'denominacion': 'LOMLOE cert', 'nivel': 2,
     'familia': 'ADG', 'plan_antiguo': False},  # NO ha d'aparèixer
]


def test_build_ab_index_c_loe_by_code():
    idx = itinerary.build_ab_index(RECORDS_C_LOE)
    assert 'c_loe_by_code' in idx
    assert 'COML0110' in idx['c_loe_by_code']
    assert 'ADGG0408' in idx['c_loe_by_code']
    # C LOMLOE (plan_antiguo=False) NO ha d'estar a l'índex
    assert 'FAKELOMLOE' not in idx['c_loe_by_code']
```

### 4b. `backend/tests/test_api.py` — 1 test nou per grado=B LOE → children_c_loe

Afegeix a continuació del test `test_itinerari_grado_b_returns_children_a` (línia ~227):

```python
_FAKE_BC_LOE_B = '{"COML0110": ["UC0969_1", "UC0970_1"], "ADGG0408": ["UC0969_1"]}'
_FAKE_OFERTES_ITINERARI_B_LOE = (
    '[{"grado":"B","codigo":"MF0969_1","denominacion":"Gestió comptable","nivel":1,"familia":"ADG"},'
    '{"grado":"C","codigo":"COML0110","denominacion":"Gestió comptable i fiscal","nivel":2,"familia":"COM","plan_antiguo":true},'
    '{"grado":"C","codigo":"ADGG0408","denominacion":"Gestió comptable avançada","nivel":3,"familia":"ADG","plan_antiguo":true}]'
)


def test_itinerari_grado_b_loe_retorna_children_c_loe(client, monkeypatch):
    """F5: GET /api/itinerari?grado=B&codigo=MF0969_1 retorna children_c_loe."""
    import app as flask_app_module
    monkeypatch.setattr(flask_app_module, "_itinerary_index_cache", {"mtime": None, "index": None})
    monkeypatch.setattr(flask_app_module, "_bc_loe_inverse_cache", {"mtime": None, "index": None})

    def _fake_open(path, *args, **kwargs):
        import builtins
        path_str = str(path)
        if 'bc_loe' in path_str:
            return mock.mock_open(read_data=_FAKE_BC_LOE_B)()
        if 'ofertes' in path_str:
            return mock.mock_open(read_data=_FAKE_OFERTES_ITINERARI_B_LOE)()
        return builtins.open(path, *args, **kwargs)

    with mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch("app.os.path.getmtime", return_value=42.0), \
         mock.patch("builtins.open", side_effect=_fake_open):
        r = client.get("/api/itinerari?grado=B&codigo=MF0969_1")

    assert r.status_code == 200
    data = r.get_json()
    assert "children_a" in data
    assert "children_c_loe" in data
    codigos_c = {c["codigo"] for c in data["children_c_loe"]}
    assert "COML0110" in codigos_c
    assert "ADGG0408" in codigos_c
```

**Verifica**:
```bash
cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -q
```
Esperat: tots els tests passen, incloent el nou `test_build_ab_index_c_loe_by_code`
i `test_itinerari_grado_b_loe_retorna_children_c_loe`. El test existent
`test_itinerari_grado_b_returns_children_a` ha de continuar passant sense canvis.

**Verifica suite completa**:
```bash
cd backend && python3 -m pytest tests/ -q
```
Esperat: exit 0, cap regressió (2 fallides pre-existents a `test_db.py` són normals).

---

## Pas 5: Frontend — `index.html` i `i18n.js`

### 5a. Afegir `childrenCLoeData` i `childrenCLoeVisible` a l'estat Alpine

Cerca el bloc (línia ~1128):
```javascript
        // F5 — Itineraris formatius
        ciclosDData: {},   // {codigo: [{denominacion, familia}] | 'loading' | 'error'}
        parentBLoeData: {},     // NOU — parent B LOE per codigo C
```

Afegeix les dues noves propietats just a continuació:
```javascript
        ciclosDData: {},
        parentBLoeData: {},
        childrenCLoeData: {},    // {row.id: [{codigo, denominacion}] | 'loading' | 'error'}
        childrenCLoeVisible: {}, // {row.id: bool}
```

### 5b. Afegir la funció `fetchChildrenCLoe()` just a continuació de `fetchCiclosD()`

Localitza el tancament de `fetchCiclosD` (la `},` al voltant de la línia 1529) i
afegeix immediatament a continuació:

```javascript
        async fetchChildrenCLoe(row) {
          // Toggle: si ja és visible i carregat, amaga'l
          if (this.childrenCLoeVisible[row.id] && this.childrenCLoeData[row.id] !== undefined) {
            this.childrenCLoeVisible = { ...this.childrenCLoeVisible, [row.id]: false };
            return;
          }
          this.childrenCLoeVisible = { ...this.childrenCLoeVisible, [row.id]: true };
          if (this.childrenCLoeData[row.id] !== undefined) return; // ja carregat
          this.childrenCLoeData = { ...this.childrenCLoeData, [row.id]: 'loading' };
          try {
            const res = await fetch(API_BASE + '/api/itinerari?grado=B&codigo=' + encodeURIComponent(row.codigo));
            const data = await res.json();
            this.childrenCLoeData = { ...this.childrenCLoeData, [row.id]: data.children_c_loe || [] };
          } catch (e) {
            this.childrenCLoeData = { ...this.childrenCLoeData, [row.id]: 'error' };
          }
        },
```

### 5c. Afegir badge "Cert. C" a les files B LOE

Localitza el bloc del badge `parentBOf(row)` (línia ~1749):
```html
                  <template x-if="parentBOf(row)">
                    <span class="badge-itinerari-b"
                      :title="t('index.itinerari.parent_b_title') + (parentBOf(row)||{}).denominacion"
                      x-text="'→ ' + ((parentBOf(row)||{}).codigo || '')"></span>
                  </template>
```

Afegeix **a continuació** d'aquest bloc:
```html
                  <template x-if="row.grado === 'B' && row.codigo && /^MF\d{4}_\d+$/.test(row.codigo)">
                    <span class="badge-itinerari-b" style="cursor:pointer"
                      @click.stop="fetchChildrenCLoe(row)"
                      x-text="t('index.itinerari.children_c_loe_btn')"></span>
                  </template>
```

### 5d. Afegir la fila expandida per a B LOE

Localitza la fila expandida de C LOE (línia ~1760):
```html
              <tr x-show="expandedId === row.id && row.grado === 'C' && row.plan_antiguo">
                <td colspan="5" class="detall-certificat">
                  ...
                </td>
              </tr>
```

Afegeix una nova `<tr>` **a continuació** del tancament `</tr>` d'aquella fila:
```html
              <!-- B→C LOE: certificats C que acrediten aquest mòdul B -->
              <tr x-show="childrenCLoeVisible[row.id] && row.grado === 'B'">
                <td colspan="5" class="detall-certificat">
                  <div class="detall-inner">
                    <template x-if="childrenCLoeData[row.id] === 'loading'">
                      <span x-text="t('index.itinerari.children_c_loe_loading')"></span>
                    </template>
                    <template x-if="childrenCLoeData[row.id] === 'error'">
                      <span x-text="t('index.itinerari.children_c_loe_err')"></span>
                    </template>
                    <template x-if="Array.isArray(childrenCLoeData[row.id]) && childrenCLoeData[row.id].length === 0">
                      <span x-text="t('index.itinerari.children_c_loe_none')"></span>
                    </template>
                    <template x-if="Array.isArray(childrenCLoeData[row.id]) && childrenCLoeData[row.id].length > 0">
                      <div>
                        <span x-text="t('index.itinerari.children_c_loe_cap')"></span>
                        <ul class="ciclos-d-list">
                          <template x-for="cert in childrenCLoeData[row.id]" :key="cert.codigo">
                            <li x-text="cert.codigo + ' — ' + cert.denominacion"></li>
                          </template>
                        </ul>
                      </div>
                    </template>
                  </div>
                </td>
              </tr>
```

### 5e. Afegir claus i18n a `frontend/i18n.js`

**Bloc CA** (just a continuació de la línia `'index.itinerari.parent_b_loe_cap': ...`, línia ~129):
```javascript
      'index.itinerari.children_c_loe_btn':     'Cert. C',
      'index.itinerari.children_c_loe_cap':     'Certificats C que acrediten aquest mòdul:',
      'index.itinerari.children_c_loe_none':    'Cap certificat C associat.',
      'index.itinerari.children_c_loe_err':     'Error carregant certificats C.',
      'index.itinerari.children_c_loe_loading': 'Carregant...',
```

**Bloc ES** (just a continuació de la línia `'index.itinerari.parent_b_loe_cap': ...`, línia ~395):
```javascript
      'index.itinerari.children_c_loe_btn':     'Cert. C',
      'index.itinerari.children_c_loe_cap':     'Certificados C que acreditan este módulo:',
      'index.itinerari.children_c_loe_none':    'Ningún certificado C asociado.',
      'index.itinerari.children_c_loe_err':     'Error cargando certificados C.',
      'index.itinerari.children_c_loe_loading': 'Cargando...',
```

---

## Test plan

### Tests unitaris — `test_itinerary.py`

Un test nou (pas 4a):
- `test_build_ab_index_c_loe_by_code` — verifica que `c_loe_by_code` existeix, conté
  els C LOE (`plan_antiguo=True`) i exclou els C LOMLOE (`plan_antiguo=False`).

### Tests d'integració — `test_api.py`

Un test nou (pas 4b):
- `test_itinerari_grado_b_loe_retorna_children_c_loe` — verifica que grado=B amb un
  codi MF retorna `children_c_loe` amb els C correctes, usant mock de `bc_loe.json`
  i `ofertes.json`.

**Comanda de verificació final**:
```bash
cd backend && python3 -m pytest tests/ -q
```
→ exit 0, sense regressions. El nombre de tests ha d'incrementar en 2.

---

## Criteris de DONE

- [ ] `cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -q` → exit 0, 2 nous tests passant
- [ ] `cd backend && python3 -m pytest tests/ -q` → exit 0, cap regressió
- [ ] `GET /api/itinerari?grado=B&codigo=MF0969_1` retorna `children_c_loe` (array, pot ser buit si bc_loe.json no té el codi)
- [ ] `GET /api/itinerari?grado=B&codigo=ADG_B_3001` retorna `children_c_loe: []` (B LOMLOE)
- [ ] Al frontend, els files de Grado B LOE (codi MF####_N) mostren el badge "Cert. C"
- [ ] Clicar el badge carrega i mostra la llista de C LOE al panell expandit
- [ ] Clicar de nou amaga el panell (toggle)
- [ ] Les files B LOMLOE (codi FAM_B_NNNN) NO mostren el badge "Cert. C"
- [ ] Cap fitxer fora de la llista "In scope" modificat (`git diff --name-only`)
- [ ] `plans/README.md` actualitzat amb estat `DONE` per al pla 046

---

## Condicions STOP

Atura't i reporta (no improvisis) si:

- **Drift**: algun fitxer de l'àmbit ha canviat des de `2270a72` i el codi no
  coincideix amb els excerpts de "Current state".
- **`re` ja importat a app.py amb un altre nom**: comprova amb
  `grep -n "^import re\|^from re" backend/app.py` i adapta l'ús del mòdul.
- **El test `test_itinerari_grado_b_returns_children_a` falla** després dels teus
  canvis: el codi nou no hauria d'afectar-lo (ADG_B_3001 no és B LOE). Si falla,
  és una regressió — atura't.
- **El mock de `builtins.open` al pas 4b llença excepcions inesperades**: usa
  `logger.debug(f"open: {path}")` temporal per veure quins paths s'obren i
  ajusta el `side_effect`.
- **Al frontend, el badge "Cert. C" apareix en files B LOMLOE** (codi `FAM_B_NNNN`):
  la regex `/^MF\d{4}_\d+$/` no hauria de coincidir — revisa-la.

---

## Notes de manteniment

- **Sincronització amb bc_loe.json**: si es re-executa `generate_bc_loe.py` al VPS,
  la cache `_bc_loe_inverse_cache` s'invalida automàticament per mtime en la propera
  petició. Cap reinici necessari.
- **B LOMLOE**: els mòduls B LOMLOE (FAM_B_NNNN) no tindran mai `children_c_loe`
  perquè no hi ha dades (veure spike 043). Retornen `[]` per disseny.
- **Rendiment**: `_get_bc_loe_inverse()` carrega 37 KB i construeix l'invers una sola
  vegada (cache mtime). Cost negligible.
- **Revisar en PR**: que el toggle de `childrenCLoeVisible` funcioni correctament si
  l'usuari obre i tanca el panell repetidament; que `children_c_loe` sempre estigui
  present a la resposta grado=B (fins i tot `[]`).
