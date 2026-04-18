"""
Suite de tests unitaris per a pdf_scraper.py (Grados A, B, C).
Cobreix requisits PDF-02 a PDF-06.
Tots els tests usen fixtures locals — sense xarxa, sense PDFs reals.
"""
import re
import pytest
from unittest.mock import patch, MagicMock

from scrapers.pdf_scraper import (
    parse_grado_a,
    parse_grado_b,
    parse_grado_c,
    PREFIX_MAP,
    _parse_row,
    _nivel_grado_a,
    _nivel_grado_b,
    _nivel_grado_c,
    _extract_records,
)


# ---------------------------------------------------------------------------
# test_prefix_map_completeness (PDF-02)
# ---------------------------------------------------------------------------

def test_prefix_map_completeness():
    """PREFIX_MAP ha de tenir exactament 30 entrades (24 nou pla + 6 pla antic/LOGSE/HTML)."""
    assert len(PREFIX_MAP) == 30


def test_prefix_map_afd():
    assert PREFIX_MAP['AFD'] == 'Actividades Físicas y Deportivas'


def test_prefix_map_iex_not_imagen():
    """IEX és Industrias Extractivas, NO Imagen y Espectáculos."""
    assert PREFIX_MAP['IEX'] == 'Industrias Extractivas'


def test_prefix_map_ims_is_imagen():
    """IMS és Imagen y Espectáculos."""
    assert PREFIX_MAP['IMS'] == 'Imagen y Espectáculos'


def test_prefix_map_vic():
    assert PREFIX_MAP['VIC'] == 'Vidrio y Cerámica'


# ---------------------------------------------------------------------------
# test_plan_antiguo_detection (PDF-04)
# ---------------------------------------------------------------------------

def test_plan_antiguo_uf_code():
    """Codi amb '(Plan antiguo)' → is_old=True, clean_code sense marcador."""
    new_code_re = re.compile(r'^[A-Z]{2,4}_[AC]_\d')
    code_cell, denom, obs = _parse_row(
        ['UF0297 (Plan antiguo)', 'Denominació', '', ''],
        new_code_re
    )
    assert code_cell == 'UF0297 (Plan antiguo)'
    is_old = '(Plan antiguo)' in code_cell
    clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
    assert is_old is True
    assert clean_code == 'UF0297'


def test_plan_antiguo_new_code():
    """Codi nou pla → is_old=False."""
    new_code_re = re.compile(r'^[A-Z]{2,4}_A_\d')
    code_cell, denom, obs = _parse_row(
        ['AFD_A_3003_01', 'Denominació', '', ''],
        new_code_re
    )
    assert code_cell == 'AFD_A_3003_01'
    is_old = '(Plan antiguo)' in code_cell
    assert is_old is False


def test_plan_antiguo_mf_code():
    """MF2268_2 (Plan antiguo) → is_old=True, clean_code='MF2268_2'."""
    new_code_re = re.compile(r'^[A-Z]{2,4}_B_\d')
    code_cell, denom, obs = _parse_row(
        ['MF2268_2 (Plan antiguo)', 'Denominació', '', ''],
        new_code_re
    )
    assert code_cell == 'MF2268_2 (Plan antiguo)'
    is_old = '(Plan antiguo)' in code_cell
    clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
    assert is_old is True
    assert clean_code == 'MF2268_2'


# ---------------------------------------------------------------------------
# test_nivel_grado_a (PDF-03)
# ---------------------------------------------------------------------------

def test_nivel_grado_a_new():
    assert _nivel_grado_a('AFD_A_3003_01', False) is None


def test_nivel_grado_a_old():
    assert _nivel_grado_a('UF0297', True) is None


# ---------------------------------------------------------------------------
# test_nivel_grado_b (PDF-03)
# ---------------------------------------------------------------------------

def test_nivel_grado_b_new():
    assert _nivel_grado_b('AFD_B_3003', False) is None


def test_nivel_grado_b_old_2():
    assert _nivel_grado_b('MF2268_2', True) == 2


def test_nivel_grado_b_old_1():
    assert _nivel_grado_b('MF2268_1', True) == 1


def test_nivel_grado_b_old_3():
    assert _nivel_grado_b('MF2268_3', True) == 3


def test_nivel_grado_b_old_no_suffix():
    """Codi pla antic sense sufix numèric → None."""
    assert _nivel_grado_b('MF2268', True) is None


# ---------------------------------------------------------------------------
# test_nivel_grado_c (PDF-03)
# ---------------------------------------------------------------------------

def test_nivel_grado_c_3b():
    assert _nivel_grado_c('AFD_C_001_3B', False) == 1


def test_nivel_grado_c_4b():
    assert _nivel_grado_c('AFD_C_001_4B', False) == 2


def test_nivel_grado_c_5b():
    assert _nivel_grado_c('AFD_C_001_5B', False) == 3


def test_nivel_grado_c_old():
    assert _nivel_grado_c('AFDA0511', True) is None


# ---------------------------------------------------------------------------
# test_familia_lookup (PDF-02)
# ---------------------------------------------------------------------------

def test_familia_known_prefix(caplog):
    """Prefix conegut → família correcta, cap warning."""
    import logging
    with caplog.at_level(logging.WARNING, logger='scrapers.pdf_scraper'):
        caplog.clear()
        new_code_re = re.compile(r'^[A-Z]{2,4}_C_\d')
        records = {}
        row = ['AFD_C_001_3B', 'Acondicionamiento físico en sala', '', '']
        code_cell, denom_cell, obs_parts = _parse_row(row, new_code_re)
        assert code_cell is not None
        is_old = '(Plan antiguo)' in code_cell
        clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
        prefix = clean_code.split('_')[0]
        familia = PREFIX_MAP.get(prefix)
        assert familia == 'Actividades Físicas y Deportivas'
        # Cap warning hauria d'haver-se emès
        assert len(caplog.records) == 0


def test_familia_unknown_prefix_warning(caplog):
    """Prefix desconegut → familia='Desconeguda', logging.warning emès."""
    import logging

    # Usar _extract_records amb mock de pdfplumber per simular una pàgina
    mock_page = MagicMock()
    mock_page.extract_table.return_value = [
        ['XXX_C_001_3B', 'Denominació desconeguda', '', ''],
    ]

    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 5 + [mock_page]  # 5 pàgines intro + 1 de dades
    # Pàgines intro retornen cap taula
    for page in mock_pdf.pages[:5]:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with caplog.at_level(logging.WARNING, logger='scrapers.pdf_scraper'):
        with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
            records = _extract_records('dummy.pdf', 'C', _nivel_grado_c)

    assert len(records) == 1
    assert records[0]['familia'] == 'Desconeguda'
    assert any('XXX' in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# test_record_schema (PDF-06)
# ---------------------------------------------------------------------------

def test_record_schema_grado_c():
    """Taula simulada de Grado C → registre amb exactament els camps correctes."""
    mock_page = MagicMock()
    mock_page.extract_table.return_value = [
        ['AFD_C_001_3B', 'Acondicionamiento físico en sala de entrenamiento polivalente', '', ''],
    ]

    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 5 + [mock_page]
    for page in mock_pdf.pages[:5]:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
        records = _extract_records('dummy.pdf', 'C', _nivel_grado_c)

    assert len(records) == 1
    rec = records[0]

    # Camps exactes — sense 'id' ni 'grado' (els afegeix pipeline)
    expected_keys = {'codigo', 'denominacion', 'familia', 'nivel', 'plan_antiguo', 'observaciones'}
    assert set(rec.keys()) == expected_keys
    assert 'id' not in rec
    assert 'grado' not in rec

    assert rec['codigo'] == 'AFD_C_001_3B'
    assert rec['nivel'] == 1
    assert rec['plan_antiguo'] is False
    assert rec['familia'] == 'Actividades Físicas y Deportivas'


# ---------------------------------------------------------------------------
# test_page_skip (PDF-05)
# ---------------------------------------------------------------------------

def test_page_skip_index_4_no_records():
    """Taula a la pàgina índex 4 (pàgina 5 del PDF) → cap registre extret."""
    data_page = MagicMock()
    data_page.extract_table.return_value = [
        ['AFD_C_001_3B', 'Acondicionamiento físico', '', ''],
    ]

    # 5 pàgines, la darrera (índex 4) conté dades — però ha de ser ignorada
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 4 + [data_page]
    for page in mock_pdf.pages[:4]:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
        records = _extract_records('dummy.pdf', 'C', _nivel_grado_c)

    assert records == []


def test_page_skip_index_5_has_records():
    """Taula a la pàgina índex 5 (pàgina 6 del PDF) → registre extret."""
    data_page = MagicMock()
    data_page.extract_table.return_value = [
        ['AFD_C_001_3B', 'Acondicionamiento físico', '', ''],
    ]

    # 6 pàgines: índex 0-4 ignorades, índex 5 conté dades
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 5 + [data_page]
    for page in mock_pdf.pages[:5]:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
        records = _extract_records('dummy.pdf', 'C', _nivel_grado_c)

    assert len(records) == 1


# ---------------------------------------------------------------------------
# test_duplicate_deduplication (PDF-05)
# ---------------------------------------------------------------------------

def test_duplicate_deduplication():
    """Codi duplicat a dues pàgines → només 1 registre conservat."""
    row = ['AFD_C_001_3B', 'Acondicionamiento físico', '', '']

    page1 = MagicMock()
    page1.extract_table.return_value = [row]
    page2 = MagicMock()
    page2.extract_table.return_value = [row]

    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 5 + [page1, page2]
    for page in mock_pdf.pages[:5]:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
        records = _extract_records('dummy.pdf', 'C', _nivel_grado_c)

    assert len(records) == 1


# ---------------------------------------------------------------------------
# test_continuation_rows_ignored
# ---------------------------------------------------------------------------

def test_continuation_rows_ignored():
    """Files de continuació (totes les cel·les del codi buides) → cap registre."""
    mock_page = MagicMock()
    # Fila de continuació: primera cel·la buida, res no coincideix amb codi
    mock_page.extract_table.return_value = [
        ['', 'Continuació de la denominació anterior', '', ''],
    ]

    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 5 + [mock_page]
    for page in mock_pdf.pages[:5]:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
        records = _extract_records('dummy.pdf', 'C', _nivel_grado_c)

    assert records == []


# ---------------------------------------------------------------------------
# test_public_api_exports
# ---------------------------------------------------------------------------

def test_public_api_exports():
    """parse_grado_a/b/c importables i accepten pdf_path: str → list[dict]."""
    mock_pdf = MagicMock()
    mock_pdf.pages = [MagicMock()] * 5  # 5 pàgines intro, cap de dades
    for page in mock_pdf.pages:
        page.extract_table.return_value = None
    mock_pdf.__enter__ = lambda s: mock_pdf
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch('scrapers.pdf_scraper.pdfplumber.open', return_value=mock_pdf):
        result_a = parse_grado_a('dummy.pdf')
        result_b = parse_grado_b('dummy.pdf')
        result_c = parse_grado_c('dummy.pdf')

    assert isinstance(result_a, list)
    assert isinstance(result_b, list)
    assert isinstance(result_c, list)
