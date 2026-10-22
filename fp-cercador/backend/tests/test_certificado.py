"""
test_certificado.py — /api/certificado/<codigo> només retorna url_boe https de boe.es.

Sense xarxa: requests.Session de app està mockejat i ofertes.json és un fitxer temporal.
"""
import json
import unittest.mock as mock

import pytest

from app import app

CODIGO = "ADGD0108"


def _fichacp_html(href):
    return f'<html><body><a class="enlace-ficha-boe" href="{href}">BOE</a></body></html>'


@pytest.fixture
def client(tmp_path, monkeypatch):
    data = tmp_path / "ofertes.json"
    data.write_text(json.dumps([
        {"codigo": CODIGO, "plan_antiguo": True, "cert_id_buscador": 123},
    ]), encoding="utf-8")
    monkeypatch.setattr("app.DATA_PATH", str(data))
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _get_url_boe(client, href):
    session = mock.MagicMock()
    session.post.return_value.text = _fichacp_html(href)
    with mock.patch("app.requests.Session", return_value=session):
        resp = client.get(f"/api/certificado/{CODIGO}")
    assert resp.status_code == 200
    return resp.get_json()["url_boe"]


@pytest.mark.parametrize("href", [
    "https://www.boe.es/buscar/doc.php?id=BOE-A-2008-1234",
    "https://boe.es/diario_boe/txt.php?id=BOE-A-2011-1",
    "http://www.boe.es/buscar/doc.php",
])
def test_url_boe_valida_es_retorna(client, href):
    assert _get_url_boe(client, href) == href


@pytest.mark.parametrize("href", [
    "javascript:alert(document.domain)//boe.es",
    "https://evil.example/?boe.es",
    "https://boe.es.evil.example/doc",
    "https://boe.es@evil.example/doc",
    "data:text/html,boe.es",
])
def test_url_boe_no_https_boe_es_es_descarta(client, href):
    assert _get_url_boe(client, href) is None
