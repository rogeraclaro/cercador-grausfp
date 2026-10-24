# Pla antic i pla nou: què està passant (documentació)

Data: 2026-10-25. Base per al text de la secció «Quin problema resol» de `frontend/per-que-grausfp.html`.

## Fets verificats al BOE (text consolidat)

1. **La reforma no esborra l'oferta anterior.** Llei Orgànica 3/2022, disposició transitòria segona: la ordenació dels ensenyaments d'FP del sistema educatiu i la dels certificats de professionalitat «continuarán vigentes hasta que se proceda al desarrollo reglamentario en el marco del nuevo Sistema de Formación Profesional».
   Font: https://www.boe.es/buscar/act.php?id=BOE-A-2022-5139

2. **Els certificats antics passen a ser Grau C.** Reial decret 659/2023, disposició transitòria primera, apartat 1: «Hasta tanto no se proceda reglamentariamente a su modificación, permanecerá vigente la ordenación de los certificados de profesionalidad recogida en cada uno de los reales decretos por los que se establecen y su oferta quedará integrada en los grados C del Sistema de Formación Profesional con la denominación de certificados profesionales.»
   Font: https://www.boe.es/buscar/act.php?id=BOE-A-2023-16889

3. **Canvia el vocabulari.** Mateixa disposició, apartat 2: «módulo formativo» passa a ser «módulo profesional»; «capacidades», «resultados de aprendizaje»; «unidad formativa», «bloque formativo».

4. **Desapareixen les pràctiques no laborals antigues.** Mateixa disposició, apartat 3: acabat el període transitori (31/12/2024, disposició transitòria sisena), el mòdul de pràctiques professionals no laborals dels certificats del RD 34/2008 se suprimeix en favor dels règims de formació dual; les hores es reparteixen entre la resta de mòduls.

5. **El marc antic queda derogat.** RD 659/2023, disposició derogatòria única, apartat 1: queda derogat el Reial decret 34/2008 (que regulava els certificats de professionalitat), excepte l'annex IV.

6. **Qui ja té un certificat antic no perd res.** LO 3/2022, disposició addicional sisena: qui tingui un certificat de professionalitat del RD 34/2008 «tendrán acreditados los estándares de competencia profesional del nuevo Catálogo Nacional de Estándares de Competencias profesionales declarados equivalentes» a les seves unitats de competència.

7. **Els títols (Grau D) segueixen la mateixa lògica.** RD 659/2023, disposició transitòria segona: la ordenació dels títols d'FP bàsica, grau mitjà i grau superior continua vigent fins que es modifiqui.

## Fets de fonts secundàries (no verificats al BOE)

- La substitució és gradual: cada nou reial decret de certificats professionals indica quins certificats antics queden derogats. Al 2025 se n'han publicat de nous (p. ex. un RD publicat al BOE el 3 d'abril de 2025 que afecta més de 50 certificats).
  Font: nota informativa de LABORA (Comunitat Valenciana) recollida per CECAP, https://cecap.es/sec_din/archivos/docs/1773938205C.%20VALENCIANA.%20NOTA%20INFORMATIVA%20LABORA%20RESPECTO%20A%20LA%20PUBLICACION%20DE%20NUEVOS%20GRADOS%20A,%20B%20Y%20C.pdf
- Curs 2025/2026: el mòdul de pràctiques no laborals ja no existeix i la formació en empresa s'integra als mòduls.
  Font: Circular 15/2025 d'Extremadura, https://cecap.es/sec_din/archivos/docs/1774888536Circular_15_2025_Funcionamiento_Grados_C(F).pdf

## Què es veu a les dades de GrausFP

Còpia de `ofertes.json` de producció (octubre 2026):

| Grau | Pla nou | Pla antic |
|---|---|---|
| A | 5.953 | 2.872 |
| B | 1.019 | 1.949 |
| C | 400 | 580 |
| D | 195 | 0 |
| E | 38 | 0 |

Gairebé 6 de cada 10 certificats C encara són del pla antic. Codis: pla antic com `ADGD0108`; pla nou com `ADG_C_001_3B`.

Conseqüències per a l'usuari:
- Conviuen dues versions de molts cursos, amb noms semblants però mòduls i convalidacions diferents.
- Per als C de pla nou sabem exactament quins mòduls comparteixen amb cada cicle D; per als de pla antic, la font oficial només diu que hi ha relació (vegeu la llegenda de l'itinerari: Complet / Parcial / Pla antic).

## Què fa GrausFP

- Marca cada registre del pla antic (etiqueta «Pla antic»).
- Filtres «Ocultar pla antic» i «Només pla antic».
- A l'itinerari, distingeix les relacions C→D completes, parcials i de pla antic (sense detall de mòduls).
