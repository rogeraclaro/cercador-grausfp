"""
pdf_scraper.py — Parsing de PDFs dels Grados A, B, C del sistema FP espanyol.

Exposa:
  parse_grado_a(pdf_path: str) -> list[dict]
  parse_grado_b(pdf_path: str) -> list[dict]
  parse_grado_c(pdf_path: str) -> list[dict]
  PREFIX_MAP: dict[str, str]  -- 24 famílies professionals

Cada registre retornat té exactament:
  {codigo, denominacion, familia, nivel, plan_antiguo, observaciones}

Camp 'id' i 'grado' els afegeix pipeline.py, NO aquest mòdul.
"""
import re
import logging
import pdfplumber

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PREFIX_MAP = {
    'AFD': 'Actividades Físicas y Deportivas',
    'ADG': 'Administración y Gestión',
    'AGA': 'Agraria',
    'ARG': 'Artes Gráficas',
    'COM': 'Comercio y Marketing',
    'ELE': 'Electricidad y Electrónica',
    'ENA': 'Energía y Agua',
    'EOC': 'Edificación y Obra Civil',
    'FME': 'Fabricación Mecánica',
    'HOT': 'Hostelería y Turismo',
    'IEX': 'Industrias Extractivas',       # NO "Imagen y Espectáculos"
    'IFC': 'Informática y Comunicaciones',
    'IMA': 'Instalación y Mantenimiento',
    'IMP': 'Imagen Personal',
    'IMS': 'Imagen y Espectáculos',        # audiovisuals, so, espectacles
    'INA': 'Industrias Alimentarias',
    'MAM': 'Madera, Mueble y Corcho',
    'MAP': 'Marítimo-Pesquera',
    'QUI': 'Química',
    'SEA': 'Seguridad y Medio Ambiente',
    'SSC': 'Servicios Socioculturales y a la Comunidad',
    'TCP': 'Textil, Confección y Piel',
    'TMV': 'Transporte y Mantenimiento de Vehículos',
    'VIC': 'Vidrio y Cerámica',
    # Famílies del pla antic / LOGSE / HTML-only
    'ART': 'Artesanía',
    'MSP': 'Mantenimiento y Servicios a la Producción',
    'SAN': 'Sanidad',
    'UF': 'Certificados de Profesionalidad',
    'MF': 'Certificados de Profesionalidad',
    # Família IA i Data (Grado E) — imatge amb alt sense prefix "Logotipo "
    'IAD': 'Inteligencia Artificial y Data',
}

# ---------------------------------------------------------------------------
# Funcions privades — derivació de nivel per Grado
# ---------------------------------------------------------------------------


def _nivel_grado_a(code: str, is_old_plan: bool) -> int | None:
    """
    Grado A nou pla (FAM_A_NNNN_XX): dedueix el nivell del segment numèric NNNN
    seguint els rangs del Catàleg Nacional de Qualificacions Professionals (CNCP):
      1–999   → Nivel 1
      1000–1999 → Nivel 2
      2000+   → Nivel 3

    Pla antic (codis UF/MF): retorna None (no deduïble sense taula externa).
    """
    if is_old_plan:
        return None
    parts = code.split('_')
    if len(parts) >= 3:
        try:
            n = int(parts[2])
            if n <= 999:
                return 1
            if n <= 1999:
                return 2
            return 3
        except ValueError:
            pass
    return None


def _nivel_grado_b(code: str, is_old_plan: bool) -> int | None:
    """Grado B nou pla (FAM_B_NNNN): dedueix el nivell del segment CNCP NNNN.
    Pla antic: extreure sufix _N (1, 2 o 3)."""
    if is_old_plan:
        m = re.search(r'_([123])$', code)
        return int(m.group(1)) if m else None
    parts = code.split('_')
    if len(parts) >= 3:
        try:
            n = int(parts[2])
            if n < 1000:
                return 1
            if n < 2000:
                return 2
            return 3
        except ValueError:
            pass
    return None


def _nivel_grado_c(code: str, is_old_plan: bool) -> int | None:
    """Grado C nou pla: _3B→1, _4B→2, _5B→3. Pla antic: None."""
    if not is_old_plan:
        if code.endswith('_3B'):
            return 1
        if code.endswith('_4B'):
            return 2
        if code.endswith('_5B'):
            return 3
    return None


# ---------------------------------------------------------------------------
# Funcions privades — parsing de files
# ---------------------------------------------------------------------------


def _parse_row(row: list, new_code_re: re.Pattern) -> tuple:
    """
    Identifica la cel·la del codi en una fila de taula pdfplumber.

    Retorna (code_cell, denom_cell, obs_parts) si la fila és una fila de dades,
    o (None, None, []) si és una fila de continuació o buit.

    El codi pot estar a qualsevol índex de columna (el nombre de columnes varia
    entre pàgines — Pitfall 1 del RESEARCH.md).
    """
    for i, cell in enumerate(row):
        if not cell or not str(cell).strip():
            continue
        cell_str = str(cell).strip()
        is_new = bool(new_code_re.match(cell_str))
        is_old = '(Plan antiguo)' in cell_str

        if is_new or is_old:
            denom = None
            for j in range(i + 1, len(row)):
                if row[j] and str(row[j]).strip():
                    denom = str(row[j]).strip()
                    break
            obs = [
                str(row[k]).strip()
                for k in range(i + 2, len(row))
                if row[k] and str(row[k]).strip()
            ]
            return cell_str, denom, obs

    return None, None, []


# ---------------------------------------------------------------------------
# Funció privada central — extracció de registres
# ---------------------------------------------------------------------------


def _extract_records(pdf_path: str, grado_letter: str, nivel_fn) -> list[dict]:
    """
    Extreu registres d'un PDF de Grado X.

    Les pàgines 0–4 (portada/intro) s'ignoren; el parsing comença a l'índex 5.
    Usa un diccionari keyed per code_cell per evitar duplicats entre pàgines
    (Pitfall 4 del RESEARCH.md): conserva únicament el primer occurrence.

    T-02-01: cada pàgina s'envolta en try/except per continuar si una pàgina
    és malformada, en lloc de fallar tot el PDF.
    """
    records: dict = {}  # code_cell -> dict (garanteix unicitat)
    new_code_re = re.compile(rf\'^[A-Z]{{2,4}}_{grado_letter}_\\d\')

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[5:]:  # skip pàgines 1–5 (índex 0–4)
            page_level = _get_nivel_from_page(page) # Nou: extreure nivell de la pàgina
            try:
                table = page.extract_table()
            except Exception as exc:  # T-02-01: pàgina malformada → warning + continuar
                logger.warning(
                    f\"Error extraient taula d\'una pàgina del PDF \'{pdf_path}\': {exc}\"
                )
                continue

            if not table:
                continue

            for row in table:
                if not row:
                    continue
                code_cell, denom_cell, obs_parts = _parse_row(row, new_code_re)

                if code_cell and code_cell not in records:
                    is_old = \'(Plan antiguo)\' in code_cell
                    clean_code = code_cell.replace(\' (Plan antiguo)\', \'\').strip()
                    # Codis nous: \'AFD_A_...\' → primary=\'AFD\'. Codis antics: \'MF2268_2\' →
                    # primary=\'MF2268\', \'UF0297\' → primary=\'UF0297\'. Extreure prefix alfabètic
                    # i provar progressivament des de la longitud màxima fins a 2 caràcters.
                    primary = clean_code.split(\'_\')[0]
                    m = re.match(r\'^([A-Z]+)\', primary)
                    alpha = m.group(1) if m else \'\'
                    prefix = \'\'
                    for length in range(len(alpha), 1, -1):
                        if alpha[:length] in PREFIX_MAP:
                            prefix = alpha[:length]
                            break
                    familia = PREFIX_MAP.get(prefix)

                    if not familia:
                        logger.warning(
                            f\"Família desconeguda per prefix \'{prefix}\' al codi \'{clean_code}\'\"\n                        )
                        familia = \'Desconeguda\'

                    records[code_cell] = {
                        \'codigo\': clean_code,
                        \'denominacion\': denom_cell or \'\',
                        \'observaciones\': \' \'.join(obs_parts),\n                        \'familia\': familia,
                        \'nivel\': page_level if grado_letter == \'B\' else nivel_fn(clean_code, is_old), # Aplica nivell de pàgina per Grau B, altrament usa funció
                        \'plan_antiguo\': is_old,
                    }

    return list(records.values())

def _get_nivel_from_page(page) -> int | None:
    \"\"\"
    Intenta extreure el nivell (1, 2 o 3) del text de la pàgina.
    Cerca el patró "/Nivel [1-3]" a la part superior dreta de la pàgina.
    \"\"\"
    try:
        # Definir una àrea de cerca a la part superior dreta de la pàgina
        # Assumim que la pàgina té un format consistent.
        # Coordenades (x0, y0, x1, y1)
        # Una àrea de 300x50px a la part superior dreta
        x0, y0, x1, y1 = page.width - 300, 0, page.width, 50
        bbox_area = (x0, y0, x1, y1)
        text = page.crop(bbox_area).extract_text()

        match = re.search(r\'/Nivel\s+(\\d)\', text)
        if match:
            return int(match.group(1))
    except Exception as exc:
        logger.debug(f\"No s\'ha pogut extreure el nivell de la pàgina: {exc}\")
    return None


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def parse_grado_a(pdf_path: str) -> list[dict]:
    """Parseja el PDF de Grado A i retorna llista de registres."""
    return _extract_records(pdf_path, 'A', _nivel_grado_a)


def parse_grado_b(pdf_path: str) -> list[dict]:
    """Parseja el PDF de Grado B i retorna llista de registres."""
    return _extract_records(pdf_path, 'B', _nivel_grado_b)


def parse_grado_c(pdf_path: str) -> list[dict]:
    """Parseja el PDF de Grado C i retorna llista de registres."""
    return _extract_records(pdf_path, 'C', _nivel_grado_c)
