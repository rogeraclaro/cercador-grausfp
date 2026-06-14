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
          '<span class="auth-greeting">Hola, ' + escHtml(email) + '</span>' +
          '<button class="auth-btn auth-btn--logout" id="btn-logout">Sortir</button>';
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
      '<a class="auth-btn" href="login.html">Entra</a>' +
      '<a class="auth-btn auth-btn--primary" href="register.html">Registra\'t</a>';
  }

  async function logout() {
    await fetch(API_BASE + '/api/auth/logout', {
      method: 'POST', credentials: 'include'
    });
    window.location.reload();
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  document.addEventListener('DOMContentLoaded', initAuth);
})();
