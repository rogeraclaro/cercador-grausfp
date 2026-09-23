#!/usr/bin/env node
// Verification harness for quick task 260923-x1s (grade A-E copy per LO 3/2022).
// Usage (from anywhere): node verify-copy.cjs [grau|rest|all]
// Loads frontend/i18n.js in a sandbox (it is browser-only), resolves CA and ES
// values through window.t(), and checks them against EXPECTED. Also checks the
// static data-i18n fallbacks in the HTML pages and the mirrored docs markdown.
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const APP = path.resolve(__dirname, '../../../fp-cercador');
const read = (rel) => fs.readFileSync(path.join(APP, rel), 'utf8');

const EXPECTED = {
  grau: {
    'perque.grau.a.nom': { ca: 'Acreditació parcial de competència', es: 'Acreditación parcial de competencia' },
    'perque.grau.a.ex': { ca: 'Preparación de los equipos', es: 'Preparación de los equipos' },
    'perque.grau.b.nom': { ca: 'Certificat de competència', es: 'Certificado de competencia' },
    'perque.grau.b.ex': { ca: 'Técnicas administrativas básicas', es: 'Técnicas administrativas básicas' },
    'perque.grau.c.nom': { ca: 'Certificat professional', es: 'Certificado profesional' },
    'perque.grau.c.ex': { ca: 'Seguridad informática', es: 'Seguridad informática' },
    'perque.grau.d.nom': { ca: 'Cicles formatius de grau bàsic, mitjà i superior', es: 'Ciclos formativos de grado básico, medio y superior' },
    'perque.grau.d.ex': { ca: 'Técnico Superior en Desarrollo de Aplicaciones Web', es: 'Técnico Superior en Desarrollo de Aplicaciones Web' },
    'perque.grau.e.nom': { ca: "Cursos d'especialització", es: 'Cursos de especialización' },
    'perque.grau.e.ex': {
      ca: 'Curso de Especialización en Ciberseguridad en Entornos de las Tecnologías de la Información',
      es: 'Curso de Especialización en Ciberseguridad en Entornos de las Tecnologías de la Información',
    },
  },
  rest: {
    'perque.feat.itineraris.desc': {
      ca: "veus d'un cop d'ull el camí sencer: de l'acreditació parcial al certificat de competència, al certificat professional i al cicle formatiu. Saps d'on pots venir i on pots arribar. Cap altra eina et mostra això.",
      es: 'ves de un vistazo el camino completo: de la acreditación parcial al certificado de competencia, al certificado profesional y al ciclo formativo. Sabes de dónde puedes venir y adónde puedes llegar. Ninguna otra herramienta te muestra esto.',
    },
    'perque.faq.3.q': {
      ca: "Els cursos d'especialització (Grau E) també hi són?",
      es: '¿También están los cursos de especialización (Grado E)?',
    },
    'perque.faq.3.a': {
      ca: "Sí. El cercador inclou 36 cursos d'especialització, amb accés des de grau mitjà o des de grau superior segons el curs.",
      es: 'Sí. El buscador incluye 36 cursos de especialización, con acceso desde grado medio o desde grado superior según el curso.',
    },
    'fonts.r2.detall': {
      ca: "Cicles formatius (Grado D) — bàsic, mitjà i superior — i cursos d'especialització (Grado E), amb denominació, família i nivell.",
      es: 'Ciclos formativos (Grado D) — básico, medio y superior — y cursos de especialización (Grado E), con denominación, familia y nivel.',
    },
  },
};

const FORBIDDEN = /Microcredencial|microcredencial|Grau Bàsic a Grau Mitjà|Grado Básico a Grado Medio|Especialització \(Grado D\)|Especialización \(Grado D\)/;
const TOUCHED = ['frontend/i18n.js', 'frontend/per-que-grausfp.html', 'frontend/fonts.html', 'docs/per-que-grausfp.md'];

function loadT(lang) {
  const ctx = {
    localStorage: { getItem: () => lang, setItem: () => {} },
    document: {
      documentElement: {},
      querySelector: () => null,
      querySelectorAll: () => [],
      addEventListener: () => {},
    },
  };
  ctx.window = ctx;
  vm.createContext(ctx);
  vm.runInContext(read('frontend/i18n.js'), ctx, { filename: 'i18n.js' });
  return ctx.t;
}

const mode = process.argv[2] || 'all';
const groups = mode === 'all' ? ['grau', 'rest'] : [mode];
if (!groups.every((g) => EXPECTED[g])) {
  console.error(`Unknown mode "${mode}". Use grau | rest | all.`);
  process.exit(2);
}

const failures = [];
const fail = (msg) => failures.push(msg);
const t = { ca: loadT('ca'), es: loadT('es') };
const html = { perque: read('frontend/per-que-grausfp.html'), fonts: read('frontend/fonts.html') };
const md = read('docs/per-que-grausfp.md');
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

for (const group of groups) {
  for (const [key, want] of Object.entries(EXPECTED[group])) {
    for (const lang of ['ca', 'es']) {
      const got = t[lang](key);
      if (got !== want[lang]) fail(`i18n.js ${lang} ${key}\n    got:  ${got}\n    want: ${want[lang]}`);
    }
    const page = key.startsWith('fonts.') ? 'fonts' : 'perque';
    const re = new RegExp(`data-i18n="${escapeRe(key)}">([^<]*)<`, 'g');
    const hits = [...html[page].matchAll(re)].map((m) => m[1]);
    if (hits.length === 0) fail(`${page} html: no data-i18n="${key}" element found`);
    for (const h of hits) {
      if (h !== want.ca) fail(`${page} html fallback ${key}\n    got:  ${h}\n    want: ${want.ca}`);
    }
  }
}

const E = (k) => (EXPECTED.grau[k] || EXPECTED.rest[k]).ca;
if (groups.includes('grau')) {
  for (const l of ['a', 'b', 'c', 'd', 'e']) {
    const row = `| **${l.toUpperCase()}** | ${E(`perque.grau.${l}.nom`)} | ${E(`perque.grau.${l}.ex`)} |`;
    if (!md.includes(row)) fail(`docs md: missing table row\n    want: ${row}`);
  }
}
if (groups.includes('rest')) {
  const itin = `**Itineraris formatius** — ${E('perque.feat.itineraris.desc')}`;
  if (!md.includes(itin)) fail(`docs md: missing itinerary line\n    want: ${itin}`);
  const faq = `**${E('perque.faq.3.q')}**\n${E('perque.faq.3.a')}`;
  if (!md.includes(faq)) fail(`docs md: missing FAQ Grau E block\n    want: ${faq}`);
}
if (mode === 'all') {
  for (const rel of TOUCHED) {
    read(rel).split('\n').forEach((line, i) => {
      if (FORBIDDEN.test(line)) fail(`forbidden legacy copy in ${rel}:${i + 1}`);
    });
  }
}

if (failures.length) {
  console.error(`FAIL (${mode}): ${failures.length} problem(s)\n- ` + failures.join('\n- '));
  process.exit(1);
}
console.log(`OK (${mode}): all grade copy checks pass`);
