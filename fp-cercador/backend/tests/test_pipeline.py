"""
test_pipeline.py — Tests unitaris del pipeline amb mocks.

Tests sense xarxa real: tots els requests.get, os.unlink, os.replace
i les funcions parse_grado_* estan mockejades.
"""
import json
import os
import tempfile
import unittest.mock as mock

import pytest


# ---------------------------------------------------------------------------
# Helpers de fixtures de registre
# ---------------------------------------------------------------------------

def _make_record(suffix='01', codigo_prefix='AFD', grado_letter='A'):
    return {
        'codigo': f'{codigo_prefix}_{grado_letter}_000{suffix}',
        'denominacion': f'Denominació {suffix}',
        'familia': 'Actividades Físicas y Deportivas',
        'nivel': None,
        'plan_antiguo': False,
        'observaciones': '',
    }


# ---------------------------------------------------------------------------
# Patch paths
# ---------------------------------------------------------------------------

PATCH_REQUESTS_GET = 'scrapers.pipeline.requests.get'
PATCH_OS_UNLINK = 'scrapers.pipeline.os.unlink'
PATCH_OS_REPLACE = 'scrapers.pipeline.os.replace'
PATCH_OS_PATH_EXISTS = 'scrapers.pipeline.os.path.exists'
PATCH_PARSE_A = 'scrapers.pipeline.parse_grado_a'
PATCH_PARSE_B = 'scrapers.pipeline.parse_grado_b'
PATCH_PARSE_C = 'scrapers.pipeline.parse_grado_c'
PATCH_TEMPFILE_NTF = 'scrapers.pipeline.tempfile.NamedTemporaryFile'
PATCH_PARSE_D_BASICO   = 'scrapers.pipeline.parse_grado_d_basico'
PATCH_PARSE_D_MEDIO    = 'scrapers.pipeline.parse_grado_d_medio'
PATCH_PARSE_D_SUPERIOR = 'scrapers.pipeline.parse_grado_d_superior'
PATCH_PARSE_E          = 'scrapers.pipeline.parse_grado_e'


# ---------------------------------------------------------------------------
# Test 1: pipeline.run() retorna el schema correcte
# ---------------------------------------------------------------------------

def test_pipeline_run_returns_correct_schema(tmp_path):
    """pipeline.run() retorna dict amb 'total', 'by_grado', 'errors', 'duration_seconds'."""
    records_a = [_make_record('01', grado_letter='A')]
    records_b = [_make_record('01', grado_letter='B'), _make_record('02', grado_letter='B')]
    records_c = [_make_record('01', grado_letter='C')]

    fake_pdf_content = b'%PDF-1.4 fake content'
    mock_response = mock.Mock()
    mock_response.content = fake_pdf_content
    mock_response.raise_for_status = mock.Mock()

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response) as mock_get, \
         mock.patch(PATCH_PARSE_A, return_value=records_a) as mock_a, \
         mock.patch(PATCH_PARSE_B, return_value=records_b) as mock_b, \
         mock.patch(PATCH_PARSE_C, return_value=records_c) as mock_c, \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch(PATCH_OS_REPLACE, side_effect=lambda src, dst: None):

        import scrapers.pipeline as pipeline_mod

        # Escriure un fitxer temporal fals per a _write_atomic
        with mock.patch('scrapers.pipeline.tempfile.NamedTemporaryFile') as mock_ntf:
            tmp_file = tmp_path / 'tmp.json'
            mock_context = mock.MagicMock()
            mock_context.__enter__ = mock.Mock(return_value=mock_context)
            mock_context.__exit__ = mock.Mock(return_value=False)
            mock_context.name = str(tmp_file)
            mock_context.write = mock.Mock()
            mock_ntf.return_value = mock_context

            result = pipeline_mod.run()

    assert 'total' in result
    assert 'by_grado' in result
    assert 'errors' in result
    assert 'duration_seconds' in result
    assert result['errors'] == []
    assert set(result['by_grado'].keys()) == {'A', 'B', 'C', 'D', 'E'}
    # D i E valen 0 (mocks retornen []); el total A+B+C ha de coincidir amb result['total']
    assert result['by_grado']['D'] == 0
    assert result['by_grado']['E'] == 0
    assert result['total'] == sum(result['by_grado'].values())


# ---------------------------------------------------------------------------
# Test 2: pipeline afegeix 'id' i 'grado' als registres
# ---------------------------------------------------------------------------

def test_pipeline_adds_id_and_grado(tmp_path):
    """Els registres escrits a ofertes.json han de tenir camp 'grado' i 'id' seqüencial (1-based)."""
    record_a = _make_record('01', grado_letter='A')
    record_b = _make_record('01', grado_letter='B')

    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    written_data = []

    def fake_json_dump(data, f, **kwargs):
        written_data.extend(data)

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response), \
         mock.patch(PATCH_PARSE_A, return_value=[record_a]), \
         mock.patch(PATCH_PARSE_B, return_value=[record_b]), \
         mock.patch(PATCH_PARSE_C, return_value=[]), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch('scrapers.pipeline.json.dump', side_effect=fake_json_dump), \
         mock.patch('scrapers.pipeline.tempfile.NamedTemporaryFile') as mock_ntf, \
         mock.patch(PATCH_OS_REPLACE):

        tmp_file = tmp_path / 'tmp.json'
        mock_context = mock.MagicMock()
        mock_context.__enter__ = mock.Mock(return_value=mock_context)
        mock_context.__exit__ = mock.Mock(return_value=False)
        mock_context.name = str(tmp_file)
        mock_ntf.return_value = mock_context

        import scrapers.pipeline as pipeline_mod
        pipeline_mod.run()

    assert len(written_data) == 2
    # Verificar que s'afegeix 'grado' correctament
    grado_a_rec = next(r for r in written_data if r.get('grado') == 'A')
    grado_b_rec = next(r for r in written_data if r.get('grado') == 'B')
    assert grado_a_rec is not None
    assert grado_b_rec is not None
    # IDs comencen en 1 i son seqüencials
    ids = sorted(r['id'] for r in written_data)
    assert ids == list(range(1, len(written_data) + 1))


# ---------------------------------------------------------------------------
# Test 3: fail fast en error de descàrrega
# ---------------------------------------------------------------------------

def test_pipeline_fail_fast_on_download_error(tmp_path):
    """Si requests.get falla per al Grado B, l'excepció es propaga i os.replace NO es crida."""
    import requests as req_lib

    mock_response_ok = mock.Mock()
    mock_response_ok.content = b'%PDF fake'
    mock_response_ok.raise_for_status = mock.Mock()

    mock_response_fail = mock.Mock()
    mock_response_fail.raise_for_status = mock.Mock(
        side_effect=req_lib.exceptions.HTTPError("403 Forbidden")
    )
    mock_response_fail.content = b''

    # Primera crida (A) ok, segona (B) falla
    mock_get = mock.Mock(side_effect=[mock_response_ok, mock_response_fail])

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, mock_get), \
         mock.patch(PATCH_PARSE_A, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)) as _, \
         mock.patch(PATCH_OS_REPLACE) as mock_replace:

        import scrapers.pipeline as pipeline_mod

        with pytest.raises(req_lib.exceptions.HTTPError):
            pipeline_mod.run()

        # ofertes.json NO s'ha d'escriure (os.replace no cridat)
        mock_replace.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: os.unlink cridat 3 cops en cas d'èxit
# ---------------------------------------------------------------------------

def test_pipeline_deletes_pdf_on_success(tmp_path):
    """Quan el pipeline acaba amb èxit, os.unlink s'ha de cridar exactament 3 cops."""
    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response), \
         mock.patch(PATCH_PARSE_A, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_B, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_C, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch('scrapers.pipeline.json.dump'), \
         mock.patch('scrapers.pipeline.tempfile.NamedTemporaryFile') as mock_ntf, \
         mock.patch(PATCH_OS_REPLACE), \
         mock.patch(PATCH_OS_UNLINK) as mock_unlink:

        tmp_file = tmp_path / 'tmp.json'
        mock_context = mock.MagicMock()
        mock_context.__enter__ = mock.Mock(return_value=mock_context)
        mock_context.__exit__ = mock.Mock(return_value=False)
        mock_context.name = str(tmp_file)
        mock_ntf.return_value = mock_context

        import scrapers.pipeline as pipeline_mod

        # Capturar paths usats als tempfiles
        unlink_paths = []
        mock_unlink.side_effect = lambda p: unlink_paths.append(p)

        pipeline_mod.run()

    assert mock_unlink.call_count == 3


# ---------------------------------------------------------------------------
# Test 5: os.unlink cridat fins i tot si parse_grado_b falla
# ---------------------------------------------------------------------------

def test_pipeline_deletes_pdf_on_error(tmp_path):
    """Si parse_grado_b falla, os.unlink s'ha de cridar igualment per al PDF de Grado B (finally block)."""
    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response), \
         mock.patch(PATCH_PARSE_A, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_B, side_effect=Exception("Parse error")), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch(PATCH_OS_UNLINK) as mock_unlink, \
         mock.patch(PATCH_OS_REPLACE):

        import scrapers.pipeline as pipeline_mod

        with pytest.raises(Exception, match="Parse error"):
            pipeline_mod.run()

    # os.unlink s'ha d'haver cridat almenys 2 cops: Grado A ok + Grado B (finally)
    assert mock_unlink.call_count >= 2


# ---------------------------------------------------------------------------
# Test 6: escriptura atòmica (os.replace cridat)
# ---------------------------------------------------------------------------

def test_pipeline_atomic_write(tmp_path):
    """Quan el pipeline acaba amb èxit, os.replace s'ha de cridar (escriptura atòmica)."""
    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response), \
         mock.patch(PATCH_PARSE_A, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_B, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_C, return_value=[_make_record()]), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch('scrapers.pipeline.json.dump'), \
         mock.patch('scrapers.pipeline.tempfile.NamedTemporaryFile') as mock_ntf, \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_REPLACE) as mock_replace:

        tmp_file = tmp_path / 'tmp.json'
        mock_context = mock.MagicMock()
        mock_context.__enter__ = mock.Mock(return_value=mock_context)
        mock_context.__exit__ = mock.Mock(return_value=False)
        mock_context.name = str(tmp_file)
        mock_ntf.return_value = mock_context

        import scrapers.pipeline as pipeline_mod
        pipeline_mod.run()

    # os.replace ha de ser cridat exactament 1 cop per escriure ofertes.json
    mock_replace.assert_called_once()
    # El segon argument ha de ser el path de DATA_PATH (el fitxer final)
    _, dst = mock_replace.call_args[0]
    assert dst == str(output_file)


# ---------------------------------------------------------------------------
# Test 7: headers correctes a les peticions HTTP
# ---------------------------------------------------------------------------

def test_pipeline_headers_used(tmp_path):
    """requests.get ha de ser cridat amb els headers User-Agent i Referer correctes."""
    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response) as mock_get, \
         mock.patch(PATCH_PARSE_A, return_value=[]), \
         mock.patch(PATCH_PARSE_B, return_value=[]), \
         mock.patch(PATCH_PARSE_C, return_value=[]), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch('scrapers.pipeline.json.dump'), \
         mock.patch('scrapers.pipeline.tempfile.NamedTemporaryFile') as mock_ntf, \
         mock.patch(PATCH_OS_REPLACE):

        tmp_file = tmp_path / 'tmp.json'
        mock_context = mock.MagicMock()
        mock_context.__enter__ = mock.Mock(return_value=mock_context)
        mock_context.__exit__ = mock.Mock(return_value=False)
        mock_context.name = str(tmp_file)
        mock_ntf.return_value = mock_context

        import scrapers.pipeline as pipeline_mod
        pipeline_mod.run()

    # Verificar que totes les crides a requests.get inclouen els headers correctes
    assert mock_get.call_count == 3
    for call in mock_get.call_args_list:
        headers = call[1].get('headers') or (call[0][1] if len(call[0]) > 1 else None)
        assert headers is not None, "headers hauria de ser passat com a kwarg"
        assert 'User-Agent' in headers
        assert 'Mozilla/5.0' in headers['User-Agent']
        assert 'Referer' in headers
        assert 'todofp.es' in headers['Referer']


# ---------------------------------------------------------------------------
# Test 8: pipeline inclou D/E i manté l'ordre d'IDs A→B→C→D→E
# ---------------------------------------------------------------------------

def test_pipeline_id_order_a_b_c_d_e(tmp_path):
    """Els IDs assignats segueixen l'ordre A, B, C, D, E (D-03)."""
    record_a = _make_record('01', grado_letter='A')
    record_b = _make_record('02', grado_letter='B')
    record_c = _make_record('03', grado_letter='C')
    # Registres D/E simulats (schema de html_scraper — sense 'grado' encara)
    record_d_basico = {'denominacion': 'D-Basico', 'familia': 'X', 'nivel': 1,
                       'codigo': None, 'plan_antiguo': False, 'observaciones': ''}
    record_d_medio = {'denominacion': 'D-Medio', 'familia': 'X', 'nivel': 2,
                      'codigo': None, 'plan_antiguo': False, 'observaciones': ''}
    record_d_superior = {'denominacion': 'D-Superior', 'familia': 'X', 'nivel': 3,
                         'codigo': None, 'plan_antiguo': False, 'observaciones': ''}
    record_e = {'denominacion': 'E-Curso', 'familia': 'X', 'nivel': None,
                'codigo': None, 'plan_antiguo': False, 'observaciones': ''}

    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    written_data = []
    def fake_json_dump(data, f, **kwargs):
        written_data.extend(data)

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response), \
         mock.patch(PATCH_PARSE_A, return_value=[record_a]), \
         mock.patch(PATCH_PARSE_B, return_value=[record_b]), \
         mock.patch(PATCH_PARSE_C, return_value=[record_c]), \
         mock.patch(PATCH_PARSE_D_BASICO, return_value=[record_d_basico]), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[record_d_medio]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[record_d_superior]), \
         mock.patch(PATCH_PARSE_E, return_value=[record_e]), \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch('scrapers.pipeline.json.dump', side_effect=fake_json_dump), \
         mock.patch('scrapers.pipeline.tempfile.NamedTemporaryFile') as mock_ntf, \
         mock.patch(PATCH_OS_REPLACE):

        tmp_file = tmp_path / 'tmp.json'
        mock_context = mock.MagicMock()
        mock_context.__enter__ = mock.Mock(return_value=mock_context)
        mock_context.__exit__ = mock.Mock(return_value=False)
        mock_context.name = str(tmp_file)
        mock_ntf.return_value = mock_context

        import scrapers.pipeline as pipeline_mod
        result = pipeline_mod.run()

    assert len(written_data) == 7  # A + B + C + 3*D + E
    # Ordre: 3 primers A/B/C (PDF), 4 ultims D/D/D/E (HTML)
    assert written_data[0]['grado'] == 'A' and written_data[0]['id'] == 1
    assert written_data[1]['grado'] == 'B' and written_data[1]['id'] == 2
    assert written_data[2]['grado'] == 'C' and written_data[2]['id'] == 3
    assert written_data[3]['grado'] == 'D' and written_data[3]['id'] == 4
    assert written_data[4]['grado'] == 'D' and written_data[4]['id'] == 5
    assert written_data[5]['grado'] == 'D' and written_data[5]['id'] == 6
    assert written_data[6]['grado'] == 'E' and written_data[6]['id'] == 7
    assert result['by_grado'] == {'A': 1, 'B': 1, 'C': 1, 'D': 3, 'E': 1}


# ---------------------------------------------------------------------------
# Test 9: fail fast si una URL HTML falla — ofertes.json NO s'escriu
# ---------------------------------------------------------------------------

def test_pipeline_fail_fast_on_html_error(tmp_path):
    """Si parse_grado_d_basico llanca excepcio, os.replace NO es crida (D-01, D-02)."""
    mock_response = mock.Mock()
    mock_response.content = b'%PDF fake'
    mock_response.raise_for_status = mock.Mock()

    output_file = tmp_path / 'ofertes.json'

    with mock.patch(PATCH_REQUESTS_GET, return_value=mock_response), \
         mock.patch(PATCH_PARSE_A, return_value=[_make_record('01', grado_letter='A')]), \
         mock.patch(PATCH_PARSE_B, return_value=[_make_record('01', grado_letter='B')]), \
         mock.patch(PATCH_PARSE_C, return_value=[_make_record('01', grado_letter='C')]), \
         mock.patch(PATCH_PARSE_D_BASICO, side_effect=Exception("HTML parse error")), \
         mock.patch(PATCH_PARSE_D_MEDIO, return_value=[]), \
         mock.patch(PATCH_PARSE_D_SUPERIOR, return_value=[]), \
         mock.patch(PATCH_PARSE_E, return_value=[]), \
         mock.patch(PATCH_OS_UNLINK), \
         mock.patch(PATCH_OS_PATH_EXISTS, return_value=True), \
         mock.patch('scrapers.pipeline.DATA_PATH', str(output_file)), \
         mock.patch(PATCH_OS_REPLACE) as mock_replace:

        import scrapers.pipeline as pipeline_mod

        with pytest.raises(Exception, match="HTML parse error"):
            pipeline_mod.run()

        mock_replace.assert_not_called()
