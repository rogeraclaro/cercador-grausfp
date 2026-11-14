"""test_gap.py — «Què em falta?» (Pla 083): càlcul pur, catàlegs fets a mà."""
from gap import compute_gap

ADG = 'Administración y Gestión'
URL_SA = 'https://www.todofp.es/adg/servicios-administrativos.html'


def _rec(grado, ref, denominacion, codigo=None, antic=False, **extra):
    return {'grado': grado, 'ref': ref, 'codigo': codigo, 'denominacion': denominacion,
            'familia': ADG, 'nivel': 1, 'plan_antiguo': antic, **extra}


RECORDS = [
    _rec('B', 'ADG_B_3001', 'Tratamiento informático de datos', 'ADG_B_3001'),
    _rec('B', 'ADG_B_3002', 'Aplicaciones básicas de ofimática', 'ADG_B_3002'),
    _rec('B', 'ADG_B_3003', 'Técnicas administrativas básicas', 'ADG_B_3003'),
    _rec('B', 'UF0510', 'B del pla antic', 'UF0510', antic=True),
    _rec('C', 'ADG_C_001_3B', 'Grabación y tratamiento de datos', 'ADG_C_001_3B'),
    _rec('C', 'ADG_C_002_3B', 'Operaciones auxiliares administrativas', 'ADG_C_002_3B'),
    _rec('C', 'ADG_C_003_3B', 'Sense res en comú', 'ADG_C_003_3B'),
    _rec('C', 'ADGG0408', 'Operaciones auxiliares (pla antic)', 'ADGG0408', antic=True),
    _rec('D', 'adg~servicios-administrativos', 'Servicios Administrativos', id=10, ficha_url=URL_SA),
    _rec('D', 'adg~gestion-administrativa', 'Gestión Administrativa', id=11),
    _rec('D', 'adg~sense-moduls-comuns', 'Sense mòduls comuns', id=12),
    _rec('A', 'UC0001_1', 'Un grau A', 'UC0001_1'),
]
BC = {
    'ADG_C_001_3B': ['ADG_B_3001', 'ADG_B_3002'],
    'ADG_C_002_3B': ['ADG_B_3002', 'ADG_B_3003'],
    'ADG_C_003_3B': ['ADG_B_9999'],
}
C_MOD = {
    'ADG_C_001_3B': [{'num': '3001', 'name': 'Tratamiento informático de datos'},
                     {'num': '3002', 'name': 'Aplicaciones básicas de ofimática'},
                     {'num': '0156', 'name': 'Inglés (GS)'},
                     {'num': '1782', 'name': 'Prevención de riesgos laborales'}],
}
D_MOD = {
    '10': {'modulos': [{'num': '3001', 'name': 'Tratamiento informático de datos'},
                       {'num': None, 'name': 'Aplicaciones basicas de ofimatica'},
                       {'num': None, 'name': 'Inglés (Grado Superior)'},
                       {'num': None, 'name': 'Prevención de riesgos laborales'},
                       {'num': None, 'name': 'Itinerario personal para la empleabilidad'}]},
    '11': {'modulos': [{'num': None, 'name': 'Prevención de riesgos laborales'},
                       {'num': None, 'name': 'Itinerario personal para la empleabilidad'},
                       {'num': '3003', 'name': 'Técnicas administrativas básicas'},
                       {'num': None, 'name': 'Contabilidad'}]},
    '12': {'modulos': [{'num': None, 'name': 'Un mòdul que no té ningú'}]},
}
CICLOS = {'ADGG0408': [{'denominacion': 'Servicios Administrativos', 'familia': ADG, 'ficha_url': URL_SA}]}


def gap(held, **kw):
    return compute_gap(held, RECORDS, BC, C_MOD, D_MOD, CICLOS, **kw)


def _obj(result, ref):
    return next((o for o in result['objectius'] if o['ref'] == ref), None)


def test_llista_buida_dona_resultat_buit():
    assert gap([]) == {'held': [], 'ignorats': [], 'objectius': [], 'relacionats': []}


def test_ref_desconegut_i_grau_a_van_a_ignorats():
    result = gap(['no-existeix', 'UC0001_1', 'ADG_B_3001'])
    assert result['ignorats'] == ['no-existeix', 'UC0001_1']
    assert result['held'] == [{'ref': 'ADG_B_3001', 'grado': 'B', 'codigo': 'ADG_B_3001',
                               'denominacion': 'Tratamiento informático de datos'}]


def test_un_b_sol_dona_un_modul():
    result = gap(['ADG_B_3001'])
    c1 = _obj(result, 'ADG_C_001_3B')
    assert (c1['tens'], c1['total'], c1['percent'], c1['complet']) == (1, 2, 50, False)
    assert c1['falta'] == [{'tipus': 'B', 'ref': 'ADG_B_3002', 'codigo': 'ADG_B_3002',
                            'denominacion': 'Aplicaciones básicas de ofimática'}]
    d = _obj(result, 'adg~servicios-administrativos')
    assert (d['tens'], d['total']) == (1, 5)
    assert _obj(result, 'ADG_C_002_3B') is None  # cap peça coberta


def test_un_c_dona_els_seus_b_i_moduls():
    result = gap(['ADG_C_001_3B'])
    assert _obj(result, 'ADG_C_001_3B') is None  # ja el té
    c2 = _obj(result, 'ADG_C_002_3B')
    assert (c2['tens'], c2['total']) == (1, 2)
    assert [f['codigo'] for f in c2['falta']] == ['ADG_B_3003']
    assert _obj(result, 'ADG_C_003_3B') is None


def test_d_objectiu_compta_per_numero_i_per_nom_normalitzat():
    d = _obj(gap(['ADG_C_001_3B']), 'adg~servicios-administrativos')
    # 3001 per número; ofimàtica sense accents i «Inglés (GS)» ↔ «(Grado Superior)» per nom
    assert (d['tens'], d['total'], d['percent']) == (3, 5, 60)
    assert d['falta'] == [{'tipus': 'modul', 'nom': 'Prevención de riesgos laborales'},
                          {'tipus': 'modul', 'nom': 'Itinerario personal para la empleabilidad'}]


def test_prl_d_un_c_no_compta_i_el_d_un_d_si():
    assert _obj(gap(['ADG_C_001_3B']), 'adg~gestion-administrativa') is None
    d = _obj(gap(['adg~servicios-administrativos']), 'adg~gestion-administrativa')
    assert (d['tens'], d['total']) == (2, 4)
    assert [f['nom'] for f in d['falta']] == ['Técnicas administrativas básicas', 'Contabilidad']


def test_un_d_cobreix_els_b_dels_seus_moduls():
    c1 = _obj(gap(['adg~servicios-administrativos']), 'ADG_C_001_3B')
    assert (c1['tens'], c1['total'], c1['percent'], c1['complet']) == (2, 2, 100, True)
    assert c1['falta'] == []


def test_b_i_c_del_pla_antic_no_donen_cap_objectiu():
    result = gap(['UF0510', 'ADGG0408'])
    assert result['objectius'] == []
    assert [h['ref'] for h in result['held']] == ['UF0510', 'ADGG0408']
    assert result['relacionats'] == [{'denominacion': 'Servicios Administrativos', 'familia': ADG,
                                      'ficha_url': URL_SA, 'via': 'ADGG0408'}]


def test_relacionats_no_repeteix_un_cicle_que_ja_te():
    assert gap(['ADGG0408', 'adg~servicios-administrativos'])['relacionats'] == []
    assert compute_gap(['ADGG0408'], RECORDS, BC, C_MOD, D_MOD)['relacionats'] == []


def test_ordre_per_percentatge_i_limit():
    result = gap(['ADG_C_001_3B', 'ADG_B_3003'])
    refs = [o['ref'] for o in result['objectius']]
    assert refs == ['ADG_C_002_3B', 'adg~servicios-administrativos', 'adg~gestion-administrativa']
    assert result['objectius'][0]['complet'] is True
    assert [o['ref'] for o in gap(['ADG_C_001_3B', 'ADG_B_3003'], limit=1)['objectius']] == ['ADG_C_002_3B']


def test_refs_repetits_es_compten_un_cop():
    assert len(gap(['ADG_B_3001', 'ADG_B_3001'])['held']) == 1


def test_mateix_nom_en_nivells_diferents_no_es_confon():
    """«Inglés profesional» és el 0156 al grau mitjà i el 0179 al superior."""
    records = [
        _rec('C', 'C_GM', 'C de grau mitjà', 'ADG_C_010_3B', nivel=2),
        _rec('D', 'd~gm', 'Cicle de grau mitjà', id=1, nivel=2),
        _rec('D', 'd~gs', 'Cicle de grau superior', id=2, nivel=3),
        _rec('D', 'd~gs2', 'Un altre cicle superior', id=3, nivel=3),
    ]
    c_mod = {'ADG_C_010_3B': [{'num': '0156', 'name': 'Inglés profesional'}]}
    d_mod = {'1': {'modulos': [{'num': None, 'name': 'Inglés profesional (GM)'}]},
             '2': {'modulos': [{'num': '0179', 'name': 'Inglés Profesional (Grado Superior)'}]},
             '3': {'modulos': [{'num': None, 'name': 'Inglés profesional (GS)'}]}}
    assert [o['ref'] for o in compute_gap(['C_GM'], records, {}, c_mod, d_mod)['objectius']] == ['d~gm']
    assert [o['ref'] for o in compute_gap(['d~gs'], records, {}, c_mod, d_mod)['objectius']] == ['d~gs2']


def test_la_nota_de_la_fitxa_no_es_un_modul_i_l_optatiu_no_casa_entre_cicles():
    nota = 'Incluye una fase de formación en empresa u organismo equiparado como parte integrada del currículo'
    optatiu = 'Módulo profesional optativo (competencia de cada Comunidad Autónoma)'
    records = [_rec('D', 'd~1', 'Cicle 1', id=1), _rec('D', 'd~2', 'Cicle 2', id=2),
               _rec('D', 'd~3', 'Cicle 3', id=3)]
    d_mod = {'1': {'modulos': [{'num': None, 'name': 'Contabilidad'}, {'num': None, 'name': optatiu},
                               {'num': None, 'name': nota}]},
             '2': {'modulos': [{'num': None, 'name': 'Contabilidad'}, {'num': None, 'name': optatiu},
                               {'num': None, 'name': nota + '*'}]},
             '3': {'modulos': [{'num': None, 'name': 'Un altre mòdul'}, {'num': None, 'name': optatiu},
                               {'num': None, 'name': nota}]}}
    objectius = compute_gap(['d~1'], records, {}, {}, d_mod)['objectius']
    assert [(o['ref'], o['tens'], o['total']) for o in objectius] == [('d~2', 1, 2)]
    assert objectius[0]['falta'] == [{'tipus': 'modul', 'nom': optatiu}]
