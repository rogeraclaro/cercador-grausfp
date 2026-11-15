"""test_compare.py — build_comparison (Pla 085): graus en columnes i el que tenen en comú."""
from compare import build_comparison


def _ctx(ref, grado='D', modulos=None, ocupaciones=(), seguents=(), previs=(), **extra):
    rec = {'ref': ref, 'grado': grado, 'codigo': extra.pop('codigo', None), 'denominacion': f'Grau {ref}',
           'familia': 'Administración y Gestión', 'nivel': extra.pop('nivel', 2),
           'plan_antiguo': extra.pop('plan_antiguo', False)}
    rec.update(extra.pop('rec', {}))
    contingut = extra.pop('contingut', {})
    if modulos is not None:
        contingut = {**contingut, 'modulos': list(modulos)}
    return {'rec': rec, 'contingut': contingut, 'ocupaciones': list(ocupaciones),
            'centres': extra.pop('centres', {'total': 0, 'per_ccaa': []}),
            'previs': [_node(r) for r in previs], 'seguents': [_node(r) for r in seguents]}


def _node(ref):
    return {'key': f'D:{ref}', 'ref': ref, 'grado': 'D', 'denominacion': f'Grau {ref}', 'ficha': None, 'id': 7}


def test_dos_d_amb_moduls_comuns_escrits_diferent():
    a = _ctx('a', modulos=['Comunicación y atención al cliente (GS)', 'Inglés profesional (GS)',
                           'Gestión de la documentación jurídica y empresarial', 'Contabilidad y fiscalidad'])
    b = _ctx('b', modulos=['Comunicacion y atencion al cliente', 'Inglés Profesional (GS)',
                           'Gestión de la documentación jurídica y empresarial.', 'Protocolo empresarial'])
    out = build_comparison([a, b])
    assert out['comuns']['moduls'] == ['Comunicación y atención al cliente (GS)', 'Inglés profesional (GS)',
                                       'Gestión de la documentación jurídica y empresarial']
    assert out['moduls_compartits'] == {'n': 3, 'de': 4}
    assert [g['ref'] for g in out['graus']] == ['a', 'b']
    assert out['graus'][1]['moduls'][3] == 'Protocolo empresarial'


def test_un_modul_comu_a_dos_de_tres_no_es_comu():
    a = _ctx('a', modulos=['Ofimática', 'Tutoría', 'Archivo'])
    b = _ctx('b', modulos=['Ofimática', 'Tutoría'])
    c = _ctx('c', modulos=['Tutoría', 'Archivo', 'Ventas', 'Compras'])
    out = build_comparison([a, b, c])
    assert out['comuns']['moduls'] == ['Tutoría']
    assert out['moduls_compartits'] == {'n': 1, 'de': 2}


def test_c_pla_nou_amb_un_d():
    # L'endpoint posa els mòduls del C (c_modulos.json) a contingut.modulos, com els dels D.
    c = _ctx('ADG_C_001_3B', grado='C', codigo='ADG_C_001_3B', modulos=['Ofimática', 'Archivo y comunicación'])
    d = _ctx('d', modulos=['Archivo y comunicación', 'Ofimática', 'Inglés profesional'])
    out = build_comparison([c, d])
    assert out['comuns']['moduls'] == ['Ofimática', 'Archivo y comunicación']
    assert out['moduls_compartits'] == {'n': 2, 'de': 2}


def test_un_grau_sense_moduls_barrejat_amb_un_d():
    a = _ctx('UC0001_1', grado='A', contingut={'ra': ['Fer x'], 'ecp': ['ECP1']})
    d = _ctx('d', modulos=['Ofimática'])
    out = build_comparison([a, d])
    assert out['comuns']['moduls'] == []
    assert out['moduls_compartits'] == {'n': 0, 'de': 0}
    assert out['graus'][0]['moduls'] == [] and out['graus'][0]['ra'] == ['Fer x'] and out['graus'][0]['ecp'] == ['ECP1']


def test_tres_graus_i_nomes_dos_amb_moduls():
    a = _ctx('UC0001_1', grado='A')
    d1 = _ctx('d1', modulos=['Ofimática', 'Archivo'])
    d2 = _ctx('d2', modulos=['Ofimática'])
    out = build_comparison([a, d1, d2])
    assert out['comuns']['moduls'] == ['Ofimática']
    assert out['moduls_compartits'] == {'n': 1, 'de': 1}


def test_la_nota_de_formacio_en_empresa_no_es_un_modul():
    nota = 'Incluye una fase de formación en empresa u organismo equiparado.'
    out = build_comparison([_ctx('a', modulos=['Ofimática', nota]), _ctx('b', modulos=[nota, 'Ofimática'])])
    assert out['graus'][0]['moduls'] == ['Ofimática']
    assert out['comuns']['moduls'] == ['Ofimática']
    assert out['moduls_compartits'] == {'n': 1, 'de': 1}


def test_ocupacions_i_seguents_comuns():
    a = _ctx('a', ocupaciones=['Auxiliar administrativo', 'Recepcionista'], seguents=['x', 'y'], previs=['p'])
    b = _ctx('b', ocupaciones=['Recepcionista', 'Telefonista'], seguents=['y', 'z'])
    out = build_comparison([a, b])
    assert out['comuns']['ocupacions'] == ['Recepcionista']
    assert out['comuns']['seguents'] == ['y']
    assert out['graus'][0]['seguents'] == [{'ref': 'x', 'grado': 'D', 'denominacion': 'Grau x'},
                                           {'ref': 'y', 'grado': 'D', 'denominacion': 'Grau y'}]
    assert out['graus'][0]['previs'] == [{'ref': 'p', 'grado': 'D', 'denominacion': 'Grau p'}]


def test_camps_de_cada_grau():
    c = _ctx('ADGG0408', grado='C', codigo='ADGG0408', plan_antiguo=True, nivel=1,
             rec={'duracion_horas': 430},
             contingut={'uc': [{'codigo': 'UC0969_1', 'nombre': 'Realizar operaciones'}]},
             centres={'total': 3, 'per_ccaa': [('Cataluña', 2), ('Aragón', 1)]})
    e = _ctx('e', grado='E', rec={'denominacion': 'Curso X (Acceso GS)'},
             contingut={'acceso': [_node('d9')], 'acceso_otros': ['Técnico Superior en Y']})
    out = build_comparison([c, e])
    g = out['graus'][0]
    assert set(g) == {'ref', 'grado', 'codigo', 'denominacion', 'familia', 'nivel', 'nivel_label', 'plan_antiguo',
                      'duracion_horas', 'moduls', 'uc', 'ra', 'ecp', 'acces', 'ocupacions', 'centres',
                      'previs', 'seguents'}
    assert (g['nivel_label'], g['plan_antiguo'], g['duracion_horas']) == ('Nivel 1', True, 430)
    assert g['uc'] == [{'codigo': 'UC0969_1', 'nombre': 'Realizar operaciones'}]
    assert g['centres'] == {'total': 3, 'per_ccaa': {'Cataluña': 2, 'Aragón': 1}}
    assert out['graus'][1]['acces'] == ['Grau d9', 'Técnico Superior en Y']
    assert out['graus'][1]['nivel_label'] == 'Acceso desde grado superior'
    assert out['graus'][1]['duracion_horas'] is None
