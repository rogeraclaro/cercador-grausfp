"""test_boe_corr_scraper.py — Pla 091: taules UC ↔ mòdul dels decrets del BOE.

Els fixtures de tests/fixtures/boe_corr/ són fragments reals de l'XML obert del BOE.
"""
import os

import pytest

from scrapers import boe_corr_scraper as boe

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures', 'boe_corr')


def _doc(name: str) -> dict:
    with open(os.path.join(FIXTURES, name), encoding='utf-8') as f:
        return boe.parse_doc(f.read())


def _block(doc: dict, kind: str, **where) -> dict:
    found = [b for b in doc['blocks'] if b['kind'] == kind and all(b[k] == v for k, v in where.items())]
    assert len(found) == 1
    return found[0]


def _nums(row: dict) -> list[str]:
    return [m['num'] for m in row['moduls']]


# ---------------------------------------------------------------------------
# Lectura de taules
# ---------------------------------------------------------------------------

def test_decret_antic_capcalera_td_amb_titol_dins_la_taula():
    doc = _doc('rd_177_2008_iea.xml')
    assert (doc['id'], doc['numero'], doc['fecha']) == ('BOE-A-2008-3957', '177/2008', '20080208')
    a = _block(doc, 'A')
    assert a['target_rd'] is None
    assert [(r['uc'], _nums(r)) for r in a['rows']] == [
        (['UC0822_2'], ['0232', '0238']),
        (['UC0825_2'], ['0240']),
        (['UC0820_2', 'UC0821_2'], ['0235']),
        (['UC0823_2', 'UC0824_2'], ['0236']),
        (['UC0836_2', 'UC0837_2'], ['0239']),
        (['UC0120_2', 'UC0121_2'], ['0237']),
    ]
    assert a['rows'][2]['moduls'] == [{'num': '0235', 'name': 'Instalaciones eléctricas interiores'}]
    assert a['unread'] == []


def test_taula_b_va_de_moduls_a_uc():
    b = _block(_doc('rd_177_2008_iea.xml'), 'B')
    assert all(r['uc'] and r['moduls'] for r in b['rows'])
    assert {'0235'} == {m['num'] for r in b['rows'] if 'UC0820_2' in r['uc'] for m in r['moduls']}


def test_capcalera_th_i_rowspan_ajunten_els_moduls_de_la_mateixa_uc():
    a = _block(_doc('rd_1397_2007_emergencias.xml'), 'A')
    assert (a['rows'][0]['uc'], _nums(a['rows'][0])) == (['UC0069_1'], ['0052', '0054'])
    # 0055 surt en dues files: són alternatives i no s'han d'ajuntar.
    assert [r['uc'] for r in a['rows'] if '0055' in _nums(r)] == [['UC0070_2'], ['UC0361_2']]


def test_capcalera_equivocada_el_tipus_surt_de_les_dades():
    """RD 1691/2007: la taula V B) porta impresa la capçalera de la V A)."""
    doc = _doc('rd_1691_2007_smr.xml')
    assert [b['kind'] for b in doc['blocks']] == ['A', 'B']
    assert _block(doc, 'B')['unread'] == []


def test_taula_de_tres_columnes_i_codi_uc_amb_lletra_o():
    doc = _doc('rd_127_2014_fragment.xml')
    xiii = _block(doc, 'B', anexo='XIII')
    assert xiii['anexo_titol'] == 'Título Profesional Básico en Tapicería y Cortinaje'
    assert len(xiii['rows']) == 6 and xiii['unread'] == []


@pytest.mark.parametrize('cell, expected', [
    ('0624.Comercialización de eventos.', [('0624', 'Comercialización de eventos')]),
    ('0902 .Planificación de la realización en cine y vídeo. ',
     [('0902', 'Planificación de la realización en cine y vídeo')]),
    ('O856.Aparatos de ortodoncia y férulas oclusales.', [('0856', 'Aparatos de ortodoncia y férulas oclusales')]),
    ('0232. Automatismos industriales. 0238. Instalaciones domóticas.',
     [('0232', 'Automatismos industriales'), ('0238', 'Instalaciones domóticas')]),
    ('1528: Mantenimiento de los medios materiales.', [('1528', 'Mantenimiento de los medios materiales')]),
    ('Formación en centros de trabajo.', []),
])
def test_variants_del_codi_de_modul(cell, expected):
    assert [(m['num'], m['name']) for m in boe.parse_modules(cell)] == expected


@pytest.mark.parametrize('cell, expected', [
    ('UC0820_2: Montar. UC0821_2: Mantener.', ['UC0820_2', 'UC0821_2']),
    ('UC0836_2 Montar instalaciones solares.', ['UC0836_2']),
    ('UCO255_1: Ejecutar operaciones básicas.', ['UC0255_1']),
    ('UC437_1 Realizar el secado.', ['UC0437_1']),
    ('UC01263_2: Montar sistemas mecánicos.', ['UC1263_2']),
    ('UC1947_2 :Organizar.', ['UC1947_2']),
    ('ECP1690_2: Organizar la actividad de un taller.', ['ECP1690_2']),
    ('UC0696_ Desarrollar proyectos.', []),
])
def test_variants_del_codi_uc(cell, expected):
    assert boe.parse_ucs(cell) == expected


def test_nota_fora_de_taula():
    a = _block(_doc('rd_note_after_table.xml'), 'A')
    assert len(a['notes']) == 1
    assert a['notes'][0].startswith('Nota: Las personas matriculadas')
    assert 'tendrán convalidados los módulos profesionales' in a['notes'][0]


def test_fila_amb_cella_buida_continua_la_de_sobre():
    table = '''<table>
      <tr><th>Módulos profesionales superados</th><th>Unidades de competencia acreditables</th></tr>
      <tr><td>1029. Pesca de litoral.</td><td>UC0542_2: Organizar las operaciones extractivas.</td></tr>
      <tr><td></td><td>UC1947_2 :Organizar la elaboración de las capturas.</td></tr>
    </table>'''
    parsed = boe.parse_table(table)
    assert parsed['kind'] == 'B'
    assert parsed['rows'] == [{'uc': ['UC0542_2', 'UC1947_2'],
                               'moduls': [{'num': '1029', 'name': 'Pesca de litoral'}]}]


def test_una_taula_que_no_es_de_correspondencia_s_ignora():
    assert boe.parse_table('<table><tr><td>Módulo profesional</td><td>Materia de Bachillerato</td></tr>'
                           '<tr><td>Electrotecnia.</td><td>Electrotecnia.</td></tr></table>') is None


# ---------------------------------------------------------------------------
# Enllaços de la fitxa
# ---------------------------------------------------------------------------

def test_enllacos_boe_de_la_fitxa_i_identificador():
    page = ('<a href="https://www.boe.es/diario_boe/txt.php?id=BOE-A-2008-3957">RD</a>'
            '<a href="https://www.boe.es/eli/es/rd/2024/05/21/499">RD 499</a>'
            '<a href="https://www.boe.es/diario_boe/txt.php?id=BOE-A-2008-3957">repetit</a>'
            '<a href="https://www.todofp.es/x.html">altres</a>')
    links = boe.boe_links(page)
    assert links == ['https://www.boe.es/diario_boe/txt.php?id=BOE-A-2008-3957',
                     'https://www.boe.es/eli/es/rd/2024/05/21/499']
    assert boe.boe_id(links[0]) == 'BOE-A-2008-3957'
    assert boe.boe_id(links[1]) is None  # adreça ELI: cal baixar la pàgina
    assert boe.boe_id('<meta name="DC.identifier" content="BOE-A-2024-10684">') == 'BOE-A-2024-10684'


# ---------------------------------------------------------------------------
# Decrets modificadors i atribució per títol
# ---------------------------------------------------------------------------

def test_modificador_atribueix_cada_taula_al_reial_decret_que_cita():
    doc = _doc('rd_500_2024_fragment.xml')
    assert [(b['kind'], b['target_rd']) for b in doc['blocks']] == [
        ('A', '1685/2007'), ('B', '1685/2007'), ('A', '1686/2007'), ('B', '1686/2007')]


def test_audiologia_guanya_la_taula_del_500_2024():
    base, modifier = _doc('rd_1685_2007_audiologia.xml'), _doc('rd_500_2024_fragment.xml')
    entry = boe.resolve_title('Técnico Superior en Audiología Protésica', [base], [base, modifier])
    assert (entry['decret'], entry['vigent']) == ('BOE-A-2008-645', 'BOE-A-2024-10685')
    assert 'vigent_acredita' not in entry
    assert entry['convalida'] == _block(modifier, 'A', target_rd='1685/2007')['rows']
    assert len(entry['acredita']) == 5 and set(entry['acredita'][0]) == {'moduls', 'uc'}
    # La taula original es conserva a part, no barrejada amb la vigent.
    assert entry['convalida_anterior'] == _block(base, 'A')['rows']
    assert entry['convalida_anterior'] != entry['convalida']


def test_sense_modificador_val_el_decret_propi():
    base = _doc('rd_177_2008_iea.xml')
    entry = boe.resolve_title('Técnico en Instalaciones Eléctricas y Automáticas', [base], [base])
    assert (entry['decret'], entry['vigent']) == ('BOE-A-2008-3957', 'BOE-A-2008-3957')
    assert 'convalida_anterior' not in entry
    assert len(entry['convalida']) == 6 and len(entry['acredita']) == 6


def test_un_modificador_d_un_altre_titol_no_s_aplica():
    base, modifier = _doc('rd_177_2008_iea.xml'), _doc('rd_500_2024_fragment.xml')
    entry = boe.resolve_title('Técnico en Instalaciones Eléctricas y Automáticas', [base], [base, modifier])
    assert entry['vigent'] == 'BOE-A-2008-3957'


# ---------------------------------------------------------------------------
# Títols bàsics: decret compartit i «6 bis» del 498/2024
# ---------------------------------------------------------------------------

def test_basic_taula_b_del_decret_compartit_i_taula_a_del_6_bis():
    base, modifier = _doc('rd_127_2014_fragment.xml'), _doc('rd_498_2024_fragment.xml')
    entry = boe.resolve_title('Título Profesional Básico en Servicios Administrativos',
                              [base, modifier], [base, modifier])
    assert entry['decret'] == 'BOE-A-2014-2360'
    assert entry['vigent'] == 'BOE-A-2024-10683'          # taula A: només existeix al 498/2024
    assert entry['vigent_acredita'] == 'BOE-A-2014-2360'  # taula B: la de l'annex I del 127/2014
    assert entry['convalida'] == _block(modifier, 'A', target_anexo='I')['rows']
    assert [r['moduls'] for r in entry['acredita']] == [r['moduls'] for r in _block(base, 'B', anexo='I')['rows']]
    assert 'convalida_anterior' not in entry


def test_basic_el_498_2024_substitueix_la_taula_b_del_seu_annex():
    base, modifier = _doc('rd_127_2014_fragment.xml'), _doc('rd_498_2024_fragment.xml')
    entry = boe.resolve_title('Título Profesional Básico en Tapicería y Cortinaje',
                              [base, modifier], [base, modifier])
    assert entry['vigent'] == 'BOE-A-2024-10683' and 'vigent_acredita' not in entry
    assert entry['convalida'] == _block(modifier, 'A', target_anexo='XIII')['rows']


def test_basic_que_no_es_al_decret_compartit_queda_sense_taula():
    base, modifier = _doc('rd_127_2014_fragment.xml'), _doc('rd_498_2024_fragment.xml')
    entry = boe.resolve_title('Título Profesional Básico en Vidriería y Alfarería',
                              [base, modifier], [base, modifier])
    assert entry == {'motiu': 'title not found among the annexes of its shared decree'}


# ---------------------------------------------------------------------------
# Decret propi
# ---------------------------------------------------------------------------

def test_sense_decret_que_estableixi_el_titol():
    modifier = _doc('rd_500_2024_fragment.xml')
    assert boe.resolve_title('Técnico Superior en Dietética', [modifier], [modifier]) == {
        'motiu': 'no establishing decree among the BOE links'}


def test_dos_decrets_propis_tria_el_que_porta_el_nom_del_titol():
    iea, audio = _doc('rd_177_2008_iea.xml'), _doc('rd_1685_2007_audiologia.xml')
    base, anexo, reason = boe.find_base('Técnico Superior en Audiología Protésica', [iea, audio])
    assert (base['id'], anexo, reason) == ('BOE-A-2008-645', None, '')
    assert boe.find_base('Técnico en Cocina y Gastronomía', [iea, audio])[0] is None


def test_decret_citat_per_un_modificador_quan_la_fitxa_no_l_enllaca():
    modifier = _doc('rd_499_2024_cites.xml')
    assert boe.cited_decree('Técnico en Comercialización de Productos Alimentarios', [modifier]) == 'BOE-A-2018-4748'
    assert boe.cited_decree('Técnico en Cocina y Gastronomía', [modifier]) is None


def test_decret_sense_uc_diu_el_motiu():
    xml = ('<documento><metadatos><identificador>BOE-A-1995-1</identificador><rango>Real Decreto</rango>'
           '<fecha_disposicion>19950407</fecha_disposicion><numero_oficial>546/1995</numero_oficial>'
           '<titulo>Real Decreto 546/1995, de 7 de abril, por el que se establece el título de Técnico en '
           'Cuidados Auxiliares de Enfermería y las correspondientes enseñanzas mínimas.</titulo></metadatos>'
           '<texto><p>Artículo 1.</p></texto></documento>')
    doc = boe.parse_doc(xml)
    assert boe.resolve_title('Técnico en Cuidados Auxiliares de Enfermería', [doc], [doc]) == {
        'decret': 'BOE-A-1995-1', 'motiu': 'the decree names no unit of competence'}
