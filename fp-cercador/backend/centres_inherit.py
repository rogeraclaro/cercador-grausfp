"""
centres_inherit.py — Herència de centres per a graus A i B LOE (pla antic).

Cap registre públic acredita centres per a A/B: un centre s'acredita pel
certificat C i, per definició, pot impartir els seus mòduls (B) i unitats
formatives (A). Aquí es deriva, en memòria i sense I/O:

  A LOE  UF####     → B LOE MF####_N        (itinerary.get_parent_b)
  B LOE  MF####_N   → UC####_N → [codigo C] (bc_loe_inverse)
  C LOE  codigo     → [centre_id]           (oferta_centres)

LOMLOE queda fora: falta la relació B→C (spike 043).
"""
import re

import itinerary

_PAT_B_LOE = re.compile(r'^MF(\d{4})_(\d+)$')
_PAT_A_LOE = re.compile(r'^UF\d{4}$')


def _centres_for_b(codigo_b: str, bc_loe_inverse: dict, oferta_centres: dict) -> list[str]:
    m = _PAT_B_LOE.match(codigo_b or '')
    if not m:
        return []
    uc_key = f'UC{m.group(1)}_{m.group(2)}'
    ids: set[str] = set()
    for codigo_c in bc_loe_inverse.get(uc_key, []):
        ids.update(oferta_centres.get(codigo_c, []))
    return sorted(ids)


def build_inherited(records: list[dict], ab_index: dict,
                    bc_loe_inverse: dict, oferta_centres: dict) -> dict[str, list[str]]:
    """
    Retorna {str(id_oferta): [centre_id, ...]} per a les ofertes A i B LOE
    que hereten centres d'algun certificat C LOE. Llistes ordenades i sense
    duplicats. Les ofertes sense cap centre heretat no apareixen.
    """
    inherited: dict[str, list[str]] = {}
    b_cache: dict[str, list[str]] = {}

    def _for_b(codigo_b: str) -> list[str]:
        if codigo_b not in b_cache:
            b_cache[codigo_b] = _centres_for_b(codigo_b, bc_loe_inverse, oferta_centres)
        return b_cache[codigo_b]

    for r in records:
        if not r.get('plan_antiguo'):
            continue
        grado = r.get('grado')
        codigo = r.get('codigo') or ''
        if grado == 'B' and _PAT_B_LOE.match(codigo):
            ids = _for_b(codigo)
        elif grado == 'A' and _PAT_A_LOE.match(codigo):
            parent_b = itinerary.get_parent_b(r, ab_index)
            ids = _for_b(parent_b['codigo']) if parent_b else []
        else:
            continue
        if ids:
            inherited[str(r['id'])] = ids
    return inherited
