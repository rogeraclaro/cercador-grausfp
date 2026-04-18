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
    # Famílies del pla antic (Certificats de Professionalitat / LOGSE)
    'MSP': 'Mantenimiento y Servicios a la Producción',
    # Família IA i Data (Grado E) — imatge amb alt sense prefix "Logotipo "
    'IAD': 'Inteligencia Artificial y Data',
}

# ---------------------------------------------------------------------------
# Funcions privades — derivació de nivel per Grado
# ---------------------------------------------------------------------------


def _nivel_grado_a(code: str, is_old_plan: bool) -> None:
    """Grado A no té distinció de nivel (nou pla ni pla antic)."""
    return None


def _nivel_grado_b(code: str, is_old_plan: bool) -> int | None:
    """Grado B nou pla: nivel=None. Pla antic: extreure sufix _N (1, 2 o 3)."""
    if is_old_plan:
        m = re.search(r'_([123])$', code)
        return int(m.group(1)) if m else None
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
    new_code_re = re.compile(rf'^[A-Z]{{2,4}}_{grado_letter}_\d')

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[5:]:  # skip pàgines 1–5 (índex 0–4)
            try:
                table = page.extract_table()
            except Exception as exc:  # T-02-01: pàgina malformada → warning + continuar
                logger.warning(
                    f"Error extraient taula d'una pàgina del PDF '{pdf_path}': {exc}"
                )
                continue

            if not table:
                continue

            for row in table:
                if not row:
                    continue
                code_cell, denom_cell, obs_parts = _parse_row(row, new_code_re)

                if code_cell and code_cell not in records:
                    is_old = '(Plan antiguo)' in code_cell
                    clean_code = code_cell.replace(' (Plan antiguo)', '').strip()
                    prefix = clean_code.split('_')[0] if '_' in clean_code else ''
                    familia = PREFIX_MAP.get(prefix)

                    if not familia:
                        logger.warning(
                            f"Família desconeguda per prefix '{prefix}' al codi '{clean_code}'"
                        )
                        familia = 'Desconeguda'

                    records[code_cell] = {
                        'codigo': clean_code,
                        'denominacion': denom_cell or '',
                        'observaciones': ' '.join(obs_parts),
                        'familia': familia,
                        'nivel': nivel_fn(clean_code, is_old),
                        'plan_antiguo': is_old,
                    }

    return list(records.values())


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
