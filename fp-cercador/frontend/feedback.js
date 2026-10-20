/* Shared feedback tab + dialog (plan 069): a vertical "Feedback" tab on the right edge that
   opens a native <dialog>. Include right after footer.js; styles live in site.css (.fb-*).
   Uses window.t (i18n.js) when loaded, Catalan otherwise. Anonymous visitors must give an
   email; signed-in users send with their account (checked against /api/auth/me on open). */
(function () {
  if (document.getElementById('fb-tab')) return;

  var API_BASE = (location.hostname === 'localhost' || location.hostname === '')
    ? 'http://localhost:5001' : '';
  var MAX_CHARS = 2000;
  /* Query params that may carry secrets or personal data: never sent as context. */
  var SENSITIVE_PARAMS = ['token', 'code', 'state', 'email', 'password', 'key', 'session'];

  var CA = {
    'fb.tab': 'Feedback',
    'fb.dialog.aria': 'Envia un comentari',
    'fb.title': 'Què vols dir-nos?',
    'fb.kinds.aria': 'Tipus de comentari',
    'fb.kind.error': 'Error',
    'fb.kind.idea': 'Idea',
    'fb.kind.data': 'Dades incorrectes',
    'fb.kind.other': 'Altre',
    'fb.label': 'Explica-ho amb una frase. Ja sabem en quina pàgina eres.',
    'fb.email.label': 'El teu email, per poder-te respondre',
    'fb.cancel': 'Cancel·la',
    'fb.send': 'Envia',
    'fb.sending': 'Enviant…',
    'fb.thanks': 'Gràcies!',
    'fb.thanks.body': 'El comentari ha arribat. El llegirem aviat.',
    'fb.close': 'Tanca',
    'fb.err.empty': 'Escriu un comentari.',
    'fb.err.email': 'Cal un email vàlid perquè et puguem respondre.',
    'fb.err.rate': "Has enviat massa comentaris. Torna-ho a provar d'aquí a una estona.",
    'fb.err.send': "No s'ha pogut enviar. Torna-ho a provar."
  };
  var KINDS = ['error', 'idea', 'data', 'other'];

  function tr(key) {
    var label = typeof window.t === 'function' ? window.t(key) : key;
    /* t() returns the key itself when a cached i18n.js lacks it: show Catalan instead */
    return label === key ? CA[key] : label;
  }

  function pageContext() {
    var params = new URLSearchParams(location.search);
    SENSITIVE_PARAMS.forEach(function (name) {
      Array.from(params.keys()).forEach(function (k) {
        if (k.toLowerCase() === name) params.delete(k);
      });
    });
    var query = params.toString();
    return {
      path: location.pathname,
      query: query ? '?' + query : '',
      lang: typeof window.getLang === 'function' ? window.getLang() : 'ca'
    };
  }

  var tab = document.createElement('button');
  tab.type = 'button';
  tab.id = 'fb-tab';
  tab.className = 'fb-tab';
  tab.textContent = tr('fb.tab');

  var dialog = document.createElement('dialog');
  dialog.className = 'fb-dialog';
  dialog.setAttribute('aria-label', tr('fb.dialog.aria'));
  dialog.innerHTML =
    '<form class="fb-body" id="fb-form" novalidate>' +
      '<p class="fb-title">' + tr('fb.title') + '</p>' +
      '<div class="fb-kinds" role="group" aria-label="' + tr('fb.kinds.aria') + '">' +
        KINDS.map(function (k) {
          return '<button type="button" class="fb-kind" data-kind="' + k + '" aria-pressed="false">' +
            tr('fb.kind.' + k) + '</button>';
        }).join('') +
      '</div>' +
      '<label for="fb-text" class="fb-label">' + tr('fb.label') + '</label>' +
      '<textarea id="fb-text" class="fb-input fb-textarea" rows="5" maxlength="' + MAX_CHARS + '"></textarea>' +
      '<div class="fb-email-row" id="fb-email-row" hidden>' +
        '<label for="fb-email" class="fb-label">' + tr('fb.email.label') + '</label>' +
        '<input id="fb-email" class="fb-input" type="email" autocomplete="email" maxlength="254">' +
      '</div>' +
      /* Honeypot: hidden from people and assistive tech; bots that fill it are dropped silently */
      '<div class="fb-hp" aria-hidden="true">' +
        '<label for="fb-website">Website</label>' +
        '<input id="fb-website" name="website" type="text" tabindex="-1" autocomplete="off">' +
      '</div>' +
      '<p class="fb-error" id="fb-error" role="alert" hidden></p>' +
      '<div class="fb-actions">' +
        '<button type="button" class="fb-btn fb-btn--secondary" data-fb-close>' + tr('fb.cancel') + '</button>' +
        '<button type="submit" class="fb-btn fb-btn--primary" id="fb-submit">' + tr('fb.send') + '</button>' +
      '</div>' +
    '</form>' +
    '<div class="fb-body" id="fb-sent" hidden>' +
      '<p class="fb-title">' + tr('fb.thanks') + '</p>' +
      '<p>' + tr('fb.thanks.body') + '</p>' +
      '<div class="fb-actions">' +
        '<button type="button" class="fb-btn fb-btn--primary" data-fb-close>' + tr('fb.close') + '</button>' +
      '</div>' +
    '</div>';

  document.body.appendChild(tab);
  document.body.appendChild(dialog);

  var form = dialog.querySelector('#fb-form');
  var sent = dialog.querySelector('#fb-sent');
  var text = dialog.querySelector('#fb-text');
  var emailRow = dialog.querySelector('#fb-email-row');
  var email = dialog.querySelector('#fb-email');
  var honeypot = dialog.querySelector('#fb-website');
  var errorEl = dialog.querySelector('#fb-error');
  var submitBtn = dialog.querySelector('#fb-submit');
  var kind = 'other';
  var signedIn = null; /* unknown until the first open */

  function setKind(next) {
    kind = next;
    dialog.querySelectorAll('.fb-kind').forEach(function (btn) {
      btn.setAttribute('aria-pressed', String(btn.dataset.kind === kind));
    });
  }

  function showError(key) {
    errorEl.textContent = key ? tr(key) : '';
    errorEl.hidden = !key;
  }

  function checkSession() {
    if (signedIn !== null) return Promise.resolve(signedIn);
    return fetch(API_BASE + '/api/auth/me', { credentials: 'include' })
      .then(function (res) { signedIn = res.ok; return signedIn; })
      .catch(function () { return false; });
  }

  function open() {
    form.hidden = false;
    sent.hidden = true;
    text.value = '';
    honeypot.value = '';
    setKind('other');
    showError(null);
    submitBtn.disabled = false;
    submitBtn.textContent = tr('fb.send');
    if (!dialog.open) dialog.showModal();
    /* showModal focuses the first control; the text is what they came to write */
    text.focus();
    checkSession().then(function (isIn) { emailRow.hidden = isIn; });
  }

  function send(event) {
    event.preventDefault();
    var message = text.value.trim();
    if (!message) { showError('fb.err.empty'); text.focus(); return; }
    var body = { kind: kind, message: message, context: pageContext(), website: honeypot.value };
    if (!emailRow.hidden) {
      var address = email.value.trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(address)) { showError('fb.err.email'); email.focus(); return; }
      body.email = address;
    }
    showError(null);
    submitBtn.disabled = true;
    submitBtn.textContent = tr('fb.sending');
    fetch(API_BASE + '/api/feedback', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    }).then(function (res) {
      if (res.ok) {
        form.hidden = true;
        sent.hidden = false;
        sent.querySelector('[data-fb-close]').focus();
        return;
      }
      showError(res.status === 429 ? 'fb.err.rate' : 'fb.err.send');
      submitBtn.disabled = false;
      submitBtn.textContent = tr('fb.send');
    }).catch(function () {
      showError('fb.err.send');
      submitBtn.disabled = false;
      submitBtn.textContent = tr('fb.send');
    });
  }

  tab.addEventListener('click', open);
  form.addEventListener('submit', send);
  dialog.addEventListener('click', function (event) {
    var kindBtn = event.target.closest('.fb-kind');
    if (kindBtn) setKind(kindBtn.dataset.kind);
    if (event.target.closest('[data-fb-close]')) dialog.close();
  });
})();
