# Pla 060 — FPO: mode "Cursos FPO" al cercador, integració amb C LOE i plana Fonts

Origen: `docs/superpowers/specs/2026-09-06-fpo-soc-catalunya-design.md` (§6, §7, §12).
Depèn de: **059 DONE** (endpoints `/api/fpo/especialitats`, `/api/fpo/especialitat/<codi>`,
`/api/fpo/by-cert`).
Executable per un agent sense context (Sonnet). El frontend és HTML/CSS/JS
vanilla + Alpine (sense infra de test JS): TDD no aplica als canvis
d'`index.html`; sí als pocs canvis de backend d'aquest pla (cap). Es valida
manualment amb server local + screenshot, com el Pla 058 Fase 5.
**Totes les decisions estan preses aquí i a la spec.**

## Context

- El cercador (`frontend/index.html`) té un toggle de mode:
  `searchMode: 'nom' | 'ocupacio'`, funció `setSearchMode(m)`, param `?mode=ocupacio`.
  El mode `ocupacio` reusa el mateix dataset (`allRecords`); aquest serà el
  **primer mode amb un dataset propi**.
- Patró modal/panell reutilitzable: `showCentresModal()` per al gating;
  `.detall-certificat` / `.detall-inner` / `.detall-btns` / `.ciclos-d-list` per
  als panells desplegables (vegeu els panells C LOE i C LOMLOE afegits al Pla 058).
- i18n: `frontend/i18n.js`, blocs `ca:` i `es:`. `data-i18n` s'aplica a
  `DOMContentLoaded` via `el.innerHTML`. `t(key, vars)` interpola `{x}` (global).
- La plana `frontend/fonts.html` (Pla "Fonts de dades") ja existeix i està
  enllaçada al footer; té seccions per host amb taules `.src-table` i claus
  `fonts.*` (CA/ES).

## Decisions de disseny

1. **Tercer mode al toggle**: `Nom · Ocupació · Cursos FPO (Catalunya)`.
   `searchMode` accepta `'fpo'`. Param URL `?mode=fpo`. Param addicional `?esp=<codi>`
   per pre-filtrar per especialitat (l'usa la integració amb C LOE).
2. **Unitat de resultat = especialitat**. Llista de `/api/fpo/especialitats`.
   Lazy-fetch en entrar al mode per primer cop.
3. **Filtres propis** (no reusa la `filter-bar` de la FP reglada):
   Família → Àrea → Especialitat (selects dependents) · Comarca → Municipi
   (selects dependents) · Nivell · Estat d'inscripció · Modalitat ·
   "Només certificats de professionalitat".
4. **Panell obert a tothom.** Sense login: panell complet, sense controls de
   desat. (Els controls de desat els afegeix el Pla 061; aquest pla deixa els
   ganxos preparats però no els implementa.)
5. **Nota contextual fixa** dins el mode FPO. **Banner d'error** si l'API torna
   `warning`.
6. Taxonomia de famílies/àrees: **la del SOC** (ve dins les dades), no
   `families.py`.

## Fase 1 — i18n

`frontend/i18n.js`, afegir a `ca:` i `es:` (valors CA / ES):

- `index.mode.fpo`: "Cursos FPO (Catalunya)" / "Cursos FPO (Catalunya)"
- `fpo.note`: "Formació professional per a l'ocupació. Oferta i gestió de la
  Generalitat de Catalunya (SOC) — un sistema diferent de la FP reglada. Cobreix
  només Catalunya." / (traducció ES)
- `fpo.banner.unavailable`: "L'oferta de cursos FPO no està disponible
  temporalment." / (ES)
- `fpo.filter.text` ("Nom o codi de l'especialitat"), `fpo.filter.familia`
  ("Família professional"), `fpo.filter.area` ("Àrea"), `fpo.filter.especialitat`
  ("Especialitat"), `fpo.filter.comarca` ("Comarca"), `fpo.filter.municipi`
  ("Municipi"), `fpo.filter.nivell` ("Nivell"), `fpo.filter.estat`
  ("Estat d'inscripció"), `fpo.filter.modalitat` ("Modalitat"),
  `fpo.filter.certprof` ("Només certificats de professionalitat"),
  `fpo.filter.all` ("Tots") — CA/ES.
- `fpo.estat.informacio` ("En informació"), `fpo.estat.inscripcio`
  ("Inscripció oberta"), `fpo.estat.gestio` ("En gestió") — CA/ES.
- `fpo.col.nom`, `fpo.col.codi`, `fpo.col.familia`, `fpo.col.area`,
  `fpo.col.nivell`, `fpo.col.hores`, `fpo.col.ncursos` ("Cursos actius"),
  `fpo.badge.certprof` ("Cert. prof.") — CA/ES.
- `fpo.detall.programa` ("Programa (PDF)"), `fpo.detall.moduls`
  ("Mòduls formatius"), `fpo.detall.requisits` ("Requisits"),
  `fpo.detall.sortides` ("Sortides professionals"),
  `fpo.detall.cursos` ("Cursos actius a Catalunya"),
  `fpo.detall.fitxa_soc` ("Fitxa al SOC"),
  `fpo.detall.centre` ("Centre"), `fpo.detall.horari` ("Horari"),
  `fpo.detall.dates` ("Dates"), `fpo.detall.modalitat` ("Modalitat") — CA/ES.
- `fpo.empty` ("No hi ha especialitats que coincideixin.") — CA/ES.
- `index.itinerari.fpo_disponible`: "També s'ofereix com a formació per a
  l'ocupació a Catalunya — {n} cursos actius" / (ES). (integració C LOE)
- `index.itinerari.fpo_veure`: "Veure'ls al cercador FPO" / (ES).
- `fonts.s6.h2` ("Servei Públic d'Ocupació de Catalunya (SOC)"),
  `fonts.s6.host` ("serveiocupacio.gencat.cat"),
  `fonts.s6.p` (nota d'àmbit autonòmic / només Catalunya),
  `fonts.r10.font`/`.detall`/`.us` (Cursos FPO),
  `fonts.r11.*` (Especialitats formatives),
  `fonts.r12.*` (Centres de formació a Catalunya) — CA/ES.

Validar amb el mateix script del Pla "Fonts": totes les claus `fpo.*` i `fonts.s6*`
resolen en CA i ES; `node --check i18n.js` OK.

## Fase 2 — Toggle i estructura del mode FPO (`frontend/index.html`)

1. **Estat Alpine** (al costat de `searchMode`, `parentBLoeData`, etc.):
   ```js
   fpoEspecs: [],           // de /api/fpo/especialitats
   fpoLoaded: false,
   fpoWarning: null,
   fpoDetall: {},           // { codi: {…} } cache de /api/fpo/especialitat/<codi>
   fpoExpanded: {},          // { codi: bool }
   fpoFilters: { text:'', familia:'', area:'', especialitat:'', comarca:'', municipi:'',
                 nivell:'', estat:'', modalitat:'', certprof:false },
   ```
2. **`setSearchMode('fpo')`**: si `!this.fpoLoaded` → `await fetchFpoEspecs()`.
3. **`fetchFpoEspecs()`**: `fetch(API_BASE + '/api/fpo/especialitats')` →
   `this.fpoEspecs = data.especialitats || []`; `this.fpoWarning = data.warning || null`;
   `this.fpoLoaded = true`. `catch` → `this.fpoWarning = t('fpo.banner.unavailable')`.
4. **`init()`**: si `_params.get('mode') === 'fpo'` → `this.searchMode = 'fpo'` +
   `fetchFpoEspecs()`; si `_params.get('esp')` → desar-lo a `this.fpoFilters.especialitat`
   (i, quan carreguin les dades, obrir-ne el panell: `this.fpoExpanded[esp] = true`).
5. **Toggle** (`.mode-toggle`, ~línia 1940): afegir tercer botó
   `<button :class="{ active: searchMode === 'fpo' }" @click="setSearchMode('fpo')"
    x-text="t('index.mode.fpo')"></button>`.
6. **Nota contextual**: bloc `<p class="fpo-note" x-show="searchMode === 'fpo'"
   x-text="t('fpo.note')"></p>` sota el toggle. CSS nou mínim (`.fpo-note`:
   fons `--warm2`, text petit, `border-left` accent).
7. **Banner**: `<div class="fpo-banner" x-show="searchMode === 'fpo' && fpoWarning"
   x-text="fpoWarning"></div>`.
8. Amagar la `filter-bar` i la taula de la FP reglada quan `searchMode === 'fpo'`
   (afegir `&& searchMode !== 'fpo'` als `x-show` existents que ara diuen
   `searchMode === 'nom'` — de fet ja ho fan; verificar que `ocupacio` i `fpo`
   no ensenyen la taula reglada).

## Fase 3 — Barra de filtres FPO

Bloc nou `<div class="filter-bar" x-show="searchMode === 'fpo'">` amb:

- **Text**: `<input x-model="fpoFilters.text" :placeholder="t('fpo.filter.text')">`.
- **Família** `<select x-model="fpoFilters.familia" @change="fpoFilters.area=''; fpoFilters.especialitat=''">`:
  opcions = famílies úniques de `fpoEspecs` (`{codi, desc}` per idioma), ordenades.
- **Àrea** `<select x-model="fpoFilters.area" @change="fpoFilters.especialitat=''"
  :disabled="!fpoFilters.familia">`: àrees úniques de `fpoEspecs` filtrades per
  `familia`.
- **Especialitat** `<select x-model="fpoFilters.especialitat" :disabled="!fpoFilters.area">`:
  especialitats de `fpoEspecs` filtrades per `area`.
- **Comarca** `<select x-model="fpoFilters.comarca" @change="fpoFilters.municipi=''">`:
  comarques úniques (unió de `espec.comarques`).
- **Municipi** `<select :disabled="!fpoFilters.comarca">`: opcions =
  `esp.municipis[]` de les especialitats de la comarca triada.
- **Nivell** `<select>`: Tots / 1 / 2 / 3.
- **Estat** `<select>`: Tots / `informacio` / `inscripcio` / `gestio` (labels
  `t('fpo.estat.*')`). Filtra per `esp.estats[]` (algun curs amb aquell estat).
- **Modalitat** `<select>`: Tots / Presencial / Teleformació / Mixta
  (`esp.modalitats[]`).
- **Cert. prof.** `<label><input type="checkbox" x-model="fpoFilters.certprof">`.

Els agregats `comarques`, `municipis`, `estats`, `modalitats` ja venen a cada
entrada de `/api/fpo/especialitats` (Pla 059).

`filteredFpoEspecs` (getter Alpine): aplica tots els filtres sobre `fpoEspecs`.
Text: match normalitzat (sense accents, minúscules) sobre `titol` + `codi`.

## Fase 4 — Taula de resultats i panell de detall

1. **Taula** `<table class="results-table" x-show="searchMode === 'fpo'">`:
   `<template x-for="esp in filteredFpoEspecs" :key="esp.codi">` amb un `<tbody>`
   per especialitat (patró idèntic a la taula reglada del Pla 058):
   - Fila: nom (`esp.titol[lang]`) · codi · família · àrea · nivell · hores ·
     `esp.nCursos` · badge `t('fpo.badge.certprof')` si `esp.esCertProf`.
   - `@click` → `toggleFpoDetall(esp.codi)`.
   - `.row-link` sempre (totes les files despleguen).
2. **`toggleFpoDetall(codi)`**: alterna `fpoExpanded[codi]`; si s'obre i
   `!fpoDetall[codi]` → `fetch(API_BASE + '/api/fpo/especialitat/' + encodeURIComponent(codi))`
   → `this.fpoDetall = { ...this.fpoDetall, [codi]: data }`.
3. **Fila-panell** `<tr x-show="fpoExpanded[esp.codi]">` →
   `<td colspan="8" class="detall-certificat"><div class="detall-inner">`:
   - `<div class="detall-btns">`: `<a class="btn-doc" :href="d.programaUrl" target="_blank" rel="noopener" x-text="t('fpo.detall.programa')">`.
   - Descripció / requisits / sortides (`d.requisits[lang]`, `d.sortides[lang]`),
     cadascun dins un `<template x-if>` que comprova que no sigui buit.
   - **Mòduls formatius**: `<ul class="ciclos-d-list">` amb
     `d.moduls` → `mod.desc[lang] + ' (' + mod.durada + ' h)'`.
   - **Cursos actius**: caption `t('fpo.detall.cursos')` + per cada `curs in d.cursos`
     una targeta `.fpo-curs` amb:
     - centre: `curs.centre.nom`, adreça (`carrer, cp municipi (comarca)`),
       `telefon`, `email` (mailto), `web` (si no buit),
       horari (`fpo.detall.horari`: dies amb valor).
     - dates: `curs.dataInici – curs.dataFi`.
     - badge d'estat: classe segons `curs.estat`
       (`fpo-estat--inscripcio` verd, `--informacio` neutre, `--gestio` gris) +
       `t('fpo.estat.' + curs.estat)`.
     - modalitat.
     - `<a class="btn-doc" :href="curs.fitxaUrl" target="_blank" x-text="t('fpo.detall.fitxa_soc')">`.
   - **Ganxo per al Pla 061** (deixar preparat, sense implementar): un
     `<div class="fpo-fav-slot"></div>` o comentari
     `<!-- Pla 061: ⭐ desa especialitat + checkbox per curs -->` al principi
     del `.detall-inner`.
4. CSS nou mínim: `.fpo-note`, `.fpo-banner`, `.fpo-curs` (targeta amb
   `border`, `padding`, `margin-bottom`), `.fpo-estat--*` (badges). Reutilitzar
   la resta.
5. **Estat buit**: `<p x-show="searchMode==='fpo' && fpoLoaded && filteredFpoEspecs.length===0" x-text="t('fpo.empty')">`.
6. **Idioma**: helper `fpoLang()` → `getLang() === 'es' ? 'es' : 'ca'`; usar-lo
   a tots els `esp.titol[...]` / `desc[...]`.

## Fase 5 — Integració a la fitxa dels Grado C de pla antic

`frontend/index.html`, panell `<tr x-show="expandedRows[row.id] && row.grado === 'C' && row.plan_antiguo">`
(el que el Pla 058 va deixar per als C LOE):

1. Estat: `fpoByCert: {}` (cache per `codigo`).
2. En expandir el panell d'un C LOE (dins la funció que ja fa `fetchCiclosD` /
   `fetchBoe` per a aquesta fila, o al `@click` de la fila), afegir:
   `if (!this.fpoByCert[row.codigo]) { fetch(API_BASE + '/api/fpo/by-cert?codigo=' + encodeURIComponent(row.codigo)).then(r=>r.json()).then(d => this.fpoByCert = {...this.fpoByCert, [row.codigo]: d}).catch(()=>{}); }`
3. Bloc nou dins `.detall-inner` del panell C LOE:
   ```html
   <template x-if="fpoByCert[row.codigo] && fpoByCert[row.codigo].nCursos > 0">
     <div class="detall-ciclos-d">
       <span x-text="t('index.itinerari.fpo_disponible', {n: fpoByCert[row.codigo].nCursos})"></span>
       <a href="#" @click.prevent="location.href='index.html?mode=fpo&esp=' + encodeURIComponent(row.codigo)"
          x-text="t('index.itinerari.fpo_veure')"></a>
     </div>
   </template>
   ```
   (Si `nCursos == 0` o l'endpoint falla, no es mostra res.)

## Fase 6 — Plana "Fonts de dades"

`frontend/fonts.html`: afegir una `<h2 data-i18n="fonts.s6.h2">` + `<p class="src-host">`
+ `<p data-i18n="fonts.s6.p">` + una `<table class="src-table">` amb 3 files
(cursos / especialitats / centres), després de la secció del Registre Estatal i
abans de "Catàleg de famílies professionals". Claus `fonts.s6.*` i `fonts.r10..r12.*`
(afegides a la Fase 1). Sense CSS nou.

## Fase 7 — Verificació i desplegament

1. `cd backend && python -m pytest` → verd (aquest pla no toca tests de backend
   més enllà dels agregats del Pla 059; si s'han afegit `municipis`/`estats`/
   `modalitats`, actualitzar `test_fpo_api.py`).
2. Server local: `mode=fpo` carrega, filtres funcionen (Família→Àrea→Especialitat
   i Comarca→Municipi dependents), panell obre amb cursos i centres, badges
   d'estat correctes, botons "Programa (PDF)" i "Fitxa al SOC" obren.
   `index.html?mode=fpo&esp=IFCD0112` obre el panell d'aquella especialitat.
   Un C LOE amb cursos FPO mostra el bloc "També s'ofereix…". CA i ES.
   Screenshot per a l'usuari.
3. Commit: `feat(fpo): mode Cursos FPO al cercador, integració amb C LOE i plana Fonts`.
4. `git push` → VPS → `git pull --ff-only` → `systemctl restart fp-cercador`
   (frontend estàtic; el restart només cal si hi ha hagut canvi de backend pels
   agregats). Verificar a producció el mode FPO i un C LOE amb cursos.
5. `plans/README.md`: 060 DONE.

## Fora d'abast

- Favorits FPO i controls de desat al panell (Pla 061).
- Admin (Pla 061).
- Alertes, mapa de centres.

## Riscos

- **`fitxaUrl`**: si el patró d'URL de fitxa de curs no s'ha pogut confirmar al
  Pla 059, el botó "Fitxa al SOC" pot no obrir la fitxa exacta. Fallback:
  enllaç al cercador del SOC. Documentar.
- **Rendiment**: `filteredFpoEspecs` recalcula amb `x-model` a cada tecla;
  ~600 registres i filtres simples → OK (constraint del projecte: fluid fins a
  1.500). Si cal, `debounce` al camp de text (patró ja usat al cercador).
