# Pla 106 — Cerca per unitat de competència (codis UC de l'INCUAL)

Prioritat P2 · Mida S · Depèn de: 090, 091 (dades ja fetes) · Origen: pregunta del propietari del 2026-11-27.
Executable per un agent sense context.

## Context

- Una **unitat de competència** (UC) és la peça mínima que acredita l'INCUAL. El codi té la forma
  `UC` + 4 xifres + `_` + nivell (`UC0493_3`). Diverses UC formen una qualificació professional.
- Ja tenim les UC a les dades, però **el cercador principal no les troba**. El 2026-11-27, cercar
  `UC0493_3` no tornava res. Aquesta UC és d'IFCD0210 (certificat del pla antic) i convalida mòduls de
  dos cicles D: `informatica-comunicaciones~admin-sist-informaticos-red` i
  `informatica-comunicaciones~des-aplicaciones-web`. Totes dues coses ja surten a l'itinerari, a
  `/grau/<ref>` i a l'exportació CSV.
- La cerca és al navegador. `filteredRecords` a `frontend/index.html` (~línia 3150) només mira
  `_normDen` i `_normCod`. `/api/ofertes` serveix `ofertes.json` tal qual (`backend/app.py`,
  `get_ofertes`), i aquest fitxer no porta cap codi d'UC.
- On són les UC (`backend/data/`, fora del git; per cercar-hi cal `rg -uu`):
  - `bc_loe.json`: `{codi_certificat: [UC…]}`, amb 1.887 UC diferents. La clau coincideix amb el
    `ref`/`codigo` dels registres C del pla antic (`IFCD0210`).
  - `d_uc_corr.json`: per `ref` de cicle D, files `convalida` / `acredita` amb camp `uc`, més
    `convalida_anterior` (taules derogades, pla 091). Hi ha 1.477 UC diferents.
  - `c_loe_estructura.json`: estructura MF/UF de cada certificat, amb el camp `uc`. És redundant amb
    `bc_loe.json` per a la cerca.
- Els C i B del pla nou (LOMLOE: `ADG_C_001_3B`, `ADG_B_3001`) no tenen codis d'UC a les dades. Queden
  fora d'abast (veure al final).

## Convencions

- Codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA). Text d'interfície
  en català i castellà a `frontend/i18n.js`, sense literals dins `x-text`. Els `x-if` porten una sola
  arrel.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`.
  Frontend: `node scripts/test_search_tools.js` des de `fp-cercador/`.
- Cap dependència nova. No desplegar sense l'aprovació del propietari.

## Què s'ha de fer

1. **Índex UC → graus (backend).** `GET /api/uc-index` retorna `{"UC0493_3": ["IFCD0210",
   "informatica-comunicaciones~admin-sist-informaticos-red", …], …}`, construït des de `bc_loe.json`
   (clau = `ref` del certificat) i `d_uc_corr.json` (UC de `convalida`, `acredita` i
   `convalida_anterior`). Es manté a la memòria cau per `mtime` dels dos fitxers, com `get_ofertes`. Els
   fitxers que falten no fan fallar res: si no n'hi ha cap, l'índex surt buit. Només entren `ref` que
   existeixen a `ofertes.json`. No es toca `/api/ofertes`, per no engreixar la càrrega inicial.
2. **Cerca (frontend).** Quan la cerca normalitzada té forma d'UC (`/^uc ?\d{4}(_\d)?$/`, és a dir,
   `uc0493`, `UC0493_3` o `uc 0493`), es carrega `/api/uc-index` una sola vegada (mandrós) i els
   registres els `ref` dels quals hi surten també coincideixen. Sense nivell (`uc0493`) casa amb
   qualsevol nivell. Mentre l'índex es carrega no es mostra «Cap resultat»: es reutilitza l'estat de
   càrrega que ja hi hagi. «Volies dir…» (`search-tools.js`) no ha de proposar res per a un codi d'UC.
   La lògica de reconeixement va a `search-tools.js` com a funció pura, amb proves.
3. **Per què surt.** A la fila d'un resultat que surt per UC i no pel nom, cal una nota curta: «Coincideix
   per la unitat de competència UC0493_3». Si el vincle ve d'una taula derogada, la nota ho ha de dir.
4. **Fer-ho constar** (petició del propietari):
   - Text d'ajuda del cercador: el placeholder `index.search.placeholder` ha de passar a dir que també
     es pot cercar per unitat de competència. Si no hi cap a 375 px, es manté el placeholder i es posa
     una línia d'ajuda sota el camp.
   - `per-que-grausfp.html`: un `feature-item` nou, «Cerca per unitat de competència», amb un exemple
     (`UC0493_3` → IFCD0210 i els dos cicles D).
   - `com-funciona.html`, secció `#cerca` (`com.demo.p1`, o un paràgraf nou): una frase que expliqui
     que es pot cercar per codi d'UC.
   - Textos en català i castellà. Les xifres que s'hi posin han de sortir de les dades reals del moment.

## Tests

- `GET /api/uc-index` amb fitxers de prova: unió de certificat i cicle, UC de la taula derogada
  inclosa, `ref` inexistent descartat, sense fitxers → `{}`, memòria cau invalidada en canviar el
  `mtime`.
- `search-tools.js`: reconeixement de formats d'UC (amb i sense nivell, minúscules, espai) i
  no-reconeixement de codis de certificat (`IFCD0210`) ni de paraules normals.
- Navegador (ca i es, 1280 i 375 px): `UC0493_3` → IFCD0210 i els dos cicles; `uc0493` → els mateixos;
  la nota «per què surt» i el text d'ajuda.

## Decisions preses en escriure el pla (revisables)

- Endpoint a part i càrrega mandrosa, en lloc d'afegir les UC a `/api/ofertes`.
- S'inclouen les UC de les taules derogades, perquè qui té un certificat antic ha de trobar els cicles
  on encara li compta. La nota ho indica.
- Només codis d'UC, no de MF (`MF0493_3`) ni de qualificació (`IFC154_3`).

## Fora d'abast

- **Graus B i C del pla nou (LOMLOE).** Cada Grau B del pla nou correspon a un estàndard de competència,
  però el codi no és a les nostres dades. Caldria un spike per veure si les fitxes de todofp o els
  decrets el donen.
- Codis de qualificació professional i de mòdul formatiu.
- Especialitats del SEPE.
