"""
test_html_scraper.py — Tests unitaris del html_scraper amb fixtures HTML minimalistes.

Tots els tests són sense xarxa real: scrapers.html_scraper.requests.get està mockat.
Cobreix els requisits HTML-01 a HTML-06 de REQUIREMENTS.md.
"""
import logging
import unittest.mock as mock

import pytest

# Els següents imports fallaran fins que el Plan 02 creï scrapers/html_scraper.py.
# Aquesta és la condició RED del TDD.
from scrapers.html_scraper import (
    HTML_FAMILY_ALIASES,
    _build_fam_map,
    _extract_titols,
    parse_grado_d_basico,
    parse_grado_d_medio,
    parse_grado_d_superior,
    parse_grado_e,
)

from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(html: str) -> mock.Mock:
    """Crea un mock de requests.Response amb .text i .raise_for_status()."""
    resp = mock.Mock()
    resp.text = html
    resp.raise_for_status = mock.Mock()
    return resp


PATCH_REQUESTS_GET = 'scrapers.html_scraper.requests.get'


# ---------------------------------------------------------------------------
# HTML-01, HTML-03: compte de títols i identificació per id="tit-*"
# ---------------------------------------------------------------------------

def test_parse_grado_d_basico_single_title(minimal_html_grado_d_one_record):
    """parse_grado_d_basico retorna 1 registre amb denominació extreta de l'<a id='tit-*'>."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_basico('http://fake')
    assert len(result) == 1
    assert result[0]['denominacion'] == 'Gestión Administrativa'


def test_parse_grado_d_medio_single_title(minimal_html_grado_d_one_record):
    """parse_grado_d_medio retorna 1 registre en un HTML d'1 títol."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_medio('http://fake')
    assert len(result) == 1


def test_parse_grado_d_superior_single_title(minimal_html_grado_d_one_record):
    """parse_grado_d_superior retorna 1 registre en un HTML d'1 títol."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_superior('http://fake')
    assert len(result) == 1


def test_parse_grado_e_single_title(minimal_html_grado_d_one_record):
    """parse_grado_e retorna 1 registre en un HTML d'1 títol (estructura idèntica)."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_e('http://fake')
    assert len(result) == 1


def test_parse_grado_d_two_records_same_family(minimal_html_grado_d_two_records_same_family):
    """2 títols de la mateixa família (rowspan=2) s'extreuen correctament."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_two_records_same_family)):
        result = parse_grado_d_basico('http://fake')
    assert len(result) == 2
    # Ambdós han de tenir la mateixa família
    assert result[0]['familia'] == result[1]['familia']
    assert result[0]['familia'] == 'Administración y Gestión'


# ---------------------------------------------------------------------------
# HTML-04: família correcta per cada registre
# ---------------------------------------------------------------------------

def test_family_mapping_direct(minimal_html_grado_d_one_record):
    """Una família canònica (sense alias) es propaga tal qual al registre."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_basico('http://fake')
    assert result[0]['familia'] == 'Administración y Gestión'


def test_family_mapping_alias_imagen_y_sonido(minimal_html_alias_imagen_y_sonido):
    """'Imagen y Sonido' del HTML es mapa a 'Imagen y Espectáculos' via HTML_FAMILY_ALIASES."""
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_alias_imagen_y_sonido)):
        result = parse_grado_d_medio('http://fake')
    assert len(result) == 1
    assert result[0]['familia'] == 'Imagen y Espectáculos'


def test_html_family_aliases_contains_known_exceptions():
    """HTML_FAMILY_ALIASES conté com a mínim les 2 entrades detectades en recerca."""
    assert 'Imagen y Sonido' in HTML_FAMILY_ALIASES
    assert HTML_FAMILY_ALIASES['Imagen y Sonido'] == 'Imagen y Espectáculos'
    assert 'Artes y Artesanias' in HTML_FAMILY_ALIASES
    assert HTML_FAMILY_ALIASES['Artes y Artesanias'] == 'Artesanía'


def test_family_unknown_becomes_desconeguda_and_warns(minimal_html_unknown_family, caplog):
    """Una família no canònica produeix familia='Desconeguda' i warning al log (D-08)."""
    caplog.set_level(logging.WARNING, logger='scrapers.html_scraper')
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_unknown_family)):
        result = parse_grado_d_superior('http://fake')
    assert len(result) == 1
    assert result[0]['familia'] == 'Desconeguda'
    # Warning emès
    assert any('Desconeguda' in rec.message or 'fam99' in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# HTML-05: nivel correcte per subtipus (Básico→1, Medio→2, Superior→3, E→None)
# ---------------------------------------------------------------------------

def test_nivel_basico_is_1(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_basico('http://fake')
    assert result[0]['nivel'] == 1


def test_nivel_medio_is_2(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_medio('http://fake')
    assert result[0]['nivel'] == 2


def test_nivel_superior_is_3(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_superior('http://fake')
    assert result[0]['nivel'] == 3


def test_nivel_grado_e_is_none(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_e('http://fake')
    assert result[0]['nivel'] is None


# ---------------------------------------------------------------------------
# HTML-06: codigo=None, plan_antiguo=False, observaciones=""
# ---------------------------------------------------------------------------

def test_record_fields_codigo_none(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_basico('http://fake')
    assert result[0]['codigo'] is None


def test_record_fields_plan_antiguo_false(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_basico('http://fake')
    assert result[0]['plan_antiguo'] is False


def test_record_fields_observaciones_empty(minimal_html_grado_d_one_record):
    with mock.patch(PATCH_REQUESTS_GET, return_value=_mock_response(minimal_html_grado_d_one_record)):
        result = parse_grado_d_basico('http://fake')
    assert result[0]['observaciones'] == ''


# ---------------------------------------------------------------------------
# Tests unitaris de helpers privats
# ---------------------------------------------------------------------------

def test_build_fam_map_ignores_header_logo():
    """_build_fam_map NO ha d'incloure l'alt del logo de TodoFP (<img alt='Logotipo de TodoFP'>) perquè no està dins un <th headers='familia'>."""
    html = """
    <html><body>
      <img alt="Logotipo de TodoFP">
      <table><tbody>
        <tr><th headers="familia" id="fam0"><img alt="Logotipo Administración y Gestión"></th></tr>
      </tbody></table>
    </body></html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    fam_map = _build_fam_map(soup)
    assert fam_map == {'fam0': 'Administración y Gestión'}


def test_extract_titols_skips_td_without_fam_id():
    """_extract_titols ignora <td> amb headers que NO continguin cap fam_id."""
    html = """
    <html><body><table><tbody>
      <tr><td headers="titulacion"><a id="tit-x" href="#">Sense família</a></td></tr>
    </tbody></table></body></html>
    """
    soup = BeautifulSoup(html, 'html.parser')
    records = _extract_titols(soup, fam_map={}, nivel=1, grado='D')
    assert records == []


# ---------------------------------------------------------------------------
# Fail fast (D-01): raise_for_status propaga excepció
# ---------------------------------------------------------------------------

def test_parse_grado_d_basico_fail_fast_on_http_error():
    """Si requests.get torna 4xx/5xx, l'excepció es propaga (D-01 fail fast)."""
    import requests as req_lib
    fail_resp = mock.Mock()
    fail_resp.raise_for_status = mock.Mock(
        side_effect=req_lib.exceptions.HTTPError("404 Not Found")
    )
    with mock.patch(PATCH_REQUESTS_GET, return_value=fail_resp):
        with pytest.raises(req_lib.exceptions.HTTPError):
            parse_grado_d_basico('http://fake')
