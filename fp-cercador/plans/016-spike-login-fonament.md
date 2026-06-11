# Plan 016: [SPIKE — F1] Dissenyar el sistema de comptes d'usuari (fonament del roadmap)

> **Executor instructions**: Aquest és un pla d'INVESTIGACIÓ I DISSENY, no de
> construcció. El lliurable és un document de disseny a `plans/outputs/`, NO
> codi de producció (prototips puntuals només si són descartables i queden a
> `plans/outputs/`). Si es dona una STOP condition, atura't i informa. En
> acabar, actualitza la fila d'aquest pla a `plans/README.md`.
>
> **Context obligatori**: llegeix primer `plans/futures/ROADMAP-FEATURES.md`
> (F1 i les features que en depenen: F2, F3, F4, F8, F10) — el disseny del
> login ha de servir-les totes sense reescriptures.

## Status

- **Priority**: P2 (fonament de l'onada 2 del roadmap)
- **Effort**: M (disseny; la construcció posterior serà L)
- **Risk**: LOW (cap canvi de codi en aquest pla)
- **Depends on**: cap (recomanat amb 001–007 DONE per tenir base sanejada)
- **Category**: direction
- **Planned at**: commit `5dc92a1`, 2026-06-10

## Why this matters

Tot el roadmap privat (favorits, alertes, seguiment de centres, exportació,
API amb token) penja d'un sistema de comptes que avui no existeix. És la
primera vegada que el projecte tindrà base de dades i estat per usuari: les
decisions d'aquest spike (model d'auth, emmagatzematge, sessions, email)
condicionen anys de manteniment. Un disseny equivocat aquí (p. ex. una
dependència pesada d'auth, o un model de sessió que no funcioni amb el
frontend estàtic servit per nginx) costaria car de desfer.

## Current state (fets del codebase rellevants per al disseny)

- Backend: Flask pur, una sola app (`backend/app.py`), sense BD — tot són
  fitxers JSON a `backend/data/`. Auth existent: un sol `ADMIN_TOKEN`
  Bearer comparat amb `hmac.compare_digest` (`app.py:71-77`).
- Frontend: 3 pàgines estàtiques servides per nginx directament
  (`deploy/nginx-cloudpanel.conf`), API sota `/api/` proxy a gunicorn
  (mateix origen → les cookies de sessió funcionen sense CORS exòtic;
  però en local el frontend s'obre per `file://` o `localhost` contra
  `localhost:5001` — el disseny ha de cobrir els dos entorns).
- Desplegament: gunicorn 1 worker + threads (pla 004) — l'estat en memòria
  per-procés és acceptable, però les sessions han de sobreviure restarts.
- Constraint de dependències: les 6 actuals. Bona notícia verificada:
  **SQLite (`sqlite3`) i email (`smtplib`) són stdlib, i el hashing de
  contrasenyes (`werkzeug.security`) ve amb Flask** — un login complet és
  viable amb ZERO dependències noves. El disseny ha de justificar qualsevol
  excepció.
- CORS global (`CORS(app)` a `app.py:59`): amb cookies de sessió caldrà
  revisar-ho (credentials + wildcard són incompatibles) — punt de disseny.

## Scope

**In scope**: crear `plans/outputs/spike-login.md`.

**Out of scope**: QUALSEVOL canvi a `backend/`, `frontend/`, `deploy/`.
Cap decisió sobre QUINES features es gategen (això és del roadmap, no del
login).

## Steps (decisions a documentar, amb opcions i recomanació)

### Step 1: Model d'autenticació

Compara com a mínim: (a) email + contrasenya clàssic, (b) magic link per
email (sense contrasenya — interessant perquè F3 ja necessita enviar
emails), (c) OAuth de tercers (Google). Criteris: fricció per a l'usuari
objectiu (famílies i orientadors, no tècnics), cost d'implementació amb
stdlib, recuperació de compte, i GDPR (mínim de dades possible).

### Step 2: Emmagatzematge

Disseny de l'esquema SQLite (taules: users, sessions/tokens, i les que F2/F3
necessitaran: lists, list_items, alerts — esbossar-les ja perquè l'esquema
no es quedi curt). On viu el fitxer `.db` (proposta: `backend/data/`, ja
ignorat pel pla 010), estratègia de migracions (scripts numerats? — mantenir
simple), i còpia de seguretat al VPS.

### Step 3: Sessions i frontend

Cookie de sessió HttpOnly+Secure+SameSite vs token en localStorage. Atenció
als dos entorns (producció mateix-origen via nginx; local `file://` o
localhost:5001 cross-port). Implicació sobre `CORS(app)` actual. Com es
reflecteix l'estat "loguejat" a les 3 pàgines estàtiques (header comú?
fragment JS compartit?).

### Step 4: Email

Necessari per a verificació/magic link i compartit amb F3 (alertes). Opcions:
smtplib + SMTP del VPS o d'un proveïdor (quin?), límits d'enviament,
plantilles. Decisió de proveïdor → demanar al propietari si ja té SMTP.

### Step 5: Seguretat i GDPR

Rate limiting de login (sense dependències noves — comptador en memòria o
SQLite?), hashing (werkzeug `generate_password_hash`), política de dades
mínimes, esborrat de compte, text legal mínim (avís de privacitat) — llista
del que cal, no redactar-lo.

### Step 6: Pla de construcció proposat

Seqüència de plans de construcció amb estimacions (p. ex. BD+registre+login;
sessions+UI; email). Definir el "primer increment demostrable" (login
funcional sense cap feature gated encara).

## Done criteria

- [ ] `plans/outputs/spike-login.md` existeix i cobreix els Steps 1–6 amb recomanació justificada a cada decisió
- [ ] L'esquema SQLite proposat cobreix també F2/F3 (llistes i alertes)
- [ ] Inclou el flux d'auth dibuixat pas a pas (registre, login, logout, recuperació)
- [ ] Inclou la llista de preguntes obertes per al propietari (SMTP, GDPR, gating)
- [ ] Cap fitxer fora de `plans/` modificat (`git status`)
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- El disseny "necessita" una dependència nova d'auth (Flask-Login,
  Authlib...) → no la incorporis per defecte: documenta el trade-off
  stdlib-vs-dependència i deixa la decisió al propietari.
- Qualsevol temptació d'escriure codi de producció "ja que hi som" → STOP,
  és un spike.

## Maintenance notes

- Aquest disseny és el fonament de F2, F3, F4, F8 i F10 — qualsevol canvi
  posterior al model de sessions o a l'esquema els afecta tots.
- El pla 017 (alertes) llegeix l'output d'aquest spike; executar 016 primer.
