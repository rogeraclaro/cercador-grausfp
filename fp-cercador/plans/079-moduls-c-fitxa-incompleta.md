# Pla 079 — C LOMLOE: completar amb el BOE els mòduls que la fitxa de todofp omet

Origen: troballa de la fase 2b del pla 078 (`plans/outputs/audit_c_modulos_boe.md`,
secció "Fitxa todofp diferent de l'annex I del decret"). En 11 C, la fitxa de todofp
no coincideix amb l'annex I del seu decret. `c_modulos.json` copia la fitxa, i per
això l'app mostra menys mòduls dels que diu el BOE i el recompte C→D també en té
menys.
Depèn de: 078 DONE. Executable per un agent sense context. TDD estricte al backend.

## Diagnosi (verificada 2026-10-30 amb el text del BOE, no repetir)

Mòduls que són a l'annex I i NO a la fitxa (11 mòduls en 10 C). Cap té Grau B al
catàleg, comprovat a `ofertes.json`: tots portaran la nota de l'art. 58.3.

| C | Decret | Mòdul que falta (nom literal de l'annex I) |
|---|---|---|
| COM_C_001_4B | RD 212/2025 (BOE-A-2025-7193) | 1233 Aplicaciones informáticas para el comercio |
| COM_C_002_4B | RD 212/2025 | 1233 Aplicaciones informáticas para el comercio |
| COM_C_003_4B | RD 212/2025 | 1233 Aplicaciones informáticas para el comercio |
| COM_C_004_4B | RD 212/2025 | 1614 Ofimática aplicada al comercio alimentario |
| IMA_C_002_4B | RD 209/2025 (BOE-A-2025-6699) | 0310 Montaje y mantenimiento de instalaciones de agua |
| IMA_C_002_4B | RD 209/2025 | 0266 Configuración de instalaciones caloríficas |
| IMA_C_006_5B | RD 209/2025 | 0944 Simulación de sistemas mecatrónicos |
| IMP_C_003_4B | RD 209/2025 | 0640 Imagen corporal y hábitos saludables |
| IMP_C_009_5B | RD 209/2025 | 1268 Diseño gráfico aplicado |
| SSC_C_002_3B | RD 208/2025 (BOE-A-2025-7040) | 3146 Seguridad en el ámbito doméstico |
| SSC_C_012_5B | RD 208/2025 | 1117 Intervención con personas con dificultades de comunicación |

Cas invers (1 C): `IMA_C_001_4B` té a la fitxa el **0266** i l'annex I del RD 209/2025
no el té (té 0037, 0038, 0302, 1782). Decisió pendent del propietari (vegeu "Decisions").

## Decisions de disseny

- **Correcció a l'API, no al JSON.** `c_modulos.json` es regenera cada setmana des de
  todofp: si s'edités a mà, el refresc ho desfaria. La correcció és una constant
  `_C_MODULOS_BOE` a `backend/app.py`, al costat de `_C_MODULOS_NOTA_NEUTRA`.
  Format: `{codigo_c: [(num, name, rd, boe_id), ...]}`.
- **S'aplica dins `_get_c_modulos()`**, després de llegir el fitxer i abans de desar-lo
  a la memòria cau. Així la fitxa del grau (`/api/itinerari`) i el recompte C→D
  (`_get_c_lomloe_to_d`) reben les mateixes dades sense tocar `cd_lomloe.py`.
- **S'autoreparen.** Un mòdul s'afegeix només si el `num` encara no és a la fitxa. Si
  todofp corregeix la fitxa, la correcció deixa d'actuar sola.
- **Cada mòdul afegit es marca amb `font: {rd, url}`**
  (`url = https://www.boe.es/buscar/act.php?id=<boe_id>`). L'API l'envia a `modulos_c`
  i la UI hi afegeix una segona nota: "La fitxa del ministeri no inclou aquest mòdul;
  consta al {rd}." amb enllaç al BOE. Requisit del propietari: informació comprovable
  amb enllaç a la font.
- Ordre: el mòdul afegit va al final de la llista del C, darrere del que ja hi ha.

## Fase 1 — Backend (TDD) — FET 2026-10-30

Constants `_C_MODULOS_BOE_AFEGITS` i `_C_MODULOS_NO_AL_DECRET` a `app.py`, aplicades per
`_apply_c_modulos_boe()` dins `_get_c_modulos()`. Camp `font: {tipus: 'afegit'|'no_al_decret',
rd, url}` (null als mòduls normals). Si el C no té fitxa llegida, no s'hi afegeix res.
`/grau/<ref>` només llista mòduls de D: no cal tocar-lo. 4 tests nous; suite 527 verds.

Tests a `backend/tests/test_centres_inherit_api.py`, que ja té el fixture `C_MODULOS`
i aïlla `C_MODULOS_PATH`:
1. Un C de `_C_MODULOS_BOE` (monkeypatch de la constant) sense el mòdul a la fitxa:
   `modulos_c` el conté amb `b: null`, `nota: 'art583'` i `font: {rd, url}`.
2. El mateix C, ara amb el mòdul a la fitxa: surt una sola vegada, i sense `font`.
3. Els mòduls de la fitxa no porten `font` (o porten `font: null`; triar-ne un i fixar-lo).
4. `test_cd_lomloe` / `_get_c_lomloe_to_d`: un mòdul afegit que també és en una D
   compta com a compartit (cal fer-ho via `_get_c_modulos`, no via `cd_lomloe`).

Implementació: constant + fusió a `_get_c_modulos()` + `font` a la serialització de
`modulos_c`.

Comprovar també si `/grau/<ref>` (pla 077, `test_grau_page.py`) llista mòduls de C.
Si ho fa, ha de rebre el mateix canvi. Si no, no tocar-lo.

## Fase 2 — UI — FET 2026-10-30

Claus `modul_boe_afegit` / `modul_boe_no_al_decret` (text + enllaç amb el RD). `i18n.js?v=20261030b`.
Verificat en local: COM_C_001_4B (1233 amb les dues notes) i IMA_C_001_4B (0266 "no consta").


- `frontend/index.html`: dins la plantilla del pla 078 (`modulosCData`), si
  `mod.font`, una segona `span.modul-nota` amb el text i l'enllaç (`target="_blank"
  rel="noopener"`).
- `frontend/i18n.js`: claus CA/ES `index.itinerari.modul_boe_afegit` ("La fitxa del
  ministeri no inclou aquest mòdul; consta al {rd}." / "La ficha del ministerio no
  incluye este módulo; consta en el {rd}."). Bump de `i18n.js?v=`.
- Verificar al navegador `COM_C_001_4B` (6 mòduls; el 1233 amb les dues notes) i
  `IMA_C_002_4B` (6 mòduls).

## Fase 3 — Verificació amb les dades de producció

- Copiar `c_modulos.json` i `d_modulos.json` del VPS (o fer-ho allà amb el python del
  venv). Calcular el recompte C→D abans/després per als 10 C i anotar-lo aquí.
- Tornar a executar `scripts/audit_c_modulos_boe.py`: la taula "Fitxa todofp diferent"
  ha de continuar llistant els 11, perquè audita la fitxa i no l'API. És el detector
  de quan todofp ho arregli.

## Decisió del propietari (2026-10-30): mantenir-lo amb nota

- `IMA_C_001_4B` 0266 (a la fitxa i no al decret). Recomanació: mantenir-lo amb una
  nota "No consta a l'annex I del RD 209/2025" i enllaç. Treure'l contradiria la
  font oficial que l'usuari veu a todofp, i no tenim cap prova de quina de les dues
  és la bona (el text consolidat del BOE tampoc el té). Alternativa: treure'l, cosa que
  deixa l'app d'acord amb el BOE i en desacord amb todofp.

## Fora d'abast

- Avisar el ministeri de les fitxes errònies (ho pot fer el propietari; la taula de
  dalt n'és l'evidència).
- Els 32 C sense decret localitzat.

## Verificació final

- `pytest backend/tests` en verd (excepte `test_ce_acces_falla_conserva_fitxer_anterior`,
  que ja fallava abans del 078).
- Producció: `/api/itinerari?...COM_C_001_4B` retorna el 1233 amb `font`.
