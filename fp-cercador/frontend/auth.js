(function () {
  var API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:5001' : '';

  async function initAuth() {
    var widget = document.getElementById('auth-widget');
    if (!widget) return;
    try {
      var res = await fetch(API_BASE + '/api/auth/me', { credentials: 'include' });
      if (res.ok) {
        var data = await res.json();
        widget.innerHTML =
          '<span class="auth-greeting">' + t('nav.greeting', { email: escHtml(data.email) }) + '</span>' +
          (data.is_admin ? '<a class="auth-btn" href="admin.html">' + t('nav.admin') + '</a>' : '') +
          '<a class="auth-btn" href="perfil.html">' + t('nav.profile') + '</a>' +
          '<button class="auth-btn auth-btn--logout" id="btn-logout">' + t('nav.logout') + '</button>';
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
      '<a class="auth-btn" href="login.html">' + t('nav.login') + '</a>' +
      '<a class="auth-btn auth-btn--primary" href="register.html">' + t('nav.register') + '</a>';
  }

  async function logout() {
    await fetch(API_BASE + '/api/auth/logout', { method: 'POST', credentials: 'include' }).catch(function () { });
    window.location.reload();
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  // Avisos de tornada del backend: /?verified=1, /?unsubscribed=1, /?unsubscribe_error=1, /?google_error=<codi>.
  function showRedirectToast() {
    var url = new URL(window.location.href);
    var params = url.searchParams;
    var key = params.get('verified') === '1' ? 'auth.verified.toast'
      : params.get('unsubscribed') === '1' ? 'auth.unsubscribed.toast'
      : params.get('unsubscribe_error') === '1' ? 'auth.unsubscribe_error.toast'
      : params.get('google_error') ? 'auth.google_error.toast' : null;
    if (!key) return;
    var isError = key === 'auth.google_error.toast' || key === 'auth.unsubscribe_error.toast';
    ['verified', 'unsubscribed', 'unsubscribe_error', 'google_error'].forEach(function (k) { params.delete(k); });
    history.replaceState(null, '', url);
    var toast = document.createElement('div');
    toast.setAttribute('role', isError ? 'alert' : 'status');
    toast.textContent = t(key);
    Object.assign(toast.style, {
      position: 'fixed', top: '24px', left: '50%',
      transform: 'translateX(-50%)',
      background: isError ? '#b3261e' : '#2e7d32', color: '#fff',
      padding: '12px 24px', borderRadius: '8px',
      fontSize: '15px', fontWeight: '500',
      boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
      zIndex: '9999', opacity: '0',
      transition: 'opacity 0.3s ease',
    });
    document.body.appendChild(toast);
    requestAnimationFrame(function () { toast.style.opacity = '1'; });
    setTimeout(function () {
      toast.style.opacity = '0';
      setTimeout(function () { toast.remove(); }, 300);
    }, 5000);
  }

  document.addEventListener('DOMContentLoaded', function () { initAuth(); showRedirectToast(); });
})();
