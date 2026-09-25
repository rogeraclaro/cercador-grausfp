"""test_ext_refresh.py — Snapshot ext_cursos.json + pipeline (Pla 062). Sense xarxa."""
import json
from unittest.mock import patch

import pytest

from scrapers import ext_cursos, pipeline


@pytest.fixture(autouse=True)
def _sense_cecot_ni_ccoo():
    with patch('scrapers.cecot_scraper.build_cecot_cursos', return_value=[{'idCurs': 'CECOT:0', 'font': 'cecot'}]), \
         patch('scrapers.ccoo_scraper.build_ccoo_cursos', return_value=[{'idCurs': 'CCOO:0', 'font': 'ccoo'}]):
        yield


def _c(font, n):
    return {'idCurs': f'{font.upper()}:{n}', 'font': font}


def _ids(tmp_path):
    return sorted(c['idCurs'] for c in json.loads((tmp_path / 'ext_cursos.json').read_text()))


def _hist(tmp_path):
    return json.loads((tmp_path / 'soc_refresh_history.json').read_text())


def test_is_plausible():
    assert ext_cursos.is_plausible([], [_c('pimec', 'a')]) is True
    assert ext_cursos.is_plausible([], []) is False
    assert ext_cursos.is_plausible([1, 2, 3, 4], [1, 2]) is True      # exactament la meitat
    assert ext_cursos.is_plausible([1, 2, 3, 4], [1]) is False


def test_diff_entry_conserva_font_soc_per_defecte():
    assert pipeline._soc_diff_entry([], [], ok=True)['font'] == 'soc'
    assert pipeline._soc_diff_entry([], [], ok=True, font='pimec')['font'] == 'pimec'


def test_refresh_ok_escriu_les_quatre_fonts(tmp_path):
    with patch('scrapers.pimec_scraper.build_pimec_cursos',
               return_value=[_c('pimec', 'a'), _c('pimec', 'b')]), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[_c('foment', 'x')]), \
         patch('scrapers.cecot_scraper.build_cecot_cursos', return_value=[_c('cecot', 'c')]), \
         patch('scrapers.ccoo_scraper.build_ccoo_cursos', return_value=[_c('ccoo', 'd')]):
        res = pipeline.refresh_ext_cursos(str(tmp_path))
    assert res == {'pimec': 2, 'foment': 1, 'cecot': 1, 'ccoo': 1}
    assert _ids(tmp_path) == ['CCOO:d', 'CECOT:c', 'FOMENT:x', 'PIMEC:a', 'PIMEC:b']
    assert {(h['font'], h['ok'], h['n_cursos']) for h in _hist(tmp_path)} == {
        ('pimec', True, 2), ('foment', True, 1), ('cecot', True, 1), ('ccoo', True, 1)}


def test_font_que_falla_conserva_l_anterior_i_avisa(tmp_path):
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(
        [_c('pimec', 'a'), _c('pimec', 'b'), _c('foment', 'x')]))
    with patch('scrapers.pimec_scraper.build_pimec_cursos', side_effect=RuntimeError('boom')), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[_c('foment', 'y')]), \
         patch('scrapers.pipeline._notify_admin_soc_failure') as notify:
        pipeline.refresh_ext_cursos(str(tmp_path))
    assert _ids(tmp_path) == ['CCOO:0', 'CECOT:0', 'FOMENT:y', 'PIMEC:a', 'PIMEC:b']
    assert notify.call_count == 1 and notify.call_args.kwargs['source'] == 'PIMEC'
    assert any(h['font'] == 'pimec' and h['ok'] is False and 'boom' in h['error']
               for h in _hist(tmp_path))


def test_no_sobreescriu_si_baixa_a_menys_de_la_meitat(tmp_path):
    prev = [_c('pimec', str(i)) for i in range(4)]
    (tmp_path / 'ext_cursos.json').write_text(json.dumps(prev))
    with patch('scrapers.pimec_scraper.build_pimec_cursos', return_value=[_c('pimec', '0')]), \
         patch('scrapers.foment_scraper.build_foment_cursos', return_value=[]), \
         patch('scrapers.pipeline._notify_admin_soc_failure') as notify:
        pipeline.refresh_ext_cursos(str(tmp_path))
    assert len(_ids(tmp_path)) == 6                 # PIMEC intacte (4) + Cecot i CCOO (1 cadascun); Foment buit sense prèvia
    assert notify.call_count == 2                   # PIMEC (caiguda) + Foment (0 cursos)


def test_avis_admin_usa_font_i_fitxer_propis(tmp_path):
    with patch('email_service.send_email') as send:
        pipeline._notify_admin_soc_failure(
            str(tmp_path), RuntimeError('x'), source='PIMEC', stamp_name='last_pimec_alert.json')
    assert 'PIMEC' in send.call_args.args[1]
    assert (tmp_path / 'last_pimec_alert.json').exists()
    assert not (tmp_path / 'last_soc_alert.json').exists()
