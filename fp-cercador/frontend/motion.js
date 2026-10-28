/* motion.js — guarda per a les microanimacions GSAP (fase 07).
 * Carregar DESPRÉS de vendor/gsap-*.min.js. Sense GSAP o amb prefers-reduced-motion: reduce
 * tot és un no-op i la pàgina es comporta exactament com abans. */
(function () {
  'use strict';
  var enabled = false;   // només mentre la consulta de moviment permès coincideix i GSAP existeix
  var slots = {};        // nom -> gsap.context de l'animació en curs

  function stop(name) {
    var c = slots[name];
    if (c) { slots[name] = null; try { c.revert(); } catch (e) { } }
  }

  if (window.gsap && typeof gsap.matchMedia === 'function') {
    try {
      gsap.matchMedia().add('(prefers-reduced-motion: no-preference)', function () {
        enabled = true;
        // Es crida quan la consulta deixa de coincidir: les animacions en curs tornen a l'estat final.
        return function () { enabled = false; Object.keys(slots).forEach(stop); };
      });
    } catch (e) { enabled = false; }
  }

  window.GFPMotion = {
    // build(gsap) crea els tweens de manera síncrona; pot retornar una funció de neteja (s'executa en revertir).
    play: function (name, build) {
      if (!enabled) return false;
      stop(name);   // reverteix l'animació anterior del mateix slot (neteja també els estils en línia)
      var failed = false;
      // NB: el context sempre es crea passant-hi una funció; sense funció no crea res i retorna el context actual.
      var c = gsap.context(function () {
        try { return build(gsap); } catch (e) { failed = true; if (window.console) console.warn('[motion]', e); }
      });
      if (failed) { try { c.revert(); } catch (e) { } return false; }
      slots[name] = c;
      return true;
    },
    stop: stop
  };
})();
