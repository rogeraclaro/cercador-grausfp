"""test_foment_scraper.py — Cursos de Foment Formació (Pla 062). Sense xarxa."""
import requests

from scrapers import foment_scraper as fo

_DETALL = ('<div class="detail-item"><div class="detail-item__texts">'
           '<label>{k}</label><span>{v}</span></div></div>')

HTML = (
    '<html><body><h1 class="hero-curso__title">ADGG0208: Ofimática</h1>'
    '<div class="sidebar-card__list">'
    '<div data-edition="edicion-presencial-09-03-26-9689">'
    '<div class="detail-item"><div class="detail-item__texts"><label>Centro</label>'
    '<a href="https://www.google.com/maps/search/?api=1&#038;query=41.3856074,2.1772219">'
    ' FOMENT FORMACIO </a></div></div>'
    + _DETALL.format(k='Comienzo', v='09/03/2026')
    + _DETALL.format(k='Final', v='29/04/2026')
    + _DETALL.format(k='Horario', v='Lunes a Viernes de 09:00 a 15:00')
    + _DETALL.format(k='Horas', v='190 horas')
    + '</div>'
    '<div data-edition="edicion-virtual-21-09-26-9999">'
    '<div class="detail-item"><div class="detail-item__texts"><label>Centro</label>'
    '<a href="https://www.google.com/maps/search/?api=1&#038;query=41.5,2.1">CENEF, SL</a></div></div>'
    + _DETALL.format(k='Comienzo', v='21/09/2026')
    + _DETALL.format(k='Final', v='30/11/2026')
    + _DETALL.format(k='Horas', v='30 horas')
    + '</div></div></body></html>'
)
URL = 'https://www.fomentformacio.com/formacion/adgd0208-mf0233-ofimatica-5'


def test_parse_course_una_fila_per_edicio():
    eds = fo.parse_course(HTML, URL)
    assert [e['idCurs'] for e in eds] == [
        'FOMENT:adgd0208-mf0233-ofimatica-5:edicion-presencial-09-03-26-9689',
        'FOMENT:adgd0208-mf0233-ofimatica-5:edicion-virtual-21-09-26-9999',
    ]
    e = eds[0]
    assert e['font'] == 'foment' and e['tipus'] == 'Altres' and e['estat'] == ''
    assert e['titol'] == {'ca': 'ADGG0208: Ofimática', 'es': 'ADGG0208: Ofimática'}
    assert e['certCodi'] == 'ADGG0208'
    assert (e['dataInici'], e['dataFi'], e['hores']) == ('2026-03-09', '2026-04-29', 190.0)
    assert e['modalitat'] == 'PRESENCIAL'
    assert e['horariText'] == 'Lunes a Viernes de 09:00 a 15:00'
    assert e['centre']['nom'] == 'FOMENT FORMACIO'
    assert (e['centre']['lat'], e['centre']['lon']) == (41.3856074, 2.1772219)
    assert e['fitxaUrl'] == URL


def test_edicio_virtual_sense_horari_ni_codi():
    e = fo.parse_course(HTML.replace('ADGG0208: ', ''), URL)[1]
    assert e['modalitat'] == 'VIDEOCONFERÈNCIA' and e['horariText'] == '' and e['certCodi'] == ''
    assert e['centre']['nom'] == 'CENEF, SL'


def test_pagina_sense_titol_no_dona_res():
    assert fo.parse_course('<html><body>404</body></html>', URL) == []


def test_list_course_urls_castella_sense_fragment_ni_repetits():
    xml = ('<urlset>'
           '<url><loc>https://www.fomentformacio.com/formacion</loc></url>'
           '<url><loc>https://www.fomentformacio.com/ca/formacio</loc></url>'
           '<url><loc>https://www.fomentformacio.com/formacion/curso-a</loc></url>'
           '<url><loc>https://www.fomentformacio.com/formacion/curso-a#edicion-virtual-15-09-26-8615</loc></url>'
           '<url><loc>https://www.fomentformacio.com/formacion/curso-b#edicion-presencial-14-09-26-9709</loc></url>'
           '<url><loc>https://www.fomentformacio.com/ca/formacio/curs-a</loc></url>'
           '</urlset>')
    assert fo.list_course_urls(xml) == ['https://www.fomentformacio.com/formacion/curso-a',
                                        'https://www.fomentformacio.com/formacion/curso-b']


class _Resp:
    def __init__(self, text='', exc=None):
        self.text, self._exc = text, exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc


class _Sess:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, timeout=30):
        r = self.pages[url]
        return r if isinstance(r, _Resp) else _Resp(r)


def test_build_salta_les_fitxes_que_fallen(monkeypatch):
    monkeypatch.setattr(fo, 'PAUSA_S', 0)
    sitemap = ('<loc>https://www.fomentformacio.com/formacion/ok</loc>'
               '<loc>https://www.fomentformacio.com/formacion/ok#edicion-virtual-1-1</loc>'
               '<loc>https://www.fomentformacio.com/formacion/ko</loc>')
    sess = _Sess({
        fo.SITEMAP_URL: sitemap,
        'https://www.fomentformacio.com/formacion/ok': HTML,
        'https://www.fomentformacio.com/formacion/ko': _Resp(exc=requests.HTTPError('500')),
    })
    out = fo.build_foment_cursos(session=sess)     # 'ok#edicion...' no es torna a baixar
    assert len(out) == 2 and all(c['idCurs'].startswith('FOMENT:ok:') for c in out)
