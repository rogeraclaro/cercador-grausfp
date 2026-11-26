# Pla 105 — Aula virtual i tutoria presencial a les especialitats SEPE

Prioritat P1 · Mida M · Depèn de: 096, 097, 099 (fets) · Origen: sessió 2026-11-26/27.
Executable per un agent sense context.

## Context comú (llegir abans de començar)

- Llegir `plans/096-…`, `plans/097-…` i `plans/099-…` (fets i desplegats): camps del catàleg, filtres de la
  pestanya «Especialitats SEPE» i panell d'entitats.
- Peces: `backend/scrapers/sepe_scraper.py` (`_request_body`, `_FILTER_WRAPPERS`, `_fetch_raw_rows`,
  `parse_row`, `build_sepe_data`), `backend/app.py` (`_sepe_llista`, `/api/sepe/especialitat/<codi>`),
  `frontend/index.html` (filtre de modalitat `sepeMod…`, bloc `sepe-block`, panell d'entitats `sepe-ent*`),
  `frontend/search-tools.js` (paràmetre `mod` a l'adreça), `frontend/i18n.js`.
- Convencions: text d'interfície a `i18n.js` en `ca` i `es` (sense literals dins `x-text`); `x-if` amb una
  sola arrel; en tocar `i18n.js` pujar `?v=` a totes les pàgines `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`; en tocar `search-tools.js`, pujar
  el seu `?v=` i afegir tests a `scripts/test_search_tools.js`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (878 en verd) i `python3 -m pytest -q tests/test_sepe_scraper.py tests/test_http_retry.py`.
- **Al Mac del propietari hi ha en marxa la descàrrega del pla 100** (`scripts/sepe_descarrega_programes.py`,
  ~23 h, escriu `backend/data/sepe_programes.json`). No l'aturis, no toquis aquest fitxer ni
  `backend/data/sepe-descarrega.log`, i fes el mínim de peticions al SEPE.

## El problema (cas real del propietari)

El propietari fa d'assistent docent a Ironhack en dos cursos que s'imparteixen **en format virtual**:
IFCT0134 i IFCT095PO. Al cercador:
- IFCT0134 té modalitat «Presencial y mixta» (sense teleformació) i queda al grup «Amb una part
  presencial»; el seu programa té un apartat «Aula virtual — Características» (connexió síncrona, registre
  de connexions). Formalment és presencial impartit per aula virtual.
- A la llista d'entitats, Ironhack surt com a «presencial» i a Bizkaia (IFCT095PO) o no hi surt (IFCT0134).

## Troballa (verificada el 2026-11-26)

El cercador del SEPE té dos filtres avançats per especialitat que no recollíem (ja són a
`_FILTER_WRAPPERS`, sempre amb valor `000` = tots):
- `…:aulaVirtualSeleccionadaWrapper:aulaVirtualSeleccionada` → `SI` / `NO`
- `…:tutoriaPresencialWrapper:tutoriaPresencial` → `SI` / `NO`

Consultant `rest/paginacionEspecialidades` amb `aulaVirtualSeleccionada=SI` i després `NO`:
**3.180 SI + 4.377 NO = 7.557** (tot el catàleg, sense solapaments). IFCT0134 = SI, ADGN0023 = SI,
IFCT095PO = NO, SSCE22 = NO, ADGA12DCP = NO.
Modalitat de les SI: «Presencial y teleformación» 2.218, «Presencial» 523, «Presencial y mixta» 412,
«Teleformación» 16, «Mixta» 11. És a dir: **523 especialitats que ara surten com a «Només presencial»
admeten aula virtual**.

Límits:
- La dada és per especialitat, no per entitat (el SEPE només diu «presencial» o «teleformació» de cada entitat).
- Un «NO» no vol dir que mai es faci en línia: IFCT095PO és NO però admet teleformació.
- Normativa: les ordres TMS/368/2019 i TMS/369/2019 (text consolidat, DA 4a) defineixen l'aula virtual
  («entorn d'aprenentatge on tutor-formador i alumnat interactuen de forma concurrent i en temps real, a
  través d'un sistema de comunicació telemàtic síncron») i diuen que és un mitjà complementari. No s'ha
  trobat la norma que permet impartir-hi tota la formació, tot i que els programes nous ho regulen.
  **A la web: descriure què és, sense citar cap article** (tret que es trobi i es verifiqui la norma).
- No s'ha verificat què vol dir exactament «Tutoría presencial SI» (es dedueix: la teleformació exigeix
  tutories presencials; el programa de SSCE22 diu «Duración total de las tutorías presenciales: 0 horas»).
  Abans de mostrar-ho, comprovar-ho amb 3–4 programes ja coneguts; si no queda clar, recollir la dada
  però no mostrar-la.

## Què s'ha de fer

### 1. Scraper
- `build_sepe_data` afegeix a cada fila `aulaVirtual: bool | None` i `tutoriaPresencial: bool | None`,
  fent, a més del llistat complet, una consulta filtrada `SI` per a cada filtre (el `NO` es dedueix; si la
  consulta `SI` falla, els camps queden a `None` i el refresc continua: és no fatal).
- Reaprofitar `_request_body`/`_fetch_raw_rows` (paràmetre opcional amb els valors dels filtres), una
  sola sessió. Validació: si el nombre de `SI` és 0 o és igual al total, tractar-ho com a error de format
  (camps a `None` + avís al log).
- Regenerar `backend/data/sepe_especs.json` en local (còpia prèvia a `$TMPDIR`).

### 2. Backend
- `_sepe_llista()`: camps compactes `av` (aula virtual) i `tp` (tutoria presencial), `true/false/null`.
- `/api/sepe/especialitat/<codi>`: els mateixos camps al detall.

### 3. Filtre de modalitat (decisió del propietari: 4 opcions, amb aquests textos)
1. **En línia al teu ritme (teleformació asíncrona)** — la modalitat inclou teleformació.
2. **En línia en directe (aula virtual)** — `av === true`.
3. **Amb una part presencial** — modalitat mixta (Mixta, Presencial y mixta) i `av !== true`.
4. **Només presencial** — modalitat «Presencial» i `av !== true`.
Una especialitat pot sortir a 1 i a 2 alhora. Mantenir la validació del paràmetre `mod` a l'adreça
(`search-tools.js`) amb els valors nous i acceptar els antics per compatibilitat (mapejar-los).
Mentre `av` sigui `null` (dades antigues), el filtre es comporta com abans.

### 4. Presentació
- Etiqueta «Aula virtual» a la fila (taula i targeta mòbil) quan `av === true`, amb text d'ajuda:
  classes en directe per videoconferència; es poden seguir des de qualsevol lloc; a efectes oficials
  compta com a formació presencial.
- Al desplegable: una línia clara sobre com es pot cursar (teleformació / aula virtual / presencial) i,
  si es mostra, la tutoria presencial.
- Exportació/columna: la columna «Modalitat» continua mostrant el valor literal del SEPE.

### 5. Panell d'entitats (aprovat pel propietari)
- **Cercador per nom** (camp de text, sense accents ni majúscules) a més de província i tipus.
- Notes: (a) la província és la del centre inscrit, no on es fa el curs; (b) una entitat «presencial» pot
  impartir per aula virtual si l'especialitat ho admet (mostrar-ho només quan `av === true`); (c) la llista
  pot no incloure totes les entitats que l'imparteixen (cas real: IFCT0134 a Ironhack no hi surt).
- El marcat del panell està duplicat (desplegable SEPE i panell FPO): tocar tots dos.

### 6. Documentació
- `per-que-grausfp.html#sepe` + `docs/per-que-grausfp.md`: què és l'aula virtual i en què es diferencia de
  la teleformació (síncrona vs asíncrona).
- `fonts.html#sepe`: que el catàleg inclou si admet aula virtual i tutoria presencial.

## Tests
- Scraper: consulta filtrada (mock), camps a `None` si falla, validació 0/total.
- API: `av`/`tp` al llistat i al detall.
- `search-tools`: valors nous i antics de `mod`.

## Verificació
- Dades locals: ~3.180 amb `av: true`; IFCT0134 `true`, IFCT095PO `false`.
- Navegador: `?grado=SEPE` amb cada opció del filtre (recomptes coherents), IFCT0134 surt a «En línia en
  directe», cerca «ironhack» dins del panell d'entitats d'IFCT095PO, CA i ES, mòbil.

## Deploy
- Copiar el `sepe_especs.json` nou al VPS (còpia prèvia) o esperar el refresc. Reinici del servei (no
  durant un refresc).
