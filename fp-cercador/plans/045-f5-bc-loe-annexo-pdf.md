# Pla 045: [F5] B→C LOE — índex UC codes (Annexo PDF) + endpoint + UI

> **Executor instructions**: Segueix el pla pas a pas. Executa cada comanda de
> verificació i confirma el resultat esperat abans de passar al pas següent. Si
> una condició STOP es dispara, atura't i reporta — no improvisis. Quan acabis,
> actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Drift check (executa primer)**:
> ```bash
> git diff --stat 5acb252..HEAD -- backend/scrapers/certificados_scraper.py backend/itinerary.py backend/app.py backend/tests/test_itinerary.py backend/tests/test_api.py requirements.txt
> ```
> Si algun fitxer ha canviat, compara els excerpts de "Current state" amb el
> codi viu. Si hi ha desviació, tracta-ho com a condició STOP.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED (descàrrega de 584 PDFs, 6 min; codi de xarxa nou; canvis a UI Alpine)
- **Depends on**: 044 DONE, 042 DONE
- **Category**: direction (F5 itineraris)
- **Planned at**: commit `5acb252`, 2026-06-19

## Per què importa

El spike 043 va confirmar que l'Annexo PDF de cada Certificat de Profesionalitat
C LOE (584 registres `plan_antiguo=True`) conté els codis UC/MF que identifiquen
els mòduls formatius B LOE que acredita. Amb 3/3 PDFs mostrejats extrets
correctament (famílies ADG, AFD, AGA) via pdfplumber, la relació B→C LOE és
tècnicament viable.

Sense aquest pla, un usuari que busca un mòdul B LOE (ex: `MF0969_1`) no sap
quins certificats C li acrediten. La implementació completa l'itinerari
A→B→C→D (la relació C→D ja funciona des del pla 042+044).

## Current state

### Fitxers rellevants

- `backend/scrapers/certificados_scraper.py` — conté `fetch_all()`, `enrich_record()`,
  `build_ciclos_index()`. Afegim `fetch_uc_codes_from_pdf()` aquí.
- `backend/itinerary.py` — conté `build_ab_index()`. Afegim el sub-índex `b_by_uc`.
- `backend/app.py` — conté `api_itinerari()`. Ampliem la branca `grado == 'C'`.
- `backend/tests/test_itinerary.py` — tests unitaris del mòdul itinerary.
- `backend/tests/test_api.py` — tests d'integració de Flask.
- `requirements.txt` — **pdfplumber NO hi és** (es va eliminar al pla 003).

### `certificados_scraper.py` — constants rellevants (línies 20–31)

```python
BASE_CERT_URL = 'https://www.todofp.es/buscadorcertificados'
BASE_DAM = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': BASE_CERT_URL + '/buscador',
}
```

URL del PDF d'un certificat: `f"{BASE_DAM}/anexos/{codigo_c.lower()}.pdf"`
Exemple: `https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/coml0110.pdf`

### `itinerary.py` — `build_ab_index()` actual (línies 20–70)

```python
_PAT_B_LOE = re.compile(r'^MF(\d+)_\d+$')

def build_ab_index(records: list[dict]) -> dict:
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
    ...
    return {
        'b_by_code':   b_by_code,
        'b_by_uf_num': b_by_uf_num,
        'a_by_b_code': a_by_b_code,
        'a_by_uf_num': a_by_uf_num,
    }
```

### `app.py` — branca `grado == 'C'` de `api_itinerari()` (approx. línies 27100–27130)

```python
if grado == 'C':
    if not os.path.exists(CICLOS_PATH):
        return jsonify({'ciclos_d': [], 'warning': '...'}), 200
    try:
        with open(CICLOS_PATH, 'r', encoding='utf-8') as f:
            ciclos_index = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("api_itinerari C: error llegint ciclos_fp.json: %s", exc)
        return jsonify({'error': 'Error llegint dades de cicles'}), 503
    ciclos = ciclos_index.get(codigo, [])
    return jsonify({'ciclos_d': ciclos})
```

Constants rellevants a `app.py`:

```python
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CICLOS_PATH = os.path.join(_DATA_DIR, "ciclos_fp.json")
```

### `app.py` — `_get_itinerary_index()` (funciona com a cache per `ofertes.json`)

```python
_itinerary_index_cache: dict = {"mtime": None, "index": None}

def _get_itinerary_index() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    mtime = os.path.getmtime(DATA_PATH)
    if _itinerary_index_cache["mtime"] == mtime and _itinerary_index_cache["index"]:
        return _itinerary_index_cache["index"]
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        records = json.load(f)
    idx = itinerary.build_ab_index(records)
    _itinerary_index_cache.update(mtime=mtime, index=idx)
    return idx
```

### Frontend — `fetchCiclosD()` actual a `frontend/index.html` (aprox. línia 38530)

```javascript
async fetchCiclosD(codigo) {
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

### Frontend — rendering de cicles D (aprox. línia 52060)

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
            <li>
              <template x-if="cicle.ficha_url">
                <a :href="cicle.ficha_url" target="_blank" rel="noopener"
                   x-text="cicle.denominacion + (cicle.familia ? ' (' + cicle.familia + ')' : '')"></a>
              </template>
              <template x-if="!cicle.ficha_url">
                <span x-text="cicle.denominacion + (cicle.familia ? ' (' + cicle.familia + ')' : '')"></span>
              </template>
            </li>
          </template>
        </ul>
      </div>
    </template>
  </div>
</template>
```

### i18n.js — claus F5 existents (aprox. línia on comença el bloc F5)

```javascript
/* ── F5: Itineraris formatius ── */
'index.itinerari.parent_b_title': 'Part de la unitat de competència: ',
'index.itinerari.ciclos_d_btn':   'Cicles FP (D)',
'index.itinerari.ciclos_d_cap':   'Cicles formatius que convaliden aquest certificat:',
'index.itinerari.ciclos_d_none':  'No hi ha cicles associats.',
'index.itinerari.ciclos_d_err':   'Error carregant cicles: ',
```

### Dades

- `backend/data/` és **gitignored** — tot el que s'hi generi s'ha de regenerar al servidor.
- `bc_loe.json` es crea a `backend/data/bc_loe.json` (gitignored automàticament).
- 584 registres C LOE (`plan_antiguo=True`). Cost estimat de generació: ~6 min.
- El camp `cert_id_buscador` dels registres C a `ofertes.json` **pot ser `None`** si
  l'enriquiment no ha corregut. Però la URL del PDF és determinista:
  `{BASE_DAM}/anexos/{codigo.lower()}.pdf`. No depèn d'enriquiment.

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat en cas d'èxit |
|---|---|---|
| Instal·lar deps | `pip install pdfplumber` | exit 0 |
| Verificar pdfplumber | `python3 -c "import pdfplumber; print('ok')"` | `ok` |
| Tests backend | `cd backend && python3 -m pytest tests/ -q` | tots passen |
| Tests filtrats | `cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -q` | tots passen |
| Generar bc_loe.json | `python3 scripts/generate_bc_loe.py` | `bc_loe.json escrit:` al final |
| Verificar bc_loe | `python3 -c "import json; d=json.load(open('backend/data/bc_loe.json')); print(len(d), 'entrades')"` | ≥500 entrades |

## Àmbit

**In scope** (els ÚNICS fitxers que has de modificar o crear):
- `requirements.txt` — afegir `pdfplumber`
- `backend/scrapers/certificados_scraper.py` — afegir `fetch_uc_codes_from_pdf()`
- `scripts/generate_bc_loe.py` — crear script de generació per lots
- `backend/itinerary.py` — afegir `_PAT_B_LOE_FULL` i `b_by_uc` a `build_ab_index()`
- `backend/app.py` — afegir `BC_LOE_PATH` i ampliar `api_itinerari` grado=C
- `backend/tests/test_itinerary.py` — afegir tests per `b_by_uc`
- `backend/tests/test_api.py` — afegir test per `parent_b_loe` a grado=C
- `frontend/index.html` — afegir `parentBLoeData`, actualitzar `fetchCiclosD()`, afegir template
- `frontend/i18n.js` — afegir claus `parent_b_loe_*`
- `plans/README.md` — actualitzar estat pla 045

**Out of scope** (NO tocar):
- `backend/scrapers/pipeline.py` — NO integrar la generació de `bc_loe.json` al pipeline
  principal. Afegir 6 min al refresh diari és massa. El script `generate_bc_loe.py`
  és l'únic mecanisme de generació per ara.
- `backend/data/bc_loe.json` — fitxer generat (no és codi); NO el commitis.
- `backend/data/ofertes.json` — no modificar mai.
- Cap fitxer de `backend/tests/` que no sigui `test_itinerary.py` o `test_api.py`.
- Cap altra pàgina HTML que no sigui `index.html`.

## Git workflow

- Branca: `feat/045-bc-loe-pdf`
- Estil de commit: `feat(f5): ...` (convencional, com els commits recents)
- Fes un commit al final (tots els canvis junts) o per etapa lògica (backend / frontend).
- NO fas push ni PR tret que el operator ho demani explícitament.

---

## Pas 1: Afegir pdfplumber a requirements.txt

Obre `requirements.txt` i afegeix `pdfplumber` al final. El fitxer ha de quedar:

```
flask
flask-cors
requests
beautifulsoup4
python-dotenv
gunicorn
apscheduler
pdfplumber
```

**Verifica**: `pip install -r requirements.txt` → exit 0 (pdfplumber instal·lat).
**Verifica**: `python3 -c "import pdfplumber; print('ok')"` → `ok`

---

## Pas 2: Afegir `fetch_uc_codes_from_pdf()` a `certificados_scraper.py`

Afegeix immediatament **després** de la darrera funció del fitxer (`enrich_record`, aprox.
línia 212–228). Insereix el codi nou **just a continuació** (no editeu les funcions existents):

```python
# ── B→C LOE: extracció UC codes de l'Annexo PDF ─────────────────────────────

import io as _io
import re as _re

_UC_PAT = _re.compile(r'\bUC\d{4}_\d+\b')
_PDF_HEADERS = {**_HEADERS, 'Referer': 'https://www.todofp.es/'}


def fetch_uc_codes_from_pdf(codigo_c: str, timeout: int = 30) -> list[str]:
    """
    Descarrega l'Annexo PDF d'un C LOE i retorna la llista de codis UC únics.

    URL: BASE_DAM/anexos/{codigo_c.lower()}.pdf
    Retorna [] si el PDF no existeix (404) o no conté UC codes llegibles.
    Eleva requests.HTTPError per errors inesperats de xarxa (no 404).
    """
    import pdfplumber as _pdfplumber

    url = f"{BASE_DAM}/anexos/{codigo_c.lower()}.pdf"
    resp = requests.get(url, headers=_PDF_HEADERS, timeout=timeout)
    if resp.status_code == 404:
        logger.debug("fetch_uc_codes_from_pdf: PDF no trobat per %s", codigo_c)
        return []
    resp.raise_for_status()

    uc_codes: list[str] = []
    with _pdfplumber.open(_io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            uc_codes.extend(_UC_PAT.findall(text))

    return list(dict.fromkeys(uc_codes))  # dedup preservant ordre
```

Notes d'implementació:
- `import pdfplumber as _pdfplumber` és un import **dins de la funció** per evitar
  que el mòdul falli en import si `pdfplumber` no és instal·lat (no s'hauria de
  passar mai un cop `requirements.txt` és correcte, però és defensiu).
- `_UC_PAT`, `_PDF_HEADERS` i `_io`, `_re` es defineixen **fora** de la funció (mòdul-level)
  per no re-compilar a cada crida. Usa els noms amb underscore inicial per evitar
  col·lisions amb els importats del mòdul.
- `dict.fromkeys(uc_codes)` manté l'ordre d'inserció i elimina duplicats.

**Verifica** (prova ràpida en local — necessita xarxa):
```bash
cd backend && python3 -c "
import sys; sys.path.insert(0,'scrapers')
from scrapers.certificados_scraper import fetch_uc_codes_from_pdf
codes = fetch_uc_codes_from_pdf('ADGG0408')
print('UC codes:', codes[:5])
assert len(codes) > 0, 'Ha de retornar UC codes'
print('OK')
"
```
Esperat: imprimeix almenys `['UC0969_1', 'UC0970_1', ...]` i `OK`.

**STOP** si el test falla perquè pdfplumber llença `ImportError` — confirma que
el `pip install pdfplumber` del pas 1 ha funcionat.

---

## Pas 3: Crear `scripts/generate_bc_loe.py`

Crea el directori si no existeix (`ls scripts/` — si no hi ha cap `scripts/`,
crea'l). Crea el fitxer `scripts/generate_bc_loe.py`:

```python
#!/usr/bin/env python3
"""
generate_bc_loe.py — Genera backend/data/bc_loe.json a partir dels Annexos PDF
dels 584 Certificats de Profesionalitat C LOE.

Execució única (~6 min amb rate limiting). Necessita xarxa i pdfplumber.
Escriu backend/data/bc_loe.json (gitignored).

Ús: python3 scripts/generate_bc_loe.py [--dry-run N]
  --dry-run N  Processa només els primers N PDFs (per a proves ràpides)
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time

import requests
import pdfplumber

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ofertes.json')
OUT_PATH  = os.path.join(_REPO_ROOT, 'backend', 'data', 'bc_loe.json')
BASE_DAM  = 'https://www.todofp.es/dam/todofp/certificados-profesionales'

_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Referer': 'https://www.todofp.es/',
}
_UC_PAT = re.compile(r'\bUC\d{4}_\d+\b')


def _fetch_pdf_uc_codes(codigo: str) -> list[str]:
    url = f"{BASE_DAM}/anexos/{codigo.lower()}.pdf"
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    uc_codes: list[str] = []
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            uc_codes.extend(_UC_PAT.findall(text))
    return list(dict.fromkeys(uc_codes))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N',
                        help='Processa només els primers N PDFs')
    args = parser.parse_args()

    if not os.path.exists(DATA_PATH):
        logger.error("ofertes.json no trobat a: %s", DATA_PATH)
        sys.exit(1)

    with open(DATA_PATH, encoding='utf-8') as f:
        records = json.load(f)

    c_loe = [
        r for r in records
        if r.get('grado') == 'C' and r.get('plan_antiguo') and r.get('codigo')
    ]
    if args.dry_run:
        c_loe = c_loe[:args.dry_run]
        logger.info("DRY-RUN: processant %d PDFs (de %d totals)", args.dry_run, len(c_loe))
    else:
        logger.info("%d registres C LOE a processar (~6 min)", len(c_loe))

    result: dict[str, list[str]] = {}
    errors: list[str] = []
    no_codes: list[str] = []

    for i, r in enumerate(c_loe, 1):
        codigo = r['codigo']
        try:
            codes = _fetch_pdf_uc_codes(codigo)
            result[codigo] = codes
            if codes:
                logger.info("[%d/%d] %s → %d UC codes", i, len(c_loe), codigo, len(codes))
            else:
                no_codes.append(codigo)
                logger.warning("[%d/%d] 0 UC codes (404 o PDF sense texto): %s",
                               i, len(c_loe), codigo)
        except Exception as exc:
            logger.error("[%d/%d] ERROR: %s — %s", i, len(c_loe), codigo, exc)
            errors.append(codigo)
            result[codigo] = []

        if i < len(c_loe):
            time.sleep(1)

    # Estadística de cobertura
    with_codes = sum(1 for v in result.values() if v)
    total = len(result)
    pct = with_codes / total * 100 if total else 0
    logger.info("═══ Resultat ═══")
    logger.info("Total processats: %d", total)
    logger.info("PDFs amb UC codes: %d (%.0f%%)", with_codes, pct)
    logger.info("Sense UC codes:   %d", len(no_codes))
    logger.info("Errors HTTP:      %d", len(errors))
    if no_codes:
        logger.info("Sense UC codes: %s", no_codes[:10])
    if errors:
        logger.info("Errors: %s", errors[:10])

    if not args.dry_run and pct < 80:
        logger.error(
            "COBERTURA INSUFICIENT (%.0f%% < 80%%). bc_loe.json NO s'ha escrit. "
            "Investiga els PDFs problemàtics i reporta.", pct
        )
        sys.exit(1)

    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, separators=(',', ':'))

    size = os.path.getsize(OUT_PATH)
    logger.info("bc_loe.json escrit: %d entrades, %d bytes", len(result), size)


if __name__ == '__main__':
    main()
```

**Verifica** (dry-run amb 3 PDFs — necessita xarxa):
```bash
python3 scripts/generate_bc_loe.py --dry-run 3
```
Esperat: processa 3 PDFs, imprimeix UC codes per a cadascun, NO falla.

---

## Pas 4: Executa el run complet — genera `bc_loe.json`

Aquest és el pas obligatori i el més lent (~6 min). **No el saltis.**

```bash
python3 scripts/generate_bc_loe.py
```

Observa la sortida. Ha de finalitzar amb:
- `PDFs amb UC codes: NNN (XX%)` on XX ≥ 80
- `bc_loe.json escrit: 584 entrades, NNN bytes`

**Verifica**:
```bash
python3 -c "
import json
d = json.load(open('backend/data/bc_loe.json'))
with_codes = sum(1 for v in d.values() if v)
print(f'Entrades: {len(d)}, amb UC codes: {with_codes} ({with_codes/len(d)*100:.0f}%)')
assert len(d) >= 500, 'Hauria de tenir >=500 entrades'
assert with_codes >= 400, 'Hauria de tenir >=400 amb UC codes'
print('OK')
"
```
Esperat: `Entrades: 584, amb UC codes: NNN (≥80%)` i `OK`.

**STOP si** la cobertura és <80%: investiga els 10 primers `no_codes` del log,
comprova manualment si el PDF de ADGG0408 carrega (`curl -I https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/adgg0408.pdf`) i reporta.

---

## Pas 5: Afegir `b_by_uc` a `build_ab_index()` en `itinerary.py`

### 5a. Afegir pattern nou (línia ~17, just sota `_PAT_B_LOE`)

```python
_PAT_B_LOE_FULL = re.compile(r'^MF(\d{4})_(\d+)$')
```

Nota: `_PAT_B_LOE` existent (`r'^MF(\d+)_\d+$'`) **NO el toquis** — els tests existents en depenen.

### 5b. Afegir `b_by_uc` al dict inicialitzat de `build_ab_index()`

Al principi del cos de la funció, on s'inicialitzen els dicts (línies 32–35 aprox.):

```python
# Existent:
b_by_code: dict   = {}
b_by_uf_num: dict = {}
a_by_b_code: dict = {}
a_by_uf_num: dict = {}
# NOU:
b_by_uc: dict = {}
```

### 5c. Afegir l'ompliment de `b_by_uc` dins del primer bucle `for r in records`

Dins del bloc `if grado == 'B':`, **just a continuació** del bloc `m_loe` existent:

```python
# Existent:
m_loe = _PAT_B_LOE.match(codigo)
if m_loe:
    num = m_loe.group(1)
    b_by_uf_num[num] = r

# NOU (afegir immediatament a continuació):
m_loe_full = _PAT_B_LOE_FULL.match(codigo)
if m_loe_full:
    uc_key = f"UC{m_loe_full.group(1)}_{m_loe_full.group(2)}"
    b_by_uc[uc_key] = r  # ex: 'UC0969_1' → registre B MF0969_1
```

### 5d. Afegir `b_by_uc` al dict retornat (al final de `build_ab_index()`)

```python
return {
    'b_by_code':   b_by_code,
    'b_by_uf_num': b_by_uf_num,
    'a_by_b_code': a_by_b_code,
    'a_by_uf_num': a_by_uf_num,
    'b_by_uc':     b_by_uc,   # NOU
}
```

**Verifica** (sense xarxa):
```bash
cd backend && python3 -c "
import json, itinerary
recs = json.load(open('data/ofertes.json'))
idx = itinerary.build_ab_index(recs)
print('b_by_uc keys (first 3):', list(idx['b_by_uc'].keys())[:3])
assert 'b_by_uc' in idx
assert len(idx['b_by_uc']) > 0, 'Ha de tenir entrades B LOE'
print('OK')
"
```
Esperat: imprimeix claus UC com `['UC0001_1', 'UC0002_1', ...]` i `OK`.

---

## Pas 6: Ampliar `api_itinerari` a `app.py`

### 6a. Afegir constant `BC_LOE_PATH` (just a continuació de `CICLOS_PATH`)

```python
# Existent:
CICLOS_PATH = os.path.join(_DATA_DIR, "ciclos_fp.json")
# NOU:
BC_LOE_PATH = os.path.join(_DATA_DIR, "bc_loe.json")
```

### 6b. Modificar la branca `grado == 'C'` de `api_itinerari()`

Substitueix la branca `if grado == 'C':` sencera. La nova versió:

```python
if grado == 'C':
    if not os.path.exists(CICLOS_PATH):
        return jsonify({'ciclos_d': [], 'parent_b_loe': [],
                        'warning': 'ciclos_fp.json no disponible — cal fer un refresh'}), 200
    try:
        with open(CICLOS_PATH, 'r', encoding='utf-8') as f:
            ciclos_index = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("api_itinerari C: error llegint ciclos_fp.json: %s", exc)
        return jsonify({'error': 'Error llegint dades de cicles'}), 503
    ciclos = ciclos_index.get(codigo, [])

    # B→C LOE: mòduls B LOE acreditats per aquest certificat C
    parent_b_loe: list[dict] = []
    if os.path.exists(BC_LOE_PATH):
        try:
            with open(BC_LOE_PATH, 'r', encoding='utf-8') as f:
                bc_loe_index = json.load(f)
            uc_codes = bc_loe_index.get(codigo, [])
            if uc_codes:
                it_idx = _get_itinerary_index()
                b_by_uc = it_idx.get('b_by_uc', {})
                for uc in uc_codes:
                    b_rec = b_by_uc.get(uc)
                    if b_rec:
                        parent_b_loe.append(_serialize(b_rec))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("api_itinerari C: error llegint bc_loe.json: %s", exc)

    return jsonify({'ciclos_d': ciclos, 'parent_b_loe': parent_b_loe})
```

**Verifica** (en local, necessita `backend/data/bc_loe.json` del pas 4):
```bash
cd backend && python3 -c "
import os, json
os.environ['FLASK_ENV'] = 'testing'
import app
client = app.app.test_client()
r = client.get('/api/itinerari?grado=C&codigo=ADGG0408')
data = json.loads(r.data)
print('ciclos_d:', len(data.get('ciclos_d', [])))
print('parent_b_loe:', len(data.get('parent_b_loe', [])))
print('Keys:', list(data.keys()))
assert 'parent_b_loe' in data
print('OK')
"
```
Esperat: `parent_b_loe:` ≥1 (si `bc_loe.json` del pas 4 existeix i `ofertes.json` local) i `OK`.

---

## Pas 7: Tests — `test_itinerary.py` i `test_api.py`

### 7a. `backend/tests/test_itinerary.py` — afegir 2 tests nous

Afegeix al **final** del fitxer (a continuació de `test_get_parent_b_invalid_codigo`):

```python
RECORDS_B_LOE_UC = [
    {'grado': 'B', 'codigo': 'MF0038_3', 'denominacion': 'Análisis enológico', 'nivel': 3, 'familia': 'AGA'},
    {'grado': 'B', 'codigo': 'MF0969_1', 'denominacion': 'Gestión contable',   'nivel': 1, 'familia': 'ADG'},
]


def test_build_ab_index_b_by_uc_present():
    idx = itinerary.build_ab_index(RECORDS_B_LOE_UC)
    assert 'b_by_uc' in idx
    assert 'UC0038_3' in idx['b_by_uc']
    assert idx['b_by_uc']['UC0038_3']['codigo'] == 'MF0038_3'


def test_build_ab_index_b_by_uc_maps_level():
    idx = itinerary.build_ab_index(RECORDS_B_LOE_UC)
    assert 'UC0969_1' in idx['b_by_uc']
    assert idx['b_by_uc']['UC0969_1']['codigo'] == 'MF0969_1'
    # UC0038_3 NO ha de correspondre a UC0038_1 (els nivells no es barregen)
    assert 'UC0038_1' not in idx['b_by_uc']
```

### 7b. `backend/tests/test_api.py` — afegir 1 test nou per grado=C

Localitza la secció dels tests `test_itinerari_grado_*`. Afegeix a continuació
del darrer test d'itinerari existent:

```python
_FAKE_BC_LOE = '{"COML0110": ["UC0969_1", "UC0970_1"]}'
_FAKE_OFERTES_ITINERARI_C = (
    '[{"grado":"B","codigo":"MF0969_1","denominacion":"Gestió comptable","nivel":1,"familia":"ADG"},'
    '{"grado":"B","codigo":"MF0970_1","denominacion":"Gestió fiscal","nivel":1,"familia":"ADG"},'
    '{"grado":"C","codigo":"COML0110","denominacion":"Gestió comptable i fiscal","nivel":2,"familia":"COM","plan_antiguo":true}]'
)
_FAKE_CICLOS = '{"COML0110": [{"denominacion": "Servicios Administrativos", "familia": "ADG", "ficha_url": null}]}'


def test_itinerari_grado_c_retorna_parent_b_loe(client, monkeypatch):
    """F5: GET /api/itinerari?grado=C inclou parent_b_loe amb els B LOE acreditats."""
    import app as flask_app_module
    monkeypatch.setattr(flask_app_module, "_itinerary_index_cache", {"mtime": None, "index": None})

    def _mock_exists(path):
        return True

    def _mock_getmtime(path):
        return 99.0

    def _fake_open(path, *args, **kwargs):
        import builtins
        if 'bc_loe' in str(path):
            return mock.mock_open(read_data=_FAKE_BC_LOE)()
        if 'ciclos_fp' in str(path):
            return mock.mock_open(read_data=_FAKE_CICLOS)()
        if 'ofertes' in str(path):
            return mock.mock_open(read_data=_FAKE_OFERTES_ITINERARI_C)()
        return builtins.open.__wrapped__(path, *args, **kwargs) if hasattr(builtins.open, '__wrapped__') else builtins.open(path, *args, **kwargs)

    with mock.patch(PATCH_OS_PATH_EXISTS, side_effect=_mock_exists), \
         mock.patch("app.os.path.getmtime", return_value=99.0), \
         mock.patch("builtins.open", side_effect=_fake_open):
        r = client.get("/api/itinerari?grado=C&codigo=COML0110")

    assert r.status_code == 200
    data = r.get_json()
    assert "ciclos_d" in data
    assert "parent_b_loe" in data
    codigos_b = {b["codigo"] for b in data["parent_b_loe"]}
    assert "MF0969_1" in codigos_b
    assert "MF0970_1" in codigos_b
```

Nota: El mock de `builtins.open` ha de distingir entre `bc_loe.json`, `ciclos_fp.json`
i `ofertes.json`. Si el patró de test existent a `test_api.py` gestiona múltiples
`open` d'una altra manera (p.ex. amb `side_effect` en lloc de `mock_open`), adapta
el test al patró del fitxer (comprova com fan els tests `test_itinerari_grado_*`
existents). El patró descrit a continuació és equivalent; si falla per l'ordre de
les crides `open`, usa `side_effect` amb una llista.

**Verifica**:
```bash
cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -q
```
Esperat: tots els tests passes, incloent els 2 nous de `test_itinerary.py` i l'1
nou de `test_api.py`.

**Verifica suite completa**:
```bash
cd backend && python3 -m pytest tests/ -q
```
Esperat: exit 0, cap regressió.

---

## Pas 8: Frontend — `index.html` i `i18n.js`

### 8a. Afegir `parentBLoeData: {}` a l'objecte de dades Alpine

Cerca la inicialització Alpine de `ciclosDData` (aprox. línia 38530 context). Hi ha un
objecte `data()` o similar. Afegeix `parentBLoeData: {}` just a continuació
de `ciclosDData: {}`:

```javascript
ciclosDData: {},        // existent
parentBLoeData: {},     // NOU — parent B LOE per codigo C
```

### 8b. Actualitzar `fetchCiclosD()` per poblar `parentBLoeData`

Substitueix la funció `fetchCiclosD` existent per:

```javascript
async fetchCiclosD(codigo) {
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

### 8c. Afegir template per a `parent_b_loe` just SOTA el bloc de cicles D existents

Localitza el tancament del `<div class="detall-ciclos-d">` (just abans del
`</template>` que tanca `x-if="ciclosDData[row.codigo]..."`). Afegeix
immediatament a continuació del `</div>` del bloc de cicles, dins del mateix
`<template x-if="ciclosDData[...]">`:

```html
<!-- B→C LOE: mòduls B LOE acreditats -->
<template x-if="parentBLoeData[row.codigo] && parentBLoeData[row.codigo].length > 0">
  <div class="detall-ciclos-d" style="margin-top:6px">
    <span x-text="t('index.itinerari.parent_b_loe_cap')"></span>
    <ul class="ciclos-d-list">
      <template x-for="bmod in parentBLoeData[row.codigo]" :key="bmod.codigo">
        <li x-text="bmod.codigo + ' — ' + bmod.denominacion"></li>
      </template>
    </ul>
  </div>
</template>
```

### 8d. Afegir claus i18n a `frontend/i18n.js`

Localitza el bloc `/* ── F5: Itineraris formatius ── */` i afegeix just a
continuació de la darrera clau existent (`ciclos_d_err`):

```javascript
'index.itinerari.parent_b_loe_cap': 'Mòduls B (LOE) acreditats per aquest certificat:',
```

I al bloc equivalent castellà (si n'hi ha — busca `'es'` o el bloc per al segon
idioma a `i18n.js`). Afegeix la mateixa clau amb text en castellà:

```javascript
'index.itinerari.parent_b_loe_cap': 'Módulos B (LOE) acreditados por este certificado:',
```

**Verifica**: obre `frontend/index.html` al navegador, busca un Certificat C LOE
(ex: `ADGG0408`), clica "Cicles FP (D)" i confirma que:
- La secció de cicles D segueix funcionant.
- Si `bc_loe.json` és al servidor i té dades per a ADGG0408, apareix la secció
  "Mòduls B (LOE) acreditats...".
- La UI no mostra errors a la consola del navegador.

Si l'entorn local no té `bc_loe.json` servit, el backend retornarà `parent_b_loe: []`
i la secció no apareixerà — aquest és el comportament esperat (graceful degradation).

---

## Pas 9: Instruccions de desplegament al VPS

Afegeix una nota a `plans/instructions.md` (secció de passos manuals) o a la
documentació de desplegament existent. La nota ha de dir:

> **bc_loe.json (Pas 045)**: Després del primer desplegament d'aquest pla,
> executa al VPS:
> ```bash
> cd /ruta/al/repo
> pip install pdfplumber
> python3 scripts/generate_bc_loe.py
> ```
> Triga ~6 min. `bc_loe.json` es genera a `backend/data/bc_loe.json`.
> No cal rellançar el servei: Flask llegeix el fitxer a cada petició.
>
> Re-executa el script si s'afegeixen nous certificats C LOE (rarament).

---

## Test plan

### Tests unitaris — `test_itinerary.py`

Dos tests nous (pas 7a), modelats sobre `test_build_ab_index_loe()` existent:
- `test_build_ab_index_b_by_uc_present` — verifica que `b_by_uc` és al dict i
  que `UC0038_3` mapeja a `MF0038_3`.
- `test_build_ab_index_b_by_uc_maps_level` — verifica que els nivells no es
  confonen: `UC0969_1` existeix però `UC0038_1` no (el B és `MF0038_3`).

### Tests d'integració — `test_api.py`

Un test nou (pas 7b), modelat sobre `test_itinerari_grado_b_returns_children_a`:
- `test_itinerari_grado_c_retorna_parent_b_loe` — verifica que la resposta
  de `grado=C` inclou `parent_b_loe` amb els B correctes.

**Comanda de verificació final**:
```bash
cd backend && python3 -m pytest tests/ -q
```
→ exit 0, sense regressions. El nombre de tests ha d'incrementar en 3.

---

## Criteris de DONE

- [ ] `python3 -c "import pdfplumber; print('ok')"` → `ok`
- [ ] `python3 scripts/generate_bc_loe.py --dry-run 5` → exit 0, ≥3 PDFs amb UC codes
- [ ] `backend/data/bc_loe.json` existeix i té ≥500 entrades (run complet DONE)
- [ ] `cd backend && python3 -m pytest tests/test_itinerary.py tests/test_api.py -q` → exit 0 amb 3 nous tests passant
- [ ] `cd backend && python3 -m pytest tests/ -q` → exit 0, cap regressió
- [ ] `python3 -c "import json; d=json.load(open('backend/data/bc_loe.json')); print(sum(1 for v in d.values() if v)/len(d)*100)"` → ≥80 (cobertura %)
- [ ] `GET /api/itinerari?grado=C&codigo=ADGG0408` retorna `parent_b_loe` no buit (si el servidor VPS té `bc_loe.json`)
- [ ] `GET /api/itinerari?grado=C&codigo=ADGG0408` retorna `ciclos_d` igual que abans (no regressió)
- [ ] Cap fitxer fora de la llista "In scope" modificat (`git diff --name-only`)
- [ ] `plans/README.md` actualitzat amb estat `DONE` per al pla 045

---

## Condicions STOP

Atura't i reporta (no improvisis) si:

- **Drift**: algun fitxer de l'àmbit ha canviat des de `5acb252` i el codi no
  coincideix amb els excerpts de "Current state".
- **Cobertura PDF < 80%** al final del pas 4: el run ha fallat massa PDFs.
  Comprova si `todofp.es` ha canviat les URLs (`curl -I {URL_sample}`).
- **`pdfplumber` falla a importar** malgrat el `pip install`: comprova
  l'entorn virtual actiu i si hi ha conflictes de dependències.
- **El mock de `builtins.open` al pas 7b no funciona**: el test llença
  excepcions inesperades. Revisa el patró de mocking dels tests existents a
  `test_api.py` i adapta el test al patró del fitxer sense canviar la lògica
  de l'assertion.
- **El test d'integració falla perquè `_fake_open` rep un path inesperat**:
  afegeix un `logger.debug(f"open: {path}")` temporal per diagnosticar quins
  paths s'intenten obrir i ajusta el `side_effect`.
- **La UI no mostra la nova secció**: comprova a la consola del navegador si
  `parentBLoeData` existeix al component Alpine (`$data.parentBLoeData`) i si
  la resposta de l'API conté `parent_b_loe`.

---

## Notes de manteniment

- **Pipeline**: `bc_loe.json` NO es regenera al pipeline diari (per disseny —
  el cost és de 6 min). Si s'afegeixen nous certificats C LOE al buscador, cal
  re-executar `generate_bc_loe.py` manualment al VPS.
- **Nous registres C LOE**: quan el ministeri publiqui nous certificats, el
  pipeline els afegirà a `ofertes.json` però sense UC codes a `bc_loe.json`.
  El frontend mostrarà `parent_b_loe: []` per a ells fins que es re-executi el
  script.
- **Canvi de format PDF**: si `todofp.es` canvia el format dels PDFs (p.ex.
  imatges en lloc de text), `_UC_PAT` no trobarà res. Simptoma: cobertura cau
  a <80% en un re-run del script.
- **B→C per a C LOMLOE**: no implementat (NO VIABLE amb fonts actuals — veure
  spike 043). No afegir lògica per a `plan_antiguo=False` sense nova font oficial.
- **Revisar en PR**: que `_HEADERS` de `fetch_uc_codes_from_pdf()` i del mòdul
  existent no entrin en conflicte; que el `import pdfplumber` dins de la funció
  no causi overhead en les crides múltiples (el `import` és cached per Python).
