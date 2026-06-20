# Disseny: Unificar el cercador d'ocupació amb el cercador principal

> **Estat: BRAINSTORM EN CURS** (no és un pla executable encara).
> Aquest document és l'àncora de continuïtat entre sessions. Es va omplint
> decisió a decisió. Quan estigui complet i aprovat → es genera un pla a `plans/`.

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
- [ ] Q-repr-default — Representació per defecte. **Proposta: Targetes** (lleugera, = preview anònim). Confirmar al disseny.
- [ ] Q-repr-persist — On es desa la preferència. **Proposta: `localStorage`** (v1 sense canvis backend; BD com a millora futura). Confirmar al disseny.

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

## Pròxima passa

Presentar el disseny complet (amb mockup de l'estat final), confirmar Q-repr-default i
Q-repr-persist, obtenir aprovació per seccions → escriure spec final → writing-plans.
