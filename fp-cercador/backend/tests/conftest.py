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


# ---------------------------------------------------------------------------
# Fixtures HTML per a tests del html_scraper (Fase 3)
# Estructura verificada contra todofp.es — vegeu 03-RESEARCH.md §Estructura HTML Verificada
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_html_grado_d_one_record():
    """HTML mínim amb 1 títol d'una família canònica ('Administración y Gestión')."""
    return """
    <html><body><table>
      <thead><tr class="cols">
        <th id="familia">Familia</th>
        <th id="titulacion">Titulación</th>
      </tr></thead>
      <tbody>
        <tr class="fpb">
          <th rowspan="1" headers="familia" id="fam0">
            <img alt="Logotipo Administración y Gestión" src="#">
          </th>
          <td headers="titulacion fam0">
            <p><a id="tit-gestion-administrativa" href="#">Gestión Administrativa</a></p>
          </td>
        </tr>
      </tbody>
    </table></body></html>
    """


@pytest.fixture
def minimal_html_grado_d_two_records_same_family():
    """HTML mínim amb 2 títols de la mateixa família (rowspan=2, segona fila sense <th>)."""
    return """
    <html><body><table>
      <thead><tr class="cols">
        <th id="familia">Familia</th>
        <th id="titulacion">Titulación</th>
      </tr></thead>
      <tbody>
        <tr class="fpb">
          <th rowspan="2" headers="familia" id="fam0">
            <img alt="Logotipo Administración y Gestión" src="#">
          </th>
          <td headers="titulacion fam0">
            <p><a id="tit-gestion-administrativa" href="#">Gestión Administrativa</a></p>
          </td>
        </tr>
        <tr class="fpb">
          <td headers="titulacion fam0">
            <p><a id="tit-servicios-administrativos" href="#">Servicios Administrativos</a></p>
          </td>
        </tr>
      </tbody>
    </table></body></html>
    """


@pytest.fixture
def minimal_html_alias_imagen_y_sonido():
    """HTML mínim amb família 'Imagen y Sonido' — requereix HTML_FAMILY_ALIASES per mapar-la a 'Imagen y Espectáculos'."""
    return """
    <html><body><table>
      <thead><tr class="cols">
        <th id="familia">Familia</th>
        <th id="titulacion">Titulación</th>
      </tr></thead>
      <tbody>
        <tr class="fpgm">
          <th rowspan="1" headers="familia" id="fam1">
            <img alt="Logotipo Imagen y Sonido" src="#">
          </th>
          <td headers="titulacion fam1">
            <p><a id="tit-realizacion-audiovisuales" href="#">Realización de Audiovisuales</a></p>
          </td>
        </tr>
      </tbody>
    </table></body></html>
    """


@pytest.fixture
def minimal_html_unknown_family():
    """HTML mínim amb família no canònica ('Mantenimiento y Servicios a la Producción') — produirà familia='Desconeguda' + warning."""
    return """
    <html><body><table>
      <thead><tr class="cols">
        <th id="familia">Familia</th>
        <th id="titulacion">Titulación</th>
      </tr></thead>
      <tbody>
        <tr class="fpgs">
          <th rowspan="1" headers="familia" id="fam99">
            <img alt="Logotipo Mantenimiento y Servicios a la Producción" src="#">
          </th>
          <td headers="titulacion fam99">
            <p><a id="tit-prevencion-riesgos" href="#">Prevención de Riesgos Profesionales</a></p>
          </td>
        </tr>
      </tbody>
    </table></body></html>
    """
