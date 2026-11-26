# Pla 096 — Dades SEPE netes: codis, creuament amb el SOC, títols i sufixos

Prioritat P1 · Mida M · Depèn de: — · Idees 3, 8, 9 i 20.
Executable per un agent sense context. Gairebé tots els plans 097–103 en depenen.

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

## Troballes (verificades amb `backend/data/sepe_especs.json` del 2026-11-14, 7.544 files)

1. **Codis amb parèntesi.** 310 especialitats tenen un codi com `CTRC0001 (FCOV0001)`. Totes són de
   competència transversal. Patró fix: `CTRx#### (FCOx####)`; es dedueix que el primer és el codi nou
   (CTR) i el del parèntesi l'antic (FCO, formació complementària). **Cal confirmar-ho** en una font
   oficial abans de documentar-ho a la web; si no es troba, dir «codi anterior» sense més.
2. **Error de creuament amb el SOC.** El SOC fa servir el codi sense parèntesi (`CTRC0001`). Com que
   desem el codi sencer, **216 especialitats** no es creuen: al mode FPO surten com a «Pròpia del SOC»
   (`vinculacio='propiaSoc'`) quan són del catàleg estatal, i a la pestanya SEPE surten amb 0 cursos i
   sense títol en català. (El pla 081 ho va anotar com «145 CTR*, probablement pròpies del SOC».)
3. **Sense família.** 404 especialitats tenen `familia_es = None`; són **exactament** les 404 amb
   `competenciaTransversal` (14 categories: Digitales/Ofimática/TICs 94, Idiomas 83, Orientación 43,
   Habilidades personales y sociales 41, Competencias básicas para la empleabilidad 31, PRL 25,
   Igualdad 24, …). 94 d'elles porten només un codi `FCO…` sense parèntesi.
4. **Interrogants.** 10 títols porten `?` on hi havia cometes o ®. El SEPE ja els envia així (no és un
   problema de codificació nostre: no hi ha cap caràcter 0x80–0x9F). 8 són parells `?…?` (cometes) i 2 són
   `MICROSOFT?` (®). Cap títol té un interrogant legítim.
5. **Majúscules.** 7.494 títols vénen tot en majúscules. El frontend els passa a minúscules amb `sc()` i
   es perden sigles i noms propis («azure», «moodle», «html»). Sigles clares (sense vocals o amb xifres):
   291 tokens diferents (PRL, 3D, CNC, SQL, PHP, CRM, HTML5, B2, 5G…). Paraules curtes ambigües: 475
   (BIM, SAP, AWS, IA, TIC, ISO, QGIS, CAD són sigles; USO, OBRA, AGUA, PLAN no).
6. **Sufixos del codi:** `PO` 2.124, `EXP` 105, `DCP` 28, `CCC` 23, `PTF` 3.
   - `PO`: «programas de formación dirigidos prioritariamente a trabajadores ocupados» (ho diu el PDF del
     programa SSCE001PO). Confirmat.
   - `DCP`: per a persones amb discapacitat (font no oficial + programes: ADGA12DCP va adreçat a persones
     amb discapacitat o trastorn de salut mental).
   - `EXP` (experimental) i `CCC` (compromís de contractació): només una font no oficial
     (editorialelearning.com/blog/especialidades-formativas-rs/). La guia de FUNDAE descriu l'estructura
     del codi però no el significat. `PTF`: desconegut.

## Què s'ha de fer

### Scraper (`backend/scrapers/sepe_scraper.py`, `parse_row`)

- `codi` = part d'abans de l'espai (`CTRC0001`); `codiAntic` = contingut del parèntesi o `None`.
  `familia_codi`/`area_codi` es continuen derivant de `codi`. `validate_rows`: unicitat sobre el `codi` net.
- `sufix`: `PO | EXP | DCP | CCC | PTF | None` (regex sobre el final del codi, després dels dígits).
- Títol: `titol_es` es guarda corregit dels interrogants (parell `?…?` → `«…»`; `?` solt enganxat a una
  paraula → s'elimina; un `¿…?` es deixa intacte). Afegir `titol_mostra`: el títol amb majúscules bones.
- `titol_mostra`: funció pura `display_title(text)` en un mòdul nou petit (p. ex. `backend/titols.py`),
  reutilitzable pel pla 098 i pels títols en català del SOC:
  1. passa a minúscules amb majúscula inicial (i després de «. » i «: »);
  2. conserva tal qual els tokens sense vocals o amb xifres i els números romans;
  3. aplica una llista `PRESERVE` (150–200 entrades) per als casos ambigus: sigles (BIM, SAP, AWS, IA,
     TIC, ISO, QGIS, CAD, IOT, ERP, RRHH, UE, PYME…) i noms propis (Azure, Moodle, Microsoft, Red Hat,
     Java, JavaScript, Excel, Word, Linux, Python, Google, Oracle, AutoCAD, WordPress…). Preparar-la
     repassant els ~500 tokens més freqüents dels títols (script d'un sol ús, no cal desar-lo).
- Regenerar `sepe_especs.json` en local i copiar-lo al VPS en desplegar (o esperar el refresc).

### Backend (`backend/app.py`)

- `_sepe_index()` indexa pel `codi` net. `_soc_espec_index()` passa a creuar bé: les 216 deixen de ser
  `propiaSoc`. `_sepe_llista()`: afegir `ca` (codi antic), `sx` (sufix), `tm` (títol per mostrar) i, per a
  les transversals, `f = 'CTR'` amb `families['CTR'] = {ca: 'Competències transversals', es:
  'Competencias transversales'}` i el nom de la categoria (`ct`) com a text de la columna de família.
- `/api/sepe/programa/<codi>` ha d'acceptar el codi net i, per compatibilitat, el codi antic.
- El títol en català del SOC en majúscules (43 casos) o amb barreja estranya passa per `display_title`.

### Frontend (`frontend/index.html`, `i18n.js`)

- Mostrar `tm` en lloc de `sc(e.t)`; cerca per `codi` **i** `codiAntic`; el codi antic es veu al
  desplegable («Codi anterior: FCOV0001»).
- Etiquetes de sufix: `PO` («Per a persones ocupades») i `DCP` («Per a persones amb discapacitat») amb
  text d'ajuda. `EXP`/`CCC`: només si es confirma amb font oficial; si no, explicar-ho a
  `per-que-grausfp.html#sepe` amb «segons…». `PTF`: res.
- Família virtual «Competències transversals» al filtre de família **només** a la pestanya SEPE; a la
  columna, «Transversal · <categoria>».
- Una frase a `per-que-grausfp.html#sepe` (+ `docs/per-que-grausfp.md`) sobre transversals i codi antic.

## Tests

- `test_sepe_scraper.py`: codi amb parèntesi → `codi`/`codiAntic`; sufixos; interrogants (els 3 casos);
  fila sense família.
- `display_title`: sigles automàtiques, llista `PRESERVE`, números romans, majúscula després de «: ».
- `test_fpo_api.py` / `test_sepe_api.py`: una especialitat `CTRC0001 (FCOV0001)` del SEPE es creua amb
  `CTRC0001` del SOC (`vinculacio='sepe'`, `nc` correcte, `tca` present).

## Verificació

- Comptar abans i després: especialitats `propiaSoc` al mode FPO (han de baixar unes 216) i especialitats
  SEPE amb `nc > 0`. Cap `?` als títols (tret de `¿…?`). Revisar a ull 100 títols a l'atzar.

## Fora d'abast

- Filtre per les 14 categories transversals (el propietari va dir que amb la família virtual n'hi ha prou).
- Filtre «per a persones amb discapacitat» (només 28 especialitats; més endavant).
