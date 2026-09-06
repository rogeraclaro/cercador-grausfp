"""
cd_lomloe.py — Derivació pura C LOMLOE → [cicles D] (Pla 058).

Un C LOMLOE és una llista de mòduls B (bc_lomloe.json). Cada cicle D llista
els seus mòduls a d_modulos.json ("Plan de formación"). Compartir mòduls de
la MATEIXA família = relació C→D. La relació no es persisteix: es refà sola
quan canvien bc_lomloe.json, d_modulos.json o les denominacions dels B.

El matching d'un mòdul D a un B: pel codi de 4 xifres si el mòdul en porta
(FAM_B_NNNN), altrament pel nom normalitzat de la denominació del B.
"""
import re
import unicodedata

_B_NUM_RE = re.compile(r'^[A-Z]{3}_B_(\d{4})$')
_GRADO_PAREN_RE = re.compile(r'\((grado superior|grado medio|gs|gm)\)')
_NON_ALNUM_RE = re.compile(r'[^a-z0-9]+')


def normalize_module_name(name: str) -> str:
    s = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode().lower()
    s = _GRADO_PAREN_RE.sub('', s)
    return _NON_ALNUM_RE.sub(' ', s).strip()


def build_c_lomloe_to_d(records, bc_lomloe, d_modulos) -> dict[str, list[dict]]:
    """{codigo_c: [{'id': id_d, 'shared': n, 'total': m}, ...]}.

    Ordenat per shared/total desc, després id asc. Sense llindar: s'inclou
    qualsevol D de la mateixa família amb shared > 0.
    """
    b_by_num: dict[str, set[str]] = {}
    b_by_name: dict[str, set[str]] = {}
    for r in records:
        if r.get('grado') != 'B' or r.get('plan_antiguo'):
            continue
        code = r.get('codigo') or ''
        m = _B_NUM_RE.match(code)
        if m:
            b_by_num.setdefault(m.group(1), set()).add(code)
        dn = normalize_module_name(r.get('denominacion') or '')
        if dn:
            b_by_name.setdefault(dn, set()).add(code)

    fam_c = {r['codigo']: r.get('familia') for r in records
             if r.get('grado') == 'C' and not r.get('plan_antiguo') and r.get('codigo')}

    d_fam = {str(r['id']): r.get('familia') for r in records if r.get('grado') == 'D'}

    d_bs: dict[str, set[str]] = {}
    for did in d_fam:
        entry = d_modulos.get(did)
        if not entry:
            continue
        bs: set[str] = set()
        for mod in entry.get('modulos', []):
            num = mod.get('num')
            if num:
                bs |= b_by_num.get(num, set())
            else:
                bs |= b_by_name.get(normalize_module_name(mod.get('name') or ''), set())
        d_bs[did] = bs

    result: dict[str, list[dict]] = {}
    for c_code, b_list in bc_lomloe.items():
        total = len(b_list)
        if total == 0:
            continue
        cfam = fam_c.get(c_code)
        b_set = set(b_list)
        entries = []
        for did, dfam in d_fam.items():
            if dfam != cfam:
                continue
            shared = len(b_set & d_bs.get(did, set()))
            if shared > 0:
                entries.append({'id': int(did), 'shared': shared, 'total': total})
        entries.sort(key=lambda e: (-e['shared'] / e['total'], e['id']))
        if entries:
            result[c_code] = entries
    return result
