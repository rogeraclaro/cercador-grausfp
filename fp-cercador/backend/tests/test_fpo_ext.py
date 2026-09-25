"""test_fpo_ext.py — Especialitats sintètiques dels cursos externs (Pla 063)."""
import fpo_ext as fx

TODAY = '2026-09-25'
FAMS = {c: {'ca': c, 'es': c} for c in ('IFC', 'ADG', 'CTR', 'COM', 'FCO')}


def _c(font, n, titol, **kw):
    base = {
        'idCurs': f'{font.upper()}:{n}', 'font': font, 'tipus': 'Subvencionat',
        'titol': {'ca': titol, 'es': titol}, 'area': '', 'certCodi': '', 'hores': 30.0,
        'modalitat': 'PRESENCIAL', 'estat': '', 'dataInici': '2026-10-01',
        'dataFi': '2026-12-01', 'municipi': 'BARCELONA', 'centre': {'nom': 'X'},
        'fitxaUrl': f'https://x/{n}',
    }
    base.update(kw)
    return base


def test_is_ext_codi():
    assert fx.is_ext_codi('PIMEC:abc') and fx.is_ext_codi('FOMENT:a:b')
    assert not fx.is_ext_codi('IFCD0112') and not fx.is_ext_codi(None)


def test_codi_especialitat_es_un_slug_sense_barres():
    c = _c('pimec', 1, 'Programació neurolingüística / Nivell I!')
    assert fx.codi_especialitat(c) == 'PIMEC:programacio-neurolinguistica-nivell-i'
    assert fx.codi_especialitat(_c('foment', 2, '')) == 'FOMENT:curs'
    assert '/' not in fx.codi_especialitat(_c('pimec', 3, 'a/b'))


def test_estat():
    assert fx.estat(_c('pimec', 1, 'x', dataFi='2026-09-24'), TODAY) == 'finalitzat'
    assert fx.estat(_c('pimec', 1, 'x', dataFi='2026-09-25'), TODAY) == ''   # avui encara compta
    assert fx.estat(_c('pimec', 1, 'x', dataFi=None), TODAY) == ''


def test_familia_pimec_per_area_sense_distingir_majuscules():
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Informàtica'), FAMS) == 'IFC'
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Docència I formació'), {'SSC': {}, 'FCO': {}}) == 'SSC'
    assert fx.familia_codi(_c('pimec', 1, 'x', area='docència i formació'), {'SSC': {}, 'FCO': {}}) == 'SSC'


def test_familia_per_defecte_fco():
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Inventada'), FAMS) == 'FCO'
    assert fx.familia_codi(_c('pimec', 1, 'x', area=''), FAMS) == 'FCO'
    assert fx.familia_codi(_c('pimec', 1, 'x', area='Informàtica'), {'FCO': {}}) == 'FCO'  # IFC no existeix


def test_familia_foment_pel_prefix_del_certificat():
    assert fx.familia_codi(_c('foment', 1, 'x', certCodi='ADGG0208'), FAMS) == 'ADG'
    assert fx.familia_codi(_c('foment', 1, 'x', certCodi='ZZZZ0001'), FAMS) == 'FCO'
    assert fx.familia_codi(_c('foment', 1, 'x'), FAMS) == 'FCO'


def test_build_index_agrupa_edicions_i_ordena():
    cursos = [
        _c('pimec', '1', 'Mindfulness', dataInici='2026-06-01', dataFi='2026-07-01'),   # finalitzada
        _c('pimec', '2', 'Mindfulness', dataInici=None, dataFi=None, tipus='Altres', modalitat=''),
        _c('pimec', '3', 'Mindfulness', dataInici='2026-11-01', dataFi='2026-12-01'),
        _c('pimec', '4', 'Mindfulness', dataInici='2026-10-05', dataFi='2026-10-30',
           area='Idiomes', modalitat='TELEFORMACIÓ'),
        _c('foment', '5', 'Mindfulness'),
        _c('altra', '6', 'Ignorat'),                                                    # font desconeguda
    ]
    idx = fx.build_index(cursos, FAMS, TODAY)
    assert [e['codi'] for e in idx['list']] == ['FOMENT:mindfulness', 'PIMEC:mindfulness']
    e = idx['list'][1]
    assert [c['idCurs'] for c in idx['cursos_by_codi']['PIMEC:mindfulness']] == [
        'PIMEC:4', 'PIMEC:3', 'PIMEC:2', 'PIMEC:1']
    assert e['font'] == 'pimec' and e['titol'] == {'ca': 'Mindfulness', 'es': 'Mindfulness'}
    assert e['familia'] == {'codi': 'CTR', 'desc': {'ca': 'CTR', 'es': 'CTR'}}   # l'edició 4 té àrea Idiomes
    assert e['area']['desc']['ca'] == 'Idiomes' and e['area']['codi'] == ''
    assert e['nCursos'] == 3                       # 4, 3 i 2 no són finalitzades
    assert e['estats'] == ['finalitzat']
    assert e['tipus'] == ['Altres', 'Subvencionat']
    assert e['modalitats'] == ['PRESENCIAL', 'TELEFORMACIÓ']
    assert e['municipis'] == ['BARCELONA'] and e['comarques'] == []
    assert e['nivell'] == 0 and e['hores'] == 30.0 and e['esCertProf'] is False
    assert idx['list'][0]['familia']['codi'] == 'FCO'


def test_familia_de_la_fila_es_la_primera_no_fco():
    cursos = [_c('pimec', '1', 'Anglès'), _c('pimec', '2', 'Anglès', area='Idiomes')]
    e = fx.build_index(cursos, FAMS, TODAY)['list'][0]
    assert e['familia']['codi'] == 'CTR'


def test_es_cert_prof_si_alguna_edicio_te_codi():
    e = fx.build_index([_c('foment', '1', 'ADGG0208: Ofimática', certCodi='ADGG0208')],
                       FAMS, TODAY)['list'][0]
    assert e['esCertProf'] is True and e['familia']['codi'] == 'ADG'


def test_curs_public():
    p = fx.curs_public(_c('foment', '9', 'x', horariText='Lunes a Viernes', dataFi='2026-01-01'), TODAY)
    assert p['idCurs'] == 'FOMENT:9' and p['estat'] == 'finalitzat'
    assert p['font'] == 'foment' and p['tipus'] == 'Subvencionat' and p['hores'] == 30.0
    assert p['horariText'] == 'Lunes a Viernes' and p['fitxaUrl'] == 'https://x/9'
    assert set(p) >= {'titol', 'centre', 'dataInici', 'dataFi', 'modalitat'}


def test_fonts_noves_i_familia_explicita():
    assert fx.is_ext_codi('CECOT:x') and fx.is_ext_codi('CCOO:1')
    c = _c('ccoo', 1, 'Excel', familiaCodi='IFC')
    assert fx.familia_codi(c, FAMS) == 'IFC'
    assert fx.familia_codi(_c('ccoo', 2, 'Excel', familiaCodi='ZZZ'), FAMS) == 'FCO'
    assert fx.familia_codi(_c('cecot', 3, 'Anglès'), FAMS) == 'FCO'
    idx = fx.build_index([_c('cecot', 'a', 'Anglès B1'), _c('ccoo', 'b', 'Anglès B1')], FAMS, TODAY)
    assert [e['codi'] for e in idx['list']] == ['CCOO:angles-b1', 'CECOT:angles-b1']
