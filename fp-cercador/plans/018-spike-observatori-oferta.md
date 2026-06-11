# Plan 018: [SPIKE — F7] Dissenyar l'observatori públic de l'oferta FP

> **Executor instructions**: Aquest és un pla d'INVESTIGACIÓ I DISSENY, no de
> construcció. El lliurable és un document de disseny a `plans/outputs/`
> (amb un mockup HTML descartable opcional dins del mateix directori), NO
> codi de producció. Si es dona una STOP condition, atura't i informa. En
> acabar, actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Context obligatori**: llegeix primer `plans/futures/ROADMAP-FEATURES.md`
> (F7) — és la peça PÚBLICA de l'onada 1, sense login.

## Status

- **Priority**: P2 (onada 1 del roadmap — independent del login)
- **Effort**: S-M (disseny; construcció posterior M)
- **Risk**: LOW (cap canvi de codi en aquest pla)
- **Depends on**: plans/005 i 006 DONE (historial fiable i lleuger — la
  matèria primera)
- **Category**: direction
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Cada refresh setmanal acumula una foto del sistema FP espanyol (totals per
grado, altes i baixes per família). Avui aquesta sèrie temporal només es veu
com a taula d'historial. Convertida en un **observatori visual públic**
("la FP espanyola creix un X% aquest curs; les famílies que més titulacions
noves treuen són..."), és contingut que orientadors, premsa educativa i
centres enllacen — SEO i autoritat per al cercador, sense necessitar login
ni cap font nova. El cost és baix perquè la dada ja es genera sola.

## Current state (fets del codebase rellevants)

- `backend/data/refresh_history.json` (post-pla 006): fins a `HISTORY_MAX=20`
  entrades amb `ts`, `total`, `by_grado`, `duration_seconds`,
  `unknown_families` i `changes` (altes/baixes per grado i famílies).
  **Limitació clau**: 20 entrades ≈ 4-5 mesos de refreshos setmanals — per a
  sèries llargues caldrà persistència pròpia de l'observatori (decisió
  central del spike).
- `backend/data/last_snapshot.json` (post-pla 006): llistes completes del
  darrer refresh (denominacions per grado, famílies) — la foto "actual" per
  a distribucions (% per família, per nivell...).
- Frontend: 3 pàgines estàtiques; `historial.html` és el patró de pàgina
  pública amb fetch + render vanilla. Constraint: cap framework nou; per a
  gràfics, opcions a avaluar: SVG/canvas a mà, una microllibreria
  vendoritzada (com es va fer amb Alpine — pla 012), o gràfics
  server-side. La decisió és del spike.
- `/api/refresh-history` ja és públic — l'observatori pot menjar d'aquí o
  d'un endpoint agregat nou.

## Scope

**In scope**: crear `plans/outputs/spike-observatori.md` (+ mockup HTML
descartable opcional a `plans/outputs/`).

**Out of scope**: canvis a codi de producció; coses que necessitin login;
dades de centres (això arribarà amb el pla 015 — deixar-hi l'endoll, no
dissenyar-ho).

## Steps (decisions a documentar)

### Step 1: Persistència de la sèrie temporal

El problema de les 20 entrades: proposar un `observatory.json` (o taula
SQLite si el 016 ja s'ha construït) on cada refresh deixi UNA fila petita
(data, total, by_grado, n_altes, n_baixes, families_amb_altes) que no es
trunqui mai. Mida estimada a 10 anys vista (≈520 files × ~150 bytes — trivial).
On s'enganxa: el mateix hook post-`history.append`.

### Step 2: Quines visualitzacions (amb les dades que realment hi ha)

Triar 4–6 visualitzacions honestes amb la dada disponible, p. ex.:
evolució del total per grado (línies), altes per família (barres, acumulat
per curs), distribució actual per família i nivell (del snapshot), "últimes
novetats" (de l'historial — enllaçant al cercador filtrat). Marcar què és
possible AVUI vs què millora quan hi hagi sèrie llarga.

### Step 3: Com es renderitzen els gràfics

Avaluar: (a) SVG generat a mà en JS vanilla (zero dependències, més feina),
(b) microllibreria vendoritzada (quina? mida? llicència? — proposar 1-2
candidates concretes), (c) imatges/SVG generats al backend en el refresh
(zero JS, cache perfecte, menys interactiu). Recomanació amb trade-offs,
coherent amb la constraint "vanilla".

### Step 4: Pàgina i SEO

`observatori.html` seguint el patró d'`historial.html`. Títols i textos
pensats per a SEO (què cercaria un periodista/orientador), meta tags,
i si cal pre-renderitzar números al HTML per als crawlers (el frontend
actual és tot client-side — limitació a documentar honestament).

### Step 5: Pla de construcció proposat

Plans seqüenciats amb estimació (persistència + endpoint agregat; pàgina +
gràfics), primer increment demostrable (p. ex. 2 gràfics amb les dades
existents), i l'endoll futur per a dades de centres (post-015).

## Done criteria

- [ ] `plans/outputs/spike-observatori.md` existeix i cobreix els Steps 1–5
- [ ] La proposta de persistència resol la truncació de HISTORY_MAX
- [ ] Cada visualització proposada cita exactament quins camps la alimenten
- [ ] La decisió de gràfics respecta les constraints (vanilla / vendoritzat justificat)
- [ ] Cap fitxer fora de `plans/` modificat (`git status`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- Els plans 005/006 no estan DONE → la matèria primera (format d'historial)
  seria una diana mòbil.
- La temptació de "ja que hi som, construeixo la pàgina" → STOP, és un spike.

## Maintenance notes

- La fila setmanal de l'observatori és acumulativa i no es trunca: és
  l'únic lloc del sistema amb memòria llarga. Protegir-la a les còpies de
  seguretat del VPS.
- Quan es construeixi, afegir l'enllaç a l'observatori des d'`index.html` i
  `historial.html` (i al feed del pla 014 si existeix).
