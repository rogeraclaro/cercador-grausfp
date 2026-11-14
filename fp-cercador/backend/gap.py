"""
gap.py — «Què em falta?» (Pla 083): dels graus B, C i D que algú ja té, quins
C LOMLOE i cicles D té més a prop i què li falta. Funció pura, sense Flask.

Les peces són mòduls: un B LOMLOE és el mòdul del seu sufix (ADG_B_3001 ↔ 3001),
un C LOMLOE porta els seus B i mòduls, un D els seus mòduls. Com que la majoria
de mòduls dels D no porten número, el creuament també va per nom normalitzat.
"""
from cd_lomloe import _B_NUM_RE, _is_prl, normalize_module_name

_HELD_GRADOS = ('B', 'C', 'D')
# Les fitxes dels cicles llisten com a mòdul una nota que no ho és (184 de 195 cicles).
_NOTE_PREFIX = 'incluye una fase de formacion en empresa'
# RD 659/2023, art. 126.4: el Proyecto intermodular i la formació en empresa no es
# convaliden mai; el mòdul optatiu és diferent a cada cicle. Compten al total del cicle,
# però no casen amb els d'un altre.
_NEVER_MATCH_PREFIXES = ('proyecto intermodular', 'formacion en centros de trabajo',
                         'modulo profesional optativo', 'modulo s profesional es optativo')
# Art. 126.3: es convaliden entre cicles del mateix grau; Digitalización i Sostenibilidad,
# a més, només dins la mateixa família professional.
_SAME_LEVEL_PREFIXES = ('ingles profesional',)
_SAME_LEVEL_AND_FAMILY_PREFIXES = ('digitalizacion aplicada', 'sostenibilidad aplicada')

def compute_gap(held_refs, records, bc_lomloe, c_modulos, d_modulos, ciclos_fp=None,
                limit=30) -> dict:
    by_ref = {r['ref']: r for r in records if r.get('ref')}
    b_by_code = {r['codigo']: r for r in records
                 if r.get('grado') == 'B' and not r.get('plan_antiguo') and r.get('codigo')}
    b_nums = {m.group(1) for m in map(_B_NUM_RE.match, b_by_code) if m}

    # Noms que designen mòduls diferents segons el nivell («Inglés profesional» de grau
    # mitjà 0156 i de superior 0179, «Maquillaje» de bàsica i de mitjà): només casen
    # amb el nivell igual. La resta de noms casen sols.
    nums_by_name: dict[str, set[str]] = {}
    num_levels: dict[str, set] = {}   # un mateix número pot ser a cicles de dos nivells (1708)

    def _learn(num, name, nivel):
        if num:
            nums_by_name.setdefault(normalize_module_name(name or ''), set()).add(num)
            if nivel is not None:
                num_levels.setdefault(num, set()).add(nivel)

    d_mods = {}
    for r in records:
        if r.get('grado') == 'D':
            d_mods[r['ref']] = [
                mod for mod in (d_modulos.get(str(r.get('id'))) or {}).get('modulos', [])
                if not normalize_module_name(mod.get('name') or '').startswith(_NOTE_PREFIX)]
            for mod in d_mods[r['ref']]:
                _learn(mod.get('num'), mod.get('name'), r.get('nivel'))
    for code, r in b_by_code.items():
        m = _B_NUM_RE.match(code)
        if m:
            _learn(m.group(1), r.get('denominacion'), r.get('nivel'))
    for mods in c_modulos.values():
        for mod in mods:
            _learn(mod.get('num'), mod.get('name'), None)
    ambiguous = {name for name, nums in nums_by_name.items() if len(nums) > 1}
    num_level = {num: next(iter(levels)) for num, levels in num_levels.items() if len(levels) == 1}

    def keys(num, name, nivel, familia):
        """Claus amb què un mòdul casa amb un altre: el número i el nom normalitzat."""
        norm = normalize_module_name(name or '')
        if norm.startswith(_NEVER_MATCH_PREFIXES):
            return set()
        nivel = num_level.get(num) or nivel
        if norm.startswith(_SAME_LEVEL_AND_FAMILY_PREFIXES):
            return {('nom', norm, nivel, familia)}
        if norm.startswith(_SAME_LEVEL_PREFIXES):
            return {('nom', norm, nivel)}
        out = {('num', num)} if num else set()
        if norm in ambiguous:
            out.add(('nom', norm, nivel))
        elif norm:
            out.add(('nom', norm))
        return out

    def b_keys(code):
        m = _B_NUM_RE.match(code)
        rec = b_by_code.get(code) or {}
        return keys(m.group(1), rec.get('denominacion'), rec.get('nivel'), rec.get('familia')) if m else set()

    held, ignorats, old_c = [], [], []
    have: set[tuple] = set()
    held_set: set[str] = set()
    for ref in held_refs:
        rec = by_ref.get(ref) if isinstance(ref, str) else None
        if not rec or rec.get('grado') not in _HELD_GRADOS:
            if ref not in ignorats:
                ignorats.append(ref)
            continue
        if ref in held_set:
            continue
        held_set.add(ref)
        held.append({'ref': ref, 'grado': rec['grado'], 'codigo': rec.get('codigo'),
                     'denominacion': rec.get('denominacion')})
        grado, code = rec['grado'], rec.get('codigo') or ''
        if grado == 'D':
            for mod in d_mods.get(ref, []):
                have |= keys(mod.get('num'), mod.get('name'), rec.get('nivel'), rec.get('familia'))
        elif rec.get('plan_antiguo'):
            if grado == 'C':
                old_c.append(rec)
        elif grado == 'B':
            have |= b_keys(code)
        else:
            for b_code in bc_lomloe.get(code, []):
                have |= b_keys(b_code)
            for mod in c_modulos.get(code, []):
                # El PRL d'un C no convalida el d'un cicle (mateix criteri que el Pla 078).
                if not _is_prl(mod, b_nums):
                    have |= keys(mod.get('num'), mod.get('name'), rec.get('nivel'), rec.get('familia'))

    def objectiu(rec, tens, falta):
        total = tens + len(falta)
        percent = 100 if not falta else min(99, max(1, round(100 * tens / total)))
        return {'ref': rec['ref'], 'grado': rec['grado'], 'codigo': rec.get('codigo'),
                'denominacion': rec.get('denominacion'), 'familia': rec.get('familia'),
                'nivel': rec.get('nivel'), 'tens': tens, 'total': total, 'percent': percent,
                'complet': not falta, 'falta': falta}

    objectius = []
    if have:
        for rec in records:
            if rec.get('ref') in held_set or rec.get('plan_antiguo'):
                continue
            if rec.get('grado') == 'C':
                b_codes = bc_lomloe.get(rec.get('codigo') or '', [])
                falta = [{'tipus': 'B', 'ref': (b_by_code.get(b) or {}).get('ref'), 'codigo': b,
                          'denominacion': (b_by_code.get(b) or {}).get('denominacion') or b}
                         for b in b_codes if not b_keys(b) & have]
                tens = len(b_codes) - len(falta)
            elif rec.get('grado') == 'D':
                mods = d_mods.get(rec['ref'], [])
                falta = [{'tipus': 'modul', 'nom': mod.get('name')} for mod in mods
                         if not keys(mod.get('num'), mod.get('name'), rec.get('nivel'), rec.get('familia')) & have]
                tens = len(mods) - len(falta)
            else:
                continue
            if tens >= 1:
                objectius.append(objectiu(rec, tens, falta))
        objectius.sort(key=lambda o: (-o['tens'] / o['total'], -o['tens'], o['denominacion'] or ''))

    held_urls = {by_ref[ref].get('ficha_url') for ref in held_set} - {None}
    relacionats, seen = [], set()
    for rec in old_c:
        for cicle in (ciclos_fp or {}).get(rec.get('codigo'), []):
            key = cicle.get('ficha_url') or cicle.get('denominacion')
            if key in seen or cicle.get('ficha_url') in held_urls:
                continue
            seen.add(key)
            relacionats.append({'denominacion': cicle.get('denominacion'), 'familia': cicle.get('familia'),
                                'ficha_url': cicle.get('ficha_url'), 'via': rec.get('codigo')})

    return {'held': held, 'ignorats': ignorats, 'objectius': objectius[:limit],
            'relacionats': relacionats}
