# Pla 039 — F4-B: Frontend seguiment de centres (botó + pàgina de gestió)

**Escrit contra el commit:** `4c11047`
**Feature:** F4 del roadmap (plans/futures/ROADMAP-FEATURES.md)
**Depèn de:** 038 (backend F4 — DONA per executar PRIMER)
**Esforç:** M
**Pla anterior:** 038 (backend)

---

## Context i valor

Aquest pla afegeix la capa visible de F4: un botó "Seguir centres" al panell de centres
de cada oferta a `index.html`, i una pàgina `seguiment.html` per gestionar els seguiments
actius. El backend (endpoints CRUD + servei) ja existeix en acabar el pla 038.

**Fitxers de referència que l'executor ha de llegir abans de començar:**
- `frontend/alertes.html` + `frontend/alertes.js` — estructura i patrons de la pàgina de gestió d'alertes que cal replicar (mismo layout, mismo estil)
- `frontend/index.html` línies 1580–1690 — el panell de centres de cada oferta (on va el botó)
- `frontend/auth.js` — com es carrega l'autenticació a totes les pàgines

---

## Fitxers en scope

| Acció | Fitxer |
|-------|--------|
| MODIFICAR | `frontend/index.html` |
| CREAR | `frontend/seguiment.html` |

**Fora de scope (no tocar):** `backend/`, `frontend/alertes.*`, `frontend/auth.js`.

---

## Pas 1 — Botó "Seguir centres" a `index.html`

### Context de la zona a modificar

El panell de centres de cada oferta a `index.html` s'obre quan l'usuari clica "Centres"
al costat d'una fila. El bloc rellevant (línies ~1580–1690) té:
- Filtre CCAA (select)
- Buscador de centres (input)
- Llista de centres

Cal afegir el botó **just a sota de la capçalera del panell** (a prop de la barra de filtres
però fora del loop de centres), visible únicament per a usuaris loguejats.

### 1a. Afegir la funció al bloc Alpine `x-data`

Al bloc de dades Alpine (al voltant de la línia 1032, on es defineixen `loggedIn`, `filterGrado`,
etc.), afegiu les noves propietats i funcions a continuació de les existents d'alertes:

```js
// F4 — Seguiment de centres
watchSaving: false,
watchSaveError: '',
watchSaved: {},      // {oferta_key: true} — marcat si l'usuari ja segueix aquesta oferta
watchedOfertaKeys: new Set(),

async loadWatches() {
  try {
    const res = await fetch(API_BASE + '/api/centres-watch', { credentials: 'include' });
    if (!res.ok) return;
    const data = await res.json();
    this.watchedOfertaKeys = new Set(data.filter(w => w.active).map(w => w.oferta_key));
  } catch (e) { /* silenci */ }
},

async toggleWatch(row) {
  if (!this.loggedIn) { this.showCentresModal(); return; }
  const key = row.codigo || String(row.id);
  if (this.watchedOfertaKeys.has(key)) return; // ja seguit — redirigir a seguiment.html
  this.watchSaving = true;
  this.watchSaveError = '';
  try {
    const res = await fetch(API_BASE + '/api/centres-watch', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        oferta_key: key,
        oferta_denom: row.denominacion || row.denominacio || '',
      })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      this.watchSaveError = err.error || 'Error desconegut';
      return;
    }
    this.watchedOfertaKeys = new Set([...this.watchedOfertaKeys, key]);
    this.watchSaved[key] = true;
    setTimeout(() => { delete this.watchSaved[key]; }, 3000);
  } catch (e) {
    this.watchSaveError = 'Error de xarxa';
  } finally {
    this.watchSaving = false;
  }
},
```

A la funció `init()` existent, afegiu `this.loadWatches()` a continuació de `this.loadFavorites()`:

```js
if (this.loggedIn) {
  this.loadFavorites();
  this.loadWatches();   // ← AFEGIR
}
```

### 1b. Afegir el botó al panell de centres

Busqueu la capçalera del panell de centres a `index.html`. Té aquesta estructura aproximada
(línies ~1580–1600):

```html
<div class="centres-header">
  <div class="centres-filters">
    <select ...>...</select>
    <input ...>
  </div>
</div>
```

Afegiu el botó **dins de `.centres-header`**, a la dreta dels filtres:

```html
<template x-if="loggedIn">
  <button
    class="watch-btn"
    :class="{ 'watch-btn--active': watchedOfertaKeys.has(row.codigo || String(row.id)) }"
    :disabled="watchSaving"
    @click.stop="watchedOfertaKeys.has(row.codigo || String(row.id))
      ? (window.location.href = 'seguiment.html')
      : toggleWatch(row)"
    x-text="watchedOfertaKeys.has(row.codigo || String(row.id))
      ? (watchSaved[row.codigo || String(row.id)] ? '✓ Seguiment desat!' : 'Seguint centres →')
      : 'Seguir centres'"
  ></button>
</template>
```

### 1c. Afegir CSS del botó

Afegiu el CSS just a sota de les regles de `.delete-btn` o dels botons de centres existents
(a la secció `<style>` de `index.html`):

```css
.watch-btn {
  font-size: 12px; font-weight: 600; font-family: inherit;
  padding: 5px 12px; border-radius: 4px; cursor: pointer;
  background: var(--white); color: var(--dark);
  border: 1px solid var(--border); white-space: nowrap;
  transition: background 0.15s;
}
.watch-btn:hover { background: var(--warm2); }
.watch-btn--active { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.watch-btn:disabled { opacity: 0.5; cursor: default; }
```

**Verificació visual:** Obre `index.html` al navegador → despliega el panell de centres
d'una oferta → ha d'aparèixer el botó "Seguir centres" per a usuaris loguejats.
Clica'l → ha de canviar a "Seguint centres →". Clica de nou → ha de redirigir a `seguiment.html`.

---

## Pas 2 — Pàgina `seguiment.html`

Crea `frontend/seguiment.html`. Utilitza exactament el mateix layout visual i la mateixa
estructura que `frontend/alertes.html`: topbar, hero, taula, footer. La diferència és
la taula i les accions.

### Estructura completa de `seguiment.html`

```html
<!DOCTYPE html>
<html lang="ca">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Seguiment de centres — Cercador Graus FP</title>

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

    .topbar { background: var(--dark); padding: 0 48px; }
    .topbar-inner { display: flex; align-items: center; height: 52px; }
    .topbar-logo { font-family: 'DM Serif Display', serif; color: var(--white); font-size: 20px; letter-spacing: -0.3px; text-decoration: none; }
    #auth-widget { margin-left: auto; display: flex; align-items: center; gap: 8px; }
    .auth-greeting { color: rgba(255,255,255,0.75); font-size: 13px; }
    .auth-btn { font-size: 13px; padding: 5px 14px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.35); color: var(--white); background: transparent; cursor: pointer; text-decoration: none; font-family: inherit; transition: background 0.15s; }
    .auth-btn:hover { background: rgba(255,255,255,0.12); }
    .auth-btn--primary { background: var(--white); color: var(--dark); border-color: var(--white); }
    .auth-btn--primary:hover { background: var(--warm2); }

    .hero { border-bottom: 2px solid var(--dark); padding: 40px 48px 32px; }
    .hero h1 { font-family: 'DM Serif Display', serif; font-size: 48px; font-weight: 400; line-height: 1.05; color: var(--dark); margin-bottom: 10px; }
    .hero-sub { font-size: 15px; color: var(--warm); }

    .content { padding: 28px 48px 64px; }

    .results-table { width: 100%; border-collapse: collapse; font-size: 14px; background: var(--white); border: 1px solid var(--border); border-radius: 2px; overflow: hidden; }
    .results-table thead tr { background: var(--warm2); border-bottom: 2px solid var(--dark); }
    .results-table th { text-align: left; padding: 11px 16px; font-weight: 600; color: var(--dark); font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; }
    .results-table th.col-prov { width: 160px; }
    .results-table th.col-created, .results-table th.col-sent { width: 140px; }
    .results-table th.col-active { width: 100px; }
    .results-table th.col-actions { width: 48px; }
    .results-table td { padding: 13px 16px; border-bottom: 1px solid var(--border); vertical-align: middle; }
    .results-table tbody tr:hover td { background: var(--warm2); }
    .results-table tbody tr:last-child td { border-bottom: none; }
    .results-table td.col-prov, .results-table td.col-created, .results-table td.col-sent { font-family: 'Geist Mono', monospace; font-size: 12px; color: var(--warm); white-space: nowrap; }

    .toggle-btn { font-size: 12px; font-weight: 600; font-family: inherit; padding: 4px 10px; border-radius: 4px; cursor: pointer; border: none; }
    .toggle-btn--active { background: #dcfce7; color: #166534; }
    .toggle-btn--inactive { background: var(--warm2); color: var(--warm); }
    .toggle-btn:hover { filter: brightness(0.92); }
    .toggle-btn:disabled { opacity: 0.5; cursor: default; }

    .delete-btn { background: none; border: none; cursor: pointer; color: var(--warm); font-size: 14px; padding: 4px 8px; border-radius: 4px; }
    .delete-btn:hover { color: #991b1b; background: #fee2e2; }
    .delete-btn:disabled { opacity: 0.5; cursor: default; }

    .empty-state { text-align: center; color: var(--warm); padding: 64px 48px; }
    .empty-state a { color: var(--dark); }
    @keyframes spin { to { transform: rotate(360deg); } }
    .loading-state { display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 64px 48px; color: var(--warm); }
    .spinner { border: 3px solid var(--border); border-top-color: var(--dark); border-radius: 50%; width: 32px; height: 32px; animation: spin 0.8s linear infinite; }

    footer { border-top: 1px solid var(--border); padding: 20px 48px; text-align: right; }
    footer a { font-size: 13px; color: var(--warm); text-decoration: none; }
    footer a:hover { color: var(--dark); }

    @media (max-width: 768px) {
      .topbar { padding: 0 16px; }
      .hero { padding: 24px 16px 20px; }
      .hero h1 { font-size: 30px; }
      .content { padding: 16px 16px 32px; }
      .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
      .results-table { min-width: 560px; }
      footer { padding: 20px 16px; }
    }
  </style>
  <script src="auth.js"></script>
</head>
<body>
  <nav class="topbar">
    <div class="topbar-inner">
      <a class="topbar-logo" href="index.html">Cercador FP España</a>
      <div id="auth-widget"></div>
    </div>
  </nav>

  <header class="hero">
    <h1>Seguiment de centres</h1>
    <p class="hero-sub">Rebràs un email quan apareguin nous centres que impartiran els ensenyaments que segueixes.</p>
  </header>

  <main class="content">
    <div class="table-wrap" id="main-content">
      <div class="loading-state">
        <div class="spinner"></div>
        <span>Carregant seguiments…</span>
      </div>
    </div>
  </main>

  <footer>
    <a href="index.html">← Tornar al cercador</a>
    &nbsp;·&nbsp;
    <a href="alertes.html">Les meves alertes</a>
    &nbsp;·&nbsp;
    <a href="politica-privacitat.html">Política de privacitat</a>
  </footer>

  <script>
  (function () {
    const API_BASE = window.location.hostname === 'localhost'
      ? 'http://localhost:5001' : '';

    function esc(s) {
      return String(s).replace(/[&<>"']/g, c =>
        ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    }

    async function fetchWatches() {
      const res = await fetch(API_BASE + '/api/centres-watch', { credentials: 'include' });
      if (res.status === 401) {
        window.location.href = 'login.html?next=seguiment.html';
        return null;
      }
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }

    async function deleteWatch(id) {
      const res = await fetch(API_BASE + '/api/centres-watch/' + id, {
        method: 'DELETE', credentials: 'include'
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
    }

    async function toggleWatch(id, active) {
      const res = await fetch(API_BASE + '/api/centres-watch/' + id, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active })
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    }

    function formatDate(iso) {
      if (!iso) return '—';
      return iso.slice(0, 10);
    }

    function renderWatches(watches) {
      const main = document.getElementById('main-content');
      if (!watches.length) {
        main.innerHTML = '<p class="empty-state">Encara no segueixes cap ensenyament.<br>'
          + 'Obre el panell de centres d\'un ensenyament al <a href="index.html">cercador</a>'
          + ' i clica "Seguir centres".</p>';
        return;
      }
      const rows = watches.map(w => `
        <tr id="watch-row-${w.id}">
          <td>${esc(w.oferta_denom)}</td>
          <td class="col-prov">${w.provincia_filter ? esc(w.provincia_filter) : '<span style="color:var(--warm)">Totes</span>'}</td>
          <td class="col-created">${formatDate(w.created_at)}</td>
          <td class="col-sent">${formatDate(w.last_sent_at)}</td>
          <td class="col-active">
            <button class="toggle-btn ${w.active ? 'toggle-btn--active' : 'toggle-btn--inactive'}"
              data-id="${w.id}" data-active="${w.active ? '1' : '0'}"
              onclick="handleToggle(${w.id}, ${w.active ? 0 : 1})">
              ${w.active ? 'Actiu' : 'Inactiu'}
            </button>
          </td>
          <td class="col-actions">
            <button class="delete-btn" title="Elimina" onclick="handleDelete(${w.id})">✕</button>
          </td>
        </tr>
      `).join('');
      main.innerHTML = `
        <table class="results-table">
          <thead><tr>
            <th>Ensenyament</th>
            <th class="col-prov">Província</th>
            <th class="col-created">Creat</th>
            <th class="col-sent">Darrer enviament</th>
            <th class="col-active">Estat</th>
            <th class="col-actions"></th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>`;
    }

    window.handleDelete = async function (id) {
      const row = document.getElementById('watch-row-' + id);
      const btn = row && row.querySelector('.delete-btn');
      if (btn) btn.disabled = true;
      try {
        await deleteWatch(id);
        if (row) row.remove();
        const tbody = document.querySelector('.results-table tbody');
        if (tbody && !tbody.children.length) {
          document.getElementById('main-content').innerHTML =
            '<p class="empty-state">Encara no segueixes cap ensenyament.<br>'
            + 'Obre el panell de centres d\'un ensenyament al <a href="index.html">cercador</a>'
            + ' i clica "Seguir centres".</p>';
        }
      } catch (e) {
        if (btn) btn.disabled = false;
        alert('Error eliminant el seguiment: ' + e.message);
      }
    };

    window.handleToggle = async function (id, newActive) {
      const row = document.getElementById('watch-row-' + id);
      const btn = row && row.querySelector('.toggle-btn');
      if (btn) btn.disabled = true;
      try {
        const updated = await toggleWatch(id, !!newActive);
        if (btn) {
          btn.disabled = false;
          btn.className = 'toggle-btn ' + (updated.active ? 'toggle-btn--active' : 'toggle-btn--inactive');
          btn.textContent = updated.active ? 'Actiu' : 'Inactiu';
          btn.setAttribute('onclick', `handleToggle(${id}, ${updated.active ? 0 : 1})`);
        }
      } catch (e) {
        if (btn) btn.disabled = false;
        alert('Error canviant estat: ' + e.message);
      }
    };

    (async () => {
      try {
        const watches = await fetchWatches();
        if (watches !== null) renderWatches(watches);
      } catch (e) {
        document.getElementById('main-content').innerHTML =
          '<p class="empty-state">Error carregant els seguiments.</p>';
      }
    })();
  })();
  </script>
</body>
</html>
```

**Verificació:** Obre `seguiment.html` sense estar logat → ha de redirigir a `login.html?next=seguiment.html`.
Logat sense seguiments → ha de mostrar l'estat buit amb l'enllaç al cercador.

---

## Verificació final del pla

### Test manual complet (seqüència mínima):

1. Arrenca el servidor: `cd backend && python3 app.py`
2. Obre `index.html` al navegador, fes login.
3. Cerca qualsevol oferta que tingui centres. Clica "Centres".
4. Ha d'aparèixer el botó "Seguir centres".
5. Clica'l → ha de canviar a "Seguint centres →" durant 3 s i retornar a "Seguint centres →".
6. Obre `seguiment.html` → ha de mostrar el seguiment creat amb estat "Actiu".
7. Clica "Inactiu" → canvia a "Inactiu".
8. Clica "✕" → elimina la fila.
9. Clica el botó "Seguir centres" d'un altre ensenyament sense estar logat → ha d'obrir el modal de login gating.

---

## Criteris de DONE

- [ ] Botó "Seguir centres" visible al panell de centres per a usuaris loguejats
- [ ] El botó desapareix (o mostra "Seguint →") si l'oferta ja és seguida
- [ ] Per a usuaris no loguejats, el botó mostra el modal de login gating (no intenta fer POST)
- [ ] `seguiment.html` existent i accessible des de la barra de navegació
- [ ] Redirecció a `login.html` si es visita `seguiment.html` sense sessió
- [ ] Llistat de seguiments amb columnes: Ensenyament, Província, Creat, Darrer enviament, Estat, Eliminar
- [ ] Toggle actiu/inactiu funcional
- [ ] Eliminar funcional (fila desapareix sense recarregar la pàgina)
- [ ] Estat buit amb missatge i enllaç al cercador

## STOP conditions

- Si `row.codigo` és undefined per a alguna oferta (no hauria de passar — totes les ofertes Grado C LOE en tenen; les D/E usen `row.id`), inspeccioneu l'estructura de l'objecte a la consola i reporteu. No improvisseu l'`oferta_key`.
- Si el modal de login gating (`showCentresModal`) no existeix a `index.html` o té un nom diferent, busqueu la funció real i useu-la en lloc de la hardcodejada.

## Nota de manteniment

- El botó de "Seguir centres" es troba dins del panell Alpine de cada fila. Si en el futur es refactoritza el component de la fila, caldrà moure el botó al nou lloc.
- La pàgina `seguiment.html` no usa Alpine.js — és JS vanilla pur, igual que `alertes.html`. Mantenir-la consistent amb `alertes.html` en qualsevol redisseny de layout.
- Si en el futur s'afegeix la funcionalitat de filtrar per província des del botó (pas de creació), cal ampliar el `toggleWatch(row)` per passar el `provincia_filter` com a paràmetre opcional.
