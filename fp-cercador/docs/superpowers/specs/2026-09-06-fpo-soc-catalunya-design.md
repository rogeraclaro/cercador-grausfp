# FPO — Formació professional per a l'ocupació (SOC Catalunya)

**Data:** 2026-09-06
**Estat:** disseny aprovat, pendent de pla d'implementació

## 1. Objectiu

Incorporar l'oferta de **formació professional per a l'ocupació (FPO)** de Catalunya
al cercador, com a font complementària a la FP reglada (Grados A–E) que ja s'hi mostra.

La FPO és un sistema diferent de la FP reglada: el gestionen les comunitats
autònomes, no dona un títol del catàleg estatal sinó especialitats formatives i
certificats de professionalitat, i l'oferta són **cursos concrets amb dates,
places i centre**. La font disponible cobreix **només Catalunya** (Servei Públic
d'Ocupació de Catalunya, SOC) i així es diu a la interfície, sense promesa
d'abast estatal.

## 2. Font de dades

El cercador integrat del SOC
(`serveiocupacio.gencat.cat/.../cercador-integrat`) està servit per **Algolia**
(cerca com a servei). El frontend consulta Algolia directament amb claus de
lectura incrustades al JavaScript del client. CORS obert (`*`), sense captcha ni
cookies. Es pot recórrer tot l'índex amb `browse`.

- **Application ID:** `GAVVNU5N19`
- **Host:** `https://gavvnu5n19-dsn.algolia.net`
- **Índexs i claus read-only:**

| Índex | Clau API | Registres (2026-09) | Contingut |
|---|---|---|---|
| `pro_SOC_CURSOS` | `1a344732c2a6e07f1e8aded4b3ec5ee5` | ~1.035 | Cursos FPO programats a Catalunya |
| `pro_SOC_ESPECS_r1a` | `a71db7100e3362cc9522f7c7f79f954f` | ~2.974 | Catàleg d'especialitats formatives |
| `pro_SOC_CENTRES` | `08611804f7810c349cd2b2bc8a77e438` | ~2.708 | Centres i entitats de formació a Catalunya |

### Esquema rellevant — `pro_SOC_CURSOS`

```
idCursIntern, idCurs (codi d'expedient), objectID
titol {cat, cas}
famProf {codi, desc{cat,cas}}          # taxonomia SOC, 28 famílies
area {codi, desc{cat,cas}}             # subdivisió dins la família (codi 4 lletres)
especialitat {codi, desc{cat,cas}}     # codi SEPE; per als cert. prof. és el codi del certificat
certProf                               # referència del RD (BOE) si és certificat de professionalitat
teCertProf ("Si"/"No")
nivellEspecialitat (0..3)
hores
modalitat ("PRESENCIAL" | "TELEFORMACIÓ" | "MIXTA")
estatInscripcio ("Curs en període d'informacio" | "...d'inscripcio" | "en Gestio...")
dataInici, dataFi (dd/mm/aaaa), dataIniciOrdre (aaaammdd)
comarca, municipi, provincia
centres {nomLoc, calleLoc, localidadLoc, codPostalLoc, telefonLoc, mailLoc,
         webLoc, idCentre, horariLoc{dilluns..diumenge}, lat, lon}
codOcupacio [{codi, desc{cat,cas}}]
programa {cat, cas}                     # URL PDF (conforcat.gencat.cat en català; SEPE en castellà)
queAprendras {cat,cas}
dadesInteres {requisits{cat,cas}, quePoderTreballar{cat,cas}}
unitatCompetencia [{codi, desc, modulFormatiu [{codi, desc, durada, unitatFormativa[]}]}]
temes [{titol, desc}]
emailAccio, esCifo ("S"/"N"), perDiscapacitats ("S"/"N")
```

### Esquema rellevant — `pro_SOC_ESPECS_r1a`

```
codi, desc {cat,cas}
familia {codi, desc}, area {codi, desc}
hores, preu, nivellEspecialitat
certProf                               # RD del certificat, o "undefined"
programa {cat, cas}                    # PDF conforcat.gencat.cat (CA) / SEPE (ES)
unitatCompetencia [...modulFormatiu...]
cursos [{idCursIntern}]                # ids de cursos actius d'aquesta especialitat
centres [{idCentre}]
espDestacada ("S"/"N"), dataBaixa
```

### Esquema rellevant — `pro_SOC_CENTRES`

```
idCentre
data {codiEntitat, raoSocial, cif, numCens, email, web, codiCentre, carrer,
      comarca, cp, municipi, provincia, telefon, lat, lng, numCursos,
      esCifo ("S"/"N"), perDiscapacitats ("S"/"N")}
especialitat []
```

### Relació amb la FP reglada

- **Cap solapament amb els Grado C de pla nou (LOMLOE).** Verificat: dels ~1.035
  cursos, cap fa servir el format de codi LOMLOE (`FAM_C_NNN_NL`); tots són del
  catàleg antic de certificats de professionalitat (RD 34/2008 i posteriors).
- **Solapament amb els Grado C de pla antic (LOE).** 720 dels cursos són
  certificats de professionalitat i el seu `especialitat.codi`
  (`ADGG0408`, `COMT0112`, `IFCD0112`…) **coincideix 1:1** amb el `codigo` dels
  registres `grado == 'C' && plan_antiguo` de `ofertes.json`. Aquesta és la clau
  d'unió del bloc d'integració (§7).
- Les famílies "Competències Transversals", "Formació Complementària", "Arts i
  Artesania" i altres del SOC **no** existeixen a la FP reglada. El mode FPO fa
  servir la taxonomia pròpia del SOC (família + àrea), no `families.py`.

## 3. Decisions de disseny

| # | Decisió |
|---|---|
| D1 | **Snapshot periòdic**, no proxy en viu. Un scraper llegeix els 3 índexs i escriu 3 JSON; s'executa dins `pipeline.run()` com a bloc no-fatal. Refresc 1×/dia (el del pipeline). |
| D2 | **Àmbit Catalunya, dit clarament.** El mode es diu "Cursos FPO (Catalunya)". Nota contextual fixa explicant que és un sistema de gestió autonòmica. Cap promesa d'abast estatal. |
| D3 | **Tercer mode al toggle existent** del cercador (`Nom · Ocupació · Cursos FPO`). No es crea pàgina separada. |
| D4 | **Unitat de resultat = especialitat formativa.** Es llisten les especialitats amb ≥1 curs actiu. El panell desplega els cursos concrets (centre + dates + estat). |
| D5 | **Panell de detall obert a tothom.** És informació pública i és la crida a l'acció. No es fa gating per login (a diferència dels centres de la FP reglada). |
| D6 | **Favorits = especialitat FPO**, amb selecció de cursos/centres a dins (mateix model que oferta → centres a la FP reglada). L'usuari ha d'estar registrat. El favorit no caduca; els cursos concrets sí. |
| D7 | **Jerarquia de filtres Família → Àrea → Especialitat** (selects dependents), a més de comarca → municipi, nivell, estat d'inscripció, modalitat i "només certificats de professionalitat". |
| D8 | **Sense alertes** per a FPO a la v1. Es podria afegir sobre l'especialitat més endavant. |
| D9 | Claus API del SOC **hardcoded** al scraper (són públiques, read-only). Si el SOC les rota, el bloc falla de manera no-fatal i avisa l'admin. |

## 4. Component 1 — Dades (`soc_scraper.py` + pipeline)

**`backend/scrapers/soc_scraper.py`** (patró: clonar l'estructura de
`bc_lomloe_scraper.py` / `d_modulos_scraper.py`):

```python
ALGOLIA_APP = 'GAVVNU5N19'
ALGOLIA_HOST = 'https://gavvnu5n19-dsn.algolia.net'
INDEXES = {
    'cursos':  ('pro_SOC_CURSOS',     '1a344732c2a6e07f1e8aded4b3ec5ee5'),
    'especs':  ('pro_SOC_ESPECS_r1a', 'a71db7100e3362cc9522f7c7f79f954f'),
    'centres': ('pro_SOC_CENTRES',    '08611804f7810c349cd2b2bc8a77e438'),
}

def browse_index(name, api_key) -> list[dict]     # POST /1/indexes/<idx>/browse, pagina amb cursor
def normalize_curs(hit) -> dict                    # aplana i neteja un hit de CURSOS
def normalize_espec(hit) -> dict
def normalize_centre(hit) -> dict
def build_soc_data() -> dict                       # {'cursos': [...], 'especs': [...], 'centres': [...]}
def write_soc_data(data, data_dir)                 # 3 fitxers atòmics (tmp + os.replace)
```

- `browse` en comptes de `query` per treure l'índex sencer sense límit de 1000.
- **Normalització**: a cada registre, resoldre `{cat, cas}` no es fa aquí (es
  guarda tal qual i el frontend tria idioma). Sí que es:
  - aplana `especialitat.codi`, `familia.codi`/`desc`, `area.codi`/`desc`
  - converteix `hores`/`preu`/`nivell` a número, dates a ISO `aaaa-mm-dd`
  - deriva `esCertProf` (bool) de `teCertProf`/`certProf`
  - a `especs`, guarda `cursIds` (de `cursos[].idCursIntern`) per a la unió ràpida
- Sortida:
  - `backend/data/soc_cursos.json` — llista de cursos normalitzats
  - `backend/data/soc_especs.json` — llista d'especialitats normalitzades
  - `backend/data/soc_centres.json` — catàleg de centres (per a deduplicació i
    dades de contacte; els cursos ja porten centre incrustat, però aquest és la
    font canònica)

**`backend/scrapers/pipeline.py`** — bloc nou just després del bloc Pla 058
(`d_modulos`), mateix patró no-fatal:

```python
_report('Cursos FPO (SOC Catalunya)')
try:
    from scrapers.soc_scraper import build_soc_data, write_soc_data
    soc = build_soc_data()
    write_soc_data(soc, os.path.dirname(DATA_PATH))
    logger.info("pipeline: soc_*.json escrit (%d cursos, %d especialitats, %d centres)",
                len(soc['cursos']), len(soc['especs']), len(soc['centres']))
except Exception as exc:
    logger.warning("pipeline: build_soc_data ha fallat (no fatal): %s", exc)
    _notify_admin_soc_failure(exc)   # §8
```

## 5. Component 2 — Backend API

`backend/app.py`:

- `SOC_CURSOS_PATH`, `SOC_ESPECS_PATH`, `SOC_CENTRES_PATH` a `_DATA_DIR`.
- `_get_soc_especs()`, `_get_soc_cursos()`, `_get_soc_centres()` — clons de
  `_get_bc_lomloe()` (cache per mtime, `[]`/`{}` si falta o corrupte).
- `_soc_meta` — data del fitxer més recent + recomptes, per a admin i banner.

**Endpoints:**

| Ruta | Retorna |
|---|---|
| `GET /api/fpo/especialitats` | Llista completa d'especialitats **amb ≥1 curs actiu**, cadascuna amb: `codi, titol{ca,es}, familia{codi,desc}, area{codi,desc}, nivell, hores, esCertProf, rd, nCursos, comarques[], programaUrl`. Filtratge al client (≈600 registres, dins el límit de 1.500 de rendiment). Camp `warning` si el snapshot ha fallat o té > N dies. |
| `GET /api/fpo/especialitat/<codi>` | Detall: `descripcio, requisits, sortides, moduls[], programaUrl`, i `cursos[]` (cada un: `idCurs, centre{nom,adreça,cp,municipi,comarca,telefon,email,web,horari,lat,lon}, dataInici, dataFi, estat, modalitat, fitxaUrl`). |
| `GET /api/fpo/by-cert?codigo=<codi_C_LOE>` | Cursos FPO l'`especialitat.codi` dels quals és `codigo`. Per al bloc d'integració §7. `{ especialitat, nCursos, cursos: [...] }` o `{}`. |

`fitxaUrl` del curs: la fitxa pública del cercador SOC
(`.../cercador-integrat/detall.html?...` o equivalent — a confirmar durant la
implementació inspeccionant un clic de resultat real).

## 6. Component 3 — Mode "Cursos FPO" al frontend

`frontend/index.html` (Alpine) + `frontend/i18n.js`.

- **Estat**: `searchMode: 'nom' | 'ocupacio' | 'fpo'`. `?mode=fpo` a la URL.
  `fpoEspecs: []`, `fpoLoaded: false`, `fpoDetall: {}` (cache per codi).
- **Toggle**: tercer botó `t('index.mode.fpo')` = "Cursos FPO (Catalunya)".
- **Lazy load**: en entrar a `fpo` per primer cop, `fetch('/api/fpo/especialitats')`.
- **Nota contextual** (sempre visible en mode `fpo`, `x-show="searchMode==='fpo'"`):
  *"Formació professional per a l'ocupació. Oferta i gestió de la Generalitat de
  Catalunya (SOC) — sistema diferent de la FP reglada. Cobreix només Catalunya."*
- **Barra de filtres pròpia** (`x-show="searchMode==='fpo'"`, no reutilitza la de
  la FP reglada):
  - Text lliure (títol / codi d'especialitat)
  - **Família** (select, taxonomia SOC) → **Àrea** (select, opcions filtrades per
    família) → **Especialitat** (select, opcions filtrades per àrea)
  - **Comarca** → **Municipi** (selects dependents, valors del SOC)
  - **Nivell** (1–3; el 0 = "sense nivell", s'inclou a "tots")
  - **Estat d'inscripció** (Tots · Informació · **Inscripció oberta**)
  - **Modalitat** (Tots · Presencial · Teleformació · Mixta)
  - Toggle "Només certificats de professionalitat"
- **Taula de resultats** (reutilitza `.results-table`):
  columnes → Nom · Codi · Família · Àrea · Nivell · Hores · Cursos actius ·
  (badge) Cert. prof.
- **Panell desplegable** (`.detall-certificat`, com la FP reglada):
  - Descripció · requisits · sortides professionals
  - Mòduls formatius (llista amb durada)
  - Botó "Programa (PDF)" → `programaUrl` (versió catalana)
  - **Llista de cursos actius**: per cada curs, targeta amb centre (nom, adreça,
    CP, municipi/comarca, telèfon, email, web, horari setmanal), dates
    inici–fi, **badge d'estat d'inscripció**, modalitat, botó "Fitxa al SOC".
  - **Usuari registrat**: ⭐ "Desa aquesta especialitat" + checkbox a cada
    curs/centre de la llista (patró idèntic a "seleccionar centres" de la FP
    reglada). Sense login: panell complet visible, sense controls de desat.
- **Banner d'error** (`x-show` si `/api/fpo/especialitats` retorna `warning` o
  falla): *"L'oferta de cursos FPO no està disponible temporalment."*
- **i18n**: claus noves `index.mode.fpo`, `fpo.note`, `fpo.filter.*`,
  `fpo.col.*`, `fpo.estat.*`, `fpo.detall.*`, `fpo.banner.unavailable` (CA + ES).
  El contingut de dades ja ve bilingüe del SOC: es tria `titol.ca`/`titol.es`
  segons `getLang()`.

## 7. Component 4 — Integració amb els Grado C de pla antic

A la fitxa de detall dels certificats `grado == 'C' && plan_antiguo`
(`frontend/index.html`, panell `x-show="... row.plan_antiguo"`):

- En expandir el panell, `fetch('/api/fpo/by-cert?codigo=' + row.codigo)`
  (cache per codi).
- Si `nCursos > 0`, bloc nou:
  *"També s'ofereix com a formació per a l'ocupació a Catalunya — **N cursos
  actius**"* + enllaç "Veure'ls al cercador FPO" que obre
  `index.html?mode=fpo&esp=<codi>` (el mode FPO llegeix `?esp=` i pre-filtra per
  aquella especialitat i n'obre el panell).
- Si `nCursos == 0` o l'endpoint falla: no es mostra res.

## 8. Component 5 — Favorits FPO

**Base de dades** — migracions noves:

```sql
-- 009_fpo_favorites.sql
CREATE TABLE fpo_favorites (
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    especialitat_codi TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, especialitat_codi)
);

-- 010_fpo_favorite_courses.sql
CREATE TABLE fpo_favorite_courses (
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    especialitat_codi TEXT    NOT NULL,
    curs_id           TEXT    NOT NULL,   -- idCurs del SOC
    centre_id         TEXT,               -- idCentre (per mostrar si el curs desapareix)
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, especialitat_codi, curs_id)
);
```

**Endpoints** (mateix estil que `/api/favorites`):

| Ruta | Acció |
|---|---|
| `GET /api/fpo/favorites` | Especialitats desades de l'usuari + els seus cursos marcats |
| `POST /api/fpo/favorites` `{especialitat_codi}` | Desa especialitat |
| `DELETE /api/fpo/favorites/<codi>` | Treu especialitat (i els seus cursos marcats) |
| `POST /api/fpo/favorites/<codi>/courses` `{curs_id, centre_id}` | Marca curs |
| `DELETE /api/fpo/favorites/<codi>/courses/<curs_id>` | Desmarca curs |

**`frontend/perfil.html`** — secció/pestanya nova "Especialitats FPO":

- Llistat en columna (mateix component visual que Favorits de la FP reglada).
- Cada especialitat: nom, família/àrea, nivell, hores, i els cursos marcats amb
  centre + dates + estat.
- Un curs marcat que ja no és a `soc_cursos.json` (ha acabat) es mostra en gris
  amb "curs finalitzat" (patró ja existent per als centres desapareguts).

## 9. Component 6 — Admin

`frontend/admin.html` + endpoint de refresc:

- Targeta nova "Cursos FPO (SOC)": data de l'últim snapshot, recompte
  (cursos / especialitats / centres), estat (OK / error + missatge).
- Botó **"Actualitzar cursos FPO"** → `POST /api/admin/refresh-fpo` (protegit amb
  `ADMIN_TOKEN`), executa `build_soc_data()` + `write_soc_data()` fora del
  pipeline complet. Reusa el patró d'estat de refresc existent
  (`refresh_state.py`) per mostrar el progrés en recarregar.

## 10. Component 7 — Gestió d'errors i avisos

- **Bloc no-fatal** al pipeline (ja contemplat): si `build_soc_data` peta, el
  refresc continua i els JSON antics es mantenen.
- **Email a l'admin**: `_notify_admin_soc_failure(exc)` via `notifier.py` /
  `email_service.py` (mateix canal que les altres alertes d'admin). Assumpte:
  "Snapshot FPO (SOC) ha fallat". Cos: excepció + hora + últim snapshot vàlid.
  Rate-limit: 1 email per dia com a màxim (per no espamejar si el SOC està caigut
  diversos dies).
- **Frontend**: banner al mode FPO si `/api/fpo/especialitats` retorna `warning`
  (fitxer inexistent, o `mtime` de fa més de X dies — X a definir, p. ex. 7).
- **Detecció de rotació de claus**: si `browse_index` retorna 401/403, es
  registra explícitament "clau API del SOC possiblement rotada" al warning i a
  l'email.

## 11. Component 8 — Historial

`backend/history.py` + `frontend/historial.html`:

- El snapshot FPO queda registrat com una font més a l'historial d'actualitzacions
  (mateix mecanisme que es va afegir per a l'scraping de centres): data, resultat
  (OK / error), i deltes bàsiques (cursos afegits / retirats respecte del
  snapshot anterior, si es pot calcular comparant `idCurs`).
- Es mostra a `historial.html` dins la mateixa taula paginada, amb etiqueta
  "Cursos FPO (SOC)".

## 12. Component 9 — Plana "Fonts de dades"

`frontend/fonts.html` + `frontend/i18n.js`:

- Secció nova **"Servei Públic d'Ocupació de Catalunya (SOC)"** (`fonts.s6.*`),
  amb host `serveiocupacio.gencat.cat` i una taula amb els 3 índexs (cursos,
  especialitats, centres) i què se n'obté.
- Nota explícita: *"La formació professional per a l'ocupació és de gestió
  autonòmica; aquesta font cobreix només Catalunya."*
- Claus `fonts.*` noves CA + ES, i `index.footer` / navegació sense canvis
  (la plana ja està enllaçada).

## 13. Fora d'abast (v1)

- Altres comunitats autònomes (cada una té el seu cercador d'FPO).
- Alertes automàtiques sobre especialitats FPO.
- Cerca per ocupació dins el mode FPO (el camp `codOcupacio` sovint ve buit).
- Mapa interactiu de centres FPO (es podria fer amb `lat`/`lon` més endavant).
- Grado C de pla nou (LOMLOE): la font del SOC no en té.

## 14. Riscos

| Risc | Mitigació |
|---|---|
| El SOC rota les claus API d'Algolia | Bloc no-fatal + email a l'admin + banner; claus fàcils d'actualitzar al scraper |
| Dades de cursos volàtils (dates, places) | Refresc diari; badge d'estat d'inscripció; cursos finalitzats es marquen, no desapareixen dels favorits |
| Barrejar dos sistemes confon l'usuari | Mode separat al toggle + nota contextual fixa + àmbit "Catalunya" explícit a tot arreu |
| Taxonomia de famílies divergent (SOC 28 vs reglada 27) | El mode FPO usa la taxonomia pròpia del SOC; no es força cap mapatge |
| Volum: ~600 especialitats + panells amb desenes de cursos | Dins el límit de rendiment de 1.500 registres; filtratge i detall al client; `/api/fpo/especialitat/<codi>` per al detall pesat |

## 15. Ordre d'implementació suggerit

Probablement **2–3 plans**:

1. **Dades + backend** (§4, §5, §10, §11): scraper, pipeline, endpoints
   `/api/fpo/*`, gestió d'error, historial. Verificable amb `curl` i tests.
2. **Mode FPO + integració** (§6, §7, §12): toggle, filtres, panell, bloc als
   Grado C LOE, plana Fonts.
3. **Favorits FPO + admin** (§8, §9): migracions, endpoints de favorits, secció a
   `perfil.html`, targeta i botó a `admin.html`.
