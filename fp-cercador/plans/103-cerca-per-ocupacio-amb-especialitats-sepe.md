# Pla 103 — Cerca per ocupació amb especialitats SEPE i prova dels «graus relacionats»

Prioritat P3 · Mida S–M · Depèn de: 100 · Idees 17 (cerca) i 16 (fase 2).
Executable per un agent sense context.

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

## Punt de partida

- El pla 100 deixa a `sepe_programes.json` les ocupacions de cada especialitat (`[{codi, nom}]`, codi de
  8 dígits, nom en castellà i majúscules).
- El mode «Cerca per ocupació» (`searchMode === 'ocupacio'`, `runOcupSearch`, endpoint a `app.py` vora
  `_CA_ES_TERMS`) cerca a `backend/data/ocupaciones.json`: 5.182 files, 4.493 oficis diferents, cada una
  amb `ocupacio`, `norm`, `grado`, `codigo`, `denominacion`, `familia`. **Només noms, sense codi**.

## Part 1 — Especialitats SEPE al mode ocupació

- Índex d'ocupacions SEPE (nom normalitzat → especialitats), construït en carregar `sepe_programes.json`.
- L'endpoint de cerca per ocupació retorna, a més dels graus, `sepe: [{codi, titol, hores, modalitat,
  ocupacions_coincidents}]`. Mateixa normalització i mateixes equivalències català–castellà que els graus.
- UI: el mateix patró de **dos blocs**: a dalt els graus que porten a l'ofici, a sota «Especialitats SEPE
  relacionades» amb l'etiqueta i l'enllaç a la fitxa (pla 101). Respectar el mur per a anònims que ja té
  el mode ocupació, si escau.
- Si moltes especialitats «PO» no tenen ocupacions (probable), dir-ho a la nota: «Només les especialitats
  amb ocupacions informades pel SEPE».

## Part 2 — Prova dels «graus relacionats» (decidir amb números)

- Creuar pel nom normalitzat les ocupacions de cada especialitat amb les de `ocupaciones.json`.
- Informe a `plans/outputs/sepe-graus-relacionats-<data>.md`: quantes especialitats tenen algun grau
  relacionat, distribució del nombre de graus per especialitat, i **30 exemples a l'atzar** per valorar-ne
  la qualitat a ull (inclou-hi SSCE22 i IFCD0025).
- **Aturar-se aquí i ensenyar l'informe al propietari.** Només si les relacions són bones es fa el bloc
  «Graus relacionats» a la fitxa (pla 101) i, simètricament, «Especialitats SEPE relacionades» a la
  pàgina de grau. Si no, es descarta i s'anota a `plans/README.md`.

## Tests

- Índex i cerca amb un fixture petit; equivalències català–castellà; especialitat sense ocupacions.
