"""
uc_corr.py — Pla 091: què convalida un conjunt d'unitats de competència (UC) en un cicle,
segons les taules oficials del BOE (d_uc_corr.json). Funcions pures, sense Flask.

Regla: una fila de la taula A només convalida els seus mòduls quan totes les UC de la fila
estan acreditades.
"""
from cd_lomloe import normalize_module_name
from gap import _NOTE_PREFIX


def convalidated(rows: list[dict], ucs) -> tuple[list[dict], list[dict]]:
    """
    (files complertes, files a mitges) d'una taula A per a les UC acreditades.

    Complerta: {'moduls', 'uc'}. A mitges (hi ha alguna UC de la fila però no totes):
    {'moduls', 'uc', 'falten'}; no convalida res.
    """
    held = set(ucs)
    full, partial = [], []
    for row in rows:
        missing = [u for u in row['uc'] if u not in held]
        if not missing:
            full.append({'moduls': row['moduls'], 'uc': row['uc']})
        elif len(missing) < len(row['uc']):
            partial.append({'moduls': row['moduls'], 'uc': row['uc'], 'falten': missing})
    return full, partial


def held_ucs(held: list[dict], loe_ucs: dict) -> list[str]:
    """
    UC que aporten els graus que algú ja té: les del certificat LOE (loe_ucs: {codi: [UC]}) i la
    del mòdul B del pla antic (MF####_N ↔ UC####_N). Els graus del pla nou no van per UC.
    """
    ucs: list[str] = []
    for rec in held:
        code = rec.get('codigo') or ''
        if not rec.get('plan_antiguo'):
            continue
        if rec.get('grado') == 'C':
            ucs += loe_ucs.get(code) or []
        elif rec.get('grado') == 'B' and code.startswith('MF'):
            ucs.append('UC' + code[2:])
    return list(dict.fromkeys(ucs))


def cycle_for_ucs(entry: dict, ucs) -> dict | None:
    """
    Correspondència d'un cicle per a unes UC, o None si cap UC surt a les seves taules.

    Mana la taula vigent. Si cap UC hi surt però sí a la taula que un decret posterior va
    substituir ('convalida_anterior'), es dona aquella amb 'derogada': True: els certificats
    d'abans del canvi porten els codis d'UC antics i l'equivalència no és a la taula.
    """
    held = set(ucs)
    for key, derogada in (('convalida', False), ('convalida_anterior', True)):
        rows = entry.get(key) or []
        used = [u for u in dict.fromkeys(u for r in rows for u in r['uc']) if u in held]
        if used:
            full, partial = convalidated(rows, held)
            nums = list(dict.fromkeys(m['num'] for r in full for m in r['moduls']))
            return {'decret': entry['decret'], 'vigent': entry['decret'] if derogada else entry['vigent'],
                    'derogada': derogada, 'substituida_per': entry['vigent'] if derogada else None,
                    'uc': used, 'convalida': full, 'a_mitges': partial, 'moduls_convalidats': nums}
    return None


def cycle_modules(modulos: list[dict], entry: dict) -> list[dict]:
    """
    Mòduls d'un cicle ({num, name}) amb el número que falta omplert des de les taules del
    BOE, casant pel nom normalitzat. No toca els que ja en porten i salta la nota sobre la
    formació en empresa que les fitxes llisten com a mòdul.
    """
    by_name: dict[str, str] = {}
    for key in ('convalida', 'acredita'):
        for row in entry.get(key) or []:
            for m in row['moduls']:
                by_name.setdefault(normalize_module_name(m['name']), m['num'])
    out = []
    for m in modulos:
        name = normalize_module_name(m.get('name') or '')
        if not name.startswith(_NOTE_PREFIX):
            out.append({'num': m.get('num') or by_name.get(name), 'name': m.get('name')})
    return out
