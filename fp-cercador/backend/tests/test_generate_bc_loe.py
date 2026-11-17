"""Tests for scripts/generate_bc_loe.py (plan 090): each certificate only gets its own annex."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from generate_bc_loe import mf_headings, own_segment, resolve_uc_codes  # noqa: E402

# Shape of elem0311.pdf: its own annex, then the start of the next one (ELEM0411).
TWO_ANNEXES = """
ANEXO I
I. IDENTIFICACIÓN DEL CERTIFICADO DE PROFESIONALIDAD
Código: ELEM0311
Relación de unidades de competencia: UC1978_2, UC1979_2
MÓDULO FORMATIVO 1
Código: MF1978_2
Asociado a la Unidad de Competencia: UC1978_2
MÓDULO FORMATIVO 2
  Código:   MF1979_2
MÓDULO DE PRÁCTICAS
Código: MP0463
ANEXO II
Código: ELEM0411
UC1975_2: Mantener electrodomésticos de gama blanca
Código: MF1975_2
"""


def test_own_segment_stops_at_the_next_certificate():
    seg = own_segment(TWO_ANNEXES, 'ELEM0311')
    assert 'MF1979_2' in seg
    assert 'ELEM0411' not in seg and 'UC1975_2' not in seg


def test_own_segment_skips_the_tail_of_the_previous_annex():
    seg = own_segment(TWO_ANNEXES, 'ELEM0411')
    assert 'MF1975_2' in seg and 'MF1978_2' not in seg


def test_own_segment_matches_suffixed_codes_by_base():
    assert 'MF1978_2' in own_segment(TWO_ANNEXES, 'ELEM0311_2')


def test_own_segment_is_empty_when_the_code_is_absent():
    assert own_segment(TWO_ANNEXES, 'ADGD0108') == ''


def test_mf_headings_keep_order_and_drop_duplicates():
    seg = 'Código: MF0002_1\nCódigo: MF0001_2\nCódigo: MF0002_1\nMF9999_3 mentioned, not a heading'
    assert mf_headings(seg) == ['MF0002_1', 'MF0001_2']


def test_annex_alone_gives_only_its_own_modules():
    codes, source = resolve_uc_codes('ELEM0311', TWO_ANNEXES, None, {}, 2)
    assert codes == ['UC1978_2', 'UC1979_2']
    assert source == 'annex'


def test_annex_confirmed_by_sepe():
    sepe = {'mf': ['MF1978', 'MF1979'], 'mp': ['MP0463'], 'nivel': 2}
    assert resolve_uc_codes('ELEM0311', TWO_ANNEXES, sepe, {}, 2) == (['UC1978_2', 'UC1979_2'], 'annex')


def test_scanned_pdf_falls_back_to_sepe_with_catalogue_levels():
    sepe = {'mf': ['MF1620', 'MF1621'], 'mp': ['MP0001'], 'nivel': 2}
    codes, source = resolve_uc_codes('MAPU0112', '', sepe, {'1620': 'MF1620_2', '1621': 'MF1621_1'}, 2)
    assert codes == ['UC1620_2', 'UC1621_1']
    assert source == 'sepe'


def test_sepe_level_falls_back_to_the_certificate_level():
    sepe = {'mf': ['MF1620'], 'mp': [], 'nivel': 3}
    assert resolve_uc_codes('MAPU0112', '', sepe, {}, 3)[0] == ['UC1620_3']


def test_incomplete_annex_is_completed_from_sepe_keeping_annex_levels():
    text = 'Código: ELES0108\nCódigo: MF0120_2\n'
    sepe = {'mf': ['MF0120', 'MF0121'], 'mp': ['MP0093'], 'nivel': 2}
    codes, source = resolve_uc_codes('ELES0108', text, sepe, {'0121': 'MF0121_2'}, 2)
    assert codes == ['UC0120_2', 'UC0121_2']
    assert source == 'sepe'


def test_truncated_sepe_list_does_not_override_a_longer_annex():
    heads = [f'MF{n:04d}_3' for n in range(1, 10)]                      # 9 modules in the annex
    text = 'Código: HOTR0110\n' + '\n'.join(f'Código: {h}' for h in heads)
    sepe = {'mf': [h[:6] for h in heads[:8]], 'mp': [], 'nivel': 3}     # SEPE caps the list at 8
    codes, source = resolve_uc_codes('HOTR0110', text, sepe, {}, 3)
    assert len(codes) == 9
    assert source == 'annex'


def test_no_annex_and_no_sepe_gives_nothing():
    assert resolve_uc_codes('COML0121_1', '', None, {}, 1) == ([], 'none')
