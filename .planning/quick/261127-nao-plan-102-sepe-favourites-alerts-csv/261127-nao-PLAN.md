---
quick_id: 261127-nao
description: "Plan 102: favourites, course alerts, approximate new-entity alerts and CSV export for SEPE specialties"
date: 2026-11-27
phase: quick-261127-nao
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - fp-cercador/backend/app.py
  - fp-cercador/backend/sepe_entity_alerts_service.py
  - fp-cercador/backend/migrations/018_sepe_entity_alerts.sql
  - fp-cercador/backend/scrapers/pipeline.py
  - fp-cercador/backend/grau_page.py
  - fp-cercador/backend/tests/test_sepe_favorites_alerts.py
  - fp-cercador/backend/tests/test_sepe_entity_alerts.py
  - fp-cercador/backend/tests/test_grau_page.py
  - fp-cercador/frontend/index.html
  - fp-cercador/frontend/perfil.html
  - fp-cercador/frontend/i18n.js
  - fp-cercador/frontend/search-tools.js
  - fp-cercador/scripts/test_search_tools.js
  - fp-cercador/frontend/*.html (i18n.js ?v= bump only, 20 pages)
  - fp-cercador/plans/ESTAT.md
autonomous: true
requirements: [P102-FAV, P102-CURS, P102-ENT, P102-CSV, P102-PERFIL, P102-TESTS]

estimate:
  tokens: 130000
  raw_tokens: 130000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "A logged-in user can heart a SEPE row; GET /api/fpo/favorites returns it with name, family, hours and modality from the SEPE catalogue when the SOC lacks the code (P102-FAV)"
    - "The SEPE row detail has a course-alert button whose text depends on whether the specialty already has courses in Catalonia; it creates an fpo_alert with espec_codi only (P102-CURS)"
    - "A user can subscribe to 'new authorised entity' alerts for a specialty with optional province and teleformation-only filters; the weekly refresh re-fetches only specialties with active alerts and sends at most one email per user per refresh, saying the entity is authorised (not a course with dates), with an unsubscribe link (P102-ENT)"
    - "perfil.html#fpo shows SEPE favourites, SEPE course alerts (with title) and entity alerts; entity alerts can be paused/resumed and deleted (P102-PERFIL)"
    - "In the SEPE tab, a logged-in user can download the filtered SEPE list as CSV with the same format as exportCSV() (; separator, BOM, CRLF) (P102-CSV)"
    - "Nothing under fp-cercador/backend/data/ is created, modified or deleted while executing this plan"
  artifacts:
    - path: fp-cercador/backend/migrations/018_sepe_entity_alerts.sql
      provides: "sepe_entity_alerts + sepe_entity_snapshots tables, schema_version 18"
    - path: fp-cercador/backend/sepe_entity_alerts_service.py
      provides: "match, entity_key, load_snapshot, save_snapshot, check_new_entities"
    - path: fp-cercador/backend/tests/test_sepe_favorites_alerts.py
      provides: "tests for SEPE-only favourites and SEPE course alerts"
    - path: fp-cercador/backend/tests/test_sepe_entity_alerts.py
      provides: "tests for entity alerts: service, API, unsubscribe, pipeline wrapper"
  key_links:
    - from: fp-cercador/backend/scrapers/pipeline.py
      to: fp-cercador/backend/sepe_entity_alerts_service.py
      via: "notify_sepe_entity_alerts(data_dir) called in run() right after refresh_sepe_especs()"
    - from: fp-cercador/backend/app.py
      to: fp-cercador/backend/sepe_entity_alerts_service.py
      via: "/api/sepe/entity-alerts routes + snapshot seeding on POST"
    - from: fp-cercador/frontend/index.html
      to: fp-cercador/backend/app.py
      via: "toggleFpoFav(e.c), POST /api/fpo/alerts {espec_codi}, POST /api/sepe/entity-alerts"
    - from: fp-cercador/frontend/perfil.html
      to: fp-cercador/backend/app.py
      via: "GET/PATCH/DELETE /api/sepe/entity-alerts, GET /api/fpo/favorites (font 'sepe')"
---

# Quick task 261127-nao — Plan 102

Spec (owner-approved, the source of truth): `fp-cercador/plans/102-favorits-alertes-i-exportacio-sepe.md`.
All paths are relative to the git root `/Users/rogermasellas/AI/Cercador Graus`; every `<automated>` command
assumes the shell starts at that root.

<objective>
Give the SEPE training specialties (pla 082 tab and preview block) the same personal tools the FPO mode has:
favourites (heart), a course alert for Catalonia, an approximate "new authorised entity" alert refreshed weekly,
and a CSV export of the filtered list. Reuse the FPO favourites/alerts tables and services; the only new table
pair is for entity alerts (+ snapshot).

Purpose: owner decision of 2026-11-26 (idea 11); real case: SSCE22 had no courses and the SOC scheduled two.
Output: backend enrichment + new entity-alert module/migration/routes/pipeline step, UI in index.html and
perfil.html, i18n keys (ca + es), version bumps, tests.
</objective>

<safety>
HARD RULES — a long SEPE download (plan 100) is running on this Mac right now.
- Do NOT create, modify, move or delete anything under `fp-cercador/backend/data/` (it writes
  `sepe_programes.json` and `sepe-descarrega.log` there). Read-only access is also unnecessary: every test
  uses `tmp_path` and monkeypatches each `*_PATH` / `*_DIR` / cache it touches.
- Do NOT kill, restart or signal any python process. Do NOT start `app.py`, gunicorn or Flask's dev server
  (app start-up wires the APScheduler refresh and reads/writes `backend/data`). No browser verification in this
  task: record "not browser-verified" in the SUMMARY.
- Do NOT run `scripts/sepe_descarrega_programes.py`, `pipeline.run`, any `refresh_*`, or any scraper against the
  network. SEPE fetches and `email_service.send_email` are always mocked in tests.
- No deploy, no `git push`, no SSH. Commit locally on `master`, conventional commits in English, with NO
  attribution trailers (no Co-Authored-By, no session links). Stage files by explicit path; never `git add -A`
  (the root has untracked `grausfp-launch/` and `pt.log` that must stay out).
- No new dependencies (Python list in CLAUDE.md is closed; frontend is vanilla JS + vendored Alpine).
- Use `rg`/`fd`/`bat`/`eza` instead of grep/find/cat/ls.
</safety>

<context>
@fp-cercador/plans/102-favorits-alertes-i-exportacio-sepe.md
@fp-cercador/plans/ESTAT.md (sections "Pla 086 «Calendari FPO»" and "Catàleg d'Especialitats Formatives del SEPE")

Verified facts from the current code (2026-11-27, HEAD b2ae4b3):
- `POST /api/fpo/favorites` (app.py ~4486) accepts any `especialitat_codi`; `GET /api/fpo/favorites` (~4443)
  enriches only via `_fpo_espec_by_codi` (SOC or external) → a SEPE-only code returns empty titol/familia.
- `POST /api/fpo/alerts` (~3955) validates `espec_codi` only by length (`_fpo_alert_fields`, max 160): it is NOT
  checked against the SOC, so SEPE codes without courses are already accepted. `GET /api/fpo/alerts` fills
  `espec_titol` only via `_fpo_espec_by_codi` → None for SEPE-only codes. `tests/test_fpo_alerts_api.py`
  asserts the exact key set of that GET: do not add keys there, only fill `espec_titol`.
- `fpo_alerts_service.match` compares `alert.espec_codi` with `curs.especialitat.codi` (clean codes since pla 096),
  so an SSCE22 course appearing in the SOC triggers an SSCE22 alert. `describe()` prints the raw code: leave it.
- `_sepe_lookup(codi)` (app.py ~1780) resolves clean code, old code (`codiAntic`) and the legacy "X (Y)" form.
  `_sepe_llista()` (~2053) gives compact rows `{c, t, tca, tm, ca, f, a, n, m, h, vi, vf, nc, av, ...}` plus
  `families` / `arees` dicts `{codi: {ca, es}}`, with title overrides (pla 098) applied.
- Pla 099 entities: `sepe_scraper.fetch_entitats(id_sepe)` returns dicts `{id, nom, tipus ('teleformacio' |
  'presencial' | raw), provincia (title-cased, e.g. 'Madrid', 'A Coruña', 'Illes Balears'), adreca, telefon, web,
  email}`. `api_sepe_entitats` (~2209) caches them in `SEPE_ENTITATS_DIR/<codi>.json` as
  `{entitats, actualitzat}`; `_read_sepe_entitats(path)` reads that file. Entity `email` is admin-only.
- `alerts_service._get_or_create_unsubscribe_token(conn, alert_id, user_id, *, kind, token_type)` already takes a
  kind and token type (pla 086). The `tokens.type` column has no CHECK constraint.
- `_needs_auth_cors(path)` (~292) lists the session-using API prefixes; `/api/sepe/entity-alerts` does not match
  the existing `/api/sepe/entitats` prefix and must be added.
- Latest migration is `017_corrections_terms_misses.sql`; migrations end with
  `INSERT INTO schema_version (version) VALUES (N);`. `tests/test_db.py` derives the expected version from the
  files, so no test constant changes.
- Plan 053 (global email opt-out) is NOT implemented (no `email_prefs` anywhere in the backend) → no preference
  check is needed; say so in the SUMMARY.
- `scrapers/pipeline.py`: `run()` calls `refresh_sepe_especs(os.path.dirname(DATA_PATH))` (~570) after the SOC
  step; non-fatal pattern = `notify_fpo_new_courses` (~279): try/except, `logger.warning(... (no fatal) ...)`,
  return 0. `_report(phase)` is the local progress helper inside `run()`.
- index.html: SEPE rows are `<template x-for="e in pagedSepe">` (~5665), 6 columns; detail buttons in
  `.detall-btns` (~5750); the entities panel is `<template x-if="sepeEnt[e.c]">` with ONE root
  `<div class="sepe-ent">` (~5769), state `sepeEnt[codi] = {open, state, entitats, prov, tipus, nom, av}` and
  helpers `sepeEntProvs(codi)`, `sepeEntTipus(codi)`, `sepeEntTipusLabel(tp)`. Heart markup to copy: FPO row
  `btn-fav` (~5923). `toggleFpoFav(codi)` (~4392), `fpoFavSet` loaded at init when logged in (~2832).
  `createFpoAlert()` (~4189) is the POST/status-message pattern. `exportCSV()` (~3188) is the CSV format.
  Toolbar export button ~4751. `sepeTitol(e)`, `sepeFamilia(e)` (~3547). `showCentresModal()` = login prompt.
  `index.html?grado=SEPE&q=<codi>` opens the SEPE tab filtered by code (GFPSearch.stateFromParams).
- perfil.html: `loadFpo()` (~920) renders favourites cards (link `index.html?mode=fpo&esp=`, meta from
  `familia.desc`, `nivell`, `hores`, `font` via `t('fpo.font.' + font)`, programme link only if
  `safeHttpUrl()` = absolute http(s)); `loadFpoAlerts()` (~877) renders `#fpo-alerts` with pause/resume/delete
  buttons `.fpo-alert-btn` hitting `/api/fpo/alerts/<id>`. Everything is built with `esc()`.
- i18n: `frontend/i18n.js` has a `ca` block and an `es` block; every new key goes in both. Current asset
  versions: `i18n.js?v=` is the same value in 20 pages and in `backend/grau_page.py` `I18N_VERSION` (asserted in
  `backend/tests/test_grau_page.py` ~330); `search-tools.js?v=4` only in index.html.
- Test commands (from `fp-cercador/backend/`): `python3 -m pytest -q --ignore-glob='tests/*scraper*'
  --ignore=tests/test_pipeline.py` and `python3 -m pytest -q tests/test_sepe_scraper.py`; frontend
  `node scripts/test_search_tools.js` from `fp-cercador/`. New test files must NOT contain "scraper" in their
  name (they would be skipped). Reusable fixtures: `fpo_data` (tests/test_fpo_api.py: SOC files incl. IFCD0112,
  patches `SEPE_ESPECS_PATH` and the SEPE/SOC caches), `SEPE_ROWS` (tests/test_sepe_api.py: IFCD0112 idSepe 777
  with SOC courses, SSCE22 idSepe 97614 without), `_login(email)` (tests/test_fpo_alerts_api.py; needs
  `DB_PATH` env + `db.init_db`), `ent_calls` pattern for mocking `sepe_scraper.fetch_entitats`.
</context>

<decisions_taken>
Decisions taken (revisable) — the spec leaves these open; the conservative option was chosen. The executor must
copy this list into the SUMMARY and into the ESTAT.md line (Task 3).
1. Favourites: the SEPE catalogue fills the favourite only when the SOC/external sources lack the code; the
   entry then carries `font: 'sepe'` and a `modalitat` field (`''` for SOC entries). In the profile, a SEPE
   favourite links to `index.html?grado=SEPE&q=<codi>` instead of the FPO mode.
2. SEPE course alert = `fpo_alert` with only `espec_codi` and `inclou_en_linia: true` (no comarca/family). It
   counts toward the existing FPO limit of 10. The alert email keeps printing the code (unchanged `describe`).
3. Entity snapshot key = entity id + type (`"<id>|<tipus>"`): an entity already authorised in person that gets
   authorised for teleformation counts as new. The snapshot only grows (union), so an entity is announced at
   most once per specialty and type even if the SEPE list flickers.
4. A specialty checked for the first time without a snapshot is stored silently (no email). To avoid losing the
   days between subscribing and the next refresh, `POST /api/sepe/entity-alerts` seeds the snapshot from the
   entities cache the user has just seen in the panel, if that cache file exists.
5. Each weekly run deletes the snapshots of specialties that no longer have any entity-alert row.
6. Province / teleformation filters reuse the entities panel's own selects: province options are the provinces
   already present for that specialty (the SEPE spelling is guaranteed); "presencial" means "any modality" for
   the alert. A province with no entity yet cannot be chosen — the user picks "all provinces". A fixed list of
   52 provinces would need the SEPE's exact spelling, only partly known.
7. Email unsubscribe pauses the alert (same as FPO); the profile can resume (PATCH) or delete. Separate limit of
   10 entity alerts per user.
8. Emails are in Catalan (same as FPO alerts). No opt-out check: plan 053 is not implemented.
9. The entity step runs only inside `pipeline.run()` (weekly refresh and full manual refresh), not in the
   FPO-only manual refresh. It does not write the public entities cache. 1 s pause between SEPE specialties.
10. The entity-alert controls are added only to the SEPE row's entities panel, not to the FPO-mode copy.
11. CSV: button only in the SEPE tab toolbar; title in the current UI language; hours rounded as in the table;
    validity dates as ISO `YYYY-MM-DD`; file `grausfp-sepe-export.csv`; a shared `csvText` helper keeps
    `exportCSV()` output byte-identical.
</decisions_taken>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1 (tracer): SEPE favourites + Catalonia course alert, end-to-end</name>
  <files>fp-cercador/backend/app.py, fp-cercador/backend/tests/test_sepe_favorites_alerts.py, fp-cercador/frontend/index.html, fp-cercador/frontend/perfil.html, fp-cercador/frontend/i18n.js</files>
  <precondition>`git -C "/Users/rogermasellas/AI/Cercador Graus" status --short fp-cercador` shows no modified tracked files before starting (untracked root items are expected).</precondition>
  <behavior>
    - SEPE-only favourite: POST /api/fpo/favorites {especialitat_codi: 'SSCE22'} → 201; GET returns that entry with font 'sepe', titol.es and titol.ca non-empty (SEPE display title; ca = SOC Catalan title if any, else the same), familia {codi:'SSC', desc:{ca, es}}, hores 50.0, modalitat 'Presencial y teleformación', programaUrl '/api/sepe/programa/SSCE22'.
    - SOC favourite unchanged: IFCD0112 keeps the SOC titol and font 'soc'; modalitat key present.
    - Unknown code in neither source still returns the old empty shape (titol {ca:'', es:''}), no 500.
    - Alert with espec_codi 'SSCE22' (no SOC courses) → 201; GET /api/fpo/alerts shows espec_titol from SEPE and keeps the exact existing key set.
    - fpo_alerts_service.dispatch with a new SOC course whose especialitat.codi is 'SSCE22' sends exactly one email to the owner of that alert (send_email patched).
  </behavior>
  <action>
Backend (app.py, FPO favourites section): add a helper `_sepe_espec_as_fpo(codi)` that returns `{}` when `_sepe_lookup(codi)` finds nothing, else a dict in the same shape `fpo_favorites_get` already emits: `font: 'sepe'`, `titol: {ca, es}` taken from the matching compact row of `_sepe_llista()['especialitats']` (`es` = `tm`, `ca` = `tca or tm`, so pla 098 overrides apply), `familia` and `area` as `{codi, desc}` using `_sepe_llista()['families'|'arees']`, `nivell` (`n or 0`), `hores` (`h or 0.0`), `modalitat` (`m`), `esCertProf: False`, `programaUrl` = `/api/sepe/programa/<clean codi>` when the raw row has `idSepe`, else ''. In `fpo_favorites_get`, when `_fpo_espec_by_codi(codi)` is empty use this helper (per spec item 1: only when the SOC lacks the code), and add `"modalitat": espec.get("modalitat", "")` to every entry. In `fpo_alerts_get`, fill `espec_titol` from the SOC as today and fall back to the helper's `titol` (None if neither); do NOT add keys. No change to the POST endpoints (they already accept SEPE codes — the new tests lock that in).

Tests first (`backend/tests/test_sepe_favorites_alerts.py`, written before the code, must fail on the favourites assertions): fixture = `fpo_data` + write `SEPE_ROWS` to `fpo_data / 'sepe_especs.json'` + reset `_sepe_llista_cache` + `DB_PATH` env to a tmp db + `db.init_db`; log in with `_login`. Cover every bullet of `<behavior>`; for the dispatch test reuse the `_soc` course builder from tests/test_fpo_agenda.py (or `_curs` from tests/test_fpo_api.py) with especialitat codi SSCE22 and patch `email_service.send_email`.

Frontend index.html (SEPE row, per spec item 1–2):
- In the SEPE row `td.col-nom`, before the title, add the same heart button as the FPO row (`btn-fav`, same SVG, `@click.stop="loggedIn ? toggleFpoFav(e.c) : showCentresModal()"`, `btn-fav--active`, `:title`, `:aria-label` built with `sepeTitol(e)`, `:aria-pressed`). Favourites share `fpo_favorites`, so a code saved from the FPO mode shows as saved here too.
- New state `sepeCursAlertMsg: {}` and method `createSepeCursAlert(codi)` modelled on `createFpoAlert()`: not logged in → `showCentresModal()`; else set the codi's message to 'saving', POST `/api/fpo/alerts` with `{espec_codi: codi, inclou_en_linia: true}` and map 201→'saved', 200→'exists', 429→'max', other/exception→'error'.
- In the SEPE detail `.detall-btns`, add a `btn-doc` button calling it with `@click.stop`, disabled while saving, text `e.nc > 0 ? t('fpo.alert.cta') : t('sepe.alertCursos.cap')`. Below the buttons, a `role="status"` line showing `t('sepe.alertCursos.msg.saved')` for 'saved' and `t('fpo.alert.msg.' + msg)` for the others, plus the existing "manage" link pattern to `perfil.html#fpo` (`t('fpo.alert.manage')`) for saved/exists/max. Every visible string through `t()`; no literals in `x-text`.

Frontend perfil.html `loadFpo()`: when `e.font === 'sepe'`, the title link goes to `index.html?grado=SEPE&q=` + encoded code, the meta line includes `t('fpo.font.sepe')` (the existing `font` branch does this once the key exists) and `e.modalitat` when present, and the programme link is `API_BASE + e.programaUrl` (relative URL, so `safeHttpUrl` would drop it). Keep everything through `esc()`.

i18n.js (ca + es): `sepe.alertCursos.cap` ("Avisa'm quan hi hagi un curs a Catalunya" / "Avísame cuando haya un curso en Cataluña"), `sepe.alertCursos.msg.saved` (an email is sent when a course of this specialty appears in Catalonia), `fpo.font.sepe` ("Catàleg SEPE" / "Catálogo SEPE"). Do not bump `?v=` here (Task 3 does all bumps once).

Commit: `feat(sepe): favourites and Catalonia course alerts for SEPE specialties (plan 102)`.
  </action>
  <verify>
    <automated>cd fp-cercador/backend && python3 -m pytest -q tests/test_sepe_favorites_alerts.py tests/test_fpo_favorites_api.py tests/test_fpo_alerts_api.py tests/test_fpo_alerts_service.py tests/test_sepe_api.py</automated>
    <automated>cd fp-cercador && test "$(rg -c 'toggleFpoFav\(e\.c\)' frontend/index.html)" -ge 1 && test "$(rg -c "'fpo\.font\.sepe'" frontend/i18n.js)" -eq 2 && test "$(rg -c "'sepe\.alertCursos\.cap'" frontend/i18n.js)" -eq 2  # [HEAD=0/0/0 EXPECT>=1/=2/=2]</automated>
  </verify>
  <done>New test file green (it failed before the backend change); existing FPO favourites/alerts and SEPE API tests still green; SEPE rows have a working heart and a course-alert button whose text follows `e.nc`; profile shows SEPE favourites with name/family/hours/modality and a working link; keys exist in ca and es; one commit.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Approximate new-entity alerts (migration, weekly non-fatal step, email, API, panel UI, profile)</name>
  <files>fp-cercador/backend/migrations/018_sepe_entity_alerts.sql, fp-cercador/backend/sepe_entity_alerts_service.py, fp-cercador/backend/app.py, fp-cercador/backend/scrapers/pipeline.py, fp-cercador/backend/tests/test_sepe_entity_alerts.py, fp-cercador/frontend/index.html, fp-cercador/frontend/perfil.html, fp-cercador/frontend/i18n.js</files>
  <behavior>
    - Service, first run for a specialty without snapshot: snapshot stored, no email.
    - Second run with one extra entity: one email to the subscriber; body names the entity, its type and province, says it is an AUTHORISED entity (not a course with dates), contains the specialty title + code, the search link and `/api/sepe/entity-alerts/<id>/unsubscribe?token=`; it never contains the entity `email` field.
    - Province filter: alert 'Madrid' gets only Madrid entities; comparison ignores case and accents ('malaga' == 'Málaga'). Teleformation filter: only tipus 'teleformacio'.
    - One user with two alerts on two specialties, both with new entities → send_email called once with both sections.
    - Only specialties with at least one active alert of a verified, active, non-deleted user are fetched (fetch called with their idSepe only); paused alerts and unverified users get nothing.
    - A fetch error on one specialty does not stop the others and leaves its snapshot unchanged; an entity that disappears and reappears is not announced again (union).
    - Snapshots of specialties with no alert rows are deleted.
    - pipeline.notify_sepe_entity_alerts returns 0 and does not raise when the service raises.
    - API: 401 without session on GET/POST/PATCH/DELETE; POST with a valid code (also the old code) → 201 and stores the clean code; unknown code, non-string/too-long province, non-bool flag → 400; duplicate → 200 already_exists and reactivates; 11th row → 429; POST seeds the snapshot from a cached entities file when there is none; PATCH/DELETE of another user's alert → 404; DELETE → 204 and drops its tokens; unsubscribe with valid token → paused + redirect `/?unsubscribed=1`, bad token → `/?unsubscribe_error=1`.
  </behavior>
  <action>
Per spec item 3 (owner decision, approximate alert) and item 5. Write `backend/tests/test_sepe_entity_alerts.py` first (red), covering every `<behavior>` bullet; mock `sepe_scraper.fetch_entitats` with monkeypatch (pattern of the `ent_calls` fixture) and patch `email_service.send_email`; DB in tmp via `DB_PATH` + `db.init_db`; SEPE catalogue = `SEPE_ROWS` written to tmp; `SEPE_ENTITATS_DIR` monkeypatched to tmp for the seeding test. Then implement:

Migration `backend/migrations/018_sepe_entity_alerts.sql` (model: 015): table `sepe_entity_alerts` (id PK autoincrement, user_id FK users ON DELETE CASCADE, codi TEXT NOT NULL, provincia TEXT NULL = any, nomes_teleformacio INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1, created_at TEXT default now, last_sent_at TEXT), indexes on user_id and codi; table `sepe_entity_snapshots` (codi TEXT PRIMARY KEY, entitat_keys TEXT NOT NULL = JSON array, updated_at TEXT default now); final `INSERT INTO schema_version (version) VALUES (18);`. Header comments in Catalan like the other migrations are fine; SQL identifiers in English as above.

New module `backend/sepe_entity_alerts_service.py` (mirror `fpo_alerts_service.py` style and docstring): constants `ALERTS_MAX_PER_USER = 10`, `MAX_ENTITATS_PER_ALERTA = 20`, `TOKEN_KIND = "sepeent"`, `TOKEN_TYPE = "sepe_entity_alert_unsubscribe"`, `PAUSE_S = 1.0`. Functions: `entity_key(e)` → `"<id>|<tipus>"`; `match(alert, entitat)` (province compared after stripping accents via unicodedata NFD + casefold + strip; NULL province = any; `nomes_teleformacio` requires tipus 'teleformacio'); `load_snapshot(conn, codi)` → set or None; `save_snapshot(conn, codi, keys)` (INSERT OR REPLACE, sorted JSON list, updated_at now); `check_new_entities(data_dir, base_url, site_url, pause_s=PAUSE_S)` → emails sent. Flow: read `sepe_especs.json` from `data_dir` into `{codi: row}`; select active alerts joined to users with `verified = 1 AND is_active = 1 AND deleted_at IS NULL`; for each distinct codi present in the catalogue with `idSepe`: call `sepe_scraper.fetch_entitats(idSepe)` (import as `from scrapers import sepe_scraper`, like app.py), on any exception log a warning and skip that codi; if no snapshot → save and continue; new = entities whose key is not in the snapshot; save snapshot ∪ current; sleep `pause_s` between codis. Then group by user, one email per user (sections per alert with matched new entities, capped at `MAX_ENTITATS_PER_ALERTA` with "… i N més"), unsubscribe token via `alerts_service._get_or_create_unsubscribe_token(conn, alert_id, user_id, kind=TOKEN_KIND, token_type=TOKEN_TYPE)`, URL `{base_url}/api/sepe/entity-alerts/{id}/unsubscribe?token=...`, update `last_sent_at`, per-user try/except so one failure does not block others. Finally delete snapshots whose codi has no row in `sepe_entity_alerts`. Email in Catalan: subject with the count of new entities; body states clearly that these are entities the SEPE has AUTHORISED to teach the specialty and that this does not mean they have a scheduled course or dates; per section the specialty title (`titol_mostra` or `titol_es` or code) and code, each entity's name, type label (teleformació / presencial), province and web if any (never `email`, `telefon` optional, never NIF), the link `{site_url}/index.html?grado=SEPE&q=<url-encoded codi>`, the unsubscribe URL, and a footer like the FPO email.

Pipeline (`scrapers/pipeline.py`): add `notify_sepe_entity_alerts(data_dir)` next to `notify_fpo_new_courses`, same non-fatal wrapper (SITE_URL/BASE_URL resolution identical, `logger.info` with the count, `except Exception` → `logger.warning(... (no fatal) ...)` and return 0). In `run()`, immediately after the `refresh_sepe_especs(...)` call, add `_report("Alertes d'entitats (SEPE)")` and call it with `os.path.dirname(DATA_PATH)`.

API (app.py, new section after the FPO alerts section, import the module at top like `fpo_alerts_service`): add `/api/sepe/entity-alerts` to `_needs_auth_cors`. Extract a one-line helper `_sepe_entitats_path(codi)` used by `api_sepe_entitats` and the seeding. Routes, all session-based like `/api/fpo/alerts`:
- GET list (`id, codi, titol` via `_sepe_espec_as_fpo(codi).get('titol')`, `provincia, nomes_teleformacio, active, created_at, last_sent_at`), newest first.
- POST `{codi, provincia?, nomes_teleformacio?}`: codi must be a non-empty string ≤ 40 resolved by `_sepe_lookup` (store `sepe['codi']`), else 400; provincia None/'' → NULL, else stripped string ≤ 60, else 400; flag must be bool when present (default False), else 400. Duplicate (same codi, casefolded province, flag) → set active = 1, 200 `already_exists`. Count all rows (incl. paused) ≥ `ALERTS_MAX_PER_USER` → 429. Insert → 201 `created`. After inserting, if `load_snapshot` is None and `_read_sepe_entitats(_sepe_entitats_path(codi))` returns data, save the snapshot of its entity keys (decision 4).
- PATCH `/<int:id>` `{active: bool}`, DELETE `/<int:id>` (204, also delete its tokens by prefix like `_fpo_alert_drop_tokens`), both 404 when not owned.
- GET `/<int:id>/unsubscribe?token=` copy of `fpo_alerts_unsubscribe` with the new kind/type.

Frontend index.html (SEPE row entities panel): inside the existing single root `<div class="sepe-ent">` (keep ONE root in the `x-if` template), after the list, add a block shown when the panel state is 'ready': a note `t('sepe.entAlert.note')`, a line `sepeEntAlertFiltres(e.c)` describing the filters that will be saved (`t('sepe.entAlert.filtres', {prov, tipus})` with `prov` = selected province or `t('sepe.entAlert.provTotes')`, `tipus` = `t('sepe.entAlert.nomesTele')` when the panel's tipus is 'teleformacio' else `t('sepe.entAlert.qualsevolTipus')`), a `btn-doc` button `t('sepe.entAlert.btn')` calling `createSepeEntAlert(e.c)` with `@click.stop`, and a `role="status"` message `t('sepe.entAlert.msg.' + msg)` plus the manage link to `perfil.html#fpo`. `createSepeEntAlert(codi)`: login guard → `showCentresModal()`; POST `/api/sepe/entity-alerts` with `{codi, provincia: ent.prov || null, nomes_teleformacio: ent.tipus === 'teleformacio'}`; store the message in `sepeEnt[codi].alertMsg` (201 saved, 200 exists, 429 max, else error). No literals in `x-text`.

Frontend perfil.html `loadFpoAlerts()`: also fetch `/api/sepe/entity-alerts`; when it returns ≥1 item, append under the FPO list an `<h2 class="fpo-alerts-title">` `t('perfil.sepeEnt.title')`, a note `t('perfil.sepeEnt.note')` and a `fpo-alerts-list` whose items reuse the FPO markup/classes (paused badge, pause/resume, delete with aria-label) with label `titol[fpoLang] (codi) · province or t('sepe.entAlert.provTotes') · t('sepe.entAlert.nomesTele') when flagged`, all through `esc()`. Give these buttons `data-kind="ent"` and make the shared click handler pick `/api/sepe/entity-alerts/` vs `/api/fpo/alerts/` from `btn.dataset.kind`.

i18n.js (ca + es): `sepe.entAlert.btn` ("Avisa'm quan una entitat nova quedi autoritzada"), `sepe.entAlert.note` (authorised entity ≠ course with dates; checked once a week), `sepe.entAlert.filtres`, `sepe.entAlert.provTotes`, `sepe.entAlert.nomesTele`, `sepe.entAlert.qualsevolTipus`, `sepe.entAlert.msg.saved|exists|max|error`, `perfil.sepeEnt.title` ("Alertes d'entitats autoritzades (SEPE)"), `perfil.sepeEnt.note`.

Commit: `feat(sepe): weekly alerts for newly authorised training entities (plan 102)`.
  </action>
  <verify>
    <automated>cd fp-cercador/backend && python3 -m pytest -q tests/test_sepe_entity_alerts.py tests/test_db.py tests/test_fpo_alerts_service.py tests/test_fpo_alerts_api.py tests/test_sepe_api.py tests/test_sepe_refresh.py</automated>
    <automated>cd fp-cercador && test "$(fd '^018_sepe_entity_alerts\.sql$' backend/migrations | wc -l)" -eq 1 && test "$(rg -c 'notify_sepe_entity_alerts\(' backend/scrapers/pipeline.py)" -eq 2 && test "$(rg -c "'sepe\.entAlert\.btn'" frontend/i18n.js)" -eq 2 && test "$(rg -c '/api/sepe/entity-alerts' backend/app.py)" -ge 6  # [HEAD=0/0/0/0 EXPECT=1/=2/=2/>=6]</automated>
  </verify>
  <done>Test file green (red before the code); migration 018 applies (test_db green); `run()` calls the step right after `refresh_sepe_especs` and the wrapper is non-fatal; API CRUD + unsubscribe work with ownership checks; the panel shows the alert block with the filters it will save; profile lists entity alerts with pause/resume/delete; ca and es keys; one commit.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: CSV export of the filtered SEPE list, i18n headers, version bumps, ESTAT line</name>
  <files>fp-cercador/frontend/search-tools.js, fp-cercador/scripts/test_search_tools.js, fp-cercador/frontend/index.html, fp-cercador/frontend/i18n.js, fp-cercador/frontend/*.html (20 pages, i18n ?v= only), fp-cercador/backend/grau_page.py, fp-cercador/backend/tests/test_grau_page.py, fp-cercador/plans/ESTAT.md</files>
  <behavior>
    - csvText([['a', 'b;c'], ['x"y', null, 3]]) → BOM + `a;"b;c"` + CRLF + `"x""y";;3`; values containing `;`, `,`, `"`, CR or LF are quoted with doubled quotes; null/undefined → empty.
  </behavior>
  <action>
Per spec item 4. Add a pure `csvText(rows)` to `frontend/search-tools.js` (rows = array of arrays, first row the headers): same escaping rule as today's `exportCSV()` (quote when the value matches `[;,"\r\n]`, double the quotes), cells joined with ';', rows with CRLF, prefixed by the U+FEFF BOM; export it in the `api` object. Add node tests for the `<behavior>` case and the edge cases to `scripts/test_search_tools.js` (write them first, red).

index.html: add a component method `downloadCsv(rows, filename)` that builds the Blob from `GFPSearch.csvText(rows)` and triggers the download exactly as `exportCSV()` does now; refactor the tail of `exportCSV()` to use it (headers become the first row array; check with rg that no current `csv.header.*` / `csv.yes|no` value in ca or es contains `;`, `,`, `"` or a newline, so the output stays byte-identical — note the check in the SUMMARY). Add `exportSepeCSV()`: login guard → `showCentresModal()`; header row from `t()`: `csv.header.codi`, `csv.header.codiAntic`, `csv.header.denom`, `csv.header.fam`, `csv.header.niv`, `csv.header.hores`, `csv.header.modalitat`, `csv.header.vigInici`, `csv.header.vigFi`, `csv.header.cursosCat`; one row per `filteredSepe` record (the full filtered list, not the current page): `e.c`, `e.ca || ''`, `sepeTitol(e)`, `sepeFamilia(e)`, `e.n || ''`, `e.h ? Math.round(e.h) : ''`, `e.m || ''`, `e.vi || ''`, `e.vf || ''`, `e.nc`; file `grausfp-sepe-export.csv`. Toolbar: next to the existing export button add a `save-alert-btn` shown when `filterGrado === 'SEPE' && sepeState === 'ready' && filteredSepe.length > 0`, text `t('index.btn.exportCsv')`, title `index.btn.exportTitle(_one)` with `filteredSepe.length`.

i18n.js (ca + es): the six new `csv.header.*` keys ("Codi anterior", "Hores", "Modalitat", "Vigència (inici)", "Vigència (fi)", "Cursos a Catalunya" and their Spanish equivalents).

Version bumps (CLAUDE convention in the spec's "Context comú"): `i18n.js?v=` → `20261205` in all 20 `frontend/*.html` pages that load it, `I18N_VERSION = '20261205'` in `backend/grau_page.py`, and the matching assert in `backend/tests/test_grau_page.py`; `search-tools.js?v=4` → `?v=5` in index.html. site.css, footer.js and feedback.js are untouched, so their versions stay. Use `sd` for the mechanical page bump.

Run the full suites (commands below). Then add one line to `fp-cercador/plans/ESTAT.md` in the "Catàleg d'Especialitats Formatives del SEPE" section, in Catalan: plan 102 done locally on <date>, NOT deployed (needs migration 018 applied by the app start-up on the VPS and a restart outside a refresh window), commits, and the decisions list from `<decisions_taken>` in short form.

Commits: `feat(sepe): CSV export of the filtered SEPE list and asset version bumps (plan 102)` and `docs(plans): record plan 102 done locally, not deployed`.
  </action>
  <verify>
    <automated>cd fp-cercador && node scripts/test_search_tools.js && cd backend && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py && python3 -m pytest -q tests/test_sepe_scraper.py</automated>
    <automated>cd fp-cercador && test "$(rg -l 'i18n\.js\?v=20261205' frontend --glob '*.html' | wc -l)" -eq 20 && test "$(rg -c 'search-tools\.js\?v=5' frontend/index.html)" -eq 1 && test "$(rg -c 'exportSepeCSV' frontend/index.html)" -ge 2 && test "$(rg -c "'csv\.header\.cursosCat'" frontend/i18n.js)" -eq 2  # [HEAD=0/0/0/0 EXPECT=20/=1/>=2/=2]</automated>
  </verify>
  <done>Node tests and both pytest commands green (no failures; report the counts); the SEPE tab offers a CSV download of the whole filtered list with the 10 columns; `exportCSV()` output unchanged; all i18n/search-tools versions bumped consistently (grau_page test green); ESTAT.md line added; nothing under `fp-cercador/backend/data/` changed; two commits.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → /api/sepe/entity-alerts, /api/fpo/* | untrusted JSON bodies and path ids from logged-in users |
| email link → /api/sepe/entity-alerts/<id>/unsubscribe | unauthenticated request carrying a token |
| SEPE site → weekly step | external HTML parsed into entity dicts, then put in emails |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-102-01 | Elevation of privilege | entity-alert PATCH/DELETE | high | mitigate | session required (401); ownership query `WHERE id = ? AND user_id = ?` → 404 for others; tested |
| T-102-02 | Spoofing | unsubscribe endpoint | medium | mitigate | 64-hex token from `_get_or_create_unsubscribe_token`, stored as `sepeent_<id>_<token>` with its own type and expiry; mismatch → `/?unsubscribe_error=1`; tested |
| T-102-03 | Information disclosure | alert email / snapshot | medium | mitigate | email body never includes the entity `email` (admin-only) nor NIF; snapshot stores only `id|tipus`; tested by asserting the mocked email is absent from the body |
| T-102-04 | Tampering / injection | POST bodies | medium | mitigate | codi must resolve via `_sepe_lookup` (catalogue only, idSepe never from the user), province length ≤ 60, bool flag, parameterised SQL |
| T-102-05 | Information disclosure (XSS) | index.html / perfil.html rendering of SEPE titles, provinces | medium | mitigate | Alpine `x-text` only; perfil strings through `esc()` |
| T-102-06 | Denial of service | weekly step / SEPE load | low | mitigate | only specialties with active alerts, 10 alerts per user, one fetch per distinct code, 1 s pause, per-code and global try/except (non-fatal) |
| T-102-07 | Repudiation / spam | alert emails | low | mitigate | only verified, active, non-deleted users; one email per user per refresh; snapshot union prevents repeats |
| T-102-08 | Tampering | CSV formula injection | low | accept | values come from the official SEPE catalogue and the export mirrors the existing `exportCSV()` format |
| T-102-SC | Tampering | npm/pip/cargo installs | high | mitigate | no installs in this plan; the dependency lists in CLAUDE.md are closed |
</threat_model>

<verification>
From the git root:
- `cd fp-cercador/backend && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py` → all green.
- `cd fp-cercador/backend && python3 -m pytest -q tests/test_sepe_scraper.py` → green.
- `cd fp-cercador && node scripts/test_search_tools.js` → green.
- `git -C "/Users/rogermasellas/AI/Cercador Graus" log --oneline -4` shows the 4 commits with no attribution trailers (`git log -4 --format=%B | rg -c 'Co-Authored-By'` → 0).
- `git status --short` shows nothing under `fp-cercador/backend/data/` (ignored dir; also confirm no new files there with `eza -la --sort=modified fp-cercador/backend/data | tail -5` only listing the download's own files).
</verification>

<success_criteria>
- Spec items 1–5 and the three spec test groups are implemented and covered by tests.
- Every decision in `<decisions_taken>` is copied into the SUMMARY and the ESTAT.md line.
- SUMMARY states: plan 053 absent (no opt-out check), not browser-verified, not deployed (migration 018 pending on the VPS).
</success_criteria>

<source_audit>
| Source | Item | Covered by |
|--------|------|-----------|
| Spec 1 | Heart on SEPE rows; GET favourites + profile completed from SEPE | Task 1 |
| Spec 2 | Course-alert button, text depends on existing courses; `espec_codi` accepted without SOC courses | Task 1 |
| Spec 3 | Entity alerts: filters, migration, snapshot, weekly non-fatal step after SEPE, only codes with alerts, one email per user, "authorised" wording, unsubscribe, plan 053 check | Task 2 (053 absent → documented) |
| Spec 4 | CSV of filtered SEPE list, same session requirement and format | Task 3 |
| Spec 5 | Profile lists new alerts and allows deleting | Task 1 (course alerts via FPO list) + Task 2 (entity alerts) |
| Spec Tests | SEPE-only favourite; alert without SOC courses; entity detection, filters, one email, unsubscribe | Tasks 1–2 |
| Context comú | i18n ca+es, no literals in x-text, single-root x-if, `?v=` + `I18N_VERSION` + test assert bumps | Tasks 1–3 |
| Out of scope | Courses outside Catalonia (plan 104); new-specialty alerts | not planned |
</source_audit>

<output>
Create `.planning/quick/261127-nao-plan-102-sepe-favourites-alerts-csv/261127-nao-SUMMARY.md` when done.
</output>
