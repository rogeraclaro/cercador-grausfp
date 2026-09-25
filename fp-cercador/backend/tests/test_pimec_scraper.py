"""test_pimec_scraper.py — Cursos de PIMEC Formació (Pla 062). Sense xarxa."""
import pytest

from scrapers import pimec_scraper as pim


def _card(slug, tipus, fecha, hores, lloc, titol='Curs X'):
    """Targeta amb l'estructura real de listcursos."""
    return (
        '<div class="col col-lg-4"><div class="curso-lista categoria-x">'
        f'<div class="imagen"><a href="/ca/pimes-autonoms/formacio/{slug}"><img src="i.jpg"/></a></div>'
        f'<div class="categoria"> {tipus} </div>'
        f'<div class="datos"><h2><a href="/ca/pimes-autonoms/formacio/{slug}">{titol}</a></h2>'
        f'<div class="fecha"> {fecha} <span class="duracion"> ({hores}h) </span></div>'
        f'<div class="lugar"> {lloc} </div><div class="precio"> </div></div></div></div>'
    )


def _one(fecha, hores=30, lloc='BARCELONA Presencial', tipus='Subvencionat'):
    return pim.parse_cards(_card('s-1', tipus, fecha, hores, lloc))[0]


def test_rang_dins_del_mateix_any():
    c = pim.parse_cards(_card('a-1', 'Subvencionat', '28 set. - 26 oct. 2026', 30,
                              'BADALONA Presencial', 'Manipulació d´equips'))[0]
    assert c['slug'] == 'a-1' and c['titol'] == 'Manipulació d´equips'
    assert c['tipus'] == 'Subvencionat'
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-09-28', '2026-10-26', 30.0)
    assert (c['municipi'], c['modalitat']) == ('BADALONA', 'PRESENCIAL')
    assert c['url'] == 'https://pimecformacio.org/ca/pimes-autonoms/formacio/a-1'


def test_data_unica_i_hores_decimals():
    c = _one('05 oct. 2026', hores='1.5')
    assert (c['dataInici'], c['dataFi'], c['hores']) == ('2026-10-05', '2026-10-05', 1.5)


def test_rang_que_creua_d_any_amb_any_explicit():
    c = _one('19 oct. 2026 - 09 jul. 2027', hores=245)
    assert (c['dataInici'], c['dataFi']) == ('2026-10-19', '2027-07-09')


def test_rang_que_creua_d_any_sense_any_a_l_inici():
    c = _one('15 des. - 20 gen. 2027')
    assert (c['dataInici'], c['dataFi']) == ('2026-12-15', '2027-01-20')


def test_dates_a_concretar():
    c = _one('Dates a concretar', hores=20, lloc='', tipus='Altres')
    assert (c['dataInici'], c['dataFi'], c['hores']) == (None, None, 20.0)
    assert (c['municipi'], c['modalitat']) == ('', '')
    assert c['tipus'] == 'Altres'


def test_mes_desconegut_no_peta():
    c = _one('05 xyz. 2026')
    assert (c['dataInici'], c['dataFi']) == (None, None)


@pytest.mark.parametrize('lloc, esperat', [
    ('Aula Virtual Videoconferència', ('', 'VIDEOCONFERÈNCIA')),
    ('Aula Virtual Online', ('', 'TELEFORMACIÓ')),
    ('GRANOLLERS Presencial', ('GRANOLLERS', 'PRESENCIAL')),
    ('TERRASSA Mixta', ('TERRASSA', 'MIXTA')),
    ('', ('', '')),
])
def test_lloc_i_modalitat(lloc, esperat):
    c = _one('05 oct. 2026', lloc=lloc)
    assert (c['municipi'], c['modalitat']) == esperat


def test_parse_arees():
    form = ('<form><input type="checkbox" name="field_fo_area[]" value="Idiomes"> Idiomes'
            '<input type="checkbox" name="field_fo_area[]" value="Informàtica">'
            '<input type="checkbox" name="field_fo_tipus[]" value="Altres"></form>')
    assert pim.parse_arees(form) == ['Idiomes', 'Informàtica']


def test_build_pagina_fins_pagina_buida_i_assigna_area(monkeypatch):
    monkeypatch.setattr(pim, 'PAUSA_S', 0)
    form = '<input name="field_fo_area[]" value="Idiomes">'
    pagines = {
        (None, 1): (_card('c1', 'Subvencionat', '28 set. - 26 oct. 2026', 30, 'BARCELONA Presencial')
                    + _card('c2', 'Altres', 'Dates a concretar', 12, '')),
        (None, 2): _card('c3', 'Bonificable', '29 set. 2026', 2, 'Aula Virtual Online'),
        ('Idiomes', 1): _card('c2', 'Altres', 'Dates a concretar', 12, ''),
    }

    def fake(session, page, area=None):
        return {'listcursos': pagines.get((area, page), ''),
                'formulari': form if (area is None and page == 1) else ''}

    monkeypatch.setattr(pim, '_get_page', fake)
    out = pim.build_pimec_cursos(session=object())
    per_id = {c['idCurs']: c for c in out}
    assert set(per_id) == {'PIMEC:c1', 'PIMEC:c2', 'PIMEC:c3'}
    assert per_id['PIMEC:c2']['area'] == 'Idiomes' and per_id['PIMEC:c1']['area'] == ''
    c1 = per_id['PIMEC:c1']
    assert c1['font'] == 'pimec' and c1['tipus'] == 'Subvencionat' and c1['estat'] == ''
    assert c1['titol'] == {'ca': 'Curs X', 'es': 'Curs X'}
    assert c1['centre']['nom'] == 'PIMEC Formació' and c1['centre']['municipi'] == 'BARCELONA'
    assert c1['fitxaUrl'].endswith('/formacio/c1')
    assert per_id['PIMEC:c3']['modalitat'] == 'TELEFORMACIÓ'


def test_build_no_duplica_cursos_repetits(monkeypatch):
    monkeypatch.setattr(pim, 'PAUSA_S', 0)
    dup = _card('c1', 'Subvencionat', '05 oct. 2026', 2, 'BARCELONA Presencial')
    pagines = {(None, 1): dup + dup}
    monkeypatch.setattr(pim, '_get_page',
                        lambda s, p, a=None: {'listcursos': pagines.get((a, p), ''), 'formulari': ''})
    assert len(pim.build_pimec_cursos(session=object())) == 1
