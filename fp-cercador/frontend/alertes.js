(function () {
  var API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5001' : '';

  var LOCALE = getLang() === 'ca' ? 'ca-ES' : 'es-ES';

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c];
    });
  }

  function buildFilterDescription(filter) {
    var parts = [];
    if (filter.grado)           parts.push('Grado ' + filter.grado);
    if (filter.familia)         parts.push(filter.familia);
    if (filter.nivel != null)   parts.push(t('alertes.filter.niv') + filter.nivel);
    if (filter.texto)           parts.push('Texto: «' + filter.texto + '»');
    return parts.length ? parts.join(' · ') : t('alertes.filter.all');
  }

  async function fetchAlerts() {
    var res = await fetch(API_BASE + '/api/alerts', { credentials: 'include' });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  async function createAlert(filterDict) {
    var res = await fetch(API_BASE + '/api/alerts', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filter_json: filterDict })
    });
    if (!res.ok) {
      var err = await res.json().catch(function () { return {}; });
      throw new Error(err.error || 'HTTP ' + res.status);
    }
    return res.json();
  }

  async function deleteAlert(id) {
    var res = await fetch(API_BASE + '/api/alerts/' + id, {
      method: 'DELETE', credentials: 'include'
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
  }

  async function toggleAlert(id, active) {
    var res = await fetch(API_BASE + '/api/alerts/' + id, {
      method: 'PATCH',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: active })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    return res.json();
  }

  function renderAlerts(alerts) {
    var main = document.getElementById('main-content');
    if (!alerts.length) {
      main.innerHTML = '<p class="empty-state">' + t('alertes.empty') + '</p>';
      return;
    }
    var rows = alerts.map(function (a) {
      var filter = JSON.parse(a.filter_json || '{}');
      var desc = buildFilterDescription(filter);
      var active = a.active === 1 || a.active === true;
      var lastSent = a.last_sent_at
        ? new Date(a.last_sent_at).toLocaleDateString(LOCALE)
        : '—';
      var created = a.created_at
        ? new Date(a.created_at).toLocaleString(LOCALE, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
      return '<tr>' +
        '<td class="col-desc">' + esc(desc) + '</td>' +
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

    main.innerHTML =
      '<div class="table-wrap">' +
      '<table class="results-table">' +
      '<thead><tr>' +
        '<th scope="col">' + t('alertes.col.filter') + '</th>' +
        '<th scope="col" class="col-created">' + t('alertes.col.created') + '</th>' +
        '<th scope="col" class="col-sent">' + t('alertes.col.sent') + '</th>' +
        '<th scope="col" class="col-active">' + t('alertes.col.state') + '</th>' +
        '<th scope="col" class="col-actions"></th>' +
      '</tr></thead>' +
      '<tbody>' + rows + '</tbody>' +
      '</table></div>';

    main.querySelectorAll('.toggle-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        var id = parseInt(btn.dataset.id);
        var currentActive = btn.dataset.active === '1';
        btn.disabled = true;
        try {
          await toggleAlert(id, !currentActive);
          await load();
        } catch (e) {
          btn.disabled = false;
          alert(t('alertes.err.toggle') + e.message);
        }
      });
    });

    main.querySelectorAll('.delete-btn').forEach(function (btn) {
      btn.addEventListener('click', async function () {
        if (!confirm(t('alertes.confirm.delete'))) return;
        var id = parseInt(btn.dataset.id);
        btn.disabled = true;
        try {
          await deleteAlert(id);
          await load();
        } catch (e) {
          btn.disabled = false;
          alert(t('alertes.err.delete') + e.message);
        }
      });
    });
  }

  async function load() {
    var main = document.getElementById('main-content');
    main.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>' + t('alertes.loading') + '</p></div>';
    try {
      var res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (!res.ok) {
        main.innerHTML = '<p class="empty-state">' + t('alertes.login.required') + '</p>';
        return;
      }
      var alerts = await fetchAlerts();
      renderAlerts(alerts);
    } catch (e) {
      main.innerHTML = '<p class="empty-state" style="color:#991b1b;">' + t('alertes.error') + '</p>';
    }
  }

  document.addEventListener('DOMContentLoaded', load);
})();
