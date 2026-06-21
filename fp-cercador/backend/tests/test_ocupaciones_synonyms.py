"""
test_ocupaciones_synonyms.py — Tests per a _expand_token (pla 050).

Verifica el diccionari CA→ES i les regles de sufix per a la cerca d'ocupació
en català.
"""
import pytest


def test_expand_token_suffix_acio():
    from app import _expand_token
    assert _expand_token('comunicacio') == ['comunicacio', 'comunicacion']


def test_expand_token_suffix_itat():
    from app import _expand_token
    assert _expand_token('electricitat') == ['electricitat', 'electricidad']


def test_expand_token_suffix_ment():
    from app import _expand_token
    assert _expand_token('manteniment') == ['manteniment', 'mantenimiento']


def test_expand_token_suffix_atge():
    from app import _expand_token
    assert _expand_token('muntatge') == ['muntatge', 'montaje']


def test_expand_token_dict_cuina():
    from app import _expand_token
    assert _expand_token('cuina') == ['cuina', 'cocina']


def test_expand_token_no_expansion():
    from app import _expand_token
    assert _expand_token('soldador') == ['soldador']


def test_expand_token_already_es():
    from app import _expand_token
    # 'comunicacion' ja és castellà — cap suffix CA coincideix
    assert _expand_token('comunicacion') == ['comunicacion']


def test_expand_token_dict_infermeria():
    from app import _expand_token
    assert _expand_token('infermeria') == ['infermeria', 'enfermeria']


def test_expand_token_dict_comerc():
    from app import _expand_token
    assert _expand_token('comerc') == ['comerc', 'comercio']


def test_expand_token_dict_esport():
    from app import _expand_token
    assert _expand_token('esport') == ['esport', 'deporte']


def test_expand_token_dict_transport():
    from app import _expand_token
    assert _expand_token('transport') == ['transport', 'transporte']
