# Spike 043 — Resultats (abast reorientat): B LOMLOE → C LOMLOE via fitxa todofp

Executat: 2026-09-06
Executor: Claude (sessió fp-cercador)
Commit base: db87698

## Nota sobre l'abast

El pla 043 original (2026-06-19) investigava dues relacions: **C LOMLOE→D** i
**B→C LOE**. La segona ja es va implementar als plans 045/046 (`bc_loe.json` +
`/api/itinerari`), i la primera ha deixat de ser prioritària. El que bloquejava
feina real el 2026-09-06 era la relació **B LOMLOE → C LOMLOE**, necessària
per heretar centres als graus A/B de pla nou (continuació del pla 056). Aquest
spike investiga això. Les preguntes originals sobre C LOMLOE→D queden obertes
(veure "Fora d'abast").

## Taula de viabilitat

| Relació | Font | Cobertura | Esforç | Risc | Veredicte |
|---|---|---|---|---|---|
| B LOMLOE → C LOMLOE | Fitxa `todofp.es/buscadorgradosfp/ficha?grado=C&id={ficha_id}` → secció "Módulos Profesionales ( NNNN ) nom" → `FAM_B_NNNN` | **1.008 / 1.019 B (99 %)**; 400/400 fitxes parsejades | S (scraper de ~400 GET + índex JSON) | LOW | ✅ **VIABLE** |
| A LOMLOE → C LOMLOE | Derivat: `FAM_A_NNNN_PP → FAM_B_NNNN` (ja a `itinerary.py`) + relació anterior | **5.893 / 5.953 A (99 %)** | — (cap font nova) | LOW | ✅ **VIABLE** |
| Centres heretats A/B LOMLOE (avui) | Cadena anterior + `oferta_centres.json` (pla 055) | 624 B (61 %), 3.631 A (61 %) — limitat pels C-nou que encara no tenen centres acreditats (249/400) | S (reutilitza `centres_inherit.py`) | LOW | ✅ **VIABLE** |
| C LOMLOE → D (pregunta original) | No investigada en aquesta execució | — | — | — | ⏸ Pendent |

## Mecanisme confirmat

Un **Grau B LOMLOE és un mòdul professional** del Catàleg Modular. El seu codi
`FAM_B_NNNN` porta el número del mòdul (`NNNN`, 4 dígits amb zeros a
l'esquerra: `HOT_B_0171`). La fitxa web de cada **C LOMLOE** llista els seus
mòduls amb aquest mateix número:

```
Código: HOT_C_005_5B … Módulos Profesionales
( 0171 ) Estructura del mercado turístico     → HOT_B_0171 ✓
( 0172 ) Protocolo y relaciones públicas      → HOT_B_0172 ✓
( 0179 ) Inglés profesional (gs)              → HOT_B_0179 ✓ (també ADG/ARG/COM/MAP_B_0179)
( 0180 ) Segunda lengua extranjera            → HOT_B_0180 ✓
( 0397 ) Gestión de productos turísticos      → HOT_B_0397 ✓
( 1782 ) Prevención de riesgos laborales      → (cap B; mòdul transversal)
```

Regla de match: `(família del C, NNNN)` → `FAM_B_NNNN`. Els mòduls compartits
entre famílies (Inglés profesional 0179) es resolen a la **mateixa família del
C**; només 1 cas de 1.897 hauria necessitat un B d'una altra família.

## Detall de proves

### Fitxes (`buscadorgradosfp/ficha?grado=C&id=`)

- Bootstrap: `GET /buscadorgradosfp/buscador` per cookies (`JSESSIONID`,
  `__Host-todofp.es`), com fa `buscador_scraper.py`. Després GET simples.
- **Els `ficha_id` del `ofertes.json` local (2026-05) són obsolets**: id 172
  retornava `HOT_C_005_5B` en lloc de `ADG_C_001_3B`. Amb els ids del
  `ofertes.json` del VPS (refrescat 2026-09-05) les **400 fitxes coincideixen
  amb el codi esperat** (verificat comparant `Código:` de la pàgina). Això
  confirma el que ja avisa `app.py` (`_resolve_ficha_id`): els ids s'han de
  llegir del refresc més recent, mai cachejar-los en codi.
- Format estable a totes les fitxes: text pla amb `( NNNN ) Nom` dins la
  secció "Módulos Profesionales", delimitada per "Nota:". També hi ha els
  estàndards de competència `( ECPNNNN_N )` (no calen per a aquest match).
- Rastreig complet: 400 GET a ~2,5 s cadascun (latència todofp) ≈ 16 min.
  16 fitxes consecutives (ELE/ENA) van fallar en una finestra transitòria;
  reintent 1 min després → 16/16 OK. **Cal reintent amb backoff** al scraper.
- Cap fitxa sense mòduls. Mitjana 4,7 mòduls per C (1.897 en total).

### Cobertura (dades VPS 2026-09-06)

| | Total | Amb C pare | Amb C pare que té centres avui |
|---|---|---|---|
| Mòduls llistats a fitxes C | 1.897 | 1.384 (73 %) tenen B | — |
| B LOMLOE | 1.019 | **1.008 (99 %)** | 624 (61 %) |
| A LOMLOE | 5.953 | **5.893 (99 %)** | 3.631 (61 %) |

- Els 513 mòduls sense B són gairebé tots transversals: "Prevención de riesgos
  laborales" (355), "…en construcción" (25), "Nivel básico en PRL" (12). No
  existeixen com a oferta B → correcte que no matxin.
- 11 B sense C pare: `AFD_B_1335`, `TMV_B_0538`, `TMV_B_0542`, `TMV_B_1621`,
  `TMV_B_1622`, `FME_B_0247`, `IMP_B_0749`, `SSC_B_0011`, `SSC_B_0015`,
  `SSC_B_1123`, +1. Probablement mòduls de cicles D encara sense C LOMLOE
  publicat. Acceptable.
- 195 B tenen més d'un C pare (màx. 15: mòduls comuns com Inglés). L'herència
  de centres ha de fer la **unió** dels C, com ja fa `centres_inherit.py`.
- El 61 % "amb centres avui" pujarà sol a mesura que els C-nou s'acreditin
  (el scraping setmanal del pla 055 ho recull).

### Artefactes generats (no producció)

- `plans/outputs/spike_043_c_lomloe_modulos.json` (232 KB): per a cada C
  LOMLOE, `{ficha_id, modulos: [{num, nombre}], ecp: [...]}`. Serveix com a
  fixture de tests i com a referència del format.

## Recomanació per a implementació (pla nou, suggerit 057)

### 1. Scraper `backend/scrapers/bc_lomloe_scraper.py` → `backend/data/bc_lomloe.json`

- Input: C LOMLOE de `ofertes.json` (`grado=='C' and not plan_antiguo`), amb
  el seu `ficha_id` **del mateix fitxer** (mai hardcoded).
- Per cada C: `GET {BASE_URL}/ficha?grado=C&id={ficha_id}` amb la sessió de
  `buscador_scraper._bootstrap()` (reutilitzar, no duplicar). Verificar que
  `Código:` == codi esperat; si no, log WARNING i saltar (ids obsolets).
- Parse: text de la secció entre "Módulos Profesionales" i "Nota:",
  regex `\(\s*(\d{4})\s*\)`. Resoldre a `FAM_B_NNNN` amb la família del C
  (els 3 primers caràcters del codi C). Guardar només els que existeixen a
  `ofertes.json` com a B LOMLOE.
- Output: `{codigo_c: [codigo_b, ...]}` — **mateixa forma que `bc_loe.json`**
  (`{codigo_c: [uc, ...]}`), perquè `_get_bc_loe_inverse` es pugui
  generalitzar o clonar amb un canvi mínim.
- Rate-limit 1 req/s, reintent ×3 amb backoff (5/15/45 s) — imprescindible
  vist el bloc de 16 fallades transitòries. ~10–16 min per run.
- Enganxar-lo al mateix job/endpoint admin que el scraping de centres (o al
  refresc d'ofertes, ja que depèn dels `ficha_id` frescos). Preferible:
  **just després del refresc d'ofertes**, que és quan els ids canvien.

### 2. Herència de centres (`backend/centres_inherit.py`)

Afegir la branca LOMLOE a `build_inherited()`:
- B LOMLOE `^[A-Z]{3}_B_\d{4}$` → `bc_lomloe_inverse[codigo_b]` → llista de
  codis C → clau a `oferta_centres` = `str(id del C)` (pla 055; **no** el
  codi, a diferència de C LOE). Cal un `c_lomloe_id_by_codigo` a l'índex.
- A LOMLOE → `itinerary.get_parent_b()` (ja resol `FAM_A_NNNN_PP → FAM_B_NNNN`)
  → mateixa branca.
- Signatura: afegir paràmetres `bc_lomloe_inverse` i `c_id_by_codigo` (o un
  únic objecte d'índex). `app.py:_get_effective_oferta_centres` i
  `centres_watch_service._inherited_ab_loe` passen a carregar també
  `bc_lomloe.json` (fail-soft si no existeix, com ara).
- La nota i18n `index.centres.inherited` ja és vàlida per als dos plans.

### 3. `/api/itinerari` (opcional, mateix pla o següent)

`grado=B` LOMLOE avui retorna `children_c_loe: []`. Amb `bc_lomloe.json` es
pot omplir un `children_c_lomloe` simètric, i per a `grado=C` LOMLOE un
`parent_b_lomloe`. Cost baix un cop existeix l'índex.

### Ordre i esforç

1 (scraper + fitxer, S) → 2 (herència, S; TDD sobre `centres_inherit`) → 3
(opcional). Total S–M. Resultat esperat en producció: ~624 B i ~3.631 A de
pla nou amb centres el primer dia, creixent amb cada scraping.

## Fora d'abast d'aquesta execució

- **C LOMLOE → D** (pregunta original del 043): no investigat. Pista nova
  trobada de passada: la fitxa C LOMLOE llista els seus mòduls `NNNN`, i els
  cicles D del `ciclosFP` també s'identifiquen per mòdul `NNNN` (spike 041).
  Un índex D per (família, NNNN) — que és exactament la SEC 5 del pla 043 —
  permetria C LOMLOE→D **sense cap font nova**, només amb `bc_lomloe.json` +
  `ciclos_fp.json`. Val la pena reprendre-ho com a spike curt.
- `plans/outputs/spike_043_investigate.py` no s'ha creat: la investigació
  s'ha fet amb scripts efímers; les comandes essencials són al text anterior.
