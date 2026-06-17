# Pla 034: [F8] Botó "Exporta CSV" al cercador

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, do NOT update `plans/README.md` —
> the reviewer maintains the index.
>
> **Drift check (run first)**: `git diff --stat bc0e738..HEAD -- fp-cercador/frontend/index.html`
> If `index.html` changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: S (1-2h)
- **Risk**: LOW — canvis purament al frontend; zero codi de backend tocat
- **Depends on**: cap
- **Category**: direction / feature
- **Planned at**: commit `bc0e738`, 2026-06-17

## Why this matters

Els orientadors de secundària que utilitzen el cercador volen lliurar als alumnes una llista imprimible dels graus que han trobat. Ara han de copiar manualment o fer screenshots. Un botó "Exporta CSV" que descarregui els registres visibles en el moment (post-filtratge) resol el cas d'ús amb zero clics extres: filtres → exporta → obra a Excel/Sheets. No requereix login, no requereix backend, i reutilitza `this.filteredRecords` que Alpine.js ja calcula.

## Codebase context

**`frontend/index.html`** — tot el cercador és un únic fitxer HTML+JS amb Alpine.js 3.x vendoritzat.

**Propietat computed rellevant (línia 1053):**
```js
get filteredRecords() {
  const q = this.search.normalize('NFD')
    .replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  const result = this.allRecords.filter(r => {
    if (this.filterOld === 'hide' && r.plan_antiguo) return false;
    if (this.filterOld === 'only' && !r.plan_antiguo) return false;
    if (this.filterGrado && r.grado !== this.filterGrado) return false;
    if (this.filterFamilia && r.familia !== this.filterFamilia) return false;
    if (this.filterNivel && r.nivel !== parseInt(this.filterNivel)) return false;
    if (this.filterFavs && !this.favorites.has(r.id)) return false;
    if (q && !r._normDen.includes(q) && !r._normCod.includes(q)) return false;
    return true;
  });
  // ... sort ...
  return result;
},
get filteredCount() { return this.filteredRecords.length; },
```

**Camps disponibles a cada registre** (de `backend/data/ofertes.json`):
```
codigo, denominacion, familia, nivel, plan_antiguo, observaciones, ficha_id, grado, id
```
Columnes a exportar: `codigo`, `denominacion`, `familia`, `grado`, `nivel`, `plan_antiguo`.

**Botó existent (patró a seguir, línia 1381):**
```html
<button class="save-alert-btn" x-show="search || filterGrado || filterFamilia || filterNivel"
  :disabled="alertSaving" @click="saveAlert()">
  🔔 Desa com a alerta
</button>
```

**Estil `.save-alert-btn` (línia 220):**
```css
.save-alert-btn {
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  padding: 5px 12px;
  border-radius: 4px;
  cursor: pointer;
  border: 1px solid var(--dark);
  color: var(--dark);
  background: transparent;
  white-space: nowrap;
  transition: background 0.15s;
  text-decoration: none;
}
.save-alert-btn:hover { background: black; color: white; }
.save-alert-btn:disabled { opacity: 0.5; cursor: default; }
```

## Scope

**In scope**:
- `frontend/index.html` — afegir 1 mètode `exportCSV()` a l'objecte Alpine.data + 1 botó al HTML

**Out of scope**: cap altre fitxer. No tocar `app.py`, `db.py`, `historial.html`, `observatori.html`, ni cap fitxer de backend.

## Commands you will need

| Propòsit | Comanda | Resultat esperat |
|---|---|---|
| Tests backend | `cd fp-cercador && python -m pytest backend/tests/ -q` | exits 0 (no toquem backend, però verificar que no s'han trencat) |
| Sintaxi JS | Obrir `frontend/index.html` al navegador → consola sense errors | cap `SyntaxError` ni `ReferenceError` |

## Steps

### Step 1: Afegir el mètode `exportCSV()` a l'objecte Alpine

Localitzar la línia `get filteredCount() { return this.filteredRecords.length; },` (línia ~1078 actual) i afegir el mètode `exportCSV()` just DESPRÉS d'aquesta línia:

```js
get filteredCount() { return this.filteredRecords.length; },

exportCSV() {
  const cols = ['codigo', 'denominacion', 'familia', 'grado', 'nivel', 'plan_antiguo'];
  const headers = ['Codi', 'Denominació', 'Família', 'Grau', 'Nivell', 'Pla antic'];
  const escape = v => {
    const s = String(v ?? '');
    return s.includes(',') || s.includes('"') || s.includes('\n')
      ? '"' + s.replace(/"/g, '""') + '"'
      : s;
  };
  const rows = [headers.join(',')];
  for (const r of this.filteredRecords) {
    rows.push(cols.map(c => escape(r[c])).join(','));
  }
  const blob = new Blob(['﻿' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'grausfp-export.csv';
  a.click();
  URL.revokeObjectURL(url);
},
```

Notes:
- `'﻿'` és el BOM UTF-8: fa que Excel i LibreOffice reconeguin els caràcters especials (accents catalans) automàticament.
- `\r\n` és el separador de línia estàndard CSV (RFC 4180).
- La funció `escape` cita amb cometes dobles qualsevol camp que contingui comes, cometes o salts de línia.

**Verificació**: `grep -n "exportCSV" fp-cercador/frontend/index.html` ha de retornar 2 resultats (la definició i la crida al HTML que afegirem al Step 2).

### Step 2: Afegir el botó "Exporta CSV" al HTML

Localitzar el bloc de botons d'acció (línia ~1380):
```html
      <a href="alertes.html" class="save-alert-btn">Veure alertes</a>
      <button class="save-alert-btn" x-show="search || filterGrado || filterFamilia || filterNivel"
        :disabled="alertSaving" @click="saveAlert()">
        🔔 Desa com a alerta
      </button>
      <button class="clear-btn"
```

Afegir el botó d'exportació JUST ABANS del `<button class="clear-btn"`:

```html
      <button class="save-alert-btn" x-show="state === 'ready' && filteredCount > 0"
        @click="exportCSV()"
        :title="'Exporta ' + filteredCount + ' registres a CSV'">
        ↓ Exporta CSV
      </button>
      <button class="clear-btn"
```

El botó és visible quan hi ha resultats (tant amb filtres com sense — permet exportar el catàleg complet), i el `title` mostra el nombre de registres que s'exportaran.

**Verificació**: `grep -n "exportCSV\|Exporta CSV" fp-cercador/frontend/index.html` — ha de retornar 2 línies (mètode + botó).

### Step 3: Verificació manual al navegador

Obrir `frontend/index.html` directament al navegador (file://) o via el servidor Flask (`python backend/app.py` i accedir a `http://localhost:5001`):

1. Esperar que carreguin les dades (12.894 registres).
2. Sense filtres: fer clic a "↓ Exporta CSV" → s'ha de descarregar `grausfp-export.csv` amb ~12.895 línies (capçalera + registres).
3. Filtrar per Grau A → el botó ha de mostrar el títol amb el nombre de registres del Grau A (~8.730).
4. Fer clic → CSV descarregat ha de contenir només registres del Grau A.
5. Obrir el CSV a un editor de text — la primera línia ha de ser `Codi,Denominació,Família,Grau,Nivell,Pla antic` i els caràcters especials (accents) han de ser llegibles.
6. Consola del navegador: zero errors.

Si no pots obrir un navegador en l'entorn d'execució, indica-ho a NOTES i salta al Step 4.

### Step 4: Commit

```bash
git add fp-cercador/frontend/index.html
git commit -m "feat(F8): botó Exporta CSV amb registres filtrats (pla 034)"
```

## Done criteria

- [ ] `grep -c "exportCSV" fp-cercador/frontend/index.html` retorna `2`
- [ ] `grep -n "Exporta CSV" fp-cercador/frontend/index.html` retorna 1 resultat (el botó)
- [ ] El mètode `exportCSV()` inclou el BOM `﻿` per compatibilitat Excel
- [ ] El botó té `x-show="state === 'ready' && filteredCount > 0"` (no apareix mentre carrega ni si no hi ha resultats)
- [ ] `git status` — cap fitxer fora de l'scope modificat
- [ ] `python -m pytest backend/tests/ -q` passa (zero regressions de backend)

## STOP conditions

- Si el codi a les línies de "Current state" no coincideix amb el que hi ha al fitxer (drift): ATURA i reporta les diferències.
- Si `filteredRecords` no és accessible com a `this.filteredRecords` dins del mètode (error de scope Alpine): ATURA — pot ser que l'Alpine.data s'hagi reestructurat.

## Maintenance notes

- Si en el futur s'afegeixen camps nous als registres d'oferta (p. ex. `url_fitxa`), afegir la columna a `cols` i `headers` al mètode `exportCSV()`.
- Si es vol afegir exportació des de l'Observatori o altres pàgines, el patró `Blob + createObjectURL` és reutilitzable tal qual.
- El BOM és intencional: sense ell, Excel a Windows obre el CSV en codificació ANSI i trenca els accents. No eliminar-lo.
