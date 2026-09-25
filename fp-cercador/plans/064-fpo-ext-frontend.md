# Pla 064 — FPO extern: insígnies, filtres, i18n, perfil, fonts i historial

Origen: `docs/superpowers/specs/2026-09-25-fpo-pimec-foment-design.md` (§7).
Depèn de: 062 i 063 DONE (`/api/fpo/especialitats` retorna `font` i `tipus` a cada fila;
els cursos porten `font`, `tipus`, `hores`, `horariText`, `estat` ∈ {'', 'finalitzat', SOC}).
Tercer dels 3 plans. Sessió neta. **No cal decidir res.**

Només frontend estàtic (`frontend/*.html`, `i18n.js`): **no cal reiniciar el servei**.
No hi ha suite de tests de UI: cada fase acaba amb una **verificació concreta** (Fase 6).

## Regles del projecte que s'apliquen

- Alpine.js 3 vendoritzat; cap altra llibreria. Tots els textos nous van a `i18n.js` en
  **català i castellà** (mateixa clau als dos blocs). Vigilar els literals dins `x-text`.
- `x-if` només accepta **un únic element arrel** (si en té dos, el segon desapareix).
- `i18n.js` es serveix sense paràmetre `?v=`: en provar, fer **recàrrega forçada**.
- Cap captura ni fitxer temporal dins el repo (`.playwright-mcp/` és versionada: no
  esborrar el directori, només les captures pròpies).

## Fets del backend (Pla 063) que fa servir la UI

Fila (`/api/fpo/especialitats`): `codi`, `titol{ca,es}`, `familia{codi,desc}`, `area{codi,desc}`,
`nivell`, `hores`, `esCertProf`, `nCursos`, `comarques`, `municipis`, `estats`, `modalitats`,
**`font`** (`soc`|`pimec`|`foment`) i **`tipus`** (llista; a les files SOC és
`['Subvencionat']` però **no s'hi mostra insígnia de tipus**). Els externs tenen `nivell: 0`
i `area.codi: ''`.
Curs (`/api/fpo/especialitat/<codi>` → `cursos[]`): a més dels camps del SOC, `font`,
`tipus` (text), `hores`, `horariText`; `estat` pot ser `''` (externs sense estat) o
`'finalitzat'`. Els cursos SOC no porten `font` (tractar-lo com `'soc'`).
Tipus reals: `Subvencionat`, `Bonificable`, `Diàleg Social (Subvencionat)`, `Altres`.

## Fitxers

Modificar: `frontend/index.html`, `frontend/i18n.js`, `frontend/perfil.html`,
`frontend/fonts.html`, `frontend/historial.html`.

---

## Fase 1 — i18n (`frontend/i18n.js`)

Fer les edicions amb l'eina d'edició (cada `old_string` és únic al fitxer).

**a)** Substituir el text de la nota (ja no és només SOC):

CA — `old`:
`'fpo.note': 'Formació professional per a l\'ocupació. Oferta i gestió de la Generalitat de Catalunya (SOC) — un sistema diferent de la FP reglada. Cobreix només Catalunya.',`
`new`:
`'fpo.note': 'Formació professional per a l\'ocupació a Catalunya: l\'oferta pública del Servei d\'Ocupació (SOC) i els cursos d\'altres entitats formadores (patronals, sindicats…). Cada curs indica la font i el tipus (subvencionat, bonificable…). És un sistema diferent de la FP reglada i cobreix només Catalunya.',`

ES — `old`:
`'fpo.note': 'Formación profesional para el empleo. Oferta y gestión de la Generalitat de Catalunya (SOC) — un sistema distinto de la FP reglada. Cubre solo Cataluña.',`
`new`:
`'fpo.note': 'Formación profesional para el empleo en Cataluña: la oferta pública del Servicio de Empleo (SOC) y los cursos de otras entidades formadoras (patronales, sindicatos…). Cada curso indica la fuente y el tipo (subvencionado, bonificable…). Es un sistema distinto de la FP reglada y cubre solo Cataluña.',`

**b)** Afegir les claus noves. CA: just **després** de `'fpo.estat.gestio': 'En gestió',`:

```js
      'fpo.estat.finalitzat': 'Finalitzat',
      'fpo.filter.font': 'Font',
      'fpo.filter.tipus': 'Tipus',
      'fpo.font.soc': 'SOC',
      'fpo.font.pimec': 'PIMEC',
      'fpo.font.foment': 'Foment',
      'fpo.tipus.subvencionat': 'Subvencionat',
      'fpo.tipus.bonificable': 'Bonificable',
      'fpo.tipus.dialeg': 'Diàleg Social (subvencionat)',
      'fpo.tipus.altres': 'Altres',
      'fpo.detall.fitxa_ext': 'Fitxa del curs',
      'fpo.detall.dates_tbd': 'Dates a concretar',
```

ES: just **després** de `'fpo.estat.gestio': 'En gestión',`:

```js
      'fpo.estat.finalitzat': 'Finalizado',
      'fpo.filter.font': 'Fuente',
      'fpo.filter.tipus': 'Tipo',
      'fpo.font.soc': 'SOC',
      'fpo.font.pimec': 'PIMEC',
      'fpo.font.foment': 'Foment',
      'fpo.tipus.subvencionat': 'Subvencionado',
      'fpo.tipus.bonificable': 'Bonificable',
      'fpo.tipus.dialeg': 'Diálogo Social (subvencionado)',
      'fpo.tipus.altres': 'Otros',
      'fpo.detall.fitxa_ext': 'Ficha del curso',
      'fpo.detall.dates_tbd': 'Fechas por concretar',
```

**c)** Claus per a `fonts.html` (Fase 5). CA: just **després** de `'fonts.r12.us': ...` (línia del
bloc CA); ES: després de la seva `'fonts.r12.us'` en castellà (`rg -n "fonts.r12.us" frontend/i18n.js`
dona les dues línies; afegir a cadascuna del seu idioma):

CA:
```js
      'fonts.s7.h2': 'PIMEC Formació',
      'fonts.s7.host': 'pimecformacio.org',
      'fonts.s7.p': 'Font d\'àmbit català: cursos de formació de PIMEC (subvencionats, bonificables i altres). Es llegeixen del cercador de cursos públic de la seva web. Cada curs mostra el tipus tal com el publica PIMEC.',
      'fonts.r13.font': 'Cursos de PIMEC Formació',
      'fonts.r13.detall': 'Títol, tipus (subvencionat, bonificable, diàleg social o altres), dates, hores, població, modalitat, àrea i enllaç a la fitxa de PIMEC.',
      'fonts.r13.us': 'Mode «Cursos FPO (Catalunya)» del cercador, marcats amb la font PIMEC.',
      'fonts.s8.h2': 'Foment Formació',
      'fonts.s8.host': 'fomentformacio.com',
      'fonts.s8.p': 'Font d\'àmbit català: cursos de Foment Formació. Es llegeixen del catàleg públic de la seva web. Foment no publica un tipus per curs, de manera que es mostren com a «Altres».',
      'fonts.r14.font': 'Cursos de Foment Formació',
      'fonts.r14.detall': 'Títol, edicions (centre, dates, horari, hores i modalitat) i enllaç a la fitxa de Foment.',
      'fonts.r14.us': 'Mode «Cursos FPO (Catalunya)» del cercador, marcats amb la font Foment.',
```

ES:
```js
      'fonts.s7.h2': 'PIMEC Formació',
      'fonts.s7.host': 'pimecformacio.org',
      'fonts.s7.p': 'Fuente de ámbito catalán: cursos de formación de PIMEC (subvencionados, bonificables y otros). Se leen del buscador de cursos público de su web. Cada curso muestra el tipo tal como lo publica PIMEC.',
      'fonts.r13.font': 'Cursos de PIMEC Formació',
      'fonts.r13.detall': 'Título, tipo (subvencionado, bonificable, diálogo social u otros), fechas, horas, población, modalidad, área y enlace a la ficha de PIMEC.',
      'fonts.r13.us': 'Modo «Cursos FPO (Cataluña)» del buscador, marcados con la fuente PIMEC.',
      'fonts.s8.h2': 'Foment Formació',
      'fonts.s8.host': 'fomentformacio.com',
      'fonts.s8.p': 'Fuente de ámbito catalán: cursos de Foment Formació. Se leen del catálogo público de su web. Foment no publica un tipo por curso, por lo que se muestran como «Otros».',
      'fonts.r14.font': 'Cursos de Foment Formació',
      'fonts.r14.detall': 'Título, ediciones (centro, fechas, horario, horas y modalidad) y enlace a la ficha de Foment.',
      'fonts.r14.us': 'Modo «Cursos FPO (Cataluña)» del buscador, marcados con la fuente Foment.',
```

### Verificació de la fase

Cada clau `fpo.*` i `fonts.*` ha d'existir als dos idiomes (recompte 2). Des de `fp-cercador/frontend`:

```
python3 - <<'EOF'
import re, collections
src = open('i18n.js', encoding='utf-8').read()
c = collections.Counter(re.findall(r"'((?:fpo|fonts)\.[A-Za-z0-9_.]+)':", src))
print({k: v for k, v in c.items() if v != 2} or 'OK: totes les claus fpo.*/fonts.* estan als 2 idiomes')
EOF
```
Ha d'imprimir `OK: ...`.

### Commit
```
git add frontend/i18n.js
git commit -m "feat(fpo): textos CA/ES per a les fonts PIMEC i Foment"
```

---

## Fase 2 — `index.html`: estat, CSS i filtres

**a) CSS.** Després del bloc `.fpo-estat--gestio { ... }` afegir:

```css
    .fpo-estat--finalitzat {
      background: var(--warm2);
      color: var(--warm);
      border-color: var(--border);
    }

    .fpo-badge {
      display: inline-block;
      padding: 1px 8px;
      margin-left: 6px;
      border-radius: 10px;
      font-size: var(--fs-label);
      font-weight: 600;
      border: 1px solid var(--border);
      background: var(--warm2);
      color: var(--warm);
      vertical-align: middle;
    }
```

**b) Estat dels filtres.** Al `fpoFilters` inicial:

`old`:
```
        fpoFilters: {
          text: '', familia: '', area: '', especialitat: '', comarca: '', municipi: '',
          nivell: '', estat: '', modalitat: '', certprof: false,
        },
```
`new`:
```
        fpoFilters: {
          text: '', familia: '', area: '', especialitat: '', comarca: '', municipi: '',
          nivell: '', estat: '', modalitat: '', certprof: false, font: '', tipus: '',
        },
```

A `fpoResetFilters()`:

`old`:
```
          this.fpoFilters = {
            text: '', familia: '', area: '', especialitat: '', comarca: '', municipi: '',
            nivell: '', estat: '', modalitat: '', certprof: false,
          };
```
`new`:
```
          this.fpoFilters = {
            text: '', familia: '', area: '', especialitat: '', comarca: '', municipi: '',
            nivell: '', estat: '', modalitat: '', certprof: false, font: '', tipus: '',
          };
```

**c) Mètode auxiliar.** Just després de `fpoLang() { return getLang() === 'es' ? 'es' : 'ca'; },`:

```js
        fpoTipusKey(ti) {
          return { 'Subvencionat': 'subvencionat', 'Bonificable': 'bonificable',
                   'Diàleg Social (Subvencionat)': 'dialeg', 'Altres': 'altres' }[ti] || 'altres';
        },
```

**d) Getters d'opcions.** Just abans de `get filteredFpoEspecs() {`:

```js
        get fpoFontsOpcions() {
          const presents = new Set(this.fpoEspecs.map(e => e.font || 'soc'));
          return ['soc', 'pimec', 'foment'].filter(f => presents.has(f));
        },

        get fpoTipusOpcions() {
          const s = new Set();
          for (const e of this.fpoEspecs) for (const ti of (e.tipus || [])) s.add(ti);
          return [...s].sort((a, b) => a.localeCompare(b, 'ca'));
        },
```

**e) Lògica de filtrat.** A `filteredFpoEspecs`, just **després** de la línia
`if (f.certprof && !e.esCertProf) return false;` afegir:

```js
            if (f.font && (e.font || 'soc') !== f.font) return false;
            if (f.tipus && !(e.tipus || []).includes(f.tipus)) return false;
```

**f) Barra de filtres.** Dins `<div class="filter-bar filter-bar--fpo">`, just **abans** de
`      <label class="checkbox-label">\n        <input type="checkbox" x-model="fpoFilters.certprof">`
inserir:

```html
      <label class="sr-only" for="fpo-font" x-text="t('fpo.filter.font')"></label>
      <select id="fpo-font" x-model="fpoFilters.font">
        <option value="" x-text="t('fpo.filter.font') + ' — ' + t('fpo.filter.all')"></option>
        <template x-for="fo in fpoFontsOpcions" :key="fo">
          <option :value="fo" x-text="t('fpo.font.' + fo)"></option>
        </template>
      </select>

      <label class="sr-only" for="fpo-tipus" x-text="t('fpo.filter.tipus')"></label>
      <select id="fpo-tipus" x-model="fpoFilters.tipus">
        <option value="" x-text="t('fpo.filter.tipus') + ' — ' + t('fpo.filter.all')"></option>
        <template x-for="ti in fpoTipusOpcions" :key="ti">
          <option :value="ti" x-text="t('fpo.tipus.' + fpoTipusKey(ti))"></option>
        </template>
      </select>

```

I al botó `clear-btn` d'aquesta barra, afegir els dos filtres a la condició: canviar
`fpoFilters.modalitat || fpoFilters.certprof || fpoFilters.especialitat"` per
`fpoFilters.modalitat || fpoFilters.certprof || fpoFilters.especialitat || fpoFilters.font || fpoFilters.tipus"`.

### Commit
```
git add frontend/index.html
git commit -m "feat(fpo): filtres per font i tipus i estil de l'estat finalitzat"
```

---

## Fase 3 — `index.html`: files i edicions

**a) Fila — nom.** A la cel·la `<td class="col-nom">`, just **després** de
`<span x-show="esp.esCertProf" class="badge-old" x-text="t('fpo.badge.certprof')"></span>` afegir:

```html
                  <span class="fpo-badge" x-text="t('fpo.font.' + (esp.font || 'soc'))"></span>
                  <template x-for="ti in ((esp.font || 'soc') !== 'soc' ? (esp.tipus || []) : [])" :key="ti">
                    <span class="fpo-badge" x-text="t('fpo.tipus.' + fpoTipusKey(ti))"></span>
                  </template>
```

**b) Fila — codi.** Els externs no tenen codi oficial (el sintètic no s'ha de mostrar).
`old`: `<td class="col-codi" x-text="esp.codi"></td>`
`new`:
```html
                <td class="col-codi" :class="{ 'cell-empty': (esp.font || 'soc') !== 'soc' }"
                  x-text="(esp.font || 'soc') === 'soc' ? esp.codi : '—'"></td>
```

**c) Edició — adreça sense línia buida** (PIMEC "Aula Virtual" no té municipi).
`old`: `(curs.centre||{}).comarca ? '(' + curs.centre.comarca + ')' : ''].filter(Boolean).join(', ')"></div>`
`new`: `(curs.centre||{}).comarca ? '(' + curs.centre.comarca + ')' : ''].map(s => (s || '').trim()).filter(Boolean).join(', ')"></div>`

**d) Edició — horari en text i "dates a concretar".** Just **després** del bloc
`<template x-if="fpoHorariEntries((curs.centre||{}).horari).length > 0"> ... </template>` i
**abans** de `<div class="fpo-curs-meta" x-show="curs.dataInici || curs.dataFi">` inserir:

```html
                                <div class="fpo-curs-meta" x-show="curs.horariText">
                                  <strong x-text="t('fpo.detall.horari') + ': '"></strong>
                                  <span x-text="curs.horariText"></span>
                                </div>
```

I just **després** del bloc de dates (`<div class="fpo-curs-meta" x-show="curs.dataInici || curs.dataFi"> ... </div>`) afegir:

```html
                                <div class="fpo-curs-meta"
                                  x-show="!curs.dataInici && !curs.dataFi && curs.font && curs.font !== 'soc'"
                                  x-text="t('fpo.detall.dates_tbd')"></div>
```

**e) Edició — línia d'estat, font, hores i enllaç.**
`old`:
```
                                  <span class="fpo-estat" :class="'fpo-estat--' + curs.estat"
                                    x-text="t('fpo.estat.' + curs.estat)"></span>
                                  <span x-show="curs.modalitat" x-text="tc(curs.modalitat)" style="margin-left:8px;"></span>
                                  <a class="btn-doc" :href="curs.fitxaUrl" target="_blank" rel="noopener"
                                    x-text="t('fpo.detall.fitxa_soc')" style="margin-left:8px;"></a>
```
`new`:
```
                                  <span class="fpo-estat" x-show="curs.estat" :class="'fpo-estat--' + curs.estat"
                                    x-text="t('fpo.estat.' + curs.estat)"></span>
                                  <span class="fpo-badge" x-show="curs.font && curs.font !== 'soc'"
                                    x-text="t('fpo.font.' + curs.font) + ' · ' + t('fpo.tipus.' + fpoTipusKey(curs.tipus))"></span>
                                  <span x-show="curs.modalitat" x-text="tc(curs.modalitat)" style="margin-left:8px;"></span>
                                  <span x-show="curs.hores && curs.font && curs.font !== 'soc'"
                                    x-text="Math.round(curs.hores) + ' h'" style="margin-left:8px;"></span>
                                  <a class="btn-doc" :href="curs.fitxaUrl" target="_blank" rel="noopener"
                                    x-text="t(curs.font && curs.font !== 'soc' ? 'fpo.detall.fitxa_ext' : 'fpo.detall.fitxa_soc')"
                                    style="margin-left:8px;"></a>
```

> Cursos SOC: `curs.estat` sempre és no buit, així que es veu com abans. `t('fpo.estat.' + '')`
> ja no s'avalua per als externs sense estat (queda amagat per `x-show`).

### Commit
```
git add frontend/index.html
git commit -m "feat(fpo): insígnies de font i tipus, dates a concretar i horari als cursos externs"
```

---

## Fase 4 — `perfil.html` (pestanya d'especialitats FPO desades)

**a)** Etiqueta de font a la línia de metadades de l'especialitat desada.
`old`: `var meta = [fam, area, e.nivell ? t('fpo.col.nivell') + ' ' + e.nivell : '',`
`new`: `var meta = [(e.font && e.font !== 'soc') ? t('fpo.font.' + e.font) : '', fam, area, e.nivell ? t('fpo.col.nivell') + ' ' + e.nivell : '',`

**b)** A `fpoCursCard`, dates a concretar + horari en text (després de la línia
`if (c.dataInici || c.dataFi) rows.push(...)`):

```js
        else if (c.font && c.font !== 'soc') rows.push('<span style="font-size:11px;">' + t('fpo.detall.dates_tbd') + '</span>');
        if (c.horariText) rows.push('<span style="font-size:11px;"><strong>' + t('fpo.detall.horari') + ':</strong> ' + esc(c.horariText) + '</span>');
```

**c)** Insígnia d'estat només si n'hi ha, i etiqueta de l'enllaç segons la font.
`old`: `var badgeLine = fpoEstatBadge(c.estat);`
`new`: `var badgeLine = c.estat ? fpoEstatBadge(c.estat) : '';`

`old`: `t('fpo.detall.fitxa_soc') + '</a>';`
`new`: `t(c.font && c.font !== 'soc' ? 'fpo.detall.fitxa_ext' : 'fpo.detall.fitxa_soc') + '</a>';`

> Els cursos `finalitzat` ja es pinten com a "Curs finalitzat" (comportament existent del
> Pla 061), així que no calen colors nous a `fpoEstatBadge`.

### Commit
```
git add frontend/perfil.html
git commit -m "feat(fpo): el perfil mostra la font dels cursos desats de PIMEC i Foment"
```

---

## Fase 5 — `fonts.html` i `historial.html`

**a) `fonts.html`.** Just **després** del `</table>` de la secció SOC (la que acaba amb la fila
`fonts.r12`) i **abans** de `<h2 data-i18n="fonts.s3.h2">`, afegir dues seccions amb
l'estructura exacta de la del SOC:

```html
    <h2 data-i18n="fonts.s7.h2">PIMEC Formació</h2>
    <p class="src-host" data-i18n="fonts.s7.host">pimecformacio.org</p>
    <p data-i18n="fonts.s7.p">Font d'àmbit català: cursos de formació de PIMEC (subvencionats, bonificables i altres). Es llegeixen del cercador de cursos públic de la seva web. Cada curs mostra el tipus tal com el publica PIMEC.</p>
    <table class="src-table">
      <thead>
        <tr>
          <th data-i18n="fonts.tbl.font">Font</th>
          <th data-i18n="fonts.tbl.detall">Què se n'obté</th>
          <th data-i18n="fonts.tbl.us">On es fa servir</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td data-i18n="fonts.r13.font">Cursos de PIMEC Formació</td>
          <td data-i18n="fonts.r13.detall">Títol, tipus (subvencionat, bonificable, diàleg social o altres), dates, hores, població, modalitat, àrea i enllaç a la fitxa de PIMEC.</td>
          <td data-i18n="fonts.r13.us">Mode «Cursos FPO (Catalunya)» del cercador, marcats amb la font PIMEC.</td>
        </tr>
      </tbody>
    </table>

    <h2 data-i18n="fonts.s8.h2">Foment Formació</h2>
    <p class="src-host" data-i18n="fonts.s8.host">fomentformacio.com</p>
    <p data-i18n="fonts.s8.p">Font d'àmbit català: cursos de Foment Formació. Es llegeixen del catàleg públic de la seva web. Foment no publica un tipus per curs, de manera que es mostren com a «Altres».</p>
    <table class="src-table">
      <thead>
        <tr>
          <th data-i18n="fonts.tbl.font">Font</th>
          <th data-i18n="fonts.tbl.detall">Què se n'obté</th>
          <th data-i18n="fonts.tbl.us">On es fa servir</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td data-i18n="fonts.r14.font">Cursos de Foment Formació</td>
          <td data-i18n="fonts.r14.detall">Títol, edicions (centre, dates, horari, hores i modalitat) i enllaç a la fitxa de Foment.</td>
          <td data-i18n="fonts.r14.us">Mode «Cursos FPO (Catalunya)» del cercador, marcats amb la font Foment.</td>
        </tr>
      </tbody>
    </table>

```

**b) `historial.html`.** Les entrades de PIMEC i Foment van al mateix historial (`font` a cada
entrada). **Compte:** el fitxer té dues taules amb el mateix marcatge (centres i FPO), per això
cada `old` de sota és una cadena que només existeix a la de FPO (comprovat: recompte 1).

1. `old`: `    const HIST_LIMIT = 20;`
   `new`:
   ```
       const HIST_LIMIT = 20;
       const FONT_LABEL = { soc: 'SOC', pimec: 'PIMEC', foment: 'Foment' };
   ```
2. `old` (fila; és la única amb `e.ok`):
   ```
               <td>${formatDate(e.ts)}</td>
               <td>${e.ok ? 'OK' : ('Error' + (e.error ? ': ' + e.error : ''))}</td>
   ```
   `new`:
   ```
               <td>${formatDate(e.ts)}</td>
               <td>${FONT_LABEL[e.font] || 'SOC'}</td>
               <td>${e.ok ? 'OK' : ('Error' + (e.error ? ': ' + e.error : ''))}</td>
   ```
3. `old`: `<th scope="col">Resultat</th>`
   `new`:
   ```
   <th scope="col">Font</th>
                     <th scope="col">Resultat</th>
   ```
4. `old`: `Historial de cursos FPO (SOC)` → `new`: `Historial de cursos FPO`.

### Commit
```
git add frontend/fonts.html frontend/historial.html
git commit -m "feat(fpo): fonts i historial mostren PIMEC i Foment"
```

---

## Fase 6 — Verificació (abans de donar el pla per fet)

**Preparació** (des de `fp-cercador/backend`; `backend/data/` és a `.gitignore`, no es versiona):

```
python3 -c "from scrapers.pipeline import refresh_ext_cursos; print(refresh_ext_cursos('data'))"
python3 app.py &     # API a :5001
cd ../frontend && python3 -m http.server 8080 &     # frontend a :8080
```
Esperat: `{'pimec': ~417, 'foment': ~150}`. Obrir `http://localhost:8080/index.html?mode=fpo`.

> **Navegador:** el projecte té una nota d'ús: `chrome-devtools-mcp` controla la pestanya
> **real** de l'usuari. Utilitzar **Playwright MCP** (instància aïllada) o **demanar abans a
> l'usuari** i deixar que ho comprovi ell. Captures fora del repo.

**Llista de comprovacions:**

1. La nota superior parla del SOC i d'«altres entitats formadores» (CA i, en canviar a ES, castellà), sense llistar-les.
2. El desplegable **Font** mostra SOC/PIMEC/Foment; **Tipus** mostra Subvencionat,
   Bonificable, Diàleg Social (subvencionat), Altres (i els del SOC no tenen insígnia de tipus).
3. Filtrar `Font = PIMEC` → només files amb insígnia PIMEC; el recompte coincideix amb
   `curl -s localhost:5001/api/fpo/especialitats | python3 -c "import sys,json;print(sum(e['font']=='pimec' for e in json.load(sys.stdin)['especialitats']))"`.
4. Filtrar `Tipus = Bonificable` → només files PIMEC amb aquesta insígnia.
5. Una fila PIMEC amb "Dates a concretar": desplegar-la mostra "Dates a concretar", cap
   adreça buida, enllaç "Fitxa del curs" que obre `pimecformacio.org`.
6. Una fila Foment: es veu horari en text, hores, centre i enllaç a `fomentformacio.com`.
7. Buscar una fila amb edicions acabades: la insígnia **Finalitzat** surt a les edicions
   passades i van al final; el filtre "Estat d'inscripció" no en trenca res.
8. Les files SOC es veuen **igual que abans** (codi, cursos, "Fitxa al SOC", estat).
9. Amb sessió: ☆ una fila PIMEC → a `perfil.html#fpo` surt amb l'etiqueta PIMEC i, en marcar
   un curs, es veu correctament; un curs acabat surt com "Curs finalitzat".
10. `fonts.html` mostra les dues seccions noves (CA/ES); `historial.html` mostra la
    columna "Font" (les entrades noves de PIMEC/Foment després d'un refresc).
11. Consola del navegador sense errors d'Alpine (`x-text`/`x-for`).

Aturar els servidors: `kill $(lsof -tiTCP:5001 -sTCP:LISTEN)` i
`kill $(lsof -tiTCP:8080 -sTCP:LISTEN)`; comprovar amb `lsof` que els ports són lliures
(`pkill -f 'python3 app.py'` no els mata a macOS).

---

## Fase 7 — Desplegament (NOMÉS amb ordre explícita de l'usuari)

Segons `reference_deploy_procedure`: confirmar amb l'usuari abans de fer `push`.

1. `git push cercador-grausfp master`.
2. `ssh contabo 'cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git status --short && git pull --ff-only'`
   (untracked normals: `venv/` i `fp-cercador/backend/scrapers/old_pdf_scraper.py`).
3. Hi ha canvis de backend (Pla 062/063): `systemctl restart fp-cercador`. No hi ha
   dependències noves (`requirements.txt` no canvia).
4. Generar `ext_cursos.json` al VPS **amb l'usuari del servei** (perquè pugui llegir-lo):
   `POST /api/admin/refresh-fpo` amb `Authorization: Bearer <ADMIN_TOKEN>` (l'usuari
   subministra el token; mai al repo) i seguir `GET /api/admin/fpo-status` fins a `done`.
   Tarda ~1–3 min. (Refresca també el SOC.)
5. Verificar a producció (`https://grausfp.masellas.info`): `curl -s …/api/fpo/especialitats`
   conté files amb `font: pimec` i `font: foment`; recàrrega forçada i repetir les
   comprovacions 1–8 de la Fase 6.

## Fora d'abast

- Mapa àrea→família definitiu de PIMEC (proposta al Pla 063; l'usuari pot ajustar-la).
- Millorar la família de Foment (només 5 de 141 títols porten codi de certificat: la majoria
  cau a "Formació complementària"). Possible pla futur: taula de paraules clau del títol.
- Integració amb certificats C (`/api/fpo/by-cert`) i cerca per ocupació.
