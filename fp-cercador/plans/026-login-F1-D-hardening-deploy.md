# Plan 026 — Login F1-D: Hardening i documentació de desplegament

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada
> comanda de verificació i confirma el resultat esperat abans de passar al
> pas següent. Si es dona qualsevol condició de la secció "STOP conditions",
> atura't i informa — no improvisis. En acabar, actualitza la fila d'aquest
> pla a `plans/README.md`.
>
> **Context previ**: Llegeix `plans/outputs/spike-login.md` (Step 5 i Step 6)
> i el pla 024 (DONE) ABANS de començar. Els endpoints `/api/auth/*` ja
> existeixen a `backend/app.py`. No reimplementis res de backend.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> ```bash
> python3 -c "
> import sys; sys.path.insert(0, 'backend')
> from app import app
> rules = sorted(r.rule for r in app.url_map.iter_rules() if '/api/auth/' in r.rule)
> assert len(rules) == 7, f'Falten rutes auth: {rules}'
> print('Backend auth OK:', rules)
> "
> # Verificar que init_db NO es crida ara a l'arrencada:
> python3 -c "
> import ast, sys
> src = open('backend/app.py').read()
> assert 'init_db' not in src, 'init_db ja cridat a app.py — re-comprova el scope'
> print('init_db pendent: OK')
> "
> ```
> Si `init_db` ja apareix a `app.py`, para i verifica si el Step 1 d'aquest
> pla ja s'ha executat parcialment.

## Status

- **Priority**: P2
- **Effort**: S (2–3h)
- **Risk**: VERY LOW (canvis additius a app.py; ampliació de DEPLOY.md)
- **Depends on**: 024, 025 (tots DONE)
- **Category**: hardening + docs (F1)
- **Planned at**: 2026-06-15

## Why this matters

Els plans 023-025 han construït el sistema de login sencer, però hi queden
dos forats petits que cal tancar abans de desplegar:

1. `init_db()` no es crida a l'arrencada de l'app: si la BD no existeix al
   VPS, tots els endpoints d'auth fallaran amb `OperationalError` ("no such
   table") en lloc de crear les taules automàticament.
2. La taula `login_attempts` creix sense límit: cada intent de login escriu
   una fila i mai s'esborra. La neteja s'ha de fer a cada restart (és suficient
   per a l'escala actual).
3. `deploy/DEPLOY.md` no documenta les variables d'entorn noves
   (`SECRET_KEY`, `BASE_URL`, `BREVO_*`), la còpia de seguretat SQLite
   ni el checklist de verificació en prod.

## Current state (fets verificats)

- `backend/app.py` — `init_db()` NO es crida; auth endpoints criden directament
  `get_db()` (que NO crea taules); `login_attempts` mai s'esborra.
- `backend/db.py` — `init_db()` existeix i funciona (aplica migracions).
- `backend/.env.example` — conté `SECRET_KEY`, `BASE_URL`, `BREVO_*`, `EMAIL_FROM`.
- `deploy/DEPLOY.md` — secció 3 documenta només `ADMIN_TOKEN`; res de SQLite backup.
- Rate limiting i CORS ja implementats i funcionals (pla 024 + commit 9d7d810).

## Scope

**In scope**:
- `backend/app.py` — afegir crida a `init_db()` a l'arrencada + neteja de
  `login_attempts` antics
- `deploy/DEPLOY.md` — ampliar secció 3 (env vars) + noves seccions (BD, backup,
  checklist VPS, headers nginx)

**Out of scope**: cap canvi a `db.py`, cap canvi a les rutes auth, cap canvi
al frontend, cap cron extern.

## Steps

### Step 1 — Afegir `init_db()` + neteja `login_attempts` a `app.py`

**Problema**: `app.py` importa `db` als endpoints però no crida `init_db()`
a l'arrencada. Si la BD no existeix en un VPS nou, el primer login retornarà
500 en lloc de funcionar.

**Solució**: afegir un bloc d'inicialització just ABANS de
`scheduler_service.init_scheduler()` (línia ~118). El lloc exacte és
important: ha d'anar ABANS d'arrancar el scheduler (que podria dependre de
la BD en futures fases) però DESPRÉS de `load_dotenv()`.

**Canvi exacte a `backend/app.py`**:

Localitza el bloc:
```python
# Phase 6 (D-06/D-07): Arrenca APScheduler i programa el job persistit (si enabled).
scheduler_service.init_scheduler()
```

I afegeix **just ABANS** (no tocar res més):
```python
# Inicialitza la BD (crea les taules si no existeixen via migracions).
# Neteja les entrades antigues de login_attempts (> 1 dia) a cada restart;
# evita creixement il·limitat sense necessitat de cron extern.
import db as _db_init
_db_conn = _db_init.init_db()
_db_conn.execute(
    "DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 day')"
)
_db_conn.commit()
_db_conn.close()
del _db_conn, _db_init
```

**Per què `del` al final**: evita contaminar el namespace global del mòdul
amb variables d'inicialització puntuals. Les crides posteriors a `db` als
endpoints seguiran fent `import db as _db` localment, com ara.

**Verificació**:
```bash
python3 -c "
import sys; sys.path.insert(0, 'backend')
# Ha d'arrencar sense errors (la BD s'inicialitzarà o ja existirà)
from app import app
print('app arrenca OK')
rules = sorted(r.rule for r in app.url_map.iter_rules() if '/api/auth/' in r.rule)
assert len(rules) == 7, f'Rutes auth perdudes: {rules}'
print('Rutes auth OK:', rules)
"
```

```bash
# Verificar que init_db ara apareix a app.py
python3 -c "
src = open('backend/app.py').read()
assert 'init_db' in src, 'init_db no trobat a app.py'
assert 'login_attempts' in src, 'neteja login_attempts no trobada'
print('Canvi app.py OK')
"
```

### Step 2 — Ampliar `deploy/DEPLOY.md`

`deploy/DEPLOY.md` (a `../deploy/DEPLOY.md` relatiu a `fp-cercador/`) cal
ampliar en quatre punts. **NO esborrar cap secció existent.**

#### 2a — Ampliar secció 3 (variables d'entorn)

La secció 3 actual documenta només `ADMIN_TOKEN`. Substituir el bloc
`.env` per la llista completa de variables requerides i opcionals:

```markdown
El `.env` ha de contenir (vegeu `fp-cercador/backend/.env.example`):

```
# — Obligatori —
ADMIN_TOKEN=<token-segur-aleatori>
SECRET_KEY=<token-segur-aleatori>   # python3 -c "import secrets; print(secrets.token_hex(32))"
BASE_URL=https://<el-teu-domini>    # sense trailing slash; usat als emails d'auth

# — Email (Brevo SMTP) —
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=<compte@domini.com>
BREVO_SMTP_KEY=<API_key_brevo>
EMAIL_FROM=noreply@<domini.com>
EMAIL_FROM_NAME=Cercador FP España

# — Brevo API (novetats/newsletters, opcional) —
BREVO_API_KEY=
BREVO_LIST_ID=
BREVO_SENDER_EMAIL=
BREVO_SENDER_NAME=Cercador FP España
```

> Si `SECRET_KEY` és buit, l'app arrenca però mostra un warning als logs.
> Si `BREVO_SMTP_KEY` és buit, els emails d'auth (verificació, reset
> contrasenya) no s'envien però el registre i el login segueixen funcionant.
```

#### 2b — Nova secció: Base de dades SQLite

Afegir com a nova **secció 9** (just ABANS de "Gestió del servei"):

```markdown
## 9. Base de dades SQLite

La BD (`backend/data/fp_cercador.db`) es crea automàticament la primera
vegada que arrenca l'app. No cal cap pas manual de migració: `init_db()`
aplica els scripts de `backend/migrations/` en ordre.

**Còpia de seguretat (cron nocturn)**

```bash
# Crear directori de backups
mkdir -p /home/masellas-grausfp/backups/fp-cercador

# Afegir al cron de root (crontab -e):
0 3 * * * sqlite3 /home/masellas-grausfp/htdocs/grausfp.masellas.info/fp-cercador/backend/data/fp_cercador.db \
    ".backup /home/masellas-grausfp/backups/fp-cercador/fp_cercador_$(date +\%Y\%m\%d).db" && \
    find /home/masellas-grausfp/backups/fp-cercador -name "*.db" -mtime +7 -delete
```

El cron executa a les 3h, fa el backup, i esborra els fitxers de més de
7 dies. Verificar que funciona el dia següent:
```bash
ls -lh /home/masellas-grausfp/backups/fp-cercador/
```
```

#### 2c — Nova secció: Checklist VPS auth

Afegir com a nova **secció 10**:

```markdown
## 10. Checklist de verificació auth en producció

Abans de donar per bo el desplegament d'auth (F1), comprova:

- [ ] **Same-origin**: el frontend i el backend se serveixen des del mateix
  domini (nginx fa proxy de `/api/` al port 8033). Les cookies d'auth no
  necessiten CORS en producció — same-origin és transparent.
- [ ] **Cookie Secure**: quan l'app corre amb gunicorn (no amb `FLASK_DEBUG=1`),
  `app.debug` és `False` i les cookies es generen amb `Secure=True`
  automàticament. Verificar:
  ```bash
  curl -c /tmp/cookies.txt -X POST https://<DOMINI>/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@test.com","password":"wrongpw"}' -v 2>&1 | grep -i "set-cookie"
  # Ha de mostrar: Secure; HttpOnly; SameSite=Lax
  ```
- [ ] **Email d'auth funcional**: registra un compte de prova i verifica que
  arriba l'email de verificació. Comprova els logs si no arriba:
  ```bash
  journalctl -u fp-cercador -f | grep "Error enviant"
  ```
- [ ] **Rate limiting**: comprova que 6 intents de login fallits des d'una
  mateixa IP retornen 429.
- [ ] **BD creada**: `ls -lh backend/data/fp_cercador.db` — ha d'existir i
  tenir mida > 0 després del primer arranc.

**Headers de seguretat nginx (recomanat)**

Afegir al bloc `server` de `deploy/nginx-cloudpanel.conf` (o via CloudPanel UI
> Nginx Configuration > Vhost):

```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

Recorda recarregar nginx: `nginx -t && systemctl reload nginx`.
```

**Verificació del Step 2**:
```bash
# deploy/DEPLOY.md modificat i conté les seccions noves
python3 -c "
text = open('../deploy/DEPLOY.md').read()
assert 'SECRET_KEY' in text, 'Falta SECRET_KEY'
assert 'BREVO_SMTP' in text, 'Falta BREVO_SMTP'
assert 'sqlite3' in text, 'Falta backup SQLite'
assert 'Checklist' in text, 'Falta checklist VPS'
assert 'X-Frame-Options' in text, 'Falten headers nginx'
print('DEPLOY.md OK')
"
```

### Step 3 — Verificació final integrada

```bash
# 1. app.py: init_db i neteja presents; rutes auth intactes; backend arrenca
python3 -c "
import sys; sys.path.insert(0, 'backend')
src = open('backend/app.py').read()
assert 'init_db' in src
assert 'login_attempts' in src and \"datetime('now', '-1 day')\" in src
from app import app
rules = sorted(r.rule for r in app.url_map.iter_rules() if '/api/auth/' in r.rule)
assert len(rules) == 7, f'Rutes auth: {rules}'
print('app.py OK:', rules)
"

# 2. deploy/DEPLOY.md: variables i seccions noves
python3 -c "
text = open('../deploy/DEPLOY.md').read()
for kw in ['SECRET_KEY', 'BASE_URL', 'BREVO_SMTP_KEY', 'sqlite3', 'Checklist', 'X-Frame-Options']:
    assert kw in text, f'Falta: {kw}'
print('DEPLOY.md OK')
"

# 3. Fitxers modificats: NOMÉS app.py i ../deploy/DEPLOY.md
git diff --name-only
# Esperat: backend/app.py  (i el deploy/DEPLOY.md apareixerà al repo pare)
```

## Done criteria

- [ ] `backend/app.py` crida `init_db()` a l'arrencada (abans de `scheduler_service.init_scheduler()`)
- [ ] `backend/app.py` fa `DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-1 day')` a cada arrencada
- [ ] `python3 -c "from app import app; print('OK')"` (des de `backend/`) no llança errors
- [ ] 7 rutes `/api/auth/*` segueixen presents i sense canvis
- [ ] `deploy/DEPLOY.md` documenta `SECRET_KEY`, `BASE_URL`, `BREVO_SMTP_KEY`
- [ ] `deploy/DEPLOY.md` documenta la còpia de seguretat SQLite amb cron + rotació 7 dies
- [ ] `deploy/DEPLOY.md` conté el checklist de verificació en producció
- [ ] `deploy/DEPLOY.md` menciona els headers de seguretat nginx (com a nota/recomanació)
- [ ] Cap fitxer de frontend modificat
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- Tentació de moure `init_db()` dins de `db.py` com a efecte secundari d'`import db` → STOP: l'efecte de module-level és sorprenent i dificulta els tests
- Tentació d'afegir un cron de Python dins de l'app per a la neteja de `login_attempts` → STOP: el restart és suficient per a l'escala actual
- Tentació de tocar `auth_login()` o qualsevol endpoint auth → STOP: el pla 024 ja és definitiu
- Tentació de moure `deploy/DEPLOY.md` dins del repo `fp-cercador/` → STOP: viu a `../deploy/` per disseny (separa el codi del deploy)

## Maintenance notes

- La neteja de `login_attempts` al restart és suficient per a l'escala actual
  (registres públics, no alta càrrega). Si el VPS mai va 30+ dies sense restart,
  s'acumularan files d'1 dia a 30 dies, cosa acceptable. Un cron extern
  setmanal es pot afegir com a millora futura.
- `SECRET_KEY` es llegeix a `app.py` però encara no s'usa (reservat per a
  futura protecció CSRF). No fa res si és buit, però documentar-lo és
  important per no oblidar-lo en el desplegament inicial.
- El deploy es fa contra `../deploy/DEPLOY.md` (fora del repositori `fp-cercador`).
  El commit d'aquest pla ha d'incloure els canvis a `backend/app.py`; els canvis
  a `../deploy/DEPLOY.md` poden anar al mateix commit si el git arrel és el del
  projecte pare, o en un commit separat si cal.
