# Phase 3: HTML Scrapers + Data Pipeline (Grados D, E) - Research

**Researched:** 2026-04-17
**Domain:** BeautifulSoup4 HTML scraping + pipeline extension (Python)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01: Fail fast** — Si qualsevol URL HTML falla (error de xarxa, 404, estructura inesperada), el pipeline s'atura i `ofertes.json` no s'actualitza. Cap escritura parcial.
- **D-02: Ampliació in-place de `pipeline.run()`** — `by_grado` s'estén afegint D i E. Interfície pública final: `{"total": N, "by_grado": {"A": N, "B": N, "C": N, "D": N, "E": N}, "errors": [], "duration_seconds": X}`.
- **D-03: Ordre IDs seqüencials A → B → C → D → E.**
- **D-04: Un únic `fp-cercador/backend/scrapers/html_scraper.py`** amb funcions `parse_grado_d_basico(url)`, `parse_grado_d_medio(url)`, `parse_grado_d_superior(url)`, `parse_grado_e(url)`. Refactorització interna amb `_parse_grado_d(url, nivel)` a discreció de l'agent si l'HTML és idèntic.
- **D-05: URLs via `.env` amb fallback hardcode.** Les 4 URLs es llegeixen amb `os.getenv('URL_GRADO_D_BASICO', 'https://...')`. El `.env.example` s'actualitza amb les 4 noves variables.
- **D-06: L'agent de recerca verifica les URLs reals** (COMPLERT — vegeu secció URLs verificades).
- **D-07: Detecció de família via `<th rowspan="N" headers="familia">` amb `<img alt="Logotipo Família">`** — L'agent confirma que `rowspan` és UN dels dos mecanismes (l'altre és `headers` a `<td>`).
- **D-08: Normalitzat contra PREFIX_MAP** — Mapeig explicit per a 3 famílies HTML que no coincideixen literalment amb PREFIX_MAP (vegeu secció Mapeig de Famílies).
- **D-09: Pàgina d'entrada Grado D:** `https://www.todofp.es/que-estudiar/grados-d.html`.
- **D-10: Esquema de registres D/E:** `{grado, nivel, familia, codigo: null, denominacion, plan_antiguo: false, observaciones: ""}`.

### Claude's Discretion

- Implementació interna de `_parse_grado_d(url, nivel)` si HTML és idèntic (CONFIRMAT — idèntic).
- Estratègia exacta de fuzzy match per al mapeig família (RESOLT — explicit dict, no fuzzy; vegeu secció Mapeig).
- Gestió de `rowspan` si no és l'únic mecanisme (RESOLT — hi ha dos mecanismes equivalents; recomanació: usar `headers` de `<td>`).
- URLs exactes dels 3 subtipus Grado D i del catàleg Grado E (RESOLT — verificades).

### Deferred Ideas (OUT OF SCOPE)

Cap — la discussió s'ha mantingut dins l'abast de la fase.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HTML-01 | Scraper extreu títols dels Grados D des de 3 URLs (Básico, Medio, Superior) | URLs verificades; estructura `id="tit-*"` confirmada (34/67/94 títols) |
| HTML-02 | Scraper extreu títols del Grado E des de URL Cursos d'Especialització | URL verificada; estructura idèntica a D; 36 títols confirmats |
| HTML-03 | Títols identificats per `id="tit-*"` | Confirmat en totes 4 pàgines |
| HTML-04 | Família professional inferida de les capçaleres de secció | Confirmat: `<th headers="familia" id="famXX"><img alt="Logotipo Família">` + `<td headers="titulacion famXX">` |
| HTML-05 | Nivel assignat per subtipus: Básico→1, Medio→2, Superior→3, Grado E→null | Confirmat; no hi ha cap atribut HTML que ho indiqui — és paràmetre a la crida |
| HTML-06 | Registres D/E amb `codigo: null` i `plan_antiguo: false` | Camp `codigo` no existeix als HTML; `plan_antiguo` sempre false per D/E |
| DATA-01 | Pipeline genera `ofertes.json` amb el schema definit | Pipeline existent + `_write_atomic` reutilitzable sense canvis |
| DATA-02 | IDs correlatius i únics | Lògica existent a `pipeline.run()` — cal estendre el loop |
| DATA-03 | Consolida Grados A, B, C, D, E en un únic array | Extensió in-place de `by_grado` + `all_records` |
| DATA-04 | Volum ~800–900 registres totals | **STALE** — el total real serà ~12.374 (A/B/C: 12.143 + D/E: 231); vegeu nota DATA-04 |

</phase_requirements>

---

## Summary

Les pàgines HTML del ministeri (todofp.es) per als Grados D i E segueixen una estructura de taula HTML semàntica consistent i ben documentada. Totes 4 URLs han estat verificades amb `curl` directament, l'HTML descarregat i analitzat amb BeautifulSoup4. La família professional de cada títol es pot extreure de dues maneres equivalents: via el `rowspan` del `<th headers="familia">`, o via el `fam_id` inclòs a l'atribut `headers` del `<td>`. L'enfocament recomanat és el segon (basant-se en `td headers`) perquè és directe i no requereix rastreig de posició de fila.

Les 4 pàgines contenen un total de 231 títols (D_Básico: 34, D_Medio: 67, D_Superior: 94, E: 36). L'integració amb `pipeline.py` és una extensió in-place: el bucle `parsers` s'estén amb 4 nous scrapers HTML que criden `requests.get` (en comptes de `_download_pdf`) i criden funcions de `html_scraper.py`. El `_write_atomic` i la lògica d'ID seqüencial no necessiten cap canvi.

Hi ha 3 noms de família en l'HTML que no coincideixen literalment amb els valors de `PREFIX_MAP`: "Imagen y Sonido", "Artes y Artesanias" i "Mantenimiento y Servicios a la Producción". El fuzzy matching (difflib) produeix resultats incorrectes per a tots 3 casos. La solució correcta és un diccionari suplementari hardcode (`HTML_FAMILY_ALIASES`) que mapeja exactament aquests 3 noms.

**Nota crítica DATA-04:** El requirement DATA-04 estima "800–900 registres totals". Aquesta xifra és obsoleta — la Fase 2 ja va generar 12.143 registres (A/B/C inclouen pla antic). Afegir D/E donarà ~12.374 totals. El requirement s'hauria d'actualitzar; el planner ha de verificar-ho amb l'usuari.

**Recomanació primària:** Usar l'atribut `headers` del `<td>` per al mapeig família (no `rowspan`), amb un dict `HTML_FAMILY_ALIASES` per als 3 noms no canònics. `beautifulsoup4` ja és a `requirements.txt`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Descàrrega pàgines HTML | API/Backend (pipeline.py) | — | `requests.get` + HEADERS; idèntic al patró PDF |
| Parsing HTML / extracció títols | API/Backend (html_scraper.py) | — | BeautifulSoup4; funcions pures, fàcils de testejar amb fixtures HTML |
| Mapeig família HTML → PREFIX_MAP | API/Backend (html_scraper.py) | — | Lògica de domini; dict lookup + alias dict |
| Consolidació A/B/C/D/E | API/Backend (pipeline.py) | — | Extensió in-place del `parsers` dict i `all_records` |
| Escriptura atòmica ofertes.json | API/Backend (pipeline.py) | — | `_write_atomic` existent, sense canvis |
| Assignació nivel per subtipus | API/Backend (html_scraper.py) | — | Paràmetre `nivel` injectat per subtipus (no present a l'HTML) |

---

## URLs Verificades

[VERIFIED: curl directe a todofp.es 2026-04-17]

| Grado | Subtipus | URL |
|-------|---------|-----|
| D | Básico | `https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html` |
| D | Medio | `https://www.todofp.es/que-estudiar/grados-d/grado-medio.html` |
| D | Superior | `https://www.todofp.es/que-estudiar/grados-d/grado-superior.html` |
| E | Cursos d'Especialització | `https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html` |

Totes retornen HTTP 200. Requereixen els mateixos headers `User-Agent` + `Referer` que els PDFs (el `HEADERS` dict existent a `pipeline.py` és vàlid).

---

## Estructura HTML Verificada

[VERIFIED: HTML descarregat i analitzat amb BeautifulSoup4 — 2026-04-17]

### Taula de títols (estructura comuna a les 4 pàgines)

```html
<table>
  <thead>
    <tr class="cols">
      <th id="familia">Familia</th>
      <th id="titulacion">Titulación</th>
      <!-- ...altres columnes (real-decreto, curriculo-mecd, etc.) -->
    </tr>
  </thead>
  <tbody>
    <!-- Família amb 2 títols (rowspan=2) -->
    <tr class="fpb">  <!-- fpb / fpgm / fpgs / fpce segons el nivell -->
      <th rowspan="2" headers="familia" id="fam0">
        <img loading="lazy" alt="Logotipo Administración y Gestión" src="...">
      </th>
      <td headers="titulacion fam0">
        <p><a id="tit-gestion-administrativa" href="...">Título en Gestión Administrativa</a></p>
      </td>
    </tr>
    <!-- Segon títol de la mateixa família (sense <th>, el rowspan el cobreix visualment) -->
    <tr class="fpb">
      <!-- NO hi ha <th headers="familia"> aquí -->
      <td headers="titulacion fam0">
        <p><a id="tit-servicios-administrativos" href="...">Título en Servicios Administrativos</a></p>
      </td>
    </tr>
    <!-- Família amb 1 títol (rowspan=1) -->
    <tr class="fpb">
      <th rowspan="1" headers="familia" id="fam011116">
        <img loading="lazy" alt="Logotipo Actividades Físicas y Deportivas" src="...">
      </th>
      <td headers="titulacion fam011116">
        <p><a id="tit-acceso-y-conservacion..." href="...">Título...</a></p>
      </td>
    </tr>
  </tbody>
</table>
```

### Mecanisme de relació família ↔ títol: DOS mètodes equivalents

**Mètode A — Via `rowspan` (tracking de posició):**
1. Iterar `<tr>` del `<tbody>`.
2. Si el `<tr>` conté `<th headers="familia">`, extreure la família de l'`alt` de la `<img>` i llegir `rowspan=N`.
3. Decrementar el comptador en cada fila fins a 0.
- Desavantatge: cal gestionar estat (comptador) entre files.

**Mètode B — Via `headers` del `<td>` (recomanat):**
1. Per a cada `<td>` amb `headers` que contingui `"titulacion"`, extreure el `fam_id` (la paraula que comença per `"fam"`).
2. Fer lookup al diccionari `fam_map` (construït previament de tots els `<th id="famXX" headers="familia">`).
- Avantatge: directe, sense estat, més simple.

**Observació important:** BeautifulSoup4 retorna l'atribut `headers` com a `AttributeValueList` (llista), no com a string. Cal tractar-ho amb `isinstance(headers_val, list)`.

### Compte de títols per pàgina

[VERIFIED: grep `id="tit-"` sobre HTML descarregat — 2026-04-17]

| Pàgina | Títols | Classe `<tr>` |
|--------|--------|--------------|
| Grado D Básico | 34 | `fpb` |
| Grado D Medio | 67 | `fpgm` |
| Grado D Superior | 94 | `fpgs` |
| Grado E Especialització | 36 | `fpce` |
| **Total D+E** | **231** | — |

---

## Mapeig de Famílies HTML → PREFIX_MAP

[VERIFIED: grep i BeautifulSoup4 sobre HTML descarregat — 2026-04-17]

### Famílies que coincideixen directament (24 de 27 úniques en HTML)

Totes les famílies de `PREFIX_MAP` excepte les que apareixen a la taula d'anomalies coincideixen exactament per nom.

### 3 anomalies que necessiten diccionari suplementari

| Nom en HTML | Correcte mapatge | Raó | Apareix a |
|-------------|-----------------|-----|-----------|
| `"Imagen y Sonido"` | `"Imagen y Espectáculos"` | Mateix domini (audiovisual, espectacles). `difflib` no funciona: fa match amb `"Imagen Personal"` (ràtio 0.67 vs 0.61) | D_Medio, D_Superior, E |
| `"Artes y Artesanias"` | `"Artesanía"` | Familía LOGSE equivalent a `ART` de PREFIX_MAP. Títols: "Artista Fallero", "Instruments musicals". `difflib` fa match amb `"Artesanía"` per ràtio (0.67) però per raó equivocada | D_Superior |
| `"Mantenimiento y Servicios a la Producción"` | `"Desconeguda"` (o nou valor) | Família LOGSE sense equivalent directe a PREFIX_MAP. Un únic títol: "Técnico Superior en Prevención de Riesgos Profesionales (Título LOGSE)". `difflib` no fa cap match (màxim 0.50 amb `"Transporte y Mantenimiento"`) | D_Superior |

**Decisió recomanada per a `"Mantenimiento y Servicios a la Producción"`:** Afegir com a nova entrada al `HTML_FAMILY_ALIASES` amb el valor `"Mantenimiento y Servicios a la Producción"` (preservar el nom original, no inventar una família nova). Alternativament, deixar-la com `"Desconeguda"` i fer warning — consistent amb D-08 del CONTEXT.md. **El planner ha de confirmar amb l'usuari quin comportament és desitjat.**

### Estratègia d'implementació: `HTML_FAMILY_ALIASES`

```python
# html_scraper.py — a dalt del fitxer, junt amb PREFIX_MAP import
HTML_FAMILY_ALIASES = {
    "Imagen y Sonido": "Imagen y Espectáculos",
    "Artes y Artesanias": "Artesanía",
    # "Mantenimiento y Servicios a la Producción": <a confirmar>
}

def _normalize_html_family(raw_name: str) -> str:
    """Mapeja el nom de família extret del HTML al nom canònic de PREFIX_MAP."""
    if raw_name in HTML_FAMILY_ALIASES:
        return HTML_FAMILY_ALIASES[raw_name]
    return raw_name  # Si coincideix directament amb un valor de PREFIX_MAP, passa tal qual
```

**Per què NO usar `difflib`:** Els tests mostren que `difflib.get_close_matches` fa matches incorrectes per a `"Imagen y Sonido"` → `"Imagen Personal"` (ràtio 0.67 vs 0.61 per `"Imagen y Espectáculos"`). El dict explicit és determinista i zero-dependència-externa.

**Per què NO usar `rapidfuzz`:** No és a `requirements.txt` ni al stack declarat del projecte. Afegir-lo per 3 casos especials seria un overhead innecessari.

---

## Standard Stack

### Core (ja a requirements.txt)
| Biblioteca | Versió a requirements.txt | Propòsit | Notes |
|-----------|--------------------------|---------|-------|
| `beautifulsoup4` | (sense pin) | Parsing HTML | [VERIFIED: requirements.txt] — ja instal·lat |
| `requests` | (sense pin) | Descàrrega pàgines HTML | [VERIFIED: requirements.txt] — reutilitzat de pipeline.py |
| `python-dotenv` | (sense pin) | Lectura `os.getenv()` amb fallback | [VERIFIED: requirements.txt] — reutilitzat |

### Sense dependències noves

Cap biblioteca nova és necessària per a aquesta fase. Tota la funcionalitat requerida és coberta per les dependències existents.

---

## Architecture Patterns

### Diagrama de flux

```
pipeline.run()
    │
    ├─── [A,B,C] PDF scrapers (existent, sense canvis)
    │         └── _download_pdf() → parse_grado_x() → records
    │
    ├─── [D_Básico]  requests.get(URL_D_BASICO) → parse_grado_d_basico()  ─┐
    ├─── [D_Medio]   requests.get(URL_D_MEDIO)  → parse_grado_d_medio()   ─┤→ records D/E
    ├─── [D_Superior] requests.get(URL_D_SUPERIOR) → parse_grado_d_superior() ─┤  afegits a all_records
    └─── [E]         requests.get(URL_E)        → parse_grado_e()          ─┘
                                                                             │
                                                                        id seqüencial
                                                                             │
                                                                     _write_atomic()
                                                                             │
                                                                     ofertes.json (~12374 registres)
```

### Estructura fitxers

```
fp-cercador/backend/
├── scrapers/
│   ├── __init__.py          (existent — no tocar)
│   ├── pdf_scraper.py       (existent — no tocar; exporta PREFIX_MAP)
│   ├── pipeline.py          (MODIFICAR — estendre parsers dict i by_grado)
│   └── html_scraper.py      (NOU — 4 funcions parse + helpers privats)
├── data/
│   └── ofertes.json         (es regenera quan s'executa pipeline.run())
├── tests/
│   ├── conftest.py          (MODIFICAR — afegir fixtures HTML per a html_scraper)
│   └── test_html_scraper.py (NOU)
│   └── test_pipeline.py     (MODIFICAR — estendre mocks per a D/E)
└── .env.example             (MODIFICAR — afegir 4 noves variables URL)
```

### Patró 1: `html_scraper.py` — funció genèrica interna

Les 4 pàgines (D_Básico, D_Medio, D_Superior, E) comparteixen la mateixa estructura HTML. Es recomana una funció privada central:

```python
# Source: verificat en HTML real de todofp.es — 2026-04-17
from bs4 import BeautifulSoup
import requests
import logging

logger = logging.getLogger(__name__)

HTML_FAMILY_ALIASES = {
    "Imagen y Sonido": "Imagen y Espectáculos",
    "Artes y Artesanias": "Artesanía",
}

def _parse_titols_html(html: str, nivel: int | None, grado: str) -> list[dict]:
    """
    Parseja una pàgina de llistat de títols del ministeri.

    Retorna llista de dicts amb:
      {denominacion, familia, nivel, codigo: None, plan_antiguo: False, observaciones: ""}
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Pas 1: construir mapa fam_id -> nom_família
    fam_map = {}
    for th in soup.find_all('th', attrs={'headers': 'familia'}):
        fam_id = th.get('id', '')
        img = th.find('img')
        if img:
            alt = img.get('alt', '')
            if alt.startswith('Logotipo '):
                raw_name = alt[len('Logotipo '):]
                fam_map[fam_id] = HTML_FAMILY_ALIASES.get(raw_name, raw_name)

    # Pas 2: extreure títols
    records = []
    for td in soup.find_all('td', attrs={'headers': True}):
        headers_val = td.get('headers', [])
        headers_list = headers_val if isinstance(headers_val, list) else headers_val.split()

        if 'titulacion' not in headers_list:
            continue

        fam_id = next((p for p in headers_list if p.startswith('fam')), None)
        a = td.find('a', id=lambda x: x and x.startswith('tit-'))

        if not a or not fam_id:
            continue

        familia = fam_map.get(fam_id, 'Desconeguda')
        if familia == 'Desconeguda':
            logger.warning(f"Família desconeguda per fam_id='{fam_id}' al Grado {grado}")

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

### Patró 2: Integració a `pipeline.py`

```python
# Afegir a pipeline.py (extensió in-place de parsers i run())
from scrapers.html_scraper import (
    parse_grado_d_basico, parse_grado_d_medio,
    parse_grado_d_superior, parse_grado_e,
)

HTML_URLS = {
    'D_BASICO':   os.getenv('URL_GRADO_D_BASICO', 'https://www.todofp.es/que-estudiar/grados-d/fp-grado-basico.html'),
    'D_MEDIO':    os.getenv('URL_GRADO_D_MEDIO',  'https://www.todofp.es/que-estudiar/grados-d/grado-medio.html'),
    'D_SUPERIOR': os.getenv('URL_GRADO_D_SUPERIOR','https://www.todofp.es/que-estudiar/grados-d/grado-superior.html'),
    'E':          os.getenv('URL_GRADO_E',         'https://www.todofp.es/que-estudiar/grados-e/curso-especializacion.html'),
}

def _fetch_html(url: str, timeout: int = 30) -> str:
    """Descàrrega una pàgina HTML i retorna el contingut com a string."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.text
```

### Anti-patterns a evitar

- **Usar `difflib` per al mapeig de famílies HTML:** Produeix resultats incorrectes (ratios massa similars entre famílies de nom paregut). Usar dict explicit.
- **Crear un `_download_html` que escrigui a fitxer temporal:** No cal — l'HTML pot processar-se directament com a string en memòria (les pàgines tenen < 3.000 línies).
- **No filtrar el `<img alt="Logotipo de TodoFP">`** (logo de la capçalera que també té "Logotipo" a l'alt): el mapa es construeix ÚNICAMENT de `<th headers="familia">`, no de totes les imatges, cosa que el filtra automàticament.

---

## Don't Hand-Roll

| Problema | No construir | Usar | Per què |
|---------|-------------|------|---------|
| Parsing HTML | Parser manual amb regex | `beautifulsoup4` (ja instal·lat) | HTML pot tenir atributs en ordre variable; regex trenca amb whitespace inconsistent |
| Escriptura JSON atòmica | `open(path, 'w')` directe | `_write_atomic()` existent | Race condition si el procés s'interromp; ja implementat i testejat |
| Mapeig família fuzzy | `difflib.get_close_matches` | Dict `HTML_FAMILY_ALIASES` | Difflib falla per a "Imagen y Sonido" → assigna "Imagen Personal" incorrectament |
| Descàrrega HTTP | `urllib` directe | `requests` (ja instal·lat) | Gestió de redirects, timeouts, raise_for_status — ja al projecte |

---

## Common Pitfalls

### Pitfall 1: `headers` és una `AttributeValueList`, no un string
**Que passa malament:** `td.get('headers', '').split()` llança `AttributeError: 'AttributeValueList' object has no attribute 'split'`.
**Per què:** BeautifulSoup4 parseja atributs multi-valor (separats per espai a l'HTML) com a llistes Python.
**Com evitar:**
```python
headers_val = td.get('headers', [])
headers_list = headers_val if isinstance(headers_val, list) else headers_val.split()
```
**Senyal d'alerta:** Tests que passen amb strings fictícis però fallen en HTML real.

### Pitfall 2: El logo de capçalera té `alt="Logotipo de TodoFP"`
**Que passa malament:** Si filtrem `img[alt^="Logotipo"]` sense context, agafem el logo de la pàgina.
**Com evitar:** Construir `fam_map` ÚNICAMENT de `<th headers="familia">`, no de totes les imatges.

### Pitfall 3: Alguns `<th headers="familia">` amb `rowspan="1"` i altres amb `rowspan="N"`
**Que passa malament:** Si es tria el mètode rowspan i no es gestiona el cas `rowspan="1"`, es pot perdre la referència de família per a les files posteriors.
**Com evitar:** Usar el Mètode B (headers del `<td>`) que no requereix tracking de rowspan.

### Pitfall 4: Famílies duplicades al Grado Medio i Superior
**Que passa malament:** "Fabricación Mecánica" i "Sanidad" apareixen dues vegades als fitxers HTML de Grado Medio i Superior (dos `<th>` amb el mateix nom però `id` diferent). No és un error — el `fam_map` ho gestiona correctament perquè cada `td` apunta al seu `fam_id` concret.
**Com evitar:** No deduplicar el `fam_map` per nom; permetre que existeixin dos `fam_id` per al mateix nom.

### Pitfall 5: test_pipeline.py comprova `set(result['by_grado'].keys()) == {'A', 'B', 'C'}`
**Que passa malament:** El test existent (`test_pipeline_run_returns_correct_schema`) fallarà quan `by_grado` tingui claus D i E.
**Com evitar:** Actualitzar el test per a `{'A', 'B', 'C', 'D', 'E'}`. El test `test_pipeline_deletes_pdf_on_success` verifica `mock_unlink.call_count == 3` — caldrà actualitzar-lo o afegir un test separat per a l'extensió.

### Pitfall 6: DATA-04 stale — volum esperat molt superior a 800–900
**Que passa malament:** La validació del SUCCESS CRITERION 5 (800–900 registres) fallarà, però no perquè el scraper sigui incorrecte.
**Realitat:** A/B/C ja generen 12.143 registres; D/E afegiran 231. Total ~12.374.
**Com evitar:** El planner ha de proposar actualitzar DATA-04 i el Success Criterion 5 a "~12.000–12.500 registres totals" o equivalent.

---

## Nota Crítica: DATA-04 i SUCCESS CRITERION 5

[VERIFIED: `ofertes.json` existent + compte HTML — 2026-04-17]

| Font | Registres |
|------|-----------|
| Grado A (PDF, actual) | 8.537 |
| Grado B (PDF, actual) | 2.786 |
| Grado C (PDF, actual) | 820 |
| Grado D Básico (HTML, verificat) | 34 |
| Grado D Medio (HTML, verificat) | 67 |
| Grado D Superior (HTML, verificat) | 94 |
| Grado E (HTML, verificat) | 36 |
| **Total esperat** | **~12.374** |

El requirement DATA-04 diu "800–900 registres". Estava basat en una estimació del PROJECT.md (A:~120, B:~200, C:~380) que no comptava registres de pla antic. El planner **ha de confirmar amb l'usuari** si:
1. DATA-04 s'actualitza a ~12.374 (recomanat — reflecteix la realitat)
2. O si el Success Criterion 5 del roadmap es redacta diferent

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existent a `backend/tests/`) |
| Config file | cap fitxer pytest.ini detectat — pytest s'executa des de `backend/` |
| Quick run command | `cd fp-cercador/backend && python -m pytest tests/test_html_scraper.py -x -q` |
| Full suite command | `cd fp-cercador/backend && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Fitxer |
|--------|----------|-----------|-------------------|--------|
| HTML-01 | `parse_grado_d_basico` extreu 34 títols | unit | `pytest tests/test_html_scraper.py::test_parse_grado_d_basico_count -x` | ❌ Wave 0 |
| HTML-02 | `parse_grado_e` extreu 36 títols | unit | `pytest tests/test_html_scraper.py::test_parse_grado_e_count -x` | ❌ Wave 0 |
| HTML-03 | Títols identificats per `id="tit-*"` | unit | `pytest tests/test_html_scraper.py::test_tit_id_extraction -x` | ❌ Wave 0 |
| HTML-04 | Família correcta per cada títol | unit | `pytest tests/test_html_scraper.py::test_family_mapping -x` | ❌ Wave 0 |
| HTML-05 | `nivel` correcte per subtipus | unit | `pytest tests/test_html_scraper.py::test_nivel_assignment -x` | ❌ Wave 0 |
| HTML-06 | `codigo=None`, `plan_antiguo=False` | unit | `pytest tests/test_html_scraper.py::test_record_fields -x` | ❌ Wave 0 |
| DATA-01 | Schema correcte a `ofertes.json` | integration | `pytest tests/test_pipeline.py::test_pipeline_run_returns_correct_schema -x` | ✅ (cal estendre) |
| DATA-02 | IDs únics i seqüencials | integration | `pytest tests/test_pipeline.py::test_pipeline_adds_id_and_grado -x` | ✅ (cal estendre) |
| DATA-03 | Tots 5 grados a `by_grado` | unit | `pytest tests/test_pipeline.py::test_pipeline_run_returns_correct_schema -x` | ✅ (cal modificar) |
| DATA-04 | Volum total correcte | integration/manual | Execució real del pipeline | manual |

### Sampling Rate
- **Per task commit:** `cd fp-cercador/backend && python -m pytest tests/test_html_scraper.py -x -q`
- **Per wave merge:** `cd fp-cercador/backend && python -m pytest tests/ -q`
- **Phase gate:** Full suite green + execució real del pipeline (compte final)

### Wave 0 Gaps
- [ ] `tests/test_html_scraper.py` — cobreix HTML-01 a HTML-06 (fitxer nou)
- [ ] Fixtures HTML a `tests/conftest.py` — snippets HTML mínims per a tests unitaris (sense xarxa)
- [ ] Actualització de `tests/test_pipeline.py` — mocks per a D/E, correcció del test que verifica `{'A', 'B', 'C'}` → `{'A', 'B', 'C', 'D', 'E'}`

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `beautifulsoup4` | html_scraper.py | ✓ | instal·lat (requirements.txt) | — |
| `requests` | html_scraper.py / pipeline.py | ✓ | instal·lat (requirements.txt) | — |
| `python-dotenv` | pipeline.py (getenv) | ✓ | instal·lat (requirements.txt) | — |
| `pytest` | tests/ | ✓ | disponible a l'entorn | — |
| Internet (todofp.es) | execució real del pipeline | ✓ | HTTP 200 verificat 2026-04-17 | — |

Cap dependència faltant ni bloquejant.

---

## Code Examples

### Exemple 1: Parsing complet d'una pàgina (patró verificat)

```python
# Source: verificat amb BeautifulSoup4 sobre HTML real de todofp.es — 2026-04-17
from bs4 import BeautifulSoup

def _build_fam_map(soup: BeautifulSoup) -> dict:
    """Retorna {fam_id: nom_canonic} per a tots els <th headers='familia'>."""
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

def _extract_titols(soup: BeautifulSoup, fam_map: dict, nivel, grado: str) -> list[dict]:
    """Extreu tots els títols d'una pàgina."""
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

### Exemple 2: Test unitari amb fixture HTML (patró dels tests existents)

```python
# tests/test_html_scraper.py — patró consistent amb test_pipeline.py
import pytest
from unittest.mock import patch, Mock
from scrapers.html_scraper import parse_grado_d_basico

MINIMAL_HTML_BASICO = """
<html><body><table>
  <thead><tr><th id="familia">Familia</th><th id="titulacion">Titulación</th></tr></thead>
  <tbody>
    <tr>
      <th rowspan="1" headers="familia" id="fam0">
        <img alt="Logotipo Administración y Gestión">
      </th>
      <td headers="titulacion fam0">
        <p><a id="tit-gestion-administrativa" href="#">Gestión Administrativa</a></p>
      </td>
    </tr>
  </tbody>
</table></body></html>
"""

def test_parse_grado_d_basico_single_title():
    mock_resp = Mock()
    mock_resp.text = MINIMAL_HTML_BASICO
    mock_resp.raise_for_status = Mock()
    with patch('scrapers.html_scraper.requests.get', return_value=mock_resp):
        result = parse_grado_d_basico('http://fake')
    assert len(result) == 1
    assert result[0]['denominacion'] == 'Gestión Administrativa'
    assert result[0]['familia'] == 'Administración y Gestión'
    assert result[0]['nivel'] == 1
    assert result[0]['codigo'] is None
    assert result[0]['plan_antiguo'] is False
```

---

## State of the Art

| Enfocament antic | Enfocament actual | Quan va canviar | Impacte |
|-----------------|-------------------|-----------------|---------|
| Parseja família via `rowspan` + tracking de fila | Parseja família via `td headers` (directe) | Descobert en recerca — 2026-04-17 | Codi més simple, sense estat |
| `difflib.get_close_matches` per al mapeig família | Dict `HTML_FAMILY_ALIASES` explicit | Descobert en recerca — 2026-04-17 | Determinista, sense falsos positius |

---

## Assumptions Log

| # | Claim | Section | Risc si és incorrecte |
|---|-------|---------|----------------------|
| A1 | Les URLs de todofp.es no canviaran entre la recerca i l'execució | URLs Verificades | Baixe — les pàgines del ministeri canvien rarament; el `.env` permet override |
| A2 | L'estructura HTML (table + th/td amb headers) és estable i no és renderitzada per JS | Estructura HTML | Mig — si el contingut és renderitzat per JS, `requests.get` retornarà HTML buit. Verificat que NO és el cas (HTML estàtic complet) |
| A3 | "Mantenimiento y Servicios a la Producción" és una família LOGSE amb un únic títol i el comportament correcte és `"Desconeguda"` o preservar el nom original | Mapeig Famílies | Mig — l'usuari pot preferir mapejar-ho a "Instalación y Mantenimiento" o créixer PREFIX_MAP |

---

## Open Questions

1. **Comportament per a "Mantenimiento y Servicios a la Producción"**
   - El que sabem: 1 únic títol (LOGSE) sota aquesta família no present a PREFIX_MAP
   - Incert: Si l'usuari vol `familia='Desconeguda'` + warning (consistent amb D-08), preservar el nom complet, o mapejar-lo manualment
   - Recomanació: El planner ha de decidir i documentar l'opció triada (o deixar a discreció de l'agent d'execució)

2. **DATA-04: actualitzar el requirement i el Success Criterion 5**
   - El que sabem: el total real serà ~12.374, no 800–900
   - Incert: Si l'usuari vol que DATA-04 quedi stale (documenta intenció original) o s'actualitzi
   - Recomanació: El planner proposi actualitzar DATA-04 a "~12.000–13.000" i el SC-5 corresponentment

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: HTML descarregat amb curl de todofp.es — 2026-04-17] — Estructura de taula, atributs `id="tit-*"`, `headers="familia"`, `rowspan`, `img alt`, comptes de títols per pàgina
- [VERIFIED: BeautifulSoup4 script sobre HTML local — 2026-04-17] — Mapeig `fam_id → nom família`, extracció de 34 títols de Grado Básico, anomalies de famílies
- [VERIFIED: `fp-cercador/backend/scrapers/pdf_scraper.py` — 2026-04-17] — `PREFIX_MAP` (26 entrades), valors canònics de famílies
- [VERIFIED: `fp-cercador/backend/data/ofertes.json` + `02-03-SUMMARY.md` — 2026-04-17] — 12.143 registres A/B/C confirmats per Fase 2
- [VERIFIED: `fp-cercador/backend/requirements.txt` — 2026-04-17] — `beautifulsoup4`, `requests`, `python-dotenv` presents

### Secondary (MEDIUM confidence)
- [CITED: docs.python.org/3/library/difflib.html] — `difflib.get_close_matches` — comportament de ratio; confirmat que 0.67 és el top per `"Imagen y Sonido"` vs `"Imagen Personal"`

---

## Metadata

**Confidence breakdown:**
- URLs verificades: HIGH — curl directe, HTTP 200, contingut comprovat
- Estructura HTML: HIGH — HTML descarregat i parsejat amb BeautifulSoup4
- Mapeig famílies: HIGH — totes 27 famílies úniques identificades i cross-referenciades
- Integració pipeline: HIGH — codi existent llegit, patrons d'extensió clars
- Comptes de títols: HIGH — `grep id="tit-"` sobre HTML descarregat
- DATA-04 stale: HIGH — `ofertes.json` existent comprovat

**Research date:** 2026-04-17
**Valid until:** 2026-06-17 (les pàgines del ministeri canvien rarament; URLs poden canviar en cursos acadèmics)
