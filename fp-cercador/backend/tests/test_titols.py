"""test_titols.py — display_title (Pla 096): títols en majúscules → text llegible."""
from titols import PRESERVE, display_title


def test_lowercase_with_initial_capital():
    assert display_title('AUXILIAR DE EMPLEADO DE OFICINA') == 'Auxiliar de empleado de oficina'


def test_acronyms_without_vowels_or_with_digits_are_kept():
    assert display_title('PRL EN TRABAJOS CON CNC Y SQL') == 'PRL en trabajos con CNC y SQL'
    assert display_title('MODELADO 3D CON HTML5 - NIVEL B2') == 'Modelado 3D con HTML5 - nivel B2'


def test_preserve_acronyms_and_proper_nouns():
    assert display_title('MICROSOFT AZURE PARA PYMES') == 'Microsoft Azure para PYMES'
    assert display_title('BIM Y SAP CON IA') == 'BIM y SAP con IA'
    assert display_title('TUTORÍA EN MOODLE') == 'Tutoría en Moodle'
    # paraules ambigües que no són sigles: minúscula
    assert display_title('USO DEL AGUA EN LA OBRA') == 'Uso del agua en la obra'


def test_preserve_phrases():
    assert display_title('INGENIERÍA DE SISTEMAS EN «RED HAT LINUX»') == 'Ingeniería de sistemas en «Red Hat Linux»'
    assert display_title('GESTIÓN DE LA RED') == 'Gestión de la red'
    assert display_title('VISUALIZACIÓN DE DATOS CON POWER BI') == 'Visualización de datos con Power BI'


def test_roman_numerals():
    assert display_title('NÓMINAS Y SEGURIDAD SOCIAL II') == 'Nóminas y seguridad social II'
    assert display_title('BASILEA II Y III: EVOLUCIÓN') == 'Basilea II y III: Evolución'
    assert display_title('RIESGOS DE CRÉDITO I') == 'Riesgos de crédito I'


def test_catalan_conjunction_i_and_elisions():
    assert display_title("CREATIVITAT I INNOVACIÓ") == 'Creativitat i innovació'
    assert display_title("PREVENCIÓ D'ACCIDENTS") == "Prevenció d'accidents"
    assert display_title("L'ÚS DE LA DESBROSSADORA") == "L'ús de la desbrossadora"


def test_capital_after_colon_and_full_stop():
    assert display_title('F.E.V.S.: VIGILANCIA EN BUQUES') == 'F.E.V.S.: Vigilancia en buques'
    assert display_title('DORA. REGLAMENTO DE RESILIENCIA') == 'DORA. Reglamento de resiliencia'
    # una sigla amb punts no tanca frase
    assert display_title('F.E.V.S. QUE PRESTEN SERVICIO') == 'F.E.V.S. que presten servicio'


def test_mixed_case_words_are_respected():
    assert display_title('SISTEMA DE I+D+i Y GESTIÓN') == 'Sistema de I+D+i y gestión'
    assert display_title('Python en ArcGIS') == 'Python en ArcGIS'


def test_hyphen_prefix_and_single_consonant():
    assert display_title('E-LEARNING EN C') == 'E-learning en C'


def test_empty():
    assert display_title('') == ''
    assert display_title(None) == ''


def test_preserve_list_size():
    assert 150 <= len(PRESERVE) <= 260
