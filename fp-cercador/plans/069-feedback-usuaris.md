# Pla 069 — Pestanya "Feedback" per als usuaris

Origen: petició del propietari (2026-10-20): una pestanya de comentaris com la de Fenya
(`/Users/rogermasellas/AI/fenya`: `feedback-widget.tsx`, `api/feedback/route.ts`,
`lib/feedback.ts`, `admin/feedback/*`), adaptada a GrausFP i oberta també als anònims.
Depèn de: login F1 (023–026), panell admin (036/037).

TDD estricte al backend. Les decisions de producte ja estan preses pel propietari (no re-preguntar).

## Fets verificats (2026-10-20; no re-investigar)

- Migracions: `backend/migrations/NNN_*.sql`, aplicades per `db.run_migrations` a l'arrencada
  (`app.py` crida `db.init_db()` en importar-se). Última: `010` → `schema_version` 10.
  Cada fitxer acaba amb `INSERT INTO schema_version (version) VALUES (N);`.
- Sessió: cookie `session`; `_get_session_user(req)` retorna el `user_id` o `None`.
  Admin: `_check_admin(req)` (Bearer `ADMIN_TOKEN` o sessió amb `is_admin=1`).
- Esborrat d'usuari: `DELETE /api/admin/users/<id>` esborra **físicament** i totes les
  taules d'usuari fan `ON DELETE CASCADE` ("totes les seves dades").
- Límit per IP existent: només al login, sobre la taula `login_attempts`
  (`request.remote_addr`, 5 errors / 15 min). No hi ha cap límit genèric reutilitzable.
- No hi ha `ProxyFix` ni lectura d'`X-Forwarded-For`/`X-Real-IP`; la config de nginx del VPS
  no és al repo.
- CORS amb credencials només per als prefixos de `_needs_auth_cors`; `Allow-Methods` no inclou
  `PATCH`.
- Emails: `email_service.send_email(to, subject, body)` (Brevo SMTP), llança excepció si falla.
- Frontend: `footer.js?v=1` és a 14 pàgines (totes menys `ocupacions.html`, que és un
  redirect); `admin.html` el carrega però no carrega `i18n.js`. `i18n.js?v=20261020`;
  `setLang` recarrega la pàgina, així que n'hi ha prou de pintar els textos un cop.
- `politica-privacitat.html`: llista "Quines dades emmagatzemem" en català (només el `h1`
  i el badge passen per i18n).

## Decisions de disseny

- **Taula `feedback`** (migració `011_feedback.sql`, `schema_version` 11): `id`, `user_id`
  (FK nullable **`ON DELETE CASCADE`**), `email` (NOT NULL), `kind`, `message`, `context`
  (JSON text), `status` (default `'new'`), `admin_note`, `created_at`, `updated_at`; índex per
  `created_at`.
  - CASCADE i no SET NULL: és el patró de totes les taules d'usuari i el que promet l'esborrat
    ("totes les seves dades"). Amb SET NULL el comentari conservaria l'email (dada personal)
    d'un compte esborrat. Els comentaris anònims tenen `user_id` NULL i no els afecta.
  - L'email es desa sempre a la fila (també per als usuaris amb sessió, des de `users`), així
    el llistat d'admin no depèn d'un JOIN.
- **`POST /api/feedback`** (públic, amb CORS de credencials):
  - `kind` ∈ `error | idea | data | other`; `message` retallat, 1–2000 caràcters.
  - Amb sessió: s'ignora l'email del cos i es fa servir el del compte.
  - Sense sessió: `email` obligatori i validat (`x@y.z`, ≤ 254) → 400 amb missatge si falta.
  - Honeypot `website`: si ve ple → 201 sense desar ni notificar (rebuig silenciós).
  - Límit **5 comentaris anònims / hora / IP**, en memòria (dict + `Lock`): gunicorn corre amb
    1 worker (pla 004), així que n'hi ha prou i no cal desar IPs a la BD (minimització RGPD).
    Es reinicia en reiniciar el servei (acceptable). → 429.
  - IP del client: `X-Real-IP` (o el darrer salt d'`X-Forwarded-For`) **només** si la petició
    arriba des de loopback (nginx); si no, `remote_addr`.
  - `context`: només `path`, `query`, `lang` (strings, tallats a 500); la resta es descarta.
    El frontend ja treu els paràmetres sensibles de la querystring (`token`, `code`, `state`,
    `email`…).
  - Avís al propietari: si hi ha `FEEDBACK_NOTIFY_EMAIL`, `email_service.send_email` en un fil
    daemon; qualsevol error es registra i mai fa fallar la petició. → 201 `{id}`.
- **Admin**: `GET /api/admin/feedback` (més nous primer, màx. 500) i
  `PATCH /api/admin/feedback/<id>` (`status` ∈ `new | in_progress | done | discarded`,
  `admin_note` ≤ 1000, buit → NULL; actualitza `updated_at`), protegits amb `_check_admin`.
  `/api/admin/feedback` entra a `_needs_auth_cors` i `PATCH` als mètodes permesos.
- **Frontend**: un sol script `frontend/feedback.js?v=1` (+ CSS a `site.css`, `?v=` pujat),
  carregat just després de `footer.js` a les 14 pàgines (també `admin.html`: una línia, cau al
  català). Pinta la pestanya vertical a la dreta (meitat d'alçada, `writing-mode: vertical-rl`,
  cantonades esquerres arrodonides, color `--dark`, més petita a ≤ 640 px) i un `<dialog>`
  natiu: tipus (botons `aria-pressed`), textarea (2000), camp email només si `/api/auth/me` dona
  401, honeypot ocult, Cancel·la / Envia, estat "Gràcies!" amb Tanca. Esc tanca (natiu);
  focus a la textarea en obrir. Textos via `window.t` amb fallback català (patró `footer.js`);
  claus `fb.*` a `i18n.js` (CA + ES), `?v=` pujat a totes les pàgines.
- **Admin UI**: secció "Comentaris" a `admin.html` amb botó Carregar (patró d'Usuaris): taula
  amb data, tipus, missatge, email, pàgina, `select` d'estat (nou / en curs / fet / descartat)
  i nota amb botó Desa → `PATCH`.
- **Privacitat**: un `<li>` nou a "Quines dades emmagatzemem" amb clau `priv.feedback` (CA/ES).

## Fase 1 — Migració 011 (TDD)

### 1.1 Tests primer: `backend/tests/test_feedback_api.py`
- La BD migrada té la taula `feedback` amb les columnes previstes i `status` per defecte `'new'`.
- Esborrar un usuari esborra els seus comentaris (CASCADE); els anònims es queden.

### 1.2 Implementació: `backend/migrations/011_feedback.sql`

### 1.3 Commit `feat(069): taula feedback (migració 011)`

## Fase 2 — `POST /api/feedback` (TDD)

### 2.1 Tests primer (mateix fitxer)
- Anònim sense email → 400; email invàlid → 400; amb email → 201 i fila desada amb
  `user_id` NULL.
- Amb sessió i sense email → 201, fila amb l'email i el `user_id` del compte.
- `kind` invàlid, missatge buit o > 2000 → 400.
- Honeypot ple → 201 i cap fila.
- 6è comentari anònim de la mateixa IP en una hora → 429; un altre IP passa.
- `context` desconegut es descarta; els strings es tallen.
- Amb `FEEDBACK_NOTIFY_EMAIL` → `send_email` cridat; si llança excepció → igualment 201.
- Preflight `OPTIONS` des de `http://localhost:8080` → `Allow-Credentials: true`.

### 2.2 Implementació a `app.py`
`_FEEDBACK_KINDS`, `_client_ip()`, `_feedback_rate_ok(ip)`, `_sanitize_feedback_context()`,
`_notify_feedback()`, ruta; prefix a `_needs_auth_cors`.

### 2.3 Commit `feat(069): endpoint POST /api/feedback amb honeypot i límit per IP`

## Fase 3 — Endpoints admin (TDD)

### 3.1 Tests primer
- Sense admin → 401 (GET i PATCH).
- GET retorna els comentaris més nous primer amb `context` com a objecte.
- PATCH canvia `status` i `admin_note`; estat invàlid → 400; id inexistent → 404.

### 3.2 Implementació a `app.py` (+ `PATCH` a `Allow-Methods`)

### 3.3 Commit `feat(069): endpoints admin per llistar i gestionar comentaris`

## Fase 4 — Pestanya i diàleg (`feedback.js`, `site.css`, `i18n.js`, 14 pàgines)

Commit `feat(069): pestanya Feedback a totes les pàgines`.

## Fase 5 — Secció "Comentaris" a `admin.html`

Commit `feat(069): secció Comentaris al panell admin`.

## Fase 6 — Privacitat, verificació i tancament

- `<li>` a `politica-privacitat.html` + `priv.feedback` (CA/ES).
- Verificació amb Playwright (frontend :8080, backend :5001, BD local `backend/data/fp_cercador.db`):
  anònim sense email bloquejat, amb email desat, honeypot, límit, usuari amb sessió sense camp
  d'email, admin (llistat + canvi d'estat), CA/ES, 1440 px i 375 px, Esc i focus, consola neta.
- Suite backend (2 fallades conegudes a `test_db`, ara amb `11 == 1`).
- Fila 069 a `plans/README.md` → DONE.
- Commit `docs(069): política de privacitat i tancament del pla`.

## Desplegament (només amb confirmació del propietari)

`git pull` al VPS + **restart** del servei (la migració 011 s'aplica sola en arrencar) +
`FEEDBACK_NOTIFY_EMAIL=...` al `.env` del VPS (opcional: sense ella no s'envia cap avís).
Comprovar que nginx passa `X-Real-IP` o `X-Forwarded-For`; si no, totes les peticions semblen
venir de 127.0.0.1 i el límit seria global (5/h per a tots els anònims).

## Fora d'abast

- Pàgina d'usuari "Els meus comentaris".
- Filtres i etiquetes al llistat d'admin; recompte de nous a la barra.
- Obrir el diàleg des d'altres components amb un tipus predefinit (l'event de Fenya).
- CAPTCHA.

## Riscos

- IP darrere de nginx (vegeu Desplegament): sense la capçalera, el límit és global.
- El límit en memòria es perd en reiniciar i no és compartit si mai es passa a > 1 worker.
- Spam amb emails falsos: el honeypot i el límit són bàsics; si cal, afegir CAPTCHA més endavant.
