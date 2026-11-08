---
phase: 261108-say-pla-081-scraper-cat-leg-sepe-enriquiment
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - fp-cercador/backend/scrapers/sepe_scraper.py
  - fp-cercador/backend/tests/test_sepe_scraper.py
  - fp-cercador/backend/tests/fixtures/sepe_paginacion_3.latin1.json
  - fp-cercador/backend/scrapers/pipeline.py
  - fp-cercador/backend/tests/test_sepe_refresh.py
  - fp-cercador/backend/app.py
  - fp-cercador/backend/tests/test_fpo_api.py
  - fp-cercador/frontend/index.html
  - fp-cercador/frontend/i18n.js
  - fp-cercador/frontend/*.html (i18n.js?v= cache-bust only, the other 14 pages)
  - fp-cercador/backend/grau_page.py
  - fp-cercador/backend/tests/test_grau_page.py
autonomous: true
requirements: [PLA-081]

estimate:
  tokens: 120000
  raw_tokens: 120000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A local run of build_sepe_data() + write_sepe_data() produces fp-cercador/backend/data/sepe_especs.json with >= 7000 rows and unique codi values"
    - "A SEPE result with fewer than 5000 rows or a duplicated codi raises SepeDataError and leaves the previous sepe_especs.json byte-identical"
    - "The pipeline refreshes sepe_especs.json only when it is missing or older than 7 days; a SEPE failure never aborts the pipeline and alerts the admin with source='SEPE' and stamp_name='last_sepe_alert.json'"
    - "Every SOC entry of /api/fpo/especialitats carries vinculacio (grauC | sepe | propiaSoc), vigenciaFi, competenciaTransversal and modalitatOficial; when sepe_especs.json is missing, non-CP entries have vinculacio null and the SEPE fields null, and every existing FPO test still passes"
    - "/api/fpo/especialitat/<codi> returns sepe {idSepe, vigenciaInici, vigenciaFi, versio} or null, and never a programaSepeUrl key"
    - "In FPO mode, a SEPE-linked specialty shows the 'Formació en el treball' badge with its explanatory text, a CTR* specialty shows 'Pròpia del SOC', CP specialties keep 'Cert. prof.', and the new 'Tipus de formació' filter narrows the list together with the certprof toggle, in CA and ES"
  artifacts:
    - path: fp-cercador/backend/scrapers/sepe_scraper.py
      provides: "SEPE catalogue scraper: build_sepe_data(), write_sepe_data(), parse_row(), SepeDataError"
      contains: "def build_sepe_data"
    - path: fp-cercador/backend/tests/test_sepe_scraper.py
      provides: "Offline scraper tests (Latin-1 fixture, pagination, validation)"
      contains: "latin"
    - path: fp-cercador/backend/tests/fixtures/sepe_paginacion_3.latin1.json
      provides: "Real 3-row paginacionEspecialidades response, Latin-1 encoded"
    - path: fp-cercador/backend/scrapers/pipeline.py
      provides: "refresh_sepe_especs(data_dir, max_age_days=7), called from run() after the SOC step"
      contains: "def refresh_sepe_especs"
    - path: fp-cercador/backend/tests/test_sepe_refresh.py
      provides: "Offline tests for the 7-day refresh gate and non-fatal failure"
      contains: "last_sepe_alert.json"
    - path: fp-cercador/backend/app.py
      provides: "SEPE_ESPECS_PATH, _get_sepe_especs(), _sepe_index(), vinculacio enrichment, sepe block in detail"
      contains: "SEPE_ESPECS_PATH"
    - path: fp-cercador/frontend/index.html
      provides: "vinculacio badges, explanatory text, competencia transversal chip, vigencia notice, Tipus de formacio filter"
      contains: "fpoFilters.vinculacio"
    - path: fp-cercador/frontend/i18n.js
      provides: "9 new fpo.* keys in CA and ES"
      contains: "fpo.badge.formacioTreball"
  key_links:
    - from: fp-cercador/backend/scrapers/pipeline.py
      to: fp-cercador/backend/scrapers/sepe_scraper.py
      via: "refresh_sepe_especs() calls sepe_scraper.build_sepe_data / write_sepe_data through module attributes"
      pattern: "sepe_scraper\\.build_sepe_data"
    - from: fp-cercador/backend/app.py
      to: fp-cercador/backend/data/sepe_especs.json
      via: "_soc_espec_index cache key includes the SEPE_ESPECS_PATH mtime"
      pattern: "_mt\\(SEPE_ESPECS_PATH\\)"
    - from: fp-cercador/frontend/index.html
      to: /api/fpo/especialitats
      via: "filteredFpoEspecs and the row badges read esp.vinculacio"
      pattern: "esp\\.vinculacio"
    - from: fp-cercador/frontend/*.html
      to: fp-cercador/frontend/i18n.js
      via: "i18n.js?v=20261108a cache-bust so the new keys reach browsers"
      pattern: "i18n\\.js\\?v=20261108a"
---

<objective>
Execute phases 1–4 of the source plan fp-cercador/plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md
(the authoritative spec): a network-free-tested scraper of the SEPE Catálogo de Especialidades Formativas,
a 7-day-gated non-fatal pipeline step, enrichment of the SOC FPO specialties with their link to the SEPE
catalogue (vinculacio grauC / sepe / propiaSoc, vigència, competència transversal), and the UI for it
(badges, explanatory text, "Tipus de formació" filter, CA/ES copy).

Purpose: users of the FPO mode can tell whether a SOC specialty leads to a Grado C certificate, is
"formació en el treball" from the state catalogue (no official FP certificate), or is a SOC-only course.

Output: sepe_scraper.py + offline tests + Latin-1 fixture; refresh_sepe_especs() in the pipeline + tests;
enriched /api/fpo/* + tests; index.html + i18n.js changes with i18n.js cache-bust.

Binding scope limits (source plan "Fora d'abast"): no /api/sepe/programa endpoint and no programaSepeUrl field
(that is plan 082); no specialties without a Catalan course inside FPO mode; no training entities; no Catalan
translation of SEPE titles; do not show the meaning of code suffixes (PO/EXP/DCP/CCC) anywhere.
The SEPE endpoint diagnosis in the source plan is verified: do not re-investigate it, implement it.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@fp-cercador/plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md
@.planning/STATE.md
@CLAUDE.md
@fp-cercador/backend/scrapers/soc_scraper.py
@fp-cercador/backend/tests/test_ext_refresh.py

Facts verified while planning (2026-11-08), use them instead of re-reading:
- soc_scraper.py: module-level `_UA` browser string, `_new_session()`, `write_soc_data()` writes each file with
  `tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json', dir=data_dir, delete=False)` then
  `os.replace`, `json.dump(..., ensure_ascii=False, indent=1)`.
- pipeline.py: `_notify_admin_soc_failure(data_dir, exc, *, source='SOC', stamp_name='last_soc_alert.json')`
  (line ~155, throttled to 1 mail/day per stamp file); `_report(...)` progress callback inside `run()`;
  SOC step at lines ~437–452; PIMEC/Foment step (`refresh_ext_cursos`) right after it at ~454.
- app.py: `SOC_*_PATH` constants at lines ~101–104 (`_DATA_DIR`); caches `_soc_*_cache = {"mtime": None, "index": None}`
  and `_soc_espec_index_cache = {"key": None, "data": None}` at ~1526–1531; `_read_soc_list(path, cache)` at ~1537
  (returns [] when missing/corrupt); `_soc_espec_index()` at ~1628 builds one dict per SOC specialty with ≥1 course
  (key = `(_mt(SOC_CURSOS_PATH), _mt(SOC_ESPECS_PATH))`); `_fpo_llista()` spreads those dicts into
  /api/fpo/especialitats; `api_fpo_especialitat` at ~1697 (ext branch first, then SOC branch).
- External FPO entries (PIMEC/Foment/Cecot/CCOO, from backend/fpo_ext.py) have `font != 'soc'`, `esCertProf`
  from certCodi, and no vinculacio. Do not classify them.
- tests/test_fpo_api.py: fixture `fpo_data` writes soc_*.json to tmp_path and monkeypatches the paths and caches;
  module-level ESPECS (IFCD0112, XXXX0000 without courses, ADGG0408 cert) and CURSOS; one test asserts the list
  is exactly {'IFCD0112', 'ADGG0408'}, so do not add entries to the module-level lists.
- index.html: `fpoFilters` initial object at ~2253 and again in `fpoResetFilters()` at ~3253 (both contain
  `tipus: ''` for an unrelated existing "Tipus" filter — Subvencionat/Bonificable); `filteredFpoEspecs` at ~3230
  (certprof line ~3245); filter controls at ~3597–3691 (certprof checkbox ~3682, clear button `x-show` ~3688);
  row badges at ~4397 (`esp.esCertProf` → `.badge-old` with `t('fpo.badge.certprof')`), followed by `.fpo-badge`
  spans; expanded detail `.detall-inner` starts right after (~4405). FPO styles (`.fpo-badge` ~486) are inline in
  index.html; site.css is not involved, so no site.css `?v=` bump.
- i18n.js: CA block starts line 3 (fpo.* keys ~334–375), ES block line 724 (fpo.* ~1055–1100); `t(key, vars)`
  interpolates `{name}` placeholders.
- i18n.js cache-bust literal is `20261105a` today in 15 frontend/*.html, `I18N_VERSION` in backend/grau_page.py
  (line 21) and one assertion in backend/tests/test_grau_page.py (~line 316).
- Real data (2026-11-08) of SOC specialties with ≥1 course: grauC 132 (e.g. ADGD0108), sepe 82 (e.g. ADGD0073),
  propiaSoc 6 (e.g. CTRD0012). ADGD0001 currently has no course, so it is not in the FPO list.
- Raw SEPE rows (2026-11-08 capture): all 7.544 rows have 11 cells; cell 3 (versio) is int; cells 7 and 9 are
  strings (hores e.g. "410"); every cell 0 has both FECHA INICIO/FIN VIGENCIA; cell 4 (familia) can be "-"
  (e.g. FCOE001PO); no duplicated codes.
- Spike capture (outside the repo, may have been cleaned):
  /private/tmp/claude-501/-Users-rogermasellas-AI-Cercador-Graus/5bb26f69-68f1-4668-8a96-4acb75252de2/scratchpad/sepe/especialidades_raw.json
  (JSON list of raw 11-cell rows) and fetch.py next to it (reference request body).

Test commands (cwd = checkout root; tests matching `*scraper*` and test_pipeline.py are excluded from the
routine run because the old ones hit the network, so run the new scraper test file explicitly):
- routine offline suite: `cd fp-cercador/backend && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
- never chain `git stash` / `git stash pop` (an old unrelated stash exists).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: SEPE catalogue scraper with offline tests and a real local snapshot</name>
  <files>fp-cercador/backend/scrapers/sepe_scraper.py, fp-cercador/backend/tests/test_sepe_scraper.py, fp-cercador/backend/tests/fixtures/sepe_paginacion_3.latin1.json</files>
  <read_first>
    - fp-cercador/plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md (sections "Diagnosi tècnica de la font" and "Fase 1")
    - fp-cercador/backend/scrapers/soc_scraper.py (lines 1–60 and 248–266: session + atomic write pattern)
    - fp-cercador/backend/tests/test_soc_scraper.py (lines 1–15 and the monkeypatch style around line 108)
  </read_first>
  <behavior>
    - parse_row on the real ADGA12DCP row returns codi 'ADGA12DCP', idSepe 107, titol_es 'AUXILIAR DE EMPLEADO DE OFICINA', versio 1, familia_es 'ADMINISTRACIÓN Y GESTIÓN', area_es 'ADMINISTRACIÓN / GESTIÓN', familia_codi 'ADG', area_codi 'ADGA', competenciaTransversal None, nivell 1, modalitat 'Presencial', hores 410.0, vigenciaInici '2004-05-24', vigenciaFi '2029-12-31'
    - parse_row on FCOE001PO returns competenciaTransversal 'Idiomas / Lingüísticas', nivell None ('Sin especificar'), familia_es None (cell is '-'), modalitat 'Presencial y teleformación', titol_es 'ALEMÁN A1 (MARCO COMÚN EUROPEO)'
    - parse_row on ADGD0073 returns nivell 2, vigenciaInici '2024-02-26', vigenciaFi '2031-12-31'
    - The fixture file bytes are not valid UTF-8 (decoding them as UTF-8 raises UnicodeDecodeError) and the fetch layer decodes them as Latin-1 into correct accented text
    - With PAGE_LENGTH patched to 2 and a fake session serving the 3 fixture rows, the fetch makes one bootstrap GET to /flows/main first, then exactly 2 POSTs with start 0 and 2, and stops because the second page has fewer rows than length
    - A non-JSON POST response (HTML error page) raises SepeDataError
    - build_sepe_data with the 3-row fake session and the default MIN_ROWS raises SepeDataError; with MIN_ROWS patched to 2 it returns 3 parsed dicts
    - write_sepe_data with fewer than MIN_ROWS rows, or with a duplicated codi, raises SepeDataError and a pre-existing sepe_especs.json stays byte-identical
    - write_sepe_data with MIN_ROWS patched to 2 writes valid JSON (ensure_ascii=False) and leaves no temp files in the directory
  </behavior>
  <action>
    Fixture first (RED). Create fp-cercador/backend/tests/fixtures/sepe_paginacion_3.latin1.json: a paginacionEspecialidades response object with keys draw (1), recordsTotal (3), recordsFiltered (3) and data holding the 3 real raw rows ADGA12DCP, ADGD0073 and FCOE001PO in that order (11 cells each, copied verbatim, HTML included). Source the rows from the spike capture path listed in the context if it still exists; otherwise make three live POSTs with the code filter field formulario:codigoWrapper:codigoEsp (one per code) using the request body described below, once, without committing any helper script. Serialize with ensure_ascii=False and write the bytes encoded as latin-1 so the file really is Latin-1. Write tests/test_sepe_scraper.py covering every bullet of the behavior block using a small fake session class (get/post methods returning objects with status_code, content bytes and raise_for_status) built from the fixture; no real network anywhere. Run it and confirm it fails because the module does not exist.

    Then implement fp-cercador/backend/scrapers/sepe_scraper.py following the soc_scraper.py layout (module docstring in Catalan explaining source and outputs, requests only, stdlib re/html/json/os/tempfile/logging):
    - Constants: BASE = 'https://sede.sepe.gob.es/FOET_CATALOGO_EEFF_SEDE', SEPE_FILE = 'sepe_especs.json', PAGE_LENGTH = 2000, MIN_ROWS = 5000, MAX_PAGES = 20 (loop guard), TIMEOUT = 30, and an own `_UA` browser string identical to soc_scraper's (duplicated on purpose, same precedent as html_scraper HEADERS).
    - `class SepeDataError(Exception)`.
    - `_new_session()` → requests.Session with User-Agent `_UA`.
    - `_request_body(start, length)` → dict exactly as in the source plan: dtInfo with draw 1, columns for data 0..10 (name '', searchable true, orderable true except columns 0 and 10, search value '' regex false), order column 1 asc, start, length, empty search; filtro with formulario:ultimaVersionCuadrado 'true', formulario_SUBMIT '1', javax.faces.ViewState 'e1s1', and value '000' for each of tutoriaPresencial, aulaVirtualSeleccionada, vinculacion, centroMovil, otrosRequisitos under the name pattern formulario:acordeonPrincipal:tabOpcionesAvanzadas:{name}Wrapper:{name}; enAltaIF false, enSEDE true, tipoBuscador 'buscadorEspecialidades'.
    - `_fetch_raw_rows(session)` → list of raw rows: GET BASE + '/flows/main' first (cookies; raise_for_status), then loop POST BASE + '/rest/paginacionEspecialidades' with json=body and timeout; raise_for_status; decode resp.content as latin-1 then json.loads; any decode/parse failure or missing data list → SepeDataError (a missing session redirects to /flows/error, which yields HTML); stop when the page has fewer rows than the length used; read PAGE_LENGTH at call time (module attribute, so tests can patch it); exceeding MAX_PAGES → SepeDataError.
    - `parse_row(cells)` → dict with keys codi, idSepe, titol_es, versio, familia_es, area_es, familia_codi, area_codi, competenciaTransversal, nivell, modalitat, hores, vigenciaInici, vigenciaFi. Rows whose length is not 11 → SepeDataError (layout change). Vigència: regexes INICIO VIGENCIA:\s*(\d{2})/(\d{2})/(\d{4}) and FIN VIGENCIA:\s*(\d{2})/(\d{2})/(\d{4}) on cell 0 → 'AAAA-MM-DD' or None. idSepe: regex getProgramaFormativoEspecialidad\((\d+)\) on cell 2 → int, None if absent. titol_es: cell 2 with tags replaced by a space, html.unescape, whitespace collapsed, stripped. versio int(cell 3). familia_es / area_es / competenciaTransversal: stripped text, None when empty or '-' (cell 4 can be '-'; this '-'-to-None normalization for familia/area is a planner decision consistent with the source plan's rule for competència transversal). nivell: int when the stripped cell is digits, else None. modalitat stripped cell 8. hores float of cell 9 (accept a comma decimal). familia_codi = codi[:3], area_codi = codi[:4]. Do not interpret code suffixes.
    - `validate_rows(rows)`: fewer than the module-level MIN_ROWS (read at call time) → SepeDataError; any duplicated codi → SepeDataError naming one example.
    - `build_sepe_data(session=None)` → parsed rows of all pages, validated; logs count at info.
    - `write_sepe_data(rows, data_dir)`: validate_rows again (guard, so a bad list never overwrites the previous snapshot), os.makedirs, atomic write to data_dir/SEPE_FILE with the same tempfile + os.replace pattern as write_soc_data (ensure_ascii=False, indent=1); remove the temp file if dumping fails.
    Make the tests pass (GREEN).

    Then produce the real local snapshot once (network, 4 requests, ~4 s): from fp-cercador/backend run build_sepe_data() and write_sepe_data(rows, 'data'), printing the count. Expect ≥ 7000 rows (7.544 on 2026-11-08) with unique codes. backend/data/ is gitignored: the JSON is not committed, but it is needed locally for Tasks 2 and 3. If the live call fails, report the exact error in the summary and continue: the offline tests are the gate, the live run is the sanity check.

    Commit only this task's files (stage explicit paths; the tree has unrelated changes such as .DS_Store, fp-cercador/plans/ESTAT.md and untracked plan files that must stay untouched): `feat(sepe): scrape the SEPE training specialties catalogue`. Conventional commit, English, no AI attribution trailer (owner rule).
  </action>
  <verify>
    <automated>cd fp-cercador/backend && python3 -m pytest -q tests/test_sepe_scraper.py && python3 -c "import json; r=json.load(open('data/sepe_especs.json', encoding='utf-8')); c=[x['codi'] for x in r]; assert len(r) >= 7000 and len(c) == len(set(c)), len(r); print(len(r), 'ok')"</automated>
  </verify>
  <done>tests/test_sepe_scraper.py passes offline (every behavior bullet has a test); fp-cercador/backend/data/sepe_especs.json exists locally with ≥ 7000 rows and unique codi (or the live failure is reported verbatim); one commit with only the three task files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: 7-day pipeline step and FPO backend enrichment (vinculacio, vigència, competència transversal)</name>
  <files>fp-cercador/backend/scrapers/pipeline.py, fp-cercador/backend/tests/test_sepe_refresh.py, fp-cercador/backend/app.py, fp-cercador/backend/tests/test_fpo_api.py</files>
  <read_first>
    - fp-cercador/plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md (sections "Fase 2" and "Fase 3")
    - fp-cercador/backend/scrapers/pipeline.py lines 113–215 (history + _notify_admin_soc_failure + refresh_ext_cursos) and 430–460 (SOC step in run())
    - fp-cercador/backend/app.py lines 95–110 and 1520–1735
    - fp-cercador/backend/tests/test_fpo_api.py (whole file, 142 lines)
    - fp-cercador/backend/tests/test_ext_refresh.py lines 1–50 (patch style for pipeline tests)
  </read_first>
  <behavior>
    - refresh_sepe_especs with a sepe_especs.json modified now → build_sepe_data is not called, returns None
    - refresh_sepe_especs with the file missing, or with mtime set 8 days in the past → build_sepe_data and write_sepe_data are called once (write with the built rows and data_dir) and the function returns the row count
    - build_sepe_data raising SepeDataError → write_sepe_data not called, the existing file is untouched, _notify_admin_soc_failure called once with source='SEPE' and stamp_name='last_sepe_alert.json', the function returns None and does not raise
    - With a SEPE fixture listing IFCD0112 and ADGG0408, and SOC data extended (inside the test only) with a CTRA0001 specialty that has one course: /api/fpo/especialitats gives ADGG0408 vinculacio 'grauC' (cert wins even if listed in SEPE), IFCD0112 'sepe' with vigenciaFi, competenciaTransversal and modalitatOficial taken from the fixture, CTRA0001 'propiaSoc' with those three fields None
    - Without sepe_especs.json: endpoints return exactly what they returned before plus the new keys; IFCD0112 has vinculacio None (not 'propiaSoc'), ADGG0408 'grauC', all SEPE fields None
    - Cache invalidation: first request without the SEPE file (IFCD0112 vinculacio None), then the SEPE file is written → the next request shows 'sepe'
    - /api/fpo/especialitat/IFCD0112 with the SEPE fixture returns sepe {idSepe, vigenciaInici, vigenciaFi, versio}; CTRA0001 returns sepe None; neither response contains a programaSepeUrl key
  </behavior>
  <action>
    Tests first (RED): create fp-cercador/backend/tests/test_sepe_refresh.py for the three pipeline bullets (tmp_path data dir; patch scrapers.sepe_scraper.build_sepe_data, scrapers.sepe_scraper.write_sepe_data and scrapers.pipeline._notify_admin_soc_failure with unittest.mock.patch, as test_ext_refresh.py does; set old mtimes with os.utime). This file name does not match the `*scraper*` ignore glob, so it runs in the routine suite. In tests/test_fpo_api.py: extend the existing fpo_data fixture so it also monkeypatches app_module.SEPE_ESPECS_PATH to tmp_path / 'sepe_especs.json' (not written by default) and resets the new SEPE caches; add a minimal SEPE fixture list (dicts in the Task 1 output shape) and the API bullets as new tests. Keep the module-level ESPECS/CURSOS unchanged; tests needing CTRA0001 rewrite soc_especs.json/soc_cursos.json in tmp_path with ESPECS + one extra specialty and CURSOS + one extra course (helpers _espec/_curs already exist). Confirm they fail.

    Pipeline (source plan Fase 2): add `refresh_sepe_especs(data_dir, *, max_age_days=7) -> int | None` to fp-cercador/backend/scrapers/pipeline.py, next to refresh_ext_cursos. It returns None without any network call when data_dir/sepe_especs.json exists and is younger than max_age_days; otherwise it imports the module (`from scrapers import sepe_scraper`) and calls sepe_scraper.build_sepe_data() then sepe_scraper.write_sepe_data(rows, data_dir) through module attributes (so tests can patch them), logs the count at info, and returns len(rows). Every exception is caught: logger.warning("pipeline: refresc del catàleg SEPE ha fallat (no fatal): %s", exc) plus _notify_admin_soc_failure(data_dir, exc, source='SEPE', stamp_name='last_sepe_alert.json'), return None; the previous JSON stays because write_sepe_data validates before replacing. In run(), right after the SOC step's except block and before the PIMEC/Foment step, add `_report("Catàleg d'especialitats (SEPE)")` and call refresh_sepe_especs(os.path.dirname(DATA_PATH)). Do not append to soc_refresh_history.json (that history tracks course diffs). No admin endpoint or scheduler change.

    Backend (source plan Fase 3) in fp-cercador/backend/app.py:
    - After SOC_CENTRES_PATH: `SEPE_ESPECS_PATH = os.path.join(_DATA_DIR, "sepe_especs.json")` with a `# Pla 081: catàleg d'especialitats del SEPE` comment.
    - Next to the SOC caches: `_sepe_especs_cache: dict = {"mtime": None, "index": None}` and `_sepe_index_cache: dict = {"key": None, "data": None}`.
    - `_get_sepe_especs()` → _read_soc_list(SEPE_ESPECS_PATH, _sepe_especs_cache). `_sepe_index()` → {codi: row} for rows with a codi, cached in _sepe_index_cache keyed by the SEPE file mtime (None when missing → {}).
    - In _soc_espec_index(): add `_mt(SEPE_ESPECS_PATH)` to the cache key tuple; fetch sepe_idx = _sepe_index() once; for each list entry add vinculacio = 'grauC' if esCertProf, else 'sepe' if the codi is in sepe_idx, else 'propiaSoc' if sepe_idx is non-empty, else None; plus vigenciaFi, competenciaTransversal and modalitatOficial (= the SEPE row's modalitat) from the SEPE row, None when absent. The None-when-no-SEPE-data rule is a planner decision implementing the source plan's "sense sepe_especs.json, tot continua igual (camps a None)": without it, a missing file would mislabel all ~80 SEPE-linked specialties as 'propiaSoc' on the VPS before its first refresh.
    - In api_fpo_especialitat (SOC branch only; leave the ext branch untouched): add 'sepe': {'idSepe', 'vigenciaInici', 'vigenciaFi', 'versio'} from the SEPE row, or None. Do not add programaSepeUrl (plan 082 is not done).
    - _run_fpo_refresh needs no change: the index cache key now includes the SEPE mtime.
    Make the tests pass (GREEN).

    Then run the routine offline suite. Other FPO test fixtures (test_fpo_ext_api.py, test_fpo_favorites_api.py, test_admin_fpo.py) do not patch SEPE_ESPECS_PATH and will now read the real local sepe_especs.json from Task 1; only new keys are added, so they should pass. If one fails because of the real file, patch SEPE_ESPECS_PATH to a tmp path in that fixture only.

    Commit only this task's files: `feat(fpo): classify SOC specialties against the SEPE catalogue`. No AI attribution trailer.
  </action>
  <verify>
    <automated>cd fp-cercador/backend && python3 -m pytest -q tests/test_sepe_refresh.py tests/test_fpo_api.py tests/test_sepe_scraper.py && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py && ADMIN_TOKEN=dev-check python3 -c "import app; from collections import Counter; L=app.app.test_client().get('/api/fpo/especialitats').get_json()['especialitats']; print(Counter(e.get('vinculacio') for e in L if e.get('font')=='soc'))"</automated>
  </verify>
  <done>New and existing tests pass offline; the routine suite is green; against the real local data the SOC entries split into grauC / sepe / propiaSoc with no None (≈132 / 82 / 6 on 2026-11-08); no programaSepeUrl anywhere; one commit with only the four task files.</done>
</task>

<task type="auto">
  <name>Task 3: FPO UI — vinculacio badges, explanatory text, vigència notice and "Tipus de formació" filter (CA/ES)</name>
  <files>fp-cercador/frontend/index.html, fp-cercador/frontend/i18n.js, fp-cercador/frontend/*.html (cache-bust only), fp-cercador/backend/grau_page.py, fp-cercador/backend/tests/test_grau_page.py</files>
  <read_first>
    - fp-cercador/plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md (section "Fase 4")
    - fp-cercador/frontend/index.html lines 480–500 (.fpo-badge), 2250–2258, 3080–3092 (fpoLang, fpoTipusKey), 3228–3258, 3664–3692, 4385–4415
    - fp-cercador/frontend/i18n.js lines 330–375 (CA fpo.*) and 1050–1100 (ES fpo.*)
  </read_first>
  <action>
    State and filtering in fp-cercador/frontend/index.html: add `vinculacio: ''` to fpoFilters in both the initial object and fpoResetFilters(). The existing `tipus` filter (Subvencionat/Bonificable) is unrelated: keep it and name the new one vinculacio everywhere. In filteredFpoEspecs add: when f.vinculacio is 'grauC' keep only e.esCertProf (so external CP courses match too, consistent with the certprof toggle); when it is 'sepe' or 'propiaSoc' keep only entries whose e.vinculacio equals it. The certprof toggle stays as is and both filters combine with AND (source plan: the toggle remains, the new filter extends it).

    Filter control: after the fpo-tipus select and before the certprof checkbox, add an sr-only label for id fpo-vinculacio with x-text t('fpo.filter.vinculacio') and a select x-model="fpoFilters.vinculacio" whose first option is t('fpo.filter.vinculacio') + ' — ' + t('fpo.filter.all') (same pattern as the neighbouring selects) followed by options grauC, sepe, propiaSoc with x-text t('fpo.vinculacio.' + value). Add `|| fpoFilters.vinculacio` to the clear button's x-show.

    Row badges (~4397): keep the existing esp.esCertProf badge unchanged; it is the Grado C badge (source plan: reuse the current badge, so no fpo.badge.grauC key). Right after it add a span x-show="esp.vinculacio === 'sepe'" class fpo-badge with x-text t('fpo.badge.formacioTreball') and :title t('fpo.tooltip.formacioTreball'), and a span x-show="esp.vinculacio === 'propiaSoc'" class fpo-badge with x-text t('fpo.badge.propiaSoc').

    Expanded detail: at the top of .detall-inner add a small block using x-show only (no x-template x-if, to avoid the single-root pitfall), reading from esp, which is in scope: (a) when esp.vinculacio === 'sepe', a short paragraph with t('fpo.tooltip.formacioTreball'), so the explanation is also reachable on touch and keyboard, where title tooltips are not; (b) when esp.competenciaTransversal, a chip with t('fpo.chip.competenciaTransversal', {nom: esp.competenciaTransversal}) (the value stays in Spanish as SEPE publishes it; translating SEPE text is out of scope); (c) when fpoVigenciaAviat(esp), a small notice with t('fpo.avis.vigencia', {data: fpoDataCurta(esp.vigenciaFi)}). Add two methods next to fpoTipusKey: fpoVigenciaAviat(esp) returns true when esp.vigenciaFi is set and its date (parsed as local midnight) is less than 183 days from now, including already expired dates; fpoDataCurta(iso) turns 'AAAA-MM-DD' into 'DD/MM/AAAA'. Render every SEPE-derived value with x-text, never x-html. All visible text goes through t(): no literal strings inside x-text. Styles: reuse .fpo-badge; if the notice needs styling, add one small .fpo-avis rule next to .fpo-badge in index.html's own style block using existing tokens (var(--fs-label), var(--warm)); do not touch site.css.

    i18n in fp-cercador/frontend/i18n.js, add each key to the CA block (near the other fpo.filter / fpo.badge keys) and the ES block:
    fpo.filter.vinculacio: 'Tipus de formació' / 'Tipo de formación';
    fpo.vinculacio.grauC: 'Grau C (certificat de professionalitat)' / 'Grado C (certificado de profesionalidad)';
    fpo.vinculacio.sepe: 'Formació en el treball' / 'Formación en el trabajo';
    fpo.vinculacio.propiaSoc: 'Pròpia del SOC' / 'Propia del SOC';
    fpo.badge.formacioTreball: 'Formació en el treball' / 'Formación en el trabajo';
    fpo.badge.propiaSoc: 'Pròpia del SOC' / 'Propia del SOC';
    fpo.tooltip.formacioTreball: 'Formació en el treball (catàleg estatal del SEPE). No condueix a cap certificat oficial del sistema de FP.' / 'Formación en el trabajo (catálogo estatal del SEPE). No conduce a ningún certificado oficial del sistema de FP.';
    fpo.chip.competenciaTransversal: 'Competència transversal: {nom}' / 'Competencia transversal: {nom}';
    fpo.avis.vigencia: 'Especialitat vigent fins al {data}' / 'Especialidad vigente hasta el {data}'.
    Escape apostrophes the way the file already does.

    Cache-bust i18n.js so browsers load the new keys (otherwise t() shows raw keys): change the version literal to 20261108a in every frontend/*.html `i18n.js?v=` reference (15 pages), in I18N_VERSION in fp-cercador/backend/grau_page.py and in the matching assertion in fp-cercador/backend/tests/test_grau_page.py. Use one sd replacement over exactly those files and check that no other version remains.

    Browser check on a local server (start the backend as usual from fp-cercador/backend; stop it afterwards with kill $(lsof -tiTCP:5001 -sTCP:LISTEN)): in FPO mode, ADGD0073 (or any 'sepe' entry) shows "Formació en el treball" with its explanation in the detail, ADGD0108 shows "Cert. prof.", CTRD0012 (or any CTR* entry with courses) shows "Pròpia del SOC"; each option of the new filter narrows the list and combines with the certprof toggle; the clear button resets it; switching to ES shows Spanish copy; no console errors. Codes are from 2026-11-08 data; pick another entry of the same class if one has no course.

    Commit only this task's files: `feat(fpo): show training type badges and filter`. No AI attribution trailer. No deploy in this plan (owner approval required; never restart during the Sunday 11:10–11:45 refresh; the VPS needs a first manual SEPE refresh, see the source plan's Verificació).
  </action>
  <verify>
    <automated>node --check fp-cercador/frontend/i18n.js && for k in fpo.filter.vinculacio fpo.vinculacio.grauC fpo.vinculacio.sepe fpo.vinculacio.propiaSoc fpo.badge.formacioTreball fpo.badge.propiaSoc fpo.tooltip.formacioTreball fpo.chip.competenciaTransversal fpo.avis.vigencia; do test "$(rg -c -F "'$k'" fp-cercador/frontend/i18n.js)" = 2 || { echo "MISSING $k"; exit 1; }; done && test "$(rg -l -F 'i18n.js?v=20261108a' fp-cercador/frontend | wc -l | tr -d ' ')" = 15 && test "$(rg -l -F 'i18n.js?v=' fp-cercador/frontend | wc -l | tr -d ' ')" = 15 && rg -q -F "I18N_VERSION = '20261108a'" fp-cercador/backend/grau_page.py && test "$(rg -c -F 'fpoFilters.vinculacio' fp-cercador/frontend/index.html)" -ge 2 && rg -q -F "esp.vinculacio === 'sepe'" fp-cercador/frontend/index.html && (cd fp-cercador/backend && python3 -m pytest -q tests/test_grau_page.py tests/test_fpo_api.py)</automated>
    <human-check>Local browser check described in the action (three badge classes, filter, ES copy, no console errors); report the result in the SUMMARY.</human-check>
  </verify>
  <done>Each of the 9 keys appears exactly twice in i18n.js (CA + ES); all 15 pages, grau_page.py and its test use i18n.js?v=20261108a; the filter, badges, explanation, chip and notice behave as described in the local browser; site.css untouched; one commit with only this task's files.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| SEPE sede → scraper | Untrusted HTML fragments and JSON from sede.sepe.gob.es enter the pipeline |
| sepe_especs.json → /api/fpo/* → browser | SEPE-derived strings (titles, competència transversal, dates) reach the DOM |
| pipeline → admin mailbox | Failures trigger admin alert emails |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261108say-01 | Tampering | sepe_scraper.parse_row → index.html | medium | mitigate | Tags stripped and entities unescaped in the scraper; the UI renders SEPE values only with x-text (no x-html), so markup in a SEPE cell cannot execute |
| T-261108say-02 | Tampering | write_sepe_data | medium | mitigate | validate_rows (≥ MIN_ROWS 5000, unique codi) runs before the atomic tempfile + os.replace; a truncated or altered response raises and the previous snapshot stays |
| T-261108say-03 | Denial of Service | _fetch_raw_rows | low | mitigate | 30 s timeout per request, MAX_PAGES 20 loop guard, refresh at most once per 7 days, step is non-fatal so the Grados pipeline always completes |
| T-261108say-04 | Denial of Service | _notify_admin_soc_failure (SEPE) | low | mitigate | Own stamp file last_sepe_alert.json reuses the existing 24 h throttle |
| T-261108say-05 | Information Disclosure | /api/fpo/especialitat | low | accept | Only public catalogue data (internal SEPE id, dates, version) is exposed; no credentials or PII involved |
| T-261108say-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package installs: requests and the stdlib are already allowed dependencies (CLAUDE.md); any new dependency is out of scope and must stop for owner approval |
</threat_model>

<verification>
- `cd fp-cercador/backend && python3 -m pytest -q tests/test_sepe_scraper.py tests/test_sepe_refresh.py tests/test_fpo_api.py` green, offline.
- Routine offline suite green: `cd fp-cercador/backend && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`.
- Local fp-cercador/backend/data/sepe_especs.json has ≥ 7000 rows with unique codi.
- Real-data API check shows SOC entries split into grauC / sepe / propiaSoc with no None.
- Browser: 'sepe' entry shows "Formació en el treball" (+ explanation in the detail), CP entry shows "Cert. prof.", CTR* entry shows "Pròpia del SOC"; filter works with the certprof toggle; ES copy present.
- No programaSepeUrl, no /api/sepe/* route, no code-suffix meaning shown, site.css untouched.
</verification>

<success_criteria>
- Three atomic conventional commits (scraper, backend, UI), each staging only its own files, no AI attribution trailer.
- Source plan phases 1–4 fully delivered; "Fora d'abast" items untouched; deploy left for the owner.
</success_criteria>

<output>
Create `.planning/quick/261108-say-pla-081-scraper-cat-leg-sepe-enriquiment/261108-say-SUMMARY.md` when done
</output>
