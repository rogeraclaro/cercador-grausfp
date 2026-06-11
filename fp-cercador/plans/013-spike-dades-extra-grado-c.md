# Plan 013: [SPIKE — direcció] Investigar l'enriquiment dels Grados C amb dades del buscador de certificats

> **Executor instructions**: Aquest és un pla d'INVESTIGACIÓ, no de
> construcció. El lliurable és un document de disseny, NO codi de producció.
> No modifiquis cap fitxer fora de `plans/outputs/`. Si es dona una STOP
> condition, atura't i informa. En acabar, actualitza la fila d'aquest pla
> a `plans/README.md`.
>
> **Drift check**: cap (no toca codi). Verifica només que
> `backend/scrapers/buscador_scraper.py` encara existeix i exposa `ficha_id`
> als registres (`grep -n "ficha_id" backend/scrapers/buscador_scraper.py`).

## Status

- **Priority**: P3 (opcional — decisió de producte)
- **Effort**: M (investigació)
- **Risk**: LOW (cap canvi de codi)
- **Depends on**: cap
- **Category**: direction
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Els registres del Grado C (Certificados de Profesionalidad, 981 registres)
mostren avui només denominació, codi, família i nivell. El "Buscador de
Certificados de Profesionalidad" del ministeri exposa, per a cada
certificat LOE, dades molt més útils per a l'usuari final: **referència BOE,
fitxa PDF, durada en hores, centres on s'imparteix i suplement Europass**.
Aquesta investigació ja es va apuntar com a fase futura del projecte (les
notes internes indiquen que el buscador de certificats accepta consultes
POST). El cercador ja envia `ficha_id` per a cada registre A/B/C
(`buscador_scraper.py:121`), o sigui que la clau d'encreuament
probablement ja existeix al pipeline.

## Current state (fets verificats al codi)

- `backend/scrapers/buscador_scraper.py` — `_map_record` (línies 113–122)
  inclou `'ficha_id': item.get('id')` a cada registre A/B/C.
- `frontend/index.html` (línies 834–845) — les files A/B/C amb `ficha_id`
  ja són clicables cap a la fitxa de todofp.es; el cas
  `row.grado === 'C' && row.plan_antiguo` té un tractament especial.
- El pipeline actual fa 1 bootstrap + 9 GETs i triga ~4s; qualsevol
  enriquiment per-registre (981 certificats) podria multiplicar el temps de
  refresh — això és LA pregunta de disseny central.

## Scope

**In scope**: crear `plans/outputs/spike-grado-c.md` (i opcionalment
scripts d'exploració llançats a mà, NO desats al repo fora de
`plans/outputs/`).

**Out of scope**: QUALSEVOL canvi a `backend/`, `frontend/` o `deploy/`.
Cap scraping massiu (límita les proves a <10 peticions de mostra, amb
els headers `User-Agent`/`Referer` que ja usa el projecte).

## Steps (preguntes a respondre, en ordre)

### Step 1: Cartografiar la font

Identifica l'URL i el contracte del buscador de certificats
(todofp.es / SEPE). Documenta: endpoint(s), mètode (POST?), paràmetres,
format de resposta, i si cal sessió/cookies (prova si el patró bootstrap
de `buscador_scraper._bootstrap_session` hi funciona).

### Step 2: Mapejar camps

Amb 3–5 certificats de mostra (p. ex. un de cada nivell), documenta quins
camps retorna la font (BOE, durada, centres, Europass, PDF) i amb quina
clau es creuen amb els registres existents (codi del certificat? el
`ficha_id` del buscador de graus? denominació normalitzada?). Anota
percentatge esperat de matching.

### Step 3: Decidir l'estratègia d'integració (amb trade-offs)

Compara com a mínim:
- **(a) Enriquiment al pipeline**: +981 peticions per refresh — quant temps
  afegiria? Acceptable per a un refresh setmanal en background?
- **(b) Enriquiment on-demand**: endpoint backend
  `/api/certificado/<codigo>` que consulta la font quan l'usuari obre el
  detall — latència per a l'usuari, cap cost al refresh.
- **(c) Pipeline separat**: refresh mensual independent dels certificats,
  fitxer de dades propi.

Recomana'n una amb justificació quantificada.

### Step 4: Esbossar l'impacte al model de dades i a la UI

Quins camps nous tindria el registre, com es mostrarien a `index.html`
(columna? fila expandible?), i impacte en la mida d'`ofertes.json`.

### Step 5: Llistar riscos i preguntes obertes

Fragilitat de l'scraping POST, ritme de canvis de la font, càrrega que li
imposem, i tot allò que necessiti decisió del propietari.

## Done criteria

- [ ] `plans/outputs/spike-grado-c.md` existeix i respon els Steps 1–5
- [ ] Inclou exemples reals de request/response (anonimitzats si cal)
- [ ] Inclou una recomanació d'estratègia amb números (temps, peticions, bytes)
- [ ] Cap fitxer fora de `plans/` modificat (`git status`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- La font requereix captcha real o autenticació que no es pot satisfer amb
  el patró bootstrap → documenta-ho com a conclusió del spike i tanca.
- Les proves de mostra reben errors 403/429 → atura les peticions
  immediatament (no insistir contra el servidor del ministeri) i documenta.

## Maintenance notes

- Si el spike conclou "viable", el pas següent seria un pla de construcció
  nou (no improvisar la implementació des del spike).
- La decisió final és del propietari: aquest document és material de
  decisió, no un compromís.
