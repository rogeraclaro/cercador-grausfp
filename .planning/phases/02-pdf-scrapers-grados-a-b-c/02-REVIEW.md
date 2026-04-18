---
phase: 02-pdf-scrapers-grados-a-b-c
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - fp-cercador/backend/scrapers/pdf_scraper.py
  - fp-cercador/backend/scrapers/pipeline.py
  - fp-cercador/backend/tests/__init__.py
  - fp-cercador/backend/tests/conftest.py
  - fp-cercador/backend/tests/test_pdf_scraper.py
  - fp-cercador/backend/tests/test_pipeline.py
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-04-17
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The scraper and pipeline code is well-structured with clear separation of concerns, good use of atomic writes, and solid fail-fast semantics. The test suite has broad coverage of the key behaviours (schema, deduplication, page-skip, fail-fast, atomic write, cleanup).

Four warnings were found: one logic bug in the `_extract_records` observation builder (off-by-one relative to denom position), one silent data loss risk when the download succeeds but the response body is not a valid PDF, one test reliability issue in `test_pipeline_fail_fast_on_download_error` that may pass vacuously, and one fragile header-assertion in the test suite that would silently miss positional header passing. Three info items note the missing `data/` directory guard, an unused conftest fixture set, and the bare `except Exception` scope.

---

## Critical Issues

None.

---

## Warnings

### WR-01: Off-by-one in observation builder — columns after denom are skipped if denom is not adjacent

**File:** `fp-cercador/backend/scrapers/pdf_scraper.py:115-119`

**Issue:** In `_parse_row`, the code cell is found at index `i`. The denominator is found at the first non-empty cell at index `j` (which may be `i+1`, `i+2`, etc. depending on empty cells). The observation columns are then collected starting from `i+2`, not from `j+1`. If the denom cell is at `i+3` (two empty cells between code and denom), columns `i+2` (an empty cell) would be included in obs, but more critically columns between `j` and `j+1` would be double-counted: the denom cell itself (`row[j]`) would be included again in the obs slice when `j >= i+2`.

```python
# Current — obs slice starts at i+2 unconditionally:
obs = [
    str(row[k]).strip()
    for k in range(i + 2, len(row))
    if row[k] and str(row[k]).strip()
]
```

The denom cell at index `j` will be re-included in `obs` whenever `j >= i + 2` (i.e. there is at least one empty column between the code cell and the denom cell).

**Fix:** Start the obs slice at `j + 1`, where `j` is the index at which denom was found. Requires tracking `j` across the two loops:

```python
denom = None
denom_idx = i + 1  # default: nothing found
for j in range(i + 1, len(row)):
    if row[j] and str(row[j]).strip():
        denom = str(row[j]).strip()
        denom_idx = j
        break
obs = [
    str(row[k]).strip()
    for k in range(denom_idx + 1, len(row))
    if row[k] and str(row[k]).strip()
]
return cell_str, denom, obs
```

---

### WR-02: No validation that the downloaded bytes are actually a PDF

**File:** `fp-cercador/backend/scrapers/pipeline.py:68-72`

**Issue:** `_download_pdf` writes `resp.content` directly to a `.pdf` temp file after checking only the HTTP status code. If `todofp.es` returns a 200 with an HTML error page (common on CDN misses or auth walls without proper 4xx codes), `pdfplumber.open()` will raise an opaque `pdfminer` exception that surfaces as an untyped `Exception` from the page-level try/except in `_extract_records`, silently skipping all pages and producing an empty record list. This means `ofertes.json` could be overwritten with zero records with no clear error.

**Fix:** Add a minimal magic-bytes check before writing:

```python
def _download_pdf(url: str, timeout: int = 120) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    if not resp.content.startswith(b'%PDF'):
        raise ValueError(
            f"Resposta de '{url}' no és un PDF vàlid "
            f"(primers bytes: {resp.content[:16]!r})"
        )
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(resp.content)
        return tmp.name
```

---

### WR-03: `test_pipeline_fail_fast_on_download_error` may pass vacuously — parse_grado_b not mocked

**File:** `fp-cercador/backend/tests/test_pipeline.py:149-181`

**Issue:** The test patches `PATCH_PARSE_A` but does NOT patch `PATCH_PARSE_B` or `PATCH_PARSE_C`. The pipeline never reaches `parse_grado_b` because the second `requests.get` call (for Grado B) raises `HTTPError` before the parser is called. This is correct for the intended scenario, but it means `parse_grado_b` and `parse_grado_c` are called against a real import, and if those imports fail for any environment reason the test would error rather than fail — masking the actual assertion. More importantly, `PATCH_PARSE_A` is mocked but then Grado A's parser runs against a non-PDF temp file (the mock `requests.get` for A returns `b'%PDF fake'`, which is valid enough for the magic-bytes check but pdfplumber would reject it). The test relies on the mock for `PATCH_PARSE_A` being applied, but `PATCH_PARSE_A` is not listed in the `with mock.patch(...)` block for this test — only `PATCH_PARSE_A` is patched but `PATCH_PARSE_B` and `PATCH_PARSE_C` are not, meaning if WR-02's fix is applied, the `ValueError` would fire before the parser anyway, but without it the pipeline calls the real `parse_grado_a` with a fake file.

**Fix:** Patch all three parsers explicitly in the fail-fast test for isolation, even if B and C are never reached:

```python
with mock.patch(PATCH_REQUESTS_GET, mock_get), \
     mock.patch(PATCH_PARSE_A, return_value=[_make_record()]), \
     mock.patch(PATCH_PARSE_B, return_value=[]), \
     mock.patch(PATCH_PARSE_C, return_value=[]), \
     mock.patch(PATCH_OS_UNLINK), \
     ...
```

---

### WR-04: Header assertion in `test_pipeline_headers_used` silently passes if headers are passed positionally

**File:** `fp-cercador/backend/tests/test_pipeline.py:329-335`

**Issue:** The assertion attempts to retrieve headers from either `call[1].get('headers')` (keyword arg) or `call[0][1]` (second positional arg). In `_download_pdf`, `requests.get` is called as `requests.get(url, headers=HEADERS, timeout=timeout)` — headers are always a keyword arg, so the positional fallback `call[0][1]` would be `None` if `headers` were accidentally dropped from the call signature. The guard `or (call[0][1] if len(call[0]) > 1 else None)` is dead code in practice but creates a false sense of completeness. If the production code changed to `requests.get(url, HEADERS, timeout=timeout)` (positional), the assertion `call[1].get('headers')` would return `None`, the fallback `call[0][1]` would return the headers dict, and the test would still pass — but the `timeout` kwarg check is absent entirely.

**Fix:** Assert on the precise call signature expected, and add a timeout assertion:

```python
for call in mock_get.call_args_list:
    args, kwargs = call
    assert 'headers' in kwargs, "headers ha de ser passat com a kwarg"
    assert 'User-Agent' in kwargs['headers']
    assert 'Mozilla/5.0' in kwargs['headers']['User-Agent']
    assert 'Referer' in kwargs['headers']
    assert 'todofp.es' in kwargs['headers']['Referer']
    assert 'timeout' in kwargs, "timeout ha de ser passat"
```

---

## Info

### IN-01: `data/` directory is not guaranteed to exist before `_write_atomic` runs

**File:** `fp-cercador/backend/scrapers/pipeline.py:83-90`

**Issue:** `_write_atomic` creates a `NamedTemporaryFile` in `dir=dir_path` (the `data/` directory). If that directory does not exist at first run, `NamedTemporaryFile` raises `FileNotFoundError`. There is no `os.makedirs` guard. This is a first-run operational issue, not a crash at import time, so it surfaces only when the pipeline actually executes.

**Fix:** Add a `makedirs` call before the `NamedTemporaryFile`:

```python
def _write_atomic(data: list, output_path: str) -> None:
    dir_path = os.path.dirname(output_path)
    os.makedirs(dir_path, exist_ok=True)  # first-run safety
    with tempfile.NamedTemporaryFile(...) as tmp:
        ...
```

---

### IN-02: `conftest.py` fixtures are defined but never used by any test

**File:** `fp-cercador/backend/tests/conftest.py:6-57`

**Issue:** All six fixtures (`sample_table_grado_c`, `sample_table_grado_c_level2`, `sample_table_grado_c_level3`, `sample_table_grado_b_old`, `sample_table_grado_a_new`, `sample_table_grado_a_old`, `sample_table_unknown_prefix`) are defined in conftest but none are referenced by any test function parameter. The tests inline their own table data or use local `MagicMock` setups. The conftest fixtures are dead code.

**Fix:** Either wire the fixtures into the corresponding tests to reduce duplication, or delete them if they are scaffolding that will not be used.

---

### IN-03: Bare `except Exception` in `_extract_records` swallows non-PDF-related errors

**File:** `fp-cercador/backend/scrapers/pdf_scraper.py:148-152`

**Issue:** The page-level `except Exception` is intentionally broad (T-02-01). This is acceptable for malformed pages, but it means programming errors in `_parse_row` or `nivel_fn` (e.g. an `AttributeError` from a future refactor) would be silently downgraded to a warning and the page skipped, making bugs hard to diagnose. The intent (tolerate malformed PDF pages) could be achieved more narrowly.

**Fix:** Consider catching `pdfplumber`-specific and `PDFSyntaxError`-type exceptions only, and re-raising unexpected ones:

```python
import pdfminer.pdfparser  # already a transitive dep via pdfplumber

try:
    table = page.extract_table()
except (pdfminer.pdfparser.PDFSyntaxError, Exception) as exc:
    # Keep broad for now but log the type for easier diagnosis
    logger.warning(
        f"[{type(exc).__name__}] Error extraient taula d'una pàgina del PDF '{pdf_path}': {exc}"
    )
    continue
```

At minimum, include the exception type in the warning message (the current log lacks it).

---

_Reviewed: 2026-04-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
