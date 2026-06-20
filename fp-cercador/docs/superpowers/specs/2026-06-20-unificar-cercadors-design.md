# Disseny: Unificar el cercador d'ocupació amb el cercador principal

> **Estat: DISSENY APROVAT (2026-06-20)** — pendent escriure el pla executable a `plans/`.
> Aquest document és l'àncora de continuïtat entre sessions i l'spec de referència.
> El disseny final aprovat és a la secció "## Disseny final (aprovat)".

- **Data inici**: 2026-06-20
- **Branca de treball**: (cap encara — brainstorm en `master`)
- **Skill**: brainstorming (superpowers) amb company visual acceptat

## Com reprendre aquesta feina (per a una sessió nova)

1. Llegeix aquest document sencer (sobretot el "Registre de decisions" i "Pregunta oberta actual").
2. Si cal, repassa l'estat real del codi amb els punters de la secció "Context del codi".
3. Continua per la "Pròxima passa".

## Problema / objectiu

Avui hi ha **dos cercadors separats** i l'usuari vol unificar-los. Què vol dir
"unificar" exactament és la primera cosa a decidir (veure preguntes obertes).

## Context del codi (verificat 2026-06-20, commit 50fdf89)

### Cercador principal — `frontend/index.html` (~2.108 línies, Alpine.js)
- Component Alpine `cercador`. `allRecords` = catàleg complet (~12.894 registres) carregat en memòria.
- Cerca de text (`x-model.debounce.250ms="search"`): **substring** sobre `_normDen`
  (denominació normalitzada NFD) + `_normCod` (codi). Veure `get filteredRecords()` (~línia 1256).
- Filtres addicionals: grau, família, nivell, pla antic (radio), favorits.
- Camps per registre: `codigo, denominacion, familia, grado, nivel, plan_antiguo, id, _normDen, _normCod`.
- Resultat = **taula** rica: centres per oferta, favorits, exporta CSV, itineraris F5, watch centres.
- Tot client-side, en temps real.

### Cercador d'ocupació — `frontend/ocupacions.html` (vanilla JS) + `/api/ocupaciones`
- Pàgina separada, JS vanilla (sense Alpine). Crida `GET /api/ocupaciones?q=`.
- Backend (`backend/app.py`, `api_ocupaciones`): **match per paraula completa** (`\b`) sobre
  `norm` dels noms d'ocupació. Dades **només en castellà**. Agrupa per grau
  (clau `codigo` per C, `id` per D/E), rankeja per nº d'ocupacions coincidents.
- Índex: `backend/data/ocupaciones.json` (gitignored, ~5.398 entrades, generat per
  `scripts/generate_ocupaciones.py`). Camps: `ocupacio, norm, grado, codigo, id, denominacion, ficha_url, familia`.
- Resultat = **targetes** agrupades per grau, amb les ocupacions coincidents i enllaç a fitxa.

### Tensions clau per a la unificació
1. **Font de dades**: catàleg en memòria (client) vs endpoint servidor (ocupacions).
2. **Semàntica de match**: substring (denom+codi) vs paraula completa (ocupacions).
3. **Forma de resultat**: taula (amb centres/favorits/CSV/itineraris) vs targetes per grau.
4. **Idioma**: catàleg cercable en la denominació mostrada vs ocupacions només ES.
5. **Tecnologia**: Alpine (index) vs vanilla (ocupacions).

## Preguntes obertes (a resoldre durant el brainstorm)

- [x] **Q1 — Què vol dir "unificar"?** → **RESOLT: commutador de mode** (opció B). Veure registre.
- [ ] Q2 — Idioma: acceptem que cercar per ocupació segueix sent només ES, o és bloquejant?
- [ ] Q3 — Forma del resultat unificat (taula única? targetes? híbrid?)
- [ ] Q4 — Criteri d'èxit (com sabrem que la unificació és "millor" que tenir-los separats?)

## Registre de decisions

### D1 (2026-06-20) — Model d'unificació: commutador de mode
Una **sola pàgina** (`index.html`) amb un commutador **"Cerca per nom" / "Cerca per ocupació"**.
Cada mode manté la seva UI òptima: taula rica per nom (com ara), targetes per grau per ocupació.
NO es barregen les semàntiques de cerca en una sola caixa. Implicació tècnica: la lògica
d'`ocupacions.html` (vanilla) s'ha de portar dins del component Alpine d'`index.html`; el
backend `/api/ocupaciones` es reutilitza tal qual. `ocupacions.html` com a pàgina separada
probablement desapareix (a confirmar al disseny).

### D2 (2026-06-20) — "Cerca per ocupació" gated darrere login
El mode "Cerca per ocupació" és **només per a usuaris registrats**. Reutilitza el patró de
gating existent (Plans 027–029 DONE: centres i alertes; modal reutilitzable tipus
`showCentresModal()`). **PENDENT confirmar la granularitat**: gate total (cal login per usar el
mode) vs *preview per anònims* (com centres: mostra'n uns quants i convida a registrar-se).
Trade-off a tenir present: gating redueix la descobribilitat (el contrari del que feia atractiva
la unificació), però l'objectiu del propietari és impulsar registres.

## Preguntes obertes addicionals (sorgides al brainstorm)

- [x] **Q-repr** → **RESOLT: opció 2, preferència d'usuari** (veure D3).
- [x] **Q-gate-gran** → **RESOLT: preview + mur** (com centres, Pla 027). Veure D4.
- [x] Q-repr-default → **RESOLT: Targetes** (default; també el que veu l'anònim al preview).
- [x] Q-repr-persist → **RESOLT: `localStorage`** (v1 sense canvis backend; BD com a millora futura).

Nota Q2 (idioma) i Q3/Q4 originals: Q2 → acceptat (ocupacions segueixen sent **només ES** en v1;
traducció CA↔ES és millora futura ja documentada a [[project-f6-spike]]). Q3 → resolt per D3
(targetes o taula, a elecció). Q4 (criteri d'èxit) → recollit a "Criteris d'èxit" més avall.

### D3 (2026-06-20) — Representació: preferència d'usuari (opció 2)
El registrat tria entre dues representacions del **mateix** conjunt de resultats d'ocupació:
- **"Targetes"** (= C): targetes per grau amb ocupacions coincidents + enllaç a fitxa.
- **"Taula"** (= A unificat): el cercador ric (taula) filtrat als graus que han coincidit per
  ocupació, amb marca "Coincideix: [ocupació]" per fila; manté centres/favorits/itineraris/CSV.
  Tècnicament viable reutilitzant la taula existent: els resultats de `/api/ocupaciones` (grau
  amb `codigo`/`id`) es mapegen a registres del catàleg i s'alimenten al mateix renderitzador.
Commutador de representació inline a la barra del mode ocupació. Default i persistència: pendents
(Q-repr-default, Q-repr-persist).

### D4 (2026-06-20) — Gating: preview + mur
El mode "Cerca per ocupació" segueix el patró de centres (Pla 027): l'anònim pot cercar i veure
els **primers 3 resultats**; la resta queda tapada amb un mur convidant a registrar-se. Manté
descobribilitat (SEO, prova abans de registre) i empeny el registre.

## Disseny final (aprovat)

Mockup de referència: `.superpowers/brainstorm/.../content/design-final.html` (gitignored).

### Arquitectura
- **Tot a `frontend/index.html`** (component Alpine `cercador` existent). Cap framework nou.
- Nou estat `searchMode: 'nom' | 'ocupacio'`, amb un **commutador** a dalt al costat de la caixa de cerca.
- **Mode "nom"** = comportament actual SENSE canvis (substring sobre denom+codi, filtres, taula rica).
- **Mode "ocupació"** = es porta la lògica de `frontend/ocupacions.html` (vanilla) dins del component
  Alpine; consumeix el `GET /api/ocupaciones?q=` **existent** (cap canvi de backend).

### Components / estat nou (Alpine)
- `searchMode` ('nom' default).
- `ocupQuery`, `ocupResults` (resposta de `/api/ocupaciones`), `ocupLoading`.
- `reprOcup: 'targetes' | 'taula'` — default **'targetes'**, persistit a **`localStorage`**.
- Debounce de la cerca d'ocupació (com el mode nom, ~250ms).

### Representacions del resultat d'ocupació (D3)
1. **Targetes** (default): targetes per grau amb les ocupacions coincidents. Cada targeta porta
   **les dues accions**: "Veure al cercador →" (pont) i "Fitxa ↗".
2. **Taula**: es mapegen els graus de `ocupResults` (clau `codigo` per C, `id`/`grado` per D/E) als
   registres ja a `allRecords` i es renderitzen amb la **taula existent**, afegint una marca
   "Coincideix: [ocupacions]" per fila. Manté centres/favorits/itineraris/CSV.
   - *Escape hatch*: si algun grau de `/api/ocupaciones` no casa amb cap registre d'`allRecords`
     (codis que no reconcilien — limitació coneguda F6), es mostra igualment com a targeta/fila
     mínima amb el que torni l'API; NO es perd el resultat. Documentar-ho.
- **"Veure al cercador →"**: posa `searchMode='nom'` i filtra pel grau/codi d'aquella targeta.

### Gating (D4 — preview + mur, patró Pla 027)
- **Anònim**: pot cercar per ocupació i veure els **primers 3 resultats**; la resta, tapada amb
  un mur "Registra't" (reutilitza el patró/modal de centres del Pla 027).
- **Registrat**: tots els resultats + commutador de representació Targetes/Taula.
- El límit (3) i el text del mur reutilitzen el mecanisme existent de gating de centres.

### `ocupacions.html`
- Deixa d'existir com a pàgina autònoma. L'enllaç del footer d'`index.html`
  (`index.footer.ocupacions`) passa a `index.html?mode=ocupacio`; en carregar, el component
  llegeix `?mode=` i posa `searchMode` en conseqüència. (Query param, no hash: enllaçable i
  llegible al càrrec inicial sense dependre de l'historial.) Si hi havia enllaços externs a
  `ocupacions.html`, es deixa un redirect mínim a `index.html?mode=ocupacio`.
- Es retiren `frontend/ocupacions.html` i les seves claus i18n específiques que ja no s'usin
  (revisar quines reutilitza el mode nou abans d'esborrar).

### i18n
- Reutilitzar les claus `ocupacions.*` existents on apliqui; afegir claus noves per al commutador
  de mode, el commutador de representació i el mur de gating (CA + ES).

### Criteris d'èxit
- Des d'`index.html`, un usuari pot alternar "nom"/"ocupació" sense recarregar.
- Cercar "soldador" en mode ocupació retorna graus; "Veure al cercador" porta a la fila del catàleg.
- L'anònim veu 3 resultats + mur; el registrat els veu tots i pot canviar Targetes/Taula (recordat).
- Mode "nom" intacte (cap regressió a la cerca actual).
- `ocupacions.html` ja no és necessària; l'enllaç antic continua funcionant (redirigeix al mode).

### Fora d'abast (v1)
- Traducció/sinònims CA↔ES de les ocupacions (segueix només ES) — millora futura ([[project-f6-spike]]).
- Persistència de la preferència a BD (v1 és localStorage).
- Barrejar les dues semàntiques de cerca en una sola caixa (descartat a D1).
- Rànquing semàntic d'ocupacions.

### Riscos / notes de manteniment
- `index.html` ja és gran (~2.100 línies); el mode ocupació afegeix estat i markup. Vigilar que el
  component Alpine no creixi inmanejable; considerar separar la lògica d'ocupació en funcions netes.
- Reutilitzar EXACTAMENT el patró de gating del Pla 027 per no divergir.
- Recordar [[feedback_alpine_xif_single_root]] (x-if requereix un sol element arrel) en afegir els
  blocs condicionals de mode/representació.

## Pròxima passa

Escriure el pla executable a `plans/048-unificar-cercadors.md` (estil improve, autocontingut), o
via writing-plans. Aquest doc és l'spec de referència.
