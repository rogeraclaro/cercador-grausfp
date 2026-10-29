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
  - **NO verificat:** si `0413`, `0533`, `0277` i `1282` també són "no associats",
    o si és una mancança del catàleg del ministeri. Cal mirar-ho al decret de cada
    C abans de posar-los la mateixa nota.
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
   No s'ha d'afirmar "no associat" sense comprovar-ho. Si la Fase 1 no pot saber
   si un mòdul està associat, la nota es limita a dir que no hi ha Grau B al catàleg.
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

## Fase 3 — API + UI (TDD a l'API)

- `backend/tests/test_itinerari*.py`: per a un C amb `c_modulos` sintètic,
  `modulos_c` té 8 entrades, 2 amb `b: null`. Sense `c_modulos.json`, retorna `modulos_c == []`.
- `app.py`: getter `_get_c_modulos()` amb memòria cau per mtime (copiar
  `_get_bc_lomloe`). Constant `C_MODULOS_PATH`.
- `index.html`: `parentBLomloeData` passa a guardar `data.modulos_c` si no és buit;
  si ho és, `parent_b_lomloe` mapejat a `{num, name, b}`. La plantilla
  distingeix `bmod.b` (enllaç) de `!bmod.b` (text + `*`).
- Verificar al navegador `SSC_C_017_5B`: 8 mòduls, 1786 i 1782 sense enllaç.

## Fase 4 — C→D: recomptar amb tots els mòduls (DECISIÓ PENDENT)

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
