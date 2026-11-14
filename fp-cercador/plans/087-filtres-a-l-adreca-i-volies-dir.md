# Pla 087 — Cerca compartible (filtres a l'adreça) i «Volies dir…»

Origen: auditoria 2026-11-14, idea 7 de 9. El propietari la va triar; les decisions tècniques
d'aquest pla són del redactor i es poden discutir abans d'executar-lo.
Executable per un agent sense context, en una sessió nova. Només toca `frontend/index.html`,
`frontend/i18n.js` i les versions de memòria cau. Sense backend.

## Què fa

1. Qualsevol cerca del mode «per nom» queda reflectida a l'adreça i es pot compartir o desar
   a les adreces d'interès.
2. Quan una cerca no dona cap resultat, el cercador proposa fins a tres termes semblants
   («Volies dir *soldadura*?»).

## Fets verificats (2026-11-14, no repetir)

- Estat de la cerca a `index.html` (component Alpine): `search`, `filterGrado`,
  `filterFamilia`, `filterNivel`, `filterOld` (`all`/…), `filterFavs`, `sortCol`, `sortDir`,
  `currentPage`, `searchMode`.
- Paràmetres que la pàgina ja llegeix en carregar:
  - `mode=ocupacio|fpo`, `esp=<codi>` (FPO);
  - `ref=…` / `oferta=…` (obre els centres d'un grau), `grado=X&ref=…|codigo=…|id=…`
    (tornada de l'itinerari; es treuen de l'adreça després d'un sol ús);
  - **`q=…` i `grado=X` sense `ref`** (afegit el 2026-11-14 per als enllaços de l'observatori):
    posen `search` i `filterGrado`.
- L'estat també es desa a `sessionStorage['grausfp.listState']` (`saveListState` /
  restauració, ~línies 2478–2510) per tornar de l'itinerari.
- La cerca normalitza (NFD, minúscules) i expandeix termes català→castellà amb `expandSearch`
  i `caEs` (`/api/ca-es-terms`). El resultat es memoritza a `filteredMemo`.
- Missatge de cap resultat: fila buida de la taula (~línia 3830), claus `index.empty*`.
- El catàleg té ~13.000 registres; les denominacions són en castellà.

## Disseny

### Adreça
- Paràmetres: `q`, `grado`, `familia`, `nivel`, `pla` (el valor de `filterOld` quan no és
  `all`), `favs=1`, `ordre=<col>` i `dir=desc`, `p=<pàgina>` (només si > 1). Els valors per
  defecte no s'escriuen: una cerca buida deixa l'adreça neta.
- Escriptura amb `history.replaceState` (no `pushState`: escriure una paraula no ha d'omplir
  l'historial del navegador), amb un retard de 300 ms després de l'últim canvi.
- Lectura en carregar, **després** del catàleg i abans de pintar, amb validació: `grado` ha
  de ser A–E, `nivel` 1–3, `familia` ha d'existir a `families`, `q` es retalla a 200
  caràcters. Un valor invàlid s'ignora en silenci.
- Prioritat en carregar: adreça > `sessionStorage` (tornada de l'itinerari) > valors per
  defecte. Si l'adreça porta algun paràmetre de cerca, no es restaura `sessionStorage`.
- No s'ha de trencar res del que ja es llegeix (`mode`, `esp`, `ref`, `oferta`, la tornada
  de l'itinerari). `favs=1` sense sessió s'ignora.
- Només el mode «per nom». Els modes ocupació i FPO conserven els seus paràmetres actuals.
- El botó «Comparteix» de la fila i l'enllaç a l'itinerari no canvien.

### «Volies dir…»
- Només quan `q` té 4 lletres o més, el resultat és buit **i** no hi ha cap altre filtre
  actiu (si n'hi ha, el missatge ja proposa treure'ls).
- Vocabulari: les paraules de 4 lletres o més de totes les denominacions, normalitzades,
  amb el nombre de registres on surten. Es construeix un sol cop, la primera vegada que cal
  (no en carregar), i es desa en memòria.
- Candidats: paraules a distància d'edició ≤ 2 de la paraula escrita (≤ 1 si en té 4 o 5),
  ordenades per distància i després per freqüència. Per a una consulta de diverses
  paraules, es corregeix només la que no té cap coincidència.
- Abans, la paraula es passa per l'expansió català→castellà: si l'usuari escriu en català i
  el terme ja es tradueix, no cal suggerir res.
- Fins a 3 suggeriments, com a botons que posen la cerca. Si no n'hi ha cap, el missatge de
  cap resultat queda com ara.
- Rendiment: la distància d'edició es calcula amb tall anticipat (abandona quan supera el
  llindar) i només contra paraules de longitud ±2. Objectiu: menys de 50 ms amb el catàleg
  sencer. Mesura-ho.

## Fases

1. **Adreça — lectura i escriptura.** Funcions pures `stateFromParams(params, families)` i
   `paramsFromState(state)` dins el `<script>` d'`index.html`, fora del component, perquè es
   puguin provar. Prova amb un script de Node a `scripts/` que n'extregui el codi (o
   copieu-les a un fitxer de prova): anada i tornada de tots els camps, valors invàlids,
   valors per defecte que no s'escriuen.
2. **Integració** amb `init()`, `saveListState` i la restauració. Comprovar a mà les quatre
   entrades: adreça amb filtres, tornada de l'itinerari, enllaç de l'observatori
   (`?grado=D&q=…`), enllaç del perfil (`?ref=…`).
3. **«Volies dir…»**: vocabulari, distància amb tall, suggeriments i marcatge accessible
   (`role="status"`, botons amb nom).
4. **Textos** (`index.didyoumean.*`, ca i es), `?v=` i `I18N_VERSION`.
5. **Verificació al navegador**, ca i es: compartir una cerca amb tres filtres i obrir-la en
   una finestra nova; `soldadra` → `soldadura`; `infermeria` (català, ja traduït) no ha de
   suggerir res si dona resultats; una paraula sense res semblant no mostra el bloc; el botó
   enrere del navegador no queda ple d'estats intermedis; 375 px.

## STOP — atura't i pregunta

- Si la lectura de l'adreça entra en conflicte amb la tornada de l'itinerari d'una manera
  que aquest pla no preveu, descriu el cas abans de triar.
- Si el càlcul de suggeriments passa de 100 ms, ensenya la mesura i dues alternatives
  (vocabulari més petit o índex per trigrames) abans d'optimitzar.
- No desplegar sense aprovació explícita.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
