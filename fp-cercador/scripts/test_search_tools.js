// Eines del cercador per nom (Pla 087). Executar: node --test scripts/test_search_tools.js
const test = require('node:test');
const assert = require('node:assert');
const { stateFromParams, paramsFromState, buildVocabulary, boundedDistance, suggest, normalize } =
  require('../frontend/search-tools.js');

const FAMILIES = ['Sanidad', 'Administración y Gestión', 'Fabricación Mecánica'];
const DEFAULTS = { search: '', filterGrado: '', filterFamilia: '', filterNivel: '', filterOld: 'all',
                   filterFavs: false, sortCol: '', sortDir: 0, currentPage: 1 };
const query = pairs => new URLSearchParams(pairs).toString();
const parse = text => stateFromParams(new URLSearchParams(text), FAMILIES);

test('els valors per defecte no s\'escriuen: una cerca buida deixa l\'adreça neta', () => {
  assert.deepStrictEqual(paramsFromState(DEFAULTS), []);
  assert.deepStrictEqual(paramsFromState({ ...DEFAULTS, search: '   ', sortCol: 'grado', sortDir: 0 }), []);
  assert.deepStrictEqual(parse(''), {});
});

test('anada i tornada de tots els camps', () => {
  const state = { search: 'gestión administrativa', filterGrado: 'D', filterFamilia: 'Administración y Gestión',
                  filterNivel: '2', filterOld: 'hide', filterFavs: true, sortCol: 'familia', sortDir: -1, currentPage: 3 };
  const text = query(paramsFromState(state));
  assert.strictEqual(text, 'q=gesti%C3%B3n+administrativa&grado=D&familia=Administraci%C3%B3n+y+Gesti%C3%B3n' +
    '&nivel=2&pla=hide&favs=1&ordre=familia&dir=desc&p=3');
  assert.deepStrictEqual(parse(text), state);
});

test('ordre ascendent no escriu dir, i es llegeix com a ascendent', () => {
  const pairs = paramsFromState({ ...DEFAULTS, sortCol: 'codigo', sortDir: 1 });
  assert.deepStrictEqual(pairs, [['ordre', 'codigo']]);
  assert.deepStrictEqual(parse(query(pairs)), { sortCol: 'codigo', sortDir: 1 });
});

test('els valors invàlids s\'ignoren en silenci', () => {
  assert.deepStrictEqual(parse('grado=F&nivel=4&familia=Inventada&pla=tot&favs=si&ordre=id&dir=desc&p=0'), {});
  assert.deepStrictEqual(parse('grado=d&nivel=2a&p=-3&p=1'), {});
  assert.deepStrictEqual(parse('grado=B&p=abc&q=%20%20'), { filterGrado: 'B' });
  assert.deepStrictEqual(parse('p=1'), {});
  assert.deepStrictEqual(parse('p=7'), { currentPage: 7 });
});

test('q es retalla a 200 caràcters, també en escriure', () => {
  assert.strictEqual(parse('q=' + 'x'.repeat(500)).search.length, 200);
  assert.strictEqual(paramsFromState({ ...DEFAULTS, search: 'y'.repeat(500) })[0][1].length, 200);
});

test('paràmetres d\'altres funcions no molesten', () => {
  assert.deepStrictEqual(parse('mode=fpo&esp=ADGG0408&ref=UF0350&compara=a,b&q=soldadura'), { search: 'soldadura' });
});

// --- «Volies dir…» ---------------------------------------------------------

const NAMES = ['Soldadura con electrodo revestido', 'Soldadura oxigás', 'Técnico en Soldadura y Calderería',
  'Cuidados auxiliares de enfermería', 'Enfermería veterinaria', 'Gestión administrativa', 'Gestión de residuos',
  'Solador alicatador', 'Peluquería', 'Operaciones de fontanería'].map(normalize);
const VOCAB = buildVocabulary(NAMES);
const has = q => NAMES.some(n => n.includes(q));

test('vocabulari: paraules de 4 lletres o més amb el nombre de registres', () => {
  assert.strictEqual(VOCAB.get('soldadura'), 3);
  assert.strictEqual(VOCAB.get('gestion'), 2);
  assert.strictEqual(VOCAB.get('enfermeria'), 2);
  assert.ok(!VOCAB.has('con') && !VOCAB.has('de'));
  assert.strictEqual(buildVocabulary(['soldadura soldadura']).get('soldadura'), 1);   // un registre, un cop
});

test('distància d\'edició amb tall', () => {
  assert.strictEqual(boundedDistance('soldadra', 'soldadura', 2), 1);
  assert.strictEqual(boundedDistance('soldadura', 'soldadura', 2), 0);
  assert.strictEqual(boundedDistance('gestio', 'gestion', 1), 1);
  assert.strictEqual(boundedDistance('abcd', 'wxyz', 2), 3);            // passa del llindar: max + 1
  assert.strictEqual(boundedDistance('curt', 'moltmesllarg', 2), 3);
});

test('soldadra → soldadura', () => {
  assert.deepStrictEqual(suggest('soldadra', VOCAB), ['soldadura']);
  assert.deepStrictEqual(suggest('Soldadrá', VOCAB, { test: has }), ['soldadura']);
});

test('ordenats per distància i després per freqüència; màxim tres', () => {
  // «gestiox»: gestion a 1; gestiona, gestor i cestion a 2 (per freqüència); bastion queda fora (3)
  const vocab = new Map([['gestiona', 99], ['gestion', 1], ['cestion', 4], ['gestor', 9], ['bastion', 70]]);
  assert.deepStrictEqual(suggest('gestiox', vocab), ['gestion', 'gestiona', 'gestor']);
  assert.deepStrictEqual(suggest('gestiox', vocab, { limit: 1 }), ['gestion']);
});

test('paraules de 4 o 5 lletres només admeten una errada', () => {
  const vocab = new Map([['solar', 5], ['soldar', 3]]);
  assert.deepStrictEqual(suggest('zolar', vocab), ['solar']);
  assert.deepStrictEqual(suggest('zxlar', vocab), []);
});

test('una paraula que ja surt (sencera o com a tros) no es corregeix', () => {
  assert.deepStrictEqual(suggest('soldadura', VOCAB), []);
  assert.deepStrictEqual(suggest('solda', VOCAB), []);
});

test('consulta de diverses paraules: es corregeix només la que no surt enlloc', () => {
  assert.deepStrictEqual(suggest('gestion administrtiva', VOCAB, { test: has }), ['gestion administrativa']);
  // el suggeriment ha de donar resultats: «gestion veterinaria» no és cap denominació
  assert.deepStrictEqual(suggest('gestion veterinria', VOCAB, { test: has }), []);
  // dues paraules mal escrites: no s'endevina
  assert.deepStrictEqual(suggest('gestoin administrtiva', VOCAB), []);
});

test('un terme en català que ja es tradueix no rep suggeriments', () => {
  const translate = token => ({ infermeria: 'enfermeria' }[token] || null);
  assert.deepStrictEqual(suggest('infermeria', VOCAB, { translate }), []);
  assert.deepStrictEqual(suggest('infermeria', VOCAB), ['enfermeria']);      // sense traducció, sí
});

test('res de semblant, paraules curtes i consulta buida: cap suggeriment', () => {
  assert.deepStrictEqual(suggest('xyzwvq', VOCAB), []);
  assert.deepStrictEqual(suggest('sol', VOCAB), []);
  assert.deepStrictEqual(suggest('', VOCAB), []);
});
