# Pla 056 — Centres heretats per a graus A i B (pla antic / LOE)

Origen: `plans/outputs/spike_centres_abc_results.md` §Fase 2 i pla 055 (DONE).
Executable per un agent sense context.

## Context

Cap registre públic acredita centres per a graus A o B: un centre s'acredita
pel **certificat C** i, per definició, pot impartir els seus mòduls (B) i
unitats formatives (A). Per tant, per a una oferta A/B mostrarem els centres
del(s) C que la contenen, indicant clarament que són **heretats**.

Només **LOE** (`plan_antiguo=True`). LOMLOE queda fora: falta la relació
B→C (spike 043, mai executat).

Cadena de dades **ja existent** (verificada al VPS el 2026-09-06):
- A LOE `UF####` → B LOE `MF####_N`: `itinerary.get_parent_b()` (`backend/itinerary.py`).
- B LOE `MF####_N` → `UC####_N` → codis C LOE: `bc_loe.json` (584 C, 2.729 UC)
  invertit per `_get_bc_loe_inverse()` a `app.py:1000`.
- C LOE → centres: `oferta_centres.json[codigo_c]`.

Cobertura real: 1.949 B LOE → 1.923 amb C pare (99 %) → 1.828 amb centres
(94 %). 2.872 A LOE hereten via el seu B.

## Decisió de disseny: derivar en memòria, NO al fitxer

Guardar l'herència a `oferta_centres.json` el faria passar de 3 MB a ~20 MB
(4.821 claus × 266 centres de mitjana). En canvi, es calcula un cop al
backend (funció pura, cache per mtime) i s'exposa **amb la mateixa clau
`str(id)` que D/E/C-nou**. Així:
- `/api/centres?id=` i `/api/centres/count` funcionen sense canviar el
  contracte; el frontend ja envia `id=` per a A/B.
- `centres-watch` pot seguir ofertes A/B sense cap canvi de clau.
- Els resums del scraping (`admin_refresh_centres`, "centres nous") segueixen
  treballant sobre el fitxer cru — no s'inflen amb dades derivades.

## Fase 1 — Mòdul pur `backend/centres_inherit.py` (TDD)

**Test primer**: `backend/tests/test_centres_inherit.py` (patró de
`test_itinerary.py`: dades inline, sense fitxers ni xarxa).

```python
def build_inherited(records: list[dict], ab_index: dict,
                    bc_loe_inverse: dict, oferta_centres: dict) -> dict[str, list[str]]:
    """
    Retorna {str(id_oferta): [centre_id, ...]} per a les ofertes A i B LOE
    que hereten centres d'algun certificat C LOE. Ordenat i sense duplicats.
    Ofertes sense cap C pare amb centres NO apareixen al resultat.
    """
```

Regles:
- B LOE (`^MF(\d{4})_(\d+)$`): `UC{g1}_{g2}` → `bc_loe_inverse[uc]` → unió de
  `oferta_centres[codigo_c]` per a cada C.
- A LOE (`^UF\d{4}$`): `itinerary.get_parent_b(record, ab_index)` → si hi ha B,
  mateixa regla que B. Reutilitzar el resultat del B (calcular B primer).
- Ignorar A/B LOMLOE i qualsevol altre grau.
- Retornar llistes `sorted(set(...))` per a determinisme.

Tests (han de fallar abans d'implementar):
1. `test_b_loe_hereta_unio_de_c_pares`: B `MF0969_1` amb dos C pares que
   tenen centres `[x, y]` i `[y, z]` → `{'<id_b>': ['x','y','z']}`.
2. `test_a_loe_hereta_via_b`: A `UF0038` → B `MF0038_3` → C → mateixos
   centres que el B.
3. `test_sense_c_pare_no_apareix`: B LOE amb UC que no és a l'índex → clau
   absent (no `[]`).
4. `test_ignora_lomloe`: `ADG_B_3001` i `ADG_A_3001_01` → absents.

## Fase 2 — Backend `app.py`

1. Helper amb cache:
   ```python
   _effective_oc_cache = {"key": None, "data": None}

   def _get_effective_oferta_centres() -> dict:
       """oferta_centres.json + herència A/B LOE. Cache per mtimes de
       ofertes.json, bc_loe.json i oferta_centres.json."""
   ```
   Clau de cache = tupla de mtimes (`DATA_PATH`, `BC_LOE_PATH`,
   `_OFERTA_CENTRES_PATH`); si algun no existeix, usa `None`. Construeix
   `{**_oferta_centres, **build_inherited(records, _get_itinerary_index(),
   _get_bc_loe_inverse(), _oferta_centres)}`.
   Els `records` es llegeixen de `DATA_PATH` (o reutilitza el que ja carrega
   `_get_itinerary_index` si és fàcil — no dupliquis lectures si no cal).
2. Substituir `_oferta_centres` per `_get_effective_oferta_centres()` **només**
   a: `get_centres` (`app.py:242`), `get_centres_count` (`:254`) i el snapshot
   inicial de `centres-watch` (`:2010`).
   **No tocar** `admin_refresh_centres` (`:758-810`): compara dades crues del
   scraping.
3. A `admin_refresh_centres`, després de `_oferta_centres = None`, invalidar
   també `_effective_oc_cache` (posar `key=None`).
4. `backend/centres_watch_service.py:_load_centres_data()` (llegeix de disc
   per al job de notificacions): aplicar el mateix merge amb
   `build_inherited` perquè un usuari que segueixi una oferta A/B rebi
   avisos. Importar `itinerary` i `centres_inherit`; llegir `bc_loe.json` amb
   el mateix path que `app.py` (`BC_LOE_PATH`). Fail-soft: si `bc_loe.json`
   no existeix, retornar el dict cru.

**Tests** (`test_api.py`, seguint el patró d'aïllament de fitxers que ja
faci servir per a centres; si no n'hi ha, crear fixtures a `tmp_path` i
monkeypatch de `_CENTRES_PATH`, `_OFERTA_CENTRES_PATH`, `DATA_PATH`,
`BC_LOE_PATH` + reset de `_centres_index`/`_oferta_centres`/caches):
- `GET /api/centres?id=<id_B_LOE>` retorna els centres del C pare.
- `GET /api/centres/count` inclou la clau del B LOE amb el recompte correcte
  i **no** inclou un B LOE sense C pare.

## Fase 3 — Frontend (mínim)

`frontend/index.html`, dins el desplegable de centres (bloc que usa
`centresData[row.id]`, ~línia 1698+): afegir una nota estàtica quan
`row.grado === 'A' || row.grado === 'B'`:

- i18n (`frontend/i18n.js`), CA i ES:
  - `index.centres.inherited`: "Centres acreditats per al certificat de
    professionalitat que inclou aquest mòdul/unitat" / "Centros acreditados
    para el certificado de profesionalidad que incluye este módulo/unidad".
- Estil: reutilitzar `.textpetit` o similar existent. Sense CSS nou.

`perfil.html`: cap canvi (usa `/api/centres/count` i `centresClau()` → ja
funciona). Verificar visualment que la pestanya de favorits mostra el
recompte per a un A/B LOE.

## Fase 4 — Verificació i desplegament

1. `cd backend && python -m pytest` — tot verd excepte les 2 fallades
   preexistents de `tests/test_db.py` (`schema_version` = 8 vs 1), que no
   s'han de tocar.
2. Local, sense xarxa: `python3 -c` que carregui `ofertes.json` +
   `oferta_centres.json` + `bc_loe.json` (cal baixar `bc_loe.json` del VPS a
   `backend/data/` si no hi és — està al `.gitignore`?) i imprimeixi
   `len(build_inherited(...))` → esperat ≈ 1.828 B + els A associats.
3. Mesurar `len(json.dumps(count))` de `/api/centres/count`: passarà de
   ~1.213 a ~6.000 claus. Acceptable (< 100 KB). Si algun dia molesta,
   comprimir o paginar — no ara.
4. Commit convencional `feat(centres): inherit centres for A/B LOE offers
   from parent C certificates`.
5. Desplegament: `git push` → al VPS **comprovar `git status` abans de
   `git pull`** (precedent de drift) → `git pull --ff-only` →
   `systemctl restart fp-cercador` (aquest servei NO va amb PM2) →
   `curl /api/centres/count` ha de respondre 200 i contenir claus noves.
6. Comprovar a producció `index.html`: un B LOE (ex. `MF0969_1`) i un A LOE
   (ex. `UF0038`) mostren badge de centres i la nota d'herència; un B LOMLOE
   (`ADG_B_3001`) continua sense badge.

## Fora d'abast

- LOMLOE A/B: bloquejat pel spike 043.
- Mostrar *quin* C pare aporta cada centre: `/api/itinerari?grado=B` ja
  retorna `children_c_loe`; si es vol enllaçar, pla a part.
- Cap canvi al scraper ni als fitxers de dades.

## Riscos

- **Memòria**: el dict efectiu afegeix ~1,3 M referències a ids (llistes
  noves, strings compartits) → estimació 10–20 MB RAM al procés Flask. Cal
  mesurar al VPS (`systemctl status` / RSS) després de desplegar.
- **`centres-watch`** per a A/B: el "snapshot inicial" es fa amb el dict
  efectiu, i el job de notificacions també (Fase 2.4). Si només es fes un
  dels dos, l'usuari rebria o bé zero avisos o bé un allau de "nous" el
  primer dia. Els dos costats han d'usar el mateix `build_inherited`.
- **Rendiment de `build_inherited`**: ~4.8 k ofertes × unió de llistes de
  fins a 4.232 ids → < 1 s. Es calcula un cop per mtime, no per request.
