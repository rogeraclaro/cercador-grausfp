# Pla 048: Unificar el cercador d'ocupació dins del cercador principal (mode toggle + gating)

> **Executor instructions**: Segueix el pla pas a pas. Executa cada comanda de
> verificació i confirma el resultat esperat abans de passar al següent. Si una
> condició STOP es dispara, atura't i reporta — no improvisis. Quan acabis,
> actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Spec de referència** (context complet del disseny i les decisions D1–D4):
> `docs/superpowers/specs/2026-06-20-unificar-cercadors-design.md`. Llegeix-la si vols
> el "per què"; aquest pla és autocontingut per al "com".
>
> **Drift check (executa primer)**:
> ```bash
> git diff --stat 12010fe..HEAD -- frontend/index.html frontend/ocupacions.html frontend/i18n.js
> ```
> Si algun fitxer ha canviat, compara els excerpts de "Current state" amb el codi
> viu. Si hi ha desviació en les línies que toques, tracta-ho com a condició STOP.

## Status

- **Priority**: P2
- **Effort**: L
- **Risk**: MED-HIGH (canvi gran a `index.html`, ~2.100 línies, component Alpine
  únic; el mode "nom" actual NO ha de tenir cap regressió)
- **Depends on**: F6 (pla 047 DONE, en producció) + login F1 (plans 023–026 DONE) +
  gating centres (pla 027 DONE)
- **Category**: direction (unificació cercadors)
- **Planned at**: commit `12010fe`, 2026-06-20

## Per què importa

Avui hi ha dos cercadors separats: el principal (`index.html`, cerca per nom/codi) i
el d'ocupació (`ocupacions.html`, F6). L'usuari vol **unificar-los en una sola pàgina**
amb un commutador de mode, perquè qui arriba a la home pugui cercar tant per nom com
per ocupació sense saber que existeix una segona pàgina.

Decisions ja preses (spec, no reobrir):
- **D1**: commutador de mode "Cerca per nom" / "Cerca per ocupació" dins `index.html`.
  El mode nom NO canvia. El mode ocupació reutilitza el `GET /api/ocupaciones` existent.
- **D2/D4**: el mode ocupació és **gated** amb el patró preview+mur (com centres, pla 027):
  anònim veu **3 resultats** + mur "Registra't"; registrat ho veu tot.
- **D3**: el registrat tria la **representació** del resultat d'ocupació: **Targetes**
  (default) o **Taula** (el cercador ric filtrat als graus coincidents). Preferència a
  **`localStorage`** (no BD en v1).
- `ocupacions.html` deixa d'existir com a pàgina; l'enllaç antic → `index.html?mode=ocupacio`.
- Les ocupacions segueixen sent **només en castellà** (v1).

## Current state

### Fitxers rellevants
- `frontend/index.html` (~2.108 línies) — component Alpine `cercador` (`<div x-data="cercador">`
  a la línia 1600). **Aquí va gairebé tot el canvi.**
- `frontend/ocupacions.html` — pàgina vanilla a retirar; la seva lògica es porta a Alpine.
- `frontend/i18n.js` — diccionari CA/ES (claus `ocupacions.*` ja existeixen del pla 047).
- `frontend/auth.js` — widget d'auth (no es toca).

### `index.html` — estat Alpine i auth (excerpts reals)

L'estat del component (cap a la línia 1134–1166) i la detecció de login:

```javascript
currentPage: 1,
// ...
loggedIn: false,
centresModalVisible: false,
favorites: new Set(),
filterFavs: false,

async init() {
  const [res, authRes] = await Promise.all([
    fetch(API_BASE + '/api/ofertes'),
    fetch(API_BASE + '/api/auth/me', { credentials: 'include' }).catch(() => ({ ok: false }))
  ]);
  this.loggedIn = authRes.ok;
  // ... carrega allRecords a partir de data ...
}
```

El **gating** ja existeix (modal reutilitzable) — `showCentresModal()` (línia 1413):
```javascript
showCentresModal() {
  this.centresModalVisible = true;
},
```
i el patró **preview-3 per anònims** (línia 1480):
```javascript
centresVisibles(row) {
  const total = (this.centresData[row.id] || []).length;
  if (this.loggedIn || total <= 3) { return this.centresFiltrats(row).slice(0, 50); }
  return (this.centresData[row.id] || []).slice(0, 3);
},
```
El modal HTML (línies 2083–2096) — REUTILITZA'L tal qual per al mur d'ocupació:
```html
<div x-show="centresModalVisible" @click="centresModalVisible = false" class="centres-modal-overlay" x-cloak>
  <div class="centres-modal" @click.stop>
    <button class="centres-modal-close" @click="centresModalVisible = false">✕</button>
    <p class="centres-modal-msg" data-i18n="modal.gate.msg">Registra't o entra...</p>
    <div class="centres-modal-actions">
      <a href="register.html" class="centres-modal-btn centres-modal-btn--primary" data-i18n="modal.gate.register">Registrar-me</a>
      <button class="centres-modal-btn centres-modal-btn--secondary" @click="centresModalVisible = false" data-i18n="modal.gate.later">Ara no</button>
    </div>
    <a href="login.html" class="centres-modal-login-link" data-i18n="modal.gate.login">Entrar</a>
  </div>
</div>
```

### `index.html` — caixa de cerca i taula (excerpts reals)

La caixa de cerca (línies 1619–1629):
```html
<div class="search-wrap">
  <svg ...>...</svg>
  <label for="search" class="sr-only" data-i18n="index.search.label">Cerca</label>
  <input type="search" id="search" x-model.debounce.250ms="search" @input="resetPage()"
    data-i18n-placeholder="index.search.placeholder" placeholder="Cerca per denominació o codi..."
    autocomplete="off">
</div>
```

La taula deriva TOTA d'un sol getter (línia 1256) — clau per a la representació Taula:
```javascript
get filteredRecords() {
  const q = this.search.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  const result = this.allRecords.filter(r => { /* filterGrado/Familia/Nivel/Old/Favs + q sobre _normDen/_normCod */ });
  if (this.sortDir !== 0) { /* sort */ }
  return result;
},
get pagedRecords() {                       // la taula itera AIXÒ
  const start = (this.currentPage - 1) * this.pageSize;
  return this.filteredRecords.slice(start, start + this.pageSize);
},
```
`pagedRecords`, `filteredCount`, `exportCSV()` i la paginació deriven de `filteredRecords`.
**Per tant, si `filteredRecords` retorna els registres coincidents per ocupació quan
estàs en mode ocupació+taula, tota la maquinària (paginació/CSV/comptador) funciona sola.**

El footer (línies 2099–2106), amb l'enllaç del pla 047:
```html
<footer style="...">
  <a href="historial.html" ... data-i18n="index.footer.historial">...</a>
  <a href="observatori.html" ... data-i18n="index.footer.obs">...</a>
  <a href="ocupacions.html" ... data-i18n="index.footer.ocupacions">Cerca per ocupació</a>
</footer>
```

### `ocupacions.html` — lògica a portar (excerpt real)
```javascript
function fichaHref(g){
  if (g.grado === 'C' && g.codigo)
    return API_BASE + '/api/ficha-redirect?grado=C&codigo=' + encodeURIComponent(g.codigo);
  return g.ficha_url || '#';
}
async function go(q){
  const r = await fetch(API_BASE + '/api/ocupaciones?q=' + encodeURIComponent(q));
  const d = await r.json();   // { query, n, resultados: [{grado, codigo, id, denominacion, familia, ficha_url, ocupaciones:[...]}] }
  // render targetes ...
}
```
Resposta de `/api/ocupaciones`: `{query, n, resultados: [{grado, codigo, id, denominacion, familia, ficha_url, ocupaciones: [str]}]}`.

## Comandes que necessitaràs

| Propòsit | Comanda | Esperat |
|---|---|---|
| Backend local | `cd backend && python3 app.py` | escolta a :5001 |
| Frontend local | `cd frontend && python3 -m http.server 8000` | escolta a :8000 |
| Índex ocupacions present? | `ls -la backend/data/ocupaciones.json` | existeix (si no, `python3 scripts/generate_ocupaciones.py`) |
| Tests backend (no regressió) | `cd backend && python3 -m pytest tests/ -q` | exit 0 (2 falles preexistents a test_db.py són alienes) |
| i18n claus | `for k in ...; do grep -c "'$k'" frontend/i18n.js; done` | cada clau → 2 |

> **Nota de verificació**: el projecte NO té test harness de JS; la verificació del
> frontend és **manual al navegador** (backend :5001 + frontend :8000, com al pla 047).
> Obrir amb `file://` NO funciona (API_BASE detecta `localhost`).

## Àmbit

**In scope** (els ÚNICS fitxers que pots crear/modificar):
- `frontend/index.html` — tot el gros (estat Alpine, UI commutadors, lògica ocupació, gating, taula)
- `frontend/i18n.js` — claus noves (CA+ES)
- `frontend/ocupacions.html` — convertir en redirect mínim a `index.html?mode=ocupacio`
- `plans/README.md` — actualitzar la fila del pla 048

**Out of scope** (NO tocar):
- `backend/` sencer — el `/api/ocupaciones` i `/api/auth/me` es reutilitzen sense canvis.
- `frontend/auth.js`, `frontend/seguiment.html`, `observatori.html`, etc.
- El comportament del **mode nom** (cerca actual): ha de quedar idèntic.
- Persistència de la preferència a BD (v1 = localStorage).
- Qualsevol traducció CA↔ES de les ocupacions (segueix només ES).

## Git workflow
- Branca: `feat/048-unificar-cercadors`
- Commits per etapa lògica (i18n / estat+toggle / mode ocupació targetes+gating / repr taula / retir ocupacions.html).
- NO push ni PR tret que l'operador ho demani.

---

## Pas 1: i18n — claus noves (CA + ES)

A `frontend/i18n.js`, afegeix al bloc `ca` i al `es` (mateixes claus a tots dos):

Bloc `ca`:
```javascript
'index.mode.nom': 'Cerca per nom',
'index.mode.ocupacio': 'Cerca per ocupació',
'ocup.repr.targetes': 'Targetes',
'ocup.repr.taula': 'Taula',
'ocup.search.placeholder': 'soldador, programador, cuidador…',
'ocup.veure.cercador': 'Veure al cercador',
'ocup.fitxa': 'Fitxa',
'ocup.wall.msg': 'Registra\'t per veure tots els graus i triar la vista.',
```
Bloc `es`:
```javascript
'index.mode.nom': 'Buscar por nombre',
'index.mode.ocupacio': 'Buscar por ocupación',
'ocup.repr.targetes': 'Tarjetas',
'ocup.repr.taula': 'Tabla',
'ocup.search.placeholder': 'soldador, programador, cuidador…',
'ocup.veure.cercador': 'Ver en el buscador',
'ocup.fitxa': 'Ficha',
'ocup.wall.msg': 'Regístrate para ver todos los grados y elegir la vista.',
```
Reutilitza les claus `ocupacions.empty`, `modal.gate.*` ja existents (no les dupliquis).

**Verifica**:
```bash
for k in index.mode.nom index.mode.ocupacio ocup.repr.targetes ocup.repr.taula \
         ocup.search.placeholder ocup.veure.cercador ocup.fitxa ocup.wall.msg; do
  n=$(grep -c "'$k'" frontend/i18n.js); echo "$k → $n"; [ "$n" -eq 2 ] || echo "  ⚠ esperat 2";
done
```
Esperat: cada clau → 2.

---

## Pas 2: Estat Alpine + commutador de mode

A `index.html`, dins l'objecte `cercador` (afegeix prop als altres camps d'estat, ~línia 1148):
```javascript
searchMode: 'nom',          // 'nom' | 'ocupacio'
ocupQuery: '',
ocupResults: [],            // resultados de /api/ocupaciones
ocupLoading: false,
ocupTimer: null,
reprOcup: (localStorage.getItem('reprOcup') === 'taula' ? 'taula' : 'targetes'),
```

Afegeix aquests mètodes dins el component (a prop de `showCentresModal`):
```javascript
setSearchMode(m) {
  this.searchMode = m;
  if (m === 'ocupacio' && this.ocupQuery.trim()) this.runOcupSearch();
},
setRepr(r) {
  this.reprOcup = r;
  try { localStorage.setItem('reprOcup', r); } catch (e) {}
},
async runOcupSearch() {
  const q = this.ocupQuery.trim();
  if (!q) { this.ocupResults = []; return; }
  this.ocupLoading = true;
  try {
    const r = await fetch(API_BASE + '/api/ocupaciones?q=' + encodeURIComponent(q));
    const d = await r.json();
    this.ocupResults = d.resultados || [];
  } catch (e) {
    this.ocupResults = [];
  } finally {
    this.ocupLoading = false;
  }
},
onOcupInput() {
  clearTimeout(this.ocupTimer);
  this.ocupTimer = setTimeout(() => this.runOcupSearch(), 250);
},
ocupFichaHref(g) {
  if (g.grado === 'C' && g.codigo)
    return API_BASE + '/api/ficha-redirect?grado=C&codigo=' + encodeURIComponent(g.codigo);
  return g.ficha_url || '#';
},
// Anònim: només 3 resultats. Registrat: tots.
ocupVisibleResults() {
  return this.loggedIn ? this.ocupResults : this.ocupResults.slice(0, 3);
},
ocupHasWall() {
  return !this.loggedIn && this.ocupResults.length > 3;
},
veureAlCercador(g) {
  // pont: canvia a mode nom filtrant pel grau (i codi si n'hi ha)
  this.searchMode = 'nom';
  this.filterGrado = g.grado || '';
  this.search = g.codigo || g.denominacion || '';
  this.resetPage();
},
```

A `init()`, després de fixar `this.loggedIn`, llegeix el query param de mode:
```javascript
const params = new URLSearchParams(location.search);
if (params.get('mode') === 'ocupacio') this.searchMode = 'ocupacio';
```

**Commutador de mode** — afegeix-lo a `index.html` JUST ABANS de `<div class="search-wrap">`
(dins de `<div class="hero">`, ~línia 1619). Recorda [[feedback]]: cada `x-show`/bloc condicional
ha de tenir un sol arrel.
```html
<div class="mode-toggle" role="tablist">
  <button :class="{ active: searchMode === 'nom' }" @click="setSearchMode('nom')"
    x-text="t('index.mode.nom')"></button>
  <button :class="{ active: searchMode === 'ocupacio' }"
    @click="if(!loggedIn && false){} setSearchMode('ocupacio')"
    x-text="t('index.mode.ocupacio')"></button>
</div>
```
(El mode ocupació NO es bloqueja en clicar el toggle — el gating és preview+mur DINS els
resultats, no al toggle. Anònim pot entrar al mode i veure 3 resultats.)

Afegeix CSS mínim per `.mode-toggle` i `.mode-toggle button.active` imitant l'estètica de
`.grau-tabs` existent (busca-la al `<style>`).

**Verifica** (manual, navegador): serveix backend+frontend, obre `http://localhost:8000/index.html`,
clica "Cerca per ocupació" → el mode canvia (de moment encara no es veu res de nou fins al Pas 3).
Consola sense errors. `index.html?mode=ocupacio` arrenca ja en mode ocupació.

---

## Pas 3: Mode ocupació — input + representació Targetes + gating

A `index.html`, dins `<div class="hero">`:
- El `search-wrap` existent (input de nom) només s'ha de veure en mode nom: embolcalla'l amb
  `<template x-if="searchMode === 'nom'">…</template>` (un sol arrel dins).
- Afegeix un input d'ocupació, visible només en mode ocupació:
```html
<template x-if="searchMode === 'ocupacio'">
  <div class="search-wrap">
    <svg ...>(copia la lupa del search-wrap de nom)</svg>
    <input type="search" x-model="ocupQuery" @input="onOcupInput()"
      :placeholder="t('ocup.search.placeholder')" autocomplete="off">
  </div>
</template>
```

Les **grau-tabs** i la **filter-bar** (i la taula del mode nom) només s'han de veure en mode nom
o en mode ocupació+taula. La manera més senzilla i sense risc: embolcalla el bloc de grau-tabs +
filter-bar amb `<template x-if="searchMode === 'nom'">`. (En mode ocupació+taula NO mostrem els
filtres de nom; els resultats ja venen filtrats per ocupació.)

**Resultats en Targetes** — afegeix un bloc nou que es vegi quan `searchMode === 'ocupacio'`
i (`reprOcup === 'targetes'` o l'usuari és anònim → en v1 l'anònim sempre veu Targetes, veure Pas 4):
```html
<template x-if="searchMode === 'ocupacio' && (reprOcup === 'targetes' || !loggedIn)">
  <div class="ocup-results">
    <!-- commutador de representació: només registrats (Pas 4) -->
    <template x-if="loggedIn">
      <div class="repr-toggle">
        <button :class="{ active: reprOcup==='targetes' }" @click="setRepr('targetes')" x-text="t('ocup.repr.targetes')"></button>
        <button :class="{ active: reprOcup==='taula' }" @click="setRepr('taula')" x-text="t('ocup.repr.taula')"></button>
      </div>
    </template>
    <template x-for="g in ocupVisibleResults()" :key="(g.codigo||'') + '-' + (g.id||'') + '-' + g.grado">
      <div class="ocup-card">
        <h3 x-text="g.denominacion + ' · ' + g.grado"></h3>
        <div class="ocup-tags">
          <template x-for="m in g.ocupaciones" :key="m"><span class="ocup-tag" x-text="m"></span></template>
        </div>
        <div class="ocup-actions">
          <button class="ocup-btn" @click="veureAlCercador(g)" x-text="t('ocup.veure.cercador') + ' →'"></button>
          <a class="ocup-link" :href="ocupFichaHref(g)" target="_blank" rel="noopener" x-text="t('ocup.fitxa') + ' ↗'"></a>
        </div>
      </div>
    </template>
    <!-- Mur per anònims (Pas 4) -->
    <template x-if="ocupHasWall()">
      <div class="ocup-wall" @click="showCentresModal()">
        <span x-text="t('ocup.wall.msg')"></span>
      </div>
    </template>
    <template x-if="searchMode==='ocupacio' && ocupQuery.trim() && !ocupLoading && ocupResults.length===0">
      <div class="empty" x-text="t('ocupacions.empty')"></div>
    </template>
  </div>
</template>
```
Afegeix CSS per `.ocup-results/.ocup-card/.ocup-tag/.ocup-actions/.ocup-btn/.ocup-link/.ocup-wall`
imitant l'estètica de targetes existent (pots inspirar-te en `ocupacions.html` abans d'esborrar-la).
Els textos dinàmics es renderitzen amb `x-text`/`t()` (NO `innerHTML`) → escaping automàtic d'Alpine.

**Verifica** (navegador, anònim): mode ocupació, cerca "soldador" → apareixen **3 targetes** + el
mur. Cada targeta té botó "Veure al cercador" i enllaç "Fitxa". Clicar "Veure al cercador" salta a
mode nom amb el grau filtrat. Clicar el mur obre el modal de registre. Consola neta.

---

## Pas 4: Gating preview+mur (verificació registrat) i mur

El gating ja està cablejat al Pas 3 via `ocupVisibleResults()` (3 per anònim) i `ocupHasWall()`
+ `showCentresModal()` (reutilitza el modal existent). Aquí només queda confirmar el camí registrat.

**Verifica** (navegador, registrat): entra amb un usuari (login.html), torna a `index.html`,
mode ocupació, cerca "soldador" → es veuen **tots** els resultats (sense mur) i apareix el
**commutador Targetes/Taula**. Consola neta.

**STOP si** no tens cap usuari de prova: crea'n un per `register.html` (necessita el backend amb
email configurat) o demana credencials a l'operador. NO desactivis el gating per "provar".

---

## Pas 5: Representació Taula (ramificar `filteredRecords`)

Quan `searchMode === 'ocupacio'` i `reprOcup === 'taula'` i `loggedIn`, la taula rica existent
ha de mostrar els graus coincidents. Com que tota la taula deriva de `filteredRecords`, ramifica
AL PRINCIPI del getter `filteredRecords` (línia ~1256):

```javascript
get filteredRecords() {
  if (this.searchMode === 'ocupacio' && this.reprOcup === 'taula' && this.loggedIn) {
    return this.ocupMatchedRecords();
  }
  const q = this.search.normalize('NFD')...   // (resta IDÈNTICA, no la toquis)
}
```

Afegeix el helper de mapeig (resultats d'ocupació → registres de `allRecords`):
```javascript
ocupMatchedRecords() {
  const byCod = new Map();
  const byId = new Map();
  for (const r of this.allRecords) {
    if (r.codigo) byCod.set(r.codigo, r);
    if (r.id != null) byId.set(String(r.id), r);
  }
  const out = [];
  const seen = new Set();
  for (const g of this.ocupResults) {
    let rec = (g.codigo && byCod.get(g.codigo)) || (g.id != null && byId.get(String(g.id))) || null;
    if (rec) {
      if (seen.has(rec.id)) continue;
      seen.add(rec.id);
      // anota les ocupacions coincidents per a la columna "Coincideix"
      this.ocupMatchByRec[rec.id] = g.ocupaciones;
      out.push(rec);
    }
    // Escape hatch: si el grau no casa amb cap registre (codi no reconciliat — limitació F6),
    // NO el perdis; però com que la taula necessita un registre del catàleg, registra'l a part:
    else { /* es queda fora de la taula; es veurà en mode Targetes. Documentar. */ }
  }
  return out;
},
```
Afegeix l'estat `ocupMatchByRec: {}` al component (i reinicialitza'l a `{}` al principi de
`ocupMatchedRecords()` per no acumular).

**Columna "Coincideix"**: a la fila de la taula (busca el `<template x-for="row in pagedRecords">`),
afegeix —només quan `searchMode==='ocupacio'`— una cel·la/etiqueta que mostri
`ocupMatchByRec[row.id]` (les ocupacions). Mantén-ho mínim per no trencar el layout de la taula.

El bloc de Targetes del Pas 3 ja s'amaga en mode taula (la seva `x-if` exclou `reprOcup==='taula'`
quan `loggedIn`). El commutador Targetes/Taula s'ha de veure també sobre la taula: posa una còpia
del `.repr-toggle` (o mou-lo fora) visible quan `searchMode==='ocupacio' && loggedIn`.

**Verifica** (navegador, registrat): mode ocupació, cerca "soldador", clica "Taula" → els graus
coincidents surten a la **taula rica** (amb centres/favorits/itineraris/CSV) + columna "Coincideix".
Recarrega la pàgina → la preferència "Taula" es recorda (localStorage). Torna a "Targetes" → torna a
les targetes. **El mode nom segueix funcionant igual** (cerca "informàtica" en mode nom → taula normal).

**STOP si** ramificar `filteredRecords` o afegir la columna t'obliga a tocar la paginació o el
mode nom de manera que en risc la cerca actual: atura't i reporta. La representació **Targetes ja
entrega la funcionalitat**; la Taula és millora i es pot diferir si resulta arriscada.

---

## Pas 6: Retirar `ocupacions.html` → redirect

Substitueix TOT el contingut de `frontend/ocupacions.html` per un redirect mínim (manté enllaços
externs antics funcionant):
```html
<!DOCTYPE html>
<html lang="ca">
<head><meta charset="utf-8"><title>Cerca per ocupació</title>
<meta http-equiv="refresh" content="0; url=index.html?mode=ocupacio">
<script>location.replace('index.html?mode=ocupacio');</script>
</head><body></body></html>
```

Canvia l'enllaç del footer a `index.html` (línia ~2105) perquè apunti al mode nou:
```html
<a href="index.html?mode=ocupacio" ... data-i18n="index.footer.ocupacions">Cerca per ocupació</a>
```
(Si prefereixes, treu l'enllaç del footer del tot, ja que ara és un mode de la mateixa pàgina —
però mantenir-lo apuntant a `?mode=ocupacio` és vàlid i menys disruptiu.)

**Verifica**: obre `http://localhost:8000/ocupacions.html` → redirigeix a `index.html?mode=ocupacio`
i arrenca en mode ocupació.

---

## Pas 7: No-regressió backend + neteja

```bash
cd backend && python3 -m pytest tests/ -q
```
Esperat: exit 0 (recorda: 2 falles preexistents a `test_db.py` —`schema_version 5≠1`— són alienes a
aquest pla; tota la resta passa). Aquest pla NO toca backend, així que no hi ha d'haver cap canvi.

Revisa que no quedin claus i18n `ocupacions.*` mortes que ja no s'usin enlloc; si en trobes, llista-les
i pregunta abans d'esborrar (NO les esborris sense confirmar).

---

## Test plan

No hi ha harness de JS al repo → verificació **manual al navegador** (com el pla 047), coberta pels
passos 2–6. Resum dels camins a comprovar:
1. Mode nom intacte (cerca per denominació/codi, filtres, paginació, CSV).
2. Commutador de mode i `?mode=ocupacio`.
3. Anònim: 3 targetes + mur → modal de registre.
4. Registrat: tots els resultats + commutador Targetes/Taula (recordat a localStorage).
5. "Veure al cercador" salta a mode nom filtrat.
6. `ocupacions.html` redirigeix.
Backend: `pytest tests/ -q` sense regressió.

## Criteris de DONE

- [ ] Drift check net (o desviacions tractades).
- [ ] Les 8 claus i18n noves existeixen 2 cops cadascuna.
- [ ] Mode nom: cap regressió (cerca/filtres/paginació/CSV funcionen com abans).
- [ ] Commutador "nom/ocupació" canvia de mode sense recarregar; `index.html?mode=ocupacio` arrenca en ocupació.
- [ ] Anònim en mode ocupació: veu exactament 3 resultats + mur; clicar el mur obre el modal de registre.
- [ ] Registrat: veu tots els resultats, té el commutador Targetes/Taula, i la tria es recorda després de recarregar.
- [ ] Targetes: cada una té "Veure al cercador →" (salta a mode nom filtrat) i "Fitxa ↗".
- [ ] Taula (registrat): els graus coincidents surten a la taula rica amb columna "Coincideix"; el mode nom segueix intacte. (Si s'ha hagut de diferir per STOP, documentat.)
- [ ] `ocupacions.html` redirigeix a `index.html?mode=ocupacio`.
- [ ] `cd backend && python3 -m pytest tests/ -q` → exit 0 (excepte les 2 falles preexistents de test_db.py).
- [ ] Cap fitxer fora d'"In scope" modificat.
- [ ] `plans/README.md` actualitzat amb estat del pla 048.

## Condicions STOP

- **Drift**: `frontend/index.html`/`i18n.js`/`ocupacions.html` han canviat des de `12010fe` i el
  codi no coincideix amb els excerpts on toques.
- **Regressió del mode nom**: si qualsevol canvi trenca la cerca/filtres/paginació/CSV actuals,
  atura't — el mode nom és sagrat.
- **Taula arriscada** (Pas 5): si ramificar `filteredRecords` o la columna "Coincideix" t'obliga a
  reescriure paginació o posa en risc el mode nom, atura't i reporta; Targetes ja entrega la feature.
- **Sense usuari de prova** per verificar el camí registrat: demana credencials, no desactivis el gating.
- **`x-if` amb múltiples arrels**: Alpine descarta silenciosament el 2n fill — cada `x-if`/`template`
  ha de tenir UN sol element arrel (limitació coneguda del projecte).

## Notes de manteniment
- `index.html` creix; vigila que el component Alpine no es faci inmanejable. Si algun bloc nou és
  gran, mantén-lo en mètodes nets del component (com s'ha fet aquí).
- **2a iteració** (fora d'abast): preferència de representació a BD (sincronitza dispositius);
  traducció/sinònims CA↔ES de les ocupacions; rànquing semàntic. Documentat a l'spec i a [[F6]].
- **Revisar en PR**: que el mode nom no tingui cap regressió; que els textos dinàmics usin `x-text`
  (no `innerHTML`); que el gating reutilitzi el modal del pla 027 sense divergir; que no s'hagin
  committejat dades gitignored.
