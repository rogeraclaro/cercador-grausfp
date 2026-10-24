"""
test_ce_acces_scraper.py — Requisits d'accés dels cursos d'especialització (E):
quins títols D hi donen accés (Pla 074).

Sense xarxa: _fetch_with_retry i time.sleep mockejats.
"""
import pytest

from scrapers import ce_acces_scraper as ces

# La llista del 20% ("Si no tienes dicha titulación…") ve sempre després i s'ha d'excloure.
_VIA_20 = """
<ul>
	<li>Si no tienes dicha titulaci&oacute;n, pero hay disponibilidad de plazas (hasta un m&aacute;ximo del 20 % de las plazas), puedes acceder si:
	<ul>
		<li>1&ordm; Si tienes un t&iacute;tulo de T&eacute;cnico Superior diferente.</li>
	</ul>
	</li>
</ul>
"""


def _page(cte: str) -> str:
    return f"""<html><body><div class="listado-dsp">
<div class="cdsp">
	<h2>Requisitos de acceso<span class="cruz"></span></h2>
	<div class="desplegable"><div class="cte"><p>{cte}</p></div></div>
</div>
<div class="cdsp">
	<h2>Salidas profesionales<span class="cruz"></span></h2>
	<div class="desplegable"><div class="cte"><ul><li>Operadores de venta.</li></ul></div></div>
</div>
</div></body></html>"""


HTML_ENLLACOS = _page("""
<ul>
	<li class="ta-justify"><a href="/que-estudiar/familias-profesionales/informatica-comunicaciones/admin-sist-informaticos-red.html">T&iacute;tulo de T&eacute;cnico Superior en Administraci&oacute;n de Sistemas Inform&aacute;ticos en Red.</a></li>
	<li class="ta-justify"><a href="/que-estudiar/familias-profesionales/informatica-comunicaciones/des-aplicaciones-web.html">T&iacute;tulo de T&eacute;cnico Superior en Desarrollo de Aplicaciones Web.</a></li>
</ul>
""" + _VIA_20)

HTML_SENSE_ENLLACOS = _page("""
<p><strong>Los t&iacute;tulos que dan acceso a este Curso de Especializaci&oacute;n son los siguientes:</strong></p>
<ul>
	<li>T&eacute;cnico Superior en Vitivinicultura.</li>
	<li>T&iacute;tulo de: T&eacute;cnico Superior en Marketing y Publicidad, establecido en el Real Decreto 1571/2011, de 4 de noviembre.</li>
	<li>T&eacute;cnico Superior en Un T&iacute;tulo Antic Inexistent.</li>
</ul>
""" + _VIA_20)

HTML_PROSA = _page("""
<p>El t&iacute;tulo que da acceso a este curso de especializaci&oacute;n es el de T&eacute;cnico en Jardiner&iacute;a y florister&iacute;a.</p>
""")

T = 'https://www.todofp.es/que-estudiar/familias-profesionales'
URL_ASIR = f'{T}/informatica-comunicaciones/admin-sist-informaticos-red.html'
URL_DAW = f'{T}/informatica-comunicaciones/des-aplicaciones-web.html'
URL_JARDI = f'{T}/agraria/jardineria-floristeria.html'
URL_E_CIBER = f'{T}/informatica-comunicaciones/ce-ciberseguridad.html'
URL_E_COMERC = f'{T}/comercio-marketing/ce-comercio-electronico.html'
URL_E_FLOR = f'{T}/agraria/ce-floristeria-arte-floral.html'


# --- parse_requisitos -------------------------------------------------------

def test_parse_llista_amb_enllacos_exclou_via_20():
    assert ces.parse_requisitos(HTML_ENLLACOS) == [
        {'text': 'Título de Técnico Superior en Administración de Sistemas Informáticos en Red.',
         'href': '/que-estudiar/familias-profesionales/informatica-comunicaciones/admin-sist-informaticos-red.html'},
        {'text': 'Título de Técnico Superior en Desarrollo de Aplicaciones Web.',
         'href': '/que-estudiar/familias-profesionales/informatica-comunicaciones/des-aplicaciones-web.html'},
    ]


def test_parse_llista_sense_enllacos_exclou_via_20():
    assert ces.parse_requisitos(HTML_SENSE_ENLLACOS) == [
        {'text': 'Técnico Superior en Vitivinicultura.', 'href': None},
        {'text': 'Título de: Técnico Superior en Marketing y Publicidad, establecido en el '
                 'Real Decreto 1571/2011, de 4 de noviembre.', 'href': None},
        {'text': 'Técnico Superior en Un Título Antic Inexistent.', 'href': None},
    ]


def test_parse_prosa_retorna_el_paragraf_sense_href():
    assert ces.parse_requisitos(HTML_PROSA) == [
        {'text': 'El título que da acceso a este curso de especialización es el de '
                 'Técnico en Jardinería y floristería.', 'href': None},
    ]


def test_parse_sense_seccio_retorna_none():
    assert ces.parse_requisitos('<html><body><div class="cdsp"><h2>Salidas</h2></div></body></html>') is None


def test_normalize_title():
    assert ces.normalize_title('Título de: Técnico Superior en Marketing y Publicidad, establecido '
                               'en el Real Decreto 1571/2011, de 4 de noviembre.') == \
        ces.normalize_title('Técnico Superior en  MARKETING y publicidad')
    assert ces.normalize_title('Título de Técnico en Jardinería y floristería.') == \
        'tecnico en jardineria y floristeria'


# --- resolve ----------------------------------------------------------------

def _rec(id_, grado, denominacion, ficha_url):
    return {'id': id_, 'grado': grado, 'denominacion': denominacion, 'ficha_url': ficha_url,
            'codigo': None, 'familia': 'F', 'nivel': 3}


D_RECS = [
    # Esquema/barra diferents dels href relatius de la pàgina: ha de lligar igualment.
    _rec(101, 'D', 'Técnico Superior en Administración de Sistemas Informáticos en Red',
         URL_ASIR.replace('https://www.', 'http://') + '/'),
    _rec(102, 'D', 'Técnico Superior en Desarrollo de Aplicaciones Web', URL_DAW),
    _rec(103, 'D', 'Técnico Superior en Vitivinicultura', f'{T}/agraria/vitivinicultura.html'),
    _rec(104, 'D', 'Técnico Superior en Marketing y Publicidad', f'{T}/comercio/mkt.html'),
    _rec(105, 'D', 'Técnico en Jardinería y Floristería', URL_JARDI),
]


def test_resolve_per_url():
    idx = ces.build_d_index(D_RECS)
    assert ces.resolve(ces.parse_requisitos(HTML_ENLLACOS), idx) == ([101, 102], [])


def test_resolve_per_nom_i_unmatched():
    idx = ces.build_d_index(D_RECS)
    assert ces.resolve(ces.parse_requisitos(HTML_SENSE_ENLLACOS), idx) == (
        [103, 104], ['Técnico Superior en Un Título Antic Inexistent.'])


def test_resolve_enllac_trencat_cau_al_nom():
    idx = ces.build_d_index(D_RECS)
    items = [{'text': 'Título de Técnico Superior en Desarrollo de Aplicaciones Web.',
              'href': '/que-estudiar/url-que-ja-no-existeix.html'}]
    assert ces.resolve(items, idx) == ([102], [])


# --- build_ce_acces ---------------------------------------------------------

E_RECS = [
    _rec(201, 'E', 'Ciberseguridad (Acceso GS)', URL_E_CIBER),
    _rec(202, 'E', 'Comercio electrónico (Acceso GS)', URL_E_COMERC),
    _rec(203, 'E', 'Floristería y arte floral (Acceso GM)', URL_E_FLOR),
    _rec(204, 'E', 'Sense fitxa', None),
]
PAGES = {URL_E_CIBER: HTML_ENLLACOS, URL_E_COMERC: HTML_SENSE_ENLLACOS, URL_E_FLOR: HTML_PROSA}


@pytest.fixture
def no_net(monkeypatch):
    monkeypatch.setattr(ces, '_fetch_with_retry', lambda session, url: PAGES[url])
    monkeypatch.setattr(ces.time, 'sleep', lambda s: None)


def test_build_ce_acces_tres_formats_i_overrides(no_net):
    overrides = {URL_E_FLOR: [URL_JARDI]}
    assert ces.build_ce_acces(D_RECS + E_RECS, overrides=overrides, session=object()) == {
        '201': {'d_ids': [101, 102], 'unmatched': []},
        '202': {'d_ids': [103, 104], 'unmatched': ['Técnico Superior en Un Título Antic Inexistent.']},
        # Override present: substitueix el text en prosa (que no lliga per nom).
        '203': {'d_ids': [105], 'unmatched': []},
    }


def test_build_ce_acces_prosa_sense_override_queda_unmatched(no_net):
    out = ces.build_ce_acces(D_RECS + E_RECS, overrides={}, session=object())
    assert out['203'] == {'d_ids': [], 'unmatched': [
        'El título que da acceso a este curso de especialización es el de '
        'Técnico en Jardinería y floristería.']}


def test_build_ce_acces_override_amb_url_desconeguda_s_avisa(no_net):
    overrides = {URL_E_FLOR: [URL_JARDI, f'{T}/no-existeix.html']}
    out = ces.build_ce_acces(D_RECS + E_RECS, overrides=overrides, session=object())
    assert out['203'] == {'d_ids': [105], 'unmatched': [f'override sense D: {T}/no-existeix.html']}


def test_build_ce_acces_fitxa_que_falla_es_salta(monkeypatch):
    def fetch(session, url):
        if url == URL_E_COMERC:
            raise RuntimeError('boom')
        return PAGES[url]
    monkeypatch.setattr(ces, '_fetch_with_retry', fetch)
    monkeypatch.setattr(ces.time, 'sleep', lambda s: None)
    out = ces.build_ce_acces(D_RECS + E_RECS, overrides={}, session=object())
    assert set(out) == {'201', '203'}


def test_build_ce_acces_cap_pagina_amb_seccio_llanca(monkeypatch):
    # Estructura de todofp canviada: no es pot sobreescriure el fitxer anterior.
    monkeypatch.setattr(ces, '_fetch_with_retry', lambda session, url: '<html></html>')
    monkeypatch.setattr(ces.time, 'sleep', lambda s: None)
    with pytest.raises(RuntimeError):
        ces.build_ce_acces(D_RECS + E_RECS, overrides={}, session=object())


def test_build_ce_acces_sense_e_no_fa_xarxa(monkeypatch):
    def fetch(session, url):
        raise AssertionError('no hi hauria d’haver xarxa')
    monkeypatch.setattr(ces, '_fetch_with_retry', fetch)
    assert ces.build_ce_acces(D_RECS, overrides={}, session=object()) == {}


def test_unmatched_warnings():
    index = {'201': {'d_ids': [1], 'unmatched': []},
             '202': {'d_ids': [], 'unmatched': ['Títol X.', 'Títol Y.']}}
    warnings = ces.unmatched_warnings(index, E_RECS)
    assert len(warnings) == 2
    assert all('Comercio electrónico (Acceso GS)' in w and URL_E_COMERC in w for w in warnings)
    assert 'Títol X.' in warnings[0] and 'Títol Y.' in warnings[1]


def test_overrides_versionat_es_valid():
    """El fitxer d'overrides del repo és {url_E: [url_D, …]} amb URLs todofp."""
    overrides = ces.load_overrides()
    assert overrides, 'ce_acces_overrides.json buit o absent'
    for e_url, d_urls in overrides.items():
        assert e_url.startswith('https://www.todofp.es/')
        assert d_urls and all(u.startswith('https://www.todofp.es/') for u in d_urls)


def test_resolve_enumeracio_a_b_dins_un_element():
    """Alguns cursos posen tots els títols en un sol <li>/<p> amb 'a) … b) …' i la cua del RD."""
    idx = ces.build_d_index(D_RECS)
    items = [{'text': 'Para acceder es necesario alguno de los siguientes títulos: '
                      'a) Técnico Superior en Vitivinicultura, establecido en el Real Decreto 1/2010, '
                      'de 1 de enero, por el que se establece el título de Técnico Superior en '
                      'Vitivinicultura y se fijan sus enseñanzas mínimas. '
                      'b) Técnico en Jardinería y Floristería, establecido en el Real Decreto 2/2010. '
                      'c) Técnico en Un Títol Inexistent, establecido en el Real Decreto 3/2010.',
              'href': None}]
    assert ces.resolve(items, idx) == (
        [103, 105], ['Técnico en Un Títol Inexistent, establecido en el Real Decreto 3/2010.'])
