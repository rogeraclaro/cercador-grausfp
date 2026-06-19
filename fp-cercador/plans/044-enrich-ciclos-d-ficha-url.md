# Pla 044: Enriquir ciclos_fp.json amb ficha_url de cada cicle D

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: 043 DONE
- **Category**: feature
- **Planned at**: commit `500127b`, 2026-06-19

---

## Per què importa

Quan l'usuari obre el panell "Cicles FP (D)" per a un Grado C LOE, la llista
mostra el nom i la família del cicle D però **no té cap link a la fitxa oficial**.
El spike 043 ha confirmat que `ciclosFP` retorna una denominació (`cells[0]`)
que coincideix amb un fragment de la `denominacion` dels registres D, i que
els 195 registres D de `ofertes.json` tots tenen `ficha_url`. El match és viable
i l'esforç és mínim: ampliar `fetch_ciclos_fp` per afegir `ficha_url` a cada
cicle i actualitzar el frontend per renderitzar-lo com a link.

---

## Current state — excerpts del codi rellevant

### `fetch_ciclos_fp` (backend/scrapers/certificados_scraper.py:105–124)

```python
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
```

**La cel·la `cells[2]` és ignorada.** Conté el mòdul professional, ex:
`"3006 - Preparación de pedidos y venta de productos"`. No es necessita per
a aquest pla però el pla 045 (B→C via PDF) la necessitarà.

### `build_ciclos_index` (backend/scrapers/certificados_scraper.py:127–148)

```python
def build_ciclos_index(cert_data: dict[str, dict]) -> dict[str, list[dict]]:
    """
    {codigo_C: [{'denominacion': str, 'familia': str}]}
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

Actualment `build_ciclos_index` no rep cap referència a `ofertes.json` — no pot
construir el D-index sense rebre-la com a paràmetre.

### Crida a `build_ciclos_index` (backend/scrapers/pipeline.py:156–165)

```python
try:
    from scrapers.certificados_scraper import build_ciclos_index
    ciclos_index = build_ciclos_index(cert_data)
    ciclos_path = os.path.join(os.path.dirname(DATA_PATH), 'ciclos_fp.json')
    with open(ciclos_path, 'w', encoding='utf-8') as f:
        import json as _json
        _json.dump(ciclos_index, f, ensure_ascii=False)
    logger.info("pipeline: ciclos_fp.json escrit (%d entrades)", len(ciclos_index))
except Exception as exc:
    logger.warning("pipeline: build_ciclos_index ha fallat (no fatal): %s", exc)
```

Aquí hi ha accés a `all_records` (la llista completa d'`ofertes.json`) just
**damunt** d'aquest bloc — pot passar-se a `build_ciclos_index` sense cap
refactor adicional.

### Rendering ciclos_d al frontend (frontend/index.html:~1737–1748)

```html
<template x-for="cicle in ciclosDData[row.codigo]" :key="cicle.denominacion">
  <li x-text="cicle.denominacion + (cicle.familia ? ' (' + cicle.familia + ')' : '')"></li>
</template>
```

Cada `cicle` ara és `{denominacion, familia}`. Caldrà afegir `ficha_url` i
renderitzar un `<a>` si és present.

### PREFIX_MAP (backend/scrapers/families.py:13–)

```python
PREFIX_MAP = {
    'ADG': 'Administración y Gestión',
    # ... 24 famílies
}
```

Confirmat al spike 043: `cells[1]` de ciclosFP pot ser el codi abreujat
(`'ADG'`) **o** el nom llarg (`'Administración y Gestión'`). El D-index
usarà la denominació (cells[0]) com a clau primària; la família servirà
únicament per a desambiguació en cas de col·lisió.

---

## Estratègia de match (confirmada al spike 043)

El spike 043 ha confirmat que:
- Les `ficha_url` dels 195 D tenen format semàntic, sense números: ex.
  `.../administracion-gestion/servicios-administrativos.html`
- `cells[0]` de ciclosFP = fragment curt de la denominació D: ex.
  `"Servicios Administrativos"`
- La denominació completa del registre D és: ex.
  `"Título Profesional Básico en Servicios Administrativos"`
- Strip dels prefixos canònics + lookup per denominació curta → match 2/2
  del cas de validació COML0110

**D-index**: `{denominacion_curta.lower(): ficha_url}` on `denominacion_curta`
s'obté eliminant els prefixos `'Título Profesional Básico en '`,
`'Técnico en '`, `'Técnico Superior en '` de la denominació completa del D.

Si existeix col·lisió (dos D amb el mateix nom curt però diferent família),
el pla preveu un segon nivell: `{(denominacion_curta.lower(), familia.lower()): ficha_url}`.
Escapa hatches: si cap dels dos nivells dona resultat, `ficha_url = None`
(el cicle es mostra sense link, com fins ara).

---

## Àmbit

**In scope** (els ÚNICS fitxers a modificar):
- `backend/scrapers/certificados_scraper.py` — `fetch_ciclos_fp` i `build_ciclos_index`
- `backend/scrapers/pipeline.py` — passa `all_records` a `build_ciclos_index`
- `frontend/index.html` — renderitza `ficha_url` com a `<a>` si és present

**Out of scope** (NO tocar):
- `backend/app.py` — l'endpoint `/api/itinerari` ja retorna `ciclos_index.get(codigo, [])` directament; no cal canviar-lo
- `backend/data/ofertes.json`, `backend/data/ciclos_fp.json` — no editar manualment
- `backend/scrapers/families.py` — llegit com a referència, no modificat
- Qualsevol altre fitxer

---

## Pas 1: Afegeix `_build_d_index` a certificados_scraper.py

Afegeix la funció **abans de `fetch_ciclos_fp`** (a la línia ~104, just
sobre la funció existent):

```python
_D_PREFIXES = (
    'Título Profesional Básico en ',
    'Técnico Superior en ',
    'Técnico en ',
)


def _build_d_index(records: list[dict]) -> dict:
    """
    Construeix un índex per trobar la ficha_url d'un cicle D a partir del
    nom curt que retorna ciclosFP.

    Retorna dos nivells:
      primary:   {denominacion_curta.lower(): ficha_url}
      secondary: {(denominacion_curta.lower(), familia.lower()): ficha_url}

    La denominació curta s'obté eliminant els prefixos canònics de la
    denominació completa del registre D.
    """
    primary: dict[str, str] = {}
    secondary: dict[tuple, str] = {}
    for r in records:
        if r.get('grado') != 'D':
            continue
        ficha_url = r.get('ficha_url')
        if not ficha_url:
            continue
        den = r.get('denominacion') or ''
        fam = (r.get('familia') or '').lower()
        short = den
        for prefix in _D_PREFIXES:
            if den.startswith(prefix):
                short = den[len(prefix):]
                break
        key = short.lower()
        primary[key] = ficha_url
        secondary[(key, fam)] = ficha_url
    return {'primary': primary, 'secondary': secondary}
```

**Verifica** (sense xarxa): el fitxer ha de parsejar sense errors de sintaxi.
```bash
python3 -c "import sys; sys.path.insert(0,'backend'); from scrapers.certificados_scraper import _build_d_index; print('ok')"
```
Esperat: `ok`

---

## Pas 2: Modifica `fetch_ciclos_fp` per acceptar el D-index i afegir ficha_url

Modifica la signatura i el cos de `fetch_ciclos_fp` (certificados_scraper.py:105–124):

**Reemplaça** el fragment actual:

```python
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
```

**Per**:

```python
def fetch_ciclos_fp(
    session: requests.Session,
    cert_id: int,
    timeout: int = 20,
    d_index: dict | None = None,
) -> list[dict]:
    """
    POST /ciclosFP per a un cert_id → llista de cicles D que el convaliden.
    Cada cicle: {'denominacion': str, 'familia': str, 'ficha_url': str | None}

    d_index: sortida de _build_d_index(). Si és None, ficha_url serà None.
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
    primary   = (d_index or {}).get('primary', {})
    secondary = (d_index or {}).get('secondary', {})

    for row in soup.select('table tr'):
        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
        if len(cells) >= 2 and cells[0] and cells[0] != 'Ciclo formativo':
            den = cells[0]
            fam = cells[1] if len(cells) > 1 else ''
            key_primary = den.lower()
            key_secondary = (key_primary, fam.lower())
            ficha_url = secondary.get(key_secondary) or primary.get(key_primary)
            ciclos.append({'denominacion': den, 'familia': fam, 'ficha_url': ficha_url})
    return ciclos
```

**Verifica** sintaxi:
```bash
python3 -c "import sys; sys.path.insert(0,'backend'); from scrapers.certificados_scraper import fetch_ciclos_fp; print('ok')"
```
Esperat: `ok`

---

## Pas 3: Modifica `build_ciclos_index` per acceptar i passar el D-index

**Reemplaça** el fragment actual (certificados_scraper.py:127–148):

```python
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

**Per**:

```python
def build_ciclos_index(
    cert_data: dict[str, dict],
    all_records: list[dict] | None = None,
) -> dict[str, list[dict]]:
    """
    Per a cada codi C LOE (clau de cert_data), crida ciclosFP i retorna
    {codigo_C: [{'denominacion': ..., 'familia': ..., 'ficha_url': ...}]}.

    cert_data:   sortida de fetch_all() → {codigo: {'cert_id': int, ...}}
    all_records: llista completa d'ofertes (conté els registres D amb ficha_url).
                 Si és None, ficha_url serà None per a tots els cicles.
    """
    if not cert_data:
        return {}

    d_index = _build_d_index(all_records) if all_records else None
    session = _bootstrap_session()
    result = {}
    for codigo, data in cert_data.items():
        cert_id = data.get('cert_id')
        if not cert_id:
            continue
        ciclos = fetch_ciclos_fp(session, cert_id, d_index=d_index)
        result[codigo] = ciclos
        logger.debug("build_ciclos_index: %s → %d cicles", codigo, len(ciclos))

    logger.info("build_ciclos_index: %d certificats processats", len(result))
    return result
```

**Verifica** sintaxi:
```bash
python3 -c "import sys; sys.path.insert(0,'backend'); from scrapers.certificados_scraper import build_ciclos_index; print('ok')"
```
Esperat: `ok`

---

## Pas 4: Passa `all_records` a `build_ciclos_index` des de pipeline.py

**Localitza** el bloc (pipeline.py:~156–165):

```python
        try:
            from scrapers.certificados_scraper import build_ciclos_index
            ciclos_index = build_ciclos_index(cert_data)
```

**Modifica únicament la crida** (una línia):

```python
        try:
            from scrapers.certificados_scraper import build_ciclos_index
            ciclos_index = build_ciclos_index(cert_data, all_records=all_records)
```

Cap altra modificació a pipeline.py.

**Verifica** sintaxi:
```bash
python3 -c "import sys; sys.path.insert(0,'backend'); from scrapers.pipeline import run; print('ok')"
```
Esperat: `ok`

---

## Pas 5: Actualitza el frontend per renderitzar `ficha_url`

**Localitza** el bloc (frontend/index.html:~1737–1742):

```html
<template x-for="cicle in ciclosDData[row.codigo]" :key="cicle.denominacion">
  <li x-text="cicle.denominacion + (cicle.familia ? ' (' + cicle.familia + ')' : '')"></li>
</template>
```

**Reemplaça per**:

```html
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
```

Aquesta implementació és retrocompatible: si `ficha_url` és `null` o absent
(cicles ja en `ciclos_fp.json` antics sense el camp), es mostra com a text pla.

---

## Pas 6: Verifica el pipeline en local (sense desplegament)

Executa una verificació ràpida del D-index sense fer cap crida de xarxa:

```bash
python3 -c "
import sys, json
sys.path.insert(0, 'backend')
from scrapers.certificados_scraper import _build_d_index
records = json.load(open('backend/data/ofertes.json'))
idx = _build_d_index(records)
print('primary keys:', len(idx['primary']))
print('secondary keys:', len(idx['secondary']))
# Valida el cas confirmat al spike 043
print('Lookup Servicios Administrativos:', idx['primary'].get('servicios administrativos', 'NO TROBAT'))
print('Lookup Servicios Comerciales:', idx['primary'].get('servicios comerciales', 'NO TROBAT'))
"
```

**Esperat**:
- `primary keys`: entre 50 i 195 (un per a cada D amb ficha_url)
- `secondary keys`: igual o superior a `primary keys`
- `Lookup Servicios Administrativos`: una URL de `todofp.es` (no `NO TROBAT`)
- `Lookup Servicios Comerciales`: una URL de `todofp.es`

Si `NO TROBAT`, **STOP i reporta** — el strip de prefixos no ha funcionat
per a algun d'aquests registres; inclou l'output complet de la verificació.

---

## Criteris de DONE

- [ ] `python3 -c "from scrapers.certificados_scraper import _build_d_index, fetch_ciclos_fp, build_ciclos_index; print('ok')"` → `ok`
- [ ] `python3 -c "from scrapers.pipeline import run; print('ok')"` → `ok`
- [ ] Verificació D-index: `primary keys` ≥ 100 (no cap registre D perdut per error de strip)
- [ ] Lookup "servicios administrativos" i "servicios comerciales" → URLs vàlides (no `NO TROBAT`)
- [ ] `git diff --name-only` mostra únicament: `backend/scrapers/certificados_scraper.py`, `backend/scrapers/pipeline.py`, `frontend/index.html`
- [ ] Cap fitxer de tests, cap fitxer de dades (`ofertes.json`, `ciclos_fp.json`) modificat
- [ ] El `<li>` del frontend renderitza `<a>` amb `href` quan `ficha_url` és present i `<span>` quan és `null`

---

## Condicions STOP

Atura't i reporta si:

- La verificació D-index retorna `primary keys < 50` — indica que `_build_d_index` no troba els D o que els registres D no tenen `ficha_url`.
- El lookup de "servicios administrativos" retorna `NO TROBAT` — el strip de prefixos no coincideix amb les denominacions reals; inclou la denominació completa del registre D amb família "Administración y Gestión" per diagnosticar.
- `python3 -c "from scrapers.pipeline import run"` eleva `SyntaxError` o `ImportError` — la modificació de pipeline.py té un error de sintaxi.
- El bloc `x-for` del frontend té un error de sintaxi Alpine (no es renderitza cap `<li>`) — inclou el fragment modificat per a revisió.

---

## Test plan

No hi ha suite de tests al projecte. La verificació és manual:

1. **Test de la funció D-index** (pas 6, sense xarxa): confirma cobertura i lookup.
2. **Test d'integració manual** (opcional, requereix xarxa): fer un `refresh` complet via `/api/admin/refresh` i verificar que `ciclos_fp.json` conté entrades amb `ficha_url` no nul·la. Ex:
   ```bash
   python3 -c "
   import json
   idx = json.load(open('backend/data/ciclos_fp.json'))
   sample = next((v for v in idx.values() if any(c.get('ficha_url') for c in v)), None)
   print(sample)
   "
   ```
   Esperat: almenys un cicle amb `ficha_url` diferent de `null`.

---

## Notes de manteniment

- **Retrocompatibilitat**: `ciclos_fp.json` existent (si el servidor el té generat sense `ficha_url`) seguirà funcionant al frontend (el `<template x-if="!cicle.ficha_url">` mostra text pla). Cal un nou refresh per regenerar-lo amb urls.
- **Pla 045 (B→C LOE via Annexo PDF)**: `fetch_ciclos_fp` ara guarda `cells[2]` implícitament (el num mòdul). El pla 045 podrà ampliar el dict per afegir `modul_num` parsejant `cells[2]` amb `re.search(r'^(\d{4})\s*-', cells[2])`.
- **Famílies abreujades**: si algun cells[1] és un codi abreujat com `'ADG'` en lloc del nom llarg `'Administración y Gestión'`, el `key_secondary` no encertarà. En aquest cas el `primary` (per denominació sola) sí funcionarà. La cobertura alta (>90%) és l'objectiu; un 100% no és crític.
- **Nous registres D**: cada vegada que el pipeline fa un refresh, `_build_d_index` es reconstrueix des d'`all_records` fresc — no cal cap manteniment addicional.
