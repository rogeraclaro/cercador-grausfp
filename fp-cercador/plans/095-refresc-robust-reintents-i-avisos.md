# Pla 095 — Refresc robust: reintents, avisos fiables i estat visible

Prioritat P1 · Mida M · Depèn de: — · Idea 5 de la sessió 2026-11-26.
Executable per un agent sense context.
**Estat: DONE i desplegat el 2026-11-26.**

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

## El problema (verificat el 2026-11-26)

- Diumenge 2026-11-22 el refresc programat va començar a les 11:10:00 i va fallar a les 11:10:14 amb
  `('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))`. Per l'hora, era la
  primera fase («Buscador Graus A/B/C», todofp). Un sol tall de connexió va tombar el refresc de tota
  la setmana. Ningú se'n va assabentar fins 4 dies després.
- `scheduler_service.run_refresh_job()` captura l'excepció, posa `status="error"` i **esborra la fase**
  (`phase=None`): l'error no diu on ha fallat.
- `heartbeat.report_refresh()` avisa Uptime Kuma (monitor push id 5, «GrausFP refresc setmanal»,
  `KUMA_PUSH_URL` configurat a producció). Marca `down` tant amb **errors** com amb **avisos**.
  Kuma només envia correu quan el monitor **canvia** d'estat. Historial real:
  15-nov `up`; 18-nov `down` per un simple avís («Requisits E …»); 22-nov `down` (l'error de debò, sense
  correu perquè ja estava caigut); 26-nov `up` després del refresc manual.
- El refresc manual del 2026-11-26 va acabar bé (12.989 registres, 94 min, 0 errors, 0 avisos).

## Què s'ha de fer

1. **Reintents de xarxa a les fases fatals** (`scrapers/pipeline.py` i els scrapers que criden:
   buscador A/B/C, HTML de D bàsic/mitjà/superior i E). 3 intents amb espera creixent (10 s, 30 s, 90 s)
   només per a errors de connexió i 5xx (`requests.ConnectionError`, `Timeout`, HTTP ≥ 500). Un 4xx o un
   error de parseig no es reintenta. Fer-ho amb un helper petit i únic, no amb una llibreria nova
   (les dependències estan tancades: veure `CLAUDE.md`).
2. **Segon intent del refresc sencer**: si `run_refresh_job` acaba en error i era un refresc programat,
   programar-ne un altre una sola vegada al cap de 2 hores (job puntual d'APScheduler). No encadenar més
   d'un reintent. El refresc manual del panell no es reprograma.
3. **Fase a l'error**: en fallar, conservar la fase en què estava i incloure-la a `errors` i al missatge
   (p. ex. «Buscador Graus A/B/C: Connection reset by peer»). `refresh_state` ja guarda `phase`.
4. **Avisos ≠ caigut**: a `heartbeat.report_refresh`, `down` només si hi ha `error` o `result["errors"]`.
   Amb només `warnings`, enviar `up` amb el text dels avisos al missatge. Actualitzar
   `backend/tests/test_scheduler.py` (hi ha un cas que espera `down` amb avisos).
5. **Correu propi en fallar**: quan el refresc acaba en error (després del reintent del punt 2), enviar
   un correu a l'administrador amb fase, error i data de les últimes dades bones. Reaprofitar el patró de
   `pipeline._notify_admin_soc_failure` (segell en disc per no repetir el mateix avís). Kuma queda com a
   segona xarxa per al cas «el refresc ni ha arrencat».
6. **Estat al panell d'administració** (`frontend/admin.html`): data de l'últim refresc **correcte**
   (mtime d'`ofertes.json` o un camp nou a `refresh_state`) i un avís visible si l'últim intent va fallar,
   amb la fase i l'error.

## Tests

- Helper de reintents: reintenta en `ConnectionError`, no en 404, respecta el nombre màxim, i el temps
  d'espera es pot parchejar a 0.
- `run_refresh_job`: en error conserva la fase; el reintent es programa una sola vegada.
- `heartbeat`: avisos → `up`; errors → `down`.
- Correu d'error: s'envia una vegada per fallada (segell), amb SMTP mockejat.

## Verificació

- Tests en verd. En local, forçar un error a la primera fase (parchejar la URL) i comprovar: 3 intents al
  log, estat `error` amb la fase, correu (SMTP de prova) i panell amb l'avís.
- Després de desplegar, **no** llançar un refresc de prova en diumenge al matí.

## Fora d'abast

- Canviar la configuració de notificacions de Kuma (és del propietari; el correu va a l'adreça que hi té
  posada). Si es vol, el propietari hi pot activar «reenviar cada X».
