/* Graus que la persona diu que ja té («Ja el tinc», Pla 083). Es desen al navegador
   (localStorage 'heldRefs', llista de ref) i, amb sessió, també al compte (/api/held).
   Compartit per que-em-falta.html, index.html i itinerari.html. */
(function () {
  var API_BASE = window.location.hostname === 'localhost' ? 'http://localhost:5001' : '';
  var KEY = 'heldRefs';
  var MAX = 50; /* mateix límit que el backend */
  var loggedIn = false;

  function clean(refs) {
    var out = [];
    (Array.isArray(refs) ? refs : []).forEach(function (ref) {
      if (typeof ref === 'string' && ref && ref.length <= 200 && out.indexOf(ref) < 0 && out.length < MAX) out.push(ref);
    });
    return out;
  }

  function read() {
    try { return clean(JSON.parse(localStorage.getItem(KEY))); } catch (e) { return []; }
  }

  function write(refs) {
    try { localStorage.setItem(KEY, JSON.stringify(refs)); } catch (e) { /* mode privat: només en memòria */ }
  }

  function push(refs) {
    if (!loggedIn) return;
    fetch(API_BASE + '/api/held', {
      method: 'PUT', credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refs: refs })
    }).catch(function () { /* queda al navegador; es torna a provar al canvi següent */ });
  }

  window.GFPHeld = {
    MAX: MAX,
    read: read,
    save: function (refs) {
      refs = clean(refs);
      write(refs);
      push(refs);
      return refs;
    },
    toggle: function (ref) {
      var refs = read();
      var at = refs.indexOf(ref);
      if (at >= 0) refs.splice(at, 1); else refs.push(ref);
      return this.save(refs);
    },
    /* Amb sessió, la llista és la unió de la del navegador i la del compte. */
    init: async function (isLoggedIn) {
      loggedIn = !!isLoggedIn;
      var local = read();
      if (!loggedIn) return local;
      try {
        var res = await fetch(API_BASE + '/api/held', { credentials: 'include' });
        if (!res.ok) return local;
        var account = clean((await res.json()).refs);
        var merged = clean(account.concat(local));
        write(merged);
        if (merged.length !== account.length) push(merged);
        return merged;
      } catch (e) {
        return local;
      }
    }
  };
})();
