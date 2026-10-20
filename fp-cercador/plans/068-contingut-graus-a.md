# Pla 068 — "En què consisteix" un Grau A (resultats d'aprenentatge del B pare)

Origen: petició del propietari (2026-10-20): els Graus A diuen a quin B pertanyen
però no expliquen en què consisteixen.
Depèn de: — (reutilitza `buscador_scraper`, `itinerary.get_parent_b`, `/api/itinerari`).

TDD estricte al backend. No cal prendre cap decisió de disseny: tot està resolt aquí.

## Fets verificats (2026-10-20; no re-investigar)

- La fitxa oficial d'un Grau A (`/buscadorgradosfp/ficha?grado=A&id=…`) **només** llista
  els B que el contenen. No hi ha descripció.
- La fitxa d'un **B LOMLOE** (`FAM_B_NNNN`) té tres blocs:
  - "Estándares de competencia": `(ECPnnnn_n) text`
  - "Resultados de aprendizaje": `(FAM_RA_NNNN_PP) text`
  - "Acreditaciones parciales de competencia (Grados A incluidos)": `(FAM_A_NNNN_PP) nom`
  El sufix `_PP` del RA coincideix 1:1 amb el del Grau A
  (`ADG_A_3001_01` ↔ `ADG_RA_3001_01`). Verificat en 16/16 B LOMLOE d'una mostra aleatòria.
- La fitxa d'un **B LOE** (`MFnnnn_n`, plan antiguo) **no té** RA ni llista d'A, només
  l'estàndard de competència (`ECPnnnn_n`). Els A LOE són `UFnnnn`; el seu B pare surt
  de `itinerary.get_parent_b` (UF → MF).
- Volums: 5.858 A LOMLOE, 2.872 A LOE, 1.003 B LOMLOE, 1.949 B LOE.
- `ofertes.json` porta el `ficha_id` viu just després de `_write_atomic` al pipeline
  (`pipeline.py:300`), com fan servir els blocs 057/058.

## Decisions de disseny

- **Fitxer nou** `backend/data/b_contingut.json`, indexat per codi de B:
  `{ "ADG_B_3001": { "ecp": [{"codigo","text"}], "ra": [{"codigo","text"}] } }`.
  Els B LOE tindran `ra: []`.
- **Endpoint**: s'amplia la branca `grado == 'A'` de `/api/itinerari` amb
  `contingut: { "ra": {"codigo","text"} | null, "ecp": [...] }`. El RA es busca pel
  codi de l'A substituint `_A_` per `_RA_` dins `ra` del B pare. `null` si no hi és.
  Si el fitxer no existeix → `contingut` amb `ra: null, ecp: []` (mai error).
- **Scraper** `backend/scrapers/b_contingut_scraper.py`, calcat de `bc_lomloe_scraper.py`
  (sessió de `buscador_scraper._bootstrap_session()`, parse sobre text pla, comprovació de
  "Código:" contra el codi esperat → si no coincideix, se salta). Diferències:
  - Recorre **tots** els B amb `ficha_id` (LOMLOE + LOE).
  - Una fitxa inabastable després dels reintents es **salta amb WARNING** (no peta el build).
  - `ThreadPoolExecutor(max_workers=4)`, una `Session` per fil, per mantenir ~3.000 fitxes
    en ~15 min.
- **Frontend**: clicar una fila A ja no obre la fitxa directament; **desplega un panell**
  (com els C) amb:
  - "En què consisteix": text del RA (si n'hi ha).
  - "Competència del Grau B": llista d'ECP.
  - Enllaç al B pare (codi + nom) i botó "Fitxa a todofp" de l'A — tots dos amb el gating
    actual (`loggedIn ? window.open(ficha-redirect) : showCentresModal()`).
  - Si no hi ha ni RA ni ECP: text "No hi ha descripció oficial disponible" + els botons.
  El contingut del panell és públic (com el panell dels C); només els enllaços externs van
  amb login, igual que ara. Fetch lazy a la primera obertura, cache per codi.
- Textos de l'API en castellà (venen del ministeri); etiquetes en CA/ES via `i18n.js`.

## Fase 1 — Scraper (TDD)

### 1.1 Tests primer: `backend/tests/test_b_contingut_scraper.py`
HTML inline (`FICHA_LOMLOE_HTML`, `FICHA_LOE_HTML`) basats en les fitxes reals
`ADG_B_3001` i `MF1018_2`. Sense xarxa (monkeypatch del fetch i de `time.sleep`).
- `parse_b_ficha(html)` d'un B LOMLOE → 1 ECP, 4 RA amb codis i textos exactes.
- `parse_b_ficha(html)` d'un B LOE → 1 ECP, `ra == []`.
- `parse_codigo` / codi no coincident → el B no surt a l'índex.
- Fetch que llança excepció per a un B → els altres B hi són igualment.
- Només entren B amb `ficha_id`; A/C/D/E s'ignoren.
- `write_b_contingut` escriu atòmicament i és rellegible.

### 1.2 Implementació: `backend/scrapers/b_contingut_scraper.py`
`build_b_contingut(records, on_progress=None, max_workers=4) -> dict`, `write_b_contingut(index, path)`.

### 1.3 Commit `feat(068): scraper de contingut de les fitxes B (ECP + RA)`

## Fase 2 — Pipeline

Bloc no fatal després del de 058 a `pipeline.py`, mateix patró
(`_report('Contingut fitxes B …')`, `try/except Exception: logger.warning(… no fatal)`),
escrivint `data/b_contingut.json`. Afegir el fitxer al `.gitignore` si els altres índexs
generats hi són. Commit amb la Fase 3.

## Fase 3 — API (TDD)

### 3.1 Tests primer: `backend/tests/test_itinerari_contingut_api.py`
Fixture `data_dir` com a `test_centres_inherit_api.py` (monkeypatch de
`B_CONTINGUT_PATH` + reset de `_b_contingut_cache`).
- A LOMLOE amb RA → `contingut.ra == {"codigo": "ADG_RA_3001_01", "text": …}` i `ecp` del B.
- A LOE (`UFnnnn`) → `ra is None`, `ecp` del MF pare.
- A sense B pare o fitxer absent → `contingut == {"ra": None, "ecp": []}`, 200.
- `parent_b` continua igual (no regressió).

### 3.2 Implementació a `app.py`
`B_CONTINGUT_PATH`, `_get_b_contingut()` amb cache per `mtime` (patró `_get_d_modulos`),
i el camp `contingut` a la branca A de `/api/itinerari`.

### 3.3 Commit `feat(068): /api/itinerari retorna el contingut d'un Grau A`

## Fase 4 — Frontend (`index.html`, `i18n.js`)

- `rowIsActionable`: A sempre és accionable.
- `activateRow`: A fa toggle d'`expandedRows[row.id]` i crida `fetchContingutA(row.codigo)`
  (patró `fetchCiclosD`: `'loading'` → dades | `'error'`, updates immutables).
- `:aria-expanded` a la fila també per a A.
- Panell `<tr x-show="expandedRows[row.id] && row.grado === 'A'">` amb classe
  `detall-certificat` / `detall-inner` (reutilitzar estils existents; cap CSS nou si no cal).
  Recordatori: `x-if` amb un sol element arrel.
- Claus i18n noves (CA i ES): `index.a.consisteix`, `index.a.competencia_b`,
  `index.a.grau_b`, `index.a.sense_descripcio`, `index.a.carregant`, `index.a.error`.
- Commit `feat(068): panell "En què consisteix" per als Graus A`.

## Fase 5 — Primera generació, verificació i desplegament

1. Generar `b_contingut.json` en local executant només el scraper (no el pipeline sencer)
   sobre `ofertes.json`. Reportar: B processats, B amb RA, B saltats, A LOMLOE amb RA trobat.
2. Verificar amb navegador (server local, port 5001): A LOMLOE, A LOE, A sense dades,
   CA/ES, 0 errors de consola; C/B/D/E sense regressió.
3. Suite backend (`cd backend && python -m pytest tests/ -q`, ignorant scrapers de xarxa i
   `test_pipeline`; 2 fallades conegudes a `test_db`).
4. Desplegament **només amb confirmació del propietari**: push + `git pull` al VPS + restart
   (canvi de backend) + generar `b_contingut.json` al VPS amb el python del venv.
5. Marcar la fila 068 a `plans/README.md`.

## Ampliació (2026-10-20) — pare real dels Graus A LOE

### Fet verificat (no re-investigar)
L'heurística actual UF↔MF pel número (`itinerary.b_by_uf_num` / `a_by_uf_num`,
`index.html` `_bByUfNum` / `parentBOf`) és **errònia**: en 25/25 UF de mostra el pare real
(fitxa oficial de l'A) té un altre número (`UF0038` → `MF0706_1`, no `MF0038_3`). Alguns UF
tenen **diversos** pares (`UF0723` → `MF0326_2`, `MF0333_2`). Afecta, des de F5 i en
producció: el badge "→ MF…" de les files A, els fills A dels B LOE (`/api/itinerari?grado=B`),
la herència de centres A→B (`centres_inherit.py`) i el panell nou d'aquest pla.
L'única font fiable és la fitxa de cada A LOE (`ficha?grado=A&id=…`), que llista els codis
`MFnnnn_n` dels B que el contenen.

### Decisions
- El scraper llegeix també les fitxes dels **A LOE** (`UFnnnn` amb `ficha_id`), comprova
  "Código:" i extreu tots els `MFnnnn_n` de la secció de B pares. Sortida
  `backend/data/a_loe_pares.json`: `{ "UF0038": ["MF0706_1"], "UF0723": ["MF0326_2","MF0333_2"] }`.
  Mateix bloc no fatal del pipeline (un sol `_report`, dues sortides) o bloc germà; tolerància
  igual (saltar inabastables amb WARNING).
- `itinerary.py`: **s'elimina l'heurística pel número**. L'índex rep el mapa `a_loe_pares`
  i construeix `b_parents_by_a` (UF → [registres B]) i `a_by_b_loe` (MF → [registres A]).
  `get_parent_b` retorna el primer pare; nova `get_parents_b` retorna la llista. Sense mapa
  (fitxer absent) → cap pare per als A LOE (millor res que un pare fals).
- `/api/itinerari?grado=A`: `parent_b` = primer pare (compatibilitat) + nou `parents_b`
  (llista). `contingut.ecp` = ECP de tots els pares, sense duplicats; `contingut.ra` igual que ara.
  `?grado=B` d'un MF retorna els fills reals.
- `centres_inherit.py`: un A LOE hereta la **unió** dels centres de tots els seus pares.
- Frontend: nou endpoint `GET /api/a-loe-pares` (el JSON tal qual, cache per mtime) carregat un
  cop a l'inici; `parentBOf` el fa servir per als UF (primer pare; si n'hi ha més, el badge
  mostra "+N" i el title els llista). Fora `_bByUfNum`. El panell A llista tots els B pares.

### Fase 6 — Tests primer, implementació, regeneració
- Tests (fallen primer): parse de la fitxa A LOE (un pare, dos pares, codi no coincident);
  `itinerary` amb el mapa (pare correcte, diversos pares, sense mapa → None, fills d'un MF);
  `/api/itinerari` A LOE (`parents_b`, `ecp` unió) i B LOE (fills reals);
  `centres_inherit` (unió de pares); `/api/a-loe-pares`. Ajustar els tests existents que
  codificaven l'heurística (`test_itinerary.py`, etc.) i explicar-ho al commit.
- Commits: `fix(068): pare real dels Graus A LOE des de la fitxa oficial` (backend) i
  `fix(068): badge i panell dels Graus A LOE amb els pares reals` (frontend).
- Regenerar `a_loe_pares.json` en local (amb `ficha_id` vius, com a la primera generació).
- Desplegament: al VPS cal generar `b_contingut.json` i `a_loe_pares.json` **amb `ficha_id`
  vius** (el `ofertes.json` del VPS pot tenir ids antics si no s'ha fet un refresc recent):
  executar el refresc complet o el mateix script amb ids vius.

## Fora d'abast

- Hores i continguts detallats dels A (són al Reial Decret de cada formació).
- Mostrar RA/ECP a les files B (possible pla futur reutilitzant el mateix índex).
- Descripció pròpia dels A LOE més enllà de l'ECP del MF pare.

## Riscos

- Fitxes B amb RA i A en nombre diferent → el RA es busca per codi, no per posició; els A
  sense RA mostren només l'ECP.
- `ficha_id` volàtil → la comprovació de "Código:" evita desar contingut d'un altre B.
- Càrrega al servidor del ministeri: 4 fils, reintents amb backoff, una sola passada per refresc.
