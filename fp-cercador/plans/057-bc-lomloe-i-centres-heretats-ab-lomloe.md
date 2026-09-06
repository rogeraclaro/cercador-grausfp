# Pla 057 — Relació B→C LOMLOE (`bc_lomloe.json`), centres heretats A/B pla nou i itinerari

Origen: `plans/outputs/spike_043_results.md` (2026-09-06, VIABLE, 99 % cobertura).
Depèn de: 055 DONE (centres C LOMLOE), 056 DONE (`centres_inherit.py`).
Executable per un agent sense context.

## Context

Els 1.019 B i 5.953 A de **pla nou (LOMLOE)** no tenen ni centres ni relació
amb el seu certificat C. El spike ha confirmat que la fitxa web de cada C
LOMLOE llista els seus mòduls professionals `( NNNN ) nom`, i que `NNNN` és
exactament el número del codi B `FAM_B_NNNN` (mateixa família que el C).
Amb això es construeix `bc_lomloe.json` i es reutilitza tota la maquinària
del pla 056.

Fets verificats (no repetir):
- URL fitxa: `https://www.todofp.es/buscadorgradosfp/ficha?grado=C&id={ficha_id}`
  amb la sessió de `buscador_scraper._bootstrap_session()`.
- Secció "Módulos Profesionales" … "Nota:" ; regex `\(\s*(\d{4})\s*\)`.
- Els `ficha_id` **només** són vàlids si vénen del `ofertes.json` del darrer
  refresc; canvien a cada refresc. Verificar `Código: FAM_C_…` a la pàgina.
- ~2,5 s per GET; un bloc de 16 fallades transitòries → reintent amb backoff.
- Fixture real de les 400 fitxes: `plans/outputs/spike_043_c_lomloe_modulos.json`.

## Decisions de disseny

1. **Fitxer nou `backend/data/bc_lomloe.json`**, forma `{codigo_c: [codigo_b, …]}`.
   Diferent de `bc_loe.json` (que guarda UCs, no codis B), però mateixa
   estructura "C → llista", i mateix tractament (gitignored, generat al VPS).
2. **Es genera dins `pipeline.run()`**, just després de `ciclos_fp.json`,
   perquè és allà on els `ficha_id` acaben de refrescar-se. No-fatal: si
   falla, el refresc d'ofertes continua (mateix patró que `build_ciclos_index`).
3. **Clau de centres per a C LOMLOE = `str(id)`** (pla 055). Per tant la
   branca LOMLOE de `centres_inherit` necessita un mapa `codigo_c → str(id)`.
4. Al frontend, el botó "Mòdul professional en aquests graus C" que avui només
   surt per a B LOE (`/^MF\d{4}_\d+$/`) passa a sortir també per a B LOMLOE
   (`/^[A-Z]{3}_B_\d{4}$/`), reutilitzant el mateix `fetchChildrenCLoe` i el
   mateix camp de resposta `children_c_loe` → renombrat semànticament a
   **`children_c`** amb `children_c_loe` mantingut com a àlies per
   compatibilitat (el frontend desplegat pot estar cachejat).

## Fase 1 — Scraper `backend/scrapers/bc_lomloe_scraper.py` (TDD)

### Tests primer: `backend/tests/test_bc_lomloe_scraper.py`

Sense xarxa. `_fetch_ficha_html` mockejat amb HTML mínim (agafa'l de la
fitxa real: `<title>…` + `Código: HOT_C_005_5B` + `Módulos Profesionales
( 0171 ) Estructura del mercado turístico ( 1782 ) Prevención de riesgos
laborales Nota: …`).

1. `test_parse_modulos_extreu_numeros_i_noms`: de l'HTML → `[('0171','Estructura del mercado turístico'), ('1782','Prevención de riesgos laborales')]`.
2. `test_parse_codigo_verifica_la_fitxa`: `parse_codigo(html) == 'HOT_C_005_5B'`.
3. `test_build_bc_lomloe_resol_b_mateixa_familia`: amb `records` que
   contenen `HOT_C_005_5B` (ficha_id 999), `HOT_B_0171`, `ADG_B_0171`, i
   cap B `1782` → `{'HOT_C_005_5B': ['HOT_B_0171']}` (no `ADG_B_0171`, no 1782).
4. `test_build_bc_lomloe_salta_fitxa_amb_codi_diferent`: si la fitxa
   retorna `Código: ADG_C_001_3B` per a l'id de `HOT_C_005_5B` → el C no
   apareix al resultat i s'ha fet `logger.warning`.
5. `test_fetch_reintenta_amb_backoff`: `_fetch_ficha_html` que falla 2 cops
   i respon al 3r → resultat OK, 3 crides, `time.sleep` mockejat cridat amb
   `[5, 15]`.

### Implementació

```python
"""
bc_lomloe_scraper.py — Relació C LOMLOE → [B LOMLOE] via fitxa todofp.
Genera backend/data/bc_lomloe.json {codigo_c: [codigo_b, ...]}.
"""
BASE_URL = buscador_scraper.BASE_URL          # 'https://www.todofp.es/buscadorgradosfp'
RATE_LIMIT_SEC = 1.0
BACKOFF = (5, 15, 45)

def parse_codigo(html) -> str | None           # r'Código:\s*([A-Z]{3}_C_\d+_\w+)'
def parse_modulos(html) -> list[tuple[str, str]]
    # text pla (strip tags, unescape, collapse ws); tallar entre
    # 'Módulos Profesionales' i 'Nota:'; r'\(\s*(\d{4})\s*\)\s*([^()]+?)\s*(?=\(|$)'
def _fetch_ficha_html(session, ficha_id, timeout=30) -> str   # GET + raise_for_status
def _fetch_with_retry(session, ficha_id) -> str               # BACKOFF, després re-raise
def build_bc_lomloe(records, session=None, on_progress=None) -> dict[str, list[str]]
    # c_lomloe = grado C & not plan_antiguo & ficha_id
    # b_by_fam_num = {(fam, num): codigo_b} de grado B & not plan_antiguo
    # per cada C: html → parse_codigo == codigo? else warning+skip
    #             mods → [b_by_fam_num.get((codigo[:3], num))] filtrats None
    # sleep RATE_LIMIT_SEC entre crides; on_progress('B→C LOMLOE', i, n) cada 25
def write_bc_lomloe(index, path)              # json atòmic (tmp + os.replace) com pipeline._write_atomic
```

Reutilitzar `buscador_scraper._bootstrap_session()` i `_HEADERS`; **no**
duplicar. Logging amb el `logger` del mòdul.

## Fase 2 — Enganxar al pipeline (`backend/scrapers/pipeline.py`)

Just després del bloc `ciclos_fp.json` (línia ~179), mateix patró no-fatal:

```python
# --- Pla 057: B→C LOMLOE via fitxes todofp ---
try:
    from scrapers.bc_lomloe_scraper import build_bc_lomloe, write_bc_lomloe
    bc_lomloe = build_bc_lomloe(all_records, on_progress=on_progress)
    write_bc_lomloe(bc_lomloe, os.path.join(os.path.dirname(DATA_PATH), 'bc_lomloe.json'))
    logger.info("pipeline: bc_lomloe.json escrit (%d certificats C)", len(bc_lomloe))
except Exception as exc:
    logger.warning("pipeline: build_bc_lomloe ha fallat (no fatal): %s", exc)
```

**Compte amb `on_progress`**: el `pipeline.run(on_progress=lambda phase: …)`
d'`app.py:512` rep un sol argument (`phase`). Adaptar: passar
`on_progress=lambda p, i, n: on_progress(f'{p} {i}/{n}')` o afegir la fase
com a string. Mirar `refresh_state.set_state` abans de decidir.

Afegir `bc_lomloe.json` al `.gitignore` al costat de `bc_loe.json`.

Test: `test_pipeline.py` ja mockeja els parsers; afegir un test que
`build_bc_lomloe` mockejat llançant excepció **no** fa fallar `run()` i que
`ofertes.json` s'escriu igualment.

## Fase 3 — Herència de centres LOMLOE (`backend/centres_inherit.py`, TDD)

### Tests primer (`test_centres_inherit.py`, afegir)

6. `test_b_lomloe_hereta_dels_c_lomloe_per_id`: B `HOT_B_0171` (id 50), C
   `HOT_C_005_5B` (id 60, plan_antiguo False), `bc_lomloe = {'HOT_C_005_5B': ['HOT_B_0171']}`,
   `oferta_centres = {'60': ['m1','m2']}` → `{'50': ['m1','m2']}`.
7. `test_a_lomloe_hereta_via_b_lomloe`: A `HOT_A_0171_01` (id 51) → mateix.
8. `test_b_lomloe_unio_de_diversos_c`: dos C amb el mateix mòdul → unió.
9. `test_sense_bc_lomloe_no_trenca`: `bc_lomloe={}` → només resultats LOE.

### Implementació

- Signatura: `build_inherited(records, ab_index, bc_loe_inverse, oferta_centres, bc_lomloe=None)`.
  `bc_lomloe` = `{codigo_c: [codigo_b]}` cru; la funció construeix
  internament `b_lomloe_inverse = {codigo_b: [codigo_c]}` i
  `c_lomloe_id = {codigo_c: str(id)}` (grado C, not plan_antiguo).
- Branca LOMLOE: `^[A-Z]{3}_B_\d{4}$` → `[oferta_centres.get(c_lomloe_id[c])
  for c in b_lomloe_inverse[codigo_b]]` unió ordenada. A LOMLOE →
  `itinerary.get_parent_b()` (ja funciona per a `FAM_A_NNNN_PP`) → mateixa branca.
- Treure el filtre `if not r.get('plan_antiguo'): continue`; discriminar per
  patró de codi (LOE `MF/UF`, LOMLOE `FAM_B_/FAM_A_`).

### Consumidors

- `app.py:_get_effective_oferta_centres`: afegir `BC_LOMLOE_PATH` al costat
  de `BC_LOE_PATH`, incloure'n el mtime a la clau de cache, carregar el JSON
  (fail-soft) i passar `bc_lomloe=`.
- `centres_watch_service._inherited_ab_loe` → renombrar a
  `_inherited_ab` i fer el mateix (llegir `bc_lomloe.json` si existeix).
  Actualitzar `test_centres_inherit_api.py` (fixture: `_BC_LOMLOE_PATH`).
- Docstring de `centres_inherit.py`: treure "LOMLOE queda fora".

## Fase 4 — `/api/itinerari` (punt 3 del spike)

`backend/app.py` `api_itinerari`:

- **`grado=B`**: si `codigo` matxeja `^[A-Z]{3}_B_\d{4}$`, resoldre via
  `bc_lomloe` invers (helper `_get_bc_lomloe_inverse()` amb cache per mtime,
  clon de `_get_bc_loe_inverse`) → llista de C LOMLOE serialitzats amb
  `_serialize`. Resposta: `children_c` (nou, per a LOE i LOMLOE) **i**
  `children_c_loe` (àlies, mateix contingut) durant una versió.
- **`grado=C`** LOMLOE (`^[A-Z]{3}_C_\d+_\w+$`): afegir `parent_b_lomloe`
  amb els B de `bc_lomloe[codigo]` serialitzats. `ciclos_d` segueix igual.

Tests (`test_api.py` o `test_centres_inherit_api.py`, mateixa fixture amb
`bc_lomloe.json`): `GET /api/itinerari?grado=B&codigo=HOT_B_0171` →
`children_c[0].codigo == 'HOT_C_005_5B'`; `GET …grado=C&codigo=HOT_C_005_5B`
→ `parent_b_lomloe[0].codigo == 'HOT_B_0171'`.

### Frontend (`frontend/index.html`)

- Línia ~2169: condició del botó `row.grado === 'B' && (/^MF\d{4}_\d+$/.test(row.codigo) || /^[A-Z]{3}_B_\d{4}$/.test(row.codigo))`.
- `fetchChildrenCLoe`: llegir `data.children_c || data.children_c_loe || []`.
- Per als C LOMLOE no hi ha panell de detall (el botó "Cicles D" viu dins el
  bloc de C LOE amb annex/BOE). **No** afegir panell nou en aquest pla; el
  `parent_b_lomloe` de l'API queda disponible per a un pla posterior d'UI.
- Cap clau i18n nova: `index.itinerari.children_c_loe_*` ja diu "graus C".

## Fase 5 — Verificació, desplegament i primera generació

1. `cd backend && python -m pytest` → tot verd excepte els 2 de `test_db.py`
   preexistents (`schema_version` 8 vs 1).
2. Commit convencional: `feat(itinerari): B→C LOMLOE index, inherited centres
   for A/B LOMLOE`.
3. Push → VPS: **`git status` abans de `git pull --ff-only`** →
   `systemctl restart fp-cercador` (no és PM2).
4. Primera generació de `bc_lomloe.json`: llançar el refresc d'ofertes des
   d'`admin.html` (o `POST /api/admin/refresh` amb token llegit al VPS).
   Durada esperada: el refresc habitual (~95 s) **+ ~10–16 min** de fitxes.
   Avisar l'usuari d'aquest increment. Alternativa sense esperar el refresc:
   `python3 -c "from scrapers.bc_lomloe_scraper import *; …"` al VPS amb el
   `ofertes.json` actual.
5. Comprovar: `ls -la backend/data/bc_lomloe.json` (~400 claus);
   `/api/centres/count` puja de 4.824 a ≈ 4.824 + 624 + 3.631 ≈ 9.000 claus;
   `index.html`: `HOT_B_0171` mostra badge de centres + botó "graus C" que
   llista `HOT_C_005_5B`; `HOT_A_0171_01` mostra badge; RSS del procés.
6. `plans/README.md`: 057 DONE amb xifres reals.

## Fora d'abast

- Panell de detall per a C LOMLOE (mostrar `parent_b_lomloe`, cicles D).
- C LOMLOE → D via mòduls NNNN + `ciclos_fp.json` (pista del spike; spike curt a part).
- Refactor de `bc_loe.json` a codis B (avui UCs). Es mantenen dos fitxers.

## Riscos

- **`ficha_id` obsolets** entre refresc i generació: per això es genera dins
  `pipeline.run()`, mai per separat amb un `ofertes.json` vell. Si es fa la
  generació manual (Fase 5.4 alternativa), fer-la immediatament després d'un
  refresc.
- **Durada del refresc** puja ~10× (95 s → ~15 min). El job programat i
  `refresh_state` han d'aguantar-ho; comprovar timeouts del reverse proxy si
  l'admin fa polling (només afecta la UI d'estat, no el job).
- **`/api/centres/count`** ≈ 9.000 claus: encara < 200 KB. Fine.
- **Memòria**: +4.255 llistes heretades (LOMLOE té menys centres per C que
  LOE: mitjana ~30 vs 266). Estimació +2–4 MB RSS.
