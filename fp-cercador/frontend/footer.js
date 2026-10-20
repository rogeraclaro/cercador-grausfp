/* Shared site footer: renders the same links into <footer id="site-footer"> on every page.
   Include right after the placeholder; uses window.t (i18n.js) when loaded, Catalan otherwise. */
(function () {
  var footer = document.getElementById('site-footer');
  if (!footer) return;

  var LINKS = [
    { href: 'per-que-grausfp.html', key: 'footer.perque', ca: 'Per què GrausFP?' },
    { href: 'fonts.html', key: 'footer.fonts', ca: 'Fonts de dades' },
    { href: 'historial.html', key: 'footer.historial', ca: "Historial d'actualitzacions" },
    { href: 'observatori.html', key: 'footer.obs', ca: 'Observatori' },
    { href: 'politica-privacitat.html', key: 'footer.priv', ca: 'Política de privacitat' }
  ];

  var currentPage = location.pathname.split('/').pop() || 'index.html';

  LINKS.forEach(function (link) {
    var anchor = document.createElement('a');
    anchor.href = link.href;
    var label = typeof window.t === 'function' ? window.t(link.key) : link.key;
    /* t() returns the key itself when a cached i18n.js lacks it: show Catalan instead */
    anchor.textContent = label === link.key ? link.ca : label;
    if (link.href === currentPage) anchor.setAttribute('aria-current', 'page');
    footer.appendChild(anchor);
  });
})();
