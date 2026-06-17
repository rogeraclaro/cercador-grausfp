# Pla 035: [F8] Selecció de centres amb checkbox → pinning al llistat + columna al CSV

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, do NOT update `plans/README.md` —
> the reviewer maintains the index. Before reporting, audit every claim in
> your report against an actual tool result from this session — only report
> what you can point to evidence for; if a verification failed or was
> skipped, say so plainly. When finished, reply with exactly the report
> format below.
>
> **Drift check (run first)**: `git diff --stat a46b9f9..HEAD -- fp-cercador/frontend/index.html`
> If `index.html` changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P2
- **Effort**: M (3-5h)
- **Risk**: LOW — canvis purament al frontend; zero codi de backend tocat
- **Depends on**: pla 034 MERGED (commit `a46b9f9`) — `exportCSV()` ha d'existir a `index.html`
- **Category**: direction / feature
- **Planned at**: commit `a46b9f9`, 2026-06-17

## Why this matters

L'orientador que utilitza el cercador no vol exportar simplement el llistat de graus: vol saber *on* s'imparteixen els que li interessen. Amb aquest pla, en obrir el panell de centres d'un grau pot marcar fins a 5 centres amb un checkbox; els marcats es pinnen al capdamunt del llistat (separats per una línia prominent) i s'inclouen automàticament en el CSV exportat com a columna `Centres seleccionats`. El workflow complet queda: cercar → filtrar → obrir centres → marcar els propers → exportar CSV.

## Codebase context

**`frontend/index.html`** — fitxer únic HTML+JS amb Alpine.js 3.x vendoritzat. Tot el cercador viu aquí. Les dades dels centres es carreguen sota demanda via `toggleCentres(row)` i es guarden a `this.centresData[row.id]` (array d'objectes `{id, nombre, localitat, direccio, ccaa, telefon, email, url_web}`).

### Estat Alpine rellevant (línia ~1003)

```js
centresCount: {},
centresVisible: {},
centresData: {},
centresCCAA: {},
centresLoading: {},
centresSearch: {},

loggedIn: false,
centresModalVisible: false,
```

### Mètodes rellevants

**`centresVisibles(row)`** (línia ~1267) — retorna els centres a renderitzar:
```js
centresVisibles(row) {
  const total = (this.centresData[row.id] || []).length;
  if (this.loggedIn || total <= 3) {
    return this.centresFiltrats(row).slice(0, 50);
  }
  return (this.centresData[row.id] || []).slice(0, 3);
},
```

**`centresFiltrats(row)`** (línia ~1275) — aplica filtre CCAA + cerca i ordena per localitat:
```js
centresFiltrats(row) {
  const data = this.centresData[row.id] || [];
  const ccaa = this.centresCCAA[row.id];
  const q = (this.centresSearch[row.id] || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  const filtered = data.filter(c => {
    if (ccaa && ccaa !== 'Totes' && c.ccaa !== ccaa) return false;
    if (q) {
      const nom = (c.nombre || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
      const loc = (c.localitat || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
      if (!nom.includes(q) && !loc.includes(q)) return false;
    }
    return true;
  });
  return [...filtered].sort((a, b) => {
    const la = (a.localitat || '').toLowerCase();
    const lb = (b.localitat || '').toLowerCase();
    if (la !== lb) return la < lb ? -1 : 1;
    return (a.nombre || '').toLowerCase() < (b.nombre || '').toLowerCase() ? -1 : 1;
  });
},
```

**`exportCSV()`** (línia ~1080, afegit per pla 034) — verifica que existeix:
```js
exportCSV() {
  const cols = ['codigo', 'denominacion', 'familia', 'grado', 'nivel', 'plan_antiguo'];
  const headers = ['Codi', 'Denominació', 'Família', 'Grau', 'Nivell', 'Pla antic'];
  const escape = v => { ... };
  const rows = [headers.join(',')];
  for (const r of this.filteredRecords) {
    rows.push(cols.map(c => escape(r[c])).join(','));
  }
  const blob = new Blob(['﻿' + rows.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
  ...
},
```

### Template HTML del panell de centres (línia ~1554)

```html
<div x-show="!centresLoading[row.id]">
  <template x-for="centre in centresVisibles(row)" :key="centre.id">
    <div class="centre-item">
      <div class="centre-nom">
        <template x-if="centre.url_web">
          <a :href="centre.url_web" target="_blank" rel="noopener" x-text="sc(centre.nombre)"></a>
        </template>
        <template x-if="!centre.url_web">
          <span x-text="sc(centre.nombre)"></span>
        </template>
      </div>
      <div class="centre-meta">
        <span x-text="tc(centre.direccio) || ''"></span>
        <span x-show="centre.direccio && centre.localitat">, </span>
        <span x-text="centre.localitat || ''"></span>
        <span x-show="centre.telefon"> · <a :href="'tel:'+centre.telefon"
            x-text="'📞 '+centre.telefon" style="color:inherit;text-decoration:none"></a></span>
        <span x-show="centre.email"> · <a :href="'mailto:'+centre.email" x-text="centre.email"
            style="color:inherit"></a></span>
      </div>
    </div>
  </template>
  <!-- Separador + upsell per a usuaris anònims (quan hi ha >3 centres) -->
  ...
```

### CSS rellevant (línia ~766)

```css
.centre-item {
  padding: 6px 0;
  border-bottom: 1px solid #e9ecef;
}
.centre-item:last-child {
  border-bottom: none;
}
```

### Patró de reactivitat per a Sets (usat a `toggleFavorite`)

Alpine.js no detecta mutació directa d'un `Set` ni d'un objecte. El patró del codi per forçar reactivitat:
```js
// Favorites:
this.favorites.delete(id);
this.favorites = new Set(this.favorites);  // <-- force reactivity

// Aplicar el mateix patró per a selectedCentres:
this.selectedCentres = { ...this.selectedCentres, [rowId]: new Set(sel) };
```

## Scope

**In scope**:
- `frontend/index.html` — únics canvis: estat, mètodes JS, CSS i template HTML

**Out of scope**: No tocar cap altre fitxer. No tocar `app.py`, `db.py`, `historial.html`, `observatori.html`, `alertes.html`, ni cap fitxer de backend.

## Commands you will need

| Propòsit | Comanda | Resultat esperat |
|---|---|---|
| Tests backend | `cd fp-cercador && python -m pytest backend/tests/ -q` | exits 0 (cap backend modificat) |
| Verificar exportCSV previ | `grep -c "exportCSV" fp-cercador/frontend/index.html` | ≥2 (pla 034 present) |
| Comptar selectedCentres | `grep -c "selectedCentres" fp-cercador/frontend/index.html` | ≥5 |
| Comptar toggleCentreSelect | `grep -c "toggleCentreSelect" fp-cercador/frontend/index.html` | 2 (definició + crida) |

## Steps

---

### Step 1: Verificar que pla 034 és present

Executar:
```bash
grep -c "exportCSV" fp-cercador/frontend/index.html
```
Ha de retornar un número ≥ 2. Si retorna 0, **ATURA** — el pla 034 no s'ha fusionat, i aquest pla ha d'esperar.

---

### Step 2: Afegir `selectedCentres: {}` a l'estat Alpine

Localitzar el bloc de propietats d'estat de centres (línia ~1008):
```js
        centresSearch: {},

        loggedIn: false,
```

Afegir `selectedCentres: {},` entre `centresSearch: {}` i `loggedIn: false`:

```js
        centresSearch: {},
        selectedCentres: {},

        loggedIn: false,
```

**Verificació**: `grep -c "selectedCentres" fp-cercador/frontend/index.html` retorna ≥ 1.

---

### Step 3: Afegir `toggleCentreSelect()`, `centresSeleccionats()` i `centresNoSeleccionats()` com a mètodes Alpine

Localitzar la línia que conté `ccaasDisponibles(row)` (línia ~1296):
```js
        ccaasDisponibles(row) {
```

Afegir els tres mètodes nous JUST ABANS de `ccaasDisponibles(row)`, deixant una línia en blanc entre `centresFiltrats` i el nou bloc:

```js
        toggleCentreSelect(rowId, centreId) {
          const sel = new Set(this.selectedCentres[rowId] || []);
          if (sel.has(centreId)) {
            sel.delete(centreId);
          } else if (sel.size < 5) {
            sel.add(centreId);
          }
          this.selectedCentres = { ...this.selectedCentres, [rowId]: sel };
        },

        centresSeleccionats(row) {
          const sel = this.selectedCentres[row.id];
          if (!sel || sel.size === 0 || !this.loggedIn) return [];
          return this.centresFiltrats(row).filter(c => sel.has(c.id));
        },

        centresNoSeleccionats(row) {
          const sel = this.selectedCentres[row.id] || new Set();
          if (!this.loggedIn) return this.centresVisibles(row);
          return this.centresFiltrats(row).filter(c => !sel.has(c.id)).slice(0, 50);
        },

        ccaasDisponibles(row) {
```

Notes importants:
- `toggleCentreSelect`: crea un nou `Set` des de l'existent (evita mutar el Set original), actualitza `selectedCentres` amb spread per forçar reactivitat Alpine.
- `centresSeleccionats`: retorna els centres marcats que encara passen el filtre CCAA/cerca actiu. Retorna array buit per a usuaris anònims.
- `centresNoSeleccionats`: retorna els no marcats (fins a 50). Per a usuaris anònims, delega a `centresVisibles` (comportament original = 3 centres).

**Verificació**: `grep -c "toggleCentreSelect" fp-cercador/frontend/index.html` retorna 1 (és la definició; la crida s'afegeix al Step 4).

---

### Step 4: Modificar `exportCSV()` per incloure la columna de centres

Localitzar el mètode `exportCSV()` (línia ~1080). Substituir el bloc complet per:

```js
        exportCSV() {
          const cols = ['codigo', 'denominacion', 'familia', 'grado', 'nivel', 'plan_antiguo'];
          const headers = ['Codi', 'Denominació', 'Família', 'Grau', 'Nivell', 'Pla antic', 'Centres seleccionats'];
          const escape = v => {
            const s = String(v ?? '');
            return s.includes(',') || s.includes('"') || s.includes('\n')
              ? '"' + s.replace(/"/g, '""') + '"'
              : s;
          };
          const rows = [headers.join(',')];
          for (const r of this.filteredRecords) {
            const sel = this.selectedCentres[r.id];
            const centreStr = (sel && sel.size > 0 && this.centresData[r.id])
              ? [...sel].map(id => {
                  const c = (this.centresData[r.id] || []).find(x => x.id === id);
                  return c ? (c.nombre + (c.localitat ? ` (${c.localitat})` : '')) : '';
                }).filter(Boolean).join(' | ')
              : '';
            rows.push([...cols.map(c => escape(r[c])), escape(centreStr)].join(','));
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
- La nova columna `Centres seleccionats` conté els noms dels centres marcats separats per ` | ` (p. ex. `IES Gaudí (Barcelona) | IES Picasso (Girona)`).
- Si l'usuari no ha obert el panell de centres d'un registre, `centresData[r.id]` és `undefined` i la columna queda buida (comportament esperat).
- La funció `escape` existia ja al mètode; no la dupliquis.

**Verificació**:
```bash
grep -c "Centres seleccionats" fp-cercador/frontend/index.html
```
Ha de retornar `1` (la capçalera CSV).

---

### Step 5: Afegir CSS per a la separació i el checkbox

Localitzar el bloc CSS `.centre-item` (línia ~766):
```css
    .centre-item {
      padding: 6px 0;
      border-bottom: 1px solid #e9ecef;
    }

    .centre-item:last-child {
      border-bottom: none;
    }
```

Substituir per:
```css
    .centre-item {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid #e9ecef;
    }

    .centre-item:last-child {
      border-bottom: none;
    }

    .centre-checkbox {
      margin-top: 3px;
      flex-shrink: 0;
      cursor: pointer;
      accent-color: #1a73e8;
    }

    .centre-checkbox:disabled {
      cursor: default;
      opacity: 0.4;
    }

    .centres-selected-sep {
      border: none;
      border-top: 2px solid #888;
      margin: 6px 0 8px;
    }
```

Notes:
- `display: flex` al `.centre-item` permet alinear el checkbox a l'esquerra del contingut.
- `.centre-checkbox` utilitza `accent-color: #1a73e8` (el blau ja usat als `badge-centres`).
- `.centres-selected-sep` és una línia `2px solid #888` — notablement més intensa que el `1px solid #e9ecef` dels separadors normals.

**Verificació**: `grep -c "centres-selected-sep" fp-cercador/frontend/index.html` retorna `2` (definició CSS + ús HTML, que s'afegirà al Step 6).

---

### Step 6: Substituir el template HTML del llistat de centres

Localitzar el bloc HTML (línia ~1554):
```html
                      <div x-show="!centresLoading[row.id]">
                        <template x-for="centre in centresVisibles(row)" :key="centre.id">
                          <div class="centre-item">
                            <div class="centre-nom">
                              <template x-if="centre.url_web">
                                <a :href="centre.url_web" target="_blank" rel="noopener" x-text="sc(centre.nombre)"></a>
                              </template>
                              <template x-if="!centre.url_web">
                                <span x-text="sc(centre.nombre)"></span>
                              </template>
                            </div>
                            <div class="centre-meta">
                              <span x-text="tc(centre.direccio) || ''"></span>
                              <span x-show="centre.direccio && centre.localitat">, </span>
                              <span x-text="centre.localitat || ''"></span>
                              <span x-show="centre.telefon"> · <a :href="'tel:'+centre.telefon"
                                  x-text="'📞 '+centre.telefon" style="color:inherit;text-decoration:none"></a></span>
                              <span x-show="centre.email"> · <a :href="'mailto:'+centre.email" x-text="centre.email"
                                  style="color:inherit"></a></span>
                            </div>
                          </div>
                        </template>
```

Substituir ÚNICAMENT el `<template x-for="centre in centresVisibles(row)" ...>` i el seu contingut fins al `</template>` de tancament (mantenint el `<div x-show="!centresLoading[row.id]">` i el que hi ha després intacte) pel bloc de dos loops + separador:

```html
                      <div x-show="!centresLoading[row.id]">
                        <!-- Centres seleccionats: sempre al capdamunt -->
                        <template x-for="centre in centresSeleccionats(row)" :key="'sel-'+centre.id">
                          <div class="centre-item">
                            <input type="checkbox" class="centre-checkbox" checked @click.stop="toggleCentreSelect(row.id, centre.id)" :title="'Treu ' + sc(centre.nombre) + ' de la selecció'">
                            <div>
                              <div class="centre-nom">
                                <template x-if="centre.url_web">
                                  <a :href="centre.url_web" target="_blank" rel="noopener" x-text="sc(centre.nombre)"></a>
                                </template>
                                <template x-if="!centre.url_web">
                                  <span x-text="sc(centre.nombre)"></span>
                                </template>
                              </div>
                              <div class="centre-meta">
                                <span x-text="tc(centre.direccio) || ''"></span>
                                <span x-show="centre.direccio && centre.localitat">, </span>
                                <span x-text="centre.localitat || ''"></span>
                                <span x-show="centre.telefon"> · <a :href="'tel:'+centre.telefon"
                                    x-text="'📞 '+centre.telefon" style="color:inherit;text-decoration:none"></a></span>
                                <span x-show="centre.email"> · <a :href="'mailto:'+centre.email" x-text="centre.email"
                                    style="color:inherit"></a></span>
                              </div>
                            </div>
                          </div>
                        </template>
                        <!-- Separador entre seleccionats i la resta (només si n'hi ha de seleccionats) -->
                        <template x-if="centresSeleccionats(row).length > 0">
                          <hr class="centres-selected-sep">
                        </template>
                        <!-- Centres no seleccionats -->
                        <template x-for="centre in centresNoSeleccionats(row)" :key="'rest-'+centre.id">
                          <div class="centre-item">
                            <input type="checkbox" class="centre-checkbox"
                              :checked="false"
                              :disabled="(selectedCentres[row.id] || new Set()).size >= 5"
                              @click.stop="toggleCentreSelect(row.id, centre.id)"
                              :title="(selectedCentres[row.id] || new Set()).size >= 5 ? 'Màxim 5 centres seleccionats' : 'Marca ' + sc(centre.nombre)"
                              x-show="loggedIn">
                            <div>
                              <div class="centre-nom">
                                <template x-if="centre.url_web">
                                  <a :href="centre.url_web" target="_blank" rel="noopener" x-text="sc(centre.nombre)"></a>
                                </template>
                                <template x-if="!centre.url_web">
                                  <span x-text="sc(centre.nombre)"></span>
                                </template>
                              </div>
                              <div class="centre-meta">
                                <span x-text="tc(centre.direccio) || ''"></span>
                                <span x-show="centre.direccio && centre.localitat">, </span>
                                <span x-text="centre.localitat || ''"></span>
                                <span x-show="centre.telefon"> · <a :href="'tel:'+centre.telefon"
                                    x-text="'📞 '+centre.telefon" style="color:inherit;text-decoration:none"></a></span>
                                <span x-show="centre.email"> · <a :href="'mailto:'+centre.email" x-text="centre.email"
                                    style="color:inherit"></a></span>
                              </div>
                            </div>
                          </div>
                        </template>
```

Notes importants:
- Els seleccionats sempre apareixen (loop `centresSeleccionats`), després el separador `<hr>`, després els no seleccionats (loop `centresNoSeleccionats`).
- El checkbox dels seleccionats no té `x-show="loggedIn"` perquè si un centre és seleccionat és que l'usuari ja estava logat; sempre és visible.
- El checkbox dels no seleccionats té `x-show="loggedIn"` — els anònims no el veuen.
- `:disabled` a 5 seleccionats: l'usuari no pot marcar un 6è.
- Mantén intactes tots els blocs `<!-- Separador + upsell per a usuaris anònims -->`, `centres-more` i `centres-buit` que venen DESPRÉS d'aquest bloc.

**Verificació**:
```bash
grep -c "centres-selected-sep" fp-cercador/frontend/index.html
```
Ha de retornar `2` (1 CSS + 1 HTML).

```bash
grep -c "toggleCentreSelect" fp-cercador/frontend/index.html
```
Ha de retornar `2` (1 definició JS + 1 crida a Step 3 + 2 crides al HTML... realment serà ≥3). Comprova que existeix tant a la secció JS com al template HTML.

---

### Step 7: Commit

```bash
git add fp-cercador/frontend/index.html
git commit -m "feat(F8): selecció centres amb checkbox → pin al llistat + columna CSV (pla 035)"
```

## Test plan

No hi ha tests automatitzats per al frontend (és un HTML+JS sense framework de test). La verificació manual al navegador és l'única via:

1. Obrir `http://localhost:5001` (cal servidor Flask: `cd fp-cercador && python backend/app.py`)
2. Loginar-se (login obligatori per veure checkboxes)
3. Buscar qualsevol grau que tingui centres (badge blau)
4. Obrir el panell de centres
5. Marcar 2 centres → verificar que pugen al capdamunt, separats per línia intensa
6. Marcar 5 centres → verificar que els no marcats queden amb checkbox disabled
7. Intentar marcar un 6è → no ha de ser possible (disabled)
8. Desmarcar un centre → baixa de la zona de seleccionats
9. Clicar "↓ Exporta CSV" → obrir el CSV → la capçalera ha de tenir `Centres seleccionats`
10. Els registres on has marcat centres han de tenir els noms separats per ` | `
11. Obrir un incògnit (sense login) → els checkboxes no han d'aparecer

Si no pots obrir un navegador en l'entorn d'execució, indica-ho a NOTES.

## Done criteria

- [ ] `grep -c "selectedCentres" fp-cercador/frontend/index.html` retorna ≥ 5
- [ ] `grep -c "toggleCentreSelect" fp-cercador/frontend/index.html` retorna ≥ 3
- [ ] `grep -c "centres-selected-sep" fp-cercador/frontend/index.html` retorna `2` (1 CSS + 1 HTML)
- [ ] `grep -c "Centres seleccionats" fp-cercador/frontend/index.html` retorna `1` (capçalera CSV)
- [ ] `grep -c "centresSeleccionats" fp-cercador/frontend/index.html` retorna ≥ 3 (definició + 2 usos al template)
- [ ] `grep -c "centresNoSeleccionats" fp-cercador/frontend/index.html` retorna ≥ 2
- [ ] `git status` — cap fitxer fora de l'scope modificat
- [ ] `python -m pytest backend/tests/ -q` exits 0

## STOP conditions

- Si `grep -c "exportCSV" fp-cercador/frontend/index.html` retorna `0`: el pla 034 no s'ha fusionat. ATURA.
- Si el codi als excerpts de "Current state" no coincideix (drift significatiu): ATURA i reporta.
- Si el bloc HTML del `x-for="centre in centresVisibles(row)"` no es troba a l'arxiu: ATURA — pot ser que la plantilla de centres hagi canviat.
- Si `filteredRecords` o `centresData` no estan accessibles com `this.filteredRecords` / `this.centresData` (reestructuració de l'Alpine.data): ATURA.

## Maintenance notes

- **Reactiu amb Set**: `selectedCentres` és un objecte de `{rowId: Set}`. Alpine detecta el canvi del diccionari (spread `{...}`) però no la mutació interna d'un Set — el mètode `toggleCentreSelect` sempre reassigna amb spread. Si en el futur es refactoritza, mantenir aquest patró.
- **Estat ephemeral**: `selectedCentres` no es persiste; es perd en tancar la pàgina. Si algun dia es vol persistir (p.ex. en `localStorage`), afegir-ho a `init()` seguint el patró de `loadFavorites()`.
- **Límit 5**: si l'usuari demana augmentar el límit, canviar el `< 5` a `toggleCentreSelect` i el `>= 5` al template. Aquestes tres ocurrències han de coincidir.
- **CSV columna centres**: la columna "Centres seleccionats" queda buida per registres on no s'ha obert el panell de centres. Això és comportament esperat i documentat.
