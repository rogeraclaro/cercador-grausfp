"""
cd_lomloe.py — Derivació pura C LOMLOE → [cicles D] (Pla 058).

Un C LOMLOE és una llista de mòduls B (bc_lomloe.json). Cada cicle D llista
els seus mòduls a d_modulos.json ("Plan de formación"). Compartir mòduls de
la MATEIXA família = relació C→D. La relació no es persisteix: es refà sola
quan canvien bc_lomloe.json, d_modulos.json o les denominacions dels B.

El matching d'un mòdul D a un B: pel codi de 4 xifres si el mòdul en porta
(FAM_B_NNNN), altrament pel nom normalitzat de la denominació del B.

Pla 078 (opció A): si hi ha c_modulos.json, el C es compta amb TOTS els mòduls de
la seva fitxa (també els sense Grau B) per número, excepte els de PRL sense Grau B.
"""
import re
import unicodedata

_B_NUM_RE = re.compile(r'^[A-Z]{3}_B_(\d{4})$')
_GRADO_PAREN_RE = re.compile(r'\((grado superior|grado medio|gs|gm)\)')
_NON_ALNUM_RE = re.compile(r'[^a-z0-9]+')
_PRL_NUMS = {'1782', '1724', '1732'}
_PRL_NAMES = ('riesgos laborales', 'riesgos profesionales')


def normalize_module_name(name: str) -> str:
    s = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode().lower()
    s = _GRADO_PAREN_RE.sub('', s)
    return _NON_ALNUM_RE.sub(' ', s).strip()


def _is_prl(mod: dict, b_nums) -> bool:
    """PRL només si no té Grau B: 0165 (calitat i PRL) té B i ha de comptar."""
    if mod.get('num') in b_nums:
        return False
    name = (mod.get('name') or '').lower()
    return mod.get('num') in _PRL_NUMS or any(p in name for p in _PRL_NAMES)


def build_c_lomloe_to_d(records, bc_lomloe, d_modulos, c_modulos=None) -> dict[str, list[dict]]:
    """{codigo_c: [{'id': id_d, 'shared': n, 'total': m}, ...]}.

    Ordenat per shared/total desc, després id asc. Sense llindar: s'inclou
    qualsevol D de la mateixa família amb shared > 0. Els C presents a c_modulos
    es compten per número de mòdul (Pla 078); la resta, per bc_lomloe com abans.
    """
    c_modulos = c_modulos or {}
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

    # Nom normalitzat → números de mòdul, per als mòduls D que no porten número.
    num_by_name: dict[str, set[str]] = {}
    for dn, codes in b_by_name.items():
        for code in codes:
            m = _B_NUM_RE.match(code)
            if m:
                num_by_name.setdefault(dn, set()).add(m.group(1))
    for mods in c_modulos.values():
        for mod in mods:
            dn = normalize_module_name(mod.get('name') or '')
            if dn and mod.get('num'):
                num_by_name.setdefault(dn, set()).add(mod['num'])

    d_bs: dict[str, set[str]] = {}
    d_nums: dict[str, set[str]] = {}
    for did in d_fam:
        entry = d_modulos.get(did)
        if not entry:
            continue
        bs: set[str] = set()
        nums: set[str] = set()
        for mod in entry.get('modulos', []):
            num = mod.get('num')
            if num:
                bs |= b_by_num.get(num, set())
                nums.add(num)
            else:
                dn = normalize_module_name(mod.get('name') or '')
                bs |= b_by_name.get(dn, set())
                nums |= num_by_name.get(dn, set())
        d_bs[did] = bs
        d_nums[did] = nums

    result: dict[str, list[dict]] = {}
    for c_code in sorted(set(bc_lomloe) | set(c_modulos)):
        if c_modulos.get(c_code):
            c_set = {m['num'] for m in c_modulos[c_code]
                     if m.get('num') and not _is_prl(m, b_by_num)}
            d_sets = d_nums
        else:
            c_set = set(bc_lomloe.get(c_code, []))
            d_sets = d_bs
        total = len(c_set)
        if total == 0:
            continue
        cfam = fam_c.get(c_code)
        entries = []
        for did, dfam in d_fam.items():
            if dfam != cfam:
                continue
            shared = len(c_set & d_sets.get(did, set()))
            if shared > 0:
                entries.append({'id': int(did), 'shared': shared, 'total': total})
        entries.sort(key=lambda e: (-e['shared'] / e['total'], e['id']))
        if entries:
            result[c_code] = entries
    return result
