# Pla 083 — «Què em falta?»: de què tens a què pots arribar

Origen: auditoria 2026-11-14, idea 1 de 9; disseny validat pel propietari el mateix dia.
Executable per un agent sense context, en una sessió nova. Depèn de: 058 (C→D per mòduls),
076 (`ref` estable), 078 (`c_modulos.json`), tots DONE.

## Què fa

L'usuari marca els Graus **B, C i D** que ja té. La pàgina li ensenya els Graus C i els cicles D
que té més a prop, amb el percentatge cobert i la llista exacta del que falta. És la promesa de
la LO 3/2022 (formació acumulable) que cap web oficial ensenya.

## Decisions del propietari (tancades, no reobrir)

| Tema | Decisió |
|---|---|
| Què declara l'usuari | Graus sencers B, C i D. **No** mòduls solts. |
| Accés | Obert, sense compte. Es desa al navegador; si hi ha sessió, també al compte. |
| Ubicació | Pàgina pròpia `que-em-falta.html` + botó «Ja el tinc» al cercador i a l'itinerari. |
| Maqueta | Dues columnes: esquerra «El que ja tinc», dreta «A prop teu» (apilades al mòbil). |

Fora d'aquesta versió: mòduls solts, Graus A i E com a objectiu, centres on cursar el que falta.

## Fets verificats (2026-11-14, no repetir)

- `bc_lomloe.json`: `{codi_C: [codi_B, …]}`, 400 C LOMLOE, 3,5 B de mitjana.
- `c_modulos.json`: `{codi_C: [{num, name}, …]}`, 400 de 400, 4,75 mòduls de mitjana.
- **El sufix del codi d'un B és el número del seu mòdul**: `ADG_B_3001` ↔ mòdul `3001`.
  Comprovat a les 1.386 parelles C→B, sense cap excepció. Regex ja existent:
  `cd_lomloe._B_NUM_RE`.
- `d_modulos.json`: `{str(id_registre): {modulos: [{num, name}], ensenanzaFP}}`, 195 cicles,
  16,4 mòduls de mitjana. **2.336 de 3.206 mòduls no porten `num`**: el creuament és per nom
  normalitzat (`cd_lomloe.normalize_module_name`), com ja fa `build_c_lomloe_to_d`.
- De mitjana, un 39 % dels mòduls d'un D existeixen en algun C; 75 cicles passen del 50 %;
  **cap** D queda cobert del tot només amb graus C (sempre falten mòduls comuns).
- `ciclos_fp.json` (només al VPS): `{codi_C_LOE: [{denominacion, familia, ficha_url}]}`, 588
  entrades, 338 amb algun cicle. No porta mòduls: no se'n pot calcular cap percentatge.
- Les claus de `d_modulos.json` són `id`, que es reassignen a cada refresc; per provar en local
  cal copiar `ofertes.json` i `d_modulos.json` **del mateix refresc** (vegeu `plans/ESTAT.md`).
- Catàleg: `_get_catalog()` a `backend/app.py` dona `records`, `by_ref`, `by_id`, `by_codigo`.
- Última migració: `012_oferta_ref.sql`. Versió de memòria cau: `I18N_VERSION` a
  `backend/grau_page.py` i `?v=` a totes les pàgines (ara `20261114c`).

## Com es calcula

Mòdul nou `backend/gap.py`, funció pura i sense Flask:

```python
def compute_gap(held_refs, records, bc_lomloe, c_modulos, d_modulos, ciclos_fp=None,
                limit=30) -> dict
```

1. **Expansió del que té.** De cada `ref` vàlid:
   - C LOMLOE → tots els seus B (`bc_lomloe`) i tots els seus mòduls (`c_modulos`).
   - B LOMLOE → el mòdul amb el número del seu sufix.
   - D → tots els seus mòduls (`d_modulos[str(id)]`).
   - C del pla antic → cap mòdul; es guarda per al pas 4.
   El resultat són tres conjunts: codis de B, números de mòdul i noms normalitzats de mòdul.
2. **Objectius C LOMLOE.** Per a cada C que l'usuari no té: `tens = B del C ∩ B que té`.
   Entra si `tens ≥ 1`. Progrés = `tens / total de B`. «Et falta» = els B restants, amb `ref`,
   codi i denominació (del catàleg).
3. **Objectius D.** Per a cada D que no té: un mòdul compta com a cobert si el seu `num` és
   als números o el seu nom normalitzat és als noms. Entra si `coberts ≥ 1`. «Et falta» = els
   mòduls restants (nom tal com ve).
   **Excepció PRL**: reutilitza `cd_lomloe._is_prl`; un mòdul de prevenció de riscos només
   compta si ve d'un D que l'usuari té, no d'un C (mateix criteri que el pla 078).
4. **C del pla antic.** Els cicles de `ciclos_fp[codi]` surten a part, a `relacionats`, sense
   percentatge, amb el text «comparteix unitats de competència».
5. **Ordre.** Per percentatge descendent, després per peces cobertes, després per denominació.
   Es talla a `limit`. Els objectius ja assolits (100 %) van primer, marcats `complet: true`.

Sortida:

```json
{"held": [{"ref", "grado", "codigo", "denominacion"}],
 "ignorats": ["ref-inexistent"],
 "objectius": [{"ref", "grado", "codigo", "denominacion", "familia", "nivel",
                "tens": 6, "total": 14, "percent": 43, "complet": false,
                "falta": [{"tipus": "modul", "nom": "…"} | {"tipus": "B", "ref", "codigo", "denominacion"}]}],
 "relacionats": [{"denominacion", "familia", "ficha_url", "via": "codi_C_LOE"}]}
```

## Fases

Cada fase acaba amb els tests verds i un commit (`feat(gap): …`, sense atribució d'IA).

### Fase 1 — Càlcul (`backend/gap.py` + `backend/tests/test_gap.py`)
Tests primer, amb catàlegs de 5–8 registres fets a mà. Casos mínims:
- un C dona els seus B i mòduls; un B sol dona un mòdul;
- un D objectiu compta mòduls per número i per nom (amb accents i «(GS)» diferents);
- el PRL d'un C no compta, el d'un D sí;
- un objectiu que l'usuari ja té no surt; un sense cap peça coberta no surt;
- `ref` desconegut va a `ignorats` i no peta; llista buida dona resultat buit;
- C del pla antic només produeix `relacionats`;
- ordre i `limit`.

### Fase 2 — API
- `POST /api/que-em-falta`, cos `{"refs": [...]}`, pública. Màxim 50 `ref`, cadascun `str` de
  ≤ 200 caràcters; si no, 400. 503 si el catàleg no es pot llegir (mateix patró que la resta).
- Carrega les dades amb els getters que ja existeixen (`_get_bc_lomloe`, `_get_c_modulos`,
  `_get_d_modulos`, `_get_catalog`); `ciclos_fp.json` amb memòria cau per mtime, opcional.
- Tests a `backend/tests/test_gap_api.py`, aïllant `DATA_PATH`, `BC_LOMLOE_PATH`,
  `C_MODULOS_PATH` i `D_MODULOS_PATH` amb `monkeypatch`.

### Fase 3 — Desat al compte
- Migració `013_user_held.sql`: `user_held(user_id, oferta_ref, created_at)`, clau primària
  `(user_id, oferta_ref)`, `ON DELETE CASCADE`.
- `GET /api/held` → `{"refs": [...]}`; `PUT /api/held` amb `{"refs": [...]}` substitueix la
  llista sencera (mateixos límits que la fase 2). 401 sense sessió. Afegir les rutes a
  `_set_auth_cors` si cal (mireu com ho fa `/api/favorites`).
- En esborrar un compte la llista ha de desaparèixer: comproveu el camí d'eliminació
  d'usuaris del panell d'admin.
- Tests a `backend/tests/test_held_api.py`: aïllament entre usuaris, límits, 401.

### Fase 4 — Pàgina `frontend/que-em-falta.html`
- Alpine 3 vendoritzat, `site.css`, barra superior, `auth.js`, `footer.js`, `feedback.js` i
  l'script d'analítica, igual que `observatori.html`. Cap llibreria nova.
- Estat: `held` (llista de `ref`), carregada de `localStorage['heldRefs']`; amb sessió, es
  fusiona amb `GET /api/held` (unió) i es desa amb `PUT` a cada canvi.
- Esquerra: llista del que té, amb ✕ per treure, i un cercador amb suggeriments sobre
  `/api/ofertes` filtrat a graus B, C i D (reutilitzeu `expandSearch`/normalització
  d'`index.html` copiant només el mínim; no extreure a un fitxer compartit en aquest pla).
- Dreta: targetes d'objectius amb barra de progrés, «N de M», llista «Et falta» plegable a
  partir de 5 elements, enllaç a `itinerari.html` i a `/grau/<ref>`. Secció «Relacionats»
  al final per als C del pla antic.
- Estats: buit (explica què fer, amb dos exemples clicables), carregant, error amb reintent,
  cap objectiu («encara no hi ha cap grau que comparteixi mòduls amb els teus»).
- Avís fix sota el títol: «Orientatiu: la convalidació la resol l'administració educativa.»
- Cada petició porta un comptador de seqüència: una resposta antiga no trepitja la nova
  (mateix patró que `runOcupSearch` a `index.html`).
- Accessibilitat: `role="progressbar"` amb `aria-valuenow`, botons amb nom, resultats en una
  regió `aria-live="polite"`.

### Fase 5 — Botó «Ja el tinc» i enllaços
- `index.html`: a la fila desplegada dels graus B, C i D, un botó commutable «Ja el tinc»
  (`aria-pressed`) al costat de «Compartir». Mateixa clau de `localStorage` i mateix `PUT`.
- `itinerari.html`: el mateix botó a la capçalera del grau enfocat.
- Enllaç «Què em falta?» a la barra superior de totes les pàgines que la tenen, a
  `footer.js` i a `backend/grau_page.py`. Si el pla 077 té regex de pàgines a nginx per a
  `?lang=es`, afegiu-hi la nova (vegeu la memòria del projecte / `og_page.py`, `PAGES_ES`).
- `sitemap`: afegir la pàgina on es generi.

### Fase 6 — Textos, privacitat i versions
- Claus `gap.*` a `i18n.js` en català i castellà; cap literal dins d'`x-text` sense `t()`.
- `politica-privacitat.html` (ca i es): a «Quines dades tractem», una línia: els graus que
  indiques que ja tens es desen al navegador i, si tens sessió, al teu compte.
- Apujar `?v=` a totes les pàgines i `I18N_VERSION`.

### Fase 7 — Verificació
- `cd backend && python3 -m pytest tests -q --ignore=tests/test_pipeline.py` verd.
- Al navegador (backend a :5001, estàtic a :8765), en català i castellà, amb dades del mateix
  refresc: marcar `ADG_C_001_3B` i comprovar que surt el cicle «Servicios Administrativos»
  amb mòduls coberts i que els números quadren amb `/api/itinerari` del mateix C.
- Amb sessió: marcar en un navegador, entrar en un altre i veure la mateixa llista.
- Mòbil (375 px): columnes apilades, sense desplaçament horitzontal.

## STOP — atura't i pregunta

- Si el creuament per nom dona falsos positius evidents (dos mòduls diferents amb el mateix
  nom normalitzat en famílies diferents): `build_c_lomloe_to_d` restringeix a la mateixa
  família; aquí **no** es restringeix perquè els mòduls comuns travessen famílies. Si surten
  més de 5 objectius D absurds per a un sol C, ensenya'n exemples abans de continuar.
- Si cal tocar el vhost d'nginx: còpia de seguretat i com desfer-ho, i l'aprovació del
  propietari, abans de res.
- No desplegar sense aprovació explícita. Mai reiniciar diumenge 11:10–11:45.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
