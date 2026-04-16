# Requirements: Cercador FP España

**Defined:** 2026-04-16
**Core Value:** Un únic cercador que consolida tota l'oferta FP espanyola (Grados A–E) en temps real, filtrable per grado, família professional, nivell i text lliure.

## v1 Requirements

### Estructura del Projecte

- [x] **PROJ-01**: El projecte té l'estructura de directoris `fp-cercador/backend/` i `fp-cercador/frontend/` amb tots els fitxers necessaris
- [x] **PROJ-02**: El fitxer `.gitignore` exclou `.env`, `data/ofertes.json` (opcional) i fitxers de cache Python
- [x] **PROJ-03**: El fitxer `requirements.txt` conté: flask, flask-cors, pdfplumber, requests, beautifulsoup4, python-dotenv

### Scraper PDFs (Grados A, B, C)

- [ ] **PDF-01**: El scraper descarrega els 3 PDFs oficials des de todofp.es amb els headers `Referer` i `User-Agent` requerits
- [ ] **PDF-02**: El scraper detecta correctament la família professional de cada registre (29 famílies)
- [ ] **PDF-03**: El scraper dedueix el nivell del sufix del codi: `_3B`→1, `_4B`→2, `_5B`→3
- [ ] **PDF-04**: El scraper detecta `plan_antiguo: true` per codis antics (format `XXXN0000NN`) i observacions amb "(Plan antiguo)"
- [ ] **PDF-05**: El scraper omiteix les pàgines 1–5 (portada i introducció) de cada PDF
- [ ] **PDF-06**: El scraper genera registres correctes per a les 3 columnes: Código, Denominación, Observaciones

### Scraper HTML (Grados D i E)

- [ ] **HTML-01**: El scraper extreu els títols dels Grados D des de les 3 URLs (Básico, Medio, Superior)
- [ ] **HTML-02**: El scraper extreu els títols del Grado E des de la URL de Cursos d'Especialització
- [ ] **HTML-03**: Els títols s'identifiquen per elements amb atribut `id="tit-*"`
- [ ] **HTML-04**: La família professional s'infereix de les capçaleres de secció del HTML
- [ ] **HTML-05**: El nivell s'assigna per subtipus: Básico→1, Medio→2, Superior→3; Grado E → `null`
- [ ] **HTML-06**: Els registres Grado D i E tenen `codigo: null` i `plan_antiguo: false`

### Generació de Dades

- [ ] **DATA-01**: El pipeline genera `backend/data/ofertes.json` amb el schema definit (id, grado, nivel, familia, codigo, denominacion, plan_antiguo, observaciones)
- [ ] **DATA-02**: Els IDs són correlatius i únics a tot el fitxer
- [ ] **DATA-03**: El fitxer consolida els Grados A, B, C, D i E en un únic array
- [ ] **DATA-04**: El volum generat és d'aproximadament 800–900 registres totals

### API Flask

- [ ] **API-01**: `GET /api/ofertes` retorna el contingut complet de `ofertes.json` (status 200)
- [ ] **API-02**: `GET /api/ofertes` retorna status 503 amb missatge d'error si `ofertes.json` no existeix
- [ ] **API-03**: `POST /api/admin/refresh` llança el pipeline en un thread separat i retorna `{"status": "started"}` immediatament
- [ ] **API-04**: `POST /api/admin/refresh` requereix header `Authorization: Bearer <ADMIN_TOKEN>`; retorna 401 si incorrecte
- [ ] **API-05**: `POST /api/admin/refresh` retorna 409 si ja hi ha un procés en curs
- [ ] **API-06**: `GET /api/refresh-status` retorna l'estat del darrer procés (idle/running/done/error) amb last_run, total, by_grado, duration_seconds, errors
- [ ] **API-07**: `GET /health` retorna `{"status": "ok"}` sense autenticació
- [ ] **API-08**: CORS habilitat per a totes les origins
- [ ] **API-09**: `ADMIN_TOKEN` llegit de variable d'entorn via `.env` (python-dotenv)

### Frontend — Cercador

- [ ] **SRCH-01**: El cercador filtra en temps real (sense botó) simultàniament per `denominacion` i `codigo`
- [ ] **SRCH-02**: Dropdown de Grado (A, B, C, D, E, Tots)
- [ ] **SRCH-03**: Dropdown de Família Professional (valors únics del JSON, dinàmic, o "Totes")
- [ ] **SRCH-04**: Dropdown de Nivell (1, 2, 3, Tots)
- [ ] **SRCH-05**: Checkbox "Ocultar pla antic" activat per defecte
- [ ] **SRCH-06**: Taula de resultats amb columnes: Codi, Denominació, Família, Grado, Nivell
- [ ] **SRCH-07**: Files amb `plan_antiguo: true` mostren un badge "Pla antic" discret
- [ ] **SRCH-08**: Comptador de resultats visibles actualitzat en temps real
- [ ] **SRCH-09**: Rendiment fluid amb fins a 1.500 registres sense paginació
- [ ] **SRCH-10**: Si `/api/ofertes` retorna 503, mostra missatge informatiu per a l'usuari

### Frontend — Panell Admin

- [ ] **ADMN-01**: El panell admin té un camp d'input per al token i un botó "Actualitzar dades"
- [ ] **ADMN-02**: En clicar, fa `POST /api/admin/refresh` amb el token com a Bearer
- [ ] **ADMN-03**: Mostra "Token incorrecte" si la resposta és 401
- [ ] **ADMN-04**: Si la resposta és 200, inicia polling a `GET /api/refresh-status` cada 3 segons
- [ ] **ADMN-05**: Mostra l'estat en curs ("Actualitzant...")
- [ ] **ADMN-06**: Quan `status === "done"`, mostra el resum: total registres, desglossat per grado, durada en segons
- [ ] **ADMN-07**: Quan `status === "error"`, mostra els errors detallats
- [ ] **ADMN-08**: El token NO es guarda a `localStorage` ni cap emmagatzematge persistent; s'esborra en tancar

## v2 Requirements

### Millores Futures

- **V2-01**: Cerca avançada per observacions
- **V2-02**: Exportació a CSV/Excel
- **V2-03**: Actualització automàtica programada (cron)
- **V2-04**: Historial de canvis entre actualitzacions (diffs)
- **V2-05**: Notificació per email quan s'afegeixen nous títols

## Out of Scope

| Feature | Reason |
|---------|--------|
| Paginació | Disseny scroll vertical; ~1.500 registres és manejable |
| Autenticació d'usuari final | El cercador és públic per definició |
| Base de dades (SQL/NoSQL) | JSON estàtic suficient per a dades quasi-estàtiques |
| Frameworks frontend | Vanilla pur per simplicitat i zero dependències |
| Persistència del token admin | Política de seguretat explícita del propietari |
| Detalls individuals per títol | Només llistats agregats del ministeri |
| Scraping de detalls de centres | Fora de l'abast del catàleg nacional |

## Traceability

*(Actualitzat 2026-04-16 — roadmap creat)*

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROJ-01 | Phase 1 | Complete |
| PROJ-02 | Phase 1 | Complete |
| PROJ-03 | Phase 1 | Complete |
| PDF-01 | Phase 2 | Pending |
| PDF-02 | Phase 2 | Pending |
| PDF-03 | Phase 2 | Pending |
| PDF-04 | Phase 2 | Pending |
| PDF-05 | Phase 2 | Pending |
| PDF-06 | Phase 2 | Pending |
| HTML-01 | Phase 3 | Pending |
| HTML-02 | Phase 3 | Pending |
| HTML-03 | Phase 3 | Pending |
| HTML-04 | Phase 3 | Pending |
| HTML-05 | Phase 3 | Pending |
| HTML-06 | Phase 3 | Pending |
| DATA-01 | Phase 3 | Pending |
| DATA-02 | Phase 3 | Pending |
| DATA-03 | Phase 3 | Pending |
| DATA-04 | Phase 3 | Pending |
| API-01 | Phase 4 | Pending |
| API-02 | Phase 4 | Pending |
| API-03 | Phase 4 | Pending |
| API-04 | Phase 4 | Pending |
| API-05 | Phase 4 | Pending |
| API-06 | Phase 4 | Pending |
| API-07 | Phase 4 | Pending |
| API-08 | Phase 4 | Pending |
| API-09 | Phase 4 | Pending |
| SRCH-01 | Phase 5 | Pending |
| SRCH-02 | Phase 5 | Pending |
| SRCH-03 | Phase 5 | Pending |
| SRCH-04 | Phase 5 | Pending |
| SRCH-05 | Phase 5 | Pending |
| SRCH-06 | Phase 5 | Pending |
| SRCH-07 | Phase 5 | Pending |
| SRCH-08 | Phase 5 | Pending |
| SRCH-09 | Phase 5 | Pending |
| SRCH-10 | Phase 5 | Pending |
| ADMN-01 | Phase 6 | Pending |
| ADMN-02 | Phase 6 | Pending |
| ADMN-03 | Phase 6 | Pending |
| ADMN-04 | Phase 6 | Pending |
| ADMN-05 | Phase 6 | Pending |
| ADMN-06 | Phase 6 | Pending |
| ADMN-07 | Phase 6 | Pending |
| ADMN-08 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-16*
*Last updated: 2026-04-16 — traceability mapped after roadmap creation*
