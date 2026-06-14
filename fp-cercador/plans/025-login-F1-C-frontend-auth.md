# Plan 025 — Login F1-C: Frontend auth (pàgines + auth.js)

> **Executor instructions**: Segueix aquest pla pas a pas. Executa cada
> comanda de verificació i confirma el resultat esperat abans de passar al
> pas següent. Si es dona qualsevol condició de la secció "STOP conditions",
> atura't i informa — no improvisis. En acabar, actualitza la fila d'aquest
> pla a `plans/README.md`.
>
> **Context previ**: Llegeix `plans/outputs/spike-login.md` (Step 3 i Step 5)
> i el pla 024 (ja DONE) ABANS de començar. Els endpoints `/api/auth/*` ja
> existeixen a `backend/app.py`. No tornis a implementar cap lògica de backend.
>
> **Drift check (executa primer, des de `fp-cercador/`)**:
> ```bash
> ls frontend/auth.js 2>/dev/null && echo "auth.js JA EXISTEIX" || echo "auth.js no existeix (esperat)"
> ls frontend/login.html 2>/dev/null && echo "login.html JA EXISTEIX" || echo "login.html no existeix (esperat)"
> python3 -c "
> import sys; sys.path.insert(0, 'backend')
> from app import app
> rules = [r.rule for r in app.url_map.iter_rules() if '/api/auth/' in r.rule]
> assert len(rules) == 7, f'Falten rutes auth: {rules}'
> print('Backend auth OK:', sorted(rules))
> "
> ```
> Si `auth.js` o `login.html` ja existeixen, atura't.

## Status

- **Priority**: P2
- **Effort**: S-M (4–6h)
- **Risk**: LOW (fitxers nous; les modificacions a index.html i historial.html
  són additives — no alteren cap lògica existent)
- **Depends on**: 024 (DONE)
- **Category**: feature (F1)
- **Planned at**: 2026-06-15

## Why this matters

El backend d'auth és complet però invisible: cap usuari pot registrar-se ni
entrar perquè no existeix cap interfície. Aquest pla tanca el primer increment
demostrable: un usuari pot obrir el navegador, registrar-se, verificar el seu
email, iniciar sessió i veure el seu estat a totes les pàgines.

## Current state (fets verificats)

- `backend/app.py` — 7 endpoints `/api/auth/*` (register, verify, login,
  logout, me, forgot-password, reset-password) + `_get_session_user()`
- `frontend/index.html` — topbar amb `<span class="topbar-logo">GrausFP</span>`,
  sense cap widget auth; usa Alpine.js (x-data="cercador")
- `frontend/historial.html` — topbar similar, logo com a `<a>`, sense widget
- `frontend/admin.html` — topbar independent; admin usa Bearer token, no cookies
- Paleta CSS: `--dark #1c1410`, `--warm #8a7060`, `--warm2 #f5ece2`,
  `--border #e8ddd4`, `--bg #fdf8f2`, `--white #ffffff`
- Tipografies: DM Sans (cos), DM Serif Display (títols), Geist Mono (codi)
- API_BASE: `http://localhost:5001` en local, `''` en producció (same-origin)

## Scope

**In scope**:
- `frontend/auth.js` — JS vanilla: `GET /api/auth/me` → injecta widget al
  topbar (estat loguejat o botons Entra/Registra't); `POST /api/auth/logout`
- `frontend/login.html` — formulari login + link "Has oblidat la contrasenya?"
- `frontend/register.html` — formulari registre + checkbox GDPR + avís de
  privacitat breu (text provisional)
- `frontend/reset-password.html` — formulari nova contrasenya (llegeix
  `?token=` de la URL; fa `POST /api/auth/reset-password`)
- `frontend/index.html` — afegir `<script src="auth.js"></script>` + placeholder
  `#auth-widget` al topbar
- `frontend/historial.html` — afegir `<script src="auth.js"></script>` +
  placeholder `#auth-widget` al topbar

**Out of scope**: cap canvi a `admin.html`, cap gating de features (quina
funcionalitat requereix login queda per un pla futur), cap canvi al backend.

## Steps

### Step 1 — `frontend/auth.js`

Mòdul vanilla pur (~90 línies). Es carrega a totes les pàgines. La seva
única responsabilitat és: comprovar si hi ha sessió activa i actualitzar el
widget `#auth-widget` del topbar.

**Comportament**:
- Al `DOMContentLoaded`: `GET /api/auth/me`
  - 200 `{email}` → substitueix `#auth-widget` per: `Hola, <email>` + botó
    "Sortir"
  - 401 / error → substitueix `#auth-widget` per: botons "Entra" i
    "Registra't"
- El botó "Sortir" fa `POST /api/auth/logout` i recarrega la pàgina.
- `API_BASE`: `http://localhost:5001` si `localhost`, `''` si no (consistent
  amb index.html).
- Les pàgines de login/register/reset-password NO inclouen `auth.js` (no
  té sentit mostrar el widget en les pròpies pàgines d'auth).

**Implementació**:

```javascript
(function () {
  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5001' : '';

  async function initAuth() {
    const widget = document.getElementById('auth-widget');
    if (!widget) return;

    try {
      const res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (res.ok) {
        const { email } = await res.json();
        widget.innerHTML =
          `<span class="auth-greeting">Hola, ${escHtml(email)}</span>` +
          `<button class="auth-btn auth-btn--logout" id="btn-logout">Sortir</button>`;
        document.getElementById('btn-logout').addEventListener('click', logout);
      } else {
        showGuestButtons(widget);
      }
    } catch (_) {
      showGuestButtons(widget);
    }
  }

  function showGuestButtons(widget) {
    widget.innerHTML =
      `<a class="auth-btn" href="login.html">Entra</a>` +
      `<a class="auth-btn auth-btn--primary" href="register.html">Registra't</a>`;
  }

  async function logout() {
    await fetch(API_BASE + '/api/auth/logout', {
      method: 'POST', credentials: 'include'
    });
    window.location.reload();
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  document.addEventListener('DOMContentLoaded', initAuth);
})();
```

**CSS dels botons** (injectat via `<style>` inline a auth.js NO; s'afegeix
a cada pàgina que l'inclou — veure Steps 4 i 5):

```css
/* Auth widget al topbar */
#auth-widget { margin-left: auto; display: flex; align-items: center; gap: 8px; }
.auth-greeting { color: rgba(255,255,255,0.75); font-size: 13px; }
.auth-btn {
  font-size: 13px; padding: 5px 14px; border-radius: 4px;
  border: 1px solid rgba(255,255,255,0.35); color: var(--white);
  background: transparent; cursor: pointer; text-decoration: none;
  font-family: inherit; transition: background 0.15s;
}
.auth-btn:hover { background: rgba(255,255,255,0.12); }
.auth-btn--primary {
  background: var(--white); color: var(--dark); border-color: var(--white);
}
.auth-btn--primary:hover { background: var(--warm2); }
.auth-btn--logout { border-color: rgba(255,255,255,0.25); }
```

**Verificació**:
```bash
ls frontend/auth.js && echo "OK"
```

### Step 2 — `frontend/login.html`

Pàgina mínima consistent amb l'estil existent. Inclou:
- Topbar amb logo (link a `index.html`) — sense widget auth
- Formulari: camps `email` + `password` + botó "Entra"
- Link "Has oblidat la contrasenya?" → `forgot-password.html` (pàgina
  simple que es crea a Step 2b) — veure nota
- Link "Crea un compte" → `register.html`
- JS inline: `POST /api/auth/login`; en cas d'èxit redirigeix a `index.html`;
  mostra errors en línia (`#msg`)
- Afegir a la URL `?verified=1` si ve de la verificació d'email

**Nota sobre "has oblidat la contrasenya"**: el flux és:
1. Usuari va a `forgot-password.html` (formulari simple: email → `POST
   /api/auth/forgot-password`); es crea com a **Step 2b** d'aquest pla.
2. L'email que rep l'usuari conté un link a `reset-password.html?token=…`
   (Step 3 d'aquest pla).

**Estructura HTML** (seguint la paleta i tipografies de les pàgines existents):

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Inicia sessió — Cercador Graus FP</title>
  <link rel="icon" type="image/png" href="favicon.png">
  <!-- fonts iguals que les altres pàgines -->
  <style>
    /* paleta, topbar, formulari centrat */
  </style>
</head>
<body>
  <div class="topbar"><div class="topbar-inner">
    <a class="topbar-logo" href="index.html">GrausFP</a>
  </div></div>

  <div class="auth-page">
    <h1>Inicia sessió</h1>
    <p id="msg" class="msg" hidden></p>
    <form id="form-login">
      <label for="email">Email</label>
      <input type="email" id="email" required autocomplete="email">
      <label for="password">Contrasenya</label>
      <input type="password" id="password" required autocomplete="current-password">
      <button type="submit">Entra</button>
    </form>
    <p class="auth-links">
      <a href="forgot-password.html">Has oblidat la contrasenya?</a>
    </p>
    <p class="auth-links">
      Sense compte? <a href="register.html">Registra't</a>
    </p>
  </div>

  <script>/* POST /api/auth/login */</script>
</body>
</html>
```

**Verificació**:
```bash
ls frontend/login.html && echo "OK"
```

### Step 2b — `frontend/forgot-password.html`

Pàgina mínima per sol·licitar el reset de contrasenya. No és al scope original
del prompt però és necessària per tancar el flux complet (el link de
`login.html` hi apunta). Inclou:
- Topbar amb logo
- Formulari: camp `email` + botó "Envia el link"
- Missatge d'èxit genèric: "Si l'email existeix, rebràs un missatge en breus."
  (no revela si l'email existeix — consistent amb el backend)
- JS inline: `POST /api/auth/forgot-password`

**Verificació**:
```bash
ls frontend/forgot-password.html && echo "OK"
```

### Step 3 — `frontend/reset-password.html`

Pàgina per introduir la nova contrasenya. El token arriba via `?token=` a la URL.

- Si no hi ha token a la URL → mostra error "Enllaç invàlid o caducat".
- Formulari: `nova contrasenya` + `confirmar contrasenya` + botó "Desa la
  contrasenya"
- Validació client: les dues contrasenyes han de coincidir i tenir ≥ 8 caràcters
- JS inline: llegeix `token` de `URLSearchParams`; `POST /api/auth/reset-password
  {token, password}`; en cas d'èxit → missatge de confirmació + link a `login.html`

**Verificació**:
```bash
ls frontend/reset-password.html && echo "OK"
```

### Step 4 — `frontend/register.html`

Formulari de registre amb GDPR mínim (Q-GDPR-1: resolt, cal des del primer dia).

Camps:
- `email` (obligatori)
- `password` (obligatori, ≥ 8 caràcters)
- `confirm-password` (obligatori, ha de coincidir)
- Checkbox `gdpr-consent` (obligatori): "He llegit i accepto la
  [política de privacitat](#)" — el link és un `<a>` a `politica-privacitat.html`
  (pàgina stub que es crea a Step 4b)
- Botó "Crea el compte"

Missatge post-registre (no redirigeix automàticament):
> "Compte creat. Revisa el teu email per verificar-lo."

Link "Ja tens compte? Entra" → `login.html`

**GDPR**: el formulari no es pot enviar sense el checkbox marcat (atribut
`required` al `<input type="checkbox">`). El text del checkbox i la política
de privacitat són **provisionals** — es poliran abans del llançament públic.

**Verificació**:
```bash
ls frontend/register.html && echo "OK"
```

### Step 4b — `frontend/politica-privacitat.html`

Pàgina stub amb l'avís de privacitat mínim requerit per GDPR. Conté:
- Topbar amb logo
- Títol "Política de privacitat (provisional)"
- Avís que és provisional i es completarà abans del llançament públic
- Dades emmagatzemades: email, hash de contrasenya, data de creació, IP i
  user-agent de sessions
- Finalitat: autenticació i, en el futur, alertes personalitzades
- Drets de l'usuari: accés, rectificació, supressió (esborrat via email a
  roger@lamosca.com mentre no hi hagi formulari integrat)
- Responsable: Roger Masellas, roger@lamosca.com

**Verificació**:
```bash
ls frontend/politica-privacitat.html && echo "OK"
```

### Step 5 — Afegir `auth.js` + widget a `index.html`

**Canvis mínims additius** a `frontend/index.html`:

1. Afegir CSS del widget auth (els estils de `.auth-btn`, `#auth-widget`, etc.)
   dins del `<style>` existent, just abans del `</style>`.

2. Afegir `<div id="auth-widget"></div>` al topbar, just a continuació de
   `<span class="topbar-logo">GrausFP</span>`.

3. Afegir `<script src="auth.js"></script>` just ABANS del
   `<script defer src="vendor/alpinejs-3.15.11.min.js"></script>` (dins del
   `<head>`). `auth.js` usa `DOMContentLoaded` — no interfereix amb Alpine.

**Canvis exactes** (no tocar res més):

```html
<!-- TOPBAR — canvi: afegir div#auth-widget -->
<div class="topbar-inner">
  <span class="topbar-logo">GrausFP</span>
  <div id="auth-widget"></div>      <!-- NOU -->
</div>
```

**Verificació**:
```bash
python3 -c "
import re
html = open('frontend/index.html').read()
assert 'auth-widget' in html, 'Falta #auth-widget'
assert 'auth.js' in html, 'Falta <script src=auth.js>'
print('index.html OK')
"
```

### Step 6 — Afegir `auth.js` + widget a `historial.html`

Idèntic a Step 5 però a `frontend/historial.html`.

El topbar de historial ja té el logo com a `<a class="topbar-logo"
href="index.html">GrausFP</a>` — no canviar-lo, només afegir el widget.

**Verificació**:
```bash
python3 -c "
html = open('frontend/historial.html').read()
assert 'auth-widget' in html, 'Falta #auth-widget'
assert 'auth.js' in html, 'Falta <script src=auth.js>'
print('historial.html OK')
"
```

### Step 7 — Verificació final integrada

```bash
# 1. Tots els fitxers nous existeixen
ls frontend/auth.js frontend/login.html frontend/register.html \
   frontend/reset-password.html frontend/forgot-password.html \
   frontend/politica-privacitat.html
echo "Fitxers nous OK"

# 2. index.html i historial.html modificats, admin.html intacte
python3 -c "
for f in ['frontend/index.html', 'frontend/historial.html']:
    html = open(f).read()
    assert 'auth-widget' in html and 'auth.js' in html, f'{f} incomplet'
admin = open('frontend/admin.html').read()
assert 'auth.js' not in admin, 'admin.html no hauria de tenir auth.js'
print('HTML OK')
"

# 3. Backend: els endpoints existents no s'han tocat
python3 -c "
import sys; sys.path.insert(0,'backend')
from app import app
rules = sorted(r.rule for r in app.url_map.iter_rules() if '/api/auth/' in r.rule)
assert len(rules) == 7, f'Rutes auth canviades: {rules}'
print('Backend intacte:', rules)
"

# 4. Cap fitxer de backend modificat
git diff --name-only | grep "^backend/" && echo "ALERTA: backend modificat" || echo "Backend net"

# 5. Fitxers modificats esperats
git diff --name-only
# Ha de mostrar NOMÉS: frontend/index.html, frontend/historial.html
# (els fitxers nous apareixeran com a "untracked" en git status, no en git diff)
```

## Done criteria

- [ ] `frontend/auth.js` existeix: `initAuth()`, `showGuestButtons()`, `logout()`
- [ ] `frontend/login.html` existeix: formulari login, link a forgot-password i register
- [ ] `frontend/forgot-password.html` existeix: formulari email, crida a `/api/auth/forgot-password`
- [ ] `frontend/register.html` existeix: formulari registre, checkbox GDPR required
- [ ] `frontend/reset-password.html` existeix: llegeix `?token=`, crida a `/api/auth/reset-password`
- [ ] `frontend/politica-privacitat.html` existeix: avís GDPR provisional
- [ ] `frontend/index.html` té `#auth-widget` al topbar i `<script src="auth.js">`
- [ ] `frontend/historial.html` té `#auth-widget` al topbar i `<script src="auth.js">`
- [ ] `frontend/admin.html` no ha estat modificat
- [ ] `git diff --name-only` mostra NOMÉS `frontend/index.html` i `frontend/historial.html`
- [ ] Fila actualitzada a `plans/README.md`

## STOP conditions

- Tentació de modificar `backend/app.py` o qualsevol fitxer backend → STOP: tot el backend ja és al pla 024
- Tentació d'implementar gating (restringir accés a features per login) → STOP: pla futur
- Tentació d'usar Alpine.js per a les pàgines noves → STOP: auth.js és vanilla pur; Alpine és NOMÉS a index.html
- `admin.html` es modifica en qualsevol forma → STOP: admin usa Bearer token, no cookies d'usuari

## Maintenance notes

- `auth.js` usa `credentials: 'include'` a cada `fetch` per enviar la cookie
  de sessió en peticions cross-origin (localhost dev); en producció same-origin
  és transparent.
- El CSS del widget auth es duplica a index.html i historial.html perquè cada
  pàgina té el seu propi `<style>` inline. Si creix, es pot externalitzar a
  un `auth.css` en un pla futur, però ara no cal.
- Les pàgines d'auth (login, register, reset, forgot-password) no inclouen
  `auth.js` intencionadament: no té sentit comprovar si l'usuari ja és loguejat
  en la pàgina de login (afegir redirect automàtic queda per un pla futur).
- El text de la política de privacitat és provisional. Marcar-lo explícitament
  com a "PROVISIONAL" al `<body>` perquè no es publiqui sense revisar.
