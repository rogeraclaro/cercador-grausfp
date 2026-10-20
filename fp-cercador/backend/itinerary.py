"""
itinerary.py — Derivació local d'itineraris A→B a partir dels codis d'ofertes.json.

No fa cap crida de xarxa ni I/O. Rep `records` (la llista d'ofertes.json) i
retorna índexs o resultats puntuals.

Patrons de codi:
  LOMLOE: A = FAM_A_NNNN_PP  →  B = FAM_B_NNNN   (extreure fam+num)
  LOE:    A = UF####          →  [B MF####_N]     (a_loe_pares.json, Ampliació 068)

Per als A LOE el número NO serveix (UF0038 → MF0706_1, no MF0038_3) i n'hi
pot haver més d'un pare: la relació ve de la fitxa oficial de cada A. Sense
aquest mapa, els A LOE no tenen pare (millor res que un pare fals).
"""
import re
from typing import Optional

_PAT_A_LOMLOE = re.compile(r'^([A-Z]+)_A_(\d+)_\d+$')
_PAT_A_LOE    = re.compile(r'^UF(\d+)$')
_PAT_B_LOMLOE = re.compile(r'^([A-Z]+)_B_(\d+)$')
_PAT_B_LOE    = re.compile(r'^MF(\d+)_\d+$')
_PAT_B_LOE_FULL = re.compile(r'^MF(\d{4})_(\d+)$')


def build_ab_index(records: list[dict], a_loe_pares: dict | None = None) -> dict:
    """
    Construeix un índex per derivar A→B i B→[A] localment.

    a_loe_pares: {codigo_UF: [codigo_MF, ...]} (a_loe_pares.json). Els MF que
    no són a records s'ignoren.

    Retorna:
      {
        'b_by_code':      {codigo_B: record_B},     # LOMLOE: FAM_B_NNNN
        'a_by_b_code':    {codigo_B: [record_A]},   # fills A per B (LOMLOE)
        'b_parents_by_a': {codigo_UF: [record_B]},  # pares B per A (LOE)
        'a_by_b_loe':     {codigo_MF: [record_A]},  # fills A per B (LOE)
      }
    """
    b_by_code: dict   = {}
    b_loe_by_code: dict = {}
    a_by_b_code: dict = {}
    b_parents_by_a: dict = {}
    a_by_b_loe: dict = {}
    b_by_uc: dict = {}
    c_loe_by_code: dict = {}   # NOU: {codigo_c: record_C} per a C LOE (plan_antiguo=True)
    c_lomloe_by_code: dict = {}  # Pla 057: {codigo_c: record_C} per a C LOMLOE (plan_antiguo=False)

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''

        if grado == 'B':
            m_lomloe = _PAT_B_LOMLOE.match(codigo)
            if m_lomloe:
                b_by_code[codigo] = r
            if _PAT_B_LOE.match(codigo):
                b_loe_by_code[codigo] = r

            m_loe_full = _PAT_B_LOE_FULL.match(codigo)
            if m_loe_full:
                uc_key = f"UC{m_loe_full.group(1)}_{m_loe_full.group(2)}"
                b_by_uc[uc_key] = r  # ex: 'UC0969_1' → registre B MF0969_1

        if grado == 'C' and codigo:
            if r.get('plan_antiguo'):
                c_loe_by_code[codigo] = r
            else:
                c_lomloe_by_code[codigo] = r

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''

        if grado == 'A':
            m_lomloe = _PAT_A_LOMLOE.match(codigo)
            if m_lomloe:
                b_codigo = f"{m_lomloe.group(1)}_B_{m_lomloe.group(2)}"
                a_by_b_code.setdefault(b_codigo, []).append(r)

            if _PAT_A_LOE.match(codigo):
                parents = [b_loe_by_code[mf] for mf in (a_loe_pares or {}).get(codigo, [])
                           if mf in b_loe_by_code]
                if parents:
                    b_parents_by_a[codigo] = parents
                for b in parents:
                    a_by_b_loe.setdefault(b['codigo'], []).append(r)

    return {
        'b_by_code':      b_by_code,
        'a_by_b_code':    a_by_b_code,
        'b_parents_by_a': b_parents_by_a,
        'a_by_b_loe':     a_by_b_loe,
        'b_by_uc':        b_by_uc,        # 'UC0969_1' → registre B MF0969_1
        'c_loe_by_code':  c_loe_by_code,  # NOU: {codigo_c: record_C} per a C LOE
        'c_lomloe_by_code': c_lomloe_by_code,  # Pla 057: {codigo_c: record_C} per a C LOMLOE
    }


def get_parents_b(record: dict, index: dict) -> list[dict]:
    """Retorna els registres B pares d'un registre A (LOMLOE: 0 o 1; LOE: 0..n)."""
    codigo = record.get('codigo') or ''

    m_lomloe = _PAT_A_LOMLOE.match(codigo)
    if m_lomloe:
        parent = index['b_by_code'].get(f"{m_lomloe.group(1)}_B_{m_lomloe.group(2)}")
        return [parent] if parent else []

    if _PAT_A_LOE.match(codigo):
        return index['b_parents_by_a'].get(codigo, [])

    return []


def get_parent_b(record: dict, index: dict) -> Optional[dict]:
    """Retorna el primer registre B pare d'un registre A, o None si no n'hi ha."""
    parents = get_parents_b(record, index)
    return parents[0] if parents else None


def get_children_a(record: dict, index: dict) -> list[dict]:
    """Retorna la llista de registres A fills d'un registre B."""
    codigo = record.get('codigo') or ''

    m_lomloe = _PAT_B_LOMLOE.match(codigo)
    if m_lomloe:
        return index['a_by_b_code'].get(codigo, [])

    if _PAT_B_LOE.match(codigo):
        return index['a_by_b_loe'].get(codigo, [])

    return []
