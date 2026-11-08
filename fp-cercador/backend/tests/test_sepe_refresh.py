"""test_sepe_refresh.py — Refresc setmanal del catàleg SEPE al pipeline (Pla 081). Sense xarxa."""
import os
import time
from unittest.mock import patch

from scrapers import pipeline
from scrapers.sepe_scraper import SepeDataError

ROWS = [{'codi': 'AAAA0001'}, {'codi': 'AAAA0002'}]


def _touch_sepe(tmp_path, age_days: float):
    path = tmp_path / 'sepe_especs.json'
    path.write_text('[{"codi": "OLD"}]')
    old = time.time() - age_days * 86400
    os.utime(path, (old, old))
    return path


def test_fresh_file_skips_network(tmp_path):
    _touch_sepe(tmp_path, 0)
    with patch('scrapers.sepe_scraper.build_sepe_data') as build, \
         patch('scrapers.sepe_scraper.write_sepe_data') as write:
        assert pipeline.refresh_sepe_especs(str(tmp_path)) is None
    build.assert_not_called()
    write.assert_not_called()


def test_missing_file_refreshes(tmp_path):
    with patch('scrapers.sepe_scraper.build_sepe_data', return_value=ROWS) as build, \
         patch('scrapers.sepe_scraper.write_sepe_data') as write:
        assert pipeline.refresh_sepe_especs(str(tmp_path)) == 2
    build.assert_called_once()
    write.assert_called_once_with(ROWS, str(tmp_path))


def test_stale_file_refreshes(tmp_path):
    _touch_sepe(tmp_path, 8)
    with patch('scrapers.sepe_scraper.build_sepe_data', return_value=ROWS) as build, \
         patch('scrapers.sepe_scraper.write_sepe_data') as write:
        assert pipeline.refresh_sepe_especs(str(tmp_path)) == 2
    build.assert_called_once()
    write.assert_called_once_with(ROWS, str(tmp_path))


def test_failure_is_non_fatal_keeps_file_and_alerts(tmp_path):
    path = _touch_sepe(tmp_path, 8)
    with patch('scrapers.sepe_scraper.build_sepe_data', side_effect=SepeDataError('boom')), \
         patch('scrapers.sepe_scraper.write_sepe_data') as write, \
         patch('scrapers.pipeline._notify_admin_soc_failure') as notify:
        assert pipeline.refresh_sepe_especs(str(tmp_path)) is None
    write.assert_not_called()
    assert path.read_text() == '[{"codi": "OLD"}]'
    notify.assert_called_once()
    args, kwargs = notify.call_args
    assert args[0] == str(tmp_path)
    assert isinstance(args[1], SepeDataError)
    assert kwargs == {'source': 'SEPE', 'stamp_name': 'last_sepe_alert.json'}


def test_write_failure_is_also_non_fatal(tmp_path):
    with patch('scrapers.sepe_scraper.build_sepe_data', return_value=ROWS), \
         patch('scrapers.sepe_scraper.write_sepe_data', side_effect=OSError('disk')), \
         patch('scrapers.pipeline._notify_admin_soc_failure') as notify:
        assert pipeline.refresh_sepe_especs(str(tmp_path)) is None
    notify.assert_called_once()
