"""test_ccoo_scraper.py — Cursos de CCOO / Fundació Paco Puerto (Pla 066). Sense xarxa."""
from scrapers import ccoo_scraper as cc

CATS = [
    {'id': 147, 'slug': 'informatica-i-comunicacions', 'name': 'Informàtica i comunicacions', 'parent': 0},
    {'id': 158, 'slug': 'ofimatica-i-internet', 'name': 'Ofimàtica i internet', 'parent': 147},
    {'id': 140, 'slug': 'funcio-publica-oposicions', 'name': 'Funció pública', 'parent': 0},
    {'id': 142, 'slug': 'autonomica-generalitat', 'name': 'Autonòmica', 'parent': 140},
    {'id': 149, 'slug': 'formacio-transversal', 'name': 'Formació transversal', 'parent': 0},
]
LOCS = [{'id': 289, 'name': 'Barcelona'}, {'id': 306, 'name': '(A determinar)'}]

PAGE = '''<html><body><h1>Excel &amp; Word avançat</h1>
<div class="cursos-meta alone dates"><div class="content">
  <p class="uppercase"><strong>Inici:</strong> 21/10/2026</p><p class="uppercase"><strong>Fi:</strong> 11/11/2026</p></div></div>
<div class="cursos-meta alone duration"><div class="content">30h</div></div>
<div class="cursos-meta alone modality"><div class="content">Teleformacio</div></div>
<div class="cursos-meta alone timetable"><div class="content">dimarts i dijous de 18:00 a 21:00 hores</div></div>
<div class="fpp-single-product-tab-information-wrapper">Aquest curs subvencionat proporcionarà...</div>
</body></html>'''

PAGE_SENSE = '''<html><body><h1>Curs obert</h1>
<div class="cursos-meta alone duration"><div class="content">12h</div></div>
<div class="cursos-meta alone modality"><div class="content">Aula Virtual</div></div>
<div class="fpp-single-product-tab-information-wrapper">Curs per a persones interessades.</div></body></html>'''


def test_roots():
    r = cc.roots(CATS)
    assert r[158] == 'informatica-i-comunicacions' and r[142] == 'funcio-publica-oposicions' and r[147] == 'informatica-i-comunicacions'


def test_parse_page():
    d = cc.parse_page(PAGE)
    assert d['titol'] == 'Excel & Word avançat'
    assert (d['dataInici'], d['dataFi'], d['hores']) == ('2026-10-21', '2026-11-11', 30.0)
    assert d['modalitat'] == 'TELEFORMACIÓ' and d['horariText'].startswith('dimarts i dijous')
    assert d['subvencionat'] is True


def test_parse_page_sense_dates():
    d = cc.parse_page(PAGE_SENSE)
    assert (d['dataInici'], d['dataFi'], d['hores']) == (None, None, 12.0)
    assert d['modalitat'] == 'VIDEOCONFERÈNCIA' and d['subvencionat'] is False and d['horariText'] == ''


def test_normalize():
    prod = {'id': 90288, 'link': 'https://fundaciopacopuerto.cat/cursos-formacio/x/excel-90288/',
            'product_cat': [158], 'localitat': [289]}
    c = cc.normalize(prod, cc.parse_page(PAGE), cc.roots(CATS), {c['id']: c for c in CATS},
                     {l['id']: l['name'] for l in LOCS})
    assert c['idCurs'] == 'CCOO:90288' and c['font'] == 'ccoo' and c['tipus'] == 'Subvencionat'
    assert c['familiaCodi'] == 'IFC' and c['area'] == 'Ofimàtica i internet'
    assert c['municipi'] == 'Barcelona' and c['centre']['nom'] == 'Fundació Paco Puerto (CCOO)'
    assert c['fitxaUrl'] == prod['link'] and c['estat'] == ''


def test_localitat_a_determinar_i_sense_area():
    prod = {'id': 1, 'link': 'https://x/1/', 'product_cat': [149], 'localitat': [306]}
    c = cc.normalize(prod, cc.parse_page(PAGE_SENSE), cc.roots(CATS), {c['id']: c for c in CATS},
                     {l['id']: l['name'] for l in LOCS})
    assert c['municipi'] == '' and c['familiaCodi'] == 'FCO' and c['area'] == '' and c['tipus'] == 'Altres'


def test_es_fpo_exclou_oposicions_i_sindical():
    r = cc.roots(CATS)
    assert cc.es_fpo({'product_cat': [158]}, r) is True
    assert cc.es_fpo({'product_cat': [142]}, r) is False
    assert cc.es_fpo({'product_cat': [158, 142]}, r) is False


class _Resp:
    def __init__(self, data=None, text=''):
        self._data, self.text = data, text

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _Sess:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(url)
        if url.endswith('/product_cat'):
            return _Resp(CATS if (params or {}).get('page', 1) == 1 else [])
        if url.endswith('/localitat'):
            return _Resp(LOCS if (params or {}).get('page', 1) == 1 else [])
        if url.endswith('/product'):
            if (params or {}).get('page') == 1:
                return _Resp([{'id': 1, 'link': 'https://x/ok/', 'product_cat': [158], 'localitat': [289]},
                              {'id': 2, 'link': 'https://x/opo/', 'product_cat': [142], 'localitat': [289]}])
            return _Resp([])
        return _Resp(text=PAGE)


def test_build_filtra_i_no_baixa_les_fitxes_excloses(monkeypatch):
    monkeypatch.setattr(cc, 'PAUSA_S', 0)
    sess = _Sess()
    out = cc.build_ccoo_cursos(session=sess)
    assert [c['idCurs'] for c in out] == ['CCOO:1']
    assert 'https://x/opo/' not in sess.calls
