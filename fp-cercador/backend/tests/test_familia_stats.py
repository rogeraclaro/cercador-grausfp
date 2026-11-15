"""test_familia_stats.py — xifres d'una família professional (Pla 088)."""
from datetime import date

from familia_stats import build_familia_stats, fpo_soon

FAM = 'Sanidad'


def _rec(ref, grado, **extra):
    return {'id': extra.pop('id', 1), 'ref': ref, 'grado': grado, 'codigo': extra.pop('codigo', ref),
            'denominacion': f'Grau {ref}', 'familia': FAM, **extra}


RECORDS = [_rec('a1', 'A'), _rec('a2', 'A'), _rec('b1', 'B'), _rec('c1', 'C', codigo='SANC01'),
           _rec('d1', 'D', codigo=None, id=40, ficha_url='https://todofp.test/d1'),
           _rec('d2', 'D', codigo=None, id=41)]


def test_recomptes_per_lletra():
    s = build_familia_stats(FAM, RECORDS)
    assert s['total'] == 6
    assert s['per_grado'] == {'A': 2, 'B': 1, 'C': 1, 'D': 2, 'E': 0}


def test_un_centre_que_imparteix_tres_graus_compta_un_cop():
    oferta = {'a1': ['X', 'Y'], 'b1': ['X'], 'c1': ['X', 'Z'], 'd1': ['W'], 'altra-familia': ['Q']}
    centres = {'X': {'ccaa': 'CATALUÑA'}, 'Y': {'ccaa': 'CATALUÑA'}, 'Z': {'ccaa': 'ARAGÓN'},
               'W': {'ccaa': None}, 'Q': {'ccaa': 'MADRID'}}
    s = build_familia_stats(FAM, RECORDS, oferta_centres=oferta, centres_index=centres)
    assert s['centres'] == {'total': 4, 'n_ccaa': 2, 'per_ccaa': [('CATALUÑA', 2), ('ARAGÓN', 1)]}


def test_comunitats_empatades_per_ordre_alfabetic():
    oferta = {'a1': ['1', '2', '3', '4']}
    centres = {'1': {'ccaa': 'MADRID'}, '2': {'ccaa': 'ARAGÓN'}, '3': {'ccaa': 'MADRID'}, '4': {'ccaa': 'ARAGÓN'}}
    s = build_familia_stats(FAM, RECORDS, oferta_centres=oferta, centres_index=centres)
    assert s['centres']['per_ccaa'] == [('ARAGÓN', 2), ('MADRID', 2)]


def test_ocupacions_mes_frequents_amb_empats():
    ocupacions = {('C', 'SANC01'): ['Celador', 'Auxiliar de enfermería', 'Celador'],
                  ('url', 'https://todofp.test/d1'): ['Auxiliar de enfermería', 'Técnico en farmacia'],
                  ('id', 41): ['Auxiliar de enfermería', 'celador de planta'],
                  ('C', 'ALTRE'): ['No hi ha de sortir']}
    s = build_familia_stats(FAM, RECORDS, ocupacions=ocupacions)
    # Auxiliar surt a tres graus; la resta, a un (Celador repetit dins d'un grau compta un cop)
    assert s['ocupacions'] == [('Auxiliar de enfermería', 3), ('Celador', 1), ('celador de planta', 1),
                               ('Técnico en farmacia', 1)]


def test_ocupacions_limit_de_dotze():
    ocupacions = {('C', 'SANC01'): [f'Ocupació {i:02d}' for i in range(20)]}
    s = build_familia_stats(FAM, RECORDS, ocupacions=ocupacions)
    assert [n for n, _ in s['ocupacions']] == [f'Ocupació {i:02d}' for i in range(12)]


def _entry(ts, new=None, removed=None, names=True):
    changes = {}
    for meta_key, names_key, items in (('new_by_grado_meta', 'new_by_grado', new),
                                       ('removed_by_grado_meta', 'removed_by_grado', removed)):
        if items is None:
            continue
        changes[meta_key] = {g: [{'denominacio': d, 'familia': f, 'nivel': 2} for d, f in v] for g, v in items.items()}
        if names:
            changes[names_key] = {g: [d for d, _ in v] for g, v in items.items()}
    return {'ts': ts, 'changes': changes}


def test_novetats_de_la_familia_amb_altes_i_baixes():
    history = [
        _entry('2026-11-08T09:00:00+00:00', new={'D': [('Técnico en X', FAM), ('Técnico en Y', 'Agraria')]},
               removed={'A': [('UC vella', FAM)]}),
        _entry('2026-07-05T09:00:00+00:00', new={'A': [('UC nova', FAM)], 'C': [('Cert nou', FAM)]}),
    ]
    s = build_familia_stats(FAM, RECORDS, history=history)
    assert s['novetats'] == [
        {'data': '2026-11-08', 'tipus': 'alta', 'grado': 'D', 'denominacio': 'Técnico en X'},
        {'data': '2026-11-08', 'tipus': 'baixa', 'grado': 'A', 'denominacio': 'UC vella'},
        {'data': '2026-07-05', 'tipus': 'alta', 'grado': 'A', 'denominacio': 'UC nova'},
        {'data': '2026-07-05', 'tipus': 'alta', 'grado': 'C', 'denominacio': 'Cert nou'},
    ]


def test_novetats_sense_metadades_o_de_la_carrega_inicial_no_surten():
    antiga = {'ts': '2026-06-20T09:00:00+00:00', 'changes': {'new_by_grado': {'D': ['Técnico en Z']}}}
    # càrrega inicial: metadades de tot el catàleg, però cap nom a new_by_grado
    inicial = {'ts': '2026-06-17T09:00:00+00:00',
               'changes': {'new_by_grado': {}, 'new_by_grado_meta': {'D': [{'denominacio': 'Tot', 'familia': FAM}]}}}
    sense_canvis = {'ts': '2026-06-16T09:00:00+00:00', 'changes': None}
    assert build_familia_stats(FAM, RECORDS, history=[antiga, inicial, sense_canvis])['novetats'] == []
    # baixes d'abans de removed_by_grado_meta: tampoc (no se'n sap la família)
    vella = {'ts': '2026-06-25T09:00:00+00:00', 'changes': {'removed_by_grado': {'C': ['Cert vell']}}}
    assert build_familia_stats(FAM, RECORDS, history=[vella])['novetats'] == []


def test_novetats_limit_de_vuit_les_mes_recents():
    history = [_entry(f'2026-0{m}-01T09:00:00+00:00', new={'A': [(f'UC {m}-{i}', FAM) for i in range(3)]})
               for m in (9, 8, 7, 6)]
    nov = build_familia_stats(FAM, RECORDS, history=history)['novetats']
    assert len(nov) == 8
    assert [n['data'] for n in nov] == ['2026-09-01'] * 3 + ['2026-08-01'] * 3 + ['2026-07-01'] * 2


def test_familia_sense_res_de_res():
    s = build_familia_stats('Inteligencia Artificial y Data', [_rec('e1', 'E')])
    assert s == {'total': 1, 'per_grado': {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'E': 1},
                 'centres': {'total': 0, 'n_ccaa': 0, 'per_ccaa': []}, 'novetats': [], 'ocupacions': []}
    assert build_familia_stats('Buida', [])['total'] == 0


def _curs(id_, inici, fam='SAN'):
    return {'idCurs': id_, 'dataInici': inici, 'familia': {'codi': fam}, 'titol': {'ca': id_, 'es': id_}}


def test_fpo_dins_i_fora_de_la_finestra():
    avui = date(2026, 11, 15)
    cursos = [_curs('ahir', '2026-11-14'), _curs('avui', '2026-11-15'), _curs('ultim', '2027-01-14'),
              _curs('fora', '2027-01-15'), _curs('altra', '2026-11-20', fam='ADG'), _curs('sense', None)]
    out = fpo_soon('SAN', cursos, avui)
    assert [c['idCurs'] for c in out['cursos']] == ['avui', 'ultim']
    assert out['total'] == 2
    assert fpo_soon('XXX', cursos, avui) == {'cursos': [], 'total': 0}


def test_fpo_limit_de_sis_els_primers_per_data():
    avui = date(2026, 11, 15)
    cursos = [_curs(f'c{i}', f'2026-12-{20 - i:02d}') for i in range(10)]
    out = fpo_soon('SAN', cursos, avui)
    assert [c['idCurs'] for c in out['cursos']] == ['c9', 'c8', 'c7', 'c6', 'c5', 'c4']
    assert out['total'] == 10
