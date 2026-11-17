# Pla 093 — Exportació relacional: certificat–MF–UF i cicle–mòdul–UC

Origen: correus d'un usuari (docent d'FPO, 2026-11) que es construïa a mà, amb una IA, un Excel amb
els certificats, els seus mòduls formatius i les unitats formatives, per creuar-lo amb els mòduls dels
cicles. Anàlisi del 2026-11-17. Les decisions tècniques d'aquest pla són del redactor i es poden
discutir abans d'executar-lo.
Executable per un agent sense context, en una sessió nova. Depèn de: 090; la part de cicles, de 091.
Pla mitjà.

## Què fa

Permet baixar, en un fitxer que l'Excel obre bé, l'estructura d'un certificat (o d'una selecció):
una fila per unitat formativa amb el seu mòdul, el seu certificat i les hores; i l'estructura d'un
cicle: una fila per mòdul amb les UC que l'acrediten.

## Fets verificats (2026-11-17, no repetir)

- L'exportació actual (`frontend/index.html`, línies ~3025–3066, plans 034–035) és la llista filtrada
  en pla: codi, denominació, família, grau, nivell, pla antic i centres triats. Separador `;`, BOM
  UTF-8, nom `grausfp-export.csv`. No porta cap relació.
- Dades que ja tenim: `bc_loe.json` (certificat → UC), mòduls B LOE `MF####_N` i unitats A LOE
  `UF####` al catàleg, `a_loe_pares.json` (UF → els seus MF). Per als LOMLOE: `bc_lomloe.json` i
  `c_modulos.json`. Per als cicles: `d_modulos.json`.
- Dades que **no** tenim: hores per MF i per UF, i el mòdul de pràctiques (`MP####`) de cada certificat.
  Només tenim `duracion_horas` del certificat.
- Els annexos dels certificats les porten. Al text de `pdftotext -layout`: `Código: MF####_N` seguit de
  `Duración: N horas`, i dins de cada mòdul `Código: UF####` amb la seva `Duración`. El lector de prova
  (`plans/outputs/analisi-20261117/scripts/parse_cp.py`) ja ho treu; `cp_parsed.json` té hores per a
  tots els mòduls de 433 dels 466 annexos fiables.
- Les hores d'un certificat no són la suma de les dels seus mòduls quan hi ha unitats transversals
  compartides (ELEE0109: la suma dona 1.130 i el certificat en té 920). El total oficial és la línia
  «Duración de la formación asociada: N horas» de l'annex.
- L'Excel de l'usuari tenia 287 parells MF–UF falsos de 664 i 97 codis de certificat inexistents:
  la IA no és una font fiable per a això, i és el valor que aporta aquesta exportació.
- El projecte no admet dependències noves (ni de Python ni de frontend).

## Disseny

- Format: CSV amb `;` i BOM, com l'exportació actual. Sense biblioteca d'Excel (no es pot afegir).
  Dos fitxers separats en lloc d'un llibre amb pestanyes.
- Índex nou `backend/data/c_loe_estructura.json`, generat en el mateix pas que `bc_loe.json` (pla 090)
  o amb un script germà: per certificat, els MF amb hores, les UF de cada MF amb hores, el mòdul de
  pràctiques i el total oficial. Si l'annex no dona hores, el camp queda buit (no s'inventa).
- Endpoint `GET /api/export/estructura?refs=<ref,…>` (límit raonable de certificats per petició) que
  torna el CSV. Columnes del fitxer de certificats: codi i nom del certificat, nivell, família, codi i
  nom del MF, hores del MF, UC associada, codi i nom de la UF, hores de la UF, transversal (sí/no).
  Una fila per UF; si el MF no té UF, una fila amb les columnes d'UF buides.
- Fitxer de cicles (quan hi hagi el 091): cicle, codi i nom del mòdul, UC que l'acrediten, i
  certificats LOE que porten aquestes UC.
- Punts d'entrada: botó a l'itinerari d'un certificat i d'un cicle; i al cercador, quan el filtre
  deixa només graus C, una segona opció al costat d'«Exporta CSV» («Exporta l'estructura»).
- Per als C LOMLOE, la mateixa exportació amb els mòduls de `c_modulos.json` i els A que en pengen.
- Peu del fitxer o columna amb la font i la data de les dades.

## Fases

1. Generador de `c_loe_estructura.json` amb tests sobre text de mostra (mòdul amb UF, mòdul sense UF,
   unitat transversal repetida, annex sense hores). Comprovar ELEE0109: 6 MF, total 920 h.
2. Endpoint i tests (certificat LOE, certificat LOMLOE, ref inexistent, límit).
3. Punts d'entrada al frontend i textos (ca i es).
4. Part de cicles, si el 091 és fet; si no, deixar-la preparada i dir-ho.
5. Verificació: obrir els fitxers amb l'Excel en català i comprovar accents, columnes i que un
   `BUSCARV` per codi de MF funciona entre el fitxer de certificats i el de cicles.

## STOP — atura't i pregunta

- Si per fer-ho bé cal una dependència nova.
- Format: **CSV, decidit pel propietari el 2026-11-17** («de moment»). No afegir cap dependència per fer
  `.xlsx`; si més endavant es vol un sol fitxer amb pestanyes, és un pla a part.
- No desplegar sense aprovació explícita.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`. `c_loe_estructura.json` s'ha de
copiar al VPS.
