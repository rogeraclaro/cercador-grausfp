# Pla 084 — Mode orientador: llistes de graus compartibles

Origen: auditoria 2026-11-14, idea 2 de 9; disseny validat pel propietari el mateix dia.
Executable per un agent sense context, en una sessió nova. Depèn de: login (023–026), favorits
(F2), 076 (`ref` estable), tots DONE. Independent del pla 083.

## Què fa

Un usuari amb compte (pensat per a orientadors, però obert a tothom) crea llistes amb nom, hi
afegeix graus amb una nota a cadascun i comparteix cada llista amb un enllaç de només lectura i
un QR. L'alumne l'obre sense compte, la pot imprimir i, si té compte, desar-ne els graus als
seus favorits.

## Decisions del propietari (tancades, no reobrir)

| Tema | Decisió |
|---|---|
| Model | Diverses llistes amb nom per usuari. Els favorits continuen sent una llista privada a part. |
| Vista de l'alumne | Títol, missatge de l'orientador, cada grau amb la seva nota i enllaços a fitxa, itinerari i centres. Botons «Imprimeix» i «Desa'ls als meus favorits». |
| QR | Llibreria petita vendoritzada (`qrcode-generator`, MIT). **Quarta excepció acceptada** a la norma de no afegir llibreries. |

Fora d'aquesta versió: centres triats per grau, edició col·laborativa, estadístiques de visites.

## Fets verificats (2026-11-14, no repetir)

- `backend/migrations/001_initial_schema.sql` ja té `lists(id, user_id, name, created_at,
  share_token)` i `list_items(id, list_id, oferta_id, oferta_codigo, notes, added_at)`;
  `012_oferta_ref.sql` hi va afegir `list_items.oferta_ref` i l'índex `(list_id, oferta_ref)`.
  `share_token` i `notes` existeixen però cap codi els fa servir.
- **El codi dona per fet una sola llista per usuari.** A `backend/app.py`:
  - línies ~2900, ~2918 i ~2994: `SELECT id FROM lists WHERE user_id = ? LIMIT 1`;
  - línia ~2903: `INSERT INTO lists (user_id, name) VALUES (?, 'Favorits')`;
  - endpoints de centres del favorit (~3023–3070): `JOIN lists … WHERE lists.user_id = ? AND
    list_items.oferta_ref = ?`, sense filtrar per llista.
  Amb llistes noves, tots aquests punts barrejarien favorits i llistes compartides.
- Última migració: `012_oferta_ref.sql`. Si el pla 083 s'ha executat abans, la `013` ja és
  agafada: fes servir el número següent lliure.
- El menú de compartir d'una fila és `.row-share-menu` a `frontend/index.html` (~línia 1327 i
  el seu marcatge); és el lloc natural per a «Afegeix a una llista…».
- Esborrar un usuari (`DELETE FROM users`, ~línia 753) ja arrossega les seves llistes per
  `ON DELETE CASCADE`.
- Versió de memòria cau: `I18N_VERSION` a `backend/grau_page.py` i `?v=` a totes les pàgines.

## Dades

Migració `0NN_shared_lists.sql`:

```sql
ALTER TABLE lists ADD COLUMN kind TEXT NOT NULL DEFAULT 'favorites';  -- 'favorites' | 'shared'
ALTER TABLE lists ADD COLUMN message TEXT;
ALTER TABLE lists ADD COLUMN updated_at TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_lists_share_token ON lists(share_token) WHERE share_token IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_lists_user_kind ON lists(user_id, kind);
```

Les llistes existents queden `favorites` pel valor per defecte: no cal migrar dades.

Límits: 20 llistes `shared` per usuari, 30 graus per llista, nom 80 caràcters, missatge 500,
nota 300. Tot validat al backend (tipus i longitud; cos JSON que no sigui objecte → 400).

## API

Amb sessió (401 sense), sempre filtrant per `user_id` **i** `kind = 'shared'`:

| Mètode i ruta | Què fa |
|---|---|
| `GET /api/lists` | Les meves llistes: `id, name, message, n_items, shared (bool), updated_at`. |
| `POST /api/lists` | Crea. Cos `{name, message?}`. 429 si ja n'hi ha 20. |
| `GET /api/lists/<id>` | Llista sencera amb els graus (`ref`, nota, i les dades del catàleg). |
| `PATCH /api/lists/<id>` | Canvia `name` i/o `message`. |
| `DELETE /api/lists/<id>` | Esborra la llista. |
| `PUT /api/lists/<id>/items/<ref>` | Afegeix el grau o en canvia la nota. Cos `{notes?}`. `ref` validat contra el catàleg. |
| `DELETE /api/lists/<id>/items/<ref>` | Treu el grau. |
| `POST /api/lists/<id>/share` | Activa l'enllaç: genera `secrets.token_urlsafe(24)` i el torna. Si ja n'hi havia un, en fa un de **nou** (l'antic deixa de funcionar). |
| `DELETE /api/lists/<id>/share` | Revoca: `share_token = NULL`. |

Pública, sense sessió:

| `GET /api/llista/<token>` | `{name, message, items: [{ref, grado, codigo, denominacion, familia, nivel, notes, n_centres, disponible}]}`. 404 si el token no existeix. |

La resposta pública **no** porta mai `user_id`, correu, `id` intern de la llista ni dates de
creació. Capçalera `X-Robots-Tag: noindex`. Límit de peticions per IP amb `_auth_rate_ok`
(cubell `shared_list`) per frenar l'enumeració de tokens.

## Fases

Cada fase acaba amb els tests verds i un commit (`feat(lists): …`, sense atribució d'IA).

### Fase 1 — Separar els favorits de la resta de llistes
Migració + tots els punts de la secció «Fets verificats» passen a filtrar `kind = 'favorites'`.
Test nou **abans** de tocar res: un usuari amb una llista `shared` que conté un grau no el veu
a `GET /api/favorites`, i esborrar un favorit no toca la llista compartida. Ha de fallar amb
el codi actual i passar després. La suite de favorits existent ha de continuar verda.

### Fase 2 — API de llistes
`backend/tests/test_lists_api.py`, tests primer: aïllament entre usuaris (404, no 403, en
tocar la llista d'un altre), límits, validació, nota i missatge, i que un `ref` inexistent es
rebutja.

### Fase 3 — Compartir
Tests: el token antic torna 404 després de regenerar-lo o revocar-lo; la resposta pública no
conté cap camp de l'autor (comparar el conjunt exacte de claus); un grau que ja no és al
catàleg surt amb `disponible: false` i sense dades; capçalera `noindex`.

### Fase 4 — `frontend/llistes.html` (amb sessió)
- Sense sessió redirigeix a `login.html?next=llistes.html` (el login ja respecta `next`).
- Columna de llistes + editor de la llista triada: nom, missatge, graus amb nota editable
  (desat en perdre el focus, amb indicador «desat»), treure grau, esborrar llista amb
  confirmació.
- Bloc «Comparteix»: activar/desactivar, copiar enllaç, QR, «Genera un enllaç nou».
- Avís fix a l'editor: «No hi escriguis dades personals de l'alumne: qui tingui l'enllaç ho
  pot llegir.»
- Enllaç «Les meves llistes» a `perfil.html`.

### Fase 5 — `frontend/llista.html?t=<token>` (pública)
- `<meta name="robots" content="noindex">`. Barra superior i peu com la resta.
- La maqueta validada: títol, missatge entre cometes, «llista compartida, només lectura»,
  i cada grau amb el seu distintiu de grau, nota, i enllaços Fitxa (`/grau/<ref>`), Itinerari
  i Centres (N) (`index.html?ref=<ref>`).
- «Imprimeix» (`window.print()`) i «Desa'ls als meus favorits»: amb sessió, un `POST
  /api/favorites` per grau, en sèrie, amb recompte final; sense sessió, porta a
  `login.html?next=llista.html` conservant el token.
- Estats: carregant, enllaç caducat o inexistent (missatge clar, sense detall tècnic), llista
  buida.
- `@media print`: sense barra, peu ni botons; al peu del full, el QR i l'adreça escrita.
- Tot el text que ve de l'API (nom, missatge, notes) es pinta amb `x-text` o escapat: és
  contingut escrit per un tercer.

### Fase 6 — «Afegeix a una llista…» al cercador
A `.row-share-menu` d'`index.html`: amb sessió, desplega les llistes de l'usuari i «Llista
nova…»; sense sessió, obre el modal d'accés que ja existeix (`showCentresModal`). Confirmació
breu en afegir. Només es carreguen les llistes la primera vegada que s'obre el menú.

### Fase 7 — QR
- `frontend/vendor/qrcode-generator-<versió>.min.js` (MIT, Kazuhiko Arase), baixat del
  paquet oficial d'npm, sense CDN, amb la llicència al costat. Carregat només a
  `llistes.html` i `llista.html`.
- El QR es pinta com a SVG en línia (`createSvgTag`), nivell de correcció M.
- Afegir l'excepció a `CLAUDE.md` (arrel del repo), al paràgraf de «Tech Stack», amb el
  mateix format que les de Cytoscape i GSAP.
- Si la llibreria no carrega, la pàgina funciona igual sense QR.

### Fase 8 — Textos, privacitat i versions
- Claus `lists.*` a `i18n.js`, en català i castellà.
- `politica-privacitat.html` (ca i es): les llistes i les notes es desen al compte, i qui té
  l'enllaç en pot veure el contingut; revocar l'enllaç ho atura.
- Apujar `?v=` a totes les pàgines i `I18N_VERSION`.

### Fase 9 — Verificació
- `cd backend && python3 -m pytest tests -q --ignore=tests/test_pipeline.py` verd.
- Al navegador, en català i castellà: crear llista, afegir tres graus des del cercador,
  anotar-los, compartir, obrir l'enllaç en una finestra privada, escanejar el QR amb un
  mòbil o descodificar-lo, regenerar l'enllaç i comprovar que l'antic dona l'estat d'error.
- Vista prèvia d'impressió: una pàgina neta amb QR.
- Mòbil (375 px) a les dues pàgines.

## STOP — atura't i pregunta

- Si la fase 1 descobreix més llocs que assumeixen una sola llista dels que hi ha llistats,
  fes-ne la llista completa abans de continuar.
- Si `qrcode-generator` no es pot baixar o la llicència no és MIT a la versió triada: no
  canviïs de llibreria sense preguntar.
- No desplegar sense aprovació explícita. Mai reiniciar diumenge 11:10–11:45.

## En acabar

Actualitza la fila del pla a `plans/README.md` i `plans/ESTAT.md`.
