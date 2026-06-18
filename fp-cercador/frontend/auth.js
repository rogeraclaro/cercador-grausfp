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
    await fetch(API_BASE + '/api/auth/logout', { method: 'POST', credentials: 'include' });
    window.location.reload();
  }

  function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function showVerifiedToast() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('verified') !== '1') return;
    history.replaceState(null, '', window.location.pathname);
    var toast = document.createElement('div');
    toast.textContent = t('auth.verified.toast');
    Object.assign(toast.style, {
      position: 'fixed', top: '24px', left: '50%',
      transform: 'translateX(-50%)',
      background: '#2e7d32', color: '#fff',
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

  document.addEventListener('DOMContentLoaded', function () { initAuth(); showVerifiedToast(); });
})();
