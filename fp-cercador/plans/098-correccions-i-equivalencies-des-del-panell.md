# Pla 098 — Correccions de títols i equivalències de cerca des del panell d'administració

Prioritat P2 · Mida M · Depèn de: 096 · Idea 19 (i part de la 13).
Executable per un agent sense context.
**Estat: DONE i desplegat el 2026-11-26.**

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

## Motiu

- El SOC té errades als títols en català i no les podem arreglar a l'origen. Exemple vist pel
  propietari: IFCD0025, «Fonaments de programació amb HTML, CSS i JAVASCRIP» (el SEPE, en castellà, el té
  bé). No es poden detectar automàticament (comparar amb el castellà dona centenars de falsos positius).
- El propietari vol poder corregir-ho ell mateix en un minut, sense desplegar.
- La cerca en català funciona amb `_CA_ES_TERMS` i `_CA_ES_SUFFIXES` (`backend/app.py`, ~línia 2168),
  escrits dins el codi. Els oficis (4.493 de diferents a `ocupaciones.json`) només existeixen en castellà.
  Decisió: **no** traduir els oficis per mostrar-los; sí fer editables les equivalències de cerca.

## Què s'ha de fer

### 1. Correccions de títol (especialitats SEPE i FPO)

- Migració nova a `backend/migrations/` (fitxers SQL numerats; l'última és `016_feedback_oferta_ref.sql`,
  la següent és la `017`; `backend/db.py` les aplica soles en arrencar): taula `title_overrides(codi TEXT PRIMARY KEY, titol_ca TEXT, titol_es TEXT, original_ca TEXT,
  original_es TEXT, updated_at, updated_by)`.
- API (totes amb `_check_admin`): `GET /api/admin/title-overrides`, `PUT /api/admin/title-overrides/<codi>`
  (valida que el codi existeix a l'índex SEPE o SOC; longitud màxima; text pla), `DELETE …/<codi>`.
- Aplicació: en construir `_sepe_llista()` i `_soc_espec_index()` (i el detall `api_fpo_especialitat`),
  si hi ha correcció es fa servir. Les caches d'aquestes funcions s'han d'invalidar quan canvia una
  correcció (afegir un comptador de versió a la clau de cache).
- «Ja no cal»: si el títol original actual coincideix amb la correcció, marcar-la com a innecessària al
  llistat del panell (no esborrar-la sola).
- UI: botó «Corregeix el títol» al desplegable de cada especialitat, **només per a administradors**
  (`/api/auth/me` ja diu si és admin; comprovar-ho al backend igualment). Quadre amb l'original i dos
  camps (CA, ES). Reaprofitar el patró de modal existent (`showCentresModal` com a referència d'estil).
- `frontend/admin.html`: secció «Correccions» amb el llistat (original | corregit | data | desfer).
- Carregar ja la correcció d'IFCD0025 («… HTML, CSS i JavaScript»).

### 2. Equivalències de cerca català → castellà

- Taula `search_terms(ca TEXT PRIMARY KEY, es TEXT, updated_at)`. A la primera execució, sembrar-la amb
  el contingut de `_CA_ES_TERMS`. Els sufixos (`_CA_ES_SUFFIXES`) es queden al codi.
- L'endpoint que avui serveix el diccionari al frontend ha de llegir de la taula (mantenir la forma de la
  resposta; `tests/test_ocupaciones_synonyms.py` s'ha d'adaptar).
- API admin: llistar, afegir/canviar, esborrar. UI a `admin.html`: secció «Equivalències de cerca».

### 3. Cerques sense resultat

- Taula `empty_searches(q TEXT PRIMARY KEY, n INTEGER, last_seen)`. Endpoint públic
  `POST /api/search-miss` amb el text normalitzat (màx. 80 caràcters, límit per IP amb `_auth_rate_ok` i
  un bucket propi). **Cap dada de qui ho ha cercat**: ni IP, ni usuari, ni sessió.
- El frontend l'envia quan una cerca de ≥ 4 lletres queda sense cap resultat (ni graus ni SEPE; i al
  mode ocupació) després d'1,5 s sense teclejar.
- `admin.html`: llistat ordenat per freqüència, amb un botó «Afegeix equivalència» que porta al punt 2.
- Esmentar-ho a `politica-privacitat.html` (es guarden cerques sense resultat, de manera agregada i anònima).

### 4. «Hi ha un error en aquesta fitxa?» a les especialitats

- El formulari (`frontend/feedback.js`, pla 089) només sap lligar un avís a un grau (`ref`, validat a
  `_feedback_oferta`). Acceptar també `espec` (codi d'especialitat, validat contra l'índex SEPE/SOC):
  nova columna a la taula `feedback` (com `oferta_ref` a la migració 016), línia «Sobre: SSCE22 · Tutorització en teleformació», i enllaç al
  desplegable SEPE i al panell FPO. Al panell d'administració, des d'un avís d'aquest tipus, enllaç directe
  a «Corregeix el títol».

## Tests

- Overrides: només admin (401 si no); codi inexistent → 404; aplicació a `/api/sepe/especialitats` i a
  `/api/fpo/especialitats`; invalidació de cache; marca «ja no cal».
- Equivalències: sembra inicial, CRUD, i que la cerca les fa servir.
- `search-miss`: retalla, agrega, aplica el límit i no desa res identificable.
- Feedback amb `espec` vàlid i invàlid.

## Fora d'abast

- Corregir altres camps (hores, nivell) o els graus A–E: el mecanisme ho permetria més endavant.
- Revisió manual dels 2.364 títols en català del SOC.
