# Pla 097 — Filtres i presentació de les especialitats SEPE al cercador

Prioritat P2 · Mida M · Depèn de: 096 · Idees 1, 2, 12, 13, 14 i 15.
Executable per un agent sense context. Només frontend i textos (i una ampliació d'equivalències al backend).

## Context comú (llegir abans de començar)

- Origen: sessió del 2026-11-26, després de desplegar el pla 082 (especialitats del SEPE al cercador
  principal). El propietari va repassar 21 idees una per una; aquest pla en recull les decisions.
  Llegir primer `plans/082-cataleg-estatal-especialitats-pagina.md` (secció «Canvi de decisió») i la
  «Diagnosi tècnica» de `plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md`.
- Peces que ja existeixen (pla 082): `backend/scrapers/sepe_scraper.py` (`build_sepe_data`,
  `fetch_programa_pdf`), `backend/app.py` (`_sepe_index`, `_sepe_llista`, `/api/sepe/especialitats`,
  `/api/sepe/programa/<codi>`), `frontend/index.html` (estat `sepe*`, getter `filteredSepe`, bloc
  `<section class="sepe-block">`, pestanya `filterGrado === 'SEPE'`), claus `sepe.*` a `frontend/i18n.js`.
- Convencions: codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA); text
  d'interfície en català i castellà a `i18n.js` (sense literals dins `x-text`); `x-if` amb una sola arrel.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines de `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`. En tocar `site.css`,
  `search-tools.js`, `footer.js` o `feedback.js`, pujar el seu `?v=`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (tot verd el 2026-11-26: 737) i `python3 -m pytest -q tests/test_sepe_scraper.py`. Frontend:
  `node scripts/test_search_tools.js`.
- `rg` no mira `backend/data/` (és a `.gitignore`): per buscar a les dades cal `rg -uu`.
- Deploy: `git push cercador-grausfp master`; `ssh contabo`, `git pull --ff-only` al directori del site;
  si hi ha canvis de backend, `systemctl restart fp-cercador`. **Mai reiniciar durant un refresc**
  (`curl localhost:8033/api/refresh-status`). Confirmar sempre amb el propietari abans de desplegar.

## Decisions preses amb el propietari

- **Dos blocs, no una taula barrejada**: graus a dalt, especialitats SEPE a sota, cadascun amb les seves
  columnes. Les especialitats no donen títol oficial i això ha de quedar clar.
- Els filtres nous surten **només a la pestanya «Especialitats SEPE»** (`filterGrado === 'SEPE'`).

## Dades (catàleg del 2026-11-14)

- Nivell: 1 → 1.671, 2 → 2.195, 3 → 1.374, 4 → 162, 5 → 23, sense especificar → 2.119. És el «nivel de
  cualificación profesional» (escala de 5 nivells del Catàleg Nacional de Qualificacions, la mateixa dels
  graus; la FP arriba al 3). **Verificar el text legal** (Ordre TMS/283/2019 o la norma que el substitueixi)
  abans d'escriure l'explicació. El número indica dificultat, no dona cap acreditació.
- Modalitat: «Presencial y teleformación» 4.266, «Presencial» 2.338, «Presencial y mixta» 618,
  «Teleformación» 305, «Mixta» 17.
- Hores: de 2 a 1.300, mediana 50. <10: 367; 10–30: 1.709; 30–60: 2.175; 60–100: 1.285; 100–200: 1.119;
  200–400: 698; >400: 191.

## Què s'ha de fer (`frontend/index.html`, `frontend/i18n.js`)

1. **Nivell (idea 1).** A la pestanya SEPE, el desplegable de nivell ofereix 1–5 i «Sense especificar».
   A la resta de pestanyes es queda en 1–3. Text d'ajuda (`title`) a la capçalera «Nivell» de la taula
   SEPE i un paràgraf a `per-que-grausfp.html#sepe`: mateixa escala que els graus, 4 i 5 per sobre de la
   FP, el número indica dificultat i no titulació. «Sense especificar» continua amb guionet a la taula.
2. **Modalitat (idea 2).** Desplegable amb 3 opcions: «Es pot fer a distància» (Teleformación + Presencial
   y teleformación), «Amb una part presencial» (Mixta + Presencial y mixta), «Només presencial». La columna
   continua mostrant el valor literal. Nota curta: la modalitat diu què **permet** el catàleg, no què
   s'ofereix ara (això ho resol el pla 099).
3. **Durada (idea 12).** Desplegable amb 4 trams: fins a 30 h; 30–100 h; 100–300 h; més de 300 h.
   Fer la taula SEPE **ordenable** per denominació, codi i hores (mateix patró `sortBy` de la taula de graus,
   amb `aria-sort`).
4. **Bloc SEPE visible (idea 14).**
   - Si cap grau coincideix: la taula de graus es redueix a una línia («Cap grau A–E coincideix») i el
     bloc SEPE puja. Ara es mostra la taula buida sencera (clau `sepe.mainEmpty`).
   - Si hi ha graus **i** especialitats: una línia sota el comptador de resultats, «També hi ha N
     especialitats del SEPE ↓», que fa scroll fins al bloc (`id="sepe-h"`).
5. **Textos (idea 15).** `index.mode.nom`: «Cerca per nom o codi» / «Buscar por nombre o código».
   `index.hero.sub`: «Explora els graus de FP i la formació per a l'ocupació» (+ ES). No es toquen
   `index.tabs.all`, el placeholder ni el títol de pàgina. La targeta d'entrada «Què vol dir Grau A, B, C,
   D, E?» s'amplia perquè també enllaci `per-que-grausfp.html#sepe` (no afegir-ne una quarta).
6. **«Volies dir…» (idea 13).** `didYouMean` només suggereix quan no hi ha res **ni** a graus **ni** a
   SEPE, i el vocabulari (`GFPSearch.buildVocabulary`) inclou els títols SEPE quan estan carregats.
   Afegir tests a `scripts/test_search_tools.js` si es toca `search-tools.js`.
7. **Equivalències català–castellà (idea 13).** Treure les ~300 paraules més freqüents dels títols SEPE
   i afegir a `_CA_ES_TERMS` (`backend/app.py`) les equivalències que faltin. Si el pla 098 ja és fet,
   afegir-les a la taula editable en lloc del codi. `tests/test_ocupaciones_synonyms.py` compara el
   diccionari amb el que rep el frontend: mantenir-lo verd.
8. Els filtres nous s'han d'incloure al botó «Esborrar filtres» i a `resetPage()`. Estat a l'adreça:
   opcional; si es fa, validar els valors a `search-tools.js` com la resta.

## Verificació

- Al navegador (local): `?grado=SEPE` amb cada filtre; «moodle» (cap grau, especialitats a dalt);
  «administración» (línia «També hi ha N…»); una errada de tecleig que només existeix al SEPE.
- a11y: `label` a cada desplegable, focus visible, capçaleres ordenables amb teclat.
- CA i ES. Mòbil: els filtres no desborden.

## Fora d'abast

- Filtres SEPE fora de la pestanya SEPE. Filtre per categoria transversal.
