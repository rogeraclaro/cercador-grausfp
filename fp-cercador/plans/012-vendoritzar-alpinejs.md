# Plan 012: Vendoritzar Alpine.js localment i documentar l'excepció a la constraint

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada comanda
> de verificació i confirma el resultat esperat abans de passar al pas següent.
> Si es dona qualsevol condició de la secció "STOP conditions", atura't i
> informa — no improvisis. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> `git diff --stat 5dc92a1..HEAD -- frontend/index.html`
> Si la línia del CDN ja no existeix, STOP (potser ja s'ha vendoritzat).

## Status

- **Priority**: P3
- **Effort**: S
- **Risk**: LOW
- **Depends on**: cap
- **Category**: tech-debt / disponibilitat
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

El cercador principal (`index.html`) depèn d'Alpine.js carregat des del CDN
de jsdelivr: si el CDN cau, és bloquejat (adblockers, xarxes corporatives)
o és lent, **tot el cercador queda mort** — la pàgina no renderitza cap
resultat. Servir el fitxer (~45 KB) des del mateix nginx que ja serveix el
frontend elimina el punt de fallada extern, millora la privacitat (cap
petició a tercers) i la latència. A més, el `CLAUDE.md` del projecte
declara la constraint "HTML/CSS/JS vanilla — sense frameworks frontend",
que Alpine contradiu: cal documentar l'excepció perquè futurs agents no
"arreglin" el codi eliminant Alpine o, a l'inrevés, hi afegeixin més
frameworks emparant-s'hi.

## Current state

- `fp-cercador/frontend/index.html:699`:
  ```html
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"></script>
  ```
  Tot el comportament de la pàgina (cerca, filtres, paginació, ordenació)
  és un component Alpine (`Alpine.data('cercador', ...)`, línies 569–697).
- `frontend/` no té cap subdirectori `vendor/`.
- `CLAUDE.md` de l'arrel del repo git, secció "Constraints":
  ```
  - **Tech Stack**: Flask + HTML/CSS/JS vanilla — sense frameworks frontend; requisit explícit del propietari
  ```
- `admin.html` i `historial.html` són JS vanilla pur (no usen Alpine) — no
  es toquen.
- nginx serveix `frontend/` com a root estàtic
  (`deploy/nginx-cloudpanel.conf`: `root .../fp-cercador/frontend;`), així
  que `frontend/vendor/alpinejs-3.15.11.min.js` quedarà servit a
  `/vendor/alpinejs-3.15.11.min.js` sense tocar nginx.

## Commands you will need

| Propòsit | Comanda (des de `fp-cercador/`) | Esperat |
|---|---|---|
| Descarregar Alpine | `mkdir -p frontend/vendor && curl -fsSL -o frontend/vendor/alpinejs-3.15.11.min.js "https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"` | exit 0 |
| Validar mida | `wc -c frontend/vendor/alpinejs-3.15.11.min.js` | > 40000 bytes |

## Scope

**In scope**:
- `frontend/vendor/alpinejs-3.15.11.min.js` (crear)
- `frontend/index.html` (només la línia 699)
- `CLAUDE.md` de l'arrel del repo git (només la línia de la constraint)

**Out of scope**:
- Canviar la versió d'Alpine (es manté exactament la 3.15.11 que ja corre).
- Reescriure `index.html` a vanilla pur — decisió del propietari, fora
  d'aquest pla.
- `admin.html`, `historial.html`.

## Git workflow

- Un commit a `master`: `chore(frontend): vendoritzar Alpine.js 3.15.11 (treure dependència del CDN)`
- NO push sense instrucció.

## Steps

### Step 1: Descarregar Alpine al directori vendor

```bash
mkdir -p frontend/vendor
curl -fsSL -o frontend/vendor/alpinejs-3.15.11.min.js \
  "https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"
```

**Verify**:
```bash
wc -c frontend/vendor/alpinejs-3.15.11.min.js
head -c 200 frontend/vendor/alpinejs-3.15.11.min.js
```
→ mida > 40.000 bytes i el contingut comença amb codi JS minificat (no HTML
d'error).

### Step 2: Apuntar index.html al fitxer local

A `frontend/index.html:699`, canvia:
```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.11/dist/cdn.min.js"></script>
```
per:
```html
<script defer src="vendor/alpinejs-3.15.11.min.js"></script>
```

(Ruta relativa: index.html i vendor/ pengen del mateix root estàtic, i així
funciona també obrint el fitxer en local.)

**Verify**: `grep -n "cdn.jsdelivr" frontend/*.html` → buit.

### Step 3: Smoke test al navegador

1. `cd backend && python app.py`
2. Obre `frontend/index.html` al navegador.
3. Confirma que el cercador carrega resultats, els filtres de grado
   funcionen i la paginació respon (tot això és Alpine: si el fitxer local
   no es carrega, la pàgina queda en estat "loading" o buida).
4. A la pestanya Network de DevTools: cap petició a `cdn.jsdelivr.net`.

### Step 4: Documentar l'excepció al CLAUDE.md

Al `CLAUDE.md` de l'arrel del repo git, canvia la línia de la constraint per:

```markdown
- **Tech Stack**: Flask + HTML/CSS/JS vanilla — sense frameworks frontend; requisit explícit del propietari. Excepció acceptada: Alpine.js 3.x (vendoritzat a `frontend/vendor/`, sense CDN) per a la reactivitat d'`index.html`. No afegir-ne cap altre.
```

**Verify**: `grep -n "Alpine" ../CLAUDE.md` → 1 resultat (executa des de
`fp-cercador/`; el CLAUDE.md del projecte és al directori pare).

## Test plan

Sense tests automatitzats (estàtic frontend). La verificació funcional és
l'smoke test del Step 3 — no el saltis: és l'única comprovació que el fitxer
vendoritzat és funcional.

## Done criteria

- [ ] `frontend/vendor/alpinejs-3.15.11.min.js` existeix, > 40 KB, JS vàlid
- [ ] `grep -rn "cdn.jsdelivr" frontend/` → buit
- [ ] El cercador funciona al navegador sense cap petició a jsdelivr
- [ ] `CLAUDE.md` documenta l'excepció d'Alpine
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

Atura't i informa si:

- El `curl` falla o retorna HTML/error en lloc de JS (sense el fitxer
  correcte NO facis el canvi d'index.html — la pàgina moriria).
- `index.html` ja no usa Alpine (redisseny posterior) — el pla seria
  irrellevant.
- L'smoke test del Step 3 falla amb el fitxer local però funciona amb el
  CDN (fitxer corrupte — torna a descarregar i compara).

## Maintenance notes

- Per actualitzar Alpine en el futur: descarregar la nova versió a
  `frontend/vendor/alpinejs-<versió>.min.js`, canviar la línia d'index.html
  i esborrar l'antiga — el nom de fitxer versionat fa el canvi explícit i
  evita problemes de cache.
- El fitxer vendoritzat es versiona al git expressament (és una dependència
  fixa, no un artefacte de runtime — no entra en conflicte amb el pla 010).
- Revisor: diff d'index.html ha de ser exactament 1 línia.
