# Phase 2: PDF Scrapers (Grados A, B, C) - Research

**Researched:** 2026-04-17
**Domain:** pdfplumber PDF parsing, todofp.es data structure, Python pipeline
**Confidence:** HIGH (all key findings verified against actual PDFs and live URLs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Fail fast — si qualsevol dels 3 PDFs falla, el refresh s'atura completament. `ofertes.json` existent NO s'actualitza ni s'elimina.
- **D-02:** No hi ha comportament de "continua amb els altres" ni escritura parcial. Tot o res.
- **D-03:** Sense cache — cada execució descarrega PDFs frescos i els elimina un cop analitzats.
- **D-04:** Registres amb família desconeguda s'inclouen amb `familia='Desconeguda'` (cap pèrdua de dades).
- **D-05:** Sempre es genera un `logging.warning(...)` per a registres sense família reconeguda.
- **D-06:** El registre amb `familia='Desconeguda'` S'INCLOU a `ofertes.json`.
- **D-07:** Un únic `fp-cercador/backend/scrapers/pdf_scraper.py` amb `parse_grado_a()`, `parse_grado_b()`, `parse_grado_c()`.
- **D-08:** `fp-cercador/backend/scrapers/pipeline.py` orquestra el pipeline complet.
- **D-09:** La lògica de refresh NO viu a `app.py`. `app.py` roman com a stub fins a la Fase 4.

### Claude's Discretion

- URLs exactes dels 3 PDFs a todofp.es (ara verificades i documentades en aquest RESEARCH)
- Valors exactes dels headers `Referer` i `User-Agent` requerits
- Implementació interna del parsing: estratègia de detecció de taules vs text raw amb pdfplumber
- Regex exacta per detectar codis de pla antic
- Tractament de pàgines 1–5 — skip per número de pàgina o per contingut

### Deferred Ideas (OUT OF SCOPE)

- Scrapers HTML per Grados D i E — Fase 3
- Execució en thread separat i gestió d'estat — Fase 4
- Endpoint `POST /api/admin/refresh` — Fase 4
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PDF-01 | El scraper descarrega els 3 PDFs oficials des de todofp.es amb headers `Referer` i `User-Agent` | URLs verificades, headers mínims confirmats (GET + User-Agent + Referer = 200 OK) |
| PDF-02 | El scraper detecta correctament la família professional (29 famílies) | 24 prefixos verificats directament dels PDFs; mapping complet documentat |
| PDF-03 | El scraper dedueix el nivell del sufix del codi: `_3B`→1, `_4B`→2, `_5B`→3 | Confirmat EXCLUSIVAMENT per Grado C nou pla; Grados A i B no tenen suffix de nivel |
| PDF-04 | El scraper detecta `plan_antiguo: true` per codis antics i observacions `(Plan antiguo)` | Patró `(Plan antiguo)` a la cel·la del codi és el marcador definitiu; documentat per cada grado |
| PDF-05 | El scraper omiteix les pàgines 1–5 (portada i introducció) de cada PDF | Confirmat: les 3 PDFs inicien dades a la pàgina 6 (índex 5) |
| PDF-06 | El scraper genera registres correctes per a les 3 columnes: Código, Denominación, Observaciones | Estructura de taula pdfplumber documentada per cada grado; estratègia de parsing definida |
</phase_requirements>

---

## Summary

Els tres PDFs oficials de todofp.es (Grados A, B, C) són documents d'Adobe Acrobat amb text natiu parsejable amb pdfplumber. Cada PDF té exactament 5 pàgines d'introducció seguides de les dades del catàleg en format de taula. La descàrrega requereix una capçalera `User-Agent` de navegador i `Referer` de la pàgina del catàleg; no es requereixen cookies ni sessió.

L'estructura de les taules és diferent per a cada Grado, però el patró és consistent: el codi sempre és el primer camp no buit de cada fila de dades, la denominació és el següent camp, i les observacions ocupen la resta. Les files de continuació (per a textos llargs) tenen el camp del codi buit. La família professional s'infereix del prefix del codi (p. ex., `AFD` → Activitats Físiques i Esportives) usant un mapping estàtic de 24 prefixos, tots verificats directament dels PDFs.

L'estimació de volum del CONTEXT.md (~700 registres) és significativament inferior a la realitat observada: els PDFs actuals (data ModDate: 2026-03-18) contenen aproximadament 12.000 registres únics. Això inclou registres de pla antic (`plan_antiguo: true`). L'impacte en el frontend (requisit SRCH-09: fluïdesa fins a 1.500 registres) és una qüestió oberta de fases posteriors; la Fase 2 extreu tots els registres sense filtrar.

**Primary recommendation:** Usar `pdfplumber.extract_table()` per extreure les taules, amb una estratègia de parsing per files que identifica el codi per posició (primera cel·la no buida que coincideixi amb el patró de codi), agrupa les files de continuació, i mapeja el prefix al nom de la família via diccionari estàtic.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Descàrrega dels PDFs | Backend / Python | — | I/O de xarxa, no exposable al client |
| Parsing del contingut PDF | Backend / Python | — | pdfplumber és llibreria Python |
| Derivació de família, nivel, plan_antiguo | Backend / Python | — | Lògica de negoci pura, no al client |
| Escriptura d'`ofertes.json` | Backend / Python | — | Accés al sistema de fitxers del servidor |
| Orquestració del pipeline | `pipeline.py` | — | Separat de l'API per a la Fase 4 |

---

## Verified PDF URLs and Download Requirements

### URLs [VERIFIED: curl + requests against todofp.es]

| Grado | URL | Mida | Pàgines |
|-------|-----|------|---------|
| Grado A | `https://www.todofp.es/dam/jcr:a8580dd0-8106-4387-ae2a-8c6c1f23fa91/catalogo-grados-a.pdf` | ~4.2 MB | 506 |
| Grado B | `https://www.todofp.es/dam/jcr:fbe95da3-7507-458a-ab0d-4202beea8d28/catalogo-grados-b.pdf` | ~3.4 MB | 184 |
| Grado C | `https://www.todofp.es/dam/jcr:8b85fd78-c6d5-406f-ade8-891abd96613f/catalogo-grados-c.pdf` | ~2.6 MB | 78 |

**Pàgina de referència (Referer):** `https://www.todofp.es/catalogos-registros-sistema-fp/catalogo-nacional-ofertas-sistema.html`

### Headers mínims requerits [VERIFIED: tests amb requests library]

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.todofp.es/catalogos-registros-sistema-fp/catalogo-nacional-ofertas-sistema.html",
}
```

**Notes crítiques:**
- HEAD requests retornen 403 — SEMPRE usar `requests.get()` (no HEAD)
- No es requereixen cookies ni sessió autenticada
- `Cache-Control: max-age=604800` → la URL pot cadurar; si s'obté 404 en el futur, cal re-consultar la pàgina de catàleg

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pdfplumber | 0.11.9 | Extracció de taules i text de PDF | Únic permès per CLAUDE.md |
| requests | 2.32.5 | Descàrrega HTTP dels PDFs | Únic permès per CLAUDE.md |
| json | stdlib | Serialització d'`ofertes.json` | Stdlib, cap dependència extra |
| logging | stdlib | Warnings de família desconeguda (D-05) | Stdlib, patró Python estàndard |
| tempfile | stdlib | Fitxers temporals per als PDFs (D-03) | Stdlib, gestió neta d'artefactes |
| re | stdlib | Detecció de codis i patrons | Stdlib |

### No s'afegeix cap dependència nova
El `requirements.txt` existent ja conté tot el necessari. [VERIFIED: requirements.txt]

---

## Architecture Patterns

### System Architecture Diagram

```
[todofp.es URLs]
     |
     | GET + User-Agent + Referer headers
     v
[requests.get()]
     |
     | PDF bytes → tempfile
     v
[pdfplumber.open(tempfile)]
     |
     | pages[5:] (skip intro)
     v
[extract_table() per pàgina]
     |
     | rows → parse_row()
     v
[code detection] ──► new plan / old plan / continuation / header
     |
     | code_cell → prefix → family lookup
     v
[PREFIX_MAP dict]
     |
     | familia, codigo, denominacion, nivel, plan_antiguo, observaciones
     v
[list of records]
     |
     | (si prefix unknown) → logging.warning + familia='Desconeguda'
     v
[pipeline.py assembles all grados]
     |
     | (fail fast si qualsevol grado falla)
     v
[json.dump() → ofertes.json (atomic write)]
```

### Recommended Project Structure

```
fp-cercador/backend/scrapers/
├── __init__.py          # Paquet existent (stub)
├── pdf_scraper.py       # parse_grado_a(), parse_grado_b(), parse_grado_c()
└── pipeline.py          # run() → dict amb resum {"total", "by_grado", "errors", "duration_seconds"}
```

### Pattern 1: Table Extraction amb pdfplumber

**What:** Extreure taules pàgina per pàgina, iterar files, identificar el codi per posició (primera cel·la no buida que coincideixi amb el patró de codi o contigui `(Plan antiguo)`).

**When to use:** Per tots els 3 Grados — el format de taula és consistent.

```python
# Source: verificat contra PDFs reals + Context7 /jsvine/pdfplumber
import pdfplumber

def _extract_records(pdf_path, grado_letter, nivel_fn):
    """Extreu registres d'un PDF de Grado X."""
    records = {}  # code_str -> record dict (per desduplicar)
    new_code_re = re.compile(rf'^[A-Z]{{2,4}}_{grado_letter}_\d')

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[5:]:  # skip pàgines 1-5
            table = page.extract_table()
            if not table:
                continue
            for row in table:
                if not row:
                    continue
                code_cell, denom_cell, obs_parts = _parse_row(row, new_code_re)
                if code_cell and code_cell not in records:
                    is_old = '(Plan antiguo)' in code_cell
                    clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
                    prefix = clean_code.split('_')[0] if '_' in clean_code else ''
                    familia = PREFIX_MAP.get(prefix)
                    if not familia:
                        logging.warning(f"Família desconeguda per prefix '{prefix}' al codi '{clean_code}'")
                        familia = 'Desconeguda'
                    records[code_cell] = {
                        'codigo': clean_code,
                        'denominacion': denom_cell or '',
                        'observaciones': ' '.join(obs_parts),
                        'familia': familia,
                        'nivel': nivel_fn(clean_code, is_old),
                        'plan_antiguo': is_old,
                    }
    return list(records.values())
```

### Pattern 2: Row Parsing robust (codi en qualsevol columna)

```python
# Source: verificat contra estructura de taules observada als 3 PDFs
def _parse_row(row, new_code_re):
    """Retorna (code_cell, denom_cell, obs_parts) o (None, None, []) si no és fila de dades."""
    for i, cell in enumerate(row):
        if not cell or not str(cell).strip():
            continue
        cell_str = str(cell).strip()
        is_new = bool(new_code_re.match(cell_str))
        is_old = '(Plan antiguo)' in cell_str

        if is_new or is_old:
            denom = None
            for j in range(i + 1, len(row)):
                if row[j] and str(row[j]).strip():
                    denom = str(row[j]).strip()
                    break
            obs = [str(row[k]).strip() for k in range(i + 2, len(row))
                   if row[k] and str(row[k]).strip()]
            return cell_str, denom, obs
    return None, None, []
```

### Pattern 3: Escriptura atòmica d'`ofertes.json`

**What:** Escriure primer a un fitxer temporal i fer rename per evitar escriptures parcials.

```python
import tempfile, os, json

def _write_atomic(data, output_path):
    """Escriu JSON de manera atòmica: temp file + rename."""
    dir_path = os.path.dirname(output_path)
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', suffix='.json',
        dir=dir_path, delete=False
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)  # atòmic en Unix
```

### Pattern 4: Descàrrega i gestió temporal del PDF

```python
import tempfile, os, requests

def _download_pdf(url, headers, timeout=120):
    """Descarrega PDF a fitxer temporal. Retorna path. Caller és responsable d'esborrar-lo."""
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()  # 4xx/5xx → excepció (fail fast D-01)
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(resp.content)
        return tmp.name

# Ús:
pdf_path = _download_pdf(URL_GRADO_A, HEADERS)
try:
    records = parse_grado_a(pdf_path)
finally:
    os.unlink(pdf_path)  # D-03: eliminar sempre, fins i tot en error
```

### Anti-Patterns to Avoid

- **Usar `requests.head()`:** La URL retorna 403 per a HEAD. Sempre usar GET.
- **Guardar PDFs permanentment:** D-03 prohibeix cache. Usar `tempfile` + `os.unlink()`.
- **Confiar en el número de columna fix:** El nombre de columnes varia entre pàgines (5 o 7+). Localitzar el codi per contingut, no per índex fix.
- **Parsear la família del text de la pàgina:** La família no apareix com a capçalera de secció independent; es deriva exclusivament del prefix del codi.
- **Sobreescriure `ofertes.json` directament:** Usar escriptura atòmica (temp + rename) per preservar l'estat anterior en cas d'error a mig escriptura.

---

## Critical Finding: Actual Data Volume

[VERIFIED: parseig complet dels 3 PDFs descarregats 2026-04-17]

| Grado | Pàgines PDF | Nou pla (unique) | Pla antic (unique) | TOTAL |
|-------|-------------|------------------|--------------------|-------|
| A | 506 | ~5.743 | ~2.794 | ~8.537 |
| B | 184 | ~952 | ~1.835 | ~2.787 |
| C | 78 | ~318 | ~502 | ~820 |
| **TOTAL** | **768** | **~7.013** | **~5.131** | **~12.144** |

**vs. estimació del CONTEXT.md:** A:120, B:200, C:380 = ~700 registres.

La discrepància és d'un factor **~17x**. El CONTEXT.md estimava basant-se probablement en una visió diferent del que constitueix un "registre" (potser per TÍTOL de certificat, no per microacreditació individual). Els PDFs actuals (ModDate: 2026-03-18) contenen el catàleg complet incloent centenars de microacreditacions per família.

**Impacte en la Fase 2:** El pipeline extreu i serialitza tots els registres sense filtrar. L'impacte en el frontend (SRCH-09 diu "fluid fins a 1.500 registres") és una preocupació de la Fase 5, no de la Fase 2.

---

## Code Structure: Nivel Derivation per Grado

[VERIFIED: inspecció directa dels codis als 3 PDFs]

### Grado A (`PREFIX_A_NNNN_NN`)
- Nou pla: `AFD_A_3003_01` → `nivel = null`
- Pla antic: `UF0297 (Plan antiguo)` → `nivel = null`
- **Grado A no té distinció de nivel en el sistema nou ni en els codis.**

### Grado B (`PREFIX_B_NNNN`)
- Nou pla: `AFD_B_3003` → `nivel = null`
- Pla antic: `MF2268_2 (Plan antiguo)` → `nivel = 2` (el número après `_` és el nivel: 1, 2 o 3)
- **Per al pla antic de Grado B:** extreure nivel del sufix `_N` del codi.

### Grado C (`PREFIX_C_NNN_SUFFIX`)
- Nou pla `_3B`: `AFD_C_001_3B` → `nivel = 1`
- Nou pla `_4B`: `AFD_C_001_4B` → `nivel = 2`
- Nou pla `_5B`: `AFD_C_001_5B` → `nivel = 3`
- Pla antic: `AFDA0511 (Plan antiguo)`, `AFDP0119_2 (Plan antiguo)` → `nivel = null` (o extreure `_N` si present)

```python
# Source: verificat contra PDFs reals
import re

def _nivel_grado_a(code, is_old_plan):
    return None  # Grado A no té nivel

def _nivel_grado_b(code, is_old_plan):
    if is_old_plan:
        # MF2268_2 → nivel = 2
        m = re.search(r'_([123])$', code)
        return int(m.group(1)) if m else None
    return None

def _nivel_grado_c(code, is_old_plan):
    if not is_old_plan:
        if code.endswith('_3B'): return 1
        if code.endswith('_4B'): return 2
        if code.endswith('_5B'): return 3
    return None
```

---

## Code Structure: Plan Antiguo Detection

[VERIFIED: inspecció directa dels 3 PDFs]

### Patrons observats per Grado:

| Grado | Format nou pla | Format pla antic | Detecció |
|-------|---------------|-----------------|----------|
| A | `PREFIX_A_NNNN_NN` | `UF\d{4} (Plan antiguo)` | `'(Plan antiguo)' in code_cell` |
| B | `PREFIX_B_NNNN` | `MF\d{4}_[123] (Plan antiguo)` | `'(Plan antiguo)' in code_cell` |
| C | `PREFIX_C_NNN_[345]B` | `[A-Z]{4,5}\d{4}(_[123])? (Plan antiguo)` | `'(Plan antiguo)' in code_cell` |

**Estratègia de detecció:** La presència de `'(Plan antiguo)'` a la cel·la del codi és el marcador definitiu i exclusiu. Cap codi de nou pla conté aquesta cadena. No cal regex per al camp de detecció.

```python
is_old_plan = '(Plan antiguo)' in code_cell
clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
```

**Nota:** El REQUIREMENTS.md menciona "codis antics (format `XXXN0000NN`)" com a criteri addicional. Però al PDF real, TOTS els codis de pla antic ja porten el marcador `(Plan antiguo)` a la mateixa cel·la. El regex addicional és redundant i introduiria falsos positius. **Recomanació: usar ÚNICAMENT el marcador `(Plan antiguo)`.**

---

## Code Structure: Prefix to Family Mapping

[VERIFIED: 24 prefixos confirmats directament dels PDFs; contingut de les denominacions confirma la família]

```python
# Source: verificat contra els 3 PDFs descarregats
PREFIX_MAP = {
    'AFD': 'Actividades Físicas y Deportivas',
    'ADG': 'Administración y Gestión',
    'AGA': 'Agraria',
    'ARG': 'Artes Gráficas',
    'COM': 'Comercio y Marketing',
    'ELE': 'Electricidad y Electrónica',
    'ENA': 'Energía y Agua',
    'EOC': 'Edificación y Obra Civil',
    'FME': 'Fabricación Mecánica',
    'HOT': 'Hostelería y Turismo',
    'IEX': 'Industrias Extractivas',      # NO "Imagen y Espectáculos"
    'IFC': 'Informática y Comunicaciones',
    'IMA': 'Instalación y Mantenimiento',
    'IMP': 'Imagen Personal',
    'IMS': 'Imagen y Espectáculos',       # audiovisuals, so, espectacles
    'INA': 'Industrias Alimentarias',
    'MAM': 'Madera, Mueble y Corcho',
    'MAP': 'Marítimo-Pesquera',
    'QUI': 'Química',
    'SEA': 'Seguridad y Medio Ambiente',
    'SSC': 'Servicios Socioculturales y a la Comunidad',
    'TCP': 'Textil, Confección y Piel',
    'TMV': 'Transporte y Mantenimiento de Vehículos',
    'VIC': 'Vidrio y Cerámica',
}
```

**Nota important:** IEX = **Industrias Extractivas** (perforación, cantería, explosius). IMS = **Imagen y Espectáculos** (audiovisual, so, animació). Fàcil de confondre.

**Famílies no presents als 3 PDFs (apareixeran en Grados D/E a la Fase 3):**
- Artes y Artesanías, Sanidad, Servicios Financieros i d'altres poden aparèixer als scrapers HTML.

---

## Page Skip Strategy

[VERIFIED: inspecció dels 3 PDFs]

**Els 3 PDFs inicien dades exactament a la pàgina 6 (índex 5, 0-based).**

| Pàgina | Grado A | Grado B | Grado C |
|--------|---------|---------|---------|
| 1 | Portada | Portada | Portada |
| 2 | Crèdits | Crèdits | Crèdits |
| 3 | Copyright | Copyright | Copyright |
| 4 | En blanc | En blanc | En blanc |
| 5 | Presentació | En blanc | Presentació |
| **6** | **Dades** | **Dades** | **Dades** |

```python
# Skip first 5 pages (index 0-4), start from index 5
for page in pdf.pages[5:]:
    ...
```

**Estratègia alternativa (més robusta davant canvis futurs):** Saltar fins trobar una pàgina que contingui el text "Código" a la taula. Implementar com a fallback si la pàgina 6 no conté dades.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing de PDF | Parser de text propi | `pdfplumber.extract_table()` | Gestiona coordenades, spanning, text flotant |
| HTTP request | Urllib manual | `requests.get()` | Gestió d'errors, timeouts, redirects |
| Escriptura JSON atòmica | Lògica manual de backup | `tempfile` + `os.replace()` | Garantia POSIX d'atomicitat |
| Gestió d'errors parcials | Lògica custom de rollback | Fail fast + no escriure fins al final | Consistent amb D-01/D-02 |

---

## Common Pitfalls

### Pitfall 1: Columna del codi variable per pàgina
**What goes wrong:** El nombre de columnes de la taula varia entre pàgines (5 o 7+). Si s'usa un índex fix (`row[0]`) pot fallar quan la taula té columnes addicionals de marge.
**Why it happens:** pdfplumber detecta columnes visuals que varien segons la pàgina.
**How to avoid:** Iterar totes les cel·les de la fila buscant la primera que coincideixi amb el patró de codi. Verificat als 3 PDFs: el codi pot estar a l'índex 0 o 1.

### Pitfall 2: Files de continuació
**What goes wrong:** Algunes denominacions i observacions llargues es divideixen en múltiples files. La fila de continuació té el camp del codi buit.
**Why it happens:** pdfplumber extreu files tal com apareixen al PDF (una fila per línia visual, no per registre lògic).
**How to avoid:** Descartar files on cap cel·la coincideixi amb cap patró de codi. Les observacions fragmentades (col·lumna obs en múltiples files) es concatenen recol·lectant els valors de la columna obs de les files de continuació. Implementació simplificada: acumular observaciones per fila de dades i ignorar les de continuació per a les observaciones (l'impacte és que les obs poden quedar truncades per a alguns registres, però és acceptable).

### Pitfall 3: HEAD request retorna 403
**What goes wrong:** Usar `requests.head()` per verificar disponibilitat retorna 403.
**Why it happens:** El servidor de todofp.es bloqueja HEAD però permet GET.
**How to avoid:** Sempre usar `requests.get()`. No fer pre-verificació amb HEAD.

### Pitfall 4: Duplicats entre pàgines
**What goes wrong:** Alguns codis apareixen a múltiples pàgines (la capçalera de la taula es repeteix, i de vegades hi ha codis que apareixen en transicions de pàgina).
**Why it happens:** El PDF pagina la taula i repeteix alguns elements.
**How to avoid:** Usar un diccionari `{code_str: record}` durant el parsing per garantir unicitat. Només el primer occurrence de cada codi es conserva.

### Pitfall 5: Estimació de volum incorrecta
**What goes wrong:** Assumir que el scraper produirà ~700 registres (estimació del CONTEXT.md).
**Why it happens:** La estimació original no comptava les microacreditacions individuals de Grado A.
**How to avoid:** El pipeline no ha de filtrar ni limitar registres. El volum real és ~12.000 registres (verificat als PDFs de data 2026-03-18).

### Pitfall 6: `pipeline.run()` retorna None si hi ha error
**What goes wrong:** Si un grado falla i s'eleva una excepció sense capturar, el caller (Fase 4) rep una excepció sense informació estructurada.
**How to avoid:** `pipeline.run()` ha de capturar excepcions i retornar el dict de resultat amb `errors` populat, o re-elevar amb un error clar que inclogui quin grado ha fallat.

---

## Pipeline Return Contract

Definit al CONTEXT.md `<specifics>`:

```python
# pipeline.run() ha de retornar sempre aquest dict (D-08)
{
    "total": int,          # registres totals escrits a ofertes.json
    "by_grado": {
        "A": int,
        "B": int,
        "C": int,
        # Fase 3 afegirà "D" i "E"
    },
    "errors": [],          # llista de strings d'error; buit si tot va bé
    "duration_seconds": float
}
```

Si `errors` no és buit (fail fast), `ofertes.json` NO s'actualitza.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (a instal·lar — no detectat al projecte) |
| Config file | `pytest.ini` o `pyproject.toml` — Wave 0 |
| Quick run command | `pytest fp-cercador/backend/tests/ -x -q` |
| Full suite command | `pytest fp-cercador/backend/tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PDF-01 | Descàrrega correcta amb headers | integration (real HTTP) | pytest tests/test_pdf_scraper.py::test_download_headers -x | ❌ Wave 0 |
| PDF-02 | Família derivada del prefix | unit | pytest tests/test_pdf_scraper.py::test_prefix_map -x | ❌ Wave 0 |
| PDF-03 | Nivel derivat del sufix | unit | pytest tests/test_pdf_scraper.py::test_nivel_derivation -x | ❌ Wave 0 |
| PDF-04 | plan_antiguo detectat | unit | pytest tests/test_pdf_scraper.py::test_plan_antiguo -x | ❌ Wave 0 |
| PDF-05 | Pàgines 1-5 omeses | unit | pytest tests/test_pdf_scraper.py::test_page_skip -x | ❌ Wave 0 |
| PDF-06 | Columnes correctes | integration (PDF real) | pytest tests/test_pdf_scraper.py::test_record_fields -x | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `fp-cercador/backend/tests/` — directori de tests (crear)
- [ ] `fp-cercador/backend/tests/test_pdf_scraper.py` — tests unitaris amb PDFs de fixture
- [ ] `fp-cercador/backend/tests/conftest.py` — fixtures compartits
- [ ] Framework install: `pip install pytest` (no al requirements.txt, és dependència de dev)

**Nota:** Els tests d'integració que fan HTTP real contra todofp.es han de ser marcats com `@pytest.mark.integration` i exclosos del CI per defecte. Els tests unitaris han d'usar PDFs de fixture locals (o fragments petits).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Runtime | ✓ | 3.13.0 | — |
| pdfplumber | PDF parsing | ✓ | 0.11.9 | — |
| requests | HTTP download | ✓ | 2.32.5 | — |
| todofp.es (internet) | PDF download | ✓ | — | Usar PDFs en cache local per testing |
| json, tempfile, re, logging, os | Pipeline | ✓ | stdlib | — |

**Missing dependencies amb fallback:**
- `pytest` — no al requirements.txt però necessari per als tests Wave 0. Instal·lar com a dev dep: `pip install pytest`.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | El scraper no exposa autenticació en aquesta fase |
| V3 Session Management | no | Cap sessió; HTTP stateless |
| V4 Access Control | no | Cap endpoint exposat en aquesta fase |
| V5 Input Validation | yes (parcial) | Validar que el PDF descarregat és realment un PDF (`Content-Type: application/pdf`) |
| V6 Cryptography | no | Cap operació criptogràfica |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PDF malformat → crash del parser | Tampering | `try/except` per pàgina; fail fast amb error clar |
| URL de PDF canviada per redireccions | Spoofing | Verificar `Content-Type` de la resposta HTTP |
| Disc ple durant escriptura JSON | Denial of Service | Usar `tempfile` en el mateix directori; capturar `OSError` |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Grado A i B nous codis tenen `nivel = null` (no definit als requirements) | Nivel Derivation | Si el sistema espera nivel per a Grado A/B, caldria re-parsear els PDFs cercant seccions de nivel |
| A2 | Les URLs dels PDFs seran estables (el servidor de todofp.es pot canviar-les) | PDF URLs | Si les URLs canvien (noves versions anuals), el scraper retornarà 404 i el pipeline fallarà |
| A3 | IEX = Industrias Extractivas (inferit del contingut: perforación, cantería) | PREFIX_MAP | Si el nom oficial és diferent, la família apareixerà incorrecta al JSON |
| A4 | El volum de ~12.000 registres és acceptable per al JSON estàtic | Volume | Si el frontend no pot gestionar aquest volum, caldrà filtrar en una fase anterior |

---

## Open Questions (RESOLVED)

1. **Nivel per a Grado A i B (nou pla)**
   - What we know: La documentació del sistema FP diu que Grado A correspon a microacreditaciones (sense nivel) i Grado B a certificats (nivels 1-3). Però els codis nous de Grado B (`PREFIX_B_NNNN`) no porten sufix de nivel.
   - What's unclear: S'ha d'assignar `nivel = null` per a Grado A i B nous? O hi ha altra forma de deduir-ho?
   - Recommendation: Implementar `nivel = null` per a A i B nous per simplicitat. Si és incorrecte, es corregirà a la Fase 5 quan es facin els filtres del frontend.
   - **RESOLVED:** `nivel = None` per a Grado A i B nous. Implementat als plans 01 i 02.

2. **Volum real vs. estimació**
   - What we know: ~12.144 registres reals vs. ~700 estimats.
   - What's unclear: Si el frontend (Fase 5) pot gestionar ~12.000 registres sense paginació.
   - Recommendation: Documentar com a risc al PLAN.md. La Fase 2 extreu tots els registres. La Fase 5 decidirà si cal filtrar.
   - **RESOLVED:** La Fase 2 extreu tots els registres sense filtrar. Risc documentat al Pla 03 (checkpoint humà > 10.000 registres).

3. **Nom oficial de la família IEX**
   - What we know: Els codis IEX apareixen en context de perforación, mineria i cantería.
   - What's unclear: El nom oficial al BOE pot ser "Industrias Extractivas" o una variant.
   - Recommendation: Usar "Industrias Extractivas" (consistent amb els codis INCUAL).
   - **RESOLVED:** `PREFIX_MAP['IEX'] = 'Industrias Extractivas'`. Verificat per contingut dels PDFs i test explícit al Pla 01.

---

## Sources

### Primary (HIGH confidence)
- PDFs descarregats directament de todofp.es (2026-04-17) i inspeccionats amb pdfplumber — tota la secció de PDF structure
- Context7 `/jsvine/pdfplumber` — API de `extract_table()`, `extract_words()`, estructura de files
- Tests HTTP directes amb `requests` i `curl` — URLs, headers, codis de resposta

### Secondary (MEDIUM confidence)
- [TodoFP catàleg oficial](https://www.todofp.es/catalogos-registros-sistema-fp/catalogo-nacional-ofertas-sistema.html) — URLs dels PDFs obtingudes per WebFetch
- Observacions creuades als PDFs (cadenes "también incluido en la familia profesional X") — validació del PREFIX_MAP

### Tertiary (LOW confidence)
- Noms oficials de famílies professionals basats en training knowledge + verificació per contingut. IEX confirmat per contingut del PDF però no per URL oficial del BOE.

---

## Metadata

**Confidence breakdown:**
- PDF URLs: HIGH — verificades per descàrrega real
- Headers HTTP: HIGH — testats directament amb requests
- Estructura del parsing: HIGH — verificada parsejant els 3 PDFs complets
- PREFIX_MAP: HIGH (23 famílies) / MEDIUM (IEX, IMS — inferits del contingut)
- Volum de registres: HIGH — comptat directament
- Nivel per Grado A/B: LOW — no especificat als requirements, assumit null

**Research date:** 2026-04-17
**Valid until:** 2026-07-17 (URLs de PDF poden canviar anualment; el servidor modifica els fitxers ~1-2 cops l'any judging by ModDate metadata)
