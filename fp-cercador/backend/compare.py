"""
compare.py — comparador de graus (Pla 085): fins a 3 graus en columnes i el que
tenen en comú. Funció pura, sense Flask: rep els contextos ja muntats per grau.
"""
from cd_lomloe import normalize_module_name
from gap import _NOTE_PREFIX
from grau_page import nivel_label


def _node(node: dict) -> dict:
    return {'ref': node.get('ref'), 'grado': node.get('grado'), 'denominacion': node.get('denominacion')}


def _grau(ctx: dict) -> dict:
    rec, contingut = ctx['rec'], ctx.get('contingut') or {}
    centres = ctx.get('centres') or {}
    return {
        'ref': rec['ref'],
        'grado': rec.get('grado'),
        'codigo': rec.get('codigo'),
        'denominacion': rec.get('denominacion'),
        'familia': rec.get('familia'),
        'nivel': rec.get('nivel'),
        'nivel_label': nivel_label(rec),
        'plan_antiguo': bool(rec.get('plan_antiguo')),
        'duracion_horas': rec.get('duracion_horas'),
        # Les fitxes dels cicles llisten com a mòdul una nota que no ho és (vegeu gap.py).
        'moduls': [m for m in contingut.get('modulos') or []
                   if not normalize_module_name(m).startswith(_NOTE_PREFIX)],
        'uc': contingut.get('uc') or [],
        'ra': contingut.get('ra') or [],
        'ecp': contingut.get('ecp') or [],
        'acces': ([n.get('denominacion') for n in contingut.get('acceso') or []]
                  + list(contingut.get('acceso_otros') or [])),
        'ocupacions': list(ctx.get('ocupaciones') or []),
        'centres': {'total': centres.get('total', 0), 'per_ccaa': dict(centres.get('per_ccaa') or [])},
        'previs': [_node(n) for n in ctx.get('previs') or []],
        'seguents': [_node(n) for n in ctx.get('seguents') or []],
    }


def _in_all(first: list, others: list[set], key=lambda v: v) -> list:
    """Elements de `first` (en el seu ordre) presents a tots els conjunts de `others`."""
    return [v for v in first if all(key(v) in other for other in others)]


def build_comparison(contexts: list[dict]) -> dict:
    """
    `contexts`: un dict per grau, el de app._grau_context més `rec` (el registre del
    catàleg). Els mòduls dels C del pla nou han de venir ja a `contingut.modulos`.
    """
    graus = [_grau(ctx) for ctx in contexts]

    # Mòduls comuns: per nom normalitzat, entre els graus que en tenen (mínim dos).
    with_mods = [g['moduls'] for g in graus if g['moduls']]
    comuns_moduls: list = []
    if len(with_mods) >= 2:
        others = [{normalize_module_name(m) for m in mods} for mods in with_mods[1:]]
        comuns_moduls = _in_all(with_mods[0], others, key=normalize_module_name)

    # Mòduls propis de cada grau: els que no són comuns (els noms poden estar escrits diferent).
    comuns_norm = {normalize_module_name(m) for m in comuns_moduls}
    for g in graus:
        g['moduls_propis'] = [m for m in g['moduls'] if normalize_module_name(m) not in comuns_norm]

    return {
        'graus': graus,
        'comuns': {
            'moduls': comuns_moduls,
            'ocupacions': _in_all(graus[0]['ocupacions'], [set(g['ocupacions']) for g in graus[1:]]),
            'seguents': _in_all([n['ref'] for n in graus[0]['seguents']],
                                [{n['ref'] for n in g['seguents']} for g in graus[1:]]),
        },
        'moduls_compartits': {'n': len(comuns_moduls),
                              'de': min(map(len, with_mods)) if len(with_mods) >= 2 else 0},
    }
