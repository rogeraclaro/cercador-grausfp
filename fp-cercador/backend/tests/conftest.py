"""Fixtures compartides per als tests de pdf_scraper."""
import pytest


@pytest.fixture
def sample_table_grado_c():
    """Simula una pàgina de taula de Grado C (nou pla, nivell 1)."""
    return [
        ['AFD_C_001_3B', 'Acondicionamiento físico en sala de entrenamiento polivalente', '', ''],
    ]


@pytest.fixture
def sample_table_grado_c_level2():
    """Simula una pàgina de taula de Grado C (nou pla, nivell 2)."""
    return [
        ['AFD_C_001_4B', 'Acondicionamiento físico nivel 2', '', ''],
    ]


@pytest.fixture
def sample_table_grado_c_level3():
    """Simula una pàgina de taula de Grado C (nou pla, nivell 3)."""
    return [
        ['AFD_C_001_5B', 'Acondicionamiento físico nivel 3', '', ''],
    ]


@pytest.fixture
def sample_table_grado_b_old():
    """Simula una pàgina de taula de Grado B (pla antic)."""
    return [
        ['MF2268_2 (Plan antiguo)', 'Gestión de la prevención de riesgos laborales', '', ''],
    ]


@pytest.fixture
def sample_table_grado_a_new():
    """Simula una pàgina de taula de Grado A (nou pla)."""
    return [
        ['AFD_A_3003_01', 'Acondicionamiento físico individual', '', ''],
    ]


@pytest.fixture
def sample_table_grado_a_old():
    """Simula una pàgina de taula de Grado A (pla antic)."""
    return [
        ['UF0297 (Plan antiguo)', 'Acondicionamiento físico básico', '', ''],
    ]


@pytest.fixture
def sample_table_unknown_prefix():
    """Simula una pàgina amb prefix de família desconegut."""
    return [
        ['XXX_C_001_3B', 'Denominació desconeguda', '', ''],
    ]
