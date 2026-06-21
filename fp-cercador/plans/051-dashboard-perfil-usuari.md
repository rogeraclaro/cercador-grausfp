# Pla 051 — Dashboard d'usuari centralitzat (`perfil.html`)

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md` — unless a reviewer dispatched you and told you they
> maintain the index.
>
> **Drift check (run first)**:
> ```bash
> git diff --stat 3301aa2..HEAD -- frontend/auth.js frontend/i18n.js
> ```
> Si algun d'aquests fitxers ha canviat des que el pla va ser escrit, compara
> els excerpts de "Current state" amb el codi viu. Si no coincideixen, STOP.

## Status

- **Priority**: P2
- **Effort**: M
- **Risk**: LOW
- **Depends on**: plans 023–029 (F1–F3 DONE — login, favorits, alertes, seguiment existents)
- **Category**: direction
- **Planned at**: commit `3301aa2`, 2026-06-21

## Why this matters

Les features d'usuari (favorits, alertes, seguiment de centres) estan disperses:
els favorits viu dins `index.html`, les alertes a `alertes.html`, el seguiment a
`seguiment.html`. Un usuari nou no sap on trobar el seu compte. No hi ha cap
pàgina "hub" ni cap nav visible que les lligui. Afegir `perfil.html` i un link
"El meu perfil" al widget d'auth consolida la inversió de F1–F4 amb cost
frontend pur: cap nou endpoint de backend, cap nova dependència.

## Current state

### Fitxers rellevants

- `frontend/auth.js` — widget d'auth de la topbar; injecta l'HTML a `#auth-widget`
- `frontend/i18n.js` — totes les traduccions (CA + ES), ~500 línies
- `frontend/alertes.html` + `frontend/alertes.js` — pàgina d'alertes existent
- `frontend/seguiment.html` — pàgina de seguiment existent (JS inline)
- `backend/app.py` — endpoints que es reutilitzen: `/api/auth/me`, `/api/favorites`,
  `/api/alerts`, `/api/centres-watch`. **No cal modificar-lo.**

### Excerpt auth.js — bloc logged-in (línies 10–15)

```javascript
        widget.innerHTML =
          '<span class="auth-greeting">' + t('nav.greeting', { email: escHtml(data.email) }) + '</span>' +
          '<button class="auth-btn auth-btn--logout" id="btn-logout">' + t('nav.logout') + '</button>';
        document.getElementById('btn-logout').addEventListener('click', logout);
```

### Excerpt i18n.js — bloc nav CA (línies 5–10)

```javascript
      'nav.greeting': 'Hola, {email}',
      'nav.logout': 'Sortir',
      'nav.login': 'Entra',
      'nav.register': "Registra't",
      'nav.lang.ca': 'CA',
      'nav.lang.es': 'ES',
```

### Excerpt i18n.js — bloc nav ES (línies 296–301)

```javascript
      'nav.greeting': 'Hola, {email}',
      'nav.logout': 'Salir',
      'nav.login': 'Entrar',
      'nav.register': 'Regístrate',
      'nav.lang.ca': 'CA',
      'nav.lang.es': 'ES',
```

### API endpoints que `perfil.html` usarà

| Endpoint | Mètode | Retorna |
|----------|--------|---------|
| `/api/auth/me` | GET | `{id, email, is_admin}` o 401 |
| `/api/favorites` | GET | `[{oferta_id, oferta_codigo, added_at}]` |
| `/api/alerts` | GET | `[{id, filter_json, active, created_at, last_sent_at}]` |
| `/api/alerts/:id` | DELETE | 204 |
| `/api/alerts/:id` | PATCH `{active: bool}` | `{active}` |
| `/api/centres-watch` | GET | `[{id, oferta_denom, provincia_filter, active, created_at, last_sent_at}]` |
| `/api/centres-watch/:id` | DELETE | 204 |
| `/api/centres-watch/:id` | PATCH `{active: bool}` | `{active}` |

### Patró visual existent (alertes.html)

Totes les pàgines d'usuari segueixen exactament el mateix patró:
- Variables CSS a `:root`: `--dark`, `--warm`, `--warm2`, `--border`, `--bg`, `--white`
- Fonts: DM Sans (cos), DM Serif Display (títols), Geist Mono (dades)
- Topbar negra amb `#auth-widget` i selector de llengua
- Bloc `.hero` amb `<h1>` DM Serif
- `<main class="content">` amb la taula
- Footer amb `← Tornar al cercador`
- Scripts: `<script src="i18n.js">` i `<script src="auth.js">` a `<head>`

## Commands you will need

| Propòsit | Comanda | Esperat |
|----------|---------|---------|
| Backend tests | `cd backend && python -m pytest tests/ -v` | ≥118 passed (els 2 pre-existents de test_db poden fallar; és normal) |
| Verificació drift | `git diff --stat 3301aa2..HEAD -- frontend/auth.js frontend/i18n.js` | 0 canvis o comparar excerpts |
| Grep done criteria | veure secció "Criteris de done" | |

No hi ha typecheck ni build frontend (vanilla JS sense transpilació).

## Scope

**En àmbit** (els únics fitxers a modificar o crear):
- `frontend/perfil.html` (crear)
- `frontend/auth.js` (modificar: afegir link de perfil)
- `frontend/i18n.js` (modificar: afegir claus `nav.profile` i `perfil.*`)

**Fora d'àmbit** (NO tocar, tot i semblar relacionat):
- `frontend/alertes.html` / `frontend/alertes.js` — resten independents
- `frontend/seguiment.html` — resta independent
- `frontend/index.html` — no afegir cap link nou aquí
- `frontend/login.html` — el redirect post-login continua a `index.html`
- `backend/app.py` — cap nou endpoint

## Git workflow

- Branca: `feat/051-perfil-dashboard`
- Commits: conventional commits, ex: `feat(perfil): pàgina dashboard d'usuari`
- No fer push ni PR tret que el reviewer ho demani.

---

## Steps

### Pas 1 — Afegir claus i18n a `frontend/i18n.js`

Localitza el bloc nav CA (cerca `'nav.lang.es': 'ES',` dins el bloc `ca:`) i
afegeix les línies noves **just després**:

```javascript
      'nav.lang.es': 'ES',
      'nav.profile': 'El meu perfil',            // ← NOU

      /* ── perfil.html ── */
      'page.title.perfil': 'El meu perfil — Cercador Graus FP',
      'perfil.hero.h1': 'El meu',
      'perfil.hero.h1.em': 'perfil',
      'perfil.hero.sub': 'Favorits, alertes i seguiment de centres en un sol lloc',
      'perfil.nav.favorits': 'Favorits',
      'perfil.nav.alertes': 'Alertes',
      'perfil.nav.seguiment': 'Seguiment',
      'perfil.favs.title': 'Graus desats',
      'perfil.favs.empty': 'Encara no tens cap grau desat. <a href="index.html">Ves al cercador</a> i desa els que t\'interessin.',
      'perfil.favs.view': 'Veure favorits al cercador →',
      'perfil.login.required': 'Cal <a href="login.html">iniciar sessió</a> per veure el teu perfil.',
      'perfil.loading': 'Carregant el teu perfil...',
      'perfil.error': 'Error carregant les dades del perfil.',
      'perfil.footer.back': '← Tornar al cercador',
```

Localitza el bloc nav ES (cerca `'nav.lang.es': 'ES',` dins el bloc `es:`) i
afegeix just després:

```javascript
      'nav.lang.es': 'ES',
      'nav.profile': 'Mi perfil',                // ← NOU

      /* ── perfil.html ── */
      'page.title.perfil': 'Mi perfil — Cercador Graus FP',
      'perfil.hero.h1': 'Mi',
      'perfil.hero.h1.em': 'perfil',
      'perfil.hero.sub': 'Favoritos, alertas y seguimiento de centros en un solo lugar',
      'perfil.nav.favorits': 'Favoritos',
      'perfil.nav.alertes': 'Alertas',
      'perfil.nav.seguiment': 'Seguimiento',
      'perfil.favs.title': 'Enseñanzas guardadas',
      'perfil.favs.empty': 'Todavía no tienes ninguna enseñanza guardada. <a href="index.html">Ve al buscador</a> y guarda las que te interesen.',
      'perfil.favs.view': 'Ver favoritos en el buscador →',
      'perfil.login.required': 'Es necesario <a href="login.html">iniciar sesión</a> para ver tu perfil.',
      'perfil.loading': 'Cargando tu perfil...',
      'perfil.error': 'Error al cargar los datos del perfil.',
      'perfil.footer.back': '← Volver al buscador',
```

**Verificació**:
```bash
grep "nav.profile\|perfil.hero\|perfil.nav\|perfil.favs\|perfil.login\|perfil.loading\|perfil.error\|perfil.footer\|page.title.perfil" frontend/i18n.js | wc -l
```
Expected: `32` (16 claus × 2 locales).

---

### Pas 2 — Actualitzar `frontend/auth.js` per afegir link de perfil

Substitueix el bloc `widget.innerHTML = ...` del cas logged-in (línies 12–15 actuals):

**Codi actual**:
```javascript
        widget.innerHTML =
          '<span class="auth-greeting">' + t('nav.greeting', { email: escHtml(data.email) }) + '</span>' +
          '<button class="auth-btn auth-btn--logout" id="btn-logout">' + t('nav.logout') + '</button>';
        document.getElementById('btn-logout').addEventListener('click', logout);
```

**Codi nou**:
```javascript
        widget.innerHTML =
          '<span class="auth-greeting">' + t('nav.greeting', { email: escHtml(data.email) }) + '</span>' +
          '<a class="auth-btn" href="perfil.html">' + t('nav.profile') + '</a>' +
          '<button class="auth-btn auth-btn--logout" id="btn-logout">' + t('nav.logout') + '</button>';
        document.getElementById('btn-logout').addEventListener('click', logout);
```

La diferència: s'afegeix un `<a class="auth-btn">` que apunta a `perfil.html`
entre el saludo i el botó de logout. L'estil `auth-btn` ja existeix a totes les
pàgines i renderitza correctament.

**Verificació**:
```bash
grep "perfil.html" frontend/auth.js
```
Expected: 1 línia amb `href="perfil.html"`.

---

### Pas 3 — Crear `frontend/perfil.html`

Crea el fitxer nou `frontend/perfil.html` amb el contingut següent **exactament**
(copia i enganxa; no resumeixis ni adaptes):

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title data-i18n="page.title.perfil">El meu perfil — Cercador Graus FP</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link
    href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display:ital@0;1&family=Geist+Mono:wght@400;500&display=swap"
    rel="stylesheet">

  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --dark: #1c1410; --warm: #8a7060; --warm2: #f5ece2;
      --border: #e8ddd4; --bg: #fdf8f2; --white: #ffffff;
    }
    body { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; color: var(--dark); background: var(--bg); }

    /* ── Topbar ── */
    .topbar { background: var(--dark); padding: 0 48px; }
    .topbar-inner { display: flex; align-items: center; height: 52px; }
    .topbar-logo { font-family: 'DM Serif Display', serif; color: var(--white); font-size: 20px; letter-spacing: -0.3px; text-decoration: none; }
    #auth-widget { margin-left: auto; display: flex; align-items: center; gap: 8px; }
    .auth-greeting { color: rgba(255,255,255,0.75); font-size: 13px; }
    .auth-btn { font-size: 13px; padding: 5px 14px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.35); color: var(--white); background: transparent; cursor: pointer; text-decoration: none; font-family: inherit; transition: background 0.15s; }
    .auth-btn:hover { background: rgba(255,255,255,0.12); }
    .auth-btn--primary { background: var(--white); color: var(--dark); border-color: var(--white); }
    .auth-btn--primary:hover { background: var(--warm2); }

    /* ── Hero ── */
    .hero { border-bottom: 2px solid var(--dark); padding: 40px 48px 32px; }
    .hero h1 { font-family: 'DM Serif Display', serif; font-size: 48px; font-weight: 400; line-height: 1.05; color: var(--dark); margin-bottom: 10px; }
    .hero-sub { font-size: 15px; color: var(--warm); }

    /* ── Section nav (tabs) ── */
    .section-nav { display: flex; gap: 0; border-bottom: 2px solid var(--border); padding: 0 48px; background: var(--white); }
    .section-nav-link {
      font-size: 13px; font-weight: 600; padding: 12px 20px;
      color: var(--warm); text-decoration: none;
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      transition: color 0.15s;
    }
    .section-nav-link:hover { color: var(--dark); }
    .section-nav-link.active { color: var(--dark); border-bottom-color: var(--dark); }

    /* ── Content ── */
    .content { padding: 28px 48px 64px; }

    /* ── Favorits section ── */
    .favs-summary { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
    .favs-count { font-family: 'DM Serif Display', serif; font-size: 36px; color: var(--dark); line-height: 1; }
    .favs-label { font-size: 13px; color: var(--warm); }
    .favs-view-btn {
      display: inline-block; margin-top: 16px;
      font-size: 13px; font-weight: 600; font-family: inherit;
      padding: 8px 20px; border-radius: 4px;
      background: var(--dark); color: var(--white);
      text-decoration: none; transition: opacity 0.15s;
    }
    .favs-view-btn:hover { opacity: 0.85; }
    .favs-list { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
    .fav-tag {
      font-family: 'Geist Mono', monospace; font-size: 12px;
      background: var(--warm2); color: var(--dark);
      padding: 4px 10px; border-radius: 3px;
      border: 1px solid var(--border);
    }

    /* ── Tables (alertes i seguiment) ── */
    .results-table { width: 100%; border-collapse: collapse; font-size: 14px; background: var(--white); border: 1px solid var(--border); border-radius: 2px; overflow: hidden; }
    .results-table thead tr { background: var(--warm2); border-bottom: 2px solid var(--dark); }
    .results-table th { text-align: left; padding: 11px 16px; font-weight: 600; color: var(--dark); font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; }
    .results-table th.col-created, .results-table th.col-sent { width: 140px; }
    .results-table th.col-active { width: 100px; }
    .results-table th.col-actions { width: 48px; }
    .results-table th.col-prov { width: 160px; }
    .results-table td { padding: 13px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }
    .results-table tbody tr:hover td { background: var(--warm2); }
    .results-table tbody tr:last-child td { border-bottom: none; }
    .results-table td.col-created, .results-table td.col-sent,
    .results-table td.col-prov { font-family: 'Geist Mono', monospace; font-size: 12px; color: var(--warm); white-space: nowrap; }

    .toggle-btn { font-size: 12px; font-weight: 600; font-family: inherit; padding: 4px 10px; border-radius: 4px; cursor: pointer; border: none; }
    .toggle-btn--active { background: #dcfce7; color: #166534; }
    .toggle-btn--inactive { background: var(--warm2); color: var(--warm); }
    .toggle-btn:hover { filter: brightness(0.92); }
    .toggle-btn:disabled { opacity: 0.5; cursor: default; }
    .delete-btn { background: none; border: none; cursor: pointer; color: var(--warm); font-size: 14px; padding: 4px 8px; border-radius: 4px; }
    .delete-btn:hover { color: #991b1b; background: #fee2e2; }
    .delete-btn:disabled { opacity: 0.5; cursor: default; }

    /* ── States ── */
    .empty-state { text-align: center; color: var(--warm); padding: 48px 0; }
    .empty-state a { color: var(--dark); }
    .loading-state { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 48px 0; color: var(--warm); }
    @keyframes spin { to { transform: rotate(360deg); } }
    .spinner { border: 3px solid var(--border); border-top-color: var(--dark); border-radius: 50%; width: 32px; height: 32px; animation: spin 0.8s linear infinite; }

    /* ── Footer ── */
    footer { border-top: 1px solid var(--border); padding: 20px 48px; text-align: right; }
    footer a { font-size: 13px; color: var(--warm); text-decoration: none; }
    footer a:hover { color: var(--dark); }

    /* ── Lang selector ── */
    .lang-selector { display: flex; align-items: center; gap: 2px; margin-left: 16px; }
    .lang-btn { font-size: 11px; font-weight: 700; font-family: inherit; padding: 3px 8px; border-radius: 3px; cursor: pointer; background: transparent; border: 1px solid rgba(255,255,255,0.3); color: rgba(255,255,255,0.6); letter-spacing: 0.04em; transition: background 0.15s, color 0.15s; }
    .lang-btn:hover { background: rgba(255,255,255,0.12); color: var(--white); }
    .lang-btn--active { background: rgba(255,255,255,0.18); color: var(--white); border-color: rgba(255,255,255,0.6); }

    @media (max-width: 768px) {
      .topbar { padding: 0 16px; }
      .hero { padding: 24px 16px 20px; }
      .hero h1 { font-size: 30px; }
      .section-nav { padding: 0 16px; }
      .content { padding: 16px 16px 32px; }
      footer { padding: 20px 16px; }
      .results-table { font-size: 13px; }
    }
  </style>
  <script src="i18n.js"></script>
  <script src="auth.js"></script>
</head>
<body>

  <header class="topbar">
    <div class="topbar-inner">
      <a href="index.html" class="topbar-logo">GrausFP</a>
      <div id="auth-widget"></div>
      <div class="lang-selector" aria-label="Language selector">
        <button class="lang-btn" data-lang="ca" onclick="setLang('ca')">CA</button>
        <button class="lang-btn" data-lang="es" onclick="setLang('es')">ES</button>
      </div>
    </div>
  </header>

  <div class="hero">
    <h1><span data-i18n="perfil.hero.h1">El meu</span><br><em data-i18n="perfil.hero.h1.em">perfil</em></h1>
    <p class="hero-sub" data-i18n="perfil.hero.sub">Favorits, alertes i seguiment de centres en un sol lloc</p>
  </div>

  <nav class="section-nav" aria-label="Seccions del perfil">
    <a href="#favorits" class="section-nav-link active" id="tab-favorits" data-i18n="perfil.nav.favorits">Favorits</a>
    <a href="#alertes" class="section-nav-link" id="tab-alertes" data-i18n="perfil.nav.alertes">Alertes</a>
    <a href="#seguiment" class="section-nav-link" id="tab-seguiment" data-i18n="perfil.nav.seguiment">Seguiment</a>
  </nav>

  <main class="content">
    <div id="section-favorits">
      <div class="loading-state"><div class="spinner"></div></div>
    </div>
    <div id="section-alertes" hidden>
      <div class="loading-state"><div class="spinner"></div></div>
    </div>
    <div id="section-seguiment" hidden>
      <div class="loading-state"><div class="spinner"></div></div>
    </div>
  </main>

  <footer>
    <a href="index.html" data-i18n="perfil.footer.back">← Tornar al cercador</a>
  </footer>

  <script>
  (function () {
    var API_BASE = window.location.hostname === 'localhost'
      ? 'http://localhost:5001' : '';

    var LOCALE = getLang() === 'ca' ? 'ca-ES' : 'es-ES';

    function esc(s) {
      return String(s).replace(/[&<>"']/g, function (c) {
        return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]);
      });
    }

    /* ── Tab switching ── */
    var tabs = ['favorits', 'alertes', 'seguiment'];

    function activateTab(name) {
      tabs.forEach(function (tab) {
        var link = document.getElementById('tab-' + tab);
        var section = document.getElementById('section-' + tab);
        if (tab === name) {
          link.classList.add('active');
          section.removeAttribute('hidden');
        } else {
          link.classList.remove('active');
          section.setAttribute('hidden', '');
        }
      });
    }

    tabs.forEach(function (tab) {
      document.getElementById('tab-' + tab).addEventListener('click', function (e) {
        e.preventDefault();
        activateTab(tab);
      });
    });

    /* ── Auth gate (comú a les 3 seccions) ── */
    async function checkAuth() {
      var res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (!res.ok) return null;
      return res.json();
    }

    /* ── Secció Favorits ── */
    async function loadFavorits() {
      var section = document.getElementById('section-favorits');
      try {
        var res = await fetch(API_BASE + '/api/favorites', { credentials: 'include' });
        if (res.status === 401) {
          section.innerHTML = '<p class="empty-state">' + t('perfil.login.required') + '</p>';
          return;
        }
        var favs = await res.json();
        if (!favs.length) {
          section.innerHTML = '<p class="empty-state">' + t('perfil.favs.empty') + '</p>';
          return;
        }
        var tags = favs.map(function (f) {
          return '<span class="fav-tag">' + esc(f.oferta_codigo || String(f.oferta_id)) + '</span>';
        }).join('');
        section.innerHTML =
          '<div class="favs-summary">' +
            '<span class="favs-count">' + favs.length + '</span>' +
            '<span class="favs-label">' + t('perfil.favs.title') + '</span>' +
          '</div>' +
          '<div class="favs-list">' + tags + '</div>' +
          '<a class="favs-view-btn" href="index.html">' + t('perfil.favs.view') + '</a>';
      } catch (e) {
        section.innerHTML = '<p class="empty-state" style="color:#991b1b;">' + t('perfil.error') + '</p>';
      }
    }

    /* ── Secció Alertes ── */
    function buildAlertFilterDesc(filter) {
      var parts = [];
      if (filter.grado) parts.push('Grado ' + filter.grado);
      if (filter.familia) parts.push(filter.familia);
      if (filter.nivel != null) parts.push(t('alertes.filter.niv') + filter.nivel);
      if (filter.texto) parts.push('Texto: «' + filter.texto + '»');
      return parts.length ? parts.join(' · ') : t('alertes.filter.all');
    }

    function renderAlertes(alerts) {
      var section = document.getElementById('section-alertes');
      if (!alerts.length) {
        section.innerHTML = '<p class="empty-state">' + t('alertes.empty') + '</p>';
        return;
      }
      var rows = alerts.map(function (a) {
        var filter = JSON.parse(a.filter_json || '{}');
        var desc = buildAlertFilterDesc(filter);
        var active = a.active === 1 || a.active === true;
        var lastSent = a.last_sent_at
          ? new Date(a.last_sent_at).toLocaleDateString(LOCALE) : '—';
        var created = a.created_at
          ? new Date(a.created_at).toLocaleString(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
          : '—';
        return '<tr>' +
          '<td>' + esc(desc) + '</td>' +
          '<td class="col-created">' + esc(created) + '</td>' +
          '<td class="col-sent">' + esc(lastSent) + '</td>' +
          '<td class="col-active">' +
            '<button class="toggle-btn ' + (active ? 'toggle-btn--active' : 'toggle-btn--inactive') + '"' +
            ' data-id="' + a.id + '" data-active="' + (active ? '1' : '0') + '">' +
            (active ? t('alertes.state.active') : t('alertes.state.inactive')) +
            '</button>' +
          '</td>' +
          '<td class="col-actions">' +
            '<button class="delete-btn" data-id="' + a.id + '" aria-label="' + t('alertes.aria.delete') + '">✕</button>' +
          '</td>' +
          '</tr>';
      }).join('');

      section.innerHTML =
        '<table class="results-table"><thead><tr>' +
        '<th>' + t('alertes.col.filter') + '</th>' +
        '<th class="col-created">' + t('alertes.col.created') + '</th>' +
        '<th class="col-sent">' + t('alertes.col.sent') + '</th>' +
        '<th class="col-active">' + t('alertes.col.state') + '</th>' +
        '<th class="col-actions"></th>' +
        '</tr></thead><tbody>' + rows + '</tbody></table>';

      section.querySelectorAll('.toggle-btn').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          var id = parseInt(btn.dataset.id);
          var currentActive = btn.dataset.active === '1';
          btn.disabled = true;
          try {
            var r = await fetch(API_BASE + '/api/alerts/' + id, {
              method: 'PATCH', credentials: 'include',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: !currentActive })
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            await loadAlertes();
          } catch (e) {
            btn.disabled = false;
            alert(t('alertes.err.toggle') + e.message);
          }
        });
      });

      section.querySelectorAll('.delete-btn').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          if (!confirm(t('alertes.confirm.delete'))) return;
          var id = parseInt(btn.dataset.id);
          btn.disabled = true;
          try {
            var r = await fetch(API_BASE + '/api/alerts/' + id, { method: 'DELETE', credentials: 'include' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            await loadAlertes();
          } catch (e) {
            btn.disabled = false;
            alert(t('alertes.err.delete') + e.message);
          }
        });
      });
    }

    async function loadAlertes() {
      var section = document.getElementById('section-alertes');
      section.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
      try {
        var res = await fetch(API_BASE + '/api/alerts', { credentials: 'include' });
        if (res.status === 401) {
          section.innerHTML = '<p class="empty-state">' + t('alertes.login.required') + '</p>';
          return;
        }
        if (!res.ok) throw new Error('HTTP ' + res.status);
        renderAlertes(await res.json());
      } catch (e) {
        section.innerHTML = '<p class="empty-state" style="color:#991b1b;">' + t('alertes.error') + '</p>';
      }
    }

    /* ── Secció Seguiment ── */
    function renderSeguiment(watches) {
      var section = document.getElementById('section-seguiment');
      if (!watches.length) {
        section.innerHTML = '<p class="empty-state">' + t('seguiment.empty') + '</p>';
        return;
      }
      var rows = watches.map(function (w) {
        var active = w.active === 1 || w.active === true;
        var prov = w.provincia_filter
          ? esc(w.provincia_filter)
          : '<span style="color:var(--warm)">' + t('seguiment.all.prov') + '</span>';
        var created = w.created_at ? w.created_at.slice(0, 10) : '—';
        var lastSent = w.last_sent_at ? w.last_sent_at.slice(0, 10) : '—';
        return '<tr id="watch-pf-' + w.id + '">' +
          '<td>' + esc(w.oferta_denom) + '</td>' +
          '<td class="col-prov">' + prov + '</td>' +
          '<td class="col-created">' + created + '</td>' +
          '<td class="col-sent">' + lastSent + '</td>' +
          '<td class="col-active">' +
            '<button class="toggle-btn ' + (active ? 'toggle-btn--active' : 'toggle-btn--inactive') + '"' +
            ' data-id="' + w.id + '" data-active="' + (active ? '1' : '0') + '">' +
            (active ? t('seguiment.state.active') : t('seguiment.state.inactive')) +
            '</button>' +
          '</td>' +
          '<td class="col-actions">' +
            '<button class="delete-btn" data-id="' + w.id + '" title="Elimina">✕</button>' +
          '</td>' +
          '</tr>';
      }).join('');

      section.innerHTML =
        '<div class="table-wrap" style="overflow-x:auto">' +
        '<table class="results-table" style="min-width:560px"><thead><tr>' +
        '<th>' + t('seguiment.col.ens') + '</th>' +
        '<th class="col-prov">' + t('seguiment.col.prov') + '</th>' +
        '<th class="col-created">' + t('seguiment.col.created') + '</th>' +
        '<th class="col-sent">' + t('seguiment.col.sent') + '</th>' +
        '<th class="col-active">' + t('seguiment.col.state') + '</th>' +
        '<th class="col-actions"></th>' +
        '</tr></thead><tbody>' + rows + '</tbody></table></div>';

      section.querySelectorAll('.toggle-btn').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          var id = parseInt(btn.dataset.id);
          var currentActive = btn.dataset.active === '1';
          btn.disabled = true;
          try {
            var r = await fetch(API_BASE + '/api/centres-watch/' + id, {
              method: 'PATCH', credentials: 'include',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ active: !currentActive })
            });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            await loadSeguiment();
          } catch (e) {
            btn.disabled = false;
            alert(t('seguiment.err.toggle') + e.message);
          }
        });
      });

      section.querySelectorAll('.delete-btn').forEach(function (btn) {
        btn.addEventListener('click', async function () {
          var id = parseInt(btn.dataset.id);
          btn.disabled = true;
          try {
            var r = await fetch(API_BASE + '/api/centres-watch/' + id, { method: 'DELETE', credentials: 'include' });
            if (!r.ok) throw new Error('HTTP ' + r.status);
            await loadSeguiment();
          } catch (e) {
            btn.disabled = false;
            alert(t('seguiment.err.toggle') + e.message);
          }
        });
      });
    }

    async function loadSeguiment() {
      var section = document.getElementById('section-seguiment');
      section.innerHTML = '<div class="loading-state"><div class="spinner"></div></div>';
      try {
        var res = await fetch(API_BASE + '/api/centres-watch', { credentials: 'include' });
        if (res.status === 401) {
          section.innerHTML = '<p class="empty-state">' + t('perfil.login.required') + '</p>';
          return;
        }
        if (!res.ok) throw new Error('HTTP ' + res.status);
        renderSeguiment(await res.json());
      } catch (e) {
        section.innerHTML = '<p class="empty-state" style="color:#991b1b;">' + t('perfil.error') + '</p>';
      }
    }

    /* ── Inicialització ── */
    document.addEventListener('DOMContentLoaded', async function () {
      var user = await checkAuth();
      if (!user) {
        ['favorits', 'alertes', 'seguiment'].forEach(function (s) {
          document.getElementById('section-' + s).innerHTML =
            '<p class="empty-state">' + t('perfil.login.required') + '</p>';
          document.getElementById('section-' + s).removeAttribute('hidden');
        });
        document.querySelectorAll('.section-nav-link').forEach(function (l) { l.style.display = 'none'; });
        return;
      }
      await Promise.all([loadFavorits(), loadAlertes(), loadSeguiment()]);
    });
  })();
  </script>
</body>
</html>
```

**Verificació**:
```bash
wc -l frontend/perfil.html
```
Expected: entre 240 i 310 línies.

```bash
grep "section-favorits\|section-alertes\|section-seguiment\|tab-favorits\|tab-alertes\|tab-seguiment" frontend/perfil.html | wc -l
```
Expected: ≥12 (cadascuna apareix almenys 2 cops).

---

### Pas 4 — Tests de backend (assegurar que res s'ha trencat)

```bash
cd backend && python -m pytest tests/ -v 2>&1 | tail -10
```

Expected: el mateix resultat que abans del canvi. Cap dels tests de backend
s'hauria d'afectar perquè no hem tocat cap fitxer Python.

---

## Test plan

No hi ha tests unitaris de frontend en aquest repo. La verificació és manual:

**Prerequisit**: backend aixecat localment (`flask run --port 5001`) amb
`fp_cercador.db` disponible i almenys un usuari de test amb favorits/alertes/seguiment.

| Cas | Acció | Esperat |
|-----|-------|---------|
| Usuari no autenticat | Obrir `perfil.html` | Missatge "Cal iniciar sessió" a les 3 seccions; sense tabs visibles |
| Usuari autenticat, cap dada | Login → anar a `perfil.html` | Spinners → "Encara no tens..." a Favorits; "Encara no tens..." a Alertes i Seguiment |
| Usuari amb favorits | Login → `perfil.html` | Secció Favorits mostra count + pills de codis + botó "Veure al cercador" |
| Usuari amb alertes | Clic tab Alertes | Taula d'alertes visible; toggle i delete funcionen |
| Usuari amb seguiment | Clic tab Seguiment | Taula de seguiment visible; toggle i delete funcionen |
| Widget topbar | Login → qualsevol pàgina | "El meu perfil" apareix entre el saludo i "Sortir" |
| Link "El meu perfil" | Clic al widget | Redirigeix a `perfil.html` |
| Canvi d'idioma | Clic ES a `perfil.html` | Tots els textos canvien; títol del navegador canvia |

---

## Criteris de done

```bash
# 1. Fitxer creat
ls -la frontend/perfil.html

# 2. Link de perfil a auth.js
grep "perfil.html" frontend/auth.js

# 3. Claus i18n presents (32 = 16 claus × 2 locales)
grep "nav.profile\|perfil.hero\|perfil.nav\|perfil.favs\|perfil.login\|perfil.loading\|perfil.error\|perfil.footer\|page.title.perfil" frontend/i18n.js | wc -l

# 4. Les 3 seccions existeixen al HTML
grep "section-favorits\|section-alertes\|section-seguiment" frontend/perfil.html

# 5. Cap canvi a backend
git diff --name-only | grep backend

# 6. Tests de backend inalterats
cd backend && python -m pytest tests/ -v 2>&1 | grep -E "passed|failed"
```

Criteris pass:
- [x] `ls` retorna el fitxer (exit 0)
- [x] `grep "perfil.html" frontend/auth.js` retorna 1 línia
- [x] El compte de claus i18n és 32
- [x] `grep "section-"` retorna ≥3 línies
- [x] `git diff --name-only | grep backend` retorna buit
- [x] Tests: ≥118 passed (els 2 de test_db pre-existents poden fallar)

---

## STOP conditions

- Si `frontend/i18n.js` té una estructura diferent dels excerpts (per exemple, el
  bloc CA no és `{ ca: { ... } }` sinó un altre format), para i reporta.
- Si `frontend/auth.js` ja té un link a `perfil.html` (pla ja executat parcialment),
  para i reporta l'estat actual.
- Si algun dels endpoints `/api/favorites`, `/api/alerts`, `/api/centres-watch`
  retorna un format diferent al documentat a "API endpoints", para i reporta.
- No afegeixis cap nova dependència JavaScript (cap llibreria, cap CDN). Tot
  ha de ser vanilla JS pur.

## Maintenance notes

- Si en el futur s'afegeix el camp `denominacion` a `/api/favorites`, la secció
  Favorits de `perfil.html` es pot millorar per mostrar el nom complet. El canvi
  és localitzat a la funció `loadFavorits()`.
- Si es crea una feature de "llistes personalitzades" (més d'una llista per
  usuari), la secció Favorits caldrà revisar-la.
- Les funcions `loadAlertes()` i `loadSeguiment()` dupliquen lògica d'`alertes.js`
  i `seguiment.html`. Si la lògica de render canvia en els originals, cal
  sincronitzar `perfil.html`. Futura refactorització: extreure a un `perfil.js`
  compartit.
- `auth.js` és compartit per totes les pàgines — el link "El meu perfil" apareixerà
  a index.html, alertes.html, seguiment.html, etc. Això és el comportament desitjat.
