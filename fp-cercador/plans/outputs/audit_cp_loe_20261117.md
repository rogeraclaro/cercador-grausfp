# Auditoria dels certificats LOE: hores, UF i certificats absents (pla 094)

Executat el 2026-11-18. Fonts contrastades: buscador de certificats de todofp (`duracion_horas`), annex PDF
de todofp, llista del SEPE (`analisi-20261117/sepe_cp_snapshot.json`) i BOE (XML de cada decret).

## Què s'ha après de les fonts

- **L'annex PDF de todofp és el text original del decret, sense consolidar.** No recull modificacions ni
  correccions d'errors posteriors.
- **El buscador de certificats** suma en alguns casos els MF tal qual, comptant dues o tres vegades les UF
  transversals (EOCE0109: 220+240+200+120 = 780, però UF0652 es repeteix a tres MF i el total oficial és 600).
  En d'altres simplement porta una xifra errònia (IMSV0408: 630, que és el total d'IMSV0308).
- **La llista del SEPE** ha tingut raó en tots els casos comprovats al BOE, inclosos els modificats.
  És una instantània baixada a mà; no la refresca cap procés.
- **`a_loe_pares.json`** (fitxa de cada UF a todofp) ha tingut raó en els 20 casos mirats.

## 1. Hores totals

De 556 certificats comparables, 530 quadren a totes les fonts. Els 26 restants:

### 1a. El buscador s'equivoca (17) — annex i SEPE coincideixen

| Certificat | Buscador (nosaltres) | Correcte |
|---|---|---|
| ADGN0110 | 690 | 730 |
| ADGN0210 | 600 | 730 |
| AFDA0210 | 620 | 590 |
| AFDA0311 | 610 | 550 |
| AGAN0411 | 400 | 450 |
| AGAR0109 | 640 | 610 |
| ARGC0110 | 380 | 420 |
| ARGT0109 | 420 | 330 |
| ARGT0112 | 520 | 630 |
| COML0109 | 550 | 520 |
| COML0309 | 420 | 390 |
| ENAT0108 | 480 | 450 |
| EOCB0208 | 360 | 320 |
| EOCE0109 | 780 | 600 |
| IMSV0308 | 540 | 630 |
| IMSV0408 | 630 | 440 |
| MAPN0111 | 440 | 390 |

Comprovat al BOE (text del decret): IMSV0408 (RD 725/2011, 440), EOCE0109 (RD 644/2011, 600), ADGN0210
(RD 610/2013, 730). Cap decret posterior en canvia la durada.

### 1b. Modificats per un decret posterior (3) — té raó el SEPE; buscador i annex desfasats

| Certificat | Buscador i annex | Correcte | Norma |
|---|---|---|---|
| MAPN0210 | 310 | 320 | RD 622/2013, disp. final 2a |
| MAPN0310 | 230 | 210 | RD 622/2013 (240) i RD 988/2013 (treu MF0010_1, 30 h) |
| MAPN0712 | 530 | 850 | RD 257/2019 (pràctiques MP0555: 400 h) |

MAPN0310: el RD 988/2013 diu literalment «de 230 horas a 200 horas», sense tenir en compte les 240 del RD
622/2013; el SEPE en dona 210 (240 − 30). Es proposa 210, que és el que surt d'aplicar els dos decrets.

### 1c. Ja el tenim bé (6) — l'annex de todofp és el desfasat

| Certificat | Nosaltres i SEPE | Annex | Comprovació |
|---|---|---|---|
| SSCE0112 | 550 | 530 | Correcció d'errors BOE-A-2013-12264: «debe decir 550» |
| MAPN0110 | 300 | 290 | RD 622/2013: 300 |
| ADGD0208 | 790 | 760 | La suma dels MF i les pràctiques de l'annex dona 790 |
| IEXM0509 | 510 | 520 | La suma dels MF i les pràctiques de l'annex dona 510 |
| ARTB0112 | 460 | 550 | 550 és la suma sense descomptar la UF transversal |
| IFCT0610 | 650 | 680 | Sense comprovació pròpia; nosaltres i el SEPE coincidim |

Aquests 6, més els 3 d'1b, surten malament a l'exportació CSV (`/api/export/estructura`), que prefereix
el total de l'annex.

### Correcció aplicada (aprovada pel propietari el 2026-11-18)

- `backend/c_horas_overrides.json`: 20 files (les 17 d'1a i les 3 d'1b) amb la xifra del buscador, la
  correcta, el motiu i la norma.
- `certificados_scraper.corrected_hours` l'aplica dins `enrich_record`, i només mentre el buscador continuï
  donant la xifra errònia coneguda; si el ministeri la canvia, mana la font i s'avisa al registre.
  Comprovat contra el buscador en viu: 20 de 20 corregits, la resta intactes.
- L'exportació prefereix `duracion_horas` i només cau al total de l'annex si falta.
- Documentat a la web: `fonts.html#errors` («Errors coneguts a les fonts oficials», ca/es). Un test comprova
  que cada fila de la taula d'excepcions surt a la pàgina.
- **Efecte**: les hores canvien a `ofertes.json` quan corre el refresc. Entre el desplegament i el refresc,
  el CSV donaria malament els 17 d'1a: cal llançar el refresc just després de desplegar.

## 2. UF penjades d'un MF diferent

Amb el lector d'annexos del pla 093, les 45 discrepàncies baixen a 20 (27 eren falsos positius del lector
de prova; en surten 2 de noves). De les 20:

- 16, mirades a mà a la «Relación de módulos formativos y de unidades formativas» de la primera pàgina
  de l'annex: **`a_loe_pares.json` té raó en totes**. Certificats: AGAO0208, AGAF0108, COMV0108, HOTR0408,
  MAMS0108, SSCS0108, ENAT0108, ELES0111, FMEC0209, HOTR0208, HOTG0208.
- 4 no són discrepàncies: el MF és d'un certificat sense estructura (IMAR0508, SANT0108, AFDA0111) o que
  ja no és al catàleg (IMAQ0110).

**El scraper no té cap error. L'error era al generador del pla 093** (`scripts/generate_c_loe_estructura.py`):
els annexos a dues columnes surten de `pdftotext -layout` amb el «Código: UF…» abans del «Código: MF…» del
seu mòdul, i la UF quedava penjada del mòdul anterior o es perdia. Afectava 17 certificats de l'exportació.

Corregit a l'origen: `apply_uf_parents` recol·loca cada UF segons `a_loe_pares.json` (una UF que la fitxa
no coneix es queda on la posa l'annex). De passada, el total de l'annex ja es llegeix quan ve escrit
«(390 horas)» o «.390 horas». `c_loe_estructura.json` regenerat en local:

- 27 certificats canvien; 36 MF amb la llista d'UF corregida; cap UF contradiu ja `a_loe_pares.json`.
- Certificats amb algun MF sense hores: de 51 a 45. Sense total de l'annex: de 39 a 29.
- Segueixen sent 556 de 580 certificats.
- Limitació: una UF que l'annex no deixava llegir i que s'afegeix per la fitxa surt sense hores (SEAG0111).
- Còpia de l'anterior: `backend/data/c_loe_estructura.json.bak-pre094`.

## 3. Certificats de la llista del SEPE que no tenim

| Certificat | Estat | Substitut al Buscador de Graus |
|---|---|---|
| SSCI0412 Operaciones en servicios funerarios | Substituït | `SSC_C_002_4B` |
| SSCI0312 Atención al cliente… servicios funerarios | Substituït | `SSC_C_001_4B` |
| SEAG0212 Mantenimiento higiénico-sanitario… | Substituït | `SEA_C_002_4B` |
| IMAQ0110 Ascensores | Substituït | `IMA_C_010_4B` |
| SSCE0110 Docencia de la FP para el empleo | Substituït | `SSC_C_017_5B` (Habilitación para la docencia en grados A, B y C) |
| FMEC0210 Soldadura oxigás y MIG/MAG | Substituït | `FME_C_004_4B` (Soldadura en atmósfera natural y protegida) |
| FMEC0110 Soldadura con electrodo revestido y TIG | Substituït | `FME_C_004_4B` |
| SEAG0110 Servicios para el control de plagas | Substituït | `SEA_C_001_4B` |
| AGAO0308M Jardinería y restauración del paisaje | Variant del SEPE d'AGAO0308, que sí que tenim | — |

Els 8 primers continuen al buscador de certificats de todofp (588 certificats), però el Buscador de Graus
FP, que és la nostra font de registres (580 LOE), ja no els llista: hi ha el Grau C nou que els
substitueix, i el tenim. **No és cap forat del scraper; no s'hi afegeix res.** L'aparellament s'ha fet per
denominació, no per una taula oficial d'equivalències.

Els 6 que tenim i la llista del SEPE no porta: COML0121_1, AFDA0119_2, FMEC0119_2, FMEC0219_2 i FMEC0319_2
són certificats del 2019–2021 que sí que són als dos buscadors de todofp (la llista del SEPE és anterior o
no els recull); AGAO0308 és el mateix que AGAO0308M. Cap acció.
