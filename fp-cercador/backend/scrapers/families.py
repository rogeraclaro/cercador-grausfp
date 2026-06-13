"""
families.py — Catàleg canònic de famílies professionals FP.

PREFIX_MAP: prefix de codi → nom canònic de família (24 famílies + extres
del pla antic/LOGSE/HTML-only).
FAMILY_ALIASES: nom no canònic (variants de les fonts) → nom canònic.
S'aplica a pipeline.py sobre tots els registres (A–E).

Origen: extret de l'antic pdf_scraper.py quan es va eliminar el parsing de
PDFs (els Grados A/B/C ara surten de l'API REST del buscador).
"""

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
    'ART': 'Artes y Artesanías',
    'MSP': 'Mantenimiento y Servicios a la Producción',
    'SAN': 'Sanidad',
    'UF': 'Certificados de Profesionalidad',
    'MF': 'Certificados de Profesionalidad',
    # Família IA i Data (Grado E) — imatge amb alt sense prefix "Logotipo "
    'IAD': 'Inteligencia Artificial y Data',
}

FAMILY_ALIASES: dict[str, str] = {
    "Artesanía": "Artes y Artesanías",
    "Artes y Artesanias": "Artes y Artesanías",
    "Imagen y Sonido": "Imagen y Espectáculos",
    "Maritimo-Pesquera": "Marítimo-Pesquera",
    "Maritimo - Pesquera": "Marítimo-Pesquera",
    "Marítimo - Pesquera": "Marítimo-Pesquera",
}
