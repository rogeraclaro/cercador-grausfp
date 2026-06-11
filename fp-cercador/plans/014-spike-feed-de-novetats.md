# Plan 014: [SPIKE — direcció] Dissenyar un feed de novetats (RSS/JSON) sobre l'historial de canvis

> **Executor instructions**: Aquest és un pla d'INVESTIGACIÓ I DISSENY, no
> de construcció. El lliurable és un document de disseny, NO codi de
> producció. No modifiquis cap fitxer fora de `plans/outputs/`. Si es dona
> una STOP condition, atura't i informa. En acabar, actualitza la fila
> d'aquest pla a `plans/README.md`.
>
> **Drift check**: verifica que els plans 005 i 006 estan DONE a
> `plans/README.md`; si no, STOP (aquest spike dissenya sobre el format
> d'historial resultant d'aquells plans).

## Status

- **Priority**: P3 (opcional — decisió de producte)
- **Effort**: S-M (disseny)
- **Risk**: LOW (cap canvi de codi)
- **Depends on**: plans/005-historial-del-refresh-programat.md, plans/006-aprimar-historial-i-gzip.md
- **Category**: direction
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

El backend ja calcula, a cada refresh, exactament el que un subscriptor
voldria saber: **quins ensenyaments nous s'han publicat i quins han
desaparegut, per grado** (`history.compute_changes` → `new_by_grado`,
`removed_by_grado`, `new_families`...). Avui aquesta informació només es pot
consultar visitant `historial.html`. Un feed RSS/Atom o JSON Feed la faria
subscrivible (lectors RSS, automatitzacions, newsletters de tercers) amb un
cost d'implementació petit: una ruta Flask que transforma l'historial
existent. És "the adjacent possible": la dada ja existeix; només falta el
format de sortida.

Públic plausible: orientadors acadèmics, centres de FP, portals educatius
que vulguin assabentar-se de noves titulacions sense vigilar el BOE.

## Current state (fets verificats al codi)

- `backend/history.py` (post-plans 005/006): entrades amb
  `ts, total, by_grado, unknown_families, duration_seconds, changes`, on
  `changes.new_by_grado` és `{grado: [denominacions...]}`.
- `backend/app.py`: rutes públiques sense auth ja existents
  (`/api/refresh-history`, `/api/next-refresh`) — el feed seguiria el mateix
  patró.
- Constraint del projecte: dependències limitades (Flask + 5 llibs) — el
  disseny ha de generar el XML/JSON **sense afegir cap dependència** (RSS
  2.0 és prou simple per a un template string; JSON Feed és JSON pla).

## Scope

**In scope**: crear `plans/outputs/spike-feed-novetats.md`.

**Out of scope**: QUALSEVOL canvi a `backend/`, `frontend/`, `deploy/`.

## Steps (decisions a documentar)

### Step 1: Triar el format

Compara RSS 2.0, Atom i JSON Feed per a aquest cas (compatibilitat amb
lectors, complexitat de generació sense dependències noves, escapat XML de
les denominacions — recordeu el precedent XSS del pla 009). Recomana'n un
(o RSS + JSON tots dos si el cost marginal és trivial).

### Step 2: Definir el contracte

- Ruta proposada (p. ex. `/api/feed.xml` o `/feed`), headers de cache.
- Què és un "item": un refresh amb canvis? Un ensenyament nou individual?
  (Trade-off: granularitat vs. soroll — un refresh amb 88 altes, són 88
  items o 1?)
- GUID estable per item (clau: no re-notificar el mateix canvi).
- Com es comporta amb refreshos sense canvis (s'ometen?).

### Step 3: Esbossar la implementació

Pseudocodi de la ruta Flask (lectura de `history.HISTORY_PATH`,
transformació, escapat), estimació de línies (~50?), tests necessaris, i
com es publicita el feed (un `<link rel="alternate">` a `index.html` i
`historial.html`).

### Step 4: Riscos i preguntes obertes

P. ex.: les entrades d'historial roten (HISTORY_MAX=20) — n'hi ha prou per
a un feed o cal persistència pròpia? Cal i18n (denominacions en castellà,
UI en català)?

## Done criteria

- [ ] `plans/outputs/spike-feed-novetats.md` existeix i cobreix els Steps 1–4
- [ ] Inclou un exemple complet del feed generat (mostra de 2 items)
- [ ] Inclou estimació d'esforç del pla de construcció resultant
- [ ] Cap fitxer fora de `plans/` modificat (`git status`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- Els plans 005/006 no estan fets (el format d'historial seria una diana
  mòbil).

## Maintenance notes

- Si el propietari aprova el disseny, escriure un pla de construcció nou
  seguint la plantilla dels plans 001–012.
- La decisió de fer-ho o no és de producte; aquest spike només deixa la
  decisió ben informada.
