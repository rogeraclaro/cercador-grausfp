"""
fpo_ext.py — Cursos FPO externs (PIMEC, Foment) com a especialitats sintètiques (Pla 063).

Funcions pures: sense E/S ni estat global. `app.py` hi passa les dades, les famílies
del SOC i la data d'avui (ISO). Vegeu `scrapers/ext_cursos.py` per al format de curs.
"""
import re
import unicodedata

FONTS = ('pimec', 'foment')
CODI_PREFIXOS = tuple(f'{f.upper()}:' for f in FONTS)
FALLBACK_FAMILIA = 'FCO'   # "Formació complementària": família real del SOC

# Àrea de PIMEC -> codi de família del SOC (claus en minúscules). Proposta revisable.
PIMEC_AREA_FAMILIA = {
    'disseny gràfic': 'ARG',
    'docència i formació': 'SSC',
    'economia i finances': 'ADG',
    'gestió empresarial': 'ADG',
    'habilitats directives': 'CTR',
    'habilitats personals': 'CTR',
    'hostaleria i turisme': 'HOT',
    'idiomes': 'CTR',
    'informàtica': 'IFC',
    'logística i transport': 'TMV',
    'manteniment i producció': 'IMA',
    'marketing digital': 'COM',
    'prevenció de riscos laborals': 'SEA',
    'recursos humans i laboral': 'ADG',
    'sectorial': 'FCO',
    'tecnologia i innovació': 'IFC',
    'vendes i marketing': 'COM',
}


def is_ext_codi(codi) -> bool:
    """True per a un codi d'especialitat (`PIMEC:...`) o un idCurs (`FOMENT:...`) extern."""
    return isinstance(codi, str) and codi.startswith(CODI_PREFIXOS)


def _slug(text) -> str:
    s = unicodedata.normalize('NFKD', text or '')
    s = ''.join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:80].strip('-') or 'curs'


def codi_especialitat(curs: dict) -> str:
    return f"{curs['font'].upper()}:{_slug((curs.get('titol') or {}).get('ca'))}"


def estat(curs: dict, today_iso: str) -> str:
    """'finalitzat' si la data de fi és anterior a avui; si no, ''."""
    fi = curs.get('dataFi')
    return 'finalitzat' if fi and fi < today_iso else ''


def familia_codi(curs: dict, families: dict) -> str:
    if curs.get('font') == 'pimec':
        codi = PIMEC_AREA_FAMILIA.get((curs.get('area') or '').strip().lower(), FALLBACK_FAMILIA)
    else:
        codi = (curs.get('certCodi') or '')[:3]
    return codi if codi in families else FALLBACK_FAMILIA


def _familia(codi: str, families: dict) -> dict:
    return {'codi': codi, 'desc': families.get(codi) or {'ca': codi, 'es': codi}}


def _rank(curs: dict, today_iso: str) -> int:
    if estat(curs, today_iso):
        return 2
    return 0 if curs.get('dataInici') else 1


def curs_public(curs: dict, today_iso: str) -> dict:
    return {
        'idCurs': curs.get('idCurs', ''),
        'titol': curs.get('titol', {'ca': '', 'es': ''}),
        'centre': curs.get('centre', {}),
        'dataInici': curs.get('dataInici'),
        'dataFi': curs.get('dataFi'),
        'estat': estat(curs, today_iso),
        'modalitat': curs.get('modalitat', ''),
        'fitxaUrl': curs.get('fitxaUrl', ''),
        'font': curs.get('font', ''),
        'tipus': curs.get('tipus', ''),
        'hores': curs.get('hores', 0.0),
        'horariText': curs.get('horariText', ''),
    }


def build_index(cursos: list, families: dict, today_iso: str) -> dict:
    """{'list': [fila, ...], 'cursos_by_codi': {codi: [edicions ordenades]}}.

    `families` és {codi_familia: {'ca':.., 'es':..}} (dels soc_especs.json).
    """
    grups: dict = {}
    for c in cursos:
        if c.get('font') in FONTS:
            grups.setdefault(codi_especialitat(c), []).append(c)

    llista, per_codi = [], {}
    for codi, eds in grups.items():
        eds.sort(key=lambda c: (_rank(c, today_iso), c.get('dataInici') or '', c.get('idCurs') or ''))
        per_codi[codi] = eds
        fam = next((f for f in (familia_codi(c, families) for c in eds)
                    if f != FALLBACK_FAMILIA), FALLBACK_FAMILIA)
        area = next((c['area'] for c in eds if c.get('area')), '')
        llista.append({
            'codi': codi,
            'titol': eds[0].get('titol', {'ca': '', 'es': ''}),
            'familia': _familia(fam, families),
            'area': {'codi': '', 'desc': {'ca': area, 'es': area}},
            'nivell': 0,
            'hores': max((c.get('hores') or 0.0 for c in eds), default=0.0),
            'esCertProf': any(c.get('certCodi') for c in eds),
            'rd': None,
            'programaUrl': '',
            'nCursos': sum(1 for c in eds if not estat(c, today_iso)),
            'comarques': [],
            'municipis': sorted({c['municipi'] for c in eds if c.get('municipi')}),
            'estats': sorted({e for e in (estat(c, today_iso) for c in eds) if e}),
            'modalitats': sorted({c['modalitat'] for c in eds if c.get('modalitat')}),
            'font': eds[0]['font'],
            'tipus': sorted({c['tipus'] for c in eds if c.get('tipus')}),
        })
    llista.sort(key=lambda x: ((x['titol'].get('ca') or x['codi']).lower(), x['codi']))
    return {'list': llista, 'cursos_by_codi': per_codi}
