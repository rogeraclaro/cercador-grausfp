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
