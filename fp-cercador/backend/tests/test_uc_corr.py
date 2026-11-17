"""test_uc_corr.py — Pla 091: regla de càlcul de la correspondència UC → mòduls."""
import uc_corr


def _m(num, name='x'):
    return {'num': num, 'name': name}


# Taula A original del RD 177/2008 (Técnico en Instalaciones Eléctricas y Automáticas).
IEA_2008 = [
    {'uc': ['UC0822_2'], 'moduls': [_m('0232'), _m('0238')]},
    {'uc': ['UC0825_2'], 'moduls': [_m('0240')]},
    {'uc': ['UC0820_2', 'UC0821_2'], 'moduls': [_m('0235')]},
    {'uc': ['UC0823_2', 'UC0824_2'], 'moduls': [_m('0236')]},
    {'uc': ['UC0836_2', 'UC0837_2'], 'moduls': [_m('0239')]},
    {'uc': ['UC0120_2', 'UC0121_2'], 'moduls': [_m('0237')]},
]
# Taula A vigent (RD 499/2024): codis d'UC nous.
IEA_2024 = [
    {'uc': ['UC2343_2'], 'moduls': [_m('0232'), _m('0238')]},
    {'uc': ['UC2341_2', 'UC2342_2'], 'moduls': [_m('0235')]},
]
ELEE0109 = ['UC0820_2', 'UC0821_2', 'UC0822_2', 'UC0823_2', 'UC0824_2', 'UC0825_2']


def _nums(rows):
    return [m['num'] for r in rows for m in r['moduls']]


def test_cas_de_referencia_elee0109_contra_la_taula_del_2008():
    full, partial = uc_corr.convalidated(IEA_2008, ELEE0109)
    assert sorted(_nums(full)) == ['0232', '0235', '0236', '0238', '0240']
    assert partial == []  # 0237 i 0239 queden fora: cap UC seva


def test_una_fila_nomes_convalida_amb_totes_les_seves_uc():
    full, partial = uc_corr.convalidated(IEA_2008, ['UC0820_2', 'UC0822_2'])
    assert _nums(full) == ['0232', '0238']
    assert partial == [{'moduls': [_m('0235')], 'uc': ['UC0820_2', 'UC0821_2'], 'falten': ['UC0821_2']}]


def test_sense_cap_uc_no_hi_ha_res():
    assert uc_corr.convalidated(IEA_2008, []) == ([], [])
    assert uc_corr.convalidated(IEA_2008, ['UC9999_9']) == ([], [])


def test_cicle_amb_la_taula_vigent():
    entry = {'decret': 'BOE-A-2008-3957', 'vigent': 'BOE-A-2024-10684',
             'convalida': IEA_2024, 'convalida_anterior': IEA_2008}
    [got] = uc_corr.cycles_for_ucs(entry, ['UC2343_2', 'UC2341_2'])
    assert got['derogada'] is False and got['substituida_per'] is None
    assert got['vigent'] == 'BOE-A-2024-10684'
    assert got['uc'] == ['UC2343_2', 'UC2341_2']
    assert got['moduls_convalidats'] == ['0232', '0238']
    assert [r['falten'] for r in got['a_mitges']] == [['UC2342_2']]


def test_cicle_amb_uc_antigues_cau_a_la_taula_substituida_i_ho_diu():
    entry = {'decret': 'BOE-A-2008-3957', 'vigent': 'BOE-A-2024-10684',
             'convalida': IEA_2024, 'convalida_anterior': IEA_2008}
    [got] = uc_corr.cycles_for_ucs(entry, ELEE0109)
    assert got['derogada'] is True
    assert (got['vigent'], got['substituida_per']) == ('BOE-A-2008-3957', 'BOE-A-2024-10684')
    assert got['moduls_convalidats'] == ['0232', '0238', '0240', '0235', '0236']


def test_uc_antigues_i_noves_alhora_donen_la_taula_vigent_i_la_substituida():
    entry = {'decret': 'BOE-A-2008-3957', 'vigent': 'BOE-A-2024-10684',
             'convalida': IEA_2024, 'convalida_anterior': IEA_2008}
    vigent, derogada = uc_corr.cycles_for_ucs(entry, ELEE0109 + ['UC2341_2'])
    assert (vigent['derogada'], vigent['moduls_convalidats']) == (False, [])
    assert [r['falten'] for r in vigent['a_mitges']] == [['UC2342_2']]
    assert (derogada['derogada'], len(derogada['moduls_convalidats'])) == (True, 5)


def test_la_taula_substituida_no_surt_si_no_aporta_cap_modul_mes():
    entry = {'decret': 'd', 'vigent': 'v', 'convalida': IEA_2024, 'convalida_anterior': IEA_2008}
    # UC0822_2 (antiga) i UC2343_2 (nova) convaliden els mateixos mòduls 0232 i 0238.
    assert [c['derogada'] for c in uc_corr.cycles_for_ucs(entry, ['UC0822_2', 'UC2343_2'])] == [False]


def test_cicle_sense_cap_uc_en_comu():
    entry = {'decret': 'd', 'vigent': 'd', 'convalida': IEA_2008}
    assert uc_corr.cycles_for_ucs(entry, ['UC0001_1']) == []


def test_modul_repetit_en_dues_files_es_compta_un_sol_cop():
    entry = {'decret': 'd', 'vigent': 'd', 'convalida': [
        {'uc': ['UC0070_2'], 'moduls': [_m('0055'), _m('0056')]},
        {'uc': ['UC0361_2'], 'moduls': [_m('0055')]}]}
    assert uc_corr.cycles_for_ucs(entry, ['UC0070_2', 'UC0361_2'])[0]['moduls_convalidats'] == ['0055', '0056']


def test_uc_dels_graus_que_ja_es_tenen():
    held = [{'grado': 'C', 'codigo': 'ELEE0109', 'plan_antiguo': True},
            {'grado': 'B', 'codigo': 'MF0836_2', 'plan_antiguo': True},
            {'grado': 'B', 'codigo': 'MF0820_2', 'plan_antiguo': True},      # repetida amb el certificat
            {'grado': 'C', 'codigo': 'ELE_C_001_2', 'plan_antiguo': False},  # pla nou: no va per UC
            {'grado': 'B', 'codigo': 'ELE_B_3001', 'plan_antiguo': False},
            {'grado': 'D', 'codigo': None}]
    assert uc_corr.held_ucs(held, {'ELEE0109': ['UC0820_2', 'UC0821_2'], 'ELE_C_001_2': ['UC0001_1']}) == [
        'UC0820_2', 'UC0821_2', 'UC0836_2']
    assert uc_corr.held_ucs([], {}) == []


def test_certificats_que_porten_totes_les_uc_d_una_fila():
    by_uc = {'UC1': [{'codigo': 'A'}, {'codigo': 'B'}], 'UC2': [{'codigo': 'B'}]}
    assert uc_corr.certs_with_all(['UC1', 'UC2'], by_uc) == [{'codigo': 'B'}]
    assert uc_corr.certs_with_all(['UC1'], by_uc) == [{'codigo': 'A'}, {'codigo': 'B'}]
    assert uc_corr.certs_with_all(['UC1', 'UC3'], by_uc) == []
    assert uc_corr.certs_with_all([], by_uc) == []


def test_numeros_de_modul_omplerts_pel_nom():
    entry = {'convalida': [{'uc': ['UC0822_2'], 'moduls': [_m('0232', 'Automatismos industriales')]}],
             'acredita': [{'uc': ['UC0825_2'], 'moduls': [_m('0240', 'Máquinas eléctricas')]}]}
    modulos = [{'num': None, 'name': 'Automatismos Industriales'},
               {'num': None, 'name': 'Máquinas eléctricas.'},
               {'num': '9999', 'name': 'Automatismos industriales'},
               {'num': None, 'name': 'Proyecto intermodular'}]
    assert uc_corr.cycle_modules(modulos, entry) == [
        {'num': '0232', 'name': 'Automatismos Industriales'},
        {'num': '0240', 'name': 'Máquinas eléctricas.'},
        {'num': '9999', 'name': 'Automatismos industriales'},
        {'num': None, 'name': 'Proyecto intermodular'}]
