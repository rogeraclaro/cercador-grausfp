# Pla 054 — Verbositat dels processos admin + gestió de canvis de centres

Escrit i executat dins la mateixa sessió (no pensat per a un executor sense
context — no cal Drift check ni STOP conditions elaborades).

## Context

Sessió del 2026-09-05/06. Ja aplicat abans d'aquest pla (commits previs,
no repetir):

- Fix del missatge "cap centre marcat" quan una oferta no té cap centre.
- Enllaç intern pels graus C de pla antic (`index.html?oferta=X`).
- Noms de pestanyes del perfil més explícits (Alertes de nous ensenyaments /
  Seguiment de centres).
- Verbositat de fase al refresh d'ofertes i al scraping de centres
  (`pipeline.py`, `centres_scraper.py`, `refresh_state.py`, `app.py`,
  `admin.html`) — **ja fet i desplegat**.
- Auto-marcar l'oferta com a favorita en seleccionar el primer centre
  (`toggleCentreSelect` a `index.html`) — **ja fet**.

Pendent (aquest pla):

1. Icona de favorit coherent al perfil (cor SVG, no ★).
2. Resum de centres nous/eliminats al final del scraping.
3. Catàleg de centres acumulatiu (base per als punts 4 i 5).
4. Resaltat visual dels centres nous dins de cada oferta (`index.html`).
5. Centre desaparegut es manté al perfil amb llegenda.
6. Historial del refresc de centres (data, durada) reaprofitant l'historial
   d'ofertes existent / observatori.

## Fase 1 — Icona de favorit coherent (`perfil.html`)

Substituir el botó `★` (`.btn-fav-remove`) per el mateix SVG de cor que
`index.html` (`.btn-fav`), amb el mateix comportament visual (buit/ple,
color warm/vermell). Sense canvis de backend.

**Verificació:** desplegar i mirar visualment que perfil i index mostren la
mateixa icona.

## Fase 2 — Catàleg de centres acumulatiu (`centres_scraper.py`)

Ara mateix `centres_by_id` es reconstrueix sencer a cada scraping — un
centre que deixa d'impartir cap oferta desapareix per sempre, sense rastre.

Canvi: a l'inici de `scrape_centres()`, carregar el `centres.json` existent
(si hi és) com a base de `centres_by_id`, en lloc de començar buit. Els
centres que continuen apareixent s'actualitzen (dades noves sobreescriuen
les velles); els que no es tornen a veure en cap oferta d'aquest run
**es mantenen** al catàleg amb les seves últimes dades conegudes.

Aquest canvi és la base tècnica que fa possibles les fases 4 i 5. Sense
ell, un centre desaparegut no es pot mostrar enlloc perquè no hi ha dades
seves.

**Verificació:** córrer els tests existents de centres (si n'hi ha) +
inspecció manual: after a scraping, comprovar que un id de centre present
abans i absent del run nou encara existeix a `centres.json` (amb les dades
antigues).

## Fase 3 — Resum nous/eliminats al final del scraping

Backend (`app.py`, dins `admin_refresh_centres._run`): abans de cridar
`build_centres_data()`, guardar el conjunt d'ids de `_centres_index`
actual (pot ser buit si és el primer run). Després del scraping, comparar
amb el nou `_centres_index` i calcular `centres_nous` (ids nous) i
`centres_eliminats` (ids que hi eren i ja no surten en cap oferta —
diferent de "esborrats del catàleg", que amb la Fase 2 mai passa; aquí
"eliminat" vol dir que ja no aparegui a cap entrada de `oferta_centres`).
Guardar els comptadors (no la llista sencera) a `_centres_scrape_state`.

Frontend (`admin.html`): mostrar al resum final, a banda del que ja hi ha,
una línia "X centres nous · Y centres que ja no apareixen a cap oferta".

**Verificació:** provar amb dades locals petites (mock) simulant un centre
que desapareix i un que apareix; comprovar els comptadors al JSON de
`/api/admin/centres-status`.

## Fase 4 — Resaltat de centres nous dins de cada oferta (`index.html`)

Backend: exposar, a banda de `oferta_centres.json`, quins ids de centre són
"nous" respecte al run anterior — comparant per oferta (no només
globalment). Guardar-ho en un fitxer petit `centres_nous_per_oferta.json`
(`{oferta_key: [centre_id, ...]}`) generat al mateix pas que la Fase 3,
només amb els que són realment nous per aquella oferta concreta (puc ja
tenir-los d'aquell càlcul, per evitar duplicar feina).

Frontend: a `index.html`, quan es despleguen els centres d'una oferta,
pintar un badge petit "Nou" al costat dels que apareguin a la llista de
nous per aquella oferta_key.

**Verificació:** desplegar una oferta amb algun centre marcat com a nou i
comprovar visualment el badge.

## Fase 5 — Centre desaparegut es manté al perfil amb llegenda

Depèn de la Fase 2 (catàleg acumulatiu) perquè les dades del centre (nom,
localitat) han de seguir existint encara que ja no aparegui a
`oferta_centres[oferta_key]`.

Backend (`app.py`, `loadFavorits` flow): quan es demanen els centres d'una
oferta per a un usuari amb `centreIds` seleccionats, si algun `centre_id`
seleccionat no apareix a la resposta normal de `/api/centres`, buscar-lo
igualment a `centres_index` (catàleg) i retornar-lo amb un flag
`actiu: false` (o similar).

Frontend (`perfil.html`, `loadFavorits`): si `c.actiu === false`, mostrar
el chip igual però amb una llegenda "Ja no imparteix aquest grau" (i sense
opció d'eliminar-lo amb el mateix pes visual que un actiu — decidir estil
al moment).

**Verificació:** simular un centre marcat que desapareix d'una oferta i
comprovar que apareix al perfil amb la llegenda, no que desapareix sense
rastre.

## Fase 6 — Historial del refresc de centres

Reaprofitar el mòdul `history.py` existent (usat per `admin_refresh` /
ofertes). Afegir una entrada equivalent quan acaba
`admin_refresh_centres._run` (data, durada, total_centres, total_ofertes,
centres_nous, centres_eliminats — reaprofitant els comptadors de la Fase
3). Marcar el tipus d'entrada (`"kind": "centres"` vs `"kind": "ofertes"`,
o el que ja faci servir `history.py` si distingeix tipus) perquè la pàgina
d'historial existent (i l'Observatori, si mostra aquest historial) pugui
distingir-les.

**Verificació:** després d'un scraping de centres, comprovar que apareix
una entrada nova a `/api/refresh-history` i que la pàgina que la consumeix
la mostra sense trencar-se amb les entrades existents de tipus ofertes.

## Ordre d'execució

Fase 1 (independent) → Fase 2 (base) → Fase 3 (usa Fase 2 indirectament,
en realitat no la necessita estrictament però s'implementa a la vegada) →
Fase 4 → Fase 5 (necessita Fase 2) → Fase 6 (independent, es pot fer en
qualsevol moment després de tenir els comptadors de la Fase 3).

Cada fase es desplega i verifica abans de passar a la següent. No fer
`systemctl restart` al VPS si hi ha un scraping de centres en curs.
