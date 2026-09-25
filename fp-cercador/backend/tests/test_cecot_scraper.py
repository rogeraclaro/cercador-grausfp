"""test_cecot_scraper.py — Cursos de Cecot Formació (Pla 066). Sense xarxa."""
import requests

from scrapers import cecot_scraper as ce

ITEM = {'Codi': 'A2025FOAP0015000015', 'Descripcio': 'Atenció sociosanitària', 'Hores': '480',
        'Inici': '01/09/2026', 'Poblacio': 'Terrassa', 'Modalitat': 'Presencial', 'Pagament': 'N'}

DETAIL = '''
<div class="folder-date d-flex">
  <div class="folder-date-start" data-date="01/09/2026"><div class="folder-date-when">Inici</div></div>
  <div class="folder-date-finish" data-date="04/01/2027"><div class="folder-date-when">Final</div></div>
</div>
<div class="course-features-block"><table class="table"><tbody>
  <tr><th scope="row">Tipus</th><td>Curs</td><th scope="row">Adreçat a</th><td>Treballadors/es a l'atur</td></tr>
  <tr><th scope="row">Durada</th><td>480 hores</td><th scope="row">Dies</th><td>DL DM DC DJ DV</td></tr>
  <tr><th scope="row">Pagament</th><td><img src="x.png"/></td><th scope="row">Horari laboral</th><td>De 09:00 a 14:00</td></tr>
  <tr><th scope="row">Adreça</th><td>Vapor Universitari<br />Carrer Colon, 114 2a planta<br />08223 - Terrassa</td>
      <th scope="row"></th><td></td></tr>
</tbody></table></div>
'''


def test_parse_detail():
    d = ce.parse_detail(DETAIL)
    assert (d['dataInici'], d['dataFi']) == ('2026-09-01', '2027-01-04')
    assert d['camps']['Dies'] == 'DL DM DC DJ DV' and d['camps']['Horari laboral'] == 'De 09:00 a 14:00'
    assert d['adreca'] == ['Vapor Universitari', 'Carrer Colon, 114 2a planta', '08223 - Terrassa']


def test_parse_detail_buit():
    assert ce.parse_detail('<html></html>') == {'dataInici': None, 'dataFi': None, 'camps': {}, 'adreca': []}


def test_normalize_amb_fitxa():
    c = ce.normalize(ITEM, ce.parse_detail(DETAIL))
    assert c['idCurs'] == 'CECOT:A2025FOAP0015000015' and c['font'] == 'cecot'
    assert c['tipus'] == 'Subvencionat' and c['estat'] == '' and c['familiaCodi'] == ''
    assert c['titol'] == {'ca': 'Atenció sociosanitària', 'es': 'Atenció sociosanitària'}
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-09-01', '2027-01-04', 480.0)
    assert (c['modalitat'], c['municipi']) == ('PRESENCIAL', 'Terrassa')
    assert c['horariText'] == 'DL DM DC DJ DV · De 09:00 a 14:00'
    assert c['centre']['nom'] == 'Cecot · Vapor Universitari'
    assert (c['centre']['carrer'], c['centre']['cp'], c['centre']['municipi']) == (
        'Carrer Colon, 114 2a planta', '08223', 'Terrassa')
    assert c['fitxaUrl'] == 'https://formacio.cecot.org/Cursos/Curs/(code)/A2025FOAP0015000015'


def test_normalize_sense_fitxa_de_pagament_virtual():
    item = dict(ITEM, Codi='P1', Poblacio='Virtual', Modalitat='Virtual', Pagament='S', Hores='3')
    c = ce.normalize(item, None)
    assert c['tipus'] == 'Altres' and c['modalitat'] == 'VIDEOCONFERÈNCIA' and c['municipi'] == ''
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-09-01', None, 3.0)
    assert c['centre']['nom'] == 'Cecot' and c['horariText'] == ''


class _Resp:
    def __init__(self, text='', data=None, exc=None):
        self.text, self._data, self._exc = text, data, exc

    def raise_for_status(self):
        if self._exc:
            raise self._exc

    def json(self):
        return self._data


class _Sess:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url, headers=None, timeout=None):
        return self.pages[url]


def test_build_llista_i_fitxes_i_tolera_una_fitxa_que_falla(monkeypatch):
    monkeypatch.setattr(ce, 'PAUSA_S', 0)
    ko = dict(ITEM, Codi='KO')
    sess = _Sess({
        ce.LIST_URL: _Resp(data={'success': True, 'data': {'items': {'list': [ITEM, ko]}}}),
        ce.DETAIL_URL.format(codi=ITEM['Codi']): _Resp(text=DETAIL),
        ce.DETAIL_URL.format(codi='KO'): _Resp(exc=requests.HTTPError('500')),
    })
    out = ce.build_cecot_cursos(session=sess)
    assert [c['idCurs'] for c in out] == ['CECOT:A2025FOAP0015000015', 'CECOT:KO']
    assert out[0]['dataFi'] == '2027-01-04' and out[1]['dataFi'] is None


def test_build_resposta_inesperada_peta():
    sess = _Sess({ce.LIST_URL: _Resp(data={'success': False})})
    try:
        ce.build_cecot_cursos(session=sess)
    except ValueError:
        return
    raise AssertionError('havia de fallar')
