// Format del .ics dels cursos FPO (Pla 086). Executar: node --test scripts/test_ics.js
const test = require('node:test');
const assert = require('node:assert');
const { buildIcs, fileName } = require('../frontend/ics.js');

const NOW = new Date(Date.UTC(2026, 10, 15, 9, 30, 0));
const CURS = {
  idCurs: '26/FOAP/123/0198494/035',
  titol: { ca: 'Gestió comptable, fiscal i laboral; nivell 2', es: 'Gestión contable, fiscal y laboral; nivel 2' },
  dataInici: '2026-12-31', dataFi: '2027-03-15', hores: 120.0, modalitat: 'PRESENCIAL',
  centreNom: "Centre d'Estudis Montsià", centreAdreca: 'C. Major, 1, 43870, Amposta',
  fitxaUrl: 'https://serveiocupacio.gencat.cat/ca/persones/vull-formar-me/cercadors-formacio-especialitats/cercador-integrat/fitxa-curs.html?codi_curso_seleccionado=26/FOAP/123/0198494/035',
};

const lines = ics => ics.split('\r\n');
const unfold = ics => ics.replace(/\r\n /g, '');
const prop = (ics, name) => unfold(ics).split('\r\n').find(l => l.startsWith(name));

test('estructura i finals de línia CRLF', () => {
  const ics = buildIcs(CURS, 'ca', NOW);
  assert.ok(ics.endsWith('END:VCALENDAR\r\n'));
  assert.ok(!/[^\r]\n/.test(ics), 'cap LF sense CR');
  assert.deepStrictEqual(lines(ics).slice(0, 2), ['BEGIN:VCALENDAR', 'VERSION:2.0']);
  for (const name of ['BEGIN:VEVENT', 'END:VEVENT', 'PRODID:', 'UID:', 'DTSTAMP:', 'DTSTART', 'SUMMARY:']) {
    assert.ok(prop(ics, name), 'falta ' + name);
  }
});

test('dia sencer el dia que comença, amb el canvi d\'any', () => {
  const ics = buildIcs(CURS, 'ca', NOW);
  assert.strictEqual(prop(ics, 'DTSTART'), 'DTSTART;VALUE=DATE:20261231');
  assert.strictEqual(prop(ics, 'DTEND'), 'DTEND;VALUE=DATE:20270101');
  assert.strictEqual(prop(ics, 'DTSTAMP'), 'DTSTAMP:20261115T093000Z');
});

test('UID estable i sense caràcters estranys', () => {
  assert.strictEqual(prop(buildIcs(CURS, 'ca', NOW), 'UID'), 'UID:26-FOAP-123-0198494-035@grausfp.es');
  assert.strictEqual(prop(buildIcs(CURS, 'es', new Date()), 'UID'), 'UID:26-FOAP-123-0198494-035@grausfp.es');
});

test('títol amb comes, punt i coma i accents: escapat', () => {
  assert.strictEqual(prop(buildIcs(CURS, 'ca', NOW), 'SUMMARY'),
    'SUMMARY:Gestió comptable\\, fiscal i laboral\; nivell 2');
  assert.strictEqual(prop(buildIcs(CURS, 'es', NOW), 'SUMMARY'),
    'SUMMARY:Gestión contable\\, fiscal y laboral\; nivel 2');
  const estrany = buildIcs({ ...CURS, titol: { ca: 'Barra \\ i salt\nde línia' } }, 'ca', NOW);
  assert.strictEqual(prop(estrany, 'SUMMARY'), 'SUMMARY:Barra \\\\ i salt\\nde línia');
});

test('cap línia passa de 75 octets i el plegat no parteix cap caràcter', () => {
  const llarg = { ...CURS, titol: { ca: 'Àrea d\'atenció sociosanitària a persones dependents en institucions socials — ç·l·l ñ '.repeat(3) } };
  const ics = buildIcs(llarg, 'ca', NOW);
  for (const line of lines(ics)) assert.ok(Buffer.byteLength(line, 'utf8') <= 75, line);
  assert.ok(lines(ics).some(l => l.startsWith(' ')), 'hi ha d\'haver línies plegades');
  assert.strictEqual(prop(ics, 'SUMMARY'), 'SUMMARY:' + llarg.titol.ca.replace(/,/g, '\\,'));
  assert.ok(!ics.includes('\uFFFD'));
  assert.ok(prop(ics, 'DESCRIPTION').includes(CURS.fitxaUrl));
});

test('lloc i descripció', () => {
  const ics = buildIcs(CURS, 'ca', NOW);
  assert.strictEqual(prop(ics, 'LOCATION'), "LOCATION:Centre d'Estudis Montsià\\, C. Major\\, 1\\, 43870\\, Amposta");
  assert.strictEqual(prop(ics, 'DESCRIPTION'),
    'DESCRIPTION:Hores: 120\\nModalitat: PRESENCIAL\\nAcaba: 15/03/2027\\nFitxa del curs: ' + CURS.fitxaUrl);
  assert.ok(prop(buildIcs(CURS, 'es', NOW), 'DESCRIPTION').startsWith('DESCRIPTION:Horas: 120\\nModalidad'));
});

test('curs sense centre ni dades opcionals', () => {
  const ics = buildIcs({ idCurs: 'PIMEC:excel:1', titol: { ca: 'Excel', es: 'Excel' }, dataInici: '2026-11-20' }, 'ca', NOW);
  assert.ok(!prop(ics, 'LOCATION'));
  assert.ok(!prop(ics, 'DESCRIPTION'));
  assert.strictEqual(prop(ics, 'UID'), 'UID:PIMEC-excel-1@grausfp.es');
});

test('curs del detall d\'una especialitat (centre com a objecte)', () => {
  const ics = buildIcs({ idCurs: '1', titol: { ca: 'Curs' }, dataInici: '2026-11-20',
    centre: { nom: 'Centre U', carrer: 'C. X, 2', cp: '08001', municipi: 'Barcelona' } }, 'ca', NOW);
  assert.strictEqual(prop(ics, 'LOCATION'), 'LOCATION:Centre U\\, C. X\\, 2\\, 08001\\, Barcelona');
});

test('sense data d\'inici no hi ha fitxer', () => {
  assert.strictEqual(buildIcs({ ...CURS, dataInici: null }, 'ca', NOW), '');
  assert.strictEqual(buildIcs({ ...CURS, dataInici: '20/11/2026' }, 'ca', NOW), '');
});

test('nom del fitxer', () => {
  assert.strictEqual(fileName(CURS, 'ca'), 'curs-gestio-comptable-fiscal-i-laboral-nivell-2.ics');
  assert.strictEqual(fileName({ titol: {} }, 'ca'), 'curs-fpo.ics');
});
