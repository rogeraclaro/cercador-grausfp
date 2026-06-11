# Plan 003: Eliminar el codi mort de pdf_scraper i la dependència pdfplumber

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- backend/scrapers/ backend/tests/ backend/requirements.txt`
> Si els imports de "Current state" no coincideixen amb el codi viu, STOP.

## Status

- **Priority**: P2
- **Effort**: S
- **Risk**: LOW
- **Depends on**: plans/002-reparar-suite-de-tests.md (cal una suite verda abans de retallar)
- **Category**: tech-debt
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Des del commit `9922870`, els Grados A/B/C s'extreuen de l'API REST del
buscador i el parsing de PDFs no s'executa mai. De `pdf_scraper.py`
(305 línies) només s'usen dos diccionaris de constants (`PREFIX_MAP` i
`FAMILY_ALIASES`). Queden ~250 línies de codi mort, 397 línies de tests que
proven codi mort (`test_pdf_scraper.py`) i una dependència pesada
(`pdfplumber`) al `requirements.txt`. Treure-ho redueix la superfície de
manteniment i el temps d'instal·lació al VPS.

## Current state

Fitxers rellevants (rutes relatives a `fp-cercador/`):

- `backend/scrapers/pdf_scraper.py` — conté `PREFIX_MAP` (línies 25–58) i
  `FAMILY_ALIASES` (línies 63–70), que SÍ s'usen, més tot el parsing PDF
  (funcions `parse_grado_a/b/c`, `_extract_records`, `_parse_row`,
  `_nivel_grado_*`, `_get_nivel_from_page`, `_get_familia_from_page`) que NO
  s'usa enlloc fora dels seus propis tests.
- Consumidors de les constants:
  - `backend/scrapers/pipeline.py:26` →
    `from scrapers.pdf_scraper import FAMILY_ALIASES, PREFIX_MAP`
  - `backend/scrapers/html_scraper.py:36` →
    `from scrapers.pdf_scraper import FAMILY_ALIASES, PREFIX_MAP`
    (i a la línia 60: `HTML_FAMILY_ALIASES = FAMILY_ALIASES`)
- `backend/tests/test_pdf_scraper.py` — 397 línies, prova només codi mort.
- `backend/tests/conftest.py` — primera línia del docstring: "Fixtures
  compartides per als tests de pdf_scraper". Conté la línia CRÍTICA
  `os.environ.setdefault("ADMIN_TOKEN", "test-token")` (línia 9) que usa
  `test_api.py`, i fixtures `sample_table_*` que probablement només usa
  `test_pdf_scraper.py`. ATENCIÓ: pot contenir també fixtures
  `minimal_html_*` que usa `test_html_scraper.py` — verifica-ho abans
  d'esborrar res (Step 3).
- `backend/requirements.txt` — conté `pdfplumber`.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Suite | `python -m pytest tests/ -q` | 0 failed |
| Buscar usos | `grep -rn "pdf_scraper\|pdfplumber" --include="*.py" . \| grep -v __pycache__` | (vegeu cada step) |

## Scope

**In scope**:
- `backend/scrapers/families.py` (crear)
- `backend/scrapers/pdf_scraper.py` (eliminar)
- `backend/scrapers/pipeline.py` (només la línia d'import)
- `backend/scrapers/html_scraper.py` (només la línia d'import i comentaris adjacents)
- `backend/tests/test_pdf_scraper.py` (eliminar)
- `backend/tests/conftest.py` (només podar fixtures òrfenes)
- `backend/requirements.txt` (treure pdfplumber)

**Out of scope**:
- Qualsevol canvi al CONTINGUT de `PREFIX_MAP` o `FAMILY_ALIASES` — es mouen
  verbatim, byte a byte, comentaris inclosos.
- `backend/app.py`, `frontend/`.
- El docstring general de `pipeline.py` (l'actualitza el pla 011).

## Git workflow

- Un sol commit atòmic a `master`:
  `refactor: moure PREFIX_MAP/FAMILY_ALIASES a families.py i eliminar pdf_scraper mort`
- NO push sense instrucció.

## Steps

### Step 1: Crear backend/scrapers/families.py

Nou fitxer amb aquest esquelet, copiant els dos diccionaris **verbatim** de
`pdf_scraper.py` (PREFIX_MAP de les línies 25–58, FAMILY_ALIASES de les
línies 63–70, amb tots els comentaris inline):

```python
"""
families.py — Catàleg canònic de famílies professionals FP.

PREFIX_MAP: prefix de codi → nom canònic de família (24 famílies + extres
del pla antic/LOGSE/HTML-only).
FAMILY_ALIASES: nom no canònic (variants de les fonts) → nom canònic.
S'aplica a pipeline.py sobre tots els registres (A–E).

Origen: extret de l'antic pdf_scraper.py quan es va eliminar el parsing de
PDFs (els Grados A/B/C ara surten de l'API REST del buscador).
"""

PREFIX_MAP = {
    # ... copiar verbatim ...
}

FAMILY_ALIASES: dict[str, str] = {
    # ... copiar verbatim ...
}
```

**Verify**:
```bash
python -c "
from scrapers.families import PREFIX_MAP, FAMILY_ALIASES
from scrapers.pdf_scraper import PREFIX_MAP as P2, FAMILY_ALIASES as F2
assert PREFIX_MAP == P2 and FAMILY_ALIASES == F2
print('Diccionaris idèntics OK')
"
```
→ `Diccionaris idèntics OK`

### Step 2: Canviar els dos imports

- `backend/scrapers/pipeline.py:26`:
  `from scrapers.pdf_scraper import FAMILY_ALIASES, PREFIX_MAP`
  → `from scrapers.families import FAMILY_ALIASES, PREFIX_MAP`
- `backend/scrapers/html_scraper.py:36`: idem. Actualitza també el comentari
  de la línia 58 (`# HTML_FAMILY_ALIASES és ara FAMILY_ALIASES importat de
  pdf_scraper.py.`) per dir `families.py`.

**Verify**: `python -m pytest tests/ -q` → 0 failed (tot encara existeix).

### Step 3: Identificar què usa conftest.py abans de podar

```bash
grep -n "def \|fixture" tests/conftest.py
grep -rn "sample_table\|minimal_html\|mock_pdf" tests/test_html_scraper.py tests/test_api.py tests/test_pipeline.py
```

Regla: una fixture de `conftest.py` només es pot esborrar si NO apareix a
cap test que sobrevisqui (`test_api.py`, `test_html_scraper.py`,
`test_pipeline.py`). La línia `os.environ.setdefault("ADMIN_TOKEN", ...)`
es manté SEMPRE. Si `test_html_scraper.py` usa fixtures de conftest,
mantén-les.

### Step 4: Eliminar el codi mort

```bash
git rm backend/scrapers/pdf_scraper.py backend/tests/test_pdf_scraper.py
```
(executa des de l'arrel `fp-cercador/`; ajusta rutes si cal). Després poda
de `conftest.py` només les fixtures que el Step 3 ha confirmat òrfenes, i
actualitza el docstring de conftest ("Fixtures compartides per als tests").
Finalment treu la línia `pdfplumber` de `backend/requirements.txt`.

**Verify**:
```bash
grep -rn "pdf_scraper\|pdfplumber" --include="*.py" backend | grep -v __pycache__
```
→ cap resultat.

### Step 5: Suite verda i imports nets

**Verify** (des de `backend/`):
```bash
python -m pytest tests/ -q && python -c "import app; print('app importa OK')"
```
→ 0 failed i `app importa OK`.

## Test plan

No hi ha tests nous: el canvi és un moviment de constants + esborrat. La
suite existent (plans 001–002) verifica les rutes d'import i la normalització
de famílies (test `test_family_alias_normalization` del pla 002 exercita
`FAMILY_ALIASES` via el nou mòdul).

## Done criteria

- [ ] `backend/scrapers/families.py` existeix amb els dos dicts idèntics als originals
- [ ] `backend/scrapers/pdf_scraper.py` i `backend/tests/test_pdf_scraper.py` no existeixen
- [ ] `grep -rn "pdf_scraper\|pdfplumber" --include="*.py" backend | grep -v __pycache__` → buit
- [ ] `grep pdfplumber backend/requirements.txt` → buit
- [ ] `cd backend && python -m pytest tests/ -q` → 0 failed
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- Trobes algun ús de `parse_grado_a/b/c` o `pdfplumber` fora de
  `pdf_scraper.py` i els seus tests (vol dir que el codi NO és mort).
- Els diccionaris copiats no passen la verificació d'identitat del Step 1.
- `test_html_scraper.py` falla després de podar conftest (has esborrat una
  fixture viva — restaura-la).

## Maintenance notes

- A partir d'ara, famílies noves detectades pel warning de
  `pipeline.py` ("Família nova detectada al refresh") s'afegeixen a
  `backend/scrapers/families.py`, no a pdf_scraper.
- El pla 011 actualitza el docstring de `pipeline.py`; si aquest pla es fa
  abans, el docstring encara mencionarà coses velles — és esperat.
- Revisor: l'únic risc real és el contingut dels diccionaris; el Step 1 ho
  verifica mecànicament abans d'esborrar l'original.
