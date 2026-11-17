# Pla 092 — Correspondència certificat ↔ mòduls de cicle a la web

Origen: correus d'un usuari (docent d'FPO, 2026-11): que els alumnes que van fent certificats puguin
veure quins mòduls d'un cicle ja tenen i què els falta. Anàlisi del 2026-11-17. Les decisions de
disseny d'aquest pla són del redactor i es poden discutir abans d'executar-lo.
Executable per un agent sense context, en una sessió nova. Depèn de: 090 i 091. Pla mitjà.

## Què fa

Mostra la correspondència oficial del pla 091 a tres llocs: l'itinerari d'un certificat LOE, la fitxa
d'un cicle, i «Què em falta?», que passa a calcular també amb certificats antics.

## Fets verificats (2026-11-17, no repetir)

- `GET /api/itinerari?grado=C&codigo=<CP LOE>` torna `ciclos_d` (de `ciclos_fp.json`: denominació,
  família, `ficha_url`) i `parent_b_loe`. Per als C LOMLOE torna `ciclos_d` amb `shared` i `total`
  (pla 058) i `modulos_c` (pla 078).
- `backend/gap.py::compute_gap`: els certificats `plan_antiguo` es desen a `old_c` i només generen
  `relacionats` (cicles de `ciclos_fp.json`, sense càlcul). `frontend/que-em-falta.html` els pinta
  amb `related()` (línia ~559).
- La regla de càlcul (una UC convalida un mòdul només si totes les UC de la seva fila hi són) i l'API
  `/api/correspondencia` venen del pla 091.
- Els mòduls B LOE del catàleg són `MF####_N` i la seva UC és `UC####_N` (mateix número i nivell).
- RD 659/2023, art. 126: el Proyecto intermodular i la formació en empresa no es convaliden mai; ja ho
  recull `gap.py` (`_NEVER_MATCH_PREFIXES`).

## Disseny

- **Itinerari d'un certificat LOE** (`itinerari.html`, panell de cicles): per cada cicle amb
  correspondència, «convalida N de M mòduls», desplegable amb els mòduls convalidats (i per quines UC)
  i els que queden. Els cicles que només venen de `ciclos_fp.json` es mantenen, marcats com a relació
  sense detall de mòduls. Mateix aspecte que el panell dels C LOMLOE (pla 058) per no inventar un
  patró nou.
- **Fitxa del cicle** (itinerari d'un D i pàgina pública `/grau/<ref>`): taula «Mòdul → UC que
  l'acrediten → certificats que porten aquestes UC», amb enllaç a cada certificat.
- **«Què em falta?»**: un certificat LOE aporta les seves UC (de `bc_loe.json`); un mòdul B LOE aporta
  la seva. Amb això es calculen els cicles com ja es fa amb els LOMLOE, i els `relacionats` queden
  només per als cicles sense taula. Un cicle acabat també ha de poder dir quines UC acredita
  (Annex V B) i, per tant, quins certificats LOE té a prop: valorar si entra aquí o es deixa per a un
  pla posterior.
- Sempre visible la font: «Segons l'annex V del <reial decret>», amb enllaç al BOE, i un avís curt que
  la convalidació la resol l'administració educativa, no la web.
- Textos en català i castellà (`i18n.js`).

## Fases

1. Backend: ampliar `/api/itinerari` per a C LOE i `compute_gap` amb les UC, amb tests
   (`tests/test_gap.py`, `tests/test_api.py`). Cas de referència: ELEE0109 contra Instalaciones
   Eléctricas y Automáticas (vegeu el pla 091).
2. Itinerari del certificat LOE.
3. Fitxa del cicle (itinerari i `grau_page.py`).
4. «Què em falta?».
5. Textos, `?v=` i `I18N_VERSION`.
6. Verificació al navegador, ca i es, 1280 i 375 px, teclat.

## STOP — atura't i pregunta

- Si la taula del cicle de referència ha canviat amb el RD 499/2024 i el cas de prova ja no val.
- Abans de canviar l'ordre o el criteri dels objectius que ja mostra «Què em falta?».
- No desplegar sense aprovació explícita.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
