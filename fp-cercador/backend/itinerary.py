"""
itinerary.py — Derivació local d'itineraris A→B a partir dels codis d'ofertes.json.

No fa cap crida de xarxa ni I/O. Rep `records` (la llista d'ofertes.json) i
retorna índexs o resultats puntuals.

Patrons de codi:
  LOMLOE: A = FAM_A_NNNN_PP  →  B = FAM_B_NNNN   (extreure fam+num)
  LOE:    A = UF####          →  B = MF####_N      (extreure num)
"""
import re
from typing import Optional

_PAT_A_LOMLOE = re.compile(r'^([A-Z]+)_A_(\d+)_\d+$')
_PAT_A_LOE    = re.compile(r'^UF(\d+)$')
_PAT_B_LOMLOE = re.compile(r'^([A-Z]+)_B_(\d+)$')
_PAT_B_LOE    = re.compile(r'^MF(\d+)_\d+$')
_PAT_B_LOE_FULL = re.compile(r'^MF(\d{4})_(\d+)$')


def build_ab_index(records: list[dict]) -> dict:
    """
    Construeix un índex per derivar A→B i B→[A] localment.

    Retorna:
      {
        'b_by_code':    {codigo_B: record_B},    # LOMLOE: FAM_B_NNNN
        'b_by_uf_num':  {uf_num_str: record_B},  # LOE: '0038' → MF0038_3
        'a_by_b_code':  {codigo_B: [record_A]},  # fills A per B (LOMLOE)
        'a_by_uf_num':  {uf_num_str: [record_A]},# fills A per B (LOE)
      }
    """
    b_by_code: dict   = {}
    b_by_uf_num: dict = {}
    a_by_b_code: dict = {}
    a_by_uf_num: dict = {}
    b_by_uc: dict = {}

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''

        if grado == 'B':
            m_lomloe = _PAT_B_LOMLOE.match(codigo)
            if m_lomloe:
                b_by_code[codigo] = r
            m_loe = _PAT_B_LOE.match(codigo)
            if m_loe:
                num = m_loe.group(1)
                b_by_uf_num[num] = r

            m_loe_full = _PAT_B_LOE_FULL.match(codigo)
            if m_loe_full:
                uc_key = f"UC{m_loe_full.group(1)}_{m_loe_full.group(2)}"
                b_by_uc[uc_key] = r  # ex: 'UC0969_1' → registre B MF0969_1

    for r in records:
        grado = r.get('grado')
        codigo = r.get('codigo') or ''

        if grado == 'A':
            m_lomloe = _PAT_A_LOMLOE.match(codigo)
            if m_lomloe:
                b_codigo = f"{m_lomloe.group(1)}_B_{m_lomloe.group(2)}"
                a_by_b_code.setdefault(b_codigo, []).append(r)

            m_loe = _PAT_A_LOE.match(codigo)
            if m_loe:
                num = m_loe.group(1)
                a_by_uf_num.setdefault(num, []).append(r)

    return {
        'b_by_code':   b_by_code,
        'b_by_uf_num': b_by_uf_num,
        'a_by_b_code': a_by_b_code,
        'a_by_uf_num': a_by_uf_num,
        'b_by_uc':     b_by_uc,   # NOU: 'UC0969_1' → registre B MF0969_1
    }


def get_parent_b(record: dict, index: dict) -> Optional[dict]:
    """Retorna el registre B pare d'un registre A, o None si no n'hi ha."""
    codigo = record.get('codigo') or ''

    m_lomloe = _PAT_A_LOMLOE.match(codigo)
    if m_lomloe:
        b_codigo = f"{m_lomloe.group(1)}_B_{m_lomloe.group(2)}"
        return index['b_by_code'].get(b_codigo)

    m_loe = _PAT_A_LOE.match(codigo)
    if m_loe:
        return index['b_by_uf_num'].get(m_loe.group(1))

    return None


def get_children_a(record: dict, index: dict) -> list[dict]:
    """Retorna la llista de registres A fills d'un registre B."""
    codigo = record.get('codigo') or ''

    m_lomloe = _PAT_B_LOMLOE.match(codigo)
    if m_lomloe:
        return index['a_by_b_code'].get(codigo, [])

    m_loe = _PAT_B_LOE.match(codigo)
    if m_loe:
        return index['a_by_uf_num'].get(m_loe.group(1), [])

    return []
