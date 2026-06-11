# Plan 015: [SPIKE — direcció] Centres on s'imparteix cada grau (Espanya): fonts, estat d'impartició i contacte

> **Executor instructions**: Aquest és un pla d'INVESTIGACIÓ I DISSENY, no de
> construcció. El lliurable és un document de disseny a `plans/outputs/`, NO
> codi de producció. No modifiquis cap fitxer fora de `plans/outputs/`. Les
> proves contra fonts externes es limiten a peticions de mostra (<20 per
> font, amb els headers `User-Agent`/`Referer` que ja usa el projecte — vegeu
> `backend/scrapers/buscador_scraper.py:36-43`). Si es dona una STOP
> condition, atura't i informa. En acabar, actualitza la fila d'aquest pla a
> `plans/README.md`.
>
> **Drift check**: cap (no toca codi). Verifica només que els registres
> actuals porten les claus d'encreuament:
> `python3 -c "import json; r=json.load(open('backend/data/ofertes.json'))[0]; print(r.get('codigo'), r.get('ficha_id'))"`

## Status

- **Priority**: P3 (feature nova — decisió de producte del propietari)
- **Effort**: M-L (investigació; la construcció posterior serà L)
- **Risk**: LOW (cap canvi de codi en aquest pla)
- **Depends on**: cap (recomanat després de 005/006 si es vol reutilitzar la maquinària de snapshots)
- **Category**: direction
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

El propietari vol que cada grau del cercador enllaci amb **els centres que
l'imparteixen a tot l'Estat espanyol**, amb dades de contacte i distingint
l'estat d'impartició: impartit en el passat / inscripció oberta / anunciat.
És el salt de valor més gran possible per al producte (de "catàleg de títols"
a "on puc estudiar-ho"), però la informació està dispersa entre l'Estat i 17
comunitats autònomes. Aquest spike valida les fonts, tria l'estratègia
d'obtenció i deixa un disseny llest per convertir en pla(ns) de construcció.

## Mapa de fonts (investigació prèvia — 2026-06-10, verificar vigència)

Aquest mapa surt d'una investigació web feta en preparar el pla. És el punt
de partida del spike, no el seu resultat: cada afirmació s'ha de validar.

### Font 1 — Registre Estatal d'Entitats de Formació FP ⭐ (candidata primària)

- **URL**: `https://registrosfp.educacion.gob.es/registroestatalentidadesformacion/buscarPublico`
- Registre creat per la mateixa Llei Orgànica 3/2022 que defineix els Graus
  A–E: **tots els centres autoritzats a impartir ofertes del Sistema de FP**.
- Cercador públic amb filtres: tipus d'oferta (**Graus C, D, E** — segons
  todofp.es, "A i B estan inclosos en C" a efectes d'autorització de
  centres), **codi i denominació de l'oferta**, modalitat
  (presencial/semipresencial/virtual), família professional, nivell,
  CCAA/província/localitat, titularitat (pública/privada/concertada).
- Resultats: codi de centre, codi de ministeri, nom, tipus de grau,
  província, localitat, CCAA + una columna d'accions (presumiblement vista
  de detall — **validar si el detall té adreça/telèfon/email**).
- Té funció d'**exportació** quan el resultat filtrat és <500 files
  ("Para exportarlo, filtre a un número menor de registros") — possible via
  d'ingesta neta sense scraping de paginació.
- Referenciat des de: `https://www.todofp.es/como-cuando-y-donde-estudiar/donde-estudiar/como-buscar-tu-centro.html`

### Font 2 — Registro Estatal de Centros Docentes no universitarios (RCD)

- **URL aplicació**: `https://www.educacion.gob.es/centros`
- Tots els centres docents no universitaris d'Espanya (dades aportades per
  les CCAA), cercable per territori i ensenyament. És la font natural per
  **enriquir dades de contacte** (adreça, telèfon, email) a partir del codi
  de centre obtingut de la Font 1 (els codis de centre haurien de coincidir
  — validar).
- Existeix un "Nodo de Interoperabilidad Educativa" amb servei de consulta
  automatitzada del RCD (esmentat a educaLAB) — **validar si és accessible
  públicament**.

### Font 3 — SEPE (vessant laboral; Grados A/B/C i certificats)

- Buscadors de la seu electrònica del SEPE
  (`https://sede.sepe.gob.es/especialidadesformativas/RXBuscadorEFRED/...`):
  centres i entitats inscrites/acreditades per especialitat formativa i
  certificat professional, amb localització i dades. Complementa la Font 1
  per a l'oferta no reglada/laboral i la teleformació.
- Relacionat amb el pla 013 (spike dades extra Grado C) — coordinar.

### Font 4 — Dades obertes autonòmiques (fallback de contacte)

- Diverses CCAA publiquen directoris de centres en CSV (p. ex. el
  "Directorio de centros docentes de Andalucía" a datosabiertos de la
  Junta). Útils com a font de contacte si el RCD no s'hi presta; cost:
  17 formats diferents — només com a últim recurs.

### El forat: l'estat d'impartició ("passat / inscripció oberta / anunciat")

Cap font estatal publica l'estat d'inscripció. Estratègies a avaluar al
spike, de més barata a més cara:

- **(a) Snapshots propis + diff** ⭐: el projecte JA té la maquinària
  exacta per a això (`history.compute_changes` — plans 005/006). Si el
  refresh setmanal captura també "centre × oferta" de la Font 1, podem
  derivar: *anunciat/nou* = parella que apareix; *impartit en el passat* =
  parella que desapareix però la conservem marcada com a històrica;
  *vigent* = present a l'última captura. No dona "inscripció oberta", però
  dona el cicle de vida sense dependre de cap font addicional.
- **(b) Camps d'estat del mateix registre**: la vista de detall de la Font 1
  pot tenir dates d'autorització/vigència — validar al spike; si hi són,
  combinar amb (a).
- **(c) "Inscripció oberta" per CCAA**: els períodes d'admissió són
  competència autonòmica (17 portals, calendaris diferents). Recomanació a
  validar: NO scrapejar-los; com a primera versió, **enllaç profund** ("Com
  matricular-s'hi") al portal d'admissió de la CCAA del centre, mantingut
  com a taula estàtica de 17 URLs revisada manualment. Scraping de
  calendaris només si el propietari ho demana com a fase pròpia.

## Current state del codebase (fets verificats, per al disseny d'integració)

- Registres actuals (`backend/data/ofertes.json`, 12.894): cada un té
  `codigo` (p. ex. `IFC_C_0123_...`), `ficha_id` (A/B/C) o `ficha_url`
  (D/E), `familia`, `nivel`, `grado` — el `codigo` i la denominació són les
  claus naturals per creuar amb la Font 1 (que permet cercar per codi
  d'oferta).
- El pipeline (`backend/scrapers/pipeline.py`) triga ~4s i corre setmanalment
  en background; pot absorbir una segona passada de captura de centres si el
  volum ho permet (a quantificar al spike).
- Constraint de rendiment del frontend: el cercador ha de ser fluid; 12.894
  registres ja pesen 3,7 MB. **Els centres NO poden anar incrustats dins
  `ofertes.json`** — el disseny ha de proposar fitxer(s) separats
  (p. ex. `centres.json` + relació `codigo ↔ codi_centre`) i càrrega
  on-demand al frontend (fetch en obrir el detall d'un grau).
- Dependències permeses: les 6 actuals (cap llibreria nova).

## Scope

**In scope**: crear `plans/outputs/spike-centres-per-grau.md` (document de
disseny). Proves manuals de mostra contra les fonts (<20 peticions/font).

**Out of scope**: QUALSEVOL canvi a `backend/`, `frontend/`, `deploy/`.
Cap scraping massiu. Cap decisió de producte tancada (el document presenta
opcions amb recomanació; decideix el propietari).

## Steps (preguntes a respondre, en ordre)

### Step 1: Validar la Font 1 a fons (el gruix del spike)

Amb el navegador i/o curl (mostra petita):
1. Com s'envia la cerca (GET/POST, noms de paràmetres, sessió/cookies — el
   patró bootstrap de `buscador_scraper._bootstrap_session` hi funciona?).
2. La cerca per **codi d'oferta** retorna els centres d'un títol concret?
   Prova amb 3 títols coneguts (un C, un D, un E) i contrasta el resultat
   amb el cercador d'una CCAA per validar la completesa.
3. Què hi ha a la **vista de detall** d'un centre: adreça? telèfon? email?
   dates d'autorització/vigència de cada oferta?
4. Com funciona l'**exportació** (<500 files): format (CSV/Excel), URL,
   autenticació? És automatitzable?
5. **Estratègia d'enumeració més barata**: val més iterar per
   família×grado×CCAA (N consultes exportables) que per títol (12.894
   consultes)? Quantifica: nombre de consultes, files totals estimades,
   temps, i si cal throttling per respecte al servidor.
6. Confirmar el tractament dels Graus A i B ("inclosos en C"): com es
   mapeja un centre autoritzat per a un certificat C cap als A/B
   acumulables que el componen?

### Step 2: Validar l'enriquiment de contacte

1. Els codis de centre de la Font 1 coincideixen amb els del RCD (Font 2)?
2. El RCD exposa adreça/telèfon/email al detall públic? I el node
   d'interoperabilitat, és accessible?
3. Si el contacte no surt de 1+2, avaluar Font 4 (CSV autonòmics): quantes
   CCAA en publiquen i amb quins camps.

### Step 3: Dissenyar el model de dades i la integració

Proposar (amb mides estimades en bytes i nombre de registres):
- `centres.json`: catàleg de centres (codi, nom, titularitat, adreça,
  municipi, província, CCAA, contacte, geolocalització si n'hi ha).
- `oferta_centres.json` (o equivalent): relació `codigo_oferta ↔
  codi_centre` amb modalitat i estat (`vigent` / `historic` / `nou`),
  derivat de l'estratègia (a) de snapshots.
- Canvis al pipeline: passada nova? pipeline separat amb cadència pròpia
  (mensual?) per no allargar el refresh setmanal? Reutilització de
  `history.compute_changes` per al cicle de vida.
- Endpoints: `/api/centres?codigo=<oferta>` (on-demand) vs fitxer estàtic.
- UI: com es mostra al frontend (fila expandible amb llista de centres i
  filtre per província? comptador "N centres" a la taula?) — esbós, no
  implementació.

### Step 4: Estratègia per a "inscripció oberta"

Documentar l'opció recomanada (enllaç profund per CCAA amb taula estàtica de
17 URLs versionada al repo) amb la llista real de les 17 URLs d'admissió FP
verificades a mà, i el cost/risc de l'alternativa de scraping de calendaris
per si mai es vol.

### Step 5: Pla de construcció proposat

Tancar el document amb la seqüència de plans de construcció recomanada
(p. ex. 016: scraper de centres + dades; 017: API + frontend; 018: cicle de
vida/estats), cadascun amb estimació d'esforç i els seus riscos — perquè el
propietari pugui aprovar fases soltes.

## Done criteria

- [ ] `plans/outputs/spike-centres-per-grau.md` existeix i respon els Steps 1–5
- [ ] Inclou exemples reals de request/response de la Font 1 (mostra)
- [ ] Inclou la decisió d'enumeració quantificada (consultes × files × temps)
- [ ] Inclou el model de dades amb mides estimades i l'esbós d'UI
- [ ] Inclou la taula de 17 URLs d'admissió per CCAA (verificades a mà)
- [ ] Cap fitxer fora de `plans/` modificat (`git status`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- La Font 1 requereix captcha real o autenticació per cercar/exportar →
  documenta-ho, prova el fallback (Font 2 + cercadors CCAA) i replanteja la
  recomanació en lloc d'insistir.
- Respostes 403/429 de qualsevol font → atura les peticions immediatament
  (són servidors públics del ministeri) i documenta el límit observat.
- El detall de centre no té dades de contacte a CAP de les fonts 1, 2 ni 4
  → escala el dubte al propietari abans de dissenyar la resta (el valor de
  la feature canvia substancialment).

## Maintenance notes

- **Coordinar amb el pla 013**: el buscadorcertificados també llista centres
  per als Grados C (LOE) — si els dos spikes s'executen, el segon ha de
  llegir l'output del primer per no duplicar investigació ni decidir
  models de dades contradictoris.
- Les fonts són administració pública: estructura i URLs canvien sense
  avís. El document de disseny ha de datar cada verificació.
- La decisió final (construir o no, i amb quin abast de "estat
  d'impartició") és del propietari; aquest spike deixa la decisió ben
  informada i pressupostada.
