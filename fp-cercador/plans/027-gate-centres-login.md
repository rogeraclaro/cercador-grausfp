# Pla 027: Panel de centres gated — preview de 3 per a usuaris no autenticats

> **Executor instructions**: Segueix el pla pas a pas. Executa cada comanda de
> verificació i confirma el resultat esperat abans de passar al pas següent. Si
> apareix qualsevol condició de STOP, para i informa — no improvisis. En acabar,
> actualitza la teva fila a `plans/README.md`.
>
> **Drift check (executa primer)**:
> `git diff --stat 78868c3..HEAD -- frontend/index.html frontend/auth.js`
> Si qualsevol dels fitxers en scope ha canviat des que el pla es va escriure,
> compara els extractes de "Current state" contra el codi viu. Si no coincideixen,
> tracta-ho com a condició de STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans/026-login-F1-D-hardening-deploy.md (login F1 DONE)
- **Category**: direction / feature
- **Planned at**: commit `78868c3`, 2026-06-15

## Why this matters

El sistema de login (plans 023–026) està en producció però cap feature de l'app
distingeix usuaris autenticats d'anònims. Aquest pla és el primer "gating" real:
el panel de centres queda restringit per incentivar el registre sense bloquejar
la navegació. L'usuari anònim veu 3 centres (teasers suficients per entendre el
valor), amb el desplegable CCAA i el cercador presents però no funcionals; qualsevol
interacció amb ells mostra un modal que convida al registre. L'usuari autenticat
manté l'experiència actual sense cap canvi.

## Current state

Un sol fitxer rellevant:

- `frontend/index.html` — tota la lògica (Alpine.js + CSS) en un sol fitxer;
  conté l'Alpine component `cercador`, el panel de centres i la comprovació
  d'autenticació inicial (via `auth.js` extern).

### Estructura del component Alpine (línies rellevants)

```js
// frontend/index.html:763–981
Alpine.data('cercador', () => ({
  // ...estat actual (no hi ha loggedIn ni centresModalVisible):
  centresCount: {},
  centresVisible: {},
  centresData: {},
  centresCCAA: {},
  centresLoading: {},
  centresSearch: {},

  async init() {                         // línia 788
    const res = await fetch(API_BASE + '/api/ofertes');
    // ...processa dades...
    this.state = 'ready';
    fetch(API_BASE + '/api/centres/count')   // fire-and-forget
      .then(r => r.json())
      .then(d => { this.centresCount = d; })
      .catch(() => { });
  },
  // ...
  centresFiltrats(row) { /* retorna array filtrat per CCAA+cerca */ },
  // ...
}));
```

### Template del panel de centres (línies rellevants)

```html
<!-- frontend/index.html:1169–1222 -->
<template x-if="centresVisible[row.id]">
  <tr class="centres-panel">
    <td colspan="5">
      <div class="centres-container">
        <div class="centres-header">
          <span x-text="centresFiltrats(row).length + ' / ' + (centresData[row.id] || []).length + ' centres'"></span>
          <select x-model="centresCCAA[row.id]">
            <template x-for="ccaa in ccaasDisponibles(row)" :key="ccaa">
              <option :value="ccaa" x-text="tc(ccaa)"></option>
            </template>
          </select>
          <input type="search" x-model="centresSearch[row.id]" placeholder="Cerca centre o població…"
            class="centres-search-input" @click.stop>
          <button @click.stop="centresVisible[row.id] = false">✕</button>
        </div>
        <div x-show="centresLoading[row.id]" class="centres-loading">Carregant centres…</div>
        <div x-show="!centresLoading[row.id]">
          <template x-for="centre in centresFiltrats(row).slice(0, 50)" :key="centre.id">
            <!-- ...card de centre... -->
          </template>
          <template x-if="centresFiltrats(row).length > 50">
            <p class="centres-more" x-text="'... i ' + (centresFiltrats(row).length - 50) + ' centres més'"></p>
          </template>
          <template x-if="centresFiltrats(row).length === 0 && !centresLoading[row.id]">
            <p class="centres-buit">Cap centre trobat per a aquesta comunitat.</p>
          </template>
        </div>
      </div>
    </td>
  </tr>
</template>
```

### CSS existent que reutilitzem

```css
/* frontend/index.html:611–613 */
[x-cloak] { display: none !important; }

/* Auth buttons existents (les reusem al modal): */
.auth-btn { /* color blanc sobre fosc */ }
.auth-btn--primary { background: var(--white); color: var(--dark); }
```

### `auth.js` (referència, NO modificar)

```js
// frontend/auth.js:9–10
const res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
if (res.ok) { /* mostra salutació */ } else { showGuestButtons(widget); }
```

L'endpoint `/api/auth/me` retorna 200+JSON si la sessió és vàlida, 401 si no.

## Commands you will need

| Propòsit | Comanda | Resultat esperat |
|----------|---------|-----------------|
| Tests Python | `cd /Users/rogermasellas/AI/Cercador\ Graus/fp-cercador && python -m pytest tests/ -q` | tots passen (els tests no cobreixen frontend) |
| Servidor dev local | `python app.py` (port 5001) | Flask running |
| Verificació manual | Obrir `http://localhost:8080` (o on serveixis el frontend) | veure la UI |

No hi ha tests automatitzats de frontend en aquest projecte.

## Scope

**En scope** (ÚNICS fitxers a modificar):
- `frontend/index.html`

**Fora de scope** (NO tocar):
- `frontend/auth.js` — ja gestiona el widget del topbar; NO afegir res aquí
- `backend/app.py` i qualsevol fitxer Python — cap canvi de backend necessari
- `frontend/login.html`, `frontend/register.html` — no s'ha de modificar
- `plans/README.md` — actualitzar-lo és la teva última acció

## Git workflow

- Branca: `feat/027-gate-centres-login`
- Commits: un per pas lògic; estil `feat(frontend): <què>` (segueix els commits recents del repo)
- NO fer push ni obrir PR tret que l'operador ho indiqui

## Steps

### Pas 1: Afegir variables d'estat al component Alpine

**Localitza** la secció d'estat del component a `frontend/index.html` (al voltant de la línia 781).
Troba la línia `centresSearch: {},` i afegeix immediatament a sota:

```js
centresSearch: {},

// Afegir:
loggedIn: false,
centresModalVisible: false,
```

**Verify**: `grep -n "loggedIn" frontend/index.html` → ha de retornar 1 línia amb la variable declarada.

---

### Pas 2: Fer check d'auth en paral·lel amb la càrrega d'ofertes

**Localitza** el mètode `async init()` (al voltant de la línia 788). Canvia la primera línia del `try`:

**Codi actual (línia ~790–791):**
```js
try {
  const res = await fetch(API_BASE + '/api/ofertes');
  if (!res.ok) { this.state = 'error'; return; }
```

**Substituir per:**
```js
try {
  const [res, authRes] = await Promise.all([
    fetch(API_BASE + '/api/ofertes'),
    fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
  ]);
  this.loggedIn = authRes.ok;
  if (!res.ok) { this.state = 'error'; return; }
```

Això fa les dues peticions en paral·lel (no afegeix latència) i emmagatzema l'estat
d'autenticació a `this.loggedIn`.

**Verify**: `grep -n "loggedIn = authRes.ok" frontend/index.html` → 1 resultat.

---

### Pas 3: Afegir el mètode `showCentresModal()` i `centresVisibles(row)`

**Localitza** el mètode `centresFiltrats(row)` (al voltant de la línia 942). Afegeix
els dos mètodes nous IMMEDIATAMENT A SOBRE de `centresFiltrats`:

```js
showCentresModal() {
  this.centresModalVisible = true;
},

centresVisibles(row) {
  const total = (this.centresData[row.id] || []).length;
  if (this.loggedIn || total <= 3) {
    return this.centresFiltrats(row).slice(0, 50);
  }
  return (this.centresData[row.id] || []).slice(0, 3);
},

centresFiltrats(row) {
  // ... codi original sense canvis ...
```

**Verify**: `grep -n "showCentresModal\|centresVisibles" frontend/index.html` → 2+ resultats.

---

### Pas 4: Afegir CSS per al modal, separador i missatge upsell

**Localitza** el bloc de CSS de centres (al voltant de la línia 615, secció `/* ── Centres per oferta ─...`).
Afegeix al FINAL d'aquest bloc (just abans de `/* Auth widget al topbar */`):

```css
/* Gating centres — modal + separator + upsell */
.centres-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.centres-modal {
  background: var(--white);
  border-radius: 8px;
  padding: 28px 32px;
  max-width: 380px;
  width: 90%;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.18);
}

.centres-modal-msg {
  font-size: 16px;
  font-weight: 500;
  color: var(--dark);
  margin-bottom: 20px;
  line-height: 1.4;
}

.centres-modal-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.centres-separator {
  border: none;
  border-top: 1px dashed var(--border);
  margin: 10px 0 8px;
}

.centres-upsell {
  font-size: 0.85rem;
  color: var(--warm);
  padding: 6px 0 2px;
  font-style: italic;
}

.centres-upsell a {
  color: #1a73e8;
  text-decoration: none;
  font-style: normal;
  font-weight: 500;
}

.centres-upsell a:hover {
  text-decoration: underline;
}
```

**Verify**: `grep -n "centres-modal-overlay\|centres-separator\|centres-upsell" frontend/index.html` → ≥3 resultats.

---

### Pas 5: Modificar el header del panel de centres

**Localitza** la línia del header count (al voltant de la línia 1175):
```html
<span x-text="centresFiltrats(row).length + ' / ' + (centresData[row.id] || []).length + ' centres'"></span>
```

**Substituir per** (usa `centresVisibles` per tenir el count correcte automàticament):
```html
<span x-text="centresVisibles(row).length + ' / ' + (centresData[row.id] || []).length + ' centres'"></span>
```

**Verify**: `grep -n "centresVisibles(row).length" frontend/index.html` → 1 resultat.

---

### Pas 6: Afegir interceptors als controls quan l'usuari no està autenticat

**Localitza** el `<select>` del desplegable CCAA (al voltant de la línia 1176):
```html
<select x-model="centresCCAA[row.id]">
```

**Substituir per:**
```html
<select x-model="centresCCAA[row.id]"
  @mousedown="if(!loggedIn){ $event.preventDefault(); showCentresModal(); }">
```

**Localitza** l'`<input type="search">` del cercador de centres (al voltant de la línia 1181):
```html
<input type="search" x-model="centresSearch[row.id]" placeholder="Cerca centre o població…"
  class="centres-search-input" @click.stop>
```

**Substituir per:**
```html
<input type="search" x-model="centresSearch[row.id]" placeholder="Cerca centre o població…"
  class="centres-search-input" @click.stop
  @focus="if(!loggedIn){ $event.target.blur(); showCentresModal(); }">
```

**Verify**:
```
grep -n "showCentresModal" frontend/index.html
```
Ha de retornar ≥3 resultats (declaració del mètode + mousedown + focus).

---

### Pas 7: Canviar la llista de centres per usar `centresVisibles`

**Localitza** el `<template x-for>` de la llista de centres (al voltant de la línia 1189):
```html
<template x-for="centre in centresFiltrats(row).slice(0, 50)" :key="centre.id">
```

**Substituir per:**
```html
<template x-for="centre in centresVisibles(row)" :key="centre.id">
```

**Verify**: `grep -n "centresVisibles(row)" frontend/index.html` → 2+ resultats.

---

### Pas 8: Afegir separador i missatge upsell; ajustar l'"X centres més"

**Localitza** el bloc `<div x-show="!centresLoading[row.id]">` (al voltant de la línia 1188).
Dins d'aquest bloc, després del `</template>` de la llista de centres i ANTES del bloc
`<template x-if="centresFiltrats(row).length > 50">`, afegeix:

```html
<!-- Separador + upsell per a usuaris anònims (quan hi ha >3 centres) -->
<template x-if="!loggedIn && (centresData[row.id] || []).length > 3">
  <div>
    <hr class="centres-separator">
    <p class="centres-upsell">
      <a href="register.html">Registra't per a veure-les totes</a>
    </p>
  </div>
</template>
```

**Modifica** el bloc "X centres més" (al voltant de la línia 1210) per afegir la condició `loggedIn`:

**Codi actual:**
```html
<template x-if="centresFiltrats(row).length > 50">
  <p class="centres-more" x-text="'... i ' + (centresFiltrats(row).length - 50) + ' centres més'">
  </p>
</template>
```

**Substituir per:**
```html
<template x-if="loggedIn && centresFiltrats(row).length > 50">
  <p class="centres-more" x-text="'... i ' + (centresFiltrats(row).length - 50) + ' centres més'">
  </p>
</template>
```

**Verify**:
```
grep -n "centres-separator\|centres-upsell\|loggedIn && centresFiltrats" frontend/index.html
```
Ha de retornar ≥3 resultats.

---

### Pas 9: Afegir el modal al DOM

**Localitza** el `</div><!-- /x-data -->` al final del body (línia ~1254). Afegeix el modal
IMMEDIATAMENT ABANS d'aquesta línia de tancament:

```html
    <!-- Modal gating centres -->
    <div x-show="centresModalVisible" @click="centresModalVisible = false"
         class="centres-modal-overlay" x-cloak>
      <div class="centres-modal" @click.stop>
        <p class="centres-modal-msg">Registra't per accedir a tota la informació</p>
        <div class="centres-modal-actions">
          <a href="register.html" class="auth-btn auth-btn--primary">Registra't</a>
          <button class="auth-btn" @click="centresModalVisible = false">Ara no</button>
        </div>
      </div>
    </div>
```

**Verify**: `grep -n "centresModalVisible" frontend/index.html` → ≥4 resultats (declaració, `x-show`, i els dos `@click`).

---

### Pas 10: Verificació manual al navegador

Serveix el frontend i verifica els dos camins:

**Setup:**
```bash
# Terminal 1: backend
cd /Users/rogermasellas/AI/Cercador\ Graus/fp-cercador
python app.py

# Terminal 2: frontend (qualsevol servidor estàtic)
cd frontend && python -m http.server 8080
```

**Camí A — usuari anònim (sense sessió):**
1. Obre `http://localhost:8080` en finestra d'incògnit (no hi ha sessió activa)
2. Cerca qualsevol oferta que tingui el badge blau "N centres" (N > 3)
3. Fes clic al badge → el panel ha d'obrir-se
4. **Comprova**: es veuen exactament 3 centres
5. **Comprova**: apareix una línia discontínua (separador) + "Registra't per a veure-les totes"
6. **Comprova**: el count diu "3 / N centres"
7. Fes clic al desplegable CCAA → apareix el modal "Registra't per accedir a tota la informació"
8. Tanca el modal (clic a "Ara no" o fora del modal) → el modal desapareix
9. Fes clic a l'input de cerca → apareix el modal (l'input NO rep el focus)
10. Fes clic a "Registra't" al modal → navega a `register.html`

**Camí B — usuari autenticat:**
1. Entra amb un compte vàlid
2. Obre el panel de centres del mateix grau
3. **Comprova**: es veuen tots els centres (sense límit de 3, sense separador, sense upsell)
4. **Comprova**: el desplegable CCAA i la cerca funcionen normalment

**Camí C — oferta amb ≤3 centres:**
1. Localitza una oferta amb 1, 2 o 3 centres (sense login)
2. **Comprova**: NO apareix ni separador ni upsell (tots els centres es veuen sense talls)

**Verify per a cada camí**: sense errors a la consola del navegador.

---

### Pas 11: Tests Python (regressió)

```bash
cd /Users/rogermasellas/AI/Cercador\ Graus/fp-cercador
python -m pytest tests/ -q
```

Resultat esperat: tots els tests passen (els canvis no toquen el backend).

---

### Pas 12: Actualitza `plans/README.md`

Canvia la fila del pla 027 a `DONE`.

## Test plan

No hi ha suite de tests de frontend en aquest projecte. La verificació és manual
(pas 10 d'aquest pla). Si en el futur s'afegeix Playwright o similar, els casos
a cobrir són:

- Usuari anònim: panel mostra 3 centres + separator + upsell; click CCAA → modal; click input → modal
- Usuari autenticat: panel funciona normalment sense cap element upsell visible
- Oferta amb ≤3 centres + usuari anònim: no apareix upsell (tots visibles)
- Modal: clic fora tanca el modal; clic "Ara no" tanca el modal; "Registra't" navega

## Done criteria

Tots han de ser certs:

- [ ] `grep -n "loggedIn" frontend/index.html` → ≥3 ocurrències (declaració + authRes.ok + condicions)
- [ ] `grep -n "centresModalVisible" frontend/index.html` → ≥4 ocurrències
- [ ] `grep -n "centresVisibles" frontend/index.html` → ≥4 ocurrències
- [ ] `grep -n "centres-separator\|centres-upsell" frontend/index.html` → ≥4 ocurrències
- [ ] Verificació manual camí A, B i C del pas 10 completada i sense errors de consola
- [ ] `python -m pytest tests/ -q` passa sense errors
- [ ] Únic fitxer modificat: `frontend/index.html` (`git status` no mostra res més)
- [ ] `plans/README.md` actualitzat a DONE per a la fila 027

## STOP conditions

Para i informa si:

- El codi als extractes de "Current state" no coincideix amb el codi viu (el repo ha
  canviat des que el pla es va escriure).
- El modal s'obre però `centresModalVisible` no torna a `false` al clicar fora (Alpine
  reactivity issue) → investiga però no reimplementis el sistema d'auth.
- `/api/auth/me` retorna 500 o errors CORS en local → comprova que el backend corre
  amb `python app.py` i que CORS té `supports_credentials=True` (ja configurat en commit
  `9d7d810`).
- L'import de `centresVisibles` en el template falla (Alpine error "centresVisibles is
  not a function") → verifica que el mètode s'ha afegit DINS de l'objecte `Alpine.data`
  i no fora.
- Qualsevol pas requereix modificar `auth.js`, `app.py` o fitxers fora de l'scope.

## Maintenance notes

- **Si s'afegeix més gating en el futur** (p. ex. detall Grado C o feed RSS),
  el patró és el mateix: `loggedIn` al component Alpine, `showCentresModal()` (o un
  mètode `showLoginModal()` renombrat genèric) per mostrar el prompt, i la comprovació
  a `init()` ja resol tota la pàgina d'un sol cop.
- **Si es vol fer el modal més genèric** (no específic de centres): renombrar
  `centresModalVisible` → `loginModalVisible` i moure el modal a un nivell superior.
  Deferred perquè ara mateix només hi ha un punt de gating.
- **`loggedIn` es calcula a `init()` i no canvia durant la sessió**. Si l'usuari
  fa logout sense recarregar (des del widget del topbar), el panel de centres
  seguirà mostrant dades completes fins a refresh. Acceptat: `auth.js` fa reload
  de pàgina en logout (`window.location.reload()`), per tant no és un escenari real.
- **El nombre màxim de centres visibles per a autenticats es manté a 50** (comportament
  actual de `centresFiltrats.slice(0, 50)`). Si en el futur s'elimina aquest limit, el
  canvi és a `centresVisibles()` i `centresFiltrats()`, no al template.
