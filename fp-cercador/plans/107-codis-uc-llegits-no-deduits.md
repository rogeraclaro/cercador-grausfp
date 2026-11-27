# Pla 107 — Que la web només mostri codis UC llegits, no deduïts

Prioritat P1 (correcció del que ja és en producció) · Mida M–L · Depèn de: 090–093 (el que corregeix) ·
Origen: comprovació del 2026-11-28, arran del pla 106.
Executable per un agent sense context.

## Context

- **Regla del propietari (2026-11-27/28): «0 invents o inferències».** Un codi oficial només es mostra
  tal com l'hem vist escrit en una font oficial, amb el prefix d'aquella font. No es construeix mai un
  codi a partir d'un altre.
- **El problema.** `backend/data/bc_loe.json` diu quines «UC» té cada certificat del pla antic, però
  **cap dels seus codis s'ha llegit com a UC**: són les capçaleres «Código: MF####_N» dels annexos amb
  el prefix canviat (`scripts/generate_bc_loe.py:85`, `as_uc = lambda mf: 'UC' + mf[2:]`). I el codi
  en producció torna a fer el mateix canvi en marxa a `backend/uc_corr.py:43`,
  `backend/itinerary.py:62` i `backend/export_estructura.py:49` i `:64`.
- **Mesures del 2026-11-28** (dades locals; informe a `plans/outputs/investigacio_uc_pla_nou.md`):

  | Què | Quant |
  |---|---|
  | Parells certificat–«UC» a `bc_loe.json` (580 certificats) | 2.328, tots deduïts |
  | Confirmats per una lectura literal al mateix annex | 1.793 |
  | No llegits enlloc com a UC | 535 |
  | — l'annex escriu la UC en altres mòduls, però no en aquest | 276 |
  | — l'annex no porta cap frase d'UC | 177 |
  | — annex escanejat o no llegit | 82 |
  | Certificats amb alguna UC llegida / sense cap | 503 / 77 |
  | Mòduls on la UC escrita té un altre número que el MF | 28 |
  | Parells on la fitxa de todofp del mòdul escriu un `ECP` amb un altre número | 201 |

- **On sí que hi ha lectures literals:**
  - `c_loe_estructura.json` (pla 093), camp `uc` de cada MF: surt de la frase «Asociado a la Unidad de
    Competencia: UC…» de l'annex (`scripts/generate_c_loe_estructura.py:45` i `:63-64`). 1.822 mòduls
    de 503 certificats. Reserva: `UC820_2` es desa com a `UC0820_2` (`zfill`), sense deixar-ne rastre.
  - `d_uc_corr.json` (pla 091): taules dels decrets dels cicles. Literal en 1.484 de 1.488 codis; els
    altres 4 són errades d'impremta del BOE corregides (`UC736_2`, `UC738_2`, `UC783_3`, `UC 1441_3`).
  - `b_contingut.json` (pla 068), camp `ecp`: fitxa de todofp de cada Grau B, amb prefix `ECP`.
- **`bc_loe.json` no és fals, està mal etiquetat.** El que conté de debò és la llista de **mòduls
  formatius** de cada certificat (capçaleres MF de l'annex en 516 certificats; llista del SEPE en 59).
  Com a relació certificat ↔ mòdul B del pla antic és bona i es pot continuar fent servir.

## On surt avui un codi UC a la web (comprovat al codi el 2026-11-28)

**A. Codis deduïts que es mostren o s'exporten com a UC** (incompleixen la regla):

| On | Codi | Què veu l'usuari |
|---|---|---|
| `/grau/<ref>` d'un certificat del pla antic | `app.py:3011-3014` → `grau_page.py:376-379` | Secció «Unidades de competencia» amb `UC####_N` de `bc_loe.json`. El nom que l'acompanya és el del **mòdul** B (`b_by_uc`), no el de la UC |
| Comparador | `compare.py:30` → `compara.html:410` | Fila «Unitats de competència» amb la mateixa llista |
| CSV de certificats | `export_estructura.py:64` | Columna «UC»: la llegida, i si no n'hi ha, `'UC' + codi MF` |
| CSV de certificats sense estructura (24) | `export_estructura.py:49` | Columna «UC» de `bc_loe.json` i columna «Codi MF» refeta amb `'MF' + uc[2:]` |
| `GET /api/correspondencia?cp=` | `app.py:1593-1597` | Camp `cp.uc` (API pública; cap pàgina el pinta) |

**B. Codis literals del BOE, però amb una afirmació que es basa en la deducció.** Les UC que es veuen
(`row.uc`, `row.falten`) són les de la taula del decret del cicle. El que és deduït és **quin
certificat o mòdul «porta» aquelles UC**, i d'aquí surten afirmacions de convalidació:

| On | Codi | Afirmació |
|---|---|---|
| Itinerari d'un certificat antic | `app.py:1504-1520`, `itinerari.html:2008-2050` | «Convalida N de M mòduls», «per UC…», «falta UC…» |
| Arestes C→D del graf | `app.py:2786-2800` (`_get_c_loe_corr`), `itinerary_graph.py:157-162` | Etiqueta de l'aresta i línia vermella de «derogada» |
| Itinerari d'un cicle i `/grau/<ref>` d'un cicle | `app.py:1522-1532`, `itinerari.html:1324-1328` i `:2071-2075`, `grau_page.py:354-357` | «Certificats del pla antic que les inclouen totes» |
| CSV de cicles | `export_estructura.py` (`cycle_rows`) | Columna «Certificats LOE del grup» |
| «Què em falta?» | `app.py:3673`, `uc_corr.py:31-44`, `que-em-falta.html:795-798` | «Convalidacions oficials» a partir dels certificats i dels mòduls `MF…` que algú té |

Totes passen per dues funcions: `_get_loe_ucs()` (`app.py:1496-1501`: `bc_loe.json` més
`uc_corr_overrides.json`) i `uc_corr.held_ucs()` (`uc_corr.py:43`, mòdul `MF…` → `'UC' + …`).

**C. Ús intern del número com a clau, que no es mostra com a UC** (no cal tocar-lo): relació
certificat ↔ mòdul B a `app.py:2702-2714` i `:2746-2748`, `itinerary_graph.py:141-146`,
`itinerary.py:60-63` (`b_by_uc`), `centres_inherit.py:36` i `centres_watch_service.py`. El que hi surt
són codis `MF…`, que sí que són escrits.

**D. Ja és literal** (fora d'abast): la nota `uc_sense_b` dels C del pla nou (`index.html:5346-5348`,
verificada a mà als decrets al pla 080) i els `ECP` de les fitxes dels B.

## Decisions del propietari que ja valen

1. Un codi es mostra només tal com surt a la seva font, amb el prefix d'aquella font.
2. No es construeix `UC…` a partir de `MF…`, ni `UC…` a partir d'`ECP…`, ni a l'inrevés.
3. Una errada d'impremta **evident** de la font (un zero que falta, un espai de més) es mostra
   corregida, amb una anotació visible que digui què hi posa la font. Un número diferent no és una
   errada evident.

## Convencions

- Codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA). Text d'interfície
  en català i castellà a `frontend/i18n.js`, sense literals dins `x-text`. Els `x-if` porten una sola
  arrel. Les pàgines `/grau/<ref>` es generen en castellà a `backend/grau_page.py`.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (935 verds el 2026-11-27). Els tests no escriuen mai a `backend/data/`.
- `backend/data/` és fora del git: per cercar-hi cal `rg -uu`. Abans de regenerar un fitxer, fer-ne
  còpia (`*.bak-pre107`).
- Cap dependència nova. No desplegar sense l'aprovació del propietari.

## Què s'ha de fer

0. **Auditoria prèvia, sense tocar producció.** Script `scripts/audit_uc_literal.py` que escriu
   `plans/outputs/audit_uc_literal.md` amb, per a les dades actuals:
   - per certificat: mòduls MF, UC llegida de cada un, i si no n'hi ha, per què;
   - la llista dels 28 mòduls on la UC escrita té un altre número que el MF;
   - **l'efecte del canvi**: quantes arestes C→D amb convalidació hi ha ara i quantes en quedarien
     amb només UC llegides, amb la llista de les que canvien (certificat, cicle, mòduls abans i
     després).
   Aturar-se aquí i presentar l'informe al propietari: és la base de les decisions obertes 1–4.
1. **Guardar la forma impresa.** A `scripts/generate_c_loe_estructura.py`, quan el `zfill` canvia el
   codi llegit, desar també `uc_font` amb la forma tal com surt a l'annex. Regenerar
   `c_loe_estructura.json` (necessita `pdftotext` i xarxa; 580 annexos) i comprovar que, fora
   d'aquest camp nou, el fitxer no canvia.
2. **Registre d'errades evidents.** `backend/uc_errades_font.json` (versionat): codi mostrat, codi tal
   com surt a la font, i document. Hi van les 4 del BOE i les que surtin del pas 1. El mateix fitxer i
   format que preveu el pla 106: si ja existeix, reaprofitar-lo. `fonts.html#errors` en porta la
   llista (ca i es) i un test comprova que pàgina i fitxer coincideixen, com
   `tests/test_c_horas_overrides.py`.
3. **Una sola font de «UC llegides» al backend.** Funció nova (p. ex. `_get_loe_ucs_literal()`):
   `{certificat: [{mf, uc}]}` a partir del camp `uc` de `c_loe_estructura.json`. `_get_loe_ucs()` passa
   a tornar només UC llegides. `uc_corr_overrides.json` es revisa entrada per entrada: es conserva
   només el codi que es pugui assenyalar escrit en un annex o un decret, amb la referència al costat.
4. **Bloc A (el que es mostra):**
   - `/grau/<ref>` i comparador: la secció passa a llistar els **mòduls formatius** del certificat
     (codi `MF…` i nom, que són escrits) i, al costat de cada un, la UC **només si s'ha llegit**. El
     títol deixa de dir només «Unidades de competencia». Un mòdul sense UC llegida surt sense UC.
   - CSV de certificats: la columna «UC» porta només el camp `uc` llegit. Se suprimeixen els dos
     reemplaçaments (`export_estructura.py:49` i `:64`). Sense estructura, la fila porta el codi MF de
     `bc_loe.json` **només** si aquell `MF…` existeix com a Grau B al catàleg, i la UC buida.
   - `/api/correspondencia?cp=`: `cp.uc` només amb UC llegides.
5. **Bloc B (les afirmacions de convalidació):** `_corr_cycles_for`, `_corr_certs_by_uc`,
   `_get_c_loe_corr` i «Què em falta?» treballen amb les UC llegides. Per a un mòdul `MF…` que algú
   té, `held_ucs` fa servir la UC llegida a l'annex per a aquell mòdul; si diferents annexos n'hi
   donen de diferents, o cap, el mòdul no aporta cap UC. Es treu `'UC' + code[2:]` de `uc_corr.py:43`.
   El que es fa amb els 535 parells sense UC llegida depèn de la decisió oberta 1.
6. **`bc_loe.json` es queda com està**, com a relació certificat ↔ mòduls (bloc C). No es reanomena
   ni el fitxer ni les claus: només s'actualitzen els comentaris i docstrings que diuen que conté UC
   (`app.py:104`, `itinerary_graph.py:14`, `itinerary.py:62-63`, capçalera de `generate_bc_loe.py`).
7. **Textos.** `fonts.html` explica d'on surt cada codi (annex, decret o fitxa) i que un certificat pot
   no tenir la UC escrita a l'annex. Revisar `cmp.row.uc`, `export.structure.title` i el text de la
   secció de `/grau/<ref>` (ca i es) perquè no prometin UC on només hi ha mòduls.

## Tests

- `_get_loe_ucs_literal()`: certificat amb UC a tots els mòduls, amb UC només en alguns, sense cap,
  sense estructura; cap codi que no sigui al fitxer d'entrada.
- Cap test ni cap funció de producció no pot construir un codi amb `'UC' +` ni `'MF' +`: un test que
  ho cerqui a `backend/*.py` (fora de `tests/` i dels generadors) i falli si en troba.
- `/grau/<ref>` i comparador: mòdul amb UC llegida, mòdul sense, certificat sense estructura.
- CSV de certificats: columna «UC» buida quan no s'ha llegit; codi MF no inventat.
- `held_ucs`: mòdul amb una sola UC llegida, amb dues de diferents, sense cap.
- `/api/correspondencia`, `/api/itinerari/complet` i `/api/que-em-falta`: una convalidació que es
  manté (UC llegida) i una que desapareix (UC només deduïda).
- Errades: pàgina i `uc_errades_font.json` coincideixen.
- Actualitzar els tests existents que donen per bona la deducció: `test_uc_corr.py`,
  `test_correspondencia_api.py`, `test_export_estructura_api.py`, `test_grau_page.py`,
  `test_compare.py`, `test_itinerari_complet.py`.
- Navegador (ca i es, 1280 i 375 px): `/grau/IFCD0210`; itinerari d'IFCD0210 i d'ELEE0109 (taula
  derogada); un certificat sense cap UC llegida (p. ex. AGAO0108); un cicle amb taula
  (`informatica-comunicaciones~des-aplicaciones-web`); «Què em falta?» amb ELEE0109 i MF0836_2; el CSV
  d'un certificat amb UC llegides i d'un sense.

## En desplegar

- Regenerar `c_loe_estructura.json` en local, copiar-lo al VPS amb còpia de l'anterior, `git pull` i
  reinici. **Mai** durant un refresc (`curl localhost:8033/api/refresh-status`).
- Comprovar a producció els mateixos casos del navegador.

## Decisions obertes per al propietari

1. **Els 535 parells sense UC llegida (77 certificats sense cap).** Amb la regla estricta deixen de
   donar convalidacions. Alternatives: (a) estricte: no s'afirma res (recomanat mentre no hi hagi
   una altra lectura); (b) llegir la fitxa de todofp del certificat, que escriu `ECP…`; però les
   taules dels decrets escriuen `UC…`, i casar-los és creuar prefixos, que el pla 106 només admet
   quan totes dues formes s'han vist escrites; (c) mantenir la deducció avisant-ho a la pantalla
   («deduït del codi del mòdul»), que contradiu la regla.
2. **Els 28 mòduls on la UC escrita té un altre número que el MF.** Algunes són errades de l'annex
   (`UC7033_1` al mòdul `MF1333_1`), però no «evidents» segons la decisió 3. Proposta: mostrar el que
   hi ha escrit, llistar-les a `fonts.html#errors` com a discrepàncies i no fer-les servir per
   convalidar. El pla 091 en va revisar 16 pel nom (13 errades de l'annex, 3 UC diferents de debò).
3. **Mòduls `MF…` a «Què em falta?»**: UC llegida a l'annex (proposta del pas 5), o cap convalidació
   a partir d'un mòdul solt.
4. **Acceptar la baixada de convalidacions** que mostri l'informe del pas 0 abans de desplegar.
5. **Com es titula la secció** de `/grau/<ref>` i del comparador quan barreja mòduls i UC.

## Relació amb el pla 106

- El 106 (cerca per UC) ja preveu no fer servir `bc_loe.json` i llegir `c_loe_estructura.json`. El 107
  crea la funció de «UC llegides» i el registre d'errades que el 106 necessita.
- **Ordre recomanat: 107 abans que el 106.** El 107 corregeix pàgines que ja són públiques; el 106
  és una funció nova i hi pot reaprofitar la funció i el fitxer d'errades.

## Fora d'abast

- La cerca per UC (pla 106) i la lectura dels estàndards dels C del pla nou.
- Les relacions certificat ↔ mòdul B i l'herència de centres (bloc C), que no mostren UC.
- Buscar la norma que relaciona `UC` i `ECP` (és un pas del pla 106).
- Els codis de mòdul de `bc_loe.json` que venen de la llista del SEPE amb el nivell suposat: només es
  deixen de mostrar si no existeixen al catàleg (pas 4); revisar-los a fons és una altra feina.
