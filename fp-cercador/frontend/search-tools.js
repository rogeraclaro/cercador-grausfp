/* Eines pures del cercador per nom (Pla 087): l'estat de la cerca a l'adreça i els
   suggeriments «Volies dir…». Sense DOM: index.html les fa servir i scripts/test_search_tools.js
   les prova amb Node. */
(function (root) {
  var SORT_COLS = ['denominacion', 'codigo', 'familia', 'grado', 'nivel'];
  /* Paràmetres de l'adreça que pertanyen a la cerca per nom. */
  var PARAMS = ['q', 'grado', 'familia', 'nivel', 'pla', 'favs', 'ordre', 'dir', 'p', 'mod', 'hores'];
  /* Pla 097: filtres propis de la pestanya «Especialitats SEPE» (grado=SEPE). */
  var SEPE_MOD = ['dist', 'part', 'pres'];
  var SEPE_HORES = ['h30', 'h100', 'h300', 'hmes'];
  var MAX_QUERY = 200;

  /* Adreça → camps de l'estat. Només torna els que hi són i són vàlids; la resta s'ignora. */
  function stateFromParams(params, families) {
    var state = {};
    var q = (params.get('q') || '').slice(0, MAX_QUERY).trim();
    if (q) state.search = q;
    var grado = params.get('grado') || '';
    if (/^([A-E]|SEPE)$/.test(grado)) state.filterGrado = grado;  // SEPE: Pla 082
    var familia = params.get('familia');
    if (familia && (families || []).indexOf(familia) >= 0) state.filterFamilia = familia;
    var nivel = params.get('nivel') || '';
    if (/^[1-3]$/.test(nivel)) state.filterNivel = nivel;
    if (grado === 'SEPE') {
      // Al catàleg del SEPE l'escala arriba al 5 i hi ha especialitats sense nivell («none»)
      if (/^([45]|none)$/.test(nivel)) state.filterNivel = nivel;
      var mod = params.get('mod');
      if (SEPE_MOD.indexOf(mod) >= 0) state.filterSepeMod = mod;
      var hores = params.get('hores');
      if (SEPE_HORES.indexOf(hores) >= 0) state.filterSepeHores = hores;
    }
    var pla = params.get('pla');
    if (pla === 'hide' || pla === 'only') state.filterOld = pla;
    if (params.get('favs') === '1') state.filterFavs = true;
    var ordre = params.get('ordre');
    if (SORT_COLS.indexOf(ordre) >= 0) {
      state.sortCol = ordre;
      state.sortDir = params.get('dir') === 'desc' ? -1 : 1;
    }
    var p = params.get('p') || '';
    if (/^[1-9]\d{0,4}$/.test(p) && Number(p) > 1) state.currentPage = Number(p);
    return state;
  }

  /* Estat → parells [clau, valor] de l'adreça. Els valors per defecte no s'escriuen. */
  function paramsFromState(state) {
    var out = [];
    var q = String(state.search || '').trim().slice(0, MAX_QUERY);
    if (q) out.push(['q', q]);
    if (state.filterGrado) out.push(['grado', state.filterGrado]);
    if (state.filterFamilia) out.push(['familia', state.filterFamilia]);
    if (state.filterNivel) out.push(['nivel', String(state.filterNivel)]);
    if (state.filterOld && state.filterOld !== 'all') out.push(['pla', state.filterOld]);
    if (state.filterFavs) out.push(['favs', '1']);
    if (state.sortCol && state.sortDir) {
      out.push(['ordre', state.sortCol]);
      if (state.sortDir < 0) out.push(['dir', 'desc']);
    }
    if (state.currentPage > 1) out.push(['p', String(state.currentPage)]);
    if (state.filterGrado === 'SEPE') {
      if (state.filterSepeMod) out.push(['mod', state.filterSepeMod]);
      if (state.filterSepeHores) out.push(['hores', state.filterSepeHores]);
    }
    return out;
  }

  /* ── «Volies dir…» ── */

  function normalize(text) {
    return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  /* Paraules de 4 lletres o més de les denominacions (ja normalitzades), amb el nombre de
     registres on surten. */
  function buildVocabulary(normalizedNames) {
    var vocab = new Map();
    for (var i = 0; i < normalizedNames.length; i++) {
      var words = new Set(normalizedNames[i].split(/[^a-z0-9]+/));
      words.forEach(function (w) { if (w.length >= 4) vocab.set(w, (vocab.get(w) || 0) + 1); });
    }
    return vocab;
  }

  /* Distància d'edició amb tall: torna max + 1 tan bon punt se sap que el passa. */
  function boundedDistance(a, b, max) {
    if (Math.abs(a.length - b.length) > max) return max + 1;
    var prev = [], curr = [], i, j;
    for (j = 0; j <= b.length; j++) prev[j] = j;
    for (i = 1; i <= a.length; i++) {
      curr[0] = i;
      var best = curr[0];
      for (j = 1; j <= b.length; j++) {
        curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (a.charCodeAt(i - 1) === b.charCodeAt(j - 1) ? 0 : 1));
        if (curr[j] < best) best = curr[j];
      }
      if (best > max) return max + 1;
      var swap = prev; prev = curr; curr = swap;
    }
    return prev[b.length];
  }

  /* Fins a `limit` cerques semblants a `query` quan no ha donat cap resultat.
     - `vocab`: Map de buildVocabulary.
     - `opts.translate(token)`: variant en castellà d'un terme en català, o null.
     - `opts.test(cerca)`: true si aquella cerca dona resultats (filtra els suggeriments).
     Es corregeix una sola paraula: la que no surt enlloc. Si n'hi ha més d'una, o cap, []. */
  function suggest(query, vocab, opts) {
    opts = opts || {};
    var limit = opts.limit || 3;
    var tokens = normalize(query).trim().split(/\s+/).filter(Boolean);
    var words = Array.from(vocab.keys());
    var known = function (token) { return words.some(function (w) { return w.indexOf(token) >= 0; }); };
    var wrong = [];
    tokens.forEach(function (token, index) {
      if (token.length < 4 || known(token)) return;
      var es = opts.translate ? opts.translate(token) : null;
      if (es && known(es)) return;          // escrit en català i ja es tradueix: no cal suggerir res
      wrong.push(index);
    });
    if (wrong.length !== 1) return [];
    var token = tokens[wrong[0]];
    var max = token.length <= 5 ? 1 : 2;
    var candidates = [];
    vocab.forEach(function (count, word) {
      if (Math.abs(word.length - token.length) > 2) return;
      var d = boundedDistance(token, word, max);
      if (d <= max) candidates.push({ word: word, d: d, count: count });
    });
    candidates.sort(function (x, y) { return x.d - y.d || y.count - x.count || (x.word < y.word ? -1 : 1); });
    var out = [];
    for (var i = 0; i < candidates.length && out.length < limit; i++) {
      var fixed = tokens.slice();
      fixed[wrong[0]] = candidates[i].word;
      var text = fixed.join(' ');
      if (!opts.test || opts.test(text)) out.push(text);
    }
    return out;
  }

  var api = { PARAMS: PARAMS, SORT_COLS: SORT_COLS, stateFromParams: stateFromParams, paramsFromState: paramsFromState,
              normalize: normalize, buildVocabulary: buildVocabulary, boundedDistance: boundedDistance, suggest: suggest };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.GFPSearch = api;
})(typeof window !== 'undefined' ? window : this);
