# Implementation Plans

Generats per l'skill `improve` el 2026-06-10, contra el commit `5dc92a1`.
Executa'ls en l'ordre de la taula tret que les dependències diguin una altra
cosa. Cada executor: llegeix el pla sencer abans de començar, respecta les
seves STOP conditions i actualitza la teva fila en acabar.

**Llegeix primer `plans/instructions.md`** — explica com executar cada pla,
amb quins prerequisits i quins passos manuals calen al servidor.

## Execution order & status

| Plan | Títol | Priority | Effort | Depends on | Status |
|------|-------|----------|--------|------------|--------|
| 001 | Aïllar tests de dades reals + netejar historial contaminat | P1 | S | — | DONE |
| 002 | Reparar la suite de tests (arquitectura actual) | P1 | M | 001 | DONE |
| 003 | Eliminar pdf_scraper mort i pdfplumber | P2 | S | 002 | DONE |
| 004 | gunicorn a 1 worker + threads | P1 | S | — | DONE |
| 005 | El refresh programat escriu historial (history.py) | P1 | S | 001 | DONE |
| 006 | Aprimar historial (11,5 MB → KB), gzip, cache ofertes | P2 | M | 005 | DONE |
| 007 | Debug de Flask fora per defecte | P2 | S | — | DONE |
| 008 | Eliminar 6 variants mortes del frontend | P2 | S | — | DONE |
| 009 | Escapar dades scrapejades a historial.html | P2 | S | — | DONE |
| 010 | Treure artefactes de dades del git | P2 | S | 001 (recomanat) | DONE |
| 011 | Actualitzar documentació obsoleta (cookies/UUID) | P3 | S | 007 (i millor després de 003, 004, 006, 010) | DONE |
| 012 | Vendoritzar Alpine.js (treure CDN) | P3 | S | — | DONE |
| 013 | [SPIKE opcional] Dades extra Grado C | P3 | M | — | DONE |
| 014 | [SPIKE opcional] Feed de novetats RSS/JSON | P3 | S-M | 005, 006 | DONE |
| 015 | [SPIKE] Centres per grau (fonts, estats, contacte) | P3 | M-L | — (millor després de 005/006; coordinar amb 013) | DONE |
| 016 | [SPIKE — F1] Login d'usuaris (fonament del roadmap) | P2 | M | — (millor amb 001–007 DONE) | DONE |
| 016b | [OPCIONAL] URL web dels centres | P3 | S | 016 | DONE |
| 017 | [SPIKE — F3] Alertes personalitzades de novetats | P2 | M | 016, 005, 006 | DONE |
| 018 | [SPIKE — F7] Observatori públic de l'oferta FP | P2 | S-M | 005, 006 | DONE |
| 019 | Migració a domini propi (checklist manual VPS) | P3 | S | — (quan hi hagi domini) | TODO |
| 020 | Enriquiment Grado C (LOE): durada, Annexe PDF, Europass, BOE | P2 | M | 001, 002, 006 | DONE |
| 021 | Construir feed de novetats RSS 2.0 i JSON Feed | P2 | S | 005, 006, 014 | DONE |
| 022 | API i frontend per a centres per oferta | P2 | M | 015, 016b | DONE |
| 023 | Login F1-A: Base de dades i model de dades | P2 | S | 016 (spike DONE) | DONE |
| 024 | Login F1-B: Backend auth (endpoints + email) | P2 | M | 023 | DONE |
| 025 | Login F1-C: Frontend auth (pàgines + auth.js) | P2 | S-M | 024 | DONE |
| 026 | Login F1-D: Hardening i documentació de desplegament | P2 | S | 024, 025 | DONE |
| 027 | Gate centres per oferta darrere del login (preview 3 per anònims) | P2 | M | 023–026 | DONE |

| 028 | Backend motor d'alertes F3 (alerts_service + CRUD endpoints) | P1 | M | 017, 023–027 | DONE |
| 029 | Frontend gestió d'alertes F3 (alertes.html + alertes.js + botó index) | P1 | M | 028 | DONE |
| 030 | [F7] Migració 002 SQLite + persistència observatory_snapshots | P2 | S | 018 (spike DONE) | DONE |
| 031 | [F7] Endpoint `/api/observatory` (dades agregades per a gràfics) | P2 | S | 030 | DONE |
| 032 | [F7] Pàgina `observatori.html` — primer increment (V1 + V3 + V6) | P2 | M | 031 | DONE |
| 033 | [F7] Gràfics addicionals (V2 + V4) + SEO refinament | P3 | S | 032 + 4 setm. dades | TODO |
| 034 | [F8] Botó "Exporta CSV" al cercador | P2 | S | — | DONE |
| 035 | [F8] Selecció centres checkbox → pin + columna CSV | P2 | M | 034 MERGED | DONE |
| 036 | Panell admin — llistar, desactivar i eliminar usuaris | P2 | M | 023–026 DONE | DONE |
| 037 | Admin s'autentica via sessió normal + guard admin.html | P2 | M | 023–026 DONE | DONE |
| 038 | [F4-A] Backend seguiment de centres (BD + servei + endpoints + hook) | P2 | M | 022, 028, 037 | DONE |
| 039 | [F4-B] Frontend seguiment de centres (botó index + seguiment.html) | P2 | M | 038 | DONE |
| 040 | [F9] Multiidioma CA/ES — `i18n.js` global + selector topbar + totes les pàgines | P2 | L | — | DONE |
| 041 | [SPIKE — F5] Itineraris formatius A→B→C→D — validació de fonts | P2 | M | — | DONE |
| 042 | [F5] Itineraris formatius A→B (local) + C→D via ciclosFP | P2 | L | 041 DONE | DONE |
| 043 | [SPIKE — F5] Investigació fonts C LOMLOE→D i B→C LOE | P2 | M | 042 DONE | DONE |
| 044 | [F5] Enriquir ciclos_fp.json amb ficha_url de cada cicle D | P2 | S | 043 DONE | DONE |
| 045 | [F5] B→C LOE — índex UC codes (Annexo PDF) + endpoint + UI | P2 | L | 044 DONE | DONE |
| 046 | [F5] Índex invers B→C LOE — des d'un Grado B mostrar els Certificats C | P2 | S | 045 DONE | DONE |
| 047 | [F6] Cerca per ocupació/sortida professional (MVP castellà, C+D+E) | P2 | L | — (spike `.planning/spikes/001-003` DONE) | TODO |

Valors de Status: `TODO` | `IN PROGRESS` | `DONE` | `BLOCKED (motiu en una línia)` | `REJECTED (motiu en una línia)`

## Dependency notes

- **002 requereix 001**: sense l'aïllament, cada execució de la suite torna
  a contaminar `refresh_history.json`.
- **003 requereix 002**: cal una suite verda abans d'esborrar codi, perquè
  la suite és la xarxa de seguretat del refactor.
- **005 requereix 001**: el pla 005 modifica la fixture `isolate_history`
  que crea el pla 001.
- **006 requereix 005**: 006 reescriu `history.append`, que 005 acaba de
  crear; fer-los en ordre invers duplicaria feina.
- **011 després de 007** (tots dos editen `README.md`) i idealment l'últim
  dels P1–P3: així documenta l'estat final.
- **014 requereix 005 i 006**: dissenya sobre el format d'historial
  resultant.
- **015 i 013 es coordinen**: tots dos toquen centres per als Grados C (el
  buscadorcertificados del 013 també en llista). Si s'executen tots dos, el
  segon ha de llegir l'output del primer a `plans/outputs/`. El 015
  recomana l'estratègia de snapshots de 005/006 per al cicle de vida dels
  centres — millor fer-lo quan aquells dos estiguin DONE.
- **016 → 017**: el spike d'alertes llegeix l'output del spike de login
  (esquema de BD i decisió d'email). No executar el 017 abans.
- **Roadmap de features (F1–F10)**: la visió completa, la taula de
  referència i l'ordre per onades són a
  `plans/futures/ROADMAP-FEATURES.md`. Els spikes 016/017/018 cobreixen
  F1/F3/F7 (onades 1–3); la resta de features (F2, F4, F5, F6, F8, F9,
  F10) tenen els spikes pendents de generar quan la seva onada s'acosti.
- 004, 007, 008, 009, 010, 012 són independents entre si i es poden fer en
  qualsevol moment i en paral·lel (no toquen els mateixos fitxers), amb una
  excepció: 010 i 011 toquen tots dos `deploy/DEPLOY.md` — no els executeu
  simultàniament.

## Plans que requereixen acció manual al servidor (VPS)

L'execució local deixa els fitxers llestos, però el canvi no és efectiu fins
que es desplega. Vegeu el detall a `plans/instructions.md`:

- **001**: executar l'script de neteja d'historial TAMBÉ al VPS si s'hi han executat tests mai.
- **004**: copiar el `.service` + `systemctl daemon-reload && systemctl restart fp-cercador`.
- **006**: executar la migració d'historial al VPS + recarregar nginx amb el conf nou.
- **010**: cap acció (el `git pull` ja ho resol), però verificar que les dades del servidor queden intactes.

## Findings considered and rejected

(Registrats perquè ningú els re-auditi.)

- **CORS wildcard (`CORS(app)` a app.py:59)**: acceptable — l'API de lectura
  és pública per disseny i els endpoints admin van per Bearer token; el CORS
  no és la barrera de seguretat aquí.
- **Shim de compatibilitat `parse_grado()` a buscador_scraper.py:140-142**:
  codi quasi-mort però innocu (3 línies); no val un pla. Si molesta,
  esborrar-lo de passada en algun canvi futur del fitxer.
- **Reescriure la història de git per treure el blob de 9,8 MB**: descartat
  al pla 010 — risc de coordinació entre clones > benefici.
- **Migrar el frontend fora d'Alpine per complir la constraint literal**:
  descartat — el cost de reescriure index.html supera el benefici; en lloc
  d'això, el pla 012 documenta l'excepció i elimina el risc real (el CDN).
- **`pip-audit` / CVEs de dependències**: NO es va auditar (sense xarxa
  fiable per a l'audit al moment); les dependències són mainstream i poques.
  Queda com a tasca menor si es vol completar.
