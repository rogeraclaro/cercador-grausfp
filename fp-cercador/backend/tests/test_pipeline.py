"""
test_pipeline.py — Tests unitaris del pipeline (arquitectura buscador+HTML).

Tests sense xarxa real: parse_buscador_all i tots els parsers HTML estan
mockejats. La constant DATA_PATH es redirigeix a tmp_path per evitar escriure
a backend/data/ofertes.json real.

Cobreix:
  D-01 Fail fast — excepció propagada, ofertes.json NO escrit
  D-02 Tot o res — escriptura atòmica
  D-03 IDs seqüencials A→B→C→D→E
  D-08 Retorna dict estructurat
"""
import json
import logging
import unittest.mock as mock

import pytest
from requests.exceptions import HTTPError


# ---------------------------------------------------------------------------
# Patch paths (arquitectura buscador+HTML actual)
# ---------------------------------------------------------------------------

PATCH_PARSE_BUSCADOR  = 'scrapers.pipeline.parse_buscador_all'
PATCH_PARSE_D_BASICO  = 'scrapers.pipeline.parse_grado_d_basico'
PATCH_PARSE_D_MEDIO   = 'scrapers.pipeline.parse_grado_d_medio'
PATCH_PARSE_D_SUPERIOR = 'scrapers.pipeline.parse_grado_d_superior'
PATCH_PARSE_E         = 'scrapers.pipeline.parse_grado_e'


# ---------------------------------------------------------------------------
# Helper de registres
# ---------------------------------------------------------------------------

def _rec(codigo='IFC_A_0001_AB', denominacion='Den X',
         familia='Informática y Comunicaciones', nivel=1):
    """Registre mínim amb el schema del buscador (A/B/C)."""
    return {
        'codigo': codigo,
        'denominacion': denominacion,
        'familia': familia,
        'nivel': nivel,
        'plan_antiguo': False,
        'observaciones': '',
        'ficha_id': 1,
    }


def _html_rec(denominacion='Den HTML', familia='Actividades Físicas y Deportivas'):
    """Registre mínim amb el schema HTML (D/E): sense codigo, amb ficha_url."""
    return {
        'codigo': None,
        'denominacion': denominacion,
        'familia': familia,
        'nivel': None,
        'plan_antiguo': False,
        'observaciones': '',
        'ficha_url': 'https://www.todofp.es/x',
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolate_data_path(tmp_path, monkeypatch):
    """Redirigeix DATA_PATH a tmp_path perquè cap test escrigui a data/ofertes.json real."""
    import scrapers.pipeline as pl
    monkeypatch.setattr(pl, 'DATA_PATH', str(tmp_path / 'ofertes.json'))


def _run_with_mocks(buscador_data, d_basico=None, d_medio=None, d_superior=None, e=None):
    """Executa pipeline.run() amb tots els parsers mockejats."""
    from scrapers.pipeline import run
    with mock.patch(PATCH_PARSE_BUSCADOR, return_value=buscador_data), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=d_basico or []), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=d_medio or []), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=d_superior or []), \
         mock.patch(PATCH_PARSE_E, return_value=e or []):
        return run()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_returns_schema():
    """pipeline.run() retorna dict amb claus esperades i errors buit (D-08)."""
    result = _run_with_mocks(
        buscador_data={'A': [_rec()], 'B': [], 'C': []},
    )
    required_keys = {
        'total', 'by_grado', 'families', 'denominacions',
        'denominacions_by_grado', 'meta_by_grado', 'errors', 'unknown_families', 'duration_seconds',
    }
    assert required_keys == set(result.keys())
    assert result['errors'] == []


def test_run_adds_grado_and_sequential_ids():
    """Cada registre de sortida té 'grado' i 'id' seqüencial 1-based."""
    result = _run_with_mocks(
        buscador_data={'A': [_rec('IFC_A_0001_AB'), _rec('IFC_A_0002_AB')], 'B': [], 'C': []},
        e=[_html_rec()],
    )
    import scrapers.pipeline as pl
    with open(pl.DATA_PATH) as f:
        records = json.load(f)

    assert all('grado' in r for r in records)
    ids = [r['id'] for r in records]
    assert ids == list(range(1, len(records) + 1))


def test_id_order_a_b_c_d_e():
    """Amb 1 registre per grado, l'ordre dels ids segueix A, B, C, D, E (D = basico+medio+superior)."""
    result = _run_with_mocks(
        buscador_data={
            'A': [_rec('IFC_A_0001_AB')],
            'B': [_rec('IFC_B_0001_AB')],
            'C': [_rec('IFC_C_0001_AB')],
        },
        d_basico=[_html_rec('Basico')],
        d_medio=[_html_rec('Medio')],
        d_superior=[_html_rec('Superior')],
        e=[_html_rec('E-rec')],
    )
    import scrapers.pipeline as pl
    with open(pl.DATA_PATH) as f:
        records = json.load(f)

    # 7 registres en total, ids 1–7
    assert len(records) == 7
    grado_order = [r['grado'] for r in records]
    assert grado_order == ['A', 'B', 'C', 'D', 'D', 'D', 'E']


def test_by_grado_counts():
    """by_grado compta correctament; D suma els 3 subtipus (D-03)."""
    result = _run_with_mocks(
        buscador_data={'A': [_rec()], 'B': [_rec(), _rec()], 'C': []},
        d_basico=[_html_rec(), _html_rec()],
        d_medio=[_html_rec()],
        d_superior=[],
        e=[_html_rec()],
    )
    assert result['by_grado'] == {'A': 1, 'B': 2, 'C': 0, 'D': 3, 'E': 1}
    assert result['total'] == 7


def test_family_alias_normalization():
    """Un registre amb familia='Imagen y Sonido' surt amb 'Imagen y Espectáculos' via FAMILY_ALIASES."""
    result = _run_with_mocks(
        buscador_data={'A': [_rec(familia='Imagen y Sonido')], 'B': [], 'C': []},
    )
    import scrapers.pipeline as pl
    with open(pl.DATA_PATH) as f:
        records = json.load(f)

    assert records[0]['familia'] == 'Imagen y Espectáculos'
    assert 'Imagen y Espectáculos' in result['families']
    assert 'Imagen y Sonido' not in result['unknown_families']


def test_unknown_family_reported(caplog):
    """Un registre amb familia desconeguda apareix a unknown_families i es loga un warning."""
    with caplog.at_level(logging.WARNING, logger='scrapers.pipeline'):
        result = _run_with_mocks(
            buscador_data={'A': [_rec(familia='Família Inventada')], 'B': [], 'C': []},
        )
    assert 'Família Inventada' in result['unknown_families']
    assert any('Família Inventada' in msg for msg in caplog.messages)


def test_fail_fast_buscador_error(tmp_path, monkeypatch):
    """Si parse_buscador_all aixeca RuntimeError, run() propaga i DATA_PATH NO existeix (D-01/D-02)."""
    import scrapers.pipeline as pl
    data_path = str(tmp_path / 'ofertes.json')
    monkeypatch.setattr(pl, 'DATA_PATH', data_path)

    with mock.patch(PATCH_PARSE_BUSCADOR, side_effect=RuntimeError('connexió fallida')):
        with pytest.raises(RuntimeError):
            pl.run()

    import os
    assert not os.path.exists(data_path), "DATA_PATH NO ha d'existir si el pipeline ha fallat"


def test_fail_fast_html_error(tmp_path, monkeypatch):
    """Si parse_grado_e aixeca HTTPError, run() propaga i DATA_PATH NO existeix (D-01/D-02)."""
    import scrapers.pipeline as pl
    data_path = str(tmp_path / 'ofertes2.json')
    monkeypatch.setattr(pl, 'DATA_PATH', data_path)

    with mock.patch(PATCH_PARSE_BUSCADOR, return_value={'A': [_rec()], 'B': [], 'C': []}), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, side_effect=HTTPError('503')):
        with pytest.raises(HTTPError):
            pl.run()

    import os
    assert not os.path.exists(data_path), "DATA_PATH NO ha d'existir si parse_grado_e ha fallat"


def test_atomic_write_output_valid_json():
    """Després de run(), DATA_PATH existeix, és JSON vàlid i el total coincideix."""
    result = _run_with_mocks(
        buscador_data={'A': [_rec(), _rec('IFC_A_0002_AB')], 'B': [_rec('IFC_B_0001_AB')], 'C': []},
        d_basico=[_html_rec()],
        e=[_html_rec()],
    )
    import os
    import scrapers.pipeline as pl
    assert os.path.exists(pl.DATA_PATH), "DATA_PATH ha d'existir després d'un run() correcte"

    with open(pl.DATA_PATH) as f:
        records = json.load(f)

    assert isinstance(records, list)
    assert len(records) == result['total']
