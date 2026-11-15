"""test_fpo_agenda.py — build_agenda (Pla 086): cursos FPO que comencen aviat."""
from datetime import date

from fpo_agenda import build_agenda

AVUI = date(2026, 11, 15)
FAMILIES = {'ADG': {'ca': 'ADG - Administració', 'es': 'ADG - Administración'},
            'FCO': {'ca': 'FCO - Complementària', 'es': 'FCO - Complementaria'}}


def _soc(id_, inici, comarca='Barcelonès', modalitat='PRESENCIAL', **extra):
    return {'idCurs': id_, 'titol': {'ca': f'Curs {id_}', 'es': f'Curso {id_}'},
            'familia': {'codi': 'ADG', 'desc': FAMILIES['ADG']}, 'especialitat': {'codi': 'ADGG0408', 'desc': {}},
            'hores': 120.0, 'modalitat': modalitat, 'estat': 'inscripcio', 'dataInici': inici,
            'dataFi': '2027-03-01', 'comarca': comarca, 'municipi': 'Barcelona',
            'centre': {'nom': 'Centre U', 'carrer': 'C. Major, 1', 'cp': '08001', 'municipi': 'Barcelona',
                       'comarca': 'Barcelonès'}, **extra}


def _ext(id_, inici, modalitat='PRESENCIAL', **extra):
    return {'idCurs': id_, 'font': 'pimec', 'tipus': 'Subvencionat', 'titol': {'ca': 'Excel', 'es': 'Excel'},
            'area': '', 'certCodi': '', 'hores': 20.0, 'modalitat': modalitat, 'estat': '', 'dataInici': inici,
            'dataFi': None, 'comarca': '', 'municipi': '', 'centre': {'nom': 'PIMEC'},
            'fitxaUrl': 'https://example.test/excel', **extra}


def _ids(out):
    return [c['idCurs'] for c in out['cursos']]


def test_els_limits_de_la_finestra_hi_entren():
    cursos = [_soc('ahir', '2026-11-14'), _soc('avui', '2026-11-15'), _soc('ultim', '2027-02-13'),
              _soc('fora', '2027-02-14')]
    out = build_agenda(cursos, AVUI, 90)
    assert _ids(out) == ['avui', 'ultim']
    assert out['generat'] == '2026-11-15'
    assert _ids(build_agenda(cursos, AVUI, 91)) == ['avui', 'ultim', 'fora']


def test_ordenats_per_data_i_despres_per_titol():
    out = build_agenda([_soc('b', '2026-12-01'), _soc('c', '2026-11-20'), _soc('a', '2026-12-01')], AVUI)
    assert _ids(out) == ['c', 'a', 'b']


def test_els_cursos_sense_data_es_compten_a_part():
    out = build_agenda([_soc('x', None), _ext('y', ''), _soc('z', '2026-11-20')], AVUI)
    assert _ids(out) == ['z']
    assert out['sense_data'] == 2


def test_en_linia():
    out = build_agenda([_soc('p', '2026-11-20'), _soc('t', '2026-11-21', modalitat='TELEFORMACIÓ'),
                        _soc('v', '2026-11-22', modalitat='VIDEOCONFERÈNCIA'),
                        _soc('m', '2026-11-23', modalitat='MIXTA'), _soc('s', '2026-11-24', modalitat='')], AVUI)
    assert [c['enLinia'] for c in out['cursos']] == [False, True, True, False, False]


def test_els_externs_no_tenen_comarca_i_porten_font_i_tipus():
    out = build_agenda([_ext('PIMEC:excel:1', '2026-11-20'), _soc('s', '2026-11-21', comarca='Gironès')],
                       AVUI, families=FAMILIES)
    ext, soc = out['cursos']
    assert (ext['comarca'], ext['font'], ext['tipus'], ext['fitxaUrl']) == \
        ('', 'pimec', 'Subvencionat', 'https://example.test/excel')
    assert ext['familia'] == {'codi': 'FCO', 'desc': FAMILIES['FCO']}
    assert ext['especialitat']['codi'].startswith('PIMEC:')
    assert (soc['font'], soc['tipus']) == ('soc', 'Subvencionat')
    assert out['comarques'] == ['Gironès']


def test_camps_d_un_curs_del_soc():
    out = build_agenda([_soc('26/1', '2026-11-20', comarca='')], AVUI)
    c = out['cursos'][0]
    assert set(c) == {'idCurs', 'font', 'tipus', 'titol', 'especialitat', 'familia', 'hores', 'modalitat', 'estat',
                      'dataInici', 'dataFi', 'comarca', 'municipi', 'centreNom', 'centreAdreca', 'fitxaUrl',
                      'enLinia'}
    assert c['comarca'] == 'Barcelonès'            # si el curs no en porta, la del centre
    assert (c['centreNom'], c['centreAdreca']) == ('Centre U', 'C. Major, 1, 08001, Barcelona')
    assert c['fitxaUrl'].endswith('fitxa-curs.html?codi_curso_seleccionado=26/1')
    assert c['especialitat'] == {'codi': 'ADGG0408'}
