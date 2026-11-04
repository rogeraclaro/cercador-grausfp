---
phase: quick-261104-prj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - fp-cercador/frontend/index.html
  - fp-cercador/frontend/i18n.js
  - fp-cercador/frontend/itinerari.html
  - fp-cercador/backend/grau_page.py
  - fp-cercador/backend/tests/test_grau_page.py
autonomous: true
requirements: [quick-261104-prj]

estimate:
  tokens: 70000
  raw_tokens: 70000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "An anonymous visitor who clicks a row's centres badge sees the whole list: up to 50 centres plus the '… i N centres més' line. The CCAA select and the search input filter it, and no login modal opens. Before this change only 3 centres showed, with a 'Registra't per a veure'ls tots' link (D-01)"
    - "Login-only features stay login-only. Centre checkboxes and the watch button render only for logged-in users. Favourites, alerts, CSV export and official-fitxa links still open the registration modal for anonymous users (D-01)"
    - "In the centres panel of a Grado C row (any CCAA filter value), a link 'Cerca'ls al cercador de centres' (CA) / 'Búscalos en el buscador de centros' (ES) opens https://centres.grausfp.es/{ca|es}/search?cert={row.ref} in a new tab. It adds &ccaa={slug} only when the panel's CCAA filter has a value in the 19-entry mapping. The link never appears in A, B, D or E panels (D-02)"
    - "The index.html top bar shows a 'Centres' (CA) / 'Centros' (ES) link, in the same style as the auth buttons, to https://centres.grausfp.es/{ca|es}/ in a new tab (D-03)"
    - "No copy says that viewing centres needs an account. The registration-modal bullet b2 (CA+ES, plus the HTML fallback text in index.html and itinerari.html) now promotes a real login-only benefit. The /grau/<ref> page no longer says the centre list needs a free account (D-01)"
    - "GET /api/centres, /api/centres/count and /api/centres/info stay public (no session check). The backend suite (scrapers and test_pipeline excluded) passes"
  artifacts:
    - path: "fp-cercador/frontend/index.html"
      provides: "centresAppHref() top-level helper + CENTRES_APP_CCAA table; ungated centres panel; Grado C link; topbar Centres link; i18n.js?v=20261104a"
      contains: "function centresAppHref"
    - path: "fp-cercador/frontend/i18n.js"
      provides: "CA+ES keys index.centres.app_link and nav.centres; reworded modal.gate.b2"
      contains: "'index.centres.app_link'"
    - path: "fp-cercador/backend/grau_page.py"
      provides: "Centres section note that points to the search engine with no account claim"
      contains: "está en el buscador"
    - path: "fp-cercador/backend/tests/test_grau_page.py"
      provides: "Regression test: the centres section of /grau/<ref> has no account claim"
      contains: "def test_centres_sense_compte"
  key_links:
    - from: "centres panel <template x-if> for Grado C rows"
      to: "centresAppHref(getLang(), row.ref, centresCCAA[row.id])"
      via: ":href binding, target=_blank rel=noopener"
      pattern: "centresAppHref\\(getLang\\(\\), row\\.ref, centresCCAA\\[row\\.id\\]\\)"
    - from: "topbar <a> before #auth-widget"
      to: "centresAppHref(getLang())"
      via: ":href binding over a static https://centres.grausfp.es/ fallback href"
      pattern: "centresAppHref\\(getLang\\(\\)\\)"
    - from: "centresNoSeleccionats / centresVisibles"
      to: "centresFiltrats(row).slice(0, 50)"
      via: "same filtered + capped list for anonymous and logged-in users"
      pattern: "centresFiltrats\\(row\\)"
---

<objective>
Open the per-grau centres panel of GrausFP (`fp-cercador/frontend/index.html`) to anonymous users, link Grado C panels to the sister centres finder (centres.grausfp.es), add a topbar entry to that finder, and remove copy that still says centres need an account.

Owner decisions (locked), referenced in the tasks as:
- D-01: Anonymous users can view centres. Favourites, centre selection checkboxes, centres-watch and alerts stay login-only. Keep the registration modal (still used elsewhere). List any dead code instead of deleting it. Fix upsell copy that promises centres as a login benefit.
- D-02: In Grado C panels only, add an i18n link (CA "Cerca'ls al cercador de centres" / ES equivalent) to `https://centres.grausfp.es/{lang}/search?cert={REF}`, plus `&ccaa=` only when the CCAA filter maps cleanly. Open it in a new tab with rel=noopener and URL-encode the params.
- D-03: Add a minimal topbar link in index.html only to `https://centres.grausfp.es/{lang}/`, styled with existing topbar classes.

Findings that ground this plan (verified 2026-11-04, no need to re-derive):
- The backend never gated centres. `/api/centres`, `/api/centres/count` and `/api/centres/info` in `fp-cercador/backend/app.py` (~lines 350-445) have no session check, and the existing tests already call them anonymously. All gating is in the index.html frontend: `centresVisibles` caps anonymous users at 3 centres, `centresNoSeleccionats` returns early for anonymous users, `@mousedown`/`@focus` handlers on the panel's CCAA select and search input open the registration modal, an anonymous-only upsell block sits at the bottom of the panel (~line 4252), and the "more than 50" line requires `loggedIn`.
- Grado C rows: `row.ref === row.codigo` for all 981 Grado C records (LOMLOE `ADG_C_001_3B` and old `ADGG0408` alike). The centres app resolves `cert` through `certificate_alias` (kind=code, uppercased), which holds both kinds of code. So REF = `row.ref`.
- CCAA: GrausFP centre `ccaa` values are the uppercase registry names (`CATALUÑA`, NFC). The centres app `ccaa` param is a slug from a fixed table, not a plain slugify of our value (`ISLAS CANARIAS`→`canarias`, `MADRID`→`comunidad-de-madrid`). That table is `fp-centres-cercador/app/importer/normalise/geo.py` `_CCAA_ROWS` + `slugify`. The mapping below was computed from it. `ESTATAL` is left out because the centres app excludes province 60, so that slug resolves to nothing. Unknown slugs are ignored there and never raise.
- Lang: `getLang()` (i18n.js) returns `ca|es` and `setLang` reloads the page, so a non-reactive read is correct. The centres app routes are `/{ca|es}/...`.

Output: the edited index.html, i18n.js, itinerari.html, grau_page.py and test_grau_page.py. The SUMMARY lists the dead code and the follow-ups.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md

Stack constraint (CLAUDE.md): Flask + vanilla JS + Alpine 3 (vendored). Add no dependencies.
Commits: conventional commits in English, one per task. The owner's global rule forbids a `Co-Authored-By` line or any AI-attribution trailer, and it overrides any harness default.
Backend tests: run from `fp-cercador/backend` with `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py` (baseline 2026-11-04: 412 passed, ~19 s). Never run test_pipeline or the scraper tests: they hit the network and hang.
Commands below assume the repo root (`/Users/rogermasellas/AI/Cercador Graus`). Each verify command starts with `cd "$(git rev-parse --show-toplevel)"`.
Do NOT edit anything under `fp-centres-cercador/`. It is a separate repo and was read only to derive the CCAA slugs.

<interfaces>
index.html top-level script (classic `<script>` right after `i18n.js` / `auth.js`, ~line 2138), 4-space indent:
- `const API_BASE = ...;` (~2139)
- `function safeHttpUrl(u) { ... }` (~2144). Globals declared here are reachable from Alpine expressions; `safeHttpUrl(...)` and `API_BASE` are already used in templates.

Alpine component `cercador` methods (index.html):
- `centresUrl(row)` ~2709, `toggleCentres(row)` ~2713, `showCentresModal()` ~2731 (opens the registration modal; still used by favourites, alerts, CSV export, fitxa links and FPO favs)
- `centresVisibles(row)` ~2805: today, anonymous users with more than 3 centres get the first 3, unfiltered
- `centresFiltrats(row)` ~2813: filters by `centresCCAA[row.id]` (raw uppercase registry value, '' = all) and `centresSearch[row.id]`, sorted
- `centresSeleccionats(row)` ~2865 (already returns [] for anonymous users), `centresNoSeleccionats(row)` ~2871, `ccaasDisponibles(row)` ~2877

Centres panel template: `<tr class="centres-panel">` ~4155 to its `</tr>` ~4273 (no nested `<tr>`). `.centres-container` has max-height 400px and scrolls.
Topbar: `<div class="topbar"><div class="topbar-inner">` ~3413: logo `<a class="topbar-logo">`, `<div id="auth-widget">` (filled by auth.js; `margin-left:auto` in site.css), `.lang-selector`. The `.auth-btn` style lives in site.css (outlined white-on-dark, 44px target on coarse pointers).
Registration modal: index.html ~4593-4620, bullet `<span data-i18n="modal.gate.b2">` ~4605. The same bullet is in itinerari.html ~1851.
i18n.js: CA dict (`'index.centres.*'` ~156-168, `'modal.gate.*'` ~197-207, `'nav.*'` keys), ES dict (`'index.centres.*'` ~876-888, `'modal.gate.*'` ~917-927). `t(key, vars)` in Alpine expressions; `data-i18n` for static text (applied on DOMContentLoaded, sets innerHTML).
</interfaces>
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Ungate the centres panel for anonymous users and add the Grado C link to the centres finder</name>
  <files>fp-cercador/frontend/index.html, fp-cercador/frontend/i18n.js</files>
  <action>
<!-- planner-discipline-allow: showCentresModal -->
<!-- planner-discipline-allow: index.centres.upsell -->
Thinnest end-to-end path: an anonymous user clicks the badge, sees the full filterable list and, on a Grado C row, follows a correct link to the centres finder.

1. Add the URL helper (D-02) to index.html. In the top-level classic script, right after `function safeHttpUrl`, at the same 4-space indent, add these three declarations in this order and with nothing else between them:
   - `const CENTRES_APP_URL = 'https://centres.grausfp.es';`
   - `const CENTRES_APP_CCAA`: an object literal mapping the GrausFP centre `ccaa` value to the centres-app slug, with exactly these 19 pairs: ANDALUCÍA→andalucia, ARAGÓN→aragon, CANTABRIA→cantabria, CASTILLA LA MANCHA→castilla-la-mancha, CASTILLA Y LEÓN→castilla-y-leon, CATALUÑA→cataluna, CEUTA→ceuta, COMUNIDAD VALENCIANA→comunidad-valenciana, EXTREMADURA→extremadura, GALICIA→galicia, ILLES BALEARS→illes-balears, ISLAS CANARIAS→canarias, LA RIOJA→la-rioja, MADRID→comunidad-de-madrid, MELILLA→melilla, NAVARRA→navarra, PAÍS VASCO→pais-vasco, PRINCIPADO DE ASTURIAS→principado-de-asturias, REGIÓN DE MURCIA→region-de-murcia. Type the keys in NFC exactly as written. Leave ESTATAL out. Add a one-line English comment above the table: it mirrors `_CCAA_ROWS` + `slugify` in the sister repo fp-centres-cercador (`app/importer/normalise/geo.py`), ESTATAL is omitted because the centres app excludes it, and an unmapped value just drops the ccaa param.
   - `function centresAppHref(lang, cert, ccaa)`. The base is `CENTRES_APP_URL + '/' + (lang === 'es' ? 'es' : 'ca') + '/'`. With no `cert`, return the base. Otherwise build `new URLSearchParams` with `cert` first. Append `ccaa` only when the value is an own key of the table (use `Object.prototype.hasOwnProperty.call`, so inherited names like `toString` never match). Return base + `'search?'` + params. The closing brace goes on its own line at 4-space indent, which the verify regex relies on.
2. Ungate viewing (D-01) in the Alpine component.
   - Reduce `centresVisibles(row)` to returning `this.centresFiltrats(row).slice(0, 50)` for everyone.
   - In `centresNoSeleccionats(row)`, delete the anonymous early-return branch. Read the selection set only when logged in (fall back to an empty Set when anonymous), so the anonymous list is the same filtered, sorted, capped list. Do not touch `centresSeleccionats`, `toggleCentreSelect`, `toggleWatch`, `toggleFavorite`, `saveAlert`, `exportCSV` or `showCentresModal()`. They stay login-gated per D-01.
3. Edit the centres panel template (`<tr class="centres-panel">` … `</tr>`):
   - Remove the `@mousedown` handler from the CCAA `<select>` and the `@focus` handler from the search `<input>` (both opened the registration modal). Keep `x-model`, `@click.stop`, the placeholder and the classes.
   - Delete the whole anonymous upsell `<template x-if="!loggedIn && …length > 3">` block, including the commented-out separator `<hr>` and the upsell anchor.
   - In the "more than 50" template, drop the `loggedIn &&` condition so anonymous users also see "… i N centres més".
   - Right after the closing `</div>` of `.centres-header` and before the loading div, add `<template x-if="row.grado === 'C'">` with a SINGLE root element (Alpine x-if drops a second root silently): `<p class="centres-extern">` containing `<a :href="centresAppHref(getLang(), row.ref, centresCCAA[row.id])" target="_blank" rel="noopener" @click.stop x-text="t('index.centres.app_link')">`. Put it at the top because the container scrolls at 400px.
   - Keep the `x-show="loggedIn"` checkbox, the `x-if="loggedIn"` watch button and the A/B inherited note as they are.
4. CSS: rename the three `.centres-upsell` selectors (`.centres-upsell`, `.centres-upsell a`, `.centres-upsell a:hover`, ~line 1875) to `.centres-extern`. The rules themselves stay unchanged and now style the new link. Leave the `/* Gating centres … */` comment and `.centres-separator` alone; `.centres-separator` goes on the SUMMARY dead-code list.
5. i18n.js: add `'index.centres.app_link'` next to the other `'index.centres.*'` keys, in the CA dict ("Cerca'ls al cercador de centres") and the ES dict ("Búscalos en el buscador de centros"). Do NOT delete the now-unused upsell key in either dict; list it in the SUMMARY (D-01: no blind deletes).
6. Bump the `i18n.js?v=` query in index.html (~line 2136) from `20261030c` to `20261104a`.
7. Commit: `feat(centres): open centres panel to anonymous users and link Grado C to centres finder`. No attribution trailer.
  </action>
  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && node -e 'const fs=require("fs");const h=fs.readFileSync("fp-cercador/frontend/index.html","utf8");const m=h.match(/const CENTRES_APP_URL[\s\S]*?\n    \}\n/);if(!m)throw new Error("helper not found");const f=new Function(m[0]+";return centresAppHref;")();const eq=(a,b)=>{if(a!==b)throw new Error(a+" vs "+b)};const B="https://centres.grausfp.es/";eq(f("ca"),B+"ca/");eq(f("es"),B+"es/");eq(f("es","ADGG0408","CATALUÑA"),B+"es/search?cert=ADGG0408&ccaa=cataluna");eq(f("ca","ADG_C_001_3B",""),B+"ca/search?cert=ADG_C_001_3B");eq(f("ca","X","ESTATAL"),B+"ca/search?cert=X");eq(f("ca","X","toString"),B+"ca/search?cert=X");eq(f("ca","A&B"),B+"ca/search?cert=A%26B");const E={"ANDALUCÍA":"andalucia","ARAGÓN":"aragon","CANTABRIA":"cantabria","CASTILLA LA MANCHA":"castilla-la-mancha","CASTILLA Y LEÓN":"castilla-y-leon","CATALUÑA":"cataluna","CEUTA":"ceuta","COMUNIDAD VALENCIANA":"comunidad-valenciana","EXTREMADURA":"extremadura","GALICIA":"galicia","ILLES BALEARS":"illes-balears","ISLAS CANARIAS":"canarias","LA RIOJA":"la-rioja","MADRID":"comunidad-de-madrid","MELILLA":"melilla","NAVARRA":"navarra","PAÍS VASCO":"pais-vasco","PRINCIPADO DE ASTURIAS":"principado-de-asturias","REGIÓN DE MURCIA":"region-de-murcia"};for(const [k,v] of Object.entries(E))eq(f("ca","X",k),B+"ca/search?cert=X&ccaa="+v);console.log("helper ok")' && ! awk '/<tr class="centres-panel">/,/<\/tr>/' fp-cercador/frontend/index.html | rg -q 'showCentresModal|index\.centres\.upsell|loggedIn && centresFiltrats' && awk '/<tr class="centres-panel">/,/<\/tr>/' fp-cercador/frontend/index.html | rg -q 'centresAppHref\(getLang\(\), row\.ref, centresCCAA\[row\.id\]\)' && ! rg -q 'if \(!this\.loggedIn\) return this\.centresVisibles' fp-cercador/frontend/index.html && test "$(rg -c "'index\.centres\.app_link':" fp-cercador/frontend/i18n.js)" = 2 && rg -q 'i18n\.js\?v=20261104a' fp-cercador/frontend/index.html && node --check fp-cercador/frontend/i18n.js && echo TASK1_OK</automated>
  </verify>
  <done>
    Baselines at HEAD (2026-11-04): the helper regex finds nothing, the panel region has 3 gate/upsell matches plus the `loggedIn && centresFiltrats` condition, the anonymous early-return exists, and app_link count is 0. After the change the verify prints `helper ok` and `TASK1_OK`. An anonymous user's panel lists up to 50 centres, filterable by CCAA and text, with no modal. Grado C panels show the finder link. One commit with the subject above.
  </done>
</task>

<task type="auto">
  <name>Task 2: Topbar link to the centres finder and registration-modal copy that no longer sells centres</name>
  <files>fp-cercador/frontend/index.html, fp-cercador/frontend/i18n.js, fp-cercador/frontend/itinerari.html</files>
  <action>
1. Topbar (D-03). In index.html, inside `.topbar-inner` between the `topbar-logo` anchor and `<div id="auth-widget">`, add one anchor with class `auth-btn topbar-centres`, static `href="https://centres.grausfp.es/"` (fallback if Alpine fails), `:href="centresAppHref(getLang())"`, `target="_blank"`, `rel="noopener"`, `data-i18n="nav.centres"` and the text content "Centres". Do not put it inside `#auth-widget`: auth.js rewrites that element. In index.html's own `<style>`, next to the other topbar/auth overrides (~line 1895, the "Auth widget al topbar" comment), add `.topbar-centres { margin-left: 16px; }`. Leave site.css untouched (it is shared by 14 pages, and D-03 limits this change to index.html).
2. i18n.js: add `'nav.centres'` next to the existing `'nav.*'` keys in both dicts: CA "Centres", ES "Centros".
3. Registration-modal copy (D-01). Bullet b2 currently promises the centres list as an account benefit, which is now false. Reword `'modal.gate.b2'` in both dicts to a real login-only benefit: CA "Marca els centres que t'interessen i troba'ls al teu perfil." ES "Marca los centros que te interesan y encuéntralos en tu perfil." Update the matching HTML fallback text inside `<span data-i18n="modal.gate.b2">` in index.html (~line 4605) and itinerari.html (~line 1851) to the new CA sentence. Leave the other bullets and the note alone.
4. Cache-bust: bump `i18n.js?v=` in itinerari.html (~line 865) from `20261102a` to `20261104a`. index.html is already on `20261104a` from Task 1. Other pages do not render changed keys, so leave them as they are.
5. Commit: `feat(topbar): link to centres finder and drop centres from signup benefits`. No attribution trailer.
  </action>
  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)" && awk '/<div class="topbar">/,/<main id="main">/' fp-cercador/frontend/index.html | rg -q 'centresAppHref\(getLang\(\)\)' && awk '/<div class="topbar">/,/<main id="main">/' fp-cercador/frontend/index.html | rg -q 'data-i18n="nav\.centres"' && test "$(rg -c "'nav\.centres':" fp-cercador/frontend/i18n.js)" = 2 && ! rg -q "'modal\.gate\.b2': 'Consulta" fp-cercador/frontend/i18n.js && ! rg -q 'data-i18n="modal\.gate\.b2">Consulta' fp-cercador/frontend/index.html fp-cercador/frontend/itinerari.html && rg -q 'i18n\.js\?v=20261104a' fp-cercador/frontend/itinerari.html && node --check fp-cercador/frontend/i18n.js && echo TASK2_OK</automated>
  </verify>
  <done>
    Baselines at HEAD: there is no topbar link and `nav.centres` count is 0. The old b2 text matches in i18n.js (CA+ES) and in both HTML fallbacks, and itinerari.html is on `20261102a`. After the change the verify prints `TASK2_OK`. The top bar shows "Centres"/"Centros" linking to `https://centres.grausfp.es/{lang}/` in a new tab. No modal bullet claims that centres need an account. One commit.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: /grau/&lt;ref&gt; page note without the account claim, plus backend regression run</name>
  <files>fp-cercador/backend/tests/test_grau_page.py, fp-cercador/backend/grau_page.py</files>
  <behavior>
    - test_centres_sense_compte: for `ADG_C_001_3B` (fixture total 3), the `<section data-centres-total="…">…</section>` block of the page contains "está en el buscador" and does not contain the word "cuenta".
    - Existing test_fitxa_oficial_sense_enllac_directe still passes. The official-fitxa note stays account-gated and is out of scope.
  </behavior>
  <action>
1. RED: in `fp-cercador/backend/tests/test_grau_page.py`, next to `test_centres_agregats_per_comunitat_sense_noms`, add `test_centres_sense_compte(client)`. It extracts the centres section from `_page(client, 'ADG_C_001_3B')` with a non-greedy DOTALL regex on `<section data-centres-total="\d+">.*?</section>`, asserts the match exists, asserts "está en el buscador" is in it and asserts "cuenta" is not. Add `import re` if it is missing. Run it and confirm it fails.
2. GREEN (D-01): in `fp-cercador/backend/grau_page.py` `_centres_html` (~line 363), replace the closing note paragraph, the sentence saying the centre list needs a free account, with `<p class="note">La lista con el nombre y los datos de cada centro está en el buscador.</p>` (Spanish, like the rest of the page per the module docstring). Keep the "Ver los centros" button and the no-centre-names rule unchanged: the SEO page still lists only CCAA counts.
3. In the module docstring (~lines 13-14), make the rationale accurate without changing the rule. It should say centre names are never shown because the list lives in the search engine. Only the official-fitxa link keeps the login gate.
4. Do not bump `I18N_VERSION` in grau_page.py: the SEO pages use none of the changed keys.
5. Run the full backend suite (command in verify). If a test asserts the old note, update that test.
6. Confirm `/api/centres` stays public: the route body between `@app.route("/api/centres")` and `@app.route("/api/centres/count")` in app.py must contain no session or admin check. This is a non-regression check, not a change; the baseline already passes.
7. Commit: `fix(grau-page): drop account claim from centres note`. No attribution trailer.
  </action>
  <verify>
    <automated>cd "$(git rev-parse --show-toplevel)/fp-cercador/backend" && python3 -m pytest -q tests/test_grau_page.py -k "centres_sense_compte or fitxa_oficial" && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py && ! rg -q 'cada centro está disponible' grau_page.py && ! awk '/^@app.route\("\/api\/centres"\)/,/^@app.route\("\/api\/centres\/count"\)/' app.py | rg -q '_get_session_user|_check_auth|_check_admin|cookies' && echo TASK3_OK</automated>
  </verify>
  <done>
    The new test fails before the copy change and passes after it. The full suite passes (baseline 412 + 1 new = 413). grau_page.py no longer has the account claim for centres. The `/api/centres` route has no auth check (unchanged, confirmed). `TASK3_OK` is printed. One commit.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser → GrausFP API | Anonymous clients now read the full `/api/centres` list in the UI. The endpoint was already public. |
| GrausFP page → centres.grausfp.es | Outbound links built from row data (`row.ref`) and the centre `ccaa` value |
| scraped centre data → DOM | `centre.url_web` and the other registry fields are rendered in the panel (pre-existing) |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261104-01 | Tampering | centresAppHref query string | low | mitigate | `cert` is encoded with URLSearchParams. `ccaa` is never passed through: only slugs from the fixed 19-entry own-key table are emitted, and unknown or inherited keys drop the param (verified by the Task 1 node check). |
| T-261104-02 | Spoofing | new-tab links (panel + topbar) | low | mitigate | `rel="noopener"` on both anchors (reverse-tabnabbing). The destination is a hard-coded https origin. |
| T-261104-03 | Information disclosure | centres list visible to anonymous users | low | accept | Owner decision D-01. The data is the public Registro Estatal de centros, and `/api/centres` was already unauthenticated, so there is no new exposure at the API level. |
| T-261104-04 | Tampering | `:href="centre.url_web"` in the panel | low | accept | Pre-existing and out of scope. The scraper normalises the protocol (fix 28da5c9). Anonymous users now see more of these links, so the SUMMARY should suggest wrapping it in the existing `safeHttpUrl()` as a follow-up. Do not change it here (scope discipline). |
| T-261104-SC | Tampering | npm/pip/cargo installs | high | mitigate | No package installs in this plan, and no new dependency (CLAUDE.md constraint). |
</threat_model>

<verification>
- The Task 1, 2 and 3 automated commands print TASK1_OK, TASK2_OK and TASK3_OK.
- Backend suite: `cd fp-cercador/backend && python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py` passes (413 expected).
- Optional manual smoke check (not blocking). Logged out, start the API with `cd fp-cercador/backend && python3 app.py` (port 5001; index.html targets `http://localhost:5001` when the hostname is `localhost`). Serve the frontend with `python3 -m http.server 8000 -d fp-cercador/frontend` and open http://localhost:8000/index.html. Search "ADGG0408" and click the centres badge. Expect the full list, a working CCAA filter with no modal, and the "Cerca'ls al cercador de centres" link pointing to `…/ca/search?cert=ADGG0408` (plus `&ccaa=cataluna` once Catalunya is picked). Stop both servers with `kill $(lsof -tiTCP:5001 -sTCP:LISTEN) $(lsof -tiTCP:8000 -sTCP:LISTEN)`, because `pkill` does not kill them.
</verification>

<success_criteria>
- D-01: anonymous users see the full, filterable centres list. Favourites, checkboxes, watch, alerts, CSV and fitxes stay login-only. No copy (modal b2 CA/ES and HTML fallbacks, /grau page note) claims centres need an account.
- D-02: Grado C panels link to `https://centres.grausfp.es/{lang}/search?cert={row.ref}` with a clean `&ccaa=` slug when one is mapped, in a new tab with noopener and encoded params.
- D-03: the index.html top bar links to `https://centres.grausfp.es/{lang}/` with the existing `.auth-btn` style.
- Three conventional commits with no attribution trailer, and the backend suite is green.
- The SUMMARY lists:
  - Dead code that was kept, not deleted: the upsell i18n key in CA+ES, and the `.centres-separator` CSS rule in index.html, whose only reference was the commented-out `<hr>` removed with the upsell block.
  - That `showCentresModal()` and the modal stay in use.
  - Follow-ups: the other pages that share the site.css topbar could get the same Centres link; wrap `centre.url_web` with `safeHttpUrl()`; the CCAA slug table mirrors fp-centres-cercador `geo.py` and must change if that table changes.
</success_criteria>

<output>
Create `.planning/quick/261104-prj-open-centres-panel-to-everyone-and-link-/261104-prj-SUMMARY.md` when done
</output>
