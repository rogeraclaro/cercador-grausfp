/* Fitxer .ics d'un curs FPO (Pla 086): esdeveniment de dia sencer el dia que comença.
   Sense llibreria ni backend. RFC 5545: CRLF, text escapat i línies plegades a 75 octets.
   Compartit per l'agenda i pel detall d'una especialitat (index.html); també es pot
   carregar des de Node per provar-ne el format (scripts/test_ics.js). */
(function (root) {
  var LABELS = {
    ca: { hores: 'Hores', modalitat: 'Modalitat', fi: 'Acaba', fitxa: 'Fitxa del curs', curs: 'curs' },
    es: { hores: 'Horas', modalitat: 'Modalidad', fi: 'Termina', fitxa: 'Ficha del curso', curs: 'curso' }
  };

  function escapeText(s) {
    return String(s == null ? '' : s)
      .replace(/\\/g, '\\\\').replace(/;/g, '\;').replace(/,/g, '\\,').replace(/\r\n|\r|\n/g, '\\n');
  }

  function utf8Length(ch) {
    var code = ch.codePointAt(0);
    return code < 0x80 ? 1 : code < 0x800 ? 2 : code < 0x10000 ? 3 : 4;
  }

  /* Plega a 75 octets sense partir cap caràcter; les línies de continuació comencen amb un espai. */
  function fold(line) {
    var out = [], current = '', size = 0;
    Array.from(line).forEach(function (ch) {
      var n = utf8Length(ch);
      if (size + n > 75) { out.push(current); current = ' '; size = 1; }
      current += ch;
      size += n;
    });
    out.push(current);
    return out.join('\r\n');
  }

  function compactDate(iso) { return String(iso).replace(/-/g, ''); }

  function nextDay(iso) {
    var p = String(iso).split('-').map(Number);
    return new Date(Date.UTC(p[0], p[1] - 1, p[2] + 1)).toISOString().slice(0, 10);
  }

  function longDate(iso) {
    var p = String(iso || '').split('-');
    return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : '';
  }

  function slug(text) {
    return String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase()
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60);
  }

  function title(curs, lang) {
    var ti = curs.titol || {};
    return (typeof ti === 'string' ? ti : ti[lang] || ti.ca || ti.es) || '';
  }

  /* `curs`: una fila de /api/fpo/agenda o un curs del detall d'una especialitat.
     `now` (Date) només per a les proves. Torna '' si el curs no té data d'inici. */
  function buildIcs(curs, lang, now) {
    if (!curs || !/^\d{4}-\d{2}-\d{2}$/.test(curs.dataInici || '')) return '';
    var L = LABELS[lang] || LABELS.ca;
    var centre = curs.centre || {};
    var where = [curs.centreNom || centre.nom,
      curs.centreAdreca || [centre.carrer, centre.cp, centre.municipi].filter(Boolean).join(', ')]
      .filter(Boolean).join(', ');
    var details = [];
    if (curs.hores) details.push(L.hores + ': ' + Math.round(curs.hores));
    if (curs.modalitat) details.push(L.modalitat + ': ' + curs.modalitat);
    if (curs.dataFi) details.push(L.fi + ': ' + longDate(curs.dataFi));
    if (curs.fitxaUrl) details.push(L.fitxa + ': ' + curs.fitxaUrl);
    var stamp = (now || new Date()).toISOString().replace(/[-:]/g, '').replace(/\.\d+/, '');
    var lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//GrausFP//Cursos FPO//CA',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VEVENT',
      'UID:' + String(curs.idCurs || slug(title(curs, lang))).replace(/[^A-Za-z0-9._-]+/g, '-') + '@grausfp.es',
      'DTSTAMP:' + stamp,
      'DTSTART;VALUE=DATE:' + compactDate(curs.dataInici),
      'DTEND;VALUE=DATE:' + compactDate(nextDay(curs.dataInici)),
      'SUMMARY:' + escapeText(title(curs, lang))
    ];
    if (where) lines.push('LOCATION:' + escapeText(where));
    if (details.length) lines.push('DESCRIPTION:' + escapeText(details.join('\n')));
    if (curs.fitxaUrl) lines.push('URL:' + curs.fitxaUrl);
    lines.push('TRANSP:TRANSPARENT', 'END:VEVENT', 'END:VCALENDAR');
    return lines.map(fold).join('\r\n') + '\r\n';
  }

  function fileName(curs, lang) {
    return ((LABELS[lang] || LABELS.ca).curs === 'curso' ? 'curso-' : 'curs-') + (slug(title(curs, lang)) || 'fpo') + '.ics';
  }

  function downloadIcs(curs, lang) {
    var ics = buildIcs(curs, lang);
    if (!ics) return false;
    var url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar;charset=utf-8' }));
    var link = document.createElement('a');
    link.href = url;
    link.download = fileName(curs, lang);
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
    return true;
  }

  var api = { buildIcs: buildIcs, downloadIcs: downloadIcs, fileName: fileName };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.GFPIcs = api;
})(typeof window !== 'undefined' ? window : this);
