# Recompte: codis UC impresos als annexos contra els desats (2026-11-28)

Només lectura (pla 107, feina prèvia). Els 575 PDF es van baixar a una carpeta temporal de la sessió i no es conserven.

## Lectura que fa `generate_c_loe_estructura.py` («Asociado a la Unidad de Competencia: UC…»)

- Certificats del pla antic: 580. Llegits: 575. Sense PDF (404): 5 (COML0121_1, AFDA0119_2, FMEC0119_2, FMEC0219_2, FMEC0319_2).
  Sense segment propi (escanejats): 9 (EOCH0108, MAMD0209, ARGI0310, HOTU0111, MAPU0112, SANT0108, AFDA0111, INAJ0110, QUIB0108).
- Coincidències de la frase: 1.850; assignades a un MF: 1.847 (3 repetides sobre un MF que ja en tenia).
- El recompte reprodueix exactament el fitxer del disc: 556 certificats, 1.822 mòduls amb `uc`, 503 certificats amb alguna.
- Desats igual que impresos: 1.841. **Canviats: 6**

| Certificat | MF | Imprès | Desat | Nota |
|---|---|---|---|---|
| ELEE0109 | MF0820_2 | UC820_2 | UC0820_2 | zero que falta |
| QUIO0110 | MF0044_2 | UC044_2 | UC0044_2 | zero que falta |
| QUIO0112 | MF0044_2 | UC044_2 | UC0044_2 | zero que falta |
| SANP0108 | MF1605_3 | uc1605_3 | UC1605_3 | minúscules |
| HOTU0109 | MF1042_2 | UC142_2 | UC0142_2 | **el zero afegit dona un codi diferent del MF (1042)**: no és una errada «evident» |
| ARTG0512 | MF2127_3 | UC217_3 | UC0217_3 | **ídem (MF 2127)** |

## Mencions d'UC que aquesta lectura no captura

- La frase «Asociado a la Unidad de Competencia:» surt 376 vegades més sense codi al costat: als annexos a dues columnes, `pdftotext -layout` deixa el codi en una altra posició.
- 442 annexos porten l'apartat «Relación de unidades de competencia que configuran el certificado de profesionalidad», amb la llista de codis.
- Codis `UC####_N` escrits al segment del certificat i que `c_loe_estructura.json` no té: 511 (en 261 certificats).
- Formes no estrictes: `UC9999` sense nivell 12, `UC 9999_9` 7, `UC99999_9` 4, `UC9999_ 9` 1, `UC9999 9` 1, `UC9999-9` 1.

## `bc_loe.json` contra tot el text del segment (segona passada, sense xarxa)

- 566 certificats llegibles, 2.285 parells certificat–UC de `bc_loe.json`.
- **2.282 surten escrits literalment (`UC####_N`) en algun lloc del segment del seu certificat**; 3 no: [('QUIE0108', ['UC0048_3'], ['UC0048_2']), ('TMVI0112', ['UC1467_3'], ['UC1462_2', 'UC1467_2']), ('FMEM0311', ['UC2156_3'], ['UC2152_3'])].
- 563 certificats amb tots els parells escrits; 3 amb una part.
- Codis `UC` escrits al segment que `bc_loe.json` no té: 40 (p. ex. HOTR0109 `UC7033_1`, MAPN0310 `UC0010_1`).
- Reserva: «escrit en algun lloc del segment» no demostra que sigui una unitat del certificat (pot ser un requisit d'accés o una referència). Caldria llegir l'apartat «Relación de unidades de competencia…» per afirmar-ho.
- Els 14 certificats no llegibles sumen 43 parells sense cap comprovació possible amb aquest mètode.

El detall per certificat era en fitxers temporals de la sessió i no es conserva. Per refer-lo: baixar els annexos amb les funcions de `scripts/generate_c_loe_estructura.py` i comparar el text imprès amb el desat.
