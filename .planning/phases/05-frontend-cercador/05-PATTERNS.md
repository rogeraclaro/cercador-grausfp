# Phase 5: Frontend — Cercador - Pattern Map

**Mapped:** 2026-04-19
**Files analyzed:** 1 (index.html — implementació completa)
**Analogs found:** 0 / 1 — cap analog directe al codebase (stub buit); patrons extrets dels documents de research verificats i del codebase backend

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `fp-cercador/frontend/index.html` | component (SPA inline) | request-response + in-memory filter | cap analog frontend existent | no-analog — usar patrons de RESEARCH.md |
| `fp-cercador/frontend/admin.html` | stub | — | admin.html actual (stub buit) | no tocar (Fase 6) |

---

## Pattern Assignments

### `fp-cercador/frontend/index.html` (SPA inline, request-response + in-memory filter)

**Analog:** cap — primer fitxer frontend del projecte. Patrons extrets de RESEARCH.md (verificats contra dades reals) i del backend `app.py` (per al format de resposta de l'API).

---

#### API — Format de resposta de `GET /api/ofertes`

**Font:** `fp-cercador/backend/app.py` línies 75–86

```python
@app.route("/api/ofertes")
def get_ofertes():
    if not os.path.exists(DATA_PATH):
        return jsonify({"error": "Data not available. Run /api/admin/refresh first."}), 503
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("ofertes.json is corrupt: %s", exc)
        return jsonify({"error": "Data file is corrupt. Run /api/admin/refresh."}), 503
    return jsonify(data), 200
```

**Implicacions per al frontend:**
- `200 OK` → `res.json()` retorna **array directe** (no wrapping object): `[{...}, {...}, ...]`
- `503` → `res.ok === false`; `res.json()` retorna `{"error": "..."}` (no usar el missatge al frontend)
- Detectar errors: `if (!res.ok) { this.state = 'error'; return; }` — cobreix tant 503 com errors de xarxa
- Camp `plan_antiguo`: booleà Python → booleà JSON (`true`/`false`), NO string
- Camp `nivel`: pot ser `null` (10.027 de 12.374 registres, tots els Grado A)
- Camp `grado`: string `"A"` / `"B"` / `"C"` / `"D"` / `"E"`

**Schema real de cada registre (verificat del JSON):**
```json
{
  "id": 1,
  "codigo": "AFD_A_3003_01",
  "denominacion": "Clasificación de tareas administrativas",
  "observaciones": "...",
  "familia": "Actividades Físicas y Deportivas",
  "nivel": null,
  "plan_antiguo": false,
  "grado": "A"
}
```

---

#### Estructura HTML del document

**Font:** `fp-cercador/frontend/index.html` línies 1–10 (stub) + UI-SPEC.md Component Inventory

El stub confirma: `lang="ca"`, `charset="UTF-8"`, títol en castellà ("Cercador FP España"). El pattern a seguir:

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cercador FP Espanya</title>
  <style>
    /* Tot el CSS inline aquí */
  </style>
  <!-- Script propi PRIMER (Alpine.data ha d'estar registrat abans que Alpine s'inicialitzi) -->
  <script>
    const API_BASE = 'http://localhost:5000';  /* D-09: única línia a canviar per producció */
    document.addEventListener('alpine:init', () => {
      Alpine.data('cercador', () => ({ /* ... */ }));
    });
  </script>
  <!-- Alpine CDN amb defer SEMPRE DESPRÉS del script propi (Pitfall 5 de RESEARCH.md) -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"></script>
</head>
<body>
  <div class="page-container" x-data="cercador">
    <!-- Contingut aquí -->
  </div>
</body>
</html>
```

**Regla crítica d'ordre:** El `<script>` amb `Alpine.data('cercador', ...)` ha d'anar **abans** del tag CDN d'Alpine. Si Alpine es carrega primer (sense `defer`), busca components al DOM i no troba `cercador`. Veure Pitfall 5 a RESEARCH.md.

---

#### Patró Alpine.data — Component complet

**Font:** RESEARCH.md Pattern 1 (verificat contra dades reals de 12.374 registres)

```javascript
document.addEventListener('alpine:init', () => {
  Alpine.data('cercador', () => ({
    // --- Estat del cicle de vida ---
    state: 'loading',   // 'loading' | 'ready' | 'error'
    allRecords: [],
    families: [],

    // --- Filtres (D-06) ---
    search: '',
    filterGrado: '',
    filterFamilia: '',
    filterNivel: '',
    hideOld: true,      // SRCH-05: activat per defecte

    // --- Paginació (D-02) ---
    currentPage: 1,
    pageSize: 50,

    // --- Init: fetch únic al carregar (D-03) ---
    async init() {
      try {
        const res = await fetch(API_BASE + '/api/ofertes');
        if (!res.ok) { this.state = 'error'; return; }   // cobreix 503 + errors xarxa
        const data = await res.json();

        // Pre-normalització NFD: executar UNA SOLA VEGADA aquí (9ms total mesurat)
        // NO normalitzar dins del getter — es recalcularia per keystroke × 12.374
        this.allRecords = data.map(r => ({
          ...r,
          _normDen: (r.denominacion || '').normalize('NFD')
                      .replace(/[\u0300-\u036f]/g, '').toLowerCase(),
          _normCod: (r.codigo || '').normalize('NFD')
                      .replace(/[\u0300-\u036f]/g, '').toLowerCase(),
        }));

        // Famílies úniques ordenades: es construeix UNA SOLA VEGADA post-fetch
        this.families = [...new Set(data.map(r => r.familia))].sort();
        this.state = 'ready';
      } catch (e) {
        this.state = 'error';
      }
    },

    // --- Getters (NO estan en cache — Pitfall 1 de RESEARCH.md) ---
    get filteredRecords() {
      const q = this.search.normalize('NFD')
                  .replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
      return this.allRecords.filter(r => {
        if (this.hideOld && r.plan_antiguo) return false;           // booleà directe (Pitfall 3)
        if (this.filterGrado && r.grado !== this.filterGrado) return false;
        if (this.filterFamilia && r.familia !== this.filterFamilia) return false;
        if (this.filterNivel && r.nivel !== parseInt(this.filterNivel)) return false;  // parseInt (Pitfall 2)
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

    // --- Paginació amb ellipsis ---
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
    },

    goToPage(n) {
      if (n < 1 || n > this.totalPages) return;
      this.currentPage = n;
      document.getElementById('results-table')?.scrollIntoView({ behavior: 'smooth' });
    },

    resetPage() { this.currentPage = 1; },
  }));
});
```

---

#### Patró de controls de filtre amb reset de pàgina

**Font:** RESEARCH.md Pattern 2

```html
<!-- Cerca amb debounce 250ms (built-in Alpine — NO setTimeout manual) -->
<input
  type="search"
  id="search"
  x-model.debounce.250ms="search"
  @input="resetPage()"
  placeholder="Cerca per denominació o codi..."
  autocomplete="off"
>

<!-- Dropdowns: reset immediat en canviar -->
<select id="filter-grado" x-model="filterGrado" @change="resetPage()">
  <option value="">Tots els grados</option>
  <option value="A">A</option>
  <option value="B">B</option>
  <option value="C">C</option>
  <option value="D">D</option>
  <option value="E">E</option>
</select>

<!-- Família: opcions dinàmiques des de this.families[] -->
<select id="filter-familia" x-model="filterFamilia" @change="resetPage()">
  <option value="">Totes les famílies</option>
  <template x-for="fam in families" :key="fam">
    <option :value="fam" x-text="fam"></option>
  </template>
</select>

<!-- Nivell: opcions estàtiques (1/2/3 o null per als Grado A) -->
<select id="filter-nivel" x-model="filterNivel" @change="resetPage()">
  <option value="">Tots els nivells</option>
  <option value="1">1</option>
  <option value="2">2</option>
  <option value="3">3</option>
</select>

<!-- Checkbox: activat per defecte (hideOld: true a x-data) -->
<label for="hide-old">
  <input type="checkbox" id="hide-old" x-model="hideOld" @change="resetPage()">
  Ocultar pla antic
</label>
```

---

#### Patró d'estats de càrrega / error / buit

**Font:** RESEARCH.md Pattern 3 + UI-SPEC.md Component Inventory

```html
<!-- Loading (D-10) -->
<div x-show="state === 'loading'" class="loading-state" role="status">
  <div class="spinner"></div>
  <p>Carregant dades del catàleg FP...</p>
</div>

<!-- Error 503 (D-11): sense botó de reintent -->
<div x-show="state === 'error'" class="error-state" role="status">
  <p>⚠️ Les dades del catàleg no estan disponibles.
     Contacteu l'administrador del sistema.</p>
</div>

<!-- Ready: filtres + taula + paginació -->
<div x-show="state === 'ready'">
  <!-- contingut principal -->
</div>
```

---

#### Patró de la taula de resultats (D-07, SRCH-06)

**Font:** UI-SPEC.md Results Table + RESEARCH.md Pattern 5

```html
<table class="results-table" id="results-table">
  <caption class="sr-only">Resultats del cercador FP Espanya</caption>
  <thead>
    <tr>
      <th scope="col">Denominació</th>
      <th scope="col">Codi</th>
      <th scope="col">Família</th>
      <th scope="col">Grado</th>
      <th scope="col">Nivell</th>
    </tr>
  </thead>
  <tbody>
    <!-- Estat buit: dins la taula, diferenciat del banner 503 (D-12) -->
    <template x-if="filteredCount === 0 && state === 'ready'">
      <tr class="empty-row">
        <td colspan="5">Cap resultat coincideix amb els filtres aplicats.</td>
      </tr>
    </template>

    <!-- Files de dades: x-for sobre pagedRecords (màx 50 <tr> al DOM — D-03, SRCH-09) -->
    <!-- CRÍTIC: iterar pagedRecords, NO filteredRecords -->
    <template x-for="row in pagedRecords" :key="row.id">
      <tr>
        <td>
          <!-- x-text escapa HTML automàticament — NO usar x-html (seguretat XSS) -->
          <span x-text="row.denominacion"></span>
          <!-- Badge "Pla antic" inline (D-08): no columna separada, no color de fila -->
          <span x-show="row.plan_antiguo" class="badge-old">Pla antic</span>
        </td>
        <td x-text="row.codigo"></td>
        <td x-text="row.familia"></td>
        <td x-text="row.grado"></td>
        <td x-text="row.nivel ?? '—'"></td>
      </tr>
    </template>
  </tbody>
</table>
```

**Nota:** `row.nivel ?? '—'` mostra guió per als 10.027 registres amb `nivel: null` (tots els Grado A).

---

#### Patró de paginació (D-02)

**Font:** UI-SPEC.md Pagination + RESEARCH.md Pitfall 4 i Pattern (ellipsis)

```html
<nav class="pagination" aria-label="Paginació de resultats">
  <!-- Anterior: aria-disabled en lloc de disabled per mantenir focus (accessibilitat) -->
  <button
    @click="goToPage(currentPage - 1)"
    :aria-disabled="currentPage === 1"
    :class="{ disabled: currentPage === 1 }"
  >Anterior</button>

  <!-- Botons de pàgina amb ellipsis -->
  <template x-for="item in buildPagination()" :key="JSON.stringify(item)">
    <template x-if="item.type === 'page'">
      <button
        @click="goToPage(item.n)"
        :aria-current="item.n === currentPage ? 'page' : false"
        :aria-label="'Pàgina ' + item.n"
        :class="{ active: item.n === currentPage }"
        x-text="item.n"
      ></button>
    </template>
    <template x-if="item.type === 'ellipsis'">
      <span class="pagination-ellipsis">…</span>
    </template>
  </template>

  <!-- Següent -->
  <button
    @click="goToPage(currentPage + 1)"
    :aria-disabled="currentPage === totalPages"
    :class="{ disabled: currentPage === totalPages }"
  >Següent</button>
</nav>
```

---

#### Patró CSS complet

**Font:** UI-SPEC.md Design System + Color + Typography + Spacing

```css
/* Reset mínim */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* Sistema de tipografia (D-05) */
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               Helvetica, Arial, sans-serif;
  font-size: 14px;       /* body */
  color: #111827;        /* text primary */
  background: #ffffff;   /* dominant */
}

/* Layout contenidor */
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 24px;    /* xl top, lg inline */
}

/* Capçalera */
h1 {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
  margin-bottom: 24px;   /* lg */
}

/* Fila de filtres */
.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;             /* md */
  margin-bottom: 8px;    /* sm */
}

/* Controls (input + select) */
input[type="search"], select {
  padding: 8px 16px;     /* sm vertical, md horizontal */
  border: 1px solid #d1d5db;  /* border */
  border-radius: 4px;
  font-size: 14px;
  background: #ffffff;
  color: #111827;
}
input[type="search"]:focus, select:focus {
  outline: none;
  border-color: #2563eb;       /* accent */
  box-shadow: 0 0 0 2px rgba(37,99,235,0.15);
}
input[type="search"]::placeholder { color: #6b7280; }  /* text muted */

/* Fila comptador + checkbox */
.controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 12px;       /* label */
  font-weight: 600;
  color: #6b7280;        /* text muted */
}

/* Taula */
.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.results-table th {
  background: #f3f4f6;  /* secondary */
  text-align: left;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  border-bottom: 1px solid #d1d5db;
}
.results-table td {
  padding: 8px 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
  min-height: 44px;     /* accessibilitat touch target */
}
.results-table tr:nth-child(even) td { background: #f3f4f6; }  /* zebra */

/* Badge "Pla antic" (D-08) */
.badge-old {
  display: inline-block;
  background: #fef3c7;
  color: #92400e;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 3px;
  margin-left: 6px;
  white-space: nowrap;
}

/* Estat buit dins la taula (D-12) */
.empty-row td {
  text-align: center;
  color: #6b7280;
  padding: 32px;
  font-style: italic;
}

/* Loading (D-10) */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px;
  color: #6b7280;
}
@keyframes spin { to { transform: rotate(360deg); } }
.spinner {
  border: 3px solid #d1d5db;
  border-top-color: #2563eb;
  border-radius: 50%;
  width: 32px;
  height: 32px;
  animation: spin 0.8s linear infinite;
}

/* Error 503 (D-11) */
.error-state {
  padding: 16px;
  background: #fee2e2;
  color: #991b1b;
  border-radius: 4px;
  margin: 16px 0;
}

/* Paginació (D-02) */
.pagination {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 16px;
  padding: 16px 0;
  background: #f3f4f6;
}
.pagination button {
  padding: 6px 12px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #ffffff;
  cursor: pointer;
  font-size: 14px;
  color: #111827;
}
.pagination button.active {
  background: #2563eb;
  color: #ffffff;
  border-color: #2563eb;
}
.pagination button[aria-disabled="true"],
.pagination button.disabled {
  color: #6b7280;
  cursor: default;
  pointer-events: none;
}
.pagination-ellipsis {
  padding: 0 4px;
  color: #6b7280;
}

/* Accessibilitat: screen-reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
  border: 0;
}

/* Responsive: filtres en dues files a viewport < 640px */
@media (max-width: 640px) {
  .filter-row { flex-direction: column; }
}
```

---

## Shared Patterns

### Detecció d'errors de l'API

**Font:** `fp-cercador/backend/app.py` línies 78–85 (comportament dels errors)
**Aplicar a:** Bloc `init()` del component Alpine.js

```javascript
// res.ok === false per a 503 (Data not available) i corrupt JSON
// Errors de xarxa llancen excepcions (capturades al catch)
const res = await fetch(API_BASE + '/api/ofertes');
if (!res.ok) { this.state = 'error'; return; }
// Nota: NO mostrar res.json().error al frontend — missatge és intern del servidor
```

### Constant API_BASE (D-09)

**Font:** CONTEXT.md D-09
**Aplicar a:** Línia 1 del bloc `<script>`, abans de `alpine:init`

```javascript
const API_BASE = 'http://localhost:5000';
// Canviar NOMÉS aquesta línia per a producció
// Nota: app.py usa port=5001 en __main__, però Flask per defecte usa 5000.
// Verificar el port real en executar `flask run`.
```

### Seguretat XSS — x-text obligatori

**Font:** RESEARCH.md Security Domain
**Aplicar a:** Tots els `x-text` de la taula

```html
<!-- SEMPRE x-text (escapa HTML automàticament) -->
<span x-text="row.denominacion"></span>
<!-- MAI x-html — risc XSS si denominacion conté HTML -->
```

### Accessibilitat — aria-disabled en paginació

**Font:** UI-SPEC.md Accessibility Baseline
**Aplicar a:** Botons Anterior / Següent de paginació

```html
<!-- aria-disabled="true" en lloc de disabled per mantenir focus de teclat (WCAG 2.1) -->
<button :aria-disabled="currentPage === 1">Anterior</button>
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `fp-cercador/frontend/index.html` | component SPA | request-response + in-memory filter | Primer fitxer frontend del projecte — stub buit. No hi ha cap altre fitxer HTML/JS al codebase per extreure patrons. Tots els patrons provenen de RESEARCH.md (verificats) i de la inspecció directa del backend `app.py` |

---

## Notes Crítiques per al Planner

### Pitfalls documentats a RESEARCH.md — el planner ha d'assegurar que el pla els cobreix:

| Pitfall | Risc | Solució obligatòria |
|---------|------|---------------------|
| Pitfall 1: Getters no cached | Lag visible si el getter és lent | Pre-normalitzar a `init()`, NO al getter |
| Pitfall 2: `nivel` tipus mixt | Filtre silenciosament trencat | `parseInt(this.filterNivel)` al filtre |
| Pitfall 3: `plan_antiguo` és booleà | Comparació sempre false | `if (r.plan_antiguo)` directe, no `=== 'true'` |
| Pitfall 4: Paginació no es reseteja | "Cap resultat" a la pàgina 10 | `@input="resetPage()"` i `@change="resetPage()"` a tots els controls |
| Pitfall 5: Ordre de scripts | Component `cercador` no trobat | Script propi ABANS del CDN Alpine amb `defer` |
| Pitfall 6: `nivel: null` Grado A | Comportament esperat, documentar | `filterNivel` buit → mostra tots; parseInt cobreix el cas |

### Dades reals verificades (impacte en UX inicial):

| Estat | Valor |
|-------|-------|
| Carrega inicial (`hideOld=true` per defecte) | **7.244 resultats** (no 12.374) |
| Pàgines inicials | **145 pàgines** de 50 |
| Pàgines màximes (hideOld=false) | **248 pàgines** |
| Famílies al dropdown | **29 opcions** + "Totes les famílies" = 30 total |

---

## Metadata

**Analog search scope:** `fp-cercador/frontend/`, `fp-cercador/backend/`
**Files scanned:** `index.html` (stub), `admin.html` (stub), `app.py` (backend), `ofertes.json` (dades reals)
**Pattern extraction date:** 2026-04-19
