/* Shared site footer: renders the same links into <footer id="site-footer"> on every page.
   Include right after the placeholder; uses window.t (i18n.js) when loaded, Catalan otherwise.
   Relabels itself on i18n.js 'langchange' (pages that switch language without reloading). */
(function () {
  var footer = document.getElementById('site-footer');
  if (!footer) return;

  var LINKS = [
    { href: 'per-que-grausfp.html', key: 'footer.perque', ca: 'Per què GrausFP?' },
    { href: 'com-funciona.html', key: 'footer.com', ca: 'Com funciona' },
    { href: 'fonts.html', key: 'footer.fonts', ca: 'Fonts de dades' },
    { href: 'historial.html', key: 'footer.historial', ca: "Historial d'actualitzacions" },
    { href: 'observatori.html', key: 'footer.obs', ca: 'Observatori' },
    { href: 'que-em-falta.html', key: 'footer.gap', ca: 'Què em falta?' },
    { href: 'politica-privacitat.html', key: 'footer.priv', ca: 'Política de privacitat' },
    { href: 'avis-legal.html', key: 'footer.legal', ca: 'Avís legal' }
  ];

  var currentPage = location.pathname.split('/').pop() || 'index.html';

  function label(link) {
    var text = typeof window.t === 'function' ? window.t(link.key) : link.key;
    /* t() returns the key itself when a cached i18n.js lacks it: show Catalan instead */
    return text === link.key ? link.ca : text;
  }

  var anchors = LINKS.map(function (link) {
    var anchor = document.createElement('a');
    anchor.href = link.href;
    anchor.textContent = label(link);
    if (link.href === currentPage) anchor.setAttribute('aria-current', 'page');
    footer.appendChild(anchor);
    return anchor;
  });

  document.addEventListener('langchange', function () {
    anchors.forEach(function (anchor, i) { anchor.textContent = label(LINKS[i]); });
  });
})();
