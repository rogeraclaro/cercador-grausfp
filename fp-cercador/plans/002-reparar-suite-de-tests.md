# Plan 002: Reparar la suite de tests perquè provi l'arquitectura actual del pipeline

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- backend/tests/test_pipeline.py backend/tests/test_html_scraper.py backend/scrapers/pipeline.py`
> Si `pipeline.py` ha canviat des que es va escriure el pla, compara els
> extractes de "Current state" amb el codi viu; si no coincideixen, STOP.

## Status

- **Priority**: P1
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans/001-aillar-tests-de-dades-reals.md
- **Category**: tests
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

10 tests fallen: 9 de `test_pipeline.py` proven una arquitectura eliminada
(el pipeline antic descarregava PDFs amb `requests.get` i cridava
`parse_grado_a/b/c`; al commit `9922870` es va substituir per l'API REST del
buscador), i 1 de `test_html_scraper.py` té un assert desfasat (el nom
canònic de la família va canviar al commit `b5957af`). Sense una suite verda
no hi ha línia base de verificació per a cap altre canvi del backend — aquest
pla desbloqueja tots els altres.

## Current state

Fitxers rellevants (rutes relatives a `fp-cercador/`):

- `backend/scrapers/pipeline.py` — l'orquestrador ACTUAL. Flux de `run()`
  (línies 81–176): crida `parse_buscador_all()` (una sola vegada, retorna
  `{'A': [...], 'B': [...], 'C': [...]}`), després els 4 parsers HTML
  (`parse_grado_d_basico/medio/superior`, `parse_grado_e`), afegeix `grado`
  a cada registre, normalitza `familia` amb `FAMILY_ALIASES`, detecta
  famílies desconegudes contra `set(PREFIX_MAP.values())`, assigna `id`
  seqüencial 1-based en ordre A→B→C→D→E, escriu `ofertes.json` atòmicament
  via `_write_atomic` (tempfile + `os.replace`) i retorna:
  ```python
  {
      "total": ..., "by_grado": {...}, "families": [...],
      "denominacions": [...], "denominacions_by_grado": {...},
      "errors": [], "unknown_families": [...], "duration_seconds": ...,
  }
  ```
  També crida `load_dotenv(override=True)` al principi (línia 102) i té la
  constant `DATA_PATH` a les línies 48–50.
- `backend/tests/test_pipeline.py` — 469 línies escrites per al pipeline
  ANTIC. Les constants de patch (línies 34–44) referencien símbols que ja no
  existeixen al namespace de pipeline: `scrapers.pipeline.requests.get`,
  `scrapers.pipeline.parse_grado_a/b/c`, `scrapers.pipeline.os.unlink`.
  Per això fallen amb `AttributeError: module 'scrapers.pipeline' has no
  attribute 'requests'`.
- `backend/tests/test_html_scraper.py:109` — assert desfasat:
  ```python
  assert HTML_FAMILY_ALIASES['Artes y Artesanias'] == 'Artesanía'
  ```
  El valor real actual (vegeu `backend/scrapers/pdf_scraper.py:63-70`,
  dict `FAMILY_ALIASES`) és `'Artes y Artesanías'`.
- `backend/scrapers/buscador_scraper.py:113-122` — `_map_record` defineix el
  schema dels registres A/B/C:
  ```python
  {'codigo', 'denominacion', 'familia', 'nivel', 'plan_antiguo',
   'observaciones', 'ficha_id'}
  ```
  Els registres D/E (html_scraper) tenen el mateix schema però amb
  `codigo=None` i `ficha_url` en lloc de `ficha_id`.

Convencions de test del repo: constants de patch-path al principi del mòdul,
helpers `_make_record(...)`, `mock.patch` com a context manager, docstrings
amb l'ID de requisit. Vegeu `test_api.py` com a exemplar d'estil.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/backend/`) | Esperat |
|---|---|---|
| Suite completa | `python -m pytest tests/ -q` | en acabar: 0 failed |
| Només pipeline | `python -m pytest tests/test_pipeline.py -q` | tots passen |
| Només html | `python -m pytest tests/test_html_scraper.py -q` | tots passen |

## Scope

**In scope** (únics fitxers a modificar):
- `backend/tests/test_pipeline.py` (reescriptura)
- `backend/tests/test_html_scraper.py` (només la línia 109)

**Out of scope** (NO tocar):
- `backend/scrapers/pipeline.py` — els tests s'adapten al codi, no al revés.
- `backend/scrapers/pdf_scraper.py` i `backend/tests/test_pdf_scraper.py` —
  s'eliminen al pla 003; aquí déixa'ls intactes.
- `backend/tests/conftest.py`.

## Git workflow

- Commits a `master`, estil: `fix(tests): reescriure test_pipeline per a l'arquitectura buscador+HTML`.
- Un commit per la línia de test_html_scraper, un per la reescriptura de
  test_pipeline (o un de sol si ho prefereixes — atòmic i coherent).
- NO push sense instrucció de l'operador.

## Steps

### Step 1: Arreglar l'assert desfasat de test_html_scraper.py

Línia 109, canvia:
```python
assert HTML_FAMILY_ALIASES['Artes y Artesanias'] == 'Artesanía'
```
per:
```python
assert HTML_FAMILY_ALIASES['Artes y Artesanias'] == 'Artes y Artesanías'
```

**Verify**: `python -m pytest tests/test_html_scraper.py -q` → tots passen.

### Step 2: Reescriure test_pipeline.py per al pipeline actual

Substitueix el contingut sencer de `backend/tests/test_pipeline.py`. Manté
les convencions (constants de patch al principi, helper de registres).
Punts de patch correctes per a l'arquitectura actual:

```python
PATCH_PARSE_BUSCADOR = 'scrapers.pipeline.parse_buscador_all'
PATCH_PARSE_D_BASICO   = 'scrapers.pipeline.parse_grado_d_basico'
PATCH_PARSE_D_MEDIO    = 'scrapers.pipeline.parse_grado_d_medio'
PATCH_PARSE_D_SUPERIOR = 'scrapers.pipeline.parse_grado_d_superior'
PATCH_PARSE_E          = 'scrapers.pipeline.parse_grado_e'
```

Per evitar escriure al `ofertes.json` real, redirigeix la constant a un
fitxer temporal a cada test (patró recomanat — fixture):

```python
@pytest.fixture(autouse=True)
def isolate_data_path(tmp_path, monkeypatch):
    import scrapers.pipeline as pl
    monkeypatch.setattr(pl, "DATA_PATH", str(tmp_path / "ofertes.json"))
```

Helper de registres (schema del buscador):

```python
def _rec(codigo='IFC_A_0001_AB', denominacion='Den X',
         familia='Informática y Comunicaciones', nivel=1):
    return {'codigo': codigo, 'denominacion': denominacion,
            'familia': familia, 'nivel': nivel, 'plan_antiguo': False,
            'observaciones': '', 'ficha_id': 1}
```

`parse_buscador_all` es mockeja retornant `{'A': [...], 'B': [...], 'C': [...]}`
i cada parser HTML retornant llistes de registres amb `codigo=None`,
`ficha_url='https://www.todofp.es/x'` (sense `ficha_id`).

Tests a escriure (mínim aquests 8):

1. **test_run_returns_schema** — `run()` retorna dict amb claus `total`,
   `by_grado`, `families`, `denominacions`, `denominacions_by_grado`,
   `errors`, `unknown_families`, `duration_seconds`; `errors == []`.
2. **test_run_adds_grado_and_sequential_ids** — cada registre té `grado` i
   els `id` són 1..N consecutius.
3. **test_id_order_a_b_c_d_e** — amb 1 registre per grado, l'ordre dels ids
   segueix A, B, C, D, E (D = basico+medio+superior en aquest ordre).
4. **test_by_grado_counts** — `by_grado` compta correctament (D suma els
   3 subtipus).
5. **test_family_alias_normalization** — un registre amb
   `familia='Imagen y Sonido'` surt amb `familia='Imagen y Espectáculos'`
   (via `FAMILY_ALIASES`) i NO apareix a `unknown_families`.
6. **test_unknown_family_reported** — un registre amb
   `familia='Família Inventada'` apareix a `unknown_families` i es loga un
   warning (usa `caplog.at_level(logging.WARNING, logger='scrapers.pipeline')`).
7. **test_fail_fast_buscador_error** — si `parse_buscador_all` aixeca
   `RuntimeError`, `run()` propaga l'excepció i el fitxer `DATA_PATH`
   (tmp) NO existeix.
8. **test_fail_fast_html_error** — si `parse_grado_e` aixeca `HTTPError`
   (de `requests.exceptions`), `run()` propaga i `DATA_PATH` NO existeix.
9. **test_atomic_write_output_valid_json** — després de `run()`, el fitxer
   `DATA_PATH` existeix i `json.load` el llegeix; el nombre de registres
   coincideix amb `total`.

Nota: `run()` crida `load_dotenv(override=True)` — és innocu als tests
(llegeix el `.env` local si existeix); no cal mockejar-lo.

**Verify**: `python -m pytest tests/test_pipeline.py -q` → 9 passed (o més).

### Step 3: Suite completa verda

**Verify**: `python -m pytest tests/ -q` → `0 failed` (seran ~68+ passed,
incloent els de test_pdf_scraper que encara existeixen).

Commit: `fix(tests): reescriure test_pipeline per a l'arquitectura buscador+HTML i actualitzar alias`

## Test plan

Aquest pla ÉS el test plan: 9 tests nous a `backend/tests/test_pipeline.py`
seguint el patró estructural de `backend/tests/test_api.py` (fixtures +
constants de patch + docstrings descriptius).

## Done criteria

- [ ] `cd backend && python -m pytest tests/ -q` → exit 0, 0 failed
- [ ] `grep -n "scrapers.pipeline.requests\|parse_grado_a\b" tests/test_pipeline.py` → cap resultat
- [ ] El md5 de `backend/data/ofertes.json` i `backend/data/refresh_history.json` no canvia en executar la suite
- [ ] `git status` net fora dels 2 fitxers in-scope
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- `pipeline.run()` no coincideix amb la descripció de "Current state"
  (p. ex. ja no crida `parse_buscador_all` o el dict de retorn té claus
  diferents) — el codi ha derivat.
- Algun test nou requereix modificar `pipeline.py` per passar — els tests
  han de descriure el comportament actual, no canviar-lo.
- Després d'executar la suite, algun fitxer de `backend/data/` ha canviat
  (l'aïllament del pla 001 no funciona o falta cobrir una via d'escriptura).

## Maintenance notes

- Quan s'executi el pla 003 (eliminar `pdf_scraper`), els imports de
  `FAMILY_ALIASES`/`PREFIX_MAP` canviaran de mòdul; aquests tests no els
  importen directament de `pdf_scraper`, així que no s'han de trencar —
  però verifica-ho llavors.
- El pla 006 canvia el format de persistència de l'historial; no afecta
  aquests tests (no toquen historial).
- Revisor: comprova que els tests de fail-fast asserten **absència** del
  fitxer de sortida, no només l'excepció — aquesta és la garantia D-02
  ("tot o res") del pipeline.
