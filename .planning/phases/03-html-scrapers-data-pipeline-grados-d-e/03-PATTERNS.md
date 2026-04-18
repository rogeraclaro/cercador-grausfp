# Phase 3: HTML Scrapers + Data Pipeline (Grados D, E) - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 5 (2 nous, 3 modificacions)
**Analogs found:** 5 / 5

---

## File Classification

| Nou/Modificat | Rol | Data Flow | Analog més proper | Qualitat |
|---------------|-----|-----------|-------------------|---------|
| `fp-cercador/backend/scrapers/html_scraper.py` | service | request-response + transform | `fp-cercador/backend/scrapers/pdf_scraper.py` | role-match |
| `fp-cercador/backend/scrapers/pipeline.py` | service | CRUD + orchestration | `fp-cercador/backend/scrapers/pipeline.py` (si mateix, extensió in-place) | exact |
| `fp-cercador/backend/tests/test_html_scraper.py` | test | unit | `fp-cercador/backend/tests/test_pdf_scraper.py` | role-match |
| `fp-cercador/backend/tests/conftest.py` | test | fixture | `fp-cercador/backend/tests/conftest.py` (si mateix, extensió) | exact |
| `fp-cercador/backend/.env.example` | config | — | `fp-cercador/backend/.env.example` (si mateix, extensió) | exact |

---

## Pattern Assignments

### `fp-cercador/backend/scrapers/html_scraper.py` (service, request-response + transform)

**Analog:** `fp-cercador/backend/scrapers/pdf_scraper.py`

**Patró d'imports** (linies 1-19 de pdf_scraper.py):
```python
"""
html_scraper.py — Parsing de pàgines HTML dels Grados D i E del sistema FP espanyol.

Exposa:
  parse_grado_d_basico(url: str) -> list[dict]
  parse_grado_d_medio(url: str) -> list[dict]
  parse_grado_d_superior(url: str) -> list[dict]
  parse_grado_e(url: str) -> list[dict]

Cada registre retornat té exactament:
  {denominacion, familia, nivel, codigo, plan_antiguo, observaciones}

Camp 'id' i 'grado' els afegeix pipeline.py, NO aquest mòdul.
"""
import logging
import requests
from bs4 import BeautifulSoup
from scrapers.pdf_scraper import PREFIX_MAP

logger = logging.getLogger(__name__)
```

**Constants — HTML_FAMILY_ALIASES** (patró consistent amb PREFIX_MAP de pdf_scraper.py linies 25-55):
```python
# 3 noms de família en l'HTML que no coincideixen literalment amb PREFIX_MAP.
# difflib produeix resultats incorrectes per a aquests casos (vegeu RESEARCH.md).
HTML_FAMILY_ALIASES = {
    "Imagen y Sonido": "Imagen y Espectáculos",
    "Artes y Artesanias": "Artesanía",
    # "Mantenimiento y Servicios a la Producción": comportament a confirmar amb usuari
    # Opció A: deixar-la com a "Desconeguda" (consistent amb D-08)
    # Opció B: preservar el nom original com a nou valor
}
```

**Funció privada central — _build_fam_map** (patró equivalent a _extract_records de pdf_scraper.py linia 130):
```python
def _build_fam_map(soup: BeautifulSoup) -> dict:
    """
    Retorna {fam_id: nom_canonic} per a tots els <th headers='familia'>.
    Construeix el map UNICAMENT de <th headers="familia"> — filtra
    automaticament el logo de capcelera <img alt="Logotipo de TodoFP">.
    """
    fam_map = {}
    for th in soup.find_all('th', attrs={'headers': 'familia'}):
        fam_id = th.get('id', '')
        img = th.find('img')
        if img:
            alt = img.get('alt', '')
            if alt.startswith('Logotipo '):
                raw = alt[len('Logotipo '):]
                fam_map[fam_id] = HTML_FAMILY_ALIASES.get(raw, raw)
    return fam_map
```

**Funció privada central — _extract_titols** (patró equivalent a _extract_records de pdf_scraper.py linia 130):
```python
def _extract_titols(soup: BeautifulSoup, fam_map: dict, nivel, grado: str) -> list[dict]:
    """
    Extreu tots els titols d'una pagina HTML del ministeri.

    IMPORTANT: headers_val es una AttributeValueList (llista), no un string.
    Cal tractar-ho amb isinstance (Pitfall 1 RESEARCH.md).
    """
    records = []
    for td in soup.find_all('td', attrs={'headers': True}):
        hv = td.get('headers', [])
        hl = hv if isinstance(hv, list) else hv.split()
        if 'titulacion' not in hl:
            continue
        fam_id = next((p for p in hl if p.startswith('fam')), None)
        a = td.find('a', id=lambda x: x and x.startswith('tit-'))
        if not a or not fam_id:
            continue
        familia = fam_map.get(fam_id, 'Desconeguda')
        if familia == 'Desconeguda':
            logger.warning(f"fam_id='{fam_id}' no resolt al Grado {grado}")
        records.append({
            'denominacion': a.get_text(strip=True),
            'familia': familia,
            'nivel': nivel,
            'codigo': None,
            'plan_antiguo': False,
            'observaciones': '',
        })
    return records
```

**Funció privada orquestradora — _parse_grado_d** (patró equivalent a _extract_records + _download_pdf de pipeline.py linies 61-72):
```python
def _parse_grado_d(url: str, nivel: int) -> list[dict]:
    """
    Funció generica interna per als 3 subtipus Grado D (estructura HTML identica).
    nivel: 1 (Basico), 2 (Medio), 3 (Superior).
    """
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()  # fail fast D-01
    soup = BeautifulSoup(resp.text, 'html.parser')
    fam_map = _build_fam_map(soup)
    return _extract_titols(soup, fam_map, nivel=nivel, grado='D')
```

**API publica — 4 funcions per subtipus** (patró equivalent a parse_grado_a/b/c de pdf_scraper.py linies 200-213):
```python
def parse_grado_d_basico(url: str) -> list[dict]:
    """Parseja la pagina HTML de Grado D Basico i retorna llista de registres."""
    return _parse_grado_d(url, nivel=1)

def parse_grado_d_medio(url: str) -> list[dict]:
    """Parseja la pagina HTML de Grado D Medio i retorna llista de registres."""
    return _parse_grado_d(url, nivel=2)

def parse_grado_d_superior(url: str) -> list[dict]:
    """Parseja la pagina HTML de Grado D Superior i retorna llista de registres."""
    return _parse_grado_d(url, nivel=3)

def parse_grado_e(url: str) -> list[dict]:
    """Parseja la pagina HTML de Grado E (Cursos d'Especialitzacio) i retorna llista de registres."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    fam_map = _build_fam_map(soup)
    return _extract_titols(soup, fam_map, nivel=None, grado='E')
```

**Gestio d'errors** (patró consistent amb pdf_scraper.py linia 178-181 i pipeline.py linia 69):
```python
# El raise_for_status() de requests propaga HTTPError (fail fast D-01).
# El warning de familia desconeguda no atura l'execucio (consistent amb D-08).
# NO hi ha try/except local — l'excepcio es propaga a pipeline.run() que decideix.
```

**HEADERS requerit** — copiar de pipeline.py (NO redefinir — importar o passar com a parametre):
```python
# HEADERS esta definit a pipeline.py linies 32-42.
# html_scraper.py ha d'importar-lo o rebre'l com a parametre per evitar duplicacio.
# Opcio recomanada: from scrapers.pipeline import HEADERS
# (si aixo crea dependencia circular, definir-lo en un modul utils.py compartit)
```

---

### `fp-cercador/backend/scrapers/pipeline.py` (service, orchestration — extensio in-place)

**Analog:** `fp-cercador/backend/scrapers/pipeline.py` (si mateix)

**Nous imports a afegir** (despres de la linia 24 — `from scrapers.pdf_scraper import ...`):
```python
# Afegir a continuacio de la linia 24 de pipeline.py
from scrapers.html_scraper import (
    parse_grado_d_basico,
    parse_grado_d_medio,
    parse_grado_d_superior,
    parse_grado_e,
)
```

**Noves constants HTML_URLS** (patró equivalent a PDF_URLS linies 44-48):
```python
# Afegir despres de PDF_URLS (linia 48 de pipeline.py)
HTML_URLS = {
    'D_BASICO':   os.getenv('URL_GRADO_D_BASICO',   'https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html'),
    'D_MEDIO':    os.getenv('URL_GRADO_D_MEDIO',    'https://www.todofp.es/que-estudiar/grados-d/grado-medio.html'),
    'D_SUPERIOR': os.getenv('URL_GRADO_D_SUPERIOR', 'https://www.todofp.es/que-estudiar/grados-d/grado-superior.html'),
    'E':          os.getenv('URL_GRADO_E',          'https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html'),
}
```

**Funcio privada _fetch_html** (nova, equivalent a _download_pdf linies 61-72 pero per HTML):
```python
def _fetch_html(url: str, timeout: int = 30) -> str:
    """
    Descarrega una pagina HTML i retorna el contingut com a string.
    A diferencia de _download_pdf, no escriu a disc — retorna el text directament.
    """
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()  # fail fast D-01
    return resp.text
```

**Extensio in-place de run()** — dict parsers (patró existent linies 120-142, extensio D/E):

Estructura actual (linies 120-124):
```python
parsers = {
    'A': (PDF_URLS['A'], parse_grado_a),
    'B': (PDF_URLS['B'], parse_grado_b),
    'C': (PDF_URLS['C'], parse_grado_c),
}
```

El loop de PDFs (linies 129-142) usa `_download_pdf` + fitxer temporal. Els HTML no usen fitxer temporal — cal un segon bloc o adaptar el loop. Recomanacio: separar el loop PDF del loop HTML per evitar complicar la logica del `finally` (que es especifica de PDFs):

```python
# --- Bloc HTML (D i E) — despres del loop PDF ---
html_parsers = {
    'D_BASICO':   (HTML_URLS['D_BASICO'],   parse_grado_d_basico,   'D'),
    'D_MEDIO':    (HTML_URLS['D_MEDIO'],    parse_grado_d_medio,    'D'),
    'D_SUPERIOR': (HTML_URLS['D_SUPERIOR'], parse_grado_d_superior, 'D'),
    'E':          (HTML_URLS['E'],          parse_grado_e,          'E'),
}

records_by_grado_html: dict = {'D': [], 'E': []}

for key, (url, parser_fn, grado_letter) in html_parsers.items():
    records = parser_fn(url)   # fail fast: excepcio es propaga (D-01)
    records_by_grado_html[grado_letter].extend(records)

for grado_letter, recs in records_by_grado_html.items():
    for r in recs:
        r['grado'] = grado_letter
    by_grado[grado_letter] = len(recs)
    all_records.extend(recs)
```

**Retorn actualitzat de run()** (linia 151-156, ara amb D i E a by_grado):
```python
# El retorn no canvia d'estructura — by_grado ara inclou D i E automaticament
return {
    "total": len(all_records),
    "by_grado": by_grado,   # {"A": N, "B": N, "C": N, "D": N, "E": N}
    "errors": [],
    "duration_seconds": round(time.time() - start, 2),
}
```

**Docstring de run() a actualitzar** (linies 98-116):
```python
# Actualitzar la linia "Grados A, B, C" → "Grados A, B, C, D, E"
# Actualitzar el retorn documentat:
#   "by_grado": {"A": int, "B": int, "C": int, "D": int, "E": int}
```

---

### `fp-cercador/backend/tests/test_html_scraper.py` (test, unit)

**Analog:** `fp-cercador/backend/tests/test_pdf_scraper.py` + `fp-cercador/backend/tests/test_pipeline.py`

**Patró d'imports** (consistent amb test_pdf_scraper.py linies 1-20):
```python
"""
test_html_scraper.py — Tests unitaris del html_scraper amb fixtures HTML minims.

Tests sense xarxa real: requests.get esta mockat en tots els tests.
Cobreix requisits HTML-01 a HTML-06.
"""
import pytest
from unittest.mock import patch, Mock
from scrapers.html_scraper import (
    parse_grado_d_basico,
    parse_grado_d_medio,
    parse_grado_d_superior,
    parse_grado_e,
    HTML_FAMILY_ALIASES,
    _build_fam_map,
    _extract_titols,
)
from bs4 import BeautifulSoup
```

**Patrons de constants HTML de fixture** (equivalent a les constants de taula a conftest.py):
```python
# Fragment HTML minim verificat contra l'estructura real de todofp.es (RESEARCH.md)
MINIMAL_HTML_BASICO = """
<html><body><table>
  <thead>
    <tr class="cols">
      <th id="familia">Familia</th>
      <th id="titulacion">Titulacion</th>
    </tr>
  </thead>
  <tbody>
    <tr class="fpb">
      <th rowspan="1" headers="familia" id="fam0">
        <img loading="lazy" alt="Logotipo Administracion y Gestion" src="#">
      </th>
      <td headers="titulacion fam0">
        <p><a id="tit-gestion-administrativa" href="#">Gestion Administrativa</a></p>
      </td>
    </tr>
  </tbody>
</table></body></html>
"""
```

**Patró de mock requests.get** (consistent amb test_pipeline.py linies 55-58):
```python
def _make_mock_response(html: str) -> Mock:
    mock_resp = Mock()
    mock_resp.text = html
    mock_resp.raise_for_status = Mock()
    return mock_resp

# Us en un test:
def test_parse_grado_d_basico_count():
    with patch('scrapers.html_scraper.requests.get', return_value=_make_mock_response(MINIMAL_HTML_BASICO)):
        result = parse_grado_d_basico('http://fake')
    assert len(result) == 1
```

**Patrons de test per requisit** (equivalent als test_prefix_map, test_plan_antiguo etc. de test_pdf_scraper.py):
```python
# HTML-01: compte de titols
def test_parse_grado_d_basico_count(): ...
def test_parse_grado_d_medio_count(): ...
def test_parse_grado_d_superior_count(): ...
def test_parse_grado_e_count(): ...

# HTML-03: identificacio per id="tit-*"
def test_tit_id_extraction(): ...

# HTML-04: familia correcta
def test_family_mapping_direct(): ...       # familia que coincideix directament
def test_family_mapping_alias_imagen(): ... # "Imagen y Sonido" → "Imagen y Espectaculos"
def test_family_mapping_alias_artes(): ...  # "Artes y Artesanias" → "Artesania"
def test_family_mapping_unknown(): ...      # familia no mapada → "Desconeguda"

# HTML-05: nivel correcte per subtipus
def test_nivel_basico_is_1(): ...
def test_nivel_medio_is_2(): ...
def test_nivel_superior_is_3(): ...
def test_nivel_grado_e_is_none(): ...

# HTML-06: camps fixes
def test_record_fields_codigo_none(): ...
def test_record_fields_plan_antiguo_false(): ...
def test_record_fields_observaciones_empty(): ...
```

---

### `fp-cercador/backend/tests/conftest.py` (test, fixture — extensio in-place)

**Analog:** `fp-cercador/backend/tests/conftest.py` (si mateix)

**Patrons nous a afegir** (consistent amb les fixtures existents linies 5-58):
```python
# Afegir al final de conftest.py — mateixa convenco de noms i docstring

@pytest.fixture
def minimal_html_grado_d_one_record():
    """HTML minim amb 1 titol de Grado D (estructura verificada contra todofp.es)."""
    return """
    <html><body><table>
      <thead><tr><th id="familia">Familia</th><th id="titulacion">Titulacion</th></tr></thead>
      <tbody>
        <tr>
          <th rowspan="1" headers="familia" id="fam0">
            <img alt="Logotipo Administracion y Gestion">
          </th>
          <td headers="titulacion fam0">
            <p><a id="tit-gestion-administrativa" href="#">Gestion Administrativa</a></p>
          </td>
        </tr>
      </tbody>
    </table></body></html>
    """

@pytest.fixture
def minimal_html_alias_familia():
    """HTML minim amb familia que requereix HTML_FAMILY_ALIASES (Imagen y Sonido)."""
    return """
    <html><body><table>
      <thead><tr><th id="familia">Familia</th><th id="titulacion">Titulacion</th></tr></thead>
      <tbody>
        <tr>
          <th rowspan="1" headers="familia" id="fam1">
            <img alt="Logotipo Imagen y Sonido">
          </th>
          <td headers="titulacion fam1">
            <p><a id="tit-realizacion" href="#">Realizacion de Audiovisuales</a></p>
          </td>
        </tr>
      </tbody>
    </table></body></html>
    """
```

---

### `fp-cercador/backend/.env.example` (config — extensio in-place)

**Analog:** `fp-cercador/backend/.env.example` (si mateix — linia 1)

**Extensio a afegir** (consistent amb el format existent d'una sola variable per linia):
```bash
# Afegir despres de la linia ADMIN_TOKEN=...
URL_GRADO_D_BASICO=https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html
URL_GRADO_D_MEDIO=https://www.todofp.es/que-estudiar/grados-d/grado-medio.html
URL_GRADO_D_SUPERIOR=https://www.todofp.es/que-estudiar/grados-d/grado-superior.html
URL_GRADO_E=https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html
```

---

## Shared Patterns

### Fail Fast (D-01)
**Font:** `fp-cercador/backend/scrapers/pipeline.py` linies 68-69
**Aplicar a:** `html_scraper.py` (totes les funcions parse_*), extensio de `pipeline.py`
```python
resp = requests.get(url, headers=HEADERS, timeout=timeout)
resp.raise_for_status()  # 4xx/5xx → excepcio (fail fast D-01)
```

### HEADERS HTTP
**Font:** `fp-cercador/backend/scrapers/pipeline.py` linies 32-42
**Aplicar a:** `html_scraper.py` (import de pipeline.py o modul compartit)
```python
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": (
        "https://www.todofp.es/catalogos-registros-sistema-fp/"
        "catalogo-nacional-ofertas-sistema.html"
    ),
}
```

### Warning per familia desconeguda (D-08)
**Font:** `fp-cercador/backend/scrapers/pdf_scraper.py` linies 178-181
**Aplicar a:** `html_scraper.py` funcion `_extract_titols`
```python
if not familia:
    logger.warning(
        f"Familia desconeguda per prefix '{prefix}' al codi '{clean_code}'"
    )
    familia = 'Desconeguda'
```

### Patrons de mock per a tests
**Font:** `fp-cercador/backend/tests/test_pipeline.py` linies 55-58 i linies 61-82
**Aplicar a:** `test_html_scraper.py`
```python
mock_response = mock.Mock()
mock_response.content = fake_content
mock_response.raise_for_status = mock.Mock()

with mock.patch('scrapers.html_scraper.requests.get', return_value=mock_response):
    result = parse_grado_d_basico('http://fake')
```

### Escriptura atomica
**Font:** `fp-cercador/backend/scrapers/pipeline.py` linies 75-90
**Aplicar a:** extensio de `pipeline.py` — NO crear noves variants, reutilitzar `_write_atomic` existent sense canvis
```python
def _write_atomic(data: list, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', suffix='.json',
        dir=dir_path, delete=False
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)
```

---

## Tests existents que cal modificar

### `fp-cercador/backend/tests/test_pipeline.py`

**Pitfall 5 de RESEARCH.md** — 2 tests fallaran quan `by_grado` inclogui D i E:

**Test 1 — linia 89** (cal actualitzar):
```python
# ACTUAL (falla quan by_grado te D i E):
assert set(result['by_grado'].keys()) == {'A', 'B', 'C'}

# CORRECTE:
assert set(result['by_grado'].keys()) == {'A', 'B', 'C', 'D', 'E'}
```

**Test 4 — linia 222** (cal actualitzar o afegir test separat):
```python
# ACTUAL (falla perque pipeline ara crida 3 PDF + 4 HTML = 7 vegades requests.get):
assert mock_unlink.call_count == 3   # PDFs nomes

# CORRECTE: os.unlink segueix sent 3 cops (PDFs), requests.get sera 7 cops
# El test actual verifica os.unlink, no requests.get — revisar si la logica canvia
```

**Patch paths nous a afegir** (patrons dels linies 34-41):
```python
PATCH_PARSE_D_BASICO   = 'scrapers.pipeline.parse_grado_d_basico'
PATCH_PARSE_D_MEDIO    = 'scrapers.pipeline.parse_grado_d_medio'
PATCH_PARSE_D_SUPERIOR = 'scrapers.pipeline.parse_grado_d_superior'
PATCH_PARSE_E          = 'scrapers.pipeline.parse_grado_e'
```

---

## No Analog Found

Cap fitxer d'aquesta fase queda sense analog — tots tenen un equivalent existent al codebase.

---

## Decisions pendents per al Planner

1. **"Mantenimiento y Servicios a la Producción"** — el RESEARCH.md no pot decidir per l'usuari. El planner ha de proposar opcions i confirmar:
   - Opció A: `familia='Desconeguda'` + warning (consistent amb D-08)
   - Opció B: preservar el nom original a `HTML_FAMILY_ALIASES` (nou valor al schema)

2. **HEADERS: import vs redefinicio** — per evitar dependencia circular, el planner ha de decidir si `html_scraper.py` importa `HEADERS` de `pipeline.py` o si es crea un `utils.py` compartit. Si la dependencia circular es detecta, la solucio mes simple es passar `HEADERS` com a parametre o duplicar-lo al html_scraper.py amb un comentari indicant la font.

3. **DATA-04 i Success Criterion 5** — el requirement diu 800–900 registres pero la realitat confirmada es ~12.374. El planner ha de proposar actualitzar-ho o deixar-ho stale.

---

## Metadata

**Scope de cerca d'analogs:** `fp-cercador/backend/scrapers/`, `fp-cercador/backend/tests/`
**Fitxers escanejats:** 6 (`pipeline.py`, `pdf_scraper.py`, `test_pipeline.py`, `test_pdf_scraper.py`, `conftest.py`, `.env.example`)
**Data d'extractor de patrons:** 2026-04-17
