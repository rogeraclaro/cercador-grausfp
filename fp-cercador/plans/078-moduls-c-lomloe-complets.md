# Pla 078 — C LOMLOE: mostrar TOTS els mòduls del certificat (també els que no tenen Grau B)

Origen: informe del propietari (2026-10-29). `SSC_C_017_5B` (Habilitación para
la docencia…) té 8 mòduls al BOE i a la fitxa de todofp, però el cercador en
mostra 6: hi falten **1786 Competencia digital para la práctica docente** i
**1782 Prevención de riesgos laborales**.
Depèn de: 057 DONE (`bc_lomloe.json`), 058 DONE (`cd_lomloe.py`).
Executable per un agent sense context. TDD estricte al backend.

## Diagnosi (verificada 2026-10-29, no repetir)

- La llista "Módulos profesionales (grados B) de este certificado" surt de
  `parent_b_lomloe` (`/api/itinerari?grado=C`, `backend/app.py` ~1873), que llegeix
  `bc_lomloe.json` i, a més, filtra `if b in _b_by_code`.
- `bc_lomloe.json` el genera `backend/scrapers/bc_lomloe_scraper.py::build_bc_lomloe`.
  Llegeix bé **tots** els mòduls de la fitxa (`parse_modulos`), però només en desa
  els que existeixen com a registre Grau B `FAM_B_NNNN` al catàleg. La resta es
  descarten **a propòsit** ("Els mòduls sense B (transversals, ex. PRL) s'ignoren").
- La fitxa viva de `SSC_C_017_5B` sí que llista els 8 mòduls. Al catàleg
  (`ofertes.json` de producció) no hi ha cap `*_B_1786` ni `*_B_1782`, de cap família.
- **No és un cas aïllat.** En una mostra aleatòria de 15 C LOMLOE, **14 perden
  algun mòdul**:
  - PRL: `1782 Prevención de riesgos laborales` (11/15), `1724 … en construcción`,
    `1732 Nivel básico en prevención de riesgos profesionales`.
  - També mòduls de cicle que no tenen Grau B al catàleg del ministeri: `0413`
    (AGA_C_002_4B), `0533` (FME_C_008_5B), `0277` (TCP_C_002_5B), `1282` (AGA_C_009_5B).
    Cap d'ells existeix com a B amb cap prefix de família.
- **Efecte secundari a C→D (pla 058).** `cd_lomloe.py` calcula
  `total = len(bc_lomloe[c])`, és a dir, sense els mòduls que no tenen B. Per tant:
  - "Complet · n de m" diu `m` = 6 quan el certificat en té 8;
  - un mòdul de cicle sense B que sí és al D (p. ex. `0413`) no compta com a compartit.
- **Base legal: per què 1786 i 1782 no tenen Grau B** (verificat al BOE el 2026-10-29):
  - RD 86/2026 (BOE-A-2026-3210), que estableix `SSC_C_017_5B`:
    - l'art. 8 i l'annex III llisten 8 mòduls (510 h);
    - l'**annex I, "Oferta de Grado B"**, n'ofereix només 6 (`SSC_B_1705`…`SSC_B_1785`);
    - l'**annex VI A** associa cadascun d'aquests 6 a un estàndard ECP. 1786 i 1782
      no tenen cap ECP associat.
  - RD 659/2023, **art. 58.1**: el Grau B "siempre estará asociada a uno o varios
    estándares de competencia profesional". **Art. 58.3**: "No serán constitutivos de
    certificados de competencia los módulos no asociados al Catálogo de Estándares
    de Competencias Profesionales".
  - RD 659/2023, **art. 12.2**: els mòduls no associats a estàndars (digitalització,
    PRL, etc.) són "imprescindibles" per al títol. Formen part del Grau C, però
    no es poden cursar soltes com a Grau B.
  - **Mòduls de cicle verificats (2026-10-29): el cas és el mateix, no és una mancança
    del catàleg.** Per a cada C, l'annex II ("Oferta de Grado B") del seu decret no
    inclou el mòdul. Tampoc l'associa a cap unitat de competència l'annex V A del
    títol associat, que és on remet l'art. 34 del decret dels C:

    | C | Decret del C (annex II) | Mòdul sense B | Títol associat (annex V A) |
    |---|---|---|---|
    | AGA_C_002_4B Ganadería ecológica | RD 207/2025 (BOE-A-2025-6797): B = 0405, 0407, 0408, 0411 | 0413, 1782 | RD 1633/2009 (BOE-A-2009-18476): 0413 no hi és |
    | AGA_C_009_5B Sanidad animal y asistencia veterinaria | RD 207/2025: B = 1279, 1280, 1281 | 1282, 1782 | RD 1585/2012 (BOE-A-2013-155): 1282 no hi és |
    | FME_C_008_5B Programación de la producción en moldeo cerrado | RD 208/2025 (BOE-A-2025-7040): B = 0162, 0163, 0531 | 0533, 1782 | RD 882/2011 (BOE-A-2011-12723): 0533 només surt en una NOTA (es convalida si s'acrediten TOTES les UC del títol) |
    | TCP_C_002_5B Gestión en la industria de la confección | RD 211/2025 (BOE-A-2025-7096): B = 0165, 0276, 0278, 0280 | 0277 | RD 954/2008 (BOE-A-2008-10619): 0277 no hi és |

    Conclusió: als 5 decrets revisats, els mòduls que el catàleg no té com a Grau B
    són exactament els que el decret no ofereix com a Grau B. Cap d'ells està associat
    a un estàndard o unitat de competència concrets.
- Els `ficha_id` caduquen a cada refresc. Per resoldre l'id viu:
  `app._resolve_ficha_id(codigo)`.

## Decisions de disseny

1. **No es toca el format de `bc_lomloe.json`.** El fan servir `centres_inherit.py`,
   `itinerary_graph.py`, `centres_watch_service.py` i `cd_lomloe.py`, i per a ells
   la semàntica "C → B existents" és la correcta.
2. Fitxer nou: **`backend/data/c_modulos.json`** =
   `{codigo_c: [{"num": "1705", "name": "Programación didáctica …"}, …]}`, en
   l'ordre de la fitxa. Es genera a la **mateixa passada** que `bc_lomloe`
   (`build_bc_lomloe` ja té l'HTML a la mà): **zero peticions extra** a todofp.
3. API `/api/itinerari?grado=C` (C LOMLOE): es manté `parent_b_lomloe` (compatibilitat)
   i s'afegeix **`modulos_c`**: llista completa en ordre de fitxa amb
   `{num, name, b: <serialize del B> | null}`.
   Si `c_modulos.json` no existeix o no té el codi, `modulos_c` = `[]` i el frontend
   fa servir `parent_b_lomloe` com ara (fail-soft).
4. UI (`frontend/index.html`, bloc "Mòduls B LOMLOE"): es pinta `modulos_c` si
   n'hi ha. Els mòduls amb `b` es mostren com ara (enllaç a la fitxa B).
   Els que no en tenen surten **com a text sense enllaç**, amb el número, i amb
   la nota final `index.itinerari.modul_sense_b`:
   "Mòdul no associat a cap estàndard de competència: forma part del certificat,
   però no es pot cursar sol com a Grau B (RD 659/2023, art. 58.3)."
   **Aprovat pel propietari (2026-10-29).** "RD 659/2023, art. 58.3" ha de ser un
   enllaç (`target="_blank" rel="noopener"`) a la font:
   `https://www.boe.es/buscar/act.php?id=BOE-A-2023-16889#a5-10` (bloc de l'art. 58 al
   text consolidat). En castellà: "Módulo no asociado a ningún estándar de competencia:
   forma parte del certificado, pero no puede cursarse por separado como Grado B
   (RD 659/2023, art. 58.3)."
   Aquesta redacció està verificada en 5 de 5 decrets (vegeu la Diagnosi). Com a
   salvaguarda, es mostra només per als mòduls que surten a la fitxa del C i que
   no tenen B al catàleg.
   Títol nou de la secció: "Mòduls professionals d'aquest certificat:"
   (CA/ES a `i18n.js`). Cal pujar el `?v=` de `i18n.js`.
5. C→D (`cd_lomloe.py`): **decisió pendent del propietari, vegeu la Fase 4.**
   Les fases 1–3 no hi depenen i es poden desplegar soles.

## Fase 1 — Scraper (TDD)

Tests a `backend/tests/test_bc_lomloe_scraper.py`:
- `build_bc_lomloe` (o una funció germana `build_bc_lomloe_and_modulos`) retorna,
  per a una fitxa de fixture amb 8 mòduls (2 sense B), `bc_lomloe[c]` amb 6 B i
  `c_modulos[c]` amb els 8 `{num, name}` en ordre.
- Una fitxa amb codi diferent (id obsolet) no apareix a cap dels dos.
- `write_c_modulos` és atòmic, igual que `write_bc_lomloe`.

Implementació: el bucle de `build_bc_lomloe` ja té `parse_modulos(html)`, així
que n'hi ha prou de desar-ho. Signatura recomanada: `build_bc_lomloe(...)` retorna
`(bc, modulos)`, i s'actualitzen tots els callers i tests existents.
Fixture: copiar l'estructura HTML real de la fitxa (`Módulos Profesionales` … `Nota:`).

## Fase 2 — Pipeline + generació puntual

- `scrapers/pipeline.py` (~358): escriure `c_modulos.json` al costat de
  `bc_lomloe.json`, dins el mateix `try` no fatal.
- Script puntual `backend/scripts/build_c_modulos.py` per generar-lo **ara**,
  sense esperar el refresc de diumenge. Resol l'id viu de cada C amb
  `_resolve_ficha_id` (~400 fitxes, 1 req/s, ~15 min) i reescriu també
  `bc_lomloe.json` perquè quedin coherents.
  **No executar-lo al VPS diumenge de 11:10 a 11:45** (refresc programat).

## Fase 2b — Auditoria de TOTS els C LOMLOE contra el BOE (abans de desplegar la UI)

Objectiu: comprovar, per a cadascun dels ~400 C LOMLOE, que els mòduls sense Grau B
al catàleg són exactament els que el seu decret no inclou a l'"Oferta de Grado B".
Així la nota de la UI no és una extrapolació de 5 casos.

- Script `backend/scripts/audit_c_modulos_boe.py`, d'un sol ús i fora del refresc:
  1. Llista de decrets: els RD de famílies de 2025 (207/2025, 208/2025, 211/2025 i
     germans: buscar "por el que se regulan aspectos específicos de los grados A, B y C")
     més els RD d'un sol certificat (p. ex. 86/2026). Es descarrega el text de
     `https://www.boe.es/diario_boe/txt.php?id=<BOE-A-…>`.
  2. Per a cada decret, parsejar: la llista "7. Módulos profesionales" de cada C
     (annex I) i els `FAM_B_NNNN` de l'annex II ("Oferta de Grado B"). En decrets d'un
     sol certificat, la secció és l'annex I. Normalitzar espais (`\s+`): el BOE fa
     servir em-space U+2003 entre "i)" i el codi.
  3. Creuar amb `c_modulos.json` i amb el catàleg B. Informe a
     `plans/outputs/audit_c_modulos_boe.md` amb quatre comptadors: OK; el decret ofereix B
     però el catàleg no el té (forat del catàleg); el catàleg té B que el decret no
     ofereix; C sense decret trobat.
- Criteri: si hi ha forats del catàleg, aquells mòduls NO porten la nota de l'art. 58.3.
  Porten una variant neutra ("No consta com a Grau B al catàleg del ministeri") i es
  reporten al propietari.
- Els C sense decret localitzat es llisten a part, per revisar-los a mà. No bloquegen.

### Resultat de la fase 2b (2026-10-30)

`scripts/audit_c_modulos_boe.py` (a `scripts/`, no a `backend/scripts/`) → `plans/outputs/audit_c_modulos_boe.md`.
Decrets: RD 207–213/2025 (18-3-2025, un per grup de famílies) i RD 86/2026. Cobreixen 368+1 dels 400 C.

- Per certificat: 331 OK; 1 forat real del catàleg (HOT_C_003_5B → HOT_B_0178, al decret i no al catàleg);
  35 "catàleg de més" (el catàleg enllaça un B de la mateixa família que el decret no ofereix per a aquell C; inofensiu).
- Per mòdul sense B al catàleg (514): 467 cap decret l'ofereix com a B (nota art. 58.3); 1 forat (0178, nota neutra);
  13 només són B d'una altra família (0156, 0179, 0165, 0538, 0020, 0017, 0116, 0790); 33 de C sense decret
  localitzat (32 són PRL 1782/1732/1724; 1 és el 1800).
- Troballa a part: 11 C on la fitxa todofp omet mòduls que el decret (també el text consolidat) sí que té
  (p. ex. COM_C_001_4B sense 1233; IMA_C_002_4B sense 0310 i 0266). L'app hereta l'error de la fitxa.

## Fase 3 — API + UI (TDD a l'API)

- `backend/tests/test_itinerari*.py`: per a un C amb `c_modulos` sintètic,
  `modulos_c` té 8 entrades, 2 amb `b: null`. Sense `c_modulos.json`, retorna `modulos_c == []`.
- `app.py`: getter `_get_c_modulos()` amb memòria cau per mtime (copiar
  `_get_bc_lomloe`). Constant `C_MODULOS_PATH`.
- `index.html`: `parentBLomloeData` passa a guardar `data.modulos_c` si no és buit;
  si ho és, `parent_b_lomloe` mapejat a `{num, name, b}`. La plantilla
  distingeix `bmod.b` (enllaç) de `!bmod.b` (text + `*`).
- Verificar al navegador `SSC_C_017_5B`: 8 mòduls, 1786 i 1782 sense enllaç.

## Fase 4 — C→D: recomptar amb tots els mòduls — DECIDIT: opció A (propietari, 2026-10-29)

Especificació (TDD a `backend/tests/test_cd_lomloe.py`):
- `build_c_lomloe_to_d(records, c_modulos, d_modulos)` passa a rebre `c_modulos` (no
  `bc_lomloe`). Si no hi ha `c_modulos` per a un C, fa servir `bc_lomloe` com ara (fail-soft).
- Mòduls del C: `c_modulos[c]` **menys els de PRL**. Un mòdul és PRL si i només si
  **no té Grau B al catàleg** i el seu número és `1782`, `1724` o `1732`, o el nom conté
  "riesgos laborales" o "riesgos profesionales".
  ⚠ La condició "sense B" és obligatòria. `0165 Gestión de la calidad, prevención de
  riesgos laborales y protección ambiental` (TCP_C_002_5B) té Grau B i NO s'ha d'excloure.
- `total` = mòduls del C després d'excloure els de PRL.
- `shared` = mòduls del C presents al D de la mateixa família (es manté la restricció
  del 058). Coincidència pel número (`num` del D), o pel nom normalitzat
  (`normalize_module_name`) si el mòdul del D no porta número.
- Tests mínims: SSC_C_017_5B → total 7 (8 − 1782); un C amb 0413 sense B que és al D
  compta com a compartit; TCP_C_002_5B → 0165 compta al total; sense `c_modulos` →
  mateix resultat que abans.
- Desplegament: cal reiniciar el backend (canvi a Python). **No fer-ho diumenge de
  11:10 a 11:45.**

Opcions que es van valorar (per a l'històric):

Problema: avui `total` exclou els mòduls sense B. Opcions:
- **A (recomanada):** el matching C↔D passa a fer-se per número de mòdul
  (`c_modulos` vs `d_modulos`, per número o per nom normalitzat), i `total` = mòduls
  del C **excepte els de PRL** (`1782`, `1724`, `1732`, i els que tinguin
  "riesgos laborales/profesionales" al nom). PRL no és mai a cap D: si comptés,
  gairebé cap C no seria "Complet", i el certificat sí que convalida la resta de mòduls del D.
  Com a efecte, guanya els mòduls de cicle sense B (`0413`…) que sí són al D.
- **B:** `total` = tots els mòduls. És més literal, però "Complet" desapareix
  de quasi tots els C.
- **C:** no tocar el pla 058. La UI de mòduls queda bé, però "n de m" segueix
  sense comptar els mòduls sense B.

## Fora d'abast

- La pàgina pública `/grau/<ref>` no mostra mòduls per als C (només per als D).
  Es podria afegir amb `c_modulos` en un pla posterior.
- Que el ministeri no publiqui Grau B per a `0413`, `0533`… és una mancança de la
  font: no s'inventen registres B.

## Verificació final

- `pytest backend/tests -q --ignore=backend/tests/scrapers --ignore=backend/tests/test_pipeline.py`
  ha de passar en verd.
- Producció: el detall de `SSC_C_017_5B` mostra 8 mòduls; `IFC_C_003_3B` mostra el
  mòdul PRL; `AGA_C_002_4B` mostra `0413` sense enllaç.
