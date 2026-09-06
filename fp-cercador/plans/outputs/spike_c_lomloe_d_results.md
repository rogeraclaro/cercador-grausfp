# Spike — C LOMLOE → D (cicles formatius) via mòduls compartits

Executat: 2026-09-06
Executor: Claude (sessió fp-cercador)
Commit base: 2df796a
Tanca la pregunta original del pla 043 ("C LOMLOE→D"), pendent des del 2026-06-19.

## Taula de viabilitat

| Relació | Font | Cobertura | Esforç | Risc | Veredicte |
|---|---|---|---|---|---|
| C LOMLOE → D | Fitxa D a todofp (`ficha_url`, 195/195 disponibles) → secció **"Plan de formación"** (`<h2>` + `<ul><li>`) → noms de mòduls → B LOMLOE per nom normalitzat (o per codi `NNNN.` quan hi és) → C LOMLOE via `bc_lomloe.json` | **381/400 C** amb ≥1 D de la mateixa família; **355/400** amb un D que conté el 100 % dels seus mòduls | S (195 GET + índex JSON; reutilitza `bc_lomloe.json`) | LOW | ✅ **VIABLE** |
| D → C LOMLOE (invers) | Mateix índex invertit | 157/195 D amb ≥1 C (f ≥ 0,5) | — | LOW | ✅ gratis |
| Centres per a D via `educacion.gob.es` | La fitxa D enllaça `buscarCentros?ensenanzaFP=NNN_NNNN` (182/195) | — | no investigat | — | ⏸ Pista per a un altre spike (avui D ja té centres via registre) |

## Mecanisme

Un C LOMLOE és un conjunt de mòduls professionals (B). Un cicle D també és un
conjunt de mòduls. La fitxa D llista els seus mòduls a "Plan de formación":

```
<h2>Plan de formación</h2> … <ul>
  <li>Estructura del mercado turístico.</li>          → HOT_B_0171 (per nom)
  <li>Protocolo y relaciones públicas.</li>            → HOT_B_0172
  <li>0179. Inglés Profesional (Grado Superior)</li>   → HOT_B_0179 (per codi)
  <li>1709. Itinerario personal para la empleabilidad I</li>  → transversal, sense B
  …
```

Match D→B: **codi `NNNN.`** si el `<li>` en porta (153 casos), si no **nom
normalitzat** (NFD sense accents, minúscules, sense "(Grado Superior/Medio)",
només `[a-z0-9 ]`) contra les denominacions dels B LOMLOE (1.159 casos).
Match C→D: comparteixen ≥1 B; **fracció** = B compartits / B del C.

## Resultats

- 195/195 fitxes D descarregades (0 errors, ~1 s cadascuna, ~4 min). Totes
  tenen la secció "Plan de formación".
- 3.206 mòduls llistats als D: 1.312 (41 %) resolen a un B LOMLOE. Els 1.894
  restants són transversals o no-B: "Itinerario personal para la
  empleabilidad" (345), "fase de formación en empresa" (184), "Digitalización
  aplicada" (156), "Sostenibilidad aplicada" (156), "Módulo optativo" (152),
  àmbits de FP Bàsica (Comunicación, Ciencias Aplicadas), "Proyecto
  intermodular". **Cap fals positiu detectat** a la mostra.
- 190/195 D tenen ≥1 B.

### C LOMLOE → D (mateixa família)

| Llindar de fracció | C amb ≥1 D | Parelles C–D | D per C |
|---|---|---|---|
| > 0 | 381/400 | 789 | 2,1 |
| ≥ 0,5 | 377/400 | 553 | 1,5 |
| ≥ 0,75 | 366/400 | 409 | 1,1 |
| = 1 (D conté tot el C) | **355/400** | 374 | 1,1 |

Coherència de nivell (parelles f ≥ 0,5): `3B`→FP Bàsica 76, `4B`→Grau Mitjà
207, `5B`→Grau Superior 266; només 4 parelles creuen nivell. Sense
restringir família surten 4.514 parelles (mòduls transversals com Inglés
0179 apareixen a moltes famílies) → **restringir a la mateixa família és
imprescindible**.

Exemples:
- `HOT_C_005_5B` (5 B) → T.S. Agencias de Viajes y Gestión de Eventos (5/5),
  Gestión de Alojamientos (4/5), Guía, Información y Asistencia (4/5).
- `ADG_C_001_3B` (3 B) → T.P. Básico en Servicios Administrativos (3/3).
- `IFC_C_005_5B` (3 B) → T.S. DAM (3/3), T.S. DAW (2/3).

Comparació amb la relació C LOE→D existent (`ciclos_fp.json`, via endpoint
`ciclosFP` de todofp): 1.343 cicles per a 588 C = 2,3 D per C. La nostra
derivació dona 2,1 (f > 0) — mateixa magnitud, cosa que confirma que
`ciclosFP` fa exactament aquest creuament per mòduls al servidor.

### Artefactes (no producció)

- `plans/outputs/spike_d_plans.json`: per a cada D (`str(id)`),
  `{denominacion, familia, nivel, modulos: [{num, name}], ensenanzaFP}`.
  Serveix de fixture de tests. Bonus: `ensenanzaFP` és el codi que
  `educacion.gob.es/centros/buscarCentros` usa per a "centres que imparteixen
  aquest cicle".

## Recomanació per a implementació (pla suggerit 058)

1. **Scraper `backend/scrapers/cd_lomloe_scraper.py`** → `backend/data/d_modulos.json`
   `{str(id_D): {"modulos": [{"num": "0179"|null, "name": "…"}], "ensenanzaFP": "…"}}`.
   195 GET a `ficha_url` (existeix per a tots els D), parse `<h2>Plan de
   formación` → primer `<ul>` → `<li>`; regex `^(\d{4})\.\s*(.+)$`. Reintent
   amb backoff com `bc_lomloe_scraper`. Enganxar-lo a `pipeline.run()` després
   de `bc_lomloe.json` (mateix patró no-fatal). +~4 min al refresc.
   Guardar **mòduls crus**, no la relació: així la relació es pot recalcular
   en memòria quan canviï `bc_lomloe.json` o les denominacions dels B.
2. **Derivació pura `backend/cd_lomloe.py`**: `build_c_lomloe_to_d(records,
   bc_lomloe, d_modulos) -> {codigo_c: [{"id": id_d, "shared": n, "total": m}]}`
   amb la normalització de noms d'aquest spike, **mateixa família** i
   ordenat per fracció desc. Exposar fracció a la UI ("cobreix 4 de 5
   mòduls"). Sense llindar dur al backend; el frontend pot amagar f < 0,5.
   TDD amb la fixture.
3. **`/api/itinerari?grado=C`** LOMLOE: omplir `ciclos_d` (avui buit per a
   C nou) amb `[{denominacion, familia, ficha_url, shared, total}]` — mateix
   contracte que C LOE més els dos camps nous. `grado=D` (nou o ampliació):
   `parent_c_lomloe`.
4. **UI**: el botó "Cicles D" viu al panell de detall de C LOE; per a C
   LOMLOE cal el panell de detall que ja estava pendent (mostrar
   `parent_b_lomloe` + `ciclos_d`). Mateix pla o el següent.

Esforç total S–M. Cap font nova de xarxa a part de les fitxes D, que ja
tenim enllaçades.

## Fora d'abast

- Centres per a D via `ensenanzaFP` (D ja té centres pel registre estatal).
- C LOE → D segueix via `ciclosFP` (no tocar).
