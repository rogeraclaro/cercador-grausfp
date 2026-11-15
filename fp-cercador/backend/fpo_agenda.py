"""
fpo_agenda.py — agenda «Comencen aviat» dels cursos FPO (Pla 086): cursos del SOC i
externs amb data d'inici dins d'una finestra, ordenats per data. Funció pura, sense Flask.
"""
from datetime import date, timedelta
from urllib.parse import quote

import fpo_ext

DIES_DEFAULT = 90
DIES_MAX = 180
EN_LINIA = ('TELEFORMACIÓ', 'VIDEOCONFERÈNCIA')
_BUIT = {'ca': '', 'es': ''}
_SOC_FITXA_CURS_URL = ("https://serveiocupacio.gencat.cat/ca/persones/vull-formar-me/"
                       "cercadors-formacio-especialitats/cercador-integrat/fitxa-curs.html")


def soc_fitxa_url(curs: dict) -> str:
    """Enllaç a la fitxa del curs concret (centre inclòs) al cercador del SOC.

    És el mateix GET que fa el formulari `formFitxaCursos` del cercador del SOC.
    """
    return f"{_SOC_FITXA_CURS_URL}?codi_curso_seleccionado={quote(curs.get('idCurs') or '', safe='/')}"


def row(curs: dict, families: dict) -> dict:
    """Un curs (del SOC o extern) amb només els camps que la vista, el .ics i les alertes necessiten."""
    centre = curs.get('centre') or {}
    ext = curs.get('font') in fpo_ext.FONTS
    if ext:
        fam_codi = fpo_ext.familia_codi(curs, families)
        familia = {'codi': fam_codi, 'desc': families.get(fam_codi) or {'ca': fam_codi, 'es': fam_codi}}
    else:
        familia = curs.get('familia') or {'codi': '', 'desc': _BUIT}
    modalitat = curs.get('modalitat') or ''
    return {
        'idCurs': curs.get('idCurs', ''),
        'font': curs['font'] if ext else 'soc',
        'tipus': (curs.get('tipus') or '') if ext else 'Subvencionat',
        'titol': fpo_ext.titol_net(curs.get('titol')) if ext else (curs.get('titol') or _BUIT),
        'especialitat': {'codi': fpo_ext.codi_especialitat(curs) if ext
                         else (curs.get('especialitat') or {}).get('codi', '')},
        'familia': {'codi': familia.get('codi', ''), 'desc': familia.get('desc') or _BUIT},
        'hores': curs.get('hores') or 0.0,
        'modalitat': modalitat,
        'estat': curs.get('estat') or '',
        'dataInici': curs.get('dataInici'),
        'dataFi': curs.get('dataFi'),
        'comarca': curs.get('comarca') or centre.get('comarca') or '',
        'municipi': curs.get('municipi') or centre.get('municipi') or '',
        'centreNom': centre.get('nom') or '',
        'centreAdreca': ', '.join(p for p in (centre.get('carrer'), centre.get('cp'),
                                              centre.get('municipi')) if p),
        'fitxaUrl': (curs.get('fitxaUrl') or '') if ext else soc_fitxa_url(curs),
        'enLinia': modalitat in EN_LINIA,
    }


def build_agenda(cursos: list, avui: date, dies: int = DIES_DEFAULT, families: dict | None = None) -> dict:
    """
    `cursos`: els de soc_cursos.json i ext_cursos.json junts. Torna els que comencen entre
    `avui` i `avui + dies` (tots dos inclosos), ordenats per data d'inici.
    """
    families = families or {}
    first, last = avui.isoformat(), (avui + timedelta(days=dies)).isoformat()
    rows = [row(c, families) for c in cursos
            if c.get('dataInici') and first <= c['dataInici'] <= last]
    rows.sort(key=lambda r: (r['dataInici'], (r['titol'].get('ca') or '').lower(), r['idCurs']))
    return {
        'cursos': rows,
        'sense_data': sum(1 for c in cursos if not c.get('dataInici')),
        'comarques': sorted({r['comarca'] for r in rows if r['comarca']}),
        'generat': first,
    }
