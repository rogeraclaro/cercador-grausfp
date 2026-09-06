# Pla 059 — FPO (SOC Catalunya): scraper, pipeline, endpoints i historial

> **DONE 2026-09-06.** Nota d'execució: l'endpoint `browse` d'Algolia retorna
> **403** amb la clau pública (només té l'ACL `search`). L'scraper pagina amb
> `POST /1/indexes/<idx>/query` + `hitsPerPage=1000&page=N` fins a `nbPages`.
> Funcions reals: `_algolia_query`, `_fetch_all` (no `_algolia_browse`/`_browse_all`).

Origen: `docs/superpowers/specs/2026-09-06-fpo-soc-catalunya-design.md` (§4, §5, §10, §11).
Depèn de: res (font nova i independent).
Primer dels 3 plans de la feature FPO. Els altres (060 mode UI + integració, 061
favorits + admin) depenen d'aquest.
Executable per un agent sense context (Sonnet). **TDD estricte**: cada fase
escriu primer els tests, els veu fallar, i després implementa.
**No cal prendre cap decisió de disseny: totes estan preses aquí i a la spec.**

## Context

El cercador integrat del SOC (`serveiocupacio.gencat.cat`) està servit per
**Algolia**. El frontend consulta Algolia directament amb claus de lectura
públiques incrustades al JS. CORS obert (`*`), sense captcha ni cookies. Es pot
recórrer l'índex sencer amb l'endpoint `browse`.

Fets verificats (no re-investigar):
- Application ID: `GAVVNU5N19`. Host: `https://gavvnu5n19-dsn.algolia.net`.
- 3 índexs (nom, clau read-only, ~registres):
  - `pro_SOC_CURSOS` · `1a344732c2a6e07f1e8aded4b3ec5ee5` · ~1.035
  - `pro_SOC_ESPECS_r1a` · `a71db7100e3362cc9522f7c7f79f954f` · ~2.974
  - `pro_SOC_CENTRES` · `08611804f7810c349cd2b2bc8a77e438` · ~2.708
- Petició: `POST https://GAVVNU5N19-dsn.algolia.net/1/indexes/<index>/browse`
  amb capçaleres `X-Algolia-Application-Id`, `X-Algolia-API-Key`,
  `Content-Type: application/x-www-form-urlencoded` i cos
  `{"params":"hitsPerPage=1000"}`. La resposta porta `hits`, `cursor` (si en
  queden més), `nbHits`. Es repeteix passant `{"params":"cursor=<cursor>"}` fins
  que no hi ha `cursor`.
- Esquema d'un hit de `CURSOS` (camps que fem servir):
  `idCurs` (codi expedient, únic), `titol{cat,cas}`, `famProf{codi,desc{cat,cas}}`,
  `area{codi,desc{cat,cas}}`, `especialitat{codi,desc{cat,cas}}`, `certProf` (RD
  o ""), `teCertProf` ("Si"/"No"), `nivellEspecialitat` (0..3), `hores`,
  `modalitat`, `estatInscripcio`, `dataInici`/`dataFi` ("dd/mm/aaaa"),
  `dataIniciOrdre` ("aaaammdd"), `comarca`, `municipi`, `provincia`,
  `centres{nomLoc,calleLoc,localidadLoc,codPostalLoc,telefonLoc,mailLoc,webLoc,idCentre,horariLoc{dilluns..diumenge},lat,lon}`,
  `programa{cat,cas}`, `queAprendras{cat,cas}`,
  `dadesInteres{requisits{cat,cas},quePoderTreballar{cat,cas}}`,
  `unitatCompetencia[{codi,desc,modulFormatiu[{codi,desc,durada,unitatFormativa[]}]}]`,
  `codOcupacio[{codi,desc{cat,cas}}]`, `esCifo`, `perDiscapacitats`.
- Esquema d'un hit de `ESPECS`: `codi`, `desc{cat,cas}`, `familia{codi,desc}`,
  `area{codi,desc}`, `hores`, `preu`, `nivellEspecialitat`, `certProf`,
  `programa{cat,cas}`, `unitatCompetencia[...]`, `cursos[{idCursIntern}]`,
  `centres[{idCentre}]`, `espDestacada`, `dataBaixa`.
- Esquema d'un hit de `CENTRES`: `idCentre`,
  `data{codiEntitat,raoSocial,cif,numCens,email,web,codiCentre,carrer,comarca,cp,municipi,provincia,telefon,lat,lng,numCursos,esCifo,perDiscapacitats}`.
- **Cap curs del SOC té codi en format LOMLOE** (`FAM_C_NNN_NL`). Els 720 cursos
  que són certificat de professionalitat tenen `especialitat.codi` en format SEPE
  (`ADGG0408`), que coincideix 1:1 amb el `codigo` dels registres
  `grado=='C' && plan_antiguo` d'`ofertes.json`.

## Decisions de disseny

1. **Snapshot periòdic**, no proxy en viu. `soc_scraper.py` escriu 3 JSON dins
   `pipeline.run()` com a bloc no-fatal (patró idèntic a `bc_lomloe`/`d_modulos`).
2. Els camps bilingües `{cat,cas}` **es guarden tal qual**; el frontend tria
   l'idioma. El scraper NO resol l'idioma.
3. La **unitat de negoci al frontend és l'especialitat**. El backend serveix
   `/api/fpo/especialitats` amb la llista d'especialitats **que tenen ≥1 curs
   actiu** (unió de `soc_especs` amb `soc_cursos` per `especialitat.codi`).
4. Claus API del SOC **hardcoded** al scraper (públiques). Si `browse` retorna
   401/403 → warning explícit "clau possiblement rotada" + email a l'admin.
5. Endpoints nous sota `/api/fpo/`. Filtratge de la llista al **client**
   (~600 especialitats, dins el límit de 1.500 de rendiment).

## Fase 1 — `backend/scrapers/soc_scraper.py` (TDD)

### Tests primer: `backend/tests/test_soc_scraper.py`

Sense xarxa: `_algolia_browse` mockejat. Fixtures inline amb 1–2 hits per índex
copiant l'estructura real dels esquemes de dalt.

1. `test_browse_pagina_amb_cursor`: `_algolia_browse` fa servir un fake que
   retorna `{'hits':[...], 'cursor':'c1'}` i després `{'hits':[...]}` (sense
   cursor) → `_browse_all(index, key)` concatena tots els hits de les dues
   pàgines i para.
2. `test_browse_401_aixeca_error_clau`: el fake retorna status 403 →
   `_browse_all` aixeca `SocKeyError` (subclasse d'`Exception`) amb el text
   "clau" al missatge.
3. `test_normalize_curs`: un hit cru de CURSOS →
   `{'idCurs': '25/.../026', 'titol': {'ca': '...', 'es': '...'},
     'familia': {'codi': 'TMV', 'desc': {'ca': '...', 'es': '...'}},
     'area': {'codi': 'TMVI', 'desc': {...}},
     'especialitat': {'codi': 'TMVI24', 'desc': {...}},
     'esCertProf': True|False, 'rd': '<certProf>'|None,
     'nivell': 1, 'hores': 24.0, 'modalitat': 'PRESENCIAL',
     'estat': 'informacio'|'inscripcio'|'gestio'|'<altre>',
     'dataInici': '2026-09-30', 'dataFi': '2026-10-05',
     'comarca': '...', 'municipi': '...', 'provincia': '...',
     'centre': {'nom','carrer','cp','municipi','comarca','telefon','email','web',
                'idCentre','horari': {dilluns..diumenge}, 'lat': float|None, 'lon': float|None},
     'programaUrl': '<programa.cat or programa.cas>',
     'queAprendras': {'ca','es'}, 'requisits': {'ca','es'}, 'sortides': {'ca','es'},
     'moduls': [{'codi','desc':{'ca','es'},'durada': float}],
     'ocupacions': [{'codi','desc':{'ca','es'}}]}`.
   - `estat`: mapejar `estatInscripcio` a un slug curt: conté "inscripcio" →
     `'inscripcio'`; conté "informacio" → `'informacio'`; conté "Gestio" →
     `'gestio'`; altrament l'string original en minúscules.
   - dates: `dd/mm/aaaa` → `aaaa-mm-dd`; buit o invàlid → `None`.
   - `lat`/`lon`: `"0"` o buit → `None`; altrament `float`.
4. `test_normalize_espec`: un hit cru d'ESPECS →
   `{'codi','titol':{'ca','es'},'familia':{'codi','desc':{'ca','es'}},
     'area':{'codi','desc':{'ca','es'}},'nivell': int,'hores': float,'preu': float,
     'esCertProf': bool,'rd': str|None,'programaUrl': str,
     'moduls':[...],'cursIds':['<idCursIntern>', ...],'destacada': bool}`.
5. `test_normalize_centre`: un hit cru de CENTRES → objecte pla amb
   `idCentre, raoSocial, cif, numCens, email, web, codiCentre, carrer, cp,
    municipi, comarca, provincia, telefon, lat, lon, numCursos, esCifo (bool),
    perDiscapacitats (bool)`.
6. `test_build_soc_data`: `_browse_all` mockejat perquè retorni els hits fixture
   de cada índex segons el nom → `build_soc_data()` retorna
   `{'cursos': [...], 'especs': [...], 'centres': [...]}` amb les 3 llistes
   normalitzades i no buides.
7. `test_write_soc_data_atomic`: `write_soc_data({'cursos':[...],'especs':[...],'centres':[...]}, tmp_path)`
   escriu `soc_cursos.json`, `soc_especs.json`, `soc_centres.json` a `tmp_path`,
   cadascun JSON vàlid amb el contingut esperat (tmp + `os.replace`).

### Implementació

Clonar l'estructura de `backend/scrapers/bc_lomloe_scraper.py` (llegir-lo
primer per al patró d'escriptura atòmica i logging). API:

```python
ALGOLIA_APP = 'GAVVNU5N19'
ALGOLIA_HOST = f'https://{ALGOLIA_APP}-dsn.algolia.net'
INDEXES = {
    'cursos':  ('pro_SOC_CURSOS',     '1a344732c2a6e07f1e8aded4b3ec5ee5'),
    'especs':  ('pro_SOC_ESPECS_r1a', 'a71db7100e3362cc9522f7c7f79f954f'),
    'centres': ('pro_SOC_CENTRES',    '08611804f7810c349cd2b2bc8a77e438'),
}

class SocKeyError(Exception): ...

def _algolia_browse(index, key, params) -> dict          # POST .../browse ; raise_for_status ; 401/403 -> SocKeyError
def _browse_all(index, key) -> list[dict]                # pagina amb cursor fins al final
def _t(obj) -> dict                                      # {'cat':..,'cas':..} -> {'ca':..,'es':..} (buit si None)
def _date(s) -> str | None                               # 'dd/mm/aaaa' -> 'aaaa-mm-dd'
def _num(v) -> float | None
def normalize_curs(hit) -> dict
def normalize_espec(hit) -> dict
def normalize_centre(hit) -> dict
def build_soc_data() -> dict                             # {'cursos','especs','centres'}
def write_soc_data(data, data_dir) -> None               # 3 fitxers atòmics
```

- `_browse_all`: `requests.Session()` amb un `User-Agent` de navegador; primer
  POST amb `params='hitsPerPage=1000'`, següents amb `params=f'cursor={cursor}'`.
- `build_soc_data`: crida `_browse_all` per als 3 índexs i mapeja amb els
  `normalize_*`. Si un índex peta amb `SocKeyError`, propaga (el pipeline ho
  captura). Si peta amb un altre error transitori, també propaga.

## Fase 2 — Pipeline (TDD)

`backend/scrapers/pipeline.py`, bloc nou just després del bloc Pla 058
(`d_modulos`), patró no-fatal:

```python
# --- Pla 059: cursos FPO del SOC (Catalunya) via Algolia (no fatal) ---
_report('Cursos FPO (SOC Catalunya)')
try:
    from scrapers.soc_scraper import build_soc_data, write_soc_data
    soc = build_soc_data()
    write_soc_data(soc, os.path.dirname(DATA_PATH))
    logger.info("pipeline: soc_*.json escrit (%d cursos, %d especialitats, %d centres)",
                len(soc['cursos']), len(soc['especs']), len(soc['centres']))
except Exception as exc:
    logger.warning("pipeline: build_soc_data ha fallat (no fatal): %s", exc)
```

`backend/tests/test_pipeline.py`: a la fixture autouse `isolate_data_path`
afegir `import scrapers.soc_scraper as soc` +
`monkeypatch.setattr(soc, 'build_soc_data', lambda **kw: {'cursos': [], 'especs': [], 'centres': []})`.
Dos tests calcats dels de `bc_lomloe`
(`test_run_escriu_soc_json`, `test_run_no_falla_si_soc_peta`) amb
`PATCH_BUILD_SOC = 'scrapers.soc_scraper.build_soc_data'`. `test_run_escriu_soc_json`
comprova que s'escriuen els 3 fitxers a `tmp_path`.

## Fase 3 — Endpoints `/api/fpo/*` a `app.py` (TDD)

### Tests primer: `backend/tests/test_fpo_api.py`

Fixtura `fpo_data` (estil `data_dir` de `test_centres_inherit_api.py`): escriu
`soc_especs.json`, `soc_cursos.json`, `soc_centres.json` a `tmp_path` amb dades
mínimes coherents (1 especialitat `IFCD0112` amb 2 cursos, 1 especialitat
`XXXX0000` sense cap curs, 1 curs d'un cert. prof. `ADGG0408`), `monkeypatch` de
`SOC_ESPECS_PATH` / `SOC_CURSOS_PATH` / `SOC_CENTRES_PATH` i dels 3 caches.

1. `test_especialitats_nomes_amb_curs_actiu`: `GET /api/fpo/especialitats` →
   inclou `IFCD0112` amb `nCursos == 2` i **no** inclou `XXXX0000`. Cada entrada
   té `codi, titol{ca,es}, familia{codi,desc}, area{codi,desc}, nivell, hores,
   esCertProf, rd, nCursos, comarques[], municipis[], estats[], modalitats[], programaUrl`.
   (`comarques`/`municipis`/`estats`/`modalitats` = sets ordenats derivats dels
   cursos actius de l'especialitat; els fa servir la barra de filtres del Pla 060.)
2. `test_especialitats_warning_si_falta_fitxer`: sense `soc_especs.json` →
   `{'especialitats': [], 'warning': '...'}`, HTTP 200.
3. `test_especialitat_detall`: `GET /api/fpo/especialitat/IFCD0112` →
   `{descripcio{ca,es}, requisits{ca,es}, sortides{ca,es}, moduls[], programaUrl,
     cursos: [{idCurs, centre{...}, dataInici, dataFi, estat, modalitat, fitxaUrl}]}`
   amb 2 cursos.
4. `test_especialitat_detall_404`: codi inexistent → `{}` amb HTTP 404.
5. `test_by_cert_match`: `GET /api/fpo/by-cert?codigo=ADGG0408` →
   `{especialitat: 'ADGG0408', nCursos: 1, cursos: [...]}`.
6. `test_by_cert_sense_match`: `codigo` sense cursos → `{}` (HTTP 200).

### Implementació

`backend/app.py`:

- `SOC_CURSOS_PATH`, `SOC_ESPECS_PATH`, `SOC_CENTRES_PATH` a `_DATA_DIR`.
- `_soc_cursos_cache`, `_soc_especs_cache`, `_soc_centres_cache` +
  `_get_soc_cursos()`, `_get_soc_especs()`, `_get_soc_centres()` — clons exactes
  de `_get_bc_lomloe()` (cache per mtime; `[]` si falta/corrupte; comprovar
  `isinstance(list)`).
- `_soc_espec_index()` (cache amb clau = tupla de mtimes de cursos+especs):
  agrupa `_get_soc_cursos()` per `especialitat.codi` i, per a cada especialitat
  d'`_get_soc_especs()` amb ≥1 curs, construeix l'entrada de llista amb
  `nCursos` i els sets ordenats `comarques`, `municipis`, `estats`,
  `modalitats` (derivats dels seus cursos actius). Guarda també
  `cursos_by_espec = {codi: [curs, ...]}` per a `/especialitat/<codi>` i
  `/by-cert`.
- `fitxaUrl` d'un curs: `https://serveiocupacio.gencat.cat/ca/persones/vull-formar-me/cercadors-formacio-especialitats/cercador-integrat/detall-curs.html?id=<idCurs>`
  **(a confirmar durant la implementació obrint un resultat real al SOC; si el
  patró no és aquest, ajustar aquí i deixar-ho documentat).**
- 3 rutes noves (`api_fpo_especialitats`, `api_fpo_especialitat`,
  `api_fpo_by_cert`), registrades amb `@app.route`.
- `warning`: si `_get_soc_especs()` és buit → `"L'oferta de cursos FPO no està
  disponible temporalment."`. Si el fitxer existeix però `mtime` > 7 dies →
  `"Les dades de cursos FPO poden estar desactualitzades."`.

## Fase 4 — Historial i avís a l'admin (TDD)

### 4a. Historial

`backend/scrapers/pipeline.py`: dins el bloc del Pla 059, quan `write_soc_data`
té èxit, cridar `history.append_source('soc', {...})` o l'equivalent al patró
existent (llegir `backend/history.py` — funció `append()` i com s'hi va afegir
l'scraping de centres al Pla 054). Registrar: data, resultat, i deltes
(`cursos_afegits`/`cursos_retirats`) comparant `idCurs` amb el `soc_cursos.json`
anterior (llegir-lo abans de sobreescriure).

Test a `backend/tests/test_history.py` (o `test_pipeline.py`): un run amb
`build_soc_data` mockejat afegeix una entrada a l'historial amb clau/etiqueta
"Cursos FPO (SOC)".

`frontend/historial.html`: si la taula d'historial es genera a partir de
`/api/historial` i les entrades porten `font`/`tipus`, afegir l'etiqueta
"Cursos FPO (SOC)" al render (buscar com es mostra "scraping de centres" i
clonar). Clau i18n `hist.font.soc` CA/ES.

### 4b. Email a l'admin si el snapshot falla

`backend/scrapers/pipeline.py`: al `except` del bloc Pla 059, cridar
`_notify_admin_soc_failure(exc)`. Implementar aquesta funció al mòdul que ja
envia avisos a l'admin (llegir `backend/notifier.py` i `backend/email_service.py`
per veure el canal existent). Assumpte "Snapshot FPO (SOC) ha fallat";
cos: `repr(exc)` + hora UTC. **Rate-limit 1/dia**: guardar un timestamp a
`backend/data/last_soc_alert.json` i no reenviar si fa < 24 h.

Test `backend/tests/test_pipeline.py` (o un `test_soc_notify.py`):
`build_soc_data` amb `side_effect=RuntimeError` → `_notify_admin_soc_failure`
cridat una vegada; una segona execució immediata **no** torna a enviar (mock del
sender, comprovar `call_count`).

## Fase 5 — Verificació i desplegament

1. `cd backend && python -m pytest` → tot verd excepte els 2 preexistents de
   `tests/test_db.py` (`schema_version`). No tocar-los.
2. Generació local del primer snapshot per validar contra dades reals:
   ```bash
   cd backend && python -c "
   import json, logging; logging.basicConfig(level=logging.INFO)
   from scrapers.soc_scraper import build_soc_data, write_soc_data
   d = build_soc_data(); write_soc_data(d, 'data')
   print('cursos', len(d['cursos']), 'especs', len(d['especs']), 'centres', len(d['centres']))
   "
   ```
   Esperar ~1.035 / ~2.974 / ~2.708. `curl -s localhost:5001/api/fpo/especialitats | python -m json.tool | head`.
3. Commit: `feat(fpo): SOC Catalunya snapshot, /api/fpo/* endpoints i historial`.
4. `git push` → VPS (`root@62.169.25.188`, clau `~/.ssh/id_ed25519_roger`):
   `cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git status -sb`
   (drift) → `git pull --ff-only` → `systemctl restart fp-cercador` →
   `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8033/api/fpo/especialitats`
   (esperat 200 amb `warning` fins que hi hagi snapshot).
5. Primera generació al VPS (les dades del SOC no caduquen ràpid):
   ```bash
   cd /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend
   ../../venv/bin/python -c "
   import json,logging; logging.basicConfig(level=logging.INFO)
   from scrapers.soc_scraper import build_soc_data, write_soc_data
   d=build_soc_data(); write_soc_data(d,'data'); print('OK',len(d['cursos']),len(d['especs']),len(d['centres']))
   "
   ```
   Comprovar `curl -s 'http://127.0.0.1:8033/api/fpo/especialitats' | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d['especialitats']))"`
   i `curl -s 'http://127.0.0.1:8033/api/fpo/by-cert?codigo=ADGG0408'`.
6. `plans/README.md`: 059 DONE amb xifres reals.

## Fora d'abast (d'aquest pla)

- Tot el frontend del mode FPO (pla 060).
- Favorits FPO i UI d'admin (pla 061).
- Alertes.

## Riscos

- **Rotació de claus API del SOC**: bloc no-fatal + `SocKeyError` explícit +
  email a l'admin. Fàcil d'actualitzar al scraper.
- **`fitxaUrl` incerta**: cal confirmar el patró real d'URL de fitxa de curs;
  si no s'aconsegueix, deixar el botó apuntant a la pàgina del cercador amb el
  text de cerca pre-omplert i documentar-ho.
- **Volum del payload**: `soc_cursos.json` ~1–3 MB. Acceptable (comparable a
  `bc_lomloe.json`). `/api/fpo/especialitats` retorna només la llista agregada.
