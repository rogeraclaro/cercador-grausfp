---
phase: 03-html-scrapers-data-pipeline-grados-d-e
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 8
files_reviewed_list:
  - fp-cercador/backend/tests/test_html_scraper.py
  - fp-cercador/backend/tests/conftest.py
  - fp-cercador/backend/.env.example
  - fp-cercador/backend/scrapers/html_scraper.py
  - fp-cercador/backend/scrapers/pipeline.py
  - fp-cercador/backend/scrapers/pdf_scraper.py
  - fp-cercador/backend/tests/test_pipeline.py
  - fp-cercador/backend/tests/test_pdf_scraper.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Fase 03: Informe de Revisió de Codi

**Revisat:** 2026-04-18
**Profunditat:** standard
**Fitxers revisats:** 8
**Estat:** issues_found

## Resum

S'han revisat els 8 fitxers de la Fase 03: el scraper HTML per als Grados D i E, el pipeline integrador de tots els grados, el pdf_scraper existent i tota la suite de tests. La implementació és sòlida en general —el patró fail-fast, l'escriptura atòmica i la gestió de famílies desconegudes estan ben coberts. S'han detectat 4 avisos (Warnings) i 3 observacions (Info), sense cap issue crític de seguretat ni de dades.

Els avisos principals afecten: (1) un `_write_atomic` que deixa un fitxer temporal orfè si `os.replace` falla; (2) el bloc `finally` del pipeline que no suprimeix `FileNotFoundError` al fer `os.unlink`; (3) duplicació de constants HEADERS sense mecanisme de sincronització garantit; i (4) un test del pipeline que importa el mòdul dins el bloc `with mock.patch` i podria no obtenir els mocks correctament si el mòdul ja estava importat.

---

## Warnings

### WR-01: `_write_atomic` deixa fitxer temporal orfè si `os.replace` falla

**Fitxer:** `fp-cercador/backend/scrapers/pipeline.py:96-103`

**Issue:** `_write_atomic` crea un fitxer temporal i crida `os.replace`. Si `os.replace` falla (ex. disc ple, sistema de fitxers de sola lectura), el fitxer temporal `tmp_path` queda al disc sense ser eliminat ni netejat. Contràriament al que diu el docstring, en aquest cas el fitxer original NO es queda intacte si `os.replace` falla a meitat de camí en alguns sistemes de fitxers, i el `.tmp.json` queda orfè en tots els casos de fallada de `replace`.

**Fix:**
```python
def _write_atomic(data: list, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', suffix='.json',
            dir=dir_path, delete=False
        ) as tmp:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp_path = tmp.name
        os.replace(tmp_path, output_path)
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

---

### WR-02: `os.unlink` al bloc `finally` pot generar `FileNotFoundError` no esperat

**Fitxer:** `fp-cercador/backend/scrapers/pipeline.py:151-154`

**Issue:** El bloc `finally` comprova `os.path.exists(pdf_path)` abans de cridar `os.unlink`, però hi ha una condició de carrera (race condition) entre `exists()` i `unlink()`: si el fitxer és eliminat entre les dues crides (poc probable però possible en entorns de CI/CD amb netejadors de temporals), s'eleva un `FileNotFoundError` que enmascara l'excepció original del pipeline. A més, si `_download_pdf` falla just després de crear el fitxer temporal però abans d'assignar a `pdf_path`, el `finally` no eliminaria res (però `pdf_path = None` ho cobreix correctament).

**Fix:** Substituir el patró `exists + unlink` per un `try/except FileNotFoundError` que és idiomàtic i sense race condition:
```python
finally:
    if pdf_path:
        try:
            os.unlink(pdf_path)
        except FileNotFoundError:
            pass  # Ja eliminat, no és un error
```

---

### WR-03: Constant `HEADERS` duplicada entre `html_scraper.py` i `pipeline.py` sense garantia de sincronització

**Fitxer:** `fp-cercador/backend/scrapers/html_scraper.py:46-56`

**Issue:** `html_scraper.py` duplica intencionadament el dict `HEADERS` de `pipeline.py` per evitar dependència circular (documentat al docstring). El problema és que si es canvia `User-Agent` o `Referer` a `pipeline.py`, és fàcil oblidar actualitzar `html_scraper.py`, i no hi ha cap test que verifiqui que els dos dicts siguin idèntics. El docstring avisa però no imposa.

**Fix:** Moure `HEADERS` a un mòdul comú `scrapers/constants.py` (o `scrapers/config.py`) que ambdós importin, eliminant la duplicació. Si es vol evitar el nou fitxer, afegir com a mínim un test que asseguri la igualtat:
```python
# test_constants.py o dins test_pipeline.py
def test_headers_consistency():
    from scrapers.html_scraper import HEADERS as HTML_HEADERS
    from scrapers.pipeline import HEADERS as PIPELINE_HEADERS
    assert HTML_HEADERS == PIPELINE_HEADERS, (
        "HEADERS desincronitzats entre html_scraper i pipeline — cal actualitzar els dos"
    )
```

---

### WR-04: Tests del pipeline importa el mòdul dins el bloc `with mock.patch` — els mocks podrien no aplicar-se si el mòdul ja estava importat

**Fitxer:** `fp-cercador/backend/tests/test_pipeline.py:78,146,159,195,215,315,359,425`

**Issue:** Tots els tests fan `import scrapers.pipeline as pipeline_mod` dins el bloc `with mock.patch(...)`. Python cacheja els mòduls a `sys.modules`, de manera que si el mòdul ja va ser importat per un test anterior, la importació no torna a executar el codi del mòdul i els atributs com `DATA_PATH` o `HEADERS` ja estan fixats. Quan es fa `mock.patch('scrapers.pipeline.DATA_PATH', ...)`, això sí funciona correctament (patcha l'atribut del mòdul ja importat). El problema real és que si algun test patcha `scrapers.pipeline.requests.get` però la funció `_download_pdf` ja tenia una referència a `requests.get` resolta en un import anterior fora del mock, el patch podria no ser efectiu.

En aquest cas concret, com que els patches apunten a `scrapers.pipeline.requests.get` (no a `requests.get` directament) i `pipeline.py` usa `requests.get` a través del mòdul (no una referència local), els mocks funcionen. No obstant, el patró `import` dins el `with` és innecessari i pot amagar bugs subtils en refactoritzacions futures.

**Fix:** Moure tots els imports a la part superior del fitxer de tests (fora de les funcions):
```python
# A l'inici de test_pipeline.py, fora de qualsevol funció
import scrapers.pipeline as pipeline_mod
```

---

## Info

### IN-01: `pdf_scraper.py` — el docstring indica 24 famílies però PREFIX_MAP en té 30

**Fitxer:** `fp-cercador/backend/scrapers/pdf_scraper.py:8`

**Issue:** La docstring del mòdul diu `PREFIX_MAP: dict[str, str]  -- 24 famílies professionals` però `PREFIX_MAP` conté 30 entrades (24 nou pla + 6 pla antic/LOGSE/HTML). El test `test_prefix_map_completeness` verifica correctament que n'hi ha 30, però el docstring és incorrecte i pot confondre.

**Fix:**
```python
PREFIX_MAP: dict[str, str]  -- 30 entrades (24 famílies nou pla + 6 pla antic/LOGSE/HTML-only)
```

---

### IN-02: `conftest.py` — fixtures `sample_table_*` per a pdf_scraper no s'utilitzen als tests

**Fitxer:** `fp-cercador/backend/tests/conftest.py:5-58`

**Issue:** Les fixtures `sample_table_grado_c`, `sample_table_grado_c_level2`, `sample_table_grado_c_level3`, `sample_table_grado_b_old`, `sample_table_grado_a_new`, `sample_table_grado_a_old` i `sample_table_unknown_prefix` estan definides al `conftest.py` però no s'utilitzen a `test_pdf_scraper.py` (que fa servir mocks inline de `MagicMock` directament). Són codi mort a efectes pràctics.

**Fix:** Verificar si eren destinades a tests futurs o a una versió anterior dels tests. Si no s'usaran, eliminar-les per reduir la superfície de manteniment del `conftest.py`.

---

### IN-03: `_nivel_grado_a` annotada com `-> None` però la signatura del tipus és enganyosa

**Fitxer:** `fp-cercador/backend/scrapers/pdf_scraper.py:65-67`

**Issue:** La funció `_nivel_grado_a` té com a type hint de retorn `-> None` però en realitat és cridada com a `nivel_fn(clean_code, is_old)` i el seu retorn s'assigna a `'nivel'` del registre. Funcionalment retorna `None` sempre (correcte), però el type hint `-> None` indica "aquesta funció no retorna res útil" quan en realitat el `None` és el valor de dades `nivel=None`. El tipus correcte seria `-> int | None` per ser consistent amb `_nivel_grado_b` i `_nivel_grado_c`.

**Fix:**
```python
def _nivel_grado_a(code: str, is_old_plan: bool) -> int | None:
    """Grado A no té distinció de nivel (nou pla ni pla antic)."""
    return None
```

---

_Revisat: 2026-04-18_
_Revisor: Claude (gsd-code-reviewer)_
_Profunditat: standard_
