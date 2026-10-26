"""
test_oferta_ref.py — Clau estable `ref` de cada registre d'ofertes.json (Pla 076).

Els `id` es reassignen a cada refresc; el `ref` no depèn de l'ordre:
  A/B/C  codigo, o codigo~<prefix família> si el codi es repeteix entre famílies
  D/E    <carpeta família>~<slug> (els dos últims segments de ficha_url, sense .html)
"""
import json
import os

import pytest

import oferta_ref
from oferta_ref import REF_RE, assign_refs, ensure_refs, stable_ref

TODOFP = 'https://www.todofp.es/que-estudiar/familias-profesionales/{}.html'


def _abc(id_, grado, codigo, familia='Administración y Gestión'):
    return {'id': id_, 'grado': grado, 'codigo': codigo, 'familia': familia}


def _de(id_, grado, path):
    return {'id': id_, 'grado': grado, 'codigo': None, 'familia': 'X', 'ficha_url': TODOFP.format(path)}


def test_abc_ref_es_el_codigo():
    assert stable_ref(_abc(1, 'C', 'ADGG0408'), set()) == 'ADGG0408'


def test_codi_repetit_porta_el_prefix_de_la_familia():
    rec = _abc(1, 'A', 'MF0432_1', familia='Administración y Gestión')
    assert stable_ref(rec, {'MF0432_1'}) == 'MF0432_1~ADG'


def test_de_ref_son_els_dos_ultims_segments_amb_titlla():
    rec = _de(1, 'D', 'informatica-comunicaciones/informatica-oficina')
    assert stable_ref(rec, set()) == 'informatica-comunicaciones~informatica-oficina'


def test_de_ref_logse():
    rec = {'grado': 'D', 'ficha_url': 'https://www.todofp.es/que-estudiar/logse/'
           'mantenimiento-servicios-produccion/prevencion-riesgos-profesionales.html'}
    assert stable_ref(rec, set()) == 'mantenimiento-servicios-produccion~prevencion-riesgos-profesionales'


def test_de_sense_ficha_url_falla():
    with pytest.raises(ValueError):
        stable_ref({'grado': 'E', 'ficha_url': None}, set())


def test_codi_repetit_amb_familia_sense_prefix_falla():
    # No s'inventen sufixos: una família fora de PREFIX_MAP atura el pipeline.
    with pytest.raises(ValueError):
        stable_ref(_abc(1, 'B', 'MF0001_1', familia='Desconeguda'), {'MF0001_1'})


def test_assign_refs_fa_refs_unics_i_valids():
    records = [
        _abc(1, 'A', 'MF0432_1', familia='Administración y Gestión'),
        _abc(2, 'A', 'MF0432_1', familia='Comercio y Marketing'),
        _abc(3, 'C', 'ADGG0408'),
        _de(4, 'D', 'administracion-gestion/informatica-oficina'),
        _de(5, 'D', 'informatica-comunicaciones/informatica-oficina'),
    ]
    assign_refs(records)
    refs = [r['ref'] for r in records]
    assert refs == ['MF0432_1~ADG', 'MF0432_1~COM', 'ADGG0408',
                    'administracion-gestion~informatica-oficina',
                    'informatica-comunicaciones~informatica-oficina']
    assert all(REF_RE.match(r) for r in refs)


def test_assign_refs_falla_si_hi_ha_refs_repetits():
    records = [_abc(1, 'A', 'MF0432_1'), _abc(2, 'A', 'MF0432_1')]  # mateixa família
    with pytest.raises(ValueError, match='MF0432_1~ADG'):
        assign_refs(records)


def test_ref_estable_entre_dos_catalegs_amb_registres_inserits():
    vell = [_abc(1, 'A', 'UF0001'), _abc(2, 'C', 'ADGG0408'),
            _de(3, 'D', 'agraria/actividades-ecuestres')]
    nou = [_abc(1, 'A', 'UF0001'), _abc(2, 'A', 'UF0002'), _abc(3, 'B', 'MF0001_1'),
           _abc(4, 'C', 'ADGG0408'), _de(5, 'D', 'agraria/jardineria'),
           _de(6, 'D', 'agraria/actividades-ecuestres')]
    assign_refs(vell)
    assign_refs(nou)
    ref_per_den = lambda recs: {r['ref']: r['id'] for r in recs}  # noqa: E731
    v, n = ref_per_den(vell), ref_per_den(nou)
    # Els id canvien, però els tres refs del catàleg vell segueixen existint.
    assert set(v) <= set(n)
    assert v['agraria~actividades-ecuestres'] == 3 and n['agraria~actividades-ecuestres'] == 6


def test_ensure_refs_respecta_els_refs_existents():
    records = [dict(_abc(1, 'C', 'ADGG0408'), ref='ADGG0408'), _abc(2, 'C', 'COML0110')]
    ensure_refs(records)
    assert [r['ref'] for r in records] == ['ADGG0408', 'COML0110']


def test_pipeline_fa_servir_assign_refs():
    from scrapers import pipeline
    assert pipeline.assign_refs is oferta_ref.assign_refs


_REAL = os.path.join(os.path.dirname(__file__), '..', 'data', 'ofertes.json')


@pytest.mark.skipif(not os.path.exists(_REAL), reason='sense ofertes.json local')
def test_cataleg_real_sense_refs_repetits():
    with open(_REAL, encoding='utf-8') as fh:
        records = json.load(fh)
    for r in records:
        r.pop('ref', None)
    assign_refs(records)  # ValueError si n'hi ha cap de repetit
    assert len({r['ref'] for r in records}) == len(records)
