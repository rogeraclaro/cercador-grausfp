# Phase 6: Frontend — Admin Panel - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Panell d'administració complet que permet operar el sistema sense SSH. Cobreix: refresh manual de dades amb polling d'estat, gestió de cookies del buscador (guardar des de l'admin sense restart), i programació de refreshos periòdics via APScheduler. Tot en una única pàgina `admin.html`.

</domain>

<decisions>
## Implementation Decisions

### Recàrrega de cookies (sense restart)
- **D-01:** Afegir `load_dotenv(override=True)` al principi de `pipeline.run()`. Quan l'admin guarda cookies noves al `.env`, el proper pipeline run les llegeix automàticament. **No cal `systemctl restart`.**
- **D-02:** Nou endpoint `POST /api/admin/update-cookies` protegit per Bearer token. Rep el valor de cookies, el valida, l'escriu al `.env` i retorna confirmació. El servei continua corrent.
- **D-03:** L'operador enganxa **ja retallat**: només `JSESSIONID=XXX; __Host-todofp.es=YYY`. Les instruccions a l'admin especifiquen exactament quines dues cookies conservar del cURL.

### Instruccions de cookies a l'admin
- **D-04:** Les instruccions s'implementen com a **collapsible/acordió** (`‹ Com obtenir les cookies? ›`). Es pot expandir però no és visible per defecte — l'operador que ja sap el procés no les veu.
- **D-05:** Les instruccions dins el collapsible cobreixen: URL del buscador, DevTools Network, reCAPTCHA, fer una cerca, Copy as cURL, i quines dues cookies extreure (`JSESSIONID` i `__Host-todofp.es`).

### Refresh periòdic (APScheduler)
- **D-06:** Integrar `APScheduler` (nova dependència a `requirements.txt`). Scheduler configurable des de l'admin: activar/desactivar + dia de la setmana + hora (HH:MM).
- **D-07:** La configuració del scheduler es guarda en un fitxer JSON local (`backend/data/scheduler.json`). Flask llegeix aquest fitxer a l'arrencada i reprograma el job automàticament.
- **D-08:** Nous endpoints necessaris: `GET /api/admin/scheduler` (estat actual), `POST /api/admin/scheduler` (actualitzar config), `DELETE /api/admin/scheduler` (desactivar).
- **D-09:** Intervals: l'admin ofereix selector de dia de la setmana (Dilluns–Diumenge o Cada dia) + hora personalitzable. No cron expressions manuals.

### Visual i layout
- **D-10:** Mateix estil visual que `index.html`: DM Sans, warm palette (`--dark: #1c1410`, `--warm: #8a7060`, `--bg: #fdf8f2`), topbar fosc.
- **D-11:** Tres seccions en una única pàgina, separades per capçaleres:
  1. **Refresh manual** — token input + botó "Actualitzar dades" + polling d'estat + resum
  2. **Cookies del buscador** — camp de text + collapsible d'instruccions + botó "Guardar"
  3. **Refresh periòdic** — toggle activar/desactivar + selector dia + hora + propera execució

### Bug: refresh doble crida
- **D-12:** Investigar per què `POST /api/admin/refresh` no funciona a la primera crida. Revisar `refresh_state._lock` i la gestió del thread. Corregir dins aquesta fase.

### Seguretat
- **D-13:** Tots els nous endpoints admin (`update-cookies`, `scheduler`) protegits pel mateix `ADMIN_TOKEN` Bearer. Cap secret nou.
- **D-14:** El token NO es guarda a localStorage (ADMN-08 mantingut). Es demana una vegada per sessió.

### Claude's Discretion
- Estil exacte del collapsible (CSS `details`/`summary` natiu o toggle JS).
- Missatge de confirmació quan es guarden cookies correctament.
- Polling interval per al refresh-status (recomanat: 3s, com especifica ADMN-04).
- Validació bàsica del format de cookies abans de guardar.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements d'aquesta fase
- `ADMN-01` a `ADMN-08` a `.planning/REQUIREMENTS.md` — requisits originals del panell admin
- `.planning/ROADMAP.md` §Phase 6 — goal i success criteria originals

### Fitxers existents a modificar/implementar
- `fp-cercador/frontend/admin.html` — stub buit, implementació completa aquí
- `fp-cercador/backend/app.py` — afegir endpoints `update-cookies` i `scheduler`
- `fp-cercador/backend/scrapers/pipeline.py` — afegir `load_dotenv(override=True)` a `run()`
- `fp-cercador/backend/requirements.txt` — afegir `apscheduler`
- `deploy/DEPLOY.md` — actualitzar instruccions de renovació de cookies (ara des de l'admin)

### Context de decisions prèvies
- `.planning/phases/05-frontend-cercador/05-CONTEXT.md` — patrons visual i tècnics de index.html
- `.planning/phases/04-flask-api/04-CONTEXT.md` — arquitectura Flask, endpoints, autenticació

### Arquitectura de referència
- `fp-cercador/backend/refresh_state.py` — gestió d'estat del refresh (bug doble crida aquí)
- `fp-cercador/backend/scrapers/buscador_scraper.py` — llegeix `BUSCADOR_COOKIES` de `os.environ`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `index.html` — CSS complet (variables, topbar, taula, botons) reutilitzable íntegrament
- `app.py` `_check_auth()` — reutilitzar per a tots els nous endpoints admin
- `refresh_state.py` — reutilitzar per al polling d'estat

### Established Patterns
- Endpoints admin: `POST` + Bearer token + JSON response
- Pipeline en thread daemon separat (no bloquejar l'API)
- Escriptura atòmica de fitxers JSON (`tempfile` + `os.replace`)

### Integration Points
- `pipeline.run()` → afegir `load_dotenv(override=True)` al principi
- `app.py` → 3 nous grups d'endpoints (cookies + scheduler)
- `requirements.txt` → `apscheduler`

</code_context>

<specifics>
## Specific Ideas

- Les cookies que cal conservar del cURL: `JSESSIONID=XXX; __Host-todofp.es=YYY` (les altres són analítiques innecessàries)
- El collapsible d'instruccions ha d'incloure: pas de reCAPTCHA, pestanya Network, Copy as cURL, i exemple del valor a enganxar
- La secció de refresh periòdic mostra la "Propera execució:" amb data i hora formatejada

</specifics>

<deferred>
## Deferred Ideas

- Historial d'execucions del refresh (logs) — V2-04 al backlog
- Notificació per email quan el refresh falla — V2-05 al backlog
- Múltiples schedules (e.g., refresc parcial per grado) — fora d'abast

</deferred>

---

*Phase: 06-admin-panel*
*Context gathered: 2026-04-25*
