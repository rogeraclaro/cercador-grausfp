"""Plan 094: documented corrections to the hours the todofp certificate search gets wrong."""
import json
import os
import re

from scrapers.certificados_scraper import corrected_hours, enrich_record, load_hours_overrides

_BACKEND = os.path.join(os.path.dirname(__file__), '..')
OVERRIDES = {'EOCE0109': {'buscador': 780, 'h': 600, 'motiu': 'transversal', 'norma': 'RD 644/2011'}}


def test_known_wrong_value_is_corrected():
    assert corrected_hours('EOCE0109', 780, OVERRIDES) == 600


def test_certificate_without_override_keeps_its_hours():
    assert corrected_hours('ELEE0109', 920, OVERRIDES) == 920
    assert corrected_hours('ELEE0109', None, OVERRIDES) is None


def test_override_stops_applying_when_the_source_changes(caplog):
    # The ministry fixed it, or changed it to something else: the source wins and the log says so.
    assert corrected_hours('EOCE0109', 600, OVERRIDES) == 600
    assert not caplog.records
    assert corrected_hours('EOCE0109', 650, OVERRIDES) == 650
    assert 'EOCE0109' in caplog.text


def test_enrich_record_applies_the_real_table():
    record = {'codigo': 'IMSV0408', 'nivel': 3}
    assert enrich_record(record, {'cert_id': 166, 'duracion_horas': 630})['duracion_horas'] == 440


def test_every_override_is_documented_on_the_sources_page():
    overrides = load_hours_overrides()
    assert len(overrides) == 20
    with open(os.path.join(_BACKEND, '..', 'frontend', 'fonts.html'), encoding='utf-8') as f:
        page = re.sub(r'\s+', ' ', f.read())
    for codigo, o in overrides.items():
        row = re.search(rf'<tr>\s*<td><code>{codigo}</code>.*?</tr>', page)
        assert row, f'{codigo} is missing from fonts.html'
        assert f'<td>{o["buscador"]} h</td> <td>{o["h"]} h</td>' in row.group(0), codigo
        assert f'fonts.err.m.{o["motiu"]}' in row.group(0) and o['norma'] in row.group(0), codigo
