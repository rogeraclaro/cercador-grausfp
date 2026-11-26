# Pla 099 — Entitats que imparteixen cada especialitat SEPE

Prioritat P2 · Mida M · Depèn de: 096 · Idea 4.
Executable per un agent sense context.

## Context comú (llegir abans de començar)

- Origen: sessió del 2026-11-26, després de desplegar el pla 082 (especialitats del SEPE al cercador
  principal). El propietari va repassar 21 idees una per una; aquest pla en recull les decisions.
  Llegir primer `plans/082-cataleg-estatal-especialitats-pagina.md` (secció «Canvi de decisió») i la
  «Diagnosi tècnica» de `plans/081-sepe-cataleg-especialitats-dades-i-enriquiment-fpo.md`.
- Peces que ja existeixen (pla 082): `backend/scrapers/sepe_scraper.py` (`build_sepe_data`,
  `fetch_programa_pdf`), `backend/app.py` (`_sepe_index`, `_sepe_llista`, `/api/sepe/especialitats`,
  `/api/sepe/programa/<codi>`), `frontend/index.html` (estat `sepe*`, getter `filteredSepe`, bloc
  `<section class="sepe-block">`, pestanya `filterGrado === 'SEPE'`), claus `sepe.*` a `frontend/i18n.js`.
- Convencions: codi, comentaris i commits en anglès (commits convencionals, sense atribució d'IA); text
  d'interfície en català i castellà a `i18n.js` (sense literals dins `x-text`); `x-if` amb una sola arrel.
- En tocar `i18n.js` cal pujar `?v=` a **totes** les pàgines de `frontend/*.html`, `I18N_VERSION` a
  `backend/grau_page.py` i l'assert de `backend/tests/test_grau_page.py`. En tocar `site.css`,
  `search-tools.js`, `footer.js` o `feedback.js`, pujar el seu `?v=`.
- Tests: des de `backend/`, `python3 -m pytest -q --ignore-glob='tests/*scraper*' --ignore=tests/test_pipeline.py`
  (tot verd el 2026-11-26: 737) i `python3 -m pytest -q tests/test_sepe_scraper.py`. Frontend:
  `node scripts/test_search_tools.js`.
- `rg` no mira `backend/data/` (és a `.gitignore`): per buscar a les dades cal `rg -uu`.
- Deploy: `git push cercador-grausfp master`; `ssh contabo`, `git pull --ff-only` al directori del site;
  si hi ha canvis de backend, `systemctl restart fp-cercador`. **Mai reiniciar durant un refresc**
  (`curl localhost:8033/api/refresh-status`). Confirmar sempre amb el propietari abans de desplegar.

## Diagnosi tècnica (verificada el 2026-11-26, no repetir)

El pla 081 ho va deixar fora d'abast pensant que era un flux amb estat de 7.544 navegacions. No ho és:
**una sola petició** retorna totes les entitats d'una especialitat, en 0,4 s i sense paginació.

```
GET  https://sede.sepe.gob.es/FOET_CATALOGO_EEFF_SEDE/flows/main        (cookies de sessió)
POST …/flows/main?execution=e1s1   multipart/form-data
  formulario_SUBMIT=1
  javax.faces.ViewState=e1s1
  formulario:codigoPropuesta=<idSepe>
  formulario:invisibleClickTargetEntidadesFormacion=
→ 302 → …/flows/main?execution=e1s2, HTML en UTF-8 (títol «Entidades de formación», ~190 KB per a 117 files)
```

És el mateix patró que `sepe_scraper.fetch_programa_pdf` (canvia l'últim camp).

HTML: taula `id="formulario:resultadoEspecialidadesTablaJSF"`. Cada entitat és una fila amb 6 `<td>`:
control (`details-control`), **Identificador**, **Nombre**, **Tipo**, **Provincia**, i una taula de detall
(`class="tablaDetalle"`) amb «NIF titular:», «Nombre del titular:», «Dirección:», «Teléfono:»,
«Sitio web :», «Mail:» (un `-` vol dir buit). Per separar entitats, partir per
`details-control details-control-background`.

Mostra SSCE22 (`idSepe` 97614): **117 entitats**; tipus «Teleformación» 67 i «Formación Presencial
(instalaciones fijas)» 50; províncies Madrid 37, Barcelona 13, Castelló 11…; 68 amb web, 95 amb correu.

## Decisions preses amb el propietari

- **A demanda**, amb còpia en disc 7 dies (com el PDF). La descàrrega completa setmanal queda per a un pla
  futur si es veu que es fa servir.
- Es mostra: nom, tipus, província, adreça, telèfon i web. **El correu només el veu l'administrador**: el
  backend no l'ha d'enviar a ningú més. El NIF i el nom del titular no es mostren a ningú.
- El botó surt a la fitxa de l'especialitat al cercador **i al mode FPO** (especialitats amb
  `vinculacio === 'sepe'`).
- Cal dir clarament que són entitats **autoritzades** a impartir-la, no entitats amb un curs obert.

## Què s'ha de fer

### Backend

- `sepe_scraper.fetch_entitats(id_sepe) -> list[dict]`: `{id, nom, tipus: 'presencial'|'teleformacio'|
  <literal si és un altre>, provincia, adreca, telefon, web, email}`. Si l'HTML no té la taula esperada,
  aixecar `SepeDataError` (no retornar llista buida en silenci). Una especialitat sense entitats sí que
  retorna `[]` (comprovar com es distingeix a l'HTML abans de decidir-ho).
- `GET /api/sepe/entitats/<codi>` a `app.py`, calcat de `api_sepe_programa`:
  codi validat contra `_sepe_index()`; cache a `backend/data/sepe_entitats/<codi>.json` amb TTL de 7 dies
  i escriptura atòmica (`_write_atomic`); si el SEPE falla i hi ha còpia caducada, servir-la; límit per IP
  amb `_auth_rate_ok('sepe_entitats', …, limit=10, window=60)` per a les peticions no cachejades.
  Resposta `{entitats: [...], actualitzat, total}`. **Treure `email`** de cada entitat si
  `_check_admin(request)` és fals. Webs: normalitzar a `https?://` (el SEPE les dona sense protocol:
  `www.adams.es`) i descartar el que no sigui una URL vàlida.
- El directori ja queda ignorat per git (`backend/data/`).

### Frontend

- Botó «Entitats que la imparteixen» al desplegable SEPE i al panell FPO. En obrir-lo: estat de càrrega,
  nombre total, filtre per província (desplegable amb les que hi ha) i per tipus (presencial /
  teleformació), i la llista. Nota fixa: «Entitats autoritzades a impartir aquesta especialitat. No vol
  dir que tinguin un curs obert ara.»
- Enllaços web amb `safeHttpUrl` i `rel="noopener"`. El correu, només si la resposta el porta.
- i18n CA/ES. Sense `x-if` amb dues arrels.

### Documentació

- `fonts.html#sepe`: fila nova «Entitats de formació» (què se n'obté, on es fa servir, com s'obté) + ES.
- `per-que-grausfp.html#sepe`: una frase.

## Tests (`backend/tests/test_sepe_api.py`, sense xarxa)

- Parseig d'un HTML de mostra desat com a fixture (3 entitats reals, una amb web/correu buits).
- Endpoint: cache encertada; cache caducada es refà; codi desconegut 404; error del SEPE 502 (o còpia
  caducada); límit per IP; **`email` absent per a anònims i present per a admin**; mai NIF.

## Verificació

- Local: SSCE22 → 117 entitats (o el nombre actual), filtres per província i tipus, segon cop instantani.
- Sessió anònima: comprovar a la resposta de xarxa que no hi viatja cap correu.

## Fora d'abast

- Nombre d'entitats a la taula de resultats i filtre del catàleg per província (requereix la descàrrega
  completa). Alertes d'entitats noves (pla 102).
