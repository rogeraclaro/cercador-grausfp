# Phase 5: Frontend — Cercador - Research

**Researched:** 2026-04-19
**Domain:** Alpine.js 3 · Vanilla HTML/CSS · In-memory search/filter/pagination · Flask API integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Alpine.js via CDN permès.
- **D-02:** Paginació clàssica. 50 resultats per pàgina. Botons Anterior / 1 2 3 ... N / Següent.
- **D-03:** Fetch únic al carregar → array JS en memòria → filtratge en memòria → renderitzar només les files de la pàgina activa.
- **D-04:** Alpine.js per a la reactivitat.
- **D-05:** Disseny funcional i net. Fons blanc/gris clar, tipografia del sistema, colors mínims.
- **D-06:** Estructura: Títol → Barra cerca + dropdowns → Checkbox + comptador → Taula → Paginació.
- **D-07:** Columnes: Denominació | Codi | Família | Grado | Nivell. Observaciones NO es mostra.
- **D-08:** Badge "Pla antic" dins la cel·la Denominació. No columna separada.
- **D-09:** `const API_BASE = 'http://localhost:5000'` al principi del fitxer.
- **D-10:** Loading spinner + text "Carregant dades del catàleg FP..." mentre es carrega.
- **D-11:** 503 → missatge d'avís, sense botó de reintent.
- **D-12:** Estat buit dins la taula, diferenciat de l'error 503.

### Claude's Discretion

- Debounce exacte (recomanat: 200–300ms; UI-SPEC resolcut a 250ms).
- Nombre de botons de pàgina visibles (recomanat 5–7 amb el·lipsis; UI-SPEC resolcut a 7).
- Colors exactes del badge "Pla antic" (UI-SPEC resolcut: #92400e text / #fef3c7 fons).
- Estil exacte del spinner (UI-SPEC resolcut: border-top 3px #2563eb, 32px, 0.8s).

### Deferred Ideas (OUT OF SCOPE)

- Sincronitzar filtres a la URL (query params).
- Botó de reset de tots els filtres.
- Exportació a CSV (V2-02).
- Columna Observaciones.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SRCH-01 | Filtratge en temps real per `denominacion` i `codigo` simultàniament | Getter Alpine.js + pre-normalització NFD + debounce 250ms |
| SRCH-02 | Dropdown Grado (A/B/C/D/E/Tots) | Opcions estàtiques; filtre AND amb resta |
| SRCH-03 | Dropdown Família (valors únics del JSON, dinàmic, ordenat) | `[...new Set(data.map(r=>r.familia))].sort()` post-fetch |
| SRCH-04 | Dropdown Nivell (1/2/3/Tots) | CRÍTICA: 10.027 de 12.374 registres tenen `nivel: null` — filtre per 1/2/3 exclou Grado A i part B/C |
| SRCH-05 | Checkbox "Ocultar pla antic" activat per defecte | `hideOld: true` a `x-data`; 5.130 registres plan_antiguo=true |
| SRCH-06 | Taula amb columnes Denominació, Codi, Família, Grado, Nivell | Taula HTML estàtica amb `x-for` sobre pàgina activa |
| SRCH-07 | Badge "Pla antic" discret a les files `plan_antiguo: true` | `x-show="row.plan_antiguo"` inline dins `<td>` |
| SRCH-08 | Comptador de resultats actualitzat en temps real | `filteredCount` getter sobre `filteredRecords` |
| SRCH-09 | Rendiment fluid (revisat: paginació 50/pàg) | 50 `<tr>` màxim al DOM; filtratge en memòria <5ms |
| SRCH-10 | 503 → missatge informatiu, sense retry | Gestió d'errors al fetch inicial; `state: 'error'` |

</phase_requirements>

---

## Summary

Aquesta fase implementa un únic fitxer `index.html` amb tota la lògica CSS i JS inline. Alpine.js 3.15.11 via CDN proporciona la reactivitat necessària. La decisió clau de rendiment (D-03) és correcta: carregar els 12.374 registres un sol cop (~3,8 MB JSON → ~2,25 MB en memòria), pre-processar strings per a cerca, i renderitzar només 50 files per pàgina.

**Descoberta crítica sobre les dades reals:** 10.027 de 12.374 registres (81%) tenen `nivel: null`. Això inclou tots els registres del Grado A (8.537) i una part de B i C. Si l'usuari filtra per Nivell 1/2/3, els Grados A quedaran exclosos — és el comportament correcte, però el planner ha de saber que el dropdown Nivell no mostrarà "Tots els nivells" de forma uniforme entre Grados.

La pre-normalització NFD dels camps de cerca al moment del fetch (9ms mesurat per 12.374 registres) és la tècnica correcta per evitar recalcular per cada keystroke. Els getters d'Alpine.js no estan en cache (a diferència de Vue computed), de manera que el filtratge s'ha d'optimitzar evitant operacions costoses dins dels getters.

**Recomanació principal:** Usar `Alpine.data('cercador', () => ({...}))` amb el patró `init() { fetch → store → precompute }`, dos getters (`filteredRecords`, `pagedRecords`) i un mètode `buildPagination()`. Els filtres activen un `$watch` o `x-effect` que reseteja a la pàgina 1.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fetch dades del catàleg | Browser/Client | — | Fetch únic al DOMContentLoaded; D-03 |
| Pre-processament (normalització) | Browser/Client | — | Es fa un cop post-fetch, no repetitiu |
| Filtratge en memòria | Browser/Client | — | Array.filter() sobre allRecords; sense API calls |
| Paginació (càlcul de pàgina) | Browser/Client | — | Slice de filteredRecords; DOM limitat a 50 tr |
| Renderització reactiva | Browser/Client (Alpine.js) | — | x-for sobre pagedRecords |
| Dades (ofertes.json) | API / Backend (Flask) | — | GET /api/ofertes → array JSON directe |
| Servei static HTML | CDN / Static (nginx CloudPanel) | — | En producció; dev: obert directament al browser |
| CORS | API / Backend | — | flask-cors ja configurat (API-08 completat) |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Alpine.js | 3.15.11 | Reactivitat declarativa, filtratge, paginació | D-01 locked; CDN via jsDelivr |

**Cap altra dependència frontend.** Tot és HTML/CSS/JS vanilla. [VERIFIED: npm registry — `npm view alpinejs version` → 3.15.11]

### CDN URL Recomanat

```html
<!-- Pinned version (producció) -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"></script>

<!-- Floating (dev, sempre latest 3.x) -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

La UI-SPEC utilitza `@3.x.x`. Per producció, millor pinnar a `@3.15.11`. [VERIFIED: alpinejs.dev/essentials/installation]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alpine.js | Vanilla JS pur | Més codi; Alpine simplifica reactivitat sense framework pesant |
| Alpine.js getter | $watch + cached array | Getter té rendiment acceptable per 50 rows; $watch útil si cal evitar recàlcul repetit |

---

## Architecture Patterns

### System Architecture Diagram

```
DOMContentLoaded
      │
      ▼
fetch(API_BASE + '/api/ofertes')
      │
   200 OK              503 / Error xarxa
      │                      │
      ▼                      ▼
allRecords[]          state = 'error'
(12.374 objs)         → mostra error banner
      │
      ▼
Pre-processa:
  _normDen, _normCod per cada registre
  families[] (29 úniques, ordenades)
      │
      ▼
state = 'ready'
      │
      ┌──────────────────────────────┐
      │   Canvis de filtre (usuari)  │
      │  search / grado / familia /  │
      │  nivel / hideOld             │
      └──────────────┬───────────────┘
                     │ (debounce 250ms per text)
                     ▼
           filteredRecords (getter)
           Array.filter() sobre allRecords
           Lògica AND: tots els filtres actius
                     │
                     ▼
           currentPage reset a 1
                     │
                     ▼
           pagedRecords (getter)
           filteredRecords.slice(start, end)
           Màx 50 elements
                     │
                     ▼
           x-for sobre pagedRecords
           Màx 50 <tr> al DOM
                     │
                     ▼
           buildPagination()
           Algorisme ellipsis (delta=2, 7 botons)
```

### Recommended Project Structure

```
fp-cercador/frontend/
  index.html    — HTML + <style> inline + <script> inline (ÚNIC FITXER)
  admin.html    — NO TOCAR (Fase 6)
```

### Pattern 1: Alpine.data amb init() async

**Què:** Registrar el component amb `Alpine.data()` al bloc `<script>` abans que Alpine es carregui.
**Quan usar:** Component d'una sola pàgina amb fetch inicial i estat complex.

```javascript
// Source: https://context7.com/alpinejs/alpine/llms.txt (Alpine.data pattern)
document.addEventListener('alpine:init', () => {
  Alpine.data('cercador', () => ({
    // --- Estat ---
    state: 'loading',   // 'loading' | 'ready' | 'error'
    allRecords: [],
    families: [],

    // --- Filtres ---
    search: '',
    filterGrado: '',
    filterFamilia: '',
    filterNivel: '',
    hideOld: true,      // SRCH-05: activat per defecte

    // --- Paginació ---
    currentPage: 1,
    pageSize: 50,

    // --- Init ---
    async init() {
      try {
        const res = await fetch(API_BASE + '/api/ofertes');
        if (!res.ok) { this.state = 'error'; return; }
        const data = await res.json();

        // Pre-processa per cerca accent-insensible (9ms mesurat)
        this.allRecords = data.map(r => ({
          ...r,
          _normDen: (r.denominacion || '').normalize('NFD')
                      .replace(/[\u0300-\u036f]/g, '').toLowerCase(),
          _normCod: (r.codigo || '').normalize('NFD')
                      .replace(/[\u0300-\u036f]/g, '').toLowerCase(),
        }));

        // Construeix llista de famílies una sola vegada
        this.families = [...new Set(data.map(r => r.familia))].sort();
        this.state = 'ready';
      } catch (e) {
        this.state = 'error';
      }
    },

    // --- Getters (computed no cachejats) ---
    get filteredRecords() {
      const q = this.search.normalize('NFD')
                  .replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
      return this.allRecords.filter(r => {
        if (this.hideOld && r.plan_antiguo) return false;
        if (this.filterGrado && r.grado !== this.filterGrado) return false;
        if (this.filterFamilia && r.familia !== this.filterFamilia) return false;
        if (this.filterNivel && r.nivel !== parseInt(this.filterNivel)) return false;
        if (q && !r._normDen.includes(q) && !r._normCod.includes(q)) return false;
        return true;
      });
    },

    get filteredCount() {
      return this.filteredRecords.length;
    },

    get pagedRecords() {
      const start = (this.currentPage - 1) * this.pageSize;
      return this.filteredRecords.slice(start, start + this.pageSize);
    },

    get totalPages() {
      return Math.ceil(this.filteredRecords.length / this.pageSize);
    },

    // --- Paginació ---
    buildPagination() {
      // Algorisme ellipsis (delta=2): [VERIFIED: gist.github.com/kottenator/9d936eb3e4e3c3e02598]
      const c = this.currentPage, m = this.totalPages, delta = 2;
      if (m <= 1) return [];
      const left = c - delta, right = c + delta + 1;
      const range = [], result = [];
      let l;
      for (let i = 1; i <= m; i++) {
        if (i === 1 || i === m || (i >= left && i < right)) range.push(i);
      }
      for (const i of range) {
        if (l) {
          if (i - l === 2) result.push({ type: 'page', n: l + 1 });
          else if (i - l !== 1) result.push({ type: 'ellipsis' });
        }
        result.push({ type: 'page', n: i });
        l = i;
      }
      return result;
    },

    goToPage(n) {
      if (n < 1 || n > this.totalPages) return;
      this.currentPage = n;
      // Scroll al top de la taula
      document.getElementById('results-table')?.scrollIntoView({ behavior: 'smooth' });
    },

    // Reset pàgina quan canvia qualsevol filtre
    resetPage() { this.currentPage = 1; },
  }));
});
```

### Pattern 2: Reset de pàgina en canvi de filtre

**Què:** Qualsevol canvi de filtre ha de tornar a la pàgina 1.
**Com:** Usar `@change="resetPage()"` o `@input="resetPage()"` als controls de filtre, a més del debounce per al text.

```html
<!-- Source: alpinejs.dev/directives/on + alpinejs.dev/directives/model -->
<!-- Cerca amb debounce 250ms + reset de pàgina -->
<input
  type="search"
  x-model.debounce.250ms="search"
  @input="resetPage()"
  placeholder="Cerca per denominació o codi..."
>

<!-- Dropdowns: reset immediat -->
<select x-model="filterGrado" @change="resetPage()">...</select>
<select x-model="filterFamilia" @change="resetPage()">...</select>
<select x-model="filterNivel" @change="resetPage()">...</select>

<!-- Checkbox: reset immediat -->
<input type="checkbox" x-model="hideOld" @change="resetPage()">
```

### Pattern 3: Estat de càrrega amb x-show

**Què:** Mostrar/ocultar seccions segons `state`.
**Quan usar:** Tres estats mútuament excloents: loading, error, ready.

```html
<!-- Source: context7.com/alpinejs/alpine/llms.txt -->
<div x-data="cercador">
  <!-- Loading state (D-10) -->
  <div x-show="state === 'loading'" class="loading-state" role="status">
    <div class="spinner"></div>
    <p>Carregant dades del catàleg FP...</p>
  </div>

  <!-- Error state 503 (D-11) -->
  <div x-show="state === 'error'" class="error-state" role="status">
    <p>⚠️ Les dades del catàleg no estan disponibles.
       Contacteu l'administrador del sistema.</p>
  </div>

  <!-- Ready state -->
  <div x-show="state === 'ready'">
    <!-- Filtres, taula, paginació -->
  </div>
</div>
```

### Pattern 4: Família dropdown dinàmic

**Quan usar:** Post-fetch, les 29 famílies úniques es poblen a l'array `families[]`.

```html
<!-- Source: alpinejs.dev/directives/for -->
<select x-model="filterFamilia" @change="resetPage()">
  <option value="">Totes les famílies</option>
  <template x-for="fam in families" :key="fam">
    <option :value="fam" x-text="fam"></option>
  </template>
</select>
```

### Pattern 5: Badge "Pla antic" inline (D-08)

```html
<!-- Source: CONTEXT.md D-08 + UI-SPEC.md Component Inventory -->
<td>
  <span x-text="row.denominacion"></span>
  <span x-show="row.plan_antiguo" class="badge-old">Pla antic</span>
</td>
```

### Pattern 6: Nivell null — filtratge correcte

**CRÍTICA:** 10.027 registres (Grado A complet + part B/C) tenen `nivel: null`. El filtre de Nivell ha de comparar correctament:

```javascript
// CORRECTE: parseInt converteix '1' -> 1, compara amb null -> false (exclou)
if (this.filterNivel && r.nivel !== parseInt(this.filterNivel)) return false;

// INCORRECTE: r.nivel != this.filterNivel  (coercions de tipus imprevisibles)
```

Quan l'usuari filtra per Nivell 1/2/3, els Grados A queden exclosos automàticament. Això és comportament correcte — els Grados A no tenen nivell assignat al dataset del ministeri.

### Anti-Patterns to Avoid

- **Mai renderitzar els 12.374 `<tr>` al DOM:** `x-for` ha d'iterar sobre `pagedRecords` (50 màx), no sobre `filteredRecords`. [VERIFIED: D-03]
- **No usar `x-for` sense `:key`:** Alpine recomana especificar clau per a llistes que canvien. Usar `:key="row.id"`.
- **No normalitzar dins del getter:** Pre-normalitzar a l'`init()` (9ms total). Normalitzar al getter recalcularia per cada keystroke × 12.374.
- **No usar `disabled` attr en botons de paginació per accessibilitat:** Usar `aria-disabled="true"` + estil visual per mantenir el focus. [CITED: WCAG 2.1 accessible focus management]
- **No fer múltiples `fetch` per a filtres:** D-03 és explícit — un únic fetch al carregar.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Debounce d'input | setTimeout manual | `x-model.debounce.250ms` | Built-in Alpine.js; correcte per cancelació |
| Normalització accent-insensible | Taules de caràcters manuals | `String.normalize('NFD').replace(/[\u0300-\u036f]/g,'')` | API nativa ES6, browser-suportada |
| Spinner CSS | Library d'animació | CSS `@keyframes spin` + `border-top` | 5 línies CSS; zero dependències |
| Ellipsis de paginació | Algorisme propi | Algorisme kottenator (verificat, 15 línies) | Edge cases coberts: inici, mig, final |
| Fetch amb gestió 503 | XMLHttpRequest | `fetch()` natiu + `res.ok` check | `res.ok` fals per 503; natiu i simple |

**Key insight:** Per un fitxer HTML únic sense build step, la millor solució és sempre la que té menys dependències externes. Alpine.js via CDN és suficient per a tota la reactivitat necessària.

---

## Common Pitfalls

### Pitfall 1: Getters Alpine.js NO estan en cache

**Que va malament:** `filteredRecords` es recalcula cada vegada que s'accedeix a la propietat al template, no solo quan canvien els filtres.
**Per que passa:** Alpine.js getters son JavaScript getters natius — no son Vue computed properties. [CITED: alpinejs.dev/directives/data — nota sobre getters]
**Com evitar:** (1) Assegurar que el getter és ràpid: `Array.filter()` sobre 12.374 objectes amb condicions simples = <5ms. (2) Pre-normalitzar strings a `init()`. (3) `pagedRecords` accedeix a `filteredRecords` una sola vegada (slice). Si el rendiment empitjora, usar `$watch` + array cachetjat.
**Senyal d'alerta:** Lag visible en escriure. Mesurar amb `performance.now()` al getter.

### Pitfall 2: Comparació de `nivel` amb tipus mixtos

**Que va malament:** `r.nivel !== this.filterNivel` compara `null` o `1` (number) amb `'1'` (string del `<select>`).
**Per que passa:** Els valors dels `<select>` són sempre strings a JS.
**Com evitar:** `parseInt(this.filterNivel)` al filtre. Quan `filterNivel` és `''` (Tots), la condició `if (this.filterNivel && ...)` el salta.

### Pitfall 3: `plan_antiguo` és booleà, no string

**Que va malament:** `r.plan_antiguo === 'true'` sempre fals.
**Per que passa:** El JSON retorna `plan_antiguo: false` com a booleà, no com a string.
**Com evitar:** Comparar directament: `if (this.hideOld && r.plan_antiguo)`.

### Pitfall 4: Paginació no es reseteja al canviar filtres

**Que va malament:** L'usuari va a la pàgina 10, canvia un filtre, i veu "cap resultat" perquè la paginació intenta mostrar la pàgina 10 d'un conjunt filtrat de 20 registres.
**Per que passa:** `currentPage` es manté independent dels filtres.
**Com evitar:** `@input="resetPage()"` i `@change="resetPage()"` a tots els controls de filtre.

### Pitfall 5: `defer` a Alpine.js CDN és obligatori

**Que va malament:** Alpine.js inicialitza el DOM abans que el `<script>` amb `Alpine.data('cercador', ...)` s'executi — el component no es troba.
**Per que passa:** Sense `defer`, Alpine s'executa immediatament a l'`<head>` i busca components al DOM.
**Com evitar:** El bloc `<script>` amb `Alpine.data()` ha d'anar ABANS del tag d'Alpine CDN, o usar el patró `document.addEventListener('alpine:init', () => {...})`.

```html
<!-- CORRECTE: script propi primer, alpine CDN amb defer -->
<script>
  const API_BASE = 'http://localhost:5000';
  document.addEventListener('alpine:init', () => {
    Alpine.data('cercador', () => ({...}));
  });
</script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"></script>
```

### Pitfall 6: `nivel: null` als Grados A (i part B/C)

**Que va malament:** Filtre per Nivell 1/2/3 sembla "trencat" per als registres Grado A.
**Per que passa:** Grado A (8.537 registres) no té nivell al dataset del ministeri — `nivel: null` és el valor correcte.
**Com evitar:** El comportament és correcte per disseny. Documentar a l'especificació que filtrar per Nivell exclou els Grados A.

---

## Code Examples

### Algorisme de paginació amb ellipsis

```javascript
// Source: https://gist.github.com/kottenator/9d936eb3e4e3c3e02598 (VERIFIED)
// Retorna array de {type: 'page', n: N} | {type: 'ellipsis'}
buildPagination() {
  const c = this.currentPage, m = this.totalPages, delta = 2;
  if (m <= 1) return [];
  const left = c - delta, right = c + delta + 1;
  const range = [], result = [];
  let l;
  for (let i = 1; i <= m; i++) {
    if (i === 1 || i === m || (i >= left && i < right)) range.push(i);
  }
  for (const i of range) {
    if (l) {
      if (i - l === 2) result.push({ type: 'page', n: l + 1 });
      else if (i - l !== 1) result.push({ type: 'ellipsis' });
    }
    result.push({ type: 'page', n: i });
    l = i;
  }
  return result;
}
```

**Exemples verificats** (248 pàgines totals amb tots els registres):

| Pàgina actual | Resultat |
|---|---|
| 1 | `[1, 2, 3, ..., 248]` |
| 5 | `[1, 2, 3, 4, 5, 6, 7, ..., 248]` |
| 124 | `[1, ..., 122, 123, 124, 125, 126, ..., 248]` |
| 248 | `[1, ..., 246, 247, 248]` |

### Pre-normalització NFD (mesurat: 9ms per 12.374 registres)

```javascript
// Source: MDN Web Docs — String.prototype.normalize() [CITED]
// Executar UNA SOLA VEGADA a init(), NO dins del getter
this.allRecords = data.map(r => ({
  ...r,
  _normDen: (r.denominacion || '').normalize('NFD')
              .replace(/[\u0300-\u036f]/g, '').toLowerCase(),
  _normCod: (r.codigo || '').normalize('NFD')
              .replace(/[\u0300-\u036f]/g, '').toLowerCase(),
}));
```

### Spinner CSS (zero dependències)

```css
/* Source: UI-SPEC.md Component Inventory — Loading State */
@keyframes spin {
  to { transform: rotate(360deg); }
}
.spinner {
  border: 3px solid #d1d5db;
  border-top-color: #2563eb;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  animation: spin 0.8s linear infinite;
}
```

### System font stack

```css
/* Source: UI-SPEC.md Design System */
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               Helvetica, Arial, sans-serif;
  font-size: 14px;
  color: #111827;
  background: #ffffff;
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Alpine.js 2.x (CDN URL diferent) | Alpine.js 3.x (`cdn.min.js`) | 2021 | API diferent — x-data, x-for, etc. incompatibles entre v2 i v3 |
| Renderitzar tot el DOM, ocultar amb CSS | Renderitzar només la pàgina activa (D-03) | — | Rendiment crític per a 12.374 registres |
| `String.indexOf` per cerca | `.normalize('NFD').replace(...).includes()` | ES6+ | Cerca accent-insensible per als noms FP espanyols |

**Deprecated/outdated:**
- Alpine.js `@2.x.x`: API diferent, no compatible. Sempre usar `@3.x.x` o `@3.15.11`.

---

## Data Insights (Verificat des del JSON real)

| Mètrica | Valor | Impacte al frontend |
|---------|-------|---------------------|
| Total registres | 12.374 | Fetch inicial ~3,8 MB JSON |
| Registres `plan_antiguo: true` | 5.130 (41%) | Checkbox actiu per defecte n'amaga molts |
| Registres visibles per defecte (hideOld=true) | 7.244 | → 145 pàgines inicials |
| Registres visibles (hideOld=false) | 12.374 | → 248 pàgines màxim |
| Registres amb `nivel: null` | 10.027 (81%) | Filtre Nivell exclou Grado A complet |
| Famílies úniques | 29 | Dropdown Família: 30 opcions (+ "Totes") |
| Grados | 5 (A,B,C,D,E) | Dropdown Grado: 6 opcions (+ "Tots") |
| Nivells possibles | 1, 2, 3, null | Dropdown Nivell: 4 opcions (+ "Tots") |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Flask backend (dev) | ✓ | 3.13.0 | — |
| Node.js | Dev tools (opcional) | ✓ | 22.17.0 | — |
| Flask backend | `GET /api/ofertes` | ✓ | Fase 4 completa | Fer mock JSON local |
| `ofertes.json` | Dades en producció | ✓ | 3,8 MB, 12.374 registres | Spinner fins que estigui disponible |
| CDN jsDelivr | Alpine.js | ✓ (xarxa) | 3.15.11 | [ASSUMED] Cap fallback offline en V1 |

**Dependències crítiques:**
- La backend Flask ha d'estar en marxa per a la funcionalitat completa. Per a proves de la UI sense backend, es pot usar un mock JSON local temporal (no inclòs en abast de la fase).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Cap framework de tests per al frontend (HTML estàtic + CDN Alpine.js) |
| Config file | N/A — tests manuals al navegador |
| Quick run command | Obrir `fp-cercador/frontend/index.html` al navegador amb Flask corrent |
| Full suite command | Checklist manual (veure baix) |

> Nota: El projecte usa pytest per al backend. El frontend no té framework de tests automatitzats configurats. Les verificacions de la fase 5 son manuals al navegador.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Command / Procediment | Automatitzable |
|--------|----------|-----------|----------------------|----------------|
| SRCH-01 | Cerca per text filtra `denominacion` i `codigo` | Manual | Escriure "ADG" al camp cerca; verificar que filtra per codi | No (UI) |
| SRCH-01 | Cerca accent-insensible: "administracio" = "administración" | Manual | Escriure "administracio" (sense accent); verificar resultats | No (UI) |
| SRCH-02 | Dropdown Grado filtra correctament | Manual | Seleccionar "B"; verificar que tots els resultats son Grado B | No |
| SRCH-03 | Dropdown Família pobla 29 opcions dinàmicament | Manual | Obrir dropdown; comptar opcions (30 incl. "Totes") | No |
| SRCH-04 | Dropdown Nivell: filtre per 1/2/3 exclou Grado A (nivel null) | Manual | Seleccionar Grado=Tots, Nivell=1; verificar 0 Grado A | No |
| SRCH-05 | Checkbox activat per defecte; oculta 5.130 registres | Manual | Carregar pàgina; comptador ha de mostrar 7.244 (no 12.374) | No |
| SRCH-06 | Taula mostra 5 columnes en ordre correcte | Manual | Inspecció visual de les capçaleres | No |
| SRCH-07 | Badge "Pla antic" apareix a files `plan_antiguo: true` | Manual | Desactivar checkbox hideOld; verificar badges | No |
| SRCH-08 | Comptador s'actualitza en temps real | Manual | Escriure text; verificar comptador canvia | No |
| SRCH-09 | Màx 50 files al DOM simultàniament | Manual | DevTools Elements; comptar `<tr>` a `<tbody>` | Sí (DevTools) |
| SRCH-10 | 503 → banner error, sense retry | Manual | Aturar Flask; recarregar; verificar banner | No |
| D-02 | Paginació: Anterior/Pàgines/Següent | Manual | Navegar pàgines; verificar ellipsis i botons disabled | No |
| D-12 | Estat buit dins la taula | Manual | Escriure "ZZZZZZZ"; verificar missatge dins taula | No |

### Checklist de Validació Manual

```
[ ] Carrega inicial: spinner apareix → desapareix → 7.244 resultats (hideOld=true)
[ ] Cerca "ADG": filtra per codi correctament
[ ] Cerca "administracio" (sense accent): troba "Administración"
[ ] Grado=B: tots els resultats mostren "B" a la columna Grado
[ ] Família=Sanidad: tots els resultats son família Sanidad
[ ] Nivell=1: cap resultat Grado A visible
[ ] hideOld desactivat: 12.374 resultats, badges "Pla antic" visibles
[ ] Pàgina 1: "Anterior" disabled; pàgina última: "Següent" disabled
[ ] Paginació ellipsis: anar pàgina 124 de 145; verificar "1 ... 122 123 [124] 125 126 ... 145"
[ ] Filtres combinats: Grado=C + Família=Sanidad + Nivell=2 → resultats correctes
[ ] Canvi filtre → reseteja a pàgina 1
[ ] Flask aturat → banner 503, sense botó retry
[ ] Cerca sense resultats → missatge dins taula (no banner d'error)
[ ] DevTools Elements: <tbody> mai té més de 50 <tr>
[ ] DevTools Network: un únic fetch a /api/ofertes per sessió
```

### Wave 0 Gaps

No hi ha framework de tests frontend a configurar. La fase comença directament amb la implementació de `index.html`.

---

## Deployment Notes

**Entorn de desenvolupament:**
- Obrir `index.html` directament al browser (file:// o HTTP simple).
- `API_BASE = 'http://localhost:5000'` — Flask corrent al port 5000.
- CORS ja habilitat per a totes les origins (flask-cors, API-08).

**Producció (CloudPanel / nginx):**
- `index.html` servit per nginx com a fitxer estàtic (no requereix Flask per al frontend).
- `API_BASE` s'haurà de canviar a la URL pública de l'API (ex: `https://api.exemple.com`) — D-09 preveu aquest canvi com a modificació d'una sola línia.
- Flask en producció: CloudPanel pot configurar Python app amb uWSGI + nginx reverse proxy. [CITED: cloudpanel.io/docs/v2/python/deployment/uwsgi/]
- CORS en producció: si nginx serveix el frontend i Flask serveix l'API en ports/dominis separats, CORS resta necessari. L'actual `CORS(app)` sense restriccions cobreix tots els casos, però per producció es pot restringir a l'origen del frontend. [ASSUMED — política CORS de producció no especificada]

---

## Open Questions

1. **URL de producció de l'API**
   - Que sabem: `API_BASE = 'http://localhost:5000'` per a dev (D-09).
   - Que no és clar: quina serà l'URL de l'API en producció (mateix domini?, subdomini?, port diferent?).
   - Recomanació: Deixar-ho com a `localhost:5000` ara. La Fase 6 o el desplegament resoldrà el canvi.

2. **Comportament del dropdown Nivell amb Grado A**
   - Que sabem: Grado A (8.537 reg.) té `nivel: null`. Filtrar Nivell=1 exclouria tots.
   - Que no és clar: Si l'usuari espera veure Grado A quan filtra per Nivell=1 (relació lògica inexistent al dataset).
   - Recomanació: El comportament actual (exclusió) és correcte. Opcionalment es podria afegir un text "Els Grados A no tienen nivell assignat" com a tooltip o nota al peu — **fora d'abast d'aquesta fase**.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Flask API corre al port 5000 en dev (no 5001 com a `__main__`) | Standard Stack | Fetch fallaria; canviar `API_BASE` |
| A2 | CDN jsDelivr disponible en xarxa de l'usuari final | Environment Availability | Pàgina sense Alpine.js; cal fallback o self-host |
| A3 | CORS de producció no requereix restricció d'origen específica | Deployment Notes | Pot caldre configurar `origins=` a flask-cors |

> Nota sobre A1: `app.py` inicia amb `port=5001` a `__main__`, però Flask per defecte usa 5000. En producció via gunicorn/uwsgi el port és configurable. Verificar el port real en execució.

---

## Security Domain

> `security_enforcement` no és explícitament `false` al config — s'inclou la secció.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Frontend públic sense auth |
| V3 Session Management | No | Sense sessions al frontend del cercador |
| V4 Access Control | No | Cerca pública; admin a Fase 6 |
| V5 Input Validation | Sí (parcial) | Input de cerca: normalitzat, no enviat al servidor |
| V6 Cryptography | No | Sense dades sensibles al frontend |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via denominacion | Tampering | Alpine.js `x-text` escapa HTML automàticament; NO usar `x-html` |
| Data injection via API | Tampering | JSON parse nativa; no `eval()`; cap interpolació d'HTML manual |

**Nota crítica:** Usar `x-text` (no `x-html`) per renderitzar tots els camps del JSON. Alpine.js escapa el contingut automàticament quan s'usa `x-text`. [CITED: alpinejs.dev/directives/text]

---

## Sources

### Primary (HIGH confidence)

- `npm view alpinejs version` → 3.15.11 [VERIFIED: npm registry, 2026-04-19]
- Context7 `/alpinejs/alpine` — patrons `x-data`, `Alpine.data()`, `x-init`, `x-model.debounce`, `$watch`, `x-for`, `x-text` [VERIFIED: Context7]
- `alpinejs.dev/essentials/installation` — CDN URL recomanat [CITED]
- Inspecció directa de `ofertes.json` (3,8 MB, 12.374 registres) [VERIFIED: Bash tool, 2026-04-19]
- Algorisme ellipsis [VERIFIED: gist.github.com/kottenator/9d936eb3e4e3c3e02598]
- Benchmark pre-normalització: 9ms per 12.374 registres [VERIFIED: Node.js benchmark, 2026-04-19]

### Secondary (MEDIUM confidence)

- `cloudpanel.io/docs/v2/python/deployment/uwsgi/` — Desplegament Flask en CloudPanel [CITED]
- MDN Web Docs — `String.prototype.normalize()` [CITED]
- `alpinejs.dev/directives/data` — Nota que els getters NO estan en cache [CITED]
- raymondcamden.com/2022/05/02 — Patró de paginació amb Alpine.js [CITED]

### Tertiary (LOW confidence)

- Comportament CORS en producció (domini únic vs. separats) [ASSUMED]

---

## Metadata

**Confidence breakdown:**

- Standard stack (Alpine.js 3.15.11): HIGH — verificat npm registry
- Architecture (fetch→filter→paginate): HIGH — verificat amb dades reals del JSON
- Data insights (nivel null, plan_antiguo counts): HIGH — verificat inspeccionant ofertes.json
- Pitfalls (getters no cached, tipus null): HIGH — verificat Context7 + docs
- Deployment producció: MEDIUM — CloudPanel docs citats, CORS policy assumida

**Research date:** 2026-04-19
**Valid until:** 2026-07-19 (Alpine.js 3.x estable; 90 dies)
