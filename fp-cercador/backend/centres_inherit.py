"""
centres_inherit.py — Herència de centres per a graus A i B (LOE i LOMLOE).

Cap registre públic acredita centres per a A/B: un centre s'acredita pel
certificat C i, per definició, pot impartir els seus mòduls (B) i unitats
formatives (A). Aquí es deriva, en memòria i sense I/O:

  LOE (pla antic)
    A  UF####      → [B MF####_N]          (itinerary.get_parents_b; unió dels pares)
    B  MF####_N    → UC####_N → [codigo C] (bc_loe_inverse)
    C  codigo      → [centre_id]           (oferta_centres[codigo])

  LOMLOE (pla nou)
    A  FAM_A_NNNN_PP → B FAM_B_NNNN        (itinerary.get_parent_b)
    B  FAM_B_NNNN    → [codigo C]          (bc_lomloe invertit)
    C  codigo        → ref → [centre_id]   (oferta_centres[ref], Pla 076)

oferta_centres.json i el resultat van per `ref`, la clau estable del Pla 076
(per als C, el ref és el codi).
"""
import re

import itinerary
from oferta_ref import ensure_refs

_PAT_B_LOE = re.compile(r'^MF(\d{4})_(\d+)$')
_PAT_A_LOE = re.compile(r'^UF\d{4}$')
_PAT_B_LOMLOE = re.compile(r'^[A-Z]{3}_B_\d{4}$')
_PAT_A_LOMLOE = re.compile(r'^[A-Z]{3}_A_\d{4}_\d+$')


def _centres_for_b_loe(codigo_b: str, bc_loe_inverse: dict, oferta_centres: dict) -> list[str]:
    m = _PAT_B_LOE.match(codigo_b or '')
    if not m:
        return []
    uc_key = f'UC{m.group(1)}_{m.group(2)}'
    ids: set[str] = set()
    for codigo_c in bc_loe_inverse.get(uc_key, []):
        ids.update(oferta_centres.get(codigo_c, []))
    return sorted(ids)


def _centres_for_b_lomloe(codigo_b: str, b_lomloe_inverse: dict,
                          c_lomloe_ref: dict, oferta_centres: dict) -> list[str]:
    ids: set[str] = set()
    for codigo_c in b_lomloe_inverse.get(codigo_b, []):
        key = c_lomloe_ref.get(codigo_c)
        if key:
            ids.update(oferta_centres.get(key, []))
    return sorted(ids)


def build_inherited(records: list[dict], ab_index: dict, bc_loe_inverse: dict,
                    oferta_centres: dict, bc_lomloe: dict | None = None) -> dict[str, list[str]]:
    """
    Retorna {ref: [centre_id, ...]} per a les ofertes A i B que
    hereten centres d'algun certificat C. Llistes ordenades i sense duplicats.
    Les ofertes sense cap centre heretat no apareixen.

    bc_lomloe: {codigo_c: [codigo_b, ...]} (bc_lomloe.json). Si és None o
    buit, la branca LOMLOE no aporta res.
    """
    ensure_refs(records)
    b_lomloe_inverse: dict[str, list[str]] = {}
    for codigo_c, b_codes in (bc_lomloe or {}).items():
        for codigo_b in b_codes:
            b_lomloe_inverse.setdefault(codigo_b, []).append(codigo_c)
    c_lomloe_ref = {r['codigo']: r['ref'] for r in records
                   if r.get('grado') == 'C' and not r.get('plan_antiguo') and r.get('codigo')}

    inherited: dict[str, list[str]] = {}
    b_cache: dict[str, list[str]] = {}

    def _for_b(codigo_b: str) -> list[str]:
        if codigo_b not in b_cache:
            if _PAT_B_LOE.match(codigo_b):
                b_cache[codigo_b] = _centres_for_b_loe(codigo_b, bc_loe_inverse, oferta_centres)
            elif _PAT_B_LOMLOE.match(codigo_b):
                b_cache[codigo_b] = _centres_for_b_lomloe(
                    codigo_b, b_lomloe_inverse, c_lomloe_ref, oferta_centres)
            else:
                b_cache[codigo_b] = []
        return b_cache[codigo_b]

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''
        if grado == 'B' and (_PAT_B_LOE.match(codigo) or _PAT_B_LOMLOE.match(codigo)):
            ids = _for_b(codigo)
        elif grado == 'A' and (_PAT_A_LOE.match(codigo) or _PAT_A_LOMLOE.match(codigo)):
            # Un A LOE pot tenir diversos B pares (Ampliació 068): unió dels seus centres
            ids = sorted({cid for b in itinerary.get_parents_b(r, ab_index)
                          for cid in _for_b(b['codigo'])})
        else:
            continue
        if ids:
            inherited[r['ref']] = ids
    return inherited
