# Pla 061 — FPO: favorits (especialitat + cursos) i UI d'admin

Origen: `docs/superpowers/specs/2026-09-06-fpo-soc-catalunya-design.md` (§8, §9).
Depèn de: **059 DONE** (endpoints `/api/fpo/*`, `soc_*.json`) i **060 DONE**
(mode FPO al cercador, panell de detall amb el ganxo `<!-- Pla 061 -->`).
Executable per un agent sense context (Sonnet). **TDD estricte** al backend
(migracions, endpoints); validació manual als canvis de `perfil.html` / `admin.html`.
**Totes les decisions estan preses aquí i a la spec.**

## Context

- Autenticació i sessió: `_get_session_user(req)` a `app.py` retorna el
  `user_id` de la sessió o `None`. Els endpoints de favorits de la FP reglada
  (`/api/favorites*`) són el patró a clonar (llegir-los primer).
- Migracions: `backend/migrations/NNN_*.sql`, l'última és `008_*`. Les noves són
  **009** i **010**. El runner de migracions és `backend/db.py` (`run_migrations`).
- Favorits reglats: taula `favorites(user_id, oferta_id)` + selecció de centres a
  `favorite_centres` (Pla del F2 / migració 007). El model FPO és equivalent:
  favorit = **especialitat**, selecció = **cursos/centres** dins l'especialitat.
- `frontend/perfil.html`: secció "Favorits" (llistat en columna amb centres
  seleccionats) i pestanyes "Alertes" / "Seguiment de centres (novetats)".
  Funció `fichaHref(row)`, `centresClau(row)`, `loadFavorits()`.
- `frontend/admin.html`: targetes d'estat dels processos de refresc; `refresh_state.py`
  guarda el progrés; endpoints d'admin protegits amb `ADMIN_TOKEN`.

## Decisions de disseny

1. **Favorit = especialitat FPO** (`fpo_favorites`). **Selecció = curs concret**
   (`fpo_favorite_courses`, clau `idCurs`), amb `centre_id` desat per poder
   mostrar el curs encara que desaparegui del snapshot.
2. Endpoints nous sota `/api/fpo/favorites`. Requereixen sessió (401 si no).
3. A `perfil.html`, **secció nova** "Especialitats FPO" (no pestanya nova al
   `section-nav`; s'afegeix com a bloc dins la mateixa pàgina, sota Favorits —
   **decisió: pestanya nova** al `section-nav` per coherència amb Alertes/Seguiment).
   → **Pestanya nova**: `#fpo` amb id `tab-fpo`, etiqueta "Especialitats FPO".
4. Un curs marcat que ja no és al snapshot es mostra en gris amb "curs
   finalitzat" (patró ja existent per als centres desapareguts a Favorits).
5. Admin: **botó de refresc dedicat** + targeta d'estat. El refresc executa
   només `build_soc_data()` + `write_soc_data()` (no el pipeline sencer).

## Fase 1 — Migracions i capa de dades (TDD)

### Tests primer: `backend/tests/test_db.py` (o `test_fpo_favorites_db.py`)

Amb una BBDD en memòria migrada:
1. `test_migracio_009_010_crea_taules`: després de `run_migrations`, existeixen
   les taules `fpo_favorites` i `fpo_favorite_courses` amb les columnes
   esperades (consulta `PRAGMA table_info`).
2. `test_fk_cascade`: esborrar un `users` row esborra les seves files a totes
   dues taules.

> Nota: `tests/test_db.py` té 2 tests preexistents que fallen per `schema_version`
> (8 vs 1). **No tocar-los**; els nous tests es poden posar en un fitxer a part
> per no barrejar-los.

### Implementació

`backend/migrations/009_fpo_favorites.sql`:
```sql
CREATE TABLE fpo_favorites (
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    especialitat_codi TEXT    NOT NULL,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, especialitat_codi)
);
```
`backend/migrations/010_fpo_favorite_courses.sql`:
```sql
CREATE TABLE fpo_favorite_courses (
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    especialitat_codi TEXT    NOT NULL,
    curs_id           TEXT    NOT NULL,
    centre_id         TEXT,
    created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, especialitat_codi, curs_id)
);
```
Actualitzar el `schema_version` de la mateixa manera que ho fan 007/008 (llegir-les).

## Fase 2 — Endpoints `/api/fpo/favorites` (TDD)

### Tests primer: `backend/tests/test_fpo_favorites_api.py`

Fixtura amb usuari + sessió vàlida (clonar el helper de sessió de
`test_*` de favorits reglats) i `soc_*.json` mínims (reusar la fixtura del Pla 059).

1. `test_get_sense_sessio_401`: `GET /api/fpo/favorites` sense cookie → 401.
2. `test_desa_i_llista_especialitat`: `POST /api/fpo/favorites {especialitat_codi:'IFCD0112'}`
   → 200/201; `GET /api/fpo/favorites` → conté `IFCD0112` amb `titol`, `familia`,
   `nivell`, `hores` (enriquit des de `_get_soc_especs()`), `cursos: []`.
3. `test_marca_curs`: `POST /api/fpo/favorites/IFCD0112/courses {curs_id:'X', centre_id:'97428'}`
   → `GET` mostra el curs amb dades resoltes del snapshot (centre, dates, estat).
4. `test_curs_finalitzat`: marcar un `curs_id` que no és a `soc_cursos.json` →
   `GET` el retorna amb `finalitzat: true` i les dades que es puguin
   (`centre_id` desat).
5. `test_delete_especialitat_esborra_cursos`: `DELETE /api/fpo/favorites/IFCD0112`
   → desapareix, i les seves files de `fpo_favorite_courses` també.
6. `test_delete_curs`: `DELETE /api/fpo/favorites/IFCD0112/courses/X` → el curs
   surt de la llista, l'especialitat es manté.

### Implementació

`backend/app.py`, rutes noves (clonar l'estil de `/api/favorites*`):

| Ruta | Acció |
|---|---|
| `GET /api/fpo/favorites` | especialitats de l'usuari, cada una enriquida amb `_get_soc_especs()` + els seus cursos marcats enriquits amb `_get_soc_cursos()` (o `finalitzat: true`) |
| `POST /api/fpo/favorites` `{especialitat_codi}` | insereix a `fpo_favorites` (idempotent) |
| `DELETE /api/fpo/favorites/<codi>` | esborra especialitat + cursos |
| `POST /api/fpo/favorites/<codi>/courses` `{curs_id, centre_id}` | insereix a `fpo_favorite_courses` |
| `DELETE /api/fpo/favorites/<codi>/courses/<curs_id>` | esborra el curs |

Totes: `user_id = _get_session_user(request)`; si `None` → `401`.

## Fase 3 — `perfil.html` — pestanya "Especialitats FPO"

1. `section-nav`: nou `<a href="#fpo" class="section-nav-link" id="tab-fpo"
   data-i18n="perfil.nav.fpo">Especialitats FPO</a>` després de
   "Seguiment de centres (novetats)". Afegir `'fpo'` a l'array de `tabs`.
2. `<div id="section-fpo">` nou.
3. `loadFpo()` (clon de `loadFavorits()`):
   - `GET /api/fpo/favorites` (amb `credentials:'include'`); 401 → missatge
     `perfil.login.required`; buida → `perfil.fpo.empty`.
   - Render en columna (mateix component visual que Favorits): per cada
     especialitat, nom · família/àrea · nivell · hores, i sota, els cursos
     marcats amb centre + dates + badge d'estat. Un curs `finalitzat: true` es
     mostra en gris amb `perfil.fpo.curs_finalitzat`.
   - Botó ✕ per treure l'especialitat (`DELETE /api/fpo/favorites/<codi>`) i ✕
     per treure cada curs marcat.
4. `main()` / init de la pàgina: afegir `loadFpo()` al `Promise.all([...])`
   existent.
5. Claus i18n noves (CA/ES): `perfil.nav.fpo`, `perfil.fpo.empty`
   ("Encara no segueixes cap especialitat de formació per a l'ocupació.<br>Obre
   el mode <a href=\"index.html?mode=fpo\">Cursos FPO</a> al cercador i desa'n
   una."), `perfil.fpo.curs_finalitzat` ("Curs finalitzat"),
   `perfil.fpo.cursos_marcats` ("Cursos que segueixes:").

### Ganxo al cercador (`index.html`, del Pla 060)

Al panell de detall d'una especialitat FPO (on el Pla 060 va deixar
`<!-- Pla 061: ⭐ ... -->`):
- Si `loggedIn`: botó ⭐ "Desa aquesta especialitat" que fa `POST`/`DELETE`
  `/api/fpo/favorites/<codi>` i reflecteix l'estat (`fpoFavSet` — un `Set` de
  codis carregat a `init()` amb `GET /api/fpo/favorites` quan `loggedIn`).
- Per cada curs de la llista, si `loggedIn` i l'especialitat és desada: un
  `<input type="checkbox">` que fa `POST`/`DELETE`
  `/api/fpo/favorites/<codi>/courses` amb `curs_id` i `centre_id`.
- Sense login: no es mostren aquests controls (el panell segueix visible).
- Claus i18n: `fpo.fav.save` ("Desa aquesta especialitat"),
  `fpo.fav.saved` ("Especialitat desada ✓"), `fpo.fav.track_course`
  ("Segueix aquest curs") — CA/ES.

## Fase 4 — Admin (TDD al backend, manual al frontend)

### Tests primer: `backend/tests/test_admin_fpo.py`

1. `test_refresh_fpo_sense_token_403`: `POST /api/admin/refresh-fpo` sense
   `ADMIN_TOKEN` → 403.
2. `test_refresh_fpo_executa_i_escriu` (`build_soc_data` mockejat): amb token →
   200, i s'han escrit `soc_*.json` a la ruta de dades; l'estat de refresc
   (`refresh_state`) reflecteix "completat".
3. `test_refresh_fpo_error_reporta` (`build_soc_data` amb `side_effect`): amb
   token → resposta d'error (5xx o `{ok:false}`), estat "error" amb missatge, i
   `_notify_admin_soc_failure` cridat (respectant el rate-limit del Pla 059).

### Implementació

`backend/app.py`:
- `POST /api/admin/refresh-fpo` (protegit amb `ADMIN_TOKEN`, com els altres
  endpoints d'admin): executa `from scrapers.soc_scraper import build_soc_data, write_soc_data`,
  escriu a `os.path.dirname(DATA_PATH)`, actualitza `refresh_state` amb una clau
  pròpia (`'fpo'`), i en cas d'error crida `_notify_admin_soc_failure` i
  registra l'estat.
- `GET /api/admin/status` (o el que ja alimenti l'admin): afegir un bloc `fpo`
  amb `{last_snapshot: mtime de soc_cursos.json, cursos, especs, centres,
  last_error}`.

`frontend/admin.html`:
- Targeta nova "Cursos FPO (SOC)": data de l'últim snapshot, recomptes, estat
  (OK / error + missatge), i botó **"Actualitzar cursos FPO"** que crida
  `POST /api/admin/refresh-fpo` amb el token i mostra el progrés (reutilitzar el
  patró de les altres targetes de refresc i `refresh_state`).
- Claus i18n `admin.fpo.*` (CA/ES): títol, botó, "Últim snapshot", "sense dades".

## Fase 5 — Verificació i desplegament

1. `cd backend && python -m pytest` → verd (excepte els 2 preexistents de
   `test_db.py`).
2. Server local + BBDD de test:
   - Registrar/entrar, obrir mode FPO, desar una especialitat, marcar 1–2
     cursos. Anar a Perfil → "Especialitats FPO": hi surten amb els cursos.
   - Marcar un `curs_id` inexistent via API i comprovar "curs finalitzat" en gris.
   - Admin: la targeta FPO mostra data i recomptes; el botó refresca.
   - CA i ES.
   - Screenshot per a l'usuari.
3. Commit: `feat(fpo): favorits d'especialitat + cursos i UI d'admin`.
4. `git push` → VPS → `git pull --ff-only`. **Aquest pla té migracions**:
   després del pull, el servei aplica `run_migrations` a l'arrencada
   (`systemctl restart fp-cercador`); verificar als logs que 009 i 010 s'han
   aplicat. `curl` de `/api/fpo/favorites` (401 sense sessió) i de
   `/api/admin/status` (amb token) mostrant el bloc `fpo`.
5. `plans/README.md`: 061 DONE. Actualitzar també la línia de la feature FPO si
   se n'ha afegit una de resum.

## Fora d'abast

- Alertes sobre especialitats FPO.
- Exportació CSV de la selecció FPO.
- Mapa de centres.

## Riscos

- **Migracions a producció**: 009/010 són `CREATE TABLE` noves, sense tocar
  dades existents → risc baix. Verificar igualment als logs post-restart.
- **Coherència de `centre_id`**: es desa com a text tal com ve del snapshot;
  si el SOC canvia el format d'`idCentre`, els cursos marcats antics quedarien
  orfes → es mostren igualment com a "finalitzat" amb el `centre_id` cru.
