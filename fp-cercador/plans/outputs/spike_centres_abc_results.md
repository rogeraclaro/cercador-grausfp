# Spike — Centres per a graus A, B i C (pla nou)

Data: 2026-09-06. Investigació pura, sense tocar codi de producció.
Prompt origen: `plans/outputs/prompt_investigacio_centres_abc.md`.

## Taula de viabilitat

| Font | Cobertura (A/B/C-nou) | Format resposta | Esforç d'integració | Veredicte |
|---|---|---|---|---|
| `registrosfp.educacion.gob.es/.../datosTablaPublico?ofertaCodigo={codi}` | **C-nou: SÍ** (mateix endpoint, mateix format de fila). A: no. B: no. | JSON DataTables idèntic al de C LOE/D/E (`data: [[codigo, codigoMinisterio, nombre, …, letrasgrado]]`) | **Molt baix** — un bloc més a `centres_scraper.py`, ~400 consultes a 1 req/s (~7 min) | ✅ **VIABLE per a C-nou** |
| Mateix endpoint amb `gradoProfesional=1/2` o `ofertaCodigo` A/B | Cap. El `<select name="gradoProfesional">` només ofereix `3=Grado C`, `4=Grado D`, `5=Grado E`. Codis `ADG_B_3001`, `ADG_A_3001_01`, `UF0038` → 0 files. | — | — | ❌ No cobreix A ni B |
| SEPE — `sede.sepe.gob.es/FOET_BuscadorDeCentros_SEDE/flows/buscadorReef` | Només **especialitats formatives SEPE** (`ADGG0408`, `ADGD0001`…). Inclou els C LOE (que ja tenim). **Zero** codis `MF*`, `UF*` ni LOMLOE (`FAM_X_NNN`). | HTML JSF/Spring Web Flow: 3 POST AJAX encadenats (família → àrea → especialitat) amb `javax.faces.ViewState` + `execution=e1sN`, darrere F5. Scriptable però fràgil. | Alt (sessió amb estat, sense API) i **sense benefici**: no aporta cap oferta nova | ❌ Descartat |
| BOE / Reials Decrets | Contingut formatiu, no centres | PDF/HTML | — | ❌ No aplica |
| **Derivació local A→B→C** (`backend/itinerary.py` + `bc_loe.json`) | A i B **per herència del C pare**: A LOE i B LOE via `MF####_N` → `UC####_N` → C LOE (ja implementat a `/api/itinerari`). A LOMLOE → B LOMLOE ja existeix; **B LOMLOE → C LOMLOE encara no** (és exactament l'abast del spike `plans/043-spike-c-lomloe-d-i-b-c-loe.md`, mai executat). | Sense xarxa | Baix (LOE) / Mitjà (LOMLOE, depèn del spike 043) | ✅ **Única via realista per a A i B** |

## Detall de proves fetes

Totes les crides amb bootstrap previ `GET /buscarPublico` (cookie `JSESSIONID`) i `Referer`, com fa el scraper actual.

### 1. Registre Estatal (Ministeri d'Educació)

Inspecció del formulari `buscarPublico` (39 KB): camps rellevants
`ofertaCodigo`, `ofertaDenominacion`, `gradoProfesional` (opcions: `3` Grado C, `4` Grado D, `5` Grado E — **no hi ha 1 ni 2**), `tipoCentroUnificado` (`3` = "Centros de oferta … exclusiva de grados A, B y/o C"), `especialidad.familia.codigo`, `especialidad.nivel.id`.

| Crida (`datosTablaPublico?…&iDisplayLength=10000&iDisplayStart=0&draw=1`) | Resultat |
|---|---|
| `ofertaCodigo=ADGG0408` (control, C LOE) | 4 219 centres |
| `ofertaCodigo=ADG_C_001_3B` (C LOMLOE) | **35 centres** — fila ex.: `["2800000577","M280006203G","TAJAMAR","Madrid","28038","MADRID","","MADRID","Calle Pio Felipe 12","914783498","jaruiz@tajamar.es","0","C"]` — mateix format de 13 columnes que parseja `_parse_centre` |
| `ofertaCodigo=ZZZ_C_999_9X` (codi fals) | 0 → la cerca és exacta, no hi ha fals positiu |
| `ofertaCodigo=ADG_C` (prefix) | 66 → el filtre és `LIKE`; cal passar sempre el codi complet |
| `ofertaDenominacion=Actividades de grabación…` (C LOMLOE per denominació) | 0 — per C-nou cal usar `ofertaCodigo`, no la denominació |
| `ofertaCodigo=ADG_B_3001` (B LOMLOE) | 0 |
| `ofertaCodigo=ADG_A_3001_01` (A LOMLOE) | 0 |
| `ofertaCodigo=UF0038` (A LOE) | 0 |
| `gradoProfesional=1`, `=2`, `=6`, `=7` sols | 0 |
| `gradoProfesional=3` sol | 10 000 (cap de pàgina; = sense filtre) |
| `tipoCentroUnificado=3` sol | 10 000; `letrasgrado` sempre `"C"` — la columna 13 no distingeix A/B, no serveix per inferir-los |

Mostra aleatòria de 25 codis C LOMLOE (seed 1), 1 req/s:

```
AGA_C_002_4B 0 | HOT_C_001_5B 1  | TCP_C_007_5B 1 | IFC_C_003_3B 19 | IFC_C_001_4B 33
ADG_C_003_4B 43| COM_C_013_5B 31 | TCP_C_005_5B 0 | ARG_C_001_5B 1  | COM_C_001_5B 38
IMS_C_002_5B 13| TCP_C_004_4B 0  | EOC_C_009_4B 1 | TCP_C_002_3B 0  | COM_C_009_5B 0
ARG_C_002_3B 3 | TMV_C_001_4B 3  | AGA_C_001_5B 0 | IFC_C_005_5B 40 | TCP_C_006_5B 0
TCP_C_008_5B 1 | ADG_C_002_3B 43 | QUI_C_005_5B 0 | AGA_C_008_5B 0  | IMA_C_004_4B 3
→ 16/25 amb centres (64 %). Els 0 són ofertes noves sense centre acreditat encara, no error.
```

Distribució dels 397 codis C-nou per sufix (nivell): `5B`=181, `4B`=158, `3B`=58.

### 2. SEPE

- URLs antigues (`RXBuscadorEFRED/BusquedaEspecialidades.do`, `InicioBusquedaCentrosPorOcupacion.do`, `BusquedaEspecPorOcupacion.do`) → **404**.
- `RXBuscadorEFRED/EntradaBuscadorCentros.do` → redirigeix a `FOET_BuscadorDeCentros_SEDE/flows/buscadorReef?execution=e1s1`.
- Flux verificat amb curl: `POST` AJAX (`Faces-Request: partial/ajax`, `javax.faces.source=formulario:j_id_1d:1:j_id_1f`) → `<redirect url="…execution=e1s2">` → `GET e1s2` (224 KB) amb `<select name="formulario:comboEspecialidad">` de **1 231 opcions** per a Administración y Gestión.
- Prefixos d'aquestes 1 231 especialitats: `ADGD` 664, `ADGN` 220, `ADGG` 185, `ADGC` 50, `ADGA` 36, … Conté `ADGG0408` (C LOE). **0** codis `MF*`, **0** `UF*`, **0** amb `_` (LOMLOE).
- Conclusió: el SEPE registra acreditació per *certificat/especialitat*, no per mòdul ni unitat; i no coneix el catàleg LOMLOE. No aporta res que no tinguem.

### 3. Estat de la derivació local (per a A i B)

- `backend/itinerary.py`: A→B ja resolt per als dos plans (`FAM_A_NNNN_PP → FAM_B_NNNN`; `UF#### → MF####_N`).
- `backend/app.py` `/api/itinerari`: B LOE → C LOE via `bc_loe.json` (`MF####_N → UC####_N → codi C`). **`bc_loe.json` no existeix a `backend/data/` en local** — només hi ha el generador `scripts/generate_bc_loe.py`; cal confirmar-ne l'estat al VPS abans de dependre'n.
- B LOMLOE → C LOMLOE: **no existeix**. Els codis no es deriven per patró (`ADG_B_3001` vs `ADG_C_001_3B`); cal la fitxa todofp del C (spike 043).

## Recomanació

### Fase 1 — C LOMLOE (barat, fer-ho ja)

Ampliar `backend/scrapers/centres_scraper.py` amb un quart bloc idèntic al de C LOE:

- `_load_ofertes()`: afegir `c_lomloe = [r for r in all if r['grado']=='C' and not r['plan_antiguo']]`.
- Consulta: `params={'ofertaCodigo': r['codigo'], 'iDisplayLength': PAGE_SIZE, 'iDisplayStart': 0, 'draw': 1}` — **exactament** com C LOE; el `_parse_centre` existent ja serveix.
- Clau a `oferta_centres.json`: el `codigo` (`ADG_C_001_3B`), coherent amb C LOE que usa el codi SEPE. Comprovar que `app.py` resol la clau per C amb `plan_antiguo=False` igual que per C LOE (avui probablement filtra per `plan_antiguo`).
- Cost: +397 consultes → ~7 min més de scraping; ~64 % retornaran centres.
- Actualitzar docstring del mòdul i `.planning/quick/20260614-centres-scraper/SUMMARY.md`.

### Fase 2 — A i B per herència del C pare (no hi ha font directa)

Cap registre públic acredita centres per a graus A o B: a l'ordenació LOMLOE (RD 659/2023) el centre s'acredita per al certificat C i, per definició, pot impartir els seus mòduls (B) i unitats (A). Per tant:

- A la UI, mostrar per a una oferta A/B els centres del(s) C que la contenen, etiquetats com a "centres del certificat X que inclou aquest mòdul" (no com a acreditació directa).
- LOE: ja hi ha tota la cadena (`A → B → UC → C`). Només cal encadenar `bc_loe.json` + `oferta_centres.json` al servei/endpoint de centres. Confirmar primer que `bc_loe.json` està generat al VPS.
- LOMLOE: bloquejat fins a tenir B→C. **Executar el spike 043** (`plans/043-spike-c-lomloe-d-i-b-c-loe.md`) — és el prerequisit real.

### Descartat

- SEPE: ja no cal tornar-hi. Esforç alt (JSF amb estat, F5) i cobertura ⊂ del que tenim.
- BOE: no dona centres.
