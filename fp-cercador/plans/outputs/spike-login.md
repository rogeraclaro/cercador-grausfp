# Spike 016 — Disseny del sistema de comptes d'usuari (F1)

> Generat el 2026-06-14. Fonament de F2, F3, F4, F8 i F10.
> Cap d'aquestes decisions implica canvi de codi en aquest pla.

---

## Step 1 — Model d'autenticació

### Opcions comparades

| Criteri | (A) Email + contrasenya | (B) Magic link (OTP per email) | (C) OAuth Google |
|---|---|---|---|
| Fricció per a l'usuari | Mitjana (cal recordar contrasenya) | Baixa (clic a l'email) | Molt baixa (un sol clic) |
| Cost implementació stdlib | Baix: werkzeug + smtplib | Mitjà: generar token, enviar email, verificar caducitat | Alt: OAuth 2.0 flow, dependència o molt codi manual |
| Recuperació de compte | Calen "oblido contrasenya" + email OTP | Gratuïta: el magic link ja és recuperació | No aplica (Google ho gestiona) |
| Dades GDPR mínimes | Email + hash contrasenya | Només email | Email + Google ID (tercera part) |
| Funciona amb F3 (alertes) | Sí, email ja el tenim | Sí, i l'email ja s'ha verificat de facto | Sí, però cal gestionar el cas "usuari sense email Google" |
| Vulnerabilitats típiques | Brute force, password reuse | Token forjat, replay (cal caducitat curta) | Token theft, dependency on third-party |

### Recomanació: (A) Email + contrasenya

**Justificació**: El públic objectiu (famílies i orientadors) és no-tècnic i acostumat a aquest patró; no tots tenen compte Google. La implementació amb `werkzeug.security` és auditada i zero dependències noves. El magic link (B) és elegant però requereix infra d'email fiable des del dia u — mentre que (A) permet fer proves de registre/login en local sense servidor SMTP. El magic link es pot afegir com a segon factor o alternativa en una iteració posterior.

**Excepció documentada (STOP condition no activada)**: Cap dependència d'auth (Flask-Login, Authlib, etc.) no és necessària. Totes les decisions de sessió i hashing es fan amb stdlib + Werkzeug (que Flask ja requereix). Si en algun punt es vol escalar (OAuth multi-proveïdor, tokens JWT), s'haurà de revisar aquest punt.

### Flux complet pas a pas

```
REGISTRE
  1. Usuari envia { email, password } → POST /api/auth/register
  2. Backend: valida email format, comprova que no existeix a users
  3. Hash: werkzeug.security.generate_password_hash(password)
  4. Insereix a users (email, password_hash, created_at, verified=False)
  5. Genera token de verificació (32 bytes urandom → hex) → insereix a tokens (user_id, token, type='email_verify', expires_at=+24h)
  6. Envia email amb link /verify?token=<tok>
  7. Retorna 201 + { "message": "Revisa el teu email per verificar el compte" }
  8. Usuari clica el link → GET /api/auth/verify?token=<tok>
  9. Backend: cerca token, comprova que no ha caducat → users.verified=True, esborra el token
  10. Redirigeix a /index.html?verified=1

LOGIN
  1. Usuari envia { email, password } → POST /api/auth/login
  2. Backend: rate limit check (màx 5 intents / 15 min per IP; ver Step 5)
  3. werkzeug.security.check_password_hash(stored_hash, password)
  4. Si OK: genera session_token (32 bytes urandom → hex) → insereix a sessions (user_id, token, created_at, expires_at=+30d, ip, user_agent)
  5. Set-Cookie: session=<tok>; HttpOnly; Secure; SameSite=Lax; Max-Age=2592000
  6. Retorna 200 + { "user": { "id", "email" } }

LOGOUT
  1. POST /api/auth/logout (porta la cookie)
  2. Backend: esborra la fila de sessions corresponent al token
  3. Set-Cookie: session=; Max-Age=0 (buida la cookie)
  4. Retorna 200

RECUPERACIÓ DE CONTRASENYA
  1. Usuari envia { email } → POST /api/auth/forgot-password
  2. Backend: SEMPRE retorna 200 (evita enumerar emails)
  3. Si email existeix: genera reset_token (32 bytes) → tokens (type='password_reset', expires_at=+1h)
  4. Envia email amb link /reset-password.html?token=<tok>
  5. Usuari envia { token, new_password } → POST /api/auth/reset-password
  6. Backend: valida token, comprova caducitat → hash nova contrasenya, update users, esborra token
  7. Retorna 200 + { "message": "Contrasenya actualitzada" }

CANVI D'EMAIL (futur, no en F1)
  → Requereix verificació del nou email; documentar quan es planifiqui
```

---

## Step 2 — Emmagatzematge

### Fitxer SQLite

**Ubicació**: `backend/data/fp_cercador.db`
- El directori `backend/data/` ja és ignorat per `.gitignore` (pla 010). ✓
- No fer servir `backend/app.py` com a referència de path; crear `backend/db.py` amb la lògica de connexió.

**Estratègia de migracions**: scripts SQL numerats a `backend/migrations/`:
```
backend/migrations/
  001_initial_schema.sql   ← totes les taules del primer increment
  002_add_alerts.sql       ← quan es construeixi F3
  ...
```
Un script Python lleuger (`backend/db.py` → funció `init_db()`) aplica les migracions no executades comparant amb una taula `schema_version`. Sense dependències (no Alembic).

### Esquema complet (cobrint F1, F2, F3)

```sql
-- ──────────────────────────────────────────
-- TAULA: users  (F1)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT    NOT NULL,
    verified      INTEGER NOT NULL DEFAULT 0,   -- 0=pendent, 1=verificat
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    deleted_at    TEXT                           -- soft delete (GDPR: esborrat compte)
);

-- ──────────────────────────────────────────
-- TAULA: sessions  (F1)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT    NOT NULL UNIQUE,          -- 32 bytes hex (64 chars)
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT    NOT NULL,
    ip         TEXT,
    user_agent TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);

-- ──────────────────────────────────────────
-- TAULA: tokens  (F1: verificació email, reset contrasenya)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT    NOT NULL UNIQUE,
    type       TEXT    NOT NULL,                 -- 'email_verify' | 'password_reset'
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT    NOT NULL
);

-- ──────────────────────────────────────────
-- TAULA: login_attempts  (F1: rate limiting)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS login_attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ip         TEXT    NOT NULL,
    email      TEXT,
    attempted_at TEXT  NOT NULL DEFAULT (datetime('now')),
    success    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_attempts_ip ON login_attempts(ip, attempted_at);

-- ──────────────────────────────────────────
-- TAULA: lists  (F2: llistes de favorits)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lists (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    share_token TEXT                             -- F8: share read-only link
);

-- ──────────────────────────────────────────
-- TAULA: list_items  (F2: ítems de cada llista)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS list_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id    INTEGER NOT NULL REFERENCES lists(id) ON DELETE CASCADE,
    oferta_id  INTEGER NOT NULL,                 -- id de ofertes.json
    oferta_codigo TEXT,                          -- codi estable per a sincronitzar
    notes      TEXT,
    added_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ──────────────────────────────────────────
-- TAULA: alerts  (F3: alertes de novetats)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filter_json TEXT   NOT NULL,                 -- JSON: {grado, familia, text_query}
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT    NOT NULL DEFAULT (datetime('now')),
    last_sent_at TEXT                            -- per evitar duplicats entre refreshos
);

-- ──────────────────────────────────────────
-- TAULA: schema_version  (per a migracions)
-- ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schema_version (
    version    INTEGER NOT NULL,
    applied_at TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

### Còpia de seguretat al VPS

Estratègia mínima:
- `sqlite3 /path/fp_cercador.db ".backup /path/backups/fp_cercador_$(date +%Y%m%d).db"` via cron nocturn
- Guardar els darrers 7 dies (rotar amb `find /path/backups -mtime +7 -delete`)
- Documentar al `DEPLOY.md` del futur pla de construcció

---

## Step 3 — Sessions i frontend

### Cookie vs localStorage

**Decisió: cookie HttpOnly + Secure + SameSite=Lax**

| Criteri | Cookie HttpOnly | Token en localStorage |
|---|---|---|
| XSS | Immune (JS no hi pot accedir) | Vulnerable (qualsevol script llegeix el token) |
| CSRF | Necessita SameSite=Lax (suficient per a GET) i headers custom per a mutations | Immune a CSRF (cal afegir al header manualment) |
| Compatibilitat nginx/gunicorn | Perfecta: mateix origen → cap CORS extra | Demana CORS permissiu i gestió manual al JS |
| Local (file:// o localhost:5001) | Problema: Secure requereix HTTPS | Funciona perfectament |

**Solució per a l'entorn local**: La cookie porta `Secure` only en producció. En local (`FLASK_ENV=development`), ometre el flag `Secure`:

```python
secure = not app.debug  # en producció (gunicorn) debug és False → Secure=True
resp.set_cookie('session', token, httponly=True, secure=secure,
                samesite='Lax', max_age=30*24*3600)
```

Això permet que les cookies funcionin a `http://localhost:5001` sense sacrificar la seguretat en producció.

### Implicació sobre CORS

L'actual `CORS(app)` (wildcard, sense credencials) és acceptable per a l'API pública. Quan s'afegeixi auth amb cookies caldrà restringir-lo **NOMÉS per a les rutes `/api/auth/*`**:

```python
CORS(app)  # wildcard per a l'API pública (ofertes, historial, etc.)
CORS(app, resources={r"/api/auth/*"}, supports_credentials=True,
     origins=["https://domini.com", "http://localhost:5001"])
```

En producció, l'API és accedida des del mateix domini via nginx → les peticions d'auth no passen per CORS (same-origin). Només el dev local ho necessita.

### Estat "loguejat" a les 3 pàgines estàtiques

Les 3 pàgines (index.html, historial.html, admin.html) compartiran un fragment JS comú (`frontend/auth.js`):

```
- Al carregar: GET /api/auth/me → { user } o 401
- Si 200: mostra "Hola, email@..." + botó "Sortir"
- Si 401: mostra "Entra" / "Registra't"
- El header comú s'injecta via un fragment HTML o un <script> compartit
```

Cada pàgina inclou `<script src="/auth.js"></script>` al `<head>`. Sense Alpine.js per a aquesta funcionalitat (Alpine és a index.html; auth.js serà vanilla JS pur).

**Ruta nova**: `GET /api/auth/me` → 200 `{id, email}` si sessió vàlida; 401 si no.

---

## Step 4 — Email

### Necessitats

- **F1**: email de verificació de compte (1 email per registre), email de reset de contrasenya (1 per demanda)
- **F3**: alertes setmanals de novetats (potencial alt volum; cal proveïdor extern)

### Opció A: smtplib + SMTP del VPS (Postfix/Exim pre-instal·lat a CloudPanel)

- Cost: 0 €
- Límit: depenent de la IP del VPS (típicament no hi ha límit tècnic, però els ISPs i anti-spam filtren IPs "fredes")
- Risc: emails a spam si el domini no té SPF/DKIM/DMARC configurat

### Opció B: Brevo (ex-Sendinblue) — SMTP relay

- Ja decidit per al projecte (memory: `project_brevo_decision.md`) per a F3 (newsletters)
- Free tier: 300 emails/dia
- smtplib pot usar Brevo com a relay SMTP (HOST: smtp-relay.brevo.com:587)
- Zero dependències noves (smtplib és stdlib)

**Recomanació: Brevo SMTP relay per a TOT el flux d'email** (verificació, reset, alertes). Consistència de proveïdor, evita problemes de deliverability, i la decisió ja estava presa per F3.

### Configuració

```
# Variables d'entorn (a .env, mai al repo)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=<compte@domini.com>
BREVO_SMTP_KEY=<API_key_brevo>
EMAIL_FROM=noreply@domini.com
```

Funció compartida `backend/email_service.py` (nova, ~50 línies) que wrap smtplib + plantilles en text pla. Cap HTML d'email complex en F1.

### Decisions d'email resoltes (2026-06-15)

- **Q-EMAIL-1**: Remitent → `roger@masellas.info`. Cal validar SPF/DKIM per a aquest domini a Brevo (pas manual al .env).
- **Q-EMAIL-2**: Compte Brevo ja existent. ✓

---

## Step 5 — Seguretat i GDPR

### Hashing de contrasenyes

`werkzeug.security.generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)`

- Ja inclòs a Flask (Werkzeug). ✓
- No emmagatzemar mai plaintext, ni logs de passwords.

### Rate limiting de login (sense dependències noves)

Estratègia via SQLite (`login_attempts`):
- Màx **5 intents fallits** en **15 minuts** per IP
- En cada intent: inserir a `login_attempts`; comptar els de l'última finestra
- Si > 5: retornar 429 `{ "error": "Massa intents. Espera 15 minuts." }`
- No cal mantenir res en memòria; la consulta SQL és immediata:

```sql
SELECT COUNT(*) FROM login_attempts
WHERE ip = ? AND success = 0 AND attempted_at > datetime('now', '-15 minutes')
```

- Netejar entrades antigues amb un cron lleuger o a cada restart (`DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 day')`).

### Proteccions addicionals

- Tokens de sessió: `secrets.token_hex(32)` (64 chars; no predictible)
- Caducitat de sessió: **30 dies absoluts** (confirmat propietari 2026-06-15)
- Verificació d'email: obligatòria per accedir a features gated (F2, F3); opcional per als que volen explorar
- Headers de seguretat a nginx: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` (afegir al pla de construcció)

### GDPR — dades mínimes

Dades emmagatzemades per usuari:
- **Email** (identificador, verificació, alertes) — obligatori
- **Hash de la contrasenya** — obligatori
- **Data de creació del compte** — legítim interès
- **IP i user_agent a sessions** — útil per seguretat/debugging; cal mencionar-ho a l'avís de privacitat

**NO emmagatzemar**: nom, telèfon, edat, localitat, ni cap dada de perfil mentre no sigui necessari per a una feature concreta.

### Esborrat de compte (GDPR art. 17 — "dret a l'oblit")

`DELETE FROM users WHERE id = ?` → `ON DELETE CASCADE` a sessions, tokens, lists, alerts. Alternativa: soft-delete (`deleted_at`) per conservar integritat referencial si calen logs d'auditoria.

**Recomanació**: soft-delete + purga automàtica als 30 dies (`deleted_at NOT NULL → 30 dies → DELETE definitiu`).

### Text legal mínim (llista, no redactat)

El pla de construcció haurà d'incloure:
- [ ] Avís de privacitat (qui és el responsable, quines dades, quant de temps, drets de l'usuari)
- [ ] Checkbox de consentiment al registre ("He llegit i accepto la política de privacitat")
- [ ] Enllaç a la política des del footer de les 3 pàgines
- [ ] Procediment d'esborrat de compte (formulari o email a contacte@?)

### Decisions GDPR resoltes (2026-06-15)

- **Q-GDPR-1**: Sí, cal GDPR mínim des del primer dia (avís + checkbox), fins i tot per al betatesting.
- **Q-GDPR-2**: Pendent de confirmar (esborrat automàtic vs via email) — no bloqueja la construcció.

---

## Step 6 — Pla de construcció proposat

### Primer increment demostrable

**Objectiu**: Login funcional (registre → verificació email → login → logout → reset contrasenya) sense cap feature gated. Demostrable al propietari: "registra't, entra, surt, oblida't la contrasenya".

### Seqüència de plans de construcció

```
Plan 016-A  BD + model de dades
  - Crear backend/db.py (connexió, init_db, run_migrations)
  - Crear backend/migrations/001_initial_schema.sql
  - Tests unitaris de db.py
  Esforç estimat: S (2–4h)

Plan 016-B  Backend auth (registre, login, logout, me, verify, forgot, reset)
  - Nous endpoints /api/auth/* a app.py (o blueprint si creix)
  - backend/email_service.py
  - Tests amb mock d'email i BD en memòria (:memory:)
  Esforç estimat: M (6–10h)

Plan 016-C  Frontend auth (UI, auth.js compartit)
  - Pàgina login.html i register.html (noves, minimal)
  - auth.js (header comú, GET /api/auth/me)
  - Integrar header a index.html, historial.html
  Esforç estimat: S-M (4–6h)

Plan 016-D  Hardening i desplegament
  - Rate limiting a login_attempts
  - Headers de seguretat nginx
  - Documentació DEPLOY.md: còpia de seguretat SQLite, variables d'entorn noves
  - Checklist manual VPS
  Esforç estimat: S (2–3h)
```

**Total estimat de construcció**: L (14–23h de dev efectiu, 3–5 sessions)

### Dependències entre plans de construcció

```
016-A → 016-B → 016-C
                016-B → 016-D
```

### Condicions prèvies per començar la construcció

1. Propietari respon Q-EMAIL-1 i Q-EMAIL-2 (proveïdor SMTP, domini)
2. Propietari respon Q-GDPR-1 (confirmar que cal GDPR)
3. Existeix un domini propi (pla 019) o es pot fer servir un subdomini per als emails de verificació

---

## Preguntes obertes per al propietari

### Decisions tècniques

| ID | Pregunta | Per a quin pla | Bloqueja? |
|---|---|---|---|
| Q-EMAIL-1 | Quin domini per enviar emails? | 016-B | **RESOLT**: `roger@masellas.info`; cal validar SPF/DKIM a Brevo |
| Q-EMAIL-2 | Compte Brevo existent o nou? | 016-B | **RESOLT**: compte existent ✓ |
| Q-GDPR-1 | Cal GDPR complet? | 016-C | **RESOLT**: sí, mínim (avís + checkbox) des del primer dia |
| Q-GDPR-2 | Esborrat de compte: des del perfil o via email? | 016-D | Pendent — no bloqueja |
| Q-GATING-1 | Quines features han de requerir login? | 016-C | Pendent — no bloqueja (F2 i F3 segur; resta a confirmar) |
| Q-SESSIONS-1 | Caducitat de sessió: 30 o 7 dies? | 016-B | **RESOLT**: 30 dies ✓ |

### Context extra recomanat

- El propietari hauria de confirmar que el pla 019 (domini propi) es planifica aviat — sense domini propi, els emails de verificació arriben des d'un subdomini provisional i la confiança és baixa.

---

## Resum de decisions

| Decisió | Opció triada | Alternativa descartada | Per canviar cal |
|---|---|---|---|
| Model auth | Email + contrasenya | Magic link, OAuth | Decisió propietari |
| Hash passwords | werkzeug PBKDF2 | bcrypt, argon2 | Dependència nova (no recomanat) |
| Sessions | Cookie HttpOnly + SameSite=Lax | localStorage token | Canvi de disseny (XSS risk) |
| BD | SQLite a backend/data/ | PostgreSQL, fitxers JSON | Canvi d'infra VPS |
| Migracions | Scripts SQL numerats | Alembic | Dependència nova |
| Email relay | Brevo SMTP | SMTP propi VPS | Risc deliverability |
| Rate limit | SQLite login_attempts | Redis, memòria | Dependència nova |
| CORS auth | CORS restringit per a /api/auth/* | Wildcard global | Impacte en cross-origin |
