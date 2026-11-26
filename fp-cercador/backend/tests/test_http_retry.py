"""test_http_retry.py — Pla 095: reintents de xarxa de les fases fatals del refresc."""
import unittest.mock as mock

import pytest
import requests

from scrapers import http_retry


@pytest.fixture(autouse=True)
def no_wait(monkeypatch):
    sleeps = []
    monkeypatch.setattr(http_retry.time, "sleep", sleeps.append)
    return sleeps


def _resp(status):
    resp = mock.Mock()
    resp.status_code = status
    return resp


def test_reintenta_connection_error_i_retorna_la_resposta(no_wait):
    ok = _resp(200)
    get = mock.Mock(side_effect=[requests.ConnectionError("reset"), requests.Timeout("lent"), ok])
    assert http_retry.get_with_retry(get, "https://x", timeout=30) is ok
    assert get.call_count == 3
    get.assert_called_with("https://x", timeout=30)
    assert no_wait == [10, 30]


def test_no_reintenta_un_404():
    not_found = _resp(404)
    get = mock.Mock(return_value=not_found)
    assert http_retry.get_with_retry(get, "https://x") is not_found
    assert get.call_count == 1


def test_no_reintenta_altres_excepcions():
    get = mock.Mock(side_effect=ValueError("parseig"))
    with pytest.raises(ValueError):
        http_retry.get_with_retry(get, "https://x")
    assert get.call_count == 1


def test_respecta_el_maxim_i_propaga_l_error(no_wait):
    get = mock.Mock(side_effect=requests.ConnectionError("reset"))
    with pytest.raises(requests.ConnectionError):
        http_retry.get_with_retry(get, "https://x")
    assert get.call_count == 1 + len(http_retry.RETRY_DELAYS)
    assert no_wait == list(http_retry.RETRY_DELAYS) == [10, 30, 90]


def test_un_5xx_es_reintenta_i_l_ultim_es_retorna_per_a_raise_for_status():
    get = mock.Mock(return_value=_resp(503))
    resp = http_retry.get_with_retry(get, "https://x", delays=(0, 0))
    assert resp.status_code == 503
    assert get.call_count == 3


def test_resposta_sense_status_code_enter_no_peta():
    """Els tests dels scrapers fan servir mock.Mock() sense status_code."""
    resp = mock.Mock()
    get = mock.Mock(return_value=resp)
    assert http_retry.get_with_retry(get, "https://x") is resp
    assert get.call_count == 1


def test_buscador_scraper_uses_retry_without_network(monkeypatch):
    """Les fases fatals criden get_with_retry de debò (un import oblidat només petava en producció)."""
    import requests
    from scrapers import buscador_scraper, http_retry

    monkeypatch.setattr(http_retry, "RETRY_DELAYS", (0, 0, 0))
    calls = {"n": 0}

    class FakeResp:
        status_code = 200
        text = "[]"
        headers = {"Content-Type": "application/json"}

        def raise_for_status(self):
            pass

        def json(self):
            return []

    class FakeSession:
        def __init__(self):
            self.headers = {}
            self.cookies = {"JSESSIONID": "x"}

        def get(self, url, timeout=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise requests.ConnectionError("reset by peer")
            return FakeResp()

    monkeypatch.setattr(buscador_scraper.requests, "Session", FakeSession)
    session = buscador_scraper._bootstrap_session()
    assert calls["n"] == 2          # el primer tall es reintenta
    assert isinstance(session, FakeSession)
