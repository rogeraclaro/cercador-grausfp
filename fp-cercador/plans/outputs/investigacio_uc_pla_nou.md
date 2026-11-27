# Investigació: codis d'UC dels Graus B i C del pla nou (pas 0 del pla 106)

Data: 2026-11-27. Només lectura: cap codi ni cap dada de producció tocats. Dades locals del
2026-11-08 (`b_contingut.json`) i del 2026-11-26 (la resta); a producció les xifres poden variar una mica.

## Conclusió

**No cal cap font nova.** Els codis ja són a les nostres dades, però amb un altre prefix: el ministeri
ara escriu `ECP0493_3` (estàndard de competència professional) on abans escrivia `UC0493_3`. El número
i el nivell són els mateixos. Per això una cerca de `UC…` a les dades no trobava res del pla nou.

| Què | D'on surt | Cobertura | Cost |
|---|---|---|---|
| Graus B del pla nou | `b_contingut.json` (pla 068), camp `ecp` | 1.016 de 1.019 | Cap: ja es baixa cada setmana |
| Graus B del pla antic (`MF…`) | `b_contingut.json`, camp `ecp` | 1.938 de 1.949 | Cap |
| Graus C del pla antic | `bc_loe.json` (pla 090) | 580 de 580 | Cap |
| Cicles D | `d_uc_corr.json` (pla 091) | 185 de 195 | Cap |
| Graus C del pla nou | Fitxa de todofp del C (secció «Estándares de competencia») | 11 de 11 a la mostra | Cap petició nova: `bc_lomloe_scraper` ja baixa aquestes 400 fitxes cada setmana; només cal llegir-ne una secció més |

Els B sense estàndard són legítims: «Inglés profesional» (2) i «Coordinación de equipos humanos» (1)
al pla nou.

## Respostes a les preguntes del pla

1. **Format del codi.** Dos prefixos per al mateix codi: `UC####_n` (decrets fins a mitjan 2025 i les
   nostres dades del pla antic) i `ECP####_n` (fitxes de todofp i decrets des del desembre del 2025).
   No hi ha taula d'equivalència perquè no cal: el número no canvia. Comprovat en 1.716 dels 2.017
   codis `ECP` de `b_contingut.json`, que tenen una `UC` amb el mateix número a `bc_loe.json`; la
   resta són estàndards nous.
2. **Un Grau B = una UC?** No sempre. Al pla nou: 525 B amb un estàndard, 298 amb dos, 113 amb tres i
   80 amb quatre o més (un, «Interpretación gráfica», en té 26).
3. **Al pla antic el codi del B no dona sempre la UC.** `MF0493_3` → `ECP0493_3` es compleix en 1.766
   dels 1.938 B; en 172 el número és un altre. Cal fer servir el camp `ecp`, no deduir-ho del codi.
4. **Manteniment.** Cap feina nova: `b_contingut.json` i les fitxes dels C es refan a cada refresc
   setmanal.

## Fonts provades

- **Fitxa de todofp (B i C).** 33 fitxes baixades (22 B i 11 C de famílies diferents). Totes porten la
  secció «Estándares de competencia», tret d'«Inglés profesional». És la mateixa pàgina que ja llegeix
  `b_contingut_scraper` (B) i `bc_lomloe_scraper` (C). La fitxa d'un Grau A no porta estàndards: remet
  al seu B.
- **Decrets del BOE.** 31 decrets baixats (8 de grup i 23 individuals). Els 400 C del pla nou hi tenen
  la llista d'estàndards (380 a l'annex I, 20 a l'article 6). Serveixen de contrast, no com a font:
  demanen un analitzador per a tres estructures diferents i no diuen quin estàndard és de cada B.
- **Catàleg de l'INCUAL.** No provat: les dues fonts anteriors ja ho cobreixen tot.

## Discrepàncies trobades (per decidir)

- **Fitxa del C contra el seu decret.** A la mostra, 9 de 11 C coincideixen. En 2 la fitxa és diferent:
  `HOT_C_001_4B` porta `ECP2816_2` on el decret diu `UC0261_2`, i a `AFD_C_006_4B` hi falta el
  `1081_2`. Sembla que la fitxa segueix el catàleg actualitzat; no ho he confirmat.
- **Unió dels B contra la llista del C.** Si les UC d'un C es calculessin sumant les dels seus B
  (`bc_lomloe.json`), només 257 dels 400 coincidirien amb el decret: en 84 en sobren (els mòduls
  compartits acrediten estàndards que no són del certificat), en 23 en falten i en 36 totes dues
  coses. Per això recomano llegir la llista de la fitxa del C i no sumar la dels B.

## Què canvia al pla 106

- L'índex UC → graus incorpora `b_contingut.json` (B nous i antics) i una llista nova d'estàndards per
  C del pla nou, extreta a `bc_lomloe_scraper` de la fitxa que ja es baixa.
- La cerca ha d'acceptar `UC0493_3` i `ECP0493_3` i casar pel número i el nivell.
- Exemple real: `UC0493_3` trobaria 8 resultats: `IFCD0210` (C antic), `MF0493_3` (B antic),
  `IFC_B_0376` i `IFC_B_0614` (B nous), `IFC_C_003_5B` i `IFC_C_007_5B` (C nous) i els dos cicles D.
- Fins al primer refresc després del desplegament, els C del pla nou no tindrien llista. Es pot
  omplir abans executant el scraper a mà (400 fitxes, 10–16 min).

## Decisions que demano

1. **Quin prefix es mostra a la web:** `UC` (el que la gent coneix), `ECP` (el que escriu ara el
   ministeri) o tots dos.
2. **Graus A:** si han de sortir en cercar una UC (heretant la del seu B) o no. Cada B en té uns
   quants i allargarien la llista.
3. **C del pla nou:** fitxa de todofp (recomanat) o llista del decret.

## Materials

Scripts i dades de la investigació, fora del repositori (carpeta temporal de la sessió): no es
conserven. Tot el que s'hi va mesurar és en aquest informe.
