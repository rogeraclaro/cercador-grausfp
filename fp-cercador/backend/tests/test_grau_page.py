"""
test_grau_page.py — Pàgines públiques per grau, famílies, sitemap i robots (Pla 077).

/api/grau/<ref>, /api/familia/<prefix>, /api/families, /api/sitemap.xml i
/api/robots.txt (nginx hi reescriu /grau/…, /familia/…, /families, /sitemap.xml
i /robots.txt). Fitxers aïllats a tmp_path.
"""
import json
import re
import xml.etree.ElementTree as ET

import pytest

import app as app_module
import grau_page

SITE = 'https://example.test'
FAM = 'Administración y Gestión'
IMA = 'Instalación y Mantenimiento'
IEX = 'Industrias Extractivas'

URL_D = 'https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/servicios-administrativos.html'
URL_E = 'https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/ce-gestion-digital.html'


def _rec(id_, codigo, grado, denominacion, familia=FAM, nivel=1, plan_antiguo=False,
         ficha_url=None, observaciones=''):
    r = {'id': id_, 'codigo': codigo, 'grado': grado, 'denominacion': denominacion,
         'familia': familia, 'nivel': nivel, 'plan_antiguo': plan_antiguo,
         'observaciones': observaciones}
    if ficha_url:
        r['ficha_url'] = ficha_url
    return r


OFERTES = [
    # LOMLOE: A → B → C → D
    _rec(1, 'ADG_A_3001_01', 'A', 'Preparación de los equipos'),
    _rec(2, 'ADG_B_3001', 'B', 'Tratamiento informático de datos'),
    _rec(3, 'ADG_C_001_3B', 'C', 'Actividades de grabación de datos',
         observaciones='Requiere <b>ESO</b>'),
    _rec(4, None, 'D', 'Título Profesional Básico en Servicios Administrativos', ficha_url=URL_D),
    _rec(5, None, 'E', 'Curso de especialización en Gestión digital (Acceso GM)', nivel=None,
         ficha_url=URL_E),
    # LOE (pla antic): A → B → C
    _rec(10, 'UF0510', 'A', 'Procesadores de textos', plan_antiguo=True),
    _rec(11, 'MF0973_1', 'B', 'Grabación de datos', plan_antiguo=True),
    _rec(12, 'ADGG0408', 'C', 'Operaciones auxiliares de servicios administrativos',
         plan_antiguo=True),
    # Codi repetit a dues famílies → ref amb ~
    _rec(20, 'UF0620', 'A', 'Replanteo de redes', familia=IMA, plan_antiguo=True),
    _rec(21, 'UF0620', 'A', 'Replanteo de redes', familia=IEX, plan_antiguo=True),
    # Dades hostils
    _rec(30, 'ADG_B_3999', 'B', '<script>alert(1)</script> & "cometes"'),
]
A_LOE_PARES = {'UF0510': ['MF0973_1']}
BC_LOE = {'ADGG0408': ['UC0973_1', 'UC9999_1']}
BC_LOMLOE = {'ADG_C_001_3B': ['ADG_B_3001']}
B_CONTINGUT = {
    'ADG_B_3001': {
        'ecp': [{'codigo': 'ECP0973_1', 'text': 'Introducir datos y textos en terminales'}],
        'ra': [{'codigo': 'ADG_RA_3001_01', 'text': 'Prepara los equipos y materiales'}],
    },
}
D_MODULOS = {'4': {'modulos': [{'num': None, 'name': 'Técnicas administrativas básicas'},
                               {'num': None, 'name': 'Archivo y comunicación'}]}}
CE_ACCES = {'5': {'d_ids': [4], 'unmatched': ['Título de Técnico en Gestión (LOGSE)']}}
OCUPACIONES = [
    {'ocupacio': 'Grabadores de datos', 'norm': 'grabadores de datos', 'grado': 'C',
     'codigo': 'ADG_C_001_3B', 'id': 3, 'denominacion': 'x', 'ficha_url': None, 'familia': FAM},
    {'ocupacio': 'Auxiliar administrativo', 'norm': 'auxiliar administrativo', 'grado': 'D',
     'codigo': None, 'id': 999, 'denominacion': 'x', 'ficha_url': URL_D, 'familia': FAM},
]
CENTRES = [
    {'id': 'C1', 'nombre': 'INSTITUTO SECRETO UNO', 'ccaa': 'CATALUÑA'},
    {'id': 'C2', 'nombre': 'INSTITUTO SECRETO DOS', 'ccaa': 'CATALUÑA'},
    {'id': 'C3', 'nombre': 'INSTITUTO SECRETO TRES', 'ccaa': 'PAÍS VASCO'},
]
OFERTA_CENTRES = {'ADG_C_001_3B': ['C1', 'C2', 'C3'], 'ADGG0408': ['C1']}

FILES = {
    'DATA_PATH': ('ofertes.json', OFERTES),
    'A_LOE_PARES_PATH': ('a_loe_pares.json', A_LOE_PARES),
    'BC_LOE_PATH': ('bc_loe.json', BC_LOE),
    'BC_LOMLOE_PATH': ('bc_lomloe.json', BC_LOMLOE),
    'B_CONTINGUT_PATH': ('b_contingut.json', B_CONTINGUT),
    'D_MODULOS_PATH': ('d_modulos.json', D_MODULOS),
    'CE_ACCES_PATH': ('ce_acces.json', CE_ACCES),
    'OCUPACIONES_PATH': ('ocupaciones.json', OCUPACIONES),
    '_CENTRES_PATH': ('centres.json', CENTRES),
    '_OFERTA_CENTRES_PATH': ('oferta_centres.json', OFERTA_CENTRES),
}
OPTIONAL = ['B_CONTINGUT_PATH', 'D_MODULOS_PATH', 'CE_ACCES_PATH', 'OCUPACIONES_PATH',
            'BC_LOE_PATH', 'BC_LOMLOE_PATH', 'A_LOE_PARES_PATH', '_CENTRES_PATH',
            '_OFERTA_CENTRES_PATH']


def _reset_caches(monkeypatch):
    for name in ('_itinerary_index_cache', '_a_loe_pares_cache', '_bc_lomloe_cache',
                 '_d_modulos_cache', '_b_contingut_cache', '_bc_loe_inverse_cache'):
        monkeypatch.setattr(app_module, name, {'mtime': None, 'index': None})
    monkeypatch.setattr(app_module, '_ocupaciones_cache', {'mtime': None, 'entries': None})
    for name in ('_cd_lomloe_cache', '_itinerary_graph_cache', '_catalog_cache',
                 '_effective_oc_cache', '_seo_cache'):
        monkeypatch.setattr(app_module, name, {'key': None, 'data': None})
    monkeypatch.setattr(app_module, '_centres_index', None)
    monkeypatch.setattr(app_module, '_oferta_centres', None)


def _setup(tmp_path, monkeypatch, skip=()):
    for attr, (name, content) in FILES.items():
        p = tmp_path / name
        if attr not in skip:
            p.write_text(json.dumps(content), encoding='utf-8')
        monkeypatch.setattr(app_module, attr, str(p))
    monkeypatch.setattr(app_module, 'CICLOS_PATH', str(tmp_path / 'ciclos_fp.json'))
    monkeypatch.setattr(app_module, 'SITE_URL', SITE)
    _reset_caches(monkeypatch)


@pytest.fixture
def client(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        yield c


def _page(client, ref):
    resp = client.get(f'/api/grau/{ref}')
    assert resp.status_code == 200, resp.get_data(as_text=True)[:300]
    assert resp.mimetype == 'text/html'
    return resp.get_data(as_text=True)


def _json_ld(body):
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)
    assert m, 'sense JSON-LD'
    return json.loads(m.group(1))


# ---------------------------------------------------------------------------
# Pàgina de grau: 404, escapament, metadades
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('ref', ['NO_EXISTEIX', '..%2Fapp', 'a%3Cb', 'x' * 200])
def test_ref_desconegut_dona_404_html(client, ref):
    resp = client.get(f'/api/grau/{ref}')
    assert resp.status_code == 404
    assert resp.mimetype == 'text/html'
    body = resp.get_data(as_text=True)
    assert '<html lang="es">' in body
    assert 'noindex' in body
    assert '<script>alert' not in body


def test_denominacio_hostil_s_escapa(client):
    body = _page(client, 'ADG_B_3999')
    assert '<script>alert(1)</script>' not in body
    assert '&lt;script&gt;alert(1)&lt;/script&gt; &amp; &quot;cometes&quot;' in body
    # El JSON-LD no pot tancar el <script> i ha de seguir sent JSON vàlid.
    ld = _json_ld(body)
    assert ld['name'] == '<script>alert(1)</script> & "cometes"'


def test_observacions_s_escapen(client):
    body = _page(client, 'ADG_C_001_3B')
    assert 'Requiere &lt;b&gt;ESO&lt;/b&gt;' in body
    assert '<b>ESO</b>' not in body


def test_metadades_canonical_og_i_titol(client):
    body = _page(client, 'UF0620~IMA')
    url = f'{SITE}/grau/UF0620~IMA'
    assert f'<link rel="canonical" href="{url}">' in body
    assert f'<meta property="og:url" content="{url}">' in body
    assert '<title>Replanteo de redes — Grado A de FP | GrausFP</title>' in body
    assert re.search(r'<meta name="description" content="[^"]{40,}">', body)
    assert '<html lang="es">' in body


def test_json_ld_course(client):
    ld = _json_ld(_page(client, 'ADG_C_001_3B'))
    assert ld['@context'] == 'https://schema.org'
    assert ld['@type'] == 'Course'
    assert ld['name'] == 'Actividades de grabación de datos'
    assert ld['courseCode'] == 'ADG_C_001_3B'
    assert ld['url'] == f'{SITE}/grau/ADG_C_001_3B'
    assert ld['provider']['name']


def test_etiquetes_grau_nivell_familia_codi_i_pla_antic(client):
    body = _page(client, 'ADGG0408')
    assert 'Grado C' in body
    assert 'Nivel 1' in body
    assert FAM in body
    assert 'ADGG0408' in body
    assert 'Plan antiguo' in body
    assert 'Plan antiguo' not in _page(client, 'ADG_C_001_3B')


def test_paragraf_explicatiu_per_grau(client):
    assert 'acreditación parcial de competencia' in _page(client, 'ADG_A_3001_01')
    assert 'certificado de competencia' in _page(client, 'ADG_B_3001')
    assert 'certificado profesional' in _page(client, 'ADG_C_001_3B')
    assert 'ciclo formativo' in _page(client, 'administracion-gestion~servicios-administrativos')
    assert 'curso de especialización' in _page(client, 'administracion-gestion~ce-gestion-digital')


# ---------------------------------------------------------------------------
# Contingut específic de cada grau
# ---------------------------------------------------------------------------

def test_b_mostra_competencies_i_resultats(client):
    body = _page(client, 'ADG_B_3001')
    assert 'Introducir datos y textos en terminales' in body
    assert 'ECP0973_1' in body
    assert 'Prepara los equipos y materiales' in body


def test_a_mostra_el_seu_resultat_d_aprenentatge(client):
    body = _page(client, 'ADG_A_3001_01')
    assert 'Prepara los equipos y materiales' in body


def test_c_pla_antic_mostra_unitats_de_competencia(client):
    body = _page(client, 'ADGG0408')
    assert 'UC0973_1' in body
    assert 'Grabación de datos' in body  # nom del mòdul MF0973_1
    assert 'UC9999_1' in body           # sense mòdul conegut: només el codi


def test_d_mostra_moduls(client):
    body = _page(client, 'administracion-gestion~servicios-administrativos')
    assert 'Técnicas administrativas básicas' in body
    assert 'Archivo y comunicación' in body
    assert 'Grado básico' in body


def test_e_mostra_els_d_que_hi_donen_acces(client):
    body = _page(client, 'administracion-gestion~ce-gestion-digital')
    assert 'href="/grau/administracion-gestion~servicios-administrativos"' in body
    assert 'Título de Técnico en Gestión (LOGSE)' in body


def test_ocupacions_relacionades(client):
    assert 'Grabadores de datos' in _page(client, 'ADG_C_001_3B')
    assert 'Auxiliar administrativo' in _page(
        client, 'administracion-gestion~servicios-administrativos')


# ---------------------------------------------------------------------------
# Centres (agregats, sense noms) i itinerari
# ---------------------------------------------------------------------------

def test_centres_agregats_per_comunitat_sense_noms(client):
    body = _page(client, 'ADG_C_001_3B')
    assert 'data-centres-total="3"' in body
    assert 'Cataluña' in body and 'País Vasco' in body
    assert 'SECRETO' not in body
    assert 'href="/index.html?ref=ADG_C_001_3B"' in body


def test_centres_d_a_i_b_coincideixen_amb_el_cercador(client):
    counts = client.get('/api/centres/count').get_json()
    assert counts['ADG_A_3001_01'] == 3  # heretats del C via el B
    assert f'data-centres-total="{counts["ADG_A_3001_01"]}"' in _page(client, 'ADG_A_3001_01')
    assert f'data-centres-total="{counts["ADG_B_3001"]}"' in _page(client, 'ADG_B_3001')


def test_grau_sense_centres(client):
    body = _page(client, 'administracion-gestion~ce-gestion-digital')
    assert 'data-centres-total="0"' in body


def test_veins_de_l_itinerari_enllacen_a_les_seves_pagines(client):
    body = _page(client, 'ADG_C_001_3B')
    assert 'href="/grau/ADG_B_3001"' in body
    assert 'href="/itinerari.html?grado=C&amp;ref=ADG_C_001_3B"' in body
    body_a = _page(client, 'ADG_A_3001_01')
    assert 'href="/grau/ADG_B_3001"' in body_a


def test_fitxa_oficial_sense_enllac_directe(client):
    body = _page(client, 'ADG_C_001_3B')
    assert 'Ficha oficial disponible con una cuenta gratuita' in body
    assert 'ficha-redirect' not in body
    assert 'todofp.es/buscador' not in body
    body_d = _page(client, 'administracion-gestion~servicios-administrativos')
    assert URL_D not in body_d


def test_ref_amb_titlla_i_enllacos_absoluts(client):
    body = _page(client, 'UF0620~IEX')
    assert 'href="/site.css' in body
    assert 'src="/i18n.js?v=' in body
    assert f'<link rel="canonical" href="{SITE}/grau/UF0620~IEX">' in body
    assert 'href="/familia/IEX"' in body
    assert '<base href="/">' in body  # footer.js i auth.js fan servir enllaços relatius


def test_falten_indexs_opcionals_i_la_pagina_surt_igual(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, skip=OPTIONAL)
    with app_module.app.test_client() as c:
        for ref in ('ADG_A_3001_01', 'ADG_B_3001', 'ADGG0408',
                    'administracion-gestion~servicios-administrativos',
                    'administracion-gestion~ce-gestion-digital'):
            resp = c.get(f'/api/grau/{ref}')
            assert resp.status_code == 200, ref
            assert 'data-centres-total="0"' in resp.get_data(as_text=True)


def test_sense_ofertes_dona_503(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, skip=['DATA_PATH'])
    with app_module.app.test_client() as c:
        resp = c.get('/api/grau/ADG_B_3001')
        assert resp.status_code == 503
        assert resp.mimetype == 'text/html'


# ---------------------------------------------------------------------------
# Famílies, sitemap, robots, capçaleres
# ---------------------------------------------------------------------------

def test_pagina_de_familia_agrupa_per_grau(client):
    resp = client.get('/api/familia/ADG')
    assert resp.status_code == 200 and resp.mimetype == 'text/html'
    body = resp.get_data(as_text=True)
    assert FAM in body
    for ref in ('ADG_A_3001_01', 'ADG_B_3001', 'ADGG0408',
                'administracion-gestion~servicios-administrativos'):
        assert f'href="/grau/{ref}"' in body
    assert 'href="/grau/UF0620~IMA"' not in body
    assert body.index('Grado A') < body.index('Grado B') < body.index('Grado C')
    assert f'<link rel="canonical" href="{SITE}/familia/ADG">' in body
    assert '&lt;script&gt;' in body and '<script>alert' not in body


@pytest.mark.parametrize('prefix', ['ZZZ', 'MF', 'adg', '%3Cx%3E'])
def test_familia_desconeguda_dona_404(client, prefix):
    resp = client.get(f'/api/familia/{prefix}')
    assert resp.status_code == 404
    assert resp.mimetype == 'text/html'


def test_llista_de_families(client):
    resp = client.get('/api/families')
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    for prefix in ('ADG', 'IMA', 'IEX'):
        assert f'href="/familia/{prefix}"' in body
    assert f'<link rel="canonical" href="{SITE}/families">' in body


def test_sitemap_valid_i_complet(client):
    resp = client.get('/api/sitemap.xml')
    assert resp.status_code == 200
    assert resp.mimetype == 'application/xml'
    root = ET.fromstring(resp.data)
    ns = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs = [u.find('s:loc', ns).text for u in root.findall('s:url', ns)]
    n_families = 3  # ADG, IMA, IEX
    assert len(locs) == len(OFERTES) + n_families + len(grau_page.STATIC_PAGES)
    assert len(set(locs)) == len(locs)
    assert f'{SITE}/grau/UF0620~IMA' in locs
    assert f'{SITE}/familia/ADG' in locs
    assert f'{SITE}/families' in locs
    assert all(loc.startswith(SITE + '/') for loc in locs)
    lastmods = {u.find('s:lastmod', ns).text for u in root.findall('s:url', ns)}
    assert all(re.fullmatch(r'\d{4}-\d{2}-\d{2}', d) for d in lastmods)


def test_robots(client):
    resp = client.get('/api/robots.txt')
    assert resp.status_code == 200
    assert resp.mimetype == 'text/plain'
    body = resp.get_data(as_text=True)
    lines = body.splitlines()
    assert 'User-agent: *' in lines
    for path in ('/api/', '/admin.html', '/perfil.html'):
        assert f'Disallow: {path}' in lines
    assert f'Sitemap: {SITE}/sitemap.xml' in lines


@pytest.mark.parametrize('path', ['/api/grau/ADG_B_3001', '/api/familia/ADG', '/api/families',
                                  '/api/sitemap.xml', '/api/robots.txt'])
def test_cache_control(client, path):
    assert client.get(path).headers['Cache-Control'] == 'public, max-age=3600'


def test_render_pur_escapa_tot():
    """grau_page.render_grau rep dades ja carregades; cap camp surt sense escapar."""
    evil = '<img src=x onerror=alert(1)>'
    rec = {'ref': 'X_B_1', 'grado': 'B', 'codigo': evil, 'denominacion': evil, 'familia': evil,
           'nivel': 2, 'plan_antiguo': False, 'observaciones': evil}
    ctx = {'contingut': {'ecp': [{'codigo': evil, 'text': evil}], 'ra': [{'codigo': evil, 'text': evil}]},
           'ocupaciones': [evil], 'centres': {'total': 1, 'per_ccaa': [(evil, 1)]},
           'previs': [{'ref': 'Y', 'grado': 'A', 'denominacion': evil, 'plan_antiguo': False}],
           'seguents': [], 'familia_prefix': None, 'lastmod': '2026-10-26'}
    body = grau_page.render_grau(rec, ctx, SITE)
    assert '<img' not in body
    assert body.count('&lt;img src=x onerror=alert(1)&gt;') >= 8
