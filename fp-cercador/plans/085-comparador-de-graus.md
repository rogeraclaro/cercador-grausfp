# Pla 085 — Comparador de graus

Origen: auditoria 2026-11-14, idea 3 de 9; disseny validat pel propietari el mateix dia.
Executable per un agent sense context, en una sessió nova. Depèn de: 058, 076, 077 (pàgines
públiques per grau, `_grau_context`), 078, tots DONE. Independent dels plans 083 i 084.

## Què fa

Compara fins a 3 graus en columnes, amb el que tenen en comú ressaltat. L'adreça
`compara.html?refs=a,b,c` es pot compartir.

## Decisions del propietari (tancades, no reobrir)

| Tema | Decisió |
|---|---|
| Abast | Fitxa completa en columnes: una columna per grau, una fila per tema. |
| Selecció | Casella «Compara» a les files del cercador; màxim 3; es poden barrejar lletres. |
| Dades que falten | **Acceptat** que l'accés i la durada dels cicles D no hi siguin: no les tenim. |

Fora d'aquesta versió: accés i durada dels D (caldria un scraper nou), més de 3 graus, desar
comparacions.

## Fets verificats (2026-11-14, no repetir)

- `backend/app.py::_grau_context(rec, seo)` (~línia 2303) ja munta, per a un grau:
  `contingut`, `ocupaciones`, `centres` (`_grau_centres(ref)`), `previs`, `seguents`,
  `familia_prefix`, `lastmod`. `seo` ve de `_get_seo_data()`.
- `contingut` depèn del grau:

  | Grau | Claus de `contingut` |
  |---|---|
  | A | `ra` (llista), `ecp` |
  | B | `ecp`, `ra` |
  | C pla antic | `uc`: `[{codigo, nombre}]` |
  | C pla nou | **buit** — els mòduls són a `_get_c_modulos()[codigo]` (`[{num, name}]`) i no s'hi afegeixen |
  | D | `modulos`: llista de noms |
  | E | `acceso` (nodes), `acceso_otros` |

- No tenim requisits d'accés dels D ni durada en hores (només `duracion_horas` dels C del pla
  antic, si el registre la porta).
- Normalització de noms de mòdul: `cd_lomloe.normalize_module_name`.
- `/api/grau/<ref>` torna **HTML** (pàgina pública), no JSON: cal un endpoint nou.
- Validació de `ref`: `oferta_ref.REF_RE` i `_resolve_oferta(ref=…)`.
- La fila desplegada del cercador té les accions a prop de `.row-share-menu`
  (`frontend/index.html`). L'estat de la llista es desa amb `saveListState()`.

## API

`GET /api/compara?refs=a,b,c` — pública.

- 2 o 3 `ref` separats per comes, cadascun validat amb `REF_RE` i resolt al catàleg.
  Menys de 2 vàlids, més de 3 o algun inexistent → 400 amb `{"error", "invalids": [...]}`.
  503 si no hi ha catàleg.
- Resposta:

```json
{"graus": [{"ref", "grado", "codigo", "denominacion", "familia", "nivel", "nivel_label",
            "plan_antiguo", "duracion_horas",
            "moduls": ["…"], "uc": [{"codigo","nombre"}], "ra": ["…"], "ecp": ["…"],
            "acces": ["…"], "ocupacions": ["…"],
            "centres": {"total": 48, "per_ccaa": {"Cataluña": 12, …}},
            "previs": [{"ref","grado","denominacion"}], "seguents": [ … ]}],
 "comuns": {"moduls": ["nom tal com surt al primer grau"],
            "ocupacions": ["…"],
            "seguents": ["ref"]},
 "moduls_compartits": {"n": 5, "de": 14}}
```

- `comuns.moduls`: noms normalitzats presents a **tots** els graus comparats que tinguin
  mòduls (mínim 2 graus amb mòduls; si no, llista buida). `moduls_compartits.de` és el
  nombre de mòduls del grau que en té menys.
- `comuns.ocupacions` i `comuns.seguents`: intersecció exacta.
- Lògica en un mòdul nou i pur, `backend/compare.py`:
  `build_comparison(contexts: list[dict]) -> dict`, que rep ja els contextos per grau.
  L'endpoint només resol els `ref`, crida `_grau_context` i afegeix els mòduls dels C del
  pla nou.
- Capçalera `Cache-Control: public, max-age=3600` (les dades només canvien amb el refresc).

## Fases

Cada fase acaba amb els tests verds i un commit (`feat(compare): …`, sense atribució d'IA).

### Fase 1 — `backend/compare.py` + `backend/tests/test_compare.py`
Tests primer. Casos mínims:
- dos D amb 3 mòduls en comú escrits amb accents i «(GS)» diferents;
- tres graus on un mòdul és comú a dos però no al tercer (no ha de sortir a `comuns`);
- C pla nou + D: els mòduls del C venen de `c_modulos`;
- un grau sense mòduls (A o B) barrejat amb un D: `comuns.moduls` buit, sense error;
- ocupacions comunes; `seguents` comuns.

### Fase 2 — Endpoint `/api/compara`
`backend/tests/test_compare_api.py`: `ref` invàlid, un sol `ref`, quatre `ref`, duplicats
(es deduplica; si en queda un de sol → 400), barreja de lletres, i que la resposta porta
`centres.per_ccaa`. Aïllar els camins de dades com fan `test_grau_page.py` i `test_refs_api.py`.

### Fase 3 — `frontend/compara.html`
- Alpine 3, `site.css`, barra superior, `auth.js`, `footer.js`, `feedback.js`, analítica.
  `<meta name="robots" content="noindex">`.
- Llegeix `refs` de l'adreça; sense `refs` o amb un de sol, estat buit que explica com triar
  graus des del cercador.
- Ordinador (≥ 900 px): taula amb la primera columna (tema) i la capçalera fixes. Cada
  capçalera de columna: distintiu de grau, denominació, ✕ per treure (actualitza l'adreça
  amb `history.replaceState`) i enllaç a `/grau/<ref>`.
- Files, en aquest ordre, **només si algun grau té la dada**: dades bàsiques · mòduls
  (bloc «comuns» amb el recompte, després «propis» per columna) · unitats de competència ·
  resultats d'aprenentatge i capacitats · requisits d'accés · sortides professionals
  (comunes ressaltades) · centres (total i selector de comunitat autònoma, que canvia el
  número de totes les columnes alhora) · d'on vens · a què dona pas.
- Cel·la sense dada: «—» amb `aria-label` «sense dades».
- Llistes de més de 8 elements: plegades amb «Mostra'n N més».
- Mòbil: una targeta per tema amb els graus apilats, cadascun amb el seu distintiu.
- Estats: carregant, error amb reintent, `ref` invàlid (missatge i enllaç al cercador).
- Botó «Comparteix» (mateix patró que la fila del cercador: menú del sistema al mòbil).

### Fase 4 — Selecció des del cercador
- `index.html`: casella «Compara» a cada fila (columna estreta nova, o dins la fila
  desplegada si la taula no hi cap al mòbil: decidiu-ho mirant-ho a 375 px).
- Estat `compareRefs` (màxim 3), desat a `sessionStorage` i inclòs a `saveListState()`.
  En arribar a 3, les altres caselles queden desactivades amb un `title` que ho explica.
- Barra fixa a baix quan n'hi ha almenys un: els graus triats amb ✕, «Compara (N)»
  (desactivat amb 1) i «Buida». No ha de tapar la paginació: afegiu `padding-bottom` al
  contenidor quan la barra és visible.
- Accessibilitat: la barra és una regió amb `aria-label`; els canvis s'anuncien amb
  `aria-live="polite"`.

### Fase 5 — «Compara amb…» des de la fitxa i l'itinerari
- `backend/grau_page.py::render_grau`: enllaç «Compara amb un altre grau» →
  `/index.html?compara=<ref>`, que el cercador llegeix per preomplir `compareRefs`.
- `itinerari.html`: el mateix enllaç a la capçalera del grau enfocat.
- Actualitzar `backend/tests/test_grau_page.py`.

### Fase 6 — Textos i versions
Claus `cmp.*` a `i18n.js` (ca i es); apujar `?v=` a totes les pàgines i `I18N_VERSION`.
Enllaç al peu (`footer.js`) no: s'hi arriba des del cercador.

### Fase 7 — Verificació
- `cd backend && python3 -m pytest tests -q --ignore=tests/test_pipeline.py` verd.
- Al navegador, ca i es, amb `ofertes.json` i `d_modulos.json` del mateix refresc:
  dos cicles D de la mateixa família (han de compartir mòduls comuns), un C del pla nou
  amb el D amb què es relaciona, i una barreja A + D (sense fila de mòduls comuns).
- Treure una columna, canviar la comunitat autònoma, compartir l'enllaç i obrir-lo net.
- 375 px: sense desplaçament horitzontal de pàgina.

## STOP — atura't i pregunta

- Si `_grau_context` triga més de ~300 ms per grau (construeix el subgraf d'itinerari):
  mesura-ho abans d'optimitzar res i ensenya la xifra.
- Si la casella «Compara» no hi cap a la taula sense trencar el disseny del mòbil
  (`DESIGN.md`): ensenya dues opcions abans de triar.
- No desplegar sense aprovació explícita. Mai reiniciar diumenge 11:10–11:45.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
