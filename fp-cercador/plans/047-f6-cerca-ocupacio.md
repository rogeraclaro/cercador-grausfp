# Pla 047: [F6] Cerca per ocupació/sortida professional (MVP castellà, C+D+E)

> **Executor instructions**: Segueix el pla pas a pas. Executa cada comanda de
> verificació i confirma el resultat esperat abans de passar al pas següent. Si
> una condició STOP es dispara, atura't i reporta — no improvisis. Quan acabis,
> actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Drift check (executa primer)**:
> ```bash
> git diff --stat 425f825..HEAD -- backend/app.py backend/scrapers/certificados_scraper.py backend/tests/test_api.py frontend/index.html frontend/i18n.js
> ```
> Si algun fitxer ha canviat, compara els excerpts de "Current state" amb el
> codi viu. Si hi ha desviació, tracta-ho com a condició STOP.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED (scraping de ~588 PDFs + ~231 pàgines HTML; endpoint i pàgina noves; cap canvi a fluxos existents)
- **Depends on**: cap (spike `.planning/spikes/001-003` DONE — validació de fonts)
- **Category**: direction (F6 cerca per ocupació)
- **Planned at**: commit `425f825`, 2026-06-20

## Per què importa

Avui el cercador només serveix si l'usuari ja sap el NOM del títol. La majoria
de gent real parteix d'una ocupació ("vull ser soldador", "cuidar gent gran").
F6 inverteix el punt d'entrada: cercar per ocupació → graus que hi porten.

L'spike (`.planning/spikes/001-003`, tot VALIDATED) va provar amb crides reals
que la font existeix i és extraïble:
- **Graus C LOE**: l'endpoint `POST /buscadorcertificados/pdfPT` retorna un PDF
  amb "Ocupaciones o puestos de trabajo relacionados" — **587/588 certs (99,8%)**.
- **Graus D i E**: la pàgina oficial (`ficha_url`, domini `que-estudiar`) té una
  secció "Salidas profesionales → Trabajar como: [llista]" — **D 100%, E 93%**.
- Total: ~3.707 ocupacions als C + les de D/E.

Aquest pla construeix el MVP: generar un índex ocupació→grau (castellà), servir-lo
amb un endpoint de cerca, i una pàgina `ocupacions.html` on l'usuari cerca i veu
els graus resultants enllaçats a la seva fitxa.

**Abast explícitament acordat (MVP)**: cerca en **castellà** sobre **C+D+E**, amb
**match per paraula completa** (evita falsos positius substring com
"informatica"→"bioinformática") i **neteja de codis CNO** del text. **SENSE** capa
de traducció/sinònims català↔castellà — és una 2a iteració documentada, no part
d'aquest pla.

## Current state

### Fitxers rellevants

- `backend/scrapers/certificados_scraper.py` — té `_bootstrap_session()` i
  `fetch_all()` (retorna `{codigo: {cert_id, duracion_horas}}` per als 588 certs C).
  El reaprofitem per import (NO el modifiquem).
- `backend/app.py` — Flask. Hi afegim una constant de path, un helper de cache i
  l'endpoint `/api/ocupaciones`.
- `backend/data/ofertes.json` — 12.894 registres. Els C tenen `codigo`; **els D i
  E tenen `codigo: None`** i només `ficha_url`. NO modificar mai.
- `backend/tests/test_api.py` — tests d'integració Flask.
- `frontend/index.html` — pàgina principal (Alpine.js). Hi afegim un enllaç a la
  nova pàgina.
- `frontend/i18n.js` — diccionari CA/ES global.
- `frontend/ocupacions.html` — **crear** (modelar sobre `frontend/seguiment.html`).

### `certificados_scraper.py` — el que reaprofitem (NO modificar)

```python
BASE_CERT_URL = 'https://www.todofp.es/buscadorcertificados'

def _bootstrap_session(timeout: int = 30) -> requests.Session:
    """GET /buscador → cookie __Host-todofp.es (sense JSESSIONID)."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    resp = session.get(BASE_CERT_URL + '/buscador', timeout=timeout)
    resp.raise_for_status()
    return session

def fetch_all() -> dict[str, dict]:
    """POST /busquedaCP (paso=600) → {codigo: {'cert_id': int, 'duracion_horas': int|None}}"""
    ...
```

### Endpoint d'ocupacions (font C) — verificat a l'spike 001

`POST {BASE_CERT_URL}/pdfPT` amb `data={'certificadoID': str(cert_id), 'codigo': codigo}`
→ retorna **bytes d'un PDF** (magic `%PDF`). El text conté:

```
Ocupaciones o puestos de trabajo relacionados
- 9811.1024 Mozo/a de almacén.
- 8333.1015 Carretillero/a.
- Operario/a de logística.
Subdirección General de Ordenación de la Formación Profesional 1
```

**Format de línia**: bullet (`-`, `–` o `—`) + CNO opcional + nom. El bullet pot
ser guió simple o doble en-dash → regex `^[-–—]+`. Els CNO tenen formats
inconsistents (`9811.1024`, `5129.003.0`, `95121019`) i només ~33% de línies en
tenen → **el nom en text lliure és l'actiu cercable; el CNO s'ha de NETEJAR del
text**.

### Font D/E — verificat a l'spike 002

La pàgina `ficha_url` (HTML) de cada D/E té un header "Salidas profesionales"
seguit d'un bloc amb "Trabajar como: [ocupacions separades per punt]". Exemple
real (Técnico en Farmacia): `['Farmacia', 'Auxiliar de Farmacia', ...]`.

### `app.py` — constants i patró de cache per mtime (línies 70, 743–767)

```python
DATA_PATH = os.path.normpath(...)                       # ofertes.json
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CICLOS_PATH = os.path.join(_DATA_DIR, "ciclos_fp.json")
BC_LOE_PATH = os.path.join(_DATA_DIR, "bc_loe.json")
```

Patró de cache existent a imitar (`_get_bc_loe_inverse`, línies 743–767):

```python
_bc_loe_inverse_cache: dict = {"mtime": None, "index": None}

def _get_bc_loe_inverse() -> dict:
    if not os.path.exists(BC_LOE_PATH):
        return {}
    mtime = os.path.getmtime(BC_LOE_PATH)
    if _bc_loe_inverse_cache["mtime"] == mtime and _bc_loe_inverse_cache["index"] is not None:
        return _bc_loe_inverse_cache["index"]
    try:
        with open(BC_LOE_PATH, 'r', encoding='utf-8') as f:
            bc_loe = json.load(f)
        inverse: dict = {}
        ...
        _bc_loe_inverse_cache.update(mtime=mtime, index=inverse)
        return inverse
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_bc_loe_inverse: error llegint bc_loe.json: %s", exc)
        return {}
```

Els endpoints es declaren amb `@app.route('/api/...')` i retornen `jsonify(...)`.
Veure `api_itinerari()` (línia 770) com a exemple d'endpoint de lectura amb
`request.args.get(...)`.

### Enllaços a fitxes (per als resultats)

- **C**: `{API_BASE}/api/ficha-redirect?grado=C&codigo={codigo}` (endpoint ja existent).
- **D / E**: el camp `ficha_url` del registre (URL directa a todofp).

### Frontend — exemplar de pàgina secundària

`frontend/seguiment.html` és el millor model: topbar amb `#auth-widget` +
selector d'idioma, `<script src="i18n.js">`, `data-i18n`, càrrega via `fetch` a
`API_BASE`. Copia'n l'estructura (topbar, hero, footer, estils de taula/targeta).
`API_BASE` es defineix a totes les pàgines — comprova com a `seguiment.html`.

### Dades

- `backend/data/` és **gitignored** — tot el que s'hi generi (`ocupaciones.json`)
  s'ha de regenerar al servidor; NO el commitis.
- Cobertura esperada del generador: C ≥99%, D ~100%, E ~93%.

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat en cas d'èxit |
|---|---|---|
| Verificar deps | `python3 -c "import requests, bs4, pdfplumber; print('ok')"` | `ok` |
| Generar índex (dry-run) | `python3 scripts/generate_ocupaciones.py --dry-run 5` | processa 5+5+5, no falla |
| Generar índex (complet) | `python3 scripts/generate_ocupaciones.py` | `ocupaciones.json escrit:` al final |
| Verificar índex | `python3 -c "import json; d=json.load(open('backend/data/ocupaciones.json')); print(len(d), 'entrades')"` | ≥3500 entrades |
| Tests filtrats | `cd backend && python3 -m pytest tests/test_api.py -q` | tots passen |
| Suite completa | `cd backend && python3 -m pytest tests/ -q` | exit 0, cap regressió |

## Codi de referència de l'spike

Els scripts de l'spike a `.planning/spikes/` són **funcionals i provats** — usa'ls
com a base (NO els importis; copia la lògica al generador nou):
- `001-occupation-source-extract/extract.py` — extracció PDF C (`/pdfPT` + regex bullets).
- `002-coverage-and-de-extension/probe_de.py` — extracció "Salidas profesionales" de D/E.
- `003-reverse-search-feel/server.py` + `build_index.py` — normalització i cerca.

## Àmbit

**In scope** (els ÚNICS fitxers que has de crear o modificar):
- `scripts/generate_ocupaciones.py` — **crear** (generador de l'índex; autocontingut)
- `backend/app.py` — afegir `OCUPACIONES_PATH`, `_get_ocupaciones_index()`, endpoint `/api/ocupaciones`
- `backend/tests/test_api.py` — afegir tests del nou endpoint
- `frontend/ocupacions.html` — **crear** (UI de cerca)
- `frontend/i18n.js` — afegir claus de la pàgina nova (CA + ES)
- `frontend/index.html` — afegir UN enllaç a `ocupacions.html` al footer (Pas 6)
- `plans/instructions.md` — afegir la nota de desplegament VPS (Pas 8)
- `plans/README.md` — actualitzar la fila del pla 047

**Out of scope** (NO tocar):
- `backend/scrapers/certificados_scraper.py` — només s'importa (`fetch_all`,
  `_bootstrap_session`); NO el modifiquis.
- `backend/scrapers/pipeline.py` — NO integrar la generació al refresh diari (el
  cost de scraping és massa per al pipeline; el script és manual, com `generate_bc_loe.py`).
- `backend/data/ocupaciones.json` — fitxer generat; NO el commitis.
- `backend/data/ofertes.json` — no modificar mai.
- Cap capa de traducció/sinònims CA↔ES (2a iteració).
- Cap altra pàgina HTML que no sigui `ocupacions.html` i l'enllaç a `index.html`.

## Git workflow

- Branca: `feat/047-cerca-ocupacio`
- Estil de commit: `feat(f6): ...` (convencional, com els commits recents). Acaba
  els missatges amb les línies `Co-Authored-By:` i `Claude-Session:` si l'entorn
  ho requereix; si no n'estàs segur, fes un commit net sense aquestes línies.
- Fes commits per etapa lògica (generador / backend / frontend) o un al final.
- NO fas push ni PR tret que l'operador ho demani explícitament.

---

## Pas 1: Crear `scripts/generate_ocupaciones.py`

Crea el directori `scripts/` si no existeix (ja existeix: conté `generate_bc_loe.py`).
Crea el fitxer `scripts/generate_ocupaciones.py` amb aquest contingut:

```python
#!/usr/bin/env python3
"""
generate_ocupaciones.py — Genera backend/data/ocupaciones.json: l'índex de cerca
per ocupació de F6.

DUES fonts (validades a .planning/spikes/001-003):
  - Graus C LOE: POST /buscadorcertificados/pdfPT → PDF amb "puestos de trabajo".
  - Graus D i E: pàgina ficha_url (que-estudiar) → secció "Salidas profesionales".

Execució única manual (~2-3 min). Necessita xarxa, pdfplumber i beautifulsoup4.
Escriu una llista plana d'entrades {ocupacio, norm, grado, codigo, id,
denominacion, ficha_url, familia}.

Ús: python3 scripts/generate_ocupaciones.py [--dry-run N]
  --dry-run N  Processa només els primers N de cada grau (proves ràpides).
"""
import argparse
import io
import json
import logging
import os
import re
import sys
import time
import unicodedata

import requests
from bs4 import BeautifulSoup
import pdfplumber

# Reutilitza la sessió/bootstrap del scraper de certificats (NO el modifica)
_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'backend'))
from scrapers import certificados_scraper as cs  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ofertes.json')
OUT_PATH = os.path.join(_REPO_ROOT, 'backend', 'data', 'ocupaciones.json')

_HTML_HEADERS = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.todofp.es/'}

# Línia del PDF C: bullet (-, –, —) + CNO opcional + nom. Capturem nom; CNO es neteja a part.
_PDF_LINE = re.compile(r'^[-–—]+\s*(.+?)\.?\s*$')
_SECTION_C = 'Ocupaciones o puestos de trabajo relacionados'
_FOOTER_C = 'Subdirección General'
# Neteja de TOTS els formats CNO observats: NNNN.NNNN, NNNN.NNN.N, 8 dígits seguits.
_CNO_CLEAN = re.compile(r'^\s*(?:\d{4}\.\d{3,4}(?:\.\d)?|\d{8})\s+')


def norm(s: str) -> str:
    """Minúscules + sense accents + col·lapsa soroll d'OCR ('/ as' → '/as')."""
    s = s.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'/\s+', '/', s)
    return re.sub(r'\s+', ' ', s).strip()


def clean_occ(text: str) -> str:
    """Treu el codi CNO inicial (qualsevol format) del nom d'ocupació."""
    return _CNO_CLEAN.sub('', text).strip()


# ── Font C: PDF /pdfPT ──────────────────────────────────────────────────────
def occupations_for_cert(session, cert_id: int, codigo: str) -> list[str]:
    r = session.post(cs.BASE_CERT_URL + '/pdfPT',
                     data={'certificadoID': str(cert_id), 'codigo': codigo}, timeout=30)
    r.raise_for_status()
    if r.content[:4] != b'%PDF':
        return []
    with pdfplumber.open(io.BytesIO(r.content)) as pdf:
        text = '\n'.join((p.extract_text() or '') for p in pdf.pages)
    out, in_section = [], False
    for raw in text.splitlines():
        line = raw.strip()
        if _SECTION_C in line:
            in_section = True
            continue
        if not in_section:
            continue
        if _FOOTER_C in line:
            break
        m = _PDF_LINE.match(line)
        if m:
            occ = clean_occ(m.group(1))
            if occ and len(occ) > 2:
                out.append(occ)
    # dedup preservant ordre
    return list(dict.fromkeys(out))


# ── Font D/E: pàgina ficha_url ──────────────────────────────────────────────
def occupations_for_ficha(url: str) -> list[str]:
    try:
        r = requests.get(url, headers=_HTML_HEADERS, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        logger.warning("ficha %s: %s", url, exc)
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'strong', 'b']):
        if 'salidas profesionales' in tag.get_text(strip=True).lower():
            blk = tag.find_next(['p', 'ul', 'div'])
            if not blk:
                return []
            txt = blk.get_text(' ', strip=True)
            txt = re.sub(r'^.*?Trabajar como:?', '', txt, flags=re.I).strip()
            parts = [p.strip(' .') for p in re.split(r'[.\n]', txt) if p.strip(' .')]
            return list(dict.fromkeys(p for p in parts if 3 < len(p) < 90))[:30]
    return []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', type=int, metavar='N', help='Primers N de cada grau')
    args = parser.parse_args()

    if not os.path.exists(DATA_PATH):
        logger.error("ofertes.json no trobat: %s", DATA_PATH)
        sys.exit(1)
    with open(DATA_PATH, encoding='utf-8') as f:
        records = json.load(f)

    den_c = {r['codigo']: r for r in records if r.get('grado') == 'C' and r.get('codigo')}
    de = [r for r in records if r.get('grado') in ('D', 'E') and r.get('ficha_url')]

    entries: list[dict] = []

    # --- Font C ---
    cert_data = cs.fetch_all()  # {codigo: {cert_id, ...}}
    cert_items = list(cert_data.items())
    if args.dry_run:
        cert_items = cert_items[:args.dry_run]
    session = cs._bootstrap_session()
    c_ok = 0
    for i, (codigo, d) in enumerate(cert_items, 1):
        try:
            occs = occupations_for_cert(session, d['cert_id'], codigo)
        except Exception as exc:
            logger.warning("[C %d/%d] %s ERROR: %s", i, len(cert_items), codigo, exc)
            occs = []
        if occs:
            c_ok += 1
        rec = den_c.get(codigo)
        denom = rec['denominacion'] if rec else codigo
        fam = rec.get('familia', '') if rec else ''
        rid = rec.get('id') if rec else None
        for occ in occs:
            entries.append({'ocupacio': occ, 'norm': norm(occ), 'grado': 'C',
                            'codigo': codigo, 'id': rid, 'denominacion': denom,
                            'ficha_url': None, 'familia': fam})
        if i % 100 == 0:
            logger.info("  C ...%d/%d", i, len(cert_items))
    logger.info("Font C: %d/%d certs amb ocupacions", c_ok, len(cert_items))

    # --- Font D/E ---
    de_items = de[:args.dry_run] if args.dry_run else de
    de_ok = 0
    for i, r in enumerate(de_items, 1):
        occs = occupations_for_ficha(r['ficha_url'])
        if occs:
            de_ok += 1
        for occ in occs:
            entries.append({'ocupacio': occ, 'norm': norm(occ), 'grado': r['grado'],
                            'codigo': r.get('codigo'), 'id': r.get('id'),
                            'denominacion': r['denominacion'], 'ficha_url': r['ficha_url'],
                            'familia': r.get('familia', '')})
        if i % 50 == 0:
            logger.info("  D/E ...%d/%d", i, len(de_items))
        time.sleep(0.2)
    logger.info("Font D/E: %d/%d amb ocupacions", de_ok, len(de_items))

    json.dump(entries, open(OUT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    logger.info("═══ ocupaciones.json escrit: %d entrades, %d bytes ═══",
                len(entries), os.path.getsize(OUT_PATH))


if __name__ == '__main__':
    main()
```

**Verifica** (dry-run, necessita xarxa):
```bash
python3 scripts/generate_ocupaciones.py --dry-run 5
```
Esperat: processa 5 certs C + 5 D/E, imprimeix "Font C: X/5", "Font D/E: Y/5" i
escriu `ocupaciones.json` amb desenes d'entrades, sense fallar.

**STOP si** "Font C: 0/5" — l'endpoint `/pdfPT` o el bootstrap ha canviat;
comprova `curl -sI https://www.todofp.es/buscadorcertificados/buscador` i reporta.

**STOP si** l'script peta amb `ImportError` (ex. `from scrapers import
certificados_scraper` o un dels seus imports com `bs4`/`pdfplumber`): confirma que
les deps estan instal·lades (`python3 -c "import requests, bs4, pdfplumber; print('ok')"`)
i que s'executa des de l'arrel del repo (el `sys.path` afegeix `backend/`).

**Nota**: `--dry-run N` agafa els N PRIMERS certs/D-E (no una mostra aleatòria), així
que és una prova de fum del camí, no una estimació fiable de cobertura. La cobertura
real es valida al Pas 2.

---

## Pas 2: Run complet — genera `ocupaciones.json`

Pas obligatori (~2-3 min). **No el saltis.**

```bash
python3 scripts/generate_ocupaciones.py
```

Ha de finalitzar amb `Font C: ~580/588`, `Font D/E: ~215/231` i
`ocupaciones.json escrit: NNNN entrades` (≥3.500).

**Verifica**:
```bash
python3 -c "
import json
d = json.load(open('backend/data/ocupaciones.json'))
from collections import Counter
print('entrades:', len(d))
print('per grau:', dict(Counter(e['grado'] for e in d)))
assert len(d) >= 3500, 'esperat >=3500 entrades'
# Cap CNO residual al text (no ha de començar amb dígits+punt)
import re
bad = [e['ocupacio'] for e in d if re.match(r'^\d{4}\.', e['ocupacio'])]
assert not bad, f'CNO residual no netejat: {bad[:3]}'
print('OK')
"
```
Esperat: `entrades: NNNN`, `per grau: {'C': ..., 'D': ..., 'E': ...}`, `OK`.

**STOP si** la cobertura C és <90% del total de certs, o si l'assert de CNO
residual falla (el regex `_CNO_CLEAN` no cobreix algun format — afegeix-lo).

---

## Pas 3: Backend — `OCUPACIONES_PATH`, cache i endpoint `/api/ocupaciones`

### 3a. Afegir la constant de path

A `backend/app.py`, just a continuació de `BC_LOE_PATH` (línia ~74):

```python
OCUPACIONES_PATH = os.path.join(_DATA_DIR, "ocupaciones.json")
```

### 3b. Afegir el helper de cache `_get_ocupaciones_index()`

Afegeix immediatament **després** de la funció `_get_bc_loe_inverse()` (acaba a
la línia ~767). Modela'l sobre el patró de cache per mtime existent:

```python
_ocupaciones_cache: dict = {"mtime": None, "entries": None}


def _get_ocupaciones() -> list[dict]:
    """
    Retorna la llista d'entrades ocupació→grau de ocupaciones.json.
    Cache invalidat per mtime. Retorna [] si el fitxer no existeix.
    """
    if not os.path.exists(OCUPACIONES_PATH):
        return []
    mtime = os.path.getmtime(OCUPACIONES_PATH)
    if _ocupaciones_cache["mtime"] == mtime and _ocupaciones_cache["entries"] is not None:
        return _ocupaciones_cache["entries"]
    try:
        with open(OCUPACIONES_PATH, 'r', encoding='utf-8') as f:
            entries = json.load(f)
        _ocupaciones_cache.update(mtime=mtime, entries=entries)
        return entries
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("_get_ocupaciones: error llegint ocupaciones.json: %s", exc)
        return []
```

### 3c. Afegir la funció de normalització i l'endpoint

Afegeix l'endpoint a continuació del helper anterior. La cerca: normalitza la
query, parteix en tokens, i exigeix que **cada token coincideixi amb una paraula
sencera** del text normalitzat (vora de paraula `\b`) — això evita els falsos
positius substring (ex. "informatica" no ha de coincidir amb "bioinformatica").
Agrupa per grau (clau `codigo` per C, `id` per D/E) i rankeja per nombre
d'ocupacions coincidents.

```python
import re as _re_ocup
import unicodedata as _ud_ocup


def _norm_ocup(s: str) -> str:
    s = (s or '').lower()
    s = ''.join(c for c in _ud_ocup.normalize('NFD', s) if _ud_ocup.category(c) != 'Mn')
    s = _re_ocup.sub(r'/\s+', '/', s)
    return _re_ocup.sub(r'\s+', ' ', s).strip()


@app.route('/api/ocupaciones')
def api_ocupaciones():
    """F6: cerca de graus per ocupació/sortida professional (castellà).

    GET /api/ocupaciones?q=soldador
      → {"query": "soldador", "n": 8, "resultados": [
            {"grado": "C", "codigo": "FMEC0110", "id": 123,
             "denominacion": "...", "familia": "...", "ficha_url": null,
             "ocupaciones": ["Soldadores por TIG", ...]}, ...]}
    """
    q = request.args.get('q', '')
    tokens = [t for t in _norm_ocup(q).split() if len(t) >= 2]
    if not tokens:
        return jsonify({'query': q, 'n': 0, 'resultados': []})

    entries = _get_ocupaciones()
    # Match per paraula completa: cada token ha de ser una paraula del 'norm'.
    patterns = [_re_ocup.compile(r'\b' + _re_ocup.escape(t) + r'\b') for t in tokens]

    grouped: dict = {}
    for e in entries:
        hay = e.get('norm', '')
        if all(p.search(hay) for p in patterns):
            key = e['codigo'] if e['grado'] == 'C' else f"{e['grado']}-{e['id']}"
            g = grouped.setdefault(key, {
                'grado': e['grado'], 'codigo': e.get('codigo'), 'id': e.get('id'),
                'denominacion': e['denominacion'], 'familia': e.get('familia', ''),
                'ficha_url': e.get('ficha_url'), 'ocupaciones': [],
            })
            g['ocupaciones'].append(e['ocupacio'])

    resultados = sorted(grouped.values(), key=lambda g: -len(g['ocupaciones']))
    return jsonify({'query': q, 'n': len(resultados), 'resultados': resultados})
```

**Verifica** (en local, necessita `ocupaciones.json` del pas 2):
```bash
cd backend && python3 -c "
import os, json
os.environ['FLASK_ENV'] = 'testing'
import app
c = app.app.test_client()
r = c.get('/api/ocupaciones?q=soldador')
d = json.loads(r.data)
print('n:', d['n'])
print('primer:', d['resultados'][0]['denominacion'] if d['n'] else None)
assert d['n'] > 0, 'soldador hauria de retornar graus'
# Match per paraula: 'informatica' NO ha de coincidir amb 'bioinformatica' a soles
r2 = c.get('/api/ocupaciones?q=zzzznoexisteix')
assert json.loads(r2.data)['n'] == 0
print('OK')
"
```
Esperat: `n: 8` (aprox.), un grau de soldadura com a primer, `OK`.

---

## Pas 4: Frontend — crear `frontend/ocupacions.html`

Crea la pàgina modelant-la sobre `frontend/seguiment.html` (copia'n topbar,
selector d'idioma, estils base i footer). El cos: un camp de cerca i una llista
de targetes de resultats. Estructura mínima de la lògica (vanilla JS, sense
frameworks — consistent amb el projecte; Alpine només s'usa a `index.html`):

```html
<main class="content">
  <header class="hero">
    <h1 data-i18n="ocupacions.hero.h1">Cerca per ocupació</h1>
    <p class="hero-sub" data-i18n="ocupacions.hero.sub">Escriu què vols fer i descobreix quins graus FP hi porten.</p>
  </header>
  <input id="q" type="search" data-i18n-placeholder="ocupacions.placeholder"
         placeholder="soldador, programador, cuidador…" autofocus>
  <p class="meta" id="meta"></p>
  <div id="results"></div>
</main>

<script src="i18n.js"></script>
<script>
  // API_BASE: línia EXACTA, idèntica a la de seguiment.html (NO copiïs l'embolcall
  // IIFE — aquest <script> és scope global de la pàgina). Verificat a seguiment.html.
  const API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:5001' : '';

  const qEl = document.getElementById('q');
  const meta = document.getElementById('meta');
  const results = document.getElementById('results');
  let timer;

  function esc(s){ return (s||'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

  function fichaHref(g){
    if (g.grado === 'C' && g.codigo)
      return API_BASE + '/api/ficha-redirect?grado=C&codigo=' + encodeURIComponent(g.codigo);
    return g.ficha_url || '#';
  }

  async function go(q){
    const r = await fetch(API_BASE + '/api/ocupaciones?q=' + encodeURIComponent(q));
    const d = await r.json();
    meta.textContent = t('ocupacions.meta', { n: d.n });
    if (!d.n){ results.innerHTML = '<div class="empty">' + esc(t('ocupacions.empty')) + '</div>'; return; }
    results.innerHTML = d.resultados.map(g => `
      <div class="card">
        <a href="${esc(fichaHref(g))}" target="_blank" rel="noopener"><h3>${esc(g.denominacion)}</h3></a>
        <div class="code">${esc(g.grado)} · ${g.ocupaciones.length}</div>
        <div class="matches">${g.ocupaciones.map(m => '<span class="m">'+esc(m)+'</span>').join('')}</div>
      </div>`).join('');
  }

  qEl.addEventListener('input', e => {
    clearTimeout(timer);
    const v = e.target.value.trim();
    timer = setTimeout(() => { if (v) go(v); else { meta.textContent=''; results.innerHTML=''; } }, 200);
  });
</script>
```

Notes IMPORTANTS sobre i18n (verificat a `i18n.js` i `seguiment.html`):
- L'API real és **`window.t(key, vars)`** (global). **NO existeix cap `applyI18n()`** —
  no la cridis. `i18n.js` aplica `data-i18n` UN sol cop al `DOMContentLoaded` (sobre
  l'HTML estàtic de la pàgina). Per tant el contingut injectat dinàmicament (les
  targetes, el missatge buit) s'ha de traduir amb **`t('clau')` inline en el moment
  de construir l'string** — tal com fa `seguiment.html` (p.ex. `t('seguiment.empty')`).
  El codi de dalt ja ho fa correctament; NO el canviïs per `data-i18n`.
- Els `data-i18n` / `data-i18n-placeholder` de l'HTML ESTÀTIC (hero, placeholder,
  títol) sí funcionen automàticament: no cal fer res més.
- Reaprofita els estils `.card`, `.hero`, `.meta`, `.empty`, `.m` definint-los al
  `<style>` de la pàgina copiant l'estètica de `seguiment.html` (mateixes variables
  CSS `--dark`, `--warm`, etc.). El CSS de targetes de
  `.planning/spikes/003-reverse-search-feel/index.html` és una referència visual provada.

**Verifica** (necessita DOS processos alhora — backend a :5001 i frontend a :8000,
perquè les pàgines detecten `localhost` per apuntar `API_BASE` a `:5001`; obrir amb
`file://` NO funciona):
```bash
# Terminal A — backend:
cd backend && python3 app.py            # escolta a :5001
# Terminal B — frontend estàtic:
cd frontend && python3 -m http.server 8000
```
Després obre **`http://localhost:8000/ocupacions.html`** al navegador, cerca
"soldador" → apareixen targetes amb graus de soldadura, cada títol enllaça a la
fitxa. Comprova la consola del navegador: cap error (especialment cap
`ReferenceError`).

---

## Pas 5: i18n — claus de la pàgina nova (CA + ES)

A `frontend/i18n.js`, afegeix al bloc català (`ca`) i al castellà (`es`) les
mateixes claus (busca com s'estructuren els dos blocs; afegeix a cadascun):

Bloc `ca`:
```javascript
'ocupacions.hero.h1': 'Cerca per ocupació',
'ocupacions.hero.sub': 'Escriu què vols fer i descobreix quins graus FP hi porten.',
'ocupacions.placeholder': 'soldador, programador, cuidador…',
'ocupacions.meta': '{n} graus amb ocupacions que coincideixen',
'ocupacions.empty': 'Cap resultat. Prova un altre terme (en castellà).',
'page.title.ocupacions': 'Cerca per ocupació — Cercador Graus FP',
'index.footer.ocupacions': 'Cerca per ocupació',
```

Bloc `es`:
```javascript
'ocupacions.hero.h1': 'Búsqueda por ocupación',
'ocupacions.hero.sub': 'Escribe qué quieres hacer y descubre qué grados FP te llevan.',
'ocupacions.placeholder': 'soldador, programador, cuidador…',
'ocupacions.meta': '{n} grados con ocupaciones que coinciden',
'ocupacions.empty': 'Sin resultados. Prueba otro término.',
'page.title.ocupacions': 'Búsqueda por ocupación — Buscador Grados FP',
'index.footer.ocupacions': 'Búsqueda por ocupación',
```

Nota sobre la clau `index.footer.ocupacions`: és la del nou enllaç del footer
d'`index.html` (Pas 6); va al namespace `index.footer.*` per coherència amb les
claus de footer existents (`index.footer.historial`, `index.footer.obs`).

**Nota d'idioma**: les DADES són només en castellà (decisió MVP). El text d'UI sí
es tradueix; els resultats sempre surten en castellà. La clau `ocupacions.empty`
en català recorda a l'usuari que provi en castellà.

**Verifica** (les 7 claus han d'existir als DOS blocs → 2 coincidències cadascuna):
```bash
for k in ocupacions.hero.h1 ocupacions.hero.sub ocupacions.placeholder \
         ocupacions.meta ocupacions.empty page.title.ocupacions index.footer.ocupacions; do
  n=$(grep -c "'$k'" frontend/i18n.js)
  echo "$k → $n"; [ "$n" -eq 2 ] || echo "  ⚠ esperat 2 (un a ca, un a es)"
done
```
Esperat: cada clau `→ 2`, cap advertiment. (NO usis `node -e require` — `i18n.js`
és un IIFE de navegador que depèn de `window`/`document` i peta sota Node.)

---

## Pas 6: Enllaç des de `index.html`

**ATENCIÓ**: la topbar d'`index.html` NO té enllaços entre pàgines (només logo +
`#auth-widget` + selector d'idioma). Els enllaços a altres pàgines viuen al
**footer**. Afegeix el nou enllaç AL FOOTER, al costat d'`observatori.html`.

Localitza el footer (aprox. línies 2099–2104). Té aquesta forma EXACTA:

```html
<footer style="border-top:1px solid var(--border); padding:20px 48px; text-align:right;">
  <a href="historial.html" style="font-size:13px; color:var(--warm); text-decoration:none;"
    data-i18n="index.footer.historial">Historial d'actualitzacions</a>
  <a href="observatori.html" style="font-size:13px; color:var(--warm); text-decoration:none; margin-left:30px;"
    data-i18n="index.footer.obs">Observatori</a>
</footer>
```

Afegeix un tercer `<a>` **just després** del d'observatori, copiant exactament els
estils inline (incloent `margin-left:30px;`):

```html
  <a href="ocupacions.html" style="font-size:13px; color:var(--warm); text-decoration:none; margin-left:30px;"
    data-i18n="index.footer.ocupacions">Cerca per ocupació</a>
```

El resultat: tres enllaços al footer (historial · observatori · cerca per ocupació).

**Verifica**: obre `index.html` (servit a `http://localhost:8000/index.html`, com al
Pas 4), confirma que apareix l'enllaç "Cerca per ocupació" al footer i que porta a
`ocupacions.html`. NO toquis cap altra cosa d'`index.html`.

---

## Pas 7: Tests — `backend/tests/test_api.py`

Localitza el patró dels tests existents (com es crea el `client`, com es fan
servir mocks de fitxers — busca `test_itinerari_*` o `mock_open`). Afegeix al
final del fitxer dos tests nous per a `/api/ocupaciones`, fent mock de
`_get_ocupaciones` perquè no depenguin de xarxa ni de `ocupaciones.json`:

```python
_FAKE_OCUP = [
    {'ocupacio': 'Soldador por TIG', 'norm': 'soldador por tig', 'grado': 'C',
     'codigo': 'FMEC0110', 'id': 1, 'denominacion': 'Soldadura TIG', 'ficha_url': None, 'familia': 'FME'},
    {'ocupacio': 'Soldador por MIG', 'norm': 'soldador por mig', 'grado': 'C',
     'codigo': 'FMEC0110', 'id': 1, 'denominacion': 'Soldadura TIG', 'ficha_url': None, 'familia': 'FME'},
    {'ocupacio': 'Programador web', 'norm': 'programador web', 'grado': 'D',
     'codigo': None, 'id': 99, 'denominacion': 'DAW', 'ficha_url': 'https://x/daw', 'familia': 'IFC'},
]


def test_ocupaciones_match_agrupa_per_grau(client, monkeypatch):
    """F6: 'soldador' retorna el grau C agrupant les seves 2 ocupacions."""
    import app as flask_app_module
    monkeypatch.setattr(flask_app_module, "_get_ocupaciones", lambda: _FAKE_OCUP)
    r = client.get('/api/ocupaciones?q=soldador')
    assert r.status_code == 200
    d = r.get_json()
    assert d['n'] == 1
    res = d['resultados'][0]
    assert res['codigo'] == 'FMEC0110'
    assert len(res['ocupaciones']) == 2


def test_ocupaciones_match_paraula_completa(client, monkeypatch):
    """F6: el match és per paraula completa, no substring."""
    import app as flask_app_module
    monkeypatch.setattr(flask_app_module, "_get_ocupaciones", lambda: _FAKE_OCUP)
    # 'program' (substring de 'programador') NO ha de coincidir (vora de paraula)
    assert client.get('/api/ocupaciones?q=program').get_json()['n'] == 0
    # 'programador' sí
    assert client.get('/api/ocupaciones?q=programador').get_json()['n'] == 1
    # query buida → 0
    assert client.get('/api/ocupaciones?q=').get_json()['n'] == 0
```

Nota: si el patró de `client`/`monkeypatch` del fitxer és diferent (p.ex. fixture
`client` definida a `conftest.py`), adapta-t'hi. NO canviïs la lògica de les
assertions.

**Verifica**:
```bash
cd backend && python3 -m pytest tests/test_api.py -q
```
Esperat: tots passen, incloent els 2 nous.

**Verifica suite completa**:
```bash
cd backend && python3 -m pytest tests/ -q
```
Esperat: exit 0, cap regressió (+2 tests).

---

## Pas 8: Nota de desplegament al VPS

Afegeix a `plans/instructions.md` (secció de passos manuals al servidor) o a la
documentació de desplegament existent:

> **ocupaciones.json (Pla 047)**: Després del primer desplegament, executa al VPS:
> ```bash
> cd /ruta/al/repo
> python3 scripts/generate_ocupaciones.py
> ```
> Triga ~2-3 min. Genera `backend/data/ocupaciones.json`. No cal rellançar el
> servei (Flask llegeix el fitxer amb cache per mtime). Re-executa el script si
> s'actualitza el catàleg de certificats o cicles.

---

## Test plan

- **`test_api.py`** (pas 7), modelats sobre els tests `test_itinerari_*` existents:
  - `test_ocupaciones_match_agrupa_per_grau` — happy path: agrupa ocupacions per grau.
  - `test_ocupaciones_match_paraula_completa` — la regressió clau del MVP: match per
    paraula completa (no substring), i query buida → 0.
- Verificació final: `cd backend && python3 -m pytest tests/ -q` → exit 0, +2 tests.

## Criteris de DONE

ALL han de complir-se:

- [ ] `python3 scripts/generate_ocupaciones.py --dry-run 5` → exit 0, "Font C" i "Font D/E" >0
- [ ] `backend/data/ocupaciones.json` existeix amb ≥3.500 entrades (run complet)
- [ ] Cap CNO residual al text (assert del pas 2 passa)
- [ ] `GET /api/ocupaciones?q=soldador` retorna `n>0` amb graus de soldadura
- [ ] `GET /api/ocupaciones?q=program` retorna `n==0` (match per paraula, no substring)
- [ ] `cd backend && python3 -m pytest tests/ -q` → exit 0, +2 tests nous
- [ ] Servint frontend a `:8000` + backend a `:5001`: `http://localhost:8000/ocupacions.html`, cerca "soldador" mostra targetes amb enllaç a fitxa; consola del navegador sense errors (cap `ReferenceError`)
- [ ] Les 7 claus i18n noves existeixen 2 cops cadascuna (`for`-loop del Pas 5 sense advertiments)
- [ ] Enllaç "Cerca per ocupació" visible al footer d'`index.html` i porta a `ocupacions.html`
- [ ] Cap fitxer fora de la llista "In scope" modificat (`git diff --name-only`)
- [ ] `plans/README.md` actualitzat amb estat `DONE` per al pla 047

## Condicions STOP

Atura't i reporta (no improvisis) si:

- **Drift**: algun fitxer de l'àmbit ha canviat des de `425f825` i el codi no
  coincideix amb els excerpts de "Current state".
- **Font C 0%** al dry-run: l'endpoint `/pdfPT` o el bootstrap del scraper han
  canviat. Comprova `curl -sI https://www.todofp.es/buscadorcertificados/buscador`.
- **Cobertura C <90%** al run complet: investiga si `todofp.es` ha canviat el
  format dels PDFs (text → imatge); reporta.
- **L'assert de CNO residual falla**: hi ha un format CNO no cobert per
  `_CNO_CLEAN`. Afegeix el format observat al regex i re-executa.
- **El patró de mock de `test_api.py` no encaixa** amb `_FAKE_OCUP`: revisa com
  els tests existents mockegen i adapta, sense canviar les assertions.
- **`API_BASE` o `t()` no existeixen** a la pàgina nova tal com els uses: revisa
  `seguiment.html` per veure el patró real i adapta-t'hi.

## Notes de manteniment

- **Pipeline**: `ocupaciones.json` NO es regenera al refresh diari (per disseny —
  scraping car). Re-executar `generate_ocupaciones.py` manualment quan canviï el
  catàleg.
- **2a iteració (NO en aquest pla)**: capa de sinònims/traducció CA↔ES (ara una
  query en català retorna 0 — vist a l'spike 003); rànquing semàntic (ex.
  "cuidador" retorna cuidadors d'animals abans que de persones); reconciliació
  fina de codis `/busquedaCP` que no casen amb `ofertes.json` (mostren codi en
  lloc de denominació). Tot documentat a `.planning/spikes/003-reverse-search-feel/README.md`.
- **Graus A/B**: no tenen ocupació pròpia (són fragments de C). Si es vol, una
  iteració futura pot fer-los heretar les ocupacions del seu C pare via el mapeig
  de F5 (`bc_loe.json` invers). Fora d'abast aquí.
- **Revisar en PR**: que el match per paraula (`\b`) no trenqui amb termes amb
  guió o barra ("auxiliar/a"); que la pàgina nova reaprofiti i18n i no introdueixi
  literals sense traduir; que `ocupaciones.json` no s'hagi committejat.
```

