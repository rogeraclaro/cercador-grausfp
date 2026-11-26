# Programes formatius i ocupacions del SEPE — prova amb 50 especialitats (pla 100)

- Data: 2026-11-26
- Sortida: fitxer de prova a la carpeta temporal de la sessió (no `backend/data/sepe_programes.json`)
- Mode: complet, mateixos paràmetres que la descàrrega de producció (pausa aleatòria 5–10 s, una sessió per especialitat) · 50 codis triats
- Temps total: 9,2 min · mitjana 11,0 s per especialitat (amb la pausa) · cap error de xarxa, cap 403/429
- **Estimació per a tot el catàleg (7.557 especialitats): ~23 h** (no ~10 h com deia el pla: la pausa de 5–10 s ja suma ~7,5 s de mitjana)
- Especialitats a l'abast de l'informe: 50

## Per plantilla esperada

Plantilla segons el catàleg: modern = vigència des del 2021; po = sufix PO; antic = vigència abans del 2015; altres = 2015–2020 sense PO.

| Plantilla | Especialitats | Baixades | Llegides bé | Mòduls validats | Mòduls no quadren | Mòduls il·legibles | Sense PDF | PDF no llegit | Sense ocupacions |
|---|---|---|---|---|---|---|---|---|---|
| modern | 30 | 30 | 30 | 30 | 0 | 0 | 0 | 0 | 7 |
| po | 15 | 15 | 15 | 0 | 0 | 0 | 0 | 0 | 15 |
| antic | 5 | 5 | 5 | 0 | 0 | 0 | 0 | 0 | 3 |

Plantilla moderna amb mòduls validats: 30/30 (100.0 %; objectiu orientatiu ≥ 90 %).

«Llegides bé»: programa llegit, amb objectiu i, a la plantilla moderna, mòduls validats (pot no tenir ocupacions).

## Plantilla detectada al PDF

- modern: modern 30
- po: po 15
- antic: antic 5

## Pitjors casos (fins a 30) per revisar a mà

| Codi | Plantilla | Motiu |
|---|---|---|
| ADGG063PO | po | sense ocupacions |
| AGAJ010PO | po | sense ocupacions |
| ARGG033PO | po | sense ocupacions |
| COMT042PO | po | sense ocupacions |
| CTRD0055 | modern | sense ocupacions |
| CTRE0008 | modern | sense ocupacions |
| CTRG0004 | modern | sense ocupacions |
| CTRR0010 | modern | sense ocupacions |
| CTRR0016 | modern | sense ocupacions |
| ENAE010PO | po | sense ocupacions |
| EOCB039PO | po | sense ocupacions |
| FCOI16 | modern | sense ocupacions |
| FCOI25 | modern | sense ocupacions |
| FCOV10 | antic | sense ocupacions |
| FMEC06EXP | antic | sense ocupacions |
| FMEM005PO | po | sense ocupacions |
| IFCD04 | antic | sense ocupacions |
| IFCT055PO | po | sense ocupacions |
| IMPQ006PO | po | sense ocupacions |
| MAPN026PO | po | sense ocupacions |
| QUIE022PO | po | sense ocupacions |
| SANT066PO | po | sense ocupacions |
| SEAG050PO | po | sense ocupacions |
| SSCE001PO | po | sense ocupacions |
| TCPC013PO | po | sense ocupacions |

## Com s'ha fet la prova

- Tria (50): 25 de plantilla moderna de famílies diferents (inclou SSCE22, IFCD0025, ADGN0023), 15 «PO»
  (inclou SSCE001PO), 5 antigues (< 2015; inclou ADGA12DCP i dues EXP) i 5 transversals `CTR*` de categories
  diferents. Cap de les 50 era del grup «altres» (2015–2020 sense PO, 309 especialitats al catàleg).
- Primera passada (19:16–19:26): 10 de 30 modernes amb «taula de mòduls il·legible». Causes: el títol
  «Modalidad de impartición» (en singular) no era a la llista d'apartats; noms de mòdul que no surten centrats
  respecte de la línia «Módulo N»; i un cas (TMVI33) amb les hores a la línia del nom. També una «PO» (COMT042PO)
  amb la frase «…A TRABAJADORES / OCUPADOS» partida en dues línies es detectava com a antiga, i a la plantilla
  moderna el text «modalidad de impartición» de dins de «Duración» tallava l'apartat (es perdien les hores de
  tutoria i les presencials).
- Per depurar-ho es van tornar a baixar les 12 especialitats afectades desant-ne el text, i després es va tornar a
  fer la prova sencera de 50 amb el lector corregit (19:30–19:39). Les xifres de temps són d'aquesta segona passada.
- Últim retoc sense xarxa: a les «PO», «Modalidad: Indistinta» posa les hores totals a presencial i a
  teleformació (vol dir «en qualsevol de les dues», no un repartiment); ara només es desa un repartiment real.
  Les taules d'aquest informe s'han refet (`--nomes-informe`) amb els textos de la segona passada i el lector final.

## Lectura dels resultats

- Tots els PDF es llegeixen. Plantilla moderna: objectiu, mòduls validats per la suma d'hores (30/30),
  requisits d'accés, hores de tutoria o presencials, i «per a què serveix» quan n'hi ha (5/30).
- «PO» i antigues: només l'objectiu (com preveu el pla). Les «PO» no tenen repartiment d'hores útil: totes les de
  la mostra són d'una sola modalitat o «Indistinta».
- Ocupacions: cap de les 15 «PO», cap de les 5 transversals ni FCOI16/FCOI25, i 3 de 5 antigues no en tenen al
  SEPE. No és un error de lectura: el modal del SEPE les dona buides. La llista de «pitjors casos» és, per
  tant, només de «sense ocupacions».

## Ordre de la descàrrega completa

Des de la carpeta `fp-cercador` del repositori, a l'ordinador del propietari (no al VPS ni en diumenge al matí):

```
caffeinate -i python3 scripts/sepe_descarrega_programes.py --des-de 2026-11-27
```

Posa a `--des-de` el dia que la llancis. Si s'atura (sol, amb un 403/429 o 5 errors seguits; o amb Ctrl+C o
una apagada), es reprèn amb **la mateixa ordre i la mateixa data**: salta les ja baixades aquell dia o després.
Desa cada 25 especialitats. Genera l'informe a `plans/outputs/sepe-programes-<data>.md`.

Després, copiar-lo al VPS (es llegeix per mtime, no cal reiniciar):

```
scp backend/data/sepe_programes.json contabo:/home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/
ssh contabo chown masellas-grausfp: /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/sepe_programes.json
```

Ús habitual més endavant: `caffeinate -i python3 scripts/sepe_descarrega_programes.py --nomes-canvis`.

## Condicions de reutilització del SEPE

L'avís legal de sepe.es (https://www.sepe.es/HomeSepe/mas-informacion-contacto/aviso-legal) aplica la Llei
37/2007 i el RD 1495/2011 de reutilització d'informació del sector públic: autoritza la reutilització, també
comercial, gratuïta i no exclusiva, amb aquestes condicions: **citar la font**, **esmentar la data de l'última
actualització**, **no desnaturalitzar el sentit de la informació** i no suggerir que el SEPE avala l'ús. No s'ha
trobat un avís propi de sede.sepe.gob.es (l'URL que s'hi va provar torna 404); el de sepe.es diu que l'avís de
reutilització ha d'estar «preferentment a la seu electrònica», així que s'entén que aplica. La fitxa ho compleix:
diu «Text del programa oficial del SEPE (en castellà), consultat el <data>», enllaça el PDF original i no
tradueix ni reescriu el text. Risc baix; no és una confirmació jurídica.
