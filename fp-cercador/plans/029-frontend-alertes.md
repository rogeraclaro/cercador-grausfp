# Pla 029 — Frontend gestió d'alertes (F3)

**Written against commit:** f8085ab  
**Status:** TODO  
**Depends on:** 028 (DONE — backend motor alertes F3)  
**Effort:** M  
**Priority:** P1

---

## Objectiu

Completar la feature F3 (alertes personalitzades) al frontend:

1. `frontend/alertes.html` — pàgina de gestió de les alertes de l'usuari
2. `frontend/alertes.js` — lògica JS (CRUD + renderitzat)
3. `frontend/index.html` — botó "Desa com a alerta" quan hi ha filtres actius

No cal modificar cap altre fitxer backend ni frontend.

---

## Context i convencions del projecte

**Stack frontend:** HTML/CSS/JS vanilla + Alpine.js 3.x (vendoritzat a `frontend/vendor/alpine.min.js`). Sense frameworks addicionals.

**Patró de pàgina estàtica (seguir historial.html):**
- Estructura: topbar → hero → main#main-content → footer
- CSS inline a `<style>` dins `<head>`
- Variables CSS:
  ```css
  --dark: #1c1410;
  --warm: #8a7060;
  --warm2: #f5ece2;
  --border: #e8ddd4;
  --bg: #fdf8f2;
  --white: #ffffff;
  ```
- `<script src="auth.js"></script>` a l'head (renderitza el widget d'autenticació)
- `API_BASE` = `window.location.hostname === 'localhost' ? 'http://localhost:5001' : ''`
- Fonts: DM Sans + DM Serif Display + Geist Mono (Google Fonts CDN igual que historial.html:9-11)
- Escape HTML: funció `esc(s)` com a historial.html:247-249

**Autenticació:** cookie de sessió (`credentials: 'include'`). `auth.js` ja gestiona el widget del topbar. Per verificar si l'usuari és autenticat, `GET /api/auth/me` — si `res.ok`, autenticat.

**Endpoints backend (pla 028, tots existents):**
- `GET /api/alerts` → `[{id, filter_json (string), active, created_at, last_sent_at}]` — requereix sessió
- `POST /api/alerts` body `{filter_json: {...}}` → 201 `{id, filter_json, active, ...}` — requereix sessió
- `DELETE /api/alerts/<id>` → 204 — requereix sessió
- `PATCH /api/alerts/<id>` body `{active: bool}` → 200 `{id, filter_json, active, ...}` — requereix sessió
- `GET /api/alerts/<id>/unsubscribe?token=<tok>` → redireccionament (sense sessió)

**Format `filter_json`** (string JSON dins la fila; el JS fa `JSON.parse`):
```json
{"grado": "A", "familia": "Sanidad", "nivel": 2, "texto": "tècnic"}
```
Tots els camps són opcionals. Almenys un present.

**`build_alert_description` (Python, alerts_service.py:89-97) — equivalent JS a implementar:**
- grado present → `"Grado X"`
- familia present → la familia
- nivel present → `"Nivell N"`
- texto present → `"Texto: «…»"`
- tot buit → `"Tots els nous ensenyaments"`
- Parts unides amb ` · `

**Alpine.js a index.html (variables rellevants, ja existents):**
- `search` — text lliure
- `filterGrado` — `''` o `'A'`…`'E'`
- `filterFamilia` — string o `''`
- `filterNivel` — string o `''`
- `loggedIn` — bool
- `showCentresModal()` — obre el modal de gating (anònim)

---

## Fitxers a crear / modificar

| Fitxer | Acció |
|--------|-------|
| `frontend/alertes.html` | Crear |
| `frontend/alertes.js` | Crear |
| `frontend/index.html` | Modificar — afegir botó + lògica `saveAlert` |

**Fora d'abast d'aquest pla:**
- `backend/app.py`, `backend/alerts_service.py` — ja estan al pla 028, no tocar
- `frontend/historial.html`, `frontend/auth.js` — no modificar
- Desplegament VPS — es fa manualment després

---

## Pas 1 — Crear `frontend/alertes.js`

Crear el fitxer `frontend/alertes.js` amb el contingut següent (JS vanilla, `'use strict'` implícit per scope IIFE):

```js
(function () {
  const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5001' : '';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  function buildFilterDescription(filter) {
    const parts = [];
    if (filter.grado)            parts.push('Grado ' + filter.grado);
    if (filter.familia)          parts.push(filter.familia);
    if (filter.nivel != null)    parts.push('Nivell ' + filter.nivel);
    if (filter.texto)            parts.push('Texto: «' + filter.texto + '»');
    return parts.length ? parts.join(' · ') : 'Tots els nous ensenyaments';
  }

  async function fetchAlerts() {
    const res = await fetch(API_BASE + '/api/alerts', { credentials: 'include' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  async function createAlert(filterDict) {
    const res = await fetch(API_BASE + '/api/alerts', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filter_json: filterDict })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'HTTP ' + res.status);
    }
    return res.json();
  }

  async function deleteAlert(id) {
    const res = await fetch(API_BASE + '/api/alerts/' + id, {
      method: 'DELETE', credentials: 'include'
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
  }

  async function toggleAlert(id, active) {
    const res = await fetch(API_BASE + '/api/alerts/' + id, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  function renderAlerts(alerts) {
    const main = document.getElementById('main-content');
    if (!alerts.length) {
      main.innerHTML = '<p class="empty-state">Encara no tens cap alerta configurada.<br>Aplica filtres al cercador i clica "Desa com a alerta".</p>';
      return;
    }
    const rows = alerts.map(a => {
      const filter = JSON.parse(a.filter_json || '{}');
      const desc = buildFilterDescription(filter);
      const active = a.active === 1 || a.active === true;
      const lastSent = a.last_sent_at
        ? new Date(a.last_sent_at).toLocaleDateString('ca-ES')
        : '—';
      const created = a.created_at
        ? new Date(a.created_at).toLocaleString('ca-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
      return `<tr>
        <td class="col-desc">${esc(desc)}</td>
        <td class="col-created">${esc(created)}</td>
        <td class="col-sent">${esc(lastSent)}</td>
        <td class="col-active">
          <button class="toggle-btn ${active ? 'toggle-btn--active' : 'toggle-btn--inactive'}"
            data-id="${a.id}" data-active="${active ? '1' : '0'}">
            ${active ? 'Activa' : 'Inactiva'}
          </button>
        </td>
        <td class="col-actions">
          <button class="delete-btn" data-id="${a.id}" aria-label="Eliminar alerta">✕</button>
        </td>
      </tr>`;
    }).join('');
    main.innerHTML = `
      <div class="table-wrap">
        <table class="results-table">
          <thead>
            <tr>
              <th scope="col">Filtre</th>
              <th scope="col" class="col-created">Creada</th>
              <th scope="col" class="col-sent">Darrer enviament</th>
              <th scope="col" class="col-active">Estat</th>
              <th scope="col" class="col-actions"></th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;

    main.querySelectorAll('.toggle-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.id);
        const currentActive = btn.dataset.active === '1';
        btn.disabled = true;
        try {
          await toggleAlert(id, !currentActive);
          await load();
        } catch (e) {
          btn.disabled = false;
          alert('Error canviant estat: ' + e.message);
        }
      });
    });

    main.querySelectorAll('.delete-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Elimines aquesta alerta?')) return;
        const id = parseInt(btn.dataset.id);
        btn.disabled = true;
        try {
          await deleteAlert(id);
          await load();
        } catch (e) {
          btn.disabled = false;
          alert('Error eliminant alerta: ' + e.message);
        }
      });
    });
  }

  async function load() {
    const main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Carregant alertes...</p></div>';
    try {
      const res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (!res.ok) {
        main.innerHTML = '<p class="empty-state">Cal <a href="login.html">iniciar sessió</a> per veure les teves alertes.</p>';
        return;
      }
      const alerts = await fetchAlerts();
      renderAlerts(alerts);
    } catch (e) {
      main.innerHTML = '<p class="empty-state" style="color:#991b1b;">Error carregant les alertes.</p>';
    }
  }

  document.addEventListener('DOMContentLoaded', load);
})();
```

**Verificació:** `node --check frontend/alertes.js` ha de sortir sense errors.

---

## Pas 2 — Crear `frontend/alertes.html`

Seguir el patró exacte de `frontend/historial.html`. Estructura:

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Les meves alertes — Cercador Graus FP</title>

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link
    href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700&family=DM+Serif+Display:ital@0;1&family=Geist+Mono:wght@400;500&display=swap"
    rel="stylesheet">

  <style>
    /* Reset + variables (idèntic a historial.html) */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --dark: #1c1410; --warm: #8a7060; --warm2: #f5ece2;
      --border: #e8ddd4; --bg: #fdf8f2; --white: #ffffff;
    }
    body { font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif; font-size: 14px; color: var(--dark); background: var(--bg); }

    /* Topbar (idèntic a historial.html) */
    .topbar { background: var(--dark); padding: 0 48px; }
    .topbar-inner { display: flex; align-items: center; height: 52px; }
    .topbar-logo { font-family: 'DM Serif Display', serif; color: var(--white); font-size: 20px; letter-spacing: -0.3px; text-decoration: none; }
    #auth-widget { margin-left: auto; display: flex; align-items: center; gap: 8px; }
    .auth-greeting { color: rgba(255,255,255,0.75); font-size: 13px; }
    .auth-btn { font-size: 13px; padding: 5px 14px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.35); color: var(--white); background: transparent; cursor: pointer; text-decoration: none; font-family: inherit; transition: background 0.15s; }
    .auth-btn:hover { background: rgba(255,255,255,0.12); }
    .auth-btn--primary { background: var(--white); color: var(--dark); border-color: var(--white); }
    .auth-btn--primary:hover { background: var(--warm2); }

    /* Hero */
    .hero { border-bottom: 2px solid var(--dark); padding: 40px 48px 32px; }
    .hero h1 { font-family: 'DM Serif Display', serif; font-size: 48px; font-weight: 400; line-height: 1.05; color: var(--dark); margin-bottom: 10px; }
    .hero-sub { font-size: 15px; color: var(--warm); }

    /* Content */
    .content { padding: 28px 48px 64px; }

    /* Taula */
    .results-table { width: 100%; border-collapse: collapse; font-size: 14px; background: var(--white); border: 1px solid var(--border); border-radius: 2px; overflow: hidden; }
    .results-table thead tr { background: var(--warm2); border-bottom: 2px solid var(--dark); }
    .results-table th { text-align: left; padding: 11px 16px; font-weight: 600; color: var(--dark); font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; }
    .results-table th.col-created, .results-table th.col-sent { width: 140px; }
    .results-table th.col-active { width: 100px; }
    .results-table th.col-actions { width: 48px; }
    .results-table td { padding: 13px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }
    .results-table tbody tr:hover td { background: var(--warm2); }
    .results-table tbody tr:last-child td { border-bottom: none; }
    .results-table td.col-created, .results-table td.col-sent { font-family: 'Geist Mono', monospace; font-size: 12px; color: var(--warm); white-space: nowrap; }

    /* Toggle button */
    .toggle-btn { font-size: 12px; font-weight: 600; font-family: inherit; padding: 4px 10px; border-radius: 4px; cursor: pointer; border: none; }
    .toggle-btn--active { background: #dcfce7; color: #166534; }
    .toggle-btn--inactive { background: var(--warm2); color: var(--warm); }
    .toggle-btn:hover { filter: brightness(0.92); }
    .toggle-btn:disabled { opacity: 0.5; cursor: default; }

    /* Delete button */
    .delete-btn { background: none; border: none; cursor: pointer; color: var(--warm); font-size: 14px; padding: 4px 8px; border-radius: 4px; }
    .delete-btn:hover { color: #991b1b; background: #fee2e2; }
    .delete-btn:disabled { opacity: 0.5; cursor: default; }

    /* States */
    .empty-state { text-align: center; color: var(--warm); padding: 64px 48px; }
    .empty-state a { color: var(--dark); }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-state { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 64px 48px; color: var(--warm); }
    .spinner { border: 3px solid var(--border); border-top-color: var(--dark); border-radius: 50%; width: 32px; height: 32px; animation: spin 0.8s linear infinite; }

    /* Footer */
    footer { border-top: 1px solid var(--border); padding: 20px 48px; text-align: right; }
    footer a { font-size: 13px; color: var(--warm); text-decoration: none; }
    footer a:hover { color: var(--dark); }

    /* Responsive */
    @media (max-width: 768px) {
      .topbar { padding: 0 16px; }
      .hero { padding: 24px 16px 20px; }
      .hero h1 { font-size: 30px; }
      .content { padding: 16px 16px 32px; }
      .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
      .results-table { min-width: 500px; }
      footer { padding: 20px 16px; }
    }
  </style>
  <script src="auth.js"></script>
</head>
<body>

  <header class="topbar">
    <div class="topbar-inner">
      <a href="index.html" class="topbar-logo">GrausFP</a>
      <div id="auth-widget"></div>
    </div>
  </header>

  <div class="hero">
    <h1>Les meves<br><em>alertes</em></h1>
    <p class="hero-sub">Rebràs un email quan apareguin nous ensenyaments que encaixin amb els teus filtres</p>
  </div>

  <main class="content" id="main-content">
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Carregant alertes...</p>
    </div>
  </main>

  <footer>
    <a href="index.html">← Tornar al cercador</a>
  </footer>

  <script src="alertes.js"></script>
</body>
</html>
```

**Verificació:** obrir `frontend/alertes.html` al navegador (amb servidor local); ha de mostrar el loading i després el missatge d'inici de sessió si no autenticat, o la taula d'alertes si autenticat.

---

## Pas 3 — Modificar `frontend/index.html`

### 3a. Afegir estat `alertModalVisible` a l'objecte Alpine

A `frontend/index.html`, cerca la línia:
```js
        centresModalVisible: false,
```
Afegir immediatament DESPRÉS (mateixa indentació):
```js
        alertModalVisible: false,
        alertSaveError: '',
        alertSaving: false,
```

### 3b. Afegir mètode `saveAlert`

A `frontend/index.html`, cerca el mètode `showCentresModal()`:
```js
        showCentresModal() {
          this.centresModalVisible = true;
        },
```
Afegir immediatament DESPRÉS (mateixa indentació):
```js
        async saveAlert() {
          if (!this.loggedIn) { this.showCentresModal(); return; }
          const filter = {};
          if (this.filterGrado)   filter.grado   = this.filterGrado;
          if (this.filterFamilia) filter.familia  = this.filterFamilia;
          if (this.filterNivel)   filter.nivel    = parseInt(this.filterNivel);
          if (this.search.trim()) filter.texto    = this.search.trim();
          if (!Object.keys(filter).length) return;
          this.alertSaving = true;
          this.alertSaveError = '';
          try {
            const res = await fetch(API_BASE + '/api/alerts', {
              method: 'POST',
              credentials: 'include',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ filter_json: filter })
            });
            if (!res.ok) {
              const err = await res.json().catch(() => ({}));
              this.alertSaveError = err.error || 'Error desant l\'alerta';
              this.alertModalVisible = true;
              return;
            }
            this.alertModalVisible = true;
          } catch (e) {
            this.alertSaveError = 'Error de connexió';
            this.alertModalVisible = true;
          } finally {
            this.alertSaving = false;
          }
        },
```

### 3c. Afegir botó "Desa com a alerta" a la barra de filtres

A `frontend/index.html`, cerca el botó "Esborrar filtres ×":
```html
      <button class="clear-btn"
        x-show="search || filterGrado || filterFamilia || filterNivel || filterOld !== 'all' || filterFavs"
        @click="search=''; filterGrado=''; filterFamilia=''; filterNivel=''; filterOld='all'; filterFavs=false; resetPage()">
        Esborrar filtres ×
      </button>
```
Afegir IMMEDIATAMENT ABANS (mateixa indentació):
```html
      <button class="save-alert-btn"
        x-show="search || filterGrado || filterFamilia || filterNivel"
        :disabled="alertSaving"
        @click="saveAlert()">
        🔔 Desa com a alerta
      </button>
```

### 3d. Afegir CSS per al botó "Desa com a alerta"

A `frontend/index.html`, cerca el bloc CSS dels botons de la barra de filtres. Localitzar algun selector com `.clear-btn` o `.checkbox-label` i afegir a continuació:

```css
    .save-alert-btn {
      font-size: 13px; font-family: inherit; font-weight: 500;
      padding: 5px 12px; border-radius: 4px; cursor: pointer;
      border: 1px solid var(--dark); color: var(--dark);
      background: transparent; white-space: nowrap; transition: background 0.15s;
    }
    .save-alert-btn:hover { background: var(--warm2); }
    .save-alert-btn:disabled { opacity: 0.5; cursor: default; }
```

### 3e. Afegir modal de confirmació d'alerta desada

A `frontend/index.html`, cerca el modal existent de centres:
```html
    <!-- Modal gating centres -->
    <div x-show="centresModalVisible" ...>
```
Afegir IMMEDIATAMENT ABANS:
```html
    <!-- Modal confirmació alerta desada -->
    <div x-show="alertModalVisible" @click="alertModalVisible = false" class="centres-modal-overlay" x-cloak>
      <div class="centres-modal" @click.stop>
        <button class="centres-modal-close" @click="alertModalVisible = false">✕</button>
        <template x-if="!alertSaveError">
          <div>
            <p class="centres-modal-msg" style="color:#166534;">✓ Alerta desada correctament</p>
            <p style="font-size:13px;color:var(--warm);margin-top:8px;text-align:center;">Rebràs un email quan hi hagi nous ensenyaments que encaixin amb els teus filtres.</p>
            <div class="centres-modal-actions" style="margin-top:16px;">
              <a href="alertes.html" class="centres-modal-btn centres-modal-btn--primary">Veure les meves alertes</a>
              <button class="centres-modal-btn centres-modal-btn--secondary" @click="alertModalVisible = false">Continuar cercant</button>
            </div>
          </div>
        </template>
        <template x-if="alertSaveError">
          <div>
            <p class="centres-modal-msg" style="color:#991b1b;" x-text="alertSaveError"></p>
            <div class="centres-modal-actions" style="margin-top:16px;">
              <button class="centres-modal-btn centres-modal-btn--secondary" @click="alertModalVisible = false">Tancar</button>
            </div>
          </div>
        </template>
      </div>
    </div>
```

---

## Pas 4 — Verificació manual (navegador)

Amb `cd backend && python app.py` (localhost:5001):

### 4a. alertes.html — usuari anònim
1. Obrir `http://localhost:5001/alertes.html` sense sessió
2. Verificar que mostra: "Cal iniciar sessió per veure les teves alertes."

### 4b. alertes.html — usuari autenticat sense alertes
1. Iniciar sessió (login.html)
2. Obrir `alertes.html`
3. Verificar que mostra el missatge d'estat buit

### 4c. index.html — botó i modal
1. Obrir `index.html`; verificar que el botó "Desa com a alerta" NO apareix sense filtres
2. Aplicar qualsevol filtre (grado, familia, nivel o search); verificar que el botó apareix
3. Sense sessió: clicar el botó → ha d'obrir el modal de gating de centres (no el d'alertes)
4. Amb sessió: clicar el botó → ha de mostrar el modal verd "✓ Alerta desada correctament" amb opcions "Veure les meves alertes" / "Continuar cercant"
5. Clicar "Veure les meves alertes" → redirigeix a `alertes.html` i la nova alerta apareix a la llista

### 4d. alertes.html — toggle i delete
1. A `alertes.html`, clicar "Activa" → es torna "Inactiva" i viceversa
2. Clicar "✕" → confirm → la fila desapareix

### 4e. Cas error: màxim 10 alertes
1. Crear 10 alertes
2. Intentar-ne crear una d'onzena → el modal ha de mostrar el missatge d'error del backend ("Màxim 10 alertes actives per usuari")

---

## Criteris de finalització (done criteria)

```
✓ node --check frontend/alertes.js → sense errors
✓ alertes.html carrega sense errors de consola (anònim i autenticat)
✓ index.html: botó "Desa com a alerta" apareix ↔ desapareix correctament amb filtres
✓ POST /api/alerts des del botó crea l'alerta (verificable a alertes.html)
✓ Toggle activa/inactiva funciona (PATCH /api/alerts/<id>)
✓ Delete funciona (DELETE /api/alerts/<id>)
✓ Modal d'error mostra el missatge del backend quan pertoca
✓ Anònim clicant el botó → s'obre el modal de gating existent (showCentresModal)
```

---

## Escape hatches

- Si `x-cloak` fa invisible el modal de confirmació permanentment, verificar que el CSS de `x-cloak` existeix a `index.html` (hauria d'estar ja definit per al modal de centres). Si no hi és, afegir `[x-cloak] { display: none !important; }`.
- Si el modal de confirmació usa `<template x-if>` i Alpine no renderitza el contingut, substituir per `x-show` + `style="display:none"`.
- Si `alertSaveError` no és reactiu, assegurar-se que és una propietat de l'objecte `cercador` (no una variable externa).

---

## Nota de manteniment

- `buildFilterDescription` a `alertes.js` ha de romandre sincronitzat amb `build_alert_description` a `backend/alerts_service.py`. Si s'afegeix un camp nou al `filter_json`, actualitzar les dues funcions.
- El botó "Desa com a alerta" s'oculta si `filterOld !== 'all'` o `filterFavs` estan actius però no hi ha cap dels quatre filtres principals; és intencionat (no es pot crear una alerta per "mostrar plans antics").
