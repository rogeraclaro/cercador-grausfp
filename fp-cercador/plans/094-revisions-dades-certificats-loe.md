# Pla 094 — Revisions de dades dels certificats LOE: hores, UF i certificats absents

Origen: anàlisi del 2026-11-17 (contrast de les nostres dades amb els annexos oficials i amb la llista
del SEPE). Són tres comprovacions petites i independents; cap està diagnosticada del tot.
Executable per un agent sense context, en una sessió nova. Millor després del 090. Pla petit.

## Què fa

Aclareix tres discrepàncies i corregeix les que resultin ser errors nostres.

## Fets verificats (2026-11-17, no repetir)

Tots els fitxers són a `plans/outputs/analisi-20261117/`.

1. **Hores totals** (`discrepancies_hores.json`): en 20 certificats, `duracion_horas` (que ve del
   buscador de certificats de todofp) no coincideix amb la llista del SEPE. Mirant la línia «Duración
   de la formación asociada» de l'annex: en 15 l'annex dona la raó al SEPE (per exemple IMSV0408:
   nosaltres 630, annex i SEPE 440; EOCE0109: 780 contra 600), en 3 ens la dona a nosaltres (MAPN0712,
   MAPN0210, MAPN0310) i en 2 no s'ha trobat la línia (MAPN0111, ENAT0108). No s'ha comprovat si el
   buscador reflecteix una modificació posterior del certificat.
2. **UF penjades d'un MF diferent** (`discrepancies_uf_pares.json`): 45 UF de 2.321 comparables on
   `a_loe_pares.json` no coincideix amb l'annex. Exemples: UF0021 (nosaltres MF0532_2, annex MF0531_2),
   UF0033 (MF0240_2 contra MF0239_2), UF1709 (nosaltres hi afegim MF1664_3). `a_loe_pares.json` el
   genera el refresc (`backend/scrapers/b_contingut_scraper.py`, `pipeline.py`). El lector de l'annex
   és de prova i també es pot equivocar: cal mirar uns quants casos a mà abans de decidir.
3. **Certificats de la llista del SEPE que no tenim** (`cp_sepe_absents_a_grausfp.json`): SSCI0412,
   SSCI0312, SEAG0212, IMAQ0110, SSCE0110 (Docència de la formació professional per a l'ocupació),
   FMEC0210, FMEC0110, SEAG0110 i AGAO0308M. I nosaltres en tenim 6 que la llista no porta:
   COML0121_1, AFDA0119_2, FMEC0119_2, FMEC0219_2, FMEC0319_2 i AGAO0308. Hipòtesi sense comprovar:
   FMEC0110/0210 van ser substituïts pels FMEC0x19 i AGAO0308M és una variant d'AGAO0308; la resta
   poden ser derogats o absents de la font que fem servir.

## Disseny

- Per a cada punt: primer diagnòstic (quina font té raó i per què), després correcció a l'origen
  (scraper o generador), mai a mà sobre el JSON.
- Hores: si l'annex i el SEPE coincideixen i no hi ha cap decret modificador, corregir amb una taula
  d'excepcions petita i documentada, o canviar la font; decidir-ho segons el que surti.
- Certificats absents: mirar al buscador de todofp i al BOE si són vigents. Si ho són i ens falten,
  és un forat del scraper; si són derogats, no s'hi fa res i es deixa escrit.
- Resultat de cada punt a `plans/outputs/audit_cp_loe_20261117.md`.

## Fases

1. Hores: comprovar 5 casos al BOE (hi ha modificació?), decidir i aplicar.
2. UF: comprovar 10 casos a mà a l'annex; si l'error és nostre, trobar-ne la causa al scraper.
3. Certificats absents: estat de cadascun dels 9 i dels 6.
4. Informe.

## STOP — atura't i pregunta

- Abans de tocar el refresc setmanal (`pipeline.py`).
- Si afegir els certificats absents canvia identificadors o `ref` existents.
- No desplegar sense aprovació explícita.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
