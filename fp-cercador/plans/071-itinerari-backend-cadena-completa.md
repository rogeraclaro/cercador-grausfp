# 071 — Itinerari: endpoint de cadena completa + relació D→C

**Prioritat:** P2 · **Esforç:** M · **Depèn de:** — · **Estat:** DONE
**Spec:** `docs/superpowers/specs/2026-10-23-itinerari-visual-design.md` (llegeix-la abans: hi ha el model de dades comú).

## Objectiu

Un sol endpoint que, donat un grau, retorni **tot el seu itinerari** (ascendents i descendents) com a nodes + arestes, perquè la pàgina `itinerari.html` (pla 072) i el graf (pla 073) no hagin d'encadenar crides. Inclou la relació inversa **D→C**, que avui no existeix.

## Contracte

`GET /api/itinerari/complet?grado=A|B|C&codigo=…` o `?grado=D|E&id=…`, paràmetre opcional `depth=1`.

```json
{
  "focus": "C:ADG_C_001_3B",
  "nodes": [{"key":"C:ADG_C_001_3B","grado":"C","codigo":"ADG_C_001_3B","id":null,
             "denominacion":"…","familia":"…","nivel":"1","plan_antiguo":false,
             "ficha":"/api/ficha-redirect?grado=C&codigo=ADG_C_001_3B"}],
  "edges": [{"from":"B:ADG_B_3001","to":"C:ADG_C_001_3B","kind":"bc"},
            {"from":"C:ADG_C_001_3B","to":"D:12776","kind":"cd","shared":3,"total":3}],
  "warnings": []
}
```

- Sense `depth`: tots els **ascendents** del focus (A→B→C→D→E, seguint arestes cap amunt) i tots els **descendents** (cap avall). No els germans d'altres branques.
- `depth=1`: només els veïns directes (amunt i avall) del node; ho fa servir l'exploració del graf.
- 400 si `grado` o l'identificador no són vàlids (reutilitza `_CODIGO_RE` per als codis; `id` numèric per a D/E); 404 si el grau no existeix.
- `warnings`: fonts que falten (p. ex. `ciclos_fp.json` absent), com fa ja `/api/itinerari`.
- `ficha`: per a A/B/C, `/api/ficha-redirect?grado=…&codigo=…` (ja existeix i resol l'id viu); per a D/E, el `ficha_url` del registre. **Només http(s)** (vegeu el criteri de l'auditoria a `safeHttpUrl`).

## Com construir-ho (reutilitza el que hi ha)

- Construeix un índex en memòria, **cachejat per mtime** dels fitxers de dades (patró de `_get_itinerary_index` i `centres_inherit`), amb arestes en totes dues direccions:
  - **A↔B:** `itinerary.build_ab_index` / `get_parents_b` (LOMLOE pel codi; LOE via `a_loe_pares.json`).
  - **B↔C:** `bc_loe.json` (LOE, B `MF####_N` ↔ `UC####_N`) i `bc_lomloe.json` (LOMLOE). Hi ha índexs inversos a `app.py` (~1201-1230, ~1547): reutilitza'ls o mou-los a un mòdul, sense canviar el comportament de `/api/itinerari`.
  - **C→D LOMLOE:** `cd_lomloe.build_c_lomloe_to_d` (porta `id`, `shared`, `total`).
  - **C→D LOE:** `ciclos_fp.json` no porta id de D: resol-lo contra els registres D de `ofertes.json` per `ficha_url` (normalitzant esquema/host/barra final) i, si no, per `denominacion` normalitzada + `familia`. Els no resolts → `warnings` (no inventis ids).
  - **D→C:** és l'índex invers de les dues fonts anteriors.
  - **D→E:** encara no hi ha dades. Deixa el punt d'extensió preparat (el pla 074 hi afegirà `ce_acces.json`); sense el fitxer, cap aresta `de` i sense warning.
- Codi nou en un mòdul propi (p. ex. `backend/itinerary_graph.py`) amb funcions pures testejables; la ruta a `app.py` només valida i serialitza.

## TDD (obligatori)

Tests nous a `backend/tests/test_itinerari_complet.py`, amb fixtures petites en memòria o fitxers temporals (no les dades reals), seguint el patró de `tests/test_itinerari_contingut_api.py`:
1. C LOMLOE → retorna els seus B, els A de cada B i el D amb `shared/total`; el focus és correcte.
2. A LOE amb dos B pare → apareixen tots dos i els C de cadascun (molts-a-molts).
3. D → retorna els C que hi porten (relació inversa) i els seus descendents.
4. C LOE amb `ciclos_fp` resolt per `ficha_url`, i un altre no resolt → `warnings`.
5. `depth=1` retorna només veïns directes.
6. Paràmetres invàlids → 400; grau inexistent → 404.
7. `ficha` de D amb esquema no http(s) → `null`.

Executa: `cd backend && python3 -m pytest tests -q --ignore=tests/test_pipeline.py -p no:cacheprovider` (2 fallos coneguts a `test_db.py` de `schema_version`; la resta verd).

## Verificació manual

Amb dades locals, `ADG_C_001_3B` ha de donar 3 B (`ADG_B_3001`, `ADG_B_3002`, `ADG_B_3004`), 4 A cadascun i el D "Título Profesional Básico en Servicios Administrativos" (`shared 3/3`). Mida de la resposta per a un A LOE amb molts pares: ha de ser raonable (< ~200 KB); si no, documenta-ho.

## STOP conditions

- Si resoldre `ciclos_fp` → D deixa més d'un 20% de C LOE sense D, para i informa (amb comptes) abans de continuar.
- No canviïs el contracte de `/api/itinerari` existent.
