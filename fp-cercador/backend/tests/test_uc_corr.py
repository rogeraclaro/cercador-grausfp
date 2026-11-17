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
    got = uc_corr.cycle_for_ucs(entry, ['UC2343_2', 'UC2341_2'])
    assert got['derogada'] is False and got['substituida_per'] is None
    assert got['vigent'] == 'BOE-A-2024-10684'
    assert got['uc'] == ['UC2343_2', 'UC2341_2']
    assert got['moduls_convalidats'] == ['0232', '0238']
    assert [r['falten'] for r in got['a_mitges']] == [['UC2342_2']]


def test_cicle_amb_uc_antigues_cau_a_la_taula_substituida_i_ho_diu():
    entry = {'decret': 'BOE-A-2008-3957', 'vigent': 'BOE-A-2024-10684',
             'convalida': IEA_2024, 'convalida_anterior': IEA_2008}
    got = uc_corr.cycle_for_ucs(entry, ELEE0109)
    assert got['derogada'] is True
    assert (got['vigent'], got['substituida_per']) == ('BOE-A-2008-3957', 'BOE-A-2024-10684')
    assert got['moduls_convalidats'] == ['0232', '0238', '0240', '0235', '0236']


def test_cicle_sense_cap_uc_en_comu():
    entry = {'decret': 'd', 'vigent': 'd', 'convalida': IEA_2008}
    assert uc_corr.cycle_for_ucs(entry, ['UC0001_1']) is None


def test_modul_repetit_en_dues_files_es_compta_un_sol_cop():
    entry = {'decret': 'd', 'vigent': 'd', 'convalida': [
        {'uc': ['UC0070_2'], 'moduls': [_m('0055'), _m('0056')]},
        {'uc': ['UC0361_2'], 'moduls': [_m('0055')]}]}
    assert uc_corr.cycle_for_ucs(entry, ['UC0070_2', 'UC0361_2'])['moduls_convalidats'] == ['0055', '0056']


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
