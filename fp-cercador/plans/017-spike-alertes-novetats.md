# Plan 017: [SPIKE — F3] Dissenyar les alertes personalitzades de novetats

> **Executor instructions**: Aquest és un pla d'INVESTIGACIÓ I DISSENY, no de
> construcció. El lliurable és un document de disseny a `plans/outputs/`, NO
> codi de producció. Si es dona una STOP condition, atura't i informa. En
> acabar, actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Context obligatori**: llegeix primer `plans/futures/ROADMAP-FEATURES.md`
> (F3, i la relació amb F4 i el pla 014) i `plans/outputs/spike-login.md`
> (output del pla 016 — esquema de BD i decisió d'email).

## Status

- **Priority**: P2 (onada 3 del roadmap — la "killer feature" del login)
- **Effort**: M (disseny; construcció posterior M)
- **Risk**: LOW (cap canvi de codi en aquest pla)
- **Depends on**: plans/016-spike-login-fonament.md (esquema BD + email);
  plans/005 i 006 DONE (format final de `history.compute_changes`)
- **Category**: direction
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

És la raó de pes perquè un usuari es registri i torni: "avisa'm quan surti
un grau nou que m'interessi". El cost marginal és baix perquè la matèria
primera ja existeix: cada refresh setmanal calcula exactament les altes i
baixes per grau (`history.compute_changes` → `new_by_grado`,
`new_families`...). Falta el matching amb subscripcions d'usuari i
l'enviament. Si el disseny és bo, F4 (seguiment de centres, post-pla-015)
serà el mateix motor amb una font més.

## Current state (fets del codebase rellevants)

- `backend/history.py` (post-plans 005/006): a cada refresh,
  `compute_changes` produeix `new_denominacions`, `new_by_grado`
  ({grado: [denominacions]}), `new_families`, i els equivalents `removed_*`.
  El refresh corre setmanalment via APScheduler (`scheduler_service.py`) i
  manualment des del panell admin — el hook natural per disparar el matching
  és just després de `history.append(result)`.
- Els registres tenen `familia`, `grado`, `nivel`, `denominacion`, `codigo` —
  els eixos de subscripció possibles.
- El pla 014 (feed RSS) és la versió anònima d'això: si es construeixen tots
  dos, han de compartir la font de veritat (les entrades de changes), no
  duplicar lògica.
- Email i BD: decidits al spike 016 (no re-obrir aquelles decisions aquí;
  si l'output del 016 no existeix, STOP).

## Scope

**In scope**: crear `plans/outputs/spike-alertes.md`.

**Out of scope**: canvis a codi; re-decidir email/BD (són del 016); decidir
si les alertes són gratuïtes o premium (decisió de producte del propietari —
llistar-la com a pregunta oberta).

## Steps (decisions a documentar)

### Step 1: Model de subscripció

Quins eixos pot combinar una alerta: família, grado, nivell, text lliure
sobre denominació (com es matcheja: substring normalitzat com fa el cercador
— vegeu la normalització NFD d'`index.html` — o paraules?), i en el futur
província/centre (F4). Esquema de taula (coherent amb l'esquema del 016) i
límits raonables (màx. N alertes/usuari?).

### Step 2: Motor de matching

On s'executa: hook després de `history.append` (mateix procés) vs job
APScheduler separat. Com es garanteix exactament-un-enviament per novetat
(idempotència si el refresh es repeteix el mateix dia; registre
d'enviaments). Què passa amb les baixes (`removed_*`) — s'alerta també?

### Step 3: L'email

Format del correu de novetats (digest setmanal vs immediat — recomanació),
plantilla (text pla + HTML senzill), enllaç de gestió/baixa de subscripció
SENSE login (token signat — important per a la fricció i per complir
normativa anti-spam), i volum estimat (usuaris × freqüència setmanal —
encaixa amb el límit del proveïdor SMTP triat al 016?).

### Step 4: UI

On viu la gestió d'alertes (pàgina nova `alertes.html`? secció dins d'un
futur "el meu compte"?). Esbós dels estats: crear alerta des d'una cerca
feta ("converteix aquesta cerca en alerta" — la cerca actual ja té tots els
filtres als seus inputs), llistar, esborrar, pausar.

### Step 5: Relació amb el feed RSS (pla 014) i F4

Com comparteixen font: proposta d'una funció única "novetats normalitzades
per consum extern" que alimenti feed públic + matching privat. Què haurà
d'afegir F4 quan existeixin snapshots de centres (no dissenyar F4, només
deixar-hi l'endoll).

### Step 6: Pla de construcció proposat

Plans de construcció seqüenciats amb estimació (model+matching; email;
UI), i el "primer increment demostrable" (p. ex. alerta per família amb
digest setmanal).

## Done criteria

- [ ] `plans/outputs/spike-alertes.md` existeix i cobreix els Steps 1–6
- [ ] L'esquema de subscripcions encaixa amb el del spike 016 (mateixa BD)
- [ ] Inclou exemple complet d'un email de digest (mock amb dades reals de l'historial)
- [ ] Inclou la decisió d'idempotència (com no enviar dues vegades el mateix)
- [ ] Llista de preguntes obertes per al propietari (gratis/premium, immediat/digest, alertar baixes?)
- [ ] Cap fitxer fora de `plans/` modificat (`git status`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- `plans/outputs/spike-login.md` no existeix o no fixa email/BD → executa
  primer el pla 016.
- Els plans 005/006 no estan DONE → el format de `compute_changes` seria una
  diana mòbil.

## Maintenance notes

- El matching de text lliure ha de reutilitzar la MATEIXA normalització que
  el cercador (NFD + lowercase) perquè "què veu l'usuari al cercador" i "què
  li arriba per alerta" coincideixin sempre.
- Quan el pla 015/F4 es construeixi, tornar aquí i estendre el motor amb la
  font de centres — el disseny ha d'haver deixat l'endoll preparat (Step 5).
