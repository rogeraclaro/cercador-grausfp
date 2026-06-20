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

- [ ] **Q1 — Què vol dir "unificar"?** (un sol camp que ho cerqui tot / commutador de mode /
      només coherència visual i navegació entre pàgines)
- [ ] Q2 — Idioma: acceptem que cercar per ocupació segueix sent només ES, o és bloquejant?
- [ ] Q3 — Forma del resultat unificat (taula única? targetes? híbrid?)
- [ ] Q4 — Criteri d'èxit (com sabrem que la unificació és "millor" que tenir-los separats?)

## Registre de decisions

(buit — s'omplirà a mesura que les tanquem)

## Pròxima passa

Resoldre **Q1** (què vol dir unificar) amb l'usuari — pregunta conceptual, al terminal.
