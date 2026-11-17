"""
export_estructura.py — Pla 093: files del CSV relacional (certificat–MF–UF i cicle–mòdul–UC).
Funcions pures, sense Flask. El CSV porta `;` i BOM UTF-8 perquè l'Excel en català l'obri bé.
"""
import csv
import io

CERT_HEADER = ['Codi certificat', 'Nom certificat', 'Nivell', 'Família', 'Hores certificat',
               'Codi MF', 'Nom MF', 'Hores MF', 'UC', 'Codi UF', 'Nom UF', 'Hores UF', 'Transversal']
CYCLE_HEADER = ['Ref cicle', 'Nom cicle', 'Nivell', 'Família', 'Codi mòdul', 'Nom mòdul',
                'UC', 'Grup d\'UC que el convalida', 'Certificats LOE del grup', 'Decret']
MP_NAME = 'Mòdul de pràctiques professionals no laborals'
_FORMULA_START = ('=', '+', '-', '@')


class AsText(str):
    """Codi numèric que Excel ha de mantenir com a text (0237, no 237): s'escriu com a ="0237"."""


def _cell(value) -> str:
    """Text d'una cel·la; els que Excel llegiria com a fórmula es desen com a text."""
    text = '' if value is None else str(value)
    if isinstance(value, AsText):
        return f'="{text}"' if text else ''
    return "'" + text if text.startswith(_FORMULA_START) else text


def to_csv(header: list[str], rows: list[list]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=';', lineterminator='\r\n')
    writer.writerow(header)
    writer.writerows([_cell(v) for v in row] for row in rows)
    return '﻿' + out.getvalue()


def _head(cert: dict) -> list:
    return [cert.get('codigo'), cert.get('denominacion'), cert.get('nivel'), cert.get('familia')]


def cert_rows_loe(cert: dict, estructura: dict | None, ucs: list, b_by_num: dict,
                  uf_names: dict) -> list[list]:
    """
    Una fila per UF de cada MF del certificat LOE; un MF sense UF dona una sola fila amb la part
    d'UF buida. Sense estructura de l'annex es cau a les UC de bc_loe.json: un MF per UC, sense hores.
    b_by_num: {'0820': {codigo, denominacion}} dels mòduls B LOE; uf_names: {codi_uf: nom}.
    """
    head = _head(cert)
    if not estructura:
        mfs = [{'codigo': 'MF' + uc[2:], 'h': None, 'uc': uc, 'ufs': []} for uc in ucs]
        total, mp = cert.get('duracion_horas'), None
    else:
        mfs, mp = estructura['mf'], estructura.get('mp')
        total = estructura['total_h'] if estructura['total_h'] is not None else cert.get('duracion_horas')
    shared: dict[str, int] = {}
    for mf in mfs:
        for uf in mf['ufs']:
            shared[uf['codigo']] = shared.get(uf['codigo'], 0) + 1

    rows = []
    for mf in mfs:
        mf_name = (b_by_num.get(mf['codigo'][2:6]) or {}).get('denominacion')
        uc = mf.get('uc') or ('UC' + mf['codigo'][2:] if 'UC' + mf['codigo'][2:] in ucs else None)
        base = head + [total, mf['codigo'], mf_name, mf['h'], uc]
        if not mf['ufs']:
            rows.append(base + [None, None, None, None])
        for uf in mf['ufs']:
            rows.append(base + [uf['codigo'], uf_names.get(uf['codigo']), uf['h'],
                                'sí' if shared[uf['codigo']] > 1 else 'no'])
    if mp:
        rows.append(head + [total, mp['codigo'], MP_NAME, mp['h'], None, None, None, None, None])
    return rows


def cert_rows_lomloe(cert: dict, modules: list[dict], children_a) -> list[list]:
    """
    Files d'un certificat C LOMLOE: una per cada A (unitat) de cada mòdul B. `modules`: registres B
    del certificat; children_a(b) → registres A. Sense hores (el catàleg no en té). UC no n'hi ha.
    """
    head = _head(cert)
    kids = {b['codigo']: children_a(b) for b in modules}
    shared: dict[str, int] = {}
    for children in kids.values():
        for a in children:
            shared[a['codigo']] = shared.get(a['codigo'], 0) + 1
    rows = []
    for b in modules:
        base = head + [None, b['codigo'], b.get('denominacion'), None, None]
        if not kids[b['codigo']]:
            rows.append(base + [None, None, None, None])
        for a in kids[b['codigo']]:
            rows.append(base + [a['codigo'], a.get('denominacion'), None,
                                'sí' if shared[a['codigo']] > 1 else 'no'])
    return rows


def cycle_rows(cycle: dict, modules: list[dict], entry: dict, certs_with_all) -> list[list]:
    """
    Una fila per mòdul del cicle i per UC que el convalida (clau per creuar amb la columna UC del
    fitxer de certificats). «Grup d'UC» conserva la fila de la taula A (les UC d'un grup s'han
    de tenir totes: separades per « + ») i els certificats LOE que les porten totes.
    Un mòdul sense cap UC a les taules dona una sola fila amb aquestes columnes buides.
    certs_with_all(ucs) → [{codigo, …}].
    """
    head = [cycle.get('ref'), cycle.get('denominacion'), cycle.get('nivel'), cycle.get('familia')]
    decret = entry.get('vigent') or entry.get('decret')  # decret de la taula en vigor (convalida)
    rows = []
    for m in modules:
        groups = [r['uc'] for r in entry.get('convalida') or []
                  if m['num'] and any(x['num'] == m['num'] for x in r['moduls'])]
        base = head + [AsText(m['num'] or ''), m['name']]
        if not groups:
            rows.append(base + [None, None, None, decret])
        for ucs in groups:
            certs = ', '.join(c['codigo'] for c in certs_with_all(ucs))
            rows += [base + [uc, ' + '.join(ucs), certs, decret] for uc in ucs]
    return rows
