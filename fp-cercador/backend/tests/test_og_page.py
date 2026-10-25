"""
test_og_page.py — /api/og-page/<pàgina>: la pàgina pública amb les metadades
de previsualització (og:*) en castellà, per als enllaços compartits amb ?lang=es.

nginx hi reescriu /<pàgina>.html?lang=es; la resta de peticions les serveix estàtiques.
"""
import pytest

from app import app

PAGES = ["index", "itinerari", "per-que-grausfp", "fonts", "observatori", "historial"]


@pytest.fixture
def client():
    with app.test_client() as c:
        yield c


@pytest.mark.parametrize("page", PAGES)
def test_pagina_publica_porta_la_imatge_en_castella(client, page):
    resp = client.get(f"/api/og-page/{page}")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"
    html = resp.get_data(as_text=True)
    assert 'content="https://grausfp.masellas.info/og-image-es.png"' in html
    assert "og-image.png" not in html
    assert '<html lang="es">' in html


def test_itinerari_porta_titol_i_descripcio_en_castella(client):
    html = client.get("/api/og-page/itinerari").get_data(as_text=True)
    assert '<meta property="og:title" content="Itinerario formativo — GrausFP">' in html
    assert "De qué grados está formada" in html
    assert "format un ensenyament" not in html  # metadades; el cos el tradueix i18n.js


@pytest.mark.parametrize("name", ["admin", "perfil", "..%2Fapp", "index.html", "x"])
def test_pagines_fora_de_la_llista_donen_404(client, name):
    assert client.get(f"/api/og-page/{name}").status_code == 404
