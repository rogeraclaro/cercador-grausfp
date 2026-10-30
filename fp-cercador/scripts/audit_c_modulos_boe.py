#!/usr/bin/env python3
"""
audit_c_modulos_boe.py — Pla 078, fase 2b: contrasta els mòduls de cada C LOMLOE
(backend/data/c_modulos.json, de les fitxes todofp) i els seus Graus B del catàleg
(bc_lomloe.json) amb el decret del BOE que els regula.

Per a cada C del decret:
  - annex I, apartat "7. Módulos profesionales": tots els mòduls del certificat;
  - annex II, bloc "x) FAM_C_…": els mòduls oferts com a Grau B (FAM_B_NNNN).

Escriu plans/outputs/audit_c_modulos_boe.md. Execució única, ~1 min (8 decrets).
Ús: python3 scripts/audit_c_modulos_boe.py [--cache DIR]
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import unicodedata

import requests

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))
DATA_DIR = os.path.join(_REPO_ROOT, 'backend', 'data')
OUT_PATH = os.path.join(_REPO_ROOT, 'plans', 'outputs', 'audit_c_modulos_boe.md')

# RD 207–213/2025 (decrets de famílies del 18-3-2025) i RD 86/2026 (Habilitació docència).
DECRETS = {
    'RD 207/2025': 'BOE-A-2025-6797',
    'RD 208/2025': 'BOE-A-2025-7040',
    'RD 209/2025': 'BOE-A-2025-6699',
    'RD 210/2025': 'BOE-A-2025-7588',
    'RD 211/2025': 'BOE-A-2025-7096',
    'RD 212/2025': 'BOE-A-2025-7193',
    'RD 213/2025': 'BOE-A-2025-7295',
    'RD 86/2026': 'BOE-A-2026-3210',
}
_C_RE = r'[A-Z]{3}_C_\d{3}_\d[A-Z]'


def fetch_text(boe_id: str, cache_dir: str | None) -> str:
    path = os.path.join(cache_dir, f'{boe_id}.txt') if cache_dir else None
    if path and os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    resp = requests.get(f'https://www.boe.es/diario_boe/txt.php?id={boe_id}', timeout=120)
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    # El BOE separa "i)" i el codi amb em-space (U+2003): \s+ ho normalitza.
    text = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', resp.text)))
    if path:
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    time.sleep(1)
    return text


# --- Pla 080: descoberta dels RD individuals (un certificat per RD i RD de títol amb Graus C) ---

DISCOVER_FROM = datetime.date(2023, 7, 19)  # RD 659/2023: primers Graus C LOMLOE possibles
DISCOVER_PATH = os.path.join(_REPO_ROOT, 'plans', 'outputs', 'boe_certificados_individuales.json')
_TITOL_RD_RE = re.compile(r'Real Decreto (\d+/\d{4})')
# Certificats individuals i RD de títol que fixen Graus C ("ofertas de grados C, B y A").
_SUMARIO_RE = re.compile(r'certificados? profesional|grados C', re.I)
_TITOL_VERB_RE = re.compile(r'por el que se (establece el Certificado profesional|establece el título|modifica)')
_TITOL_MODIFICA_RE = re.compile(r'se modifica el Real Decreto (\d+/\d{4})')
_TITOL_DENOM_RE = re.compile(r'Certificado profesional en (.+?), de la familia', re.I)


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', s).split())


def parse_titol(titol: str) -> dict | None:
    """{rd, tipus: establece|titol|modifica|correccion, denominacion, modifica_rd} o None."""
    if not _SUMARIO_RE.search(titol):
        return None
    m = _TITOL_RD_RE.search(titol)
    # El primer "por el que se …" decideix el tipus: un RD pot establir un certificat i, de
    # passada, modificar-ne un altre (RD 488/2026 modifica el RD 300/2026).
    verb = _TITOL_VERB_RE.search(titol)
    if titol.startswith('Corrección de errores'):
        tipus = 'correccion'
    elif not verb:
        return None
    elif verb.group(1) == 'modifica':
        tipus = 'modifica'
    elif verb.group(1) == 'establece el título':
        if 'grados C' not in titol:
            return None
        tipus = 'titol'  # RD de títol (Grau D) que també fixa Graus C
    else:
        tipus = 'establece'
    d = _TITOL_DENOM_RE.search(titol)
    return {'rd': f'RD {m.group(1)}' if m else None, 'tipus': tipus,
            'denominacion': d.group(1).strip() if d and tipus == 'establece' else None,
            'modifica_rd': [f'RD {n}' for n in _TITOL_MODIFICA_RE.findall(titol)]}


def fetch_sumario(day: datetime.date, cache_dir: str | None) -> list[dict]:
    """Títols de certificats professionals del sumari del BOE d'un dia ([] si no n'hi ha BOE)."""
    key = day.strftime('%Y%m%d')
    path = os.path.join(cache_dir, f'sumario2-{key}.json') if cache_dir else None
    if path and os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    resp = requests.get(f'https://www.boe.es/datosabiertos/api/boe/sumario/{key}',
                        headers={'Accept': 'application/json'}, timeout=60)
    items = []
    if resp.status_code != 404:  # 404 = dia sense BOE (diumenges)
        resp.raise_for_status()

        def walk(o):
            if isinstance(o, dict):
                if _SUMARIO_RE.search(o.get('titulo') or ''):
                    items.append({'id': o.get('identificador'), 'titulo': o['titulo'], 'data': key})
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(resp.json())
    if path:
        os.makedirs(cache_dir, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False)
    time.sleep(1)
    return items


def discover(cache_dir: str | None, until: datetime.date) -> dict:
    """{boe_id: {rd, tipus, denominacion, data, titulo}} de tots els sumaris des de DISCOVER_FROM."""
    found = {}
    day = DISCOVER_FROM
    while day <= until:
        for it in fetch_sumario(day, cache_dir):
            parsed = parse_titol(it['titulo'])
            if parsed:
                found[it['id']] = {**parsed, 'data': it['data'], 'titulo': it['titulo']}
        day += datetime.timedelta(days=1)
    return found


def confirmacio(codigo: str, nums: list[str], text: str) -> str | None:
    """'codi' si el text del RD conté el codi del C; 'moduls' si conté tots els seus mòduls
    ("NNNN.") — el BOE publica de vegades el codi amb marcadors (EOC_C_00X_4B); None si no."""
    if codigo in text:
        return 'codi'
    if nums and all(f'{n}.' in text for n in nums):
        return 'moduls'
    return None


def aparellar(c_denoms: dict, troballes: dict) -> tuple[dict, list]:
    """({codigo_c: boe_id}, [codigo_c sense RD]) per denominació normalitzada (només 'establece')."""
    by_denom = {}
    for boe_id, t in sorted(troballes.items()):
        if t['tipus'] == 'establece' and t.get('denominacion'):
            by_denom.setdefault(norm(t['denominacion']), boe_id)
    matched, unmatched = {}, []
    for codigo, denom in sorted(c_denoms.items()):
        boe_id = by_denom.get(norm(denom))
        if boe_id:
            matched[codigo] = boe_id
        else:
            unmatched.append(codigo)
    return matched, unmatched


def parse_modulos_annex_i(text: str, codigo: str) -> list[str] | None:
    """Números de mòdul de l'apartat 7 del certificat a l'annex I."""
    m = re.search(rf'Código: {codigo}\.', text)
    if not m:
        return None
    end = re.search(r'CERTIFICADO PROFESIONAL:|ANEXO', text[m.end():])
    block = text[m.end(): m.end() + end.start()] if end else text[m.end():]
    i = block.find('7. Módulos profesionales')
    if i < 0:
        return None
    # "3051.Operaciones": el BOE de vegades no posa espai després del punt.
    return list(dict.fromkeys(re.findall(r'\b(\d{4})\. ?(?=[A-ZÁÉÍÓÚÑ])', block[i:])))


def parse_oferta_b_annex_ii(text: str, codigo: str) -> list[str] | None:
    """Números dels FAM_B_NNNN que l'annex II ofereix per al certificat."""
    m = re.search(rf'\b[a-zñ]{{1,3}}\) {codigo}[.:] ', text)
    if not m:
        return None
    end = re.search(rf'\b[a-zñ]{{1,3}}\) [A-Z]{{3}}_[BC]_\w+[.:] |CERTIFICADOS DE COMPETENCIA|ANEXO III', text[m.end():])
    block = text[m.end(): m.end() + end.start()] if end else text[m.end():]
    return sorted(set(re.findall(r'\b[A-Z]{3}_B_(\d{4})\b', block)))


def audit(c_modulos: dict, bc_lomloe: dict, texts: dict) -> dict:
    rows = {}
    for codigo in sorted(c_modulos):
        decret = next((rd for rd, t in texts.items() if f'Código: {codigo}.' in t), None)
        ficha = [m['num'] for m in c_modulos[codigo]]
        cat_b = sorted({b.rsplit('_', 1)[1] for b in bc_lomloe.get(codigo, [])})
        row = {'decret': decret, 'ficha': ficha, 'cataleg_b': cat_b}
        if decret:
            row['boe_moduls'] = parse_modulos_annex_i(texts[decret], codigo)
            row['boe_b'] = parse_oferta_b_annex_ii(texts[decret], codigo)
        rows[codigo] = row
    return rows


def classify(row: dict) -> str:
    if not row['decret']:
        return 'sense_decret'
    if row.get('boe_b') is None or row.get('boe_moduls') is None:
        return 'no_parsejat'
    boe_b, cat_b = set(row['boe_b']), set(row['cataleg_b'])
    if boe_b - cat_b:
        return 'forat_cataleg'
    if cat_b - boe_b:
        return 'cataleg_de_mes'
    return 'ok'


def audit_modulos(c_modulos: dict, bc_lomloe: dict, texts: dict, cataleg_b: set) -> dict:
    """
    Per a cada mòdul de fitxa sense Grau B al catàleg (el que la UI mostrarà sense
    enllaç), mira si algun decret l'ofereix com a Grau B (FAM_B_NNNN, qualsevol annex).
      - 'cap_decret': cap decret l'ofereix com a B → nota de l'art. 58.3;
      - 'forat_cataleg': el decret ofereix FAM_B_NNNN de la mateixa família i el catàleg no;
      - 'altra_familia': només existeix com a B d'una altra família;
      - 'sense_decret': cap decret l'ofereix, però el decret del C no s'ha localitzat.
    """
    boe_b = {code for t in texts.values() for code in re.findall(r'\b[A-Z]{3}_B_\d{4}\b', t)}
    result = {'cap_decret': [], 'forat_cataleg': [], 'altra_familia': [], 'sense_decret': []}
    for codigo, mods in sorted(c_modulos.items()):
        fam = codigo[:3]
        has_decret = any(f'Código: {codigo}.' in t for t in texts.values())
        linked = {b.rsplit('_', 1)[1] for b in bc_lomloe.get(codigo, [])}
        for m in mods:
            if m['num'] in linked:
                continue
            same = f"{fam}_B_{m['num']}"
            others = sorted(b for b in (boe_b | cataleg_b) if b.endswith('_B_' + m['num']) and b != same)
            if same in boe_b:
                key = 'forat_cataleg'
            elif others:
                key = 'altra_familia'
            else:
                key = 'cap_decret' if has_decret else 'sense_decret'
            result[key].append((codigo, m['num'], m['name'], others))
    return result


def render_modulos(mods: dict) -> list[str]:
    total = sum(len(v) for v in mods.values())
    lines = [
        '## Mòduls sense Grau B al catàleg (els que la UI mostrarà sense enllaç)', '',
        '| Resultat | Mòduls | Nota a la UI |', '|---|---|---|',
        f"| Cap decret l'ofereix com a Grau B | {len(mods['cap_decret'])} | art. 58.3 RD 659/2023 |",
        f"| El decret l'ofereix com a Grau B i el catàleg no el té | {len(mods['forat_cataleg'])} | neutra |",
        f"| Només existeix com a Grau B d'una altra família | {len(mods['altra_familia'])} | a decidir |",
        f"| Cap decret l'ofereix, però el decret del C no s'ha localitzat | {len(mods['sense_decret'])} | a decidir |",
        f'| **Total** | **{total}** | |', '',
    ]
    for key, title in (('forat_cataleg', 'Forats del catàleg (per mòdul)'),
                       ('altra_familia', "Grau B d'una altra família"),
                       ('sense_decret', 'Mòduls de C sense decret localitzat')):
        if mods[key]:
            lines += [f'### {title}', '', '| C | Mòdul | Nom | B existents |', '|---|---|---|---|']
            lines += [f"| {c} | {n} | {name} | {', '.join(o)} |" for c, n, name, o in mods[key]]
            lines.append('')
    nums = sorted({(n, name) for _, n, name, _ in mods['cap_decret']})
    lines += ["### Mòduls que cap decret ofereix com a Grau B", '',
              ', '.join(f'{n} {name}' for n, name in nums), '']
    return lines


def render(rows: dict) -> str:
    cats = {}
    for codigo, row in rows.items():
        cats.setdefault(classify(row), []).append(codigo)
    no_b_total = sum(len(set(r['ficha']) - set(r['cataleg_b'])) for r in rows.values())
    ficha_vs_boe = [c for c, r in rows.items()
                    if r.get('boe_moduls') is not None and sorted(r['ficha']) != sorted(r['boe_moduls'])]
    lines = [
        '# Auditoria pla 078 — mòduls dels C LOMLOE contra el BOE',
        '',
        'Generat per `scripts/audit_c_modulos_boe.py` a partir de `c_modulos.json`/`bc_lomloe.json`',
        'de producció i dels decrets: ' + ', '.join(f'{rd} ([{b}](https://www.boe.es/buscar/act.php?id={b}))'
                                             for rd, b in DECRETS.items()) + '.',
        '',
        '- **OK**: els Graus B del catàleg són exactament l\'oferta de Grau B del decret (annex II).',
        '- **Forat del catàleg**: el decret ofereix un Grau B que el catàleg no té.',
        '- **Catàleg de més**: el catàleg té un Grau B que el decret no ofereix.',
        '- SSC_C_017_5B (RD 86/2026) té una altra estructura i surt com a no parsejat: es va',
        '  verificar a mà (annex I: només 1705, 1706, 1707, 1783, 1784, 1785 com a Grau B).',
        '',
        '| Resultat | Certificats |',
        '|---|---|',
    ]
    for key, label in (('ok', 'OK'), ('forat_cataleg', 'Forat del catàleg'),
                       ('cataleg_de_mes', 'Catàleg de més'), ('no_parsejat', 'Decret trobat, no parsejat'),
                       ('sense_decret', 'Sense decret localitzat')):
        lines.append(f'| {label} | {len(cats.get(key, []))} |')
    lines += ['', f'Total: {len(rows)} certificats; {no_b_total} mòduls de fitxa sense Grau B al catàleg.', '']

    for key, title in (('forat_cataleg', 'Forats del catàleg'), ('cataleg_de_mes', 'Catàleg de més'),
                       ('no_parsejat', 'Decret trobat però no parsejat')):
        if cats.get(key):
            lines += [f'## {title}', '', '| C | Decret | B al BOE | B al catàleg |', '|---|---|---|---|']
            for c in cats[key]:
                r = rows[c]
                lines.append(f"| {c} | {r['decret']} | {', '.join(r.get('boe_b') or [])} | {', '.join(r['cataleg_b'])} |")
            lines.append('')

    lines += ['## Fitxa todofp diferent de l\'annex I del decret', '']
    if ficha_vs_boe:
        lines += ['| C | Fitxa | BOE annex I |', '|---|---|---|']
        for c in ficha_vs_boe:
            lines.append(f"| {c} | {', '.join(rows[c]['ficha'])} | {', '.join(rows[c]['boe_moduls'])} |")
    else:
        lines.append('Cap: tots els mòduls de les fitxes coincideixen amb el decret.')
    lines.append('')

    if cats.get('sense_decret'):
        lines += ['## Sense decret localitzat (revisar a mà)', '',
                  ', '.join(cats['sense_decret']), '']
    return '\n'.join(lines)


def main_discover(cache_dir: str | None) -> int:
    """Pla 080, fase 1: aparella cada C LOMLOE amb el seu RD individual i ho confirma amb el
    "Código:" del text. Escriu DISCOVER_PATH. ~1.200 sumaris a 1 req/s (~20 min) la primera vegada."""
    with open(os.path.join(DATA_DIR, 'c_modulos.json'), encoding='utf-8') as f:
        c_modulos = json.load(f)
    with open(os.path.join(DATA_DIR, 'ofertes.json'), encoding='utf-8') as f:
        c_denoms = {r['codigo']: r['denominacion'] for r in json.load(f)
                    if r.get('grado') == 'C' and r.get('codigo') in c_modulos}
    group_texts = [fetch_text(boe_id, cache_dir) for boe_id in DECRETS.values()]
    sense_decret = sorted(c for c in c_denoms if not any(f'Código: {c}' in t for t in group_texts))
    # PRL (1724/1732/1782) és comú a molts RD: no serveix per confirmar.
    nums = {c: [m['num'] for m in c_modulos[c] if m['num'] not in ('1724', '1732', '1782')]
            for c in sense_decret}

    troballes = discover(cache_dir, datetime.date.today())
    matched, unmatched = aparellar({c: c_denoms[c] for c in sense_decret}, troballes)
    aparellats = {}
    for codigo, boe_id in matched.items():
        aparellats[codigo] = {'boe_id': boe_id, 'rd': troballes[boe_id]['rd'],
                              'confirmat': confirmacio(codigo, nums[codigo], fetch_text(boe_id, cache_dir))}
    # Els que no aparellen pel nom: buscar el codi dins dels RD de títol (Grau D).
    titols = sorted(b for b, t in troballes.items() if t['tipus'] == 'titol')
    for codigo in list(unmatched):
        for boe_id in titols:
            if codigo in fetch_text(boe_id, cache_dir):
                aparellats[codigo] = {'boe_id': boe_id, 'rd': troballes[boe_id]['rd'], 'confirmat': 'codi'}
                unmatched.remove(codigo)
                break
    rds = {t['rd'] for b, t in troballes.items() if b in {v['boe_id'] for v in aparellats.values()}}
    canvis = {b: t for b, t in troballes.items()
              if (t['tipus'] == 'correccion' and t['rd'] in rds) or set(t['modifica_rd']) & rds}
    out = {'aparellats': aparellats, 'sense_rd': unmatched, 'modificacions_i_correccions': canvis,
           'troballes': troballes}
    os.makedirs(os.path.dirname(DISCOVER_PATH), exist_ok=True)
    with open(DISCOVER_PATH, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'{len(sense_decret)} C sense decret de grup; {len(troballes)} disposicions de certificats trobades')
    for codigo, v in aparellats.items():
        print(f"  {codigo} → {v['rd']} ({v['boe_id']})  [{v['confirmat'] or '⚠ NO confirmat'}]")
    for codigo in unmatched:
        print(f'  {codigo} → SENSE RD ({c_denoms[codigo]})')
    for b, t in canvis.items():
        print(f"  canvi: {t['tipus']} {b} {t['titulo'][:100]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', metavar='DIR', help='Directori on desar/llegir els textos del BOE')
    parser.add_argument('--data', metavar='DIR', help='Directori de dades (per defecte backend/data)')
    parser.add_argument('--discover', action='store_true',
                        help='Pla 080: busca als sumaris del BOE els RD individuals de cada C')
    args = parser.parse_args()
    global DATA_DIR
    DATA_DIR = args.data or DATA_DIR
    if args.discover:
        return main_discover(args.cache)
    with open(os.path.join(DATA_DIR, 'c_modulos.json'), encoding='utf-8') as f:
        c_modulos = json.load(f)
    with open(os.path.join(DATA_DIR, 'bc_lomloe.json'), encoding='utf-8') as f:
        bc_lomloe = json.load(f)
    with open(os.path.join(DATA_DIR, 'ofertes.json'), encoding='utf-8') as f:
        cataleg_b = {r['codigo'] for r in json.load(f)
                     if r.get('grado') == 'B' and re.match(r'^[A-Z]{3}_B_\d{4}$', r.get('codigo') or '')}
    texts = {rd: fetch_text(boe_id, args.cache) for rd, boe_id in DECRETS.items()}
    rows = audit(c_modulos, bc_lomloe, texts)
    mods = audit_modulos(c_modulos, bc_lomloe, texts, cataleg_b)
    head, _, tail = render(rows).partition('\n## ')
    report = head + '\n' + '\n'.join(render_modulos(mods)) + '\n## ' + tail
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)
    print(head)
    print('\n'.join(render_modulos(mods)[:9]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
