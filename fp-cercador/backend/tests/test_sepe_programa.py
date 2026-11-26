"""
test_sepe_programa.py — Pla 100: lector dels programes del SEPE, modal d'ocupacions i
script de descàrrega completa. Sense xarxa: textos i HTML reals desats com a fixtures
(baixats el 2026-11-26) i el SEPE mockejat.
"""
import importlib.util
import json
import os
import zlib

import pytest
import requests

import sepe_programa
from scrapers import sepe_scraper

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')

_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'sepe_descarrega_programes.py')
_spec = importlib.util.spec_from_file_location('sepe_descarrega_programes', _SCRIPT)
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)


def _fixture(nom):
    with open(os.path.join(FIXTURES, nom), encoding='utf-8') as f:
        return f.read()


# --- parse_programa ---

def test_modern_ssce22():
    p = sepe_programa.parse_programa(_fixture('sepe_programa_SSCE22.txt'), 50.0)
    assert p['format'] == 'modern'
    assert p['objectiu'].startswith('Adquirir los conocimientos, destrezas y habilidades')
    assert p['objectiu'].endswith('en la modalidad de teleformación.')
    # Noms partits en diverses línies (cel·la centrada) ben recomposats
    assert p['moduls'] == [
        {'nom': 'APRENDIZAJE MEDIANTE TELEFORMACIÓN Y FIGURA DEL TUTOR-FORMADOR', 'hores': 10},
        {'nom': 'HERRAMIENTAS Y ESTRATEGIAS METODOLÓGICAS PARA EL APRENDIZAJE EN TELEFORMACIÓN', 'hores': 30},
        {'nom': 'EVALUACIÓN DEL APRENDIZAJE EN TELEFORMACIÓN', 'hores': 10},
    ]
    assert p['moduls_ok'] is True and p['moduls_error'] is None
    assert p['tutories_presencials_h'] == 0
    req = {r['tipus']: r['text'] for r in p['requisits_acces']}
    assert set(req) == {'titulacio', 'experiencia', 'altres'}      # sense la fila «Modalidad de teleformación»
    assert req['experiencia'] == 'No se requiere'
    assert req['titulacio'].startswith('Cumplir como mínimo alguno de los siguientes requisitos:\n-Título de Graduado')
    assert not req['titulacio'].startswith('/')                     # el rètol partit «/ titulaciones» no hi és
    assert 'tutores-formadores' in p['vinculacions']                 # guió de final de línia enganxat
    assert 'Ocupaciones' not in p['vinculacions']


def test_modern_llarg_adgn0023():
    p = sepe_programa.parse_programa(_fixture('sepe_programa_ADGN0023.txt'), 350.0)
    assert p['format'] == 'modern'
    assert len(p['moduls']) == 10 and sum(m['hores'] for m in p['moduls']) == 350
    assert p['moduls'][0] == {'nom': 'INSTRUMENTOS Y MERCADOS FINANCIEROS', 'hores': 100}
    assert p['hores_presencial'] == 150                              # mixta: part presencial
    assert p['tutories_presencials_h'] is None
    req = {r['tipus']: r['text'] for r in p['requisits_acces']}
    # El rètol «Experiencia profesional» es repeteix en canviar de pàgina: un sol requisit
    assert req['experiencia'].startswith('En el caso de no poseer')
    assert req['experiencia'].endswith('(sector financiero).')
    assert 'Página' not in req['experiencia']
    assert p['vinculacions'].startswith('• Esta formación habilita')
    assert 'Otras especificaciones' not in p['vinculacions']


def test_po_ssce001po():
    p = sepe_programa.parse_programa(_fixture('sepe_programa_SSCE001PO.txt'), 50.0)
    assert p['format'] == 'po'
    assert p['objectiu'] == ('Adquirir las habilidades y competencias necesarias para la impartición de '
                             'acciones formativas en modalidad teleformación utilizando técnicas, '
                             'estrategias y recursos didácticos.')
    # Teleformació pura (presencial 0): el repartiment no aporta res que no digui el catàleg
    assert (p['hores_presencial'], p['hores_teleformacio']) == (None, None)
    assert p['moduls'] is None and p['moduls_ok'] is False


PO_DURADA = '''PROGRAMAS DE FORMACIÓN DIRIGIDOS PRIORITARIAMENTE A TRABAJADORES
OCUPADOS
4. Objetivo General: Gestionar compras.
5. Número de participantes: 30
6. Duración:
Horas totales{total} Modalidad: {mod}
Distribución de hora{s}
Presencial:........... {pres}
Teleformación:...... {tele}
7. Requisitos mínimos
'''


@pytest.mark.parametrize('total,mod,pres,tele,esperat', [
    (': 20', 'Indistinta', 20, 20, (None, None)),     # en qualsevol de les dues, no un repartiment
    (' 20', 'Mixta', 8, 12, (8, 12)),                 # repartiment real («Horas totales» sense «:»)
])
def test_po_distribucio_d_hores(total, mod, pres, tele, esperat):
    text = PO_DURADA.format(total=total, mod=mod, s='', pres=pres, tele=tele)
    p = sepe_programa.parse_programa(text, 20.0)
    assert p['format'] == 'po'                       # la frase partida en dues línies també es detecta
    assert (p['hores_presencial'], p['hores_teleformacio']) == esperat


def test_antic_adga12dcp():
    p = sepe_programa.parse_programa(_fixture('sepe_programa_ADGA12DCP.txt'), 410.0)
    assert p['format'] == 'antic'
    assert p['objectiu'].startswith('Formar en tareas administrativas sencillas')
    assert p['objectiu'].endswith('como en la Administración Pública.')
    assert '6.' not in p['objectiu']
    assert p['moduls'] is None


def test_hores_que_no_quadren_descarten_els_moduls():
    p = sepe_programa.parse_programa(_fixture('sepe_programa_SSCE22.txt'), 60.0)   # 10+30+10 = 50
    assert p['moduls'] is None
    assert p['moduls_ok'] is False and p['moduls_error'] == 'suma'
    assert p['objectiu'] and p['requisits_acces']                    # la resta es conserva


def test_tolerancia_d_una_hora():
    assert sepe_programa.parse_programa(_fixture('sepe_programa_SSCE22.txt'), 51.0)['moduls_ok'] is True


def test_sense_hores_del_cataleg_compara_amb_la_durada_del_programa():
    assert sepe_programa.parse_programa(_fixture('sepe_programa_SSCE22.txt'))['moduls_ok'] is True


@pytest.mark.parametrize('text', ['', 'Un text qualsevol\nsense plantilla', None])
def test_text_sense_plantilla_es_none(text):
    assert sepe_programa.parse_programa(text) is None


def test_moduls_repartiment_que_no_quadra_es_none():
    # Cap repartiment no quadra: el nom començaria a mitja frase
    assert sepe_programa.parse_moduls(['Módulo 1 10 horas', 'resta del nom']) is None
    # Sense hores enlloc
    assert sepe_programa.parse_moduls(['Módulo 1 UNO']) is None
    # Numeració saltada
    assert sepe_programa.parse_moduls(['Módulo 1 UNO 10 horas', 'Módulo 3 TRES 5 horas']) is None
    assert sepe_programa.parse_moduls(['NOM', 'Módulo 1 5 horas', 'LLARG']) == [{'nom': 'NOM LLARG', 'hores': 5}]


def test_moduls_nom_no_centrat_es_reparteix_per_minuscules():
    # Cas real (AFDA0003): el nom d'una sola línia surt a sobre del «Módulo 1», no al costat
    lines = ['El sector de los eSports. Stakeholders, roles y relaciones', 'Módulo 1 5 horas',
             'Módulo 2 Coordinación de un centro de eSport 25 horas',
             'Herramientas para la gestión del equipo de trabajo del', 'Módulo 3 20 horas', 'centro']
    assert sepe_programa.parse_moduls(lines) == [
        {'nom': 'El sector de los eSports. Stakeholders, roles y relaciones', 'hores': 5},
        {'nom': 'Coordinación de un centro de eSport', 'hores': 25},
        {'nom': 'Herramientas para la gestión del equipo de trabajo del centro', 'hores': 20},
    ]


def test_moduls_hores_a_la_linia_del_nom():
    # Cas real (TMVI33): les hores surten a la línia del nom, no a la del «Módulo 1»
    lines = ['Atención al Cliente de Transporte de Viajeros (Formación Complementaria 8 horas',
             'Módulo 1', 'CAP Viajeros)']
    assert sepe_programa.parse_moduls(lines) == [
        {'nom': 'Atención al Cliente de Transporte de Viajeros (Formación Complementaria CAP Viajeros)',
         'hores': 8}]


def test_taula_de_moduls_illegible_es_marca():
    text = _fixture('sepe_programa_SSCE22.txt').replace('Módulo 3 EVALUACIÓN', 'Módulo 4 EVALUACIÓN')
    p = sepe_programa.parse_programa(text, 50.0)
    assert p['moduls'] is None and p['moduls_error'] == 'format'


# --- Ocupacions (modal del cercador) ---

def test_parse_ocupacions_amb_files():
    assert sepe_scraper.parse_ocupacions(_fixture('sepe_ocupacions_3.html')) == [
        {'codi': '23291029', 'nom': 'FORMADORES DE FORMACIÓN PARA EL EMPLEO'},
        {'codi': '23291010', 'nom': 'FORMADORES DE FORMACIÓN NO REGLADA'},
        {'codi': '23211034', 'nom': 'FORMADORES DE FORMADORES'},
    ]


def test_parse_ocupacions_sense_files():
    assert sepe_scraper.parse_ocupacions(_fixture('sepe_ocupacions_buida.html')) == []


@pytest.mark.parametrize('page', [
    '<html><title>Error</title></html>',
    '<tbody id="formulario:modalOcupaciones:ocupacionesSeleccionadasTable:tbody_element"><tr><td>x</td></tr></tbody>',
])
def test_parse_ocupacions_format_desconegut(page):
    with pytest.raises(sepe_scraper.SepeDataError):
        sepe_scraper.parse_ocupacions(page)


class _Resp:
    def __init__(self, content=b'', ctype=''):
        self.content, self.headers = content, {'Content-Type': ctype}

    def raise_for_status(self):
        pass


class _Session:
    def __init__(self, *posts):
        self.posts, self.posted, self.gets = list(posts), [], 0

    def get(self, url, timeout):
        self.gets += 1
        return _Resp()

    def post(self, url, files, timeout):
        self.posted.append(files)
        return self.posts.pop(0)


def test_fetch_programa_i_ocupacions_una_sessio():
    s = _Session(_Resp(b'%PDF-1.4 x', 'pdf'),
                 _Resp(_fixture('sepe_ocupacions_3.html').encode('utf-8'), 'text/html; charset=UTF-8'))
    pdf, ocu = sepe_scraper.fetch_programa_i_ocupacions(97614, session=s)
    assert pdf == b'%PDF-1.4 x' and len(ocu) == 3
    assert s.gets == 1
    assert 'formulario:invisibleClickTargetProgramaFormativoEspecialidad' in s.posted[0]
    assert 'formulario:invisibleClickTargetShowOcupaciones' in s.posted[1]
    assert s.posted[1]['formulario:codigoPropuesta'] == (None, '97614')


def test_fetch_programa_i_ocupacions_sense_pdf():
    s = _Session(_Resp(b'<html>no tiene documento</html>', 'text/html'),
                 _Resp(_fixture('sepe_ocupacions_buida.html').encode('utf-8'), 'text/html'))
    assert sepe_scraper.fetch_programa_i_ocupacions(1, session=s) == (None, [])


# --- Script de descàrrega (SEPE mockejat) ---

def _espec(codi, versio=1, id_sepe=None, hores=50.0, inici='2025-01-01', sufix=None):
    return {'codi': codi, 'idSepe': id_sepe or zlib.crc32(codi.encode()), 'versio': versio,
            'hores': hores, 'vigenciaInici': inici, 'sufix': sufix}


@pytest.fixture
def entorn(tmp_path, monkeypatch):
    especs = [_espec(f'AAAA{i:04d}') for i in range(8)]
    path = tmp_path / 'especs.json'
    path.write_text(json.dumps(especs), encoding='utf-8')
    monkeypatch.setattr(script, 'pdf_to_text', lambda content: content.decode('utf-8'))
    return {'especs': especs, 'especs_path': str(path), 'out': str(tmp_path / 'out.json'),
            'informe': str(tmp_path / 'informe.md')}


def _args(entorn, *extra):
    return ['--especs', entorn['especs_path'], '--sortida', entorn['out'], '--informe', entorn['informe'],
            '--pausa', '0', '0', *extra]


class _Fetch:
    """SEPE fals: `errors` = {crida: excepció}; per defecte, el programa SSCE22 i 1 ocupació."""
    def __init__(self, errors=None):
        self.n, self.ids, self.errors = 0, [], errors or {}

    def __call__(self, id_sepe):
        self.n += 1
        self.ids.append(id_sepe)
        exc = self.errors.get(self.n)
        if exc:
            raise exc
        return _fixture('sepe_programa_SSCE22.txt').encode('utf-8'), [{'codi': '1', 'nom': 'X'}]


def _http_error(status):
    resp = requests.Response()
    resp.status_code = status
    return requests.HTTPError(response=resp)


def _llegeix(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def test_script_baixa_i_desa(entorn):
    fetch = _Fetch()
    assert script.main(_args(entorn), fetch=fetch) == script.EXIT_OK
    data = _llegeix(entorn['out'])
    assert set(data) == {e['codi'] for e in entorn['especs']}
    entry = data['AAAA0000']
    assert entry['versio'] == 1 and entry['baixat'] and entry['sense_pdf'] is False
    assert entry['programa']['format'] == 'modern' and entry['programa']['moduls_ok'] is True
    assert entry['ocupacions'] == [{'codi': '1', 'nom': 'X'}]
    informe = open(entorn['informe'], encoding='utf-8').read()
    assert '| modern | 8 | 8 | 8 | 8 |' in informe


def test_script_represa_salta_les_ja_baixades(entorn):
    assert script.main(_args(entorn, '--limit', '3'), fetch=_Fetch()) == 0
    assert len(_llegeix(entorn['out'])) == 3
    fetch = _Fetch()
    assert script.main(_args(entorn), fetch=fetch) == 0
    assert fetch.n == 5                                       # només les 5 que faltaven
    assert len(_llegeix(entorn['out'])) == 8


def test_script_mode_complet_refa_les_anteriors_a_des_de(entorn):
    script.main(_args(entorn), fetch=_Fetch())
    data = _llegeix(entorn['out'])
    data['AAAA0001']['baixat'] = '2020-01-01T00:00:00+00:00'
    script.desa(entorn['out'], data)
    fetch = _Fetch()
    script.main(_args(entorn, '--des-de', '2025-01-01'), fetch=fetch)
    assert fetch.n == 1


def test_script_nomes_canvis(entorn, tmp_path):
    script.main(_args(entorn), fetch=_Fetch())
    data = _llegeix(entorn['out'])
    for v in data.values():
        v['baixat'] = '2020-01-01T00:00:00+00:00'               # antigues, però mateixa versió
    script.desa(entorn['out'], data)
    especs = entorn['especs'] + [_espec('NOVA0001')]
    especs[2] = dict(especs[2], versio=2)                       # canvi de versió
    with open(entorn['especs_path'], 'w', encoding='utf-8') as f:
        json.dump(especs, f)
    fetch = _Fetch()
    assert script.main(_args(entorn, '--nomes-canvis'), fetch=fetch) == 0
    assert sorted(fetch.ids) == sorted([especs[2]['idSepe'], especs[-1]['idSepe']])
    assert _llegeix(entorn['out'])['AAAA0002']['versio'] == 2


def test_script_s_atura_amb_5_errors_seguits(entorn):
    err = requests.ConnectionError('caigut')
    fetch = _Fetch({2: err, 3: err, 4: err, 5: err, 6: err})
    assert script.main(_args(entorn), fetch=fetch) == script.EXIT_ERRORS
    assert fetch.n == 6                                       # no continua ni reintenta
    assert list(_llegeix(entorn['out'])) == ['AAAA0000']      # el que ja tenia queda desat


def test_script_errors_no_seguits_no_aturen(entorn):
    err = requests.ConnectionError('caigut')
    fetch = _Fetch({1: err, 2: err, 3: err, 4: err, 6: err})
    assert script.main(_args(entorn), fetch=fetch) == script.EXIT_OK
    assert len(_llegeix(entorn['out'])) == 3


@pytest.mark.parametrize('status', [403, 429])
def test_script_s_atura_amb_403_o_429(entorn, status):
    fetch = _Fetch({3: _http_error(status)})
    assert script.main(_args(entorn), fetch=fetch) == script.EXIT_BLOQUEIG
    assert fetch.n == 3
    assert len(_llegeix(entorn['out'])) == 2


def test_script_desa_cada_25(entorn, monkeypatch):
    desades = []
    real = script.desa
    monkeypatch.setattr(script, 'DESA_CADA', 3)
    monkeypatch.setattr(script, 'desa', lambda path, data: (desades.append(len(data)), real(path, data)))
    script.main(_args(entorn), fetch=_Fetch())
    assert desades[:2] == [3, 6] and desades[-1] == 8


def test_script_sense_pdf(entorn):
    def fetch(id_sepe):
        return None, []
    script.main(_args(entorn, '--limit', '1'), fetch=fetch)
    entry = _llegeix(entorn['out'])['AAAA0000']
    assert entry['sense_pdf'] is True and entry['programa'] is None and entry['ocupacions'] == []
