"""Tests for scripts/generate_c_loe_estructura.py (plan 093): MF/UF hours from an annex text."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from generate_c_loe_estructura import blank_inconsistent_hours, parse_estructura  # noqa: E402

# Shape of elee0109.pdf (pdfplumber text), cut down: MF with UF, a shared UF, MF without UF, MP.
SAMPLE = """
Código: ELEE0109
Duración de la formación asociada: 920 horas.
Relación de módulos formativos y de unidades formativas:
Denominación: Instalaciones eléctricas en edificios de viviendas.
Código: MF0820_2
Nivel de cualificación: 2
Asociado a la Unidad de Competencia:
UC0820_2 Montar instalaciones.
Duración: 170 horas.
UNIDAD FORMATIVA 1
Denominación: Montaje de instalaciones de enlace.
Código: UF0884
Duración: 60 horas.
Referente de competencia: Esta unidad formativa se corresponde con la RP1.
Código: UF0885
Duración: 80 horas.
UNIDAD FORMATIVA 3
Denominación: Prevención.
Código: UF0886
Duración: 30 horas.
Código: MF0821_2
Asociado a la Unidad de Competencia: UC0821_2
Duración: 230 horas.
Código: UF0886
Duración: 30 horas.
Código: MF0825_2
Asociado a la Unidad de Competencia: UC0825_2
Duración: 180 horas.
Código: MP0183
Duración: 80 horas.
"""


def test_mf_with_ufs_hours_and_uc():
    info = parse_estructura(SAMPLE)
    first = info['mf'][0]
    assert first['codigo'] == 'MF0820_2' and first['h'] == 170 and first['uc'] == 'UC0820_2'
    assert [(u['codigo'], u['h']) for u in first['ufs']] == [('UF0884', 60), ('UF0885', 80), ('UF0886', 30)]


def test_shared_uf_listed_under_every_mf():
    info = parse_estructura(SAMPLE)
    assert [u['codigo'] for u in info['mf'][1]['ufs']] == ['UF0886']


def test_mf_without_uf_and_practice_module_and_total():
    info = parse_estructura(SAMPLE)
    assert info['mf'][2]['ufs'] == [] and info['mf'][2]['h'] == 180
    assert info['mp'] == {'codigo': 'MP0183', 'h': 80}
    assert info['total_h'] == 920


def test_annex_without_hours_leaves_none():
    info = parse_estructura('Código: MF0001_1\nAsociado a la Unidad de Competencia: UC0001_1\nCódigo: UF0001\n')
    assert info['total_h'] is None
    assert info['mf'][0]['h'] is None and info['mf'][0]['ufs'][0]['h'] is None


def test_typos_in_annex_codes_are_normalised():
    # elesm0108.pdf writes MF0121-2 and UF425: without this the MF is lost and its UF hang from the previous MF.
    info = parse_estructura('Código: MF0120_2\nDuración: 180 horas\nCódigo: MF0121-2\nDuración: 150 horas\n'
                            'Código: UF425\nDuración: 50 horas\nCódigo: MP093\nDuración: 120 horas')
    assert [m['codigo'] for m in info['mf']] == ['MF0120_2', 'MF0121_2']
    assert info['mf'][1]['ufs'] == [{'codigo': 'UF0425', 'h': 50}]
    assert info['mp'] == {'codigo': 'MP0093', 'h': 120}


def test_spaces_and_missing_colon_in_annex_headers():
    info = parse_estructura('Código: MF 1323_1\nDuración: 80 horas\nCódigo MF0881_1\nDuración: 60 horas.')
    assert [(m['codigo'], m['h']) for m in info['mf']] == [('MF1323_1', 80), ('MF0881_1', 60)]


def test_hours_that_do_not_add_up_are_blanked():
    info = parse_estructura('Código: MF0001_1\nDuración: 100 horas\nCódigo: UF0001\nDuración: 30 horas\n'
                            'Código: UF0002\nDuración: 30 horas')
    assert blank_inconsistent_hours(info) == 1
    assert info['mf'][0]['h'] is None and all(u['h'] is None for u in info['mf'][0]['ufs'])
    ok = parse_estructura('Código: MF0001_1\nDuración: 60 horas\nCódigo: UF0001\nDuración: 30 horas\n'
                          'Código: UF0002\nDuración: 30 horas')
    assert blank_inconsistent_hours(ok) == 0 and ok['mf'][0]['h'] == 60
