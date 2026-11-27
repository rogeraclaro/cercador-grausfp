# Pla 106 — Cerca per unitat de competència (codis UC / ECP)

Prioritat P2 · Mida M · Depèn de: 068, 090, 091 (dades ja fetes) · Origen: pregunta del propietari del 2026-11-27.
Executable per un agent sense context.

## Context

- Una **unitat de competència** (UC) és la peça mínima que acredita l'INCUAL. El codi té la forma
  prefix + 4 xifres + `_` + nivell. Els decrets del BOE fins a mitjan 2025 escriuen `UC` (`UC0493_3`);
  les fitxes de todofp i els decrets des del desembre del 2025 escriuen `ECP` (`ECP0493_3`, «estàndard
  de competència professional»). Molts números surten amb tots dos prefixos, però **no hem llegit cap
  norma que digui que són el mateix codi**: és una observació, no un fet establert (veure la decisió 1).
- El cercador principal no troba res per codi d'UC. El 2026-11-27, cercar `UC0493_3` no tornava res.
- La cerca és al navegador. `filteredRecords` a `frontend/index.html` (~línia 3150) només mira
  `_normDen` i `_normCod`. `/api/ofertes` serveix `ofertes.json` tal qual (`backend/app.py`,
  `get_ofertes`), i aquest fitxer no porta cap codi d'UC.
- Investigació prèvia (pas 0, fet el 2026-11-27): `plans/outputs/investigacio_uc_pla_nou.md`. **Llegir-la
  abans de començar.**
- On són els codis (`backend/data/`, fora del git; per cercar-hi cal `rg -uu`, i buscar `UC\d{4}` sol
  no troba el pla nou):

  | Què | Fitxer | Forma |
  |---|---|---|
  | C del pla antic | `bc_loe.json` | `{codi_certificat: ["UC0491_3", …]}`; la clau és el `ref` del registre |
  | B del pla nou i del pla antic | `b_contingut.json` (pla 068) | `{codi_b: {ecp: [{codigo: "ECP0493_3", text}], ra: […]}}` |
  | Cicles D | `d_uc_corr.json` (pla 091) | per `ref`: files `convalida`, `acredita` i `convalida_anterior` (derogades) amb camp `uc` |
  | C del pla nou | **encara no es desa** | la fitxa de todofp del C porta la secció «Estándares de competencia»; `bc_lomloe_scraper` ja baixa aquesta fitxa cada setmana |

## Decisions del propietari (2026-11-27)

1. **Zero invents o inferències: un codi només es mostra tal com l'hem vist escrit en una font oficial.**
   (Substitueix la decisió anterior de mostrar sempre «UC0493_3 (ECP0493_3)».)
   - Cada resultat mostra el codi amb el prefix que porta **la seva pròpia font**: `UC…` per als C del
     pla antic i els cicles D (decrets del BOE), `ECP…` per als B i els C del pla nou (fitxes de todofp).
   - No es construeix mai un codi canviant-li el prefix. `ECP2596_2` no es mostra mai com a «UC2596_2».
   - La cerca casa `UC####_n` amb `ECP####_n` **només** quan les dues formes són a l'índex, és a dir,
     quan totes dues s'han vist escrites. Si algú cerca una forma que no hem vist mai (`UC2596_2`), no
     surt res per aquesta via.
   - Dades del 2026-11-27: 1.918 codis vistos amb tots dos prefixos, 99 només com a `ECP` i 286 només
     com a `UC`. Dels 1.115 on es poden comparar els títols del decret i de la fitxa, 724 són idèntics
     i 391 tenen una altra redacció: no es pot afirmar que siguin «el mateix text».
2. **Els Graus A no surten** en cercar una UC. Des del B ja s'hi arriba.
3. **Els C del pla nou es llegeixen de la fitxa de todofp**, no dels decrets del BOE ni sumant els dels
   seus B (la suma només coincideix amb el decret en 257 de 400).

## Convencions

- Codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA). Text d'interfície
  en català i castellà a `frontend/i18n.js`, sense literals dins `x-text`. Els `x-if` porten una sola
  arrel.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`. En tocar `search-tools.js`,
  pujar el seu `?v=`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (935 verds el 2026-11-27). Frontend: `node scripts/test_search_tools.js` des de `fp-cercador/`.
- Els tests no han d'escriure mai a `backend/data/`: fitxers de prova en directoris temporals.
- Cap dependència nova. No desplegar sense l'aprovació del propietari.

## Què s'ha de fer

1. **Estàndards dels C del pla nou (scraper).** A `backend/scrapers/bc_lomloe_scraper.py`, llegir de la
   mateixa fitxa que ja es baixa la secció «Estándares de competencia» (elements «( ECP####_n ) text»;
   `b_contingut_scraper.parse_b_ficha` ja fa aquesta lectura per als B i es pot reaprofitar) i desar
   `backend/data/c_ecp.json`: `{codi_c: [{codigo, text}]}`. S'escriu al mateix punt de `pipeline.py` on
   s'escriuen `bc_lomloe.json` i `c_modulos.json`, amb el mateix tractament d'errors (no fatal). Cap
   petició nova a todofp. Afegir `c_ecp.json` al `.gitignore` si no hi entra pel patró existent.
2. **Índex codi → graus (backend).** `GET /api/uc-index` retorna, per **codi literal tal com l'escriu la
   font** (amb el seu prefix), els `ref` que el porten i quins venen només d'una taula derogada:
   `{"UC0493_3": {"refs": ["IFCD0210", "informatica-comunicaciones~des-aplicaciones-web", …], "derogats": [...]},
   "ECP0493_3": {"refs": ["MF0493_3", "IFC_B_0376", "IFC_B_0614", …], "derogats": []}}`.
   Cap codi es normalitza ni es reescriu en construir l'índex.
   - Fonts: `bc_loe.json` (C antic), `b_contingut.json` camp `ecp` (B nou i antic), `c_ecp.json` (C nou)
     i `d_uc_corr.json` (D: `convalida` i `acredita`; `convalida_anterior` va a `derogats` quan el `ref`
     no surt també per una taula vigent).
   - Només entren `ref` que existeixen a `ofertes.json`. Els Graus A no hi entren.
   - Memòria cau per `mtime` dels fitxers, com `get_ofertes`. Un fitxer que falta o és invàlid s'ignora
     amb un avís al registre; sense cap fitxer, l'índex és `{}`.
   - No es toca `/api/ofertes`, per no engreixar la càrrega inicial.
3. **Cerca (frontend).** Quan la cerca normalitzada té forma de codi (`/^(uc|ecp) ?\d{4}(_\d)?$/`:
   `uc0493`, `UC0493_3`, `ecp0493_3`, `uc 0493`), es carrega `/api/uc-index` una sola vegada (mandrós) i
   els registres els `ref` dels quals hi surten també coincideixen. Es busquen les claus de l'índex amb
   el prefix escrit; la forma amb l'altre prefix s'hi afegeix només si **totes dues** claus existeixen a
   l'índex. Sense nivell casa amb qualsevol nivell d'aquell prefix, amb la mateixa regla. Mentre
   l'índex es carrega no es mostra «Cap resultat». «Volies dir…» no ha de proposar res
   per a un codi d'UC. El reconeixement del codi va a `search-tools.js` com a funció pura, amb proves.
   Si l'índex no es pot carregar, la cerca es comporta com ara.
4. **Per què surt.** A la fila d'un resultat que surt per aquest camí i no pel nom ni pel codi, una nota
   curta amb el codi **tal com l'escriu la font d'aquell resultat**: «Coincideix per la unitat de
   competència UC0493_3» en un cicle D o un C del pla antic; «Coincideix per l'estàndard de competència
   ECP0493_3» en un B o un C del pla nou. Mai tots dos junts ni una forma deduïda. Si el `ref` és a
   `derogats`, la nota ho ha de dir («taula de convalidació derogada»).
5. **Fer-ho constar** (petició del propietari). Textos en català i castellà:
   - Camp de cerca: que digui que també es pot cercar per unitat de competència. Si no hi cap al
     placeholder a 375 px, es manté el placeholder i s'hi posa una línia d'ajuda a sota.
   - `per-que-grausfp.html`: un `feature-item` nou, «Cerca per unitat de competència», amb l'exemple
     `UC0493_3`. Sobre els dos prefixos, el text només pot dir el que s'ha observat: els decrets del
     BOE escriuen `UC…` i les fitxes del ministeri escriuen `ECP…`, sovint amb el mateix número. **No**
     pot dir que són «el mateix codi» ni que un substitueix l'altre, tret que abans es trobi la norma
     que ho estableix i es citi. Buscar-la és part d'aquest pas; si no es troba, es deixa el text
     descriptiu.
   - `com-funciona.html`, secció `#cerca`: una frase que digui que es pot cercar per codi d'UC.
   - `fonts.html`: d'on surten els estàndards (fitxes de todofp per als B i C, decrets per als cicles) i
     l'avís que la fitxa d'un C pot no coincidir amb el seu decret (2 de 11 a la mostra del pas 0:
     `HOT_C_001_4B` i `AFD_C_006_4B`).
   - Les xifres que s'hi posin han de sortir de les dades reals del moment.

## Tests

- Lectura de la secció d'estàndards d'una fitxa de C (HTML de prova): codis i textos, fitxa sense secció
  → llista buida.
- `GET /api/uc-index` amb fitxers de prova: cada font sota el seu codi literal (`UC0493_3` i
  `ECP0493_3` són dues claus diferents), cap clau que no surti escrita en un fitxer d'entrada, `ref`
  que només ve d'una taula derogada marcat a `derogats`, `ref` inexistent i Graus A descartats, sense
  fitxers → `{}`, memòria cau invalidada en canviar un `mtime`.
- `search-tools.js`: reconeixement dels formats (dos prefixos, amb i sense nivell, minúscules, espai),
  no-reconeixement de codis de certificat (`IFCD0210`, `MF0493_3`) ni de paraules normals, i la regla de
  creuament: amb un índex que té `UC0493_3` i `ECP0493_3`, qualsevol de les dues cerques torna la unió;
  amb un índex que només té `ECP2596_2`, cercar `UC2596_2` no torna res i cercar `ECP2596_2` sí.
- Navegador (ca i es, 1280 i 375 px): `UC0493_3` i `ecp0493_3` donen els mateixos resultats (amb les
  dades del 2026-11-27: `IFCD0210`, `MF0493_3`, `IFC_B_0376`, `IFC_B_0614` i els dos cicles D; els C nous
  `IFC_C_003_5B` i `IFC_C_007_5B` quan hi hagi `c_ecp.json`). Cada fila mostra el codi amb el prefix de
  la seva font. `UC2596_2` no torna res. El text d'ajuda.

## En desplegar

- `c_ecp.json` no existirà fins que corri el scraper. O bé s'espera al refresc setmanal següent, o bé
  es llança un refresc manual des del panell (uns 94 min; **mai** durant un altre refresc). Fins
  llavors, cercar una UC no torna els C del pla nou; la resta funciona.
- Cal reiniciar el servei (ruta nova). Comprovar abans `/api/refresh-status`.

## Decisions preses en escriure el pla (revisables)

- Endpoint a part i càrrega mandrosa, en lloc d'afegir les UC a `/api/ofertes`.
- S'inclouen les UC de les taules derogades dels cicles, perquè qui té un certificat antic ha de trobar
  els cicles on encara li compta. La nota ho indica.
- Els B del pla antic es llegeixen del camp `ecp` i no es dedueixen del codi `MF…`: en 172 de 1.938 el
  número és un altre.

## Fora d'abast

- Graus A (decisió del propietari).
- Codis de qualificació professional (`IFC154_3`) i cerca pel codi de mòdul formatiu.
- Especialitats del SEPE.
- Mostrar els estàndards d'un C del pla nou a la seva fitxa o a l'itinerari: aquest pla només els fa
  servir per a la cerca.
