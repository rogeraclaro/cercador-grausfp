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
