# Pla 102 — Favorits, alertes i exportació per a les especialitats SEPE

Prioritat P3 · Mida M · Depèn de: 096 (i 099 per a l'alerta d'entitats) · Idea 11.
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

## Què hi ha fet i es pot reaprofitar

- **Favorits de l'FPO** (`fpo_favorites`, `POST /api/fpo/favorites` amb `especialitat_codi`): accepten
  qualsevol codi. Les especialitats SEPE i les de l'FPO comparteixen codis (un cop fet el pla 096).
  `GET /api/fpo/favorites` treu el nom de l'especialitat de les dades del SOC: una especialitat SEPE
  sense cursos a Catalunya hi sortiria sense nom.
- **Alertes de l'FPO** (`fpo_alerts`, `POST /api/fpo/alerts` amb `comarca?`, `familia_codi?`,
  `espec_codi?`, `inclou_en_linia?`; servei `fpo_alerts_service`): avisen de cursos nous a Catalunya.
  Comprovar si `espec_codi` es valida contra el SOC (ha d'acceptar codis del SEPE sense cap curs encara).
- **Exportació CSV** dels graus: `exportCSV()` a `index.html` (separador `;`, BOM, requereix sessió).

## Què s'ha de fer

1. **Favorits.** Cor a les files SEPE (mateix botó que la taula FPO, `toggleFpoFav`). Al perfil
   (`perfil.html#fpo`) i a `GET /api/fpo/favorites`, completar nom, família, hores i modalitat amb el
   catàleg SEPE quan el SOC no té l'especialitat.
2. **Alerta de cursos a Catalunya.** Botó «Avisa'm quan hi hagi un curs a Catalunya» al desplegable SEPE
   (crea una `fpo_alert` amb `espec_codi`). Si ja n'hi ha cursos, el text és «Avisa'm de cursos nous».
   Cas real: SSCE22 no tenia cursos i el SOC en va programar dos per al desembre del 2026.
3. **Alerta aproximada d'entitats noves** (decisió del propietari; depèn del pla 099).
   - «Avisa'm quan una entitat nova quedi autoritzada per impartir aquesta especialitat», amb filtre
     opcional per província i per teleformació.
   - Migració SQL nova a `backend/migrations/` (veure la `015_fpo_alerts.sql` com a model). Taula `sepe_entity_alerts(user_id, codi, provincia, nomes_teleformacio, created_at)` i una instantània
     dels identificadors d'entitat coneguts per especialitat.
   - Un pas setmanal (dins del refresc, no fatal, després del SEPE) torna a demanar les entitats **només**
     de les especialitats que tenen alguna alerta, compara amb la instantània i envia un correu amb les
     noves. Respectar la preferència global d'emails si el pla 053 és fet.
   - El text ha de dir clarament que és una entitat **autoritzada**, no un curs amb dates.
   - Baixa amb enllaç al correu (mateix patró d'`/api/fpo/alerts/<id>/unsubscribe`).
4. **Exportació CSV** de la llista SEPE filtrada: codi, codi antic, títol, família, nivell, hores,
   modalitat, vigència (inici i fi), cursos a Catalunya. Al navegador, amb el mateix requisit de sessió i
   el mateix format que `exportCSV()`.
5. **Perfil**: les alertes noves han de sortir a la llista d'alertes de l'usuari i es poden esborrar.

## Tests

- Favorits d'una especialitat només SEPE: es desa i el llistat en porta el nom.
- Alerta amb `espec_codi` del SEPE sense cursos al SOC.
- Alertes d'entitats: detecció d'entitats noves amb el SEPE mockejat, filtres de província i
  teleformació, un sol correu per usuari i refresc, baixa.

## Fora d'abast

- Alerta de **cursos programats** fora de Catalunya: no hi ha font de dades (veure el pla 104).
- Alerta d'especialitats noves al catàleg.
