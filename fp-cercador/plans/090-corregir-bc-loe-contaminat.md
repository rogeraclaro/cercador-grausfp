# Pla 090 — Corregir `bc_loe.json`: UC d'altres certificats enganxades

Origen: anàlisi del 2026-11-17 arran dels correus d'un usuari (docent d'FPO) que demanava la
correspondència entre certificats i mòduls de cicle. En contrastar les nostres dades amb els annexos
oficials va sortir aquest error. Les decisions tècniques d'aquest pla són del redactor i es poden
discutir abans d'executar-lo.
Executable per un agent sense context, en una sessió nova. No depèn de cap altre pla. Pla petit.
**Va abans que el 091, el 092 i el 093**, que es construeixen sobre `bc_loe.json`.

## Què fa

Regenera `backend/data/bc_loe.json` (certificat C LOE → les seves UC) de manera que cada certificat
només porti les UC del seu propi annex, i recupera les UC dels tres certificats que avui no en tenen.

## Fets verificats (2026-11-17, no repetir)

- `scripts/generate_bc_loe.py` baixa `https://www.todofp.es/dam/todofp/certificados-profesionales/anexos/<codi>.pdf`
  i hi aplica `\bUC\d{4}_\d+\b` a **tot** el text (`_fetch_pdf_uc_codes`).
- 170 dels 575 PDF contenen el codi de més d'un certificat: el PDF és un tall del BOE i sovint arrossega
  l'inici de l'annex següent (o el final de l'anterior). Exemple: `elem0311.pdf`, 29 pàgines; a la pàgina 29
  comença l'annex d'ELEM0411 i d'allà surten UC1975_2, UC1976_2 i UC1977_2, que avui atribuïm a ELEM0311.
- Abast: dels 466 annexos on el lector de prova quadra MF i UC, **110 tenen UC de més** (333 enllaços UC→CP
  falsos de 2.729) i cap en té de menys. Llista: `plans/outputs/analisi-20261117/errors_bc_loe.json`.
- Contra la llista de MF del SEPE (583 certificats): 444 iguals, 130 amb UC de més, 3 amb UC de menys
  (MAPU0112, EOCH0108, QUIB0108: PDF escanejats, sense text) i 1 de creuat (FMEM0311). Llista:
  `errors_bc_loe_vs_sepe.json`. La llista del SEPE coincideix amb l'annex en 462 de 465 casos.
- 5 certificats amb sufix (`AFDA0119_2`, `COML0121_1`, `FMEC0119_2`, `FMEC0219_2`, `FMEC0319_2`) no tenen
  annex a aquesta adreça (404). Avui ja queden amb llista buida.
- Qui llegeix `bc_loe.json`: `backend/app.py` (itinerari B↔C LOE i `_get_bc_loe_inverse`),
  `backend/itinerary_graph.py`, `backend/centres_inherit.py` i `backend/centres_watch_service.py`. Per tant
  l'error també fa que un mòdul B LOE **hereti centres** de certificats que no el contenen, i pot haver
  generat avisos de seguiment de centres equivocats.
- `backend/data/` és fora del git (`.gitignore`); el fitxer es genera en local i es copia al VPS.
- Estructura d'un annex (text de `pdftotext -layout`): `Código: <CP>` a la identificació; les UC del
  certificat surten com a capçaleres `Código: UC####_N` (apartat II) i els mòduls com a `Código: MF####_N`
  (apartat III). Aquestes capçaleres són fiables; el paràgraf «Relación de unidades de competencia…» de
  la primera pàgina surt il·legible en alguns PDF (tipus de lletra sense mapa de caràcters).
- Lector de prova que ja fa el retall: `plans/outputs/analisi-20261117/scripts/parse_cp.py`. Sortida:
  `cp_parsed.json`. Els 109 annexos on MF i UC no quadren són a `annexos_dubtosos.json`.
- Instantània de la llista del SEPE (dades públiques: MF, hores i RD per certificat):
  `plans/outputs/analisi-20261117/sepe_cp_snapshot.json`.

## Disseny

- Retallar el text de cada PDF al segment propi: des de la primera aparició de `Código: <CP>` fins a la
  primera aparició posterior de `Código: <un altre CP>` (patró `[A-Z]{4}\d{4}`), o el final.
- Dins del segment, les UC del certificat són les de les capçaleres `Código: UC####_N`. Com a comprovació,
  han de coincidir en número amb les capçaleres `Código: MF####_N`.
- Si no coincideixen, o el PDF no té text, o no s'hi troba el codi propi: fer servir la llista de MF de
  `sepe_cp_snapshot.json` (MF####  → UC####, amb el nivell del certificat). Copiar aquesta instantània a
  `scripts/data/` o equivalent perquè el generador no depengui de `plans/outputs/`.
- Si les dues fonts discrepen, guanya l'annex quan MF i UC hi quadren; si no, el SEPE. Cada cas
  discrepant s'escriu en un informe (`plans/outputs/audit_bc_loe.md`) amb la font triada.
- El generador ha de continuar fallant si la cobertura baixa del 80 %.
- No canviar el format de `bc_loe.json` ni cap consumidor.

## Fases

1. Test primer (`backend/tests/` o un test del script, seguint el que ja hi hagi per a
   `build_c_modulos.py`): amb un text de mostra que conté dos annexos, la funció de retall només torna
   les UC del primer. Cas real de referència: ELEM0311 → `UC1978_2`, `UC1979_2`.
2. Reescriure l'extracció de `generate_bc_loe.py` amb el retall i la segona font.
3. Executar-lo i comparar amb el fitxer actual: han de desaparèixer les UC llistades a
   `errors_bc_loe.json`, i MAPU0112, EOCH0108 i QUIB0108 han de passar a tenir UC. Escriure l'informe.
4. Comprovar a la web en local: itinerari d'ELEM0311 (2 mòduls B, no 5), un mòdul B que abans penjava
   de dos certificats i ara d'un, i els centres heretats d'aquest mòdul.
5. Revisar si `centres_watch_service.py` té estat desat que depengui dels enllaços antics (avisos ja
   enviats, llistes de centres vistes) i si cal fer-hi res perquè el canvi no dispari avisos de cop.

## STOP — atura't i pregunta

- Si després del canvi algun certificat que avui té UC es queda sense cap.
- Si la fase 5 troba que el canvi dispararia correus a usuaris.
- No desplegar sense aprovació explícita. No reiniciar diumenge al migdia sense mirar abans
  `/api/refresh-status`.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`. Recorda que `bc_loe.json` s'ha de
copiar al VPS (no viatja amb el git).
