# Pla 058 — C LOMLOE → D (`d_modulos.json` + derivació) i panell de detall per a C de pla nou

Origen: `plans/outputs/spike_c_lomloe_d_results.md` (2026-09-06, VIABLE 381/400).
Depèn de: 057 DONE (`bc_lomloe.json`, `_get_bc_lomloe()`, `c_lomloe_by_code`).
Executable per un agent sense context (pensat per a Sonnet). Segueix TDD estricte:
cada fase escriu primer els tests, els veu fallar, i després implementa.
**No cal prendre cap decisió de disseny: totes estan preses aquí.**

## Context

Els C de pla antic mostren "Cicles FP (D)" gràcies a `ciclos_fp.json`
(endpoint `ciclosFP` de todofp), que no existeix per als 400 C LOMLOE. El
spike ha confirmat que la fitxa de cada D llista els seus mòduls ("Plan de
formación"), i que un C LOMLOE és una llista de mòduls B (`bc_lomloe.json`).
Compartir mòduls de la **mateixa família** = relació C→D. 355/400 C queden
íntegrament dins d'un D.

Fets verificats (no repetir):
- Els 195 D tenen `ficha_url` (`ofertes.json`, grau D). 195/195 fitxes
  descarregades sense error, ~1 s cadascuna.
- HTML: `<h2>Plan de formación<span class="cruz"></span></h2>` … primer
  `<ul>` … `<li>Nom del mòdul.</li>` o `<li>0179. Inglés Profesional (Grado Superior)</li>`.
- Fixture real de les 195 fitxes parsejades: `plans/outputs/spike_d_plans.json`
  (`{"d": {str(id): {denominacion, familia, nivel, modulos: [{num, name}], ensenanzaFP}}}`).
- Els mòduls sense B (Itinerario personal, Digitalización, Sostenibilidad,
  FOL, àmbits de FPB, Proyecto intermodular, fase en empresa) s'han
  d'ignorar silenciosament: són transversals, no error.
- **Sense restringir a la mateixa família surten 4.514 parelles** (Inglés
  0179 és a 5 famílies). Amb família: 789. La restricció és obligatòria.

## Decisions de disseny

1. **Fitxer `backend/data/d_modulos.json`** amb els mòduls **crus** de cada D,
   clau `str(id)`: `{"<id>": {"modulos": [{"num": "0179"|null, "name": "…"}], "ensenanzaFP": "123_2501"|null}}`.
   No es persisteix la relació C→D: es deriva en memòria (com els centres
   heretats), així es refà sola quan canviïn `bc_lomloe.json` o les
   denominacions dels B.
2. Es genera dins `pipeline.run()` just després del bloc `bc_lomloe.json`,
   mateix patró no-fatal. +~4 min al refresc.
3. Derivació pura a `backend/cd_lomloe.py`, testable amb la fixture.
4. `/api/itinerari?grado=C` per a C LOMLOE omple `ciclos_d` amb el **mateix
   contracte** que C LOE (`denominacion`, `familia`, `ficha_url`) **més**
   `id`, `shared`, `total`. Ordenat per `shared/total` desc, després
   `denominacion`. Sense llindar al backend.
5. UI: clicar una fila C LOMLOE **desplega un panell** (com C LOE) en lloc
   d'obrir la fitxa externa. El panell té: botó "Fitxa todofp" (l'enllaç
   que abans obria el clic), botó "Cicles FP (D)" (mateix `fetchCiclosD`),
   i la llista de mòduls B (`parent_b_lomloe`, ja a l'API). Cada cicle D
   mostra "(4/5 mòduls)" si `shared < total`, res si els cobreix tots. El
   frontend **no amaga** cap cicle (el backend ja els ordena per rellevància).

## Fase 1 — Scraper `backend/scrapers/d_modulos_scraper.py` (TDD)

### Tests primer: `backend/tests/test_d_modulos_scraper.py`

HTML mínim inline (copiar l'estructura real):

```html
<div class="cdsp"><h2>Plan de formación<span class="cruz"></span></h2>
<div class="desplegable"><div class="cte"><p>Si estudias 1&ordm; ... vas a cursar:</p>
<ul>
  <li>Estructura del mercado tur&iacute;stico.</li>
  <li>0179. Ingl&eacute;s Profesional (Grado Superior)</li>
  <li>M&oacute;dulo profesional optativo (competencia de cada Comunidad Aut&oacute;noma)</li>
</ul></div></div></div>
<a href="https://www.educacion.gob.es/centros/buscarCentros?ensenanzaFP=122_2403">Centros</a>
```

1. `test_parse_modulos_noms_i_codis`: → `[{'num': None, 'name': 'Estructura del mercado turístico'}, {'num': '0179', 'name': 'Inglés Profesional (Grado Superior)'}, {'num': None, 'name': 'Módulo profesional optativo (competencia de cada Comunidad Autónoma)'}]`
   (punt final eliminat, entitats HTML descodificades, sense retallar res més).
2. `test_parse_modulos_sense_seccio_retorna_buit`: HTML sense "Plan de formación" → `[]`.
3. `test_parse_ensenanza_fp`: → `'122_2403'`; sense enllaç → `None`.
4. `test_build_d_modulos_clau_per_id_i_salta_sense_ficha_url`: `records` amb
   un D (id 12774, `ficha_url` set) i un D sense `ficha_url` i un C →
   `_fetch_with_retry` mockejat → resultat `{'12774': {'modulos': [...], 'ensenanzaFP': '122_2403'}}`.
5. `test_fetch_reintenta_amb_backoff`: idèntic al de `test_bc_lomloe_scraper.py`
   (2 fallades + èxit → `sleep` cridat amb `[5, 15]`).

### Implementació

Clonar l'estructura de `backend/scrapers/bc_lomloe_scraper.py` (llegir-lo
primer). API:

```python
RATE_LIMIT_SEC = 1.0
BACKOFF = (5, 15, 45)

def parse_modulos(html: str) -> list[dict]        # [{'num': str|None, 'name': str}]
def parse_ensenanza_fp(html: str) -> str | None   # r'ensenanzaFP=([\w]+)'
def _fetch_ficha_html(session, url, timeout=30) -> str   # GET url + raise_for_status
def _fetch_with_retry(session, url) -> str
def build_d_modulos(records, session=None, on_progress=None) -> dict[str, dict]
def write_d_modulos(index, path)                  # atòmic (tmp + os.replace)
```

`parse_modulos`: localitzar `Plan de formaci` a l'HTML cru; agafar fins al
primer `</ul>`; `re.findall(r'<li[^>]*>(.*?)</li>', seg, re.S)`; per a cada
item: treure tags, `html.unescape`, `strip`; `m = re.match(r'^(\d{4})\.\s*(.+)$', it)`;
`name = (m.group(2) if m else it).rstrip('.').strip()`.
`build_d_modulos`: `d_recs = [r for r in records if r.get('grado') == 'D' and r.get('ficha_url')]`;
si buit → `{}` sense bootstrap; sessió = `requests.Session()` amb
`buscador_scraper.HEADERS` (les fitxes D són pàgines estàtiques, no cal
`_bootstrap_session`); `on_progress('Mòduls D', i, n)` cada 25.

## Fase 2 — Pipeline

`backend/scrapers/pipeline.py`, just després del bloc `bc_lomloe` (Pla 057):

```python
# --- Pla 058: mòduls de cada cicle D via fitxes todofp (no fatal) ---
_report('Mòduls dels cicles D (fitxes todofp)')
try:
    from scrapers.d_modulos_scraper import build_d_modulos, write_d_modulos
    d_modulos = build_d_modulos(all_records, on_progress=lambda phase, i, n: _report(f'{phase} {i}/{n}'))
    write_d_modulos(d_modulos, os.path.join(os.path.dirname(DATA_PATH), 'd_modulos.json'))
    logger.info("pipeline: d_modulos.json escrit (%d cicles D)", len(d_modulos))
except Exception as exc:
    logger.warning("pipeline: build_d_modulos ha fallat (no fatal): %s", exc)
```

`tests/test_pipeline.py`: a la fixture autouse `isolate_data_path` afegir
`monkeypatch.setattr(dms, 'build_d_modulos', lambda records, **kw: {})`
(import `scrapers.d_modulos_scraper as dms`), i dos tests calcats dels de
`bc_lomloe` (`test_run_escriu_d_modulos_json`, `test_run_no_falla_si_d_modulos_peta`)
amb `PATCH_BUILD_D_MODULOS = 'scrapers.d_modulos_scraper.build_d_modulos'`.

## Fase 3 — Derivació pura `backend/cd_lomloe.py` (TDD)

### Tests primer: `backend/tests/test_cd_lomloe.py`

Dades inline (no cal la fixture per als unitaris; usar-la només al test 6).

```python
from cd_lomloe import normalize_module_name, build_c_lomloe_to_d
```

1. `test_normalize`: `'Inglés Profesional (Grado Superior)'` → `'ingles profesional'`;
   `'Estructura del mercado turístico.'` → `'estructura del mercado turistico'`;
   `'Protocolo y relaciones públicas'` → `'protocolo y relaciones publicas'`.
2. `test_c_a_d_per_nom_mateixa_familia`: records: C `HOT_C_005_5B` (fam
   "Hostelería y Turismo"), B `HOT_B_0171` "Estructura del mercado turístico",
   D id 700 (fam "Hostelería y Turismo", mòduls `[{num: None, name: 'Estructura del mercado turístico.'}]`)
   → `{'HOT_C_005_5B': [{'id': 700, 'shared': 1, 'total': 1}]}`.
3. `test_c_a_d_per_codi`: mòdul D `{num: '0171', name: 'qualsevol'}` → mateix resultat (el codi mana).
4. `test_ignora_altra_familia`: D de família "Comercio y Marketing" amb el
   mateix mòdul → `{}`.
5. `test_ordena_per_fraccio_i_calcula_total`: C amb 2 B; D1 comparteix 2, D2
   comparteix 1 → `[{'id': D1, 'shared': 2, 'total': 2}, {'id': D2, 'shared': 1, 'total': 2}]`.
6. `test_fixture_real_cobertura`: carregar `plans/outputs/spike_d_plans.json`
   (`d`) com a `d_modulos` i `plans/outputs/spike_043_c_lomloe_modulos.json`
   per construir `bc_lomloe` i records mínims (C amb família = del prefix via
   `scrapers.pipeline.PREFIX_MAP` o inline per a 3 famílies); comprovar que
   `HOT_C_005_5B` té com a primer D un amb `shared == total == 5` i
   denominació que conté "Agencias de Viajes". (Si muntar records complets
   és pesat, limitar el test a la família HOT: 1 C, els seus 5 B, i els D
   de la fixture amb `familia == 'Hostelería y Turismo'`.)

### Implementació

```python
def normalize_module_name(name: str) -> str:
    s = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode().lower()
    s = re.sub(r'\((grado superior|grado medio|gs|gm)\)', '', s)
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()

def build_c_lomloe_to_d(records, bc_lomloe, d_modulos) -> dict[str, list[dict]]:
    """{codigo_c: [{'id': id_d, 'shared': n, 'total': m}, ...]} ordenat per shared/total desc, id asc."""
```

Passos: `b_by_num` (`^[A-Z]{3}_B_(\d{4})$` → codi) i `b_by_name`
(`normalize(denominacion)` → set de codis) dels B LOMLOE; `fam_c` per codi C;
`d_recs` per id (família); per a cada D: `bs = ∪ (b_by_num[num] si num else b_by_name[normalize(name)])`;
per a cada C de `bc_lomloe`: `total = len(bc[c])`; per a cada D de la
mateixa família: `shared = |set(bc[c]) ∩ bs|`; si > 0 → afegir. `total == 0` → saltar el C.

## Fase 4 — `app.py` (TDD a `tests/test_centres_inherit_api.py`)

Afegir a la fixture `data_dir`: `d_modulos.json` amb el D id 700 (fam "H",
mòduls `[{num: None, name: 'B nou'}]`, coincident amb la denominació del B
id 50 `HOT_B_0171` = 'B nou'), un registre D a `OFERTES`
(`{'id': 700, 'grado': 'D', 'codigo': None, 'plan_antiguo': False, 'denominacion': 'T.S. Prova', 'familia': 'H', 'nivel': 3, 'ficha_url': 'https://x/y.html'}`),
`monkeypatch` de `D_MODULOS_PATH` i `_d_modulos_cache`.

Tests:
1. `test_itinerari_c_lomloe_ciclos_d`: `GET /api/itinerari?grado=C&codigo=HOT_C_005_5B`
   → `ciclos_d == [{'id': 700, 'denominacion': 'T.S. Prova', 'familia': 'H', 'ficha_url': 'https://x/y.html', 'shared': 1, 'total': 1}]`.
2. `test_itinerari_c_loe_ciclos_d_no_canvia`: per a `ADGG0408` (C LOE) la
   resposta continua sortint de `ciclos_fp.json` (mockejar `CICLOS_PATH` a
   un fitxer tmp amb `{"ADGG0408": [{"denominacion": "X", "familia": "F", "ficha_url": null}]}`).

Implementació:
- `D_MODULOS_PATH = os.path.join(_DATA_DIR, "d_modulos.json")`, `_d_modulos_cache`,
  `_get_d_modulos()` (clon exacte de `_get_bc_lomloe`, amb el check `isinstance(dict)`).
- `_cd_lomloe_cache = {"key": None, "data": None}` i `_get_c_lomloe_to_d()`:
  clau = mtimes de `DATA_PATH`, `BC_LOMLOE_PATH`, `D_MODULOS_PATH`; llegeix
  `records` de `DATA_PATH` i crida `cd_lomloe.build_c_lomloe_to_d(records, _get_bc_lomloe(), _get_d_modulos())`.
  Guardar també `d_by_id = {str(r['id']): r for r in records if r.get('grado') == 'D'}` a la cache.
- A `api_itinerari`, branca `grado == 'C'`: si `codigo` matxeja
  `^[A-Z]{3}_C_\d+_\w+$` (LOMLOE) → `ciclos = [{'id': int(e['id']), 'denominacion': d['denominacion'], 'familia': d['familia'], 'ficha_url': d.get('ficha_url'), 'shared': e['shared'], 'total': e['total']} for e in entries if d := d_by_id.get(str(e['id']))]`
  **sense** passar pel `CICLOS_PATH` (moure el `if not os.path.exists(CICLOS_PATH)` dins de la branca LOE). C LOE: sense canvis.
- Els tests de `test_api.py` que mockegen `builtins.open` (`test_itinerari_grado_c_retorna_parent_b_loe`)
  tenen un `_fake_open`: afegir-hi `if 'd_modulos' in path_str: return mock.mock_open(read_data='{}')()`
  **abans** de la branca `'bc_loe'`.

## Fase 5 — Frontend (`frontend/index.html`, `frontend/i18n.js`)

1. **Clic de fila** (línia ~2123, `@click`): la primera branca passa de
   `row.grado === 'C' && row.plan_antiguo` a `row.grado === 'C'` (tots els C
   despleguen). La classe `row-link` ja cobreix C amb `ficha_id`.
2. **Panell** (línia ~2181): `<tr x-show="expandedRows[row.id] && row.grado === 'C' && row.plan_antiguo">`
   → afegir un segon `<tr x-show="expandedRows[row.id] && row.grado === 'C' && !row.plan_antiguo">`
   amb `<td colspan="5" class="detall-certificat"><div class="detall-inner">`:
   - `<div class="detall-btns">`: `<a class="btn-doc" href="#" @click.prevent="loggedIn ? window.open(API_BASE + '/api/ficha-redirect?grado=C&codigo=' + encodeURIComponent(row.codigo), '_blank') : showCentresModal()" x-text="t('index.detall.ficha_todofp')">`
     i `<button @click.stop="fetchCiclosD(row.codigo)" class="btn-doc" x-text="t('index.itinerari.ciclos_d_btn')">`.
   - Bloc cicles D: **copiar** el bloc `<!-- F5: Cicles D -->` existent i, a
     l'`x-text` del cicle, afegir el sufix
     `(cicle.total && cicle.shared < cicle.total ? ' — ' + t('index.itinerari.ciclos_d_parcial', {n: cicle.shared, m: cicle.total}) : '')`.
     `:key` → `cicle.id ?? cicle.denominacion`.
   - Bloc mòduls B: copiar el de `parentBLoeData` canviant a `parentBLomloeData[row.codigo]`
     i la caption `t('index.itinerari.parent_b_lomloe_cap')`.
3. `fetchCiclosD`: afegir `this.parentBLomloeData = { ...this.parentBLomloeData, [codigo]: data.parent_b_lomloe || [] };`
   i declarar `parentBLomloeData: {}` al costat de `parentBLoeData`.
4. i18n (CA / ES):
   - `index.detall.ficha_todofp`: 'Fitxa a todofp.es' / 'Ficha en todofp.es'
   - `index.itinerari.ciclos_d_parcial`: 'cobreix {n} de {m} mòduls' / 'cubre {n} de {m} módulos'
   - `index.itinerari.parent_b_lomloe_cap`: 'Mòduls professionals (graus B) d\'aquest certificat:' / 'Módulos profesionales (grados B) de este certificado:'
   Comprovar que la funció `t()` accepta `{n, m}` (ja ho fa amb `{n}` a `index.centres.count`).
5. Cap CSS nou: reutilitzar `.detall-certificat`, `.detall-btns`, `.btn-doc`, `.ciclos-d-list`.

## Fase 6 — Verificació, desplegament, primera generació

1. `cd backend && python -m pytest` → tot verd excepte els 2 preexistents de
   `tests/test_db.py` (`schema_version` 8 vs 1). No tocar-los.
2. Commit: `feat(itinerari): C LOMLOE → D via shared modules; detail panel for new-plan C`.
3. `git push` → VPS (`root@62.169.25.188`, clau `~/.ssh/id_ed25519_roger`):
   `cd /home/masellas-grausfp/htdocs/grausfp.masellas.info && git status -sb`
   (**comprovar drift abans**) → `git pull --ff-only` → `systemctl restart fp-cercador`
   (no és PM2) → `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8033/api/centres/count` = 200.
4. Primera generació sense esperar el refresc (les `ficha_url` dels D no
   caduquen, a diferència dels `ficha_id`):
   ```bash
   cd /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend
   nohup ../../venv/bin/python -c "
   import json,logging; logging.basicConfig(level=logging.INFO)
   from scrapers.d_modulos_scraper import build_d_modulos, write_d_modulos
   r=json.load(open('data/ofertes.json',encoding='utf-8'))
   idx=build_d_modulos(r,on_progress=lambda p,i,n: print(f'PROGRESS {p} {i}/{n}',flush=True))
   write_d_modulos(idx,'data/d_modulos.json'); print('DONE',len(idx),flush=True)
   " > /tmp/d_modulos_gen.log 2>&1 &
   ```
   Esperar `DONE 195` (~4 min). El servei no cal reiniciar-lo (cache per mtime).
5. Comprovar: `curl -s 'http://127.0.0.1:8033/api/itinerari?grado=C&codigo=HOT_C_005_5B'`
   → `ciclos_d` amb ≥3 entrades, la primera amb `shared == total == 5` i
   denominació "…Agencias de Viajes…"; `ADG_C_001_3B` → "Servicios
   Administrativos" `3/3`. A `index.html`, clicar la fila `HOT_C_005_5B`:
   panell amb "Fitxa a todofp.es", "Cicles FP (D)" → llista amb "(cobreix 4
   de 5 mòduls)" als parcials, i la llista de 5 mòduls B. Un C antic
   (`ADGG0408`) continua igual.
6. `plans/README.md`: 058 DONE amb xifres reals (nombre de C amb cicles).

## Fora d'abast

- `grado=D` → `parent_c_lomloe` (invers). Trivial afegir-ho després si la UI ho demana.
- Centres per a D via `ensenanzaFP`.
- Tocar `ciclos_fp.json` / C LOE.

## Riscos

- **Fals positiu per nom**: dos mòduls amb el mateix nom normalitzat en famílies
  diferents es resolen a B diferents; la restricció de família del C ho
  neutralitza. Verificat al spike: 4 parelles sorolloses de 553.
- **Durada del refresc**: +4 min (ja era ~15 min amb el 057).
- **Canvi de comportament del clic** a files C noves (abans obria la fitxa):
  l'enllaç segueix disponible dins el panell. Avisar-ho a l'usuari al resum.
