"""
test_site_url.py — les adreces públiques (feed, correu de novetats) surten de SITE_URL,
perquè el canvi de domini sigui només canviar la variable d'entorn.
"""
import pytest

import app as app_module
import notifier
from app import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "SITE_URL", "https://grausfp.example")
    with app.test_client() as c:
        yield c


def test_feed_rss_i_json_usen_site_url(client):
    assert "<link>https://grausfp.example</link>" in client.get("/api/feed.rss").get_data(as_text=True)
    assert client.get("/api/feed.json").get_json()["home_page_url"] == "https://grausfp.example"


def test_correu_de_novetats_enllaca_a_site_url():
    html = notifier._build_html([], "https://grausfp.example")
    assert "href='https://grausfp.example'" in html
    assert "masellas" not in html
