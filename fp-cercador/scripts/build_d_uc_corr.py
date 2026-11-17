#!/usr/bin/env python3
"""
build_d_uc_corr.py — Pla 091: genera backend/data/d_uc_corr.json, la correspondència
oficial entre unitats de competència (UC) i mòduls professionals de cada cicle D, i
l'informe plans/outputs/audit_d_uc_corr.md.

Per a cada cicle: fitxa de todofp → enllaços al BOE → XML obert de cada decret → taules
dels annexos V A) i V B). Els decrets que substitueixen annexos d'altres (RD 498–500/2024,
«actualización» del 2023) s'apliquen a tots els cicles, encara que la fitxa no els enllaci.

~195 fitxes i ~330 decrets a 1 petició/s ≈ 10 min sense memòria cau. Execució manual; no
forma part del refresc setmanal. Els graus E queden fora (només es compten a l'informe).

Ús: python3 scripts/build_d_uc_corr.py [--cache DIR] [--dry-run]
  --cache DIR  Desa les fitxes i els XML a DIR (fitxa/, boe/) i els reaprofita
  --dry-run    No escriu d_uc_corr.json (l'informe sí)
"""
import argparse
import collections
import json
import logging
import os
import re
import sys
import tempfile

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(_REPO_ROOT, 'backend'))

from scrapers import boe_corr_scraper as boe  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(_REPO_ROOT, 'backend', 'data')
OUT_PATH = os.path.join(DATA_DIR, 'd_uc_corr.json')
REPORT_PATH = os.path.join(_REPO_ROOT, 'plans', 'outputs', 'audit_d_uc_corr.md')
NIVELLS = {1: 'Grau bàsic', 2: 'Grau mitjà', 3: 'Grau superior'}
# Cobertura del lector de prova (pla 091): per sota d'això, alguna cosa s'ha trencat.
MIN_AMB_TAULA_A = {2: 59, 3: 83}


def _safe(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', text.lower())


class Sources:
    """Fitxes de todofp i decrets del BOE, amb memòria cau a disc."""

    def __init__(self, cache_dir: str):
        self.dir = cache_dir
        self.docs: dict[str, dict] = {}

    def links(self, record: dict) -> list[str]:
        page = boe.fetch(record['ficha_url'], os.path.join(self.dir, 'fitxa', _safe(record['ref']) + '.html'),
                         referer='https://www.todofp.es/')
        return boe.boe_links(page)

    def doc_id(self, link: str) -> str | None:
        """Identificador BOE d'un enllaç; les adreces ELI es resolen baixant la pàgina."""
        found = boe.boe_id(link)
        if not found and '/eli/' in link:
            found = boe.boe_id(boe.fetch(link, os.path.join(self.dir, 'boe', 'eli_' + _safe(link)[-60:] + '.html')))
        return found

    def doc(self, doc_id: str) -> dict:
        if doc_id not in self.docs:
            xml = boe.fetch(boe.BOE_XML_URL.format(doc_id), os.path.join(self.dir, 'boe', doc_id + '.xml'))
            self.docs[doc_id] = boe.parse_doc(xml)
        return self.docs[doc_id]


def collect(records: list[dict], sources: Sources) -> tuple[dict[str, list[dict]], dict[str, str]]:
    """({ref: decrets enllaçats}, {ref: error}) per als registres donats."""
    linked: dict[str, list[dict]] = {}
    errors: dict[str, str] = {}
    for i, record in enumerate(records, start=1):
        try:
            ids = [sources.doc_id(link) for link in sources.links(record)]
            docs = [sources.doc(doc_id) for doc_id in dict.fromkeys(filter(None, ids))]
            cited = boe.cited_decree(record['denominacion'], docs)
            if cited and not boe.find_base(record['denominacion'], docs)[0]:
                docs.append(sources.doc(cited))
            linked[record['ref']] = docs
        except Exception as exc:  # una fitxa caiguda no ha d'aturar la resta
            errors[record['ref']] = str(exc)
            logger.warning('%s: %s', record['ref'], exc)
        if i % 25 == 0:
            logger.info('%d/%d', i, len(records))
    return linked, errors


def build(records: list[dict], linked: dict[str, list[dict]], all_docs: list[dict]) -> tuple[dict, dict]:
    """(índex {ref: entrada}, {ref: motiu} dels cicles sense cap taula)."""
    index: dict[str, dict] = {}
    without: dict[str, str] = {}
    for record in records:
        if record['ref'] not in linked:
            continue
        entry = boe.resolve_title(record['denominacion'], linked[record['ref']], all_docs)
        if entry.get('convalida') or entry.get('acredita'):
            index[record['ref']] = entry
        else:
            without[record['ref']] = entry.get('motiu') or 'table found but no row could be read'
    return index, without


def _b_loe_ucs(records: list[dict]) -> set[str]:
    """UC que existeixen al catàleg com a mòdul B del pla antic (MF####_N ↔ UC####_N)."""
    return {'UC' + r['codigo'][2:] for r in records
            if r.get('grado') == 'B' and r.get('plan_antiguo') and (r.get('codigo') or '').startswith('MF')}


def report(records: list[dict], d_records: list[dict], linked: dict, e_linked: dict, index: dict,
           without: dict, errors: dict, docs: dict[str, dict], bc_loe: dict, ciclos_fp: dict) -> str:
    by_ref = {r['ref']: r for r in d_records}
    out = ['# Auditoria de `d_uc_corr.json` (pla 091)', '',
           'Generat per `scripts/build_d_uc_corr.py`. Font: XML obert del BOE dels decrets que',
           'enllaça la fitxa de cada cicle a todofp, més els decrets que en substitueixen annexos.', '',
           '## Cobertura', '', '| Tipus | Total | Amb taula A | Amb taula B | Taula vigent d\'un decret posterior |',
           '|---|---|---|---|---|']
    for nivel, label in NIVELLS.items():
        refs = [r['ref'] for r in d_records if r.get('nivel') == nivel]
        entries = [index[ref] for ref in refs if ref in index]
        out.append(f"| {label} | {len(refs)} | {sum(1 for e in entries if e['convalida'])} | "
                   f"{sum(1 for e in entries if e['acredita'])} | "
                   f"{sum(1 for e in entries if e['vigent'] != e['decret'])} |")

    vigents = collections.Counter(e['vigent'] for e in index.values() if e['vigent'] != e['decret'])
    out += ['', '## Decrets que substitueixen o afegeixen taules', '',
            '| Decret | Cicles | Títol |', '|---|---|---|']
    out += [f"| {doc_id} | {n} | {docs[doc_id]['titulo'][:150]} |" for doc_id, n in vigents.most_common()]
    anterior = sorted(ref for ref, e in index.items() if e.get('convalida_anterior'))
    out += ['', f'{len(anterior)} cicles conserven a `convalida_anterior` la taula A original que un decret '
            'posterior va substituir: els certificats LOE porten els codis d\'UC d\'aquella taula.']

    out += ['', f'## Cicles sense taula ({len(without)})', '', '| Cicle | Nivell | Motiu | Decrets enllaçats |',
            '|---|---|---|---|']
    for ref, motiu in sorted(without.items()):
        out.append(f"| {by_ref[ref]['denominacion']} (`{ref}`) | {by_ref[ref].get('nivel')} | {motiu} | "
                   f"{', '.join(d['id'] for d in linked.get(ref, []))} |")
    if errors:
        out += ['', f'## Errors de baixada ({len(errors)})', ''] + [f'- `{ref}`: {err}' for ref, err in sorted(errors.items())]

    unread = [(ref, u) for ref, e in sorted(index.items()) for u in e.get('unread', [])]
    out += ['', f'## Files que no s\'han pogut llegir ({len(unread)})', '']
    out += [f'- `{ref}`: {u[:220]}' for ref, u in unread] or ['Cap.']

    known = _b_loe_ucs(records)
    table_ucs = collections.defaultdict(set)
    for ref, e in index.items():
        for row in e['convalida'] + e.get('convalida_anterior', []):
            for uc in row['uc']:
                table_ucs[uc].add(ref)
    unknown = sorted(uc for uc in table_ucs if uc not in known)
    out += ['', '## UC de les taules A que no són cap mòdul B LOE del catàleg', '',
            f'{len(unknown)} de {len(table_ucs)} UC. La majoria són UC de qualificacions actualitzades '
            '(codis nous) que encara no tenen certificat al catàleg del pla antic.', '',
            ', '.join(unknown) or 'Cap.']

    in_force = {uc for e in index.values() for row in e['convalida'] for uc in row['uc']}
    older = {uc for e in index.values() for row in e.get('convalida_anterior', []) for uc in row['uc']}
    some = [c for c, ucs in bc_loe.items() if set(ucs) & in_force]
    out += ['', '## Certificats LOE (bc_loe.json)', '',
            f'- {len(bc_loe)} certificats amb UC.',
            f'- {len(some)} tenen alguna UC a una taula vigent; '
            f'{sum(1 for c in some if set(bc_loe[c]) <= in_force)} les hi tenen totes.',
            f'- {sum(1 for c, ucs in bc_loe.items() if set(ucs) & older and not set(ucs) & in_force)} '
            'només surten a una taula substituïda (`convalida_anterior`): '
            + ', '.join(sorted(c for c, ucs in bc_loe.items() if set(ucs) & older and not set(ucs) & in_force)) + '.']
    todofp = {c for c, cicles in ciclos_fp.items() if cicles}
    boe_any = {c for c, ucs in bc_loe.items() if set(ucs) & (in_force | older)}
    out += ['', '## Comparació amb `ciclos_fp.json` (relació certificat → cicle de todofp)', '',
            f'- Amb cicle a todofp i al BOE: {len(todofp & boe_any)}.',
            f'- Només al BOE ({len(boe_any - todofp)}): {", ".join(sorted(boe_any - todofp))}.',
            f'- Només a todofp ({len(todofp - boe_any)}): {", ".join(sorted(todofp - boe_any))}.']

    e_with = sum(1 for ds in e_linked.values() if any(b['rows'] and not b['target_rd'] for d in ds for b in d['blocks']))
    out += ['', '## Fora d\'abast', '',
            f'- Graus E: {len(e_linked)} cursos d\'especialització, {e_with} amb alguna taula al decret propi. '
            'No s\'inclouen a l\'índex.',
            '- Títols anteriors al sistema d\'UC (LOGSE): sense taula; són a la llista de cicles sense taula.', '']
    return '\n'.join(out)


def _load(name: str) -> dict:
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', metavar='DIR')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    with open(os.path.join(DATA_DIR, 'ofertes.json'), encoding='utf-8') as f:
        records = json.load(f)
    d_records = [r for r in records if r.get('grado') == 'D' and r.get('ref') and r.get('ficha_url')]
    e_records = [r for r in records if r.get('grado') == 'E' and r.get('ref') and r.get('ficha_url')]

    sources = Sources(args.cache or tempfile.mkdtemp(prefix='d_uc_corr_'))
    linked, errors = collect(d_records, sources)
    e_linked, _ = collect(e_records, sources)  # només per a l'informe; també porta decrets modificadors
    index, without = build(d_records, linked, list(sources.docs.values()))

    text = report(records, d_records, linked, e_linked, index, without, errors, sources.docs,
                  _load('bc_loe.json'), _load('ciclos_fp.json'))
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(text)
    logger.info('Informe: %s', REPORT_PATH)

    for nivel, minimum in MIN_AMB_TAULA_A.items():
        got = sum(1 for r in d_records if r.get('nivel') == nivel and index.get(r['ref'], {}).get('convalida'))
        if got < minimum:
            logger.error('%s: %d cicles amb taula A, menys que els %d esperats. No s\'escriu res.',
                         NIVELLS[nivel], got, minimum)
            return 1
    if args.dry_run:
        logger.info('--dry-run: %d cicles, %d sense taula; no s\'escriu %s', len(index), len(without), OUT_PATH)
        return 0
    for entry in index.values():
        entry.pop('unread')  # només per a l'informe
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    logger.info('Escrit %s: %d cicles (%d sense taula)', OUT_PATH, len(index), len(without))
    return 0


if __name__ == '__main__':
    sys.exit(main())
