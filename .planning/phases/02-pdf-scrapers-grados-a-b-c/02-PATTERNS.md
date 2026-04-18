# Phase 2: PDF Scrapers (Grados A, B, C) - Pattern Map

**Mapped:** 2026-04-16
**Files analyzed:** 4 (2 nous + 2 existents modificats/llegits)
**Analogs found:** 0 / 2 (cap analog intern — projecte nou sense scrapers)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `fp-cercador/backend/scrapers/pdf_scraper.py` | service | file-I/O + transform | cap — projecte nou | no analog |
| `fp-cercador/backend/scrapers/pipeline.py` | service | batch + file-I/O | cap — projecte nou | no analog |
| `fp-cercador/backend/data/ofertes.json` | output artifact | — | existent (mostra) | referència d'esquema |
| `fp-cercador/backend/scrapers/__init__.py` | config | — | existent (stub) | existent — no modificar |

---

## Pattern Assignments

### `fp-cercador/backend/scrapers/pdf_scraper.py` (service, file-I/O + transform)

**Analog:** cap intern. Patrons extrets de RESEARCH.md (verificats contra els PDFs reals).

**Imports pattern** (des de RESEARCH.md — verificat):
```python
import re
import logging
import pdfplumber
```

**Constants pattern** — PREFIX_MAP complet (24 prefixos verificats directament dels PDFs):
```python
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
    'IEX': 'Industrias Extractivas',
    'IFC': 'Informática y Comunicaciones',
    'IMA': 'Instalación y Mantenimiento',
    'IMP': 'Imagen Personal',
    'IMS': 'Imagen y Espectáculos',
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
# NOTA: IEX != IMS. IEX = mineria/cantería. IMS = audiovisual/espectacles.
```

**Core parsing pattern** — extracció de taules amb pdfplumber (RESEARCH.md Pattern 1):
```python
def _extract_records(pdf_path, grado_letter, nivel_fn):
    """Extreu registres d'un PDF de Grado X."""
    records = {}  # code_str -> record dict (per garantir unicitat entre pàgines)
    new_code_re = re.compile(rf'^[A-Z]{{2,4}}_{grado_letter}_\d')

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[5:]:  # skip pàgines 1-5 (portada/intro — verificat als 3 PDFs)
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
                        logging.warning(
                            f"Família desconeguda per prefix '{prefix}' al codi '{clean_code}'"
                        )
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

**Row parsing pattern** — codi localitzat per contingut, no per índex fix (RESEARCH.md Pattern 2):
```python
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
# IMPORTANT: El nombre de columnes varia entre pàgines (5 o 7+).
# Mai usar row[0] com a índex fix — el codi pot estar a l'índex 0 o 1.
```

**Nivel derivation pattern** per cada Grado (RESEARCH.md — verificat directament als PDFs):
```python
def _nivel_grado_a(code, is_old_plan):
    return None  # Grado A no té nivel (nou ni antic)

def _nivel_grado_b(code, is_old_plan):
    if is_old_plan:
        m = re.search(r'_([123])$', code)
        return int(m.group(1)) if m else None
    return None  # Grado B nou pla no té nivel als codis

def _nivel_grado_c(code, is_old_plan):
    if not is_old_plan:
        if code.endswith('_3B'): return 1
        if code.endswith('_4B'): return 2
        if code.endswith('_5B'): return 3
    return None
```

**Plan antiguo detection pattern** (RESEARCH.md — marcador definitiu):
```python
# La presència de '(Plan antiguo)' a la cel·la del codi és l'únic marcador necessari.
# Cap regex addicional — introduiria falsos positius.
is_old_plan = '(Plan antiguo)' in code_cell
clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
```

**Interfície pública del mòdul** (D-07 — una funció per Grado):
```python
def parse_grado_a(pdf_path: str) -> list[dict]:
    return _extract_records(pdf_path, 'A', _nivel_grado_a)

def parse_grado_b(pdf_path: str) -> list[dict]:
    return _extract_records(pdf_path, 'B', _nivel_grado_b)

def parse_grado_c(pdf_path: str) -> list[dict]:
    return _extract_records(pdf_path, 'C', _nivel_grado_c)
```

**Esquema del registre de sortida** (derivat de `data/ofertes.json` existent):
```python
# Cada registre té exactament aquests camps (consistent amb ofertes.json de mostra):
{
    'grado': str,          # 'A', 'B' o 'C' — afegit pel pipeline, no pel pdf_scraper
    'familia': str,        # nom de la família o 'Desconeguda'
    'codigo': str,         # codi net sense ' (Plan antiguo)'
    'denominacion': str,   # text de la denominació
    'nivel': int | None,   # 1, 2, 3 o None
    'plan_antiguo': bool,  # True si porta '(Plan antiguo)'
    'observaciones': str,  # text de la columna d'observacions
}
# NOTA: el camp 'id' és afegit pel pipeline en enumerar tots els registres.
# El camp 'grado' és afegit pel pipeline, no per pdf_scraper.
```

---

### `fp-cercador/backend/scrapers/pipeline.py` (service, batch + file-I/O)

**Analog:** cap intern. Patrons extrets de RESEARCH.md (verificats).

**Imports pattern**:
```python
import json
import logging
import os
import tempfile
import time
import requests
from scrapers.pdf_scraper import parse_grado_a, parse_grado_b, parse_grado_c
```

**Download pattern** — descàrrega HTTP amb fail fast (RESEARCH.md Pattern 4):
```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.todofp.es/catalogos-registros-sistema-fp/catalogo-nacional-ofertas-sistema.html",
}

PDF_URLS = {
    'A': 'https://www.todofp.es/dam/jcr:a8580dd0-8106-4387-ae2a-8c6c1f23fa91/catalogo-grados-a.pdf',
    'B': 'https://www.todofp.es/dam/jcr:fbe95da3-7507-458a-ab0d-4202beea8d28/catalogo-grados-b.pdf',
    'C': 'https://www.todofp.es/dam/jcr:8b85fd78-c6d5-406f-ade8-891abd96613f/catalogo-grados-c.pdf',
}

def _download_pdf(url: str, timeout: int = 120) -> str:
    """Descarrega PDF a fitxer temporal. Retorna el path. Caller és responsable d'esborrar-lo."""
    # IMPORTANT: Mai usar requests.head() — retorna 403. Sempre GET.
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()  # 4xx/5xx → excepció (fail fast D-01)
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(resp.content)
        return tmp.name
```

**Atomic write pattern** — escriptura segura del JSON (RESEARCH.md Pattern 3):
```python
def _write_atomic(data: list, output_path: str) -> None:
    """Escriu JSON de manera atòmica: temp file + rename per evitar escriptures parcials."""
    dir_path = os.path.dirname(output_path)
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', suffix='.json',
        dir=dir_path, delete=False
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, output_path)  # atòmic en Unix (POSIX rename)
```

**Core pipeline pattern** — fail fast + retorn estructurat (D-01, D-02, D-08):
```python
def run() -> dict:
    """
    Executa el pipeline complet. Retorna resum estructurat.
    Si qualsevol Grado falla, ofertes.json NO s'actualitza (D-01/D-02).
    """
    start = time.time()
    parsers = {
        'A': (PDF_URLS['A'], parse_grado_a),
        'B': (PDF_URLS['B'], parse_grado_b),
        'C': (PDF_URLS['C'], parse_grado_c),
    }
    all_records = []
    by_grado = {}

    for grado_letter, (url, parser_fn) in parsers.items():
        pdf_path = None
        try:
            pdf_path = _download_pdf(url)
            records = parser_fn(pdf_path)
            for r in records:
                r['grado'] = grado_letter
            by_grado[grado_letter] = len(records)
            all_records.extend(records)
        finally:
            if pdf_path and os.path.exists(pdf_path):
                os.unlink(pdf_path)  # D-03: eliminar sempre, fins i tot en error

    # Afegir id seqüencial
    for i, record in enumerate(all_records, start=1):
        record['id'] = i

    output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ofertes.json')
    output_path = os.path.normpath(output_path)
    _write_atomic(all_records, output_path)

    return {
        "total": len(all_records),
        "by_grado": by_grado,
        "errors": [],
        "duration_seconds": round(time.time() - start, 2),
    }
# NOTA: El try/finally garanteix que el PDF temporal s'esborra sempre.
# Si _download_pdf() o parser_fn() eleven excepció, es propaga (fail fast D-01).
# ofertes.json no s'escriu si hi ha error — _write_atomic() no s'arriba a cridar.
```

**Return contract** (D-08, des de CONTEXT.md `<specifics>`):
```python
# pipeline.run() retorna sempre aquest dict:
{
    "total": int,           # registres totals escrits a ofertes.json
    "by_grado": {
        "A": int,
        "B": int,
        "C": int,
        # Fase 3 afegirà "D" i "E"
    },
    "errors": [],           # llista de strings d'error; buit si tot va bé
    "duration_seconds": float
}
# Si hi ha excepció no capturada, ofertes.json NO s'actualitza (D-01/D-02).
```

---

## Shared Patterns

### Logging de warnings (D-05)
**Aplica a:** `pdf_scraper.py` (registres amb família desconeguda)
**Patró:** `logging.warning(...)` — mai `print()`. El mòdul `logging` és stdlib.
```python
import logging
# A nivell de mòdul — cap configuració addicional; el caller (pipeline.py o app.py) configura el handler.
logging.warning(f"Família desconeguda per prefix '{prefix}' al codi '{clean_code}'")
```

### Gestió de fitxers temporals (D-03)
**Aplica a:** `pipeline.py` (PDFs temporals) i `pipeline.py` (JSON temporal per escriptura atòmica)
**Patró:** `tempfile.NamedTemporaryFile(delete=False)` + `os.unlink()` en `finally`.
```python
import tempfile, os
tmp_path = None
with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
    tmp.write(content)
    tmp_path = tmp.name
try:
    # usar tmp_path
finally:
    if tmp_path and os.path.exists(tmp_path):
        os.unlink(tmp_path)
```

### Fail fast (D-01)
**Aplica a:** `pipeline.py` (descàrrega i parse), `pdf_scraper.py` (per pàgina)
**Patró:** cap try/except que emmascaressin errors. `resp.raise_for_status()` a `_download_pdf()`. Excepció no capturada = pipeline s'atura, `ofertes.json` no s'escriu.

### Esquema de camps del registre
**Aplica a:** tots dos fitxers — la sortida de `pdf_scraper.py` ha de ser consistent amb l'esquema de `data/ofertes.json` (mostra existent a la línia 1–72):
```
id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones
```
El camp `grado` i `id` els afegeix `pipeline.py`, no `pdf_scraper.py`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `fp-cercador/backend/scrapers/pdf_scraper.py` | service | file-I/O + transform | No existeix cap scraper de PDF al projecte — creació neta |
| `fp-cercador/backend/scrapers/pipeline.py` | service | batch + file-I/O | No existeix cap pipeline d'orquestració — creació neta |

Els patrons de referència provenen exclusivament de RESEARCH.md (verificats contra els PDFs reals i la documentació de pdfplumber).

---

## Metadata

**Analog search scope:** `fp-cercador/backend/` (tot el backend)
**Files scanned:** 6 fitxers Python/JSON existents
**Pattern extraction date:** 2026-04-16

**Nota sobre el codebase:** El projecte és en fase inicial (Fase 1 completada). L'únic codi Python existent és `app.py` (stub Flask de 11 línies) i `scrapers/__init__.py` (1 línia de comentari). No hi ha cap analog intern per a scrapers, pipelines ni parsing. Tots els patrons provenen de la recerca verificada de RESEARCH.md.
