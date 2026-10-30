# Pla 080 — Auditar contra el BOE els 32 C LOMLOE sense decret localitzat

Origen: fase 2b del pla 078 (`plans/outputs/audit_c_modulos_boe.md`, secció "Sense
decret localitzat"). L'auditoria només coneixia els RD 207–213/2025 i el RD 86/2026, i
32 C hi quedaven fora. Dels seus mòduls sense B, l'app en mostra 32 de PRL amb la nota
de l'art. 58.3, i un (ARG_C_008_5B 1800) amb nota neutra, **sense haver-ho contrastat
amb cap decret**.
Depèn de: 078 i 079 DONE. Executable per un agent sense context.

## Diagnosi (verificada 2026-10-30, no repetir)

- Els 32 C tenen mòduls amb números nous (1686–1800). **Cadascun el crea un RD
  propi d'un sol certificat**, posterior al març de 2025. Exemples:
  - RD 1126–1131/2025, d'11-12-2025 (BOE 16-12-2025, BOE-A-2025-25699…25704): Construcción en piedra seca, Ecoturismo, Enoturismo, Instalaciones de suministro y evacuación de aguas, Instalaciones de protección contra incendios i Mecanizado de piezas de madera.
  - RD 3/2026, de 8-1-2026 (BOE-A-2026-676): QUI_C_006_4B, Operaciones de fabricación de pirotecnia.
- **Descoberta automàtica viable.** L'API del sumari diari del BOE respon amb
  `Accept: application/json`: `https://www.boe.es/datosabiertos/api/boe/sumario/AAAAMMDD`.
  Els títols són del tipus "Real Decreto N/AAAA, … por el que se establece el Certificado
  profesional en <denominación>, de la familia …". Comprovat amb el 20251216, que en retorna 6.
- **Estructura d'un RD individual** (comprovada a BOE-A-2025-25701, Enoturismo):
  - Article "Módulos profesionales": "Dichos módulos son los que a continuación se relacionan: a) 1737. Experiencias enoturísticas. b) …", fins a "Este certificado profesional incorpora…".
  - "ANEXO I Oferta de grado B: Certificados de competencia": hi surten els `FAM_B_NNNN` fins a "ANEXO II".
  - El primer "Código:" és el del C.
  - L'estructura és diferent de la dels RD 207–213 (annex I = perfil de cada C, annex II = oferta de B). Per això cal un parser propi.
- Mostra: per a HOT_C_015_5B, el catàleg i el decret coincideixen. L'annex I ofereix HOT_B_0020, 0179, 1232, 1737 i 1738, i tots són al catàleg i a `bc_lomloe`.

## Fase 1 — Descoberta dels RD (script)

Afegir a `scripts/audit_c_modulos_boe.py` l'opció `--discover`:
- Recorre els sumaris del 2025-03-19 fins avui, a 1 req/s (~590 dies, ~10 min), amb el
  mateix `--cache`.
- Desa a `plans/outputs/boe_certificados_individuales.json` els títols que contenen
  "por el que se establece el Certificado profesional": `{boe_id: {rd, data, titol}}`.
- Hi afegeix també els títols "se modifica" i "corrección de errores" que mencionen un
  certificat professional. Es llisten a part, perquè poden canviar mòduls.
- Fa l'aparellament C ↔ RD per denominació normalitzada (minúscules, sense accents ni
  puntuació) i en confirma cada cas amb el "Código:" del text del RD. Si una
  denominació no aparella, es llista per revisar-la a mà; no s'endevina.

### Resultat de la fase 1 (2026-10-30)

`python3 scripts/audit_c_modulos_boe.py --discover --cache DIR --data DIR` → `plans/outputs/boe_certificados_individuales.json`.
Desviacions respecte al pla, totes verificades amb el text del BOE:
- Eren **31**, no 32: `IMP_C_006_4B` sí que és en un decret de grup (abans el parser no el llegia).
- **No tots són RD individuals.** 11 C surten de **RD de títol** (Grau D) que també fixen Graus C:
  - SEA_C_001…006_4B → RD 1157/2024 (BOE-A-2024-24102, Técnico en Sanidad ambiental aplicada);
  - SSC_C_001/002_4B → RD 533/2025 (BOE-A-2025-14086, Técnico en Servicios funerarios);
  - ART_C_001…003_5B → RD 300/2026 (BOE-A-2026-8022).
  Per això la descoberta comença el 2023-07-19 (RD 659/2023) i també capta "ofertas de grados C, B y A".
- **Codis amb marcadors.** El BOE publica alguns codis amb marcadors (`EOC_C_00X_4B`, `IMA_C_0XX_4B`,
  `IMA_C_XXXX_4B`, `ENA_`). Aquests 4 C (ENA_C_003_4B, EOC_C_012_4B, IMA_C_008/009_4B) es confirmen
  perquè tots els mòduls de la fitxa (sense PRL) apareixen al RD. Els altres 27 es confirmen pel codi.
- **31/31 aparellats i confirmats**; cap sense RD.
- **Modificacions posteriors que la fase 3 HA de tenir en compte:**
  - RD 488/2026 (BOE-A-2026-13294) modifica el RD 300/2026 (ART_C_001…003_5B).
  - RD 489/2026 (BOE-A-2026-13295) modifica el RD 404/2025 (EOC_C_011_4B).
  - RD 490/2026 (BOE-A-2026-13296) modifica el RD 1127/2025 (HOT_C_016_5B).
  - Corrección de errores del RD 1157/2024 (BOE-A-2025-10206) (SEA).
  Millor que això: fer servir el **text consolidat** del BOE (`act.php?id=…`), si n'hi ha, en lloc del text original.

## Fase 2 — Parser del RD individual (TDD)

Cal cobrir tres formats: RD individual, RD de títol (els Graus C hi tenen el seu propi bloc) i
el text consolidat. Abans d'escriure el parser, mirar l'estructura del RD 1157/2024 i del RD 300/2026.

- `parse_rd_individual(text) -> (codigo, [num_modul], [codigo_b])`, amb els talls
  de la diagnosi.
- Tests amb fragments reals copiats del BOE-A-2025-25701 (Enoturismo) i del
  BOE-A-2026-676 (Pirotecnia) a `backend/tests/` (o a `scripts/tests/` si l'script ja en
  té). Cal cobrir els números enganxats ("3051.Operaciones"), com ja passava al 078.

### Resultat de la fase 2 (2026-10-30)

`parse_rd(text, codigo, denominacion, tipus)` a `scripts/audit_c_modulos_boe.py`; 8 tests nous a
`backend/tests/test_audit_c_modulos_boe.py`, amb fragments reals.
- **RD individual:** mòduls de "Dichos módulos son los que a continuación se relacionan:"; oferta de B
  d'"ANEXO I Oferta (de) grado B" fins a "ANEXO II". Cal l'annex, perquè l'articulat també en parla i
  el RD 488/2026 hi modifica el RD 300/2026.
- **RD de títol:** els mòduls, amb el lector dels decrets de grup (`parse_modulos_annex_i`, que ara també
  acaba el bloc a "Certificado profesional:" en minúscules). L'oferta de B surt del bloc "Certificados de
  competencia incluidos en el Certificado profesional <nom>[:.]", buscat pel nom normalitzat.
- **Modificacions posteriors:** no toquen ni la llista de mòduls ni l'oferta de B, així que n'hi ha prou
  amb el text original (fitxa d'anàlisi `act.php`, "Referencias posteriores"):
  - RD 489/2026 → annex V (professorat) del RD 404/2025;
  - RD 488/2026 → annex VIII (Grau A) del RD 300/2026;
  - RD 490/2026 → durada i hores de l'annex III del RD 1127/2025 (mateixa llista de mòduls).
  La correcció d'errors del RD 1157/2024 afegeix a l'annex IV A/B la correspondència
  **UC2519_2 ↔ 1732 Nivel básico de PRL** (vegeu la fase 3).
- **Sense regressions:** l'auditoria dels decrets de grup surt idèntica (`audit_c_modulos_boe.md` sense diff).
- **Prova amb els 31 C i les dades de producció:** 30/31 coincideixen del tot (mòduls de la fitxa =
  mòduls del RD; B del catàleg = oferta de B del RD). Únic cas: `HOT_C_016_5B`, catàleg de més. El
  catàleg enllaça HOT_B_0171, però el RD 1127/2025 no l'ofereix com a B d'aquest C. És inofensiu i
  en la mateixa categoria que els 35 del 078.
- **Primeres conseqüències per a la fase 4**, per confirmar a la fase 3:
  - **ARG_C_008_5B 1800:** el RD 87/2026 no l'ofereix com a B → hauria de passar de nota neutra a art. 58.3.
  - **1732 als SEA:** és associat a UC2519_2 per la correcció d'errors. Cal decidir si la nota de
    l'art. 58.3 ("mòdul no associat a cap estàndard de competència") hi és correcta.

## Fase 3 — Auditoria ampliada

- `audit()` i `audit_modulos()` també fan servir els RD individuals. Mateixes categories
  que al 078: OK / forat del catàleg / catàleg de més, fitxa ≠ decret, i classificació
  de cada mòdul sense B.
- Regenerar `plans/outputs/audit_c_modulos_boe.md`. La secció "Sense decret localitzat"
  només ha de contenir els C que de debò no tinguin RD.
- Fer servir les dades de producció (copiar del VPS `ofertes.json`, `c_modulos.json` i
  `bc_lomloe.json`; les locals poden ser antigues).

### Resultat de la fase 3 (2026-10-30)

`audit()` / `audit_modulos()` accepten `individuals` (llegits de `boe_certificados_individuales.json`).
`te_codi()` accepta també "– Código: X –" (RD 209/2025, IMP_C_006_4B). 3 tests nous. Auditoria regenerada
amb les dades de producció:
- Per certificat: **OK 331 → 362**; forat del catàleg 1 (igual); catàleg de més 35 → 36 (+HOT_C_016_5B,
  HOT_B_0171); no parsejat 1 (SSC_C_017_5B, verificat a mà); **sense decret 32 → 0**.
- "Fitxa ≠ decret": cap C nou. Els 31 C tenen fitxes completes; continuen sortint només els 11 del 079.
- Per mòdul: art. 58.3 467 → 500; neutre 1; altra família 13; sense decret 33 → 0.

**Verificació de la nota de l'art. 58.3 ("mòdul no associat a cap estàndard de competència").**
Es buscaren les files de taula de correspondència "UCxxxx_x: … NNNN." / "NNNN. … UCxxxx_x" dins el decret
de cada C, per als 500 mòduls:
- **10 parells SÍ estan associats a un UC**. Per tant la nota hi és FALSA (encara que no siguin Grau B):
  - 1724 ↔ UC2327_2 ("funciones de nivel básico para la prevención de riesgos en construcción"):
    EOC_C_009_4B (RD 405/2025), EOC_C_010_4B (RD 406/2025), EOC_C_011_4B (RD 404/2025).
  - 1732 ↔ UC2519_2 ("… prevención de riesgos laborales"): SSC_C_002_4B (RD 533/2025, annex IV) i
    SEA_C_001…006_4B (RD 1157/2024, afegit per la correcció d'errors BOE-A-2025-10206).
- **1782 no s'associa a cap UC en cap taula.** La nota hi és correcta.
- **Probable, però no verificable.** Els decrets de grup no tenen taules mòdul ↔ UC, només la llista
  d'UC de cada C. SEA_C_004_5B i SEA_C_006_5B (RD 211/2025) inclouen UC1970_2 (PRL en incendis
  forestals), i el seu únic mòdul de PRL és el 1782.
- **ARG_C_008_5B 1800:** el RD 87/2026 no l'ofereix com a B i no l'associa a cap UC → art. 58.3.

## Fase 4 — Aplicar a l'app (només el que surti a la fase 3)

Abans de tocar res, cal portar els resultats al propietari. Correccions previstes, totes
amb les constants que ja existeixen a `backend/app.py`:
- **Fitxa ≠ decret:** entrades noves a `_C_MODULOS_BOE_AFEGITS` / `_C_MODULOS_NO_AL_DECRET`
  (pla 079).
- **ARG_C_008_5B 1800:**
  - Si el RD no l'ofereix com a B, s'ha de treure de `_C_MODULOS_NOTA_NEUTRA`, i passarà a portar la nota de l'art. 58.3.
  - Si l'ofereix, és un forat del catàleg i es manté la nota neutra.
- **PRL (1724, 1732, 1782):** confirmar que cap RD individual no l'ofereix com a B. Si
  algun ho fa, aquell parell passa a `_C_MODULOS_NOTA_NEUTRA`.
- **Forats del catàleg nous:** el parell va a `_C_MODULOS_NOTA_NEUTRA`.

Si la fase 3 no troba cap discrepància, la fase 4 no canvia res de codi. Només s'anota
el resultat.

## Fora d'abast

- Executar la descoberta automàticament quan aparegui un C nou al catàleg (es pot
  plantejar després, amb el detector d'aquest pla).
- Avisar el ministeri de les discrepàncies.

## Verificació final

- La secció "Sense decret localitzat" queda buida, o amb cada cas justificat.
- Si hi ha fase 4: `pytest backend/tests` en verd, i a producció l'API d'un C afectat
  retorna la nota nova.
