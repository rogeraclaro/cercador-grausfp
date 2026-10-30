"""Pla 080: descoberta dels RD individuals de certificats professionals (scripts/audit_c_modulos_boe.py)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import audit_c_modulos_boe as a  # noqa: E402

TITOL_ENOTURISMO = (
    'Real Decreto 1128/2025, de 11 de diciembre, por el que se establece el Certificado profesional '
    'en Enoturismo, de la familia profesional Hostelería y Turismo, se fija su currículo y las '
    'ofertas de grados B y A incluidas en este certificado profesional.')


def test_parse_titol_establece():
    assert a.parse_titol(TITOL_ENOTURISMO) == {
        'rd': 'RD 1128/2025', 'tipus': 'establece', 'denominacion': 'Enoturismo', 'modifica_rd': []}


def test_parse_titol_establece_i_modifica_un_altre_rd():
    # RD 488/2026 (BOE-A-2026-13294): estableix IMP_C_012_5B i modifica el RD 300/2026 (ART).
    t = a.parse_titol(
        'Real Decreto 488/2026, de 17 de junio, por el que se establece el Certificado profesional en '
        'Procedimientos y técnicas de micropigmentación, de la familia profesional Imagen Personal, se fija '
        'su currículo y las ofertas de grados B y A incluidas en este certificado profesional y se modifica '
        'el Real Decreto 300/2026, de 8 de abril, por el que se establece el título de Formación Profesional '
        'de Grado Superior de Técnico Superior en Diseño y construcción artesanal de instrumentos musicales '
        'de cuerda, se fijan los aspectos básicos del currículo y las ofertas de grados C, B y A incluidos '
        'en este título.')
    assert (t['tipus'], t['denominacion'], t['modifica_rd']) == \
        ('establece', 'Procedimientos y técnicas de micropigmentación', ['RD 300/2026'])


def test_parse_titol_modifica_i_correccio():
    mod = a.parse_titol('Real Decreto 5/2026, de 2 de febrero, por el que se modifica el Real Decreto '
                        '1128/2025, por el que se establece el Certificado profesional en Enoturismo.')
    assert mod['tipus'] == 'modifica' and mod['rd'] == 'RD 5/2026' and mod['modifica_rd'] == ['RD 1128/2025']
    cor = a.parse_titol('Corrección de errores del Real Decreto 1128/2025, de 11 de diciembre, por el que '
                        'se establece el Certificado profesional en Enoturismo, de la familia profesional X.')
    assert cor['tipus'] == 'correccion'


def test_parse_titol_de_titol_fp_amb_grados_c():
    # Els RD de títol (Grau D) també estableixen Graus C (p. ex. RD 533/2025, funeraris).
    t = a.parse_titol('Real Decreto 533/2025, de 24 de junio, por el que se establece el título de Formación '
                      'Profesional de Grado Medio de Técnico en Servicios funerarios, se fijan los aspectos '
                      'básicos del currículo y las ofertas de grados C, B y A incluidos en este título.')
    assert t == {'rd': 'RD 533/2025', 'tipus': 'titol', 'denominacion': None, 'modifica_rd': []}


def test_confirmacio_per_codi_o_per_moduls():
    # El BOE publica de vegades el codi amb marcadors (EOC_C_00X_4B): es confirma pels mòduls.
    text = 'Código: EOC_C_00X_4B. a) 1739. Piedra. b) 1740. Muros. c) 1724. Prevención.'
    assert a.confirmacio('EOC_C_012_4B', ['1724', '1740', '1739'], text) == 'moduls'
    assert a.confirmacio('EOC_C_012_4B', ['1739', '9999'], text) is None
    assert a.confirmacio('EOC_C_00X_4B', [], text) == 'codi'


def test_parse_titol_ignora_altres_disposicions():
    assert a.parse_titol('Real Decreto 1/2026, por el que se regula el Sistema de Formación Profesional.') is None


def test_norm_ignora_accents_majuscules_i_puntuacio():
    assert a.norm('Servicios de control de plagas/organismos nocivos') == \
        a.norm('servicios de control de plagas / organismos  nocivos')
    assert a.norm('Instalación') == 'instalacion'


def test_aparellar_per_denominacio():
    cs = {'HOT_C_015_5B': 'Enoturismo', 'XXX_C_001_4B': 'Sense RD'}
    troballes = {'BOE-A-2025-25701': {'rd': 'RD 1128/2025', 'tipus': 'establece',
                                      'denominacion': 'enoturismo', 'data': '20251216'}}
    assert a.aparellar(cs, troballes) == ({'HOT_C_015_5B': 'BOE-A-2025-25701'}, ['XXX_C_001_4B'])


# --- Fase 2: lectors del RD individual i del RD de títol (fragments reals del BOE) ---

# BOE-A-2025-25701 (RD 1128/2025, Enoturismo): article de mòduls i annex I.
RD_INDIVIDUAL = (
    'Artículo 2. Identificación. b) Código: HOT_C_015_5B. '
    'Artículo 8. Módulos profesionales. Los módulos profesionales de este certificado profesional quedan '
    'desarrollados en el anexo III. Dichos módulos son los que a continuación se relacionan: '
    'a) 1737. Experiencias enoturísticas. b) 1738. Análisis sensorial de productos selectos propios de '
    'sumillería y diseño de sus ofertas. c) 1232. Procesos de venta. d) 0020. Primeros auxilios. '
    'e) 0179. Inglés Profesional (GS). f) 1782. Prevención de riesgos laborales. Este certificado '
    'profesional incorpora un periodo de formación en empresa. '
    'ANEXO I Oferta de grado B: Certificados de competencia Formación a cursar Certificado de competencia '
    'Duración 1737. Experiencias enoturísticas. HOT_B_1737. Experiencias enoturísticas. 200 '
    '1232. Procesos de venta. HOT_B_1232. Procesos de venta. 160 0020. Primeros auxilios. HOT_B_0020. '
    'Primeros auxilios. 60 ANEXO II Oferta de grado A: Acreditaciones parciales de competencia '
    'a) HOT_B_9999. Fora del bloc.')

# BOE-A-2024-24102 (RD 1157/2024, Sanidad ambiental aplicada): annex V (C) i annex VI (B).
RD_TITOL = (
    'ANEXO V Oferta de Grado C: certificados profesionales a) CERTIFICADO PROFESIONAL: SERVICIOS DE CONTROL '
    'DE PLAGAS/ORGANISMOS NOCIVOS. 1. Identificación b) Código: SEA_C_001_4B. c) Nivel: 2. '
    '7. Módulos profesionales del Certificado Profesional Módulos Profesionales 1697. Preparación y traslado '
    'de materiales. 1698. Control de organismos nocivos, artrópodos y roedores. 1732. Nivel básico de '
    'Prevención de riesgos laborales. b) CERTIFICADO PROFESIONAL: MANTENIMIENTO HIGIÉNICO-SANITARIO DE '
    'INSTALACIONES SUSCEPTIBLES DE PROLIFERACIÓN DE LEGIONELLA. 1. Identificación b) Código: SEA_C_002_4B. '
    '7. Módulos profesionales del Certificado Profesional Módulos Profesionales 1697. Preparación. '
    '1700. Control de Legionella. 1732. Nivel básico de Prevención de riesgos laborales. '
    'ANEXO VI Oferta de Grado B: certificados de competencia a) Certificados de competencia incluidos en el '
    'Certificado profesional Servicios de control de plagas/organismos nocivos: Formación a cursar '
    'Certificado de competencia Duración 1697. Preparación. SEA_B_1697. Preparación. 90 1698. Control. '
    'SEA_B_1698. Control. 310 b) Certificados de competencia incluidos en el Certificado profesional '
    'Mantenimiento higiénico-sanitario de instalaciones susceptibles de proliferación de Legionella : '
    'Formación a cursar 1697. Preparación. SEA_B_1697. Preparación. 90 1700. Control de Legionella. '
    'SEA_B_1700. Control de Legionella. 230 ANEXO VII Oferta de Grado A')


def test_parse_rd_individual():
    assert a.parse_rd(RD_INDIVIDUAL, 'HOT_C_015_5B', 'Enoturismo', 'establece') == (
        ['1737', '1738', '1232', '0020', '0179', '1782'], ['0020', '1232', '1737'])


def test_parse_rd_individual_amb_codi_amb_marcadors():
    # BOE-A-2025-25699: "Código: EOC_C_00X_4B." — l'únic C del RD, el codi no cal.
    text = RD_INDIVIDUAL.replace('HOT_C_015_5B', 'EOC_C_00X_4B')
    assert a.parse_rd(text, 'EOC_C_012_4B', 'X', 'establece')[0][0] == '1737'


def test_parse_rd_titol():
    assert a.parse_rd(RD_TITOL, 'SEA_C_001_4B', 'Servicios de control de plagas/organismos nocivos',
                      'titol') == (['1697', '1698', '1732'], ['1697', '1698'])
    assert a.parse_rd(RD_TITOL, 'SEA_C_002_4B',
                      'Mantenimiento higiénico-sanitario de instalaciones susceptibles de proliferación de legionella',
                      'titol') == (['1697', '1700', '1732'], ['1697', '1700'])


def test_parse_rd_no_trobat_retorna_none():
    assert a.parse_rd(RD_TITOL, 'SEA_C_009_4B', 'No hi és', 'titol') == (None, None)


def test_parse_rd_individual_ignora_mencions_de_l_oferta_b_fora_de_l_annex():
    # BOE-A-2026-13294 (RD 488/2026): l'articulat parla de l'"Oferta de grado B" i modifica
    # l'annex d'un altre RD (ART_B_1771) abans de l'ANEXO I. Només compta l'ANEXO I.
    text = ('Oferta de grado B: ver anexo. Se modifica la letra g) ART_B_1771. Construcción, de la Oferta '
            'de Grado A del RD 300/2026. ANEXO II del RD 300/2026. ' + RD_INDIVIDUAL)
    assert a.parse_rd(text, 'HOT_C_015_5B', 'Enoturismo', 'establece')[1] == ['0020', '1232', '1737']


def test_parse_rd_titol_capcalera_acabada_en_punt_i_bloc_en_minuscules():
    # BOE-A-2026-8022 (RD 300/2026, ART): "Certificado profesional: …" en minúscules acaba el bloc
    # del C anterior, i el nom de l'oferta de B acaba en punt, no en dos punts.
    text = ('ANEXO VI Oferta de Grado C a) Certificado profesional: Guitarras. b) Código: ART_C_001_5B. '
            '7. Módulos profesionales del certificado profesional. Módulos profesionales 1750. Taller. '
            '1769. Guitarras. 1732. Nivel básico. b) Certificado profesional: Arco. b) Código: ART_C_002_5B. '
            '7. Módulos profesionales 1771. Arco. ANEXO VII Oferta de Grado B: Certificados de competencia '
            'a) Certificados de competencia incluidos en el Certificado profesional Guitarras, bandurrias y '
            'laúdes españoles. Formación a cursar 1750. Taller. ART_B_1750. Taller. 90 1769. Guitarras. '
            'ART_B_1769. Guitarras. 300 b) Certificados de competencia incluidos en el Certificado profesional '
            'Arco: Formación a cursar 1771. Arco. ART_B_1771. Arco. 200 ANEXO VIII')
    assert a.parse_rd(text, 'ART_C_001_5B', 'Guitarras, bandurrias y laúdes españoles', 'titol') == (
        ['1750', '1769', '1732'], ['1750', '1769'])


def test_parse_rd_individual_annex_sense_de():
    # BOE-A-2025-25704 (RD 1131/2025, MAM_C_007_4B): "ANEXO I Oferta grado B:".
    text = RD_INDIVIDUAL.replace('ANEXO I Oferta de grado B', 'ANEXO I Oferta grado B')
    assert a.parse_rd(text, 'HOT_C_015_5B', 'Enoturismo', 'establece')[1] == ['0020', '1232', '1737']


# --- Fase 3: auditoria amb els RD individuals i de títol ---

def test_audit_fa_servir_el_rd_individual():
    c_modulos = {'HOT_C_015_5B': [{'num': n, 'name': 'x'} for n in ('1737', '1232', '0020', '1782')]}
    bc = {'HOT_C_015_5B': ['HOT_B_0020', 'HOT_B_1232', 'HOT_B_1737']}
    ind = {'HOT_C_015_5B': ('RD 1128/2025', RD_INDIVIDUAL, 'Enoturismo', 'establece')}
    row = a.audit(c_modulos, bc, {}, ind)['HOT_C_015_5B']
    assert row['decret'] == 'RD 1128/2025'
    assert row['boe_b'] == ['0020', '1232', '1737'] and a.classify(row) == 'ok'


def test_audit_modulos_c_amb_rd_individual_no_queda_sense_decret():
    c_modulos = {'SEA_C_001_4B': [{'num': '1732', 'name': 'PRL'}]}
    ind = {'SEA_C_001_4B': ('RD 1157/2024', RD_TITOL, 'Servicios de control de plagas/organismos nocivos', 'titol')}
    mods = a.audit_modulos(c_modulos, {}, {}, set(), ind)
    assert [m[:2] for m in mods['cap_decret']] == [('SEA_C_001_4B', '1732')] and not mods['sense_decret']


def test_codi_entre_guions_al_decret_de_grup():
    # BOE-A-2025-6699 (RD 209/2025): "– Código: IMP_C_006_4B – Título de Formación Profesional…".
    text = ('– Código: IMP_C_006_4B – Título asociado. 7. Módulos profesionales 0842. Peinados. '
            '0843. Coloración capilar. 1782. Prevención de riesgos laborales. ANEXO II')
    assert a.parse_modulos_annex_i(text, 'IMP_C_006_4B') == ['0842', '0843', '1782']
    assert a.te_codi(text, 'IMP_C_006_4B') and not a.te_codi(text, 'IMP_C_006_5B')
